@echo off
setlocal EnableDelayedExpansion

:: -----------------------------------------------------------------------------
:: ControlSphere — Safe Port-Targeted Process Stopper
:: Terminates ONLY processes listening on ControlSphere ports (8000 and 5173)
:: -----------------------------------------------------------------------------

title ControlSphere Stopper
echo ===============================================================================
echo                CONTROLSPHERE SERVICE TERMINATION UTILITY
echo ===============================================================================
echo.

set "STOPPED_ANY=0"

:: Targeted termination for Backend listening on port 8000
echo [*] Checking for active ControlSphere processes on port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /R /C:":8000 .*LISTENING"') do (
    set "TARGET_PID=%%a"
    if not "!TARGET_PID!"=="0" (
        echo [*] Stopping backend process on PID !TARGET_PID!...
        taskkill /PID !TARGET_PID! /T /F >nul 2>&1
        set "STOPPED_ANY=1"
    )
)

:: Targeted termination for Frontend listening on port 5173
echo [*] Checking for active ControlSphere processes on port 5173...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /R /C:":5173 .*LISTENING"') do (
    set "TARGET_PID=%%a"
    if not "!TARGET_PID!"=="0" (
        echo [*] Stopping frontend process on PID !TARGET_PID!...
        taskkill /PID !TARGET_PID! /T /F >nul 2>&1
        set "STOPPED_ANY=1"
    )
)

if "!STOPPED_ANY!"=="1" (
    echo.
    echo [SUCCESS] ControlSphere processes stopped successfully.
) else (
    echo.
    echo [*] No active ControlSphere services found running on ports 8000 or 5173.
)

echo.
echo ===============================================================================
endlocal
