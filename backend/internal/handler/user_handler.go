package handler

import (
	"net/http"

	"ai-law-assistant/internal/dto/request"
	"ai-law-assistant/internal/dto/response"
	"ai-law-assistant/internal/middleware"
	"ai-law-assistant/internal/pkg/errcode"
	"ai-law-assistant/internal/service"

	"github.com/gin-gonic/gin"
)

type UserHandler struct {
	userService *service.UserService
}

func NewUserHandler(userService *service.UserService) *UserHandler {
	return &UserHandler{userService: userService}
}

// GetProfile GET /api/v1/user/profile
func (h *UserHandler) GetProfile(c *gin.Context) {
	userID := middleware.GetUserID(c)

	user, err := h.userService.GetProfile(c.Request.Context(), userID)
	if err != nil {
		response.Error(c, http.StatusNotFound, errcode.CodeUserNotFound)
		return
	}

	response.Success(c, response.UserInfo{
		ID:        user.ID,
		Username:  user.Username,
		Nickname:  user.Nickname,
		AvatarURL: user.AvatarURL,
	})
}

// UpdateProfile PUT /api/v1/user/profile
func (h *UserHandler) UpdateProfile(c *gin.Context) {
	userID := middleware.GetUserID(c)

	var req request.UpdateProfileRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.Error(c, http.StatusBadRequest, errcode.CodeInvalidParam)
		return
	}

	if err := h.userService.UpdateProfile(c.Request.Context(), userID, req.Nickname, req.AvatarURL); err != nil {
		response.Error(c, http.StatusBadRequest, errcode.CodeInvalidParam)
		return
	}

	response.SuccessWithMessage(c, "更新成功", nil)
}

// UpdatePrivacy PUT /api/v1/user/privacy
func (h *UserHandler) UpdatePrivacy(c *gin.Context) {
	userID := middleware.GetUserID(c)

	var req request.UpdatePrivacyRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.Error(c, http.StatusBadRequest, errcode.CodeInvalidParam)
		return
	}

	if err := h.userService.UpdatePrivacy(c.Request.Context(), userID, req.PrivacySaveHistory); err != nil {
		response.Error(c, http.StatusInternalServerError, errcode.CodeInternalError)
		return
	}

	response.SuccessWithMessage(c, "隐私设置已更新", nil)
}
