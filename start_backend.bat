@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist ".env" (
  if exist ".env.example" copy /Y ".env.example" ".env" >nul
)

set "PYTHON_VERSION_CHECK=import sys; raise SystemExit(0 if (3, 10) <= sys.version_info[:2] <= (3, 12) else 1)"
set "PYTHON_CMD="
if defined PYTHON (
  "%PYTHON%" -c "%PYTHON_VERSION_CHECK%" >nul 2>&1
  if not errorlevel 1 set "PYTHON_CMD=%PYTHON%"
)
for %%V in (3.12 3.11 3.10) do (
  if not defined PYTHON_CMD (
    py -%%V -c "%PYTHON_VERSION_CHECK%" >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=py -%%V"
  )
)

if not defined PYTHON_CMD (
  for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "%USERPROFILE%\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\python.exe"
    "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
  ) do (
    if not defined PYTHON_CMD (
      if exist "%%~fP" (
        "%%~fP" -c "%PYTHON_VERSION_CHECK%" >nul 2>&1
        if not errorlevel 1 set "PYTHON_CMD=%%~fP"
      )
    )
  )
)

if not defined PYTHON_CMD (
  python -c "%PYTHON_VERSION_CHECK%" >nul 2>&1
  if not errorlevel 1 set "PYTHON_CMD=python"
)

cd /d "%~dp0backend"
if not defined BACKEND_PORT set "BACKEND_PORT=8000"
if defined BACKEND_DATABASE_URL (
  set "DATABASE_URL=%BACKEND_DATABASE_URL%"
  set "DATABASE_SOURCE=BACKEND_DATABASE_URL"
) else (
  set "DATABASE_URL=sqlite:///../data/resume_ai_dev.db"
  set "DATABASE_SOURCE=local SQLite default"
)
if not defined USE_CELERY set "USE_CELERY=false"
set "REDIS_URL="

echo ========================================
echo  Resume AI Backend
echo  Port: %BACKEND_PORT%
echo ========================================
echo.

set "VENV_OK="
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -c "%PYTHON_VERSION_CHECK%" >nul 2>&1
  if not errorlevel 1 set "VENV_OK=1"
)
if exist ".venv\Scripts\python.exe" if not defined VENV_OK (
  echo Existing backend .venv is incompatible ^(need Python 3.10-3.12^); recreating...
  rmdir /s /q ".venv"
)

if not exist ".venv\Scripts\python.exe" (
  if not defined PYTHON_CMD (
    echo [ERROR] Python 3.10 / 3.11 / 3.12 is required.
    echo Your default may be Python 3.14 - that will NOT work.
    echo Install Python 3.12: https://www.python.org/downloads/
    echo Then run: py -3.12 --version
    goto :fail
  )
  echo Creating venv with: %PYTHON_CMD%
  %PYTHON_CMD% -m venv .venv
  if errorlevel 1 goto :fail
  set "VENV_OK=1"
)

set "VENV_PY=%CD%\.venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
  echo [ERROR] backend\.venv\Scripts\python.exe not found.
  goto :fail
)

"%VENV_PY%" -c "import sys; print('Using backend venv Python ' + sys.version.split()[0])"

echo Installing deps with venv pip...
"%VENV_PY%" -m pip install --upgrade pip
if errorlevel 1 goto :fail
"%VENV_PY%" -m pip install --prefer-binary -r requirements.txt
if errorlevel 1 (
  echo.
  echo [HINT] Pillow/deps failed: do NOT use Python 3.13/3.14.
  echo Delete backend\.venv, install Python 3.12, then re-run.
  goto :fail
)

"%VENV_PY%" scripts\ensure_database.py
if errorlevel 1 goto :fail

for /f "usebackq delims=" %%P in (`"%VENV_PY%" scripts\pick_free_port.py --preferred %BACKEND_PORT%`) do set "BACKEND_PORT=%%P"
if not defined BACKEND_PORT (
  echo [ERROR] No free backend port in 8000-8010.
  echo Close old python/uvicorn windows in Task Manager, then retry.
  goto :fail
)
if /I not "%BACKEND_PORT%"=="8000" echo [INFO] Preferred port busy; using BACKEND_PORT=%BACKEND_PORT%

echo.
echo Backend starting at http://127.0.0.1:%BACKEND_PORT%
echo Database source: %DATABASE_SOURCE%
echo Worker mode: USE_CELERY=%USE_CELERY%
echo Press Ctrl+C to stop.
echo.
"%VENV_PY%" -m uvicorn app.main:app --reload --host 127.0.0.1 --port %BACKEND_PORT%
set "UV_RC=%ERRORLEVEL%"
echo.
if not "%UV_RC%"=="0" (
  echo [ERROR] uvicorn exited with code %UV_RC%
  echo If WinError 10013/10048: another process still holds the port.
  echo Task Manager -^> end python.exe that runs uvicorn, then retry.
)
goto :end

:fail
set "UV_RC=1"
echo.
echo [ERROR] Backend setup failed.
goto :end

:end
echo.
pause
if not defined UV_RC set "UV_RC=0"
exit /b %UV_RC%
