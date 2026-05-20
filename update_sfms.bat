@echo off
title SFMS Updater
color 0E
echo ========================================
echo    SFMS UPDATE INSTALLER
echo ========================================
echo.
echo This will update SFMS to the latest version.
echo Your data will NOT be affected.
echo.
pause

echo.
echo [1/4] Backing up current database...
copy C:\SFMS\db.sqlite3 C:\SFMS\db_backup.sqlite3

echo [2/4] Installing updates...
xcopy /E /I /Y "%~dp0*" "C:\SFMS\"

echo [3/4] Running database migrations...
cd /d C:\SFMS
python manage.py migrate

echo [4/4] Cleaning up...
echo Update complete!

echo.
echo ========================================
echo    UPDATE COMPLETE!
echo ========================================
echo.
pause
