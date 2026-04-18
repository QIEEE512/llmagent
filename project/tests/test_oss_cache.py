from __future__ import annotations

from pathlib import Path

import pytest


def test_oss_put_is_cached_by_content(monkeypatch, tmp_path: Path):
    from app.services import oss
    from app.config import settings

    # ensure cache clean
    oss.cache_clear()

    # configure minimal creds
    settings.oss_access_key_id = "ak"
    settings.oss_access_key_secret = "sk"
    settings.oss_bucket = "agent-teacher-ai1"
    settings.oss_endpoint = "https://oss-cn-hangzhou.aliyuncs.com"

    fp = tmp_path / "img.png"
    fp.write_bytes(b"same-content")

    calls = {"put": 0}

    class _Resp:
        status_code = 200
        text = "OK"

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def put(self, url, content=None, headers=None):
            calls["put"] += 1
            return _Resp()

    monkeypatch.setattr(oss.httpx, "Client", _Client)

    r1 = oss.put_file_from_local(fp, object_key="i2v_inputs/img.png")
    r2 = oss.put_file_from_local(fp, object_key="i2v_inputs/img.png")

    assert r1.object_key == r2.object_key
    assert calls["put"] == 1
