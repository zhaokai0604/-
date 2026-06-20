@echo off
setlocal EnableExtensions
cd /d %~dp0
if not exist .env copy .env.example .env

set "PYTHON_CMD="
for %%V in (3.12 3.11 3.10) do (
  if not defined PYTHON_CMD (
    py -%%V -c "import sys" >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=py -%%V"
  )
)

if not defined PYTHON_CMD (
  echo [ERROR] 需要 Python 3.10 / 3.11 / 3.12，当前未检测到可用版本。
  echo         请从 https://www.python.org/downloads/ 安装 Python 3.12 并勾选 "Add to PATH"。
  echo         安装后执行: py -3.12 --version
  exit /b 1
)

echo Using %PYTHON_CMD%
cd backend

if exist .venv (
  for /f "delims=" %%P in ('.venv\Scripts\python.exe -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2^>nul') do set "VENV_PY=%%P"
  if not "%VENV_PY%"=="3.10" if not "%VENV_PY%"=="3.11" if not "%VENV_PY%"=="3.12" (
    echo Recreating .venv ^(found Python %VENV_PY%, need 3.10-3.12^)...
    rmdir /s /q .venv
  )
)

if not exist .venv (
  %PYTHON_CMD% -m venv .venv
  if errorlevel 1 exit /b 1
)

call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 exit /b 1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
