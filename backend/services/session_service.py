"""
AI法律助手 v1.0 — 会话管理服务
创建、列表、详情、删除会话
"""
import logging
from datetime import datetime, timezone
from typing import List, Tuple, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

logger = logging.getLogger(__name__)


class SessionService:
    """
    会话管理服务
    管理用户的咨询会话生命周期
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        初始化会话服务

        Args:
            db: MongoDB 数据库实例
        """
        self.db = db

    # ═══════════════════════════════════════
    # 创建会话
    # ═══════════════════════════════════════

    async def create(
        self,
        user_id: str,
        title: str = "",
        category: str = "",
    ) -> dict:
        """
        创建新会话

        Args:
            user_id: 用户ID（字符串）
            title: 会话标题，默认为"法律咨询"
            category: 会话分类，默认为"general"

        Returns:
            创建的会话信息:
                - id: 会话ID
                - user_id: 用户ID
                - title: 标题
                - category: 分类
                - msg_count: 消息数（0）
                - created_at: 创建时间
        """
        if not title:
            title = "法律咨询"
        if not category:
            category = "general"

        now = datetime.now(timezone.utc).isoformat()

        session_doc = {
            "user_id": user_id,
            "title": title,
            "category": category,
            "msg_count": 0,
            "status": 1,  # 1 = 正常
            "created_at": now,
            "updated_at": now,
        }

        result = await self.db.sessions.insert_one(session_doc)
        session_id = str(result.inserted_id)

        logger.info(f"会话创建成功: id={session_id}, user_id={user_id}")

        return {
            "id": session_id,
            "user_id": user_id,
            "title": title,
            "category": category,
            "msg_count": 0,
            "created_at": now,
            "updated_at": now,
        }

    # ═══════════════════════════════════════
    # 会话列表
    # ═══════════════════════════════════════

    async def list_sessions(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[dict], int]:
        """
        获取用户的会话列表（分页）

        Args:
            user_id: 用户ID（字符串）
            page: 页码（从1开始）
            page_size: 每页条数

        Returns:
            (会话列表, 总数)
        """
        # 查询条件：用户ID + 正常状态
        query = {
            "user_id": user_id,
            "status": 1,
        }

        # 获取总数
        total = await self.db.sessions.count_documents(query)

        # 分页查询，按更新时间倒序
        skip = (page - 1) * page_size
        cursor = (
            self.db.sessions.find(query)
            .sort("updated_at", -1)
            .skip(skip)
            .limit(page_size)
        )

        sessions = []
        async for doc in cursor:
            sessions.append({
                "id": str(doc["_id"]),
                "title": doc.get("title", "法律咨询"),
                "category": doc.get("category", ""),
                "msg_count": doc.get("msg_count", 0),
                "updated_at": doc.get("updated_at", ""),
                "created_at": doc.get("created_at", ""),
            })

        return sessions, total

    # ═══════════════════════════════════════
    # 会话详情
    # ═══════════════════════════════════════

    async def get_detail(
        self,
        session_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> Optional[dict]:
        """
        获取会话详情（含消息列表）

        Args:
            session_id: 会话ID（字符串）
            page: 消息页码
            page_size: 消息每页条数

        Returns:
            会话详情，含 messages 列表；会话不存在返回 None
        """
        try:
            oid = ObjectId(session_id)
        except Exception:
            logger.warning(f"无效的会话ID: {session_id}")
            return None

        # 获取会话
        session = await self.db.sessions.find_one({"_id": oid, "status": 1})
        if not session:
            return None

        # 获取消息列表（按时间正序）
        skip = (page - 1) * page_size
        msg_cursor = (
            self.db.messages.find({"session_id": session_id, "status": 1})
            .sort("created_at", 1)
            .skip(skip)
            .limit(page_size)
        )

        messages = []
        async for msg in msg_cursor:
            msg_data = {
                "id": str(msg["_id"]),
                "session_id": msg.get("session_id", ""),
                "role": msg.get("role", ""),
                "content": msg.get("content", ""),
                "content_type": msg.get("content_type", "text"),
                "tokens": msg.get("tokens", 0),
                "created_at": msg.get("created_at", ""),
            }

            # 如果是 assistant 消息，加载法条引用
            if msg.get("role") == "assistant":
                refs = []
                ref_cursor = self.db.law_refs.find(
                    {"message_id": str(msg["_id"])}
                )
                async for ref in ref_cursor:
                    refs.append({
                        "name": ref.get("law_name", ""),
                        "article": ref.get("article_num", ""),
                        "text": ref.get("law_text", ""),
                        "source": ref.get("source", ""),
                        "chunk_id": ref.get("chunk_id", ""),
                        "relevance": ref.get("relevance", 0),
                    })
                msg_data["law_refs"] = refs

            messages.append(msg_data)

        return {
            "id": str(session["_id"]),
            "title": session.get("title", "法律咨询"),
            "category": session.get("category", ""),
            "msg_count": session.get("msg_count", 0),
            "updated_at": session.get("updated_at", ""),
            "messages": messages,
        }

    # ═══════════════════════════════════════
    # 删除会话
    # ═══════════════════════════════════════

    async def delete(self, session_id: str, user_id: str) -> bool:
        """
        软删除会话

        Args:
            session_id: 会话ID（字符串）
            user_id: 用户ID（字符串），用于权限验证

        Returns:
            是否删除成功
        """
        try:
            oid = ObjectId(session_id)
        except Exception:
            return False

        # 软删除：更新 status 为 0
        result = await self.db.sessions.update_one(
            {"_id": oid, "user_id": user_id},
            {
                "$set": {
                    "status": 0,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            },
        )

        if result.modified_count > 0:
            logger.info(f"会话删除成功: id={session_id}, user_id={user_id}")
            return True

        return False

    # ═══════════════════════════════════════
    # 清空全部会话
    # ═══════════════════════════════════════

    async def clear_all(self, user_id: str) -> int:
        """
        清空用户全部历史会话（软删除）

        Args:
            user_id: 用户ID（字符串）

        Returns:
            删除的会话数量
        """
        result = await self.db.sessions.update_many(
            {"user_id": user_id, "status": 1},
            {
                "$set": {
                    "status": 0,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            },
        )

        count = result.modified_count
        logger.info(f"清空全部会话: user_id={user_id}, 删除 {count} 个会话")
        return count

    # ═══════════════════════════════════════
    # 更新消息计数
    # ═══════════════════════════════════════

    async def increment_msg_count(self, session_id: str) -> None:
        """
        增加会话的消息计数

        Args:
            session_id: 会话ID（字符串）
        """
        try:
            oid = ObjectId(session_id)
            await self.db.sessions.update_one(
                {"_id": oid},
                {
                    "$inc": {"msg_count": 1},
                    "$set": {"updated_at": datetime.now(timezone.utc).isoformat()},
                },
            )
        except Exception as e:
            logger.warning(f"更新消息计数失败: {e}")
