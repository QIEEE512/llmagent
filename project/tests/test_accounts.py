import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)


def _setup_fake_db(monkeypatch):
    class _Coll:
        def __init__(self):
            self.store = {}

        def find_one(self, q):
            # account 查询
            if "account" in q:
                for v in self.store.values():
                    if v.get("account") == q["account"]:
                        return v
            _id = q.get("_id")
            if _id is not None:
                # 可能还带 userId
                if "userId" in q:
                    v = self.store.get(_id)
                    if v and v.get("userId") == q["userId"]:
                        return v
                    return None
                return self.store.get(_id)
            return None

        def insert_one(self, doc):
            self.store[doc["_id"]] = doc

        def delete_one(self, q):
            _id = q.get("_id")
            if _id in self.store and self.store[_id].get("userId") == q.get("userId"):
                del self.store[_id]
                return type("R", (), {"deleted_count": 1})()
            return type("R", (), {"deleted_count": 0})()

        def update_one(self, q, upd):
            _id = q.get("_id")
            if _id in self.store:
                if "$set" in upd:
                    self.store[_id].update(upd["$set"])

        def find(self, q):
            # very small fake cursor
            items = [v for v in self.store.values() if v.get("userId") == q.get("userId")]

            class _Cursor(list):
                def sort(self, *_args, **_kwargs):
                    return self

            return _Cursor(items)

    class _DB(dict):
        def __getitem__(self, k):
            if k not in self:
                self[k] = _Coll()
            return dict.__getitem__(self, k)

    fake_db = _DB()

    import app.db as dbmod

    monkeypatch.setattr(dbmod, "get_db", lambda: fake_db)
    return fake_db


def test_accounts_flow(client, monkeypatch):
    fake_db = _setup_fake_db(monkeypatch)

    # seed user + one account
    from app.security import hash_password

    fake_db["users"].insert_one(
        {
            "_id": "u_1008611",
            "name": "调试用户",
            "account": "1008611",
            "phone": None,
            "passwordHash": hash_password("1008611"),
            "activeAccountId": None,
            "createdAt": 0,
        }
    )
    fake_db["accounts"].insert_one(
        {"_id": "a1", "userId": "u_1008611", "name": "小朋友", "account": "1008611", "createdAt": 0}
    )

    # login
    r = client.post("/api/auth/login", json={"account": "1008611", "password": "1008611"})
    assert r.status_code == 200
    token = r.json()["data"]["accessToken"]

    # /auth/me
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["data"]["account"] == "1008611"

    # list
    r = client.get("/api/accounts", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert "items" in r.json()["data"]

    # create
    r = client.post("/api/accounts", json={"name": "家长"}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    new_id = r.json()["data"]["id"]

    # switch
    r = client.post("/api/accounts/switch", json={"accountId": new_id}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["data"]["activeAccountId"] == new_id

    # delete
    r = client.post(f"/api/accounts/{new_id}/delete", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
