---
name: telemetry-dataset
description: >-
  Interact with Claude Code telemetry JSONL data, employees.csv enrichment,
  ETL CLI commands, Docker bootstrap flow, and analytics API/SQL patterns.
  Use when inspecting, loading, querying, or debugging telemetry analytics data.
---

# Telemetry Dataset Skill

Use this skill when working with the Claude Telemetry Analytics dataset or pipeline.

## Dataset layout

| File | Purpose |
|------|---------|
| `data/raw/telemetry_logs.jsonl` | One JSON object per line; synthetic or provided telemetry |
| `data/raw/employees.csv` | User role enrichment: `email`, `full_name`, `practice`, `level`, `location` |

Both files are gitignored. Generate locally:

```bash
python generate_fake_data.py
# or inside Docker:
docker compose exec api python generate_fake_data.py
```

## JSONL record shape

Flat records (from `generate_fake_data.py`) contain:

- `body` — fully qualified event type, e.g. `claude_code.api_request`
- `attributes` — metrics (`event.name`, `event.timestamp`, `model`, token counts, `cost_usd`, `duration_ms`)
- `resource` — user context (`user.email`, `user.practice`, `user.profile`)

The ETL normalizes `event.name` to short names (`api_request`, `user_prompt`, `tool_result`, `api_error`).

## ETL CLI

Run from repo root or inside the `api` container (`/app`):

```bash
# Inspect structure
python -m etl.run inspect --input data/raw/telemetry_logs.jsonl --limit 5

# Parse first record
python -m etl.run sample --input data/raw/telemetry_logs.jsonl

# Load api_request facts + enrich dim_users
python -m etl.run load \
  --input data/raw/telemetry_logs.jsonl \
  --employees data/raw/employees.csv
```

**Load behavior:**

1. Parses all events; validates timestamps and user email.
2. Upserts `dim_users` from `employees.csv` and observed telemetry emails.
3. Inserts only `api_request` rows into `fact_api_requests`.

## One-command bootstrap

```powershell
# Windows
.\scripts\bootstrap.ps1

# Linux / macOS
./scripts/bootstrap.sh
```

Starts Docker Compose, runs migrations, generates sample data if missing, and loads the warehouse.

## Analytics API

Base URL: `http://localhost:8000` (host) or `http://api:8000` (Compose network)

| Endpoint | Use case |
|----------|----------|
| `GET /health` | Liveness + DB connectivity |
| `GET /analytics/overview` | Platform KPI totals |
| `GET /analytics/models` | Cost and latency by model |
| `GET /analytics/top-users?limit=10` | Highest spenders |
| `GET /analytics/practices` | Cost by engineering practice (requires employee enrichment) |
| `GET /analytics/levels` | Cost by seniority level |
| `GET /analytics/trends` | Daily request and cost trends |

Dashboard: `http://localhost:8501` — persona views (Executive, Engineering Manager, FinOps).

## Example SQL (psql)

```bash
docker compose exec postgres psql -U telemetry -d telemetry
```

```sql
-- Overview mirror
SELECT COUNT(*), SUM(cost_usd), COUNT(DISTINCT user_email)
FROM fact_api_requests;

-- Cost by practice (join enrichment)
SELECT d.practice, SUM(f.cost_usd) AS total_cost_usd
FROM fact_api_requests f
JOIN dim_users d ON d.email = f.user_email
GROUP BY d.practice
ORDER BY total_cost_usd DESC;

-- Daily trend
SELECT DATE_TRUNC('day', event_ts)::date AS day, COUNT(*), SUM(cost_usd)
FROM fact_api_requests
GROUP BY 1
ORDER BY 1;
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Empty dashboard charts | Data not loaded | Run bootstrap or `etl.run load` with `--employees` |
| Practice/level charts empty | `dim_users` not enriched | Pass `--employees data/raw/employees.csv` on load |
| `/health` returns 503 | PostgreSQL not ready | Wait for postgres healthcheck; run migrations |
| Docker metadata.db read-only | Host disk full | Free C: drive space; prune Docker; restart Docker Desktop |

## Agent setup reference

See `docs/agent-setup.md` and `docs/llm-usage.md` for reproducible Cursor configuration committed to this repository.
