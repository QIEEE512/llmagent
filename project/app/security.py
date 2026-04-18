from __future__ import annotations

import time
from typing import Any

import jwt
from passlib.context import CryptContext

from app.config import settings

# bcrypt 在部分环境（例如 bcrypt 4.x 与 passlib 1.7.4 的组合）可能出现兼容性问题。
# 第一阶段先用 PBKDF2-SHA256（纯 Python 实现，稳定）保证注册/登录可用。
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(*, subject: str, extra: dict[str, Any] | None = None) -> str:
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + settings.access_token_expires_in,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
