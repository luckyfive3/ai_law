package middleware

import (
	"context"
	"fmt"
	"net/http"
	"time"

	"ai-law-assistant/internal/dto/response"
	"ai-law-assistant/internal/pkg/errcode"

	"github.com/gin-gonic/gin"
	"github.com/redis/go-redis/v9"
)

// RateLimiter 限流中间件
type RateLimiter struct {
	redis *redis.Client
}

func NewRateLimiter(rdb *redis.Client) *RateLimiter {
	return &RateLimiter{redis: rdb}
}

// UserMessageRateLimit 每用户每分钟消息发送限制
func (rl *RateLimiter) UserMessageRateLimit(limitPerMinute int) gin.HandlerFunc {
	return func(c *gin.Context) {
		userID := GetUserID(c)
		key := fmt.Sprintf("rate:user:%d:minute", userID)

		count, err := rl.redis.Incr(c.Request.Context(), key).Result()
		if err != nil {
			// Redis 不可用时降级放行
			c.Next()
			return
		}

		if count == 1 {
			rl.redis.Expire(c.Request.Context(), key, 60*time.Second)
		}

		if count > int64(limitPerMinute) {
			response.Error(c, http.StatusTooManyRequests, errcode.CodeRateLimited)
			return
		}
		c.Next()
	}
}

// IPRateLimit 每IP每分钟请求限制
func (rl *RateLimiter) IPRateLimit(limitPerMinute int) gin.HandlerFunc {
	return func(c *gin.Context) {
		ip := c.ClientIP()
		key := fmt.Sprintf("rate:ip:%s:minute", ip)

		count, err := rl.redis.Incr(context.Background(), key).Result()
		if err != nil {
			c.Next()
			return
		}

		if count == 1 {
			rl.redis.Expire(context.Background(), key, 60*time.Second)
		}

		if count > int64(limitPerMinute) {
			response.Error(c, http.StatusTooManyRequests, errcode.CodeRateLimited)
			return
		}
		c.Next()
	}
}

// CheckSMSLimit 检查短信发送频率限制（60秒内不可重发）
func (rl *RateLimiter) CheckSMSLimit(phone string) (bool, error) {
	key := fmt.Sprintf("sms:limit:%s", phone)
	exists, err := rl.redis.Exists(context.Background(), key).Result()
	if err != nil {
		return false, err
	}
	return exists == 0, nil
}

// SetSMSLimit 设置短信频率限制标记
func (rl *RateLimiter) SetSMSLimit(phone string) error {
	key := fmt.Sprintf("sms:limit:%s", phone)
	return rl.redis.Set(context.Background(), key, 1, 60*time.Second).Err()
}

// SetSMSCode 缓存验证码（5分钟有效期）
func (rl *RateLimiter) SetSMSCode(phone, code string) error {
	key := fmt.Sprintf("sms:code:%s", phone)
	return rl.redis.Set(context.Background(), key, code, 5*time.Minute).Err()
}

// GetSMSCode 获取缓存的验证码
func (rl *RateLimiter) GetSMSCode(phone string) (string, error) {
	key := fmt.Sprintf("sms:code:%s", phone)
	return rl.redis.Get(context.Background(), key).Result()
}
