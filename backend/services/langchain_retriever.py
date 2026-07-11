"""
AI法律助手 v1.0 — LangChain Retriever 封装
将 RAGFlow HTTP API 包装为 LangChain 标准的 BaseRetriever 接口
"""
from __future__ import annotations

import logging
from typing import List

from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from langchain_core.callbacks import CallbackManagerForRetrieverRun

from services.ragflow_client import RAGFlowClient

logger = logging.getLogger(__name__)


class RAGFlowRetriever(BaseRetriever):
    """
    LangChain 标准 Retriever，封装 RAGFlow 检索能力

    使用示例：
        retriever = RAGFlowRetriever(ragflow_client=client, top_k=5)
        docs = retriever.invoke("劳动合同纠纷怎么处理？")

    返回的 Document 对象可直接传给 LangChain Chain 或作为上下文拼接。
    """

    ragflow_client: RAGFlowClient
    top_k: int = 5

    class Config:
        arbitrary_types_allowed = True

    def _get_relevant_documents(self, query: str, *, dataset_id: str = None, run_manager: CallbackManagerForRetrieverRun | None = None,
    ) -> List[Document]:
        """
        同步检索（由 BaseRetriever 框架调用）

        实际上 internal 走的是异步 httpx，因此这个方法内部使用
        asyncio 跑异步检索并等待结果。
        """
        import asyncio

        async def _retrieve():
            return await self.ragflow_client.search(query=query, top_k=self.top_k, dataset_id=dataset_id)

        try:
            # 如果在事件循环中，创建 future；否则 run_until_complete
            loop = asyncio.get_running_loop()
            # 已有事件循环，需要在新线程中跑
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    _retrieve()
                )
                raw_results = future.result(timeout=15)
        except RuntimeError:
            raw_results = asyncio.run(_retrieve())

        return self._raw_to_documents(raw_results)

    async def _aget_relevant_documents(self, query: str, *, dataset_id: str = None, run_manager: CallbackManagerForRetrieverRun | None = None,
    ) -> List[Document]:
        """异步检索"""
        raw_results = await self.ragflow_client.search(query=query, top_k=self.top_k, dataset_id=dataset_id)
        return self._raw_to_documents(raw_results)

    def _raw_to_documents(self, raw_results: List[dict]) -> List[Document]:
        """将 RAGFlow 原始结果转为 LangChain Document 列表"""
        documents = []
        for r in raw_results:
            law_name = r.get("law_name", "未知法律")
            article_num = r.get("article_num", "")
            law_text = r.get("law_text", "")

            # page_content: 法条的完整文本（用于检索和展示）
            page_content = f"《{law_name}》{article_num}\n{law_text}" if article_num else law_text

            doc = Document(
                page_content=page_content,
                metadata={
                    "law_name": law_name,
                    "article_num": article_num,
                    "source": r.get("source", ""),
                    "chunk_id": r.get("chunk_id", ""),
                    "relevance": r.get("relevance", 0),
                },
            )
            documents.append(doc)

        logger.info(f"RAGFlowRetriever: 检索到 {len(documents)} 个文档")
        return documents


# ═══════════════════════════════════════
# 辅助函数：将 Document 列表格式化为 LLM 上下文
# ═══════════════════════════════════════

def format_docs(docs: List[Document]) -> str:
    """
    将检索到的文档列表格式化为 Prompt 中可用的法律依据文本

    这是 RAG 链路中 "检索后格式化" 的标准做法。
    使用 LangChain 的函数式 Runnable 可以直接作为链的一环。

    Args:
        docs: 检索返回的 Document 列表

    Returns:
        格式化后的法律依据上下文字符串
    """
    if not docs:
        return "（未检索到相关法条，请基于通用法律知识回答，并提示用户建议咨询专业律师）"

    lines = []
    for i, doc in enumerate(docs, start=1):
        meta = doc.metadata
        law_name = meta.get("law_name", "未知法律")
        article_num = meta.get("article_num", "")
        relevance = meta.get("relevance", 0)

        header = f"{i}. 《{law_name}》{article_num}" if article_num else f"{i}. 《{law_name}》"
        header += f"（相关度: {relevance:.2f}）"
        lines.append(header)
        lines.append(f"   原文：{doc.page_content}")

    return "\n".join(lines)
