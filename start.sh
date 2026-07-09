#!/bin/bash
# ═══════════════════════════════════════════════════════
# AI法律助手 v2.0 — Linux/Mac 统一启动脚本
# 用法: ./start.sh [命令]
#   (无参数)   → 启动全部服务
#   install    → 安装所有依赖
#   start      → 启动前后端
#   backend    → 仅启动后端
#   frontend   → 仅启动前端
#   stop       → 停止所有服务
#   restart    → 重启所有服务
#   status     → 查看服务状态
#   docker     → Docker 开发环境一键启动
#   logs       → 查看日志
# ═══════════════════════════════════════════════════════

set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_PID=""
FRONTEND_PID=""
PID_FILE="$ROOT/.pids"

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

# ── 检查 Python ──
check_python() {
    if ! command -v python3 &>/dev/null && ! command -v python &>/dev/null; then
        echo -e "${RED}[错误] 未找到 Python，请先安装 Python 3.11+${NC}"
        exit 1
    fi
    PYTHON=$(command -v python3 || command -v python)
}

# ── 安装依赖 ──
do_install() {
    echo -e "${CYAN}[安装] 正在安装 Python 依赖...${NC}"
    cd "$ROOT"
    $PYTHON -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    echo -e "${GREEN}[完成] 所有依赖安装成功！${NC}"
}

# ── 启动后端 ──
start_backend() {
    echo -e "${CYAN}[启动] 后端服务 → http://localhost:8080${NC}"
    cd "$ROOT/backend"
    nohup $PYTHON -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload \
        > "$ROOT/logs/backend.log" 2>&1 &
    echo $! >> "$PID_FILE"
    echo -e "${GREEN}  后端 PID: $(tail -1 "$PID_FILE")${NC}"
}

# ── 启动前端 ──
start_frontend() {
    echo -e "${CYAN}[启动] 前端服务 → http://localhost:3000${NC}"
    cd "$ROOT/frontend"
    nohup $PYTHON -m uvicorn main:app --host 0.0.0.0 --port 3000 --reload \
        > "$ROOT/logs/frontend.log" 2>&1 &
    echo $! >> "$PID_FILE"
    echo -e "${GREEN}  前端 PID: $(tail -1 "$PID_FILE")${NC}"
}

# ── 停止服务 ──
do_stop() {
    echo -e "${YELLOW}[停止] 正在关闭所有服务...${NC}"
    if [ -f "$PID_FILE" ]; then
        while read -r pid; do
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid" 2>/dev/null && echo "  已终止 PID: $pid"
            fi
        done < "$PID_FILE"
        rm -f "$PID_FILE"
    fi
    # 兜底：按端口杀进程
    lsof -ti:8080 2>/dev/null | xargs -r kill 2>/dev/null || true
    lsof -ti:3000 2>/dev/null | xargs -r kill 2>/dev/null || true
    echo -e "${GREEN}[完成] 所有服务已停止${NC}"
}

# ── 查看状态 ──
do_status() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════${NC}"
    echo -e "${CYAN}  服务状态${NC}"
    echo -e "${CYAN}═══════════════════════════════════════${NC}"
    echo ""

    if lsof -ti:8080 >/dev/null 2>&1; then
        echo -e "  后端 (8080):  ${GREEN}运行中${NC}  PID: $(lsof -ti:8080)"
    else
        echo -e "  后端 (8080):  ${RED}未运行${NC}"
    fi

    if lsof -ti:3000 >/dev/null 2>&1; then
        echo -e "  前端 (3000):  ${GREEN}运行中${NC}  PID: $(lsof -ti:3000)"
    else
        echo -e "  前端 (3000):  ${RED}未运行${NC}"
    fi
    echo ""
}

# ── 查看日志 ──
do_logs() {
    if [ -f "$ROOT/logs/backend.log" ] || [ -f "$ROOT/logs/frontend.log" ]; then
        tail -f "$ROOT"/logs/*.log
    else
        echo -e "${YELLOW}暂无日志文件${NC}"
    fi
}

# ── Docker 启动 ──
do_docker() {
    echo -e "${CYAN}[Docker] 正在启动开发环境容器...${NC}"
    cd "$ROOT"
    docker compose up -d
    echo -e "${GREEN}[完成] Docker 开发环境已启动！${NC}"
    echo -e "  后端:    http://localhost:8080"
    echo -e "  前端:    http://localhost:3000"
    echo -e "  MongoDB: localhost:27017"
    echo -e "  RAGFlow: http://localhost:9380"
}

# ═══════════════════ 主入口 ═══════════════════

check_python
mkdir -p "$ROOT/logs"

CMD="${1:-start}"

case "$CMD" in
    install)
        do_install
        ;;
    start)
        do_stop 2>/dev/null || true
        rm -f "$PID_FILE"
        start_backend
        sleep 2
        start_frontend
        echo ""
        echo -e "${GREEN}═══════════════════════════════════════${NC}"
        echo -e "${GREEN}  全部服务已启动！${NC}"
        echo -e "${GREEN}  后端: http://localhost:8080${NC}"
        echo -e "${GREEN}  前端: http://localhost:3000${NC}"
        echo -e "${GREEN}  日志: tail -f logs/*.log${NC}"
        echo -e "${GREEN}═══════════════════════════════════════${NC}"
        ;;
    backend)
        start_backend
        ;;
    frontend)
        start_frontend
        ;;
    stop)
        do_stop
        ;;
    restart)
        do_stop
        sleep 1
        rm -f "$PID_FILE"
        start_backend
        sleep 2
        start_frontend
        echo -e "${GREEN}[完成] 服务已重启${NC}"
        ;;
    status)
        do_status
        ;;
    docker)
        do_docker
        ;;
    logs)
        do_logs
        ;;
    *)
        echo -e "${RED}未知命令: $CMD${NC}"
        echo "可用命令: install, start, backend, frontend, stop, restart, status, docker, logs"
        exit 1
        ;;
esac
