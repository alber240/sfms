@echo off
title SFMS - School Financial Management System
color 0E
echo ========================================
echo    SFMS - School Financial Management
echo    Liberia Edition
echo ========================================
echo.
echo Starting server...
echo.
echo The system will open in your browser automatically
echo.
cd /d C:\SFMS
start http://localhost:8000
python manage.py runserver
