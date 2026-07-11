"""
services/langchain_retriever 模块单元测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.documents import Document


class TestFormatDocs:
    """format_docs 格式化函数测试"""

    def test_empty_list(self):
        from services.langchain_retriever import format_docs
        result = format_docs([])
        assert "未检索到相关法条" in result

    def test_single_document_with_article(self):
        from services.langchain_retriever import format_docs
        doc = Document(
            page_content="家庭应当树立优良家风",
            metadata={
                "law_name": "民法典",
                "article_num": "第1043条",
                "relevance": 0.95,
            },
        )
        result = format_docs([doc])
        assert "民法典" in result
        assert "第1043条" in result
        assert "0.95" in result

    def test_multiple_documents(self):
        from services.langchain_retriever import format_docs
        docs = [
            Document(page_content="text1", metadata={"law_name": "民法典", "relevance": 0.9}),
            Document(page_content="text2", metadata={"law_name": "刑法", "relevance": 0.8}),
        ]
        result = format_docs(docs)
        assert "1." in result
        assert "2." in result

    def test_document_without_article(self):
        from services.langchain_retriever import format_docs
        doc = Document(page_content="content", metadata={"law_name": "宪法", "relevance": 0.5})
        result = format_docs([doc])
        assert "《宪法》" in result
        assert "content" in result


class TestRAGFlowRetriever:
    """RAGFlowRetriever 测试"""

    @pytest.fixture
    def mock_ragflow(self):
        from services.ragflow_client import RAGFlowClient
        client = MagicMock(spec=RAGFlowClient)
        client.search = AsyncMock(return_value=[
            {
                "law_name": "民法典",
                "article_num": "第1043条",
                "law_text": "家庭应当树立优良家风",
                "source": "民法典全文",
                "chunk_id": "chunk001",
                "relevance": 0.9,
            },
        ])
        return client

    def test_init_default_top_k(self, mock_ragflow):
        from services.langchain_retriever import RAGFlowRetriever
        retriever = RAGFlowRetriever(ragflow_client=mock_ragflow)
        assert retriever.top_k == 5

    def test_init_custom_top_k(self, mock_ragflow):
        from services.langchain_retriever import RAGFlowRetriever
        retriever = RAGFlowRetriever(ragflow_client=mock_ragflow, top_k=10)
        assert retriever.top_k == 10

    @pytest.mark.asyncio
    async def test_aget_relevant_documents(self, mock_ragflow):
        from services.langchain_retriever import RAGFlowRetriever
        retriever = RAGFlowRetriever(ragflow_client=mock_ragflow, top_k=5)
        docs = await retriever._aget_relevant_documents("民法问题")
        assert len(docs) == 1
        assert isinstance(docs[0], Document)
        assert docs[0].metadata["law_name"] == "民法典"

    def test_get_relevant_documents(self, mock_ragflow):
        from services.langchain_retriever import RAGFlowRetriever
        retriever = RAGFlowRetriever(ragflow_client=mock_ragflow, top_k=5)
        docs = retriever._get_relevant_documents("民法问题")
        assert len(docs) == 1
        assert isinstance(docs[0], Document)

    def test_raw_to_documents(self, mock_ragflow):
        from services.langchain_retriever import RAGFlowRetriever
        retriever = RAGFlowRetriever(ragflow_client=mock_ragflow)
        raw = [{
            "law_name": "劳动法", "article_num": "第1条",
            "law_text": "为了保护劳动者的合法权益",
            "source": "", "chunk_id": "c1", "relevance": 0.85,
        }]
        docs = retriever._raw_to_documents(raw)
        assert len(docs) == 1
        assert "劳动法" in docs[0].page_content
        assert docs[0].metadata["relevance"] == 0.85

    def test_raw_to_documents_no_article(self, mock_ragflow):
        from services.langchain_retriever import RAGFlowRetriever
        retriever = RAGFlowRetriever(ragflow_client=mock_ragflow)
        raw = [{"law_name": "刑法", "article_num": "", "law_text": "test"}]
        docs = retriever._raw_to_documents(raw)
        assert docs[0].page_content == "test"
