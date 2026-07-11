# AI 法律助手 (AI Law Assistant)

> 基于大模型 + RAG 的智能法律咨询服务，面向普通公众提供便捷、可靠的基础法律指导。

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-7.0-brightgreen.svg)](https://www.mongodb.com/)
[![LangChain](https://img.shields.io/badge/LangChain-0.3+-orange.svg)](https://www.langchain.com/)
[![RAGFlow](https://img.shields.io/badge/RAGFlow-v0.15.0-blueviolet.svg)](https://ragflow.io/)
[![License](https://img.shields.io/badge/License-MIT-lightgrey.svg)](./LICENSE)

---

## 📖 目录

- [项目简介](#项目简介)
- [技术架构](#技术架构)
- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [文档索引](#文档索引)
- [开发指南](#开发指南)
- [部署](#部署)

---

## 项目简介

AI 法律助手是一款面向普通公众的 **AI 智能法律咨询服务工具**。用户通过自然语言对话方式提出法律问题，系统基于权威法律知识库结合大模型生成专业、合规的法律建议回复。

### 覆盖领域

婚姻家庭 · 劳动纠纷 · 合同纠纷 · 交通事故 · 房产纠纷 · 消费维权

### ⚠️ 免责声明

本产品 AI 回答仅供参考，不构成法律意见。如遇重大法律问题，强烈建议咨询具有执业资格的律师。

---

## 技术架构

```
浏览器 → Nginx (HTTPS) → 前端 FastAPI SSR (:3000)
                              │
            API 代理 (/api/v1/proxy/*)
                              │
                    后端 FastAPI (:8080)
                    ├── JWT 鉴权 + 限流
                    ├── 业务逻辑 (用户/会话/消息)
                    ├── LangChain 编排
                    │   ├── RAGFlow 检索
                    │   └── DeepSeek LLM
                    └── MongoDB 7.0
```

| 层级 | 技术 | 说明 |
|------|------|------|
| **前端** | FastAPI + Jinja2 SSR + 纯 JavaScript | 服务端渲染，端口 3000 |
| **后端** | Python 3.11 + FastAPI | 异步高性能，端口 8080 |
| **AI 框架** | LangChain 0.3+ | RAG 链条编排 + LLM 调用封装 |
| **知识检索** | RAGFlow v0.15.0 | 文档解析 / Embedding / 混合检索 |
| **大模型** | DeepSeek Chat API | 中文法律理解力强，128K 上下文 |
| **数据库** | MongoDB 7.0 (Motor 异步驱动) | 文档模型，天然匹配对话数据 |
| **反向代理** | Nginx 1.25+ | SSL 终止 + 反代 + 限流 |
| **容器化** | Docker + Docker Compose | 一键部署 |

---

## 快速开始

### 环境要求

- **Python** 3.11+
- **Node.js** 18+ (仅本地 MongoDB 需要)
- **Docker + Docker Compose** (可选，推荐)

### 本地开发

#### Windows

```powershell
# 1. 安装依赖
.\scripts\start.bat install

# 2. 启动所有服务 (MongoDB + 后端 + 前端)
.\scripts\start.bat start

# 3. 开发模式（热重载）
.\scripts\start.bat dev
```

#### Linux / macOS

```bash
# 1. 安装依赖
bash scripts/start.sh install

# 2. 启动所有服务
bash scripts/start.sh start

# 3. 开发模式
bash scripts/start.sh dev
```

启动后访问：
- 前端页面：**http://localhost:3000**
- 后端 API 文档：**http://localhost:8080/docs**
- 健康检查：**http://localhost:8080/health**

### Docker 部署

```bash
# 开发环境
make docker
# 或
docker compose up -d

# 生产环境
make docker-prod
# 或
docker compose -f docker-compose.prod.yml up -d
```

### 环境变量配置

```bash
# 复制配置文件
cp .env.example backend/.env

# 编辑 backend/.env，填入以下必填项：
DEEPSEEK_API_KEY=sk-xxxxx          # DeepSeek API Key
RAGFLOW_API_KEY=ragflow-xxxxx      # RAGFlow API Key
RAGFLOW_DATASET_ID=xxxxx           # RAGFlow 数据集 ID
JWT_SECRET=你的随机密钥至少32位       # JWT 签名密钥
```

---

## 项目结构

```
ai_law/
├── backend/                    # 🐍 后端 (Python FastAPI, 端口 8080)
│   ├── main.py                 # 应用入口
│   ├── config.py / config.yaml # 配置管理
│   ├── database.py             # MongoDB 连接 + 索引
│   ├── api/                    # API 路由层
│   ├── services/               # 业务逻辑层
│   │   ├── chat_service_v2.py  #   👈 当前主用：LangChain 全链路 SSE 对话
│   │   ├── llm_service_v2.py   #   LangChain ChatOpenAI 封装
│   │   ├── ragflow_client.py   #   RAGFlow SDK 客户端
│   │   ├── rag_chain.py        #   LCEL RAG 对话链
│   │   ├── safety_filter.py    #   System Prompt + 安全过滤
│   │   └── ...                 #   prompts / callbacks / retriever 等
│   ├── middleware/              # 中间件 (auth / cors / rate_limiter)
│   ├── schemas/ / utils/       # 数据模型 / 工具函数
│   └── internal/ cmd/          # Go 遗留代码 (v1.0，当前不使用)
│
├── frontend/                   # 🎨 前端 (FastAPI + Jinja2 SSR, 端口 3000)
│   ├── main.py                 # 前端入口
│   ├── routes/                 # 页面路由 + API 代理
│   ├── templates/              # Jinja2 模板 (11 个页面)
│   └── static/                 # CSS (4) + JS (5) + 图片
│
├── deploy/                     # 🚀 部署配置
│   ├── nginx.conf              # Nginx 反代 + SSL
│   ├── deploy.sh               # ECS 一键部署
│   └── certs/                  # SSL 证书
│
├── scripts/                    # 🔧 启动脚本
│   ├── start.sh / start.bat    # 启动/停止/重启
│   └── start_mongodb.js        # 本地 MongoDB 实例
│
├── data/laws/                  # 📜 法律条文文档 (.docx)
├── docs/                       # 📚 项目文档
├── docker-compose.yml          # 开发环境
├── docker-compose.prod.yml     # 生产环境
└── Makefile                    # 构建命令
```

---

## 文档索引

| 文档 | 说明 |
|------|------|
| [需求范围确认书](docs/需求范围确认书.md) | 功能范围、交互细节、验收标准 |
| [项目计划](docs/项目计划.md) | 6 周里程碑、甘特图、风险识别 |
| [架构设计文档](docs/架构设计文档.md) | 系统架构、技术选型、API 设计、AI 链路 |
| [AI法律助手 任务文档](docs/AI法律助手_任务文档.md) | 各岗位职责、交付物、协作接口 |
| [LangChain 深度集成指南](docs/LangChain深度集成指南.md) | LangChain 组件使用说明 |
| [添加新法律步骤](docs/添加新的法律步骤.txt) | 知识库扩充操作指南 |

---

## 开发指南

### API 接口

所有接口以 `/api/v1` 为前缀，遵循统一的 `{ code, message, data }` 响应格式。

| 模块 | 路径前缀 | 鉴权 |
|------|----------|:---:|
| 认证 | `/api/v1/auth` | 部分 |
| 用户 | `/api/v1/user` | 是 |
| 会话 | `/api/v1/sessions` | 是 |
| 聊天 | `/api/v1/chat` | 是 |
| 知识库 | `/api/v1/knowledge` | 否 |

> 完整的 API 文档启动后端后访问 **http://localhost:8080/docs** 查看 Swagger。

### SSE 流式对话事件

```
event: thinking   → 正在检索相关法条...
event: chunk      → 逐 token 输出 AI 回复
event: law_ref    → 法条引用信息
event: done       → 对话完成（含 message_id / tokens）
```

### 技术栈详细版本

```
Python 3.11+          FastAPI 0.115+
LangChain 0.3+        langchain-openai 0.2+
MongoDB 7.0           Motor 3.7+ (异步驱动)
RAGFlow v0.15.0       ragflow-sdk 0.22+
DeepSeek Chat API     PyJWT 2.10+
Uvicorn 0.34+         passlib[bcrypt] 1.7+
```

---

## 部署

### 阿里云 ECS 部署

```bash
# 1. 配置环境变量
cp .env.production deploy/.env
# 编辑 deploy/.env，填入生产环境配置

# 2. 上传代码到服务器 (Windows)
powershell -File deploy/upload.ps1

# 3. SSH 到服务器执行部署
ssh root@your-server-ip
cd /opt/ai-law/lfai
bash deploy/deploy.sh
```

### Docker Compose 服务清单

| 服务 | 镜像 | 端口 | 说明 |
|------|------|:---:|------|
| nginx | `nginx:1.25-alpine` | 80/443 | SSL 终止 + 反代 (仅生产) |
| frontend | 构建自 `./frontend/` | 3000 | FastAPI SSR |
| backend | 构建自 `./backend/` | 8080 | FastAPI API |
| mongodb | `mongo:7` | 27017 | 数据库 |
| ragflow | `infiniflow/ragflow:v0.15.0` | 9380 | RAG 知识检索 |

---

## 参与贡献

1. Fork 本仓库
2. 新建 `Feat_xxx` 分支
3. 提交代码
4. 新建 Pull Request

---

## License

[MIT](./LICENSE)
