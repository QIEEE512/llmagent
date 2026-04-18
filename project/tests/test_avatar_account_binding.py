from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

import app.db as db
from app.main import api


class _FakeCollection:
    def __init__(self):
        self.docs = []

    def find_one(self, filt):
        for d in self.docs:
            ok = True
            for k, v in filt.items():
                if d.get(k) != v:
                    ok = False
                    break
            if ok:
                return dict(d)
        return None

    def insert_one(self, doc):
        self.docs.append(dict(doc))
        return None

    def update_one(self, filt, update, upsert=False):
        found = None
        for d in self.docs:
            ok = True
            for k, v in filt.items():
                if d.get(k) != v:
                    ok = False
                    break
            if ok:
                found = d
                break

        if found is None:
            if not upsert:
                return None
            found = {}
            self.docs.append(found)
            if "$setOnInsert" in update:
                found.update(update["$setOnInsert"])

        if "$set" in update:
            found.update(update["$set"])
        return None


class _FakeDB(dict):
    def __getitem__(self, name):
        if name not in self:
            self[name] = _FakeCollection()
        return dict.__getitem__(self, name)


def _auth_header(user_id: str) -> dict:
    # Patch decode_token usage by providing a real JWT is unnecessary here;
    # instead we call endpoints at router level with dependency injection bypass via overridden get_current_user_id.
    return {"Authorization": "Bearer test"}


def test_avatar_generate_and_active_are_bound_to_account(monkeypatch):
    fake_db = _FakeDB()

    # arrange: create fake uploaded files in /tmp/uploads to satisfy backend resolver
    uploads = Path("/tmp/uploads")
    uploads.mkdir(parents=True, exist_ok=True)
    (uploads / "p1.jpg").write_bytes(b"fake")
    (uploads / "p2.jpg").write_bytes(b"fake")

    # Seed user + 2 accounts
    fake_db["users"].insert_one({"_id": "u1", "account": "1008611", "activeAccountId": "a1"})
    fake_db["accounts"].insert_one({"_id": "a1", "userId": "u1", "name": "kid1", "account": "child1"})
    fake_db["accounts"].insert_one({"_id": "a2", "userId": "u1", "name": "kid2", "account": "child2"})

    monkeypatch.setattr(db, "get_db", lambda: fake_db)

    # Override auth dependency
    import app.deps as deps

    api.dependency_overrides[deps.get_current_user_id] = lambda: "u1"

    # Avoid real model call
    import app.routers.avatar as avatar_router

    def fake_t2i_generate_to_file(*, prompt: str, size: str = "1280*1280", **kwargs):
        # Distinguish first/second call by a small marker in freeText
        if "p2" in prompt:
            fp = uploads / "gen2.png"
            fp.write_bytes(b"fake")
            return fp, "/files/gen2.png"
        fp = uploads / "gen1.png"
        fp.write_bytes(b"fake")
        return fp, "/files/gen1.png"

    monkeypatch.setattr(avatar_router, "wanx_t2i_generate_to_file", fake_t2i_generate_to_file)

    client = TestClient(api)

    payload = {
        "portraitUrl": "/files/p1.jpg",
        "profile": {"age": 8, "interests": ["恐龙"], "style": "活泼", "freeText": ""},
        "voice": {"presetId": "kid_bright_01", "note": ""},
        "output": {"characterStyle": "kids_cartoon"},
    }

    r1 = client.post("/avatar/generate", json=payload, headers=_auth_header("u1"))
    assert r1.status_code == 200
    data1 = r1.json()["data"]
    assert data1["imageUrl"] == "/files/gen1.png"

    # Overwrite for same account
    payload2 = dict(payload)
    payload2["portraitUrl"] = "/files/p2.jpg"
    payload2["profile"] = dict(payload2["profile"])
    payload2["profile"]["freeText"] = "p2"
    r2 = client.post("/avatar/generate", json=payload2, headers=_auth_header("u1"))
    assert r2.status_code == 200

    # active should be updated to p2.jpg
    r3 = client.get("/avatar/active", headers=_auth_header("u1"))
    assert r3.status_code == 200
    active = r3.json()["data"]
    assert active["imageUrl"] == "/files/gen2.png"

    # switch account -> should see no avatar
    fake_db["users"].update_one({"_id": "u1"}, {"$set": {"activeAccountId": "a2"}}, upsert=False)
    r4 = client.get("/avatar/active", headers=_auth_header("u1"))
    assert r4.status_code == 200
    assert r4.json()["data"] is None

    api.dependency_overrides = {}
