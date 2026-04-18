from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Allow running this script from anywhere.
# It ensures the project root (the parent of "scripts") is on sys.path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.ai import vision_answer


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/debug_vision.py <image_path> [question]")
        return 2

    image_path = Path(sys.argv[1])
    question = sys.argv[2] if len(sys.argv) >= 3 else "请描述这张图片的内容。"

    if not image_path.exists() or not image_path.is_file():
        print(f"ERROR: file not found: {image_path}")
        return 2

    # quick key diagnostics
    keys = {
        "APP_OPENAI_API_KEY": bool(os.environ.get("APP_OPENAI_API_KEY")),
        "APP_DASHSCOPE_API_KEY": bool(os.environ.get("APP_DASHSCOPE_API_KEY")),
        "OPENAI_API_KEY": bool(os.environ.get("OPENAI_API_KEY")),
        # note: ai.py also checks APP_DASHSCOPE_API_KEY via env
    }
    print("[vision] key configured:", keys)

    data = image_path.read_bytes()

    # naive mime detection by extension
    ext = image_path.suffix.lower()
    mime = "image/png"
    if ext in (".jpg", ".jpeg"):
        mime = "image/jpeg"
    elif ext == ".webp":
        mime = "image/webp"

    print(f"[vision] image={image_path} bytes={len(data)} mime={mime}")
    print(f"[vision] question={question}")

    t0 = time.perf_counter()
    try:
        ans = vision_answer(question=question, image_bytes=data, mime=mime)
    except Exception as e:
        dt = time.perf_counter() - t0
        print(f"[vision] ERROR after {dt:.3f}s: {type(e).__name__}: {e}")
        return 1

    dt = time.perf_counter() - t0
    print(f"[vision] OK in {dt:.3f}s")
    print("[vision] answer:\n" + (ans or ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
