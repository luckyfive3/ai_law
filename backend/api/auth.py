from middleware.rate_limiter import limiter
"""
AI法律助手 v1.0 — 认证 API 路由
提供用户注册、登录、Token 刷新、退出登录接口
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request

from schemas.request import RegisterRequest, LoginRequest, RefreshTokenRequest
from schemas.response import success_response, error_response
from schemas.response import AuthResponse, UserInfo
from utils import errcode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["认证"])


# ==================== 依赖注入 ====================

def get_auth_service(request: Request):
    """
    从应用状态中获取 AuthService 实例
    该实例在 main.py 启动时被注册到 app.state.services 中
    """
    return request.app.state.services["auth_service"]


# ==================== 注册 ====================

@router.post("/register", summary="用户注册")
@limiter.limit("5/minute")
async def register(request: Request, 
    req: RegisterRequest,
    auth_service=Depends(get_auth_service),
):
    """
    用户注册接口

    校验用户名是否已被占用，密码是否一致，
    创建新用户并返回 JWT 访问令牌和刷新令牌。

    Args:
        req: 注册请求体，包含 username / password / confirm_password / agree_terms

    Returns:
        成功时返回 access_token、refresh_token、expires_in 和用户信息
    """
    try:
        result = await auth_service.register(
            username=req.username,
            password=req.password,
            agree_terms=req.agree_terms,
        )

        # 构造 AuthResponse
        auth_data = AuthResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            expires_in=result["expires_in"],
            user=UserInfo(
                id=result["user"]["id"],
                username=result["user"]["username"],
                nickname=result["user"].get("nickname", ""),
                avatar_url=result["user"].get("avatar_url", ""),
            ),
        )

        logger.info(f"用户注册成功: username={req.username}")
        return success_response(auth_data.model_dump())

    except ValueError as e:
        # 用户名已被注册或参数无效
        logger.warning(f"注册失败: {e}")
        raise HTTPException(
            status_code=400,
            detail=error_response(errcode.CodeInvalidParam, str(e)),
        )
    except Exception as e:
        logger.error(f"注册异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(errcode.CodeInternalError),
        )


# ==================== 登录 ====================

@router.post("/login", summary="用户登录")
async def login(
    req: LoginRequest,
    auth_service=Depends(get_auth_service),
):
    """
    用户登录接口

    校验用户名和密码，成功后返回 JWT 令牌。

    Args:
        req: 登录请求体，包含 username / password / agree_terms

    Returns:
        成功时返回 access_token、refresh_token、expires_in 和用户信息
    """
    try:
        result = await auth_service.login(
            username=req.username,
            password=req.password,
            agree_terms=req.agree_terms,
        )

        auth_data = AuthResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            expires_in=result["expires_in"],
            user=UserInfo(
                id=result["user"]["id"],
                username=result["user"]["username"],
                nickname=result["user"].get("nickname", ""),
                avatar_url=result["user"].get("avatar_url", ""),
            ),
        )

        logger.info(f"用户登录成功: username={req.username}")
        return success_response(auth_data.model_dump())

    except ValueError as e:
        logger.warning(f"登录失败: {e}")
        raise HTTPException(
            status_code=401,
            detail=error_response(errcode.CodeInvalidCredentials),
        )
    except Exception as e:
        logger.error(f"登录异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(errcode.CodeInternalError),
        )


# ==================== Token 刷新 ====================

@router.post("/refresh", summary="刷新 Token")
async def refresh(
    req: RefreshTokenRequest,
    auth_service=Depends(get_auth_service),
):
    """
    刷新 Token 接口

    使用有效的 Refresh Token 换取新的 Access Token 和 Refresh Token。

    Args:
        req: 刷新请求体，包含 refresh_token

    Returns:
        成功时返回新的 access_token、refresh_token 和 expires_in
    """
    try:
        result = await auth_service.refresh_token(req.refresh_token)

        logger.info("Token 刷新成功")
        return success_response(result)

    except ValueError as e:
        logger.warning(f"Token 刷新失败: {e}")
        raise HTTPException(
            status_code=401,
            detail=error_response(errcode.CodeTokenInvalid),
        )
    except Exception as e:
        logger.error(f"Token 刷新异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(errcode.CodeInternalError),
        )


# ==================== 退出登录 ====================

@router.post("/logout", summary="退出登录")
async def logout(
    auth_service=Depends(get_auth_service),
):
    """
    退出登录接口

    当前 JWT 采用无状态模式，退出登录仅做日志记录。
    未来如需实现 Token 黑名单，可在此扩展。

    Returns:
        成功消息
    """
    try:
        await auth_service.logout()
        logger.info("用户退出登录")
        return success_response({"message": "已退出登录"})

    except Exception as e:
        logger.error(f"退出登录异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(errcode.CodeInternalError),
        )
