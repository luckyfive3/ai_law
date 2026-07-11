"""
utils/jwt_utils 模块单元测试
"""
import time
import pytest
import jwt
from unittest.mock import patch
from utils.jwt_utils import create_access_token, create_refresh_token, decode_token


SECRET = "test-secret-32chars-minimum!!"
ACCESS_TTL = 3600
REFRESH_TTL = 86400


class TestJWTUtils:
    """JWT 工具函数测试"""

    def test_create_access_token_valid(self):
        """UT-JWT-01: 生成的 access_token 可正确解码"""
        token = create_access_token("user123", "alice", secret=SECRET, access_ttl=ACCESS_TTL)
        payload = jwt.decode(token, SECRET, algorithms=["HS256"])

        assert payload["user_id"] == "user123"
        assert payload["username"] == "alice"
        assert payload["sub"] == "user123"
        assert payload["iss"] == "ai-law-assistant"
        assert "exp" in payload
        assert "iat" in payload

    def test_create_refresh_token_has_type(self):
        """UT-JWT-02: refresh_token payload 含 type='refresh'"""
        token = create_refresh_token("user123", "alice", secret=SECRET, refresh_ttl=REFRESH_TTL)
        payload = jwt.decode(token, SECRET, algorithms=["HS256"])

        assert payload["type"] == "refresh"
        assert payload["user_id"] == "user123"

    def test_decode_token_normal(self):
        """UT-JWT-03: decode_token 返回完整 payload"""
        token = create_access_token("user456", "bob", secret=SECRET, access_ttl=ACCESS_TTL)
        result = decode_token(token, secret=SECRET)

        assert result["user_id"] == "user456"
        assert result["username"] == "bob"
        assert result["type"] == "access"
        assert "exp" in result

    def test_decode_token_expired(self):
        """UT-JWT-04: 过期 token 抛出 ExpiredSignatureError"""
        # 创建一个已过期的token（exp在过去）
        now = int(time.time())
        payload = {
            "user_id": "user123",
            "username": "alice",
            "sub": "user123",
            "iat": now - 7200,
            "exp": now - 3600,  # 1小时前过期
            "iss": "ai-law-assistant",
        }
        token = jwt.encode(payload, SECRET, algorithm="HS256")

        with pytest.raises(jwt.ExpiredSignatureError):
            decode_token(token, secret=SECRET)

    def test_decode_token_wrong_secret(self):
        """UT-JWT-05: 错误密钥抛出 InvalidTokenError"""
        token = create_access_token("user123", "alice", secret=SECRET, access_ttl=ACCESS_TTL)

        with pytest.raises(jwt.InvalidTokenError):
            decode_token(token, secret="wrong-secret-key!!")

    def test_decode_token_tampered(self):
        """UT-JWT-06: 篡改token抛出 InvalidTokenError"""
        token = create_access_token("user123", "alice", secret=SECRET, access_ttl=ACCESS_TTL)
        # 修改最后一个字符
        tampered = token[:-1] + ("A" if token[-1] != "A" else "B")

        with pytest.raises(jwt.InvalidTokenError):
            decode_token(tampered, secret=SECRET)

    def test_access_token_expiry_set_correctly(self):
        """access_token 过期时间 = iat + access_ttl"""
        token = create_access_token("user123", "alice", secret=SECRET, access_ttl=300)
        payload = jwt.decode(token, SECRET, algorithms=["HS256"])

        assert payload["exp"] - payload["iat"] == 300

    def test_refresh_token_expiry_set_correctly(self):
        """refresh_token 过期时间 = iat + refresh_ttl"""
        token = create_refresh_token("user123", "alice", secret=SECRET, refresh_ttl=7200)
        payload = jwt.decode(token, SECRET, algorithms=["HS256"])

        assert payload["exp"] - payload["iat"] == 7200
