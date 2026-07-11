"""
AI法律助手 v1.0 — FastAPI 应用入口
阿里云 ECS (Ubuntu Linux) + MongoDB (Motor) + RAGFlow + LangChain

启动方式:
    python main.py
    或: uvicorn main:app --host 0.0.0.0 --port 8080
"""
import json
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Dict, Any

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import JSONResponse

# ── 配置与数据库 ──
from config import load_config, Settings
from database import init_database, close_database, get_database

# ── 服务层 ──
from services.safety_filter import SafetyFilter
from services.chat_service_v2 import ChatService as ChatServiceV2, ContentSafetyCheck
from services.ragflow_client import RAGFlowClient
from services.llm_service_v2 import LLMService as LLMServiceV2
from services.auth_service import AuthService
from services.user_service import UserService
from services.session_service import SessionService
from services.knowledge_service import KnowledgeService
from services.case_service import CaseService

# ── 中间件 ──
from middleware.logger import RequestLoggerMiddleware
from middleware.content_safety import ContentSafety
from middleware.cors import setup_cors
from middleware.rate_limiter import setup_rate_limiter
from slowapi.middleware import SlowAPIMiddleware

# ── API 路由 ──
from api.auth import router as auth_router
from api.user import router as user_router
from api.session import router as session_router
from api.chat import router as chat_router
from api.knowledge import router as knowledge_router
from api.cases import router as case_router

# ── 工具层 ──
from utils import errcode

# ══════════════════════════════════════════════════════════════
# 日志配置
# ══════════════════════════════════════════════════════════════

def _setup_logging() -> None:
    """配置应用日志格式和级别"""
    log_format = (
        "[%(asctime)s] %(levelname)-8s %(name)-28s %(message)s"
    )
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )
    # 降低第三方库的日志级别，减少噪音
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("motor").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("slowapi").setLevel(logging.WARNING)

_setup_logging()

logger = logging.getLogger("ai_law")

# ══════════════════════════════════════════════════════════════
# 应用生命周期
# ══════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 生命周期管理器
    负责应用启动时的资源初始化和关闭时的资源释放
    """
    # ── 启动阶段 ──
    logger.info("=" * 60)
    logger.info("AI法律助手 v1.0 正在启动...")
    logger.info(f"运行环境: {sys.platform}")
    logger.info(f"Python 版本: {sys.version}")
    logger.info(f"服务地址: {app.state.settings.server_host}:{app.state.settings.server_port}")
    logger.info("=" * 60)

    try:
        # 初始化 MongoDB 连接
        db = await init_database(app.state.settings)
        app.state.db = db
        logger.info("MongoDB 初始化成功")
    except Exception as e:
        logger.critical(f"MongoDB 初始化失败，应用无法启动: {e}")
        sys.exit(1)

    # ── 创建所有服务实例 ──
    _init_services(app)

    logger.info("=" * 60)
    logger.info("AI法律助手 v1.0 启动完成，等待请求...")
    logger.info("=" * 60)

    yield  # 应用运行中

    # ── 关闭阶段 ──
    logger.info("AI法律助手正在关闭...")
    try:
        await close_database()
    except Exception as e:
        logger.error(f"关闭数据库连接时出错: {e}")
    logger.info("AI法律助手已关闭")


def _init_services(app: FastAPI) -> None:
    """
    初始化所有业务服务实例并存入 app.state.services

    Args:
        app: FastAPI 应用实例
    """
    settings: Settings = app.state.settings
    db = app.state.db

    # ── 基础服务（无依赖） ──
    safety_filter = SafetyFilter(enable=settings.safety_enable)
    content_safety_check = ContentSafetyCheck(enable=settings.safety_enable)
    ragflow_client = RAGFlowClient(settings)
    llm_service = LLMServiceV2(settings)

    # ── 数据库相关服务 ──
    auth_service = AuthService(db)
    user_service = UserService(db)
    session_service = SessionService(db)

    # ── 组合服务（v2 升级版：LangChain LCEL RAG 链 + 结构化 Prompt） ──
    chat_service = ChatServiceV2(
        db=db,
        ragflow_client=ragflow_client,
        llm_service=llm_service,
        safety_filter=safety_filter,
        content_safety=content_safety_check,
    )
    knowledge_service = KnowledgeService(ragflow_client=ragflow_client)

    # ── 案件管理服务 ──
    case_service = CaseService(db)

    # ── 存入 app.state.services ──
    app.state.services = {
        "safety_filter": safety_filter,
        "content_safety_check": content_safety_check,
        "ragflow_client": ragflow_client,
        "llm_service": llm_service,
        "auth_service": auth_service,
        "user_service": user_service,
        "session_service": session_service,
        "chat_service": chat_service,
        "knowledge_service": knowledge_service,
        "case_service": case_service,
    }

    logger.info(f"已初始化 {len(app.state.services)} 个服务实例")
    for name in app.state.services:
        logger.info(f"  - {name}")


# ══════════════════════════════════════════════════════════════
# 创建 FastAPI 应用
# ══════════════════════════════════════════════════════════════

# 加载配置
settings: Settings = load_config()

app = FastAPI(
    title="AI法律助手",
    description="基于 RAGFlow + LangChain 的中文法律AI助手后端服务",
    version="1.0.0",
    lifespan=lifespan,
)

# 将配置存入应用状态（供服务初始化前访问）
app.state.settings = settings

# ── 静态文件挂载（上传文件视图） ──
import os as _os
from fastapi.staticfiles import StaticFiles as _StaticFiles
_upload_dir = _os.path.join(_os.path.dirname(__file__), "uploads")
_os.makedirs(_upload_dir, exist_ok=True)
app.mount("/uploads", _StaticFiles(directory=_upload_dir), name="uploads")

# ══════════════════════════════════════════════════════════════
# 全局依赖：Settings
# ══════════════════════════════════════════════════════════════

async def get_settings() -> Settings:
    """
    全局配置依赖函数
    可在路由处理函数中通过 Depends(get_settings) 获取配置
    """
    return settings

# ══════════════════════════════════════════════════════════════
# 中间件注册
# ══════════════════════════════════════════════════════════════

# 1. 请求日志中间件（记录每个请求的耗时、状态码等）
app.add_middleware(RequestLoggerMiddleware)

# 2. CORS 跨域中间件
setup_cors(app)

# 3. 内容安全中间件（敏感词检测）
content_safety_middleware = ContentSafety(settings)
app.middleware("http")(content_safety_middleware.middleware)

# 4. 全局限流中间件
setup_rate_limiter(app, settings)
app.add_middleware(SlowAPIMiddleware)

# ══════════════════════════════════════════════════════════════
# API 路由注册
# ══════════════════════════════════════════════════════════════

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(session_router)
app.include_router(chat_router)
app.include_router(knowledge_router)
app.include_router(case_router)

# ══════════════════════════════════════════════════════════════
# 健康检查端点
# ══════════════════════════════════════════════════════════════

@app.get("/health", tags=["系统"])
async def health_check() -> Dict[str, Any]:
    """
    服务健康检查

    返回服务运行状态和当前时间戳，
    可用于负载均衡健康探测、监控告警等场景。
    """
    return {
        "status": "ok",
        "time": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
    }

# ══════════════════════════════════════════════════════════════
# 全局异常处理
# ══════════════════════════════════════════════════════════════

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    处理 404 未找到的请求

    返回统一的 JSON 错误格式，便于前端统一处理。
    """
    logger.warning(f"404 未找到: method={request.method} path={request.url.path}")
    return JSONResponse(
        status_code=404,
        content={
            "code": 404,
            "message": f"请求的资源不存在: {request.url.path}",
        },
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    处理 500 服务器内部错误

    返回统一 JSON 格式，记录完整堆栈信息用于排查。
    """
    logger.error(
        f"500 服务器内部错误: method={request.method} path={request.url.path}",
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={
            "code": errcode.CodeInternalError,
            "message": errcode.get_message(errcode.CodeInternalError),
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    处理所有 HTTPException
    确保所有 HTTP 异常都以统一 JSON 格式返回
    """
    # 如果 detail 已经是包含 code/message 的字典格式，直接使用
    if isinstance(exc.detail, dict):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail,
        )
    # 否则包装为标准格式
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": str(exc.detail),
        },
    )


# ══════════════════════════════════════════════════════════════
# 直接启动入口
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=False,
    )
