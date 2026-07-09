"""
AI法律助手 v1.0 — JWT 认证中间件

提供 FastAPI 依赖注入式的认证功能：
- get_current_user: 强制认证，无有效 Token 返回 401
- get_optional_user: 可选认证，无 Token 时返回 None
"""
import jwt
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, Depends
from config import Settings
from utils.jwt_utils import decode_token
from utils import errcode


async def _get_settings(request: Request) -> Settings:
    """从应用状态中获取配置"""
    return request.app.state.settings


async def get_current_user(request: Request, settings: Settings = Depends(_get_settings)) -> Dict[str, Any]:
    """
    JWT 认证依赖函数（强制）
    
    从请求头 Authorization 中提取 Bearer Token，
    解码并验证 JWT，返回包含 user_id 和 username 的字典。

    Args:
        request: FastAPI 请求对象
        settings: 应用配置

    Returns:
        dict: {"user_id": str, "username": str}

    Raises:
        HTTPException: Token 缺失、无效或过期时返回 401
    """
    # 提取 Authorization 头
    auth_header: Optional[str] = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=401,
            detail={
                "code": errcode.CodeUnauthorized,
                "message": errcode.get_message(errcode.CodeUnauthorized),
            },
        )

    # 解析 Bearer Token
    parts = auth_header.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail={
                "code": errcode.CodeTokenInvalid,
                "message": errcode.get_message(errcode.CodeTokenInvalid),
            },
        )

    token = parts[1]

    # 解码并验证 Token
    try:
        user_info = decode_token(token, settings.jwt_secret)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail={
                "code": errcode.CodeTokenExpired,
                "message": errcode.get_message(errcode.CodeTokenExpired),
            },
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail={
                "code": errcode.CodeTokenInvalid,
                "message": errcode.get_message(errcode.CodeTokenInvalid),
            },
        )

    return user_info


async def get_optional_user(request: Request, settings: Settings = Depends(_get_settings)) -> Optional[Dict[str, Any]]:
    """
    JWT 认证依赖函数（可选）
    
    与 get_current_user 类似，但 Token 缺失或无效时不抛出异常，
    而是返回 None。

    Args:
        request: FastAPI 请求对象
        settings: 应用配置

    Returns:
        dict | None: 认证成功返回用户信息，否则返回 None
    """
    auth_header: Optional[str] = request.headers.get("Authorization")
    if not auth_header:
        return None

    parts = auth_header.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    token = parts[1]

    try:
        return decode_token(token, settings.jwt_secret)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
