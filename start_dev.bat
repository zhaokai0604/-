@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not defined BACKEND_PORT set "BACKEND_PORT=8000"
if not defined FRONTEND_PORT set "FRONTEND_PORT=5174"

REM Prefer project venv for port probe; fall back to py -3.12
set "PICK_PY="
if exist "%~dp0backend\.venv\Scripts\python.exe" set "PICK_PY=%~dp0backend\.venv\Scripts\python.exe"
if not defined PICK_PY (
  py -3.12 -c "import sys" >nul 2>&1
  if not errorlevel 1 set "PICK_PY=py -3.12"
)
if defined PICK_PY (
  for /f "usebackq delims=" %%P in (`%PICK_PY% "%~dp0backend\scripts\pick_free_port.py" --preferred %BACKEND_PORT%`) do set "BACKEND_PORT=%%P"
)

echo Starting local resume analysis stack...
echo Backend:  http://127.0.0.1:%BACKEND_PORT%
echo Frontend: http://127.0.0.1:%FRONTEND_PORT%
echo.

start "Resume AI Backend" /D "%~dp0" cmd /k "set BACKEND_PORT=%BACKEND_PORT%&& call "%~dp0start_backend.bat""
if errorlevel 1 (
  echo [ERROR] Failed to open backend window.
  pause
  exit /b 1
)

echo Waiting for backend health check...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$deadline=(Get-Date).AddSeconds(60); do { try { $r=Invoke-RestMethod -Uri 'http://127.0.0.1:%BACKEND_PORT%/api/health' -TimeoutSec 2; if ($r.status) { exit 0 } } catch {}; Start-Sleep -Seconds 1 } while ((Get-Date) -lt $deadline); exit 1"
if errorlevel 1 (
  echo [WARN] Backend health check did not pass yet. Check the Backend window for errors.
) else (
  echo Backend is ready.
)

start "Resume AI Frontend" /D "%~dp0" cmd /k "set BACKEND_PORT=%BACKEND_PORT%&& set FRONTEND_PORT=%FRONTEND_PORT%&& call "%~dp0start_frontend.bat""
if errorlevel 1 (
  echo [ERROR] Failed to open frontend window.
  pause
  exit /b 1
)

echo Waiting for frontend...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$deadline=(Get-Date).AddSeconds(45); do { try { $r=Invoke-WebRequest -Uri 'http://127.0.0.1:%FRONTEND_PORT%' -TimeoutSec 2; if ($r.StatusCode -ge 200) { exit 0 } } catch {}; Start-Sleep -Seconds 1 } while ((Get-Date) -lt $deadline); exit 1"
if errorlevel 1 (
  echo [WARN] Frontend did not respond yet. Open it after Vite finishes compiling.
) else (
  start "" "http://127.0.0.1:%FRONTEND_PORT%"
)

echo.
echo Local startup command finished.
echo Keep the Backend / Frontend black windows open while using the app.
pause
