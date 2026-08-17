@echo off
setlocal enabledelayedexpansion
title Facebook Marketplace Bot - Local Server
echo ========================================================
echo   Launching Facebook Marketplace Bot (Localhost)
echo ========================================================
echo.

:: 1. Determine Python executable
set "PY_RUN="

if exist "venv\Scripts\python.exe" (
    set "PY_RUN=venv\Scripts\python.exe"
    goto :START_SERVER
)

:: Fallback check standard python
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_RUN=python"
    goto :START_SERVER
)

:: Fallback check py launcher
py -3.11 --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_RUN=py -3.11"
    goto :START_SERVER
)

py -3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_RUN=py -3"
    goto :START_SERVER
)

:: Check User AppData paths
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PY_RUN=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    goto :START_SERVER
)

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PY_RUN=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :START_SERVER
)

:: Check Program Files paths
if exist "C:\Program Files\Python311\python.exe" (
    set "PY_RUN=C:\Program Files\Python311\python.exe"
    goto :START_SERVER
)

if exist "C:\Program Files\Python312\python.exe" (
    set "PY_RUN=C:\Program Files\Python312\python.exe"
    goto :START_SERVER
)

:START_SERVER
if "%PY_RUN%"=="" (
    echo [ERROR] Python environment not found!
    echo Please double-click 'setup.bat' first to install the environment.
    echo.
    pause
    exit /b 1
)

echo Using Python: %PY_RUN%
echo.

:: 2. Verify dependencies
%PY_RUN% -c "import fastapi, uvicorn, selenium, pandas" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Required libraries are not installed in this environment.
    echo.
    echo Please double-click 'setup.bat' first to install all dependencies.
    echo.
    pause
    exit /b 1
)

:: 3. Automatically open default browser after 2 seconds
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://127.0.0.1:8000"

:: 4. Launch server
%PY_RUN% server.py

if %errorlevel% neq 0 (
    echo.
    echo ========================================================
    echo [ERROR] Server stopped unexpectedly.
    echo ========================================================
    echo.
    pause
)



