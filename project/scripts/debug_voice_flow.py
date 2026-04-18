from __future__ import annotations

import os
import time

import requests
VOICE_PATH="/home/devbox/project/1月26日.MP3"

def main() -> int:
    base = os.environ.get("BASE_URL", "http://127.0.0.1:8080")

    voice_path = VOICE_PATH
    if not voice_path:
        print("ERROR: set VOICE_PATH to a local audio file (aac/mp3/m4a)")
        return 2

    # login
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

    # 1) upload voice
    t0 = time.perf_counter()
    with open(voice_path, "rb") as f:
        r = requests.post(
            base + "/api/upload/voice",
            files={"file": (os.path.basename(voice_path), f, "audio/aac")},
            headers=headers,
            timeout=30,
        )
    dt = time.perf_counter() - t0
    print("upload", r.status_code, f"dt={dt:.3f}s")
    print(r.text[:500])
    data = (r.json().get("data") or {}) if r.headers.get("content-type", "").startswith("application/json") else {}
    voice_url = data.get("url")
    if not voice_url:
        print("ERROR: no voiceUrl returned")
        return 1

    # 2) voice chat
    t1 = time.perf_counter()
    r2 = requests.post(
        base + "/api/voice/chat",
        json={"voiceUrl": voice_url, "meta": {"source": "voice"}},
        headers=headers,
        timeout=70,
    )
    dt2 = time.perf_counter() - t1
    print("voice/chat", r2.status_code, f"dt={dt2:.3f}s")
    print(r2.text[:1000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
