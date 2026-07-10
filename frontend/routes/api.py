"""API 代理路由 — 将前端请求转发到后端 Python 服务"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
import httpx
import os

router = APIRouter()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080")
API_PREFIX = "/api/v1"


async def proxy_request(request: Request, path: str):
    """通用代理：将请求转发到后端 Python 服务"""
    body = None
    if request.method in ("POST", "PUT", "PATCH"):
        body = await request.body()

    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)

    url = f"{BACKEND_URL}{API_PREFIX}/{path}"
    if request.url.query:
        url += f"?{request.url.query}"

    # SSE 流式需要长超时，普通请求正常超时
    is_stream_path = path.endswith("/stream")
    timeout = httpx.Timeout(300.0, connect=10.0) if is_stream_path else httpx.Timeout(30.0, connect=10.0)
    client = httpx.AsyncClient(timeout=timeout, trust_env=False)

    try:
        resp = await client.send(
            client.build_request(
                method=request.method,
                url=url,
                headers=headers,
                content=body,
            ),
            stream=True,
        )

        content_type = resp.headers.get("content-type", "")

        # SSE 流式响应 —— 透传字节流，客户端生命周期绑定到生成器
        if content_type.startswith("text/event-stream"):
            async def sse_stream():
                try:
                    async for chunk in resp.aiter_bytes():
                        yield chunk
                finally:
                    await resp.aclose()
                    await client.aclose()

            return StreamingResponse(
                sse_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

        # 非流式 —— 先读取响应体再解析 JSON
        await resp.aread()
        data = resp.json()
        status_code = resp.status_code
        if status_code >= 400 and "detail" in data:
            detail = data["detail"]
            if isinstance(detail, dict) and "code" in detail:
                return JSONResponse(content=detail, status_code=status_code)
        return JSONResponse(content=data, status_code=status_code)

    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="后端服务暂不可用")
    finally:
        # 非流式响应在 finally 中关闭；流式响应由 sse_stream 生成器关闭
        if not (is_stream_path and 'resp' in locals() and
                resp.headers.get("content-type", "").startswith("text/event-stream")):
            await client.aclose()


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_all(request: Request, path: str):
    """代理所有 API 请求到后端 Python 服务"""
    return await proxy_request(request, path)
