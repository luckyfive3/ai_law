"""
加密工具模块
提供密码哈希、手机号加密与脱敏功能
"""

import hashlib
from passlib.hash import bcrypt


def hash_password(password: str) -> str:
    """
    使用 bcrypt 算法对密码进行哈希处理

    Args:
        password: 明文密码

    Returns:
        bcrypt 哈希后的密码字符串
    """
    return bcrypt.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """
    验证明文密码是否与哈希值匹配

    Args:
        plain: 明文密码
        hashed: bcrypt 哈希后的密码字符串

    Returns:
        匹配返回 True，否则返回 False
    """
    return bcrypt.verify(plain, hashed)


def hash_phone(phone: str) -> str:
    """
    使用 SHA256 对手机号进行哈希处理（用于脱敏存储）

    Args:
        phone: 明文手机号

    Returns:
        SHA256 哈希后的十六进制字符串
    """
    return hashlib.sha256(phone.encode("utf-8")).hexdigest()


def mask_phone(phone: str) -> str:
    """
    对手机号进行脱敏处理，显示格式为 138****1234

    Args:
        phone: 完整手机号（11位）

    Returns:
        脱敏后的手机号字符串，如 138****1234
    """
    if not phone or len(phone) < 7:
        return phone or ""

    return phone[:3] + "****" + phone[-4:]
