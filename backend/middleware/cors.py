"""
AI法律助手 v1.0 — CORS 跨域中间件

允许前端跨域访问 API，配置允许所有来源、方法和请求头。
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def setup_cors(app: FastAPI) -> None:
    """
    为 FastAPI 应用添加 CORS 中间件

    允许所有来源（开发阶段），生产环境应根据需要限制 origins。

    Args:
        app: FastAPI 应用实例
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],           # 允许所有来源
        allow_credentials=True,        # 允许携带凭据
        allow_methods=["*"],           # 允许所有 HTTP 方法
        allow_headers=["*"],           # 允许所有请求头
    )
