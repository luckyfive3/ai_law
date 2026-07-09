package repository

import (
	"context"

	"ai-law-assistant/internal/model"

	"gorm.io/gorm"
)

type LawRefRepo struct {
	db *gorm.DB
}

func NewLawRefRepo(db *gorm.DB) *LawRefRepo {
	return &LawRefRepo{db: db}
}

func (r *LawRefRepo) Create(ctx context.Context, ref *model.MessageLawRef) error {
	return r.db.WithContext(ctx).Create(ref).Error
}

func (r *LawRefRepo) FindByMessageID(ctx context.Context, messageID int64) ([]model.MessageLawRef, error) {
	var refs []model.MessageLawRef
	err := r.db.WithContext(ctx).
		Where("message_id = ?", messageID).
		Find(&refs).Error
	if err != nil {
		return nil, err
	}
	return refs, nil
}
