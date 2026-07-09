"""
响应模型模块
定义所有 API 响应的 Pydantic 数据模型及辅助函数
"""

from typing import Any, Optional, List
from pydantic import BaseModel, Field

from backend.utils.errcode import CodeSuccess, get_message


# ==================== 通用响应模型 ====================

class ApiResponse(BaseModel):
    """
    通用 API 响应结构

    Fields:
        code: 状态码，0 表示成功
        message: 响应消息
        data: 响应数据（任意类型）
    """
    code: int = Field(default=CodeSuccess, description="状态码")
    message: str = Field(default="操作成功", description="响应消息")
    data: Any = Field(default=None, description="响应数据")


class PaginatedData(BaseModel):
    """
    分页数据容器

    Fields:
        list: 数据列表
        total: 总记录数
        page: 当前页码
        page_size: 每页数量
        has_more: 是否还有更多数据
    """
    list: List[Any] = Field(default_factory=list, description="数据列表")
    total: int = Field(default=0, description="总记录数")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=20, description="每页数量")
    has_more: bool = Field(default=False, description="是否还有更多数据")


# ==================== 认证相关响应 ====================

class UserInfo(BaseModel):
    """
    用户基本信息

    Fields:
        id: 用户 ID
        username: 用户名
        nickname: 昵称
        avatar_url: 头像 URL
    """
    id: str = Field(..., description="用户 ID")
    username: str = Field(..., description="用户名")
    nickname: str = Field(default="", description="昵称")
    avatar_url: str = Field(default="", description="头像 URL")


class AuthResponse(BaseModel):
    """
    认证响应（登录/注册成功后返回）

    Fields:
        access_token: 访问令牌
        refresh_token: 刷新令牌
        expires_in: 过期时间（秒）
        user: 用户信息
    """
    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
    expires_in: int = Field(..., description="过期时间（秒）")
    user: UserInfo = Field(..., description="用户信息")


# ==================== 会话相关响应 ====================

class SessionInfo(BaseModel):
    """
    会话摘要信息

    Fields:
        id: 会话 ID
        title: 会话标题
        category: 法律分类
        msg_count: 消息数量
        updated_at: 最后更新时间
    """
    id: str = Field(..., description="会话 ID")
    title: str = Field(default="", description="会话标题")
    category: str = Field(default="", description="法律分类")
    msg_count: int = Field(default=0, description="消息数量")
    updated_at: str = Field(default="", description="最后更新时间")


class SessionDetailResponse(BaseModel):
    """
    会话详情响应（包含消息列表）

    Fields:
        id: 会话 ID
        title: 会话标题
        category: 法律分类
        msg_count: 消息数量
        updated_at: 最后更新时间
        messages: 消息列表
    """
    id: str = Field(..., description="会话 ID")
    title: str = Field(default="", description="会话标题")
    category: str = Field(default="", description="法律分类")
    msg_count: int = Field(default=0, description="消息数量")
    updated_at: str = Field(default="", description="最后更新时间")
    messages: List["MessageInfo"] = Field(default_factory=list, description="消息列表")


# ==================== 消息相关响应 ====================

class MessageInfo(BaseModel):
    """
    消息信息

    Fields:
        id: 消息 ID
        role: 角色（user / assistant）
        content: 消息内容
        tokens: 消耗的 Token 数量
        law_refs: 引用的法律条文列表（可选）
        created_at: 创建时间
    """
    id: str = Field(..., description="消息 ID")
    role: str = Field(..., description="角色")
    content: str = Field(..., description="消息内容")
    tokens: int = Field(default=0, description="Token 数量")
    law_refs: Optional[List["LawRefInfo"]] = Field(default=None, description="法律引用列表")
    created_at: str = Field(..., description="创建时间")


class LawRefInfo(BaseModel):
    """
    法律引用信息

    Fields:
        name: 法律名称
        article: 条款编号
        text: 条款内容
        source: 来源（可选）
        relevance: 相关度（可选）
    """
    name: str = Field(..., description="法律名称")
    article: str = Field(..., description="条款编号")
    text: str = Field(..., description="条款内容")
    source: Optional[str] = Field(default=None, description="来源")
    relevance: Optional[float] = Field(default=None, description="相关度")


# ==================== 知识库相关响应 ====================

class LawCategory(BaseModel):
    """
    法律分类信息

    Fields:
        id: 分类 ID
        name: 分类名称
    """
    id: int = Field(..., description="分类 ID")
    name: str = Field(..., description="分类名称")


class KnowledgeSearchResult(BaseModel):
    """
    知识库搜索结果

    Fields:
        id: 法律 ID
        name: 法律名称
        category: 所属分类
        summary: 摘要
    """
    id: int = Field(..., description="法律 ID")
    name: str = Field(..., description="法律名称")
    category: str = Field(default="", description="所属分类")
    summary: str = Field(default="", description="摘要")


class LawArticle(BaseModel):
    """
    法律条款信息

    Fields:
        num: 条款编号（如 "第一条"、"第12条"）
        content: 条款内容
    """
    num: str = Field(..., description="条款编号")
    content: str = Field(..., description="条款内容")


class LawDetail(BaseModel):
    """
    法律详情

    Fields:
        id: 法律 ID
        name: 法律名称
        year: 颁布年份
        articles: 条款列表
    """
    id: int = Field(..., description="法律 ID")
    name: str = Field(..., description="法律名称")
    year: int = Field(default=0, description="颁布年份")
    articles: List[LawArticle] = Field(default_factory=list, description="条款列表")


# ==================== SSE 流式响应 ====================

class TokenInfo(BaseModel):
    """
    Token 用量信息

    Fields:
        input: 输入 Token 数量
        output: 输出 Token 数量
    """
    input: int = Field(default=0, description="输入 Token 数")
    output: int = Field(default=0, description="输出 Token 数")


class SSEChunk(BaseModel):
    """
    SSE 流式响应块

    Fields:
        status: 状态（generating / done / error）
        content: 当前块的内容
        index: 块序号
        done: 是否结束
        message_id: 消息 ID（结束时返回）
        laws: 引用的法律列表（结束时返回）
        tokens: Token 用量（结束时返回）
        error: 错误信息（出错时返回）
    """
    status: str = Field(default="generating", description="状态")
    content: str = Field(default="", description="当前块内容")
    index: int = Field(default=0, description="块序号")
    done: bool = Field(default=False, description="是否结束")
    message_id: Optional[str] = Field(default=None, description="消息 ID")
    laws: Optional[List[LawRefInfo]] = Field(default=None, description="引用的法律列表")
    tokens: Optional[TokenInfo] = Field(default=None, description="Token 用量")
    error: Optional[str] = Field(default=None, description="错误信息")


# ==================== 辅助函数 ====================

def success_response(data: Any = None) -> dict:
    """
    构建成功响应

    Args:
        data: 响应数据

    Returns:
        成功状态的字典响应
    """
    return {
        "code": CodeSuccess,
        "message": get_message(CodeSuccess),
        "data": data,
    }


def error_response(code: int, data: Any = None) -> dict:
    """
    构建错误响应

    Args:
        code: 错误码
        data: 附加数据（可选）

    Returns:
        错误状态的字典响应
    """
    return {
        "code": code,
        "message": get_message(code),
        "data": data,
    }


def paginated_response(
    data_list: List[Any],
    total: int,
    page: int,
    page_size: int,
) -> dict:
    """
    构建分页响应

    Args:
        data_list: 当前页的数据列表
        total: 总记录数
        page: 当前页码
        page_size: 每页数量

    Returns:
        包含分页信息的状态字典
    """
    has_more = page * page_size < total
    return success_response({
        "list": data_list,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": has_more,
    })
