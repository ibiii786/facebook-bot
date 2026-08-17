@echo off
title Facebook Marketplace Bot - Local Server
echo ========================================================
echo   Launching Facebook Marketplace Bot (Localhost)
echo ========================================================
echo.

:: Detect Python executable
set "PY_CMD=python"
if exist "venv\Scripts\python.exe" (
    set "PY_CMD=venv\Scripts\python.exe"
    call venv\Scripts\activate.bat
)

:: Verify dependencies before starting
%PY_CMD% -c "import fastapi, uvicorn, selenium, pandas" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Required libraries are missing or corrupt in this environment!
    echo.
    echo Please run 'setup.bat' to install all required dependencies.
    echo.
    pause
    exit /b 1
)

:: Automatically open default browser to localhost after 2 seconds
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://127.0.0.1:8000"

:: Launch server
%PY_CMD% server.py

if %errorlevel% neq 0 (
    echo.
    echo ========================================================
    echo [ERROR] Server stopped unexpectedly.
    echo See the error message above for details.
    echo ========================================================
    echo.
    pause
)


