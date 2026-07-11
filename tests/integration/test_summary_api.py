"""
摘要与用户画像 API 集成测试
GET /api/v1/summary/session/{id}, POST /generate, GET /profile, POST /profile/refresh, GET /context
"""
import pytest
from unittest.mock import AsyncMock


def _get_token():
    from utils.jwt_utils import create_access_token
    return create_access_token("507f1f77bcf86cd799439011", "testuser",
                                secret="dev-jwt-secret-change-in-production-32chars",
                                access_ttl=86400)


class TestSessionSummary:
    """会话摘要接口"""

    def test_get_summary_unauthorized(self, test_app):
        """无 Token → 401"""
        resp = test_app.get("/api/v1/summary/session/507f1f77bcf86cd799439022")
        assert resp.status_code == 401

    def test_get_summary_no_summary(self, test_app):
        """摘要不存在 → 200 含空数据"""
        token = _get_token()

        mock_svc = test_app.app.state.services["summary_service"]
        mock_svc.get_session_summary = AsyncMock(return_value=None)

        resp = test_app.get("/api/v1/summary/session/507f1f77bcf86cd799439022",
                            headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert "暂未生成摘要" in data["message"]

    def test_get_summary_exists(self, test_app):
        """IT-SUMMARY-01: 摘要存在 → 200"""
        token = _get_token()

        mock_svc = test_app.app.state.services["summary_service"]
        mock_svc.get_session_summary = AsyncMock(return_value={
            "id": "507f1f77bcf86cd799439022",
            "title": "劳动争议咨询",
            "summary": "用户咨询了劳动合同解除相关问题",
            "category": "labor",
            "msg_count": 6,
        })

        resp = test_app.get("/api/v1/summary/session/507f1f77bcf86cd799439022",
                            headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["summary"] == "用户咨询了劳动合同解除相关问题"

    def test_generate_summary_unauthorized(self, test_app):
        """无 Token → 401"""
        resp = test_app.post("/api/v1/summary/session/sid/generate")
        assert resp.status_code == 401

    def test_generate_summary_success(self, test_app):
        """IT-SUMMARY-02: 手动生成 → 200"""
        token = _get_token()

        mock_svc = test_app.app.state.services["summary_service"]
        mock_svc.generate_session_summary = AsyncMock(
            return_value="用户咨询了工伤认定相关问题"
        )

        resp = test_app.post("/api/v1/summary/session/507f1f77bcf86cd799439022/generate",
                             headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert "摘要生成成功" in data["message"]

    def test_generate_summary_insufficient(self, test_app):
        """消息不足 → 200 含提示"""
        token = _get_token()

        mock_svc = test_app.app.state.services["summary_service"]
        mock_svc.generate_session_summary = AsyncMock(return_value=None)

        resp = test_app.post("/api/v1/summary/session/sid/generate",
                             headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200
        data = resp.json()
        assert "消息数不足" in data["message"]

    def test_generate_summary_with_force(self, test_app):
        """IT-SUMMARY-03: 强制生成 → 200"""
        token = _get_token()

        mock_svc = test_app.app.state.services["summary_service"]
        mock_svc.generate_session_summary = AsyncMock(return_value="强制生成的摘要")

        resp = test_app.post("/api/v1/summary/session/sid/generate?force=true",
                             headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0


class TestUserProfile:
    """用户画像接口"""

    def test_get_profile_unauthorized(self, test_app):
        """无 Token → 401"""
        resp = test_app.get("/api/v1/summary/profile")
        assert resp.status_code == 401

    def test_get_profile_empty(self, test_app):
        """IT-SUMMARY-04: 无画像 → 200 返回空画像"""
        token = _get_token()

        mock_svc = test_app.app.state.services["summary_service"]
        mock_svc.get_user_profile = AsyncMock(return_value=None)

        resp = test_app.get("/api/v1/summary/profile",
                            headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["total_sessions"] == 0

    def test_get_profile_with_data(self, test_app):
        """IT-SUMMARY-05: 有画像 → 200 返回完整数据"""
        token = _get_token()

        mock_svc = test_app.app.state.services["summary_service"]
        mock_svc.get_user_profile = AsyncMock(return_value={
            "user_id": "507f1f77bcf86cd799439011",
            "total_sessions": 10,
            "total_messages": 50,
            "category_distribution": {"labor": 5, "civil": 3},
            "top_categories": ["labor", "civil"],
            "profile_text": "该用户主要关注劳动纠纷，偏好实用建议",
        })

        resp = test_app.get("/api/v1/summary/profile",
                            headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["total_sessions"] == 10
        assert data["data"]["top_categories"] == ["labor", "civil"]

    def test_refresh_profile_unauthorized(self, test_app):
        """无 Token → 401"""
        resp = test_app.post("/api/v1/summary/profile/refresh")
        assert resp.status_code == 401

    def test_refresh_profile_success(self, test_app):
        """IT-SUMMARY-06: 刷新画像 → 200"""
        token = _get_token()

        mock_svc = test_app.app.state.services["summary_service"]
        mock_svc.update_user_profile = AsyncMock(return_value={
            "user_id": "user1", "total_sessions": 5, "total_messages": 25,
            "category_distribution": {}, "top_categories": [], "profile_text": "",
        })

        resp = test_app.post("/api/v1/summary/profile/refresh",
                             headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert "已刷新" in data["message"]


class TestPersonalizedContext:
    """个性化上下文接口"""

    def test_get_context_unauthorized(self, test_app):
        """无 Token → 401"""
        resp = test_app.get("/api/v1/summary/context")
        assert resp.status_code == 401

    def test_get_context_empty(self, test_app):
        """IT-SUMMARY-07: 无画像 → 返回空上下文"""
        token = _get_token()

        mock_svc = test_app.app.state.services["summary_service"]
        mock_svc.get_personalized_context = AsyncMock(return_value="")

        resp = test_app.get("/api/v1/summary/context",
                            headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["context"] == ""

    def test_get_context_with_data(self, test_app):
        """IT-SUMMARY-08: 有画像 → 返回上下文"""
        token = _get_token()

        mock_svc = test_app.app.state.services["summary_service"]
        mock_svc.get_personalized_context = AsyncMock(
            return_value="该用户主要咨询领域：劳动纠纷\n用户画像：偏好实用建议\n该用户已进行过 5 次法律咨询"
        )

        resp = test_app.get("/api/v1/summary/context",
                            headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert "劳动纠纷" in data["data"]["context"]
