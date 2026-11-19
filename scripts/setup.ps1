# One-time local setup on Windows (PowerShell). Requires Python 3.12+ and Node 20+.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location "$root\backend"
if (-not (Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
if (-not (Test-Path "$root\.env")) { Copy-Item "$root\.env.example" "$root\.env" }
.\.venv\Scripts\python.exe -m alembic upgrade head
Set-Location "$root\frontend"
npm ci
npm run build
Write-Host "Setup complete. Next: scripts\refresh.ps1 (first data import, ~4-5 min), then scripts\run.ps1"
