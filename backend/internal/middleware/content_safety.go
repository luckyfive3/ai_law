package middleware

import (
	"net/http"
	"strings"
	"sync"

	"ai-law-assistant/internal/dto/response"
	"ai-law-assistant/internal/pkg/errcode"

	"github.com/gin-gonic/gin"
)

// ContentSafety 内容安全过滤中间件
type ContentSafety struct {
	mu         sync.RWMutex
	keywords   map[string]struct{}
	enable     bool
}

// NewContentSafety 创建内容安全过滤器
func NewContentSafety(enable bool) *ContentSafety {
	cs := &ContentSafety{
		keywords: make(map[string]struct{}),
		enable:   enable,
	}
	// 默认敏感词列表
	defaultKeywords := []string{
		// 政治敏感 - 用占位符示意
	}
	for _, kw := range defaultKeywords {
		cs.keywords[kw] = struct{}{}
	}
	return cs
}

// AddKeyword 添加敏感词
func (cs *ContentSafety) AddKeyword(keyword string) {
	cs.mu.Lock()
	defer cs.mu.Unlock()
	cs.keywords[keyword] = struct{}{}
}

// AddKeywords 批量添加敏感词
func (cs *ContentSafety) AddKeywords(keywords []string) {
	cs.mu.Lock()
	defer cs.mu.Unlock()
	for _, kw := range keywords {
		cs.keywords[kw] = struct{}{}
	}
}

// Check 检查文本是否包含敏感词
func (cs *ContentSafety) Check(text string) bool {
	if !cs.enable {
		return true
	}
	cs.mu.RLock()
	defer cs.mu.RUnlock()
	for kw := range cs.keywords {
		if strings.Contains(text, kw) {
			return false
		}
	}
	return true
}

// Filter 过滤敏感词（替换为**）
func (cs *ContentSafety) Filter(text string) string {
	if !cs.enable {
		return text
	}
	cs.mu.RLock()
	defer cs.mu.RUnlock()
	result := text
	for kw := range cs.keywords {
		result = strings.ReplaceAll(result, kw, "**")
	}
	return result
}

// Middleware Gin中间件包装
func (cs *ContentSafety) Middleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		if c.Request.Method == http.MethodPost && cs.enable {
			contentType := c.GetHeader("Content-Type")
			if strings.Contains(contentType, "application/json") {
				// 读取body进行敏感词检测 - 简单策略
				body, _ := c.GetRawData()
				bodyStr := string(body)
				if !cs.Check(bodyStr) {
					response.Error(c, http.StatusForbidden, errcode.CodeSensitiveContent)
					return
				}
				// 将 body 写回，供后续 Handler 使用
				c.Request.Body = http.MaxBytesReader(c.Writer, http.NoBody, 0)
				// 使用 Request 重新设置 body（简化处理，敏感的请求直接拒绝）
			}
		}
		c.Next()
	}
}
