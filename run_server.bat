@echo off
title SysMonitor Pro - Live System Status & RAM Optimizer
cd /d "%~dp0"
echo ========================================================
echo   SYSMONITOR PRO - LIVE SYSTEM TRACKER & RAM OPTIMIZER
echo ========================================================
echo.
echo Ensuring database and administrator credentials...
python init_setup.py
echo.
echo Starting Django Server on 0.0.0.0:8000 ...
echo.
echo Local Access:       http://127.0.0.1:8000
echo Network/LAN Access: http://160.191.14.183:8000
echo.
echo Authorized User: Avinash
echo Credentials are required to access telemetry and tools.
echo.
echo Press Ctrl+C in this window to stop the server.
echo ========================================================
python manage.py runserver 0.0.0.0:8000
pause
