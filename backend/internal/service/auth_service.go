package service

import (
	"context"
	"errors"
	"fmt"
	"log"

	"ai-law-assistant/internal/config"
	"ai-law-assistant/internal/model"
	"ai-law-assistant/internal/pkg/errcode"
	"ai-law-assistant/internal/pkg/jwt"
	"ai-law-assistant/internal/repository"

	"golang.org/x/crypto/bcrypt"
	"gorm.io/gorm"
)

// 预定义错误，供 Handler 层做类型判断
var (
	ErrUsernameExists = errors.New("username_exists")
)

type AuthService struct {
	config     *config.Config
	jwtManager *jwt.Manager
	userRepo   *repository.UserRepo
}

func NewAuthService(
	cfg *config.Config,
	userRepo *repository.UserRepo,
) *AuthService {
	return &AuthService{
		config:     cfg,
		jwtManager: jwt.NewManager(cfg.JWT.Secret, cfg.JWT.AccessTTL, cfg.JWT.RefreshTTL),
		userRepo:   userRepo,
	}
}

// Register 用户注册
func (s *AuthService) Register(ctx context.Context, username, password string) (*model.User, error) {
	// 检查用户名是否已存在
	existing, err := s.userRepo.FindByUsername(ctx, username)
	if err == nil && existing != nil {
		return nil, ErrUsernameExists
	}
	if err != nil && !errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, fmt.Errorf("check username: %w", err)
	}

	// 密码哈希
	passwordHash, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
	if err != nil {
		return nil, fmt.Errorf("hash password: %w", err)
	}

	user := &model.User{
		Username:     username,
		PasswordHash: string(passwordHash),
		Nickname:     username,
		Status:       1,
	}
	if err := s.userRepo.Create(ctx, user); err != nil {
		return nil, fmt.Errorf("create user: %w", err)
	}

	log.Printf("[INFO] User registered: %s (id=%d)", username, user.ID)
	return user, nil
}

// Login 用户名密码登录
func (s *AuthService) Login(ctx context.Context, username, password string) (*model.User, error) {
	user, err := s.userRepo.FindByUsername(ctx, username)
	if err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, fmt.Errorf(errcode.GetMessage(errcode.CodeInvalidCredentials))
		}
		return nil, fmt.Errorf("find user: %w", err)
	}

	// 验证密码
	if err := bcrypt.CompareHashAndPassword([]byte(user.PasswordHash), []byte(password)); err != nil {
		return nil, fmt.Errorf(errcode.GetMessage(errcode.CodeInvalidCredentials))
	}

	log.Printf("[INFO] User logged in: %s (id=%d)", username, user.ID)
	return user, nil
}

// GenerateTokens 生成 Access Token 和 Refresh Token
func (s *AuthService) GenerateTokens(user *model.User) (string, string, error) {
	accessToken, err := s.jwtManager.GenerateAccessToken(user.ID, user.Username)
	if err != nil {
		return "", "", fmt.Errorf("generate access token: %w", err)
	}

	refreshToken, err := s.jwtManager.GenerateRefreshToken(user.ID, user.Username)
	if err != nil {
		return "", "", fmt.Errorf("generate refresh token: %w", err)
	}

	return accessToken, refreshToken, nil
}

// RefreshToken 刷新Token
func (s *AuthService) RefreshToken(refreshTokenStr string) (string, string, error) {
	claims, err := s.jwtManager.ParseToken(refreshTokenStr)
	if err != nil {
		return "", "", fmt.Errorf(errcode.GetMessage(errcode.CodeRefreshTokenInvalid))
	}

	accessToken, refreshToken, err := s.GenerateTokens(&model.User{
		ID:       claims.UserID,
		Username: claims.Username,
	})
	if err != nil {
		return "", "", err
	}

	return accessToken, refreshToken, nil
}

// GetJWTManager 获取 JWT Manager（用于中间件）
func (s *AuthService) GetJWTManager() *jwt.Manager {
	return s.jwtManager
}
