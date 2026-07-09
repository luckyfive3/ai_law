package repository

import (
	"context"
	"time"

	"ai-law-assistant/internal/model"

	"gorm.io/gorm"
)

type UserRepo struct {
	db *gorm.DB
}

func NewUserRepo(db *gorm.DB) *UserRepo {
	return &UserRepo{db: db}
}

func (r *UserRepo) Create(ctx context.Context, user *model.User) error {
	return r.db.WithContext(ctx).Create(user).Error
}

func (r *UserRepo) FindByPhoneHash(ctx context.Context, phoneHash string) (*model.User, error) {
	var user model.User
	err := r.db.WithContext(ctx).Where("phone_hash = ? AND status = 1", phoneHash).First(&user).Error
	if err != nil {
		return nil, err
	}
	return &user, nil
}

func (r *UserRepo) FindByUsername(ctx context.Context, username string) (*model.User, error) {
	var user model.User
	err := r.db.WithContext(ctx).Where("username = ? AND status = 1", username).First(&user).Error
	if err != nil {
		return nil, err
	}
	return &user, nil
}

func (r *UserRepo) FindByID(ctx context.Context, id int64) (*model.User, error) {
	var user model.User
	err := r.db.WithContext(ctx).Where("id = ? AND status = 1", id).First(&user).Error
	if err != nil {
		return nil, err
	}
	return &user, nil
}

func (r *UserRepo) Update(ctx context.Context, user *model.User) error {
	return r.db.WithContext(ctx).Save(user).Error
}

func (r *UserRepo) UpdateProfile(ctx context.Context, id int64, nickname, avatarURL string) error {
	return r.db.WithContext(ctx).Model(&model.User{}).
		Where("id = ?", id).
		Updates(map[string]interface{}{
			"nickname":   nickname,
			"avatar_url": avatarURL,
			"updated_at": time.Now(),
		}).Error
}

func (r *UserRepo) UpdatePrivacy(ctx context.Context, id int64, saveHistory bool) error {
	return r.db.WithContext(ctx).Model(&model.User{}).
		Where("id = ?", id).
		Updates(map[string]interface{}{
			"privacy_save_history": saveHistory,
			"updated_at":           time.Now(),
		}).Error
}
