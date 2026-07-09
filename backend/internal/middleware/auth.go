package middleware

import (
	"fmt"
	"net/http"
	"strings"

	"ai-law-assistant/internal/pkg/errcode"
	jwtpkg "ai-law-assistant/internal/pkg/jwt"
	"ai-law-assistant/internal/dto/response"

	"github.com/gin-gonic/gin"
)

// Auth JWT鉴权中间件
func Auth(jwtManager *jwtpkg.Manager) gin.HandlerFunc {
	return func(c *gin.Context) {
		authHeader := c.GetHeader("Authorization")
		if authHeader == "" {
			response.Error(c, http.StatusUnauthorized, errcode.CodeUnauthorized)
			return
		}

		parts := strings.SplitN(authHeader, " ", 2)
		if len(parts) != 2 || strings.ToLower(parts[0]) != "bearer" {
			response.Error(c, http.StatusUnauthorized, errcode.CodeUnauthorized)
			return
		}

		claims, err := jwtManager.ParseToken(parts[1])
		if err != nil {
			response.Error(c, http.StatusUnauthorized, errcode.CodeTokenExpired)
			return
		}

		// 将用户信息注入上下文
		c.Set("user_id", claims.UserID)
		c.Set("username", claims.Username)
		c.Next()
	}
}

// GetUserID 从上下文中获取用户ID
func GetUserID(c *gin.Context) int64 {
	uid, exists := c.Get("user_id")
	if !exists {
		return 0
	}
	id, ok := uid.(int64)
	if !ok {
		// 兼容 float64（JSON 解析可能出现）
		if f, ok := uid.(float64); ok {
			return int64(f)
		}
		return 0
	}
	return id
}

// GetUsername 从上下文中获取用户名
func GetUsername(c *gin.Context) string {
	username, exists := c.Get("username")
	if !exists {
		return ""
	}
	return fmt.Sprintf("%v", username)
}

// OptionalAuth 可选鉴权（不强制要求登录）
func OptionalAuth(jwtManager *jwtpkg.Manager) gin.HandlerFunc {
	return func(c *gin.Context) {
		authHeader := c.GetHeader("Authorization")
		if authHeader == "" {
			c.Next()
			return
		}
		parts := strings.SplitN(authHeader, " ", 2)
		if len(parts) != 2 || strings.ToLower(parts[0]) != "bearer" {
			c.Next()
			return
		}
		claims, err := jwtManager.ParseToken(parts[1])
		if err != nil {
			c.Next()
			return
		}
		c.Set("user_id", claims.UserID)
		c.Set("username", claims.Username)
		c.Next()
	}
}
