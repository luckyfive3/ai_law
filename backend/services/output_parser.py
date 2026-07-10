"""
AI法律助手 v1.0 — 结构化输出解析器
使用 PydanticOutputParser 让 LLM 返回可被代码直接消费的结构化数据
"""
from __future__ import annotations

import json
import logging
from typing import List, Optional

from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.exceptions import OutputParserException

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════
# 1. Pydantic 数据模型
# ═══════════════════════════════════════

class LawReference(BaseModel):
    """单条法条引用"""
    law_name: str = Field(description="法律全称，如《中华人民共和国民法典》")
    article: str = Field(description="条款号，如第X条第Y款")
    content: str = Field(description="法条原文")
    relevance: str = Field(description="与本问题的关联说明")


class LegalAnalysis(BaseModel):
    """法律分析完整结果"""
    category: str = Field(description="问题分类：婚姻家庭|劳动纠纷|合同纠纷|交通事故|房产纠纷|消费维权|刑事法律|行政法律|其他")
    issue_analysis: str = Field(description="问题分析：法律关系梳理")
    legal_basis: List[LawReference] = Field(description="引用的法律依据列表")
    suggestion: str = Field(description="建议/结论")
    risk_warning: str = Field(description="风险提示")
    need_lawyer: bool = Field(description="是否强烈建议咨询律师")


class RefuseResponse(BaseModel):
    """拒答响应"""
    refused: bool = Field(default=True, description="是否拒答")
    reason: str = Field(description="拒答原因")


# ═══════════════════════════════════════
# 2. 输出解析器
# ═══════════════════════════════════════

# 法律分析解析器
legal_analysis_parser = PydanticOutputParser(pydantic_object=LegalAnalysis)

# 拒答解析器
refuse_parser = PydanticOutputParser(pydantic_object=RefuseResponse)


# ═══════════════════════════════════════
# 3. 带格式指令的 System Prompt（供 Prompt 模板使用）
# ═══════════════════════════════════════

LEGAL_ANALYSIS_FORMAT_INSTRUCTIONS = legal_analysis_parser.get_format_instructions()


def get_legal_analysis_system_prompt() -> str:
    """
    返回包含 JSON 输出格式指令的 System Prompt
    可直接插入 ChatPromptTemplate 的 system 消息中
    """
    return (
        "[系统角色]\n"
        "你是一名专业的AI法律助手，基于权威法律法规为用户提供法律信息参考。\n"
        "你必须严格基于检索到的真实法条回答问题，不得虚构或编造法律条文。\n"
        "你没有律师执业资格，你的回答不构成法律意见。\n"
        "你的服务对象是普通中国公民，回答应使用通俗易懂的中文。\n\n"
        "[输出格式要求]\n"
        "你必须只输出 JSON 格式，不要有任何其他文字。JSON 格式如下：\n"
        + LEGAL_ANALYSIS_FORMAT_INSTRUCTIONS +
        "\n\n[拒答规则]\n"
        "如果问题超出法律咨询范畴，返回 JSON: {\"refused\": true, \"reason\": \"拒答原因\"}"
    )


def parse_legal_analysis(text: str) -> Optional[LegalAnalysis]:
    """
    安全解析 LLM 返回的法律分析 JSON

    Args:
        text: LLM 输出的原始文本

    Returns:
        LegalAnalysis 实例；解析失败返回 None
    """
    try:
        return legal_analysis_parser.parse(text)
    except OutputParserException:
        # 兜底：尝试从文本中提取 JSON
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            json_str = text[start:end]
            result_dict = json.loads(json_str)

            # 手动构建
            laws = []
            for ref in result_dict.get("legal_basis", []):
                laws.append(LawReference(
                    law_name=ref.get("law_name", ""),
                    article=ref.get("article", ""),
                    content=ref.get("content", ""),
                    relevance=ref.get("relevance", ""),
                ))

            return LegalAnalysis(
                category=result_dict.get("category", "其他"),
                issue_analysis=result_dict.get("issue_analysis", ""),
                legal_basis=laws,
                suggestion=result_dict.get("suggestion", ""),
                risk_warning=result_dict.get("risk_warning", ""),
                need_lawyer=result_dict.get("need_lawyer", False),
            )
        except (ValueError, KeyError) as e:
            logger.warning(f"结构化输出解析失败: {e}, raw_text[:200]={text[:200]}")
            return None


def is_refused(text: str) -> tuple[bool, str]:
    """
    判断 LLM 响应是否为拒答

    Returns:
        (是否拒答, 拒答原因)
    """
    try:
        result = refuse_parser.parse(text)
        return result.refused, result.reason
    except OutputParserException:
        return False, ""
