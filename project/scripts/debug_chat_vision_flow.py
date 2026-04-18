from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# Allow running from anywhere by adding project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.ai import simple_ai_reply, vision_answer


def _print_keys() -> None:
    keys = {
        "APP_OPENAI_API_KEY": bool(os.environ.get("APP_OPENAI_API_KEY")),
        "APP_DASHSCOPE_API_KEY": bool(os.environ.get("APP_DASHSCOPE_API_KEY")),
        "OPENAI_API_KEY": bool(os.environ.get("OPENAI_API_KEY")),
    }
    print("[keys]", keys)


def _mime_from_ext(p: Path) -> str:
    ext = p.suffix.lower()
    if ext in (".jpg", ".jpeg"):
        return "image/jpeg"
    if ext == ".webp":
        return "image/webp"
    return "image/png"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Debug a flow that resembles /api/chat with image: read image -> vision -> chat(LLM)."
    )
    parser.add_argument("image_path", help="Local image path")
    parser.add_argument(
        "--text",
        default="描述图片",
        help="User text (same meaning as payload.text in /api/chat)",
    )
    parser.add_argument(
        "--question",
        default=None,
        help="Question passed to vision model (defaults to --text if set, else a generic prompt)",
    )
    parser.add_argument(
        "--skip-vision",
        action="store_true",
        help="Skip vision step (useful to isolate LLM latency)",
    )
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="Skip LLM step (useful to isolate vision latency)",
    )
    args = parser.parse_args()

    image_path = Path(args.image_path)
    if not image_path.exists() or not image_path.is_file():
        print(f"ERROR: file not found: {image_path}")
        return 2

    _print_keys()

    t0 = time.perf_counter()

    # 1) read image
    t_read0 = time.perf_counter()
    image_bytes = image_path.read_bytes()
    mime = _mime_from_ext(image_path)
    t_read = time.perf_counter() - t_read0
    print(f"[read] {image_path} bytes={len(image_bytes)} mime={mime} dt={t_read:.3f}s")

    # 2) vision
    vision_text = ""
    if not args.skip_vision:
        q = args.question or (args.text.strip() if args.text.strip() else "请描述这张图片。")
        t_v0 = time.perf_counter()
        try:
            vision_text = vision_answer(question=q, image_bytes=image_bytes, mime=mime)
        except Exception as e:
            dt = time.perf_counter() - t_v0
            print(f"[vision] ERROR dt={dt:.3f}s {type(e).__name__}: {e}")
            return 1
        t_v = time.perf_counter() - t_v0
        print(f"[vision] OK dt={t_v:.3f}s")
        print("[vision] answer:\n" + (vision_text or ""))
    else:
        print("[vision] skipped")

    # 3) chat llm (resembles /api/chat server-side prompt injection)
    if not args.skip_llm:
        injected = []
        injected.append("我这条消息带了图片附件：")
        injected.append(f"- image: {image_path.name}")
        if vision_text:
            injected.append("图片理解结果：")
            injected.append(vision_text)
        history = [{"role": "user", "content": "\n".join(injected)}]

        prompt_text = args.text.strip() or "请根据我上传的图片进行说明。"
        t_llm0 = time.perf_counter()
        try:
            answer = simple_ai_reply(prompt_text, history=history)
        except Exception as e:
            dt = time.perf_counter() - t_llm0
            print(f"[llm] ERROR dt={dt:.3f}s {type(e).__name__}: {e}")
            return 1
        t_llm = time.perf_counter() - t_llm0
        print(f"[llm] OK dt={t_llm:.3f}s")
        print("[llm] answer:\n" + (answer or ""))
    else:
        print("[llm] skipped")

    total = time.perf_counter() - t0
    print(f"[total] dt={total:.3f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
