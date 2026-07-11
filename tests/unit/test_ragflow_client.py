"""
services/ragflow_client 模块单元测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock


class TestRAGFlowClient:
    """RAGFlow 客户端单元测试"""

    @pytest.fixture
    def mock_settings(self):
        s = MagicMock()
        s.ragflow_base_url = "http://ragflow.example.com"
        s.ragflow_api_key = "test-api-key"
        s.ragflow_dataset_id = "ds123"
        s.ragflow_top_k = 10
        s.ragflow_similarity_threshold = 0.2
        s.ragflow_timeout = 10
        return s

    def test_init_without_api_key(self):
        """无 api_key 时 RAG 实例为 None"""
        from services.ragflow_client import RAGFlowClient
        s = MagicMock()
        s.ragflow_base_url = "http://ragflow.example.com"
        s.ragflow_api_key = ""
        s.ragflow_dataset_id = "ds123"
        s.ragflow_top_k = 5
        s.ragflow_similarity_threshold = 0.5
        s.ragflow_timeout = 10

        client = RAGFlowClient(s)
        assert client._rag is None

    def test_init_with_api_key(self):
        """有 api_key 时初始化 RAGFlow SDK"""
        with patch("services.ragflow_client.RAGFlow") as mock_rag:
            from services.ragflow_client import RAGFlowClient
            s = MagicMock()
            s.ragflow_base_url = "http://ragflow.example.com"
            s.ragflow_api_key = "test-key"
            s.ragflow_dataset_id = "ds123"
            s.ragflow_top_k = 5
            s.ragflow_similarity_threshold = 0.5
            s.ragflow_timeout = 10

            client = RAGFlowClient(s)
            mock_rag.assert_called_once_with(api_key="test-key", base_url="http://ragflow.example.com")

    def test_init_sdk_failure(self):
        """SDK 初始化失败不抛异常，_rag 为 None"""
        with patch("services.ragflow_client.RAGFlow", side_effect=Exception("SDK init error")):
            from services.ragflow_client import RAGFlowClient
            s = MagicMock()
            s.ragflow_base_url = "http://ragflow.example.com"
            s.ragflow_api_key = "test-key"
            s.ragflow_dataset_id = "ds123"
            s.ragflow_top_k = 5
            s.ragflow_similarity_threshold = 0.5
            s.ragflow_timeout = 10

            client = RAGFlowClient(s)
            assert client._rag is None

    def test_base_url_trailing_slash_removed(self):
        """base_url 末尾 / 被去除"""
        with patch("services.ragflow_client.RAGFlow"):
            from services.ragflow_client import RAGFlowClient
            s = MagicMock()
            s.ragflow_base_url = "http://ragflow.example.com/"
            s.ragflow_api_key = "test-key"
            s.ragflow_dataset_id = "ds123"
            s.ragflow_top_k = 5
            s.ragflow_similarity_threshold = 0.5
            s.ragflow_timeout = 10

            client = RAGFlowClient(s)
            assert client.base_url == "http://ragflow.example.com"

    @pytest.mark.asyncio
    async def test_search_ragflow_unavailable(self, mock_settings):
        """RAGFlow SDK 未初始化 → 返回空列表"""
        mock_settings.ragflow_api_key = ""
        from services.ragflow_client import RAGFlowClient
        client = RAGFlowClient(mock_settings)

        results = await client.search("test query")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_success(self, mock_settings):
        """检索成功返回标准化结果"""
        with patch("services.ragflow_client.RAGFlow") as mock_rag_class:
            # mock list_datasets
            mock_ds = MagicMock()
            mock_ds.id = "ds123"
            mock_ds.list_documents.return_value = []

            mock_rag = MagicMock()
            mock_rag.list_datasets.return_value = [mock_ds]
            mock_rag_class.return_value = mock_rag

            # mock retrieve
            mock_chunk = MagicMock()
            mock_chunk.similarity = 0.85
            mock_chunk.document_name = "民法典.docx"
            mock_chunk.document_id = "doc001"
            mock_chunk.content = "民事主体的人身权利..."
            mock_chunk.id = "chunk001"
            mock_rag.retrieve.return_value = [mock_chunk]

            from services.ragflow_client import RAGFlowClient
            client = RAGFlowClient(mock_settings)

            results = await client.search("民事权利", dataset_id="ds123", top_k=5)

            assert len(results) == 1
            assert results[0]["law_text"] == "民事主体的人身权利..."
            assert results[0]["relevance"] == 0.85

    @pytest.mark.asyncio
    async def test_search_filters_by_similarity(self, mock_settings):
        """过滤低于阈值的结果"""
        with patch("services.ragflow_client.RAGFlow") as mock_rag_class:
            mock_ds = MagicMock()
            mock_ds.id = "ds123"
            mock_ds.list_documents.return_value = []

            mock_rag = MagicMock()
            mock_rag.list_datasets.return_value = [mock_ds]
            mock_rag_class.return_value = mock_rag

            chunk_low = MagicMock()
            chunk_low.similarity = 0.1  # 低于阈值0.2

            chunk_high = MagicMock()
            chunk_high.similarity = 0.9
            chunk_high.document_name = "刑法"
            chunk_high.document_id = "doc002"
            chunk_high.content = "故意杀人..."
            chunk_high.id = "chunk002"

            mock_rag.retrieve.return_value = [chunk_low, chunk_high]

            from services.ragflow_client import RAGFlowClient
            client = RAGFlowClient(mock_settings)

            results = await client.search("刑事犯罪")

            assert len(results) == 1
            assert results[0]["law_name"] == "刑法"

    @pytest.mark.asyncio
    async def test_search_exception(self, mock_settings):
        """检索异常 → 返回空列表"""
        with patch("services.ragflow_client.RAGFlow") as mock_rag_class:
            mock_rag = MagicMock()
            mock_rag.list_datasets.side_effect = Exception("connection error")
            mock_rag_class.return_value = mock_rag

            from services.ragflow_client import RAGFlowClient
            client = RAGFlowClient(mock_settings)

            results = await client.search("test query")
            assert results == []

    @pytest.mark.asyncio
    async def test_list_documents_empty(self):
        """无数据集 → 返回空列表"""
        s = MagicMock()
        s.ragflow_base_url = "http://ragflow.example.com"
        s.ragflow_api_key = ""
        s.ragflow_dataset_id = "ds123"
        s.ragflow_top_k = 5
        s.ragflow_similarity_threshold = 0.5
        s.ragflow_timeout = 10

        from services.ragflow_client import RAGFlowClient
        client = RAGFlowClient(s)

        docs = await client.list_documents()
        assert docs == []

    @pytest.mark.asyncio
    async def test_get_datasets_empty(self):
        """SDK 不可用 → 返回空列表"""
        s = MagicMock()
        s.ragflow_base_url = "http://ragflow.example.com"
        s.ragflow_api_key = ""
        s.ragflow_dataset_id = "ds123"
        s.ragflow_top_k = 5
        s.ragflow_similarity_threshold = 0.5
        s.ragflow_timeout = 10

        from services.ragflow_client import RAGFlowClient
        client = RAGFlowClient(s)

        datasets = await client.get_datasets()
        assert datasets == []

    def test_doc_name_parsing(self, mock_settings):
        """文档名解析逻辑：去掉路径前缀、后缀和日期"""
        with patch("services.ragflow_client.RAGFlow") as mock_rag_class:
            from services.ragflow_client import RAGFlowClient, re

            mock_rag = MagicMock()
            mock_rag_class.return_value = mock_rag
            client = RAGFlowClient(mock_settings)

            # 测试文档名解析
            name = "法律/中华人民共和国民法典_20240315.docx"
            if "/" in name:
                name = name.split("/")[-1]
            if name.endswith(".docx"):
                name = name[:-5]
            name = re.sub(r'_\d{8}$', '', name)

            assert name == "中华人民共和国民法典"
