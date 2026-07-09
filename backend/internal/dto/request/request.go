package request

// RegisterRequest 注册请求
type RegisterRequest struct {
	Username        string `json:"username" binding:"required,min=2,max=50"`
	Password        string `json:"password" binding:"required,min=6,max=100"`
	ConfirmPassword string `json:"confirm_password" binding:"required"`
	AgreeTerms      bool   `json:"agree_terms" binding:"required"`
}

// LoginRequest 登录请求
type LoginRequest struct {
	Username   string `json:"username" binding:"required"`
	Password   string `json:"password" binding:"required"`
	AgreeTerms bool   `json:"agree_terms" binding:"required"`
}

// RefreshTokenRequest 刷新Token请求
type RefreshTokenRequest struct {
	RefreshToken string `json:"refresh_token" binding:"required"`
}

// CreateSessionRequest 创建会话请求
type CreateSessionRequest struct {
	Title    string `json:"title"`
	Category string `json:"category"`
}

// ChatStreamRequest 发送消息请求
type ChatStreamRequest struct {
	SessionID int64  `json:"session_id" binding:"required"`
	Content   string `json:"content" binding:"required,max=2000"`
	Category  string `json:"category"`
}

// UpdateProfileRequest 更新个人信息请求
type UpdateProfileRequest struct {
	Nickname  string `json:"nickname" binding:"max=50"`
	AvatarURL string `json:"avatar_url" binding:"max=500"`
}

// UpdatePrivacyRequest 更新隐私设置请求
type UpdatePrivacyRequest struct {
	PrivacySaveHistory bool `json:"privacy_save_history"`
}

// SearchKnowledgeRequest 知识库搜索请求
type SearchKnowledgeRequest struct {
	Keyword  string `json:"keyword" form:"keyword" binding:"required"`
	Page     int    `json:"page" form:"page"`
	PageSize int    `json:"page_size" form:"page_size"`
}

// PaginationRequest 分页请求
type PaginationRequest struct {
	Page     int `form:"page" json:"page"`
	PageSize int `form:"page_size" json:"page_size"`
}

func (p *PaginationRequest) Normalize() {
	if p.Page <= 0 {
		p.Page = 1
	}
	if p.PageSize <= 0 || p.PageSize > 50 {
		p.PageSize = 20
	}
}

func (p *PaginationRequest) Offset() int {
	return (p.Page - 1) * p.PageSize
}
