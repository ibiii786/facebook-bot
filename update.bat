@echo off
setlocal enabledelayedexpansion
title Facebook Bot - Auto Updater

echo ========================================================
echo   Facebook Bot - Automatic Update from GitHub
echo ========================================================
echo.
echo This will update your bot to the latest version from GitHub,
echo while PRESERVING all your logged-in Facebook profiles and data.
echo.
echo Data that will be PRESERVED:
echo   - profiles\         (all logged-in Facebook Chrome sessions)
echo   - emails.csv        (your account credentials)
echo   - completed_log.json
echo   - listing_history.json
echo   - flagged_accounts.json
echo   - image_usage_log.json
echo   - account_names.json
echo   - session_state.json
echo.
echo Press any key to start the update (or close this window to cancel)...
pause >nul

:: ── Detect Python ────────────────────────────────────────────────────────────
set "PY_RUN="
if exist "venv\Scripts\python.exe" (
    set "PY_RUN=venv\Scripts\python.exe"
    echo [INFO] Using venv Python: venv\Scripts\python.exe
) else (
    python --version >nul 2>&1
    if !errorlevel! equ 0 (
        set "PY_RUN=python"
        echo [INFO] Using system Python.
    ) else (
        echo [WARNING] Python not found. Dependencies will not be updated automatically.
    )
)

:: ── Try git first (fastest, most reliable) ───────────────────────────────────
git --version >nul 2>&1
if !errorlevel! equ 0 (
    echo.
    echo [1/3] Git detected. Pulling latest code from GitHub...
    echo       Your data files are excluded from git tracking and will not be touched.

    :: stash any local edits to code files only (preserves data files automatically)
    git stash push -m "pre-update stash" -- "*.py" "*.js" "*.html" "*.css" "*.bat" "requirements.txt" >nul 2>&1

    git pull origin main
    if !errorlevel! neq 0 (
        echo [ERROR] git pull failed. Check your internet connection or git config.
        git stash pop >nul 2>&1
        pause
        exit /b 1
    )

    :: restore any stashed local overrides (safe — only code files were stashed)
    git stash pop >nul 2>&1

    echo [2/3] Code update complete!
    goto install_deps
)

:: ── Fallback: download ZIP from GitHub ───────────────────────────────────────
echo.
echo [1/3] Git not found. Downloading latest ZIP from GitHub...
set "REPO_ZIP_URL=https://codeload.github.com/ibiii786/facebook-bot/zip/refs/heads/main"
set "ZIP_FILE=%TEMP%\fb_bot_update_%RANDOM%.zip"
set "TMP_DIR=%TEMP%\fb_bot_update_%RANDOM%"

curl -L --progress-bar -o "%ZIP_FILE%" "%REPO_ZIP_URL%"
if !errorlevel! neq 0 (
    echo [ERROR] Download failed. Check your internet connection.
    pause
    exit /b 1
)
echo Download complete.

:: ── Backup data files before overwriting anything ────────────────────────────
echo.
echo [2/3] Backing up your data files...
set "BACKUP=%TEMP%\fb_bot_backup_%RANDOM%"
mkdir "%BACKUP%" >nul 2>&1

for %%F in (emails.csv completed_log.json listing_history.json flagged_accounts.json image_usage_log.json account_names.json session_state.json) do (
    if exist "%%F" (
        copy /y "%%F" "%BACKUP%\%%F" >nul
        echo       Backed up: %%F
    )
)
if exist "profiles" (
    xcopy "profiles" "%BACKUP%\profiles\" /e /i /h /q /y >nul
    echo       Backed up: profiles\ folder
)
if exist "account_names.json" (
    copy /y "account_names.json" "%BACKUP%\account_names.json" >nul
)
echo       Backup stored in: %BACKUP%

:: ── Extract ZIP ───────────────────────────────────────────────────────────────
echo       Extracting update archive...
mkdir "%TMP_DIR%" >nul 2>&1
powershell -NoProfile -Command "Expand-Archive -LiteralPath '%ZIP_FILE%' -DestinationPath '%TMP_DIR%' -Force" 2>&1
if !errorlevel! neq 0 (
    echo [ERROR] Failed to extract ZIP archive.
    pause
    exit /b 1
)

:: GitHub ZIP extracts into a subfolder named "facebook-bot-main"
set "SRC=%TMP_DIR%\facebook-bot-main"
if not exist "%SRC%" (
    :: Try any subfolder
    for /d %%D in ("%TMP_DIR%\*") do set "SRC=%%D"
)

:: ── Write exclusion list for xcopy ───────────────────────────────────────────
echo profiles\> "%TEMP%\fb_update_excludes.txt"
echo emails.csv>> "%TEMP%\fb_update_excludes.txt"
echo completed_log.json>> "%TEMP%\fb_update_excludes.txt"
echo listing_history.json>> "%TEMP%\fb_update_excludes.txt"
echo flagged_accounts.json>> "%TEMP%\fb_update_excludes.txt"
echo image_usage_log.json>> "%TEMP%\fb_update_excludes.txt"
echo account_names.json>> "%TEMP%\fb_update_excludes.txt"
echo session_state.json>> "%TEMP%\fb_update_excludes.txt"
echo update.bat>> "%TEMP%\fb_update_excludes.txt"

:: ── Copy new code (excluding data files) ─────────────────────────────────────
xcopy "%SRC%\*" "." /e /y /exclude:"%TEMP%\fb_update_excludes.txt" >nul
echo       New code files copied.

:: ── Restore backed-up data ───────────────────────────────────────────────────
for %%F in (emails.csv completed_log.json listing_history.json flagged_accounts.json image_usage_log.json account_names.json session_state.json) do (
    if exist "%BACKUP%\%%F" (
        copy /y "%BACKUP%\%%F" "%%F" >nul
    )
)
if exist "%BACKUP%\profiles" (
    xcopy "%BACKUP%\profiles" "profiles\" /e /i /h /q /y >nul
)
echo       Data files restored.

:: ── Clean up temp files ───────────────────────────────────────────────────────
del "%ZIP_FILE%" >nul 2>&1
del "%TEMP%\fb_update_excludes.txt" >nul 2>&1
rmdir /s /q "%TMP_DIR%" >nul 2>&1

:install_deps
:: ── Install / update Python dependencies ─────────────────────────────────────
echo.
echo [3/3] Installing/updating Python dependencies...
if defined PY_RUN (
    %PY_RUN% -m pip install -r requirements.txt --quiet --disable-pip-version-check
    if !errorlevel! equ 0 (
        echo       Dependencies OK.
    ) else (
        echo [WARNING] pip install had errors - check requirements.txt or internet connection.
    )
) else (
    echo [SKIP] Python not found, skipping dependency update.
)

echo.
echo ========================================================
echo   Update COMPLETE!
echo.
echo   - All your logged-in Facebook profiles are preserved.
echo   - Your emails.csv and other data are intact.
echo.
echo   Run start_bot.bat to launch the updated bot.
echo ========================================================
echo.
pause

