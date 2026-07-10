"""
AI法律助手 v1.0 — 知识库服务
法律知识检索、分类和降级搜索
"""
import logging
import json
import os
import re
from typing import List, Optional

from services.ragflow_client import RAGFlowClient

logger = logging.getLogger(__name__)

# 法律数据文件路径
LAWS_DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "..", "frontend", "static", "js", "laws_data.js"
)


class KnowledgeService:
    """
    知识库服务
    提供法律知识的分类浏览、关键词搜索和法条详情查询
    """

    def __init__(self, ragflow_client: RAGFlowClient):
        """
        初始化知识库服务

        Args:
            ragflow_client: RAGFlow 客户端实例
        """
        self.ragflow_client = ragflow_client
        self._laws_data = None
        self._search_cache = {}
        self._cache_ttl = 300  # 缓存5分钟

    def _load_laws_data(self) -> list:
        """加载法学数据（带缓存）"""
        if self._laws_data is not None:
            return self._laws_data

        try:
            normalized = os.path.normpath(LAWS_DATA_PATH)
            if os.path.exists(normalized):
                with open(normalized, 'r', encoding='utf-8') as f:
                    content = f.read()
                # 提取 JSON（去掉 window.LAWS_DATA = 前缀和末尾分号）
                match = re.search(r'window\.LAWS_DATA\s*=\s*(\[[\s\S]*\])\s*;?\s*$', content)
                if match:
                    self._laws_data = json.loads(match.group(1))
                    logger.info(f"加载法律数据成功，共 {len(self._laws_data)} 部法律")
                    return self._laws_data
        except Exception as e:
            logger.warning(f"加载法律数据失败: {e}")

        self._laws_data = []
        return self._laws_data

    def _get_builtin_laws(self) -> list:
        """获取内置法律列表（用于搜索时的摘要匹配）"""
        laws = self._load_laws_data()
        if laws:
            return laws

        # 如果数据文件不可用，使用内置摘要
        return [
            {"id": 1, "name": "中华人民共和国宪法", "summary": "国家根本法", "year": "1982年", "articleCount": 134},
            {"id": 2, "name": "中华人民共和国民法典", "summary": "调整平等主体之间的人身关系和财产关系", "year": "2020年", "articleCount": 1109},
            {"id": 3, "name": "中华人民共和国刑法", "summary": "规定犯罪、刑事责任和刑罚的法律", "year": "2020年修正", "articleCount": 561},
            {"id": 4, "name": "中华人民共和国劳动法", "summary": "调整劳动关系", "year": "2018年修正", "articleCount": 109},
            {"id": 5, "name": "中华人民共和国劳动合同法", "summary": "规范劳动合同", "year": "2012年修正", "articleCount": 126},
            {"id": 6, "name": "中华人民共和国消费者权益保护法", "summary": "保护消费者合法权益", "year": "2013年修正", "articleCount": 65},
            {"id": 7, "name": "中华人民共和国反家庭暴力法", "summary": "预防和制止家庭暴力", "year": "2015年", "articleCount": 39},
            {"id": 8, "name": "中华人民共和国未成年人保护法", "summary": "保护未成年人", "year": "2024年修正", "articleCount": 147},
            {"id": 9, "name": "中华人民共和国监察法", "summary": "国家监察体制改革", "year": "2024年修正", "articleCount": 81},
            {"id": 10, "name": "中华人民共和国商标法", "summary": "保护商标专用权", "year": "2026年修正", "articleCount": 129},
            {"id": 11, "name": "中华人民共和国城市房地产管理法", "summary": "管理城市房地产", "year": "2019年修正", "articleCount": 82},
            {"id": 12, "name": "中华人民共和国国防交通法", "summary": "国防交通建设", "year": "2016年", "articleCount": 60},
        ]

    # ═══════════════════════════════════════
    # RAGFlow 文档列表
    # ═══════════════════════════════════════

    async def get_ragflow_documents(self) -> list:
        """
        从 RAGFlow 获取全部文档列表

        Returns:
            文档列表，每项包含: id, name, category, year, chunks, tokens
        """
        try:
            return await self.ragflow_client.list_documents()
        except Exception as e:
            logger.error(f"获取 RAGFlow 文档列表失败: {e}")
            return []

    # ═══════════════════════════════════════
    # 法律分类
    # ═══════════════════════════════════════

    async def get_categories(self) -> list:
        """
        获取法律分类列表

        Returns:
            法律分类列表，每项含 id 和 name
        """
        categories = [
            {"id": 1, "name": "宪法"},
            {"id": 2, "name": "民法"},
            {"id": 3, "name": "刑法"},
            {"id": 4, "name": "劳动法"},
            {"id": 5, "name": "婚姻家庭"},
            {"id": 6, "name": "交通法"},
            {"id": 7, "name": "消费者权益"},
            {"id": 8, "name": "房产法"},
        ]
        return categories

    # ═══════════════════════════════════════
    # 关键词搜索
    # ═══════════════════════════════════════

    async def search(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 10,
    ) -> dict:
        """
        关键词搜索法条

        Args:
            keyword: 搜索关键词
            page: 页码（从1开始）
            page_size: 每页条数

        Returns:
            搜索结果字典:
                - items: 搜索结果列表
                - count: 总数
        """
        import time
        cache_key = f"{keyword}:{page}:{page_size}"
        if cache_key in self._search_cache:
            entry = self._search_cache[cache_key]
            if time.time() - entry["ts"] < self._cache_ttl:
                return entry["data"]

        # 调用 RAGFlow 检索
        try:
            results = await self.ragflow_client.search(
                query=keyword,
                top_k=page_size,
            )
        except Exception as e:
            logger.warning(f"知识库搜索 RAGFlow 调用失败: {e}")
            results = []

        # RAGFlow 不可用时使用降级搜索
        if not results:
            logger.info(f"RAGFlow 无结果，启用降级搜索: keyword='{keyword}'")
            results = self.fallback_search(keyword)

        # 分页处理
        total = len(results)
        start = (page - 1) * page_size
        end = start + page_size
        paged_items = results[start:end]

        # 格式化输出项
        items = []
        for i, item in enumerate(paged_items, start=start + 1):
            items.append({
                "id": str(i),
                "name": item.get("law_name", ""),
                "article_num": item.get("article_num", ""),
                "content": item.get("law_text", ""),
                "source": item.get("source", ""),
                "relevance": item.get("relevance", 0),
            })

        result = {
            "items": items,
            "count": total,
        }
        # 写入缓存
        self._search_cache[cache_key] = {"data": result, "ts": time.time()}
        return result

    # ═══════════════════════════════════════
    # 法条详情
    # ═══════════════════════════════════════

    async def get_law_detail(self, law_id: str) -> dict:
        """
        获取法条详情（从 RAGFlow 获取文档块）

        Args:
            law_id: 法条/文档 ID（RAGFlow document_id）

        Returns:
            法条详情字典:
                - id: 文档ID
                - name: 文档名称
                - chunks: chunk 列表 [{content}]

        Raises:
            ValueError: 文档不存在
        """
        # 从 RAGFlow 获取文档块
        try:
            chunks = await self.ragflow_client.get_document_chunks(law_id)
        except Exception as e:
            logger.warning(f"RAGFlow 获取文档块失败: {e}")
            chunks = []

        if not chunks:
            # 尝试从本地数据查找
            laws_data = self._load_laws_data()
            if laws_data:
                try:
                    lid = int(law_id)
                    law = next((l for l in laws_data if l.get("id") == lid), None)
                    if law:
                        return {
                            "id": law.get("id"),
                            "name": law.get("name", ""),
                            "year": law.get("year", ""),
                            "chunks": [{"content": a.get("content", "")} for a in law.get("articles", [])],
                        }
                except (ValueError, TypeError):
                    pass
            raise ValueError("文档不存在或未解析")

        # 从文档列表中查找文档名称
        doc_name = "未知法律"
        try:
            docs = await self.ragflow_client.list_documents()
            for d in docs:
                if d.get("id") == law_id:
                    doc_name = d.get("name", doc_name)
                    break
        except Exception:
            pass

        return {
            "id": law_id,
            "name": doc_name,
            "year": "",
            "chunks": chunks,
        }

    # ═══════════════════════════════════════
    # 降级搜索（内置法律数据库）
    # ═══════════════════════════════════════

    def fallback_search(self, keyword: str) -> list:
        """
        RAGFlow 不可用时的降级搜索
        使用法律数据文件中的法律作为备用知识库

        Args:
            keyword: 搜索关键词

        Returns:
            匹配的法律列表
        """
        laws_data = self._load_laws_data()
        if laws_data:
            # 使用真实法律数据
            matched = []
            for law in laws_data:
                # 在法律名称和所有法条内容中搜索
                name_match = keyword in law.get("name", "")
                article_match = False
                matched_articles = []
                
                for article in law.get("articles", []):
                    if keyword in article.get("content", ""):
                        article_match = True
                        matched_articles.append(article)
                
                if name_match or article_match:
                    for art in matched_articles[:3]:  # 每个法律最多返回3条匹配法条
                        matched.append({
                            "law_name": law.get("name", ""),
                            "article_num": art.get("num", ""),
                            "law_text": art.get("content", ""),
                            "source": f"共{law.get('articleCount', 0)}条",
                            "relevance": 1.0 if name_match else 0.8,
                        })
                    
                    # 如果名称匹配但没有法条匹配，返回摘要
                    if name_match and not matched_articles:
                        matched.append({
                            "law_name": law.get("name", ""),
                            "article_num": "",
                            "law_text": law.get("summary", ""),
                            "source": f"共{law.get('articleCount', 0)}条",
                            "relevance": 1.0,
                        })

            if matched:
                return matched

        # 如果数据文件不可用，使用内置摘要数据
        builtin = self._get_builtin_laws()
        matched = []
        for law in builtin:
            if (
                keyword in law.get("name", "")
                or keyword in law.get("summary", "")
            ):
                matched.append({
                    "law_name": law.get("name", ""),
                    "article_num": "",
                    "law_text": law.get("summary", ""),
                    "source": law.get("year", ""),
                    "relevance": 0.9,
                })

        if not matched:
            # 返回所有法律摘要
            for law in builtin:
                matched.append({
                    "law_name": law.get("name", ""),
                    "article_num": "",
                    "law_text": law.get("summary", ""),
                    "source": law.get("year", ""),
                    "relevance": 0.6,
                })

        return matched
