// PM2 process for the CMA app (FastAPI serving /api and the static Next.js export).
module.exports = {
  apps: [{
    name: "cma",
    cwd: __dirname + "/backend",
    script: ".venv/bin/uvicorn",
    args: "app.main:app --host 127.0.0.1 --port 8010 --proxy-headers --forwarded-allow-ips=127.0.0.1",
    interpreter: "none",
    autorestart: true,
    max_memory_restart: "1G",
  }],
};
