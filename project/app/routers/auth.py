from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

import app.db as db
from fastapi import Depends

from app.deps import get_current_user_id
from app.schemas import ApiResponse, LoginRequest, MeResponseData, RegisterRequest, RegisterResponseData
from app.security import create_access_token, hash_password, verify_password
from pymongo.errors import PyMongoError

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("/me", response_model=ApiResponse)
def me(user_id: str = Depends(get_current_user_id)):
    database = db.get_db()
    users = database["users"]
    try:
        user = users.find_one({"_id": user_id})
    except PyMongoError as e:
        raise HTTPException(status_code=503, detail=f"数据库不可用：{e}")
    if not user:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")

    # 根据前端要求，返回用户信息，包括 id、name 和 account
    # 兼容字段别名（id|accountId|account, name|nickname|displayName, account|username|login）
    data = MeResponseData(id=str(user.get("_id")), name=user.get("name", ""), account=user.get("account", ""))
    return ApiResponse(ok=True, data=data)


@router.post("/register", response_model=ApiResponse)
def register(payload: RegisterRequest):
    database = db.get_db()
    users = database["users"]
    try:
        if users.find_one({"account": payload.account}):
            # 前端验收：第二次同 account 注册返回 409/400 且 detail 明确
            raise HTTPException(status_code=409, detail="账号已存在")
    except PyMongoError as e:
        raise HTTPException(status_code=503, detail=f"数据库不可用：{e}")
        # 前端验收：第二次同 account 注册返回 409/400 且 detail 明确
        raise HTTPException(status_code=409, detail="账号已存在")

    user_id = f"u_{uuid.uuid4().hex[:12]}"
    try:
        users.insert_one(
        {
            "_id": user_id,
            "name": payload.name,
            "account": payload.account,
            # 前端可能传空字符串：这里统一转为 None
            "phone": (payload.phone or None),
            "passwordHash": hash_password(payload.password),
            "createdAt": uuid.uuid1().time,
        }
        )
    except PyMongoError as e:
        raise HTTPException(status_code=503, detail=f"数据库不可用：{e}")

    return ApiResponse(ok=True, data=RegisterResponseData(userId=user_id))


@router.post("/login", response_model=ApiResponse)
def login(payload: LoginRequest):
    database = db.get_db()
    users = database["users"]
    try:
        user = users.find_one({"account": payload.account})
    except PyMongoError as e:
        raise HTTPException(status_code=503, detail=f"数据库不可用：{e}")
    if not user:
        raise HTTPException(status_code=401, detail="账号或密码错误")

    if not verify_password(payload.password, user.get("passwordHash", "")):
        raise HTTPException(status_code=401, detail="账号或密码错误")

    # 兼容性：部分 jwt 实现/配置下可能返回 bytes 或出现换行，导致前端/后续鉴权解析失败。
    token = str(create_access_token(subject=str(user["_id"]))).replace("\n", "")
    # 登录页对接：只要求返回 accessToken + tokenType
    return ApiResponse(ok=True, data={"accessToken": token, "tokenType": "bearer"})