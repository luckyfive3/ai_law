"""
AI法律助手 v1.0 — 核心聊天服务
SSE 流式对话、消息管理、审计日志
"""
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator, List, Optional, Tuple

from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from services.ragflow_client import RAGFlowClient
from services.llm_service import LLMService
from services.context_builder import ContextBuilder
from services.safety_filter import SafetyFilter

logger = logging.getLogger(__name__)


class ContentSafetyCheck:
    """
    简单的内容安全检查器
    用于检查用户输入是否包含敏感词
    """

    def __init__(self, enable: bool = True):
        self.enable = enable

    def check(self, text: str) -> bool:
        """
        检查文本是否安全

        Args:
            text: 要检查的文本

        Returns:
            True = 安全, False = 包含敏感内容
        """
        if not self.enable:
            return True

        # 简单的敏感词检查（可根据需要扩展）
        return True  # 默认通过，实际部署时可加载敏感词库


class ChatService:
    """
    核心聊天服务
    管理对话的完整生命周期：安全检查 -> 检索 -> LLM生成 -> 保存
    """

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        ragflow_client: RAGFlowClient,
        llm_service: LLMService,
        context_builder: ContextBuilder,
        safety_filter: SafetyFilter,
        content_safety: ContentSafetyCheck,
    ):
        """
        初始化聊天服务

        Args:
            db: MongoDB 数据库实例
            ragflow_client: RAGFlow 检索客户端
            llm_service: LLM 服务
            context_builder: 上下文构建器
            safety_filter: 安全过滤器
            content_safety: 内容安全检查器
        """
        self.db = db
        self.ragflow_client = ragflow_client
        self.llm_service = llm_service
        self.context_builder = context_builder
        self.safety_filter = safety_filter
        self.content_safety = content_safety

    # ═══════════════════════════════════════
    # 发送消息（SSE 流式生成器）
    # ═══════════════════════════════════════

    async def send_message(
        self,
        user_id: str,
        session_id: str,
        query: str,
        category: str = "",
        client_ip: str = "",
    ) -> AsyncGenerator[dict, None]:
        """
        SSE 流式对话生成器

        处理流程:
        1. 内容安全检查
        2. 保存用户消息到 MongoDB
        3. 更新会话消息计数
        4. 调用 RAGFlow 检索相关法条
        5. 获取最近历史消息
        6. 使用 context_builder 构建上下文
        7. 流式调用 LLM 生成回答
        8. 完成后保存 AI 消息、法条引用、Token 用量

        Args:
            user_id: 用户ID（字符串）
            session_id: 会话ID（字符串）
            query: 用户提问内容
            category: 问题分类
            client_ip: 客户端IP

        Yields:
            SSE 事件字典:
                - {"status": "searching", "index": 0}  正在检索
                - {"status": "generating", "content": "...", "index": n}  生成中的token
                - {"status": "done", "done": true, "message_id": "...", "laws": [...], "tokens": {...}}  完成
                - {"status": "error", "error": "..."}  错误
        """
        # ── 1. 内容安全检查 ──
        if not self.content_safety.check(query):
            logger.warning(
                f"内容安全检查不通过: user_id={user_id}, ip={client_ip}, "
                f"query={query[:100]}"
            )
            self._log_audit(
                user_id, client_ip, "block_query", "message", "",
                f"敏感内容: {query[:100]}"
            )
            yield {"status": "error", "error": "内容包含敏感信息，请修改后重试"}
            return

        # ── 2. 立即通知前端"正在检索"，让用户看到即时反馈 ──
        now = datetime.now(timezone.utc).isoformat()
        yield {"status": "searching"}

        # ── 3. 保存用户消息 ──
        user_msg_doc = {
            "session_id": session_id,
            "role": "user",
            "content": query,
            "content_type": "text",
            "tokens": 0,
            "status": 1,
            "created_at": now,
        }
        user_msg_result = await self.db.messages.insert_one(user_msg_doc)
        user_msg_id = str(user_msg_result.inserted_id)

        # ── 3. 更新会话消息计数 ──
        try:
            session_oid = ObjectId(session_id)
            await self.db.sessions.update_one(
                {"_id": session_oid},
                {
                    "$inc": {"msg_count": 1},
                    "$set": {"updated_at": now},
                },
            )
        except Exception as e:
            logger.warning(f"更新会话消息计数失败: {e}")

        # ── 4. RAGFlow 检索 ──
        search_results: List[dict] = []
        try:
            search_results = await self.ragflow_client.search(
                query=query,
            )
            logger.info(
                f"RAGFlow 检索完成: session_id={session_id}, "
                f"结果数={len(search_results)}"
            )
        except Exception as e:
            logger.warning(f"RAGFlow 检索异常，继续使用空结果: {e}")

        # ── 5. 获取历史消息 ──
        history_messages: List[dict] = []
        try:
            cursor = (
                self.db.messages.find({"session_id": session_id, "status": 1})
                .sort("created_at", -1)
                .limit(10)
            )
            async for msg in cursor:
                history_messages.append({
                    "role": msg.get("role", ""),
                    "content": msg.get("content", ""),
                })
            # 因为按时间倒序取，需要反转
            history_messages.reverse()
        except Exception as e:
            logger.warning(f"获取历史消息失败: {e}")

        # ── 6. 构建上下文 ──
        legal_context = self.context_builder.build_context(
            user_query=query,
            history_messages=history_messages,
            search_results=search_results,
        )
        system_prompt = self.safety_filter.system_prompt()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": legal_context},
        ]

        # ── 7. 流式 LLM 生成 ──
        full_content = ""
        index = 0
        stream_error = False

        try:
            async for token in self.llm_service.generate_stream(messages):
                full_content += token
                yield {"status": "generating", "content": token, "index": index}
                index += 1
        except Exception as e:
            logger.error(f"LLM 流式生成失败: {e}")
            stream_error = True
            fallback = self.safety_filter.get_fallback_message()
            full_content = fallback
            yield {"status": "generating", "content": fallback, "index": 0}

        # ── 9. 后处理 ──
        if not full_content:
            full_content = self.safety_filter.get_fallback_message()

        # ── 10. 保存 AI 消息 ──
        now = datetime.now(timezone.utc).isoformat()
        ai_msg_doc = {
            "session_id": session_id,
            "role": "assistant",
            "content": full_content,
            "content_type": "markdown",
            "tokens": len(full_content),
            "status": 1,
            "created_at": now,
        }
        ai_msg_result = await self.db.messages.insert_one(ai_msg_doc)
        ai_msg_id = str(ai_msg_result.inserted_id)

        # ── 11. 保存法条引用 ──
        law_refs = []
        if search_results:
            ref_docs = []
            for r in search_results:
                law_ref = {
                    "name": r.get("law_name", ""),
                    "article": r.get("article_num", ""),
                    "text": r.get("law_text", ""),
                    "source": r.get("source", ""),
                    "chunk_id": r.get("chunk_id", ""),
                    "relevance": r.get("relevance", 0),
                }
                law_refs.append(law_ref)

                # 准备入库文档
                ref_docs.append({
                    "message_id": ai_msg_id,
                    "law_name": r.get("law_name", ""),
                    "article_num": r.get("article_num", ""),
                    "law_text": r.get("law_text", ""),
                    "source": r.get("source", ""),
                    "chunk_id": r.get("chunk_id", ""),
                    "relevance": r.get("relevance", 0),
                    "created_at": now,
                })

            if ref_docs:
                await self.db.law_refs.insert_many(ref_docs)

        # ── 12. 记录 Token 用量 ──
        input_tokens = len(query) + len(legal_context)  # 粗略估算
        output_tokens = len(full_content)
        try:
            await self.db.token_usage.insert_one({
                "user_id": user_id,
                "session_id": session_id,
                "message_id": ai_msg_id,
                "model": self.llm_service.model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "created_at": now,
            })
        except Exception as e:
            logger.warning(f"记录 Token 用量失败: {e}")

        # ── 13. 审计日志 ──
        self._log_audit(
            user_id, client_ip, "send_message", "session",
            session_id, f"查询: {query[:100]}"
        )

        # ── 14. Yield "done" ──
        yield {
            "done": True,
            "status": "done",
            "message_id": ai_msg_id,
            "laws": law_refs,
            "tokens": {
                "input": input_tokens,
                "output": output_tokens,
            },
        }

    # ═══════════════════════════════════════
    # 获取消息列表
    # ═══════════════════════════════════════

    async def get_messages(
        self,
        session_id: str,
        offset: int = 0,
        limit: int = 50,
    ) -> Tuple[List[dict], int]:
        """
        获取会话的消息列表

        Args:
            session_id: 会话ID（字符串）
            offset: 偏移量
            limit: 返回条数

        Returns:
            (消息列表, 总数)
        """
        query = {"session_id": session_id, "status": 1}
        total = await self.db.messages.count_documents(query)

        cursor = (
            self.db.messages.find(query)
            .sort("created_at", 1)
            .skip(offset)
            .limit(limit)
        )

        messages = []
        async for msg in cursor:
            msg_data = {
                "id": str(msg["_id"]),
                "session_id": msg.get("session_id", ""),
                "role": msg.get("role", ""),
                "content": msg.get("content", ""),
                "content_type": msg.get("content_type", "text"),
                "tokens": msg.get("tokens", 0),
                "created_at": msg.get("created_at", ""),
            }

            # 加载法条引用
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

        return messages, total

    # ═══════════════════════════════════════
    # 导出消息
    # ═══════════════════════════════════════

    async def export_messages(self, session_id: str) -> str:
        """
        导出会话消息为文本格式

        Args:
            session_id: 会话ID（字符串）

        Returns:
            纯文本格式的对话记录
            角色标签：用户 / AI法律助手
        """
        messages, _ = await self.get_messages(session_id, 0, 200)

        lines = []
        for msg in messages:
            role = "用户" if msg["role"] == "user" else "AI法律助手"
            time_str = msg.get("created_at", "")
            lines.append(f"【{role}】{time_str}")
            lines.append(msg.get("content", ""))
            lines.append("")  # 空行分隔

        return "\n".join(lines)

    # ═══════════════════════════════════════
    # 审计日志（内部方法）
    # ═══════════════════════════════════════

    def _log_audit(
        self,
        user_id: str,
        ip: str,
        action: str,
        target_type: str,
        target_id: str,
        detail: str,
    ):
        """
        记录审计日志（非阻塞，fire-and-forget）

        Args:
            user_id: 用户ID（字符串）
            ip: 客户端IP
            action: 操作类型
            target_type: 目标类型 (message / session / user)
            target_id: 目标ID
            detail: 详细信息
        """
        import asyncio

        async def _insert():
            try:
                await self.db.audit_logs.insert_one({
                    "user_id": user_id,
                    "action": action,
                    "target_type": target_type,
                    "target_id": target_id,
                    "detail": detail,
                    "ip": ip,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })
            except Exception as e:
                logger.warning(f"审计日志写入失败: {e}")

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_insert())
        except RuntimeError:
            pass
