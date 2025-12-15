@echo off
title Personal Engineering OS - Local Launcher
color 0A

echo.
echo  ============================================
echo   Personal Engineering OS v1.0.1
echo   Local Development Launcher
echo  ============================================
echo.

:: Check if Node.js is installed
where node >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Node.js not found! Install from https://nodejs.org
    pause
    exit /b 1
)

:: Check if Python is installed
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python not found! Install from https://python.org
    pause
    exit /b 1
)

echo [1/4] Starting PostgreSQL (via Docker)...
docker ps -q -f name=eng-db >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Starting new PostgreSQL container...
    docker run -d --name eng-db -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=engineering_os -p 5432:5432 -v "%~dp0database\init.sql:/docker-entrypoint-initdb.d/init.sql" postgres:16-alpine
) else (
    echo PostgreSQL already running.
)

timeout /t 3 /nobreak >nul

echo.
echo [2/4] Starting copilot-api (GitHub Copilot Proxy)...
start "copilot-api" cmd /k "title copilot-api && npx copilot-api@latest start"

timeout /t 2 /nobreak >nul

echo.
echo [3/4] Starting Backend (FastAPI)...
start "Backend" cmd /k "title Backend - FastAPI && cd /d %~dp0backend && pip install -q -r requirements.txt && uvicorn main:app --reload --port 8000"

timeout /t 2 /nobreak >nul

echo.
echo [4/4] Starting Frontend (Next.js)...
start "Frontend" cmd /k "title Frontend - Next.js && cd /d %~dp0frontend && npm install && npm run dev"

echo.
echo  ============================================
echo   All services starting!
echo  ============================================
echo.
echo   Frontend:  http://localhost:3000
echo   Backend:   http://localhost:8000
echo   API Docs:  http://localhost:8000/docs
echo.
echo   Press any key to open the dashboard...
pause >nul

start http://localhost:3000
