from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.deps import get_current_user
from app.schemas import ApiResponse

# 该 router 会被挂载到 /api 下（见 app/main.py），因此此处的 path 应当与前端一致：
# - POST /api/upload/image
# - POST /api/upload/file
# 为了兼容历史路径，也保留：
# - POST /api/upload/upload/image
# - POST /api/upload/upload/file
router = APIRouter(prefix="/upload", tags=["Upload"])

UPLOAD_DIR = Path("/tmp/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

VOICE_DIR = UPLOAD_DIR / "voice"
VOICE_DIR.mkdir(parents=True, exist_ok=True)

# 大小限制（字节）
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_FILE_BYTES = 50 * 1024 * 1024
MAX_VOICE_BYTES = 20 * 1024 * 1024  # 允许更长的录音（微信式按住说话通常 15~60s）

# 允许的 MIME（前端联调关键约束）
ALLOWED_IMAGE_MIMES = {"image/png", "image/jpeg", "image/webp"}
# 文件允许范围保持宽松，便于联调；后续可按业务收紧
ALLOWED_FILE_MIMES = {
    "application/pdf",
    "application/zip",
    "application/x-zip-compressed",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # docx
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # pptx
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # xlsx
    "text/plain",
    "text/markdown",
}

# 语音 MIME（前端建议 aac，后端尽量兼容）
ALLOWED_VOICE_MIMES = {
    "audio/aac",
    "audio/mp4",
    "audio/m4a",
    "audio/mpeg",
    "audio/x-m4a",
    "audio/wav",
    "audio/webm",
    "application/octet-stream",  # 部分端上可能不传/传错 content-type，先放宽，后续可用 magic bytes 收紧
}


def _ensure_max_size(file: UploadFile, limit_bytes: int) -> None:
    # UploadFile 可能没有 size，只能通过 seek/tell 获取
    try:
        pos = file.file.tell()
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(pos)
        if size > limit_bytes:
            raise HTTPException(status_code=413, detail=f"file too large (>{limit_bytes} bytes)")
    except HTTPException:
        raise
    except Exception:
        # 无法获取大小就放行（避免阻塞联调）；后续可改为强制限制
        return


def _check_mime(mime: str | None, allowed: set[str]) -> None:
    if mime and mime not in allowed:
        raise HTTPException(status_code=415, detail=f"unsupported content-type: {mime}")


def _save_file(file: UploadFile) -> tuple[str, str]:
    """Save uploaded file to /tmp/uploads and return (save_path, public_url).

    The backend exposes /tmp/uploads via app.mount('/files', StaticFiles(...)).
    """

    # Keep a safe filename (avoid path traversal)
    original = (file.filename or "upload.bin").split("/")[-1].split("\\")[-1]
    suffix = Path(original).suffix
    # Slightly unique name to avoid collision
    import time
    name = f"{int(time.time() * 1000)}_{original}"
    if not suffix:
        name = f"{int(time.time() * 1000)}_{original}"

    save_path = UPLOAD_DIR / name

    # Stream copy
    with save_path.open("wb") as f:
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)

    return str(save_path), f"/files/{name}"


def _save_voice(file: UploadFile) -> tuple[str, str]:
    """Save uploaded voice file under /tmp/uploads/voice and return (save_path, public_url)."""

    original = (file.filename or "voice.aac").split("/")[-1].split("\\")[-1]
    import time

    name = f"{int(time.time() * 1000)}_{original}"
    save_path = VOICE_DIR / name

    with save_path.open("wb") as f:
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)

    return str(save_path), f"/files/voice/{name}"


def _build_upload_data(public_url: str, saved_path: Path, original_name: Optional[str], content_type: Optional[str]):
    size = None
    try:
        size = saved_path.stat().st_size
    except Exception:
        size = None

    mime = content_type or mimetypes.guess_type(str(saved_path))[0] or "application/octet-stream"

    return {
        "url": public_url,
        "name": original_name or saved_path.name,
        "size": size,
        "mime": mime,
    }


# 新路径（对齐前端）：/api/upload/image
@router.post("/image", response_model=ApiResponse)
# 旧路径兼容：/api/upload/upload/image
@router.post("/upload/image", response_model=ApiResponse)
def upload_image(file: UploadFile = File(...), user=Depends(get_current_user)):
    _ensure_max_size(file, MAX_IMAGE_BYTES)
    _check_mime(file.content_type, ALLOWED_IMAGE_MIMES)
    save_path, url = _save_file(file)
    saved_path = Path(save_path)
    data = _build_upload_data(public_url=url, saved_path=saved_path, original_name=file.filename, content_type=file.content_type)
    return ApiResponse(data=data)


# 新路径（对齐前端）：/api/upload/file
@router.post("/file", response_model=ApiResponse)
# 旧路径兼容：/api/upload/upload/file
@router.post("/upload/file", response_model=ApiResponse)
def upload_file(file: UploadFile = File(...), user=Depends(get_current_user)):
    _ensure_max_size(file, MAX_FILE_BYTES)
    _check_mime(file.content_type, ALLOWED_FILE_MIMES)
    save_path, url = _save_file(file)
    saved_path = Path(save_path)
    data = _build_upload_data(public_url=url, saved_path=saved_path, original_name=file.filename, content_type=file.content_type)
    return ApiResponse(data=data)


@router.post("/voice", response_model=ApiResponse)
def upload_voice(file: UploadFile = File(...), user=Depends(get_current_user)):
    """Upload a voice recording file.

    Frontend contract: POST /api/upload/voice, form field name: file
    Returns: /files/voice/<name>
    """

    _ensure_max_size(file, MAX_VOICE_BYTES)
    _check_mime(file.content_type, ALLOWED_VOICE_MIMES)

    save_path, url = _save_voice(file)
    saved_path = Path(save_path)
    data = _build_upload_data(public_url=url, saved_path=saved_path, original_name=file.filename, content_type=file.content_type)
    return ApiResponse(data=data)
