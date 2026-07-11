# AI Law Assistant (AI 法律助手)

> An intelligent legal consultation service powered by LLM + RAG, providing accessible and reliable legal guidance for the general public.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-7.0-brightgreen.svg)](https://www.mongodb.com/)
[![LangChain](https://img.shields.io/badge/LangChain-0.3+-orange.svg)](https://www.langchain.com/)
[![RAGFlow](https://img.shields.io/badge/RAGFlow-v0.15.0-blueviolet.svg)](https://ragflow.io/)
[![License](https://img.shields.io/badge/License-MIT-lightgrey.svg)](./LICENSE)

---

## 📖 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Documentation](#documentation)
- [Development Guide](#development-guide)
- [Deployment](#deployment)

---

## Overview

The AI Law Assistant provides **AI-powered legal consultation** through natural language conversations. It uses authoritative legal databases combined with large language models to generate professional, compliant legal advice.

### Coverage Areas

Family Law · Labor Disputes · Contract Disputes · Traffic Accidents · Property Disputes · Consumer Rights

### ⚠️ Disclaimer

AI responses are for reference only and do not constitute legal advice. For significant legal matters, consulting a licensed attorney is strongly recommended.

---

## Architecture

```
Browser → Nginx (HTTPS) → Frontend FastAPI SSR (:3000)
                              │
          API Proxy (/api/v1/proxy/*)
                              │
                   Backend FastAPI (:8080)
                   ├── JWT Auth + Rate Limiting
                   ├── Business Logic (Users/Sessions/Chat)
                   ├── LangChain Orchestration
                   │   ├── RAGFlow Retrieval
                   │   └── DeepSeek LLM
                   └── MongoDB 7.0
```

| Layer | Technology | Notes |
|------|------|------|
| **Frontend** | FastAPI + Jinja2 SSR + Vanilla JS | Server-side rendering, port 3000 |
| **Backend** | Python 3.11 + FastAPI | Async high-performance, port 8080 |
| **AI Framework** | LangChain 0.3+ | RAG chain orchestration + LLM abstraction |
| **Knowledge Retrieval** | RAGFlow v0.15.0 | Doc parsing / Embedding / Hybrid search |
| **LLM** | DeepSeek Chat API | Strong Chinese legal comprehension, 128K context |
| **Database** | MongoDB 7.0 (Motor async driver) | Document model, natural fit for conversations |
| **Reverse Proxy** | Nginx 1.25+ | SSL termination + proxying + rate limiting |
| **Containerization** | Docker + Docker Compose | One-click deployment |

---

## Quick Start

### Prerequisites

- **Python** 3.11+
- **Node.js** 18+ (local MongoDB only)
- **Docker + Docker Compose** (optional, recommended)

### Local Development

#### Windows

```powershell
# 1. Install dependencies
.\scripts\start.bat install

# 2. Start all services (MongoDB + Backend + Frontend)
.\scripts\start.bat start

# 3. Dev mode (hot reload)
.\scripts\start.bat dev
```

#### Linux / macOS

```bash
# 1. Install dependencies
bash scripts/start.sh install

# 2. Start all services
bash scripts/start.sh start

# 3. Dev mode
bash scripts/start.sh dev
```

After startup:
- Frontend: **http://localhost:3000**
- API Docs (Swagger): **http://localhost:8080/docs**
- Health Check: **http://localhost:8080/health**

### Docker Deployment

```bash
# Development environment
make docker
# or
docker compose up -d

# Production environment
make docker-prod
# or
docker compose -f docker-compose.prod.yml up -d
```

### Environment Variables

```bash
# Copy config template
cp .env.example backend/.env

# Edit backend/.env, fill in required values:
DEEPSEEK_API_KEY=sk-xxxxx
RAGFLOW_API_KEY=ragflow-xxxxx
RAGFLOW_DATASET_ID=xxxxx
JWT_SECRET=your-random-secret-at-least-32-chars
```

---

## Project Structure

```
ai_law/
├── backend/                    # 🐍 Backend (Python FastAPI, port 8080)
│   ├── main.py                 # App entry point
│   ├── config.py / config.yaml # Configuration
│   ├── database.py             # MongoDB connection + indexes
│   ├── api/                    # API route layer
│   ├── services/               # Business logic layer
│   │   ├── chat_service_v2.py  #   👈 Main: LangChain end-to-end SSE chat
│   │   ├── llm_service_v2.py   #   LangChain ChatOpenAI wrapper
│   │   ├── ragflow_client.py   #   RAGFlow SDK client
│   │   ├── rag_chain.py        #   LCEL RAG conversation chain
│   │   ├── safety_filter.py    #   System Prompt + safety filters
│   │   └── ...                 #   prompts / callbacks / retriever etc.
│   ├── middleware/              # Middleware (auth / cors / rate_limiter)
│   ├── schemas/ / utils/       # Data models / utilities
│   └── internal/ cmd/          # Go legacy code (v1.0, not in use)
│
├── frontend/                   # 🎨 Frontend (FastAPI + Jinja2 SSR, port 3000)
│   ├── main.py                 # Frontend entry point
│   ├── routes/                 # Page routes + API proxy
│   ├── templates/              # Jinja2 templates (11 pages)
│   └── static/                 # CSS (4) + JS (5) + images
│
├── deploy/                     # 🚀 Deployment configs
│   ├── nginx.conf              # Nginx reverse proxy + SSL
│   ├── deploy.sh               # ECS one-click deployment
│   └── certs/                  # SSL certificates
│
├── scripts/                    # 🔧 Startup scripts
│   ├── start.sh / start.bat    # Start / stop / restart
│   └── start_mongodb.js        # Local MongoDB instance
│
├── data/laws/                  # 📜 Legal documents (.docx)
├── docs/                       # 📚 Project documentation
├── docker-compose.yml          # Dev environment
├── docker-compose.prod.yml     # Production environment
└── Makefile                    # Build commands
```

---

## Documentation

| Document | Description |
|------|------|
| [Requirements Spec (Chinese)](docs/需求范围确认书.md) | Feature scope, interactions, acceptance criteria |
| [Project Plan (Chinese)](docs/项目计划.md) | 6-week milestones, Gantt chart, risk identification |
| [Architecture Design (Chinese)](docs/架构设计文档.md) | System architecture, tech decisions, API design, AI pipeline |
| [Task Breakdown (Chinese)](docs/AI法律助手_任务文档.md) | Role responsibilities, deliverables, collaboration interfaces |
| [LangChain Integration Guide (Chinese)](docs/LangChain深度集成指南.md) | LangChain component usage guide |
| [Adding New Laws (Chinese)](docs/添加新的法律步骤.txt) | Knowledge base expansion guide |

---

## Development Guide

### API Endpoints

All endpoints use the `/api/v1` prefix and follow the `{ code, message, data }` response format.

| Module | Prefix | Auth |
|------|----------|:---:|
| Authentication | `/api/v1/auth` | Partial |
| User | `/api/v1/user` | Yes |
| Session | `/api/v1/sessions` | Yes |
| Chat | `/api/v1/chat` | Yes |
| Knowledge Base | `/api/v1/knowledge` | No |

> Full API documentation is available at **http://localhost:8080/docs** after starting the backend.

### SSE Streaming Events

```
event: thinking   → Retrieving relevant legal articles...
event: chunk      → Streaming AI response token by token
event: law_ref    → Legal article reference info
event: done       → Conversation complete (with message_id / tokens)
```

### Dependency Versions

```
Python 3.11+          FastAPI 0.115+
LangChain 0.3+        langchain-openai 0.2+
MongoDB 7.0           Motor 3.7+ (async driver)
RAGFlow v0.15.0       ragflow-sdk 0.22+
DeepSeek Chat API     PyJWT 2.10+
Uvicorn 0.34+         passlib[bcrypt] 1.7+
```

---

## Deployment

### Alibaba Cloud ECS

```bash
# 1. Configure environment variables
cp .env.production deploy/.env
# Edit deploy/.env with production values

# 2. Upload code to server (Windows)
powershell -File deploy/upload.ps1

# 3. SSH to server and deploy
ssh root@your-server-ip
cd /opt/ai-law/lfai
bash deploy/deploy.sh
```

### Docker Compose Services

| Service | Image | Port | Description |
|------|------|:---:|------|
| nginx | `nginx:1.25-alpine` | 80/443 | SSL termination + reverse proxy (production only) |
| frontend | Built from `./frontend/` | 3000 | FastAPI SSR |
| backend | Built from `./backend/` | 8080 | FastAPI API |
| mongodb | `mongo:7` | 27017 | Database |
| ragflow | `infiniflow/ragflow:v0.15.0` | 9380 | RAG knowledge retrieval |

---

## Contributing

1. Fork the repository
2. Create a `Feat_xxx` branch
3. Commit your changes
4. Create a Pull Request

---

## License

[MIT](./LICENSE)
