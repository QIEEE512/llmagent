from __future__ import annotations

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.security import decode_token

bearer = HTTPBearer(auto_error=False)


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> str:
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")

    try:
        payload = decode_token(credentials.credentials)
    except Exception:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")

    return str(sub)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> dict:
    """返回当前登录用户（最小 dict 结构），供需要取 user 信息的路由使用。"""

    user_id = get_current_user_id(credentials)
    return {"id": user_id}


# 兼容：部分路由导入 get_current_user_id
if "get_current_user_id" not in globals():
    from fastapi import Depends

    def get_current_user_id(user=Depends(get_current_user)) -> str:  # type: ignore[no-redef]
        return str(user.get("id") or user.get("userId") or user.get("_id"))
