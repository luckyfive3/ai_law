"""
middleware/logger 模块单元测试
"""
import sys
import os
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))


class TestGetClientIP:
    """_get_client_ip 静态方法测试"""

    def test_x_forwarded_for_first_ip(self):
        """X-Forwarded-For → 取第一个 IP"""
        from middleware.logger import RequestLoggerMiddleware
        request = MagicMock()
        request.headers = {
            "X-Forwarded-For": "10.0.0.1, 10.0.0.2, 10.0.0.3",
        }

        ip = RequestLoggerMiddleware._get_client_ip(request)
        assert ip == "10.0.0.1"

    def test_x_real_ip(self):
        """X-Real-IP → 直接使用"""
        from middleware.logger import RequestLoggerMiddleware
        request = MagicMock()
        request.headers = {
            "X-Real-IP": "192.168.1.100",
        }

        ip = RequestLoggerMiddleware._get_client_ip(request)
        assert ip == "192.168.1.100"

    def test_fallback_to_client_host(self):
        """无代理头 → 取直连 IP"""
        from middleware.logger import RequestLoggerMiddleware
        request = MagicMock()
        request.headers = {}
        request.client.host = "127.0.0.1"

        ip = RequestLoggerMiddleware._get_client_ip(request)
        assert ip == "127.0.0.1"

    def test_fallback_to_unknown(self):
        """完全无 IP → unknown"""
        from middleware.logger import RequestLoggerMiddleware
        request = MagicMock()
        request.headers = {}
        request.client = None

        ip = RequestLoggerMiddleware._get_client_ip(request)
        assert ip == "unknown"

    def test_x_forwarded_for_priority_over_x_real_ip(self):
        """X-Forwarded-For 优先级高于 X-Real-IP"""
        from middleware.logger import RequestLoggerMiddleware
        request = MagicMock()
        request.headers = {
            "X-Forwarded-For": "10.0.0.1",
            "X-Real-IP": "192.168.1.1",
        }

        ip = RequestLoggerMiddleware._get_client_ip(request)
        assert ip == "10.0.0.1"


class TestRequestLoggerMiddleware:
    """请求日志中间件测试"""

    @pytest.mark.asyncio
    async def test_logs_request_info(self):
        """正常请求 → 记录日志"""
        from middleware.logger import RequestLoggerMiddleware
        middleware = RequestLoggerMiddleware(app=MagicMock())

        request = MagicMock()
        request.method = "POST"
        request.url.path = "/api/v1/chat/stream"
        request.headers = {}
        request.client.host = "192.168.1.1"

        response = MagicMock(status_code=200)
        call_next = AsyncMock(return_value=response)

        result = await middleware.dispatch(request, call_next)
        assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_logs_error_status(self):
        """异常请求 → 记录 500"""
        from middleware.logger import RequestLoggerMiddleware
        middleware = RequestLoggerMiddleware(app=MagicMock())

        request = MagicMock()
        request.method = "GET"
        request.url.path = "/api/v1/error"
        request.headers = {}
        request.client.host = "10.0.0.1"

        call_next = AsyncMock(side_effect=Exception("internal error"))

        with pytest.raises(Exception, match="internal error"):
            await middleware.dispatch(request, call_next)
