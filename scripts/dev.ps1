# Development: API with auto-reload on :8000 and the Next.js dev server on :3000 (proxies /api to :8000).
$root = Split-Path -Parent $PSScriptRoot
Start-Process -NoNewWindow -FilePath "$root\backend\.venv\Scripts\python.exe" -ArgumentList "-m","uvicorn","app.main:app","--reload","--port","8000" -WorkingDirectory "$root\backend"
Set-Location "$root\frontend"
$env:NEXT_TELEMETRY_DISABLED = "1"
npm run dev
