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

// SearchClient 检索服务调用客户端
type SearchClient struct {
	baseURL string
	timeout time.Duration
	topK    int
	client  *http.Client
}

type SearchConfig struct {
	BaseURL string
	Timeout time.Duration
	TopK    int
}

// SearchResult 检索结果
type SearchResult struct {
	ChunkID   string  `json:"chunk_id"`
	LawName   string  `json:"law_name"`
	ArticleNum string `json:"article_num"`
	LawText   string  `json:"law_text"`
	Source    string  `json:"source"`
	Relevance float64 `json:"relevance"`
	Category  string  `json:"category"`
}

// SearchResponse 检索响应
type SearchResponse struct {
	Results []SearchResult `json:"results"`
	Total   int            `json:"total"`
}

func NewSearchClient(cfg SearchConfig) *SearchClient {
	return &SearchClient{
		baseURL: cfg.BaseURL,
		timeout: cfg.Timeout,
		topK:    cfg.TopK,
		client: &http.Client{
			Timeout: cfg.Timeout,
		},
	}
}

// Search 调用检索服务
func (c *SearchClient) Search(ctx context.Context, query string, category string) (*SearchResponse, error) {
	reqBody := map[string]interface{}{
		"query":    query,
		"top_k":    c.topK,
		"category": category,
	}

	jsonBody, err := json.Marshal(reqBody)
	if err != nil {
		return nil, fmt.Errorf("marshal search request: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost,
		c.baseURL+"/internal/search", bytes.NewReader(jsonBody))
	if err != nil {
		return nil, fmt.Errorf("create search request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("call search service: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read search response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("search service error: status=%d body=%s", resp.StatusCode, string(body))
	}

	var result SearchResponse
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("unmarshal search response: %w", err)
	}

	return &result, nil
}
