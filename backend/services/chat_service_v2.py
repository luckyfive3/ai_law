"""
AI法律助手 v1.0 — 升级版聊天服务（LangChain 增强）
集成 RAGFlowRetriever、LegalRAGChain、CallbackHandler
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import AsyncGenerator, List, Tuple, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from services.ragflow_client import RAGFlowClient
from services.llm_service_v2 import LLMService
from services.rag_chain import LegalRAGChain
from services.langchain_retriever import RAGFlowRetriever, format_docs
from services.langchain_callbacks import LegalAICallbackHandler
from services.safety_filter import SafetyFilter
from services.prompts import build_legal_consult_prompt

logger = logging.getLogger(__name__)


class ContentSafetyCheck:
    """简单的内容安全检查器"""
    def __init__(self, enable: bool = True):
        self.enable = enable

    def check(self, text: str) -> bool:
        return True  # 部署时加载敏感词库


class ChatService:
    """
    升级版聊天服务

    相比 v1 的改进：
        1. 使用 LegalRAGChain（LCEL 链）替代手动编排
        2. 集成 LegalAICallbackHandler 自动 Token 统计和监控
        3. 使用 RAGFlowRetriever（LangChain 标准接口）替代直接 HTTP 调用
        4. 使用 ChatPromptTemplate 替代字符串拼接
    """

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        ragflow_client: RAGFlowClient,
        llm_service: LLMService,
        safety_filter: SafetyFilter,
        content_safety: ContentSafetyCheck,
    ):
        self.db = db
        self.ragflow_client = ragflow_client
        self.llm_service = llm_service
        self.safety_filter = safety_filter
        self.content_safety = content_safety

        # ── LangChain 增强组件 ──
        # 1. Retriever（封装 RAGFlow）
        self._retriever = RAGFlowRetriever(ragflow_client=ragflow_client, top_k=5)

        # 2. Prompt 模板（结构化）
        self._prompt = build_legal_consult_prompt()

    def _create_callback_handler(
        self, session_id: str, user_id: str
    ) -> LegalAICallbackHandler:
        """为每次请求创建独立的回调处理器"""
        return LegalAICallbackHandler(
            session_id=session_id,
            user_id=user_id,
            db=self.db,
        )

    # ═══════════════════════════════════════
    # 方法 A：使用 LegalRAGChain（推荐 - LCEL）
    # ═══════════════════════════════════════

    async def send_message_with_chain(
        self,
        user_id: str,
        session_id: str,
        query: str,
        category: str = "",
        client_ip: str = "",
    ) -> AsyncGenerator[dict, None]:
        """
        SSE 流式对话（使用 LCEL RAG Chain）

        核心链路：
            用户提问 → RAGFlow检索 → 格式化 → Prompt → LLM → SSE推送
        """
        # 1. 安全检查
        if not self.content_safety.check(query):
            yield {"status": "error", "error": "内容包含敏感信息，请修改后重试"}
            return

        # 2. 保存用户消息
        now = datetime.now(timezone.utc).isoformat()
        user_msg_result = await self.db.messages.insert_one({
            "session_id": session_id,
            "role": "user",
            "content": query,
            "content_type": "text",
            "tokens": 0,
            "status": 1,
            "created_at": now,
        })

        # 3. 更新会话计数
        try:
            await self.db.sessions.update_one(
                {"_id": ObjectId(session_id)},
                {"$inc": {"msg_count": 1}, "$set": {"updated_at": now}},
            )
        except Exception:
            pass

        # 4. 获取历史消息（转换为 LangChain 格式）
        history_messages = await self._get_history(session_id)
        langchain_history = LegalRAGChain.dict_to_langchain_messages(history_messages)

        # 5. 创建回调处理器
        callback = self._create_callback_handler(session_id, user_id)

        # 6. 创建 LLM 实例（带回调）
        from langchain_openai import ChatOpenAI
        llm_with_callback = ChatOpenAI(
            model=self.llm_service.model,
            base_url=self.llm_service.settings.llm_base_url,
            api_key=self.llm_service.settings.llm_api_key,
            temperature=self.llm_service.temperature,
            max_tokens=self.llm_service.max_tokens,
            timeout=self.llm_service.timeout,
            max_retries=self.llm_service.max_retries,
            callbacks=[callback],
        )

        # 7. 创建 RAG Chain
        chain = LegalRAGChain(llm=llm_with_callback, retriever=self._retriever)

        # 8. 流式生成
        full_content = ""
        index = 0

        yield {"status": "searching", "index": 0}

        try:
            async for token in chain.astream(
                question=query,
                history=langchain_history,
            ):
                full_content += token
                yield {"status": "generating", "content": token, "index": index}
                index += 1
        except Exception as e:
            logger.error(f"RAG Chain 生成失败: {e}")
            fallback = self.safety_filter.get_fallback_message()
            full_content = fallback
            yield {"status": "generating", "content": fallback, "index": 0}

        # 9. 附加免责声明
        full_content = self.safety_filter.append_disclaimer(full_content) if full_content else ""

        # 10. 保存 AI 消息
        now = datetime.now(timezone.utc).isoformat()
        ai_msg_result = await self.db.messages.insert_one({
            "session_id": session_id,
            "role": "assistant",
            "content": full_content,
            "content_type": "markdown",
            "tokens": len(full_content),
            "status": 1,
            "created_at": now,
        })
        ai_msg_id = str(ai_msg_result.inserted_id)

        # 11. 输出统计信息（来自回调）
        stats = callback.get_stats()

        yield {
            "done": True,
            "status": "done",
            "message_id": ai_msg_id,
            "tokens": {
                "input": stats["total_input_tokens"],
                "output": stats["total_output_tokens"],
            },
            "stats": stats,
        }

    # ═══════════════════════════════════════
    # 方法 B：使用结构化 Prompt + LangChain 消息（兼容方案）
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
        SSE 流式对话（使用结构化 Prompt 模板，兼容原有链路）

        相比 v1：使用 ChatPromptTemplate.invoke() 替代 ContextBuilder.build_context()
        """
        # 1. 安全检查
        if not self.content_safety.check(query):
            self._log_audit(user_id, client_ip, "block_query", "message", "", f"敏感内容: {query[:100]}")
            yield {"status": "error", "error": "内容包含敏感信息，请修改后重试"}
            return

        # 2. 保存用户消息
        now = datetime.now(timezone.utc).isoformat()
        await self.db.messages.insert_one({
            "session_id": session_id,
            "role": "user",
            "content": query,
            "content_type": "text",
            "tokens": 0,
            "status": 1,
            "created_at": now,
        })

        # 3. 更新会话
        try:
            await self.db.sessions.update_one(
                {"_id": ObjectId(session_id)},
                {"$inc": {"msg_count": 1}, "$set": {"updated_at": now}},
            )
        except Exception:
            pass

        # 4. 检索法条 → 使用 Retriever 转为 LangChain Document
        law_docs = await self._retriever._aget_relevant_documents(query)
        legal_context = format_docs(law_docs)

        # 5. 获取历史消息 → 转为 LangChain 消息
        history_dicts = await self._get_history(session_id)
        history_msgs = LegalRAGChain.dict_to_langchain_messages(history_dicts)

        # 6. 使用 ChatPromptTemplate 构建消息列表
        messages = self._prompt.invoke({
            "legal_context": legal_context,
            "history": history_msgs,
            "question": query,
        }).to_messages()

        # 7. 流式生成
        yield {"status": "searching", "index": 0}

        full_content = ""
        index = 0

        try:
            async for token in self.llm_service.generate_stream(
                [{"role": "system", "content": msg.content} if msg.type == "system"
                 else {"role": "assistant", "content": msg.content} if msg.type == "ai"
                 else {"role": "user", "content": msg.content}
                 for msg in messages]
            ):
                full_content += token
                yield {"status": "generating", "content": token, "index": index}
                index += 1
        except Exception as e:
            logger.error(f"LLM 生成失败: {e}")
            fallback = self.safety_filter.get_fallback_message()
            full_content = fallback
            yield {"status": "generating", "content": fallback, "index": 0}

        # 8. 后处理
        full_content = self.safety_filter.append_disclaimer(full_content) if full_content else ""

        # 9. 保存 AI 消息
        now = datetime.now(timezone.utc).isoformat()
        ai_msg_result = await self.db.messages.insert_one({
            "session_id": session_id,
            "role": "assistant",
            "content": full_content,
            "content_type": "markdown",
            "tokens": len(full_content),
            "status": 1,
            "created_at": now,
        })
        ai_msg_id = str(ai_msg_result.inserted_id)

        # 10. 保存法条引用
        law_refs = []
        if law_docs:
            ref_docs = []
            for doc in law_docs:
                meta = doc.metadata
                law_ref = {
                    "name": meta.get("law_name", ""),
                    "article": meta.get("article_num", ""),
                    "text": doc.page_content,
                    "source": meta.get("source", ""),
                    "chunk_id": meta.get("chunk_id", ""),
                    "relevance": meta.get("relevance", 0),
                }
                law_refs.append(law_ref)
                ref_docs.append({
                    **law_ref,
                    "message_id": ai_msg_id,
                    "created_at": now,
                })

            if ref_docs:
                await self.db.law_refs.insert_many(ref_docs)

        # 11. 审计
        self._log_audit(user_id, client_ip, "send_message", "session", session_id, f"查询: {query[:100]}")

        # 12. 完成
        yield {
            "done": True,
            "status": "done",
            "message_id": ai_msg_id,
            "laws": law_refs,
            "tokens": {"input": len(query) + len(legal_context), "output": len(full_content)},
        }

    # ═══════════════════════════════════════
    # 辅助方法
    # ═══════════════════════════════════════

    async def _get_history(self, session_id: str, limit: int = 10) -> List[dict]:
        """获取会话历史消息（最近 N 条）"""
        messages = []
        try:
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
        except Exception as e:
            logger.warning(f"获取历史消息失败: {e}")
        return messages

    async def get_messages(self, session_id: str, offset: int = 0, limit: int = 50) -> Tuple[List[dict], int]:
        """获取消息列表"""
        query_filter = {"session_id": session_id, "status": 1}
        total = await self.db.messages.count_documents(query_filter)

        cursor = self.db.messages.find(query_filter).sort("created_at", 1).skip(offset).limit(limit)
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

            if msg.get("role") == "assistant":
                refs = []
                async for ref in self.db.law_refs.find({"message_id": str(msg["_id"])}):
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

    async def export_messages(self, session_id: str) -> str:
        """导出消息"""
        messages, _ = await self.get_messages(session_id, 0, 200)
        lines = []
        for msg in messages:
            role = "用户" if msg["role"] == "user" else "AI法律助手"
            time_str = msg.get("created_at", "")
            lines.append(f"【{role}】{time_str}")
            lines.append(msg.get("content", ""))
            lines.append("")
        return "\n".join(lines)

    def _log_audit(self, user_id, ip, action, target_type, target_id, detail):
        """审计日志（非阻塞）"""
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
