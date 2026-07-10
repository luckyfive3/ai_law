"""
AI法律助手 v1.0 — 聊天 API 路由
提供 SSE 流式对话、消息列表查询和对话导出接口
"""

import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from middleware.auth import get_current_user
from schemas.request import ChatStreamRequest
from schemas.response import success_response, error_response
from utils import errcode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["对话"])


# ==================== 依赖注入 ====================

def get_chat_service(request: Request):
    """
    从应用状态中获取 ChatService 实例
    该实例在 main.py 启动时被注册到 app.state.services 中
    """
    return request.app.state.services["chat_service"]


def get_session_service(request: Request):
    """
    从应用状态中获取 SessionService 实例
    用于校验会话归属
    """
    return request.app.state.services["session_service"]


# ==================== SSE 流式对话 ====================

@router.post("/stream", summary="SSE 流式对话")
async def send_message(
    req: ChatStreamRequest,
    request: Request,
    current_user=Depends(get_current_user),
    chat_service=Depends(get_chat_service),
    session_service=Depends(get_session_service),
):
    """
    SSE 流式对话接口

    使用 Server-Sent Events 协议实时推送 AI 回答。
    需要有效的 JWT Token。

    事件类型：
        - event: thinking  → 正在检索法律知识库
        - event: chunk     → AI 生成的文本片段
        - event: law_ref   → 引用的法律条文（生成完成后）
        - event: done      → 对话完成，含 message_id 和 Token 用量
        - event: error     → 发生错误

    Args:
        req: 聊天请求体，包含 session_id、content 和可选的 category

    Returns:
        StreamingResponse，媒体类型为 text/event-stream
    """
    user_id = current_user["user_id"]
    client_ip = request.client.host if request.client else ""

    # 获取会话信息以确认会话存在且属于当前用户
    try:
        session_detail = await session_service.get_detail(req.session_id, page=1, page_size=1)
        if session_detail is None:
            raise HTTPException(
                status_code=404,
                detail=error_response(errcode.CodeSessionNotFound),
            )
    except HTTPException:
        raise
    except Exception:
        pass  # 不做严格校验，让聊天服务内部处理

    async def event_generator():
        """
        SSE 事件异步生成器

        逐条从 chat_service.send_message() 中获取数据块，
        根据 status 字段格式化为对应的 SSE 事件。

        协议: thinking → chunk* → done
        """
        try:
            async for chunk in chat_service.send_message(
                user_id=user_id,
                session_id=req.session_id,
                query=req.content,
                category=req.category or "",
                client_ip=client_ip,
            ):
                status = chunk.get("status", "")

                if status == "searching":
                    data = json.dumps({
                        "status": "searching",
                    }, ensure_ascii=False)
                    yield f"data: {data}\n\n"

                elif status == "generating":
                    data = json.dumps({
                        "content": chunk.get("content", ""),
                    }, ensure_ascii=False)
                    yield f"data: {data}\n\n"

                elif chunk.get("done") is True:
                    # 生成完成，统一在此发送 message_id、laws、tokens
                    data = json.dumps({
                        "done": True,
                        "message_id": chunk.get("message_id", ""),
                        "laws": chunk.get("laws", []),
                        "tokens": chunk.get("tokens", {}),
                    }, ensure_ascii=False)
                    yield f"data: {data}\n\n"

                elif status == "error":
                    data = json.dumps({
                        "status": "error",
                        "error": chunk.get("error", "未知错误"),
                    }, ensure_ascii=False)
                    yield f"data: {data}\n\n"

                else:
                    # 兜底处理
                    data = json.dumps({
                        "content": chunk.get("content", ""),
                    }, ensure_ascii=False)
                    yield f"data: {data}\n\n"

        except Exception as gen_error:
            logger.error(f"SSE 生成器异常: {gen_error}", exc_info=True)
            data = json.dumps({
                "status": "error",
                "error": "服务暂时不可用，请稍后再试",
            }, ensure_ascii=False)
            yield f"data: {data}\n\n"

    # 返回 StreamingResponse，关闭连接时记录日志
    async def on_close():
        logger.debug(f"SSE 连接关闭: user_id={user_id}, session_id={req.session_id}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
        background=BackgroundTask(on_close),
    )


# ==================== 获取会话消息 ====================

@router.get("/{session_id}/messages", summary="获取会话消息列表")
async def get_messages(
    session_id: str,
    request: Request,
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=50, ge=1, le=50, description="每页数量"),
    current_user=Depends(get_current_user),
    chat_service=Depends(get_chat_service),
):
    """
    获取指定会话的消息列表（分页）

    按创建时间正序排列。
    需要有效的 JWT Token。

    Args:
        session_id: 会话 ID
        page: 页码（从 1 开始）
        page_size: 每页数量（1-50）

    Returns:
        分页的消息列表，包含 list、total、page、page_size、has_more
    """
    try:
        user_id = current_user["user_id"]

        # 计算偏移量
        offset = (page - 1) * page_size
        messages, total = await chat_service.get_messages(
            session_id=session_id,
            offset=offset,
            limit=page_size,
        )

        logger.info(f"获取消息列表成功: session_id={session_id}, total={total}")
        return success_response({
            "list": messages,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": (page * page_size) < total,
        })

    except Exception as e:
        logger.error(f"获取消息列表异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(errcode.CodeInternalError),
        )


# ==================== 导出会话消息 ====================

@router.get("/{session_id}/export", summary="导出会话消息")
async def export_messages(
    session_id: str,
    request: Request,
    current_user=Depends(get_current_user),
    chat_service=Depends(get_chat_service),
):
    """
    导出指定会话的所有消息为纯文本格式

    按创建时间正序排列，角色标记为"用户"或"AI法律助手"。
    需要有效的 JWT Token。

    Args:
        session_id: 会话 ID

    Returns:
        纯文本格式的对话记录
    """
    try:
        user_id = current_user["user_id"]

        text_content = await chat_service.export_messages(session_id)

        logger.info(f"导出消息成功: session_id={session_id}, user_id={user_id}")

        # 作为纯文本文件返回
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(
            content=text_content,
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="session_{session_id}.txt"',
            },
        )

    except Exception as e:
        logger.error(f"导出消息异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_response(errcode.CodeInternalError),
        )
