@echo off
setlocal enabledelayedexpansion
title Facebook Bot - Automatic Environment Setup
echo ========================================================
echo   Facebook Marketplace Bot - Automatic Environment Setup
echo ========================================================
echo.

:: 1. Find Python executable (checks py launcher, standard python, and default install locations)
set "PYTHON_EXE="

:: Check standard 'python'
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_EXE=python"
    goto :FOUND_PYTHON
)

:: Check Python Launcher 'py -3.11'
py -3.11 --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_EXE=py -3.11"
    goto :FOUND_PYTHON
)

:: Check Python Launcher 'py'
py -3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_EXE=py -3"
    goto :FOUND_PYTHON
)

:: Check Default User AppData Path for Python 3.11
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    goto :FOUND_PYTHON
)

:: Check Default User AppData Path for Python 3.12
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :FOUND_PYTHON
)

:: Check Program Files Path
if exist "C:\Program Files\Python311\python.exe" (
    set "PYTHON_EXE=C:\Program Files\Python311\python.exe"
    goto :FOUND_PYTHON
)

if exist "C:\Program Files\Python312\python.exe" (
    set "PYTHON_EXE=C:\Program Files\Python312\python.exe"
    goto :FOUND_PYTHON
)

:: If not found:
echo [ERROR] Python was not found on your system!
echo.
echo If you just installed Python 3.11, please RESTART your PC or ensure you checked:
echo   [x] "Add python.exe to PATH" during installation.
echo.
echo You can download the official Python 3.11.9 installer here:
echo   https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
echo.
pause
exit /b 1

:FOUND_PYTHON
echo [1/3] Python detected: %PYTHON_EXE%
%PYTHON_EXE% --version
echo.

:: 2. Clean and Create Virtual Environment
echo [2/3] Preparing isolated Python virtual environment (venv)...
if exist "venv" (
    echo Cleaning previous environment...
    rmdir /s /q "venv" >nul 2>&1
)

%PYTHON_EXE% -m venv venv
if not exist "venv\Scripts\python.exe" (
    echo.
    echo [ERROR] Failed to create virtual environment!
    echo Attempting direct installation with %PYTHON_EXE%...
) else (
    echo Virtual environment (venv) created successfully.
)
echo.

:: 3. Install Requirements
echo [3/3] Installing and upgrading required libraries...
if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe -m pip install --upgrade pip
    venv\Scripts\python.exe -m pip install -r requirements.txt
    if !errorlevel! neq 0 (
        echo.
        echo [ERROR] Package installation failed. Please check your internet connection.
        echo.
        pause
        exit /b 1
    )
) else (
    %PYTHON_EXE% -m pip install --upgrade pip
    %PYTHON_EXE% -m pip install -r requirements.txt
)

echo.
echo ========================================================
echo   [SUCCESS] Setup Completed Flawlessly!
echo   You can now launch the bot anytime using 'start_bot.bat'
echo ========================================================
echo.
pause


