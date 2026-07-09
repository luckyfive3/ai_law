# ═══════════════════════════════════════════════════════
# AI法律助手 v2.0 — 统一 Makefile（前后端共用）
# ═══════════════════════════════════════════════════════

.PHONY: help install start backend frontend stop restart status clean docker docker-prod logs

# 默认目标
help:
	@echo ""
	@echo " AI法律助手 v2.0 — 命令列表"
	@echo " ═══════════════════════════════════════"
	@echo ""
	@echo "  make install      安装所有 Python 依赖"
	@echo "  make start        启动前后端服务"
	@echo "  make backend      仅启动后端 (8080)"
	@echo "  make frontend     仅启动前端 (3000)"
	@echo "  make stop         停止所有服务"
	@echo "  make restart      重启所有服务"
	@echo "  make status       查看服务状态"
	@echo "  make logs         查看运行日志"
	@echo "  make docker       启动 Docker 开发环境"
	@echo "  make docker-prod  启动 Docker 生产环境"
	@echo "  make clean        清理临时文件"
	@echo ""

# ── 安装依赖 ──
install:
	@echo "[安装] 安装所有 Python 依赖..."
	pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
	@echo "[完成] 依赖安装成功"

# ── 启动全部服务 ──
start: stop
	@mkdir -p logs
	@echo "[启动] 后端服务 → http://localhost:8080"
	@cd backend && nohup python -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload > ../logs/backend.log 2>&1 & echo $$! > ../logs/backend.pid
	@sleep 2
	@echo "[启动] 前端服务 → http://localhost:3000"
	@cd frontend && nohup python -m uvicorn main:app --host 0.0.0.0 --port 3000 --reload > ../logs/frontend.log 2>&1 & echo $$! > ../logs/frontend.pid
	@echo ""
	@echo "═══════════════════════════════════════"
	@echo "  全部服务已启动！"
	@echo "  后端: http://localhost:8080"
	@echo "  前端: http://localhost:3000"
	@echo "  日志: make logs"
	@echo "═══════════════════════════════════════"

# ── 仅启动后端 ──
backend:
	@mkdir -p logs
	@echo "[启动] 后端服务 → http://localhost:8080"
	@cd backend && nohup python -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload > ../logs/backend.log 2>&1 & echo $$! > ../logs/backend.pid
	@echo "[完成] 后端 PID: $$(cat logs/backend.pid)"

# ── 仅启动前端 ──
frontend:
	@mkdir -p logs
	@echo "[启动] 前端服务 → http://localhost:3000"
	@cd frontend && nohup python -m uvicorn main:app --host 0.0.0.0 --port 3000 --reload > ../logs/frontend.log 2>&1 & echo $$! > ../logs/frontend.pid
	@echo "[完成] 前端 PID: $$(cat logs/frontend.pid)"

# ── 停止服务 ──
stop:
	@echo "[停止] 关闭所有服务..."
	@-kill $$(cat logs/backend.pid 2>/dev/null) 2>/dev/null || true
	@-kill $$(cat logs/frontend.pid 2>/dev/null) 2>/dev/null || true
	@-lsof -ti:8080 | xargs -r kill 2>/dev/null || true
	@-lsof -ti:3000 | xargs -r kill 2>/dev/null || true
	@rm -f logs/backend.pid logs/frontend.pid
	@echo "[完成] 服务已停止"

# ── 重启 ──
restart: stop
	@sleep 1
	@$(MAKE) start

# ── 查看状态 ──
status:
	@echo ""
	@echo "═══════════════════════════════════════"
	@echo "  服务状态"
	@echo "═══════════════════════════════════════"
	@echo ""
	@if lsof -ti:8080 >/dev/null 2>&1; then \
		echo "  后端 (8080):  运行中  PID: $$(lsof -ti:8080)"; \
	else \
		echo "  后端 (8080):  未运行"; \
	fi
	@if lsof -ti:3000 >/dev/null 2>&1; then \
		echo "  前端 (3000):  运行中  PID: $$(lsof -ti:3000)"; \
	else \
		echo "  前端 (3000):  未运行"; \
	fi
	@echo ""

# ── 日志 ──
logs:
	@tail -f logs/*.log 2>/dev/null || echo "暂无日志，请先启动服务"

# ── Docker ──
docker:
	@echo "[Docker] 启动开发环境..."
	docker compose up -d
	@echo "[完成] Docker 开发环境已启动"
	@echo "  后端:    http://localhost:8080"
	@echo "  前端:    http://localhost:3000"
	@echo "  MongoDB: localhost:27017"
	@echo "  RAGFlow: http://localhost:9380"

docker-prod:
	@echo "[Docker] 启动生产环境..."
	docker compose -f docker-compose.prod.yml up -d
	@echo "[完成] Docker 生产环境已启动"

# ── 清理 ──
clean:
	@echo "[清理] 删除临时文件和日志..."
	rm -rf logs/
	rm -rf __pycache__/ backend/__pycache__/ frontend/__pycache__/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "[完成] 清理完毕"
