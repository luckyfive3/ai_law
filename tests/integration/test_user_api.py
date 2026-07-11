"""
用户 API 集成测试
GET /api/v1/user/profile, PUT /user/profile, PUT /user/privacy
"""
import pytest
from unittest.mock import AsyncMock
from bson import ObjectId


def _get_token():
    from utils.jwt_utils import create_access_token
    return create_access_token("507f1f77bcf86cd799439011", "testuser",
                                secret="dev-jwt-secret-change-in-production-32chars",
                                access_ttl=86400)


class TestUserProfile:
    """用户资料接口"""

    def test_get_profile_unauthorized(self, test_app):
        """IT-USER-02: 无 Token → 401"""
        resp = test_app.get("/api/v1/user/profile")

        assert resp.status_code == 401

    def test_get_profile_with_auth(self, test_app):
        """IT-USER-01: 已认证 → 200"""
        token = _get_token()
        mock_user = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "username": "testuser",
            "nickname": "测试用户",
            "avatar_url": "",
            "privacy_save_history": True,
            "created_at": "2024-01-01T00:00:00",
        }
        test_app.app.state.db.users.find_one = AsyncMock(return_value=mock_user)

        resp = test_app.get("/api/v1/user/profile",
                            headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["username"] == "testuser"

    def test_get_profile_user_not_found(self, test_app):
        """用户不存在 → 404"""
        token = _get_token()
        test_app.app.state.db.users.find_one = AsyncMock(side_effect=ValueError("用户不存在"))

        resp = test_app.get("/api/v1/user/profile",
                            headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 404


class TestUserUpdateProfile:
    """更新资料接口"""

    def test_update_profile_unauthorized(self, test_app):
        """无 Token → 401"""
        resp = test_app.put("/api/v1/user/profile", json={"nickname": "新昵称"})

        assert resp.status_code == 401

    def test_update_profile_empty(self, test_app):
        """IT-USER-04: 无更新字段 → 400"""
        token = _get_token()
        resp = test_app.put("/api/v1/user/profile", json={},
                            headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 400

    def test_update_profile_success(self, test_app):
        """IT-USER-03: 更新昵称 → 200"""
        token = _get_token()
        mock_user = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "username": "testuser",
            "nickname": "新昵称",
            "avatar_url": "",
            "privacy_save_history": True,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-06-01T00:00:00",
        }
        test_app.app.state.db.users.update_one = AsyncMock()
        test_app.app.state.db.users.update_one.return_value.matched_count = 1
        test_app.app.state.db.users.find_one = AsyncMock(return_value=mock_user)

        resp = test_app.put("/api/v1/user/profile", json={"nickname": "新昵称"},
                            headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["nickname"] == "新昵称"


class TestUserPrivacy:
    """隐私设置接口"""

    def test_update_privacy_unauthorized(self, test_app):
        """无 Token → 401"""
        resp = test_app.put("/api/v1/user/privacy", json={"privacy_save_history": False})

        assert resp.status_code == 401

    def test_update_privacy_success(self, test_app):
        """IT-USER-05: 更新隐私设置 → 200"""
        token = _get_token()
        test_app.app.state.db.users.update_one = AsyncMock()
        test_app.app.state.db.users.update_one.return_value.matched_count = 1

        resp = test_app.put("/api/v1/user/privacy",
                            json={"privacy_save_history": False},
                            headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["privacy_save_history"] is False
