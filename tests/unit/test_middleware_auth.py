"""
middleware/auth 模块单元测试
直接测试 get_current_user 和 get_optional_user 函数
"""
import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))


class TestGetCurrentUser:
    """JWT 认证 get_current_user 测试"""

    @pytest.fixture
    def mock_settings(self):
        s = MagicMock()
        s.jwt_secret = "test-secret"
        return s

    @pytest.mark.asyncio
    async def test_no_auth_header(self, mock_settings):
        """无 Authorization 头 → 401"""
        from middleware.auth import get_current_user
        from fastapi import HTTPException

        request = MagicMock()
        request.headers = {}

        with pytest.raises(HTTPException) as exc:
            await get_current_user(request, settings=mock_settings)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_token(self, mock_settings):
        """有效 Token → 返回用户信息"""
        from middleware.auth import get_current_user

        request = MagicMock()
        request.headers = {"Authorization": "Bearer valid-token"}

        with patch("middleware.auth.decode_token") as mock_decode:
            mock_decode.return_value = {
                "user_id": "507f1f77bcf86cd799439011",
                "username": "testuser",
            }
            result = await get_current_user(request, settings=mock_settings)
            assert result["user_id"] == "507f1f77bcf86cd799439011"

    @pytest.mark.asyncio
    async def test_expired_token(self, mock_settings):
        """过期 Token → 401"""
        import jwt
        from middleware.auth import get_current_user
        from fastapi import HTTPException

        request = MagicMock()
        request.headers = {"Authorization": "Bearer expired-token"}

        with patch("middleware.auth.decode_token") as mock_decode:
            mock_decode.side_effect = jwt.ExpiredSignatureError
            with pytest.raises(HTTPException) as exc:
                await get_current_user(request, settings=mock_settings)
            assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token(self, mock_settings):
        """无效 Token → 401"""
        import jwt
        from middleware.auth import get_current_user
        from fastapi import HTTPException

        request = MagicMock()
        request.headers = {"Authorization": "Bearer bad-token"}

        with patch("middleware.auth.decode_token") as mock_decode:
            mock_decode.side_effect = jwt.InvalidTokenError
            with pytest.raises(HTTPException) as exc:
                await get_current_user(request, settings=mock_settings)
            assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_malformed_auth_header(self, mock_settings):
        """格式错误的 Authorization 头 → 401"""
        from middleware.auth import get_current_user
        from fastapi import HTTPException

        request = MagicMock()
        request.headers = {"Authorization": "InvalidFormat"}

        with pytest.raises(HTTPException) as exc:
            await get_current_user(request, settings=mock_settings)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_not_bearer_scheme(self, mock_settings):
        """非 Bearer scheme → 401"""
        from middleware.auth import get_current_user
        from fastapi import HTTPException

        request = MagicMock()
        request.headers = {"Authorization": "Basic dXNlcjpwYXNz"}

        with pytest.raises(HTTPException) as exc:
            await get_current_user(request, settings=mock_settings)
        assert exc.value.status_code == 401


class TestGetOptionalUser:
    """JWT 可选认证 get_optional_user 测试"""

    @pytest.fixture
    def mock_settings(self):
        s = MagicMock()
        s.jwt_secret = "test-secret"
        return s

    @pytest.mark.asyncio
    async def test_no_token_returns_none(self, mock_settings):
        """无 Token → None"""
        from middleware.auth import get_optional_user

        request = MagicMock()
        request.headers = {}
        result = await get_optional_user(request, settings=mock_settings)
        assert result is None

    @pytest.mark.asyncio
    async def test_valid_token_returns_user(self, mock_settings):
        """有效 Token → 返回用户"""
        from middleware.auth import get_optional_user

        request = MagicMock()
        request.headers = {"Authorization": "Bearer valid-token"}

        with patch("middleware.auth.decode_token") as mock_decode:
            mock_decode.return_value = {"user_id": "uid", "username": "u"}
            result = await get_optional_user(request, settings=mock_settings)
            assert result is not None
            assert result["user_id"] == "uid"

    @pytest.mark.asyncio
    async def test_invalid_token_returns_none(self, mock_settings):
        """无效 Token → None (不抛异常)"""
        import jwt
        from middleware.auth import get_optional_user

        request = MagicMock()
        request.headers = {"Authorization": "Bearer invalid-token"}

        with patch("middleware.auth.decode_token") as mock_decode:
            mock_decode.side_effect = jwt.InvalidTokenError
            result = await get_optional_user(request, settings=mock_settings)
            assert result is None

    @pytest.mark.asyncio
    async def test_malformed_auth_returns_none(self, mock_settings):
        """格式错误 → None"""
        from middleware.auth import get_optional_user

        request = MagicMock()
        request.headers = {"Authorization": "badheader"}
        result = await get_optional_user(request, settings=mock_settings)
        assert result is None
