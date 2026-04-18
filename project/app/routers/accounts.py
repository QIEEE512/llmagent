from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

import app.db as db
from app.deps import get_current_user_id
from app.schemas import (
    AccountItem,
    AccountsCreateRequest,
    AccountsListResponseData,
    AccountsSwitchRequest,
    AccountsSwitchResponseData,
    ApiResponse,
)

router = APIRouter(prefix="/accounts", tags=["Accounts"])


def _account_to_item(doc) -> AccountItem:
    return AccountItem(id=str(doc.get("_id")), name=doc.get("name", ""), account=doc.get("account", ""))


def _get_or_create_single_account(database, *, user_id: str) -> dict[str, Any]:
    accounts = database["accounts"]
    users = database["users"]

    # Keep deterministic one-account behavior: always choose the earliest one.
    account = accounts.find_one({"userId": user_id}, sort=[("createdAt", 1)])
    if account:
        account_id = str(account.get("_id"))
        users.update_one({"_id": user_id}, {"$set": {"activeAccountId": account_id}})
        return account

    user = users.find_one({"_id": user_id}) or {}
    account_id = f"a_{uuid.uuid4().hex[:10]}"
    account_login = str(user.get("account") or f"user_{uuid.uuid4().hex[:6]}")
    name = str(user.get("name") or "默认账号")

    account = {
        "_id": account_id,
        "userId": user_id,
        "name": name,
        "account": account_login,
        "createdAt": uuid.uuid1().time,
    }
    accounts.insert_one(account)
    users.update_one({"_id": user_id}, {"$set": {"activeAccountId": account_id}})
    return account


@router.get("", response_model=ApiResponse)
def list_accounts(user_id: str = Depends(get_current_user_id)):
    database = db.get_db()
    account = _get_or_create_single_account(database, user_id=user_id)
    items = [_account_to_item(account)]
    
    # 根据前端要求，可以返回 items 数组或者直接的数据数组
    # 这里我们保持 items 结构，因为它更符合 OpenAPI 规范
    return ApiResponse(ok=True, data=AccountsListResponseData(items=items))


@router.post("", response_model=ApiResponse)
def create_account(payload: AccountsCreateRequest, user_id: str = Depends(get_current_user_id)):
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name 不能为空")

    database = db.get_db()
    col = database["accounts"]

    # One-user-one-account policy: do not allow creating a second account.
    existing = col.find_one({"userId": user_id})
    if existing:
        raise HTTPException(status_code=409, detail="同一用户仅允许一个账号")

    account_id = f"a_{uuid.uuid4().hex[:10]}"
    # account 字段给前端展示用：给一个稳定的占位值即可（后续可改成真正的子账号体系）
    account_login = f"child_{uuid.uuid4().hex[:6]}"

    doc = {
        "_id": account_id,
        "userId": user_id,
        "name": name,
        "account": account_login,
        "createdAt": uuid.uuid1().time,
    }
    col.insert_one(doc)

    return ApiResponse(ok=True, data=_account_to_item(doc))


@router.post("/{accountId}/delete", response_model=ApiResponse)
def delete_account(accountId: str, user_id: str = Depends(get_current_user_id)):
    raise HTTPException(status_code=409, detail="单账号策略不支持删除账号")


@router.post("/switch", response_model=ApiResponse)
def switch_account(payload: AccountsSwitchRequest, user_id: str = Depends(get_current_user_id)):
    database = db.get_db()
    account = _get_or_create_single_account(database, user_id=user_id)
    active_id = str(account.get("_id"))

    # Keep API compatibility: switch is effectively a no-op in single-account mode.
    req_id = str(payload.accountId or "").strip()
    if req_id and req_id != active_id:
        raise HTTPException(status_code=409, detail="单账号策略下不可切换到其他账号")

    return ApiResponse(ok=True, data=AccountsSwitchResponseData(activeAccountId=active_id))