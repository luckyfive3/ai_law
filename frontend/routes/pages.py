"""页面路由"""

from fastapi import APIRouter, Request
from starlette.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path

router = APIRouter()
TEMPLATES_DIR = str(Path(__file__).resolve().parent.parent / "templates")
env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(),
    cache_size=0,
)
templates = Jinja2Templates(env=env)

# ── P1 首页 ──
@router.get("/", response_class=None)
async def home_page(request: Request):
    return templates.TemplateResponse(request, "pages/home.html", {"page": "home"})


# ── P2 对话页 ──
@router.get("/chat")
async def chat_page(request: Request, session_id: int = None):
    return templates.TemplateResponse(
        request, "pages/chat.html",
        {"page": "chat", "session_id": session_id},
    )


# ── P4 历史记录列表 ──
@router.get("/history")
async def history_page(request: Request):
    return templates.TemplateResponse(request, "pages/history.html", {"page": "history"})


# ── P5 历史对话详情 ──
@router.get("/history/{session_id}")
async def history_detail_page(request: Request, session_id: int):
    return templates.TemplateResponse(
        request, "pages/history_detail.html",
        {"page": "history_detail", "session_id": session_id},
    )


# ── P6 个人中心 ──
@router.get("/profile")
async def profile_page(request: Request):
    return templates.TemplateResponse(request, "pages/profile.html", {"page": "profile"})


# ── P7 登录注册页 ──
@router.get("/login")
async def login_page(request: Request, redirect: str = None):
    return templates.TemplateResponse(
        request, "pages/login.html",
        {"page": "login", "redirect": redirect},
    )


# ── P8 法律知识库 ──
@router.get("/knowledge")
async def knowledge_page(request: Request):
    return templates.TemplateResponse(
        request, "pages/knowledge.html", {"page": "knowledge"}
    )


# ── P8 知识库法条详情 ──
@router.get("/knowledge/{law_id}")
async def knowledge_detail_page(request: Request, law_id: str):
    return templates.TemplateResponse(
        request, "pages/knowledge_detail.html",
        {"page": "knowledge", "law_id": law_id},
    )


# ── P9 免责声明 ──
@router.get("/disclaimer")
async def disclaimer_page(request: Request):
    return templates.TemplateResponse(
        request, "pages/disclaimer.html", {"page": "disclaimer"}
    )
