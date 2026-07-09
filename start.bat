@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ═══════════════════════════════════════════════════════
:: AI法律助手 v2.0 — Windows 统一启动脚本
:: 用法: start.bat [命令]
::   (无参数)   → 交互式菜单
::   install    → 安装所有依赖
::   start      → 启动前后端（两个窗口）
::   backend    → 仅启动后端
::   frontend   → 仅启动前端
::   stop       → 停止所有服务
::   status     → 查看服务状态
::   docker     → Docker 开发环境一键启动
:: ═══════════════════════════════════════════════════════

set "ROOT=%~dp0"
cd /d "%ROOT%"

:: ── 检查 Python ──
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.11+
    pause
    exit /b 1
)

:: ── 解析命令参数 ──
set "CMD=%~1"
if "%CMD%"=="" goto menu
goto cmd_%CMD% 2>nul || (
    echo [错误] 未知命令: %CMD%
    echo 可用命令: install, start, backend, frontend, stop, status, docker
    exit /b 1
)

:: ═══════════════════════════════════════
:: 交互式菜单
:: ═══════════════════════════════════════
:menu
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║     AI法律助手 v2.0 — 启动管理         ║
echo  ╠══════════════════════════════════════════╣
echo  ║  [1] 安装依赖                           ║
echo  ║  [2] 启动全部服务（前端 + 后端）        ║
echo  ║  [3] 仅启动后端 (port 8080)             ║
echo  ║  [4] 仅启动前端 (port 3000)             ║
echo  ║  [5] 停止所有服务                       ║
echo  ║  [6] 查看服务状态                       ║
echo  ║  [D] Docker 开发环境一键启动            ║
echo  ║  [Q] 退出                               ║
echo  ╚══════════════════════════════════════════╝
echo.
set /p CHOICE="请输入选项: "

if /i "%CHOICE%"=="1" goto cmd_install
if /i "%CHOICE%"=="2" goto cmd_start
if /i "%CHOICE%"=="3" goto cmd_backend
if /i "%CHOICE%"=="4" goto cmd_frontend
if /i "%CHOICE%"=="5" goto cmd_stop
if /i "%CHOICE%"=="6" goto cmd_status
if /i "%CHOICE%"=="D" goto cmd_docker
if /i "%CHOICE%"=="d" goto cmd_docker
if /i "%CHOICE%"=="Q" exit /b 0
if /i "%CHOICE%"=="q" exit /b 0

echo [错误] 无效选项
goto menu

:: ═══════════════════════════════════════
:: [1] 安装所有依赖
:: ═══════════════════════════════════════
:cmd_install
echo.
echo [安装] 正在安装 Python 依赖...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if %errorlevel% equ 0 (
    echo [完成] 所有依赖安装成功！
) else (
    echo [错误] 依赖安装失败，请检查网络或 pip 配置
)
if "%CMD%"=="" pause && goto menu
exit /b 0

:: ═══════════════════════════════════════
:: [2] 启动全部服务
:: ═══════════════════════════════════════
:cmd_start
echo.
echo [启动] 正在启动前后端服务...
echo   后端 → http://localhost:8080
echo   前端 → http://localhost:3000
echo.
echo 提示: 关闭窗口即可停止对应服务

start "AI法律助手-后端" cmd /k "cd /d "%ROOT%backend" && title AI法律助手-后端 :8080 && uvicorn main:app --host 0.0.0.0 --port 8080 --reload"
timeout /t 2 >nul
start "AI法律助手-前端" cmd /k "cd /d "%ROOT%frontend" && title AI法律助手-前端 :3000 && uvicorn main:app --host 0.0.0.0 --port 3000 --reload"

if "%CMD%"=="" goto menu
exit /b 0

:: ═══════════════════════════════════════
:: [3] 仅启动后端
:: ═══════════════════════════════════════
:cmd_backend
echo.
echo [启动] 正在启动后端服务 → http://localhost:8080
start "AI法律助手-后端" cmd /k "cd /d "%ROOT%backend" && title AI法律助手-后端 :8080 && uvicorn main:app --host 0.0.0.0 --port 8080 --reload"
if "%CMD%"=="" pause && goto menu
exit /b 0

:: ═══════════════════════════════════════
:: [4] 仅启动前端
:: ═══════════════════════════════════════
:cmd_frontend
echo.
echo [启动] 正在启动前端服务 → http://localhost:3000
start "AI法律助手-前端" cmd /k "cd /d "%ROOT%frontend" && title AI法律助手-前端 :3000 && uvicorn main:app --host 0.0.0.0 --port 3000 --reload"
if "%CMD%"=="" pause && goto menu
exit /b 0

:: ═══════════════════════════════════════
:: [5] 停止所有服务
:: ═══════════════════════════════════════
:cmd_stop
echo.
echo [停止] 正在关闭所有服务...
taskkill /fi "WINDOWTITLE eq AI法律助手-后端*" /f 2>nul
taskkill /fi "WINDOWTITLE eq AI法律助手-前端*" /f 2>nul
:: 备用: 按端口杀进程
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8080" ^| findstr "LISTENING"') do taskkill /f /pid %%a 2>nul
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000" ^| findstr "LISTENING"') do taskkill /f /pid %%a 2>nul
echo [完成] 服务已停止
if "%CMD%"=="" pause && goto menu
exit /b 0

:: ═══════════════════════════════════════
:: [6] 查看服务状态
:: ═══════════════════════════════════════
:cmd_status
echo.
echo ═══════════════════════════════════════
echo  服务状态检查
echo ═══════════════════════════════════════
echo.
echo --- 后端 (8080) ---
netstat -ano | findstr ":8080.*LISTENING" >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8080.*LISTENING"') do echo [运行中] PID: %%a
) else (
    echo [未运行]
)
echo.
echo --- 前端 (3000) ---
netstat -ano | findstr ":3000.*LISTENING" >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000.*LISTENING"') do echo [运行中] PID: %%a
) else (
    echo [未运行]
)
echo.
if "%CMD%"=="" pause && goto menu
exit /b 0

:: ═══════════════════════════════════════
:: [D] Docker 开发环境一键启动
:: ═══════════════════════════════════════
:cmd_docker
echo.
echo [Docker] 正在启动开发环境容器...
docker compose up -d
if %errorlevel% equ 0 (
    echo [完成] Docker 开发环境已启动！
    echo   后端:    http://localhost:8080
    echo   前端:    http://localhost:3000
    echo   MongoDB: localhost:27017
    echo   RAGFlow: http://localhost:9380
) else (
    echo [错误] Docker 启动失败，请检查 Docker Desktop 是否运行
)
if "%CMD%"=="" pause && goto menu
exit /b 0
