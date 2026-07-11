"""
services/llm_service 模块单元测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage


class TestLLMServiceConvertMessages:
    """消息转换静态方法测试"""

    def test_convert_system_message(self):
        """system role → SystemMessage"""
        from services.llm_service import LLMService
        messages = [{"role": "system", "content": "你是一个法律助手"}]
        converted = LLMService._convert_messages(messages)
        assert len(converted) == 1
        assert isinstance(converted[0], SystemMessage)
        assert converted[0].content == "你是一个法律助手"

    def test_convert_human_message(self):
        """user role → HumanMessage"""
        from services.llm_service import LLMService
        messages = [{"role": "user", "content": "什么是工伤"}]
        converted = LLMService._convert_messages(messages)
        assert len(converted) == 1
        assert isinstance(converted[0], HumanMessage)

    def test_convert_assistant_message(self):
        """assistant role → AIMessage"""
        from services.llm_service import LLMService
        messages = [{"role": "assistant", "content": "根据法律..."}]
        converted = LLMService._convert_messages(messages)
        assert len(converted) == 1
        assert isinstance(converted[0], AIMessage)

    def test_convert_mixed_messages(self):
        """混合角色消息列表转换"""
        from services.llm_service import LLMService
        messages = [
            {"role": "system", "content": "prompt"},
            {"role": "user", "content": "问题"},
            {"role": "assistant", "content": "回答"},
        ]
        converted = LLMService._convert_messages(messages)
        assert len(converted) == 3
        assert isinstance(converted[0], SystemMessage)
        assert isinstance(converted[1], HumanMessage)
        assert isinstance(converted[2], AIMessage)

    def test_convert_unknown_role(self):
        """未知 role → HumanMessage（默认）"""
        from services.llm_service import LLMService
        messages = [{"role": "unknown_role", "content": "test"}]
        converted = LLMService._convert_messages(messages)
        assert len(converted) == 1
        assert isinstance(converted[0], HumanMessage)

    def test_convert_empty_list(self):
        """空列表返回空列表"""
        from services.llm_service import LLMService
        converted = LLMService._convert_messages([])
        assert converted == []


class TestLLMService:
    """LLM 服务核心测试"""

    @pytest.fixture
    def mock_settings(self):
        s = MagicMock()
        s.llm_model = "deepseek-chat"
        s.llm_base_url = "https://api.deepseek.com/v1"
        s.llm_api_key = "sk-test-key"
        s.llm_temperature = 0.2
        s.llm_max_tokens = 2048
        s.llm_timeout = 30
        s.llm_max_retries = 3
        return s

    def test_init_creates_chat_openai(self, mock_settings):
        """初始化时创建 ChatOpenAI 实例"""
        with patch("services.llm_service.ChatOpenAI") as mock_llm:
            from services.llm_service import LLMService
            svc = LLMService(mock_settings)

            mock_llm.assert_called_once()
            assert svc.model == "deepseek-chat"
            assert svc._llm is not None

    @pytest.mark.asyncio
    async def test_generate_when_llm_is_none(self, mock_settings):
        """LLM未初始化 → 返回兜底消息"""
        with patch("services.llm_service.ChatOpenAI", side_effect=Exception("init fail")):
            from services.llm_service import LLMService
            svc = LLMService(mock_settings)
            svc._llm = None

            result = await svc.generate([{"role": "user", "content": "test"}])
            assert "暂不可用" in result or "请稍后" in result

    @pytest.mark.asyncio
    async def test_generate_success(self, mock_settings):
        """非流式生成成功"""
        with patch("services.llm_service.ChatOpenAI") as mock_llm_class:
            mock_llm = MagicMock()
            mock_llm.ainvoke = AsyncMock()
            mock_response = MagicMock()
            mock_response.content = "法律分析结果..."
            mock_llm.ainvoke.return_value = mock_response
            mock_llm_class.return_value = mock_llm

            from services.llm_service import LLMService
            svc = LLMService(mock_settings)

            result = await svc.generate([{"role": "user", "content": "合同纠纷"}])
            assert "法律分析结果" in result

    @pytest.mark.asyncio
    async def test_generate_exception_fallback(self, mock_settings):
        """LLM调用异常 → 返回错误兜底消息"""
        with patch("services.llm_service.ChatOpenAI") as mock_llm_class:
            mock_llm = MagicMock()
            mock_llm.ainvoke = AsyncMock(side_effect=Exception("API error"))
            mock_llm_class.return_value = mock_llm

            from services.llm_service import LLMService
            svc = LLMService(mock_settings)

            result = await svc.generate([{"role": "user", "content": "test"}])
            assert "暂不可用" in result or "异常" in result or "稍后" in result

    @pytest.mark.asyncio
    async def test_generate_stream_success(self, mock_settings):
        """流式生成逐个yield token"""
        with patch("services.llm_service.ChatOpenAI") as mock_llm_class:
            mock_llm = MagicMock()

            async def mock_astream(_messages):
                class Chunk:
                    def __init__(self, c):
                        self.content = c
                for t in ["根据", "《民法典》", "规定"]:
                    yield Chunk(t)

            mock_llm.astream = mock_astream
            mock_llm_class.return_value = mock_llm

            from services.llm_service import LLMService
            svc = LLMService(mock_settings)

            tokens = []
            async for token in svc.generate_stream([{"role": "user", "content": "test"}]):
                tokens.append(token)

            assert len(tokens) == 3
            assert "".join(tokens) == "根据《民法典》规定"

    @pytest.mark.asyncio
    async def test_generate_stream_llm_none(self, mock_settings):
        """LLM未初始化 → yield 兜底消息后停止"""
        with patch("services.llm_service.ChatOpenAI", side_effect=Exception("init fail")):
            from services.llm_service import LLMService
            svc = LLMService(mock_settings)
            svc._llm = None

            tokens = []
            async for token in svc.generate_stream([{"role": "user", "content": "test"}]):
                tokens.append(token)

            assert len(tokens) == 1
            assert "暂不可用" in tokens[0]

    @pytest.mark.asyncio
    async def test_generate_stream_exception_fallback(self, mock_settings):
        """流式异常 → yield 兜底消息后停止"""
        with patch("services.llm_service.ChatOpenAI") as mock_llm_class:
            mock_llm = MagicMock()
            mock_llm.astream = MagicMock(side_effect=Exception("stream error"))
            mock_llm_class.return_value = mock_llm

            from services.llm_service import LLMService
            svc = LLMService(mock_settings)

            tokens = []
            async for token in svc.generate_stream([{"role": "user", "content": "test"}]):
                tokens.append(token)

            assert len(tokens) == 1
            assert "暂不可用" in tokens[0] or "异常" in tokens[0] or "稍后" in tokens[0]
