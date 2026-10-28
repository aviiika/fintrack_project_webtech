<#
.SYNOPSIS
    dev.ps1 - FinTrack Pro Windows task runner
.DESCRIPTION
    Usage: .\dev.ps1 <command>    Run .\dev.ps1 help for all commands.
#>
param([Parameter(Position=0)][string]$Command = "help")
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"

function Update-SessionPath {
    $m = [System.Environment]::GetEnvironmentVariable("PATH","Machine")
    $u = [System.Environment]::GetEnvironmentVariable("PATH","User")
    $env:PATH = (($m + ";" + $u) -split ";" | Select-Object -Unique | Where-Object { $_ -ne "" }) -join ";"
    $uvBin = Join-Path $env:USERPROFILE ".local\bin"
    if ((Test-Path $uvBin) -and ($env:PATH -notlike "*$uvBin*")) { $env:PATH = "$uvBin;$env:PATH" }
}
Update-SessionPath

function Write-Step([string]$m) { Write-Host ""; Write-Host "  >> $m" -ForegroundColor Cyan }
function Assert-Tool([string]$t) {
    if (-not (Get-Command $t -ErrorAction SilentlyContinue)) {
        Write-Host "  ERROR: '$t' not found." -ForegroundColor Red
        if ($t -eq "uv") { Write-Host "  Install: powershell -ExecutionPolicy ByPass -c `"irm https://astral.sh/uv/install.ps1 | iex`"" }
        if ($t -eq "npm") { Write-Host "  Install Node.js from https://nodejs.org" }
        exit 1
    }
}

function cmd-install { cmd-install-backend; cmd-install-frontend }
function cmd-install-backend { Write-Step "Installing Python deps..."; Assert-Tool "uv"; Push-Location $Backend; try { uv sync } finally { Pop-Location } }
function cmd-install-frontend { Write-Step "Installing Node deps..."; Assert-Tool "npm"; Push-Location $Frontend; try { npm install } finally { Pop-Location } }
function cmd-dev {
    Write-Step "Starting both servers..."
    $be = "Set-Location '$Backend'; uv run python -m app.database.seed 2>null; uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
    $fe = "Set-Location '$Frontend'; npm run dev"
    Start-Process powershell -ArgumentList "-NoExit","-Command",$be
    Start-Sleep -Seconds 2
    Start-Process powershell -ArgumentList "-NoExit","-Command",$fe
    Write-Host "  Backend   : http://localhost:8000" -ForegroundColor Green
    Write-Host "  Frontend  : http://localhost:5173" -ForegroundColor Green
    Write-Host "  ML page   : http://localhost:5173/ml" -ForegroundColor Green
    Write-Host "  Portfolio : http://localhost:5173/portfolio" -ForegroundColor Green
    Write-Host "  Net Worth : http://localhost:5173/networth" -ForegroundColor Green
    Write-Host "  Loans     : http://localhost:5173/loans" -ForegroundColor Green
    Write-Host "  API docs  : http://localhost:8000/docs" -ForegroundColor Green
}
function cmd-dev-backend { Assert-Tool "uv"; Push-Location $Backend; try { uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 } finally { Pop-Location } }
function cmd-dev-frontend { Assert-Tool "npm"; Push-Location $Frontend; try { npm run dev } finally { Pop-Location } }
function cmd-seed { Assert-Tool "uv"; Push-Location $Backend; try { uv run python -m app.database.seed } finally { Pop-Location } }
function cmd-train { Assert-Tool "uv"; Push-Location $Backend; try { uv run python -m app.ml.training.train_categoriser } finally { Pop-Location } }
function cmd-test { Assert-Tool "uv"; Push-Location $Backend; try { uv run pytest -v } finally { Pop-Location } }
function cmd-build { Assert-Tool "npm"; Push-Location $Frontend; try { npm run build } finally { Pop-Location } }
function cmd-reset {
    Assert-Tool "uv"
    Write-Step "Resetting database..."
    $db = Join-Path $Backend "fintrack.db"
    if (Test-Path $db) { Remove-Item $db -Force; Write-Host "  Deleted fintrack.db" }
    cmd-seed
}
function cmd-help {
    Write-Host @"

  FinTrack Pro - dev.ps1 commands

    install          Install backend + frontend dependencies
    dev              Start both servers in new windows
    dev-backend      FastAPI only -> http://localhost:8000
    dev-frontend     Vite only    -> http://localhost:5173
    seed             Seed demo data (txns, holdings, loans) + train initial ML model
    train            Manually retrain the categoriser from current data
    reset            Delete the database, then re-seed from scratch
    build            Production build of the frontend
    test             Run backend pytest suite (57 tests)
    help             Show this message

  Demo login: demo@fintrack.app / demo12345

  Pages (all eight are implemented):
    /dashboard      Metrics, category charts, daily trend, recent transactions
    /import         Multi-bank CSV upload with drag and drop
    /transactions   Search, filter, inline category edit (ML feedback loop)
    /reports        Annual charts, budget tracker, CSV and Excel export
    /ml             Model Insights (accuracy, retrain, predict, anomalies)
    /portfolio      Live stock prices over WebSocket
    /networth       Assets minus liabilities, snapshot history
    /loans          Reducing-balance amortization

"@ -ForegroundColor White
}

switch ($Command.ToLower()) {
    "install" { cmd-install }; "install-backend" { cmd-install-backend }; "install-frontend" { cmd-install-frontend }
    "dev" { cmd-dev }; "dev-backend" { cmd-dev-backend }; "dev-frontend" { cmd-dev-frontend }
    "seed" { cmd-seed }; "train" { cmd-train }; "reset" { cmd-reset }
    "build" { cmd-build }; "test" { cmd-test }; "help" { cmd-help }
    default { Write-Host "Unknown: '$Command'" -ForegroundColor Red; cmd-help; exit 1 }
}
