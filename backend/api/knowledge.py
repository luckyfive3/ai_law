"""
AI法律助手 v1.0 — 知识库 API 路由
提供法律分类、关键词搜索和法条详情查询接口
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from schemas.response import success_response, error_response
from utils import errcode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/knowledge", tags=["知识库"])


# ==================== 依赖注入 ====================

def get_knowledge_service(request: Request):
    return request.app.state.services["knowledge_service"]


# ==================== 获取 RAGFlow 文档列表 ====================

@router.get("/documents", summary="获取 RAGFlow 文档列表")
async def get_ragflow_documents(
    request: Request,
    filter_type: str = Query(default="category", description="category 或 module"),
    filter_value: str = Query(default="all", description="筛选值"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=100, ge=1, le=200, description="每页数量"),
    knowledge_service=Depends(get_knowledge_service),
):
    """获取文档列表。filter_type=category 按法律领域，filter_type=module 按知识库模块"""
    try:
        result = await knowledge_service.get_ragflow_documents(
            filter_type=filter_type, filter_value=filter_value,
            page=page, page_size=page_size,
        )
        logger.info(f"文档列表: type={filter_type} val={filter_value} page={page} total={result.get('total',0)}")
        return success_response(result)
    except Exception as e:
        logger.error(f"获取文档列表异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=error_response(errcode.CodeInternalError))


# ==================== 获取法律分类 ====================

@router.get("/categories", summary="获取法律分类和模块列表")
async def get_categories(
    request: Request,
    knowledge_service=Depends(get_knowledge_service),
):
    """获取法律领域分类列表 + 知识库模块列表"""
    try:
        categories = await knowledge_service.get_categories()
        modules = await knowledge_service.get_modules()
        logger.info(f"分类: {len(categories)} 法律领域, {len(modules)} 模块")
        return success_response({"categories": categories, "modules": modules})
    except Exception as e:
        logger.error(f"获取分类异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=error_response(errcode.CodeInternalError))


# ==================== 关键词搜索 ====================

@router.get("/search", summary="关键词搜索法条")
async def search_laws(
    request: Request,
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=10, ge=1, le=50, description="每页数量"),
    knowledge_service=Depends(get_knowledge_service),
):
    """通过关键词搜索法律知识库"""
    try:
        result = await knowledge_service.search(keyword=keyword, page=page, page_size=page_size)
        logger.info(f"法律搜索成功: keyword='{keyword}', 结果数={result.get('count', 0)}")
        return success_response(result)
    except Exception as e:
        logger.error(f"法律搜索异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=error_response(errcode.CodeSearchError))


# ==================== 获取法条详情 ====================

@router.get("/laws/{law_id}", summary="获取法条详情")
async def get_law_detail(
    law_id: str,
    request: Request,
    knowledge_service=Depends(get_knowledge_service),
):
    """获取指定法条（文档）的详细信息"""
    try:
        detail = await knowledge_service.get_law_detail(law_id)
        logger.info(f"获取法条详情成功: law_id={law_id}")
        return success_response(detail)
    except ValueError:
        logger.warning(f"法条不存在: law_id={law_id}")
        raise HTTPException(status_code=404, detail=error_response(errcode.CodeLawNotFound))
    except Exception as e:
        logger.error(f"获取法条详情异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=error_response(errcode.CodeSearchError))
