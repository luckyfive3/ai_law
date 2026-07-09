package service

import (
	"fmt"
	"strings"
)

// ContextBuilder 上下文拼接
type ContextBuilder struct {
	maxHistoryRounds int // 最大历史对话轮数
}

func NewContextBuilder(maxHistoryRounds int) *ContextBuilder {
	if maxHistoryRounds <= 0 {
		maxHistoryRounds = 3
	}
	return &ContextBuilder{
		maxHistoryRounds: maxHistoryRounds,
	}
}

// BuildContext 构建完整的 Prompt 上下文
func (b *ContextBuilder) BuildContext(
	userQuery string,
	historyMessages []HistoryMessage,
	searchResults []SearchResult,
) string {
	var sb strings.Builder

	// 1. 历史对话
	if len(historyMessages) > 0 {
		sb.WriteString("[历史对话]\n")
		// 只取最近N轮（每轮 = user + assistant）
		start := len(historyMessages) - b.maxHistoryRounds*2
		if start < 0 {
			start = 0
		}
		for _, msg := range historyMessages[start:] {
			if msg.Role == "user" {
				sb.WriteString(fmt.Sprintf("用户问：%s\n", msg.Content))
			} else {
				sb.WriteString(fmt.Sprintf("AI答：%s\n", msg.Content))
			}
		}
		sb.WriteString("\n")
	}

	// 2. 检索到的法条
	if len(searchResults) > 0 {
		sb.WriteString("[相关法律依据]\n")
		for i, result := range searchResults {
			sb.WriteString(fmt.Sprintf("%d. 《%s》%s\n", i+1, result.LawName, result.ArticleNum))
			sb.WriteString(fmt.Sprintf("   原文：%s\n", result.LawText))
			sb.WriteString(fmt.Sprintf("   来源：%s\n", result.Source))
		}
		sb.WriteString("\n")
	}

	// 3. 用户当前问题
	sb.WriteString(fmt.Sprintf("[用户问题]\n%s\n", userQuery))

	return sb.String()
}

// HistoryMessage 历史消息（简化版，用于上下文拼接）
type HistoryMessage struct {
	Role    string
	Content string
}
