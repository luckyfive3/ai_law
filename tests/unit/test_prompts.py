"""
services/prompts 模块单元测试
"""
import pytest
from services.prompts import build_legal_consult_prompt, SESSION_SUMMARY_PROMPT


class TestBuildLegalConsultPrompt:
    """build_legal_consult_prompt 测试"""

    def test_returns_chat_prompt_template(self):
        from langchain_core.prompts import ChatPromptTemplate
        prompt = build_legal_consult_prompt()
        assert isinstance(prompt, ChatPromptTemplate)

    def test_has_required_variables(self):
        """包含 legal_context、history、question 变量"""
        prompt = build_legal_consult_prompt()
        vars = prompt.input_variables
        assert "legal_context" in vars
        assert "history" in vars
        assert "question" in vars

    def test_invoke_returns_messages(self):
        """invoke 返回消息列表"""
        from langchain_core.messages import HumanMessage
        prompt = build_legal_consult_prompt()
        result = prompt.invoke({
            "legal_context": "法条内容",
            "history": [HumanMessage(content="之前的问题")],
            "question": "新问题",
        })
        msgs = result.to_messages()
        assert len(msgs) >= 2  # system + history + human

    def test_system_message_contains_role(self):
        """system 消息包含 AI法律助手 角色定义"""
        prompt = build_legal_consult_prompt()
        result = prompt.invoke({
            "legal_context": "",
            "history": [],
            "question": "test",
        })
        msgs = result.to_messages()
        system_msg = msgs[0]
        assert "AI法律助手" in system_msg.content
        assert "免责声明" in system_msg.content

    def test_human_message_contains_legal_context(self):
        """human 消息包含法条上下文和用户问题"""
        prompt = build_legal_consult_prompt()
        result = prompt.invoke({
            "legal_context": "《民法典》第1条",
            "history": [],
            "question": "什么是合同？",
        })
        text = result.to_messages()[-1].content
        assert "民法典" in text
        assert "合同" in text


class TestSessionSummaryPrompt:
    """SESSION_SUMMARY_PROMPT 测试"""

    def test_is_chat_prompt_template(self):
        from langchain_core.prompts import ChatPromptTemplate
        assert isinstance(SESSION_SUMMARY_PROMPT, ChatPromptTemplate)

    def test_invoke_with_conversation(self):
        result = SESSION_SUMMARY_PROMPT.invoke({
            "conversation": "用户: 咨询工伤\nAI: 建议认定"
        })
        msgs = result.to_messages()
        assert len(msgs) == 2  # system + human
        assert "工伤" in msgs[1].content
