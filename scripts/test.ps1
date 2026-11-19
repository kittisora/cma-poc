# Offline tests, then (optionally) live county checks and the browser workflow.
param([switch]$Live, [switch]$Browser)
$root = Split-Path -Parent $PSScriptRoot
Set-Location "$root\backend"
.\.venv\Scripts\python.exe -m pytest -q
if ($Live) { .\.venv\Scripts\python.exe -m pytest -q -m live }
if ($Browser) { .\.venv\Scripts\python.exe "$root\scripts\e2e_ui.py" --out "$root\e2e_output" }
