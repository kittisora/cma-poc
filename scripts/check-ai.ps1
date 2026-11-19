# Check the AI key and model with one small request (prints the provider, model and reply; never the key).
$root = Split-Path -Parent $PSScriptRoot
Set-Location "$root\backend"
.\.venv\Scripts\python.exe -m app.agent.check
