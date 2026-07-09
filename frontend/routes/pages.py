"""页面路由"""

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

# ── P1 首页 ──
@router.get("/", response_class=None)
async def home_page(request: Request):
    return templates.TemplateResponse("pages/home.html", {"request": request, "page": "home"})


# ── P2 对话页 ──
@router.get("/chat")
async def chat_page(request: Request, session_id: int = None):
    return templates.TemplateResponse(
        "pages/chat.html",
        {"request": request, "page": "chat", "session_id": session_id},
    )


# ── P4 历史记录列表 ──
@router.get("/history")
async def history_page(request: Request):
    return templates.TemplateResponse("pages/history.html", {"request": request, "page": "history"})


# ── P5 历史对话详情 ──
@router.get("/history/{session_id}")
async def history_detail_page(request: Request, session_id: int):
    return templates.TemplateResponse(
        "pages/history_detail.html",
        {"request": request, "page": "history_detail", "session_id": session_id},
    )


# ── P6 个人中心 ──
@router.get("/profile")
async def profile_page(request: Request):
    return templates.TemplateResponse("pages/profile.html", {"request": request, "page": "profile"})


# ── P7 登录注册页 ──
@router.get("/login")
async def login_page(request: Request, redirect: str = None):
    return templates.TemplateResponse(
        "pages/login.html",
        {"request": request, "page": "login", "redirect": redirect},
    )


# ── P8 法律知识库 ──
@router.get("/knowledge")
async def knowledge_page(request: Request):
    return templates.TemplateResponse(
        "pages/knowledge.html", {"request": request, "page": "knowledge"}
    )


# ── P8 知识库法条详情 ──
@router.get("/knowledge/{law_id}")
async def knowledge_detail_page(request: Request, law_id: str):
    return templates.TemplateResponse(
        "pages/knowledge_detail.html",
        {"request": request, "page": "knowledge", "law_id": law_id},
    )


# ── P9 免责声明 ──
@router.get("/disclaimer")
async def disclaimer_page(request: Request):
    return templates.TemplateResponse(
        "pages/disclaimer.html", {"request": request, "page": "disclaimer"}
    )
