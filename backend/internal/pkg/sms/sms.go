package sms

import (
	"fmt"
	"math/rand"
	"time"
)

// Service 短信服务接口（生产环境对接阿里云/腾讯云短信SDK）
type Service struct {
	// 生产环境配置: accessKey, secret, signName, templateCode
}

func NewService() *Service {
	return &Service{}
}

// GenerateCode 生成6位数字验证码
func GenerateCode() string {
	rng := rand.New(rand.NewSource(time.Now().UnixNano()))
	return fmt.Sprintf("%06d", rng.Intn(1000000))
}

// SendCode 发送短信验证码
// 开发环境仅打印日志，生产环境调用云短信API
func (s *Service) SendCode(phone, code string) error {
	// TODO: 对接阿里云/腾讯云短信服务
	// 开发环境直接输出到日志
	fmt.Printf("[SMS] Send code '%s' to phone '%s'\n", code, phone)
	return nil
}
