"""
services/auth_service 模块单元测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId
from services.auth_service import AuthService, hash_password, verify_password


class TestHashPassword:
    """密码哈希工具函数测试"""

    def test_hash_and_verify(self):
        """哈希后可验证匹配"""
        hashed = hash_password("mypassword123")
        assert hashed != "mypassword123"
        assert verify_password("mypassword123", hashed) is True

    def test_verify_wrong_password(self):
        """错误密码验证失败"""
        hashed = hash_password("correct")
        assert verify_password("wrong", hashed) is False

    def test_hash_is_unique(self):
        """相同密码生成不同哈希（salt）"""
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2


class TestAuthService:
    """认证服务单元测试（mock MongoDB）"""

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.users = MagicMock()
        db.users.find_one = AsyncMock()
        db.users.insert_one = AsyncMock()
        db.users.update_one = AsyncMock()
        return db

    @pytest.fixture
    def auth_svc(self, mock_db):
        with patch("services.auth_service.load_config") as mock_config:
            mock_settings = MagicMock()
            mock_settings.jwt_secret = "test-secret-32chars-x"
            mock_settings.jwt_access_ttl = 3600
            mock_settings.jwt_refresh_ttl = 86400
            mock_config.return_value = mock_settings
            return AuthService(mock_db)

    @pytest.mark.asyncio
    async def test_register_success(self, auth_svc, mock_db):
        """UT-AS-01: 注册新用户成功"""
        mock_db.users.find_one.return_value = None
        mock_db.users.insert_one.return_value = MagicMock(inserted_id=ObjectId())

        result = await auth_svc.register("newuser123", "password123", agree_terms=True)

        assert "access_token" in result
        assert "refresh_token" in result
        assert result["user"]["username"] == "newuser123"
        mock_db.users.insert_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, auth_svc, mock_db):
        """UT-AS-02: 用户名已存在 → ValueError"""
        mock_db.users.find_one.return_value = {"username": "existing"}

        with pytest.raises(ValueError, match="已被注册"):
            await auth_svc.register("existing", "password123", agree_terms=True)

    @pytest.mark.asyncio
    async def test_register_short_username(self, auth_svc, mock_db):
        """UT-AS-03: 用户名过短(<3) → ValueError"""
        with pytest.raises(ValueError, match="用户名"):
            await auth_svc.register("ab", "password123", agree_terms=True)

    @pytest.mark.asyncio
    async def test_register_short_password(self, auth_svc, mock_db):
        """UT-AS-04: 密码过短(<6) → ValueError"""
        with pytest.raises(ValueError, match="密码"):
            await auth_svc.register("validuser", "12345", agree_terms=True)

    @pytest.mark.asyncio
    async def test_login_success(self, auth_svc, mock_db):
        """UT-AS-05: 正确凭据登录成功"""
        hashed = hash_password("correct123")
        mock_db.users.find_one.return_value = {
            "_id": ObjectId(),
            "username": "testuser",
            "password_hash": hashed,
            "nickname": "测试",
            "avatar_url": "",
            "status": 1,
        }

        result = await auth_svc.login("testuser", "correct123", agree_terms=True)

        assert "access_token" in result
        assert result["user"]["username"] == "testuser"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, auth_svc, mock_db):
        """UT-AS-06: 错误密码 → ValueError"""
        hashed = hash_password("correct123")
        mock_db.users.find_one.return_value = {
            "_id": ObjectId(),
            "username": "testuser",
            "password_hash": hashed,
            "status": 1,
        }

        with pytest.raises(ValueError, match="用户名或密码"):
            await auth_svc.login("testuser", "wrong_password")

    @pytest.mark.asyncio
    async def test_login_user_not_found(self, auth_svc, mock_db):
        """UT-AS-07: 用户不存在 → ValueError"""
        mock_db.users.find_one.return_value = None

        with pytest.raises(ValueError, match="用户名或密码"):
            await auth_svc.login("nouser", "password123")

    @pytest.mark.asyncio
    async def test_login_disabled_user(self, auth_svc, mock_db):
        """UT-AS-08: 已禁用用户(status!=1) → ValueError"""
        hashed = hash_password("password123")
        mock_db.users.find_one.return_value = {
            "_id": ObjectId(),
            "username": "disabled_user",
            "password_hash": hashed,
            "status": 0,  # 禁用
        }

        with pytest.raises(ValueError, match="禁用"):
            await auth_svc.login("disabled_user", "password123")

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, auth_svc, mock_db):
        """UT-AS-09: 有效 refresh_token 刷新成功"""
        from utils.jwt_utils import create_refresh_token

        # 使用与 auth_svc 相同的 mock secret
        refresh_token = create_refresh_token(
            "user123", "alice",
            secret="test-secret-32chars-x",
            refresh_ttl=86400,
        )
        mock_db.users.find_one.return_value = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "status": 1,
        }

        # 还需要 patch jwt_utils._get_config 以便 decode_token 使用相同密钥
        with patch("services.auth_service.decode_token") as mock_decode:
            mock_decode.return_value = {
                "user_id": "507f1f77bcf86cd799439011",
                "username": "alice",
                "type": "refresh",
            }
            result = await auth_svc.refresh_token(refresh_token)

        assert "access_token" in result
        assert "refresh_token" in result

    @pytest.mark.asyncio
    async def test_refresh_token_with_access_token(self, auth_svc, mock_db):
        """UT-AS-10: 用access_token刷新 → ValueError"""
        from utils.jwt_utils import create_access_token
        access_token = create_access_token(
            "user123", "alice",
            secret="test-secret-32chars-x",
            access_ttl=3600,
        )

        with pytest.raises(ValueError, match="无效"):
            await auth_svc.refresh_token(access_token)

    @pytest.mark.asyncio
    async def test_refresh_token_expired(self, auth_svc, mock_db):
        """UT-AS-11: 过期 refresh_token → ValueError"""
        import time
        import jwt

        payload = {
            "user_id": "user123",
            "username": "alice",
            "sub": "user123",
            "type": "refresh",
            "iat": int(time.time()) - 172800,
            "exp": int(time.time()) - 86400,  # 昨天过期
            "iss": "ai-law-assistant",
        }
        expired_token = jwt.encode(payload, "test-secret-32chars-x", algorithm="HS256")

        with pytest.raises(ValueError, match="过期|无效"):
            await auth_svc.refresh_token(expired_token)

    @pytest.mark.asyncio
    async def test_logout_no_error(self, auth_svc):
        """退出登录不抛异常"""
        result = await auth_svc.logout()
        assert result is None
