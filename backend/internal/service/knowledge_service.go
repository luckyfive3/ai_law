package service

import (
	"context"
	"fmt"
	"strings"

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
		{ID: 1, Name: "宪法"},
		{ID: 2, Name: "民法"},
		{ID: 3, Name: "刑法"},
		{ID: 4, Name: "劳动法"},
		{ID: 5, Name: "婚姻家庭"},
		{ID: 6, Name: "交通法"},
		{ID: 7, Name: "消费者权益"},
		{ID: 8, Name: "房产法"},
	}
}

// BuiltinLaw 内置法律摘要
type BuiltinLaw struct {
	ID           int
	Name         string
	Category     string
	Year         string
	Summary      string
	ArticleCount int
}

// getBuiltinLaws 获取完整的内置法律列表
func getBuiltinLaws() []BuiltinLaw {
	return []BuiltinLaw{
		{ID: 1, Name: "中华人民共和国宪法", Category: "constitution", Year: "1982年", Summary: "国家根本法，规定国家根本制度和根本任务", ArticleCount: 134},
		{ID: 2, Name: "中华人民共和国民法典", Category: "civil", Year: "2020年5月28日颁布", Summary: "调整平等主体之间的人身关系和财产关系", ArticleCount: 1109},
		{ID: 3, Name: "中华人民共和国刑法", Category: "criminal", Year: "2020年修正", Summary: "规定犯罪、刑事责任和刑罚的法律", ArticleCount: 561},
		{ID: 4, Name: "中华人民共和国劳动法", Category: "labor", Year: "2018年修正", Summary: "调整劳动关系及与劳动关系密切联系的其他社会关系", ArticleCount: 109},
		{ID: 5, Name: "中华人民共和国劳动合同法", Category: "labor", Year: "2012年修正", Summary: "规范劳动合同的订立、履行、变更、解除和终止", ArticleCount: 126},
		{ID: 6, Name: "中华人民共和国消费者权益保护法", Category: "consumer", Year: "2013年修正", Summary: "保护消费者合法权益，维护社会经济秩序", ArticleCount: 65},
		{ID: 7, Name: "中华人民共和国反家庭暴力法", Category: "marriage", Year: "2015年", Summary: "预防和制止家庭暴力，保护家庭成员的合法权益", ArticleCount: 39},
		{ID: 8, Name: "中华人民共和国未成年人保护法", Category: "civil", Year: "2024年修正", Summary: "保护未成年人身心健康，保障未成年人合法权益", ArticleCount: 147},
		{ID: 9, Name: "中华人民共和国监察法", Category: "constitution", Year: "2024年修正", Summary: "深化国家监察体制改革，加强对所有行使公权力的公职人员的监督", ArticleCount: 81},
		{ID: 10, Name: "中华人民共和国商标法", Category: "civil", Year: "2026年修正", Summary: "加强商标管理，保护商标专用权", ArticleCount: 129},
		{ID: 11, Name: "中华人民共和国城市房地产管理法", Category: "housing", Year: "2019年修正", Summary: "加强对城市房地产的管理，维护房地产市场秩序", ArticleCount: 82},
		{ID: 12, Name: "中华人民共和国国防交通法", Category: "constitution", Year: "2016年", Summary: "加强国防交通建设，促进交通领域军民融合发展", ArticleCount: 60},
		{ID: 13, Name: "婚姻登记条例", Category: "marriage", Year: "2025年", Summary: "规范婚姻登记工作，保障婚姻自由、一夫一妻、男女平等的婚姻制度实施", ArticleCount: 31},
	}
}

// SearchResult 搜索返回项
type SearchResultItem struct {
	ID         int
	LawName    string
	Category   string
	LawText    string
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
		// 检索失败时返回降级数据
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
		// 搜索失败，返回降级数据
		return s.fallbackDetail(lawID)
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

// fallbackDetail 法条详情降级返回
func (s *KnowledgeService) fallbackDetail(lawID string) (*response.LawDetail, error) {
	builtinLaws := getBuiltinLaws()
	for _, law := range builtinLaws {
		if strings.Contains(law.Name, lawID) || fmt.Sprintf("%d", law.ID) == lawID {
			return &response.LawDetail{
				ID:   law.ID,
				Name: law.Name,
				Year: law.Year,
				Articles: []response.LawArticle{
					{
						Num:     "一",
						Content: law.Summary,
					},
				},
			}, nil
		}
	}

	return nil, fmt.Errorf("法条不存在")
}

// fallbackSearch 检索服务不可用时的降级搜索
func (s *KnowledgeService) fallbackSearch(keyword string) *SearchResults {
	// 内置法律数据库作为降级
	builtinLaws := getBuiltinLaws()
	var matched []SearchResultItem

	for _, law := range builtinLaws {
		keywordLower := strings.ToLower(keyword)
		nameLower := strings.ToLower(law.Name)
		summaryLower := strings.ToLower(law.Summary)

		if strings.Contains(nameLower, keywordLower) || strings.Contains(summaryLower, keywordLower) {
			matched = append(matched, SearchResultItem{
				ID:         law.ID,
				LawName:    law.Name,
				Category:   law.Category,
				LawText:    law.Summary,
				ArticleNum: "",
			})
		}
	}

	if len(matched) == 0 {
		// 未匹配时返回全部
		for _, law := range builtinLaws {
			matched = append(matched, SearchResultItem{
				ID:         law.ID,
				LawName:    law.Name,
				Category:   law.Category,
				LawText:    law.Summary,
				ArticleNum: "",
			})
		}
	}

	return &SearchResults{
		Items: matched,
		Count: len(matched),
	}
}
