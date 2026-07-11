"""
services/langchain_callbacks 模块单元测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from services.langchain_callbacks import LegalAICallbackHandler


class TestLegalAICallbackHandler:
    """LangChain 回调处理器测试"""

    def test_init_defaults(self):
        """初始化默认值"""
        handler = LegalAICallbackHandler()
        assert handler.session_id == ""
        assert handler.user_id == ""
        assert handler.db is None
        assert handler.total_input_tokens == 0
        assert handler.llm_call_count == 0
        assert handler.retrieval_count == 0

    def test_init_with_params(self):
        """初始化传参"""
        db = MagicMock()
        handler = LegalAICallbackHandler(
            session_id="sid123", user_id="uid456", db=db
        )
        assert handler.session_id == "sid123"
        assert handler.user_id == "uid456"
        assert handler.db is db

    def test_on_llm_start_increments_count(self):
        """LLM 开始 → call_count + 1"""
        handler = LegalAICallbackHandler()
        handler.on_llm_start(
            serialized={}, prompts=["test prompt"],
            run_id=uuid4(),
        )
        assert handler.llm_call_count == 1

    def test_on_llm_end_updates_tokens(self):
        """LLM 结束 → 统计 token"""
        handler = LegalAICallbackHandler()
        handler.on_llm_start(
            serialized={}, prompts=["test"],
            run_id=uuid4(),
        )

        from langchain_core.outputs import LLMResult, Generation, ChatGeneration
        response = LLMResult(
            generations=[[Generation(text="reply")]],
            llm_output={
                "token_usage": {
                    "prompt_tokens": 50,
                    "completion_tokens": 30,
                }
            },
        )
        handler.on_llm_end(response, run_id=uuid4())
        assert handler.total_input_tokens == 50
        assert handler.total_output_tokens == 30

    def test_on_llm_end_no_token_usage(self):
        """无 token_usage → 不更新"""
        handler = LegalAICallbackHandler()
        handler.on_llm_start(serialized={}, prompts=["test"], run_id=uuid4())

        from langchain_core.outputs import LLMResult, Generation
        response = LLMResult(
            generations=[[Generation(text="reply")]],
            llm_output={},
        )
        handler.on_llm_end(response, run_id=uuid4())
        assert handler.total_input_tokens == 0

    def test_on_llm_error_records(self):
        """LLM 错误 → errors 列表记录"""
        handler = LegalAICallbackHandler(session_id="test")
        handler.on_llm_error(
            ValueError("API timeout"), run_id=uuid4()
        )
        assert len(handler.errors) == 1
        assert "ValueError" in handler.errors[0]

    def test_on_retriever_start_increments(self):
        """检索开始 → retrieval_count + 1"""
        handler = LegalAICallbackHandler()
        handler.on_retriever_start(
            serialized={}, query="法律问题",
            run_id=uuid4(),
        )
        assert handler.retrieval_count == 1

    def test_on_retriever_end(self):
        """检索结束 → 记录日志"""
        handler = LegalAICallbackHandler(session_id="test")
        # 不应该抛异常
        handler.on_retriever_end(documents=[], run_id=uuid4())

    def test_on_retriever_error_records(self):
        """检索错误 → errors 列表记录"""
        handler = LegalAICallbackHandler(session_id="test")
        handler.on_retriever_error(
            ConnectionError("timeout"), run_id=uuid4()
        )
        assert len(handler.errors) == 1

    def test_on_chain_start_end(self):
        """chain 事件 → 不抛异常"""
        handler = LegalAICallbackHandler()
        rid = uuid4()
        handler.on_chain_start(serialized={}, inputs={}, run_id=rid)
        handler.on_chain_end(outputs={}, run_id=rid)
        # 不抛异常即通过

    def test_on_chain_error_records(self):
        """chain 错误 → errors 列表记录"""
        handler = LegalAICallbackHandler()
        handler.on_chain_error(ValueError("bad"), run_id=uuid4())
        assert len(handler.errors) == 1

    def test_get_stats(self):
        """get_stats 返回统计摘要"""
        handler = LegalAICallbackHandler(session_id="s1", user_id="u1")
        handler.on_llm_start(serialized={}, prompts=["p"], run_id=uuid4())
        from langchain_core.outputs import LLMResult, Generation
        response = LLMResult(
            generations=[[Generation(text="r")]],
            llm_output={"token_usage": {"prompt_tokens": 10, "completion_tokens": 5}},
        )
        handler.on_llm_end(response, run_id=uuid4())

        stats = handler.get_stats()
        assert stats["session_id"] == "s1"
        assert stats["llm_call_count"] == 1
        assert stats["total_input_tokens"] == 10
        assert stats["total_output_tokens"] == 5

    def test_reset(self):
        """reset 清零所有计数器"""
        handler = LegalAICallbackHandler()
        handler.total_input_tokens = 100
        handler.llm_call_count = 5
        handler.retrieval_count = 3
        handler.errors = ["err1", "err2"]

        handler.reset()
        assert handler.total_input_tokens == 0
        assert handler.llm_call_count == 0
        assert handler.retrieval_count == 0
        assert handler.errors == []

    def test_get_stats_no_latency(self):
        """无 LLM 调用时 avg_latency 为 0"""
        handler = LegalAICallbackHandler()
        stats = handler.get_stats()
        assert stats["avg_latency"] == 0

    def test_save_token_usage(self):
        """保存 token 用量到 DB"""
        from unittest.mock import patch as local_patch

        db = MagicMock()
        db.token_usage.insert_one = AsyncMock()
        handler = LegalAICallbackHandler(
            session_id="s1", user_id="u1", db=db
        )
        handler.total_input_tokens = 100
        handler.total_output_tokens = 50

        loop = MagicMock()
        loop.create_task = MagicMock()

        with local_patch("asyncio.get_running_loop", return_value=loop):
            handler._save_token_usage()
            loop.create_task.assert_called_once()
