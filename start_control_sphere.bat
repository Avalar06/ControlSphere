@echo off
setlocal EnableDelayedExpansion

:: =============================================================================
:: ControlSphere — One-Click Windows Startup Launcher
:: Enterprise GRC & Cybersecurity Governance Platform
:: =============================================================================

title ControlSphere Launcher
echo ===============================================================================
echo                 CONTROLSPHERE LOCAL ENVIRONMENT LAUNCHER
echo ===============================================================================
echo.

:: 1. Dynamic Root Directory Resolution
set "ROOT_DIR=%~dp0"
if "%ROOT_DIR:~-1%"=="\" set "ROOT_DIR=%ROOT_DIR:~0,-1%"

set "BACKEND_DIR=%ROOT_DIR%\backend"
set "FRONTEND_DIR=%ROOT_DIR%\frontend"
set "BACKEND_PORT=8000"
set "FRONTEND_PORT=5173"

echo [*] Workspace Root: "%ROOT_DIR%"
echo.

:: [1/5] Checking prerequisites: Node.js and npm
echo [1/5] Checking prerequisites...
where node >nul 2>&1
if !errorlevel! neq 0 (
    echo [ERROR] Node.js was not found on PATH.
    echo Please install Node.js v18+ to run the frontend.
    pause
    exit /b 1
)

where npm >nul 2>&1
if !errorlevel! neq 0 (
    echo [ERROR] npm was not found on PATH.
    pause
    exit /b 1
)
echo      [+] Node.js and npm runtime verified.

:: [2/5] Verifying Python virtual environment
echo [2/5] Checking Python environment...
set "PYTHON_EXE="
if exist "%BACKEND_DIR%\venv\Scripts\python.exe" (
    set "PYTHON_EXE=%BACKEND_DIR%\venv\Scripts\python.exe"
    echo      [+] Detected dedicated virtual environment: "%BACKEND_DIR%\venv"
) else (
    if exist "%ROOT_DIR%\.venv\Scripts\python.exe" (
        set "PYTHON_EXE=%ROOT_DIR%\.venv\Scripts\python.exe"
        echo      [+] Detected virtual environment: "%ROOT_DIR%\.venv"
    ) else (
        where python >nul 2>&1
        if !errorlevel! equ 0 (
            set "PYTHON_EXE=python"
            echo      [!] Warning: Dedicated venv not found. Using system Python.
        ) else (
            echo [ERROR] Python executable not found in backend\venv, .venv, or system PATH.
            echo Please ensure Python 3.11+ is installed.
            pause
            exit /b 1
        )
    )
)

:: [3/5] Verifying frontend dependencies
echo [3/5] Checking frontend dependencies...
if not exist "%FRONTEND_DIR%\node_modules" (
    echo      [!] node_modules not found in "%FRONTEND_DIR%".
    echo      [*] Installing frontend dependencies via npm install...
    pushd "%FRONTEND_DIR%"
    call npm install
    popd
    if !errorlevel! neq 0 (
        echo [ERROR] npm install failed. Please check your network connection and npm configuration.
        pause
        exit /b 1
    )
    echo      [+] Frontend dependencies successfully installed.
) else (
    echo      [+] Frontend dependencies verified: node_modules present.
)

:: [4/5] Checking port availability and running instances
echo [4/5] Checking port availability...
set "BACKEND_ACTIVE=0"
set "FRONTEND_ACTIVE=0"

netstat -ano | findstr /R /C:":8000 .*LISTENING" >nul 2>&1
if !errorlevel! equ 0 (
    set "BACKEND_ACTIVE=1"
    echo      [!] Backend is already active and listening on port 8000. Skipping launch.
) else (
    echo      [+] Port 8000 is available for backend.
)

netstat -ano | findstr /R /C:":5173 .*LISTENING" >nul 2>&1
if !errorlevel! equ 0 (
    set "FRONTEND_ACTIVE=1"
    echo      [!] Frontend is already active and listening on port 5173. Skipping launch.
) else (
    echo      [+] Port 5173 is available for frontend.
)

:: [5/5] Launching backend and frontend in separate terminals
echo [5/5] Starting ControlSphere services...

if "!BACKEND_ACTIVE!"=="0" (
    echo      [*] Launching FastAPI Backend on http://127.0.0.1:8000...
    start "ControlSphere Backend" cmd /k "cd /d "%BACKEND_DIR%" && title ControlSphere Backend && "%PYTHON_EXE%" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
) else (
    echo      [*] Backend process is already running.
)

if "!FRONTEND_ACTIVE!"=="0" (
    echo      [*] Launching React/Vite Frontend on http://localhost:5173...
    start "ControlSphere Frontend" cmd /k "cd /d "%FRONTEND_DIR%" && title ControlSphere Frontend && npm run dev"
) else (
    echo      [*] Frontend process is already running.
)

:: Summary Display
echo.
echo ===============================================================================
echo                 CONTROLSPHERE STARTUP SEQUENCE COMPLETED
echo ===============================================================================
echo.
echo  Workspace Directory : %ROOT_DIR%
echo  Backend Terminal    : Port %BACKEND_PORT% [FastAPI]
echo  Frontend Terminal   : Port %FRONTEND_PORT% [React / Vite]
echo.
echo  Application URLs:
echo  -----------------------------------------------------------------------------
echo  [+] Frontend App    : http://localhost:5173
echo  [+] Backend API     : http://127.0.0.1:8000
echo  [+] API Docs (Docs) : http://127.0.0.1:8000/api/v1/docs
echo  [+] OpenAPI Spec    : http://127.0.0.1:8000/api/v1/openapi.json
echo  [+] Health Check    : http://127.0.0.1:8000/health
echo.
echo  Authentication Notice:
echo  -----------------------------------------------------------------------------
echo  Demo accounts are available on the ControlSphere login page.
echo.
echo  Terminal windows remain active for live logs and hot reloading.
echo  To safely stop all ControlSphere services, execute stop_control_sphere.bat.
echo ===============================================================================
echo.

endlocal
