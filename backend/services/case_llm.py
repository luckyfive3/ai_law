"""案件 LLM 分析器"""
import logging, httpx
logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """[角色]你是一名资深法律分析师。

[案件基本信息]
案件名称：{title} | 类型：{case_type} | 审理阶段：{court_level} | 描述：{description}

[上传文件内容]
{file_contents}

[要求]基于以上信息，严格按以下JSON格式输出（只输出JSON，不要其他文字）：
{{
  "案情摘要": "200-300字",
  "案情时间轴": [{{"date":"YYYY-MM-DD","title":"事件","description":"描述"}}],
  "事实分析": "基于文件内容的事实分析500-800字",
  "法律分析": "法律条文引用与适用逻辑500-800字",
  "定争分析": "争议焦点归纳400-600字",
  "司法推理": "裁判逻辑推演300-500字",
  "参考判例": "文件引用的判例，无则空字符串"
}}
必须基于文件真实内容，不得编造。信息不足时写明"文件信息不足"。JSON必须合法。"""

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
            title=title, case_type=case_type, court_level=court_level,
            description=description or "无", file_contents=file_contents or "无上传文件"
        )
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.api_base}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={"model": self.model, "messages": [
                        {"role": "system", "content": "你是一个法律分析AI，只输出合法JSON。"},
                        {"role": "user", "content": prompt}
                    ], "temperature": self.temperature, "max_tokens": self.max_tokens}
                )
                if resp.status_code != 200:
                    logger.error(f"LLM error: {resp.status_code}")
                    return None
                return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"LLM调用异常: {e}")
            return None
