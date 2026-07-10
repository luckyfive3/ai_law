"""
AI法律助手 v1.0 — LCEL RAG 对话链
用 LangChain 表达式语言（LCEL）声明式组织整个 RAG 流水线

核心链路：
    用户提问 → 检索法条 → 格式化上下文 → 填充 Prompt → LLM 生成 → 解析输出
"""
from __future__ import annotations

import logging
from operator import itemgetter
from typing import List, Dict, Any, Optional, AsyncGenerator

from langchain_core.runnables import RunnablePassthrough, RunnableLambda, RunnableParallel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from services.prompts import build_legal_consult_prompt
from services.langchain_retriever import RAGFlowRetriever, format_docs

logger = logging.getLogger(__name__)


class LegalRAGChain:
    """
    法律 RAG 对话链（基于 LCEL）

    将所有步骤声明为一个可执行链：
        检索 → 格式化 → 填充 Prompt → LLM → 输出

    用法：
        chain = LegalRAGChain(llm=llm, retriever=retriever)
        result = await chain.ainvoke("劳动合同纠纷怎么处理？", history=history_msgs)
    """

    def __init__(
        self,
        llm: ChatOpenAI,
        retriever: RAGFlowRetriever,
    ):
        self.llm = llm
        self.retriever = retriever
        self.prompt = build_legal_consult_prompt()

        # ── 构建 LCEL 链 ──
        self._chain = self._build_chain()
        # 流式专用链：输出为逐个 token
        self._stream_chain = self._build_stream_chain()

    def _build_chain(self):
        """
        构建完整的 RAG 链（非流式）

        数据流向：
            {
                "question": "用户问题",
                "legal_context": "检索+格式化后的法条文本",
                "history": [历史 BaseMessage 列表],
            }
            → ChatPromptTemplate
            → ChatOpenAI
            → StrOutputParser
        """
        # 检索 → 格式化 子链
        retrieval_chain = (
            RunnableLambda(lambda q: q["question"])
            | self.retriever
            | format_docs
        )

        # 主链：并行获取上下文 + 保留原输入
        full_chain = (
            RunnableParallel(
                question=itemgetter("question"),
                legal_context=retrieval_chain,
                history=itemgetter("history"),
            )
            | self.prompt
            | self.llm
            | StrOutputParser()
        )

        return full_chain

    def _build_stream_chain(self):
        """构建流式 RAG 链（同结构，但通过 astream 获取 token）"""
        retrieval_chain = (
            RunnableLambda(lambda q: q["question"])
            | self.retriever
            | format_docs
        )

        full_chain = (
            RunnableParallel(
                question=itemgetter("question"),
                legal_context=retrieval_chain,
                history=itemgetter("history"),
            )
            | self.prompt
            | self.llm
            | StrOutputParser()
        )

        return full_chain

    # ═══════════════════════════════════════
    # 公共 API
    # ═══════════════════════════════════════

    async def ainvoke(
        self,
        question: str,
        history: Optional[List[BaseMessage]] = None,
    ) -> str:
        """
        非流式调用：输入问题，返回完整回答

        Args:
            question: 用户问题
            history:  历史对话消息列表

        Returns:
            LLM 生成的完整回答文本
        """
        if history is None:
            history = []

        result = await self._chain.ainvoke({
            "question": question,
            "history": history,
        })
        return result

    async def astream(
        self,
        question: str,
        history: Optional[List[BaseMessage]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        流式调用：逐 token 返回回答

        Args:
            question: 用户问题
            history:  历史对话消息列表

        Yields:
            逐个 token 字符串
        """
        if history is None:
            history = []

        async for chunk in self._stream_chain.astream({
            "question": question,
            "history": history,
        }):
            yield chunk

    # ═══════════════════════════════════════
    # 工具方法
    # ═══════════════════════════════════════

    @staticmethod
    def dict_to_langchain_messages(
        messages: List[Dict[str, str]]
    ) -> List[BaseMessage]:
        """
        将数据库读取的字典列表转换为 LangChain BaseMessage 列表

        Args:
            messages: [{"role": "user", "content": "..."}, ...]

        Returns:
            [HumanMessage(...), AIMessage(...), ...]
        """
        converted: List[BaseMessage] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                converted.append(SystemMessage(content=content))
            elif role == "assistant":
                converted.append(AIMessage(content=content))
            else:
                converted.append(HumanMessage(content=content))
        return converted
