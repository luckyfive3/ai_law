"""
AI法律助手 v1.0 — 上下文拼接服务
负责将历史对话、检索法条和用户问题拼接为 LLM 上下文
"""
import logging
from typing import List

logger = logging.getLogger(__name__)


class ContextBuilder:
    """
    上下文构建器
    将历史对话、检索结果和用户问题组织为结构化的 Prompt
    """

    def __init__(self, max_history_rounds: int = 3):
        """
        初始化上下文构建器

        Args:
            max_history_rounds: 最大历史对话轮数（每轮 = user + assistant）
        """
        self.max_history_rounds = max(1, max_history_rounds)

    # ═══════════════════════════════════════
    # 上下文构建
    # ═══════════════════════════════════════

    def build_context(
        self,
        user_query: str,
        history_messages: List[dict],
        search_results: List[dict],
    ) -> str:
        """
        构建完整的 Prompt 上下文

        Args:
            user_query: 用户当前提问
            history_messages: 历史消息列表，每条含 role 和 content
            search_results: 检索到的法条列表，每条含:
                - law_name: 法律名称
                - article_num: 条款号
                - law_text: 法条原文
                - source: 来源
                - relevance: 相关度

        Returns:
            拼接好的上下文字符串
        """
        sections: List[str] = []

        # ── 1. 历史对话 ──
        if history_messages:
            history_section = self._build_history_section(history_messages)
            sections.append(history_section)

        # ── 2. 相关法律依据 ──
        if search_results:
            legal_section = self._build_legal_section(search_results)
            sections.append(legal_section)

        # ── 3. 用户问题 ──
        question_section = self._build_question_section(user_query)
        sections.append(question_section)

        return "\n\n".join(sections)

    def _build_history_section(self, history_messages: List[dict]) -> str:
        """
        构建 [历史对话] 段落

        Args:
            history_messages: 历史消息列表

        Returns:
            格式化的历史对话文本
        """
        lines = ["[历史对话]"]

        # 只取最近 N 轮（每轮 = user + assistant，共 2 条）
        max_messages = self.max_history_rounds * 2
        recent = history_messages[-max_messages:] if len(history_messages) > max_messages else history_messages

        for msg in recent:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                lines.append(f"用户问：{content}")
            elif role == "assistant":
                lines.append(f"AI答：{content}")

        return "\n".join(lines)

    def _build_legal_section(self, search_results: List[dict]) -> str:
        """
        构建 [相关法律依据] 段落

        Args:
            search_results: 检索结果列表

        Returns:
            格式化的法律依据文本
        """
        lines = ["[相关法律依据]"]

        for i, result in enumerate(search_results, start=1):
            law_name = result.get("law_name", "未知法律")
            article_num = result.get("article_num", "")
            law_text = result.get("law_text", "")
            source = result.get("source", "")

            # 条款编号格式化：如果有条款号就加上，否则只显示法律名称
            if article_num:
                lines.append(f"{i}. 《{law_name}》{article_num}")
            else:
                lines.append(f"{i}. 《{law_name}》")

            lines.append(f"   原文：{law_text}")
            if source:
                lines.append(f"   来源：{source}")

        return "\n".join(lines)

    def _build_question_section(self, user_query: str) -> str:
        """
        构建 [用户问题] 段落

        Args:
            user_query: 用户当前提问

        Returns:
            格式化的用户问题文本
        """
        return f"[用户问题]\n{user_query}"
