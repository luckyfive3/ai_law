package handler

import (
	"net/http"

	"ai-law-assistant/internal/dto/response"
	"ai-law-assistant/internal/pkg/errcode"
	"ai-law-assistant/internal/service"

	"github.com/gin-gonic/gin"
)

type KnowledgeHandler struct {
	knowledgeService *service.KnowledgeService
}

func NewKnowledgeHandler(knowledgeService *service.KnowledgeService) *KnowledgeHandler {
	return &KnowledgeHandler{knowledgeService: knowledgeService}
}

// GetCategories GET /api/v1/knowledge/categories
func (h *KnowledgeHandler) GetCategories(c *gin.Context) {
	categories := h.knowledgeService.GetCategories(c.Request.Context())
	response.Success(c, categories)
}

// Search GET /api/v1/knowledge/search?keyword=xxx&page=1&page_size=20
func (h *KnowledgeHandler) Search(c *gin.Context) {
	keyword := c.Query("keyword")
	if keyword == "" {
		response.Error(c, http.StatusBadRequest, errcode.CodeInvalidParam)
		return
	}

	page := 1
	pageSize := 20
	if p := c.Query("page"); p != "" {
		// simple parse
	}
	if ps := c.Query("page_size"); ps != "" {
		if n, ok := parseInt(ps); ok && n > 0 && n <= 50 {
			pageSize = n
		}
	}

	results, err := h.knowledgeService.Search(c.Request.Context(), keyword, page, pageSize)
	if err != nil {
		response.Error(c, http.StatusInternalServerError, errcode.CodeSearchError)
		return
	}

	// 转换响应
	var list []response.KnowledgeSearchResult
	for _, r := range results.Items {
		list = append(list, response.KnowledgeSearchResult{
			ID:       r.ID,
			Name:     r.LawName,
			Category: r.Category,
			Summary:  truncateSummary(r.LawText, 100),
		})
	}

	response.Paginated(c, list, int64(results.Count), page, pageSize)
}

// GetLawDetail GET /api/v1/knowledge/laws/:id
// 返回法条详情，匹配前端 knowledge_detail.html 期望的格式
func (h *KnowledgeHandler) GetLawDetail(c *gin.Context) {
	lawID := c.Param("id")

	detail, err := h.knowledgeService.GetLawDetail(c.Request.Context(), lawID)
	if err != nil {
		response.Error(c, http.StatusNotFound, errcode.CodeLawNotFound)
		return
	}

	response.Success(c, detail)
}

func parseInt(s string) (int, bool) {
	n := 0
	for _, c := range s {
		if c < '0' || c > '9' {
			return 0, false
		}
		n = n*10 + int(c-'0')
	}
	return n, true
}

func truncateSummary(text string, maxLen int) string {
	runes := []rune(text)
	if len(runes) <= maxLen {
		return text
	}
	return string(runes[:maxLen]) + "…"
}
