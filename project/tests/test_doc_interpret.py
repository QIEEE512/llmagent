from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import api


def test_doc_interpret_txt(monkeypatch, tmp_path: Path):
    # arrange: create a fake uploaded txt file in /tmp/uploads
    uploads = Path("/tmp/uploads")
    uploads.mkdir(parents=True, exist_ok=True)

    name = "test_doc.txt"
    fp = uploads / name
    fp.write_text("Hello world. This is a test document about cats and dogs.", encoding="utf-8")

    # auth: bypass get_current_user (FastAPI dependency override)
    import app.deps as deps

    api.dependency_overrides[deps.get_current_user] = lambda: {"id": "u_1008611"}

    client = TestClient(api)

    # act
    resp = client.post(
    "/doc/interpret",
        json={"fileUrl": f"/files/{name}", "question": "这份文档主要讲什么？"},
        headers={"Authorization": "Bearer fake"},
    )

    # assert
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["code"] == 0
    assert "answer" in (body.get("data") or {})

    api.dependency_overrides = {}


def test_doc_interpret_invalid_url(monkeypatch):
    import app.deps as deps

    api.dependency_overrides[deps.get_current_user] = lambda: {"id": "u_1008611"}

    client = TestClient(api)
    resp = client.post(
    "/doc/interpret",
        json={"fileUrl": "http://evil.com/x.pdf"},
        headers={"Authorization": "Bearer fake"},
    )
    assert resp.status_code == 400

    api.dependency_overrides = {}


def test_doc_interpret_fallback_to_tfidf(monkeypatch):
    # Force embeddings retrieval to fail, ensure endpoint still works.
    uploads = Path("/tmp/uploads")
    uploads.mkdir(parents=True, exist_ok=True)

    name = "test_doc2.txt"
    (uploads / name).write_text("This document is about apples. Apples are fruits.", encoding="utf-8")

    import app.deps as deps

    api.dependency_overrides[deps.get_current_user] = lambda: {"id": "u_1008611"}

    # monkeypatch embeddings to raise (doc.py imported retrieve_embeddings at module import time)
    import app.routers.doc as doc_router

    def boom(*args, **kwargs):
        raise RuntimeError("embeddings down")

    monkeypatch.setattr(doc_router, "retrieve_embeddings", boom)

    client = TestClient(api)
    resp = client.post(
    "/doc/interpret",
        json={"fileUrl": f"/files/{name}", "question": "What is it about?"},
        headers={"Authorization": "Bearer fake"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["data"]["meta"]["rag"]["method"] == "tfidf"

    api.dependency_overrides = {}
