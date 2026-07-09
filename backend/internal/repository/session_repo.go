package repository

import (
	"context"
	"time"

	"ai-law-assistant/internal/model"

	"gorm.io/gorm"
)

type SessionRepo struct {
	db *gorm.DB
}

func NewSessionRepo(db *gorm.DB) *SessionRepo {
	return &SessionRepo{db: db}
}

func (r *SessionRepo) Create(ctx context.Context, session *model.Session) error {
	return r.db.WithContext(ctx).Create(session).Error
}

func (r *SessionRepo) FindByID(ctx context.Context, id int64) (*model.Session, error) {
	var session model.Session
	err := r.db.WithContext(ctx).
		Where("id = ? AND status = 1", id).
		First(&session).Error
	if err != nil {
		return nil, err
	}
	return &session, nil
}

func (r *SessionRepo) FindByUserID(ctx context.Context, userID int64, offset, limit int) ([]model.Session, int64, error) {
	var sessions []model.Session
	var total int64

	query := r.db.WithContext(ctx).Model(&model.Session{}).
		Where("user_id = ? AND status = 1", userID)

	if err := query.Count(&total).Error; err != nil {
		return nil, 0, err
	}

	err := query.Order("updated_at DESC").
		Offset(offset).Limit(limit).
		Find(&sessions).Error
	if err != nil {
		return nil, 0, err
	}
	return sessions, total, nil
}

func (r *SessionRepo) Update(ctx context.Context, session *model.Session) error {
	return r.db.WithContext(ctx).Save(session).Error
}

func (r *SessionRepo) SoftDelete(ctx context.Context, id, userID int64) error {
	return r.db.WithContext(ctx).Model(&model.Session{}).
		Where("id = ? AND user_id = ?", id, userID).
		Updates(map[string]interface{}{
			"status":     0,
			"updated_at": time.Now(),
		}).Error
}

// SoftDeleteAllByUser 软删除用户的所有会话
func (r *SessionRepo) SoftDeleteAllByUser(ctx context.Context, userID int64) error {
	return r.db.WithContext(ctx).Model(&model.Session{}).
		Where("user_id = ? AND status = 1", userID).
		Updates(map[string]interface{}{
			"status":     0,
			"updated_at": time.Now(),
		}).Error
}

func (r *SessionRepo) IncrementMsgCount(ctx context.Context, id int64) error {
	return r.db.WithContext(ctx).Model(&model.Session{}).
		Where("id = ?", id).
		Updates(map[string]interface{}{
			"msg_count":  gorm.Expr("msg_count + 1"),
			"updated_at": time.Now(),
		}).Error
}
