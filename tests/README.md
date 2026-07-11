# AI法律助手 v1.0 — 测试文档

---

## 一、项目概述

AI法律助手是一套基于 **FastAPI + MongoDB + RAGFlow + DeepSeek LLM** 的法律咨询平台，采用前后端分离架构。

| 层 | 技术栈 | 端口 |
|---|--------|------|
| 后端 API | Python FastAPI + Motor (MongoDB async) | 8080 |
| 前端 | Python FastAPI + Jinja2 模板渲染 | 3000 |
| 数据库 | MongoDB | 27017 |
| 检索 | RAGFlow SDK | 外部服务 |
| LLM | DeepSeek (via LangChain) | 外部 API |

---

## 二、测试策略

### 2.1 测试金字塔

```
         /\
        /E2E\          Playwright 浏览器自动化 — 19 条用户流程
       /------\
      /  集成   \       pytest + FastAPI TestClient — 61 条 API 场景
     /----------\
    / 前端单测  \      vitest + jsdom — 50 条 JS 模块
   /------------\
  /   后端单测   \     pytest + unittest.mock — 280 条 service/util/schema
 /--------------\
```

### 2.2 各层职责

| 层级 | 工具 | 覆盖目标 | 不覆盖 |
|------|------|---------|--------|
| **单元测试** | pytest + MagicMock | 所有 service/util 的纯逻辑 | 网络 I/O、数据库 |
| **集成测试** | pytest + httpx + mongomock | 所有 API 端点的请求/响应 | 外部服务(RAGFlow/LLM) |
| **E2E** | Playwright | 关键用户流程 | 边界异常 |

### 2.3 运行方式

```bash
# 安装测试依赖
pip install pytest pytest-asyncio pytest-cov mongomock httpx
npm install

# 后端单元测试
cd backend
python -m pytest tests/unit/ -v

# 前端单元测试
npx vitest run tests/frontend-unit/

# 集成测试
python -m pytest tests/integration/ -v

# E2E 测试（需要前后端都启动）
python -m pytest tests/e2e/ -v

# 全部后端测试 + 覆盖率
python -m pytest tests/ --cov=. --cov-report=html -v
```

### 2.4 环境要求

| 测试层级 | MongoDB | 后端运行 | 前端运行 | RAGFlow | DeepSeek |
|---------|---------|---------|---------|---------|----------|
| 单元 | 不需要 | 不需要 | 不需要 | 不需要 | 不需要 |
| 集成 | mongomock | 不需要 | 不需要 | Mock | Mock |
| E2E | 需要 | 需要 | 需要 | 需要 | 需要 |

---

## 三、单元测试用例清单

### 3.1 错误码模块 (`test_errcode.py`)

| 用例ID | 场景 | 预期 |
|--------|------|------|
| UT-ERR-01 | get_message 返回已知错误码消息 | 正确中文消息 |
| UT-ERR-02 | get_message 未知错误码 | "未知错误" |
| UT-ERR-03 | 所有已定义错误码都有对应消息 | 无遗漏 |

### 3.2 JWT 工具 (`test_jwt_utils.py`)

| 用例ID | 场景 | 预期 |
|--------|------|------|
| UT-JWT-01 | create_access_token 生成有效token | 可解码出 user_id/username |
| UT-JWT-02 | create_refresh_token 含 type=refresh | payload 中 type="refresh" |
| UT-JWT-03 | decode_token 正常解码 | 返回完整 payload |
| UT-JWT-04 | decode_token 过期token | jwt.ExpiredSignatureError |
| UT-JWT-05 | decode_token 错误密钥 | jwt.InvalidTokenError |
| UT-JWT-06 | decode_token 篡改token | jwt.InvalidTokenError |

### 3.3 安全过滤 (`test_safety_filter.py`)

| 用例ID | 场景 | 预期 |
|--------|------|------|
| UT-SF-01 | system_prompt 返回非空字符串 | 包含"AI法律助手" |
| UT-SF-02 | should_refuse 含"拒答"关键词 | True |
| UT-SF-03 | should_refuse 不含关键词 | False |
| UT-SF-04 | should_refuse enable=False | 始终 False |
| UT-SF-05 | refuse_answer 返回拒答话术 | 含"超出范围" |
| UT-SF-06 | append_disclaimer 附加声明 | 含"免责声明" |
| UT-SF-07 | get_fallback_message 返回兜底 | 含"稍后再试" |

### 3.4 上下文构建 (`test_context_builder.py`)

| 用例ID | 场景 | 预期 |
|--------|------|------|
| UT-CB-01 | 只有用户问题无历史无法条 | 仅含用户问题段落 |
| UT-CB-02 | 含历史对话 | 含"[历史对话]"段落 |
| UT-CB-03 | 含检索结果 | 含"[相关法律依据]"段落 |
| UT-CB-04 | 完整上下文 | 三段都有 |
| UT-CB-05 | 历史超过max_history_rounds | 截断到最近N轮 |
| UT-CB-06 | max_history_rounds=0 | 自动修正为1 |
| UT-CB-07 | 法条结果含条款号和法条原文 | 格式化含条款号 |

### 3.5 认证服务 (`test_auth_service.py`)

| 用例ID | 场景 | 预期 |
|--------|------|------|
| UT-AS-01 | register 新用户成功 | 返回 user + tokens |
| UT-AS-02 | register 用户名已存在 | ValueError |
| UT-AS-03 | register 用户名过短(<3) | ValueError |
| UT-AS-04 | register 密码过短(<6) | ValueError |
| UT-AS-05 | login 正确凭据 | 返回 tokens |
| UT-AS-06 | login 错误密码 | ValueError |
| UT-AS-07 | login 不存在用户 | ValueError |
| UT-AS-08 | login 已禁用(status!=1) | ValueError |
| UT-AS-09 | refresh_token 有效 | 返回新 tokens |
| UT-AS-10 | refresh_token access类型token | ValueError |
| UT-AS-11 | refresh_token 过期 | ValueError |

### 3.6 知识库服务 (`test_knowledge_service.py`)

| 用例ID | 场景 | 预期 |
|--------|------|------|
| UT-KS-01 | get_categories 返回8个分类 | 列表含"宪法""民法""刑法"等 |
| UT-KS-02 | fallback_search 关键词匹配名称 | 返回匹配法律 |
| UT-KS-03 | fallback_search 关键词匹配内容 | 返回含该关键词的法条 |
| UT-KS-04 | fallback_search 无匹配 | 返回所有法律摘要(兜底) |
| UT-KS-05 | search 缓存命中 | 直接返回缓存 |

---

## 四、前端单元测试用例清单

### 4.1 工具函数 (`utils.test.js`)

| 用例ID | 场景 | 预期 |
|--------|------|------|
| FE-UT-01 | escapeHtml 转义 & | `&amp;` |
| FE-UT-02 | escapeHtml 转义 <> | `&lt;` `&gt;` |
| FE-UT-03 | escapeHtml 转义引号 | `&quot;` `&#39;` |
| FE-UT-04 | escapeHtml 空值处理 | 返回空字符串 |
| FE-UT-05 | escapeHtml XSS 防护 | 不执行 script |
| FE-UT-06 | formatTime 刚刚 | 小于1分钟 → "刚刚" |
| FE-UT-07 | formatTime X分钟前 | 5分钟前 → "5分钟前" |
| FE-UT-08 | formatTime X小时前 | 2小时前 → "2小时前" |
| FE-UT-09 | formatTime 跨年显示 | 含完整年份 |
| FE-UT-10 | formatDate 今天/昨天 | 相对日期正确 |
| FE-UT-11 | formatDate 较早日期 | "2023年1月15日" |
| FE-UT-12 | simpleMarkdown 粗体/斜体 | `<strong>` `<em>` |
| FE-UT-13 | simpleMarkdown 标题 | `<h3>` `<h4>` |
| FE-UT-14 | simpleMarkdown 代码块 | `<pre><code>` |
| FE-UT-15 | simpleMarkdown 链接 | `<a target="_blank">` |
| FE-UT-16 | simpleMarkdown 列表/引用 | `<ul>` `<blockquote>` |
| FE-UT-17 | simpleMarkdown XSS 防护 | script 标签被转义 |

### 4.2 鉴权状态管理 (`auth.test.js`)

| 用例ID | 场景 | 预期 |
|--------|------|------|
| FE-UT-18 | Auth 初始未登录 | isLoggedIn=false |
| FE-UT-19 | login 设置 token | token 和 user 存入 localStorage |
| FE-UT-20 | logout 清除状态 | token/user 清空 |
| FE-UT-21 | requireLogin 已登录 | 返回 true |
| FE-UT-22 | requireLogin 未登录 | 返回跳转URL |
| FE-UT-23 | init 恢复登录态 | 从 localStorage 恢复 |
| FE-UT-24 | 防抖搜索 400ms | 只触发最后一次 |

### 4.3 法律数据库 (`data-sse.test.js`)

| 用例ID | 场景 | 预期 |
|--------|------|------|
| FE-UT-25 | LAWS_DATA 非空 | 数组长度 > 0 |
| FE-UT-26 | 每条记录含必要字段 | id/name/category/articles |
| FE-UT-27 | id 唯一 | 无重复 |
| FE-UT-28 | SSE searching | 解析 status=searching |
| FE-UT-29 | SSE generating | 解析 content 字段 |
| FE-UT-30 | SSE done | 解析 tokens 统计 |
| FE-UT-31 | SSE error | 解析错误事件 |
| FE-UT-32 | SSE 流式多token | 拼接后 = "根据民法典" |
| FE-UT-33 | SSE 忽略非data行 | event: ping 被跳过 |
| FE-UT-34 | SSE 容忍坏JSON | 不崩溃 |

---

## 五、集成测试用例清单

### 4.1 认证 API (`test_auth_api.py`)

| 用例ID | 端点 | 场景 | 预期 |
|--------|------|------|------|
| IT-AUTH-01 | POST /auth/register | 正常注册 | 200, 返回token+用户信息 |
| IT-AUTH-02 | POST /auth/register | 密码不一致 | 400 |
| IT-AUTH-03 | POST /auth/register | 不同意协议 | 400 |
| IT-AUTH-04 | POST /auth/register | 用户名为空 | 422 |
| IT-AUTH-05 | POST /auth/login | 正常登录 | 200, 返回token |
| IT-AUTH-06 | POST /auth/login | 错误密码 | 401 |
| IT-AUTH-07 | POST /auth/refresh | 有效refresh_token | 200 |
| IT-AUTH-08 | POST /auth/refresh | 无效token | 401 |
| IT-AUTH-09 | POST /auth/logout | 正常退出 | 200 |

### 4.2 用户 API (`test_user_api.py`)

| 用例ID | 端点 | 场景 | 预期 |
|--------|------|------|------|
| IT-USER-01 | GET /user/profile | 已认证 | 200, 返回用户信息 |
| IT-USER-02 | GET /user/profile | 无Token | 401 |
| IT-USER-03 | PUT /user/profile | 更新昵称 | 200 |
| IT-USER-04 | PUT /user/profile | 空字段 | 400 |
| IT-USER-05 | PUT /user/privacy | 更新隐私设置 | 200 |

### 4.3 会话 API (`test_session_api.py`)

| 用例ID | 端点 | 场景 | 预期 |
|--------|------|------|------|
| IT-SESS-01 | POST /sessions | 创建会话 | 200, 返回session |
| IT-SESS-02 | GET /sessions | 获取列表 | 200, 含分页 |
| IT-SESS-03 | GET /sessions/{id} | 获取详情 | 200, 含messages |
| IT-SESS-04 | GET /sessions/{id} | 不存在的ID | 404 |
| IT-SESS-05 | DELETE /sessions/{id} | 删除会话 | 200 |
| IT-SESS-06 | DELETE /sessions/clear-all | 清空全部 | 200 |

### 4.4 知识库 API (`test_knowledge_api.py`)

| 用例ID | 端点 | 场景 | 预期 |
|--------|------|------|------|
| IT-KB-01 | GET /knowledge/documents | 获取文档列表 | 200 |
| IT-KB-02 | GET /knowledge/categories | 获取分类 | 200, 8个分类 |
| IT-KB-03 | GET /knowledge/search?keyword=劳动 | 搜索 | 200, 含items |
| IT-KB-04 | GET /knowledge/search | 无keyword | 422 |
| IT-KB-05 | GET /knowledge/laws/{id} | 存在 | 200, 含chunks |
| IT-KB-06 | GET /knowledge/laws/{id} | 不存在 | 404 |

### 4.5 聊天 API (`test_chat_api.py`)

| 用例ID | 端点 | 场景 | 预期 |
|--------|------|------|------|
| IT-CHAT-01 | POST /chat/stream | SSE 流式对话 | 200, text/event-stream |
| IT-CHAT-02 | POST /chat/stream | 空content | 422 |
| IT-CHAT-03 | GET /chat/{id}/messages | 获取消息 | 200, 含分页 |
| IT-CHAT-04 | GET /chat/{id}/export | 导出消息 | 200, text/plain |

---

## 六、E2E 测试用例清单

| 用例ID | 流程 | 步骤 | 验证点 |
|--------|------|------|--------|
| E2E-01 | 注册→登录 | 打开/login → 注册 → 登录 | 跳转到首页 |
| E2E-02 | 新建对话 | 登录 → 新建会话 → 发送消息 | 收到AI回复 |
| E2E-03 | 历史浏览 | 登录 → 进入历史 → 查看某条 | 显示历史消息 |
| E2E-04 | 知识库浏览 | 访问/knowledge → 点击某法律 | 显示法条详情 |
| E2E-05 | 个人中心 | 登录 → 进入/profile → 改昵称 | 昵称更新成功 |
| E2E-06 | 免责声明 | 访问/disclaimer | 页面正常显示 |

---

## 七、预期覆盖率目标

| 模块 | 行覆盖率 | 分支覆盖率 |
|------|---------|-----------|
| utils/ | ≥90% | ≥85% |
| services/ (不含外部调用) | ≥80% | ≥70% |
| api/ | ≥70% | — |
| middleware/ | ≥60% | — |

---

## 八、测试执行结果 (2026-07-11 最终版)

### 总体统计

| 层级 | 测试数 | 通过 | 失败 |
|------|--------|------|------|
| 后端单元测试 | 280 | 280 | 0 |
| 前端单元测试 | 50 | 50 | 0 |
| 集成测试 | 61 | 61 | 0 |
| E2E | 19 | 19 | 0 |
| **合计** | **410** | **410** | **0** |

### 单元测试覆盖详情

| 模块 | 测试文件 | 用例数 |
|------|---------|--------|
| 错误码 | `test_errcode.py` | 4 |
| JWT 工具 | `test_jwt_utils.py` | 8 |
| 安全过滤 | `test_safety_filter.py` | 9 |
| 上下文构建 | `test_context_builder.py` | 9 |
| 认证服务 | `test_auth_service.py` | 15 |
| 知识库服务 | `test_knowledge_service.py` | 8 |
| LLM 服务 v1 | `test_llm_service.py` | 11 |
| LLM 服务 v2 | `test_llm_service_v2.py` | 14 |
| RAGFlow 客户端 | `test_ragflow_client.py` | 10 |
| 会话服务 | `test_session_service.py` | 12 |
| 用户服务 | `test_user_service.py` | 13 |
| 聊天服务 | `test_chat_service.py` | 11 |
| 摘要与画像服务 | `test_summary_service.py` | 19 |
| Pydantic Schemas | `test_schemas.py` | 22 |
| 加密工具 | `test_crypto_utils.py` | 13 |
| 输出解析器 | `test_output_parser.py` | 11 |
| LangChain Retriever | `test_langchain_retriever.py` | 8 |
| LangChain Callbacks | `test_langchain_callbacks.py` | 13 |
| RAG Chain | `test_rag_chain.py` | 8 |
| Prompts | `test_prompts.py` | 6 |
| 中间件 Auth | `test_middleware_auth.py` | 10 |
| 中间件 ContentSafety | `test_middleware_content_safety.py` | 10 |
| 中间件 Logger | `test_middleware_logger.py` | 7 |
| 中间件 RateLimiter/CORS | `test_middleware_ratelimit_cors.py` | 4 |

### 集成测试覆盖详情

| API 模块 | 测试文件 | 用例数 | 覆盖场景 |
|---------|---------|--------|---------|
| 认证 API | `test_auth_api.py` | 11 | 注册/登录/刷新/退出 |
| 用户 API | `test_user_api.py` | 8 | 资料/隐私 |
| 会话 API | `test_session_api.py` | 10 | 创建/列表/详情/删除/清空 |
| 知识库 API | `test_knowledge_api.py` | 7 | 文档/分类/搜索/详情 |
| 聊天 API | `test_chat_api.py` | 9 | 流式/消息/导出 |
| 摘要与画像 API | `test_summary_api.py` | 15 | 摘要查询/生成/画像/上下文 |
| 健康检查 | 同上 | 1 | /health |

### 本次更新的修复

- **`schemas/response.py`**: `success_response` 新增 `message` 参数支持（修复 `api/summary.py` TypeError）

### 执行命令

```bash
# 单元测试
python -m pytest tests/unit/ -v

# 集成测试
python -m pytest tests/integration/ -v

# 全部测试（不含 E2E）
python -m pytest tests/unit/ tests/integration/ -v
```
