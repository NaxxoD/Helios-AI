# Helios — script de lancement dev (Tour)
# Lance Ollama + backend dans le bon ordre avec les bons paramètres

Write-Host "=== Helios Dev Launcher ===" -ForegroundColor Cyan

# 1. Ollama avec timeout étendu
Write-Host "Démarrage Ollama (timeout 120s)..." -ForegroundColor Yellow
$env:OLLAMA_REQUEST_TIMEOUT = "120"
Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Normal

Start-Sleep 3

# 2. Backend FastAPI
Write-Host "Démarrage backend FastAPI..." -ForegroundColor Yellow
Set-Location "$PSScriptRoot\backend"
$env:PYTHONPATH = "$PSScriptRoot\backend"
Start-Process -FilePath "python" -ArgumentList "main.py" -WorkingDirectory "$PSScriptRoot\backend" -WindowStyle Normal

Write-Host ""
Write-Host "Services lancés :" -ForegroundColor Green
Write-Host "  Backend  → http://localhost:8000" -ForegroundColor Green
Write-Host "  API docs → http://localhost:8000/docs" -ForegroundColor Green
Write-Host ""
Write-Host "Lance le frontend séparément : cd frontend && npm run dev" -ForegroundColor Cyan
