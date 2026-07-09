package errcode

// 错误码定义
const (
	// 成功
	CodeSuccess = 0

	// 参数校验错误 40001-40099
	CodeInvalidParam     = 40003
	CodeAgreementRequired = 40004
	CodeContentTooLong   = 40005
	CodeInvalidUsername   = 40006
	CodeInvalidPassword   = 40007
	CodePasswordMismatch  = 40008
	CodeUsernameExists    = 40009

	// 鉴权错误 40100-40199
	CodeUnauthorized       = 40100
	CodeTokenExpired       = 40101
	CodeTokenInvalid       = 40102
	CodeRefreshTokenInvalid = 40103
	CodeInvalidCredentials  = 40104

	// 限流/熔断 40200-40299
	CodeRateLimited  = 40200
	CodeCircuitOpen  = 40201
	CodeServiceBusy  = 40202

	// 内容安全 40300-40399
	CodeSensitiveContent = 40300
	CodeAIRefused        = 40301

	// 资源不存在 40400-40499
	CodeSessionNotFound = 40400
	CodeMessageNotFound = 40401
	CodeUserNotFound    = 40402
	CodeLawNotFound     = 40403

	// 服务内部错误 50000-50099
	CodeInternalError = 50000
	CodeAIServiceError = 50001
	CodeSearchError   = 50002
	CodeDatabaseError = 50003
)

// 错误码对应的消息
var messages = map[int]string{
	CodeSuccess:             "ok",
	CodeInvalidParam:        "参数错误",
	CodeAgreementRequired:   "请先同意用户协议",
	CodeContentTooLong:      "内容过长，请限制在2000字以内",
	CodeInvalidUsername:     "用户名格式错误（2-50个字符）",
	CodeInvalidPassword:     "密码至少6个字符",
	CodePasswordMismatch:    "两次输入的密码不一致",
	CodeUsernameExists:      "用户名已存在",
	CodeUnauthorized:        "未登录或登录已过期",
	CodeTokenExpired:        "Token已过期，请重新登录",
	CodeTokenInvalid:        "Token无效",
	CodeRefreshTokenInvalid: "Refresh Token无效",
	CodeInvalidCredentials:  "用户名或密码错误",
	CodeRateLimited:         "操作过于频繁，请稍后再试",
	CodeCircuitOpen:         "服务暂时不可用，请稍后重试",
	CodeServiceBusy:         "服务繁忙，请稍后再试",
	CodeSensitiveContent:    "输入内容包含敏感信息，请修改后重试",
	CodeAIRefused:           "抱歉，您的问题超出了我能回答的范围",
	CodeSessionNotFound:     "会话不存在",
	CodeMessageNotFound:     "消息不存在",
	CodeUserNotFound:        "用户不存在",
	CodeLawNotFound:         "法条不存在",
	CodeInternalError:       "系统内部错误",
	CodeAIServiceError:      "AI服务异常，请稍后重试",
	CodeSearchError:         "检索服务异常",
	CodeDatabaseError:       "数据库异常",
}

func GetMessage(code int) string {
	if msg, ok := messages[code]; ok {
		return msg
	}
	return "未知错误"
}
