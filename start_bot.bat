@echo off
title Facebook Marketplace Bot - Local Server
echo ========================================================
echo   Launching Facebook Marketplace Bot (Localhost)
echo ========================================================
echo.

:: Check if virtual environment exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo [NOTE] Running with global Python installation...
)

:: Auto-open browser after 2 seconds in the background
start "" /b powershell -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:8000'"

:: Launch the FastAPI/Uvicorn server
python server.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Server encountered an issue and stopped.
    echo If this is a new PC, please make sure you ran 'setup.bat' first.
    echo.
    pause
)
