"""
AI法律助手 v1.0 — RAGFlow HTTP API 客户端
通过 HTTP 调用 RAGFlow 检索 API 获取相关法条
"""
import logging
from typing import List, Optional

import httpx
from config import Settings

logger = logging.getLogger(__name__)


class RAGFlowClient:
    """
    RAGFlow HTTP API 客户端
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
        调用 RAGFlow 检索 API

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
        url = f"{self.base_url}/api/v1/retrieval"

        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "question": query,
            "dataset_id": ds_id,
            "top_k": k,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)

                if response.status_code != 200:
                    logger.warning(
                        f"RAGFlow 检索返回非200状态码: {response.status_code}, "
                        f"body: {response.text[:200]}"
                    )
                    return []

                data = response.json()

                # 解析 RAGFlow 返回的检索结果
                results = self._parse_search_results(data)

                logger.info(
                    f"RAGFlow 检索成功: query='{query[:50]}...', "
                    f"返回 {len(results)} 条结果"
                )
                return results

        except httpx.TimeoutException:
            logger.warning(f"RAGFlow 检索超时 ({self.timeout}s): query='{query[:50]}...'")
            return []
        except httpx.ConnectError:
            logger.warning(f"RAGFlow 连接失败: {self.base_url}")
            return []
        except Exception as e:
            logger.error(f"RAGFlow 检索异常: {type(e).__name__}: {e}")
            return []

    def _parse_search_results(self, data: dict) -> List[dict]:
        """
        解析 RAGFlow 返回的检索结果

        Args:
            data: RAGFlow API 返回的 JSON 数据

        Returns:
            标准化后的检索结果列表
        """
        results = []

        # RAGFlow 返回格式: {"data": {"chunks": [...]}}
        # 同时兼容 {"data": [...]} 格式
        records = []

        if isinstance(data, dict):
            inner = data.get("data", data)
            if isinstance(inner, dict):
                records = inner.get("chunks", [])
            elif isinstance(inner, list):
                records = inner

        if not isinstance(records, list):
            return results

        for chunk in records:
            if not isinstance(chunk, dict):
                continue

            # 提取关键元数据
            law_name = (
                chunk.get("law_name")
                or chunk.get("doc_name")
                or chunk.get("title")
                or "未知法律"
            )
            article_num = chunk.get("article_num") or chunk.get("article") or ""
            law_text = chunk.get("content") or chunk.get("law_text") or ""
            source = chunk.get("source") or chunk.get("doc_name") or ""
            chunk_id = chunk.get("chunk_id") or chunk.get("id") or ""
            relevance = float(chunk.get("similarity", chunk.get("relevance", 0)))

            # 过滤相似度低于阈值的结果
            if relevance < self.similarity_threshold:
                continue

            results.append({
                "law_name": law_name,
                "article_num": article_num,
                "law_text": law_text,
                "source": source,
                "chunk_id": str(chunk_id),
                "relevance": relevance,
            })

        # 按相关度降序排序
        results.sort(key=lambda x: x["relevance"], reverse=True)

        return results

    # ═══════════════════════════════════════
    # 数据集管理
    # ═══════════════════════════════════════

    async def get_datasets(self) -> List[dict]:
        """
        获取所有数据集列表

        Returns:
            数据集列表
        """
        url = f"{self.base_url}/api/v1/datasets"
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)

                if response.status_code != 200:
                    logger.warning(f"获取数据集失败: {response.status_code}")
                    return []

                data = response.json()
                datasets = data.get("data", []) if isinstance(data, dict) else []
                return datasets if isinstance(datasets, list) else []

        except Exception as e:
            logger.error(f"获取数据集异常: {e}")
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
