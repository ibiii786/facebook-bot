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
    echo Please download and install the official Python 3.11 or 3.12 64-bit installer:
    echo   https://www.python.org/downloads/release/python-3.119/
    echo.
    echo IMPORTANT: Make sure to check the box "Add python.exe to PATH" during installation!
    echo.
    pause
    exit /b 1
)

:: Display detected python version
for /f "tokens=*" %%i in ('python --version') do set PY_VER=%%i
echo [1/3] %PY_VER% detected.

:: Warn against Python 3.13+ or 3.14 pre-release
echo %PY_VER% | findstr /i "3.14 3.13" >nul
if %errorlevel% equ 0 (
    echo.
    echo ⚠️ [WARNING] You are using an experimental or unsupported Python version (%PY_VER%).
    echo Many essential data libraries (pandas, Pillow, selenium) do NOT support Python 3.14 yet
    echo and will fail to install without a full Visual C++ compiler toolchain.
    echo.
    echo Recommended Fix:
    echo 1. Uninstall Python 3.14 (or the Windows Store MSIX package).
    echo 2. Download and install standard Python 3.11.9 (64-bit Windows Installer):
    echo    https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
    echo 3. Check "Add python.exe to PATH" during installation.
    echo.
    echo Press any key if you still wish to attempt setup, or close this window to install Python 3.11...
    pause
)
echo.

:: Create virtual environment if it doesn't exist
if not exist "venv\Scripts\python.exe" (
    if exist "venv" rmdir /s /q "venv"
    echo [2/3] Creating isolated Python virtual environment (venv)...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo.
        echo [ERROR] Failed to create virtual environment!
        echo This often happens with Windows Store (MSIX) Python installations.
        echo Please install standard Python 3.11 64-bit from python.org.
        echo.
        pause
        exit /b 1
    )
) else (
    echo [2/3] Virtual environment (venv) found and ready.
)
echo.

:: Install / upgrade dependencies inside the venv
echo [3/3] Installing and verifying required packages...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Package installation failed!
    echo If building packages (like pandas or Pillow) failed, please install Python 3.11.9:
    echo   https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
    echo.
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

