"""
AI法律助手 v1.0 — 知识库服务
"""
import logging, json, os, re
from typing import List, Optional
from services.ragflow_client import RAGFlowClient

logger = logging.getLogger(__name__)
LAWS_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "frontend", "static", "js", "laws_data.js")

ALL_DATASET_IDS = [
    "e2d5546a7c5011f19855b7acec531fcb",
    "350004b87cdf11f199b8b7e53ff0faa6",
    "53fdb5127ce011f199b8b7e53ff0faa6",
    "7e7270a87ce011f199b8b7e53ff0faa6",
    "9734a8187ce011f199b8b7e53ff0faa6",
    "be93c2947ce111f199b8b7e53ff0faa6",
    "fc5695a27ce111f199b8b7e53ff0faa6",
]

MODULE_DATASET_MAP = {
    "marriage": "350004b87cdf11f199b8b7e53ff0faa6",
    "labor": "53fdb5127ce011f199b8b7e53ff0faa6",
    "contract": "7e7270a87ce011f199b8b7e53ff0faa6",
    "traffic": "9734a8187ce011f199b8b7e53ff0faa6",
    "housing": "be93c2947ce111f199b8b7e53ff0faa6",
    "consumer": "fc5695a27ce111f199b8b7e53ff0faa6",
}

class KnowledgeService:
    def __init__(self, ragflow_client: RAGFlowClient):
        self.ragflow_client = ragflow_client
        self._laws_data = None
        self._search_cache = {}
        self._cache_ttl = 300

    def _load_laws_data(self) -> list:
        if self._laws_data is not None: return self._laws_data
        try:
            fp = os.path.normpath(LAWS_DATA_PATH)
            if os.path.exists(fp):
                with open(fp, 'r', encoding='utf-8') as f:
                    raw = f.read()
                m = re.search(r'window\.LAWS_DATA\s*=\s*(\[[\s\S]*\])\s*;?\s*$', raw)
                if m:
                    self._laws_data = json.loads(m.group(1))
                    logger.info(f"加载法律数据成功，共 {len(self._laws_data)} 部")
                    return self._laws_data
        except Exception as e:
            logger.warning(f"加载法律数据失败: {e}")
        self._laws_data = []
        return self._laws_data

    def _get_builtin_laws(self) -> list:
        laws = self._load_laws_data()
        return laws or [
            {"id": 1, "name": "中华人民共和国宪法", "summary": "国家根本法", "year": "1982年", "articleCount": 134},
            {"id": 2, "name": "中华人民共和国民法典", "summary": "民事基本法", "year": "2020年", "articleCount": 1109},
            {"id": 3, "name": "中华人民共和国刑法", "summary": "刑事基本法", "year": "2020年修正", "articleCount": 561},
        ]

    async def get_categories(self) -> list:
        return [
            {"name": "全部", "category": "all"},
            {"name": "宪法", "category": "constitution"},
            {"name": "民法", "category": "civil"},
            {"name": "刑法", "category": "criminal"},
            {"name": "劳动法", "category": "labor"},
            {"name": "婚姻家庭", "category": "marriage"},
            {"name": "交通法", "category": "traffic"},
            {"name": "消费者权益", "category": "consumer"},
            {"name": "房产法", "category": "housing"},
        ]

    async def get_modules(self) -> list:
        return [
            {"name": "综合", "module": "all"},
            {"name": "婚姻家庭", "module": "marriage"},
            {"name": "劳动纠纷", "module": "labor"},
            {"name": "合同纠纷", "module": "contract"},
            {"name": "交通事故", "module": "traffic"},
            {"name": "房产纠纷", "module": "housing"},
            {"name": "消费维权", "module": "consumer"},
        ]

    async def get_ragflow_documents(self, filter_type="category", filter_value="all", page=1, page_size=100) -> dict:
        try:
            if filter_type == "module" and filter_value != "all":
                ds_id = MODULE_DATASET_MAP.get(filter_value)
                if not ds_id: return {"items": [], "total": 0, "page": page, "page_size": page_size}
                return await self.ragflow_client.list_documents(dataset_id=ds_id, page=page, page_size=page_size)
            all_items = await self.ragflow_client.list_all_datasets_documents()
            if filter_value != "all":
                all_items = [d for d in all_items if d.get("category") == filter_value]
            total = len(all_items)
            start = (page - 1) * page_size
            return {"items": all_items[start:start + page_size], "total": total, "page": page, "page_size": page_size}
        except Exception as e:
            logger.error(f"获取文档列表失败: {e}")
            return {"items": [], "total": 0, "page": page, "page_size": page_size}

    async def get_law_detail(self, law_id: str) -> dict:
        # 先从所有数据集中找到该文档的名称和所属数据集
        found_name = ""
        target_ds_id = ""
        try:
            all_docs = await self.ragflow_client.list_all_datasets_documents()
            for d in all_docs:
                if d.get("id") == law_id:
                    found_name = d.get("name", "")
                    break
        except Exception:
            pass

        # 用 RAGFlow SDK 的 retrieve 来间接查 chunks（更可靠）
        chunks = []
        if found_name:
            # 在所有数据集中尝试获取 chunks
            for ds_id in ALL_DATASET_IDS:
                try:
                    c = await self.ragflow_client.get_document_chunks(law_id, ds_id)
                    if c:
                        chunks = c
                        target_ds_id = ds_id
                        break
                except Exception:
                    continue

        if not chunks:
            laws_data = self._load_laws_data()
            if laws_data:
                try:
                    lid = int(law_id)
                    law = next((l for l in laws_data if l.get("id") == lid), None)
                    if law:
                        return {"id": law.get("id"), "name": law.get("name", ""), "year": law.get("year", ""),
                                "chunks": [{"content": a.get("content", "")} for a in law.get("articles", [])]}
                except (ValueError, TypeError):
                    pass
            if not found_name:
                raise ValueError("文档不存在或未解析")

        return {"id": law_id, "name": found_name or "未知法律", "year": "", "chunks": chunks}

    async def search(self, keyword: str, page: int = 1, page_size: int = 10) -> dict:
        import time
        ck = f"{keyword}:{page}:{page_size}"
        if ck in self._search_cache:
            if time.time() - self._search_cache[ck]["ts"] < self._cache_ttl:
                return self._search_cache[ck]["data"]
        try:
            results = await self.ragflow_client.search(query=keyword, top_k=page_size)
        except Exception as e:
            logger.warning(f"RAGFlow 搜索失败: {e}")
            results = []
        if not results:
            results = self.fallback_search(keyword)
        total = len(results)
        items = []
        for i, item in enumerate(results[(page - 1) * page_size: page * page_size], start=(page - 1) * page_size + 1):
            items.append({
                "id": str(i), "name": item.get("law_name", ""), "article_num": item.get("article_num", ""),
                "content": item.get("law_text", ""), "source": item.get("source", ""), "relevance": item.get("relevance", 0),
            })
        result = {"items": items, "count": total}
        self._search_cache[ck] = {"data": result, "ts": time.time()}
        return result

    def fallback_search(self, keyword: str) -> list:
        laws_data = self._load_laws_data()
        if laws_data:
            matched = []
            for law in laws_data:
                name_match = keyword in law.get("name", "")
                mas = [a for a in law.get("articles", []) if keyword in a.get("content", "")]
                for art in mas[:3]:
                    matched.append({"law_name": law.get("name", ""), "article_num": art.get("num", ""),
                                    "law_text": art.get("content", ""), "source": f"共{law.get('articleCount', 0)}条",
                                    "relevance": 1.0 if name_match else 0.8})
                if name_match and not mas:
                    matched.append({"law_name": law.get("name", ""), "article_num": "",
                                    "law_text": law.get("summary", ""), "source": f"共{law.get('articleCount', 0)}条", "relevance": 1.0})
            if matched: return matched
        builtin = self._get_builtin_laws()
        return [{"law_name": l.get("name", ""), "article_num": "", "law_text": l.get("summary", ""),
                 "source": l.get("year", ""), "relevance": 0.9} for l in builtin]
