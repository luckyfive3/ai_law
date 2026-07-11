""""
services/chat_service 模块单元测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId


def _make_async_cursor(items):
    """创建一个模拟的 async cursor"""
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


class TestContentSafetyCheck:
    """内容安全检查器测试"""

    def test_check_enabled(self):
        """启用时默认通过"""
        from services.chat_service import ContentSafetyCheck
        checker = ContentSafetyCheck(enable=True)
        assert checker.check("正常问题") is True

    def test_check_disabled(self):
        """禁用时始终通过"""
        from services.chat_service import ContentSafetyCheck
        checker = ContentSafetyCheck(enable=False)
        assert checker.check("任何内容") is True


class TestChatService:
    """聊天服务单元测试"""

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.messages = MagicMock()
        db.messages.insert_one = AsyncMock()
        db.messages.find = MagicMock()
        db.messages.count_documents = AsyncMock(return_value=0)
        db.sessions = MagicMock()
        db.sessions.update_one = AsyncMock()
        db.law_refs = MagicMock()
        db.law_refs.find = MagicMock()
        db.law_refs.insert_many = AsyncMock()
        db.token_usage = MagicMock()
        db.token_usage.insert_one = AsyncMock()
        db.audit_logs = MagicMock()
        db.audit_logs.insert_one = AsyncMock()
        return db

    @pytest.fixture
    def mock_ragflow(self):
        client = MagicMock()
        client.search = AsyncMock(return_value=[
            {
                "law_name": "民法典",
                "article_num": "第1043条",
                "law_text": "家庭应当树立优良家风",
                "source": "",
                "chunk_id": "chunk1",
                "relevance": 0.9,
            }
        ])
        return client

    @pytest.fixture
    def mock_llm(self):
        svc = MagicMock()
        svc.model = "deepseek-chat"

        async def fake_stream(_messages):
            for t in ["根据", "民法典", "规定"]:
                yield t

        svc.generate_stream = fake_stream
        return svc

    @pytest.fixture
    def mock_context(self):
        builder = MagicMock()
        builder.build_context.return_value = "[相关法律依据]\n...\n\n[用户问题]\n工伤认定"
        return builder

    @pytest.fixture
    def mock_safety(self):
        sf = MagicMock()
        sf.system_prompt.return_value = "你是AI法律助手"
        sf.get_fallback_message.return_value = "服务暂不可用"
        return sf

    @pytest.fixture
    def mock_content_safety(self):
        from services.chat_service import ContentSafetyCheck
        return ContentSafetyCheck(enable=True)

    @pytest.fixture
    def chat_svc(self, mock_db, mock_ragflow, mock_llm, mock_context, mock_safety, mock_content_safety):
        from services.chat_service import ChatService
        return ChatService(
            db=mock_db,
            ragflow_client=mock_ragflow,
            llm_service=mock_llm,
            context_builder=mock_context,
            safety_filter=mock_safety,
            content_safety=mock_content_safety,
        )

    @pytest.mark.asyncio
    async def test_send_message_streaming(self, chat_svc, mock_db):
        """完整 SSE 流式对话流程"""
        mock_db.messages.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))

        events = []
        async for event in chat_svc.send_message(
            user_id="507f1f77bcf86cd799439011",
            session_id="507f1f77bcf86cd799439022",
            query="工伤认定需要什么条件",
        ):
            events.append(event)

        # 应有 searching + generating + done 事件
        assert len(events) >= 3
        assert events[0]["status"] == "searching"

        done_events = [e for e in events if e.get("done")]
        assert len(done_events) == 1
        assert "message_id" in done_events[0]
        assert "tokens" in done_events[0]

    @pytest.mark.asyncio
    async def test_send_message_saves_user_message(self, chat_svc, mock_db):
        """保存用户消息到 MongoDB"""
        mock_db.messages.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))

        async for _ in chat_svc.send_message(
            user_id="user1", session_id="session1", query="test query",
        ):
            pass

        # 验证 insert_one 被调用（用户消息 + AI消息）
        assert mock_db.messages.insert_one.call_count >= 2

    @pytest.mark.asyncio
    async def test_send_message_saves_ai_message(self, chat_svc, mock_db):
        """保存 AI 回复到 MongoDB"""
        mock_db.messages.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))

        async for _ in chat_svc.send_message(
            user_id="user1", session_id="session1", query="test",
        ):
            pass

        # 第二次调用 insert_one 是保存 AI 消息
        ai_call = mock_db.messages.insert_one.call_args_list[1][0][0]
        assert ai_call["role"] == "assistant"
        assert "content" in ai_call

    @pytest.mark.asyncio
    async def test_send_message_saves_law_refs(self, chat_svc, mock_db):
        """保存法条引用到 law_refs"""
        mock_db.messages.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))

        async for _ in chat_svc.send_message(
            user_id="user1", session_id="session1", query="家庭纠纷",
        ):
            pass

        assert mock_db.law_refs.insert_many.called

    @pytest.mark.asyncio
    async def test_send_message_records_token_usage(self, chat_svc, mock_db):
        """记录 token 用量"""
        mock_db.messages.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))

        async for _ in chat_svc.send_message(
            user_id="user1", session_id="session1", query="test",
        ):
            pass

        assert mock_db.token_usage.insert_one.called

    @pytest.mark.asyncio
    async def test_send_message_ragflow_fails_gracefully(self, chat_svc, mock_db, mock_ragflow):
        """RAGFlow 检索失败 → 不中断流程"""
        mock_ragflow.search = AsyncMock(side_effect=Exception("connection error"))
        mock_db.messages.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))

        events = []
        try:
            async for event in chat_svc.send_message(
                user_id="user1", session_id="session1", query="test",
            ):
                events.append(event)
        except Exception:
            pytest.fail("RAGFlow 异常不应中断对话流程")

        # 至少应有 done 事件
        done_events = [e for e in events if e.get("done")]
        assert len(done_events) == 1

    @pytest.mark.asyncio
    async def test_send_message_llm_fails_fallback(self, chat_svc, mock_db, mock_llm):
        """LLM 失败 → 使用兜底消息"""
        mock_db.messages.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))
        mock_llm.generate_stream = MagicMock(side_effect=Exception("API error"))

        full_content = ""
        async for event in chat_svc.send_message(
            user_id="user1", session_id="session1", query="test",
        ):
            if event.get("status") == "generating":
                full_content += event.get("content", "")

        assert len(full_content) > 0

    @pytest.mark.asyncio
    async def test_send_message_empty_ai_response(self, chat_svc, mock_db, mock_llm):
        """AI 返回空内容 → 使用兜底消息"""
        mock_db.messages.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))

        async def empty_stream(_messages):
            return
            yield  # never yields

        mock_llm.generate_stream = empty_stream

        events = []
        async for event in chat_svc.send_message(
            user_id="user1", session_id="session1", query="test",
        ):
            events.append(event)

        done = [e for e in events if e.get("done")]
        assert len(done) >= 1

    # ── 获取消息列表 ──

    @pytest.mark.asyncio
    async def test_get_messages_empty(self, chat_svc, mock_db):
        """空消息列表"""
        mock_db.messages.count_documents = AsyncMock(return_value=0)
        mock_db.messages.find.side_effect = lambda *a, **kw: _make_async_cursor([])

        messages, total = await chat_svc.get_messages("session1", 0, 50)
        assert messages == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_get_messages_with_data(self, chat_svc, mock_db):
        """有消息数据"""
        mock_db.messages.count_documents = AsyncMock(return_value=2)

        now = "2024-01-01T00:00:00"
        msg_docs = [
            {"_id": ObjectId(), "session_id": "s1", "role": "user", "content": "问题",
             "content_type": "text", "tokens": 0, "created_at": now},
            {"_id": ObjectId(), "session_id": "s1", "role": "assistant", "content": "回答",
             "content_type": "markdown", "tokens": 100, "created_at": now},
        ]

        mock_db.messages.find.side_effect = lambda *a, **kw: _make_async_cursor(msg_docs)

        messages, total = await chat_svc.get_messages("session1")

        assert len(messages) == 2
        assert total == 2
        assert messages[0]["role"] == "user"

    # ── 导出消息 ──

    @pytest.mark.asyncio
    async def test_export_messages(self, chat_svc, mock_db):
        """导出消息为文本"""
        mock_db.messages.count_documents = AsyncMock(return_value=2)

        msg_docs = [
            {"_id": ObjectId(), "session_id": "s1", "role": "user", "content": "问题是？",
             "content_type": "text", "tokens": 0, "created_at": "2024-01-01T00:00:00"},
            {"_id": ObjectId(), "session_id": "s1", "role": "assistant", "content": "答案是。",
             "content_type": "markdown", "tokens": 10, "created_at": "2024-01-01T00:00:01"},
        ]

        mock_db.messages.find.side_effect = lambda *a, **kw: _make_async_cursor(msg_docs)

        text = await chat_svc.export_messages("session1")

        assert "用户" in text
        assert "AI法律助手" in text
        assert "问题是？" in text
        assert "答案是。" in text
