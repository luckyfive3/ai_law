package handler

import (
	"net/http"

	"ai-law-assistant/internal/dto/request"
	"ai-law-assistant/internal/dto/response"
	"ai-law-assistant/internal/pkg/errcode"
	"ai-law-assistant/internal/service"

	"github.com/gin-gonic/gin"
)

type AuthHandler struct {
	authService *service.AuthService
	userService *service.UserService
}

func NewAuthHandler(authService *service.AuthService, userService *service.UserService) *AuthHandler {
	return &AuthHandler{
		authService: authService,
		userService: userService,
	}
}

// Register POST /api/v1/auth/register
func (h *AuthHandler) Register(c *gin.Context) {
	var req request.RegisterRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.Error(c, http.StatusBadRequest, errcode.CodeInvalidParam)
		return
	}

	// 确认密码一致性
	if req.Password != req.ConfirmPassword {
		response.Error(c, http.StatusBadRequest, errcode.CodePasswordMismatch)
		return
	}

	if !req.AgreeTerms {
		response.Error(c, http.StatusBadRequest, errcode.CodeAgreementRequired)
		return
	}

	user, err := h.authService.Register(c.Request.Context(), req.Username, req.Password)
	if err != nil {
		if err == service.ErrUsernameExists {
			response.Error(c, http.StatusConflict, errcode.CodeUsernameExists)
			return
		}
		response.Error(c, http.StatusInternalServerError, errcode.CodeInternalError)
		return
	}

	accessToken, refreshToken, err := h.authService.GenerateTokens(user)
	if err != nil {
		response.Error(c, http.StatusInternalServerError, errcode.CodeInternalError)
		return
	}

	response.Success(c, response.AuthResponse{
		AccessToken:  accessToken,
		RefreshToken: refreshToken,
		ExpiresIn:    86400,
		User: response.UserInfo{
			ID:        user.ID,
			Username:  user.Username,
			Nickname:  user.Nickname,
			AvatarURL: user.AvatarURL,
		},
	})
}

// Login POST /api/v1/auth/login
func (h *AuthHandler) Login(c *gin.Context) {
	var req request.LoginRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.Error(c, http.StatusBadRequest, errcode.CodeInvalidParam)
		return
	}

	if !req.AgreeTerms {
		response.Error(c, http.StatusBadRequest, errcode.CodeAgreementRequired)
		return
	}

	user, err := h.authService.Login(c.Request.Context(), req.Username, req.Password)
	if err != nil {
		response.Error(c, http.StatusUnauthorized, errcode.CodeInvalidCredentials)
		return
	}

	accessToken, refreshToken, err := h.authService.GenerateTokens(user)
	if err != nil {
		response.Error(c, http.StatusInternalServerError, errcode.CodeInternalError)
		return
	}

	response.Success(c, response.AuthResponse{
		AccessToken:  accessToken,
		RefreshToken: refreshToken,
		ExpiresIn:    86400,
		User: response.UserInfo{
			ID:        user.ID,
			Username:  user.Username,
			Nickname:  user.Nickname,
			AvatarURL: user.AvatarURL,
		},
	})
}

// RefreshToken POST /api/v1/auth/refresh
func (h *AuthHandler) RefreshToken(c *gin.Context) {
	var req request.RefreshTokenRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		response.Error(c, http.StatusBadRequest, errcode.CodeInvalidParam)
		return
	}

	accessToken, refreshToken, err := h.authService.RefreshToken(req.RefreshToken)
	if err != nil {
		response.Error(c, http.StatusUnauthorized, errcode.CodeRefreshTokenInvalid)
		return
	}

	response.Success(c, gin.H{
		"access_token":  accessToken,
		"refresh_token": refreshToken,
		"expires_in":    86400,
	})
}

// Logout POST /api/v1/auth/logout
func (h *AuthHandler) Logout(c *gin.Context) {
	// JWT 无状态，退出登录只需客户端清除 Token
	response.SuccessWithMessage(c, "已退出登录", nil)
}
