@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: =============================================================
:: AI法律助手 v1.0 — Windows 一键启动脚本
:: 用法: start.bat [命令]
::   (无参数)   → 交互式菜单
::   install    → 安装所有依赖
::   start      → 启动全部服务(MongoDB+后端+前端)
::   backend    → 仅启动后端
::   frontend   → 仅启动前端
::   stop       → 停止所有服务
::   status     → 查看服务状态
:: =============================================================

set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
cd /d "%ROOT%"

:: ── Conda 环境名称（根据实际情况修改） ──
set "CONDA_ENV=law"

:: ── 自动检测 Python（优先 conda 环境，回退系统 Python） ──
set "PYTHON_CMD="
set "CONDA_PATH="

:: 查找 conda 安装路径（支持 Anaconda/Miniconda）
for %%p in (anaconda3 Anaconda3 miniconda3 Miniconda3) do (
    if exist "%USERPROFILE%\%%p\Scripts\conda.exe" (
        set "CONDA_PATH=%USERPROFILE%\%%p"
    )
)

if defined CONDA_PATH (
    conda run -n %CONDA_ENV% python --version >nul 2>&1
    if %errorlevel% equ 0 (
        set "PYTHON_CMD=conda run -n %CONDA_ENV% python"
    )
)
if not defined PYTHON_CMD (
    where python >nul 2>&1
    if %errorlevel% equ 0 (set "PYTHON_CMD=python")
)
if not defined PYTHON_CMD (
    echo [ERROR] Python not found. Install Python 3.11+ or: conda create -n %CONDA_ENV% python=3.11
    pause
    exit /b 1
)

:: 构建新窗口中的启动命令前缀（自动激活 conda 环境）
if defined CONDA_PATH (
    set "WIN_CMD=cmd /k call "%CONDA_PATH%\Scripts\activate.bat" ^&^& conda activate %CONDA_ENV% ^&^&"
) else (
    set "WIN_CMD=cmd /k"
)

echo [INFO] Python: %PYTHON_CMD%

:: ── 解析命令参数 ──
set "CMD=%~1"
if "%CMD%"=="" goto menu
if /i "%CMD%"=="install"  goto cmd_install
if /i "%CMD%"=="start"    goto cmd_start
if /i "%CMD%"=="backend"  goto cmd_backend
if /i "%CMD%"=="frontend" goto cmd_frontend
if /i "%CMD%"=="stop"     goto cmd_stop
if /i "%CMD%"=="status"   goto cmd_status
echo [ERROR] Unknown command: %CMD%
echo Available: install, start, backend, frontend, stop, status
exit /b 1

:: =============================================================
:: 交互式菜单
:: =============================================================
:menu
echo.
echo  ========================================
echo    AI Legal Assistant v1.0 - Menu
echo  ========================================
echo    [1] Install dependencies
echo    [2] Start ALL (MongoDB + Backend + Frontend)
echo    [3] Start Backend only (port 8080)
echo    [4] Start Frontend only (port 3000)
echo    [5] Stop all services
echo    [6] Check service status
echo    [Q] Quit
echo  ========================================
echo.
set /p CHOICE="Enter option: "

if "%CHOICE%"=="1" goto cmd_install
if "%CHOICE%"=="2" goto cmd_start
if "%CHOICE%"=="3" goto cmd_backend
if "%CHOICE%"=="4" goto cmd_frontend
if "%CHOICE%"=="5" goto cmd_stop
if "%CHOICE%"=="6" goto cmd_status
if /i "%CHOICE%"=="Q" exit /b 0
echo [ERROR] Invalid option
goto menu

:: =============================================================
:: [1] Install dependencies
:: =============================================================
:cmd_install
echo.
echo [1/2] Installing backend dependencies...
%PYTHON_CMD% -m pip install -r "%ROOT%\backend\requirements.txt"
if %errorlevel% neq 0 (
    echo [ERROR] Backend dependency installation failed
    goto install_end
)
echo [1/2] Backend dependencies OK

echo.
echo [2/2] Installing frontend dependencies...
%PYTHON_CMD% -m pip install -r "%ROOT%\frontend\requirements.txt"
if %errorlevel% neq 0 (
    echo [ERROR] Frontend dependency installation failed
    goto install_end
)
echo [2/2] Frontend dependencies OK

echo.
echo [DONE] All dependencies installed successfully!
:install_end
if "%CMD%"=="" pause
if "%CMD%"=="" goto menu
exit /b 0

:: =============================================================
:: [2] Start ALL services
:: =============================================================
:cmd_start
echo.
echo ========================================
echo   Starting all services...
echo ========================================

:: --- MongoDB ---
echo [1/3] Starting MongoDB...
start "MongoDB" cmd /k "cd /d "%ROOT%" && title MongoDB :27017 && node start_mongodb.js"
timeout /t 3 >nul
echo        MongoDB started (port 27017)

:: --- Backend ---
echo [2/3] Starting Backend...
if defined CONDA_PATH (
    start "AI-Law-Backend" cmd /k call %CONDA_PATH%\Scripts\activate.bat ^&^& conda activate %CONDA_ENV% ^&^& cd /d %ROOT%\backend ^&^& title Backend :8080 ^&^& python main.py
) else (
    start "AI-Law-Backend" cmd /k cd /d %ROOT%\backend ^&^& title Backend :8080 ^&^& python main.py
)
timeout /t 4 >nul
echo        Backend started (http://localhost:8080)

:: --- Frontend ---
echo [3/3] Starting Frontend...
if defined CONDA_PATH (
    start "AI-Law-Frontend" cmd /k call %CONDA_PATH%\Scripts\activate.bat ^&^& conda activate %CONDA_ENV% ^&^& cd /d %ROOT%\frontend ^&^& title Frontend :3000 ^&^& python main.py
) else (
    start "AI-Law-Frontend" cmd /k cd /d %ROOT%\frontend ^&^& title Frontend :3000 ^&^& python main.py
)
timeout /t 2 >nul
echo        Frontend started (http://localhost:3000)

:: --- Open browser ---
start http://localhost:3000

echo.
echo ========================================
echo   All services started!
echo   Frontend: http://localhost:3000
echo   Backend:  http://localhost:8080
echo   MongoDB:  localhost:27017
echo ========================================

if "%CMD%"=="" pause
if "%CMD%"=="" goto menu
exit /b 0

:: =============================================================
:: [3] Start Backend only
:: =============================================================
:cmd_backend
echo.
echo Starting Backend (port 8080)...

:: MongoDB is required by backend
call :ensure_mongodb

if defined CONDA_PATH (
    start "AI-Law-Backend" cmd /k call %CONDA_PATH%\Scripts\activate.bat ^&^& conda activate %CONDA_ENV% ^&^& cd /d %ROOT%\backend ^&^& title Backend :8080 ^&^& python main.py
) else (
    start "AI-Law-Backend" cmd /k cd /d %ROOT%\backend ^&^& title Backend :8080 ^&^& python main.py
)
timeout /t 4 >nul
echo Backend started: http://localhost:8080

if "%CMD%"=="" pause
if "%CMD%"=="" goto menu
exit /b 0

:: =============================================================
:: [4] Start Frontend only
:: =============================================================
:cmd_frontend
echo.
echo Starting Frontend (port 3000)...
if defined CONDA_PATH (
    start "AI-Law-Frontend" cmd /k call %CONDA_PATH%\Scripts\activate.bat ^&^& conda activate %CONDA_ENV% ^&^& cd /d %ROOT%\frontend ^&^& title Frontend :3000 ^&^& python main.py
) else (
    start "AI-Law-Frontend" cmd /k cd /d %ROOT%\frontend ^&^& title Frontend :3000 ^&^& python main.py
)
timeout /t 2 >nul
echo Frontend started: http://localhost:3000
start http://localhost:3000

if "%CMD%"=="" pause
if "%CMD%"=="" goto menu
exit /b 0

:: =============================================================
:: [5] Stop all services
:: =============================================================
:cmd_stop
echo.
echo Stopping all services...

:: MongoDB
taskkill /fi "WINDOWTITLE eq MongoDB*" /f 2>nul
:: Backend & Frontend
taskkill /fi "WINDOWTITLE eq AI-Law-Backend*" /f 2>nul
taskkill /fi "WINDOWTITLE eq AI-Law-Frontend*" /f 2>nul

:: Fallback: kill by port
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":27017" ^| findstr "LISTENING"') do taskkill /f /pid %%a 2>nul
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8080"  ^| findstr "LISTENING"') do taskkill /f /pid %%a 2>nul
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000"  ^| findstr "LISTENING"') do taskkill /f /pid %%a 2>nul

echo All services stopped.

if "%CMD%"=="" pause
if "%CMD%"=="" goto menu
exit /b 0

:: =============================================================
:: [6] Check service status
:: =============================================================
:cmd_status
echo.
echo ========================================
echo   Service Status
echo ========================================

call :check_port "MongoDB" 27017
call :check_port "Backend" 8080
call :check_port "Frontend" 3000

echo.
if "%CMD%"=="" pause
if "%CMD%"=="" goto menu
exit /b 0

:: =============================================================
:: Helper: Check if port is listening
:: =============================================================
:check_port
netstat -ano | findstr ":%2 " | findstr "LISTENING" >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%2 " ^| findstr "LISTENING"') do (
        echo   [RUNNING] %~1 (port %~2, PID: %%a)
    )
) else (
    echo   [STOPPED] %~1 (port %~2)
)
exit /b 0

:: =============================================================
:: Helper: Ensure MongoDB is running
:: =============================================================
:ensure_mongodb
netstat -ano | findstr ":27017 " | findstr "LISTENING" >nul 2>&1
if %errorlevel% neq 0 (
    echo        MongoDB not running, starting...
    start "MongoDB" cmd /k "cd /d "%ROOT%" && title MongoDB :27017 && node start_mongodb.js"
    timeout /t 3 >nul
)
exit /b 0
