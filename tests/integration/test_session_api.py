"""
会话 API 集成测试
POST /api/v1/sessions, GET /sessions, GET /sessions/{id}, DELETE /sessions/{id}
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from bson import ObjectId


class TestSessionCreate:
    """创建会话"""

    def test_create_session_without_auth(self, test_app):
        """无 Token 创建会话 → 401"""
        resp = test_app.post("/api/v1/sessions", json={
            "title": "测试会话",
            "category": "civil",
        })

        assert resp.status_code == 401

    def test_create_session_with_auth(self, test_app):
        """IT-SESS-01: 已认证用户创建会话 → 200"""
        token = _get_token()

        # mock insert
        from bson import ObjectId
        result = AsyncMock()
        result.inserted_id = ObjectId("507f1f77bcf86cd799439022")
        test_app.app.state.db.sessions.insert_one = result

        resp = test_app.post("/api/v1/sessions", json={
            "title": "法律咨询",
            "category": "civil",
        }, headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0

    def test_create_session_empty_title_defaults(self, test_app):
        """空标题 → 使用默认值"""
        token = _get_token()

        from bson import ObjectId
        result = AsyncMock()
        result.inserted_id = ObjectId("507f1f77bcf86cd799439022")
        test_app.app.state.db.sessions.insert_one = result

        resp = test_app.post("/api/v1/sessions", json={},
                             headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200


class TestSessionList:
    """会话列表"""

    def test_list_sessions_unauthorized(self, test_app):
        """无 Token 获取列表 → 401"""
        resp = test_app.get("/api/v1/sessions")

        assert resp.status_code == 401

    def test_list_sessions_with_auth(self, test_app):
        """IT-SESS-02: 已认证获取列表 → 200 含分页"""
        token = _get_token()

        from bson import ObjectId
        now = "2024-01-01T00:00:00"
        session_docs = [
            {"_id": ObjectId("507f1f77bcf86cd799439001"), "title": "会话1",
             "category": "civil", "msg_count": 3, "updated_at": now, "created_at": now},
            {"_id": ObjectId("507f1f77bcf86cd799439002"), "title": "会话2",
             "category": "criminal", "msg_count": 1, "updated_at": now, "created_at": now},
        ]

        test_app.app.state.db.sessions.count_documents = AsyncMock(return_value=2)

        def _make_cursor(items):
            c = MagicMock()
            c.sort.return_value = c
            c.skip.return_value = c
            c.limit.return_value = c

            class AsyncIter:
                def __init__(self, items):
                    self._items = items
                    self._idx = 0
                def __aiter__(self):
                    return self
                async def __anext__(self):
                    if self._idx >= len(self._items):
                        raise StopAsyncIteration
                    item = self._items[self._idx]
                    self._idx += 1
                    return item
            c.__aiter__.side_effect = lambda: AsyncIter(items).__aiter__()
            return c

        test_app.app.state.db.sessions.find.side_effect = lambda *a, **kw: _make_cursor(session_docs)

        resp = test_app.get("/api/v1/sessions?page=1&page_size=10",
                            headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert "list" in data["data"]
        assert data["data"]["total"] == 2
        assert len(data["data"]["list"]) == 2


class TestSessionDetail:
    """会话详情"""

    def test_detail_invalid_id(self, test_app):
        """无效 session_id → 404"""
        token = _get_token()
        test_app.app.state.db.sessions.find_one = AsyncMock(return_value=None)

        resp = test_app.get("/api/v1/sessions/invalid123",
                            headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 404

    def test_detail_not_found(self, test_app):
        """IT-SESS-04: 不存在的会话 → 404"""
        token = _get_token()
        test_app.app.state.db.sessions.find_one = AsyncMock(return_value=None)

        resp = test_app.get("/api/v1/sessions/507f1f77bcf86cd799439999",
                            headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 404


class TestSessionDelete:
    """删除会话"""

    def test_delete_unauthorized(self, test_app):
        """无 Token 删除 → 401"""
        resp = test_app.delete("/api/v1/sessions/507f1f77bcf86cd799439022")

        assert resp.status_code == 401

    def test_delete_success(self, test_app):
        """IT-SESS-05: 已认证删除 → 200"""
        token = _get_token()
        test_app.app.state.db.sessions.update_one = AsyncMock()
        test_app.app.state.db.sessions.update_one.return_value.modified_count = 1

        resp = test_app.delete("/api/v1/sessions/507f1f77bcf86cd799439022",
                               headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0


class TestSessionClearAll:
    """清空全部会话"""

    def test_clear_all_unauthorized(self, test_app):
        """无 Token → 401"""
        resp = test_app.delete("/api/v1/sessions/clear-all")

        assert resp.status_code == 401

    def test_clear_all_success(self, test_app):
        """IT-SESS-06: 已认证清空 → 200"""
        token = _get_token()
        test_app.app.state.db.sessions.update_many = AsyncMock()
        test_app.app.state.db.sessions.update_many.return_value.modified_count = 3

        resp = test_app.delete("/api/v1/sessions/clear-all",
                               headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["deleted_count"] == 3


def _get_token():
    """生成测试用 JWT token"""
    from utils.jwt_utils import create_access_token
    return create_access_token("507f1f77bcf86cd799439011", "testuser",
                                secret="dev-jwt-secret-change-in-production-32chars",
                                access_ttl=86400)
