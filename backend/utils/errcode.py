"""
错误码常量定义模块
与 Go 版本 pkg/errcode/errcode.go 保持一致
"""

# ==================== 成功 ====================
CodeSuccess = 0

# ==================== 客户端错误 4xxxx ====================
# 参数相关
CodeInvalidParam = 40003          # 参数无效
CodeAgreementRequired = 40004     # 需要同意协议
CodeContentTooLong = 40005        # 内容过长

# 认证相关
CodeUnauthorized = 40100           # 未授权
CodeTokenExpired = 40101           # Token 已过期
CodeTokenInvalid = 40102           # Token 无效
CodeInvalidCredentials = 40104     # 用户名或密码错误

# 限流相关
CodeRateLimited = 40200            # 请求过于频繁
CodeServiceBusy = 40202            # 服务繁忙

# 内容安全
CodeSensitiveContent = 40300       # 包含敏感内容
CodeAIRefused = 40301              # AI 拒绝回答

# 资源不存在
CodeSessionNotFound = 40400        # 会话不存在
CodeUserNotFound = 40402           # 用户不存在
CodeLawNotFound = 40403            # 法律条文不存在

# ==================== 服务端错误 5xxxx ====================
CodeInternalError = 50000          # 服务器内部错误
CodeAIServiceError = 50001         # AI 服务错误
CodeSearchError = 50002            # 搜索服务错误
CodeDatabaseError = 50003          # 数据库错误

# ==================== 错误码对应的中文消息 ====================
MESSAGES = {
    CodeSuccess: "操作成功",

    CodeInvalidParam: "请求参数无效",
    CodeAgreementRequired: "请先同意用户协议",
    CodeContentTooLong: "输入内容过长",

    CodeUnauthorized: "请先登录",
    CodeTokenExpired: "登录已过期，请重新登录",
    CodeTokenInvalid: "登录凭证无效",
    CodeInvalidCredentials: "用户名或密码错误",

    CodeRateLimited: "请求过于频繁，请稍后再试",
    CodeServiceBusy: "服务繁忙，请稍后再试",

    CodeSensitiveContent: "内容包含敏感信息，请修改后重试",
    CodeAIRefused: "AI 无法回答该问题",

    CodeSessionNotFound: "会话不存在",
    CodeUserNotFound: "用户不存在",
    CodeLawNotFound: "法律条文不存在",

    CodeInternalError: "服务器内部错误，请稍后再试",
    CodeAIServiceError: "AI 服务暂时不可用，请稍后再试",
    CodeSearchError: "搜索服务暂时不可用，请稍后再试",
    CodeDatabaseError: "数据库操作失败，请稍后再试",
}


def get_message(code: int) -> str:
    """
    根据错误码获取对应的中文消息

    Args:
        code: 错误码

    Returns:
        对应的中文消息，如果错误码不存在则返回默认消息
    """
    return MESSAGES.get(code, "未知错误")
