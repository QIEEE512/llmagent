from __future__ import annotations

import sys
import time
from pathlib import Path

# allow running from anywhere
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.rag import embed_texts


def main() -> int:
    texts = [
        "今天天气很好，我们去公园玩。",
        "我喜欢学习数学和编程。",
    ]

    t0 = time.perf_counter()
    vecs = embed_texts(texts, model="text-embedding-v4")
    dt = time.perf_counter() - t0

    print(f"embedded {len(vecs)} texts in {dt:.3f}s")
    for i, v in enumerate(vecs):
        print(i, "dim=", len(v), "head=", v[:5])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
