from __future__ import annotations

import base64
import os
import socket
import tempfile
from dataclasses import dataclass
from typing import List, Optional

import dashscope
from dotenv import load_dotenv
from openai import OpenAI

from app.config import settings

load_dotenv()  # 会把项目根的 .env 加入 os.environ


def _request_timeout_seconds(default: float) -> float:
    """Resolve per-request timeout.

    Priority:
    1) APP_MODEL_TIMEOUT_SECONDS env
    2) default

    Notes:
    - Keep this local to avoid expanding Settings surface area.
    """

    raw = os.environ.get("APP_MODEL_TIMEOUT_SECONDS")
    if not raw:
        return float(default)
    try:
        v = float(raw)
        # avoid 0/negative
        return v if v > 0 else float(default)
    except Exception:
        return float(default)


def _is_timeout_error(e: Exception) -> bool:
    # Best-effort detection across openai/httpx variants.
    name = type(e).__name__.lower()
    if "timeout" in name:
        return True
    if isinstance(e, TimeoutError):
        return True
    if isinstance(e, socket.timeout):
        return True
    # message heuristics
    msg = str(e).lower()
    return "timed out" in msg or "timeout" in msg


def _build_messages(user_text: str, history: Optional[List[dict]] = None) -> List[dict]:
    # 简单地把用户输入打包为 messages，并支持拼接多轮历史
    msgs: List[dict] = []
    # system prompt to instruct qwen model to respond in Chinese and be friendly
    msgs.append(
        {
            "role": "system",
            "content": "你是一个友好的中文 AI 教师，回答要简洁、适合儿童理解。不使用 Markdown 语法，不要出现 ** 或 __。不要用加粗/斜体/标题/引用/代码块",
        }
    )

    if history:
        # 只接受 role/content，避免把 DB 字段原样塞进模型
        for m in history:
            role = m.get("role")
            content = m.get("content")
            if role in ("system", "user", "assistant") and isinstance(content, str):
                c = content.strip()
                if c:
                    msgs.append({"role": role, "content": c})

    msgs.append({"role": "user", "content": user_text})
    return msgs


def simple_ai_reply(
    text: str,
    history: Optional[List[dict]] = None,
    *,
    timeout_s: Optional[float] = None,
    max_tokens: int = 2000,
) -> str:
    text = (text or "").strip()
    if not text:
        return "你想聊点什么？"

    key = (
        settings.openai_api_key
        or settings.dashscope_api_key
        or os.environ.get("OPENAI_API_KEY")
        or os.environ.get("APP_DASHSCOPE_API_KEY")
    )
    if not key:
        return "（模型未配置）我收到了你的消息，但当前服务未配置大模型 Key。"

    # 判断是否使用 DashScope
    if settings.dashscope_api_key and not settings.openai_api_key:
        client = OpenAI(api_key=key, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
    else:
        client = OpenAI(api_key=key)

    messages = _build_messages(text, history=history)

    try:
        resolved_timeout = float(timeout_s) if isinstance(timeout_s, (int, float)) and float(timeout_s) > 0 else _request_timeout_seconds(15)
        resolved_max_tokens = int(max_tokens) if isinstance(max_tokens, int) and max_tokens > 0 else 2000
        resp = client.chat.completions.create(
            model="qwen3-max",
            messages=messages,
            temperature=0.7,
            max_tokens=resolved_max_tokens,
            timeout=resolved_timeout,
        )

        content = resp.choices[0].message.content
        if content:
            return content.strip()

        return "（模型返回空内容）"

    except Exception as e:
        if _is_timeout_error(e):
            return "（模型超时）当前请求处理时间过长，请稍后重试。"
        # 不把底层异常直接暴露给前端
        return "（模型调用失败）请稍后重试。"


# === Vision (qwen3-vl-flash) ===


def _get_openai_client() -> OpenAI:
    key = (
        settings.openai_api_key
        or settings.dashscope_api_key
        or os.environ.get("OPENAI_API_KEY")
        or os.environ.get("APP_DASHSCOPE_API_KEY")
    )
    if not key:
        raise RuntimeError("missing model key")

    # DashScope compatible-mode
    if settings.dashscope_api_key and not settings.openai_api_key:
        return OpenAI(api_key=key, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")

    return OpenAI(api_key=key)


def _image_bytes_to_data_url(image_bytes: bytes, mime: str) -> str:
    b64 = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{mime};base64,{b64}"


def vision_answer(question: str, image_bytes: bytes, mime: str = "image/png") -> str:
    """Use qwen3-vl-flash to answer based on an image and a user question."""
    question = (question or "").strip() or "请描述这张图片。"

    try:
        client = _get_openai_client()
    except Exception:
        return "（模型未配置）当前服务未配置大模型 Key。"

    data_url = _image_bytes_to_data_url(image_bytes, mime)

    try:
        timeout_s = _request_timeout_seconds(15)
        # DashScope compatible multimodal format via chat.completions
        resp = client.chat.completions.create(
            model="qwen3-vl-flash",
            messages=[
                {
                    "role": "system",
                    "content": "你是一个中文 AI 助手，能理解图片内容并回答用户问题。回答要简洁、准确。",
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
            timeout=timeout_s,
        )

        content = resp.choices[0].message.content
        if content:
            return content.strip()
        return "（视觉模型返回空内容）"

    except Exception as e:
        if _is_timeout_error(e):
            return "（视觉模型超时）当前请求处理时间过长，请稍后重试。"
        return "（视觉模型调用失败）请稍后重试。"


# === ASR / Voice (qwen3-asr-flash) ===


@dataclass(frozen=True)
class _AudioMagicResult:
    format: str
    confidence: str  # "high" | "medium" | "low"


def _detect_audio_format_magic(audio_bytes: bytes, filename: str = "") -> _AudioMagicResult:
    """Best-effort audio container/codec detection by magic bytes.

    We only need a coarse `audio/<format>` hint for DashScope data URL.
    Prefer container detection (mp3/wav/aac/mp4/webm/ogg/flac) and avoid relying on extension.
    """

    b = audio_bytes or b""
    head = b[:64]

    # WAV: RIFF....WAVE
    if len(head) >= 12 and head[0:4] == b"RIFF" and head[8:12] == b"WAVE":
        return _AudioMagicResult(format="wav", confidence="high")

    # FLAC
    if head.startswith(b"fLaC"):
        return _AudioMagicResult(format="flac", confidence="high")

    # OGG
    if head.startswith(b"OggS"):
        # could be vorbis/opus, but container is ogg
        return _AudioMagicResult(format="ogg", confidence="high")

    # WebM / Matroska: 1A 45 DF A3
    if head.startswith(b"\x1aE\xdf\xa3"):
        return _AudioMagicResult(format="webm", confidence="high")

    # MP3: ID3 tag or frame sync 0xFFEx/0xFFFx
    if head.startswith(b"ID3"):
        return _AudioMagicResult(format="mp3", confidence="high")
    if len(head) >= 2 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0:
        return _AudioMagicResult(format="mp3", confidence="medium")

    # AAC ADTS: 0xFFF1/0xFFF9 sync word
    if len(head) >= 2 and head[0] == 0xFF and (head[1] & 0xF6) in (0xF0, 0xF2, 0xF4, 0xF6):
        return _AudioMagicResult(format="aac", confidence="medium")

    # MP4 / M4A: ....ftyp....
    if len(head) >= 12 and head[4:8] == b"ftyp":
        major = head[8:12]
        # Most common for audio-only: M4A, isom, mp42, 3gp4.
        if major in (b"M4A ", b"M4B ", b"isom", b"mp41", b"mp42", b"3gp4", b"3g2a"):
            return _AudioMagicResult(format="m4a", confidence="high")
        return _AudioMagicResult(format="mp4", confidence="medium")

    # MPEG-TS / others: no strong signature here.

    # Fallback to extension if we have it, but mark as low confidence.
    ext = os.path.splitext(filename or "")[1].lstrip(".").lower()
    if ext in ("mp3", "wav", "aac", "m4a", "mp4", "webm", "ogg", "flac"):
        return _AudioMagicResult(format=ext, confidence="low")

    return _AudioMagicResult(format="mp3", confidence="low")


def voice_asr_text(audio_bytes: bytes, filename: str = "voice.aac") -> str:
    """Transcribe voice to text using qwen3-asr-flash.

    Prefer DashScope native MultiModalConversation (方案A) because DashScope compatible-mode
    audio.transcriptions may be unsupported (404) in some gateways.

    Fallback to OpenAI-compatible audio.transcriptions when available.
    """

    if not audio_bytes:
        return ""

    timeout_s = _request_timeout_seconds(30)
    asr_model = os.environ.get("APP_QWEN_ASR_MODEL") or "qwen3-asr-flash"

    # --- Preferred: DashScope native (方案A) ---
    key = (
        settings.dashscope_api_key
        or os.environ.get("DASHSCOPE_API_KEY")
        or os.environ.get("APP_DASHSCOPE_API_KEY")
        or settings.openai_api_key
        or os.environ.get("OPENAI_API_KEY")
    )
    if key and hasattr(dashscope, "MultiModalConversation"):
        try:
            # Some dashscope modules use global api_key.
            dashscope.api_key = key

            magic = _detect_audio_format_magic(audio_bytes, filename=filename)
            audio_format = magic.format or "mp3"
            data_url = f"data:audio/{audio_format};base64,{base64.b64encode(audio_bytes).decode('ascii')}"
            messages = [
                {"role": "system", "content": [{"text": ""}]},
                {
                    "role": "user",
                    "content": [
                        {
                            "audio": data_url,
                        }
                    ],
                },
            ]

            resp = dashscope.MultiModalConversation.call(
                api_key=key,
                model=asr_model,
                messages=messages,
                result_format="message",
                asr_options={
                    "enable_lid": True,
                    "enable_itn": False,
                },
                timeout=timeout_s,
            )

            if isinstance(resp, dict):
                output = resp.get("output") or {}
                choices = output.get("choices") or []
                if choices:
                    msg = (choices[0] or {}).get("message") or {}
                    content = msg.get("content") or []
                    if content and isinstance(content[0], dict):
                        text = content[0].get("text")
                        if isinstance(text, str):
                            return text.strip()
        except Exception as e:
            # Native path failed; continue to fallback, but keep a short hint.
            native_err = e
    else:
        native_err = None

    # --- Fallback: OpenAI-compatible audio.transcriptions ---
    try:
        client = _get_openai_client()
    except Exception:
        return "（模型未配置）当前服务未配置大模型 Key。"

    try:
        try:
            # openai-python expects bytes / io.IOBase / PathLike / (filename, bytes)
            resp = client.audio.transcriptions.create(
                model=asr_model,
                file=(filename, audio_bytes),
                timeout=timeout_s,
            )
            text = getattr(resp, "text", None)
            if isinstance(text, str):
                return text.strip()
            if isinstance(resp, dict) and isinstance(resp.get("text"), str):
                return resp["text"].strip()
            return ""
        except AttributeError:
            return "（语音能力不可用）当前 SDK/网关未暴露 audio.transcriptions 接口。"

    except Exception as e:
        if _is_timeout_error(e):
            return "（语音识别超时）请稍后重试。"
        # Keep message readable but include a small hint for debugging.
        hint = type(e).__name__
        msg = str(e)
        if msg:
            msg = msg.replace("\n", " ")
            if len(msg) > 200:
                msg = msg[:200] + "..."
            hint = f"{hint}: {msg}"
        if 'native_err' in locals() and native_err is not None:
            n_hint = type(native_err).__name__
            n_msg = str(native_err)
            if n_msg:
                n_msg = n_msg.replace("\n", " ")
                if len(n_msg) > 200:
                    n_msg = n_msg[:200] + "..."
                n_hint = f"{n_hint}: {n_msg}"
            return f"（语音识别失败）请稍后重试。[native={n_hint}; fallback={hint}]"
        return f"（语音识别失败）请稍后重试。[{hint}]"

    # If both native and fallback didn't throw but also didn't return text.
    if 'native_err' in locals() and native_err is not None:
        return f"（语音识别失败）请稍后重试。[native={type(native_err).__name__}]"
    return "（语音识别失败）请稍后重试。"