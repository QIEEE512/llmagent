import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)


def test_register_login_and_chat_flow(client, monkeypatch):
    # 使用内存 fake db，避免依赖真实 MongoDB
    class _Coll:
        def __init__(self):
            self.store = {}

        def find_one(self, q):
            if "account" in q:
                for v in self.store.values():
                    if v.get("account") == q["account"]:
                        return v
            _id = q.get("_id")
            if _id:
                return self.store.get(_id)
            return None

        def insert_one(self, doc):
            self.store[doc["_id"]] = doc
            return None

    class _DB(dict):
        def __getitem__(self, k):
            if k not in self:
                self[k] = _Coll()
            return dict.__getitem__(self, k)

    fake_db = _DB()

    import app.db as dbmod

    monkeypatch.setattr(dbmod, "get_db", lambda: fake_db)

    r = client.post(
        "/api/auth/register",
        json={"name": "小明", "account": "test@example.com", "password": "123456"},
    )
    assert r.status_code == 200
    user_id = r.json()["data"]["userId"]
    assert user_id.startswith("u_")

    r = client.post(
        "/api/auth/login",
        json={"account": "test@example.com", "password": "123456"},
    )
    assert r.status_code == 200
    token = r.json()["data"]["accessToken"]
    assert r.json()["data"]["tokenType"] == "bearer"

    r = client.post(
        "/api/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"text": "你好"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["answer"]


def test_debug_user_1008611_can_login(client, monkeypatch):
    # 用内存 fake db 并手动 seed 调试账号，模拟 startup seed 的效果
    class _Coll:
        def __init__(self):
            self.store = {}

        def find_one(self, q):
            if "account" in q:
                for v in self.store.values():
                    if v.get("account") == q["account"]:
                        return v
            _id = q.get("_id")
            if _id:
                return self.store.get(_id)
            return None

        def insert_one(self, doc):
            self.store[doc["_id"]] = doc
            return None

    class _DB(dict):
        def __getitem__(self, k):
            if k not in self:
                self[k] = _Coll()
            return dict.__getitem__(self, k)

    fake_db = _DB()

    import app.db as dbmod
    from app.security import hash_password

    monkeypatch.setattr(dbmod, "get_db", lambda: fake_db)

    # seed debug user
    fake_db["users"].insert_one(
        {
            "_id": "u_1008611",
            "name": "调试用户",
            "account": "1008611",
            "phone": None,
            "passwordHash": hash_password("1008611"),
            "createdAt": 0,
        }
    )

    r = client.post("/api/auth/login", json={"account": "1008611", "password": "1008611"})
    assert r.status_code == 200
    assert r.json()["data"]["accessToken"]
    assert r.json()["data"]["tokenType"] == "bearer"
