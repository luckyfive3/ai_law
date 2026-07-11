"""
请求模型模块
定义所有 API 请求体的 Pydantic 数据模型
"""

from typing import Optional
from pydantic import BaseModel, Field, model_validator


# ==================== 认证相关请求 ====================

class RegisterRequest(BaseModel):
    """
    用户注册请求

    Fields:
        username: 用户名，2-50个字符
        password: 密码，6-100个字符
        confirm_password: 确认密码，必须与 password 一致
        agree_terms: 是否同意用户协议，必须为 True
    """
    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=100, description="密码")
    confirm_password: str = Field(..., min_length=6, max_length=100, description="确认密码")
    agree_terms: bool = Field(..., description="是否同意用户协议")

    @model_validator(mode="after")
    def passwords_match(self):
        """验证两次输入的密码是否一致"""
        if self.password != self.confirm_password:
            raise ValueError("两次输入的密码不一致")
        return self

    @model_validator(mode="after")
    def check_agree_terms(self):
        """验证是否同意用户协议"""
        if not self.agree_terms:
            raise ValueError("请先同意用户协议")
        return self


class LoginRequest(BaseModel):
    """
    用户登录请求

    Fields:
        username: 用户名
        password: 密码
        agree_terms: 是否同意用户协议
    """
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")
    agree_terms: bool = Field(..., description="是否同意用户协议")

    @model_validator(mode="after")
    def check_agree_terms(self):
        """验证是否同意用户协议"""
        if not self.agree_terms:
            raise ValueError("请先同意用户协议")
        return self


class RefreshTokenRequest(BaseModel):
    """
    刷新 Token 请求

    Fields:
        refresh_token: 刷新令牌
    """
    refresh_token: str = Field(..., description="刷新令牌")


# ==================== 会话相关请求 ====================

class CreateSessionRequest(BaseModel):
    """
    创建会话请求

    Fields:
        title: 会话标题（可选）
        category: 会话分类（可选）
    """
    title: Optional[str] = Field(default=None, description="会话标题")
    category: Optional[str] = Field(default=None, description="会话分类")


class ChatStreamRequest(BaseModel):
    """
    聊天流式请求

    Fields:
        session_id: 会话 ID
        content: 用户输入内容，最大2000字符
        category: 法律分类（可选）
        case_id: 关联案件ID（可选）
    """
    session_id: str = Field(..., description="会话 ID")
    content: str = Field(..., max_length=2000, description="用户输入内容")
    category: Optional[str] = Field(default=None, description="法律分类")
    case_id: Optional[str] = Field(default=None, description="关联案件ID")


# ==================== 用户相关请求 ====================

class UpdateProfileRequest(BaseModel):
    """
    更新用户资料请求

    Fields:
        nickname: 昵称，最大50字符（可选）
        avatar_url: 头像 URL，最大500字符（可选）
    """
    nickname: Optional[str] = Field(default=None, max_length=50, description="昵称")
    avatar_url: Optional[str] = Field(default=None, max_length=500, description="头像 URL")


class UpdatePrivacyRequest(BaseModel):
    """
    更新隐私设置请求

    Fields:
        privacy_save_history: 是否保存聊天历史
    """
    privacy_save_history: bool = Field(..., description="是否保存聊天历史")


# ==================== 通用分页请求 ====================

class PaginationRequest(BaseModel):
    """
    分页请求基类

    Fields:
        page: 页码，从1开始，默认1
        page_size: 每页数量，默认20，最大50
    """
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=50, description="每页数量")

    def normalize(self) -> dict:
        """
        规范化分页参数，返回包含 page 和 page_size 的字典

        Returns:
            {"page": int, "page_size": int}
        """
        return {
            "page": self.page,
            "page_size": self.page_size,
        }

    @property
    def offset(self) -> int:
        """
        计算 SQL 查询的 OFFSET 值

        Returns:
            偏移量 (page - 1) * page_size
        """
        return (self.page - 1) * self.page_size
