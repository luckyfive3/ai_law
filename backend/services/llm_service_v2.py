"""
AI法律助手 v1.0 — 升级版 LangChain LLM 服务
集成 Callback 监控、结构化输出、LCEL Chain
"""
from __future__ import annotations

import logging
from typing import AsyncGenerator, List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
from config import Settings

logger = logging.getLogger(__name__)


class LLMService:
    """
    升级版 LLM 服务封装

    相比 v1 的改进：
        1. 支持传入 LangChain Callbacks（自动 Token 统计、延迟监控）
        2. 新增结构化生成方法（generate_with_parser）
        3. 保持向后兼容的非流式 generate() 和流式 generate_stream()
    """

    def __init__(
        self,
        settings: Settings,
        callbacks: Optional[List] = None,
    ):
        """
        初始化 LLM 服务

        Args:
            settings:  应用配置实例
            callbacks: LangChain BaseCallbackHandler 列表（监控用）
        """
        self.settings = settings
        self.model = settings.llm_model
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens
        self.timeout = settings.llm_timeout
        self.max_retries = settings.llm_max_retries
        self._callbacks = callbacks or []
        self._llm: ChatOpenAI | None = None
        self._init_llm()

    def _init_llm(self):
        """初始化 LangChain ChatOpenAI 实例"""
        try:
            self._llm = ChatOpenAI(
                model=self.model,
                base_url=self.settings.llm_base_url,
                api_key=self.settings.llm_api_key,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout,
                max_retries=self.max_retries,
                callbacks=self._callbacks,          # ← 注入回调
                verbose=False,
            )
            logger.info(
                f"LLM 初始化成功: model={self.model}, "
                f"base_url={self.settings.llm_base_url}"
            )
        except Exception as e:
            logger.error(f"LLM 初始化失败: {e}")
            self._llm = None

    def get_llm(self) -> Optional[ChatOpenAI]:
        """获取底层 ChatOpenAI 实例（供 LegalRAGChain 等使用）"""
        return self._llm

    def get_callbacks(self) -> List:
        """获取回调列表"""
        return self._callbacks

    # ═══════════════════════════════════════
    # 消息转换
    # ═══════════════════════════════════════

    @staticmethod
    def _convert_messages(messages: List[dict]) -> List[BaseMessage]:
        """字典 → LangChain 消息列表"""
        converted: List[BaseMessage] = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                converted.append(SystemMessage(content=content))
            elif role == "assistant":
                converted.append(AIMessage(content=content))
            else:
                converted.append(HumanMessage(content=content))
        return converted

    # ═══════════════════════════════════════
    # 非流式生成
    # ═══════════════════════════════════════

    async def generate(self, messages: List[dict]) -> str:
        """非流式调用（保持向后兼容）"""
        if self._llm is None:
            logger.error("LLM 未初始化")
            return "抱歉，AI服务暂不可用，请稍后重试。"

        try:
            langchain_messages = self._convert_messages(messages)
            response = await self._llm.ainvoke(langchain_messages)
            content = response.content if hasattr(response, "content") else str(response)
            logger.info(f"LLM 生成完成: 输出长度={len(content)}")
            return content
        except Exception as e:
            logger.error(f"LLM 调用失败: {type(e).__name__}: {e}")
            return "抱歉，AI服务暂时异常，请稍后重试。如您有紧急法律问题，建议直接咨询执业律师。"

    # ═══════════════════════════════════════
    # 流式生成
    # ═══════════════════════════════════════

    async def generate_stream(
        self, messages: List[dict]
    ) -> AsyncGenerator[str, None]:
        """流式调用（保持向后兼容）"""
        if self._llm is None:
            yield "抱歉，AI服务暂不可用，请稍后重试。"
            return

        try:
            langchain_messages = self._convert_messages(messages)
            token_count = 0
            async for chunk in self._llm.astream(langchain_messages):
                if hasattr(chunk, "content") and chunk.content:
                    token_count += 1
                    yield chunk.content
            logger.info(f"LLM 流式完成: token数={token_count}")
        except Exception as e:
            logger.error(f"LLM 流式调用失败: {type(e).__name__}: {e}")
            yield "抱歉，AI服务暂时异常，请稍后重试。如您有紧急法律问题，建议直接咨询执业律师。"

    # ═══════════════════════════════════════
    # 新增：结构化生成
    # ═══════════════════════════════════════

    async def generate_structured(
        self,
        messages: List[dict],
        output_parser,
    ):
        """
        生成结构化输出（新增方法）

        Args:
            messages:      消息列表
            output_parser: LangChain OutputParser 实例（如 PydanticOutputParser）

        Returns:
            解析后的 Pydantic 对象，失败返回 None

        用法：
            from services.output_parser import legal_analysis_parser
            result = await llm_service.generate_structured(messages, legal_analysis_parser)
        """
        if self._llm is None:
            logger.error("LLM 未初始化")
            return None

        try:
            langchain_messages = self._convert_messages(messages)

            # 链式调用：LLM → 输出解析器
            chain = self._llm | output_parser
            result = await chain.ainvoke(langchain_messages)

            logger.info(f"结构化生成完成: type={type(result).__name__}")
            return result
        except Exception as e:
            logger.error(f"结构化生成失败: {type(e).__name__}: {e}")
            return None
