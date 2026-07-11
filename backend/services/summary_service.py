"""
AI法律助手 v1.0 — 会话摘要与用户画像服务
基于 LLM 自动生成会话摘要，追踪用户咨询习惯
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from langchain_core.messages import HumanMessage

from services.prompts import SESSION_SUMMARY_PROMPT
from services.llm_service_v2 import LLMService

logger = logging.getLogger(__name__)

# 触发自动摘要的最小消息数
MIN_MESSAGES_FOR_SUMMARY = 4

# 用于生成用户画像摘要的 Prompt
USER_PROFILE_PROMPT_TEMPLATE = """你是一个用户行为分析助手。请根据以下用户的多次法律咨询记录，
分析用户的咨询习惯和偏好，生成一段简洁的用户画像（不超过200字）。

分析维度包括：
- 主要关注的法律领域（如劳动纠纷、婚姻家庭、合同纠纷等）
- 咨询风格（简洁直接 / 叙述详细 / 情绪化表达）
- 用户身份推断（如劳动者、企业主、普通居民等，基于问题内容推断）
- 给 AI 回答的建议（如"该用户偏好实用的行动建议"或"该用户喜欢法条原文引用"）

以下是该用户最近的咨询记录摘要：
{conversation_summaries}

请直接输出用户画像，不要有任何前缀说明。"""


class SummaryService:
    """
    会话摘要与用户画像服务

    功能：
        1. 为对话会话自动生成标题和摘要
        2. 追踪用户咨询习惯，生成用户画像
        3. 基于用户画像提供个性化回答建议
    """

    def __init__(self, db: AsyncIOMotorDatabase, llm_service: LLMService):
        """
        Args:
            db: MongoDB 数据库实例
            llm_service: LLM 服务实例（用于生成摘要）
        """
        self.db = db
        self.llm_service = llm_service

    # ═══════════════════════════════════════
    # 会话摘要
    # ═══════════════════════════════════════

    async def generate_session_summary(
        self,
        session_id: str,
        force: bool = False,
    ) -> Optional[str]:
        """
        为指定会话生成 AI 摘要，并更新会话的 title 和 summary 字段。

        仅在消息数 >= MIN_MESSAGES_FOR_SUMMARY 时生成，除非设置 force=True。

        Args:
            session_id: 会话 ID
            force: 是否强制生成（忽略消息数限制）

        Returns:
            生成的摘要文本，失败返回 None
        """
        from bson import ObjectId

        # 检查消息数量
        msg_count = await self.db.messages.count_documents({
            "session_id": session_id,
            "status": 1,
        })

        if msg_count < MIN_MESSAGES_FOR_SUMMARY and not force:
            logger.debug(f"会话 {session_id} 消息数不足 ({msg_count})，跳过摘要生成")
            return None

        # 获取对话内容（取最近的用户消息和 AI 回复）
        messages = await self._get_recent_messages(session_id, limit=20)
        if not messages:
            return None

        conversation_text = "\n".join(
            f"【{'用户' if m['role'] == 'user' else 'AI'}】{m['content'][:300]}"
            for m in messages
        )

        try:
            # 使用 LLM 生成摘要
            prompt_messages = SESSION_SUMMARY_PROMPT.invoke({
                "conversation": conversation_text,
            }).to_messages()

            # 非流式调用
            summary = ""
            async for token in self.llm_service.generate_stream(
                [{"role": "system", "content": msg.content} if msg.type == "system"
                 else {"role": "user", "content": msg.content}
                 for msg in prompt_messages]
            ):
                summary += token

            summary = summary.strip()

            if summary:
                # 更新会话的 title 和 summary
                try:
                    oid = ObjectId(session_id)
                    await self.db.sessions.update_one(
                        {"_id": oid},
                        {"$set": {
                            "summary": summary,
                            "title": summary[:50] if len(summary) > 50 else summary,
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }},
                    )
                except Exception:
                    pass

                logger.info(f"会话摘要已生成: session_id={session_id}, summary={summary[:50]}...")
                return summary

        except Exception as e:
            logger.error(f"生成会话摘要失败: {e}")

        return None

    async def _get_recent_messages(self, session_id: str, limit: int = 20) -> List[dict]:
        """获取会话最近的消息"""
        messages = []
        cursor = (
            self.db.messages.find({"session_id": session_id, "status": 1})
            .sort("created_at", -1)
            .limit(limit)
        )
        async for msg in cursor:
            messages.append({
                "role": msg.get("role", ""),
                "content": msg.get("content", ""),
            })
        messages.reverse()
        return messages

    async def get_session_summary(self, session_id: str) -> Optional[dict]:
        """获取已有的会话摘要"""
        from bson import ObjectId
        try:
            oid = ObjectId(session_id)
            session = await self.db.sessions.find_one({"_id": oid, "status": 1})
            if session and session.get("summary"):
                return {
                    "id": str(session["_id"]),
                    "title": session.get("title", ""),
                    "summary": session.get("summary", ""),
                    "category": session.get("category", ""),
                    "msg_count": session.get("msg_count", 0),
                }
        except Exception:
            pass
        return None

    # ═══════════════════════════════════════
    # 用户画像
    # ═══════════════════════════════════════

    async def update_user_profile(self, user_id: str) -> Optional[dict]:
        """
        更新用户画像：统计咨询习惯，使用 LLM 生成画像描述。

        Args:
            user_id: 用户 ID

        Returns:
            更新后的用户画像
        """
        # 1. 收集用户所有会话摘要
        summaries = []
        session_cursor = self.db.sessions.find(
            {"user_id": user_id, "status": 1, "summary": {"$exists": True}}
        ).sort("updated_at", -1).limit(20)

        async for s in session_cursor:
            summaries.append({
                "title": s.get("title", ""),
                "summary": s.get("summary", ""),
                "category": s.get("category", ""),
                "msg_count": s.get("msg_count", 0),
                "date": s.get("updated_at", "")[:10],
            })

        # 2. 统计类别分布
        category_stats = {}
        cat_cursor = self.db.sessions.find(
            {"user_id": user_id, "status": 1, "category": {"$ne": "general"}}
        )
        async for s in cat_cursor:
            cat = s.get("category", "general")
            category_stats[cat] = category_stats.get(cat, 0) + 1

        # 统计总消息数
        total_messages = 0
        pipeline = [
            {"$lookup": {
                "from": "messages",
                "localField": "_id",
                "foreignField": "session_id",
                "pipeline": [{"$match": {"status": 1}}],
                "as": "messages",
            }},
            {"$match": {"user_id": user_id, "status": 1}},
            {"$project": {"msg_count": {"$size": "$messages"}}},
        ]
        async for doc in self.db.sessions.aggregate(pipeline):
            total_messages += doc.get("msg_count", 0)

        # 3. 用 LLM 生成画像描述
        profile_text = ""
        if summaries:
            conv_text = "\n---\n".join(
                f"日期: {s['date']}, 领域: {s['category']}, 摘要: {s['summary'][:100]}"
                for s in summaries[:10]
            )
            try:
                prompt = USER_PROFILE_PROMPT_TEMPLATE.format(
                    conversation_summaries=conv_text,
                )
                async for token in self.llm_service.generate_stream(
                    [{"role": "user", "content": prompt}]
                ):
                    profile_text += token
                profile_text = profile_text.strip()
            except Exception as e:
                logger.error(f"生成用户画像失败: {e}")
                profile_text = ""

        # 4. 保存画像
        now = datetime.now(timezone.utc).isoformat()
        profile_data = {
            "user_id": user_id,
            "total_sessions": len(summaries),
            "total_messages": total_messages,
            "category_distribution": category_stats,
            "top_categories": sorted(
                category_stats, key=category_stats.get, reverse=True
            )[:3] if category_stats else [],
            "profile_text": profile_text,
            "recent_summaries": summaries[:5],
            "updated_at": now,
        }

        await self.db.user_profiles.update_one(
            {"user_id": user_id},
            {"$set": profile_data},
            upsert=True,
        )

        logger.info(f"用户画像已更新: user_id={user_id}, sessions={len(summaries)}")
        return profile_data

    async def get_user_profile(self, user_id: str) -> Optional[dict]:
        """获取用户画像"""
        profile = await self.db.user_profiles.find_one({"user_id": user_id})
        if not profile:
            return None

        return {
            "user_id": profile["user_id"],
            "total_sessions": profile.get("total_sessions", 0),
            "total_messages": profile.get("total_messages", 0),
            "category_distribution": profile.get("category_distribution", {}),
            "top_categories": profile.get("top_categories", []),
            "profile_text": profile.get("profile_text", ""),
            "updated_at": profile.get("updated_at", ""),
        }

    async def get_personalized_context(
        self, user_id: str, max_length: int = 300
    ) -> str:
        """
        获取个性化的上下文提示，用于注入到对话 System Prompt 中。

        返回空字符串表示无需个性化（新用户或无足够数据）。

        Args:
            user_id: 用户 ID
            max_length: 最大字符长度

        Returns:
            个性化上下文文本
        """
        profile = await self.get_user_profile(user_id)
        if not profile:
            return ""

        parts = []

        # 用户偏好的领域
        top_cats = profile.get("top_categories", [])
        if top_cats:
            cat_names = {
                "marriage": "婚姻家庭", "labor": "劳动纠纷",
                "contract": "合同纠纷", "traffic": "交通事故",
                "housing": "房产纠纷", "consumer": "消费维权",
                "criminal": "刑事法律", "general": "综合",
            }
            cat_labels = [cat_names.get(c, c) for c in top_cats]
            parts.append(f"该用户主要咨询领域：{'、'.join(cat_labels[:3])}")

        # 用户画像文字（LLM 生成）
        profile_text = profile.get("profile_text", "")
        if profile_text:
            parts.append(f"用户画像：{profile_text[:200]}")

        # 历史会话数
        total = profile.get("total_sessions", 0)
        if total > 0:
            parts.append(f"该用户已进行过 {total} 次法律咨询")

        context = "\n".join(parts)
        if len(context) > max_length:
            context = context[:max_length-3] + "..."

        return context

    # ═══════════════════════════════════════
    # 批量生成（后台任务）
    # ═══════════════════════════════════════

    async def auto_summary_and_profile(
        self,
        session_id: str,
        user_id: str,
    ) -> None:
        """
        后台任务：自动生成会话摘要，然后更新用户画像。

        在每次对话结束后调用（fire-and-forget）。

        Args:
            session_id: 会话 ID
            user_id: 用户 ID
        """
        try:
            # 1. 生成会话摘要
            await self.generate_session_summary(session_id)

            # 2. 更新用户画像
            await self.update_user_profile(user_id)

        except Exception as e:
            logger.error(f"自动摘要/画像生成失败: {e}")
