from __future__ import annotations

import os
import subprocess
import time
from http import HTTPStatus
from pathlib import Path, PurePosixPath
from typing import Optional
from urllib.parse import unquote, urlparse

import dashscope
import requests
from dashscope import ImageSynthesis, VideoSynthesis

from app.config import settings

# Ensure base URL aligns with user provided sample.
dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"


def _get_api_key() -> str:
    key = settings.dashscope_api_key or os.getenv("DASHSCOPE_API_KEY") or os.getenv("APP_DASHSCOPE_API_KEY")
    if not key:
        raise RuntimeError("missing DASHSCOPE_API_KEY")
    return key


def _safe_filename_from_url(url: str) -> str:
    name = PurePosixPath(unquote(urlparse(url).path)).parts[-1]
    # prevent weird names
    name = name.replace("/", "_").replace("\\", "_")
    return name or f"wanx_{int(time.time()*1000)}.png"


def wanx_t2i_generate_to_file(
    *,
    prompt: str,
    size: str = "1024*1024",
    out_dir: Path = Path("/tmp/uploads"),
    filename_prefix: str = "avatar_",
    model: str = "wanx2.0-t2i-turbo",
    timeout_s: float = 60.0,
    retries: int = 1,
) -> tuple[Path, str]:
    """Generate an image with WanX T2I and save it to local disk.

    Returns: (local_path, public_url) where public_url is /files/<name>.

    Notes:
    - This is a synchronous call, matching the sample.
    - Network download uses requests with a timeout.
    """

    prompt = (prompt or "").strip()
    if not prompt:
        raise ValueError("prompt is required")

    # WanX T2I size must be one of a fixed set; normalize or fallback.
    allowed_sizes = {
        "768*768",
        "576*1024",
        "1024*576",
        "1024*1024",
        "720*1280",
        "1280*720",
        "864*1152",
        "1152*864",
    }
    size = (size or "").strip()
    if size not in allowed_sizes:
        size = "1024*1024"

    out_dir.mkdir(parents=True, exist_ok=True)

    last_rsp = None
    attempts = max(1, int(retries) + 1)
    for i in range(attempts):
        rsp = ImageSynthesis.call(
            api_key=_get_api_key(),
            model=model,
            prompt=prompt,
            n=1,
            size=size,
        )
        last_rsp = rsp

        if rsp.status_code != HTTPStatus.OK:
            # Keep message readable for frontend
            raise RuntimeError(
                f"wanx t2i failed: status={rsp.status_code} code={getattr(rsp, 'code', None)} message={getattr(rsp, 'message', None)}"
            )

        results = getattr(getattr(rsp, "output", None), "results", None) or []
        if results:
            break

        # empty results happens occasionally; backoff and retry
        if i < attempts - 1:
            time.sleep(0.4 * (i + 1))
    else:
        results = []

    if not results:
        out = getattr(last_rsp, "output", None)
        usage = getattr(last_rsp, "usage", None)
        raise RuntimeError(
            "wanx t2i returned empty results"
            f" (model={model} size={size} output={out} usage={usage} request_id={getattr(last_rsp, 'request_id', None)})"
        )

    url = results[0].url
    if not url:
        raise RuntimeError("wanx t2i result url is empty")

    remote_name = _safe_filename_from_url(url)
    stamp = int(time.time() * 1000)
    local_name = f"{filename_prefix}{stamp}_{remote_name}"
    fp = out_dir / local_name

    r = requests.get(url, timeout=timeout_s)
    r.raise_for_status()
    fp.write_bytes(r.content)

    return fp, f"/files/{fp.name}"


def wan_i2v_create_task(
    *,
    prompt: str,
    img_url: str,
    audio_url: Optional[str] = None,
    resolution: str = "720P",
    duration: int = 10,
    audio: bool = True,
    shot_type: str = "multi",
    extend_prompt: bool = True,
    model: str = "wan2.6-i2v",
) -> tuple[str, str]:
    """Create an async image-to-video task.

    Returns: (task_id, task_status)
    """

    prompt = (prompt or "").strip()
    if not prompt:
        raise ValueError("prompt is required")
    img_url = (img_url or "").strip()
    if not img_url:
        raise ValueError("img_url is required")

    rsp = VideoSynthesis.async_call(
        api_key=_get_api_key(),
        model=model,
        prompt=prompt,
        img_url=img_url,
        audio_url=audio_url,
        audio=True,
        resolution=resolution,
        extend_prompt=bool(extend_prompt),
        duration=int(duration),
        shot_type=shot_type,
    )

    if rsp.status_code != HTTPStatus.OK:
        raise RuntimeError(
            f"wan i2v async_call failed: status={rsp.status_code} code={getattr(rsp, 'code', None)} message={getattr(rsp, 'message', None)}"
        )

    out = getattr(rsp, "output", None)
    task_id = getattr(out, "task_id", None)
    task_status = getattr(out, "task_status", None) or "UNKNOWN"
    if not task_id:
        raise RuntimeError("wan i2v returned empty task_id")
    return str(task_id), str(task_status)


def wan_i2v_fetch(*, task_id: str, model: str = "wan2.6-i2v-flash"):
    """Fetch i2v task info using task_id."""
    task_id = (task_id or "").strip()
    if not task_id:
        raise ValueError("task_id is required")
    rsp = VideoSynthesis.fetch(task_id, api_key=_get_api_key())
    if rsp.status_code != HTTPStatus.OK:
        raise RuntimeError(
            f"wan i2v fetch failed: status={rsp.status_code} code={getattr(rsp, 'code', None)} message={getattr(rsp, 'message', None)}"
        )
    return rsp


def wan_i2v_wait(*, task_id: str, poll_interval_s: float = 2.0) :
    """Wait i2v task done and return response."""

    rsp = VideoSynthesis.wait(task_id, api_key=_get_api_key(), poll_interval=poll_interval_s)
    if rsp.status_code != HTTPStatus.OK:
        raise RuntimeError(
            f"wan i2v wait failed: status={rsp.status_code} code={getattr(rsp, 'code', None)} message={getattr(rsp, 'message', None)}"
        )
    return rsp


def wan_i2v_download_video_to_file(
    *,
    video_url: str,
    out_dir: Path = Path("/tmp/uploads"),
    filename_prefix: str = "avatar_video_",
    timeout_s: float = 120.0,
) -> tuple[Path, str]:
    """Download video_url to local file and return (local_path, /files url)."""

    video_url = (video_url or "").strip()
    if not video_url:
        raise ValueError("video_url is required")

    out_dir.mkdir(parents=True, exist_ok=True)
    remote_name = _safe_filename_from_url(video_url)
    stamp = int(time.time() * 1000)
    # ensure extension
    if not remote_name.lower().endswith((".mp4", ".mov", ".webm")):
        remote_name = remote_name + ".mp4"
    local_name = f"{filename_prefix}{stamp}_{remote_name}"
    fp = out_dir / local_name

    r = requests.get(video_url, timeout=timeout_s)
    r.raise_for_status()
    fp.write_bytes(r.content)
    _convert_video_for_mobile_compat(fp)
    return fp, f"/files/{fp.name}"


def _convert_video_for_mobile_compat(fp: Path) -> None:
    if not fp.exists() or not fp.is_file():
        return

    try:
        import imageio_ffmpeg

        ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return

    tmp_out = fp.with_name(f"{fp.stem}_mobile.mp4")

    cmd = [
        ffmpeg_bin,
        "-y",
        "-i",
        str(fp),
        "-map",
        "0:v:0",
        "-map",
        "0:a:0?",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-profile:v",
        "high",
        "-level",
        "4.1",
        "-movflags",
        "+faststart",
        "-c:a",
        "aac",
        "-ar",
        "44100",
        "-ac",
        "2",
        "-b:a",
        "128k",
        str(tmp_out),
    ]

    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if p.returncode != 0:
            if tmp_out.exists():
                tmp_out.unlink(missing_ok=True)
            return
        if not tmp_out.exists() or tmp_out.stat().st_size <= 0:
            tmp_out.unlink(missing_ok=True)
            return
        tmp_out.replace(fp)
    except Exception:
        if tmp_out.exists():
            tmp_out.unlink(missing_ok=True)
        return
