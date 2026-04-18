from fastapi.testclient import TestClient

from app.main import api


def _override_user_id():
    return "u_test"


def test_avatar_video_generate_and_status(monkeypatch):
    # override auth for sub-app
    # Important: restore overrides afterwards to avoid cross-test contamination.
    prev_overrides = dict(getattr(api, "dependency_overrides", {}) or {})
    api.dependency_overrides = {}
    from app import deps

    api.dependency_overrides[deps.get_current_user_id] = _override_user_id

    # patch account resolver to stable value via overriding users collection behavior
    # easiest: patch the router helper to return a fixed accountId
    import app.routers.avatar as avatar_router

    monkeypatch.setattr(avatar_router, "_get_active_account_id", lambda database, user_id: "a1")

    # patch wanx video functions (note: avatar router imports symbols directly)
    import app.routers.avatar as avatar_router

    class _Out:
        task_status = "SUCCEEDED"
        video_url = "https://example.com/v.mp4"

    class _Rsp:
        output = _Out()

    monkeypatch.setattr(avatar_router, "wan_i2v_create_task", lambda prompt, img_url, model=None: ("t123", "PENDING"))
    monkeypatch.setattr(avatar_router, "wan_i2v_fetch", lambda task_id: _Rsp())
    monkeypatch.setattr(
        avatar_router,
        "wan_i2v_download_video_to_file",
        lambda video_url, filename_prefix="": (None, "/files/v_local.mp4"),
    )

    # mock OSS upload + presign
    class _PutRes:
        object_key = "i2v_inputs/img.png"

    monkeypatch.setattr(avatar_router, "put_file_from_local", lambda *args, **kwargs: _PutRes())
    monkeypatch.setattr(avatar_router, "presign_get_url", lambda *args, **kwargs: "https://oss.example.com/i2v_inputs/img.png?sig=1")

    # mock preflight http check for signed url
    class _HResp:
        def __init__(self, status_code=200, headers=None):
            self.status_code = status_code
            self.headers = headers or {"content-type": "image/png"}

    class _HClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def head(self, url, *args, **kwargs):
            return _HResp(200, {"content-type": "image/png"})

        def get(self, url, *args, **kwargs):
            return _HResp(206, {"content-type": "image/png"})

    monkeypatch.setattr(avatar_router.httpx, "Client", _HClient)

    # patch db to in-memory fake
    class _FakeColl:
        def __init__(self):
            self.docs = {}

        def update_one(self, filt, upd, upsert=False):
            _id = filt.get("_id")
            if _id is not None:
                doc = self.docs.get(_id, {}).copy()
                if "$setOnInsert" in upd and upsert and _id not in self.docs:
                    doc.update(upd["$setOnInsert"])
                if "$set" in upd:
                    doc.update(upd["$set"])
                doc["_id"] = _id
                self.docs[_id] = doc
                return

            # Non-_id upsert (needed for avatars collection keyed by userId+accountId)
            found_id = None
            for k, v in self.docs.items():
                ok = True
                for fk, fv in filt.items():
                    if v.get(fk) != fv:
                        ok = False
                        break
                if ok:
                    found_id = k
                    break

            if found_id is None:
                if not upsert:
                    return
                found_id = f"auto_{len(self.docs) + 1}"
                self.docs[found_id] = {"_id": found_id}
                if "$setOnInsert" in upd:
                    self.docs[found_id].update(upd["$setOnInsert"])

            if "$set" in upd:
                self.docs[found_id].update(upd["$set"])
            self.docs[found_id]["_id"] = found_id
            return

        def find_one(self, filt):
            if "_id" in filt:
                doc = self.docs.get(filt["_id"])
                if not doc:
                    return None
                for k, v in filt.items():
                    if k == "_id":
                        continue
                    if doc.get(k) != v:
                        return None
                return doc
            # naive scan
            for doc in self.docs.values():
                ok = True
                for k, v in filt.items():
                    if doc.get(k) != v:
                        ok = False
                        break
                if ok:
                    return doc
            return None

    class _FakeDB:
        def __init__(self):
            self.c = {"avatar_video_jobs": _FakeColl()}

        def __getitem__(self, name):
            return self.c.setdefault(name, _FakeColl())

        def get_collection(self, name):
            return self.__getitem__(name)

    fake_db = _FakeDB()

    import app.db as app_db

    monkeypatch.setattr(app_db, "get_db", lambda: fake_db)

    # security: portrait files path resolution should accept /files/*.png
    # it checks local file existence; create a dummy file
    from pathlib import Path

    uploads = Path("/tmp/uploads")
    uploads.mkdir(parents=True, exist_ok=True)
    (uploads / "img.png").write_bytes(b"x")

    try:
        client = TestClient(api)

        r = client.post("/avatar/video/generate", json={"imageUrl": "/files/img.png", "prompt": "hi"})
        assert r.status_code == 200
        job_id = r.json()["data"]["jobId"]
        assert job_id.startswith("vj_")

        # fallback: use current active avatar imageUrl when imageUrl is missing
        # seed avatars collection with an active imageUrl
        fake_db.get_collection("avatars").update_one(
            {"userId": "u_test", "accountId": "a1"},
            {"$set": {"userId": "u_test", "accountId": "a1", "imageUrl": "/files/img.png"}},
            upsert=True,
        )
        r_fallback = client.post("/avatar/video/generate", json={"prompt": "hi"})
        assert r_fallback.status_code == 200
        job_id_2 = r_fallback.json()["data"]["jobId"]
        assert job_id_2.startswith("vj_")

        r2 = client.get("/avatar/video/status", params={"jobId": job_id})
        assert r2.status_code == 200
        data = r2.json()["data"]
        assert data["jobId"] == job_id
        assert data["status"] == "SUCCEEDED"
        assert data["videoUrl"] == "/files/v_local.mp4"
    finally:
        api.dependency_overrides = prev_overrides
