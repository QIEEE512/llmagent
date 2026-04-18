from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.main import app


class _FakeResult:
    def __init__(self, matched_count: int = 1):
        self.matched_count = matched_count


class _FakeCollection:
    def __init__(self, initial=None):
        self.rows = list(initial or [])

    def find_one(self, query):
        for r in self.rows:
            ok = True
            for k, v in query.items():
                if r.get(k) != v:
                    ok = False
                    break
            if ok:
                return dict(r)
        return None

    def insert_one(self, doc):
        self.rows.append(dict(doc))
        return None

    def update_one(self, query, update, upsert=False):
        return _FakeResult(1)

    def find(self, query, projection=None):
        # used by _load_history; return empty history
        return []


class _FakeDB(dict):
    pass


@pytest.fixture()
def client(monkeypatch):
    fake_db = _FakeDB(
        {
            "users": _FakeCollection([
                {"_id": "u1", "account": "100", "activeAccountId": "a1"},
            ]),
            "accounts": _FakeCollection([
                {"_id": "a1", "userId": "u1", "account": "100", "name": "kid", "createdAt": 0},
            ]),
            "conversations": _FakeCollection([]),
            "messages": _FakeCollection([]),
        }
    )

    from app import db as real_db

    monkeypatch.setattr(real_db, "get_db", lambda: fake_db)

    from app import deps as real_deps

    monkeypatch.setattr(real_deps, "decode_token", lambda _t: {"sub": "u1"})

    # avoid calling external models: chat router imports simple_ai_reply directly
    from app.routers import chat as chat_router

    monkeypatch.setattr(chat_router, "simple_ai_reply", lambda _prompt, history=None: "ok")

    return TestClient(app)


def test_chat_store_false_requires_conversation_id_and_does_not_write_messages(client: TestClient):
    headers = {"Authorization": "Bearer test-token"}

    # missing conversationId -> 400
    r = client.post("/api/chat", json={"text": "hi", "store": False}, headers=headers)
    assert r.status_code == 400

    # with conversationId -> 200
    r = client.post("/api/chat", json={"text": "hi", "store": False, "conversationId": "c1"}, headers=headers)
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["conversationId"] == "c1"
    assert data["answer"] == "ok"
    assert data["messageId"] is None
