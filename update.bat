@echo off
setlocal enabledelayedexpansion
title Facebook Bot - Migrate Data from Old Bot

echo ============================================================
echo   Facebook Bot - Migrate Data from Old Bot
echo ============================================================
echo.
echo This tool copies your logged-in Facebook profiles and all
echo data files from your OLD bot folder into THIS (new) bot folder.
echo.
echo After running this, the new bot will have:
echo   - All your logged-in Facebook Chrome profiles (no re-login needed)
echo   - Your emails.csv (account list)
echo   - Your completed_log.json, listing_history.json
echo   - All other saved data
echo.
echo ============================================================

:: Ask for old bot folder path
echo.
set "OLD_BOT="
set /p OLD_BOT=Enter the FULL path to your OLD bot folder (e.g. C:\Users\You\Downloads\facebook-bot-old): 

if not defined OLD_BOT (
    echo [ERROR] No path entered. Exiting.
    pause
    exit /b 1
)

:: Remove trailing backslash if present
if "!OLD_BOT:~-1!"=="\" set "OLD_BOT=!OLD_BOT:~0,-1!"

:: Validate the folder
if not exist "!OLD_BOT!" (
    echo [ERROR] Folder not found: !OLD_BOT!
    echo Please double-check the path and try again.
    pause
    exit /b 1
)

:: Confirm with user
echo.
echo Old bot folder : !OLD_BOT!
echo New bot folder : %~dp0
echo.
echo The following data will be copied over:
echo   - profiles\         (logged-in Chrome sessions)
echo   - emails.csv
echo   - completed_log.json
echo   - listing_history.json
echo   - flagged_accounts.json
echo   - image_usage_log.json
echo   - account_names.json
echo   - session_state.json
echo.
echo Any existing files in this new bot will be OVERWRITTEN by the old bot's data.
echo.
set /p CONFIRM=Are you sure? Type YES to continue: 

if /i not "!CONFIRM!"=="YES" (
    echo Cancelled. No files were changed.
    pause
    exit /b 0
)

echo.
echo [1/2] Copying data files from old bot...

:: Copy individual data files
set "COPIED=0"
for %%F in (emails.csv completed_log.json listing_history.json flagged_accounts.json image_usage_log.json account_names.json session_state.json) do (
    if exist "!OLD_BOT!\%%F" (
        copy /y "!OLD_BOT!\%%F" "%~dp0%%F" >nul
        echo       Copied: %%F
        set /a COPIED+=1
    ) else (
        echo       Not found (skipped): %%F
    )
)

:: Copy profiles folder (the most important — contains logged-in Chrome sessions)
if exist "!OLD_BOT!\profiles" (
    echo       Copying profiles\ folder (this may take a moment)...
    xcopy "!OLD_BOT!\profiles" "%~dp0profiles\" /e /i /h /q /y >nul
    echo       Copied: profiles\ folder
    set /a COPIED+=1
) else (
    echo       Not found (skipped): profiles\
)

echo.
echo [2/2] Migration complete! Copied !COPIED! item(s).

echo.
echo ============================================================
echo   Done! Your new bot now has all the data from the old bot.
echo   Run start_bot.bat to launch the updated bot.
echo ============================================================
echo.
pause
