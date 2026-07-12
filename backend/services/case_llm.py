"""案件 LLM 分析器 — 接入 DeepSeek API"""
import logging, json as _json, httpx
logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """[角色] 你是一名资深法律分析师，擅长从案件文件中提取关键信息并进行专业法律分析。

[案件基本信息]
案件名称：{title}
案件类型：{case_type}
审理阶段：{court_level}
案件描述：{description}

[上传文件内容]
{file_contents}

[要求] 基于以上信息，严格按以下JSON格式输出（只输出JSON，不要Markdown代码块，不要其他文字）：
{{
  "案情摘要": "200-300字概括案件核心事实与法律关系",
  "案情时间轴": [{{"date":"YYYY-MM-DD","title":"事件标题","description":"事件描述"}}],
  "事实分析": "基于文件内容的事实梳理与关键信息提取，500-800字",
  "法律分析": "引用具体法律条文并分析适用逻辑，500-800字",
  "定争分析": "归纳案件争议焦点并分析各方立场，400-600字",
  "司法推理": "基于事实和法律的裁判逻辑推演，300-500字",
  "参考判例": "如文件中引用了判例则列出，无则写空字符串",
  "胜诉率评估": 45-95之间的整数，基于案件事实和法律依据综合评估
}}

必须基于文件真实内容，不得编造。信息不足时写明"文件信息不足，建议补充相关材料"。JSON必须合法，对象键名必须与示例完全一致。
胜诉率评估必须是整数，不带引号。"""

class CaseLLMAnalyzer:
    def __init__(self, llm_service):
        self.api_key = llm_service.settings.llm_api_key
        self.api_base = llm_service.settings.llm_base_url.rstrip('/')
        self.model = llm_service.model
        self.temperature = llm_service.temperature
        self.max_tokens = 4096
        self.timeout = 120

    async def analyze(self, title, case_type, court_level, description, file_contents):
        prompt = ANALYSIS_PROMPT.format(
            title=title, case_type=case_type or "未指定",
            court_level=court_level or "未指定",
            description=description or "无",
            file_contents=file_contents or "无上传文件"
        )
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.api_base}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={"model": self.model, "messages": [
                        {"role": "system", "content": "你是一个专业的法律分析AI，只输出合法的JSON，不要输出Markdown代码块。"},
                        {"role": "user", "content": prompt}
                    ], "temperature": self.temperature, "max_tokens": self.max_tokens}
                )
                if resp.status_code != 200:
                    logger.error(f"LLM API error: {resp.status_code} {resp.text[:300]}")
                    return None
                data = resp.json()
                raw = data["choices"][0]["message"]["content"]
                # 清理可能的 Markdown 代码块包裹
                raw = raw.strip()
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[-1]
                    if raw.endswith("```"):
                        raw = raw[:-3]
                    raw = raw.strip()
                return raw
        except Exception as e:
            logger.error(f"LLM调用异常: {e}")
            return None
