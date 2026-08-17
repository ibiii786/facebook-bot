@echo off
title Facebook Marketplace Bot - Local Server
echo ========================================================
echo   Launching Facebook Marketplace Bot (Localhost)
echo ========================================================
echo.

:: 1. Detect Python
set "PY_RUN="

if exist "venv\Scripts\python.exe" (
    set "PY_RUN=venv\Scripts\python.exe"
)

if "%PY_RUN%"=="" (
    python --version >nul 2>&1
    if %errorlevel% equ 0 set "PY_RUN=python"
)

if "%PY_RUN%"=="" (
    py -3.11 --version >nul 2>&1
    if %errorlevel% equ 0 set "PY_RUN=py -3.11"
)

if "%PY_RUN%"=="" (
    py -3 --version >nul 2>&1
    if %errorlevel% equ 0 set "PY_RUN=py -3"
)

if "%PY_RUN%"=="" (
    if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PY_RUN=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
)

if "%PY_RUN%"=="" (
    if exist "C:\Program Files\Python311\python.exe" set "PY_RUN=C:\Program Files\Python311\python.exe"
)

if "%PY_RUN%"=="" (
    echo [ERROR] Python environment not found!
    echo Please run 'setup.bat' first.
    echo.
    pause
    exit /b 1
)

:: 2. Verify dependencies (auto-install if missing)
call %PY_RUN% -c "import fastapi, uvicorn, selenium, pandas" >nul 2>&1
if %errorlevel% neq 0 (
    echo [NOTE] Installing required libraries now...
    call %PY_RUN% -m pip install -r requirements.txt
)

:: 3. Automatically open browser after 2 seconds
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://127.0.0.1:8000"

:: 4. Launch server
call %PY_RUN% server.py

if %errorlevel% neq 0 (
    echo.
    echo ========================================================
    echo [ERROR] Server stopped unexpectedly.
    echo ========================================================
    echo.
    pause
)




