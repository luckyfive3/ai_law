"""
AI法律助手 v1.0 — 会话摘要与用户画像 API
提供会话摘要查询、用户画像查看和手动触发摘要生成
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Query

from middleware.auth import get_current_user
from schemas.response import success_response, error_response
from utils import errcode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/summary", tags=["摘要与画像"])


def get_summary_service(request: Request):
    """从应用状态获取 SummaryService"""
    return request.app.state.services.get("summary_service")


# ═══════════════════════════════════════
# 会话摘要
# ═══════════════════════════════════════

@router.get("/session/{session_id}", summary="获取会话摘要")
async def get_session_summary(
    session_id: str,
    request: Request,
    current_user=Depends(get_current_user),
    summary_service=Depends(get_summary_service),
):
    """
    获取指定会话的 AI 摘要。

    如果摘要不存在（尚未生成），返回 404。

    Args:
        session_id: 会话 ID
    """
    if not summary_service:
        raise HTTPException(status_code=500, detail=error_response(errcode.CodeInternalError))

    summary = await summary_service.get_session_summary(session_id)
    if not summary:
        return success_response(None, message="该会话暂未生成摘要")

    return success_response(summary)


@router.post("/session/{session_id}/generate", summary="手动生成会话摘要")
async def generate_session_summary(
    session_id: str,
    request: Request,
    current_user=Depends(get_current_user),
    summary_service=Depends(get_summary_service),
    force: bool = Query(default=False, description="是否强制重新生成"),
):
    """
    手动触发指定会话的 AI 摘要生成。

    默认仅在消息数 >= 4 时生成。设置 force=true 可强制生成。

    Args:
        session_id: 会话 ID
        force: 是否强制生成
    """
    if not summary_service:
        raise HTTPException(status_code=500, detail=error_response(errcode.CodeInternalError))

    try:
        result = await summary_service.generate_session_summary(session_id, force=force)
        if result:
            return success_response({"summary": result}, message="摘要生成成功")
        else:
            return success_response(None, message="消息数不足，暂未生成摘要")
    except Exception as e:
        logger.error(f"生成摘要失败: {e}")
        raise HTTPException(status_code=500, detail=error_response(errcode.CodeInternalError))


# ═══════════════════════════════════════
# 用户画像
# ═══════════════════════════════════════

@router.get("/profile", summary="获取用户画像")
async def get_user_profile(
    request: Request,
    current_user=Depends(get_current_user),
    summary_service=Depends(get_summary_service),
):
    """
    获取当前用户的 AI 画像。

    包含：
        - 总咨询次数、总消息数
        - 咨询领域分布
        - AI 生成的用户画像文字
        - 最近会话摘要

    新用户或无会话摘要的用户返回空画像。
    """
    if not summary_service:
        raise HTTPException(status_code=500, detail=error_response(errcode.CodeInternalError))

    user_id = current_user["user_id"]
    profile = await summary_service.get_user_profile(user_id)

    return success_response(profile or {
        "user_id": user_id,
        "total_sessions": 0,
        "total_messages": 0,
        "category_distribution": {},
        "top_categories": [],
        "profile_text": "",
    })


@router.post("/profile/refresh", summary="刷新用户画像")
async def refresh_user_profile(
    request: Request,
    current_user=Depends(get_current_user),
    summary_service=Depends(get_summary_service),
):
    """
    手动触发用户画像更新。

    会重新收集所有已生成摘要的会话，调用 LLM 分析用户习惯，
    更新 user_profiles 集合。
    """
    if not summary_service:
        raise HTTPException(status_code=500, detail=error_response(errcode.CodeInternalError))

    user_id = current_user["user_id"]
    try:
        profile = await summary_service.update_user_profile(user_id)
        return success_response(profile, message="用户画像已刷新")
    except Exception as e:
        logger.error(f"刷新用户画像失败: {e}")
        raise HTTPException(status_code=500, detail=error_response(errcode.CodeInternalError))


# ═══════════════════════════════════════
# 个性化上下文（内部使用，也可暴露给前端调试）
# ═══════════════════════════════════════

@router.get("/context", summary="获取个性化对话上下文")
async def get_personalized_context(
    request: Request,
    current_user=Depends(get_current_user),
    summary_service=Depends(get_summary_service),
):
    """
    获取当前用户的个性化对话上下文。

    这是注入到 AI 对话 System Prompt 中的文本，
    可帮助 AI 根据用户习惯生成更合适的回答。

    新用户返回空字符串。
    """
    if not summary_service:
        return success_response({"context": ""})

    user_id = current_user["user_id"]
    context = await summary_service.get_personalized_context(user_id)
    return success_response({"context": context})
