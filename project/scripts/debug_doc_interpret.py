from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests


def main() -> int:
    base = os.environ.get("BASE_URL", "http://127.0.0.1:8080")

    file_url = os.environ.get("FILE_URL")
    if not file_url:
        # fallback: interpret an existing local /tmp/uploads file by name (if any)
        print("ERROR: set FILE_URL like /files/xxx.pdf")
        return 2

    # login with seeded debug user
    login = requests.post(
        base + "/api/auth/login",
        json={"account": "1008611", "password": "1008611"},
        timeout=10,
    )
    token = (login.json().get("data") or {}).get("token") or (login.json().get("data") or {}).get("accessToken")
    if not token:
        print("ERROR: login failed:", login.status_code, login.text[:200])
        return 1

    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "fileUrl": file_url,
        "fileName": os.environ.get("FILE_NAME"),
        "fileSize": None,
        "fileMime": os.environ.get("FILE_MIME"),
        "question": os.environ.get("QUESTION", "请总结这份文档的核心内容")
    }

    t0 = time.perf_counter()
    r = requests.post(base + "/api/doc/interpret", json=payload, headers=headers, timeout=70)
    dt = time.perf_counter() - t0
    print("status", r.status_code, f"dt={dt:.3f}s")
    print(r.text[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
