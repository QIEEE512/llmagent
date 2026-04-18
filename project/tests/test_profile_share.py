from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient


class _FakeCollection:
    def __init__(self, initial=None):
        self.rows = list(initial or [])

    def find_one(self, query):
        for r in self.rows:
            ok = True
            for k, v in query.items():
                if isinstance(v, dict) and "$exists" in v:
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

    def update_one(self, query, update, upsert=False):
        # very small subset: $set and $inc
        target = None
        for i, r in enumerate(self.rows):
            ok = True
            for k, v in query.items():
                if r.get(k) != v:
                    ok = False
                    break
            if ok:
                target = i
                break
        if target is None:
            return type("R", (), {"matched_count": 0})

        if "$set" in update and isinstance(update["$set"], dict):
            self.rows[target].update(update["$set"])
        if "$inc" in update and isinstance(update["$inc"], dict):
            for k, v in update["$inc"].items():
                try:
                    self.rows[target][k] = int(self.rows[target].get(k) or 0) + int(v)
                except Exception:
                    self.rows[target][k] = (self.rows[target].get(k) or 0) + v
        return type("R", (), {"matched_count": 1})

    def find(self, query, projection=None):
        def _match(row):
            for k, v in query.items():
                if isinstance(v, dict) and "$exists" in v:
                    exists = k in row
                    if bool(v["$exists"]) != exists:
                        return False
                    continue
                if row.get(k) != v:
                    return False
            return True

        return _FakeCursor([dict(r) for r in self.rows if _match(r)])


class _FakeCursor(list):
    def sort(self, key, direction):
        reverse = direction == -1
        super().sort(key=lambda x: x.get(key) or datetime.min, reverse=reverse)
        return self


class _FakeDB(dict):
    pass


def test_profile_export_and_share(monkeypatch):
    from app.main import app

    now = datetime(2026, 2, 7, 10, 0, 0)
    fake_db = _FakeDB(
        {
            "users": _FakeCollection([
                {"_id": "u1", "account": "100", "activeAccountId": "a1"},
            ]),
            "accounts": _FakeCollection([
                {"_id": "a1", "userId": "u1", "account": "100", "name": "kid", "createdAt": 0},
            ]),
            "profile_stories": _FakeCollection(
                [
                    {
                        "_id": "s1",
                        "userId": "u1",
                        "accountId": "a1",
                        "story": {"storyVersion": 1, "title": "t1", "chapters": [{"chapterTitle": "c", "paragraphs": ["p"]}], "milestones": [], "meta": {}},
                        "source": {"sourceType": "dateRange"},
                        "createdAt": now,
                        "savedAt": now,
                        "updatedAt": now,
                    }
                ]
            ),
            "profile_story_exports": _FakeCollection([]),
            "profile_story_shares": _FakeCollection([]),
        }
    )

    from app import db as real_db

    monkeypatch.setattr(real_db, "get_db", lambda: fake_db)

    from app import deps as real_deps

    monkeypatch.setattr(real_deps, "decode_token", lambda _t: {"sub": "u1"})

    # mock export -> OSS upload
    from app import services
    from app.services import profile_exports as pe

    class _PutRes:
        def __init__(self, object_key: str):
            self.object_key = object_key
            self.bucket = "b"

    def _mock_put(fp, object_key=None):
        return _PutRes(object_key)

    monkeypatch.setattr(pe, "put_file_from_local", _mock_put)

    from app.routers import profile_share as ps

    monkeypatch.setattr(ps, "presign_get_url", lambda object_key, **kwargs: "https://oss.example.com/" + object_key)

    client = TestClient(app)
    headers = {"Authorization": "Bearer t"}

    r = client.post("/api/profile/stories/s1/export-word", json={"template": "default"}, headers=headers)
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["storyId"] == "s1"
    assert data["exportId"].startswith("e_")
    assert data["fileUrl"].startswith("https://oss.example.com/exports/")
    assert data["pdfUrl"].startswith("https://oss.example.com/exports/")

    # share with explicit exportId
    export_id = data["exportId"]
    r2 = client.post("/api/profile/stories/s1/share", json={"exportId": export_id, "expiresInDays": 7}, headers=headers)
    assert r2.status_code == 200
    d2 = r2.json()["data"]
    assert d2["shareId"].startswith("Sh_")
    assert d2["shareUrl"].startswith("/s/Sh_")
    assert d2["shareUrl"].endswith("/view")
    assert d2["shareDownloadUrl"].startswith("/s/Sh_")
    assert "shareFullUrl" in d2


def test_share_auto_export_when_no_latest_export(monkeypatch):
    from app.main import app

    now = datetime(2026, 2, 7, 10, 0, 0)
    fake_db = _FakeDB(
        {
            "users": _FakeCollection([
                {"_id": "u1", "account": "100", "activeAccountId": "a1"},
            ]),
            "accounts": _FakeCollection([
                {"_id": "a1", "userId": "u1", "account": "100", "name": "kid", "createdAt": 0},
            ]),
            "profile_stories": _FakeCollection(
                [
                    {
                        "_id": "s1",
                        "userId": "u1",
                        "accountId": "a1",
                        "story": {"storyVersion": 1, "title": "t1", "chapters": [], "milestones": [], "meta": {}},
                        "source": {"sourceType": "dateRange"},
                        "createdAt": now,
                        "savedAt": now,
                        "updatedAt": now,
                    }
                ]
            ),
            "profile_story_exports": _FakeCollection([]),
            "profile_story_shares": _FakeCollection([]),
        }
    )

    from app import db as real_db

    monkeypatch.setattr(real_db, "get_db", lambda: fake_db)

    from app import deps as real_deps

    monkeypatch.setattr(real_deps, "decode_token", lambda _t: {"sub": "u1"})

    from app.services import profile_exports as pe

    class _PutRes:
        def __init__(self, object_key: str):
            self.object_key = object_key
            self.bucket = "b"

    def _mock_put(fp, object_key=None):
        return _PutRes(object_key)

    monkeypatch.setattr(pe, "put_file_from_local", _mock_put)

    from app.routers import profile_share as ps

    client = TestClient(app)
    headers = {"Authorization": "Bearer t"}

    r = client.post("/api/profile/stories/s1/share", json={}, headers=headers)
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["shareId"].startswith("Sh_")
    assert d["shareUrl"].startswith("/s/Sh_")
    assert d["shareUrl"].endswith("/view")
    assert d["shareDownloadUrl"].startswith("/s/Sh_")
    assert "shareFullUrl" in d

    # export should be created implicitly
    exports = fake_db["profile_story_exports"].rows
    assert len(exports) == 1
    assert exports[0]["storyId"] == "s1"


def test_share_revoke_and_public_download(monkeypatch):
    from app.main import app

    now = datetime(2026, 2, 7, 10, 0, 0)
    fake_db = _FakeDB(
        {
            "users": _FakeCollection([
                {"_id": "u1", "account": "100", "activeAccountId": "a1"},
            ]),
            "accounts": _FakeCollection([
                {"_id": "a1", "userId": "u1", "account": "100", "name": "kid", "createdAt": 0},
            ]),
            "profile_stories": _FakeCollection(
                [
                    {
                        "_id": "s1",
                        "userId": "u1",
                        "accountId": "a1",
                        "story": {"storyVersion": 1, "title": "t1", "chapters": [], "milestones": [], "meta": {}},
                        "source": {"sourceType": "dateRange"},
                        "createdAt": now,
                        "savedAt": now,
                        "updatedAt": now,
                    }
                ]
            ),
            "profile_story_exports": _FakeCollection(
                [
                    {
                        "_id": "e1",
                        "storyId": "s1",
                        "userId": "u1",
                        "accountId": "a1",
                        "fileName": "x.docx",
                        "objectKey": "exports/u1/a1/e1.docx",
                        "pdfFileName": "x.pdf",
                        "pdfObjectKey": "exports/u1/a1/e1.pdf",
                        "createdAt": now,
                    }
                ]
            ),
            "profile_story_shares": _FakeCollection(
                [
                    {
                        "_id": "Sh_test",
                        "shareId": "Sh_test",
                        "storyId": "s1",
                        "exportId": "e1",
                        "userId": "u1",
                        "accountId": "a1",
                        "status": "active",
                        "createdAt": now,
                        "expiresAt": now.replace(year=2026, month=2, day=14),
                    }
                ]
            ),
        }
    )

    from app import db as real_db

    monkeypatch.setattr(real_db, "get_db", lambda: fake_db)

    from app import deps as real_deps

    monkeypatch.setattr(real_deps, "decode_token", lambda _t: {"sub": "u1"})

    # presign mock
    from app.routers import public_share as pub

    monkeypatch.setattr(pub, "presign_get_url", lambda object_key, **kwargs: "https://oss.example.com/" + object_key)

    client = TestClient(app)

    # public preview ok -> 302 (default: pdf)
    r = client.get("/s/Sh_test", allow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"].endswith(".pdf")

    r_pdf = client.get("/s/Sh_test?format=pdf", allow_redirects=False)
    assert r_pdf.status_code == 302
    assert r_pdf.headers["location"].endswith(".pdf")

    r_docx = client.get("/s/Sh_test?format=docx", allow_redirects=False)
    assert r_docx.status_code == 302
    assert r_docx.headers["location"].endswith(".docx")

    # public view page -> HTML content
    r_view = client.get("/s/Sh_test/view")
    assert r_view.status_code == 200
    assert "text/html" in r_view.headers.get("content-type", "")
    assert "成长档案预览" in r_view.text
    assert "下载 Word" in r_view.text
    assert "打开/下载 PDF" in r_view.text
    # story content
    assert "t1" in r_view.text

    # revoked -> 410
    fake_db["profile_story_shares"].update_one({"_id": "Sh_test"}, {"$set": {"status": "revoked"}})
    r_view_revoked = client.get("/s/Sh_test/view")
    assert r_view_revoked.status_code == 410


def test_public_share_view_page_expired_returns_410(monkeypatch):
    from app.main import app

    now = datetime(2026, 2, 7, 10, 0, 0)
    fake_db = _FakeDB(
        {
            "profile_story_exports": _FakeCollection(
                [
                    {
                        "_id": "e1",
                        "storyId": "s1",
                        "objectKey": "exports/u1/a1/e1.docx",
                        "pdfObjectKey": "exports/u1/a1/e1.pdf",
                        "createdAt": now,
                    }
                ]
            ),
            "profile_story_shares": _FakeCollection(
                [
                    {
                        "_id": "Sh_test",
                        "shareId": "Sh_test",
                        "storyId": "s1",
                        "exportId": "e1",
                        "status": "active",
                        "createdAt": now,
                        "expiresAt": now.replace(year=2026, month=2, day=6),
                    }
                ]
            ),
            "profile_stories": _FakeCollection(
                [
                    {
                        "_id": "s1",
                        "story": {"storyVersion": 1, "title": "t1", "chapters": [{"chapterTitle": "c", "paragraphs": ["p"]}], "milestones": [], "meta": {}},
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

    from app.routers import public_share as pub

    monkeypatch.setattr(pub, "presign_get_url", lambda object_key, **kwargs: "https://oss.example.com/" + object_key)

    client = TestClient(app)
    r = client.get("/s/Sh_test/view")
    assert r.status_code == 410
