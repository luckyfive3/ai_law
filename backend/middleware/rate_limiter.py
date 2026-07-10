"""
AI法律助手 v1.0 — 限流中间件

基于 slowapi 实现 API 访问频率限制：
- IP 级别：限制每个 IP 的请求频率
- 用户级别：限制每个用户的消息发送频率
"""
from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from config import Settings
from utils import errcode


from slowapi import Limiter
from slowapi.util import get_remote_address

# 全局限流器实例
limiter = Limiter(key_func=get_remote_address, default_limits=["30/minute"])


def setup_rate_limiter(app: FastAPI, settings: Settings) -> None:
    """
    为 FastAPI 应用配置限流中间件

    Args:
        app: FastAPI 应用实例
        settings: 应用配置（包含限流参数）
    """
    # 设置全局限流器
    app.state.limiter = limiter

    # 注册限流超限异常处理器
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # 自定义限流超限响应格式
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=429,
            content={
                "code": errcode.CodeRateLimited,
                "message": errcode.get_message(errcode.CodeRateLimited),
            },
        )

    # 替换默认的限流超限处理器
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
