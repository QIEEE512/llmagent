from __future__ import annotations

import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.main import app


class _FakeCollection:
    def __init__(self, initial=None):
        self.rows = list(initial or [])

    def find_one(self, query):
        for r in self.rows:
            ok = True
            for k, v in query.items():
                if isinstance(v, dict) and "$exists" in v:
                    # Mongo $exists only checks whether the field is present, not whether it's null.
                    exists = k in r
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

    def find(self, query):
        def _match(row):
            for k, v in query.items():
                if isinstance(v, dict) and "$exists" in v:
                    exists = k in row
                    if bool(v["$exists"]) != exists:
                        return False
                    continue
                if isinstance(v, dict) and "$in" in v:
                    if row.get(k) not in v["$in"]:
                        return False
                    continue
                if isinstance(v, dict) and ("$gte" in v or "$lt" in v):
                    val = row.get(k)
                    if "$gte" in v and not (val >= v["$gte"]):
                        return False
                    if "$lt" in v and not (val < v["$lt"]):
                        return False
                    continue
                if row.get(k) != v:
                    return False
            return True

        return _FakeCursor([dict(r) for r in self.rows if _match(r)])

    def update_one(self, query, update, upsert=False):
        return None


class _FakeCursor(list):
    def sort(self, key, direction):
        reverse = direction == -1
        super().sort(key=lambda x: x.get(key) or datetime.min, reverse=reverse)
        return self


class _FakeDB(dict):
    pass


@pytest.fixture()
def client(monkeypatch):
    now = datetime(2026, 2, 6, 10, 0, 0)
    fake_db = _FakeDB(
        {
            "users": _FakeCollection([
                {"_id": "u1", "account": "100", "activeAccountId": "a1"},
            ]),
            "accounts": _FakeCollection([
                {"_id": "a1", "userId": "u1", "account": "100", "name": "kid", "createdAt": 0},
            ]),
            "conversations": _FakeCollection([
                {"_id": "c1", "userId": "u1", "accountId": "a1", "createdAt": now, "updatedAt": now},
            ]),
            "messages": _FakeCollection(
                [
                    {"_id": "m1", "conversationId": "c1", "userId": "u1", "accountId": "a1", "role": "user", "content": "我今天学会了加法", "createdAt": now},
                    {"_id": "m2", "conversationId": "c1", "userId": "u1", "accountId": "a1", "role": "assistant", "content": "太棒了！", "createdAt": now},
                ]
            ),
            "profile_stories": _FakeCollection([]),
        }
    )

    from app import db as real_db

    monkeypatch.setattr(real_db, "get_db", lambda: fake_db)

    from app import deps as real_deps

    monkeypatch.setattr(real_deps, "decode_token", lambda _t: {"sub": "u1"})

    # mock model: two-stage generation
    from app.routers import profile_story as ps

    def _mock_reply(prompt: str, history=None):
        if "提炼一个简短的 timeline JSON" in prompt:
            return json.dumps(
                {
                    "timeline": [
                        {"at": "2026-02-06T10:00:00Z", "summary": "孩子学习了加法", "type": "math"}
                    ]
                },
                ensure_ascii=False,
            )

        return json.dumps(
            {
                "storyVersion": 1,
                "title": "t",
                "chapters": [
                    {
                        "chapterTitle": "c",
                        "paragraphs": ["p1"],
                        "timeline": [
                            {"at": "2026-02-06T10:00:00Z", "summary": "s"}
                        ],
                    }
                ],
                "milestones": [
                    {"title": "m", "at": "2026-02-06T10:00:00Z", "summary": "ms", "type": "math"}
                ],
                "meta": {},
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr(ps, "simple_ai_reply", _mock_reply)

    return TestClient(app)


def test_profile_story_generate_and_save(client: TestClient):
    headers = {"Authorization": "Bearer test-token"}

    r = client.post(
        "/api/profile/story/generate",
        json={"sourceType": "conversations", "conversationIds": ["c1"], "includeAssistant": True},
        headers=headers,
    )
    assert r.status_code == 200
    story = r.json()["data"]
    assert story["storyVersion"] == 1
    assert story["chapters"][0]["chapterTitle"] == "c"
    assert story["meta"]["sourceType"] == "conversations"

    r = client.post(
        "/api/profile/story/save",
        json={"story": story, "source": {"sourceType": "conversations", "conversationIds": ["c1"], "includeAssistant": True}},
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert str(data["storyId"]).startswith("s_")
    assert data["savedAt"]


def test_profile_story_generate_date_range_uses_local_timezone(monkeypatch):
    # Default local tz is UTC+8.
    # Material message at 2026-02-05 16:30Z equals 2026-02-06 00:30 in UTC+8,
    # so it should be included when dateFrom=dateTo=2026-02-06.
    from app.main import app

    from fastapi.testclient import TestClient

    msg_utc = datetime(2026, 2, 5, 16, 30, 0)  # naive UTC in our DB style
    fake_db = _FakeDB(
        {
            "users": _FakeCollection([
                {"_id": "u1", "account": "100", "activeAccountId": "a1"},
            ]),
            "accounts": _FakeCollection([
                {"_id": "a1", "userId": "u1", "account": "100", "name": "kid", "createdAt": 0},
            ]),
            "conversations": _FakeCollection([]),
            "messages": _FakeCollection(
                [
                    {"_id": "m1", "conversationId": "c1", "userId": "u1", "accountId": "a1", "role": "user", "content": "素材", "createdAt": msg_utc},
                ]
            ),
            "profile_stories": _FakeCollection([]),
        }
    )

    from app import db as real_db

    monkeypatch.setattr(real_db, "get_db", lambda: fake_db)

    from app import deps as real_deps

    monkeypatch.setattr(real_deps, "decode_token", lambda _t: {"sub": "u1"})

    # mock model: two-stage generation
    from app.routers import profile_story as ps

    def _mock_reply(prompt: str, history=None):
        if "提炼一个简短的 timeline JSON" in prompt:
            return json.dumps(
                {"timeline": [{"at": "2026-02-06T00:30:00+08:00", "summary": "素材", "type": "other"}]},
                ensure_ascii=False,
            )
        return json.dumps(
            {"storyVersion": 1, "title": "t", "chapters": [], "milestones": [], "meta": {}},
            ensure_ascii=False,
        )

    monkeypatch.setattr(ps, "simple_ai_reply", _mock_reply)

    client = TestClient(app)
    headers = {"Authorization": "Bearer test-token"}

    r = client.post(
        "/api/profile/story/generate",
        json={"sourceType": "dateRange", "dateFrom": "2026-02-06", "dateTo": "2026-02-06", "includeAssistant": False},
        headers=headers,
    )
    assert r.status_code == 200


def test_profile_story_generate_parses_json_fence(monkeypatch):
    from app.main import app

    from fastapi.testclient import TestClient

    now = datetime(2026, 2, 6, 10, 0, 0)
    fake_db = _FakeDB(
        {
            "users": _FakeCollection([
                {"_id": "u1", "account": "100", "activeAccountId": "a1"},
            ]),
            "accounts": _FakeCollection([
                {"_id": "a1", "userId": "u1", "account": "100", "name": "kid", "createdAt": 0},
            ]),
            "conversations": _FakeCollection([
                {"_id": "c1", "userId": "u1", "accountId": "a1", "createdAt": now, "updatedAt": now},
            ]),
            "messages": _FakeCollection(
                [
                    {"_id": "m1", "conversationId": "c1", "userId": "u1", "accountId": "a1", "role": "user", "content": "素材", "createdAt": now},
                ]
            ),
            "profile_stories": _FakeCollection([]),
        }
    )

    from app import db as real_db

    monkeypatch.setattr(real_db, "get_db", lambda: fake_db)

    from app import deps as real_deps

    monkeypatch.setattr(real_deps, "decode_token", lambda _t: {"sub": "u1"})

    from app.routers import profile_story as ps

    def _mock_reply(prompt: str, history=None):
        if "提炼一个简短的 timeline JSON" in prompt:
            inner = json.dumps(
                {"timeline": [{"at": "2026-02-06T10:00:00Z", "summary": "素材", "type": "other"}]},
                ensure_ascii=False,
            )
            return "```json\n" + inner + "\n```"
        return json.dumps({"storyVersion": 1, "title": "t", "chapters": [], "milestones": [], "meta": {}}, ensure_ascii=False)

    monkeypatch.setattr(ps, "simple_ai_reply", _mock_reply)

    client = TestClient(app)
    headers = {"Authorization": "Bearer test-token"}

    r = client.post(
        "/api/profile/story/generate",
        json={"sourceType": "conversations", "conversationIds": ["c1"], "includeAssistant": False},
        headers=headers,
    )
    assert r.status_code == 200


def test_profile_story_saved_list_detail_delete(monkeypatch):
    from app.main import app

    from fastapi.testclient import TestClient

    now = datetime(2026, 2, 6, 10, 0, 0)
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
            "profile_stories": _FakeCollection(
                [
                    {
                        "_id": "s1",
                        "userId": "u1",
                        "accountId": "a1",
                        "story": {"storyVersion": 1, "title": "t1", "chapters": [], "milestones": [], "meta": {}},
                        "source": {"sourceType": "dateRange", "dateFrom": "2026-02-01", "dateTo": "2026-02-06", "includeAssistant": True},
                        "createdAt": now,
                        "savedAt": now,
                        "updatedAt": now,
                    }
                ]
            ),
        }
    )

    from app import db as real_db

    monkeypatch.setattr(real_db, "get_db", lambda: fake_db)

    from app import deps as real_deps

    monkeypatch.setattr(real_deps, "decode_token", lambda _t: {"sub": "u1"})

    client = TestClient(app)
    headers = {"Authorization": "Bearer test-token"}

    # list
    r = client.get("/api/profile/stories", headers=headers)
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["items"][0]["storyId"] == "s1"
    assert data["items"][0]["title"] == "t1"

    # detail
    r = client.get("/api/profile/stories/s1", headers=headers)
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["storyId"] == "s1"
    assert d["story"]["title"] == "t1"

    # delete
    r = client.post("/api/profile/stories/s1/delete", headers=headers)
    assert r.status_code == 200
