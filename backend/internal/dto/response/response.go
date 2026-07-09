package response

import (
	"net/http"

	"ai-law-assistant/internal/pkg/errcode"

	"github.com/gin-gonic/gin"
)

// ═══════════════════════════════════════
// 统一 API 响应格式
// { "code": 0, "message": "ok", "data": {...} }
// ═══════════════════════════════════════

// Response 统一响应结构
type Response struct {
	Code    int         `json:"code"`
	Message string      `json:"message"`
	Data    interface{} `json:"data"`
}

// PaginatedData 分页数据
type PaginatedData struct {
	List     interface{} `json:"list"`
	Total    int64       `json:"total"`
	Page     int         `json:"page"`
	PageSize int         `json:"page_size"`
	HasMore  bool        `json:"has_more"`
}

// ═══════════════════════════════════════
// 认证相关响应
// ═══════════════════════════════════════

// AuthResponse 登录/注册响应
type AuthResponse struct {
	AccessToken  string   `json:"access_token"`
	RefreshToken string   `json:"refresh_token"`
	ExpiresIn    int64    `json:"expires_in"`
	User         UserInfo `json:"user"`
}

// ═══════════════════════════════════════
// 用户相关响应
// ═══════════════════════════════════════

// UserInfo 用户信息
type UserInfo struct {
	ID        int64  `json:"id"`
	Username  string `json:"username"`
	Nickname  string `json:"nickname"`
	AvatarURL string `json:"avatar_url,omitempty"`
}

// ═══════════════════════════════════════
// 会话相关响应
// ═══════════════════════════════════════

// SessionInfo 会话列表项信息
type SessionInfo struct {
	ID        int64  `json:"id"`
	Title     string `json:"title"`
	Category  string `json:"category,omitempty"`
	MsgCount  int    `json:"msg_count"`
	UpdatedAt string `json:"updated_at"`
}

// SessionDetailResponse 会话详情响应（扁平结构，匹配前端 history_detail 期望）
type SessionDetailResponse struct {
	ID        int64          `json:"id"`
	Title     string         `json:"title"`
	Category  string         `json:"category,omitempty"`
	MsgCount  int            `json:"msg_count"`
	UpdatedAt string         `json:"updated_at"`
	Messages  []MessageInfo  `json:"messages"`
}

// ═══════════════════════════════════════
// 消息相关响应
// ═══════════════════════════════════════

// MessageInfo 消息信息
// 注意：法条引用字段名使用 name/article/text 匹配前端 JS
type MessageInfo struct {
	ID        int64        `json:"id"`
	Role      string       `json:"role"`
	Content   string       `json:"content"`
	Tokens    int          `json:"tokens"`
	LawRefs   []LawRefInfo `json:"law_refs,omitempty"`
	CreatedAt string       `json:"created_at"`
}

// LawRefInfo 法条引用信息
// 前端 chat.js/history.js 使用: law.name, law.article, law.text, law.source
type LawRefInfo struct {
	Name     string  `json:"name"`
	Article  string  `json:"article"`
	Text     string  `json:"text"`
	Source   string  `json:"source,omitempty"`
	ChunkID  string  `json:"chunk_id,omitempty"`
	Relevance float64 `json:"relevance,omitempty"`
}

// ═══════════════════════════════════════
// 知识库相关响应
// ═══════════════════════════════════════

// LawCategory 法律分类
type LawCategory struct {
	ID       int           `json:"id"`
	Name     string        `json:"name"`
	Children []LawCategory `json:"children,omitempty"`
}

// KnowledgeSearchResult 知识库搜索结果
type KnowledgeSearchResult struct {
	ID         int    `json:"id"`
	Name       string `json:"name"`
	Category   string `json:"category"`
	Year       string `json:"year,omitempty"`
	Summary    string `json:"summary,omitempty"`
}

// LawDetail 法条详情
type LawDetail struct {
	ID       int          `json:"id"`
	Name     string       `json:"name"`
	Year     string       `json:"year,omitempty"`
	Articles []LawArticle `json:"articles"`
}

// LawArticle 法条条款
type LawArticle struct {
	Num     string `json:"num"`
	Content string `json:"content"`
}

// ═══════════════════════════════════════
// SSE 流式响应（用于 chat/stream）
// 前端 chat.js 解析 SSE 事件期望字段
// ═══════════════════════════════════════

// SSEChunk SSE 流中的每个数据块
type SSEChunk struct {
	Status    string       `json:"status,omitempty"`    // "searching" | "generating" | "done"
	Content   string       `json:"content,omitempty"`   // 文本内容
	Index     int          `json:"index,omitempty"`     // 序号
	Done      bool         `json:"done,omitempty"`      // 是否完成
	MessageID int64        `json:"message_id,omitempty"` // 消息ID
	Laws      []LawRefInfo `json:"laws,omitempty"`      // 法条引用
	Tokens    *TokenInfo   `json:"tokens,omitempty"`    // Token统计
	Error     string       `json:"error,omitempty"`     // 错误信息
}

// TokenInfo Token信息
type TokenInfo struct {
	Input  int `json:"input"`
	Output int `json:"output"`
}

// ═══════════════════════════════════════
// 辅助响应方法
// ═══════════════════════════════════════

// Success 成功响应
func Success(c *gin.Context, data interface{}) {
	c.JSON(http.StatusOK, Response{
		Code:    errcode.CodeSuccess,
		Message: "ok",
		Data:    data,
	})
}

// SuccessWithMessage 带消息的成功响应
func SuccessWithMessage(c *gin.Context, message string, data interface{}) {
	c.JSON(http.StatusOK, Response{
		Code:    errcode.CodeSuccess,
		Message: message,
		Data:    data,
	})
}

// Error 错误响应
func Error(c *gin.Context, httpStatus int, code int) {
	ErrorWithDetail(c, httpStatus, code, nil)
}

// ErrorWithDetail 带详情的错误响应
func ErrorWithDetail(c *gin.Context, httpStatus int, code int, data interface{}) {
	c.AbortWithStatusJSON(httpStatus, Response{
		Code:    code,
		Message: errcode.GetMessage(code),
		Data:    data,
	})
}

// Paginated 分页成功响应
func Paginated(c *gin.Context, list interface{}, total int64, page, pageSize int) {
	Success(c, PaginatedData{
		List:     list,
		Total:    total,
		Page:     page,
		PageSize: pageSize,
		HasMore:  int64(page*pageSize) < total,
	})
}
