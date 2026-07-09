package service

import (
	"context"
	"fmt"

	"ai-law-assistant/internal/dto/response"
)

// KnowledgeService 知识库服务
type KnowledgeService struct {
	searchClient *SearchClient
}

func NewKnowledgeService(searchClient *SearchClient) *KnowledgeService {
	return &KnowledgeService{
		searchClient: searchClient,
	}
}

// GetCategories 获取法律分类树
func (s *KnowledgeService) GetCategories(_ context.Context) []response.LawCategory {
	return []response.LawCategory{
		{ID: 1, Name: "婚姻家庭"},
		{ID: 2, Name: "劳动纠纷"},
		{ID: 3, Name: "合同纠纷"},
		{ID: 4, Name: "交通事故"},
		{ID: 5, Name: "房产纠纷"},
		{ID: 6, Name: "消费维权"},
	}
}

// SearchResult 搜索返回项
type SearchResultItem struct {
	ID       int
	LawName  string
	Category string
	LawText  string
	ArticleNum string
}

// SearchResults 搜索结果
type SearchResults struct {
	Items []SearchResultItem
	Count int
}

// Search 关键词搜索法条
func (s *KnowledgeService) Search(ctx context.Context, keyword string, page, pageSize int) (*SearchResults, error) {
	// 调用检索服务
	result, err := s.searchClient.Search(ctx, keyword, "")
	if err != nil {
		// 检索失败时返回模拟数据作为降级
		return s.fallbackSearch(keyword), nil
	}

	items := make([]SearchResultItem, 0)
	for i, r := range result.Results {
		items = append(items, SearchResultItem{
			ID:         i + 1,
			LawName:    r.LawName,
			Category:   r.Category,
			LawText:    r.LawText,
			ArticleNum: r.ArticleNum,
		})
	}

	return &SearchResults{
		Items: items,
		Count: result.Total,
	}, nil
}

// GetLawDetail 获取法条详情
func (s *KnowledgeService) GetLawDetail(ctx context.Context, lawID string) (*response.LawDetail, error) {
	// 查询法条
	result, err := s.searchClient.Search(ctx, lawID, "")
	if err != nil || len(result.Results) == 0 {
		return nil, fmt.Errorf("法条不存在")
	}

	law := result.Results[0]
	detail := &response.LawDetail{
		ID:   1,
		Name: law.LawName,
		Year: law.Source,
		Articles: []response.LawArticle{
			{
				Num:     law.ArticleNum,
				Content: law.LawText,
			},
		},
	}

	return detail, nil
}

// fallbackSearch 检索服务不可用时的降级搜索
func (s *KnowledgeService) fallbackSearch(keyword string) *SearchResults {
	// 内置法律数据库作为降级
	builtinLaws := []SearchResultItem{
		{ID: 1, LawName: "中华人民共和国宪法", Category: "constitution", LawText: "国家根本法，规定国家根本制度和根本任务"},
		{ID: 2, LawName: "中华人民共和国民法典", Category: "civil", LawText: "调整平等主体之间的人身关系和财产关系"},
		{ID: 3, LawName: "中华人民共和国刑法", Category: "criminal", LawText: "规定犯罪、刑事责任和刑罚的法律"},
		{ID: 4, LawName: "中华人民共和国劳动法", Category: "labor", LawText: "调整劳动关系及与劳动关系密切联系的其他社会关系"},
		{ID: 5, LawName: "中华人民共和国劳动合同法", Category: "labor", LawText: "规范劳动合同的订立、履行、变更、解除和终止"},
		{ID: 6, LawName: "中华人民共和国道路交通安全法", Category: "traffic", LawText: "维护道路交通秩序，预防和减少交通事故"},
		{ID: 7, LawName: "中华人民共和国消费者权益保护法", Category: "consumer", LawText: "保护消费者合法权益，维护社会经济秩序"},
		{ID: 8, LawName: "中华人民共和国反家庭暴力法", Category: "marriage", LawText: "预防和制止家庭暴力，保护家庭成员的合法权益"},
	}

	var matched []SearchResultItem
	for _, law := range builtinLaws {
		if contains(law.LawName, keyword) || contains(law.LawText, keyword) {
			matched = append(matched, law)
		}
	}

	if len(matched) == 0 {
		matched = builtinLaws
	}

	return &SearchResults{
		Items: matched,
		Count: len(matched),
	}
}
