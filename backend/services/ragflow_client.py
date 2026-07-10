"""
AI法律助手 v1.0 — RAGFlow 客户端
使用 RAGFlow 官方 Python SDK 进行检索和文档管理
"""
import logging
import asyncio
import re
from typing import List, Optional

import httpx
from ragflow_sdk import RAGFlow
from config import Settings

logger = logging.getLogger(__name__)


class RAGFlowClient:
    """
    RAGFlow 客户端
    负责与 RAGFlow 检索服务通信，获取法律条文检索结果
    """

    def __init__(self, settings: Settings):
        """
        初始化 RAGFlow 客户端

        Args:
            settings: 应用配置实例
        """
        self.base_url = settings.ragflow_base_url.rstrip("/")
        self.api_key = settings.ragflow_api_key
        self.default_dataset_id = settings.ragflow_dataset_id
        self.default_top_k = settings.ragflow_top_k
        self.similarity_threshold = settings.ragflow_similarity_threshold
        self.timeout = settings.ragflow_timeout

        # 初始化 RAGFlow SDK 实例
        self._rag: Optional[RAGFlow] = None
        self._doc_name_cache: dict = {}
        if self.api_key and self.base_url:
            try:
                self._rag = RAGFlow(
                    api_key=self.api_key,
                    base_url=self.base_url,
                )
                logger.info(f"RAGFlow SDK 初始化成功: {self.base_url}")
            except Exception as e:
                logger.warning(f"RAGFlow SDK 初始化失败: {e}")

    def _get_rag(self) -> Optional[RAGFlow]:
        """获取 SDK 实例"""
        return self._rag

    async def _ensure_doc_names(self, dataset_id: str):
        """确保文档名缓存已加载（分页获取全部文档）"""
        if self._doc_name_cache:
            return
        rag = self._get_rag()
        if not rag:
            return
        try:
            datasets = await asyncio.to_thread(rag.list_datasets)
            for ds in datasets:
                if ds.id == dataset_id:
                    # 分页获取全部文档名
                    page = 1
                    while True:
                        docs = await asyncio.to_thread(
                            ds.list_documents, page=page, page_size=50
                        )
                        if not docs:
                            break
                        for d in docs:
                            name = d.name or ""
                            if '/' in name:
                                name = name.split('/')[-1]
                            if name.endswith('.docx'):
                                name = name[:-5]
                            # 去掉日期后缀 _YYYYMMDD
                            name = re.sub(r'_\d{8}$', '', name)
                            self._doc_name_cache[d.id] = name
                        if len(docs) < 50:
                            break
                        page += 1
                    logger.info(f"已加载 {len(self._doc_name_cache)} 个文档名")
                    break
        except Exception as e:
            logger.warning(f"加载文档名失败: {e}")

    # ═══════════════════════════════════════
    # 检索
    # ═══════════════════════════════════════

    async def search(
        self,
        query: str,
        dataset_id: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> List[dict]:
        """
        调用 RAGFlow SDK 检索

        Args:
            query: 检索查询文本
            dataset_id: 数据集ID，默认使用配置中的
            top_k: 返回结果数量，默认使用配置中的

        Returns:
            检索结果列表，每项包含:
                - law_name: 法律名称
                - article_num: 条款编号
                - law_text: 法条原文
                - source: 法律来源
                - chunk_id: 文档块ID
                - relevance: 相关度分数
            如果 RAGFlow 不可用，返回空列表
        """
        ds_id = dataset_id or self.default_dataset_id
        k = top_k or self.default_top_k
        rag = self._get_rag()

        if not rag:
            logger.warning("RAGFlow SDK 未初始化，跳过检索")
            return []

        try:
            # 确保文档名已加载
            await self._ensure_doc_names(ds_id)

            # RAGFlow SDK 的 retrieve 是同步方法，在线程池中执行
            results = await asyncio.to_thread(
                rag.retrieve,
                question=query,
                dataset_ids=[ds_id],
                document_ids=[],
                top_k=k,
            )

            # 标准化结果格式
            parsed = []
            for chunk in results:
                similarity = float(getattr(chunk, "similarity", 0))

                if similarity < self.similarity_threshold:
                    continue

                doc_name = getattr(chunk, "document_name", "") or ""
                doc_id = getattr(chunk, "document_id", "") or ""
                law_name = self._doc_name_cache.get(doc_id, doc_name) or "未知法律"

                parsed.append({
                    "law_name": law_name,
                    "article_num": "",
                    "law_text": getattr(chunk, "content", "") or "",
                    "source": law_name,
                    "chunk_id": str(getattr(chunk, "id", "")),
                    "relevance": similarity,
                })

            # 按相关度降序排序，取 top_k
            parsed.sort(key=lambda x: x["relevance"], reverse=True)
            parsed = parsed[:k]

            logger.info(
                f"RAGFlow 检索成功: query='{query[:50]}...', "
                f"返回 {len(parsed)} 条结果"
            )
            return parsed

        except Exception as e:
            logger.error(f"RAGFlow 检索异常: {type(e).__name__}: {e}")
            return []

    # ═══════════════════════════════════════
    # 数据集管理
    # ═══════════════════════════════════════

    async def get_datasets(self) -> List[dict]:
        """
        获取所有数据集列表

        Returns:
            数据集列表
        """
        rag = self._get_rag()
        if not rag:
            return []

        try:
            datasets = await asyncio.to_thread(rag.list_datasets)
            return [{"id": ds.id, "name": ds.name} for ds in datasets]
        except Exception as e:
            logger.error(f"获取数据集异常: {e}")
            return []

    # ═══════════════════════════════════════
    # 文档列表
    # ═══════════════════════════════════════

    async def list_documents(self, dataset_id: Optional[str] = None) -> List[dict]:
        """
        获取数据集中的文档列表（分页获取全部）

        Args:
            dataset_id: 数据集ID，默认使用配置中的

        Returns:
            文档列表，每项包含: id, name, chunks, tokens, status, create_date
        """
        ds_id = dataset_id or self.default_dataset_id
        rag = self._get_rag()
        if not rag:
            return []

        try:
            datasets = rag.list_datasets()
            target = None
            for d in datasets:
                if d.id == ds_id:
                    target = d
                    break

            if not target:
                logger.warning(f"未找到数据集: {ds_id}")
                return []

            # 分页获取全部文档
            all_docs = []
            page = 1
            while True:
                docs = target.list_documents(page=page, page_size=50)
                if not docs:
                    break
                all_docs.extend(docs)
                if len(docs) < 50:
                    break
                page += 1

            result = []
            for doc in all_docs:
                # 从文件路径提取法律名称
                name = doc.name or ""
                if "/" in name:
                    name = name.split("/")[-1]
                # 去掉 .docx 后缀
                if name.endswith(".docx"):
                    name = name[:-5]
                # 去掉日期后缀 _YYYYMMDD
                name = re.sub(r'_\d{8}$', '', name)

                # 尝试解析名称中的日期
                year = ""
                date_match = re.search(r"_(\d{8})", doc.name)
                if date_match:
                    d = date_match.group(1)
                    year = f"{d[:4]}年{d[4:6]}月{d[6:8]}日"

                # 确定分类
                name_lower = name.lower()
                if "宪法" in name or "基本法" in name:
                    category = "constitution"
                elif "民" in name_lower and ("法" in name or "典" in name) and "刑法" not in name:
                    category = "civil"
                elif "刑" in name:
                    category = "criminal"
                elif "劳动" in name or "劳动合同" in name or "就业" in name:
                    category = "labor"
                elif "婚姻" in name or "家庭" in name or "继承" in name or "收养" in name:
                    category = "marriage"
                elif "交通" in name or "道路" in name or "铁路" in name or "航空" in name or "轨道" in name:
                    category = "traffic"
                elif "消费" in name or "食品" in name or "产品" in name:
                    category = "consumer"
                elif "房" in name or "建筑" in name or "物业" in name:
                    category = "housing"
                else:
                    category = "other"

                result.append({
                    "id": str(getattr(doc, "id", "")),
                    "name": name,
                    "category": category,
                    "year": year,
                    "chunk_count": getattr(doc, "chunk_count", 0),
                    "token_count": getattr(doc, "token_count", 0),
                    "status": str(getattr(doc, "status", "0")),
                })

            logger.info(f"获取文档列表成功: 共 {len(result)} 个文档")
            return result

        except Exception as e:
            logger.error(f"获取文档列表异常: {e}")
            return []

    # ═══════════════════════════════════════
    # 文档详情
    # ═══════════════════════════════════════

    async def get_document_chunks(self, document_id: str, dataset_id: Optional[str] = None) -> List[dict]:
        """
        获取指定文档的全部 chunk 块

        Args:
            document_id: 文档ID
            dataset_id: 数据集ID

        Returns:
            chunk 列表
        """
        ds_id = dataset_id or self.default_dataset_id
        url = f"{self.base_url}/api/v1/datasets/{ds_id}/documents/{document_id}/chunks"

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                all_chunks = []
                page = 1
                while True:
                    resp = await client.get(f"{url}?page={page}&page_size=50", headers=headers)
                    if resp.status_code != 200:
                        logger.warning(f"获取文档块失败: {resp.status_code}")
                        break

                    data = resp.json()
                    if isinstance(data, dict):
                        chunks = data.get("data", {}).get("chunks", []) if isinstance(data.get("data"), dict) else data.get("data", [])
                    else:
                        chunks = []

                    if not chunks:
                        break

                    for chunk in chunks:
                        if isinstance(chunk, dict):
                            all_chunks.append({
                                "id": str(chunk.get("id", "")),
                                "content": chunk.get("content", "") or chunk.get("content_with_weight", ""),
                            })

                    if len(chunks) < 50:
                        break
                    page += 1

                logger.info(f"获取文档块成功: doc={document_id}, 共 {len(all_chunks)} 块")
                return all_chunks

        except Exception as e:
            logger.error(f"获取文档块异常: {e}")
            return []

    # ═══════════════════════════════════════
    # 文档上传
    # ═══════════════════════════════════════

    async def upload_document(self, file_path: str, dataset_id: str) -> dict:
        """
        上传文档到指定数据集

        Args:
            file_path: 要上传的文件路径
            dataset_id: 目标数据集ID

        Returns:
            上传结果，包含文档ID等信息
        """
        url = f"{self.base_url}/api/v1/datasets/{dataset_id}/documents"
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                with open(file_path, "rb") as f:
                    files = {"file": (file_path.split("/")[-1], f)}
                    response = await client.post(
                        url, headers=headers, files=files
                    )

                if response.status_code not in (200, 201):
                    logger.error(
                        f"上传文档失败: status={response.status_code}, "
                        f"body={response.text[:200]}"
                    )
                    return {"error": response.text}

                data = response.json()
                logger.info(f"文档上传成功: {file_path} -> dataset {dataset_id}")
                return data

        except FileNotFoundError:
            logger.error(f"上传文档失败: 文件不存在 {file_path}")
            return {"error": f"文件不存在: {file_path}"}
        except Exception as e:
            logger.error(f"上传文档异常: {e}")
            return {"error": str(e)}
