@echo off
title Facebook Bot - Environment Setup
echo ========================================================
echo   Facebook Marketplace Bot - Automatic Environment Setup
echo ========================================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to your system PATH!
    echo.
    echo Please download and install Python 3.10, 3.11, or 3.12 from:
    echo   https://www.python.org/downloads/
    echo.
    echo IMPORTANT: Make sure to check the box "Add Python to PATH" during installation!
    echo.
    pause
    exit /b 1
)

echo [1/3] Python detected successfully.
echo.

:: Create virtual environment if it doesn't exist
if not exist "venv" (
    echo [2/3] Creating isolated Python virtual environment (venv)...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo [2/3] Virtual environment (venv) already exists.
)
echo.

:: Install / upgrade dependencies
echo [3/3] Installing and verifying required packages...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Package installation failed. Please check your internet connection.
    pause
    exit /b 1
)

echo.
echo ========================================================
echo   [SUCCESS] Setup Completed Flawlessly!
echo   You can now launch the bot anytime using 'start_bot.bat'
echo ========================================================
echo.
pause
