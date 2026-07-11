"""
services/llm_service_v2 模块单元测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestLLMServiceV2:
    """LLM 服务 v2 单元测试"""

    @pytest.fixture
    def mock_settings(self):
        s = MagicMock()
        s.llm_model = "deepseek-chat"
        s.llm_base_url = "https://api.deepseek.com/v1"
        s.llm_api_key = "test-key"
        s.llm_temperature = 0.3
        s.llm_max_tokens = 2000
        s.llm_timeout = 30
        s.llm_max_retries = 2
        return s

    def test_init_creates_chat_openai(self, mock_settings):
        """初始化时创建 ChatOpenAI 实例"""
        with patch("services.llm_service_v2.ChatOpenAI") as mock_chat:
            from services.llm_service_v2 import LLMService
            svc = LLMService(mock_settings)
            mock_chat.assert_called_once()
            assert svc.model == "deepseek-chat"
            assert svc.temperature == 0.3

    def test_init_with_callbacks(self, mock_settings):
        """初始化时传入 callbacks"""
        cb = MagicMock()
        with patch("services.llm_service_v2.ChatOpenAI") as mock_chat:
            from services.llm_service_v2 import LLMService
            svc = LLMService(mock_settings, callbacks=[cb])
            assert len(svc.get_callbacks()) == 1

    def test_init_failure_sets_llm_none(self, mock_settings):
        """ChatOpenAI 初始化失败 → _llm 为 None"""
        with patch("services.llm_service_v2.ChatOpenAI", side_effect=Exception("init error")):
            from services.llm_service_v2 import LLMService
            svc = LLMService(mock_settings)
            assert svc.get_llm() is None

    def test_get_llm_returns_instance(self, mock_settings):
        """get_llm 返回底层实例"""
        with patch("services.llm_service_v2.ChatOpenAI"):
            from services.llm_service_v2 import LLMService
            svc = LLMService(mock_settings)
            assert svc.get_llm() is not None

    def test_convert_messages(self, mock_settings):
        """消息转换：字典 → LangChain 消息"""
        with patch("services.llm_service_v2.ChatOpenAI"):
            from services.llm_service_v2 import LLMService
            from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
            svc = LLMService(mock_settings)

            messages = [
                {"role": "system", "content": "You are helpful"},
                {"role": "assistant", "content": "Hi there"},
                {"role": "user", "content": "Hello"},
                {"role": "", "content": "unknown role"},
            ]
            result = svc._convert_messages(messages)
            assert len(result) == 4
            assert isinstance(result[0], SystemMessage)
            assert isinstance(result[1], AIMessage)
            assert isinstance(result[2], HumanMessage)
            assert isinstance(result[3], HumanMessage)  # unknown → HumanMessage

    # ── generate ──

    @pytest.mark.asyncio
    async def test_generate_success(self, mock_settings):
        """非流式调用成功"""
        with patch("services.llm_service_v2.ChatOpenAI") as mock_chat:
            mock_llm = MagicMock()
            mock_llm.ainvoke = AsyncMock()
            mock_response = MagicMock()
            mock_response.content = "这是AI的回答"
            mock_llm.ainvoke.return_value = mock_response
            mock_chat.return_value = mock_llm

            from services.llm_service_v2 import LLMService
            svc = LLMService(mock_settings)
            result = await svc.generate([{"role": "user", "content": "test"}])
            assert result == "这是AI的回答"

    @pytest.mark.asyncio
    async def test_generate_llm_none(self, mock_settings):
        """LLM 未初始化 → 返回兜底消息"""
        with patch("services.llm_service_v2.ChatOpenAI", side_effect=Exception("fail")):
            from services.llm_service_v2 import LLMService
            svc = LLMService(mock_settings)
            result = await svc.generate([{"role": "user", "content": "test"}])
            assert "暂不可用" in result

    @pytest.mark.asyncio
    async def test_generate_failure(self, mock_settings):
        """LLM 调用失败 → 返回兜底消息"""
        with patch("services.llm_service_v2.ChatOpenAI") as mock_chat:
            mock_llm = MagicMock()
            mock_llm.ainvoke = AsyncMock(side_effect=Exception("API error"))
            mock_chat.return_value = mock_llm

            from services.llm_service_v2 import LLMService
            svc = LLMService(mock_settings)
            result = await svc.generate([{"role": "user", "content": "test"}])
            assert "暂时异常" in result

    # ── generate_stream ──

    @pytest.mark.asyncio
    async def test_generate_stream_success(self, mock_settings):
        """流式调用成功"""
        with patch("services.llm_service_v2.ChatOpenAI") as mock_chat:
            mock_llm = MagicMock()

            async def fake_astream(_msgs):
                chunks = [MagicMock(content="你好"), MagicMock(content="世界")]
                for c in chunks:
                    yield c

            mock_llm.astream = fake_astream
            mock_chat.return_value = mock_llm

            from services.llm_service_v2 import LLMService
            svc = LLMService(mock_settings)
            tokens = []
            async for t in svc.generate_stream([{"role": "user", "content": "hi"}]):
                tokens.append(t)
            assert tokens == ["你好", "世界"]

    @pytest.mark.asyncio
    async def test_generate_stream_llm_none(self, mock_settings):
        """LLM 未初始化 → yield 兜底消息"""
        with patch("services.llm_service_v2.ChatOpenAI", side_effect=Exception("fail")):
            from services.llm_service_v2 import LLMService
            svc = LLMService(mock_settings)
            tokens = []
            async for t in svc.generate_stream([{"role": "user", "content": "test"}]):
                tokens.append(t)
            assert len(tokens) == 1
            assert "暂不可用" in tokens[0]

    @pytest.mark.asyncio
    async def test_generate_stream_failure(self, mock_settings):
        """流式调用失败 → yield 兜底消息"""
        with patch("services.llm_service_v2.ChatOpenAI") as mock_chat:
            mock_llm = MagicMock()
            mock_llm.astream = MagicMock(side_effect=Exception("stream error"))
            mock_chat.return_value = mock_llm

            from services.llm_service_v2 import LLMService
            svc = LLMService(mock_settings)
            tokens = []
            async for t in svc.generate_stream([{"role": "user", "content": "test"}]):
                tokens.append(t)
            assert len(tokens) == 1
            assert "暂时异常" in tokens[0]

    # ── generate_structured ──

    @pytest.mark.asyncio
    async def test_generate_structured_success(self, mock_settings):
        """结构化生成成功"""
        with patch("services.llm_service_v2.ChatOpenAI") as mock_chat:
            mock_llm = MagicMock()
            mock_parser = MagicMock()

            # mock chain (LLM | parser)
            mock_chain = MagicMock()
            mock_chain.ainvoke = AsyncMock(return_value={"category": "civil"})
            mock_llm.__or__.return_value = mock_chain
            mock_chat.return_value = mock_llm

            from services.llm_service_v2 import LLMService
            svc = LLMService(mock_settings)
            result = await svc.generate_structured(
                [{"role": "user", "content": "合同纠纷"}], mock_parser
            )
            assert result == {"category": "civil"}

    @pytest.mark.asyncio
    async def test_generate_structured_llm_none(self, mock_settings):
        """LLM 未初始化 → None"""
        with patch("services.llm_service_v2.ChatOpenAI", side_effect=Exception("fail")):
            from services.llm_service_v2 import LLMService
            svc = LLMService(mock_settings)
            result = await svc.generate_structured([], MagicMock())
            assert result is None

    @pytest.mark.asyncio
    async def test_generate_structured_failure(self, mock_settings):
        """结构化生成失败 → None"""
        with patch("services.llm_service_v2.ChatOpenAI") as mock_chat:
            mock_llm = MagicMock()
            mock_llm.__or__.return_value.ainvoke = AsyncMock(
                side_effect=Exception("parse error"))
            mock_chat.return_value = mock_llm

            from services.llm_service_v2 import LLMService
            svc = LLMService(mock_settings)
            result = await svc.generate_structured(
                [{"role": "user", "content": "test"}], MagicMock()
            )
            assert result is None
