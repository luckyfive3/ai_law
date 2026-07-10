"""
AI法律助手 v1.0 — LangChain Callback 处理器
拦截 LLM 调用全链路事件，实现自动化监控和 Token 统计
"""
from __future__ import annotations

import time
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

logger = logging.getLogger(__name__)


class LegalAICallbackHandler(BaseCallbackHandler):
    """
    法律AI助手的 LangChain 回调处理器

    功能：
        1. Token 消耗自动统计（按会话/用户维度记录）
        2. LLM 调用延迟监控（P50/P95/P99）
        3. 检索耗时追踪
        4. 异常检测与告警

    用法：
        handler = LegalAICallbackHandler(session_id="xxx", user_id="yyy")
        llm = ChatOpenAI(callbacks=[handler], ...)
    """

    def __init__(
        self,
        session_id: str = "",
        user_id: str = "",
        db: Any = None,  # Optional AsyncIOMotorDatabase
    ):
        super().__init__()
        self.session_id = session_id
        self.user_id = user_id
        self.db = db

        # 统计计数器
        self._llm_start_time: float = 0
        self._retriever_start_time: float = 0
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self.llm_call_count: int = 0
        self.retrieval_count: int = 0
        self.llm_latencies: List[float] = []
        self.errors: List[str] = []

    # ═══════════════════════════════════════
    # LLM 事件
    # ═══════════════════════════════════════

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        self._llm_start_time = time.time()
        self.llm_call_count += 1
        logger.debug(
            f"[LLM Start] session={self.session_id}, "
            f"prompt_chars={sum(len(p) for p in prompts)}, "
            f"call_count={self.llm_call_count}"
        )

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        latency = time.time() - self._llm_start_time
        self.llm_latencies.append(latency)

        # 提取 Token 使用量
        if response.llm_output and "token_usage" in response.llm_output:
            usage = response.llm_output["token_usage"]
            self.total_input_tokens += usage.get("prompt_tokens", 0)
            self.total_output_tokens += usage.get("completion_tokens", 0)

        logger.info(
            f"[LLM End] session={self.session_id}, "
            f"latency={latency:.2f}s, "
            f"input_tokens={self.total_input_tokens}, "
            f"output_tokens={self.total_output_tokens}"
        )

        # 异步写入 MongoDB Token 用量记录
        if self.db and self.session_id:
            self._save_token_usage()

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        error_msg = f"LLM Error: {type(error).__name__}: {error}"
        self.errors.append(error_msg)
        logger.error(f"[{self.session_id}] {error_msg}")

    # ═══════════════════════════════════════
    # Retriever 事件
    # ═══════════════════════════════════════

    def on_retriever_start(
        self,
        serialized: Dict[str, Any],
        query: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        self._retriever_start_time = time.time()
        self.retrieval_count += 1
        logger.debug(
            f"[Retriever Start] session={self.session_id}, "
            f"query='{query[:80]}...'"
        )

    def on_retriever_end(
        self,
        documents: List[Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        latency = time.time() - self._retriever_start_time
        logger.info(
            f"[Retriever End] session={self.session_id}, "
            f"docs_count={len(documents)}, "
            f"latency={latency:.2f}s"
        )

    def on_retriever_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        error_msg = f"Retriever Error: {type(error).__name__}: {error}"
        self.errors.append(error_msg)
        logger.error(f"[{self.session_id}] {error_msg}")

    # ═══════════════════════════════════════
    # Chain 事件
    # ═══════════════════════════════════════

    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        logger.debug(
            f"[Chain Start] session={self.session_id}, "
            f"run_id={run_id}"
        )

    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        logger.debug(
            f"[Chain End] session={self.session_id}, "
            f"run_id={run_id}"
        )

    def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        error_msg = f"Chain Error: {type(error).__name__}: {error}"
        self.errors.append(error_msg)
        logger.error(f"[{self.session_id}] {error_msg}")

    # ═══════════════════════════════════════
    # 内部方法
    # ═══════════════════════════════════════

    def _save_token_usage(self):
        """异步保存 Token 用量到 MongoDB（非阻塞）"""
        import asyncio
        from datetime import datetime, timezone

        async def _save():
            if not self.db:
                return
            try:
                await self.db.token_usage.insert_one({
                    "user_id": self.user_id,
                    "session_id": self.session_id,
                    "input_tokens": self.total_input_tokens,
                    "output_tokens": self.total_output_tokens,
                    "llm_call_count": self.llm_call_count,
                    "retrieval_count": self.retrieval_count,
                    "avg_latency": (
                        sum(self.llm_latencies) / len(self.llm_latencies)
                        if self.llm_latencies else 0
                    ),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })
            except Exception as e:
                logger.warning(f"保存 Token 用量失败: {e}")

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_save())
        except RuntimeError:
            pass

    def get_stats(self) -> Dict[str, Any]:
        """返回当前回调统计摘要"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "llm_call_count": self.llm_call_count,
            "retrieval_count": self.retrieval_count,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "avg_latency": (
                sum(self.llm_latencies) / len(self.llm_latencies)
                if self.llm_latencies else 0
            ),
            "error_count": len(self.errors),
        }

    def reset(self):
        """重置所有计数器"""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.llm_call_count = 0
        self.retrieval_count = 0
        self.llm_latencies.clear()
        self.errors.clear()
