@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not defined BACKEND_PORT set "BACKEND_PORT=8000"
if not defined FRONTEND_PORT set "FRONTEND_PORT=5174"

echo Starting local resume analysis stack...
echo Backend:  http://127.0.0.1:%BACKEND_PORT%
echo Frontend: http://127.0.0.1:%FRONTEND_PORT%
echo.

start "Resume AI Backend" cmd /k ""%~dp0start_backend.bat""

echo Waiting for backend health check...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$deadline=(Get-Date).AddSeconds(45); do { try { $r=Invoke-RestMethod -Uri 'http://127.0.0.1:%BACKEND_PORT%/api/health' -TimeoutSec 2; if ($r.status) { exit 0 } } catch {}; Start-Sleep -Seconds 1 } while ((Get-Date) -lt $deadline); exit 1"
if errorlevel 1 (
  echo [WARN] Backend health check did not pass yet. Frontend will still start.
) else (
  echo Backend is ready.
)

start "Resume AI Frontend" cmd /k ""%~dp0start_frontend.bat""

echo Waiting for frontend...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$deadline=(Get-Date).AddSeconds(30); do { try { $r=Invoke-WebRequest -Uri 'http://127.0.0.1:%FRONTEND_PORT%' -TimeoutSec 2; if ($r.StatusCode -ge 200) { exit 0 } } catch {}; Start-Sleep -Seconds 1 } while ((Get-Date) -lt $deadline); exit 1"
if errorlevel 1 (
  echo [WARN] Frontend did not respond yet. Open it after Vite finishes compiling.
) else (
  start "" "http://127.0.0.1:%FRONTEND_PORT%"
)

echo.
echo Local startup command finished.
pause
