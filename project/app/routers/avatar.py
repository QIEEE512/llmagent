from __future__ import annotations

import time

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pathlib import Path
from typing import Any

import httpx

import app.db as db
import app.deps as deps
from app.schemas import ApiResponse, AvatarActiveResponseData, AvatarGenerateRequest, AvatarProfile, AvatarVoice
from app.services.documents import resolve_local_path_from_files_url
from app.services.wanx import (
    wan_i2v_create_task,
    wan_i2v_download_video_to_file,
    wan_i2v_fetch,
    wanx_t2i_generate_to_file,
)
from app.services.oss import put_file_from_local, presign_get_url
from pymongo.errors import PyMongoError

from app.routers.upload import _save_file

router = APIRouter(prefix="/avatar", tags=["Avatar"])

USER_AVATAR_ACCOUNT_ID = "__user__"


def _coll(database, name: str):
    try:
        return getattr(database, name)
    except Exception:
        return database[name]


def _get_active_account_id(database, user_id: str) -> str:
    """Same semantics as chat._get_active_account_id: use users.activeAccountId; fallback to first/auto-create."""

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
        # auto create a default account
        from bson import ObjectId

        active = f"a_{ObjectId()}"
        try:
            accounts.insert_one(
                {
                    "_id": active,
                    "userId": user_id,
                    "name": "默认账号",
                    "account": user.get("account"),
                    "createdAt": 0,
                }
            )
        except Exception:
            pass
        try:
            users.update_one({"_id": user_id}, {"$set": {"activeAccountId": active}})
        except Exception:
            pass

    if not active:
        raise HTTPException(status_code=400, detail="no active account")
    return str(active)


def _resolve_avatar_scope(database, *, user_id: str, scope: str) -> tuple[str, str]:
    scope = (scope or "").strip().lower() or "account"
    if scope not in ("account", "user"):
        raise HTTPException(status_code=400, detail="scope must be account or user")

    if scope == "user":
        return scope, USER_AVATAR_ACCOUNT_ID

    account_id = _get_active_account_id(database, user_id)
    return scope, account_id


def _now_ts() -> int:
    return int(time.time())


def _build_sound_description(*, profile: dict | None, intro_text: str) -> str:
    p = profile or {}
    age = p.get("age")
    interests = p.get("interests") or []
    style = (p.get("style") or "").strip()
    free_text = (p.get("freeText") or "").strip()

    if not isinstance(interests, list):
        interests = []

    age_group = "儿童"
    if isinstance(age, int) and age <= 6:
        age_group = "幼儿"
    elif isinstance(age, int) and age >= 13:
        age_group = "青少年"

    interest_text = "、".join([str(x) for x in interests if str(x).strip()])
    if not interest_text:
        interest_text = "学习和探索"

    speech_content = intro_text.strip() if intro_text else f"大家好，我是{age_group}小朋友，我喜欢{interest_text}。"

    voice_style = "清亮童声"
    if age_group == "幼儿":
        voice_style = "稚嫩童声"
    elif age_group == "青少年":
        voice_style = "阳光少年音色"

    tone_style = "自然上扬"
    if style:
        tone_style = f"{tone_style}，带{style}风格"
    if free_text:
        tone_style = f"{tone_style}，{free_text}"

    return (
        "声音描述：\n"
        f"- 人声：说“{speech_content}”；情绪友好愉快；语调{tone_style}；语速适中；音色{voice_style}；口音普通话；口型清晰与语音同步。\n"
        "- 音效：轻微环境音，偶尔有细微动作声，不喧宾夺主。\n"
        "- 背景音乐：温暖轻快的钢琴/木吉他配乐，节奏中等偏轻。"
    )


@router.post("/upload", response_model=ApiResponse)
def avatar_upload(
    user_id: str = Depends(deps.get_current_user_id),
    file: UploadFile = File(...),
):
    save_path, url = _save_file(file)
    p = Path(save_path)
    size = None
    try:
        size = p.stat().st_size
    except Exception:
        size = None

    return ApiResponse(
        data={
            "url": url,
            "name": file.filename or p.name,
            "size": size,
            "mime": file.content_type or "application/octet-stream",
        }
    )


@router.post("/generate", response_model=ApiResponse)
def avatar_generate(
    payload: AvatarGenerateRequest,
    scope: str = "account",
    user_id: str = Depends(deps.get_current_user_id),
):
    """Generate a cartoon avatar and bind it to the *active account*.

    Contract aligns with FRONTEND_TODO.md一期：同步返回 imageUrl。
    Each account only keeps one current avatar: we upsert into avatars by (userId, accountId).
    """

    # Security: only accept /files/... url
    try:
        _ = resolve_local_path_from_files_url(payload.portraitUrl)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="portraitUrl is invalid")

    database = db.get_db()
    scope, account_id = _resolve_avatar_scope(database, user_id=user_id, scope=scope)

    avatars = _coll(database, "avatars")

    # Use WanX T2I to generate avatar image and save it under /tmp/uploads (served by /files/..)
    # If model key is missing, surface as a user-friendly error.
    try:
        prompt = (
            "请根据以下设定生成一张儿童卡通风格的半身头像，画面干净、背景简洁、风格统一。\n"
            f"年龄: {payload.profile.age}\n"
            f"兴趣: {', '.join(payload.profile.interests or [])}\n"
            f"风格: {payload.profile.style or ''}\n"
            f"补充: {payload.profile.freeText or ''}\n"
            "要求：明亮、友好、可爱，适合儿童。"
        ).strip()

        fp, image_url = wanx_t2i_generate_to_file(
            prompt=prompt,
            size="1024*1024",
            filename_prefix="avatar_",
        )
    except RuntimeError as e:
        # model call / download failure
        msg = str(e)
        # InvalidParameter is a client-side request issue (e.g., size not allowed)
        if "InvalidParameter" in msg or "invalid parameter" in msg.lower() or "does not match the allowed size" in msg:
            raise HTTPException(status_code=400, detail=msg)
        raise HTTPException(status_code=502, detail=msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"avatar generation failed: {type(e).__name__}")
    avatar_id = f"av_{user_id}_{account_id}"

    doc: dict[str, Any] = {
        "_id": avatar_id,
        "userId": user_id,
        "accountId": account_id,
        "status": "succeeded",
        "portraitUrl": payload.portraitUrl,
        "imageUrl": image_url,
        "profile": payload.profile.model_dump(),
        "voice": payload.voice.model_dump(),
        "output": payload.output.model_dump() if payload.output else None,
        "updatedAt": _now_ts(),
        # keep first create time if exist
        "$setOnInsert": {"createdAt": _now_ts()},
    }

    try:
        # upsert: overwrite update fields; keep createdAt
        update = {"$set": {k: v for k, v in doc.items() if k != "$setOnInsert"}, "$setOnInsert": doc["$setOnInsert"]}
        avatars.update_one({"userId": user_id, "accountId": account_id}, update, upsert=True)
        saved = avatars.find_one({"userId": user_id, "accountId": account_id})
    except PyMongoError as e:
        raise HTTPException(status_code=503, detail=f"数据库不可用：{e}")

    saved_id = str((saved or {}).get("_id") or avatar_id)
    data = {
        # 前端兼容字段
        "avatarId": saved_id,
        "id": saved_id,
        "imageUrl": image_url,
        "url": image_url,
        "scope": scope,
        "meta": {"style": (payload.output.characterStyle if payload.output else None) or "kids_cartoon"},
    }
    return ApiResponse(ok=True, data=data)


@router.get("/active", response_model=ApiResponse)
def avatar_active(scope: str = "account", user_id: str = Depends(deps.get_current_user_id)):
    """Get active account's current avatar.

    Each account only keeps one avatar, so this returns at most one record.
    """

    database = db.get_db()
    scope, account_id = _resolve_avatar_scope(database, user_id=user_id, scope=scope)
    avatars = _coll(database, "avatars")

    try:
        doc = avatars.find_one({"userId": user_id, "accountId": account_id})
    except PyMongoError as e:
        raise HTTPException(status_code=503, detail=f"数据库不可用：{e}")

    if not doc:
        return ApiResponse(ok=True, data=None)

    data = AvatarActiveResponseData(
        avatarId=str(doc.get("_id")),
        imageUrl=str(doc.get("imageUrl")),
        portraitUrl=doc.get("portraitUrl"),
        profile=AvatarProfile(**doc.get("profile")) if isinstance(doc.get("profile"), dict) else None,
        voice=AvatarVoice(**doc.get("voice")) if isinstance(doc.get("voice"), dict) else None,
        createdAt=doc.get("createdAt"),
    )
    payload = data.model_dump()
    payload["scope"] = scope
    return ApiResponse(ok=True, data=payload)


@router.post("/video/generate", response_model=ApiResponse)
def avatar_video_generate(
    payload: dict,
    scope: str = "account",
    user_id: str = Depends(deps.get_current_user_id),
):
    """Create an image-to-video generation job for current account.

    Request (suggested): { imageUrl: "/files/xxx.png", prompt?: "..." }
    Response: { ok: true, data: { jobId } }
    """

    image_url = (
        payload.get("imageUrl")
        or payload.get("imgUrl")
        or payload.get("fileUrl")
        or payload.get("url")
        or ""
    ).strip()

    intro_text = (payload.get("introText") or payload.get("intro") or "").strip()
    resolution = (payload.get("resolution") or "720P").strip() or "720P"
    duration = payload.get("duration") or 10
    shot_type = (payload.get("shotType") or payload.get("shot_type") or "multi").strip() or "multi"

    database = db.get_db()
    scope, account_id = _resolve_avatar_scope(database, user_id=user_id, scope=scope)

    # Backward-compatible fallback:
    # If imageUrl is missing, use current account's active avatar imageUrl.
    avatar_profile = None
    if not image_url:
        avatars = _coll(database, "avatars")
        try:
            av = avatars.find_one({"userId": user_id, "accountId": account_id})
        except PyMongoError as e:
            raise HTTPException(status_code=503, detail=f"数据库不可用：{e}")

        image_url = str((av or {}).get("imageUrl") or "").strip()
        if isinstance(av, dict):
            avatar_profile = av.get("profile") if isinstance(av.get("profile"), dict) else None
        if not image_url:
            raise HTTPException(status_code=400, detail="imageUrl is required (or generate an avatar first)")
    else:
        avatars = _coll(database, "avatars")
        try:
            av = avatars.find_one({"userId": user_id, "accountId": account_id})
            if isinstance(av, dict):
                avatar_profile = av.get("profile") if isinstance(av.get("profile"), dict) else None
        except PyMongoError:
            avatar_profile = None

    if not image_url.startswith("/files/"):
        raise HTTPException(status_code=400, detail="fileUrl must start with /files/")

    # security: only allow local files
    local_fp = resolve_local_path_from_files_url(image_url)

    base_prompt = (payload.get("prompt") or "").strip() or "让这个卡通形象做自然的微笑、点头和挥手动作，背景保持简洁。"
    sound_desc = _build_sound_description(profile=avatar_profile, intro_text=intro_text)
    prompt = (
        "主体：儿童卡通角色\n"
        "场景：明亮、简洁、温暖的学习环境\n"
        f"运动：{base_prompt}\n"
        f"{sound_desc}"
    )

    jobs = _coll(database, "avatar_video_jobs")

    # Upload local /files/* to OSS (private bucket) and generate a signed URL for the cloud model.
    # This avoids DashScope i2v failing on local, non-public URLs.
    try:
        put_res = put_file_from_local(local_fp, object_key=f"i2v_inputs/{local_fp.name}")
        model_img_url = presign_get_url(object_key=put_res.object_key)
    except RuntimeError as e:
        # Missing OSS creds or upload failed
        raise HTTPException(status_code=503, detail=f"OSS unavailable: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OSS upload failed: {type(e).__name__}")

    # Preflight check: ensure the signed URL is reachable and looks like an image.
    # This makes it far easier to diagnose DataInspection failures.
    try:
        ct = None
        status = None
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            hr = client.head(model_img_url)
            status = hr.status_code
            ct = (hr.headers.get("content-type") or "").split(";")[0].strip().lower() or None
            # Some OSS setups don't support HEAD reliably; fallback to GET with range
            if status >= 400 or not ct:
                gr = client.get(model_img_url, headers={"Range": "bytes=0-15"})
                status = gr.status_code
                ct = (gr.headers.get("content-type") or "").split(";")[0].strip().lower() or None
        if status and status >= 400:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"OSS signed url is not reachable (status={status}, content-type={ct}). "
                    "Common causes: object not found, signature mismatch/expired, bucket policy blocks access."
                ),
            )
        if ct and not ct.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"OSS signed url content-type is not image/* (content-type={ct}). "
                    "This usually means OSS returned an error XML/HTML instead of the image."
                ),
            )
    except HTTPException:
        raise
    except Exception as e:
        # Keep message short but actionable
        raise HTTPException(status_code=400, detail=f"OSS signed url preflight failed: {type(e).__name__}")

    try:
        task_id, task_status = wan_i2v_create_task(
            prompt=prompt,
            img_url=model_img_url,
            audio_url=None,
            resolution=resolution,
            duration=int(duration),
            shot_type=shot_type,
            model="wan2.6-i2v-flash",
        )
    except RuntimeError as e:
        msg = str(e)
        # DashScope returns 400 InvalidParameter.DataInspection when img_url format/visibility is invalid.
        # Typical cause in our setup: using local "/files/..." URL which is not publicly accessible.
        if "InvalidParameter.DataInspection" in msg or "data inspection" in msg.lower():
            raise HTTPException(
                status_code=400,
                detail=(
                    f"i2v input image is invalid or unsupported: {msg}. "
                    "Tip: ensure the image URL is reachable by the cloud model and is a standard image (png/jpg/webp)."
                ),
            )
        raise HTTPException(status_code=502, detail=msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"video generation failed: {type(e).__name__}")

    job_id = f"vj_{task_id}"
    now = _now_ts()
    doc: dict[str, Any] = {
        "_id": job_id,
        "taskId": task_id,
        "status": task_status,
        "userId": user_id,
        "accountId": account_id,
        "imageUrl": image_url,
        "introText": intro_text or None,
        "prompt": prompt,
        "videoUrl": None,
        "updatedAt": now,
    }

    try:
        # createdAt must only appear in one update operator, otherwise MongoDB raises
        # "Updating the path 'createdAt' would create a conflict".
        update_doc = {"$set": doc, "$setOnInsert": {"createdAt": now}}
        jobs.update_one({"_id": job_id}, update_doc, upsert=True)
    except PyMongoError as e:
        raise HTTPException(status_code=503, detail=f"数据库不可用：{e}")

    return ApiResponse(ok=True, data={"jobId": job_id})


@router.get("/video/status", response_model=ApiResponse)
def avatar_video_status(
    jobId: str,
    scope: str = "account",
    user_id: str = Depends(deps.get_current_user_id),
):
    """Query video generation job status.

    If the DashScope task is finished and returns a remote video url, this endpoint downloads it
    to /tmp/uploads and stores local /files/... url as videoUrl.
    """

    job_id = (jobId or "").strip()
    if not job_id:
        raise HTTPException(status_code=400, detail="jobId is required")

    database = db.get_db()
    scope, account_id = _resolve_avatar_scope(database, user_id=user_id, scope=scope)
    jobs = _coll(database, "avatar_video_jobs")

    try:
        job = jobs.find_one({"_id": job_id, "userId": user_id, "accountId": account_id})
    except PyMongoError as e:
        raise HTTPException(status_code=503, detail=f"数据库不可用：{e}")

    if not job:
        raise HTTPException(status_code=404, detail="job not found")

    # If already has local videoUrl, return directly
    if job.get("videoUrl"):
        return ApiResponse(
            ok=True,
            data={"jobId": job_id, "status": job.get("status"), "videoUrl": job.get("videoUrl"), "scope": scope},
        )

    task_id = job.get("taskId")
    if not task_id:
        return ApiResponse(
            ok=True,
            data={"jobId": job_id, "status": job.get("status") or "UNKNOWN", "videoUrl": None, "scope": scope},
        )

    try:
        rsp = wan_i2v_fetch(task_id=str(task_id))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    out = getattr(rsp, "output", None)
    task_status = getattr(out, "task_status", None) or job.get("status") or "UNKNOWN"
    remote_video_url = getattr(out, "video_url", None)

    update: dict[str, Any] = {"status": task_status, "updatedAt": _now_ts()}

    # If remote video url is ready, download once and persist local url
    if remote_video_url:
        try:
            _fp, local_url = wan_i2v_download_video_to_file(video_url=str(remote_video_url), filename_prefix="avatar_video_")
            update["videoUrl"] = local_url
        except Exception:
            # keep status; surface without failing whole query
            update["videoUrl"] = None

    try:
        jobs.update_one({"_id": job_id}, {"$set": update})
        job = jobs.find_one({"_id": job_id})
    except PyMongoError:
        pass

    return ApiResponse(
        ok=True,
        data={
            "jobId": job_id,
            "status": update.get("status"),
            "videoUrl": update.get("videoUrl") or (job.get("videoUrl") if job else None),
            "scope": scope,
        },
    )
