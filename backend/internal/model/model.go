package model

import "time"

type User struct {
	ID                 int64     `gorm:"column:id;primaryKey;autoIncrement" json:"id"`
	Username           string    `gorm:"column:username;size:50;uniqueIndex;not null" json:"username"`
	PasswordHash       string    `gorm:"column:password_hash;size:255;not null" json:"-"`
	Phone              string    `gorm:"column:phone" json:"-"`
	PhoneHash          string    `gorm:"column:phone_hash" json:"-"`
	PhoneEncrypted     string    `gorm:"column:phone_encrypted" json:"-"`
	Nickname           string    `gorm:"column:nickname;default:法律助手用户" json:"nickname"`
	AvatarURL          string    `gorm:"column:avatar_url" json:"avatar_url"`
	PrivacySaveHistory bool      `gorm:"column:privacy_save_history;default:true" json:"privacy_save_history"`
	Status             int16     `gorm:"column:status;default:1" json:"status"`
	CreatedAt          time.Time `gorm:"column:created_at;autoCreateTime" json:"created_at"`
	UpdatedAt          time.Time `gorm:"column:updated_at;autoUpdateTime" json:"updated_at"`
}

func (User) TableName() string { return "users" }

type Session struct {
	ID        int64      `gorm:"column:id;primaryKey;autoIncrement" json:"id"`
	UserID    int64      `gorm:"column:user_id;not null;index" json:"user_id"`
	Title     string     `gorm:"column:title;default:法律咨询" json:"title"`
	Category  string     `gorm:"column:category" json:"category"`
	MsgCount  int        `gorm:"column:msg_count;default:0" json:"msg_count"`
	Status    int16      `gorm:"column:status;default:1" json:"status"`
	CreatedAt time.Time  `gorm:"column:created_at;autoCreateTime" json:"created_at"`
	UpdatedAt time.Time  `gorm:"column:updated_at;autoUpdateTime" json:"updated_at"`
}

func (Session) TableName() string { return "sessions" }

type Message struct {
	ID          int64     `gorm:"column:id;primaryKey;autoIncrement" json:"id"`
	SessionID   int64     `gorm:"column:session_id;not null;index" json:"session_id"`
	Role        string    `gorm:"column:role;not null" json:"role"` // "user" | "assistant"
	Content     string    `gorm:"column:content;not null" json:"content"`
	ContentType string    `gorm:"column:content_type;default:text" json:"content_type"` // "text" | "markdown"
	Tokens      int       `gorm:"column:tokens" json:"tokens"`
	IsStreaming bool      `gorm:"column:is_streaming;default:false" json:"is_streaming"`
	Status      int16     `gorm:"column:status;default:1" json:"status"`
	CreatedAt   time.Time `gorm:"column:created_at;autoCreateTime" json:"created_at"`
}

func (Message) TableName() string { return "messages" }

type MessageLawRef struct {
	ID        int64     `gorm:"column:id;primaryKey;autoIncrement" json:"id"`
	MessageID int64     `gorm:"column:message_id;not null;index" json:"message_id"`
	LawName   string    `gorm:"column:law_name;not null" json:"law_name"`
	ArticleNum string   `gorm:"column:article_num" json:"article_num"`
	LawText   string    `gorm:"column:law_text" json:"law_text"`
	Source    string    `gorm:"column:source" json:"source"`
	ChunkID   string    `gorm:"column:chunk_id" json:"chunk_id"`
	Relevance float64   `gorm:"column:relevance" json:"relevance"`
	CreatedAt time.Time `gorm:"column:created_at;autoCreateTime" json:"created_at"`
}

func (MessageLawRef) TableName() string { return "message_law_refs" }

type AuditLog struct {
	ID         int64     `gorm:"column:id;primaryKey;autoIncrement" json:"id"`
	UserID     int64     `gorm:"column:user_id;index" json:"user_id"`
	Action     string    `gorm:"column:action;not null" json:"action"`
	TargetType string    `gorm:"column:target_type;not null" json:"target_type"`
	TargetID   int64     `gorm:"column:target_id" json:"target_id"`
	Detail     string    `gorm:"column:detail" json:"detail"`
	OperatorID int64     `gorm:"column:operator_id" json:"operator_id"`
	IP         string    `gorm:"column:ip" json:"ip"`
	CreatedAt  time.Time `gorm:"column:created_at;autoCreateTime" json:"created_at"`
}

func (AuditLog) TableName() string { return "audit_logs" }

type TokenUsage struct {
	ID           int64     `gorm:"column:id;primaryKey;autoIncrement" json:"id"`
	UserID       int64     `gorm:"column:user_id;index" json:"user_id"`
	SessionID    int64     `gorm:"column:session_id;index" json:"session_id"`
	MessageID    int64     `gorm:"column:message_id" json:"message_id"`
	Model        string    `gorm:"column:model;not null" json:"model"`
	InputTokens  int       `gorm:"column:input_tokens;default:0" json:"input_tokens"`
	OutputTokens int       `gorm:"column:output_tokens;default:0" json:"output_tokens"`
	CreatedAt    time.Time `gorm:"column:created_at;autoCreateTime" json:"created_at"`
}

func (TokenUsage) TableName() string { return "token_usage" }

type SMSCode struct {
	ID        int64     `gorm:"column:id;primaryKey;autoIncrement" json:"id"`
	Phone     string    `gorm:"column:phone;not null" json:"-"`
	Code      string    `gorm:"column:code;not null" json:"-"`
	Used      bool      `gorm:"column:used;default:false" json:"used"`
	ExpiresAt time.Time `gorm:"column:expires_at;not null" json:"expires_at"`
	CreatedAt time.Time `gorm:"column:created_at;autoCreateTime" json:"created_at"`
}

func (SMSCode) TableName() string { return "sms_codes" }
