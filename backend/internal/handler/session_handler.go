package handler

import (
	"net/http"
	"strconv"

	"ai-law-assistant/internal/dto/request"
	"ai-law-assistant/internal/dto/response"
	"ai-law-assistant/internal/middleware"
	"ai-law-assistant/internal/pkg/errcode"
	"ai-law-assistant/internal/pkg/crypto"
	"ai-law-assistant/internal/service"

	"github.com/gin-gonic/gin"
)

type SessionHandler struct {
	sessionService *service.SessionService
}

func NewSessionHandler(sessionService *service.SessionService) *SessionHandler {
	return &SessionHandler{sessionService: sessionService}
}

// Create POST /api/v1/sessions
func (h *SessionHandler) Create(c *gin.Context) {
	userID := middleware.GetUserID(c)

	var req request.CreateSessionRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.Error(c, http.StatusBadRequest, errcode.CodeInvalidParam)
		return
	}

	session, err := h.sessionService.CreateSession(c.Request.Context(), userID, req.Title, req.Category)
	if err != nil {
		response.Error(c, http.StatusInternalServerError, errcode.CodeInternalError)
		return
	}

	response.Success(c, response.SessionInfo{
		ID:        session.ID,
		Title:     session.Title,
		Category:  session.Category,
		MsgCount:  session.MsgCount,
		UpdatedAt: session.UpdatedAt.Format("2006-01-02T15:04:05Z"),
	})
}

// List GET /api/v1/sessions
func (h *SessionHandler) List(c *gin.Context) {
	userID := middleware.GetUserID(c)

	var pagination request.PaginationRequest
	if err := c.ShouldBindQuery(&pagination); err != nil {
		response.Error(c, http.StatusBadRequest, errcode.CodeInvalidParam)
		return
	}
	pagination.Normalize()

	sessions, total, err := h.sessionService.GetSessions(c.Request.Context(), userID, pagination.Offset(), pagination.PageSize)
	if err != nil {
		response.Error(c, http.StatusInternalServerError, errcode.CodeInternalError)
		return
	}

	var list []response.SessionInfo
	for _, s := range sessions {
		list = append(list, response.SessionInfo{
			ID:        s.ID,
			Title:     s.Title,
			Category:  s.Category,
			MsgCount:  s.MsgCount,
			UpdatedAt: s.UpdatedAt.Format("2006-01-02T15:04:05Z"),
		})
	}

	response.Paginated(c, list, total, pagination.Page, pagination.PageSize)
}

// Detail GET /api/v1/sessions/:id
// 返回扁平结构：前端 history_detail.html 期望 data.title, data.msg_count, data.updated_at, data.messages 直接在 data 下
func (h *SessionHandler) Detail(c *gin.Context) {
	userID := middleware.GetUserID(c)
	sessionID, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil {
		response.Error(c, http.StatusBadRequest, errcode.CodeInvalidParam)
		return
	}

	var pagination request.PaginationRequest
	if err := c.ShouldBindQuery(&pagination); err != nil {
		pagination.Page = 1
		pagination.PageSize = 50
	}
	pagination.Normalize()

	session, messages, _, err := h.sessionService.GetSessionDetail(
		c.Request.Context(), sessionID, userID, pagination.Offset(), pagination.PageSize)
	if err != nil {
		response.Error(c, http.StatusNotFound, errcode.CodeSessionNotFound)
		return
	}
	if session == nil {
		response.Error(c, http.StatusForbidden, errcode.CodeSessionNotFound)
		return
	}

	var msgList []response.MessageInfo
	for _, m := range messages {
		msgList = append(msgList, response.MessageInfo{
			ID:        m.ID,
			Role:      m.Role,
			Content:   m.Content,
			Tokens:    m.Tokens,
			CreatedAt: m.CreatedAt.Format("2006-01-02T15:04:05Z"),
		})
	}

	// 扁平结构：title, msg_count, updated_at, messages 直接在 data 层
	response.Success(c, response.SessionDetailResponse{
		ID:        session.ID,
		Title:     session.Title,
		Category:  session.Category,
		MsgCount:  session.MsgCount,
		UpdatedAt: session.UpdatedAt.Format("2006-01-02T15:04:05Z"),
		Messages:  msgList,
	})
}

// Delete DELETE /api/v1/sessions/:id
func (h *SessionHandler) Delete(c *gin.Context) {
	userID := middleware.GetUserID(c)
	sessionID, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil {
		response.Error(c, http.StatusBadRequest, errcode.CodeInvalidParam)
		return
	}

	if err := h.sessionService.DeleteSession(c.Request.Context(), sessionID, userID); err != nil {
		response.Error(c, http.StatusInternalServerError, errcode.CodeInternalError)
		return
	}

	response.SuccessWithMessage(c, "删除成功", nil)
}

// ClearAllHistory DELETE /api/v1/sessions/clear-all
// 清空当前用户全部历史记录
func (h *SessionHandler) ClearAllHistory(c *gin.Context) {
	userID := middleware.GetUserID(c)

	if err := h.sessionService.ClearAllSessions(c.Request.Context(), userID); err != nil {
		response.Error(c, http.StatusInternalServerError, errcode.CodeInternalError)
		return
	}

	response.SuccessWithMessage(c, "已清空全部历史记录", nil)
}

// 导出手机号脱敏
var maskPhoneForLog = crypto.MaskPhone
var _ = maskPhoneForLog
