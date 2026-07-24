@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist ".env" copy /Y ".env.example" ".env" >nul

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
  for %%P in ("%LOCALAPPDATA%\Programs\Python\Python312\python.exe" "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe") do (
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

set "VENV_OK="
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -c "%PYTHON_VERSION_CHECK%" >nul 2>&1
  if not errorlevel 1 set "VENV_OK=1"
)
if exist ".venv\Scripts\python.exe" if not defined VENV_OK (
  echo Existing backend .venv is missing or incompatible; recreating it.
  rmdir /s /q ".venv"
)

if not exist ".venv\Scripts\python.exe" (
  if not defined PYTHON_CMD (
    echo [ERROR] Python 3.10 / 3.11 / 3.12 is required.
    echo Install Python 3.12 from https://www.python.org/downloads/
    echo Then run: py -3.12 --version
    pause
    exit /b 1
  )
  echo Using %PYTHON_CMD%
  %PYTHON_CMD% -m venv .venv
  if errorlevel 1 goto :fail
  set "VENV_OK=1"
)

if defined VENV_OK (
  ".venv\Scripts\python.exe" -c "import sys; print('Using backend venv Python ' + sys.version.split()[0])"
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto :fail
pip install -r requirements.txt
if errorlevel 1 goto :fail

python scripts\ensure_database.py
if errorlevel 1 goto :fail

echo.
echo Backend starting at http://127.0.0.1:%BACKEND_PORT%
echo Database source: %DATABASE_SOURCE%
echo Worker mode: USE_CELERY=%USE_CELERY%
echo Press Ctrl+C to stop.
echo.
uvicorn app.main:app --reload --host 127.0.0.1 --port %BACKEND_PORT%
goto :eof

:fail
echo.
echo [ERROR] Backend setup failed.
pause
exit /b 1
