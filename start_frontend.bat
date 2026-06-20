@echo off
cd /d %~dp0\frontend
if not exist node_modules (
  npm install
)
npm run dev -- --host 127.0.0.1 --port 5173
