package middleware

import (
	"log"
	"net"
	"net/http"
	"runtime/debug"

	"ai-law-assistant/internal/dto/response"
	"ai-law-assistant/internal/pkg/errcode"

	"github.com/gin-gonic/gin"
)

// Recovery Panic恢复中间件
func Recovery() gin.HandlerFunc {
	return func(c *gin.Context) {
		defer func() {
			if err := recover(); err != nil {
				// 检查是否是断开的连接
				var brokenPipe bool
				if ne, ok := err.(*net.OpError); ok {
					if se, ok := ne.Err.(*net.OpError); ok {
						if se.Op == "write" {
							brokenPipe = true
						}
					}
				}

				stack := string(debug.Stack())
				log.Printf("[RECOVERY] panic recovered:\n%s\n%s", err, stack)

				if brokenPipe {
					c.Error(err.(error))
					c.Abort()
					return
				}

				response.Error(c, http.StatusInternalServerError, errcode.CodeInternalError)
			}
		}()
		c.Next()
	}
}
