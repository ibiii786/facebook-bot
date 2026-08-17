@echo off
title Facebook Bot - Environment Setup
echo ========================================================
echo   Facebook Marketplace Bot - Automatic Environment Setup
echo ========================================================
echo.

:: 1. Detect Python
set "PYTHON_EXE="

python --version >nul 2>&1
if %errorlevel% equ 0 set "PYTHON_EXE=python"

if "%PYTHON_EXE%"=="" (
    py -3.11 --version >nul 2>&1
    if %errorlevel% equ 0 set "PYTHON_EXE=py -3.11"
)

if "%PYTHON_EXE%"=="" (
    py -3 --version >nul 2>&1
    if %errorlevel% equ 0 set "PYTHON_EXE=py -3"
)

if "%PYTHON_EXE%"=="" (
    if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
)

if "%PYTHON_EXE%"=="" (
    if exist "C:\Program Files\Python311\python.exe" set "PYTHON_EXE=C:\Program Files\Python311\python.exe"
)

if "%PYTHON_EXE%"=="" (
    echo [ERROR] Python was not detected on your system.
    echo.
    echo Please make sure you installed Python 3.11 from:
    echo   https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
    echo.
    echo And make sure "Add python.exe to PATH" was checked.
    echo.
    pause
    exit /b 1
)

echo [1/3] Using Python: %PYTHON_EXE%
call %PYTHON_EXE% --version
echo.

:: 2. Create Virtual Environment
echo [2/3] Preparing virtual environment (venv)...
if not exist "venv\Scripts\python.exe" (
    if exist "venv" rmdir /s /q "venv" >nul 2>&1
    call %PYTHON_EXE% -m venv venv
)

if exist "venv\Scripts\python.exe" (
    echo Virtual environment created successfully.
    set "PY_CMD=venv\Scripts\python.exe"
) else (
    echo [NOTE] Using direct Python executable.
    set "PY_CMD=%PYTHON_EXE%"
)
echo.

:: 3. Install packages
echo [3/3] Installing required libraries (this takes ~15-30 seconds)...
echo.
call %PY_CMD% -m pip install --upgrade pip
call %PY_CMD% -m pip install -r requirements.txt

echo.
echo ========================================================
echo   [SUCCESS] Setup Completed!
echo   You can now launch the bot using 'start_bot.bat'
echo ========================================================
echo.
pause



