"""
services/knowledge_service 模块单元测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from services.knowledge_service import KnowledgeService


class TestKnowledgeService:
    """知识库服务单元测试"""

    @pytest.fixture
    def mock_ragflow(self):
        client = MagicMock()
        client.list_documents = AsyncMock()
        client.search = AsyncMock()
        client.get_document_chunks = AsyncMock()
        return client

    @pytest.fixture
    def ks(self, mock_ragflow):
        with patch("services.knowledge_service.os.path.exists", return_value=False):
            return KnowledgeService(ragflow_client=mock_ragflow)

    @pytest.mark.asyncio
    async def test_get_categories_returns_8(self, ks):
        """UT-KS-01: get_categories 返回8个预定义分类"""
        categories = await ks.get_categories()

        assert len(categories) == 8
        names = [c["name"] for c in categories]
        assert "宪法" in names
        assert "民法" in names
        assert "刑法" in names

    def test_fallback_search_by_name(self, ks):
        """UT-KS-02: 降级搜索按法律名称匹配"""
        results = ks.fallback_search("婚姻")

        assert len(results) > 0
        # 至少有一条匹配"婚姻"
        marriage_results = [r for r in results if "婚姻" in r.get("law_name", "")]
        assert len(marriage_results) > 0

    def test_fallback_search_by_summary(self, ks):
        """降级搜索按摘要匹配"""
        results = ks.fallback_search("消费者")

        assert len(results) > 0
        consumer_results = [r for r in results
                          if "消费" in r.get("law_name", "") or "消费" in r.get("law_text", "")]
        assert len(consumer_results) > 0

    def test_fallback_search_no_match_returns_all(self, ks):
        """UT-KS-04: 无匹配时返回全部法律摘要"""
        results = ks.fallback_search("zzzz_no_match_xyz")

        assert len(results) > 0
        # 所有结果的relevance应该较低
        for r in results:
            assert r["relevance"] <= 1.0

    def test_fallback_search_result_structure(self, ks):
        """降级搜索结果包含必要字段"""
        results = ks.fallback_search("劳动")

        for r in results:
            assert "law_name" in r
            assert "law_text" in r
            assert "relevance" in r
            assert isinstance(r["relevance"], (int, float))

    @pytest.mark.asyncio
    async def test_search_with_ragflow(self, ks, mock_ragflow):
        """通过 RAGFlow 检索"""
        mock_ragflow.search.return_value = [
            {"law_name": "劳动法", "article_num": "第1条", "law_text": "...", "source": "", "relevance": 0.9}
        ]

        result = await ks.search("劳动", page=1, page_size=10)

        assert result["count"] == 1
        assert len(result["items"]) == 1
        assert result["items"][0]["name"] == "劳动法"
        mock_ragflow.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_ragflow_fails_fallback(self, ks, mock_ragflow):
        """RAGFlow 失败时降级到本地搜索"""
        mock_ragflow.search.side_effect = Exception("connection error")

        result = await ks.search("劳动", page=1, page_size=10)

        assert result["count"] > 0
        assert "items" in result

    @pytest.mark.asyncio
    async def test_search_cache_hit(self, ks, mock_ragflow):
        """搜索结果被缓存"""
        mock_ragflow.search.return_value = [
            {"law_name": "劳动法", "article_num": "第1条", "law_text": "...", "source": "", "relevance": 0.9}
        ]

        # 第一次调用
        result1 = await ks.search("cache_test", page=1, page_size=10)
        # 第二次调用应使用缓存
        result2 = await ks.search("cache_test", page=1, page_size=10)

        assert result1 == result2
        # RAGFlow 只被调用一次
        assert mock_ragflow.search.call_count == 1
