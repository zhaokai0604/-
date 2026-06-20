@echo off
setlocal EnableExtensions
cd /d %~dp0

set "PYTHON_CMD="
for %%V in (3.12 3.11 3.10) do (
  if not defined PYTHON_CMD (
    py -%%V -c "import sys" >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=py -%%V"
  )
)

if not defined PYTHON_CMD (
  echo [ERROR] 需要 Python 3.10 / 3.11 / 3.12 才能运行测试。
  exit /b 1
)

cd backend
if not exist .venv (
  echo [INFO] 未找到 .venv，请先运行 start_backend.bat 或手动创建虚拟环境。
  %PYTHON_CMD% -m venv .venv
  call .venv\Scripts\activate
  python -m pip install --upgrade pip
  pip install -r requirements.txt
) else (
  call .venv\Scripts\activate
)

set DATABASE_URL=sqlite:///:memory:
set SESSION_SECRET=ci-test-secret
set ALLOW_REGISTER=true
python -m pytest tests/ -q
exit /b %ERRORLEVEL%
