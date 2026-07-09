"""本地模拟认证 API — 绕过 Python 后端，提供注册/登录功能
用于开发环境，无需启动后端服务即可进行前后端联调
用户数据存储在本地 JSON 文件中，JWT Token 由前端自行签发"""

import hashlib
import json
import os
import secrets
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException

router = APIRouter()

# 用户数据存储文件
DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "users.json"

# JWT 签名密钥（与后端 .env 中的 JWT_SECRET 保持一致）
SECRET = "dev-jwt-secret-change-in-production-32chars"


def _load_users() -> dict:
    """从本地 JSON 文件加载用户数据"""
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return {}


def _save_users(users: dict):
    """将用户数据保存到本地 JSON 文件"""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(users, ensure_ascii=False, indent=2), encoding="utf-8")


def _hash_password(password: str) -> str:
    """使用 PBKDF2-SHA256 对密码进行哈希处理"""
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return f"pbkdf2:{salt}:{h.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    """验证密码是否与存储的哈希值匹配"""
    parts = stored.split(":")
    if len(parts) != 3 or parts[0] != "pbkdf2":
        return False
    salt = parts[1]
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return h.hex() == parts[2]


def _generate_token(user_id: str, username: str) -> str:
    """生成标准 JWT Token（HMAC-SHA256，兼容 PyJWT 后端验证）
    user_id 为 MongoDB 风格的十六进制字符串（UUID 格式）"""
    import hmac as _hmac
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "user_id": user_id,
        "username": username,
        "sub": str(user_id),
        "exp": int(time.time()) + 86400,  # 24 小时过期
        "iat": int(time.time()),
        "iss": "ai-law-assistant",
    }
    b64 = lambda d: __import__("base64").urlsafe_b64encode(d).rstrip(b"=").decode()
    header_b64 = b64(json.dumps(header).encode())
    payload_b64 = b64(json.dumps(payload).encode())
    sig_raw = f"{header_b64}.{payload_b64}".encode()
    # 标准 HMAC-SHA256 签名 → base64url（与 PyJWT 一致）
    sig = b64(_hmac.new(SECRET.encode(), sig_raw, hashlib.sha256).digest())
    return f"{header_b64}.{payload_b64}.{sig}"


def _parse_token(token: str) -> dict | None:
    """解析 JWT Token，验证签名和过期时间"""
    import hmac as _hmac
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig = parts
        b64d = lambda d: __import__("base64").urlsafe_b64decode(d + "=" * (len(d) % 4))
        b64e = lambda d: __import__("base64").urlsafe_b64encode(d).rstrip(b"=").decode()
        # 标准 HMAC-SHA256 验证（与 PyJWT 一致）
        sig_raw = f"{header_b64}.{payload_b64}".encode()
        sig_check = b64e(_hmac.new(SECRET.encode(), sig_raw, hashlib.sha256).digest())
        if sig != sig_check:
            return None
        payload = json.loads(b64d(payload_b64))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


def _generate_user_id() -> str:
    """生成 MongoDB 风格的 UUID 用户 ID（24 位十六进制字符串）"""
    return uuid.uuid4().hex[:24]


# ========== 认证相关接口 ==========


@router.post("/api/v1/proxy/auth/register")
async def register(request: Request):
    """用户注册"""
    body = await request.json()
    username = body.get("username", "").strip()
    password = body.get("password", "")
    confirm_password = body.get("confirm_password", "")
    agree_terms = body.get("agree_terms", False)

    # 参数校验
    if not username or len(username) < 2 or len(username) > 50:
        raise HTTPException(400, detail="用户名格式错误（2-50个字符）")
    if not password or len(password) < 6:
        raise HTTPException(400, detail="密码至少6个字符")
    if password != confirm_password:
        raise HTTPException(400, detail="两次输入的密码不一致")
    if not agree_terms:
        raise HTTPException(400, detail="请先同意用户协议")

    users = _load_users()

    # 检查用户名是否已存在
    for u in users.values():
        if u["username"] == username:
            return {"code": 40009, "message": "用户名已存在", "data": None}

    # 生成 MongoDB 风格的 UUID 用户 ID
    user_id = _generate_user_id()
    users[user_id] = {
        "id": user_id,
        "username": username,
        "password_hash": _hash_password(password),
        "nickname": username,
        "avatar_url": "",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    _save_users(users)

    # 生成访问令牌和刷新令牌
    token = _generate_token(user_id, username)
    refresh_token = _generate_token(_generate_user_id(), username)
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "access_token": token,
            "refresh_token": refresh_token,
            "expires_in": 86400,
            "user": {"id": user_id, "username": username, "nickname": username, "avatar_url": ""},
        },
    }


@router.post("/api/v1/proxy/auth/login")
async def login(request: Request):
    """用户登录"""
    body = await request.json()
    username = body.get("username", "").strip()
    password = body.get("password", "")
    agree_terms = body.get("agree_terms", False)

    # 参数校验
    if not username or not password:
        raise HTTPException(400, detail="用户名和密码不能为空")
    if not agree_terms:
        raise HTTPException(400, detail="请先同意用户协议")

    users = _load_users()

    # 按用户名查找用户
    matched = None
    for u in users.values():
        if u["username"] == username:
            matched = u
            break

    if not matched or not _verify_password(password, matched["password_hash"]):
        return {"code": 40104, "message": "用户名或密码错误", "data": None}

    # 生成访问令牌和刷新令牌
    token = _generate_token(matched["id"], matched["username"])
    refresh_token = _generate_token(_generate_user_id(), matched["username"])
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "access_token": token,
            "refresh_token": refresh_token,
            "expires_in": 86400,
            "user": {
                "id": matched["id"],
                "username": matched["username"],
                "nickname": matched["nickname"],
                "avatar_url": matched.get("avatar_url", ""),
            },
        },
    }


# ========== 用户信息相关接口 ==========


@router.get("/api/v1/proxy/user/profile")
async def get_profile(request: Request):
    """获取当前登录用户信息"""
    token = request.headers.get("authorization", "").replace("Bearer ", "")
    payload = _parse_token(token)
    if not payload:
        return {"code": 40100, "message": "未登录或登录已过期", "data": None}

    users = _load_users()
    user = users.get(str(payload["user_id"]))
    if not user:
        return {"code": 40402, "message": "用户不存在", "data": None}

    return {
        "code": 0,
        "message": "ok",
        "data": {
            "id": user["id"],
            "username": user["username"],
            "nickname": user["nickname"],
            "avatar_url": user.get("avatar_url", ""),
        },
    }


@router.put("/api/v1/proxy/user/profile")
async def update_profile(request: Request):
    """更新用户个人资料（昵称、头像）"""
    token = request.headers.get("authorization", "").replace("Bearer ", "")
    payload = _parse_token(token)
    if not payload:
        return {"code": 40100, "message": "未登录或登录已过期", "data": None}

    body = await request.json()
    users = _load_users()
    uid = str(payload["user_id"])
    user = users.get(uid)
    if not user:
        return {"code": 40402, "message": "用户不存在", "data": None}

    # 更新昵称
    nickname = body.get("nickname", "").strip()
    if nickname:
        user["nickname"] = nickname

    # 更新头像 URL
    avatar_url = body.get("avatar_url", "").strip()
    if avatar_url:
        user["avatar_url"] = avatar_url

    _save_users(users)
    return {"code": 0, "message": "更新成功", "data": None}


@router.put("/api/v1/proxy/user/privacy")
async def update_privacy(request: Request):
    """更新用户隐私设置（当前为占位接口）"""
    token = request.headers.get("authorization", "").replace("Bearer ", "")
    payload = _parse_token(token)
    if not payload:
        return {"code": 40100, "message": "未登录或登录已过期", "data": None}
    return {"code": 0, "message": "隐私设置已更新", "data": None}


# ========== Token 管理接口 ==========


@router.post("/api/v1/proxy/auth/refresh")
async def refresh_token(request: Request):
    """刷新访问令牌"""
    body = await request.json()
    refresh_token_str = body.get("refresh_token", "")

    # 解析刷新令牌获取用户信息
    payload = _parse_token(refresh_token_str)
    username = payload["username"] if payload else "user"
    uid = payload["user_id"] if payload else _generate_user_id()

    # 生成新的访问令牌和刷新令牌
    token = _generate_token(uid, username)
    refresh = _generate_token(_generate_user_id(), username)
    return {
        "code": 0,
        "message": "ok",
        "data": {"access_token": token, "refresh_token": refresh, "expires_in": 86400},
    }


@router.post("/api/v1/proxy/auth/logout")
async def logout(request: Request):
    """用户退出登录"""
    return {"code": 0, "message": "已退出登录", "data": None}
