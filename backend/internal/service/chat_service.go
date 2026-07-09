package service

import (
	"context"
	"fmt"
	"time"

	"ai-law-assistant/internal/dto/response"
	"ai-law-assistant/internal/middleware"
	"ai-law-assistant/internal/model"
	"ai-law-assistant/internal/pkg/crypto"
	"ai-law-assistant/internal/repository"
)

type ChatService struct {
	messageRepo    *repository.MessageRepo
	sessionRepo    *repository.SessionRepo
	lawRefRepo     *repository.LawRefRepo
	auditRepo      *repository.AuditRepo
	tokenRepo      *repository.TokenRepo
	searchClient   *SearchClient
	llmClient      *LLMClient
	contextBuilder *ContextBuilder
	safetyFilter   *SafetyFilter
	contentSafety  *middleware.ContentSafety
}

func NewChatService(
	messageRepo *repository.MessageRepo,
	sessionRepo *repository.SessionRepo,
	lawRefRepo *repository.LawRefRepo,
	auditRepo *repository.AuditRepo,
	tokenRepo *repository.TokenRepo,
	searchClient *SearchClient,
	llmClient *LLMClient,
	contextBuilder *ContextBuilder,
	safetyFilter *SafetyFilter,
	contentSafety *middleware.ContentSafety,
) *ChatService {
	return &ChatService{
		messageRepo:    messageRepo,
		sessionRepo:    sessionRepo,
		lawRefRepo:     lawRefRepo,
		auditRepo:      auditRepo,
		tokenRepo:      tokenRepo,
		searchClient:   searchClient,
		llmClient:      llmClient,
		contextBuilder: contextBuilder,
		safetyFilter:   safetyFilter,
		contentSafety:  contentSafety,
	}
}

// ChatContext 对话上下文
type ChatContext struct {
	UserID    int64
	SessionID int64
	Query     string
	Category  string
	ClientIP  string
}

// ChatResult 对话结果
type ChatResult struct {
	UserMessage  *model.Message
	AIMessage    *model.Message
	LawRefs      []response.LawRefInfo
	StreamChunk  chan *response.SSEChunk
	InputTokens  int
	OutputTokens int
}

// SendMessage 发送消息并获取流式回复
func (s *ChatService) SendMessage(ctx context.Context, chatCtx *ChatContext) (*ChatResult, error) {
	// 1. 内容安全检查
	if !s.contentSafety.Check(chatCtx.Query) {
		s.logAudit(ctx, chatCtx.UserID, chatCtx.ClientIP, "block_query", "message", 0, "敏感内容: "+truncate(chatCtx.Query, 100))
		return nil, fmt.Errorf("内容包含敏感信息")
	}

	// 2. 保存用户消息
	userMsg := &model.Message{
		SessionID:   chatCtx.SessionID,
		Role:        "user",
		Content:     chatCtx.Query,
		ContentType: "text",
		Status:      1,
	}
	if err := s.messageRepo.Create(ctx, userMsg); err != nil {
		return nil, fmt.Errorf("save user message: %w", err)
	}

	// 3. 更新会话计数
	s.sessionRepo.IncrementMsgCount(ctx, chatCtx.SessionID)

	// 4. 调用检索服务
	searchResults, err := s.searchClient.Search(ctx, chatCtx.Query, chatCtx.Category)
	if err != nil {
		searchResults = &SearchResponse{Results: []SearchResult{}}
	}

	// 5. 获取历史消息
	historyMsgs, _ := s.messageRepo.GetRecentMessages(ctx, chatCtx.SessionID, 6)
	var historyForContext []HistoryMessage
	for _, m := range historyMsgs {
		historyForContext = append(historyForContext, HistoryMessage{
			Role:    m.Role,
			Content: m.Content,
		})
	}

	// 6. 拼接上下文
	systemPrompt := s.safetyFilter.SystemPrompt()
	legalContext := s.contextBuilder.BuildContext(chatCtx.Query, historyForContext, searchResults.Results)

	messages := []ChatMessage{
		{Role: "system", Content: systemPrompt},
		{Role: "user", Content: legalContext},
	}

	// 7. 调用大模型流式
	streamChan, errChan := s.llmClient.GenerateStream(ctx, messages)

	chunkChan := make(chan *response.SSEChunk, 100)
	result := &ChatResult{
		UserMessage: userMsg,
		StreamChunk: chunkChan,
	}

	// 8. 异步处理流式输出
	go func() {
		defer close(chunkChan)

		var fullContent string
		index := 0

		// "思考中"状态 → 前端 chat.js 识别 event:thinking + data.status==="searching"
		select {
		case chunkChan <- &response.SSEChunk{Status: "searching", Index: 0}:
		case <-ctx.Done():
			return
		}

		for {
			select {
			case streamResp, ok := <-streamChan:
				if !ok {
					goto finish
				}
				if len(streamResp.Choices) > 0 {
					token := streamResp.Choices[0].Delta.Content
					if token != "" {
						fullContent += token
						select {
						case chunkChan <- &response.SSEChunk{Content: token, Index: index, Status: "generating"}:
							index++
						case <-ctx.Done():
							return
						}
					}
					if streamResp.Choices[0].FinishReason == "stop" {
						goto finish
					}
				}
			case err := <-errChan:
				if err != nil {
					fallback := GetFallbackMessage()
					fullContent = fallback
					select {
					case chunkChan <- &response.SSEChunk{Content: fallback, Index: 0, Status: "generating"}:
					default:
					}
					goto finish
				}
				goto finish
			case <-ctx.Done():
				return
			}
		}

	finish:
		// 9. 后处理 + 保存
		if fullContent == "" {
			fullContent = GetFallbackMessage()
		}
		fullContent = s.safetyFilter.AppendDisclaimer(fullContent)

		// 保存AI消息
		aiMsg := &model.Message{
			SessionID:   chatCtx.SessionID,
			Role:        "assistant",
			Content:     fullContent,
			ContentType: "markdown",
			Status:      1,
		}
		s.messageRepo.Create(ctx, aiMsg)

		// 转换为前端兼容的法条引用格式 (name/article/text)
		lawRefs := make([]response.LawRefInfo, 0)
		for _, r := range searchResults.Results {
			lawRef := response.LawRefInfo{
				Name:     r.LawName,
				Article:  r.ArticleNum,
				Text:     r.LawText,
				Source:   r.Source,
				ChunkID:  r.ChunkID,
				Relevance: r.Relevance,
			}
			// 保存到数据库
			s.lawRefRepo.Create(ctx, &model.MessageLawRef{
				MessageID:  aiMsg.ID,
				LawName:    r.LawName,
				ArticleNum: r.ArticleNum,
				LawText:    r.LawText,
				Source:     r.Source,
				ChunkID:    r.ChunkID,
				Relevance:  r.Relevance,
			})
			lawRefs = append(lawRefs, lawRef)
		}

		// 记录Token消耗
		inputTokens := 500
		outputTokens := len(fullContent) / 2
		s.tokenRepo.Create(ctx, &model.TokenUsage{
			UserID:       chatCtx.UserID,
			SessionID:    chatCtx.SessionID,
			MessageID:    aiMsg.ID,
			Model:        "deepseek-chat",
			InputTokens:  inputTokens,
			OutputTokens: outputTokens,
		})

		// 发送完成事件 → 前端 chat.js 识别 done=true + message_id + laws + tokens
		select {
		case chunkChan <- &response.SSEChunk{
			Done:      true,
			Status:    "done",
			MessageID: aiMsg.ID,
			Laws:      lawRefs,
			Tokens: &response.TokenInfo{
				Input:  inputTokens,
				Output: outputTokens,
			},
		}:
		default:
		}
	}()

	return result, nil
}

// GetMessages 获取会话消息列表（含法条引用）
func (s *ChatService) GetMessages(ctx context.Context, sessionID int64, offset, limit int) ([]response.MessageInfo, int64, error) {
	messages, total, err := s.messageRepo.FindBySessionID(ctx, sessionID, offset, limit)
	if err != nil {
		return nil, 0, err
	}

	var result []response.MessageInfo
	for _, m := range messages {
		msg := response.MessageInfo{
			ID:        m.ID,
			Role:      m.Role,
			Content:   m.Content,
			Tokens:    m.Tokens,
			CreatedAt: m.CreatedAt.Format("2006-01-02T15:04:05Z"),
		}

		// 加载法条引用
		if m.Role == "assistant" {
			refs, _ := s.lawRefRepo.FindByMessageID(ctx, m.ID)
			for _, r := range refs {
				msg.LawRefs = append(msg.LawRefs, response.LawRefInfo{
					Name:     r.LawName,
					Article:  r.ArticleNum,
					Text:     r.LawText,
					Source:   r.Source,
					ChunkID:  r.ChunkID,
					Relevance: r.Relevance,
				})
			}
		}

		result = append(result, msg)
	}

	return result, total, nil
}

// ExportMessages 导出对话为文本
func (s *ChatService) ExportMessages(ctx context.Context, sessionID int64) (string, error) {
	messages, _, err := s.messageRepo.FindBySessionID(ctx, sessionID, 0, 200)
	if err != nil {
		return "", err
	}

	var export string
	for _, msg := range messages {
		role := "用户"
		if msg.Role == "assistant" {
			role = "AI法律助手"
		}
		export += fmt.Sprintf("【%s】%s\n", role, msg.CreatedAt.Format(time.DateTime))
		export += fmt.Sprintf("%s\n\n", msg.Content)
	}
	return export, nil
}

func (s *ChatService) logAudit(ctx context.Context, userID int64, ip string, action, targetType string, targetID int64, detail string) {
	s.auditRepo.Create(ctx, &model.AuditLog{
		UserID:     userID,
		Action:     action,
		TargetType: targetType,
		TargetID:   targetID,
		Detail:     detail,
		IP:         ip,
	})
}

func truncate(s string, maxLen int) string {
	runes := []rune(s)
	if len(runes) <= maxLen {
		return s
	}
	return string(runes[:maxLen]) + "..."
}

// MaskPhoneForExport 脱敏手机号
func MaskPhoneForExport(phone string) string {
	return crypto.MaskPhone(phone)
}
