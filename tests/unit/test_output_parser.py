"""
services/output_parser 模块单元测试
"""
import pytest
from services.output_parser import (
    LawReference, LegalAnalysis, RefuseResponse,
    parse_legal_analysis, is_refused, get_legal_analysis_system_prompt,
)


class TestPydanticModels:
    """结构化输出数据模型"""

    def test_law_reference_valid(self):
        ref = LawReference(
            law_name="《中华人民共和国民法典》",
            article="第1043条",
            content="家庭应当树立优良家风",
            relevance="直接相关",
        )
        assert ref.law_name == "《中华人民共和国民法典》"

    def test_law_reference_missing_field(self):
        """缺少必填字段 → ValidationError"""
        with pytest.raises(Exception):
            LawReference(law_name="《民法典》")

    def test_legal_analysis_valid(self):
        analysis = LegalAnalysis(
            category="婚姻家庭",
            issue_analysis="涉及家庭关系",
            legal_basis=[],
            suggestion="建议协商",
            risk_warning="以上仅供参考",
            need_lawyer=False,
        )
        assert analysis.category == "婚姻家庭"
        assert analysis.need_lawyer is False

    def test_refuse_response(self):
        r = RefuseResponse(refused=True, reason="超出法律咨询范畴")
        assert r.refused is True
        assert "超出" in r.reason


class TestParseLegalAnalysis:
    """parse_legal_analysis 函数测试"""

    def test_valid_json_output(self):
        """标准 JSON → LegalAnalysis"""
        valid_json = '''{
            "category": "劳动纠纷",
            "issue_analysis": "工伤认定问题",
            "legal_basis": [
                {
                    "law_name": "工伤保险条例",
                    "article": "第14条",
                    "content": "应当认定为工伤的情形",
                    "relevance": "直接适用"
                }
            ],
            "suggestion": "建议申请工伤认定",
            "risk_warning": "证据完整性很重要",
            "need_lawyer": true
        }'''
        result = parse_legal_analysis(valid_json)
        assert result is not None
        assert result.category == "劳动纠纷"
        assert len(result.legal_basis) == 1
        assert result.need_lawyer is True

    def test_json_with_extra_text(self):
        """JSON 被包裹在额外文本中 → 提取并解析"""
        text = '根据分析，结果如下：\n```json\n{"category": "刑事法律", "issue_analysis": "test", "legal_basis": [], "suggestion": "建议报警", "risk_warning": "注意安全", "need_lawyer": true}\n```'
        result = parse_legal_analysis(text)
        assert result is not None
        assert result.category == "刑事法律"

    def test_invalid_text(self):
        """完全无法解析的文本 → None"""
        result = parse_legal_analysis("这是一段普通的文字回复，不是JSON格式")
        assert result is None

    def test_missing_fields_in_json(self):
        """JSON 缺少部分字段 → 兜底解析使用默认值"""
        text = '{"category": "婚姻家庭"}'
        result = parse_legal_analysis(text)
        # 兜底解析成功，缺失字段使用默认值
        assert result is not None
        assert result.category == "婚姻家庭"


class TestIsRefused:
    """is_refused 函数测试"""

    def test_refused_response(self):
        text = '{"refused": true, "reason": "超出法律咨询范围"}'
        refused, reason = is_refused(text)
        assert refused is True
        assert "超出" in reason

    def test_not_refused(self):
        """非拒答格式 → False"""
        refused, reason = is_refused("这是正常回答")
        assert refused is False

    def test_refused_false_json(self):
        """refused 为 false → (False, '')"""
        text = '{"refused": false, "reason": ""}'
        refused, reason = is_refused(text)
        assert refused is False


class TestSystemPrompt:
    """get_legal_analysis_system_prompt 函数测试"""

    def test_returns_non_empty_string(self):
        prompt = get_legal_analysis_system_prompt()
        assert len(prompt) > 50
        assert "AI" in prompt or "JSON" in prompt
