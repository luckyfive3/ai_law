"""
utils/crypto_utils 模块单元测试
"""
import pytest
from utils.crypto_utils import hash_password, verify_password, hash_phone, mask_phone


class TestHashPassword:
    """密码哈希测试"""

    def test_hash_returns_bcrypt_string(self):
        """返回 bcrypt 格式的哈希字符串"""
        hashed = hash_password("mypassword123")
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")

    def test_same_input_different_hash(self):
        """相同输入产生不同哈希（salt 随机）"""
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2

    def test_hash_min_length(self):
        """哈希值有合理长度"""
        hashed = hash_password("pwd")
        assert len(hashed) > 20


class TestVerifyPassword:
    """密码验证测试"""

    def test_verify_correct_password(self):
        """正确密码 → True"""
        hashed = hash_password("secret123")
        assert verify_password("secret123", hashed) is True

    def test_verify_wrong_password(self):
        """错误密码 → False"""
        hashed = hash_password("secret123")
        assert verify_password("wrong_password", hashed) is False

    def test_verify_case_sensitive(self):
        """大小写敏感"""
        hashed = hash_password("Secret123")
        assert verify_password("secret123", hashed) is False


class TestHashPhone:
    """手机号哈希测试"""

    def test_hash_returns_64_char_hex(self):
        """SHA256 返回 64 字符十六进制"""
        h = hash_phone("13800138000")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_same_input_same_hash(self):
        """相同输入产生相同哈希"""
        assert hash_phone("13800138000") == hash_phone("13800138000")

    def test_different_input_different_hash(self):
        """不同手机号产生不同哈希"""
        assert hash_phone("13800138000") != hash_phone("13900139000")


class TestMaskPhone:
    """手机号脱敏测试"""

    def test_standard_11_digit(self):
        """标准 11 位手机号 → 138****1234"""
        assert mask_phone("13812341234") == "138****1234"

    def test_short_number(self):
        """短号码 → 原样返回"""
        assert mask_phone("12345") == "12345"

    def test_empty_string(self):
        """空字符串 → 空字符串"""
        assert mask_phone("") == ""

    def test_none_input(self):
        """None → 空字符串"""
        assert mask_phone(None) == ""
