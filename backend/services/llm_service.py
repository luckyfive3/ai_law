"""
AI法律助手 v1.0 — LangChain LLM 服务
基于 DeepSeek 模型，提供非流式和流式生成能力
"""
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator, List

from langchain_openai import ChatOpenAI
from langchain.schema import AIMessage, HumanMessage, SystemMessage, BaseMessage
from config import Settings

logger = logging.getLogger(__name__)


class LLMService:
    """
    LLM 服务封装
    使用 LangChain ChatOpenAI 调用 DeepSeek API
    """

    def __init__(self, settings: Settings):
        """
        初始化 LLM 服务

        Args:
            settings: 应用配置实例
        """
        self.settings = settings
        self.model = settings.llm_model
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens
        self.timeout = settings.llm_timeout
        self.max_retries = settings.llm_max_retries

        # 创建 ChatOpenAI 实例
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
            )
            logger.info(
                f"LLM 初始化成功: model={self.model}, "
                f"base_url={self.settings.llm_base_url}"
            )
        except Exception as e:
            logger.error(f"LLM 初始化失败: {e}")
            self._llm = None

    # ═══════════════════════════════════════
    # 消息转换
    # ═══════════════════════════════════════

    @staticmethod
    def _convert_messages(messages: List[dict]) -> List[BaseMessage]:
        """
        将字典格式的消息列表转换为 LangChain BaseMessage 列表

        Args:
            messages: 字典格式的消息列表，每条含 role 和 content

        Returns:
            LangChain 消息列表
        """
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
        """
        非流式调用 LLM 生成回答

        Args:
            messages: 消息列表，每条含 role 和 content

        Returns:
            LLM 生成的完整回答文本
            如果调用失败，返回兜底消息
        """
        if self._llm is None:
            logger.error("LLM 未初始化，无法生成回答")
            return "抱歉，AI服务暂不可用，请稍后重试。"

        try:
            langchain_messages = self._convert_messages(messages)
            response = await self._llm.ainvoke(langchain_messages)
            content = response.content if hasattr(response, "content") else str(response)

            logger.info(
                f"LLM 非流式生成完成: model={self.model}, "
                f"输出长度={len(content)}"
            )
            return content

        except Exception as e:
            logger.error(f"LLM 非流式调用失败: {type(e).__name__}: {e}")
            return "抱歉，AI服务暂时异常，请稍后重试。如您有紧急法律问题，建议直接咨询执业律师。"

    # ═══════════════════════════════════════
    # 流式生成
    # ═══════════════════════════════════════

    async def generate_stream(
        self, messages: List[dict]
    ) -> AsyncGenerator[str, None]:
        """
        流式调用 LLM 生成回答

        Args:
            messages: 消息列表，每条含 role 和 content

        Yields:
            逐个生成的文本 token

        注意：
            - 如果 LLM 未初始化或调用失败，yield 兜底消息后停止
        """
        if self._llm is None:
            logger.error("LLM 未初始化，无法流式生成回答")
            yield "抱歉，AI服务暂不可用，请稍后重试。"
            return

        try:
            langchain_messages = self._convert_messages(messages)

            # 使用 ainvoke 的流式变体 astream
            token_count = 0
            async for chunk in self._llm.astream(langchain_messages):
                if hasattr(chunk, "content") and chunk.content:
                    token_count += 1
                    yield chunk.content

            logger.info(
                f"LLM 流式生成完成: model={self.model}, "
                f"输出token数={token_count}"
            )

        except Exception as e:
            logger.error(f"LLM 流式调用失败: {type(e).__name__}: {e}")
            yield "抱歉，AI服务暂时异常，请稍后重试。如您有紧急法律问题，建议直接咨询执业律师。"
