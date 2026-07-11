"""
middleware/content_safety 模块单元测试
"""
import os
import sys
import pytest
import tempfile
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))


class TestContentSafety:
    """内容安全检查器测试"""

    def make_settings(self, keywords_file="blocked_keywords.txt", enabled=True):
        s = MagicMock()
        s.safety_enable = enabled
        s.safety_keywords_file = keywords_file
        return s

    def test_init_disabled(self):
        """禁用状态 → 不加载关键词"""
        from middleware.content_safety import ContentSafety
        s = self.make_settings(enabled=False)
        cs = ContentSafety(s)
        assert cs.check("任何内容") is True

    def test_init_with_missing_file(self):
        """关键词文件不存在 → 不抛异常，跳过检查"""
        from middleware.content_safety import ContentSafety
        s = self.make_settings(keywords_file="/nonexistent/file.txt")
        cs = ContentSafety(s)
        assert cs.check("test") is True

    def test_init_loads_keywords(self):
        """从文件加载关键词"""
        from middleware.content_safety import ContentSafety

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False,
                                         encoding="utf-8") as f:
            f.write("敏感词1\n敏感词2\n# 注释行\n\n敏感词3\n")
            tmp_path = f.name

        try:
            s = self.make_settings(keywords_file=tmp_path)
            cs = ContentSafety(s)
            assert len(cs._blocked_keywords) == 3
        finally:
            os.unlink(tmp_path)

    def test_check_no_keywords_respects_enabled(self):
        """无关键词 + 已启用 → 检查通过"""
        from middleware.content_safety import ContentSafety
        s = self.make_settings(keywords_file="/nonexistent/file.txt")
        s.safety_enable = True
        cs = ContentSafety(s)
        assert cs.check("任意内容") is True

    def test_check_blocked_content(self):
        """含敏感词 → False"""
        from middleware.content_safety import ContentSafety

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False,
                                         encoding="utf-8") as f:
            f.write("违禁词\n")
            tmp_path = f.name

        try:
            s = self.make_settings(keywords_file=tmp_path)
            cs = ContentSafety(s)
            assert cs.check("包含违禁词的内容") is False
            assert cs.check("正常内容") is True
        finally:
            os.unlink(tmp_path)

    def test_check_case_insensitive(self):
        """大小写不敏感"""
        from middleware.content_safety import ContentSafety

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False,
                                         encoding="utf-8") as f:
            f.write("VIOLATION\n")
            tmp_path = f.name

        try:
            s = self.make_settings(keywords_file=tmp_path)
            cs = ContentSafety(s)
            assert cs.check("contains violation word") is False
        finally:
            os.unlink(tmp_path)

    def test_check_disabled_always_true(self):
        """禁用 → 始终返回 True"""
        from middleware.content_safety import ContentSafety

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False,
                                         encoding="utf-8") as f:
            f.write("敏感词\n")
            tmp_path = f.name

        try:
            s = self.make_settings(keywords_file=tmp_path, enabled=False)
            cs = ContentSafety(s)
            assert cs.check("含敏感词的内容") is True
        finally:
            os.unlink(tmp_path)


class TestContentSafetyMiddleware:
    """中间件拦截测试"""

    @pytest.mark.asyncio
    async def test_get_request_passes_through(self):
        """GET 请求直接放行"""
        from middleware.content_safety import ContentSafety
        cs = ContentSafety(MagicMock(safety_enable=True, safety_keywords_file="/nonexistent"))
        request = MagicMock()
        request.method = "GET"

        call_next = AsyncMock(return_value=MagicMock(status_code=200))
        response = await cs.middleware(request, call_next)
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_post_with_safe_content(self):
        """POST 正常内容 → 放行"""
        from middleware.content_safety import ContentSafety
        s = MagicMock()
        s.safety_enable = True
        s.safety_keywords_file = "/nonexistent"
        cs = ContentSafety(s)

        request = MagicMock()
        request.method = "POST"
        request.body = AsyncMock(return_value='{"content": "正常问题"}'.encode("utf-8"))

        call_next = AsyncMock(return_value=MagicMock(status_code=200))
        response = await cs.middleware(request, call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_post_with_blocked_content(self):
        """POST 敏感内容 → 403"""
        from middleware.content_safety import ContentSafety
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False,
                                         encoding="utf-8") as f:
            f.write("敏感词\n")
            tmp_path = f.name

        try:
            s = MagicMock()
            s.safety_enable = True
            s.safety_keywords_file = tmp_path
            cs = ContentSafety(s)

            request = MagicMock()
            request.method = "POST"
            # JSON body containing the blocked keyword
            body_data = '{"content": "包含敏感词的文本"}'
            request.body = AsyncMock(return_value=body_data.encode("utf-8"))

            call_next = AsyncMock()
            response = await cs.middleware(request, call_next)
            assert response.status_code == 403
        finally:
            os.unlink(tmp_path)
