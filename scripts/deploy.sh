#!/usr/bin/env bash
# Deploy on a Linux host with Docker: build, start PostGIS + app, run migrations, load data.
#   ./scripts/deploy.sh            # build + start + refresh
#   ./scripts/deploy.sh --no-refresh
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] || { cp .env.example .env; echo "Created .env from .env.example — set POSTGRES_PASSWORD and OPENAI_API_KEY."; }
docker compose up -d --build            # the app runs Alembic migrations on start
if [ "${1:-}" != "--no-refresh" ]; then
  docker compose --profile refresh run --rm refresh
fi
docker compose ps
echo "App: http://localhost:8000   Schedule daily refresh with cron, e.g.:"
echo "  15 6 * * *  cd $(pwd) && docker compose --profile refresh run --rm refresh >> refresh.log 2>&1"
