@echo off
setlocal EnableExtensions
cd /d "%~dp0frontend"
if not defined BACKEND_PORT set "BACKEND_PORT=8000"
if not defined FRONTEND_PORT set "FRONTEND_PORT=5174"
set "VITE_API_TARGET=http://127.0.0.1:%BACKEND_PORT%"

if not exist node_modules (
  npm install
)

echo.
echo Frontend starting at http://127.0.0.1:%FRONTEND_PORT%
echo API proxy target: %VITE_API_TARGET%
echo Press Ctrl+C to stop.
echo.
npm run dev -- --host 127.0.0.1 --port %FRONTEND_PORT% --strictPort
