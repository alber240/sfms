@echo off
title SFMS Installer - Liberia Edition
color 0A
echo ========================================
echo    SFMS INSTALLATION
echo    School Financial Management System
echo    Liberia Edition
echo ========================================
echo.
echo This will install SFMS on this computer.
echo.
pause

echo.
echo [1/8] Creating directories...
mkdir C:\SFMS 2>nul
mkdir C:\SFMS\media 2>nul
mkdir C:\SFMS\backups 2>nul
mkdir C:\SFMS\sent_emails 2>nul
mkdir C:\SFMS\logs 2>nul
mkdir C:\SFMS\scripts 2>nul

echo [2/8] Copying files...
xcopy /E /I /Y "%~dp0*" "C:\SFMS\"

echo [3/8] Installing Python dependencies...
cd /d C:\SFMS
pip install django pillow reportlab openpyxl requests cryptography python-decouple whitenoise supabase

echo [4/8] Setting up database...
python manage.py migrate

echo [5/8] Creating unique school users...
python scripts\create_school_users.py

echo [6/8] Creating desktop shortcut...
echo [InternetShortcut] > "%USERPROFILE%\Desktop\SFMS.url"
echo URL=http://localhost:8000 >> "%USERPROFILE%\Desktop\SFMS.url"
echo IconIndex=0 >> "%USERPROFILE%\Desktop\SFMS.url"

echo [7/8] Creating start script...
echo @echo off > "%USERPROFILE%\Desktop\Start SFMS.bat"
echo title SFMS - School Financial Management System >> "%USERPROFILE%\Desktop\Start SFMS.bat"
echo cd /d C:\SFMS >> "%USERPROFILE%\Desktop\Start SFMS.bat"
echo start http://localhost:8000 >> "%USERPROFILE%\Desktop\Start SFMS.bat"
echo python manage.py runserver >> "%USERPROFILE%\Desktop\Start SFMS.bat"

echo [8/8] Setting permissions...
icacls C:\SFMS\db.sqlite3 /grant "Everyone:(R,W)" 2>nul

echo.
echo ========================================
echo    INSTALLATION COMPLETE!
echo ========================================
echo.
echo To start SFMS:
echo 1. Double-click "Start SFMS.bat" on desktop
echo 2. Check the credentials file on desktop
echo 3. Login with your username and temporary password
echo.
echo IMPORTANT: You will be asked to change your password on first login!
echo.
pause
