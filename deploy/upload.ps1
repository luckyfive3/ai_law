# ═══════════════════════════════════════
# AI法律助手 v1.0 — Windows 上传到阿里云
# 使用前请修改 SERVER_IP 为你的服务器 IP
# ═══════════════════════════════════════

$SERVER_IP = "123.57.89.197"
$SERVER_USER = "root"
$REMOTE_DIR = "/opt/ai-law/lfai"

Write-Host "============================================" -ForegroundColor Green
Write-Host "   AI法律助手 — 上传到阿里云服务器" -ForegroundColor Green
Write-Host "   目标: $SERVER_USER@$SERVER_IP`:$REMOTE_DIR" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green

# 1. 创建远程目录
Write-Host "`n[1/4] 创建远程目录..." -ForegroundColor Yellow
ssh $SERVER_USER@$SERVER_IP "mkdir -p $REMOTE_DIR/deploy/certs"

# 2. 上传配置文件
Write-Host "`n[2/4] 上传配置文件..." -ForegroundColor Yellow
scp docker-compose.prod.yml $SERVER_USER@$SERVER_IP`:$REMOTE_DIR/
scp .env.production $SERVER_USER@$SERVER_IP`:$REMOTE_DIR/.env
scp -r deploy/nginx.conf $SERVER_USER@$SERVER_IP`:$REMOTE_DIR/deploy/
scp -r deploy/deploy.sh $SERVER_USER@$SERVER_IP`:$REMOTE_DIR/deploy/

# 3. 上传后端代码
Write-Host "`n[3/4] 上传后端代码..." -ForegroundColor Yellow
ssh $SERVER_USER@$SERVER_IP "mkdir -p $REMOTE_DIR/backend"
scp -r backend/cmd $SERVER_USER@$SERVER_IP`:$REMOTE_DIR/backend/
scp -r backend/internal $SERVER_USER@$SERVER_IP`:$REMOTE_DIR/backend/
scp -r backend/config $SERVER_USER@$SERVER_IP`:$REMOTE_DIR/backend/
scp -r backend/migrations $SERVER_USER@$SERVER_IP`:$REMOTE_DIR/backend/
scp backend/go.mod backend/Dockerfile backend/blocked_keywords.txt $SERVER_USER@$SERVER_IP`:$REMOTE_DIR/backend/

# 4. 上传前端代码
Write-Host "`n[4/4] 上传前端代码..." -ForegroundColor Yellow
ssh $SERVER_USER@$SERVER_IP "mkdir -p $REMOTE_DIR/frontend"
scp -r frontend/main.py frontend/requirements.txt frontend/Dockerfile $SERVER_USER@$SERVER_IP`:$REMOTE_DIR/frontend/
scp -r frontend/routes $SERVER_USER@$SERVER_IP`:$REMOTE_DIR/frontend/
scp -r frontend/templates $SERVER_USER@$SERVER_IP`:$REMOTE_DIR/frontend/
scp -r frontend/static $SERVER_USER@$SERVER_IP`:$REMOTE_DIR/frontend/

Write-Host "`n============================================" -ForegroundColor Green
Write-Host "   上传完成！" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green

Write-Host "`n接下来登录服务器执行：" -ForegroundColor Yellow
Write-Host "  ssh $SERVER_USER@$SERVER_IP" -ForegroundColor White
Write-Host "  cd $REMOTE_DIR" -ForegroundColor White
Write-Host "  chmod +x deploy/deploy.sh && ./deploy/deploy.sh" -ForegroundColor White
