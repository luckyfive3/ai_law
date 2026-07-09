"""
AI法律助手 v1.0 — 知识库服务
法律知识检索、分类和降级搜索
"""
import logging
from typing import List, Optional

from services.ragflow_client import RAGFlowClient

logger = logging.getLogger(__name__)


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
            {"id": 1, "name": "婚姻家庭"},
            {"id": 2, "name": "劳动纠纷"},
            {"id": 3, "name": "合同纠纷"},
            {"id": 4, "name": "交通事故"},
            {"id": 5, "name": "房产纠纷"},
            {"id": 6, "name": "消费维权"},
            {"id": 7, "name": "刑事辩护"},
            {"id": 8, "name": "公司经营"},
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

        return {
            "items": items,
            "count": total,
        }

    # ═══════════════════════════════════════
    # 法条详情
    # ═══════════════════════════════════════

    async def get_law_detail(self, law_id: str) -> dict:
        """
        获取法条详情

        Args:
            law_id: 法条标识

        Returns:
            法条详情字典:
                - id: 法条ID
                - name: 法律名称
                - articles: 条款列表 [{num, content}]

        Raises:
            ValueError: 法条不存在
        """
        # 通过 RAGFlow 检索获取法条详情
        try:
            results = await self.ragflow_client.search(
                query=law_id,
                top_k=1,
            )
        except Exception:
            results = []

        if not results:
            # 尝试降级搜索
            fallback = self.fallback_search(law_id)
            if fallback:
                item = fallback[0]
                return {
                    "id": 1,
                    "name": item.get("law_name", ""),
                    "articles": [
                        {
                            "num": item.get("article_num", ""),
                            "content": item.get("law_text", ""),
                        }
                    ],
                }
            raise ValueError("法条不存在")

        first = results[0]
        return {
            "id": 1,
            "name": first.get("law_name", ""),
            "articles": [
                {
                    "num": first.get("article_num", ""),
                    "content": first.get("law_text", ""),
                }
            ],
        }

    # ═══════════════════════════════════════
    # 降级搜索（内置法律数据库）
    # ═══════════════════════════════════════

    def fallback_search(self, keyword: str) -> list:
        """
        RAGFlow 不可用时的降级搜索
        使用内置的8部中国法律作为备用知识库

        Args:
            keyword: 搜索关键词

        Returns:
            匹配的法律列表
        """
        builtin_laws = [
            {
                "law_name": "中华人民共和国宪法",
                "article_num": "",
                "law_text": "国家根本法，规定国家根本制度和根本任务",
                "source": "全国人民代表大会",
                "relevance": 1.0,
            },
            {
                "law_name": "中华人民共和国民法典",
                "article_num": "",
                "law_text": "调整平等主体之间的人身关系和财产关系",
                "source": "全国人民代表大会",
                "relevance": 0.9,
            },
            {
                "law_name": "中华人民共和国刑法",
                "article_num": "",
                "law_text": "规定犯罪、刑事责任和刑罚的法律",
                "source": "全国人民代表大会",
                "relevance": 0.9,
            },
            {
                "law_name": "中华人民共和国劳动法",
                "article_num": "",
                "law_text": "调整劳动关系及与劳动关系密切联系的其他社会关系",
                "source": "全国人民代表大会常务委员会",
                "relevance": 0.8,
            },
            {
                "law_name": "中华人民共和国劳动合同法",
                "article_num": "",
                "law_text": "规范劳动合同的订立、履行、变更、解除和终止",
                "source": "全国人民代表大会常务委员会",
                "relevance": 0.8,
            },
            {
                "law_name": "中华人民共和国道路交通安全法",
                "article_num": "",
                "law_text": "维护道路交通秩序，预防和减少交通事故",
                "source": "全国人民代表大会常务委员会",
                "relevance": 0.7,
            },
            {
                "law_name": "中华人民共和国消费者权益保护法",
                "article_num": "",
                "law_text": "保护消费者合法权益，维护社会经济秩序",
                "source": "全国人民代表大会常务委员会",
                "relevance": 0.7,
            },
            {
                "law_name": "中华人民共和国反家庭暴力法",
                "article_num": "",
                "law_text": "预防和制止家庭暴力，保护家庭成员的合法权益",
                "source": "全国人民代表大会常务委员会",
                "relevance": 0.7,
            },
        ]

        # 关键词匹配
        if not keyword:
            return builtin_laws

        matched = []
        for law in builtin_laws:
            if (
                keyword in law["law_name"]
                or keyword in law["law_text"]
                or keyword in law.get("source", "")
            ):
                matched.append(law)

        # 如果没有任何匹配的，返回全部
        if not matched:
            return builtin_laws

        return matched
