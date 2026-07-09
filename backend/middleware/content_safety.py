"""
AI法律助手 v1.0 — 内容安全中间件

对用户提交的内容进行敏感词检测，拦截包含违禁关键词的请求。
关键词列表从 blocked_keywords.txt 文件加载。
"""
import os
import json
import logging
from pathlib import Path
from typing import Optional, List
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from config import Settings
from utils import errcode

logger = logging.getLogger(__name__)


class ContentSafety:
    """
    内容安全检查器

    加载敏感词列表，提供内容检测和中间件拦截功能。
    """

    def __init__(self, settings: Settings):
        """
        初始化内容安全检查器，从文件加载屏蔽关键词

        Args:
            settings: 应用配置
        """
        self._settings = settings
        self._blocked_keywords: List[str] = []
        self._enabled = settings.safety_enable
        self._load_keywords()

    def _load_keywords(self) -> None:
        """从 blocked_keywords.txt 加载屏蔽关键词列表"""
        keywords_file = self._settings.safety_keywords_file

        # 支持相对路径和绝对路径
        if not os.path.isabs(keywords_file):
            keywords_file = str(Path(__file__).parent.parent / keywords_file)

        if not os.path.exists(keywords_file):
            logger.warning(f"屏蔽关键词文件不存在: {keywords_file}，内容安全检查将跳过")
            return

        try:
            with open(keywords_file, "r", encoding="utf-8") as f:
                for line in f:
                    keyword = line.strip()
                    # 跳过空行和注释行
                    if keyword and not keyword.startswith("#"):
                        self._blocked_keywords.append(keyword)
            logger.info(
                f"已加载 {len(self._blocked_keywords)} 个屏蔽关键词 "
                f"(来源: {keywords_file})"
            )
        except Exception as e:
            logger.error(f"加载屏蔽关键词文件失败: {e}")

    def check(self, content: str) -> bool:
        """
        检查内容是否安全

        Args:
            content: 待检测的文本内容

        Returns:
            bool: True 表示内容通过安全检查，False 表示包含敏感词
        """
        if not self._enabled:
            return True

        if not self._blocked_keywords:
            return True

        content_lower = content.lower()
        for keyword in self._blocked_keywords:
            if keyword.lower() in content_lower:
                logger.warning(f"内容命中屏蔽关键词: {keyword}")
                return False

        return True

    async def middleware(self, request: Request, call_next):
        """
        FastAPI 中间件函数

        拦截 POST 请求，检查请求体中的文本内容是否包含敏感词。

        Args:
            request: 请求对象
            call_next: 下一个中间件或路由处理函数

        Returns:
            Response: 正常响应或 403 敏感内容拦截响应
        """
        # 仅检查 POST / PUT / PATCH 请求
        if request.method not in ("POST", "PUT", "PATCH"):
            return await call_next(request)

        # 读取请求体并检查
        try:
            body = await request.body()
            if body:
                # 尝试解析 JSON 格式的请求体
                try:
                    data = json.loads(body.decode("utf-8"))
                    # 将请求体中的文本字段连接起来检查
                    text_parts = []
                    for key, value in data.items():
                        if isinstance(value, str):
                            text_parts.append(value)
                    combined_text = " ".join(text_parts)

                    if combined_text and not self.check(combined_text):
                        return JSONResponse(
                            status_code=403,
                            content={
                                "code": errcode.CodeSensitiveContent,
                                "message": errcode.get_message(
                                    errcode.CodeSensitiveContent
                                ),
                            },
                        )
                except (json.JSONDecodeError, UnicodeDecodeError):
                    # 非 JSON 请求体，跳过检查
                    pass
        except Exception as e:
            logger.error(f"内容安全检查异常: {e}")

        return await call_next(request)
