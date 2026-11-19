# Load or refresh Fairfax County records for TARGET_ZIPS. Safe to repeat; never deletes sales.
$root = Split-Path -Parent $PSScriptRoot
Set-Location "$root\backend"
.\.venv\Scripts\python.exe -m app.ingest.refresh @args
