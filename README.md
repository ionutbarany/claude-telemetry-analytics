# Claude Telemetry Analytics

Production-style analytics platform for Claude Code OpenTelemetry logs. Ingest JSONL telemetry, load API request facts into PostgreSQL, expose rollups through a typed REST API, and visualize usage and cost in a Streamlit dashboard.

The bundled sample dataset contains **113k+ telemetry events** across prompts, API calls, tool results, and errors — enough volume to exercise realistic ETL and aggregation paths without a live data pipeline.

---

## Architecture

```
  data/raw/telemetry_logs.jsonl
              |
              v
  +---------------------------+
  |  ETL (etl/)               |
  |  parse -> transform -> load|
  +-------------+-------------+
                |
                v
  +---------------------------+
  |  PostgreSQL               |
  |  fact_api_requests (+ dims) |
  +------+--------------+-----+
         |              |
    read |              | read
         v              v
  +-------------+  +------------------+
  |  FastAPI    |  |  Streamlit       |
  |  REST API   |<-|  Plotly dashboard|
  +------+------+  +------------------+
         |
         v
   clients / curl / OpenAPI
```

**Data flow:** raw JSONL → ETL CLI → PostgreSQL → FastAPI serves aggregates → Streamlit consumes the API (not direct DB access).

Local orchestration uses **Docker Compose** (PostgreSQL 16, FastAPI, Streamlit) with environment-based configuration.

---

## Tech stack

| Layer | Choice |
|-------|--------|
| Language | Python 3.12 |
| API | FastAPI + Uvicorn |
| Dashboard | Streamlit + Plotly |
| ETL | Polars-oriented pipeline, SQLAlchemy loaders |
| Database | PostgreSQL 16 |
| ORM / migrations | SQLAlchemy 2.0 + Alembic |
| Testing | pytest |

---

## Quick start (Docker)

**Prerequisites:** Docker and Docker Compose.

```bash
# 1. Configure environment
cp .env.example .env

# 2. Start PostgreSQL, API, and dashboard
docker compose --env-file .env up --build -d

# 3. Apply database migrations
docker compose exec api alembic upgrade head

# 4. Generate sample data (if data/raw/ is empty)
docker compose exec api python generate_fake_data.py

# 5. Load api_request events into PostgreSQL
docker compose exec api python -m etl.run load --input data/raw/telemetry_logs.jsonl
```

**Verify the stack:**

```bash
curl http://localhost:8000/health
curl http://localhost:8000/analytics/overview
```

| Service | URL |
|---------|-----|
| API (OpenAPI) | http://localhost:8000/docs |
| Health check | http://localhost:8000/health |
| Dashboard | http://localhost:8501 |

Stop services: `docker compose down`  
Remove persisted DB data: `docker compose down -v`

---

## ETL commands

Run inside the `api` container (repo is bind-mounted at `/app`) or locally with `DATABASE_URL` pointing at PostgreSQL.

```bash
# Inspect JSONL structure (batch sizes, attribute keys)
docker compose exec api python -m etl.run inspect \
  --input data/raw/telemetry_logs.jsonl \
  --limit 5

# Parse and pretty-print the first telemetry record
docker compose exec api python -m etl.run sample \
  --input data/raw/telemetry_logs.jsonl

# Parse full file and insert api_request events into fact_api_requests
docker compose exec api python -m etl.run load \
  --input data/raw/telemetry_logs.jsonl
```

The `load` command reports records read, events parsed, and rows inserted. Only `claude_code.api_request` events are persisted in the current schema.

Optional logging verbosity: `--log-level DEBUG`

---

## API endpoints

Base URL: `http://localhost:8000`

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | API liveness and database connectivity |
| `GET` | `/analytics/overview` | Platform-wide totals (requests, cost, tokens, latency, users) |
| `GET` | `/analytics/models` | Per-model request count, cost, and average latency |
| `GET` | `/analytics/top-users` | Highest-spending users by total cost (`?limit=5`, max 100) |

**Examples:**

```bash
curl -s http://localhost:8000/health | jq

curl -s http://localhost:8000/analytics/overview | jq
# {
#   "total_requests": 42150,
#   "total_cost_usd": 1842.33,
#   "total_input_tokens": 9123400,
#   "total_output_tokens": 2100450,
#   "avg_latency_ms": 8421.5,
#   "unique_users": 30
# }

curl -s http://localhost:8000/analytics/models | jq

curl -s "http://localhost:8000/analytics/top-users?limit=10" | jq
```

`/health` returns HTTP 503 when the database probe fails. Interactive schema docs live at `/docs`.

---

## Dashboard

Open **http://localhost:8501** after `docker compose up`.

The Streamlit app reads from the FastAPI analytics layer (`http://api:8000` inside Compose). It shows:

- KPI cards — requests, cost, tokens, latency, unique users
- Cost and request volume by model (Plotly bar charts)
- Top users by spend

Use the sidebar **Refresh** button to bypass the 60-second response cache after reloading data.

---

## Example analytics queries

These mirror what the API computes; useful for ad-hoc SQL in `psql` or BI tools.

```sql
-- Platform overview (same grain as GET /analytics/overview)
SELECT
  COUNT(*)                          AS total_requests,
  COALESCE(SUM(cost_usd), 0)        AS total_cost_usd,
  COALESCE(SUM(input_tokens), 0)    AS total_input_tokens,
  COALESCE(SUM(output_tokens), 0)   AS total_output_tokens,
  COALESCE(AVG(duration_ms), 0)     AS avg_latency_ms,
  COUNT(DISTINCT user_email)        AS unique_users
FROM fact_api_requests;

-- Cost by model (GET /analytics/models)
SELECT
  model_name,
  COUNT(*)                   AS requests,
  SUM(cost_usd)              AS total_cost_usd,
  AVG(duration_ms)           AS avg_latency_ms
FROM fact_api_requests
GROUP BY model_name
ORDER BY total_cost_usd DESC;

-- Top spenders (GET /analytics/top-users)
SELECT
  user_email,
  SUM(cost_usd)                              AS total_cost_usd,
  SUM(input_tokens + output_tokens)          AS total_tokens
FROM fact_api_requests
GROUP BY user_email
ORDER BY total_cost_usd DESC
LIMIT 10;
```

Connect to PostgreSQL from the host:

```bash
docker compose exec postgres psql -U telemetry -d telemetry
```

---

## Project structure

```
app/                 FastAPI application (routes, schemas, db models)
  api/routes/        REST endpoints (/health, /analytics/*)
  db/                SQLAlchemy models, session factory
etl/                 CLI and pipeline (parsers, transformers, loaders)
dashboard/           Streamlit UI (Home.py)
alembic/             Database migrations
docker/              Container Dockerfiles
tests/               pytest suite
docs/                Architecture and data-model reference
data/raw/            Sample telemetry_logs.jsonl (gitignored; generate locally)
generate_fake_data.py  Synthetic dataset generator
docker-compose.yml   Local stack definition
```

Business logic lives in ETL loaders and service-layer queries — route handlers and Streamlit pages stay thin.

---

## Design decisions

**Why FastAPI sits between Streamlit and PostgreSQL**

Streamlit could query PostgreSQL directly, but a dedicated API layer provides:

1. **Single source of truth for metrics** — aggregation SQL lives once in the API; the dashboard and any external client see identical numbers.
2. **Separation of concerns** — Streamlit handles presentation; FastAPI handles validation, typed responses, and OpenAPI documentation.
3. **Scalability path** — add caching, rate limits, or read replicas at the API tier without touching the UI.
4. **Security** — the dashboard needs read-only HTTP access, not database credentials or write-capable sessions.
5. **Interview/production signal** — mirrors how internal analytics UIs typically consume a backend service rather than embedding SQL in page scripts.

ETL runs as batch jobs outside the request path so API latency stays predictable as event volume grows.

See `docs/architecture.md` and `docs/data-model.md` for the full star-schema roadmap.

---

## Testing

Tests use mocked database sessions — no running PostgreSQL required.

```bash
# Local
pip install -r requirements.txt
pytest

# Inside Docker
docker compose exec api pytest
```

Current coverage includes health check behavior and analytics overview response shape. Run `pytest -v` for per-test output.

---

## Future improvements

- **Expand the star schema** — load `user_prompt`, `tool_result`, and `api_error` facts (see `docs/data-model.md`).
- **Dimension enrichment** — join `employees.csv` for practice, level, and location rollups.
- **Partitioning** — range-partition fact tables on `event_ts` for retention and query pruning.
- **Materialized views** — precompute daily cost and token rollups for faster dashboard loads.
- **Auth and TLS** — protect the API and dashboard for non-local deployments.
- **Observability** — structured request metrics, ETL job duration, and trace IDs across batch and API paths.
- **CI pipeline** — lint, test, and migration checks on every pull request.

---

## License

Internal / portfolio project. Adjust licensing before public distribution.
