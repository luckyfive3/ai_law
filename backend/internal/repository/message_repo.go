package repository

import (
	"context"

	"ai-law-assistant/internal/model"

	"gorm.io/gorm"
)

type MessageRepo struct {
	db *gorm.DB
}

func NewMessageRepo(db *gorm.DB) *MessageRepo {
	return &MessageRepo{db: db}
}

func (r *MessageRepo) Create(ctx context.Context, msg *model.Message) error {
	return r.db.WithContext(ctx).Create(msg).Error
}

func (r *MessageRepo) FindByID(ctx context.Context, id int64) (*model.Message, error) {
	var msg model.Message
	err := r.db.WithContext(ctx).
		Where("id = ? AND status = 1", id).
		First(&msg).Error
	if err != nil {
		return nil, err
	}
	return &msg, nil
}

func (r *MessageRepo) FindBySessionID(ctx context.Context, sessionID int64, offset, limit int) ([]model.Message, int64, error) {
	var messages []model.Message
	var total int64

	query := r.db.WithContext(ctx).Model(&model.Message{}).
		Where("session_id = ? AND status = 1", sessionID)

	if err := query.Count(&total).Error; err != nil {
		return nil, 0, err
	}

	err := query.Order("created_at ASC").
		Offset(offset).Limit(limit).
		Find(&messages).Error
	if err != nil {
		return nil, 0, err
	}
	return messages, total, nil
}

// GetRecentMessages 获取会话最近N条消息（用于上下文拼接）
func (r *MessageRepo) GetRecentMessages(ctx context.Context, sessionID int64, limit int) ([]model.Message, error) {
	var messages []model.Message
	err := r.db.WithContext(ctx).
		Where("session_id = ? AND status = 1", sessionID).
		Order("created_at DESC").
		Limit(limit).
		Find(&messages).Error
	if err != nil {
		return nil, err
	}
	// 反转顺序（从旧到新）
	for i, j := 0, len(messages)-1; i < j; i, j = i+1, j-1 {
		messages[i], messages[j] = messages[j], messages[i]
	}
	return messages, nil
}

func (r *MessageRepo) SoftDelete(ctx context.Context, id int64) error {
	return r.db.WithContext(ctx).Model(&model.Message{}).
		Where("id = ?", id).
		Update("status", 0).Error
}
