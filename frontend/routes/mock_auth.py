"""本地模拟认证 API — 绕过 Go 后端，提供注册/登录功能"""

import hashlib
import json
import os
import secrets
import time
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException

router = APIRouter()

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "users.json"

# JWT-like token (简化版，用 HMAC-SHA256 签名)
SECRET = secrets.token_hex(32)


def _load_users():
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return {}


def _save_users(users):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(users, ensure_ascii=False, indent=2), encoding="utf-8")


def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return f"pbkdf2:{salt}:{h.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    parts = stored.split(":")
    if len(parts) != 3 or parts[0] != "pbkdf2":
        return False
    salt = parts[1]
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return h.hex() == parts[2]


def _generate_token(user_id: int, username: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"user_id": user_id, "username": username, "exp": int(time.time()) + 86400, "iat": int(time.time())}
    h = hashlib.sha256
    b64 = lambda d: __import__("base64").urlsafe_b64encode(d).rstrip(b"=").decode()
    header_b64 = b64(json.dumps(header).encode())
    payload_b64 = b64(json.dumps(payload).encode())
    sig_raw = f"{header_b64}.{payload_b64}".encode()
    sig = h(sig_raw + SECRET.encode()).hexdigest()
    return f"{header_b64}.{payload_b64}.{sig}"


def _parse_token(token: str) -> dict | None:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig = parts
        b64 = lambda d: __import__("base64").urlsafe_b64decode(d + "=" * (len(d) % 4))
        sig_check = hashlib.sha256(f"{header_b64}.{payload_b64}".encode() + SECRET.encode()).hexdigest()
        if sig != sig_check:
            return None
        payload = json.loads(b64(payload_b64))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


@router.post("/api/v1/proxy/auth/register")
async def register(request: Request):
    body = await request.json()
    username = body.get("username", "").strip()
    password = body.get("password", "")
    confirm_password = body.get("confirm_password", "")
    agree_terms = body.get("agree_terms", False)

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

    user_id = int(time.time() * 1000)
    users[str(user_id)] = {
        "id": user_id,
        "username": username,
        "password_hash": _hash_password(password),
        "nickname": username,
        "avatar_url": "",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    _save_users(users)

    token = _generate_token(user_id, username)
    refresh_token = _generate_token(user_id + 1, username)
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
    body = await request.json()
    username = body.get("username", "").strip()
    password = body.get("password", "")
    agree_terms = body.get("agree_terms", False)

    if not username or not password:
        raise HTTPException(400, detail="用户名和密码不能为空")
    if not agree_terms:
        raise HTTPException(400, detail="请先同意用户协议")

    users = _load_users()
    matched = None
    for u in users.values():
        if u["username"] == username:
            matched = u
            break

    if not matched or not _verify_password(password, matched["password_hash"]):
        return {"code": 40104, "message": "用户名或密码错误", "data": None}

    token = _generate_token(matched["id"], matched["username"])
    refresh_token = _generate_token(matched["id"] + 1, matched["username"])
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


@router.get("/api/v1/proxy/user/profile")
async def get_profile(request: Request):
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
    nickname = body.get("nickname", "").strip()
    if nickname:
        user["nickname"] = nickname
    avatar_url = body.get("avatar_url", "").strip()
    if avatar_url:
        user["avatar_url"] = avatar_url
    _save_users(users)
    return {"code": 0, "message": "更新成功", "data": None}


@router.put("/api/v1/proxy/user/privacy")
async def update_privacy(request: Request):
    token = request.headers.get("authorization", "").replace("Bearer ", "")
    payload = _parse_token(token)
    if not payload:
        return {"code": 40100, "message": "未登录或登录已过期", "data": None}
    return {"code": 0, "message": "隐私设置已更新", "data": None}


@router.post("/api/v1/proxy/auth/refresh")
async def refresh_token(request: Request):
    body = await request.json()
    refresh_token_str = body.get("refresh_token", "")
    # 简单返回新 token
    payload = _parse_token(refresh_token_str)
    username = payload["username"] if payload else "user"
    uid = payload["user_id"] if payload else 999
    token = _generate_token(uid, username)
    refresh = _generate_token(uid + 1, username)
    return {
        "code": 0,
        "message": "ok",
        "data": {"access_token": token, "refresh_token": refresh, "expires_in": 86400},
    }


@router.post("/api/v1/proxy/auth/logout")
async def logout(request: Request):
    return {"code": 0, "message": "已退出登录", "data": None}
