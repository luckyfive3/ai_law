"""
services/summary_service 模块单元测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId


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


def _make_async_aggregate(items):
    """创建模拟的 async aggregate cursor"""
    class AggCursor:
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
    return AggCursor(items)


class TestSummaryService:
    """会话摘要与用户画像服务单元测试"""

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.messages = MagicMock()
        db.messages.find = MagicMock()
        db.messages.count_documents = AsyncMock()
        db.sessions = MagicMock()
        db.sessions.find = MagicMock()
        db.sessions.find_one = AsyncMock()
        db.sessions.update_one = AsyncMock()
        db.sessions.aggregate = MagicMock()
        db.user_profiles = MagicMock()
        db.user_profiles.find_one = AsyncMock()
        db.user_profiles.update_one = AsyncMock()
        return db

    @pytest.fixture
    def mock_llm(self):
        svc = MagicMock()

        async def fake_stream(_messages):
            for t in ["劳动争议", "咨询摘要", "测试"]:
                yield t

        svc.generate_stream = fake_stream
        return svc

    @pytest.fixture
    def svc(self, mock_db, mock_llm):
        from services.summary_service import SummaryService
        return SummaryService(db=mock_db, llm_service=mock_llm)

    # ── 初始化 ──

    def test_init_stores_dependencies(self, mock_db, mock_llm):
        from services.summary_service import SummaryService
        svc = SummaryService(db=mock_db, llm_service=mock_llm)
        assert svc.db is mock_db
        assert svc.llm_service is mock_llm

    # ── generate_session_summary ──

    @pytest.mark.asyncio
    async def test_generate_skips_when_too_few_messages(self, svc, mock_db):
        """消息数 < 4 → 跳过，返回 None"""
        mock_db.messages.count_documents = AsyncMock(return_value=2)

        result = await svc.generate_session_summary("507f1f77bcf86cd799439001")
        assert result is None

    @pytest.mark.asyncio
    async def test_generate_with_force_skips_count_check(self, svc, mock_db):
        """force=True 忽略消息数限制"""
        mock_db.messages.count_documents = AsyncMock(return_value=1)
        mock_db.messages.find.side_effect = lambda *a, **kw: _make_async_cursor([
            {"role": "user", "content": "工伤怎么认定"},
            {"role": "assistant", "content": "需满足三个条件"},
        ])
        mock_db.sessions.update_one = AsyncMock()

        result = await svc.generate_session_summary("507f1f77bcf86cd799439001", force=True)
        assert result is not None
        assert "劳动" in result
        mock_db.sessions.update_one.assert_called()

    @pytest.mark.asyncio
    async def test_generate_with_enough_messages(self, svc, mock_db):
        """消息数 >= 4 → 生成摘要并更新会话"""
        mock_db.messages.count_documents = AsyncMock(return_value=4)
        mock_db.messages.find.side_effect = lambda *a, **kw: _make_async_cursor([
            {"role": "user", "content": "问题1"},
            {"role": "assistant", "content": "回答1"},
            {"role": "user", "content": "问题2"},
            {"role": "assistant", "content": "回答2"},
        ])
        mock_db.sessions.update_one = AsyncMock()

        result = await svc.generate_session_summary("507f1f77bcf86cd799439001")
        assert result is not None
        mock_db.sessions.update_one.assert_called()

    @pytest.mark.asyncio
    async def test_generate_empty_messages_returns_none(self, svc, mock_db):
        """无消息内容 → None"""
        mock_db.messages.count_documents = AsyncMock(return_value=4)
        mock_db.messages.find.side_effect = lambda *a, **kw: _make_async_cursor([])

        result = await svc.generate_session_summary("507f1f77bcf86cd799439001")
        assert result is None

    @pytest.mark.asyncio
    async def test_generate_llm_failure_returns_none(self, svc, mock_db, mock_llm):
        """LLM 调用失败 → 返回 None"""
        mock_db.messages.count_documents = AsyncMock(return_value=4)
        mock_db.messages.find.side_effect = lambda *a, **kw: _make_async_cursor([
            {"role": "user", "content": "test"},
            {"role": "assistant", "content": "reply"},
        ])
        mock_llm.generate_stream = MagicMock(side_effect=Exception("API error"))

        result = await svc.generate_session_summary("507f1f77bcf86cd799439001")
        assert result is None

    # ── get_session_summary ──

    @pytest.mark.asyncio
    async def test_get_session_summary_exists(self, svc, mock_db):
        """会话有摘要 → 返回摘要字典"""
        mock_db.sessions.find_one = AsyncMock(return_value={
            "_id": ObjectId("507f1f77bcf86cd799439001"),
            "title": "劳动争议咨询",
            "summary": "用户咨询了关于劳动合同解除的问题",
            "category": "labor",
            "msg_count": 6,
        })

        result = await svc.get_session_summary("507f1f77bcf86cd799439001")
        assert result is not None
        assert result["summary"] == "用户咨询了关于劳动合同解除的问题"
        assert result["title"] == "劳动争议咨询"

    @pytest.mark.asyncio
    async def test_get_session_summary_no_summary_field(self, svc, mock_db):
        """会话无 summary 字段 → None"""
        mock_db.sessions.find_one = AsyncMock(return_value={
            "_id": ObjectId("507f1f77bcf86cd799439001"),
            "title": "法律咨询",
        })

        result = await svc.get_session_summary("507f1f77bcf86cd799439001")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_session_summary_not_found(self, svc, mock_db):
        """会话不存在 → None"""
        mock_db.sessions.find_one = AsyncMock(return_value=None)
        result = await svc.get_session_summary("507f1f77bcf86cd799439999")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_session_summary_invalid_id(self, svc, mock_db):
        """无效 ObjectId → None（不抛异常）"""
        result = await svc.get_session_summary("invalid-id")
        assert result is None

    # ── update_user_profile ──

    @pytest.mark.asyncio
    async def test_update_profile_with_summaries(self, svc, mock_db):
        """有会话摘要 → 生成完整画像"""
        mock_db.sessions.find.side_effect = [
            _make_async_cursor([
                {"title": "咨询1", "summary": "劳动纠纷", "category": "labor",
                 "msg_count": 5, "updated_at": "2024-06-01T00:00:00"},
            ]),
            _make_async_cursor([
                {"category": "labor", "msg_count": 5},
                {"category": "civil", "msg_count": 3},
            ]),
        ]
        mock_db.sessions.aggregate.side_effect = lambda *a, **kw: _make_async_aggregate([
            {"msg_count": 5}, {"msg_count": 3},
        ])
        mock_db.user_profiles.update_one = AsyncMock()

        result = await svc.update_user_profile("507f1f77bcf86cd799439011")
        assert result is not None
        assert result["total_sessions"] == 1
        assert "labor" in result["top_categories"]
        mock_db.user_profiles.update_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_profile_no_summaries(self, svc, mock_db):
        """无会话摘要 → 生成基础画像"""
        mock_db.sessions.find.side_effect = [
            _make_async_cursor([]),
            _make_async_cursor([]),
        ]
        mock_db.sessions.aggregate.side_effect = lambda *a, **kw: _make_async_aggregate([])
        mock_db.user_profiles.update_one = AsyncMock()

        result = await svc.update_user_profile("user_without_sessions")
        assert result is not None
        assert result["total_sessions"] == 0
        assert result["total_messages"] == 0

    # ── get_user_profile ──

    @pytest.mark.asyncio
    async def test_get_user_profile_exists(self, svc, mock_db):
        """画像存在 → 返回完整数据"""
        mock_db.user_profiles.find_one = AsyncMock(return_value={
            "user_id": "user1",
            "total_sessions": 10,
            "total_messages": 50,
            "category_distribution": {"labor": 5, "civil": 3},
            "top_categories": ["labor", "civil"],
            "profile_text": "该用户主要关注劳动纠纷",
            "updated_at": "2024-06-01T00:00:00",
        })

        result = await svc.get_user_profile("user1")
        assert result is not None
        assert result["total_sessions"] == 10
        assert result["top_categories"] == ["labor", "civil"]

    @pytest.mark.asyncio
    async def test_get_user_profile_not_found(self, svc, mock_db):
        """画像不存在 → None"""
        mock_db.user_profiles.find_one = AsyncMock(return_value=None)
        result = await svc.get_user_profile("new_user")
        assert result is None

    # ── get_personalized_context ──

    @pytest.mark.asyncio
    async def test_personalized_context_no_profile(self, svc, mock_db):
        """无画像 → 返回空字符串"""
        mock_db.user_profiles.find_one = AsyncMock(return_value=None)

        ctx = await svc.get_personalized_context("new_user")
        assert ctx == ""

    @pytest.mark.asyncio
    async def test_personalized_context_with_profile(self, svc, mock_db):
        """有画像 → 返回上下文文本"""
        mock_db.user_profiles.find_one = AsyncMock(return_value={
            "user_id": "user1",
            "total_sessions": 5,
            "total_messages": 20,
            "category_distribution": {"labor": 5},
            "top_categories": ["labor"],
            "profile_text": "该用户主要关注劳动纠纷，偏好实用建议",
        })

        ctx = await svc.get_personalized_context("user1")
        assert "劳动纠纷" in ctx
        assert "5 次" in ctx

    @pytest.mark.asyncio
    async def test_personalized_context_truncation(self, svc, mock_db):
        """上下文超长时截断"""
        long_text = "偏好" * 300
        mock_db.user_profiles.find_one = AsyncMock(return_value={
            "user_id": "user1",
            "total_sessions": 100,
            "total_messages": 1000,
            "category_distribution": {"labor": 50},
            "top_categories": ["labor", "civil", "contract", "traffic"],
            "profile_text": long_text,
        })

        ctx = await svc.get_personalized_context("user1", max_length=50)
        assert len(ctx) <= 53  # max_length + "..."

    # ── auto_summary_and_profile ──

    @pytest.mark.asyncio
    async def test_auto_summary_and_profile(self, svc, mock_db):
        """自动摘要和画像更新 — 调用 generate + update"""
        mock_db.messages.count_documents = AsyncMock(return_value=6)
        mock_db.messages.find.side_effect = lambda *a, **kw: _make_async_cursor([
            {"role": "user", "content": "工伤赔偿"}, {"role": "assistant", "content": "根据工伤保险条例"},
            {"role": "user", "content": "具体金额"}, {"role": "assistant", "content": "需要鉴定等级"},
        ])
        mock_db.sessions.update_one = AsyncMock()
        mock_db.sessions.find.side_effect = [
            _make_async_cursor([{"title": "工伤咨询", "summary": "test", "category": "labor",
                                  "msg_count": 4, "updated_at": "2024-06-01T00:00:00"}]),
            _make_async_cursor([]),
        ]
        mock_db.sessions.aggregate.side_effect = lambda *a, **kw: _make_async_aggregate([])
        mock_db.user_profiles.update_one = AsyncMock()

        # 不应抛异常
        await svc.auto_summary_and_profile("507f1f77bcf86cd799439001", "user1")

    @pytest.mark.asyncio
    async def test_auto_summary_handles_exception(self, svc, mock_db):
        """auto_summary 内部异常不传播"""
        mock_db.messages.count_documents = AsyncMock(side_effect=Exception("DB error"))

        # 不应抛异常
        try:
            await svc.auto_summary_and_profile("sid", "uid")
        except Exception:
            pytest.fail("auto_summary_and_profile 应吞掉异常")
