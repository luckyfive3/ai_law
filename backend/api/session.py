"""
AI法律助手 v1.0 — 会话管理 API 路由
提供会话的创建、列表、详情、删除和清空接口
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from middleware.auth import get_current_user
from schemas.request import CreateSessionRequest
from schemas.response import success_response, error_response, paginated_response
from utils import errcode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sessions", tags=["会话"])


# ==================== 依赖注入 ====================

def get_session_service(request: Request):
    """
    从应用状态中获取 SessionService 实例
    该实例在 main.py 启动时被注册到 app.state.services 中
    """
    return request.app.state.services["session_service"]


# ==================== 创建会话 ====================

@router.post("", summary="创建新会话")
async def create_session(
    req: CreateSessionRequest,
    request: Request,
    current_user=Depends(get_current_user),
    session_service=Depends(get_session_service),
):
    """
    创建新的法律咨询会话

    需要有效的 JWT Token。

    Args:
        req: 创建会话请求体，包含可选的 title 和 category

    Returns:
        创建的会话信息，包含 id、title、category、msg_count 等
    """
    try:
        user_id = current_user["user_id"]
        session = await session_service.create(
            user_id=user_id,
            title=req.title or "",
            category=req.category or "",
        )

        logger.info(f"会话创建成功: session_id={session['id']}, user_id={user_id}")
        return success_response(session)

    except Exception as e:
        logger.error(f"创建会话异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(errcode.CodeInternalError),
        )


# ==================== 会话列表 ====================

@router.get("", summary="获取用户会话列表")
async def list_sessions(
    request: Request,
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=50, description="每页数量"),
    current_user=Depends(get_current_user),
    session_service=Depends(get_session_service),
):
    """
    获取当前用户的会话列表（分页）

    按最后更新时间倒序排列。
    需要有效的 JWT Token。

    Args:
        page: 页码（从 1 开始）
        page_size: 每页数量（1-50）

    Returns:
        分页的会话列表，包含 list、total、page、page_size、has_more
    """
    try:
        user_id = current_user["user_id"]
        sessions, total = await session_service.list_sessions(
            user_id=user_id,
            page=page,
            page_size=page_size,
        )

        logger.info(f"获取会话列表成功: user_id={user_id}, total={total}")
        return paginated_response(sessions, total, page, page_size)

    except Exception as e:
        logger.error(f"获取会话列表异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(errcode.CodeInternalError),
        )


# ==================== 清空全部会话 ====================
# 注意：此路由必须在 /{session_id} 之前注册，否则 "clear-all" 会被当作 session_id 处理

@router.delete("/clear-all", summary="清空全部会话")
async def clear_all_sessions(
    request: Request,
    current_user=Depends(get_current_user),
    session_service=Depends(get_session_service),
):
    """
    清空当前用户的所有历史会话（软删除）

    需要有效的 JWT Token。

    Returns:
        被删除的会话数量
    """
    try:
        user_id = current_user["user_id"]
        count = await session_service.clear_all(user_id)

        logger.info(f"清空全部会话成功: user_id={user_id}, 删除数量={count}")
        return success_response({
            "deleted_count": count,
            "message": f"已清空 {count} 个会话",
        })

    except Exception as e:
        logger.error(f"清空全部会话异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(errcode.CodeInternalError),
        )


# ==================== 会话详情 ====================

@router.get("/{session_id}", summary="获取会话详情")
async def get_session_detail(
    session_id: str,
    request: Request,
    page: int = Query(default=1, ge=1, description="消息页码"),
    page_size: int = Query(default=50, ge=1, le=50, description="每页消息数"),
    current_user=Depends(get_current_user),
    session_service=Depends(get_session_service),
):
    """
    获取指定会话的详细信息，包含消息列表

    需要有效的 JWT Token。

    Args:
        session_id: 会话 ID
        page: 消息页码（从 1 开始）
        page_size: 每页消息数（1-50）

    Returns:
        会话详情，包含基本信息（id、title、category 等）和消息列表（messages）
    """
    try:
        detail = await session_service.get_detail(
            session_id=session_id,
            page=page,
            page_size=page_size,
        )

        if detail is None:
            raise HTTPException(
                status_code=404,
                detail=error_response(errcode.CodeSessionNotFound),
            )

        logger.info(f"获取会话详情成功: session_id={session_id}")
        return success_response(detail)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话详情异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(errcode.CodeInternalError),
        )


# ==================== 删除会话 ====================

@router.delete("/{session_id}", summary="删除指定会话")
async def delete_session(
    session_id: str,
    request: Request,
    current_user=Depends(get_current_user),
    session_service=Depends(get_session_service),
):
    """
    删除指定的会话（软删除）

    需要有效的 JWT Token。
    仅允许删除属于当前用户的会话。

    Args:
        session_id: 会话 ID

    Returns:
        删除结果
    """
    try:
        user_id = current_user["user_id"]
        success = await session_service.delete(session_id, user_id)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=error_response(errcode.CodeSessionNotFound),
            )

        logger.info(f"会话删除成功: session_id={session_id}, user_id={user_id}")
        return success_response({"message": "会话已删除"})

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除会话异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(errcode.CodeInternalError),
        )
