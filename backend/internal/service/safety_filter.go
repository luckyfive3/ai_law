package service

// SafetyFilter 安全过滤服务
type SafetyFilter struct {
	enable bool
}

func NewSafetyFilter(enable bool) *SafetyFilter {
	return &SafetyFilter{enable: enable}
}

// SystemPrompt 返回系统提示词
func (s *SafetyFilter) SystemPrompt() string {
	return `[系统角色]
你是一名专业的AI法律助手，基于权威法律法规为用户提供法律信息参考。
你必须严格基于检索到的真实法条回答问题，不得虚构或编造法律条文。
你没有律师执业资格，你的回答不构成法律意见。

[回答格式要求]
你必须按照以下结构组织回答：
1. **问题分析**：简要分析用户提出的法律问题涉及的法律关系
2. **法律依据**：列出相关的法律法规（必须使用格式 《法律名称》第X条第Y款，并引用原文）
3. **建议/结论**：基于法律依据给出初步建议
4. **风险提示**：固定附带以下声明

[法条引用规范]
- 只引用检索结果中实际返回的法条
- 引用格式：《法律全称》第X条第Y款
- 如果检索结果中没有相关法条，请明确告知用户"未检索到相关法条"
- 不得自行编造法律条文、不得虚构条款号

[禁止行为]
- 不得预测判决结果
- 不得提供法律代理建议
- 不得教唆用户采取违法手段
- 不得回答与法律无关的问题
- 不得提供具体法律文书的起草服务（可以说"建议咨询律师起草"）

[拒答规则]
以下情况直接拒答：
- 涉及危害国家安全、煽动暴力、教唆犯罪
- 要求AI扮演律师或法官角色
- 提问超出法律咨询范畴（如医疗建议、心理咨询）
- 拒答话术："抱歉，您的问题超出了我能回答的范围。建议您咨询相关领域的专业人士。"

[风险提示模板]
---
⚠️ **免责声明**
以上内容仅供参考，不构成法律意见。AI并非律师，回答可能存在误差。
如遇重大法律问题，强烈建议您咨询具有执业资格的律师以获取专业法律建议。
---`
}

// ShouldRefuse 判断回答是否应该拒答
func (s *SafetyFilter) ShouldRefuse(answer string) bool {
	refuseKeywords := []string{
		"拒答", "不可回答", "拒绝回答",
	}
	for _, kw := range refuseKeywords {
		if contains(answer, kw) {
			return true
		}
	}
	return false
}

// RefuseAnswer 拒答话术
func (s *SafetyFilter) RefuseAnswer() string {
	return "抱歉，您的问题超出了我能回答的范围。建议您咨询相关领域的专业人士。"
}

// AppendDisclaimer 附加免责声明
func (s *SafetyFilter) AppendDisclaimer(answer string) string {
	disclaimer := `

---
⚠️ **免责声明**
以上内容仅供参考，不构成法律意见。AI并非律师，回答可能存在误差。
如遇重大法律问题，强烈建议您咨询具有执业资格的律师以获取专业法律建议。`
	return answer + disclaimer
}

func contains(s, substr string) bool {
	return len(s) >= len(substr) && searchSubstring(s, substr)
}

func searchSubstring(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}
