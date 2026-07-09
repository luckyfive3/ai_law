"""
AI法律助手 v1.0 — MongoDB 数据库连接
使用 Motor 异步驱动
"""
import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from config import Settings

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def init_database(settings: Settings) -> AsyncIOMotorDatabase:
    """初始化 MongoDB 连接"""
    global _client, _db

    _client = AsyncIOMotorClient(
        settings.mongo_uri,
        maxPoolSize=settings.mongo_max_pool_size,
        minPoolSize=settings.mongo_min_pool_size,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
    )

    _db = _client[settings.mongo_db_name]

    # 验证连接
    await _client.admin.command("ping")
    logger.info(f"MongoDB 连接成功: {settings.mongo_uri}, 数据库: {settings.mongo_db_name}")

    # 创建索引
    await _create_indexes()

    return _db


async def _create_indexes():
    """创建必要的数据库索引"""
    # 用户集合
    await _db.users.create_index("username", unique=True, sparse=True)
    await _db.users.create_index("phone_hash", sparse=True)
    await _db.users.create_index("created_at")

    # 会话集合
    await _db.sessions.create_index("user_id")
    await _db.sessions.create_index([("user_id", 1), ("updated_at", -1)])
    await _db.sessions.create_index("status")

    # 消息集合
    await _db.messages.create_index("session_id")
    await _db.messages.create_index([("session_id", 1), ("created_at", 1)])
    await _db.messages.create_index("role")

    # 法条引用集合
    await _db.law_refs.create_index("message_id")

    # 审计日志集合
    await _db.audit_logs.create_index("user_id")
    await _db.audit_logs.create_index("created_at")

    # Token 用量集合
    await _db.token_usage.create_index("user_id")
    await _db.token_usage.create_index([("user_id", 1), ("date", 1)])

    # SMS 验证码集合 (TTL 索引，自动过期)
    await _db.sms_codes.create_index("phone_hash")
    await _db.sms_codes.create_index("expires_at", expireAfterSeconds=0)

    logger.info("MongoDB 索引创建完成")


def get_database() -> AsyncIOMotorDatabase:
    """获取数据库实例"""
    if _db is None:
        raise RuntimeError("数据库未初始化，请先调用 init_database()")
    return _db


async def close_database():
    """关闭数据库连接"""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
        logger.info("MongoDB 连接已关闭")
