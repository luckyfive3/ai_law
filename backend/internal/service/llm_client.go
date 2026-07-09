package service

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

// LLMClient 大模型调用封装
type LLMClient struct {
	baseURL     string
	apiKey      string
	model       string
	temperature float64
	maxTokens   int
	timeout     time.Duration
	client      *http.Client
}

type LLMConfig struct {
	BaseURL     string
	APIKey      string
	Model       string
	Temperature float64
	MaxTokens   int
	Timeout     time.Duration
}

func NewLLMClient(cfg LLMConfig) *LLMClient {
	return &LLMClient{
		baseURL:     cfg.BaseURL,
		apiKey:      cfg.APIKey,
		model:       cfg.Model,
		temperature: cfg.Temperature,
		maxTokens:   cfg.MaxTokens,
		timeout:     cfg.Timeout,
		client: &http.Client{
			Timeout: cfg.Timeout,
		},
	}
}

// ChatMessage 消息结构
type ChatMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// ChatCompletionRequest 非流式请求
type chatCompletionRequest struct {
	Model       string        `json:"model"`
	Messages    []ChatMessage `json:"messages"`
	Temperature float64       `json:"temperature"`
	MaxTokens   int           `json:"max_tokens"`
	Stream      bool          `json:"stream"`
}

// ChatCompletionResponse 非流式响应
type ChatCompletionResponse struct {
	ID      string `json:"id"`
	Choices []struct {
		Message ChatMessage `json:"message"`
	} `json:"choices"`
	Usage struct {
		PromptTokens     int `json:"prompt_tokens"`
		CompletionTokens int `json:"completion_tokens"`
		TotalTokens      int `json:"total_tokens"`
	} `json:"usage"`
}

// Generate 非流式调用大模型
func (c *LLMClient) Generate(ctx context.Context, messages []ChatMessage) (*ChatCompletionResponse, error) {
	reqBody := chatCompletionRequest{
		Model:       c.model,
		Messages:    messages,
		Temperature: c.temperature,
		MaxTokens:   c.maxTokens,
		Stream:      false,
	}

	jsonBody, err := json.Marshal(reqBody)
	if err != nil {
		return nil, fmt.Errorf("marshal request: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost,
		c.baseURL+"/chat/completions", bytes.NewReader(jsonBody))
	if err != nil {
		return nil, fmt.Errorf("create request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+c.apiKey)

	resp, err := c.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("call llm: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("llm api error: status=%d body=%s", resp.StatusCode, string(body))
	}

	var result ChatCompletionResponse
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("unmarshal response: %w", err)
	}

	return &result, nil
}

// StreamResponse SSE流式响应行
type StreamResponse struct {
	ID      string `json:"id"`
	Choices []struct {
		Delta struct {
			Content string `json:"content"`
		} `json:"delta"`
		FinishReason string `json:"finish_reason"`
	} `json:"choices"`
}

// GenerateStream 流式调用大模型，返回 channel
func (c *LLMClient) GenerateStream(ctx context.Context, messages []ChatMessage) (<-chan *StreamResponse, <-chan error) {
	respChan := make(chan *StreamResponse, 100)
	errChan := make(chan error, 1)

	go func() {
		defer close(respChan)
		defer close(errChan)

		reqBody := chatCompletionRequest{
			Model:       c.model,
			Messages:    messages,
			Temperature: c.temperature,
			MaxTokens:   c.maxTokens,
			Stream:      true,
		}

		jsonBody, err := json.Marshal(reqBody)
		if err != nil {
			errChan <- fmt.Errorf("marshal request: %w", err)
			return
		}

		req, err := http.NewRequestWithContext(ctx, http.MethodPost,
			c.baseURL+"/chat/completions", bytes.NewReader(jsonBody))
		if err != nil {
			errChan <- fmt.Errorf("create request: %w", err)
			return
		}
		req.Header.Set("Content-Type", "application/json")
		req.Header.Set("Authorization", "Bearer "+c.apiKey)
		req.Header.Set("Accept", "text/event-stream")

		resp, err := c.client.Do(req)
		if err != nil {
			errChan <- fmt.Errorf("call llm stream: %w", err)
			return
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			body, _ := io.ReadAll(resp.Body)
			errChan <- fmt.Errorf("llm api error: status=%d body=%s", resp.StatusCode, string(body))
			return
		}

		// 读取 SSE 行
		decoder := json.NewDecoder(resp.Body)
		for {
			select {
			case <-ctx.Done():
				return
			default:
			}

			// SSE 格式: data: {...}\n\n
			// 简化为逐行 JSON 解析
			var streamResp StreamResponse
			if err := decoder.Decode(&streamResp); err != nil {
				if err == io.EOF {
					return
				}
				// 非致命错误继续读取
				continue
			}

			select {
			case respChan <- &streamResp:
			case <-ctx.Done():
				return
			}

			// 检查是否结束
			if len(streamResp.Choices) > 0 && streamResp.Choices[0].FinishReason == "stop" {
				return
			}
		}
	}()

	return respChan, errChan
}

// GetFallbackMessage 获取兜底回复
func GetFallbackMessage() string {
	return "抱歉，服务暂时繁忙，请稍后再试。如您有紧急法律问题，建议直接咨询执业律师。"
}
