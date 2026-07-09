package repository

import (
	"context"
	"time"

	"ai-law-assistant/internal/model"

	"gorm.io/gorm"
)

type AuditRepo struct {
	db *gorm.DB
}

func NewAuditRepo(db *gorm.DB) *AuditRepo {
	return &AuditRepo{db: db}
}

func (r *AuditRepo) Create(ctx context.Context, log *model.AuditLog) error {
	return r.db.WithContext(ctx).Create(log).Error
}

type TokenRepo struct {
	db *gorm.DB
}

func NewTokenRepo(db *gorm.DB) *TokenRepo {
	return &TokenRepo{db: db}
}

func (r *TokenRepo) Create(ctx context.Context, usage *model.TokenUsage) error {
	return r.db.WithContext(ctx).Create(usage).Error
}

func (r *TokenRepo) FindByUserAndDate(ctx context.Context, userID int64, date time.Time) ([]model.TokenUsage, error) {
	var usages []model.TokenUsage
	err := r.db.WithContext(ctx).
		Where("user_id = ? AND DATE(created_at) = DATE(?)", userID, date).
		Find(&usages).Error
	return usages, err
}

type SMSRepo struct {
	db *gorm.DB
}

func NewSMSRepo(db *gorm.DB) *SMSRepo {
	return &SMSRepo{db: db}
}

func (r *SMSRepo) Create(ctx context.Context, sms *model.SMSCode) error {
	return r.db.WithContext(ctx).Create(sms).Error
}

func (r *SMSRepo) FindLatestByPhone(ctx context.Context, phone string) (*model.SMSCode, error) {
	var sms model.SMSCode
	err := r.db.WithContext(ctx).
		Where("phone = ? AND used = false AND expires_at > ?", phone, time.Now()).
		Order("created_at DESC").
		First(&sms).Error
	if err != nil {
		return nil, err
	}
	return &sms, nil
}

func (r *SMSRepo) MarkUsed(ctx context.Context, id int64) error {
	return r.db.WithContext(ctx).Model(&model.SMSCode{}).
		Where("id = ?", id).
		Update("used", true).Error
}
