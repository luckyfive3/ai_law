"""
AI法律助手 v1.0 — 用户 API 路由
提供用户个人资料查询、更新和隐私设置接口
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request

from middleware.auth import get_current_user
from schemas.request import UpdateProfileRequest, UpdatePrivacyRequest
from schemas.response import success_response, error_response
from utils import errcode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/user", tags=["用户"])


# ==================== 依赖注入 ====================

def get_user_service(request: Request):
    """
    从应用状态中获取 UserService 实例
    该实例在 main.py 启动时被注册到 app.state.services 中
    """
    return request.app.state.services["user_service"]


# ==================== 获取个人资料 ====================

@router.get("/profile", summary="获取用户个人资料")
async def get_profile(
    request: Request,
    current_user=Depends(get_current_user),
    user_service=Depends(get_user_service),
):
    """
    获取当前登录用户的个人资料

    需要有效的 JWT Token（通过 Bearer 方式传递）。

    Returns:
        用户信息包含 id、username、nickname、avatar_url、privacy_save_history、created_at
    """
    try:
        user_id = current_user["user_id"]
        profile = await user_service.get_profile(user_id)

        logger.info(f"获取用户资料成功: user_id={user_id}")
        return success_response(profile)

    except ValueError as e:
        logger.warning(f"获取用户资料失败: {e}")
        raise HTTPException(
            status_code=404,
            detail=error_response(errcode.CodeUserNotFound),
        )
    except Exception as e:
        logger.error(f"获取用户资料异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(errcode.CodeInternalError),
        )


# ==================== 更新个人资料 ====================

@router.put("/profile", summary="更新用户个人资料")
async def update_profile(
    req: UpdateProfileRequest,
    request: Request,
    current_user=Depends(get_current_user),
    user_service=Depends(get_user_service),
):
    """
    更新当前登录用户的个人资料

    可更新字段：nickname（昵称）、avatar_url（头像 URL）。
    需要有效的 JWT Token。

    Args:
        req: 更新请求体，包含可选的 nickname 和 avatar_url

    Returns:
        更新后的完整用户信息
    """
    try:
        user_id = current_user["user_id"]

        # 构建要更新的字段字典（只传递非 None 的字段）
        updates = {}
        if req.nickname is not None:
            updates["nickname"] = req.nickname
        if req.avatar_url is not None:
            updates["avatar_url"] = req.avatar_url

        if not updates:
            raise HTTPException(
                status_code=400,
                detail=error_response(errcode.CodeInvalidParam, "没有提供需要更新的字段"),
            )

        result = await user_service.update_profile(user_id, updates)

        logger.info(f"用户资料更新成功: user_id={user_id}")
        return success_response(result)

    except ValueError as e:
        logger.warning(f"更新用户资料失败: {e}")
        raise HTTPException(
            status_code=400,
            detail=error_response(errcode.CodeInvalidParam, str(e)),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新用户资料异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(errcode.CodeInternalError),
        )


# ==================== 更新隐私设置 ====================

@router.put("/privacy", summary="更新隐私设置")
async def update_privacy(
    req: UpdatePrivacyRequest,
    request: Request,
    current_user=Depends(get_current_user),
    user_service=Depends(get_user_service),
):
    """
    更新当前登录用户的隐私设置

    目前支持设置：privacy_save_history（是否保存对话历史）。
    需要有效的 JWT Token。

    Args:
        req: 隐私设置请求体，包含 privacy_save_history

    Returns:
        更新后的隐私设置状态
    """
    try:
        user_id = current_user["user_id"]
        result = await user_service.update_privacy(
            user_id,
            req.privacy_save_history,
        )

        logger.info(f"隐私设置更新成功: user_id={user_id}")
        return success_response(result)

    except ValueError as e:
        logger.warning(f"更新隐私设置失败: {e}")
        raise HTTPException(
            status_code=404,
            detail=error_response(errcode.CodeUserNotFound),
        )
    except Exception as e:
        logger.error(f"更新隐私设置异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(errcode.CodeInternalError),
        )
