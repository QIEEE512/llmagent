from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pymongo.errors import PyMongoError

import app.db as db
from app import deps
from app.config import settings
from app.schemas import ApiResponse
from app.services.oss import presign_get_url
from app.services.profile_exports import create_export_to_oss, generate_share_id

router = APIRouter()


def _coll(database, name: str):
    try:
        return getattr(database, name)
    except Exception:
        return database[name]


def _now() -> datetime:
    return datetime.utcnow()


def _dt_to_iso(v: Any) -> Any:
    if isinstance(v, datetime):
        return v.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    return v


def _get_active_account_id(database, user_id: str) -> str:
    # keep consistent with chat.py & conversations.py & profile_story.py
    users = _coll(database, "users")
    accounts = _coll(database, "accounts")

    user = users.find_one({"_id": user_id})
    if not user:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")

    active = user.get("activeAccountId")
    if not active:
        acc = accounts.find_one({"userId": user_id})
        if acc and acc.get("_id"):
            active = str(acc.get("_id"))
            try:
                users.update_one({"_id": user_id}, {"$set": {"activeAccountId": active}})
            except Exception:
                pass

    if not active:
        active = f"a_{ObjectId()}"
        try:
            accounts.insert_one({"_id": active, "userId": user_id, "name": "默认账号", "account": user.get("account"), "createdAt": 0})
        except Exception:
            pass
        try:
            users.update_one({"_id": user_id}, {"$set": {"activeAccountId": active}})
        except Exception:
            pass

    if not active:
        raise HTTPException(status_code=400, detail="no active account")

    return str(active)


def _require_story_owner(database, *, story_id: str, user_id: str, account_id: str) -> dict:
    stories = _coll(database, "profile_stories")
    doc = stories.find_one({"_id": story_id, "userId": user_id, "accountId": account_id, "deletedAt": {"$exists": False}})
    if not doc:
        raise HTTPException(status_code=404, detail="story not found")
    return doc


@router.post("/profile/stories/{story_id}/export-word", response_model=ApiResponse)
def profile_story_export_word(
    story_id: str,
    payload: Optional[dict[str, Any]] = None,
    user_id: str = Depends(deps.get_current_user_id),
):
    payload = payload or {}
    template = (payload.get("template") or "default").strip() or "default"

    database = db.get_db()
    account_id = _get_active_account_id(database, user_id)

    story_doc = _require_story_owner(database, story_id=story_id, user_id=user_id, account_id=account_id)

    # Create export and upload to OSS
    try:
        res = create_export_to_oss(story_id=story_id, user_id=user_id, account_id=account_id, story_doc=story_doc, template=template)
    except RuntimeError as e:
        # OSS missing creds or HTTP failure
        raise HTTPException(status_code=503, detail=f"OSS unavailable: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"export failed: {type(e).__name__}")

    exports = _coll(database, "profile_story_exports")
    doc = {
        "_id": res.export_id,
        "exportId": res.export_id,
        "storyId": story_id,
        "userId": user_id,
        "accountId": account_id,
        "template": template,
        "fileName": res.file_name,
        "objectKey": res.object_key,
    "pdfFileName": res.pdf_file_name,
    "pdfObjectKey": res.pdf_object_key,
        "storage": {"type": "oss", "bucket": None},
        "createdAt": res.created_at,
    }

    try:
        exports.insert_one(doc)
    except PyMongoError as e:
        raise HTTPException(status_code=503, detail=f"数据库不可用：{e}")

    # return a short-lived signed url for immediate download
    try:
        file_url = presign_get_url(object_key=res.object_key)
    except Exception:
        file_url = None

    try:
        pdf_url = presign_get_url(object_key=res.pdf_object_key)
    except Exception:
        pdf_url = None

    return ApiResponse(
        ok=True,
        data={
            "exportId": res.export_id,
            "storyId": story_id,
            "fileName": res.file_name,
            "fileUrl": file_url,
            "pdfFileName": res.pdf_file_name,
            "pdfUrl": pdf_url,
            "createdAt": _dt_to_iso(res.created_at),
        },
    )


def _find_export(database, *, story_id: str, user_id: str, account_id: str, export_id: str) -> dict:
    exports = _coll(database, "profile_story_exports")
    doc = exports.find_one({"_id": export_id, "storyId": story_id, "userId": user_id, "accountId": account_id})
    if not doc:
        raise HTTPException(status_code=404, detail="export not found")
    return doc


def _latest_export(database, *, story_id: str, user_id: str, account_id: str) -> Optional[dict]:
    exports = _coll(database, "profile_story_exports")
    try:
        cursor = exports.find({"storyId": story_id, "userId": user_id, "accountId": account_id})
        try:
            cursor = cursor.sort("createdAt", -1)
        except Exception:
            pass
        items = list(cursor)
        return items[0] if items else None
    except Exception:
        return None


@router.post("/profile/stories/{story_id}/share", response_model=ApiResponse)
def profile_story_share_create(
    story_id: str,
    payload: Optional[dict[str, Any]] = None,
    user_id: str = Depends(deps.get_current_user_id),
):
    payload = payload or {}
    export_id = (payload.get("exportId") or "").strip() or None
    expires_in_days = payload.get("expiresInDays")
    if expires_in_days is None:
        expires_in_days = 7
    try:
        expires_in_days = int(expires_in_days)
    except Exception:
        raise HTTPException(status_code=400, detail="expiresInDays must be int")

    if expires_in_days < 1:
        expires_in_days = 1
    if expires_in_days > 30:
        expires_in_days = 30

    database = db.get_db()
    account_id = _get_active_account_id(database, user_id)

    # owner check
    story_doc = _require_story_owner(database, story_id=story_id, user_id=user_id, account_id=account_id)

    # resolve export
    export_doc: Optional[dict] = None
    if export_id:
        export_doc = _find_export(database, story_id=story_id, user_id=user_id, account_id=account_id, export_id=export_id)
    else:
        export_doc = _latest_export(database, story_id=story_id, user_id=user_id, account_id=account_id)
        if not export_doc:
            # auto export when none exists
            try:
                res = create_export_to_oss(story_id=story_id, user_id=user_id, account_id=account_id, story_doc=story_doc, template="default")
            except RuntimeError as e:
                raise HTTPException(status_code=503, detail=f"OSS unavailable: {e}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"export failed: {type(e).__name__}")

            exports = _coll(database, "profile_story_exports")
            export_doc = {
                "_id": res.export_id,
                "exportId": res.export_id,
                "storyId": story_id,
                "userId": user_id,
                "accountId": account_id,
                "template": "default",
                "fileName": res.file_name,
                "objectKey": res.object_key,
                "pdfFileName": res.pdf_file_name,
                "pdfObjectKey": res.pdf_object_key,
                "storage": {"type": "oss", "bucket": None},
                "createdAt": res.created_at,
            }
            try:
                exports.insert_one(export_doc)
            except PyMongoError as e:
                raise HTTPException(status_code=503, detail=f"数据库不可用：{e}")

    assert export_doc is not None

    share_id = generate_share_id()
    now = _now()
    expires_at = now + timedelta(days=expires_in_days)

    shares = _coll(database, "profile_story_shares")
    share_doc = {
        "_id": share_id,
        "shareId": share_id,
        "storyId": story_id,
        "exportId": str(export_doc.get("_id")),
        "userId": user_id,
        "accountId": account_id,
        "status": "active",
        "createdAt": now,
        "expiresAt": expires_at,
    }

    try:
        shares.insert_one(share_doc)
    except PyMongoError as e:
        raise HTTPException(status_code=503, detail=f"数据库不可用：{e}")

    # shareUrl: public web page entry
    share_url = f"/s/{share_id}/view"
    share_download_url = f"/s/{share_id}"

    base = (settings.public_base_url or settings.oss_public_base_url or "").rstrip("/")
    share_full_url = f"{base}{share_url}" if base else None

    return ApiResponse(
        ok=True,
        data={
            "shareId": share_id,
            "shareUrl": share_url,
            "shareDownloadUrl": share_download_url,
            "shareFullUrl": share_full_url,
            "expiresAt": _dt_to_iso(expires_at),
            "status": "active",
        },
    )


@router.post("/profile/shares/{share_id}/revoke", response_model=ApiResponse)
def profile_share_revoke(
    share_id: str,
    user_id: str = Depends(deps.get_current_user_id),
):
    database = db.get_db()
    account_id = _get_active_account_id(database, user_id)
    shares = _coll(database, "profile_story_shares")

    doc = shares.find_one({"_id": share_id, "userId": user_id, "accountId": account_id})
    if not doc:
        raise HTTPException(status_code=404, detail="share not found")

    if (doc.get("status") or "active") == "revoked":
        # idempotent
        revoked_at = doc.get("revokedAt")
        return ApiResponse(ok=True, data={"shareId": share_id, "status": "revoked", "revokedAt": _dt_to_iso(revoked_at)})

    now = _now()
    try:
        shares.update_one({"_id": share_id, "userId": user_id, "accountId": account_id}, {"$set": {"status": "revoked", "revokedAt": now}})
    except PyMongoError as e:
        raise HTTPException(status_code=503, detail=f"数据库不可用：{e}")

    return ApiResponse(ok=True, data={"shareId": share_id, "status": "revoked", "revokedAt": _dt_to_iso(now)})
