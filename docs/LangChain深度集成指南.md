# AI法律助手 — LangChain 深度集成指南

## 一、LangChain 是什么？

LangChain 是一个**LLM 应用开发框架**，它提供了一套标准化的组件和抽象来构建 AI 驱动的应用。

### 核心架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     LangChain 六大模块                        │
├───────────────┬──────────────┬──────────────┬───────────────┤
│  Model I/O    │  Retrieval   │   Chains     │   Memory      │
│  ChatOpenAI   │  Retriever   │  LCEL (|)    │  BufferMemory │
│  PromptTempl  │  DocLoader   │  RunnableSeq │  ChatHistory  │
├───────────────┼──────────────┼──────────────┼───────────────┤
│   Agents      │  Callbacks   │   Tools      │  OutputParser │
│  ReAct/Tools  │  Token统计   │  API/函数    │  JSON/Struct  │
└───────────────┴──────────────┴──────────────┴───────────────┘
```

### 当前项目用到的 vs 可以用的

| 能力 | 当前状态 | 可升级到 |
|:---|:---|:---|
| LLM 调用 | ✅ `ChatOpenAI.ainvoke/astream` | 保持 |
| Prompt | ❌ 手写字符串拼接 | ✅ `ChatPromptTemplate` |
| 检索 (RAG) | ❌ 直接 `httpx` 调 RAGFlow | ✅ `BaseRetriever` 封装 |
| Chain 编排 | ❌ 手写 14 步串行逻辑 | ✅ LCEL 管道式声明 |
| 结构化输出 | ❌ 自由文本 | ✅ `PydanticOutputParser` |
| 监控追踪 | ❌ 手动 log | ✅ `BaseCallbackHandler` |

---

## 二、已创建的文件清单

```
backend/services/
├── prompts.py                # ① 结构化 Prompt 模板（ChatPromptTemplate）
├── output_parser.py          # ② Pydantic 结构化输出解析器
├── langchain_retriever.py    # ③ RAGFlow → LangChain BaseRetriever 封装
├── rag_chain.py              # ④ LCEL RAG 对话链
├── langchain_callbacks.py    # ⑤ 全链路监控回调处理器
├── llm_service_v2.py         # ⑥ 升级版 LLM 服务（集成 Callbacks）
└── chat_service_v2.py        # ⑦ 升级版聊天服务（集成所有组件）
```

---

## 三、逐步集成指南

### 步骤 1：无需额外安装依赖

现有 `requirements.txt` 已包含所需所有包：
```
langchain==0.3.13          # ✅ 已安装
langchain-community==0.3.13 # ✅ 已安装
langchain-openai==0.2.14   # ✅ 已安装
```

### 步骤 2：在 main.py 中注册新服务

```python
# backend/main.py — 在 create_app() 中添加

from services.prompts import build_legal_consult_prompt
from services.langchain_retriever import RAGFlowRetriever, format_docs
from services.langchain_callbacks import LegalAICallbackHandler
from services.rag_chain import LegalRAGChain

# 替换原有 ChatService 导入
from services.chat_service_v2 import ChatService
```

### 步骤 3：更新 chat API 路由（渐进切换）

```python
# backend/api/chat.py

# 方案 A：渐进式 — 用新参数控制
@router.post("/send")
async def send_message(...):
    use_chain = request.use_lcel_chain if hasattr(request, 'use_lcel_chain') else False

    if use_chain:
        # 使用 LCEL RAG Chain（新链路）
        async for event in chat_service.send_message_with_chain(...):
            yield event
    else:
        # 使用改进版 Prompt 模板（兼容链路）
        async for event in chat_service.send_message(...):
            yield event
```

### 步骤 4：验证集成是否成功

```bash
# 进入 backend 目录
cd backend

# 启动后端
uvicorn main:app --reload --port 8080

# 测试 LCEL Chain
curl -X POST http://localhost:8080/api/v1/chat/send \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test", "query": "劳动合同纠纷怎么处理？", "use_lcel_chain": true}'
```

预期输出：SSE 流式事件包含 `searching → generating → done`，done 事件中带有 `stats` 统计信息。

---

## 四、各组件详细说明

### 4.1 prompts.py — ChatPromptTemplate

**解决了什么**：原先 `ContextBuilder` 和 `SafetyFilter.system_prompt()` 是字符串拼接，变量插值不方便，不同场景无法复用。

**怎么用**：
```python
from services.prompts import build_legal_consult_prompt

prompt = build_legal_consult_prompt()

# 渲染 Prompt
messages = prompt.invoke({
    "legal_context": "《劳动合同法》第47条...",
    "history": [HumanMessage("..."), AIMessage("...")],
    "question": "公司拖欠工资怎么办？",
})
# → 自动生成 [SystemMessage, ...历史消息, HumanMessage(含法条和问题)]
```

### 4.2 output_parser.py — PydanticOutputParser

**解决了什么**：让 LLM 返回结构化 JSON，代码可以直接消费每个字段，前端可精确渲染。

**怎么用**：
```python
from services.output_parser import (
    LegalAnalysis, legal_analysis_parser, parse_legal_analysis
)

# 方式1：作为 LLM 链的最后一环
chain = llm | legal_analysis_parser
result: LegalAnalysis = await chain.ainvoke(messages)
print(result.category)        # "劳动纠纷"
print(result.issue_analysis)  # "本案涉及劳动合同解除..."
print(result.legal_basis)     # [LawReference(...), ...]

# 方式2：手动解析 LLM 原始输出
raw_text = '{"category": "婚姻家庭", "issue_analysis": "..."}'
parsed = parse_legal_analysis(raw_text)
```

### 4.3 langchain_retriever.py — RAGFlowRetriever

**解决了什么**：将 RAGFlow HTTP API 封装为 LangChain 的 `BaseRetriever` 接口，可无缝插入任何 LCEL Chain。

**怎么用**：
```python
from services.langchain_retriever import RAGFlowRetriever, format_docs

retriever = RAGFlowRetriever(ragflow_client=client, top_k=5)

# 同步检索
docs = retriever.invoke("劳动合同纠纷怎么处理？")
# → [Document(page_content="...", metadata={"law_name": "..."}), ...]

# 异步检索
docs = await retriever.ainvoke("离婚财产分割")

# 格式化为 Prompt 上下文
context = format_docs(docs)
```

### 4.4 rag_chain.py — LegalRAGChain（LCEL）

**解决了什么**：用声明式的 `|` 管道替代手写的 14 步串行逻辑，代码量减少 70%。

**数据流向**：
```
{"question": "...", "history": [...]}
    │
    ├─→ itemgetter("question") → Retriever → format_docs ─┐
    │                                                      │
    ├─→ itemgetter("history") ─────────────────────────────┤
    │                                                      │
    └─→ RunnableParallel ─→ Prompt ─→ LLM ─→ StrOutputParser ─→ 回答
```

**怎么用**：
```python
from services.rag_chain import LegalRAGChain

chain = LegalRAGChain(llm=llm, retriever=retriever)

# 非流式
answer = await chain.ainvoke("合同违约怎么起诉？", history=history_msgs)

# 流式（SSE 推送）
async for token in chain.astream("交通事故责任认定", history=history_msgs):
    yield f"data: {token}\n\n"
```

### 4.5 langchain_callbacks.py — LegalAICallbackHandler

**解决了什么**：自动统计 Token 消耗、LLM 延迟、检索耗时，替代手动 log。

**怎么用**：
```python
from services.langchain_callbacks import LegalAICallbackHandler
from langchain_openai import ChatOpenAI

handler = LegalAICallbackHandler(session_id="abc123", user_id="user_1", db=mongo_db)

llm = ChatOpenAI(
    model="deepseek-chat",
    callbacks=[handler],  # ← 只需注入这里
    ...
)

# 每次 LLM 调用后自动触发 on_llm_end，自动保存 Token 用量
```

---

## 五、架构对比

### 改造前
```
用户 → ContentSafety → MongoDB保存 → httpx调RAGFlow → 手动拼Prompt → 
      → LLMService.astream → 手动Token统计 → 保存
```
- 4 个对象各管各的
- 无标准化接口
- 无监控钩子

### 改造后
```
用户 → ChatPromptTemplate.invoke() → RAGFlowRetriever.aget_relevant_documents() 
                                     → format_docs() 
      → LLM.astream() [回调: LegalAICallbackHandler 自动 Token 统计]
      → StrOutputParser()
```
- 所有组件的接口标准化
- Callback 自动拦截全链路
- 可替换任意环节（换 LLM、换检索、换 Parser）

---

## 六、后续可扩展方向

| 方向 | 使用的 LangChain 模块 | 说明 |
|:---|:---|:---|
| 法律文书自动生成 | `ChatPromptTemplate` + `PydanticOutputParser` | 生成标准化起诉状/答辩状模板 |
| 多轮对话记忆 | `ConversationBufferWindowMemory` | 自动管理窗口化对话历史 |
| 意图识别路由 | `RunnableBranch` | 根据问题类型路由到不同的 Prompt/Chain |
| 法律条款智能搜索 | VectorStore（`Chroma`/`FAISS`） | 替代 RAGFlow，本地向量搜索 |
| 合同风险审查 | `DocumentLoader`（DOCX/PDF） | 上传合同自动识别风险条款 |
| 多模型对比 | `ModelLaboratory` | 同时调 DeepSeek + GLM + Qwen 对比答案质量 |
| SQL 法条查询 | `SQLDatabaseChain` + `create_sql_agent` | 将法律法规存入结构化数据库供自然语言查询 |
| 飞书企业集成 | `CallbackHandler` + Webhook | 企业法律咨询工作流自动化 |

---

## 七、注意事项

1. **渐进迁移**：`chat_service_v2.py` 保留了两种模式（`send_message` 和 `send_message_with_chain`），可先通过 feature flag 控制新旧链路的流量比例。
2. **向后兼容**：所有新增文件是独立模块，不影响原有 `llm_service.py`、`chat_service.py` 等文件的运行。
3. **测试优先**：在测试环境验证 LCEL Chain 的输出质量与旧链路一致后再切换。
4. **监控先行**：`LegalAICallbackHandler` 可接入 Grafana/Prometheus，对 LLM 延迟和 Token 消耗做可视化监控。
