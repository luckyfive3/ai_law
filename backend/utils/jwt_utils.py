"""
AI法律助手 v1.0 — JWT 工具函数
基于 PyJWT 实现 Token 编解码
"""
import time
import jwt
from typing import Dict, Any


def _get_config():
    """获取 JWT 配置（延迟导入避免循环依赖）"""
    from config import load_config
    cfg = load_config()
    return cfg.jwt_secret, cfg.jwt_access_ttl, cfg.jwt_refresh_ttl


def create_access_token(user_id: str, username: str, secret: str = None, access_ttl: int = None) -> str:
    """创建访问令牌 (Access Token)"""
    if secret is None or access_ttl is None:
        secret, access_ttl, _ = _get_config()
    now = int(time.time())
    payload = {
        "user_id": user_id, "username": username, "sub": str(user_id),
        "iat": now, "exp": now + access_ttl, "iss": "ai-law-assistant",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def create_refresh_token(user_id: str, username: str, secret: str = None, refresh_ttl: int = None) -> str:
    """创建刷新令牌 (Refresh Token)"""
    if secret is None or refresh_ttl is None:
        secret, _, refresh_ttl = _get_config()
    now = int(time.time())
    payload = {
        "user_id": user_id, "username": username, "sub": str(user_id),
        "iat": now, "exp": now + refresh_ttl, "iss": "ai-law-assistant", "type": "refresh",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_token(token: str, secret: str = None) -> Dict[str, Any]:
    """解码并验证 JWT Token"""
    if secret is None:
        secret, _, _ = _get_config()
    payload = jwt.decode(token, secret, algorithms=["HS256"],
                         options={"require": ["exp", "sub"]})
    return {
        "user_id": payload.get("user_id") or payload.get("sub"),
        "username": payload.get("username", ""),
        "exp": payload.get("exp"),
        "type": payload.get("type", "access"),
    }
