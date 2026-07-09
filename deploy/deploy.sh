#!/bin/bash
# ═══════════════════════════════════════
# AI法律助手 v1.0 — 阿里云一键部署脚本
# 适用系统: CentOS 7+ / Alibaba Cloud Linux / Ubuntu 20.04+
# 使用方法: chmod +x deploy.sh && ./deploy.sh
# ═══════════════════════════════════════

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}   AI法律助手 v1.0 — 阿里云部署脚本${NC}"
echo -e "${GREEN}============================================${NC}"

# ─── 1. 检查 Docker ───
echo -e "\n${YELLOW}[1/7] 检查 Docker 环境...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Docker 未安装，正在安装...${NC}"
    curl -fsSL https://get.docker.com | bash
    systemctl enable docker
    systemctl start docker
else
    echo -e "${GREEN}Docker 已安装: $(docker --version)${NC}"
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${YELLOW}Docker Compose 插件未安装，正在安装...${NC}"
    apt-get update && apt-get install -y docker-compose-plugin 2>/dev/null || \
    yum install -y docker-compose-plugin 2>/dev/null || \
    (curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose && chmod +x /usr/local/bin/docker-compose)
fi

# ─── 2. 创建项目目录 ───
echo -e "\n${YELLOW}[2/7] 创建项目目录 /opt/ai-law...${NC}"
mkdir -p /opt/ai-law
cd /opt/ai-law

# ─── 3. 配置环境变量 ───
echo -e "\n${YELLOW}[3/7] 配置环境变量...${NC}"
if [ ! -f .env ]; then
    echo -e "${RED}请先配置 .env 文件！${NC}"
    echo ""
    echo "=== 生成环境变量请运行 ==="
    echo ""
    echo "cat > /opt/ai-law/.env << 'EOF'"
    echo "DB_USER=ailaw"
    echo "DB_PASSWORD=$(openssl rand -base64 16)"
    echo "REDIS_PASSWORD=$(openssl rand -base64 16)"
    echo "JWT_SECRET=$(openssl rand -base64 32)"
    echo "DEEPSEEK_API_KEY=sk-your-deepseek-api-key"
    echo "EOF"
    echo ""
    echo "然后修改 DEEPSEEK_API_KEY 为你的真实 API Key"
    echo "再重新运行 ./deploy.sh"
    exit 1
fi
echo -e "${GREEN}.env 已配置${NC}"

# ─── 4. 生成自签名 SSL 证书（如有正式证书请替换） ───
echo -e "\n${YELLOW}[4/7] 生成 SSL 证书...${NC}"
mkdir -p deploy/certs
if [ ! -f deploy/certs/server.crt ]; then
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout deploy/certs/server.key \
        -out deploy/certs/server.crt \
        -subj "/C=CN/ST=Shanghai/L=Shanghai/O=AI-Law/CN=localhost" 2>/dev/null
    echo -e "${GREEN}自签名证书已生成（建议后续更换为 Let's Encrypt 正式证书）${NC}"
else
    echo -e "${GREEN}SSL 证书已存在${NC}"
fi

# ─── 5. 拉取代码 ───
echo -e "\n${YELLOW}[5/7] 拉取项目代码...${NC}"
# 如果你用 Git：git pull origin main
# 这里假设代码已从本机 scp/rsync 上传到 /opt/ai-law
echo -e "${YELLOW}请确保代码已上传到 /opt/ai-law（backend/ frontend/ deploy/ docker-compose.prod.yml）${NC}"

# ─── 6. 构建并启动 ───
echo -e "\n${YELLOW}[6/7] 构建 Docker 镜像并启动服务...${NC}"
docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d

# ─── 7. 等待服务就绪 ───
echo -e "\n${YELLOW}[7/7] 等待服务就绪...${NC}"
sleep 10

# 健康检查
echo -e "\n${GREEN}=== 健康检查 ===${NC}"
curl -s http://localhost/health || echo -e "${RED}后端未就绪，请检查日志${NC}"
curl -s -o /dev/null -w "前端 HTTP 状态: %{http_code}\n" http://localhost/ || echo -e "${RED}前端未就绪${NC}"

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}   部署完成！${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "访问地址: ${GREEN}https://你的服务器IP${NC}"
echo -e "（首次访问需跳过 HTTPS 证书警告）"
echo ""
echo -e "常用命令:"
echo -e "  查看日志:  ${YELLOW}cd /opt/ai-law && docker compose -f docker-compose.prod.yml logs -f${NC}"
echo -e "  重启服务:  ${YELLOW}cd /opt/ai-law && docker compose -f docker-compose.prod.yml restart${NC}"
echo -e "  停止服务:  ${YELLOW}cd /opt/ai-law && docker compose -f docker-compose.prod.yml down${NC}"
echo -e "  查看状态:  ${YELLOW}cd /opt/ai-law && docker compose -f docker-compose.prod.yml ps${NC}"

# ─── 阿里云安全组提示 ───
echo ""
echo -e "${RED}⚠️  重要：请在阿里云安全组中开放以下端口:${NC}"
echo -e "   80 (HTTP)  /  443 (HTTPS)"
echo -e "   阿里云控制台 → 云服务器 ECS → 安全组 → 入方向 → 添加规则"
