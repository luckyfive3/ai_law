"""
services/user_service 模块单元测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId


class TestUserService:
    """用户资料服务单元测试"""

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.users = MagicMock()
        db.users.find_one = AsyncMock()
        db.users.update_one = AsyncMock()
        return db

    @pytest.fixture
    def svc(self, mock_db):
        from services.user_service import UserService
        return UserService(mock_db)

    USER_ID_HEX = "507f1f77bcf86cd799439011"

    # ── 获取个人信息 ──

    @pytest.mark.asyncio
    async def test_get_profile_success(self, svc, mock_db):
        """正常获取用户信息"""
        mock_db.users.find_one = AsyncMock(return_value={
            "_id": ObjectId(self.USER_ID_HEX),
            "username": "testuser",
            "nickname": "测试用户",
            "avatar_url": "https://example.com/avatar.png",
            "privacy_save_history": True,
            "created_at": "2024-01-01T00:00:00",
        })

        profile = await svc.get_profile(self.USER_ID_HEX)

        assert profile["username"] == "testuser"
        assert profile["nickname"] == "测试用户"
        assert profile["avatar_url"] == "https://example.com/avatar.png"
        assert profile["privacy_save_history"] is True

    @pytest.mark.asyncio
    async def test_get_profile_invalid_id(self, svc, mock_db):
        """无效 user_id → ValueError"""
        with pytest.raises(ValueError, match="格式无效"):
            await svc.get_profile("invalid-id")

    @pytest.mark.asyncio
    async def test_get_profile_not_found(self, svc, mock_db):
        """用户不存在 → ValueError"""
        mock_db.users.find_one = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="不存在"):
            await svc.get_profile(self.USER_ID_HEX)

    # ── 更新个人信息 ──

    @pytest.mark.asyncio
    async def test_update_profile_success(self, svc, mock_db):
        """更新昵称成功"""
        mock_db.users.update_one = AsyncMock()
        mock_db.users.update_one.return_value.matched_count = 1
        mock_db.users.find_one = AsyncMock(return_value={
            "_id": ObjectId(self.USER_ID_HEX),
            "username": "testuser",
            "nickname": "新昵称",
            "avatar_url": "",
            "privacy_save_history": True,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-06-01T00:00:00",
        })

        result = await svc.update_profile(self.USER_ID_HEX, {"nickname": "新昵称"})

        assert result["nickname"] == "新昵称"

    @pytest.mark.asyncio
    async def test_update_profile_invalid_id(self, svc, mock_db):
        """无效 ID → ValueError"""
        with pytest.raises(ValueError, match="格式无效"):
            await svc.update_profile("bad-id", {"nickname": "test"})

    @pytest.mark.asyncio
    async def test_update_profile_empty_nickname(self, svc, mock_db):
        """空昵称 → ValueError"""
        with pytest.raises(ValueError, match="不能为空"):
            await svc.update_profile(self.USER_ID_HEX, {"nickname": "  "})

    @pytest.mark.asyncio
    async def test_update_profile_nickname_too_long(self, svc, mock_db):
        """昵称超过50字 → ValueError"""
        with pytest.raises(ValueError, match="不能超过50字"):
            await svc.update_profile(self.USER_ID_HEX, {"nickname": "x" * 51})

    @pytest.mark.asyncio
    async def test_update_profile_no_fields(self, svc, mock_db):
        """无更新字段 → ValueError"""
        with pytest.raises(ValueError, match="没有可更新"):
            await svc.update_profile(self.USER_ID_HEX, {})

    @pytest.mark.asyncio
    async def test_update_profile_no_allowed_fields(self, svc, mock_db):
        """传入不允许的字段 → 被忽略，无更新抛出异常"""
        with pytest.raises(ValueError, match="没有可更新"):
            await svc.update_profile(self.USER_ID_HEX, {"password": "newpass"})

    @pytest.mark.asyncio
    async def test_update_profile_user_not_found(self, svc, mock_db):
        """用户不存在 → ValueError"""
        mock_db.users.update_one = AsyncMock()
        mock_db.users.update_one.return_value.matched_count = 0

        with pytest.raises(ValueError, match="不存在"):
            await svc.update_profile(self.USER_ID_HEX, {"nickname": "test"})

    @pytest.mark.asyncio
    async def test_update_profile_avatar_url(self, svc, mock_db):
        """更新头像 URL"""
        mock_db.users.update_one = AsyncMock()
        mock_db.users.update_one.return_value.matched_count = 1
        mock_db.users.find_one = AsyncMock(return_value={
            "_id": ObjectId(self.USER_ID_HEX),
            "username": "testuser",
            "nickname": "testuser",
            "avatar_url": "https://new.url/avatar.png",
            "privacy_save_history": True,
            "created_at": "2024-01-01T00:00:00",
        })

        result = await svc.update_profile(self.USER_ID_HEX, {"avatar_url": "https://new.url/avatar.png"})

        assert result["avatar_url"] == "https://new.url/avatar.png"

    # ── 更新隐私设置 ──

    @pytest.mark.asyncio
    async def test_update_privacy_success(self, svc, mock_db):
        """更新隐私设置成功"""
        mock_db.users.update_one = AsyncMock()
        mock_db.users.update_one.return_value.matched_count = 1

        result = await svc.update_privacy(self.USER_ID_HEX, save_history=False)

        assert result["privacy_save_history"] is False
        assert "已更新" in result["message"]

    @pytest.mark.asyncio
    async def test_update_privacy_invalid_id(self, svc, mock_db):
        """无效 ID → ValueError"""
        with pytest.raises(ValueError, match="格式无效"):
            await svc.update_privacy("bad-id", False)

    @pytest.mark.asyncio
    async def test_update_privacy_user_not_found(self, svc, mock_db):
        """用户不存在 → ValueError"""
        mock_db.users.update_one = AsyncMock()
        mock_db.users.update_one.return_value.matched_count = 0

        with pytest.raises(ValueError, match="不存在"):
            await svc.update_privacy(self.USER_ID_HEX, False)
