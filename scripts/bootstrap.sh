#!/usr/bin/env bash
# Bootstrap the local telemetry analytics stack end-to-end.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ENV_FILE=".env"
TELEMETRY_FILE="data/raw/telemetry_logs.jsonl"
EMPLOYEES_FILE="data/raw/employees.csv"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Creating $ENV_FILE from .env.example"
  cp .env.example "$ENV_FILE"
fi

echo "Starting Docker Compose stack..."
docker compose --env-file "$ENV_FILE" up --build -d

echo "Waiting for PostgreSQL to become healthy..."
until docker compose exec -T postgres pg_isready -U telemetry -d telemetry >/dev/null 2>&1; do
  sleep 2
done

echo "Applying database migrations..."
docker compose exec -T api alembic upgrade head

if [[ ! -f "$TELEMETRY_FILE" ]]; then
  echo "Generating sample telemetry and employee data..."
  docker compose exec -T api python generate_fake_data.py
fi

echo "Loading telemetry into PostgreSQL..."
docker compose exec -T api python -m etl.run load \
  --input "$TELEMETRY_FILE" \
  --employees "$EMPLOYEES_FILE"

echo ""
echo "Bootstrap complete."
echo "  API docs:    http://localhost:8000/docs"
echo "  Health:      http://localhost:8000/health"
echo "  Dashboard:   http://localhost:8501"
echo ""
echo "Verify: curl http://localhost:8000/analytics/overview"
