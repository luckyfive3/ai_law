"""
AI法律助手 v1.0 — 认证服务
用户注册、登录、Token刷新
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Optional

from passlib.context import CryptContext
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from config import Settings, load_config
from utils.jwt_utils import create_access_token, create_refresh_token, decode_token

logger = logging.getLogger(__name__)

# ── 密码哈希上下文 ──
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """对密码进行 bcrypt 哈希"""
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码是否匹配"""
    return _pwd_context.verify(plain_password, hashed_password)


class AuthService:
    """
    认证服务
    处理用户注册、登录、Token刷新
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        初始化认证服务

        Args:
            db: MongoDB 数据库实例
        """
        self.db = db
        self._settings = load_config()

    # ═══════════════════════════════════════
    # 注册
    # ═══════════════════════════════════════

    async def register(
        self,
        username: str,
        password: str,
        agree_terms: bool = False,
    ) -> dict:
        """
        用户注册

        Args:
            username: 用户名（3-50字符）
            password: 密码（至少6字符）
            agree_terms: 是否同意用户协议

        Returns:
            包含用户信息和 Token 的字典:
                - user: {id, username, nickname, created_at}
                - access_token: JWT访问令牌
                - refresh_token: JWT刷新令牌
                - expires_in: 访问令牌过期秒数

        Raises:
            ValueError: 用户名已存在 / 参数无效
        """
        # 参数校验
        if not username or len(username.strip()) < 3 or len(username.strip()) > 50:
            raise ValueError("用户名长度应在3-50个字符之间")
        if not password or len(password) < 6:
            raise ValueError("密码长度至少6个字符")

        username = username.strip()

        # 检查用户名是否已存在
        existing = await self.db.users.find_one({"username": username})
        if existing:
            raise ValueError("用户名已被注册")

        # 密码哈希
        password_hash = hash_password(password)
        now = datetime.now(timezone.utc)
        now_str = now.isoformat()

        # 创建用户文档
        user_doc = {
            "username": username,
            "password_hash": password_hash,
            "nickname": username,  # 默认昵称 = 用户名
            "avatar_url": "",
            "privacy_save_history": True,
            "agree_terms": agree_terms,
            "status": 1,  # 1 = 正常
            "created_at": now_str,
            "updated_at": now_str,
        }

        result = await self.db.users.insert_one(user_doc)
        user_id = str(result.inserted_id)

        logger.info(f"用户注册成功: username={username}, user_id={user_id}")

        # 生成 Token
        access_token, refresh_token, expires_in = self._generate_tokens(
            user_id, username
        )

        return {
            "user": {
                "id": user_id,
                "username": username,
                "nickname": username,
                "created_at": now_str,
            },
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": expires_in,
        }

    # ═══════════════════════════════════════
    # 登录
    # ═══════════════════════════════════════

    async def login(
        self,
        username: str,
        password: str,
        agree_terms: bool = False,
    ) -> dict:
        """
        用户登录

        Args:
            username: 用户名
            password: 密码
            agree_terms: 是否同意用户协议

        Returns:
            包含 Token 的字典

        Raises:
            ValueError: 用户名或密码错误
        """
        username = username.strip()

        # 查找用户
        user = await self.db.users.find_one({"username": username})
        if not user:
            raise ValueError("用户名或密码错误")

        # 校验密码
        if not verify_password(password, user.get("password_hash", "")):
            raise ValueError("用户名或密码错误")

        # 检查用户状态
        if user.get("status") != 1:
            raise ValueError("账户已被禁用")

        user_id = str(user["_id"])

        # 更新登录时间
        now = datetime.now(timezone.utc).isoformat()
        await self.db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"last_login_at": now, "updated_at": now}},
        )

        logger.info(f"用户登录成功: username={username}, user_id={user_id}")

        # 生成 Token
        access_token, refresh_token, expires_in = self._generate_tokens(
            user_id, username
        )

        return {
            "user": {
                "id": user_id,
                "username": user.get("username", username),
                "nickname": user.get("nickname", username),
                "avatar_url": user.get("avatar_url", ""),
            },
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": expires_in,
        }

    # ═══════════════════════════════════════
    # Token 刷新
    # ═══════════════════════════════════════

    async def refresh_token(self, refresh_token_str: str) -> dict:
        """
        通过 Refresh Token 获取新的 Token 对

        Args:
            refresh_token_str: Refresh Token 字符串

        Returns:
            包含新 Token 的字典

        Raises:
            ValueError: Refresh Token 无效或过期
        """
        try:
            payload = decode_token(refresh_token_str)

            # 校验 Token 类型
            if payload.get("type") != "refresh":
                raise ValueError("无效的刷新令牌")

            user_id = payload["user_id"]
            username = payload["username"]

            # 确认用户存在
            from bson import ObjectId as OID
            user = await self.db.users.find_one({"_id": OID(user_id)})
            if not user or user.get("status") != 1:
                raise ValueError("用户不存在或已被禁用")

            # 生成新的 Token 对
            access_token, refresh_token, expires_in = self._generate_tokens(
                user_id, username
            )

            logger.info(f"Token 刷新成功: user_id={user_id}")

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_in": expires_in,
            }

        except Exception as e:
            logger.warning(f"Token 刷新失败: {e}")
            raise ValueError("刷新令牌无效或已过期")

    # ═══════════════════════════════════════
    # 退出登录
    # ═══════════════════════════════════════

    async def logout(self) -> None:
        """
        退出登录（当前为无状态 JWT，仅做日志记录）

        如果后续需要实现 Token 黑名单，可在此扩展
        """
        logger.info("用户退出登录（JWT 模式下无需服务端操作）")
        return None

    # ═══════════════════════════════════════
    # Token 生成（内部方法）
    # ═══════════════════════════════════════

    def _generate_tokens(
        self, user_id: str, username: str
    ) -> tuple[str, str, int]:
        """
        生成 Access Token 和 Refresh Token

        Args:
            user_id: 用户ID（字符串）
            username: 用户名

        Returns:
            (access_token, refresh_token, expires_in)
        """
        access_token = create_access_token(user_id, username)
        refresh_token = create_refresh_token(user_id, username)
        expires_in = self._settings.jwt_access_ttl

        return access_token, refresh_token, expires_in
