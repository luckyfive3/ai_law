"""
AI法律助手 v1.0 — 用户资料服务
用户个人信息查询与更新
"""
import logging
from datetime import datetime, timezone
from typing import Dict

from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

logger = logging.getLogger(__name__)


class UserService:
    """
    用户资料服务
    管理用户个人信息和隐私设置
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        初始化用户服务

        Args:
            db: MongoDB 数据库实例
        """
        self.db = db

    # ═══════════════════════════════════════
    # 获取个人信息
    # ═══════════════════════════════════════

    async def get_profile(self, user_id: str) -> dict:
        """
        获取用户个人信息

        Args:
            user_id: 用户ID（字符串）

        Returns:
            用户信息字典，包含:
                - id: 用户ID
                - username: 用户名
                - nickname: 昵称
                - avatar_url: 头像URL
                - privacy_save_history: 是否保存历史记录
                - created_at: 注册时间

        Raises:
            ValueError: 用户不存在
        """
        try:
            user = await self.db.users.find_one({"_id": ObjectId(user_id)})
        except Exception:
            raise ValueError("用户ID格式无效")

        if not user:
            raise ValueError("用户不存在")

        return {
            "id": str(user["_id"]),
            "username": user.get("username", ""),
            "nickname": user.get("nickname", ""),
            "avatar_url": user.get("avatar_url", ""),
            "privacy_save_history": user.get("privacy_save_history", True),
            "created_at": user.get("created_at", ""),
        }

    # ═══════════════════════════════════════
    # 更新个人信息
    # ═══════════════════════════════════════

    async def update_profile(self, user_id: str, updates: dict) -> dict:
        """
        更新用户个人信息

        Args:
            user_id: 用户ID（字符串）
            updates: 要更新的字段，支持:
                - nickname: 昵称（1-50字符）
                - avatar_url: 头像URL

        Returns:
            更新后的用户信息

        Raises:
            ValueError: 用户不存在 / 参数无效
        """
        try:
            oid = ObjectId(user_id)
        except Exception:
            raise ValueError("用户ID格式无效")

        # 校验可更新的字段
        allowed_fields = {"nickname", "avatar_url"}
        update_data = {}

        for key in allowed_fields:
            if key in updates:
                val = updates[key]
                if key == "nickname":
                    if not val or len(str(val).strip()) == 0:
                        raise ValueError("昵称不能为空")
                    if len(str(val)) > 50:
                        raise ValueError("昵称长度不能超过50字")
                    update_data[key] = str(val).strip()
                elif key == "avatar_url":
                    update_data[key] = str(val)

        if not update_data:
            raise ValueError("没有可更新的字段")

        # 添加更新时间
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        # 更新文档
        result = await self.db.users.update_one(
            {"_id": oid},
            {"$set": update_data},
        )

        if result.matched_count == 0:
            raise ValueError("用户不存在")

        logger.info(f"用户信息更新成功: user_id={user_id}, fields={list(update_data.keys())}")

        # 重新获取更新后的信息
        user = await self.db.users.find_one({"_id": oid})
        return {
            "id": str(user["_id"]),
            "username": user.get("username", ""),
            "nickname": user.get("nickname", ""),
            "avatar_url": user.get("avatar_url", ""),
            "privacy_save_history": user.get("privacy_save_history", True),
            "created_at": user.get("created_at", ""),
            "updated_at": user.get("updated_at", ""),
        }

    # ═══════════════════════════════════════
    # 更新隐私设置
    # ═══════════════════════════════════════

    async def update_privacy(self, user_id: str, save_history: bool) -> dict:
        """
        更新用户隐私设置

        Args:
            user_id: 用户ID（字符串）
            save_history: 是否保存对话历史

        Returns:
            更新后的隐私设置状态

        Raises:
            ValueError: 用户不存在
        """
        try:
            oid = ObjectId(user_id)
        except Exception:
            raise ValueError("用户ID格式无效")

        now = datetime.now(timezone.utc).isoformat()

        result = await self.db.users.update_one(
            {"_id": oid},
            {
                "$set": {
                    "privacy_save_history": save_history,
                    "updated_at": now,
                }
            },
        )

        if result.matched_count == 0:
            raise ValueError("用户不存在")

        logger.info(
            f"隐私设置更新成功: user_id={user_id}, save_history={save_history}"
        )

        return {
            "privacy_save_history": save_history,
            "message": "隐私设置已更新",
        }
