from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import Response
from fastapi.responses import StreamingResponse

from app.routers.asr import router as asr_router
from app.routers.accounts import router as accounts_router
from app.routers.auth import router as auth_router
from app.routers.avatar import router as avatar_router
from app.routers.chat import router as chat_router
from app.routers.conversations import router as conversations_router
from app.routers.doc import router as doc_router
from app.routers.profile_story import router as profile_story_router
from app.routers.profile_share import router as profile_share_router
from app.routers.upload import router as upload_router
from app.routers.voice import router as voice_router
from app.routers.public_share import router as public_share_router

import app.db as db
from app.security import hash_password

app = FastAPI(title="我的数字老师 - 后端接口", version="0.1.0")
_UPLOAD_ROOT = Path("/tmp/uploads").resolve()


@app.on_event("startup")
def _seed_debug_user() -> None:
    """为登录页联调预置账号：1008611/1008611。

    目标：前端不依赖注册流程也能测试登录、拿到 token，并访问需要鉴权的接口。
    """

    try:
        database = db.get_db()
        users = database["users"]

        account = "1008611"
        if users.find_one({"account": account}):
            return

        users.insert_one(
            {
                "_id": "u_1008611",
                "name": "调试用户",
                "account": account,
                "phone": None,
                "passwordHash": hash_password("1008611"),
                "createdAt": 0,
                "activeAccountId": None,
            }
        )

        # 同步 seed 一个默认账户，便于账户管理页直接展示
        accounts = database["accounts"]
        if not accounts.find_one({"_id": "a1", "userId": "u_1008611"}):
            accounts.insert_one(
                {
                    "_id": "a1",
                    "userId": "u_1008611",
                    "name": "小朋友",
                    "account": "1008611",
                    "createdAt": 0,
                }
            )
    except Exception as e:
        # MongoDB 不可用时，不阻塞服务启动；前端仍可访问不依赖 DB 的接口。
        # 登录/注册/对话落库等依赖 DB 的能力会不可用（会在请求时再报错）。
        print(f"[startup] skip seeding debug user because MongoDB is unavailable: {e}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"] ,
)

def _resolve_upload_file(rel_path: str) -> Path:
    rel = (rel_path or "").strip().lstrip("/")
    if not rel:
        raise HTTPException(status_code=404, detail="file not found")

    fp = (_UPLOAD_ROOT / rel).resolve()
    if not str(fp).startswith(str(_UPLOAD_ROOT)):
        raise HTTPException(status_code=404, detail="file not found")
    if not fp.exists() or not fp.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    return fp


@app.api_route("/files/{file_path:path}", methods=["GET", "HEAD"])
def serve_file(file_path: str, request: Request):
    fp = _resolve_upload_file(file_path)
    file_size = fp.stat().st_size
    content_type = mimetypes.guess_type(str(fp))[0] or "application/octet-stream"
    range_header = request.headers.get("range")

    if not range_header:
        if request.method == "HEAD":
            return Response(
                status_code=200,
                headers={
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(file_size),
                },
                media_type=content_type,
            )

        return FileResponse(
            path=str(fp),
            media_type=content_type,
            headers={"Accept-Ranges": "bytes"},
        )

    if not range_header.startswith("bytes="):
        raise HTTPException(status_code=416, detail="invalid range")

    range_value = range_header.replace("bytes=", "", 1).strip()
    if "," in range_value:
        raise HTTPException(status_code=416, detail="multiple ranges not supported")

    start_s, end_s = (range_value.split("-", 1) + [""])[:2]
    if start_s == "" and end_s == "":
        raise HTTPException(status_code=416, detail="invalid range")

    if start_s == "":
        suffix_len = int(end_s)
        if suffix_len <= 0:
            raise HTTPException(status_code=416, detail="invalid range")
        start = max(0, file_size - suffix_len)
        end = file_size - 1
    else:
        start = int(start_s)
        end = int(end_s) if end_s else file_size - 1

    if start < 0 or end < start or start >= file_size:
        raise HTTPException(status_code=416, detail="range not satisfiable")

    end = min(end, file_size - 1)
    chunk_size = 1024 * 256

    def _iter_file():
        with fp.open("rb") as f:
            f.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                data = f.read(min(chunk_size, remaining))
                if not data:
                    break
                remaining -= len(data)
                yield data

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Content-Length": str(end - start + 1),
    }
    if request.method == "HEAD":
        return Response(status_code=206, headers=headers, media_type=content_type)
    return StreamingResponse(_iter_file(), status_code=206, media_type=content_type, headers=headers)

# public share download entry (no auth)
app.include_router(public_share_router)

# 按 openapi.yaml 约定：Base URL /api
api = FastAPI(openapi_url="/openapi.json", docs_url="/docs", redoc_url="/redoc")
api.include_router(auth_router)
api.include_router(accounts_router)
api.include_router(chat_router)
api.include_router(conversations_router)
api.include_router(doc_router)
api.include_router(profile_story_router)
api.include_router(profile_share_router)
api.include_router(upload_router)
api.include_router(asr_router)
api.include_router(voice_router)
api.include_router(avatar_router)

app.mount("/api", api)
