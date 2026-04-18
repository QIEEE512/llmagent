from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.main import app


class _FakeResult:
    def __init__(self, matched_count: int = 1):
        self.matched_count = matched_count


class _FakeCursor(list):
    def sort(self, key, direction):
        reverse = direction == -1
        super().sort(key=lambda x: x.get(key) or datetime.min, reverse=reverse)
        return self


class _FakeCollection:
    def __init__(self, initial=None):
        self.rows = list(initial or [])

    def find_one(self, query):
        for r in self.rows:
            ok = True
            for k, v in query.items():
                if isinstance(v, dict) and "$exists" in v:
                    exists = k in r and r[k] is not None
                    if bool(v["$exists"]) != exists:
                        ok = False
                        break
                    continue
                if r.get(k) != v:
                    ok = False
                    break
            if ok:
                return dict(r)
        return None

    def insert_one(self, doc):
        self.rows.append(dict(doc))
        return None

    def find(self, query, projection=None):
        out = []
        for r in self.rows:
            ok = True
            for k, v in query.items():
                if isinstance(v, dict) and "$exists" in v:
                    exists = k in r and r[k] is not None
                    if bool(v["$exists"]) != exists:
                        ok = False
                        break
                    continue
                if r.get(k) != v:
                    ok = False
                    break
            if ok:
                out.append(dict(r))
        return _FakeCursor(out)

    def update_one(self, query, update, upsert=False):
        target_idx = None
        for i, r in enumerate(self.rows):
            ok = True
            for k, v in query.items():
                if isinstance(v, dict) and "$exists" in v:
                    exists = k in r and r[k] is not None
                    if bool(v["$exists"]) != exists:
                        ok = False
                        break
                    continue
                if r.get(k) != v:
                    ok = False
                    break
            if ok:
                target_idx = i
                break

        if target_idx is None:
            if not upsert:
                return _FakeResult(matched_count=0)
            base = dict(query)
            if "$setOnInsert" in update:
                base.update(update["$setOnInsert"])
            if "$set" in update:
                base.update(update["$set"])
            self.rows.append(base)
            return _FakeResult(matched_count=1)

        if "$set" in update:
            self.rows[target_idx].update(update["$set"])
        return _FakeResult(matched_count=1)


class _FakeDB(dict):
    pass


@pytest.fixture()
def client(monkeypatch):
    fake_db = _FakeDB(
        {
            "users": _FakeCollection(
                [
                    {"_id": "u1", "account": "100", "activeAccountId": "a1"},
                ]
            ),
            "accounts": _FakeCollection([
                {"_id": "a1", "userId": "u1", "account": "100", "name": "kid"},
            ]),
            "conversations": _FakeCollection([]),
            "messages": _FakeCollection([]),
        }
    )

    from app import db as real_db

    monkeypatch.setattr(real_db, "get_db", lambda: fake_db)

    # bypass JWT decoding: deps.get_current_user_id uses app.deps.decode_token
    from app import deps as real_deps
    from app import security as real_security

    # Patch both to avoid cross-test monkeypatch ordering issues.
    monkeypatch.setattr(real_security, "decode_token", lambda _t: {"sub": "u1"}, raising=True)
    monkeypatch.setattr(real_deps, "decode_token", lambda _t: {"sub": "u1"}, raising=True)

    return TestClient(app)


def test_conversation_crud_and_messages_idempotent(client: TestClient):
    headers = {"Authorization": "Bearer test-token"}

    # create
    r = client.post("/api/conversations", json={"title": "t1"}, headers=headers)
    assert r.status_code == 200
    cid = r.json()["data"]["conversationId"]

    # append user message
    r = client.post(
        f"/api/conversations/{cid}/messages",
        json={"role": "user", "text": "hello", "attachments": [], "clientMsgId": "c1"},
    headers=headers,
    )
    assert r.status_code == 200
    mid1 = r.json()["data"]["messageId"]

    # idempotent retry
    r = client.post(
        f"/api/conversations/{cid}/messages",
        json={"role": "user", "text": "hello", "attachments": [], "clientMsgId": "c1"},
    headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["data"]["messageId"] == mid1

    # list conversations should include lastMessage
    r = client.get("/api/conversations")
    # endpoint requires auth, but list doesn't accept headers in this test client call by default
    r = client.get("/api/conversations", headers=headers)
    assert r.status_code == 200
    items = r.json()["data"]
    assert len(items) == 1
    assert items[0]["conversationId"] == cid
    assert items[0]["lastMessage"] == "hello"

    # get conversation with messages
    r = client.get(f"/api/conversations/{cid}", headers=headers)
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["conversationId"] == cid
    assert data["title"] == "t1"
    assert len(data["messages"]) == 1
    assert data["messages"][0]["messageId"] == mid1
    assert data["messages"][0]["text"] == "hello"

    # soft delete
    r = client.post(f"/api/conversations/{cid}/delete", headers=headers)
    assert r.status_code == 200

    # list should be empty
    r = client.get("/api/conversations", headers=headers)
    assert r.status_code == 200
    assert r.json()["data"] == []

    # get should 404
    r = client.get(f"/api/conversations/{cid}", headers=headers)
    assert r.status_code == 404
