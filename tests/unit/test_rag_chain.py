"""
services/rag_chain 模块单元测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from services.rag_chain import LegalRAGChain


class TestDictToLangchainMessages:
    """dict_to_langchain_messages 静态方法测试"""

    def test_converts_user(self):
        from langchain_core.messages import HumanMessage
        msgs = [{"role": "user", "content": "你好"}]
        result = LegalRAGChain.dict_to_langchain_messages(msgs)
        assert len(result) == 1
        assert isinstance(result[0], HumanMessage)

    def test_converts_assistant(self):
        from langchain_core.messages import AIMessage
        msgs = [{"role": "assistant", "content": "您好"}]
        result = LegalRAGChain.dict_to_langchain_messages(msgs)
        assert isinstance(result[0], AIMessage)

    def test_converts_system(self):
        from langchain_core.messages import SystemMessage
        msgs = [{"role": "system", "content": "你是助手"}]
        result = LegalRAGChain.dict_to_langchain_messages(msgs)
        assert isinstance(result[0], SystemMessage)

    def test_converts_mixed(self):
        msgs = [
            {"role": "system", "content": "系统提示"},
            {"role": "user", "content": "问题"},
            {"role": "assistant", "content": "回答"},
        ]
        result = LegalRAGChain.dict_to_langchain_messages(msgs)
        assert len(result) == 3

    def test_converts_empty(self):
        result = LegalRAGChain.dict_to_langchain_messages([])
        assert result == []

    def test_unknown_role_defaults_to_human(self):
        from langchain_core.messages import HumanMessage
        msgs = [{"role": "unknown", "content": "test"}]
        result = LegalRAGChain.dict_to_langchain_messages(msgs)
        assert isinstance(result[0], HumanMessage)


class TestLegalRAGChainInit:
    """初始化测试"""

    def test_init_builds_chain(self):
        mock_llm = MagicMock()
        mock_retriever = MagicMock()
        chain = LegalRAGChain(llm=mock_llm, retriever=mock_retriever)
        assert chain._chain is not None
        assert chain._stream_chain is not None
        assert chain.llm is mock_llm
        assert chain.retriever is mock_retriever
