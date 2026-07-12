"""
AI法律助手 v1.0 — 案件管理 API 路由
提供案件 CRUD、AI 分析、证据管理、文档管理等接口
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from middleware.auth import get_current_user
from schemas.case_schemas import (
    CaseCreateRequest,
    CaseUpdateRequest,
    CaseQARequest,
    CaseAnalysisRequest,
    EvidenceCreateRequest,
    EvidenceUpdateRequest,
    DocumentCreateRequest,
    success_response,
    error_response,
)
from utils import errcode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/cases", tags=["案件管理"])


# ==================== 依赖注入 ====================

def get_case_service(request: Request):
    """
    从应用状态中获取 CaseService 实例
    该实例在 main.py 启动时被注册到 app.state.services 中
    """
    return request.app.state.services["case_service"]


# ==================== 案件 CRUD ====================

@router.get("", summary="获取案件列表")
@router.get("/", summary="获取案件列表（带斜杠兼容）")
async def list_cases(
    request: Request,
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=50, description="每页数量"),
    status: str = Query(default="", description="状态筛选"),
    keyword: str = Query(default="", description="关键词搜索"),
    current_user=Depends(get_current_user),
    case_service=Depends(get_case_service),
):
    """
    获取当前用户的案件列表（分页）

    支持按状态筛选和关键词搜索。
    需要有效的 JWT Token。

    Args:
        page: 页码（从1开始）
        page_size: 每页数量（1-50）
        status: 状态筛选（待分析/分析中/已分析）
        keyword: 关键词搜索（匹配标题和描述）

    Returns:
        分页的案件列表
    """
    try:
        user_id = current_user["user_id"]
        cases, total = await case_service.list_cases(
            user_id=user_id,
            page=page,
            page_size=page_size,
            status_filter=status,
            keyword=keyword,
        )

        has_more = page * page_size < total
        return success_response({
            "list": cases,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": has_more,
        })

    except Exception as e:
        logger.error(f"获取案件列表异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(errcode.CodeInternalError),
        )


@router.post("", summary="创建案件")
@router.post("/", summary="创建案件（带斜杠兼容）")
async def create_case(
    req: CaseCreateRequest,
    request: Request,
    current_user=Depends(get_current_user),
    case_service=Depends(get_case_service),
):
    """
    创建新案件

    需要有效的 JWT Token。

    Args:
        req: 创建案件请求体

    Returns:
        创建的案件信息
    """
    try:
        user_id = current_user["user_id"]
        case = await case_service.create_case(user_id, req)
        logger.info(f"案件创建成功: id={case['id']}, user_id={user_id}")
        return success_response(case, "案件创建成功")

    except Exception as e:
        logger.error(f"创建案件异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(errcode.CodeInternalError),
        )


@router.get("/{case_id}", summary="获取案件详情")
async def get_case(
    case_id: str,
    request: Request,
    current_user=Depends(get_current_user),
    case_service=Depends(get_case_service),
):
    """
    获取案件详情（含分析记录和问答历史）

    需要有效的 JWT Token。

    Args:
        case_id: 案件ID

    Returns:
        案件详情
    """
    try:
        user_id = current_user["user_id"]
        case = await case_service.get_case(user_id, case_id)

        if case is None:
            raise HTTPException(
                status_code=404,
                detail=error_response(errcode.CodeCaseNotFound),
            )

        return success_response(case)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取案件详情异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(errcode.CodeInternalError),
        )


@router.put("/{case_id}", summary="更新案件")
async def update_case(
    case_id: str,
    req: CaseUpdateRequest,
    request: Request,
    current_user=Depends(get_current_user),
    case_service=Depends(get_case_service),
):
    """
    更新案件信息

    需要有效的 JWT Token。

    Args:
        case_id: 案件ID
        req: 更新请求体

    Returns:
        更新后的案件信息
    """
    try:
        user_id = current_user["user_id"]
        case = await case_service.update_case(user_id, case_id, req)

        if case is None:
            raise HTTPException(
                status_code=404,
                detail=error_response(errcode.CodeCaseNotFound),
            )

        return success_response(case, "案件更新成功")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新案件异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(errcode.CodeInternalError),
        )


@router.delete("/{case_id}", summary="删除案件")
async def delete_case(
    case_id: str,
    request: Request,
    current_user=Depends(get_current_user),
    case_service=Depends(get_case_service),
):
    """
    删除案件（软删除）

    需要有效的 JWT Token。

    Args:
        case_id: 案件ID

    Returns:
        删除结果
    """
    try:
        user_id = current_user["user_id"]
        deleted = await case_service.delete_case(user_id, case_id)

        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=error_response(errcode.CodeCaseNotFound),
            )

        return success_response(None, "案件删除成功")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除案件异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(errcode.CodeInternalError),
        )


# ==================== 案件分析 ====================

@router.post("/{case_id}/analysis", summary="触发案件分析")
async def trigger_analysis(
    case_id: str,
    request: Request,
    body: CaseAnalysisRequest = None,
    current_user=Depends(get_current_user),
    case_service=Depends(get_case_service),
):
    """
    触发 AI 案件综合分析

    生成包含案情摘要、时间轴、事实分析、法律分析、定争分析、
    司法推理、参考判例的完整分析报告。
    需要有效的 JWT Token。

    Args:
        case_id: 案件ID

    Returns:
        分析结果
    """
    try:
        user_id = current_user["user_id"]

        result = await case_service.analyze_case(user_id, case_id)
        if result is None:
            raise HTTPException(
                status_code=404,
                detail=error_response(errcode.CodeCaseNotFound),
            )

        return success_response(result, "案件分析完成")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"案件分析异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(errcode.CodeInternalError),
        )


@router.get("/{case_id}/analysis", summary="获取最新分析")
async def get_latest_analysis(
    case_id: str,
    request: Request,
    current_user=Depends(get_current_user),
    case_service=Depends(get_case_service),
):
    """
    获取案件的最新分析结果

    需要有效的 JWT Token。

    Args:
        case_id: 案件ID

    Returns:
        最新的分析结果（扁平化，内容直接在顶层）
    """
    try:
        user_id = current_user["user_id"]

        case = await case_service.get_case(user_id, case_id)
        if case is None:
            raise HTTPException(
                status_code=404,
                detail=error_response(errcode.CodeCaseNotFound),
            )

        analyses = case.get("analyses", [])
        latest_overview = None
        for a in analyses:
            if a.get("analysis_type") == "case_overview":
                latest_overview = a
                break

        if latest_overview and latest_overview.get("content"):
            # 扁平化：将 content 字典的键提升到顶层
            result = {k: v for k, v in latest_overview.items() if k != "content"}
            result.update(latest_overview["content"])
            return success_response(result)
        else:
            return success_response(latest_overview)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取案件分析异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(errcode.CodeInternalError),
        )


# ==================== 文档管理 ====================

@router.get("/{case_id}/documents", summary="获取文档列表")
async def list_documents(
    case_id: str,
    request: Request,
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=50, description="每页数量"),
    current_user=Depends(get_current_user),
    case_service=Depends(get_case_service),
):
    """
    获取案件的文档列表（分页）

    需要有效的 JWT Token。

    Args:
        case_id: 案件ID
        page: 页码
        page_size: 每页数量

    Returns:
        分页的文档列表
    """
    try:
        user_id = current_user["user_id"]

        case = await case_service.get_case(user_id, case_id)
        if case is None:
            raise HTTPException(
                status_code=404,
                detail=error_response(errcode.CodeCaseNotFound),
            )

        documents, total = await case_service.list_documents(
            user_id, case_id, page, page_size
        )

        has_more = page * page_size < total
        return success_response({
            "list": documents,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": has_more,
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档列表异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(errcode.CodeInternalError),
        )


@router.post("/{case_id}/documents", summary="创建文档")
async def create_document(
    case_id: str,
    req: DocumentCreateRequest,
    request: Request,
    current_user=Depends(get_current_user),
    case_service=Depends(get_case_service),
):
    """
    创建文档记录

    需要有效的 JWT Token。

    Args:
        case_id: 案件ID
        req: 创建文档请求体

    Returns:
        创建的文档信息
    """
    try:
        user_id = current_user["user_id"]

        case = await case_service.get_case(user_id, case_id)
        if case is None:
            raise HTTPException(
                status_code=404,
                detail=error_response(errcode.CodeCaseNotFound),
            )

        document = await case_service.create_document(user_id, case_id, req)
        return success_response(document, "文档创建成功")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建文档异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(errcode.CodeInternalError),
        )


@router.delete("/{case_id}/documents/{document_id}", summary="删除文档")
async def delete_document(
    case_id: str,
    document_id: str,
    request: Request,
    current_user=Depends(get_current_user),
    case_service=Depends(get_case_service),
):
    """
    删除文档（软删除）

    需要有效的 JWT Token。

    Args:
        case_id: 案件ID
        document_id: 文档ID

    Returns:
        删除结果
    """
    try:
        user_id = current_user["user_id"]

        deleted = await case_service.delete_document(user_id, case_id, document_id)
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=error_response(errcode.CodeDocumentNotFound),
            )

        return success_response(None, "文档删除成功")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(errcode.CodeInternalError),
        )


# ==================== 文件上传 ====================

import os as _os2
import uuid
import aiofiles
from fastapi import File, UploadFile

UPLOAD_DIR = _os2.path.join(_os2.path.dirname(_os2.path.dirname(__file__)), "uploads")


@router.post("/{case_id}/upload", summary="上传案件文件")
async def upload_case_file(
    case_id: str,
    request: Request,
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    case_service=Depends(get_case_service),
):
    """
    上传案件相关文件（支持 .pdf/.doc/.docx/.txt/.png/.jpg 等格式）

    上传后自动创建文档记录。
    需要有效的 JWT Token。

    Args:
        case_id: 案件ID
        file: 上传的文件

    Returns:
        上传结果
    """
    try:
        user_id = current_user["user_id"]

        case = await case_service.get_case(user_id, case_id)
        if case is None:
            raise HTTPException(
                status_code=404,
                detail=error_response(errcode.CodeCaseNotFound),
            )

        # 确保上传目录存在
        _os2.makedirs(UPLOAD_DIR, exist_ok=True)

        # 生成唯一文件名
        ext = _os2.path.splitext(file.filename or "document")[1]
        safe_name = f"{uuid.uuid4().hex}{ext}"
        file_path = _os2.path.join(UPLOAD_DIR, safe_name)

        # 保存文件
        async with aiofiles.open(file_path, "wb") as f:
            content = await file.read()
            await f.write(content)

        # 确定文件类型
        ext_lower = ext.lower()
        if ext_lower in [".pdf"]:
            doc_type = "pdf"
        elif ext_lower in [".doc", ".docx"]:
            doc_type = "word"
        elif ext_lower in [".xls", ".xlsx"]:
            doc_type = "excel"
        elif ext_lower in [".png", ".jpg", ".jpeg"]:
            doc_type = "image"
        elif ext_lower in [".txt"]:
            doc_type = "text"
        else:
            doc_type = "other"

        # 创建文档记录（通过服务层）
        # 从 form data 读取文件类别参数
        doc_category_val = ""
        try:
            form_data = await request.form()
            doc_category_val = form_data.get("doc_category", "") if form_data else ""
        except:
            pass

        doc_req = DocumentCreateRequest(
            name=file.filename or "未命名文件",
            file_url=f"/uploads/{safe_name}",
            doc_type=doc_type,
            doc_category=doc_category_val,
            file_path=file_path,
            description=f"用户上传的文件，大小: {len(content)} 字节",
        )
        doc_info = await case_service.create_document(user_id, case_id, doc_req)
        
        # 直接更新 MongoDB 确保 file_path 被正确写入
        from bson import ObjectId as _ObjId
        await case_service.db.case_documents.update_one(
            {"_id": _ObjId(doc_info["id"])},
            {"$set": {"file_path": file_path}}
        )

        # 更新案件证据上传标志
        oid = case_service._safe_oid(case_id)
        if oid:
            await case_service.db.cases.update_one(
                {"_id": oid, "user_id": user_id},
                {"$set": {"evidence_uploaded": True, "updated_at": case_service._now()}},
            )

        logger.info(f"文件上传成功: case_id={case_id}, filename={file.filename}")

        return success_response({
            "filename": file.filename,
            "file_url": f"/uploads/{safe_name}",
            "doc_type": doc_type,
            "size": len(content),
        }, "文件上传成功")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(errcode.CodeInternalError),
        )


# ==================== 案件列表（供聊天页选择） ====================

@router.get("/list/simple", summary="获取案件简要列表")
async def list_cases_simple(
    request: Request,
    current_user=Depends(get_current_user),
    case_service=Depends(get_case_service),
):
    """
    获取用户所有案件的简要列表（供聊天页关联案件使用）

    不需要分页，返回所有未删除案件。
    需要有效的 JWT Token。
    """
    try:
        user_id = current_user["user_id"]
        cases, total = await case_service.list_cases(
            user_id=user_id, page=1, page_size=200
        )
        # 只返回 id 和 title
        simple_list = [{"id": c["id"], "title": c["title"]} for c in cases]
        return success_response(simple_list)
    except Exception as e:
        logger.error(f"获取案件简要列表异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(errcode.CodeInternalError),
        )
