package service

import (
	"context"
	"fmt"

	"ai-law-assistant/internal/model"
	"ai-law-assistant/internal/repository"
)

type UserService struct {
	userRepo *repository.UserRepo
}

func NewUserService(userRepo *repository.UserRepo) *UserService {
	return &UserService{userRepo: userRepo}
}

// GetProfile 获取用户个人信息
func (s *UserService) GetProfile(ctx context.Context, userID int64) (*model.User, error) {
	return s.userRepo.FindByID(ctx, userID)
}

// UpdateProfile 更新用户信息
func (s *UserService) UpdateProfile(ctx context.Context, userID int64, nickname, avatarURL string) error {
	if nickname == "" {
		return fmt.Errorf("昵称不能为空")
	}
	if len(nickname) > 50 {
		return fmt.Errorf("昵称长度不能超过50字")
	}
	return s.userRepo.UpdateProfile(ctx, userID, nickname, avatarURL)
}

// UpdatePrivacy 更新隐私设置
func (s *UserService) UpdatePrivacy(ctx context.Context, userID int64, saveHistory bool) error {
	return s.userRepo.UpdatePrivacy(ctx, userID, saveHistory)
}
