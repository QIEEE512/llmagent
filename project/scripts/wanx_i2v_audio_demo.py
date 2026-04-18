#!/home/devbox/project/bin/python
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Optional

import dashscope
import requests
from dashscope import VideoSynthesis
from PIL import Image

# Allow running this file directly: python scripts/wanx_i2v_audio_demo.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.oss import presign_get_url, put_file_from_local
from app.config import settings

# DashScope base URL
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/api/v1"

dashscope.base_http_api_url = DASHSCOPE_BASE_URL

DEFAULT_IMG_FILE = "/home/devbox/project/屏幕截图 2025-09-22 160242.png"
DEFAULT_AUDIO_FILE = "/home/devbox/project/1月26日.MP3"
DEFAULT_PROMPT = "一个人面对镜头进行自然中文口播，发音清晰、语速适中、语气稳定，口型与语音同步，真实对话感。"
DEFAULT_COMPARE_PROMPT = "一个人面对镜头进行自然中文口播，内容是“大家好，我是ai助手”，发音清晰、语速适中、语气稳定，生成有声视频。"


def _get_api_key() -> str:
    key = (
        os.getenv("DASHSCOPE_API_KEY")
        or os.getenv("APP_DASHSCOPE_API_KEY")
        or settings.dashscope_api_key
    )
    if not key:
        raise RuntimeError("missing DASHSCOPE_API_KEY")
    return key


def _download(url: str, out_path: Path, timeout_s: float = 120.0) -> None:
    r = requests.get(url, timeout=timeout_s)
    r.raise_for_status()
    out_path.write_bytes(r.content)


def _resolve_media_url(*, media_url: Optional[str], media_file: Optional[str], object_prefix: str) -> Optional[str]:
    url = (media_url or "").strip()
    fp = (media_file or "").strip()

    if url and fp:
        raise ValueError("only one of url/file should be provided")

    if url:
        return url

    if not fp:
        return None

    local_fp = Path(fp).expanduser().resolve()
    if not local_fp.exists() or not local_fp.is_file():
        raise ValueError(f"file not found: {local_fp}")

    object_key = f"{object_prefix}{int(time.time() * 1000)}_{local_fp.name}"
    put_res = put_file_from_local(local_fp, object_key=object_key)
    return presign_get_url(object_key=put_res.object_key)


def _normalize_image_for_i2v(fp: Path) -> Path:
    """Ensure local image dimensions are within [240, 7680] for i2v."""

    min_side = 240
    max_side = 7680

    with Image.open(fp) as img:
        width, height = img.size

        need_up = min(width, height) < min_side
        need_down = max(width, height) > max_side
        if not need_up and not need_down:
            return fp

        scale_up = (min_side / min(width, height)) if need_up else 1.0
        scale_down = (max_side / max(width, height)) if need_down else 1.0
        scale = min(scale_up if need_up else 1.0, scale_down)
        if need_up and not need_down:
            scale = scale_up

        new_w = max(min_side, min(max_side, int(round(width * scale))))
        new_h = max(min_side, min(max_side, int(round(height * scale))))

        out_fp = Path("/tmp") / f"wanx_i2v_norm_{int(time.time() * 1000)}.png"
        img.resize((new_w, new_h), Image.Resampling.LANCZOS).save(out_fp, format="PNG")
        return out_fp


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="WanX I2V audio demo (supports URL or local file)")
    parser.add_argument("--img-url", default="", help="Public image URL for i2v input")
    parser.add_argument(
        "--img-file",
        default=DEFAULT_IMG_FILE if Path(DEFAULT_IMG_FILE).is_file() else "",
        help="Local image file path, auto-upload to OSS",
    )
    parser.add_argument("--audio-url", default="", help="Public audio URL (wav/mp3) for lip sync")
    parser.add_argument(
        "--audio-file",
        default=DEFAULT_AUDIO_FILE if Path(DEFAULT_AUDIO_FILE).is_file() else "",
        help="Local audio file path, auto-upload to OSS",
    )
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="Prompt text for the video")
    parser.add_argument(
        "--compare-no-audio-url",
        action="store_true",
        help="Also generate a contrast video with audio=True but without audio_url",
    )
    parser.add_argument(
        "--compare-prompt",
        default=DEFAULT_COMPARE_PROMPT,
        help="Optional prompt for the contrast video; default uses --prompt",
    )
    parser.add_argument("--duration", type=int, default=10, help="Video duration in seconds")
    parser.add_argument("--resolution", default="720P", help="Resolution, e.g. 720P")
    parser.add_argument("--shot-type", default="multi", help="Shot type, e.g. multi")
    parser.add_argument("--model", default="wan2.6-i2v", help="I2V model name")
    parser.add_argument("--poll-interval", type=float, default=2.0, help="Polling interval in seconds")
    parser.add_argument("--out", default="/tmp/wanx_i2v_audio.mp4", help="Output video path for main result")
    return parser.parse_args()


def _submit_and_wait(
    *,
    api_key: str,
    model: str,
    prompt: str,
    img_url: str,
    audio_url: Optional[str],
    resolution: str,
    duration: int,
    shot_type: str,
    poll_interval: float,
) -> str:
    rsp = VideoSynthesis.async_call(
        api_key=api_key,
        model=model,
        prompt=prompt,
        img_url=img_url,
        audio_url=audio_url,
        resolution=resolution,
        duration=int(duration),
        shot_type=shot_type,
        extend_prompt=True,
    )

    if rsp.status_code != 200:
        raise RuntimeError(
            f"async_call failed: status={rsp.status_code} code={getattr(rsp, 'code', None)} message={getattr(rsp, 'message', None)}"
        )

    out = getattr(rsp, "output", None)
    task_id = getattr(out, "task_id", None)
    if not task_id:
        raise RuntimeError("empty task_id")

    last_fetch = None
    while True:
        fetch = VideoSynthesis.fetch(str(task_id), api_key=api_key)
        last_fetch = fetch
        if fetch.status_code != 200:
            raise RuntimeError(
                f"fetch failed: status={fetch.status_code} code={getattr(fetch, 'code', None)} message={getattr(fetch, 'message', None)}"
            )
        f_out = getattr(fetch, "output", None)
        task_status = getattr(f_out, "task_status", None)
        if task_status in {"SUCCEEDED", "FAILED", "CANCELED"}:
            break
        time.sleep(float(poll_interval))

    if task_status != "SUCCEEDED":
        raise RuntimeError(
            "task not succeeded: "
            f"status={task_status} code={getattr(last_fetch, 'code', None)} "
            f"message={getattr(last_fetch, 'message', None)} output={f_out} request_id={getattr(last_fetch, 'request_id', None)}"
        )

    video_url = getattr(f_out, "video_url", None)
    if not video_url:
        raise RuntimeError("missing video_url in output")
    return str(video_url)


def main() -> int:
    args = _parse_args()
    api_key = _get_api_key()

    normalized_img_file = (args.img_file or "").strip()
    if normalized_img_file:
        normalized_img_fp = _normalize_image_for_i2v(Path(normalized_img_file).expanduser().resolve())
        normalized_img_file = str(normalized_img_fp)

    img_url = _resolve_media_url(media_url=args.img_url, media_file=normalized_img_file, object_prefix="debug/wanx/img/")
    if not img_url:
        raise ValueError("one of --img-url / --img-file is required")

    audio_url = _resolve_media_url(media_url=args.audio_url, media_file=args.audio_file, object_prefix="debug/wanx/audio/")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    main_video_url = _submit_and_wait(
        api_key=api_key,
        model=args.model,
        prompt=args.prompt,
        img_url=img_url,
        audio_url=audio_url,
        resolution=args.resolution,
        duration=int(args.duration),
        shot_type=args.shot_type,
        poll_interval=float(args.poll_interval),
    )
    _download(main_video_url, out_path)

    print(f"main_video={out_path}")

    if args.compare_no_audio_url:
        compare_prompt = (args.compare_prompt or "").strip() or args.prompt
        compare_video_url = _submit_and_wait(
            api_key=api_key,
            model=args.model,
            prompt=compare_prompt,
            img_url=img_url,
            audio_url=None,
            resolution=args.resolution,
            duration=int(args.duration),
            shot_type=args.shot_type,
            poll_interval=float(args.poll_interval),
        )
        compare_out = out_path.with_name(f"{out_path.stem}_compare_no_audio_url{out_path.suffix}")
        _download(compare_video_url, compare_out)
        print(f"compare_video={compare_out}")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
