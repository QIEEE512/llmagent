from __future__ import annotations

import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.logger import logger

from app.deps import get_current_user
from app.schemas import ApiResponse
from app.services.ai import _detect_audio_format_magic, voice_asr_text
from app.services.documents import resolve_local_path_from_files_url

router = APIRouter(prefix="/voice", tags=["Voice"])


def _validate_voice_url(url: str) -> str:
    if not isinstance(url, str) or not url.strip():
        raise HTTPException(status_code=400, detail="voiceUrl required")
    u = url.strip()
    if not u.startswith("/files/"):
        raise HTTPException(status_code=400, detail="voiceUrl must start with /files/")
    return u


@router.post("/chat", response_model=ApiResponse)
def voice_chat(payload: Dict[str, Any], user=Depends(get_current_user)):
    """Voice understanding (ASR) -> return text for frontend to send to /api/chat.

    Frontend contract:
    - POST /api/voice/chat
    - JSON: { voiceUrl, conversationId?, meta? }

    Model: qwen3-asr-flash
    """

    voice_url = _validate_voice_url(payload.get("voiceUrl"))
    conversation_id: Optional[str] = payload.get("conversationId")

    logger.info("voice_chat: voiceUrl=%s user=%s", voice_url, getattr(user, "get", lambda k, d=None: None)("account", None) if isinstance(user, dict) else None)

    # Reuse secure local file resolver
    fp = resolve_local_path_from_files_url(voice_url)

    # Basic mime allowlist (best-effort)
    ext = fp.suffix.lower()
    if ext not in (".aac", ".m4a", ".mp3", ".mp4", ".wav"):
        # Keep it permissive; frontend can produce mp4 container.
        raise HTTPException(status_code=415, detail="unsupported audio type")

    audio_bytes = fp.read_bytes()

    magic = _detect_audio_format_magic(audio_bytes, filename=fp.name)
    logger.info(
        "voice_chat: file=%s size=%d magic_format=%s confidence=%s",
        fp.name,
        len(audio_bytes),
        magic.format,
        magic.confidence,
    )

    # Edge case: press-and-release too quickly.
    # AAC/MP3 headers alone can be a few hundred bytes; use a conservative threshold.
    if len(audio_bytes) < 8000:
        raise HTTPException(status_code=400, detail="recording too short")

    t0 = time.perf_counter()
    text = voice_asr_text(audio_bytes, filename=fp.name)
    dt_ms = int((time.perf_counter() - t0) * 1000)

    # If ASR failed, return an error so frontend can show retry UI instead of sending it to /api/chat.
    if not text or text.strip().startswith("（语音识别失败") or text.strip().startswith("（语音识别超时"):
        raise HTTPException(
            status_code=502,
            detail={
                "message": "语音识别失败",
                "model": "qwen3-asr-flash",
                "latencyMs": dt_ms,
                "asr": (text or "")[:300],
            },
        )

    return ApiResponse(
        data={
            "conversationId": conversation_id,
            "text": text,
            # answer is optional; frontend prefers text
            "meta": {
                "model": "qwen3-asr-flash",
                "durationMs": None,
                "latencyMs": dt_ms,
            },
        }
    )
