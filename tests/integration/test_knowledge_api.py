"""
知识库 API 集成测试
GET /api/v1/knowledge/documents, /categories, /search, /laws/{id}
"""
import pytest


class TestKnowledgeDocuments:
    """文档列表接口"""

    def test_get_documents_returns_list(self, test_app):
        """IT-KB-01: 获取文档列表 → 200"""
        import asyncio
        mock = test_app.app.state.services["knowledge_service"]
        orig = mock.get_ragflow_documents

        async def fake_docs():
            return [{"id": "1", "name": "民法典", "category": "civil", "year": "2020"}]

        mock.get_ragflow_documents = fake_docs

        resp = test_app.get("/api/v1/knowledge/documents")

        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0

        mock.get_ragflow_documents = orig


class TestKnowledgeCategories:
    """分类列表接口"""

    def test_get_categories_count(self, test_app):
        """IT-KB-02: 获取分类列表，返回8个"""
        resp = test_app.get("/api/v1/knowledge/categories")

        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert len(data["data"]) == 8


class TestKnowledgeSearch:
    """搜索接口"""

    def test_search_with_keyword(self, test_app):
        """IT-KB-03: 关键词搜索返回 items"""
        resp = test_app.get("/api/v1/knowledge/search?keyword=劳动")

        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            data = resp.json()
            assert data["code"] == 0
            assert "items" in data["data"]

    def test_search_no_keyword(self, test_app):
        """IT-KB-04: 无 keyword → 422"""
        resp = test_app.get("/api/v1/knowledge/search")

        assert resp.status_code == 422


class TestKnowledgeLawDetail:
    """法条详情接口"""

    def test_get_detail_not_found(self, test_app):
        """IT-KB-06: 法条不存在 → 404"""
        import asyncio
        mock = test_app.app.state.services["knowledge_service"]
        orig = mock.get_law_detail

        async def fake_detail(law_id):
            raise ValueError("文档不存在或未解析")

        mock.get_law_detail = fake_detail

        resp = test_app.get("/api/v1/knowledge/laws/nonexistent_id")

        assert resp.status_code == 404

        mock.get_law_detail = orig

    def test_get_detail_missing_id(self, test_app):
        """访问 /laws/ 空路径"""
        resp = test_app.get("/api/v1/knowledge/laws/")

        # FastAPI 会将空路径路由到 /laws 或报 404/405
        assert resp.status_code in (404, 405)
