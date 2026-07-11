"""
schemas/request & response 模块单元测试
"""
import pytest
from pydantic import ValidationError
from schemas.request import (
    RegisterRequest,
    LoginRequest,
    RefreshTokenRequest,
    CreateSessionRequest,
    ChatStreamRequest,
    UpdateProfileRequest,
    UpdatePrivacyRequest,
    PaginationRequest,
)
from schemas.response import success_response, error_response, paginated_response
from utils import errcode


class TestRegisterRequest:
    """注册请求模型验证"""

    def test_valid_register(self):
        """有效注册请求"""
        req = RegisterRequest(
            username="testuser",
            password="password123",
            confirm_password="password123",
            agree_terms=True,
        )
        assert req.username == "testuser"

    def test_password_mismatch(self):
        """密码不一致"""
        with pytest.raises(ValidationError):
            RegisterRequest(
                username="testuser",
                password="password123",
                confirm_password="different",
                agree_terms=True,
            )

    def test_not_agree_terms(self):
        """不同意协议"""
        with pytest.raises(ValidationError):
            RegisterRequest(
                username="testuser",
                password="password123",
                confirm_password="password123",
                agree_terms=False,
            )

    def test_username_too_short(self):
        """用户名过短"""
        with pytest.raises(ValidationError):
            RegisterRequest(
                username="a",
                password="password123",
                confirm_password="password123",
                agree_terms=True,
            )

    def test_username_too_long(self):
        """用户名过长"""
        with pytest.raises(ValidationError):
            RegisterRequest(
                username="x" * 51,
                password="password123",
                confirm_password="password123",
                agree_terms=True,
            )

    def test_password_too_short(self):
        """密码过短"""
        with pytest.raises(ValidationError):
            RegisterRequest(
                username="testuser",
                password="12345",
                confirm_password="12345",
                agree_terms=True,
            )


class TestLoginRequest:
    """登录请求模型验证"""

    def test_valid_login(self):
        """有效登录请求"""
        req = LoginRequest(username="testuser", password="password123", agree_terms=True)
        assert req.username == "testuser"

    def test_missing_agree_terms(self):
        """不同意协议"""
        with pytest.raises(ValidationError):
            LoginRequest(username="testuser", password="password123", agree_terms=False)

    def test_missing_username(self):
        """缺少用户名"""
        with pytest.raises(ValidationError):
            LoginRequest(password="password123", agree_terms=True)


class TestRefreshTokenRequest:
    """刷新 Token 请求"""

    def test_valid_refresh(self):
        req = RefreshTokenRequest(refresh_token="some-token-string")
        assert req.refresh_token == "some-token-string"

    def test_missing_token(self):
        with pytest.raises(ValidationError):
            RefreshTokenRequest()


class TestCreateSessionRequest:
    """创建会话请求"""

    def test_default_values(self):
        req = CreateSessionRequest()
        assert req.title is None
        assert req.category is None

    def test_with_values(self):
        req = CreateSessionRequest(title="咨询", category="civil")
        assert req.title == "咨询"
        assert req.category == "civil"


class TestChatStreamRequest:
    """聊天流式请求"""

    def test_valid_request(self):
        req = ChatStreamRequest(
            session_id="507f1f77bcf86cd799439022",
            content="什么是民法典",
        )
        assert req.session_id == "507f1f77bcf86cd799439022"
        assert req.content == "什么是民法典"

    def test_content_too_long(self):
        with pytest.raises(ValidationError):
            ChatStreamRequest(
                session_id="sid",
                content="x" * 2001,
            )

    def test_content_max_boundary(self):
        """恰好2000字符 → 通过"""
        req = ChatStreamRequest(session_id="sid", content="y" * 2000)
        assert len(req.content) == 2000

    def test_optional_category(self):
        req = ChatStreamRequest(session_id="sid", content="test", category="civil")
        assert req.category == "civil"


class TestUpdateProfileRequest:
    """更新资料请求"""

    def test_valid_nickname(self):
        req = UpdateProfileRequest(nickname="新昵称")
        assert req.nickname == "新昵称"

    def test_valid_avatar(self):
        req = UpdateProfileRequest(avatar_url="https://example.com/avatar.png")
        assert req.avatar_url == "https://example.com/avatar.png"

    def test_empty_request_allowed(self):
        """空请求允许但业务层拒绝"""
        req = UpdateProfileRequest()
        assert req.nickname is None

    def test_nickname_too_long(self):
        with pytest.raises(ValidationError):
            UpdateProfileRequest(nickname="x" * 51)


class TestUpdatePrivacyRequest:
    """更新隐私请求"""

    def test_valid_privacy(self):
        req = UpdatePrivacyRequest(privacy_save_history=False)
        assert req.privacy_save_history is False

    def test_missing_field(self):
        with pytest.raises(ValidationError):
            UpdatePrivacyRequest()


class TestPaginationRequest:
    """分页请求"""

    def test_default_values(self):
        req = PaginationRequest()
        assert req.page == 1
        assert req.page_size == 20
        assert req.offset == 0

    def test_custom_values(self):
        req = PaginationRequest(page=3, page_size=10)
        assert req.page == 3
        assert req.page_size == 10
        assert req.offset == 20

    def test_page_min_value(self):
        with pytest.raises(ValidationError):
            PaginationRequest(page=0)

    def test_page_size_max_value(self):
        with pytest.raises(ValidationError):
            PaginationRequest(page_size=51)

    def test_normalize_output(self):
        result = PaginationRequest(page=2, page_size=25).normalize()
        assert result == {"page": 2, "page_size": 25}


class TestResponseHelpers:
    """响应辅助函数测试"""

    def test_success_response(self):
        result = success_response({"key": "value"})
        assert result["code"] == errcode.CodeSuccess
        assert result["data"] == {"key": "value"}

    def test_success_response_none_data(self):
        result = success_response()
        assert result["code"] == errcode.CodeSuccess
        assert result["data"] is None

    def test_error_response(self):
        result = error_response(errcode.CodeSessionNotFound)
        assert result["code"] == errcode.CodeSessionNotFound
        assert result["data"] is None

    def test_error_response_with_data(self):
        result = error_response(errcode.CodeInvalidParam, "detail info")
        assert result["data"] == "detail info"

    def test_paginated_response(self):
        result = paginated_response(
            data_list=[1, 2, 3],
            total=10,
            page=1,
            page_size=3,
        )
        assert result["code"] == errcode.CodeSuccess
        assert result["data"]["list"] == [1, 2, 3]
        assert result["data"]["total"] == 10
        assert result["data"]["page"] == 1
        assert result["data"]["page_size"] == 3
        assert result["data"]["has_more"] is True

    def test_paginated_response_no_more(self):
        result = paginated_response(
            data_list=[1],
            total=1,
            page=1,
            page_size=10,
        )
        assert result["data"]["has_more"] is False
