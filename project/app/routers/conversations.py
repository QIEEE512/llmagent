from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pymongo.errors import PyMongoError

import app.db as db
from app import deps
from app.schemas import ApiResponse

router = APIRouter()


def _coll(database, name: str):
    """Get collection from either a pymongo Database (attribute access) or a dict-like fake db (item access)."""

    try:
        return getattr(database, name)
    except Exception:
        return database[name]


def _now() -> datetime:
    return datetime.utcnow()


def _get_active_account_id(database, user_id: str) -> str:
    """Same behavior as chat.py: conversations are isolated by (userId, activeAccountId)."""

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


def _conv_brief(conv: dict) -> dict:
    return {
        "conversationId": str(conv.get("_id")),
        "title": conv.get("title") or "新对话",
        "lastMessage": conv.get("lastMessage"),
        "updatedAt": conv.get("updatedAt"),
    }


def _msg_out(m: dict) -> dict:
    return {
        "messageId": str(m.get("_id")),
        "role": m.get("role"),
        # Storage-level field name is `content`, frontend expects `text`.
        "text": m.get("text") if m.get("text") is not None else m.get("content"),
        "attachments": m.get("attachments") or [],
        "createdAt": m.get("createdAt"),
    }


def _summarize_last_message(role: str, text: str, attachments: list[dict]) -> str:
    t = (text or "").strip()
    if t:
        return t[:50]
    if attachments:
        # very small summary for list rendering
        img_n = sum(1 for a in attachments if a.get("type") == "image")
        file_n = sum(1 for a in attachments if a.get("type") == "file")
        parts = []
        if img_n:
            parts.append(f"{img_n}张图片")
        if file_n:
            parts.append(f"{file_n}个文件")
        return "附件：" + " ".join(parts)
    # empty message shouldn't happen (frontend should validate), keep a placeholder
    return "(空消息)"


@router.get("/conversations", response_model=ApiResponse)
def conversations_list(user_id: str = Depends(deps.get_current_user_id)):
    database = db.get_db()
    account_id = _get_active_account_id(database, user_id)

    conversations = _coll(database, "conversations")

    try:
        cursor = conversations.find({"userId": user_id, "accountId": account_id, "deletedAt": {"$exists": False}})
        try:
            cursor = cursor.sort("updatedAt", -1)
        except Exception:
            pass
        items = [_conv_brief(c) for c in cursor]
    except PyMongoError as e:
        raise HTTPException(status_code=503, detail=f"数据库不可用：{e}")
    except Exception:
        # fake db might not support find/sort
        items = []

    return ApiResponse(ok=True, data=items)


@router.post("/conversations", response_model=ApiResponse)
def conversations_create(payload: Optional[dict[str, Any]] = None, user_id: str = Depends(deps.get_current_user_id)):
    payload = payload or {}
    title = (payload.get("title") or "").strip() or "新对话"

    database = db.get_db()
    account_id = _get_active_account_id(database, user_id)
    conversations = _coll(database, "conversations")

    now = _now()
    conversation_id = f"c_{ObjectId()}"
    doc = {
        "_id": conversation_id,
        "userId": user_id,
        "accountId": account_id,
        "title": title,
        "lastMessage": None,
        "createdAt": now,
        "updatedAt": now,
    }

    try:
        conversations.insert_one(doc)
    except PyMongoError as e:
        raise HTTPException(status_code=503, detail=f"数据库不可用：{e}")

    return ApiResponse(ok=True, data={"conversationId": conversation_id, "title": title})


@router.get("/conversations/{conversationId}", response_model=ApiResponse)
def conversations_get(conversationId: str, user_id: str = Depends(deps.get_current_user_id)):
    conversation_id = (conversationId or "").strip()
    if not conversation_id:
        raise HTTPException(status_code=400, detail="conversationId is required")

    database = db.get_db()
    account_id = _get_active_account_id(database, user_id)

    conversations = _coll(database, "conversations")
    messages = _coll(database, "messages")

    try:
        conv = conversations.find_one(
            {"_id": conversation_id, "userId": user_id, "accountId": account_id, "deletedAt": {"$exists": False}}
        )
    except PyMongoError as e:
        raise HTTPException(status_code=503, detail=f"数据库不可用：{e}")

    if not conv:
        raise HTTPException(status_code=404, detail="conversation not found")

    msgs: List[dict] = []
    try:
        if hasattr(messages, "find"):
            cursor = messages.find({"conversationId": conversation_id, "userId": user_id, "accountId": account_id})
            try:
                cursor = cursor.sort("createdAt", 1)
            except Exception:
                pass
            msgs = [_msg_out(m) for m in cursor]
    except PyMongoError as e:
        raise HTTPException(status_code=503, detail=f"数据库不可用：{e}")

    return ApiResponse(
        ok=True,
        data={
            "conversationId": conversation_id,
            "title": conv.get("title") or "新对话",
            "messages": msgs,
        },
    )


@router.post("/conversations/{conversationId}/messages", response_model=ApiResponse)
def conversations_append_message(conversationId: str, payload: dict[str, Any], user_id: str = Depends(deps.get_current_user_id)):
    conversation_id = (conversationId or "").strip()
    if not conversation_id:
        raise HTTPException(status_code=400, detail="conversationId is required")

    role = (payload.get("role") or "").strip()
    if role not in ("user", "assistant", "system"):
        raise HTTPException(status_code=400, detail="role invalid")

    text = (payload.get("text") or "")
    attachments = payload.get("attachments") or []
    if attachments is None:
        attachments = []
    if not isinstance(attachments, list):
        raise HTTPException(status_code=400, detail="attachments must be an array")

    client_msg_id = payload.get("clientMsgId")
    if client_msg_id is not None:
        client_msg_id = str(client_msg_id).strip() or None

    database = db.get_db()
    account_id = _get_active_account_id(database, user_id)

    conversations = _coll(database, "conversations")
    messages = _coll(database, "messages")

    try:
        conv = conversations.find_one(
            {"_id": conversation_id, "userId": user_id, "accountId": account_id, "deletedAt": {"$exists": False}}
        )
    except PyMongoError as e:
        raise HTTPException(status_code=503, detail=f"数据库不可用：{e}")

    if not conv:
        raise HTTPException(status_code=404, detail="conversation not found")

    # Idempotency: (conversationId, clientMsgId)
    if client_msg_id and hasattr(messages, "find_one"):
        try:
            existed = messages.find_one(
                {
                    "conversationId": conversation_id,
                    "userId": user_id,
                    "accountId": account_id,
                    "clientMsgId": client_msg_id,
                }
            )
            if existed and existed.get("_id"):
                return ApiResponse(
                    ok=True,
                    data={
                        "messageId": str(existed.get("_id")),
                        "conversationId": conversation_id,
                        "updatedAt": conv.get("updatedAt"),
                    },
                )
        except PyMongoError as e:
            raise HTTPException(status_code=503, detail=f"数据库不可用：{e}")

    now = _now()
    message_id = f"m_{ObjectId()}"

    msg_doc = {
        "_id": message_id,
        "conversationId": conversation_id,
        "userId": user_id,
        "accountId": account_id,
        "role": role,
        "content": text,
        "attachments": attachments,
        "clientMsgId": client_msg_id,
        "createdAt": now,
    }

    try:
        messages.insert_one(msg_doc)
    except PyMongoError as e:
        raise HTTPException(status_code=503, detail=f"数据库不可用：{e}")

    last_message = _summarize_last_message(role=role, text=str(text or ""), attachments=attachments)

    try:
        conversations.update_one(
            {"_id": conversation_id, "userId": user_id, "accountId": account_id},
            {"$set": {"updatedAt": now, "lastMessage": last_message}},
        )
    except Exception:
        # don't block storing message
        pass

    return ApiResponse(ok=True, data={"messageId": message_id, "conversationId": conversation_id, "updatedAt": now})


@router.post("/conversations/{conversationId}/delete", response_model=ApiResponse)
def conversations_delete(conversationId: str, user_id: str = Depends(deps.get_current_user_id)):
    conversation_id = (conversationId or "").strip()
    if not conversation_id:
        raise HTTPException(status_code=400, detail="conversationId is required")

    database = db.get_db()
    account_id = _get_active_account_id(database, user_id)
    conversations = _coll(database, "conversations")

    now = _now()
    try:
        res = conversations.update_one(
            {"_id": conversation_id, "userId": user_id, "accountId": account_id, "deletedAt": {"$exists": False}},
            {"$set": {"deletedAt": now, "updatedAt": now}},
        )
        # pymongo returns modified_count; fake db might not
        if hasattr(res, "matched_count") and res.matched_count == 0:
            raise HTTPException(status_code=404, detail="conversation not found")
    except HTTPException:
        raise
    except PyMongoError as e:
        raise HTTPException(status_code=503, detail=f"数据库不可用：{e}")
    except Exception:
        pass

    return ApiResponse(ok=True, data=None)
