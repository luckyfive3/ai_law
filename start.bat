@echo off
chcp 65001 >nul 2>nul
setlocal enabledelayedexpansion

:: =============================================================
:: AI法律助手 v1.0 — Windows start script
:: Usage: start.bat [install|start|stop|restart|status|dev]
:: =============================================================

set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
cd /d "%ROOT%"

set "CONDA_ENV=law"

:: Parse command argument
set "CMD=%~1"
if "%CMD%"=="" goto menu
if /i "%CMD%"=="install"  goto cmd_install
if /i "%CMD%"=="start"    goto cmd_start
if /i "%CMD%"=="backend"  goto cmd_backend
if /i "%CMD%"=="frontend" goto cmd_frontend
if /i "%CMD%"=="stop"     goto cmd_stop
if /i "%CMD%"=="restart"  goto cmd_restart
if /i "%CMD%"=="status"   goto cmd_status
if /i "%CMD%"=="dev"      goto cmd_dev
echo [ERROR] Unknown: %CMD%
echo Usage: start.bat [install^|start^|stop^|restart^|status^|dev]
pause
exit /b 1

:: =============================================================
:: Menu
:: =============================================================
:menu
cls
echo.
echo  ========================================
echo     AI Law Assistant v1.0 - Menu
echo  ========================================
echo.
echo    [1] Install dependencies
echo    [2] Start ALL (MongoDB + Backend + Frontend)
echo    [3] Start Backend only   (port 8080)
echo    [4] Start Frontend only  (port 3000)
echo    [5] Stop all services
echo    [6] Restart all services
echo    [7] Check service status
echo    [8] Dev mode (hot reload)
echo    [0] Quit
echo  ========================================
echo.
set /p CHOICE="Enter option: "

if "%CHOICE%"=="1" goto cmd_install
if "%CHOICE%"=="2" goto cmd_start
if "%CHOICE%"=="3" goto cmd_backend
if "%CHOICE%"=="4" goto cmd_frontend
if "%CHOICE%"=="5" goto cmd_stop
if "%CHOICE%"=="6" goto cmd_restart
if "%CHOICE%"=="7" goto cmd_status
if "%CHOICE%"=="8" goto cmd_dev
if "%CHOICE%"=="0" exit /b 0
echo Invalid option
timeout /t 1 >nul
goto menu

:: =============================================================
:: Environment Detection
:: =============================================================
:detect_env
echo [DETECT] Checking environment...

set "PYTHON_CMD="
set "CONDA_PATH="

rem Find conda
for %%p in (anaconda3 Anaconda3 miniconda3 Miniconda3) do (
    if exist "%USERPROFILE%\%%p\Scripts\conda.exe" set "CONDA_PATH=%USERPROFILE%\%%p"
)
if exist "C:\ProgramData\anaconda3\Scripts\conda.exe" set "CONDA_PATH=C:\ProgramData\anaconda3"
if exist "C:\ProgramData\miniconda3\Scripts\conda.exe" set "CONDA_PATH=C:\ProgramData\miniconda3"

if defined CONDA_PATH (
    "%CONDA_PATH%\Scripts\conda.exe" run -n %CONDA_ENV% python --version >nul 2>&1
    if !errorlevel! equ 0 (
        set "PYTHON_CMD=%CONDA_PATH%\Scripts\conda.exe run -n %CONDA_ENV% python"
        echo   [OK] Python (conda: %CONDA_ENV%)
        goto detect_node
    )
    echo   [WARN] conda env '%CONDA_ENV%' not found, trying system Python
)

where python >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON_CMD=python"
    echo   [OK] Python (system)
    goto detect_node
)

echo   [ERROR] Python not found
echo   Install Python 3.11+ or: conda create -n %CONDA_ENV% python=3.11
pause
exit /b 1

:detect_node
set "NODE_EXE="
where node >nul 2>&1
if !errorlevel! equ 0 set "NODE_EXE=node"
if not defined NODE_EXE if exist "C:\Program Files\nodejs\node.exe" set "NODE_EXE=C:\Program Files\nodejs\node.exe"
if not defined NODE_EXE if exist "%USERPROFILE%\scoop\apps\nodejs\current\node.exe" set "NODE_EXE=%USERPROFILE%\scoop\apps\nodejs\current\node.exe"
if defined NODE_EXE (
    for /f "tokens=*" %%v in ('"%NODE_EXE%" -v 2^>nul') do (
        echo   [OK] Node.js %%v
        set "NPM_CMD=%NODE_EXE:\node.exe=\npm.cmd%"
        if not exist "!NPM_CMD!" set "NPM_CMD=npm"
    )
) else (
    echo   [WARN] Node.js not found, MongoDB memory server won't work
)

rem --- .env check ---
if not exist "%ROOT%\backend\.env" (
    if exist "%ROOT%\.env.example" (
        echo   [WARN] backend\.env missing, copying from .env.example
        copy "%ROOT%\.env.example" "%ROOT%\backend\.env" >nul
        echo   [TODO] Edit backend\.env and set DEEPSEEK_API_KEY, JWT_SECRET
    )
)

rem --- npm deps ---
if not exist "%ROOT%\node_modules\mongodb-memory-server" (
    if exist "%ROOT%\package.json" (
        if defined NPM_CMD (
            echo   [ACTION] Installing mongodb-memory-server...
            call "!NPM_CMD!" install mongodb-memory-server@10.1.0 --save 2>nul
        if !errorlevel! neq 0 (
            echo   [WARN] npm install failed
        ) else (
            echo   [OK] npm dependency installed
        )
    )
)

rem --- logs dir ---
if not exist "%ROOT%\logs" mkdir "%ROOT%\logs"

echo   [OK] Environment ready
echo.
exit /b 0

:: =============================================================
:: [1] Install dependencies
:: =============================================================
:cmd_install
cls
echo ========================================
echo   Install Dependencies
echo ========================================
echo.

call :detect_env

echo [1/3] Installing backend Python deps...
%PYTHON_CMD% -m pip install -r "%ROOT%\backend\requirements.txt" --quiet
if !errorlevel! neq 0 (
    echo   [ERROR] Backend install failed
    goto install_done
)
echo   [OK] Backend deps

echo [2/3] Installing frontend Python deps...
%PYTHON_CMD% -m pip install -r "%ROOT%\frontend\requirements.txt" --quiet
if !errorlevel! neq 0 (
    echo   [ERROR] Frontend install failed
    goto install_done
)
echo   [OK] Frontend deps

echo [3/3] Installing Node.js deps...
if exist "%ROOT%\package.json" (
    call npm install 2>nul
    echo   [OK] Node.js deps
) else (
    echo   [SKIP] No package.json
)

echo.
echo [DONE] All dependencies installed

:install_done
cd /d "%ROOT%"
if "%CMD%"=="install" (pause & exit /b 0)
pause
goto menu

:: =============================================================
:: Helper: start MongoDB
:: =============================================================
:start_mongodb
netstat -ano | findstr ":27017 " | findstr "LISTENING" >nul 2>&1
if !errorlevel! equ 0 (
    echo   MongoDB already running
    exit /b 0
)
if not exist "%ROOT%\start_mongodb.js" (
    echo   [WARN] start_mongodb.js missing
    exit /b 1
)
if defined NODE_EXE (start "MongoDB" cmd /c "cd /d "%ROOT%" && title MongoDB :27017 && "%NODE_EXE%" start_mongodb.js") else (echo   [ERROR] Node.js required for MongoDB)
timeout /t 4 >nul
exit /b 0

:: =============================================================
:: Helper: start Backend
:: =============================================================
:start_backend
if defined CONDA_PATH (
    start "AI-Law-Backend" cmd /c "call "%CONDA_PATH%\Scripts\activate.bat" && conda activate %CONDA_ENV% && cd /d "%ROOT%\backend" && title Backend :8080 && python main.py"
) else (
    start "AI-Law-Backend" cmd /c "cd /d "%ROOT%\backend" && title Backend :8080 && python main.py"
)
timeout /t 4 >nul
exit /b 0

:: =============================================================
:: Helper: start Frontend
:: =============================================================
:start_frontend
if defined CONDA_PATH (
    start "AI-Law-Frontend" cmd /c "call "%CONDA_PATH%\Scripts\activate.bat" && conda activate %CONDA_ENV% && cd /d "%ROOT%\frontend" && title Frontend :3000 && python main.py"
) else (
    start "AI-Law-Frontend" cmd /c "cd /d "%ROOT%\frontend" && title Frontend :3000 && python main.py"
)
timeout /t 2 >nul
exit /b 0

:: =============================================================
:: Helper: ensure MongoDB
:: =============================================================
:ensure_mongodb
netstat -ano | findstr ":27017 " | findstr "LISTENING" >nul 2>&1
if !errorlevel! neq 0 (
    echo   Starting MongoDB...
    call :start_mongodb
)
exit /b 0

:: =============================================================
:: Helper: health check
:: =============================================================
:health_check
netstat -ano | findstr ":%1 " | findstr "LISTENING" >nul 2>&1
if !errorlevel! equ 0 (
    echo   [OK] %~2 (port %1)
) else (
    echo   [WARN] %~2 not ready on port %1
)
exit /b 0

:: =============================================================
:: Helper: check port status
:: =============================================================
:check_port
netstat -ano | findstr ":%2 " | findstr "LISTENING" >nul 2>&1
if !errorlevel! equ 0 (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%2 " ^| findstr "LISTENING"') do (
        echo   [RUNNING] %~1 (port %~2, PID: %%a)
    )
) else (
    echo   [STOPPED] %~1 (port %~2)
)
exit /b 0

:: =============================================================
:: Helper: kill port
:: =============================================================
:kill_port
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%1 " ^| findstr "LISTENING" 2^>nul') do (
    taskkill /f /pid %%a >nul 2>&1
    if !errorlevel! equ 0 echo   Killed %~2 (PID %%a)
)
exit /b 0

:: =============================================================
:: [2] Start ALL
:: =============================================================
:cmd_start
cls
echo ========================================
echo   Start All Services
echo ========================================
echo.

call :detect_env

echo [1/3] Starting MongoDB...
call :start_mongodb

echo [2/3] Starting Backend...
call :start_backend

echo [3/3] Starting Frontend...
call :start_frontend

echo.
echo Waiting for services...
timeout /t 5 >nul
call :health_check 8080 "Backend"
call :health_check 3000 "Frontend"

start http://localhost:3000

echo.
echo ========================================
echo   All services started
echo   Frontend: http://localhost:3000
echo   Backend:  http://localhost:8080
echo ========================================

:start_done
if "%CMD%"=="start" (pause & exit /b 0)
pause
goto menu

:: =============================================================
:: [3] Start Backend
:: =============================================================
:cmd_backend
cls
echo ========================================
echo   Start Backend
echo ========================================
echo.

call :detect_env
call :ensure_mongodb
call :start_backend
timeout /t 3 >nul
call :health_check 8080 "Backend"
echo Backend: http://localhost:8080

if "%CMD%"=="backend" (pause & exit /b 0)
pause
goto menu

:: =============================================================
:: [4] Start Frontend
:: =============================================================
:cmd_frontend
cls
echo ========================================
echo   Start Frontend
echo ========================================
echo.

call :detect_env
call :start_frontend
timeout /t 2 >nul
call :health_check 3000 "Frontend"
start http://localhost:3000

if "%CMD%"=="frontend" (pause & exit /b 0)
pause
goto menu

:: =============================================================
:: [5] Stop all
:: =============================================================
:cmd_stop
cls
echo Stopping all services...
echo.

taskkill /fi "WINDOWTITLE eq MongoDB*" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq AI-Law-Backend*" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq AI-Law-Frontend*" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq Backend-Dev*" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq Frontend-Dev*" /f >nul 2>&1

call :kill_port 27017 "MongoDB"
call :kill_port 8080  "Backend"
call :kill_port 3000  "Frontend"

echo All services stopped.

if "%CMD%"=="stop" (pause & exit /b 0)
pause
goto menu

:: =============================================================
:: [6] Restart
:: =============================================================
:cmd_restart
call :cmd_stop
timeout /t 2 >nul
call :cmd_start
exit /b 0

:: =============================================================
:: [7] Status
:: =============================================================
:cmd_status
cls
echo ========================================
echo   Service Status
echo ========================================
echo.
call :check_port "MongoDB" 27017
call :check_port "Backend"  8080
call :check_port "Frontend" 3000
echo.

if "%CMD%"=="status" (pause & exit /b 0)
pause
goto menu

:: =============================================================
:: [8] Dev mode (hot reload)
:: =============================================================
:cmd_dev
cls
echo ========================================
echo   Dev Mode (hot reload)
echo   Ctrl+C to stop, code changes auto-restart
echo ========================================
echo.

call :detect_env
call :ensure_mongodb

echo Starting Backend with hot reload...
if defined CONDA_PATH (
    start "Backend-Dev" cmd /c "call "%CONDA_PATH%\Scripts\activate.bat" && conda activate %CONDA_ENV% && cd /d "%ROOT%\backend" && title Backend-Dev :8080 && uvicorn main:app --host 0.0.0.0 --port 8080 --reload"
) else (
    start "Backend-Dev" cmd /c "cd /d "%ROOT%\backend" && title Backend-Dev :8080 && uvicorn main:app --host 0.0.0.0 --port 8080 --reload"
)

echo Starting Frontend with hot reload...
if defined CONDA_PATH (
    start "Frontend-Dev" cmd /c "call "%CONDA_PATH%\Scripts\activate.bat" && conda activate %CONDA_ENV% && cd /d "%ROOT%\frontend" && title Frontend-Dev :3000 && uvicorn main:app --host 0.0.0.0 --port 3000 --reload"
) else (
    start "Frontend-Dev" cmd /c "cd /d "%ROOT%\frontend" && title Frontend-Dev :3000 && uvicorn main:app --host 0.0.0.0 --port 3000 --reload"
)

timeout /t 4 >nul
start http://localhost:3000

echo.
echo Dev mode started:
echo   Backend:  http://localhost:8080 (auto-reload)
echo   Frontend: http://localhost:3000 (auto-reload)

if "%CMD%"=="dev" (pause & exit /b 0)
pause
goto menu
