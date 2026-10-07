@echo off
echo Lancement Helios AI...

set ROOT=%~dp0

start "Helios Backend" cmd /k "cd /d %ROOT%backend && python -m uvicorn main:app --reload --port 8000"
timeout /t 2 /nobreak >nul
start "Helios Frontend" cmd /k "cd /d %ROOT%frontend && npm run dev"

echo Backend  : http://localhost:8000/docs
echo Frontend : http://localhost:5173
