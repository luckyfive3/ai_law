"""
AI法律助手 v1.0 — JWT 工具函数
基于 PyJWT 实现 Token 编解码
"""
import time
import jwt
from typing import Dict, Any


def create_access_token(user_id: str, username: str, secret: str, access_ttl: int) -> str:
    """
    创建访问令牌 (Access Token)

    Args:
        user_id: 用户ID
        username: 用户名
        secret: JWT 密钥
        access_ttl: 过期时间（秒），默认 24h

    Returns:
        JWT token 字符串
    """
    now = int(time.time())
    payload = {
        "user_id": user_id,
        "username": username,
        "sub": str(user_id),
        "iat": now,
        "exp": now + access_ttl,
        "iss": "ai-law-assistant",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def create_refresh_token(user_id: str, username: str, secret: str, refresh_ttl: int) -> str:
    """
    创建刷新令牌 (Refresh Token)

    Args:
        user_id: 用户ID
        username: 用户名
        secret: JWT 密钥
        refresh_ttl: 过期时间（秒），默认 7d

    Returns:
        JWT token 字符串
    """
    now = int(time.time())
    payload = {
        "user_id": user_id,
        "username": username,
        "sub": str(user_id),
        "iat": now,
        "exp": now + refresh_ttl,
        "iss": "ai-law-assistant",
        "type": "refresh",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_token(token: str, secret: str) -> Dict[str, Any]:
    """
    解码并验证 JWT Token

    Args:
        token: JWT token 字符串
        secret: JWT 密钥

    Returns:
        dict: 包含 user_id、username 等字段的 payload

    Raises:
        jwt.ExpiredSignatureError: Token 已过期
        jwt.InvalidTokenError: Token 无效
    """
    payload = jwt.decode(
        token,
        secret,
        algorithms=["HS256"],
        options={"require": ["exp", "sub"]},
    )
    return {
        "user_id": payload.get("user_id") or payload.get("sub"),
        "username": payload.get("username", ""),
        "exp": payload.get("exp"),
    }
