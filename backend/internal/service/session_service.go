package service

import (
	"context"

	"ai-law-assistant/internal/model"
	"ai-law-assistant/internal/repository"

	"gorm.io/gorm"
)

type SessionService struct {
	sessionRepo *repository.SessionRepo
	messageRepo *repository.MessageRepo
}

func NewSessionService(sessionRepo *repository.SessionRepo, messageRepo *repository.MessageRepo) *SessionService {
	return &SessionService{
		sessionRepo: sessionRepo,
		messageRepo: messageRepo,
	}
}

// CreateSession 创建新会话
func (s *SessionService) CreateSession(ctx context.Context, userID int64, title, category string) (*model.Session, error) {
	if title == "" {
		title = "法律咨询"
	}
	if category == "" {
		category = "general"
	}
	session := &model.Session{
		UserID:   userID,
		Title:    title,
		Category: category,
		Status:   1,
	}
	if err := s.sessionRepo.Create(ctx, session); err != nil {
		return nil, err
	}
	return session, nil
}

// GetSessions 获取用户会话列表
func (s *SessionService) GetSessions(ctx context.Context, userID int64, offset, limit int) ([]model.Session, int64, error) {
	return s.sessionRepo.FindByUserID(ctx, userID, offset, limit)
}

// GetSessionDetail 获取会话详情（含消息列表）
func (s *SessionService) GetSessionDetail(ctx context.Context, sessionID, userID int64, offset, limit int) (*model.Session, []model.Message, int64, error) {
	session, err := s.sessionRepo.FindByID(ctx, sessionID)
	if err != nil {
		if err == gorm.ErrRecordNotFound {
			return nil, nil, 0, nil
		}
		return nil, nil, 0, err
	}

	// 权限校验：只能查看自己的会话
	if session.UserID != userID {
		return nil, nil, 0, nil
	}

	messages, total, err := s.messageRepo.FindBySessionID(ctx, sessionID, offset, limit)
	if err != nil {
		return nil, nil, 0, err
	}

	return session, messages, total, nil
}

// DeleteSession 删除会话（软删除）
func (s *SessionService) DeleteSession(ctx context.Context, sessionID, userID int64) error {
	return s.sessionRepo.SoftDelete(ctx, sessionID, userID)
}

// ClearAllSessions 清空用户全部历史会话
func (s *SessionService) ClearAllSessions(ctx context.Context, userID int64) error {
	return s.sessionRepo.SoftDeleteAllByUser(ctx, userID)
}
