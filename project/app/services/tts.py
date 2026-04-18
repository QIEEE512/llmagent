from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path
from typing import Optional

import requests

from app.config import settings

TTS_DIR = Path("/tmp/uploads/voice")
TTS_DIR.mkdir(parents=True, exist_ok=True)


def _get_api_key() -> str:
    key = settings.dashscope_api_key or os.getenv("DASHSCOPE_API_KEY") or os.getenv("APP_DASHSCOPE_API_KEY")
    if not key:
        raise RuntimeError("missing DASHSCOPE_API_KEY")
    return key


def _load_voice_map() -> dict:
    raw = os.getenv("APP_TTS_VOICE_MAP_JSON")
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def resolve_tts_voice(preset_id: Optional[str]) -> Optional[str]:
    if not preset_id:
        return None
    voice_map = _load_voice_map()
    mapped = voice_map.get(str(preset_id))
    if isinstance(mapped, str) and mapped.strip():
        return mapped.strip()
    return None


def _save_audio_bytes(audio_bytes: bytes, *, suffix: str = ".mp3") -> tuple[Path, str]:
    stamp = int(time.time() * 1000)
    name = f"tts_{stamp}{suffix}"
    fp = TTS_DIR / name
    fp.write_bytes(audio_bytes)
    return fp, f"/files/voice/{fp.name}"


def _download_audio(url: str) -> bytes:
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.content


def generate_tts_audio(*, text: str, voice: Optional[str] = None, model: str = "qwen3-tts-flash") -> str:
    """Generate TTS audio and return a /files/voice/... url.

    Uses DashScope qwen3-tts-flash. If voice is None, use model default voice.
    """

    text = (text or "").strip()
    if not text:
        raise RuntimeError("tts text is empty")

    try:
        from dashscope.audio.qwen_tts import SpeechSynthesizer
    except Exception as e:
        raise RuntimeError(f"dashscope tts unavailable: {type(e).__name__}")

    kwargs = {"api_key": _get_api_key()}
    if voice:
        kwargs["voice"] = voice

    rsp = SpeechSynthesizer.call(model=model, text=text, **kwargs)
    status = getattr(rsp, "status_code", None)
    if status is not None and int(status) != 200:
        raise RuntimeError(f"tts failed: status={status} code={getattr(rsp, 'code', None)} message={getattr(rsp, 'message', None)}")

    output = getattr(rsp, "output", None)
    audio = getattr(output, "audio", None) if output else None
    if not audio:
        raise RuntimeError("tts output missing audio")

    url = getattr(audio, "url", None)
    data = getattr(audio, "data", None)
    if url:
        audio_bytes = _download_audio(str(url))
        # best-effort suffix from url
        suffix = Path(str(url)).suffix or ".mp3"
        _fp, public_url = _save_audio_bytes(audio_bytes, suffix=suffix)
        return public_url

    if data:
        audio_bytes = base64.b64decode(str(data))
        _fp, public_url = _save_audio_bytes(audio_bytes, suffix=".mp3")
        return public_url

    raise RuntimeError("tts audio has no url or data")
