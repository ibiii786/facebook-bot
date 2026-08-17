@echo off
title Facebook Marketplace Bot - Local Server
echo ========================================================
echo   Launching Facebook Marketplace Bot (Localhost)
echo ========================================================
echo.

:: Activate virtual environment if present
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

:: Automatically open default browser to localhost after 2 seconds
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://127.0.0.1:8000"

:: Launch server
python server.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Server encountered an issue and stopped.
    echo If this is a new PC, please make sure you ran 'setup.bat' first.
    echo.
    pause
)

