"""
AI法律助手 v1.0 — 请求日志中间件

ASGI 中间件，记录每个 HTTP 请求的方法、路径、状态码、
响应耗时和客户端 IP，便于问题排查和性能监控。
"""
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("ai_law.request")


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """
    请求日志中间件

    记录每个请求的关键信息：
    - 请求方法 (method)
    - 请求路径 (path)
    - 响应状态码 (status_code)
    - 请求处理耗时 (duration_ms)
    - 客户端 IP (client_ip)
    """

    async def dispatch(self, request: Request, call_next):
        """
        处理请求并记录日志

        Args:
            request: 请求对象
            call_next: 下一个中间件或路由处理函数

        Returns:
            Response: 请求处理结果
        """
        # 记录请求开始时间
        start_time = time.time()

        # 获取客户端 IP（支持代理转发场景）
        client_ip = self._get_client_ip(request)

        # 执行后续处理
        response = None
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as e:
            status_code = 500
            logger.error(
                f"[{request.method}] {request.url.path} - 异常: {str(e)}",
                exc_info=True,
            )
            raise
        finally:
            # 计算耗时（毫秒）
            duration_ms = round((time.time() - start_time) * 1000, 2)

            # 输出日志
            logger.info(
                f"method={request.method} "
                f"path={request.url.path} "
                f"status={status_code} "
                f"duration={duration_ms}ms "
                f"client_ip={client_ip}"
            )

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """
        获取客户端真实 IP

        优先从 X-Forwarded-For、X-Real-IP 等代理头获取，
        最后回退到直连 IP。

        Args:
            request: 请求对象

        Returns:
            str: 客户端 IP 地址
        """
        # 按优先级尝试常见的代理/负载均衡转发头
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # X-Forwarded-For 可能包含多个 IP，取第一个
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # 回退到直连 IP
        if request.client:
            return request.client.host

        return "unknown"
