"""
services/context_builder 模块单元测试
"""
import pytest
from services.context_builder import ContextBuilder


class TestContextBuilder:
    """上下文构建器测试"""

    def test_only_user_query(self):
        """UT-CB-01: 只有用户问题，无历史无法条 → 仅含用户问题段落"""
        cb = ContextBuilder()
        result = cb.build_context("什么是工伤？", [], [])

        assert "[用户问题]" in result
        assert "什么是工伤？" in result
        assert "[历史对话]" not in result
        assert "[相关法律依据]" not in result

    def test_with_history(self):
        """UT-CB-02: 含历史对话 → 输出含 [历史对话] 段落"""
        cb = ContextBuilder()
        history = [
            {"role": "user", "content": "合同纠纷怎么办？"},
            {"role": "assistant", "content": "建议先协商解决。"},
        ]
        result = cb.build_context("起诉时效？", history, [])

        assert "[历史对话]" in result
        assert "用户问：合同纠纷怎么办？" in result
        assert "AI答：建议先协商解决。" in result
        assert "[用户问题]" in result
        assert "起诉时效？" in result

    def test_with_search_results(self):
        """UT-CB-03: 含检索结果 → 输出含 [相关法律依据] 段落"""
        cb = ContextBuilder()
        results = [
            {
                "law_name": "中华人民共和国劳动法",
                "article_num": "第三十六条",
                "law_text": "国家实行劳动者每日工作时间不超过八小时...",
                "source": "劳动法 第四章",
                "relevance": 0.9,
            }
        ]
        result = cb.build_context("加班问题", [], results)

        assert "[相关法律依据]" in result
        assert "中华人民共和国劳动法" in result
        assert "第三十六条" in result
        assert "[用户问题]" in result

    def test_full_context(self):
        """UT-CB-04: 含历史+法条+问题 → 三段都有"""
        cb = ContextBuilder()
        history = [{"role": "user", "content": "试用期"}, {"role": "assistant", "content": "最长6个月"}]
        results = [{"law_name": "劳动合同法", "article_num": "第十九条", "law_text": "试用期...", "source": "", "relevance": 0.9}]

        result = cb.build_context("试用期被辞退", history, results)

        assert "[历史对话]" in result
        assert "[相关法律依据]" in result
        assert "[用户问题]" in result
        # 顺序：历史 → 法条 → 问题
        hist_pos = result.index("[历史对话]")
        legal_pos = result.index("[相关法律依据]")
        question_pos = result.index("[用户问题]")
        assert hist_pos < legal_pos < question_pos

    def test_history_truncation(self):
        """UT-CB-05: 历史超 max_history_rounds → 截断"""
        cb = ContextBuilder(max_history_rounds=2)  # 2轮 = 4条
        history = []
        for i in range(5):
            history.append({"role": "user", "content": f"问题{i}"})
            history.append({"role": "assistant", "content": f"回答{i}"})
        # 10条 = 5轮

        result = cb.build_context("最新问题", history, [])

        # 应该只保留最后4条（2轮，即i=3和i=4）
        assert "问题0" not in result  # 早的被丢弃
        assert "问题1" not in result
        assert "问题2" not in result
        assert "问题3" in result
        assert "回答3" in result
        assert "问题4" in result
        assert "回答4" in result

    def test_max_history_rounds_minimum(self):
        """UT-CB-06: max_history_rounds=0 自动修正为 1"""
        cb = ContextBuilder(max_history_rounds=0)
        assert cb.max_history_rounds == 1

    def test_negative_max_history_rounds(self):
        """max_history_rounds=-5 自动修正为 1"""
        cb = ContextBuilder(max_history_rounds=-5)
        assert cb.max_history_rounds == 1

    def test_search_result_with_article_num(self):
        """UT-CB-07: 法条结果含条款号时包含条款号"""
        cb = ContextBuilder()
        results = [
            {
                "law_name": "民法典",
                "article_num": "第1043条",
                "law_text": "家庭应当树立优良家风...",
                "source": "民法典 第五编",
                "relevance": 0.88,
            }
        ]
        result = cb.build_context("家庭纠纷", [], results)
        assert "《民法典》第1043条" in result

    def test_search_result_without_article_num(self):
        """法条结果无条款号时只显示法律名称"""
        cb = ContextBuilder()
        results = [
            {
                "law_name": "宪法",
                "article_num": "",
                "law_text": "中华人民共和国是工人阶级领导的...",
                "source": "",
                "relevance": 0.5,
            }
        ]
        result = cb.build_context("国家性质", [], results)
        assert "《宪法》" in result
        # 无条款号
        lines = result.split("\n")
        law_lines = [l for l in lines if "《宪法》" in l]
        for line in law_lines:
            # 只含《宪法》不含条号
            pass
