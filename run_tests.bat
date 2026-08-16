@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PYTHON_CMD="
for %%V in (3.12 3.11 3.10) do (
  if not defined PYTHON_CMD (
    py -%%V -c "import sys" >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=py -%%V"
  )
)

if not defined PYTHON_CMD (
  echo [ERROR] Python 3.10 / 3.11 / 3.12 is required.
  pause
  exit /b 1
)

cd /d "%~dp0backend"

set "VENV_PY=%CD%\.venv\Scripts\python.exe"

if not exist "%VENV_PY%" (
  echo [INFO] .venv not found. Creating virtual environment...
  %PYTHON_CMD% -m venv .venv
  if errorlevel 1 goto :fail
  "%VENV_PY%" -m pip install --upgrade pip
  if errorlevel 1 goto :fail
  "%VENV_PY%" -m pip install --prefer-binary -r requirements.txt
  if errorlevel 1 goto :fail
)

set DATABASE_URL=sqlite:///:memory:
set SESSION_SECRET=ci-test-secret
set ALLOW_REGISTER=true

"%VENV_PY%" -m pytest tests/ -q
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [FAILED] pytest exit code %RC%
) else (
  echo [OK] All tests passed.
)
pause
exit /b %RC%

:fail
echo.
echo [ERROR] Test setup failed.
pause
exit /b 1
