from __future__ import annotations

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.config import settings


_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        # 设置连接超时，避免在 Mongo 不可达时长时间阻塞（单位 ms）
        # connectTimeoutMS: 连接建立超时
        # serverSelectionTimeoutMS: 选择服务器超时（用于快速失败）
        # socketTimeoutMS: socket 操作超时
        _client = MongoClient(
            settings.mongodb_uri,
            connectTimeoutMS=5000,
            serverSelectionTimeoutMS=5000,
            socketTimeoutMS=5000,
        )
    return _client


def get_db():
    return get_client()[settings.mongodb_db]
