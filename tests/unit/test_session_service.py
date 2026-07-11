"""
services/session_service 模块单元测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId
from datetime import datetime, timezone


def _make_async_cursor(items):
    """创建模拟的 async cursor"""
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


class TestSessionService:
    """会话管理服务单元测试"""

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.sessions = MagicMock()
        db.sessions.insert_one = AsyncMock()
        db.sessions.find_one = AsyncMock()
        db.sessions.find = MagicMock()
        db.sessions.count_documents = AsyncMock()
        db.sessions.update_one = AsyncMock()
        db.sessions.update_many = AsyncMock()
        db.messages = MagicMock()
        db.messages.find = MagicMock()
        db.messages.count_documents = AsyncMock()
        db.law_refs = MagicMock()
        db.law_refs.find = MagicMock()
        return db

    @pytest.fixture
    def svc(self, mock_db):
        from services.session_service import SessionService
        return SessionService(mock_db)

    # ── 创建会话 ──

    @pytest.mark.asyncio
    async def test_create_default_values(self, svc, mock_db):
        """创建会话使用默认值"""
        mock_db.sessions.insert_one.return_value = MagicMock(inserted_id=ObjectId())

        result = await svc.create(
            user_id="507f1f77bcf86cd799439011",
        )

        assert result["title"] == "法律咨询"
        assert result["category"] == "general"
        assert result["msg_count"] == 0

    @pytest.mark.asyncio
    async def test_create_with_custom_values(self, svc, mock_db):
        """创建会话使用自定义值"""
        mock_db.sessions.insert_one.return_value = MagicMock(inserted_id=ObjectId())

        result = await svc.create(
            user_id="507f1f77bcf86cd799439011",
            title="劳动争议咨询",
            category="labor",
        )

        assert result["title"] == "劳动争议咨询"
        assert result["category"] == "labor"

    # ── 会话列表 ──

    @pytest.mark.asyncio
    async def test_list_sessions_empty(self, svc, mock_db):
        """空列表 → 返回空数组"""
        mock_db.sessions.count_documents = AsyncMock(return_value=0)
        mock_db.sessions.find.side_effect = lambda *a, **kw: _make_async_cursor([])

        sessions, total = await svc.list_sessions("user123")

        assert sessions == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_list_sessions_with_data(self, svc, mock_db):
        """有会话数据 → 返回列表"""
        mock_db.sessions.count_documents = AsyncMock(return_value=2)

        now = datetime.now(timezone.utc).isoformat()
        session_docs = [
            {
                "_id": ObjectId("507f1f77bcf86cd799439001"),
                "title": "会话1",
                "category": "civil",
                "msg_count": 3,
                "updated_at": now,
                "created_at": now,
            },
            {
                "_id": ObjectId("507f1f77bcf86cd799439002"),
                "title": "会话2",
                "category": "criminal",
                "msg_count": 1,
                "updated_at": now,
                "created_at": now,
            },
        ]

        mock_db.sessions.find.side_effect = lambda *a, **kw: _make_async_cursor(session_docs)

        sessions, total = await svc.list_sessions("user123", page=1, page_size=10)

        assert len(sessions) == 2
        assert total == 2
        assert sessions[0]["id"] == "507f1f77bcf86cd799439001"
        assert sessions[0]["title"] == "会话1"

    @pytest.mark.asyncio
    async def test_list_sessions_with_keyword(self, svc, mock_db):
        """带关键词搜索"""
        mock_db.sessions.count_documents = AsyncMock(return_value=1)

        mock_db.sessions.find.side_effect = lambda *a, **kw: _make_async_cursor([])
        mock_db.messages.find.side_effect = lambda *a, **kw: _make_async_cursor(
            [{"session_id": "507f1f77bcf86cd799439001"}]
        )

        sessions, total = await svc.list_sessions("user123", keyword="合同")

        assert total == 1

    # ── 会话详情 ──

    @pytest.mark.asyncio
    async def test_get_detail_invalid_id(self, svc, mock_db):
        """无效 ObjectId → None"""
        result = await svc.get_detail("invalid-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_detail_not_found(self, svc, mock_db):
        """会话不存在 → None"""
        mock_db.sessions.find_one = AsyncMock(return_value=None)

        result = await svc.get_detail("507f1f77bcf86cd799439001")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_detail_with_messages(self, svc, mock_db):
        """会话存在且有消息"""
        now = datetime.now(timezone.utc).isoformat()
        mock_db.sessions.find_one = AsyncMock(return_value={
            "_id": ObjectId("507f1f77bcf86cd799439001"),
            "title": "法律咨询",
            "category": "civil",
            "msg_count": 2,
            "updated_at": now,
        })

        messages = [
            {"_id": ObjectId(), "session_id": "xxx", "role": "user", "content": "问题",
             "content_type": "text", "tokens": 0, "created_at": now},
            {"_id": ObjectId(), "session_id": "xxx", "role": "assistant", "content": "回答",
             "content_type": "markdown", "tokens": 100, "created_at": now},
        ]

        mock_db.messages.find.side_effect = lambda *a, **kw: _make_async_cursor(messages)

        result = await svc.get_detail("507f1f77bcf86cd799439001")

        assert result is not None
        assert result["id"] == "507f1f77bcf86cd799439001"
        assert len(result["messages"]) == 2

    # ── 删除会话 ──

    @pytest.mark.asyncio
    async def test_delete_invalid_id(self, svc, mock_db):
        """无效 ID → False"""
        result = await svc.delete("bad-id", "user123")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_success(self, svc, mock_db):
        """软删除成功 → True"""
        mock_db.sessions.update_one = AsyncMock()
        mock_db.sessions.update_one.return_value.modified_count = 1

        result = await svc.delete("507f1f77bcf86cd799439001", "user123")
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_not_found(self, svc, mock_db):
        """会话不属于该用户 → False"""
        mock_db.sessions.update_one = AsyncMock()
        mock_db.sessions.update_one.return_value.modified_count = 0

        result = await svc.delete("507f1f77bcf86cd799439001", "user123")
        assert result is False

    # ── 清空全部会话 ──

    @pytest.mark.asyncio
    async def test_clear_all(self, svc, mock_db):
        """清空全部返回删除数量"""
        mock_db.sessions.update_many = AsyncMock()
        mock_db.sessions.update_many.return_value.modified_count = 5

        count = await svc.clear_all("user123")
        assert count == 5

    # ── 更新消息计数 ──

    @pytest.mark.asyncio
    async def test_increment_msg_count(self, svc, mock_db):
        """增加消息计数不抛异常"""
        mock_db.sessions.update_one = AsyncMock()

        try:
            await svc.increment_msg_count("507f1f77bcf86cd799439001")
        except Exception:
            pytest.fail("不应该抛出异常")

    @pytest.mark.asyncio
    async def test_increment_msg_count_invalid_id(self, svc, mock_db):
        """无效ID不抛异常"""
        try:
            await svc.increment_msg_count("bad-id")
        except Exception:
            pytest.fail("无效ID不应该抛出异常")
