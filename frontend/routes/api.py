"""API 代理路由 — 将前端请求转发到后端 Python 服务"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
import httpx
import os
import json

router = APIRouter()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080")
API_PREFIX = "/api/v1"


async def proxy_request(request: Request, path: str):
    """通用代理：将请求转发到后端 Python 服务"""
    client = httpx.AsyncClient(timeout=30.0)
    body = None
    if request.method in ("POST", "PUT", "PATCH"):
        body = await request.body()

    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)

    url = f"{BACKEND_URL}{API_PREFIX}/{path}"
    if request.url.query:
        url += f"?{request.url.query}"

    try:
        resp = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=body,
        )

        # SSE 流式响应：直接透传，不做 JSON 解析
        if resp.headers.get("content-type", "").startswith("text/event-stream"):
            return StreamingResponse(
                resp.aiter_bytes(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
            )

        # 透传 HTTP 状态码，并将后端 FastAPI 的 detail 嵌套格式展开
        data = resp.json()
        status_code = resp.status_code
        if status_code >= 400 and "detail" in data:
            # FastAPI HTTPException 会把错误包在 {"detail": {...}} 中，展开它
            detail = data["detail"]
            if isinstance(detail, dict) and "code" in detail:
                return JSONResponse(content=detail, status_code=status_code)
        return JSONResponse(content=data, status_code=status_code)
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="后端服务暂不可用")
    finally:
        await client.aclose()


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_all(request: Request, path: str):
    """代理所有 API 请求到后端 Python 服务"""
    return await proxy_request(request, path)
