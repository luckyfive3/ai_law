"""
services/safety_filter 模块单元测试
"""
import pytest
from services.safety_filter import SafetyFilter


class TestSafetyFilter:
    """安全过滤服务测试"""

    @pytest.fixture
    def sf(self):
        return SafetyFilter(enable=True)

    @pytest.fixture
    def sf_disabled(self):
        return SafetyFilter(enable=False)

    # ── system_prompt ──

    def test_system_prompt_not_empty(self, sf):
        """UT-SF-01: system_prompt 返回非空字符串"""
        prompt = sf.system_prompt()
        assert len(prompt) > 100
        assert "AI法律助手" in prompt

    def test_system_prompt_contains_keywords(self, sf):
        """system_prompt 包含关键指导语"""
        prompt = sf.system_prompt()
        assert "系统角色" in prompt
        assert "回答格式要求" in prompt
        assert "法条引用规范" in prompt
        assert "禁止行为" in prompt
        assert "拒答规则" in prompt
        assert "风险提示" in prompt
        assert "免责声明" in prompt

    # ── should_refuse ──

    def test_should_refuse_with_keyword(self, sf):
        """UT-SF-02: 包含'拒答'关键词返回 True"""
        assert sf.should_refuse("根据法律拒答此问题") is True

    def test_should_refuse_with_reject_keyword(self, sf):
        """包含'拒绝回答'关键词返回 True"""
        assert sf.should_refuse("此问题不可回答") is True

    def test_should_refuse_normal_answer(self, sf):
        """UT-SF-03: 正常回答不含拒答关键词返回 False"""
        assert sf.should_refuse("根据《民法典》第X条，您的情况...") is False

    def test_should_refuse_disabled(self, sf_disabled):
        """UT-SF-04: enable=False 时始终返回 False"""
        assert sf_disabled.should_refuse("此问题拒答处理") is False

    # ── refuse_answer ──

    def test_refuse_answer_returns_message(self, sf):
        """UT-SF-05: 拒答话术包含预期文本"""
        msg = sf.refuse_answer()
        assert "超出" in msg or "不能回答" in msg
        assert len(msg) > 0

    # ── append_disclaimer ──

    def test_append_disclaimer_adds_text(self, sf):
        """UT-SF-06: append_disclaimer 在末尾附加免责声明"""
        answer = "关于您的问题..."
        result = sf.append_disclaimer(answer)
        assert result.startswith("关于您的问题...")
        assert "免责声明" in result
        assert len(result) > len(answer)

    # ── get_fallback_message ──

    def test_get_fallback_message(self, sf):
        """UT-SF-07: 兜底消息包含预期文本"""
        msg = sf.get_fallback_message()
        assert "稍后再试" in msg or "暂不可用" in msg or "稍后" in msg
        assert len(msg) > 0
