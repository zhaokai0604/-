@echo off
setlocal EnableExtensions
cd /d "%~dp0frontend"
if not defined BACKEND_PORT set "BACKEND_PORT=8000"
if not defined FRONTEND_PORT set "FRONTEND_PORT=5174"
set "VITE_API_TARGET=http://127.0.0.1:%BACKEND_PORT%"

echo ========================================
echo  Resume AI Frontend
echo  Port: %FRONTEND_PORT%
echo ========================================
echo.

where npm >nul 2>&1
if errorlevel 1 (
  echo [ERROR] npm not found. Install Node.js 18+ from https://nodejs.org/
  goto :fail
)

if not exist node_modules (
  echo Installing npm packages...
  call npm install
  if errorlevel 1 goto :fail
)

echo.
echo Frontend starting at http://127.0.0.1:%FRONTEND_PORT%
echo API proxy target: %VITE_API_TARGET%
echo Press Ctrl+C to stop.
echo.
call npm run dev -- --host 127.0.0.1 --port %FRONTEND_PORT% --strictPort
set "NPM_RC=%ERRORLEVEL%"
echo.
if not "%NPM_RC%"=="0" (
  echo [ERROR] Frontend exited with code %NPM_RC%
  echo If port in use: close old Frontend window, or set FRONTEND_PORT=5175
)
goto :end

:fail
set "NPM_RC=1"
echo.
echo [ERROR] Frontend setup failed.
goto :end

:end
echo.
pause
exit /b %NPM_RC%
