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
    """
    从应用状态中获取 KnowledgeService 实例
    该实例在 main.py 启动时被注册到 app.state.services 中
    """
    return request.app.state.services["knowledge_service"]


# ==================== 获取法律分类 ====================

@router.get("/categories", summary="获取法律分类列表")
async def get_categories(
    request: Request,
    knowledge_service=Depends(get_knowledge_service),
):
    """
    获取法律知识库的分类列表

    不需要登录即可访问。

    Returns:
        法律分类列表，每项包含 id 和 name
    """
    try:
        categories = await knowledge_service.get_categories()

        logger.info(f"获取法律分类成功，共 {len(categories)} 个分类")
        return success_response(categories)

    except Exception as e:
        logger.error(f"获取法律分类异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(errcode.CodeInternalError),
        )


# ==================== 关键词搜索 ====================

@router.get("/search", summary="关键词搜索法条")
async def search_laws(
    request: Request,
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=10, ge=1, le=50, description="每页数量"),
    knowledge_service=Depends(get_knowledge_service),
):
    """
    通过关键词搜索法律知识库

    先在 RAGFlow 中检索，若无结果则回退到内置法律数据库。
    不需要登录即可访问。

    Args:
        keyword: 搜索关键词（必填）
        page: 页码（从 1 开始）
        page_size: 每页数量（1-50）

    Returns:
        搜索结果，包含 items 列表和 count 总数
    """
    try:
        result = await knowledge_service.search(
            keyword=keyword,
            page=page,
            page_size=page_size,
        )

        logger.info(
            f"法律搜索成功: keyword='{keyword}', "
            f"结果数={result.get('count', 0)}"
        )
        return success_response(result)

    except Exception as e:
        logger.error(f"法律搜索异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(errcode.CodeSearchError),
        )


# ==================== 获取法条详情 ====================

@router.get("/laws/{law_id}", summary="获取法条详情")
async def get_law_detail(
    law_id: str,
    request: Request,
    knowledge_service=Depends(get_knowledge_service),
):
    """
    获取指定法条的详细信息

    不需要登录即可访问。

    Args:
        law_id: 法条 ID

    Returns:
        法条详情，包含 id、name 和 articles 列表
    """
    try:
        detail = await knowledge_service.get_law_detail(law_id)

        logger.info(f"获取法条详情成功: law_id={law_id}")
        return success_response(detail)

    except ValueError:
        logger.warning(f"法条不存在: law_id={law_id}")
        raise HTTPException(
            status_code=404,
            detail=error_response(errcode.CodeLawNotFound),
        )
    except Exception as e:
        logger.error(f"获取法条详情异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(errcode.CodeSearchError),
        )
