"""
聊天 API 集成测试
POST /api/v1/chat/stream, GET /chat/{id}/messages, GET /chat/{id}/export
"""
import pytest
from unittest.mock import AsyncMock


def _get_token():
    from utils.jwt_utils import create_access_token
    return create_access_token("507f1f77bcf86cd799439011", "testuser",
                                secret="dev-jwt-secret-change-in-production-32chars",
                                access_ttl=86400)


class TestChatStream:
    """SSE 流式对话"""

    def test_stream_unauthorized(self, test_app):
        """无 Token → 401"""
        resp = test_app.post("/api/v1/chat/stream", json={
            "session_id": "507f1f77bcf86cd799439022",
            "content": "什么是工伤？",
        })

        assert resp.status_code == 401

    def test_stream_empty_content(self, test_app):
        """空 content — FastAPI 不会拒绝空字符串(min_length未设)，由业务层处理"""
        token = _get_token()

        resp = test_app.post("/api/v1/chat/stream", json={
            "session_id": "507f1f77bcf86cd799439022",
            "content": "",
        }, headers={"Authorization": f"Bearer {token}"})

        # FastAPI 不会拒绝空字符串（min_length 未在 ChatStreamRequest.content 设置）
        assert resp.status_code in (200, 422)

    def test_stream_content_too_long(self, test_app):
        """content 超过2000字符 → 422"""
        token = _get_token()

        resp = test_app.post("/api/v1/chat/stream", json={
            "session_id": "507f1f77bcf86cd799439022",
            "content": "x" * 2001,
        }, headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 422

    def test_stream_content_max_length_ok(self, test_app):
        """content 刚好2000字符 → 200"""
        token = _get_token()
        from bson import ObjectId

        # mock session detail
        mock_session = {
            "_id": ObjectId("507f1f77bcf86cd799439022"),
            "user_id": "507f1f77bcf86cd799439011",
            "title": "测试",
            "msg_count": 0,
            "updated_at": "",
        }
        test_app.app.state.db.sessions.find_one = AsyncMock(return_value=mock_session)
        test_app.app.state.db.messages.find = MagicMock()

        # mock chat_service.send_message
        mock_chat = test_app.app.state.services["chat_service"]
        orig = mock_chat.send_message

        async def fake_stream(*args, **kwargs):
            yield {"status": "searching"}
            yield {"done": True, "status": "done", "message_id": "msg1",
                   "laws": [], "tokens": {"input": 10, "output": 20}}

        mock_chat.send_message = fake_stream

        resp = test_app.post("/api/v1/chat/stream", json={
            "session_id": "507f1f77bcf86cd799439022",
            "content": "y" * 2000,
        }, headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")

        mock_chat.send_message = orig


class TestChatMessages:
    """消息列表"""

    def test_messages_unauthorized(self, test_app):
        """无 Token → 401"""
        resp = test_app.get("/api/v1/chat/507f1f77bcf86cd799439022/messages")

        assert resp.status_code == 401

    def test_messages_with_auth(self, test_app):
        """IT-CHAT-03: 已认证 → 200, 含分页"""
        token = _get_token()
        test_app.app.state.db.messages.count_documents = AsyncMock(return_value=5)

        resp = test_app.get("/api/v1/chat/507f1f77bcf86cd799439022/messages",
                            headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert "list" in data["data"]
        assert "total" in data["data"]
        assert data["data"]["total"] == 5

    def test_messages_pagination_defaults(self, test_app):
        """默认分页参数 page=1, page_size=50"""
        token = _get_token()
        test_app.app.state.db.messages.count_documents = AsyncMock(return_value=0)

        resp = test_app.get("/api/v1/chat/507f1f77bcf86cd799439022/messages",
                            headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["page"] == 1
        assert data["data"]["page_size"] == 50


class TestChatExport:
    """消息导出"""

    def test_export_unauthorized(self, test_app):
        """无 Token → 401"""
        resp = test_app.get("/api/v1/chat/507f1f77bcf86cd799439022/export")

        assert resp.status_code == 401

    def test_export_with_auth(self, test_app):
        """IT-CHAT-04: 已认证导出 → 200 返回文本"""
        token = _get_token()
        test_app.app.state.db.messages.count_documents = AsyncMock(return_value=2)

        msg_docs = [
            {"_id": "msg1", "session_id": "s1", "role": "user", "content": "问题是？",
             "content_type": "text", "tokens": 0, "created_at": "2024-01-01T00:00:00"},
            {"_id": "msg2", "session_id": "s1", "role": "assistant", "content": "答案是。",
             "content_type": "markdown", "tokens": 10, "created_at": "2024-01-01T00:00:01"},
        ]

        test_app.app.state.db.messages.find.side_effect = lambda *a, **kw: make_cursor(msg_docs)

        resp = test_app.get("/api/v1/chat/507f1f77bcf86cd799439022/export",
                            headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200
        assert "text/plain" in resp.headers.get("content-type", "")
        assert "用户" in resp.text
        assert "AI法律助手" in resp.text


class TestHealthEndpoint:
    """健康检查接口"""

    def test_health_check(self, test_app):
        """IT-SYS-01: /health → 200"""
        resp = test_app.get("/health")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


def make_cursor(items):
    cursor = MagicMock()
    cursor.sort.return_value = cursor
    cursor.skip.return_value = cursor
    cursor.limit.return_value = cursor

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

    cursor.__aiter__.side_effect = lambda: AsyncIter(items).__aiter__()
    return cursor


from unittest.mock import MagicMock
