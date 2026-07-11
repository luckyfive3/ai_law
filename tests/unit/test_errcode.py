"""
utils/errcode 模块单元测试
"""
import pytest
from utils import errcode


class TestErrCode:
    """错误码模块测试"""

    def test_get_message_known_code(self):
        """UT-ERR-01: get_message 返回已知错误码的中文消息"""
        assert errcode.get_message(errcode.CodeSuccess) == "操作成功"
        assert errcode.get_message(errcode.CodeUnauthorized) == "请先登录"
        assert errcode.get_message(errcode.CodeTokenExpired) == "登录已过期，请重新登录"
        assert errcode.get_message(errcode.CodeSessionNotFound) == "会话不存在"
        assert errcode.get_message(errcode.CodeInternalError) == "服务器内部错误，请稍后再试"

    def test_get_message_unknown_code(self):
        """UT-ERR-02: get_message 未知错误码返回默认消息"""
        assert errcode.get_message(99999) == "未知错误"
        assert errcode.get_message(-1) == "未知错误"

    def test_all_codes_have_messages(self):
        """UT-ERR-03: 所有已定义错误码都有对应消息"""
        codes = [
            errcode.CodeSuccess,
            errcode.CodeInvalidParam,
            errcode.CodeAgreementRequired,
            errcode.CodeContentTooLong,
            errcode.CodeUnauthorized,
            errcode.CodeTokenExpired,
            errcode.CodeTokenInvalid,
            errcode.CodeInvalidCredentials,
            errcode.CodeRateLimited,
            errcode.CodeServiceBusy,
            errcode.CodeSensitiveContent,
            errcode.CodeAIRefused,
            errcode.CodeSessionNotFound,
            errcode.CodeUserNotFound,
            errcode.CodeLawNotFound,
            errcode.CodeInternalError,
            errcode.CodeAIServiceError,
            errcode.CodeSearchError,
            errcode.CodeDatabaseError,
        ]
        for code in codes:
            msg = errcode.get_message(code)
            assert isinstance(msg, str), f"code={code} 的消息不是字符串"
            assert len(msg) > 0, f"code={code} 的消息为空"

    def test_error_codes_are_distinct(self):
        """所有错误码互不相同"""
        codes = [
            errcode.CodeSuccess,
            errcode.CodeInvalidParam,
            errcode.CodeAgreementRequired,
            errcode.CodeContentTooLong,
            errcode.CodeUnauthorized,
            errcode.CodeTokenExpired,
            errcode.CodeTokenInvalid,
            errcode.CodeInvalidCredentials,
            errcode.CodeRateLimited,
            errcode.CodeServiceBusy,
            errcode.CodeSensitiveContent,
            errcode.CodeAIRefused,
            errcode.CodeSessionNotFound,
            errcode.CodeUserNotFound,
            errcode.CodeLawNotFound,
            errcode.CodeInternalError,
            errcode.CodeAIServiceError,
            errcode.CodeSearchError,
            errcode.CodeDatabaseError,
        ]
        assert len(codes) == len(set(codes)), "存在重复的错误码"
