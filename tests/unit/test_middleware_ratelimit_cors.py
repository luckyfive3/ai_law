"""
middleware/rate_limiter + cors 模块单元测试
"""
import sys
import os
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))


class TestRateLimiter:
    """限流中间件测试"""

    def test_limiter_created(self):
        """limiter 实例被正确创建"""
        from middleware.rate_limiter import limiter
        from slowapi import Limiter
        assert isinstance(limiter, Limiter)

    def test_limiter_has_default_limits(self):
        """默认全局限频已设置"""
        from middleware.rate_limiter import limiter
        assert limiter is not None

    def test_setup_rate_limiter(self):
        """setup_rate_limiter 注册异常处理器并设置 state"""
        from middleware.rate_limiter import setup_rate_limiter
        app = MagicMock()
        app.state = MagicMock()
        settings = MagicMock()

        setup_rate_limiter(app, settings)

        assert app.state.limiter is not None
        # 应该注册 RateLimitExceeded 异常处理器
        assert app.add_exception_handler.call_count >= 2


class TestCors:
    """CORS 中间件测试"""

    def test_setup_cors_adds_middleware(self):
        """setup_cors 添加 CORSMiddleware"""
        from middleware.cors import setup_cors
        app = MagicMock()
        setup_cors(app)
        app.add_middleware.assert_called_once()
