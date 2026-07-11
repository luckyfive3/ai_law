"""
AI法律助手 v1.0 — 前端服务入口
基于 FastAPI + Jinja2 的服务端渲染前端
后端为 Python FastAPI 服务，前端通过 API 代理转发请求到后端
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import uvicorn

from routes.pages import router as pages_router
from routes.api import router as api_router
from routes.mock_auth import router as mock_auth_router
from routes.mock_cases import router as mock_cases_router

app = FastAPI(title="AI法律助手", version="1.0.0", docs_url=None, redoc_url=None)

BASE_DIR = Path(__file__).resolve().parent

# 静态文件服务（CSS、JS、图片等）
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# 页面路由（Jinja2 模板渲染）
app.include_router(pages_router)

# 本地模拟认证路由（开发环境使用，无需后端）
# 注：后端已启动时注释掉，让代理转发到后端处理
# app.include_router(mock_auth_router)
# 本地模拟案件 API（开发测试使用）
# app.include_router(mock_cases_router)

# API 代理路由 —— 将 /api/v1/proxy/* 转发到后端 Python 服务
app.include_router(api_router, prefix="/api/v1/proxy")


from starlette.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader, select_autoescape

_error_env = Environment(
    loader=FileSystemLoader(str(BASE_DIR / "templates")),
    autoescape=select_autoescape(),
    cache_size=0,
)
_error_templates = Jinja2Templates(env=_error_env)


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """404 页面处理"""
    return _error_templates.TemplateResponse(request, "pages/404.html", status_code=404)


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    """500 服务器错误页面处理"""
    return _error_templates.TemplateResponse(request, "pages/500.html", status_code=500)


if __name__ == "__main__":
    # 前端服务监听 3000 端口，代理请求到后端 8080 端口
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=False)
