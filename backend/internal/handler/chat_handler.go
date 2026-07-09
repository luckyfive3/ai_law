package handler

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strconv"

	"ai-law-assistant/internal/dto/request"
	"ai-law-assistant/internal/dto/response"
	"ai-law-assistant/internal/middleware"
	"ai-law-assistant/internal/pkg/errcode"
	"ai-law-assistant/internal/service"

	"github.com/gin-gonic/gin"
)

type ChatHandler struct {
	chatService *service.ChatService
}

func NewChatHandler(chatService *service.ChatService) *ChatHandler {
	return &ChatHandler{chatService: chatService}
}

// SendMessage POST /api/v1/chat/stream (SSE)
// 前端 chat.js 解析 event:thinking / event:chunk / event:law_ref / event:done
func (h *ChatHandler) SendMessage(c *gin.Context) {
	userID := middleware.GetUserID(c)
	clientIP := c.ClientIP()

	var req request.ChatStreamRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.Error(c, http.StatusBadRequest, errcode.CodeInvalidParam)
		return
	}

	chatCtx := &service.ChatContext{
		UserID:    userID,
		SessionID: req.SessionID,
		Query:     req.Content,
		Category:  req.Category,
		ClientIP:  clientIP,
	}

	result, err := h.chatService.SendMessage(c.Request.Context(), chatCtx)
	if err != nil {
		response.Error(c, http.StatusForbidden, errcode.CodeSensitiveContent)
		return
	}

	// SSE 响应头
	c.Header("Content-Type", "text/event-stream")
	c.Header("Cache-Control", "no-cache")
	c.Header("Connection", "keep-alive")
	c.Header("X-Accel-Buffering", "no")

	c.Stream(func(w io.Writer) bool {
		chunk, ok := <-result.StreamChunk
		if !ok {
			return false
		}

		data, _ := json.Marshal(chunk)

		switch chunk.Status {
		case "searching":
			// event:thinking → 前端 chat.js 显示"正在检索相关法条…"
			fmt.Fprintf(w, "event: thinking\ndata: %s\n\n", data)
		case "generating":
			// event:chunk → 前端 chat.js 接收 data.content 逐字渲染
			if chunk.Content != "" {
				fmt.Fprintf(w, "event: chunk\ndata: %s\n\n", data)
			}
		default:
			if chunk.Done {
				// event:law_ref → 前端 chat.js 接收 data.laws 渲染法条卡片
				if len(chunk.Laws) > 0 {
					lawData, _ := json.Marshal(gin.H{"laws": chunk.Laws})
					fmt.Fprintf(w, "event: law_ref\ndata: %s\n\n", lawData)
				}
				// event:done → 前端 chat.js 最终处理
				doneData, _ := json.Marshal(gin.H{
					"status":     "done",
					"done":       true,
					"message_id": chunk.MessageID,
					"tokens":     chunk.Tokens,
				})
				fmt.Fprintf(w, "event: done\ndata: %s\n\n", doneData)
				return false
			}
		}
		return true
	})
}

// GetMessages GET /api/v1/chat/:session_id/messages
func (h *ChatHandler) GetMessages(c *gin.Context) {
	sessionID, err := strconv.ParseInt(c.Param("session_id"), 10, 64)
	if err != nil {
		response.Error(c, http.StatusBadRequest, errcode.CodeInvalidParam)
		return
	}

	var pagination request.PaginationRequest
	if err := c.ShouldBindQuery(&pagination); err != nil {
		response.Error(c, http.StatusBadRequest, errcode.CodeInvalidParam)
		return
	}
	pagination.Normalize()

	messages, total, err := h.chatService.GetMessages(c.Request.Context(), sessionID, pagination.Offset(), pagination.PageSize)
	if err != nil {
		response.Error(c, http.StatusInternalServerError, errcode.CodeInternalError)
		return
	}

	response.Paginated(c, messages, total, pagination.Page, pagination.PageSize)
}

// Export GET /api/v1/chat/:session_id/export
// 前端 history_detail.html 用 fetch 直接请求此接口并获得 text/plain 下载
func (h *ChatHandler) Export(c *gin.Context) {
	sessionID, err := strconv.ParseInt(c.Param("session_id"), 10, 64)
	if err != nil {
		response.Error(c, http.StatusBadRequest, errcode.CodeInvalidParam)
		return
	}

	content, err := h.chatService.ExportMessages(c.Request.Context(), sessionID)
	if err != nil {
		response.Error(c, http.StatusInternalServerError, errcode.CodeInternalError)
		return
	}

	c.Header("Content-Type", "text/plain; charset=utf-8")
	c.Header("Content-Disposition", fmt.Sprintf("attachment; filename=chat_%d.txt", sessionID))
	c.String(http.StatusOK, content)
}
