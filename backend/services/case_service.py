"""
AI法律助手 v1.0 — 案件管理服务
管理案件、证据、文档的全生命周期，提供 AI 分析、问答、证据审核等 Mock 功能
"""

import logging
import os
from datetime import datetime, timezone
from typing import List, Tuple, Optional, Dict, Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from services.case_llm import CaseLLMAnalyzer
from services.case_file_parser import parse_file
from schemas.case_schemas import (
    CaseCreateRequest,
    CaseUpdateRequest,
    CaseQARequest,
    EvidenceCreateRequest,
    EvidenceUpdateRequest,
    DocumentCreateRequest,
)

logger = logging.getLogger(__name__)


class CaseService:
    """
    案件管理服务
    管理案件、证据、文档的全生命周期操作
    提供 Mock AI 分析、问答、证据审核等功能
    """

    def __init__(self, db: AsyncIOMotorDatabase, llm_service=None):
        """
        初始化案件管理服务

        Args:
            db: MongoDB 数据库实例
            llm_service: LLM 服务实例（可选，当前版本使用 Mock 数据）
        """
        self.db = db
        self.llm_service = llm_service
        self.llm = CaseLLMAnalyzer(llm_service) if llm_service else None

    # ═══════════════════════════════════════
    # 辅助方法
    # ═══════════════════════════════════════

    def _now(self) -> str:
        """获取当前 UTC 时间字符串"""
        return datetime.now(timezone.utc).isoformat()

    def _safe_oid(self, id_str: str) -> ObjectId:
        """安全地将字符串转换为 ObjectId"""
        try:
            return ObjectId(id_str)
        except Exception:
            return None

    def _doc_to_case_info(self, doc: Dict) -> Dict:
        """将 MongoDB 文档转换为 CaseInfo 格式"""
        return {
            "id": str(doc["_id"]),
            "title": doc.get("title", ""),
            "case_type": doc.get("case_type", ""),
            "status": doc.get("status", "待分析"),
            "win_rate": doc.get("win_rate", 0),
            "evidence_uploaded": doc.get("evidence_uploaded", False),
            "court_level": doc.get("court_level", ""),
            "parties": doc.get("parties", []),
            "created_at": doc.get("created_at", ""),
            "updated_at": doc.get("updated_at", ""),
            "tags": doc.get("tags", []),
        }

    def _doc_to_evidence_info(self, doc: Dict) -> Dict:
        """将 MongoDB 文档转换为 EvidenceInfo 格式"""
        return {
            "id": str(doc["_id"]),
            "name": doc.get("name", ""),
            "evidence_type": doc.get("evidence_type", ""),
            "description": doc.get("description", ""),
            "purpose": doc.get("purpose", ""),
            "status": doc.get("status", "待审核"),
            "audit_result": doc.get("audit_result"),
            "audit_reason": doc.get("audit_reason"),
            "created_at": doc.get("created_at", ""),
        }

    def _doc_to_evidence_detail(self, doc: Dict) -> Dict:
        """将 MongoDB 文档转换为 EvidenceDetailInfo 格式"""
        info = self._doc_to_evidence_info(doc)
        info.update({
            "source": doc.get("source", ""),
            "collection_method": doc.get("collection_method", ""),
            "collection_note": doc.get("collection_note", ""),
            "uploader_name": doc.get("uploader_name", ""),
        })
        return info

    def _doc_to_document_info(self, doc: Dict) -> Dict:
        """将 MongoDB 文档转换为 DocumentInfo 格式"""
        return {
            "id": str(doc["_id"]),
            "name": doc.get("name", ""),
            "file_url": doc.get("file_url", ""),
            "doc_type": doc.get("doc_type", ""),
            "uploader": doc.get("uploader", ""),
            "created_at": doc.get("created_at", ""),
        }

    def _doc_to_analysis_info(self, doc: Dict) -> Dict:
        """将 MongoDB 文档转换为 AnalysisInfo 格式"""
        return {
            "id": str(doc["_id"]),
            "analysis_type": doc.get("analysis_type", ""),
            "content": doc.get("content", {}),
            "created_at": doc.get("created_at", ""),
        }

    def _doc_to_qa_info(self, doc: Dict) -> Dict:
        """将 MongoDB 文档转换为 QAInfo 格式"""
        return {
            "id": str(doc["_id"]),
            "question": doc.get("question", ""),
            "answer": doc.get("answer", ""),
            "created_at": doc.get("created_at", ""),
        }

    # ═══════════════════════════════════════
    # 案件 CRUD
    # ═══════════════════════════════════════

    async def list_cases(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        status_filter: str = "",
        keyword: str = "",
    ) -> Tuple[List[Dict], int]:
        """
        获取用户案件列表（分页）

        Args:
            user_id: 用户ID
            page: 页码（从1开始）
            page_size: 每页条数
            status_filter: 状态筛选
            keyword: 关键词搜索

        Returns:
            (案件列表, 总数)
        """
        query: Dict[str, Any] = {
            "user_id": user_id,
            "is_deleted": {"$ne": True},
        }

        if status_filter:
            query["status"] = status_filter

        if keyword:
            escaped = keyword.replace("\\", "\\\\").replace("\"", "\\\"")
            query["$or"] = [
                {"title": {"$regex": escaped, "$options": "i"}},
                {"description": {"$regex": escaped, "$options": "i"}},
            ]

        total = await self.db.cases.count_documents(query)

        skip = (page - 1) * page_size
        cursor = (
            self.db.cases.find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(page_size)
        )

        cases = []
        async for doc in cursor:
            cases.append(self._doc_to_case_info(doc))

        return cases, total

    async def get_case(self, user_id: str, case_id: str) -> Optional[Dict]:
        """
        获取单个案件详情（含分析记录和问答历史）

        Args:
            user_id: 用户ID
            case_id: 案件ID

        Returns:
            案件详情字典，不存在返回 None
        """
        oid = self._safe_oid(case_id)
        if oid is None:
            return None

        case_doc = await self.db.cases.find_one({
            "_id": oid,
            "user_id": user_id,
            "is_deleted": {"$ne": True},
        })

        if not case_doc:
            return None

        case_info = self._doc_to_case_info(case_doc)
        case_info["description"] = case_doc.get("description", "")

        # 加载分析记录
        analyses = []
        analysis_cursor = self.db.case_analyses.find({"case_id": case_id}).sort("created_at", -1)
        async for a_doc in analysis_cursor:
            analyses.append(self._doc_to_analysis_info(a_doc))
        case_info["analyses"] = analyses

        # 加载问答历史
        qa_history = []
        qa_cursor = self.db.case_qa.find({"case_id": case_id}).sort("created_at", -1)
        async for q_doc in qa_cursor:
            qa_history.append(self._doc_to_qa_info(q_doc))
        case_info["qa_history"] = qa_history

        return case_info

    async def create_case(self, user_id: str, data: CaseCreateRequest) -> Dict:
        """
        创建新案件

        Args:
            user_id: 用户ID
            data: 创建请求数据

        Returns:
            创建的案件信息
        """
        now = self._now()
        case_doc = {
            "user_id": user_id,
            "title": data.title,
            "case_type": data.case_type,
            "description": data.description,
            "court_level": data.court_level,
            "parties": [p.model_dump() for p in data.parties],
            "tags": data.tags,
            "status": "待分析",
            "win_rate": 0,
            "evidence_uploaded": False,
            "is_deleted": False,
            "created_at": now,
            "updated_at": now,
        }

        result = await self.db.cases.insert_one(case_doc)
        case_id = str(result.inserted_id)

        logger.info(f"案件创建成功: id={case_id}, user_id={user_id}, title={data.title}")

        case_doc["_id"] = result.inserted_id
        return self._doc_to_case_info(case_doc)

    async def update_case(self, user_id: str, case_id: str, data: CaseUpdateRequest) -> Optional[Dict]:
        """
        更新案件信息

        Args:
            user_id: 用户ID
            case_id: 案件ID
            data: 更新请求数据

        Returns:
            更新后的案件信息，不存在返回 None
        """
        oid = self._safe_oid(case_id)
        if oid is None:
            return None

        update_fields = {"updated_at": self._now()}

        if data.title is not None:
            update_fields["title"] = data.title
        if data.description is not None:
            update_fields["description"] = data.description
        if data.status is not None:
            update_fields["status"] = data.status
        if data.court_level is not None:
            update_fields["court_level"] = data.court_level
        if data.tags is not None:
            update_fields["tags"] = data.tags
        if data.parties is not None:
            update_fields["parties"] = [p.model_dump() for p in data.parties]

        result = await self.db.cases.find_one_and_update(
            {"_id": oid, "user_id": user_id, "is_deleted": {"$ne": True}},
            {"$set": update_fields},
            return_document=True,
        )

        if not result:
            logger.warning(f"案件更新失败: case_id={case_id}, user_id={user_id}")
            return None

        logger.info(f"案件更新成功: case_id={case_id}")
        return self._doc_to_case_info(result)

    async def delete_case(self, user_id: str, case_id: str) -> bool:
        """
        软删除案件

        Args:
            user_id: 用户ID
            case_id: 案件ID

        Returns:
            是否删除成功
        """
        oid = self._safe_oid(case_id)
        if oid is None:
            return False

        result = await self.db.cases.update_one(
            {"_id": oid, "user_id": user_id},
            {"$set": {"is_deleted": True, "updated_at": self._now()}},
        )

        if result.modified_count > 0:
            logger.info(f"案件删除成功: id={case_id}, user_id={user_id}")
            return True

        return False

    # ═══════════════════════════════════════
    # AI 案件分析（Mock）
    # ═══════════════════════════════════════

    async def analyze_case(self, user_id: str, case_id: str) -> Optional[Dict]:
        """AI 案件综合分析 — 读取上传文件，调用 LLM 生成分析报告"""
        case = await self.get_case(user_id, case_id)
        if case is None:
            return None

        # 更新状态为"分析中"
        await self.db.cases.update_one(
            {"_id": self._safe_oid(case_id)},
            {"$set": {"status": "分析中", "updated_at": self._now()}},
        )

        # 读取上传文件内容
        file_contents = ""
        docs_cursor = self.db.case_documents.find(
            {"case_id": case_id, "user_id": user_id, "is_deleted": {"$ne": True}}
        )
        docs = await docs_cursor.to_list(length=50)
        upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
        for doc in docs:
            path = doc.get("file_path", "")
            # Fallback: 从 file_url 构造路径
            if not path:
                file_url = doc.get("file_url", "")
                if file_url:
                    fname = file_url.rsplit("/", 1)[-1]
                    path = os.path.join(upload_dir, fname)
            cat = doc.get("doc_category", "")
            cat_label = cat or "其他文件"
            if path and os.path.exists(path):
                text = parse_file(path)
                file_contents += f"\n=== {cat_label}: {doc.get('name', '')} ===\n{text}\n"

        # 调用 LLM
        content = None
        if self.llm:
            raw = await self.llm.analyze(
                title=case["title"],
                case_type=case["case_type"],
                court_level=case.get("court_level", ""),
                description=case.get("description", ""),
                file_contents=file_contents or "无上传文件",
            )
            if raw:
                import json
                try:
                    content = json.loads(raw)
                except json.JSONDecodeError:
                    # Try to extract JSON from the response
                    import re as _re
                    m = _re.search(r'\{[^{}]*\}', raw, _re.DOTALL)
                    if m:
                        try:
                            content = json.loads(m.group())
                        except:
                            pass
                    if not content:
                        content = {"案情摘要": raw[:500], "事实分析": "", "法律分析": "", "定争分析": "", "司法推理": "", "参考判例": "", "胜诉率评估": 50}

        if not content:
            content = {"案情摘要": "AI分析暂时不可用，请稍后重试", "事实分析": "", "法律分析": "", "定争分析": "", "司法推理": "", "参考判例": "", "胜诉率评估": 50}

        # 提取胜诉率
        win_rate = content.get("胜诉率评估", 50)
        if isinstance(win_rate, str):
            try:
                win_rate = int(win_rate)
            except:
                win_rate = 50

        # 存储分析结果
        now = self._now()
        analysis_doc = {
            "case_id": case_id,
            "user_id": user_id,
            "analysis_type": "case_overview",
            "content": content,
            "created_at": now,
        }
        analysis_result = await self.db.case_analyses.insert_one(analysis_doc)

        # 更新案件状态和胜诉率
        await self.db.cases.update_one(
            {"_id": self._safe_oid(case_id)},
            {"$set": {"status": "已分析", "win_rate": win_rate, "updated_at": now}},
        )

        logger.info(f"案件AI分析完成: case_id={case_id}, win_rate={win_rate}")
        return {
            "id": str(analysis_result.inserted_id),
            "analysis_type": "case_overview",
            "content": content,
            "win_rate": win_rate,
            "created_at": now,
        }

    async def list_documents(
        self,
        user_id: str,
        case_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict], int]:
        """
        获取案件文档列表（分页）

        Args:
            user_id: 用户ID
            case_id: 案件ID
            page: 页码
            page_size: 每页条数

        Returns:
            (文档列表, 总数)
        """
        query = {"case_id": case_id, "is_deleted": {"$ne": True}}

        total = await self.db.case_documents.count_documents(query)

        skip = (page - 1) * page_size
        cursor = (
            self.db.case_documents.find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(page_size)
        )

        documents = []
        async for doc in cursor:
            documents.append(self._doc_to_document_info(doc))

        return documents, total

    async def create_document(
        self, user_id: str, case_id: str, data: DocumentCreateRequest
    ) -> Dict:
        """
        创建文档记录

        Args:
            user_id: 用户ID
            case_id: 案件ID
            data: 创建请求数据

        Returns:
            创建的文档信息
        """
        now = self._now()
        doc_doc = {
            "case_id": case_id,
            "user_id": user_id,
            "name": data.name,
            "file_url": data.file_url,
            "doc_type": data.doc_type,
            "doc_category": getattr(data, "doc_category", "") or "",
            "file_path": getattr(data, "file_path", "") or "",
            "description": data.description,
            "uploader": "",
            "is_deleted": False,
            "created_at": now,
            "updated_at": now,
        }

        result = await self.db.case_documents.insert_one(doc_doc)

        logger.info(f"文档创建成功: id={str(result.inserted_id)}, case_id={case_id}")

        doc_doc["_id"] = result.inserted_id
        return self._doc_to_document_info(doc_doc)

    async def delete_document(self, user_id: str, case_id: str, document_id: str) -> bool:
        """
        删除文档（软删除）

        Args:
            user_id: 用户ID
            case_id: 案件ID
            document_id: 文档ID

        Returns:
            是否删除成功
        """
        oid = self._safe_oid(document_id)
        if oid is None:
            return False

        result = await self.db.case_documents.update_one(
            {"_id": oid, "case_id": case_id},
            {"$set": {"is_deleted": True, "updated_at": self._now()}},
        )

        if result.modified_count > 0:
            logger.info(f"文档删除成功: id={document_id}")
            return True

        return False
