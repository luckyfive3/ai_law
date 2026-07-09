package middleware

import (
	"time"

	"github.com/gin-gonic/gin"
	"log"
)

// Logger 请求日志中间件
func Logger() gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()
		path := c.Request.URL.Path
		query := c.Request.URL.RawQuery

		c.Next()

		latency := time.Since(start)
		statusCode := c.Writer.Status()

		if query != "" {
			path = path + "?" + query
		}

		log.Printf("[GIN] %s | %3d | %13v | %-15s | %-7s %s",
			time.Now().Format("2006-01-02 15:04:05"),
			statusCode,
			latency,
			c.ClientIP(),
			c.Request.Method,
			path,
		)

		// 记录错误
		if len(c.Errors) > 0 {
			for _, e := range c.Errors {
				log.Printf("[GIN] Error: %v", e.Err)
			}
		}
	}
}
