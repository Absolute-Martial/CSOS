@echo off
title Stop Engineering OS
color 0C

echo.
echo Stopping all services...
echo.

:: Stop Docker container
docker stop engineering-os-db 2>nul
echo [x] PostgreSQL stopped

:: Kill Node processes (copilot-api and Next.js)
taskkill /F /IM node.exe 2>nul
echo [x] Node.js processes stopped

:: Kill Python processes (uvicorn)
taskkill /F /FI "WINDOWTITLE eq Backend*" 2>nul
echo [x] Backend stopped

echo.
echo All services stopped.
pause
