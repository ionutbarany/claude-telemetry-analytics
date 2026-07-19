# Architecture — Claude Telemetry Analytics

## Project goal

Build a production-style telemetry analytics platform that ingests event data, transforms it into analytically useful aggregates, persists results in PostgreSQL, exposes queryable APIs, and surfaces insights through interactive dashboards.

The system is designed as interview-ready engineering: modular packages, typed Python, environment-based configuration, and clear separation between ingestion, storage, API, and presentation layers.

---

## High-level architecture

```
                    +------------------+
                    |  External / raw  |
                    |  telemetry data  |
                    |  (files, APIs)   |
                    +--------+---------+
                             |
                             v
              +------------------------------+
              |            ETL               |
              |  parsers → transforms → load |
              |         (Polars)             |
              +--------------+---------------+
                             |
                             v
              +------------------------------+
              |         PostgreSQL           |
              |  raw / staging / aggregates  |
              |  (SQLAlchemy + Alembic)      |
              +------+---------------+-------+
                     |               |
          read/write |               | read
                     v               v
          +----------------+   +------------------+
          |    FastAPI     |   |    Streamlit     |
          |  REST endpoints|   |  Plotly charts   |
          |  services/domain|  |  dashboard pages |
          +--------+-------+   +--------+---------+
                   |                    |
                   v                    v
            API consumers         Analysts / demo
            (clients, tools)      (local browser)
```

Local orchestration uses **Docker Compose** so PostgreSQL, the API, and the dashboard can run as coordinated services with shared configuration.

---

## Components

### ETL (`etl/`)

Responsible for moving data from source to warehouse shape:

| Stage | Responsibility |
|-------|----------------|
| **Parsers** | Read and validate raw inputs (CSV, JSON, or similar). Fail early on schema violations. |
| **Transforms** | Clean, enrich, and aggregate with Polars (joins, window metrics, scoring). Business rules live here, not in routes or UI. |
| **Loaders** | Write to PostgreSQL via SQLAlchemy sessions or bulk insert paths. Idempotent loads where practical. |

ETL is a batch-oriented pipeline suitable for scheduled runs or one-shot backfills. Heavy computation stays out of the request path.

### Database (PostgreSQL)

System of record for telemetry and derived metrics. Typical layers:

- **Staging / raw** — near-source records for audit and reprocessing
- **Curated events** — cleaned, typed event rows
- **Aggregates** — precomputed summaries for API and dashboard latency

Schema evolution goes through **Alembic** migrations. Application access uses **SQLAlchemy 2.0** (`select()`, mapped models, explicit sessions)—not the legacy Query API.

### API (`app/`)

FastAPI application that:

- Exposes REST endpoints for health, events, and analytics queries
- Delegates business logic to service/domain modules
- Reads configuration from environment variables and fails fast when required settings are missing
- Uses dependency-injected DB sessions for request-scoped work

Route handlers stay thin: validate input, call a service, return a typed response.

### Dashboard (`dashboard/`)

Streamlit + Plotly UI for exploration and demos:

- Pages and components consume API responses or shared query helpers
- Charts and filters live in presentation code; aggregations and scoring stay in ETL/services
- Intended for local or internal use, not as a public multi-tenant product surface

---

## Technology choices

### Why FastAPI

- **Performance and async support** — efficient for I/O-bound API work without sacrificing sync SQLAlchemy patterns where needed.
- **First-class typing** — Pydantic models give request/response validation and OpenAPI docs for free; aligns with typed service code.
- **Interview signal** — demonstrates modern Python API design: dependency injection, clear layering, automatic schema documentation.
- **Ergonomics** — less boilerplate than Flask for structured APIs; lighter than Django for a focused analytics backend.

### Why PostgreSQL

- **Reliability and SQL depth** — ACID transactions, strong constraints, and rich SQL for analytics-friendly queries and indexes.
- **Operational familiarity** — widely used in production; easy to run locally and in Compose.
- **Fit for this domain** — event storage, aggregations, and time-range filters map well to relational modeling plus indexes (and later partitioning if volume grows).
- **Ecosystem** — mature drivers (`psycopg`), SQLAlchemy, and Alembic support.

Alternatives (e.g. DuckDB for local analytics-only, or a warehouse like BigQuery) are deferred until volume or concurrency justifies them. PostgreSQL keeps a single durable store for API and dashboard.

### Why Streamlit

- **Speed to insight** — interactive charts and filters with minimal UI code; ideal for analytics demos and stakeholder reviews.
- **Python-native** — same language and libraries as ETL/API; Plotly integrates cleanly.
- **Scope match** — internal analytics UI does not need a full SPA framework early. Streamlit can later sit behind the same API the product UI would use.

### Why Polars

- **Performance** — columnar engine and lazy evaluation handle larger event files faster than Pandas for typical ETL.
- **Clear API** — expressive expressions and type-aware transforms reduce silent dtype bugs.
- **Project standard** — Polars is preferred for DataFrames; Pandas only when a dependency forces it.
- **Pipeline clarity** — composable transforms map cleanly onto modular `etl/` packages.

### Why Docker Compose

- **Reproducible local stack** — one command to bring up PostgreSQL, API, and dashboard with shared env and networking.
- **Parity with deployment thinking** — services are defined as processes with ports and dependencies, not ad-hoc local installs.
- **Isolation** — database credentials and ports stay in Compose/env files, not hardcoded paths.
- **Interview narrative** — shows how components are intended to run together in a real environment.

---

## End-to-end data flow

1. **Ingest** — Raw telemetry arrives as files or pull sources. Parsers validate required fields and types.
2. **Transform** — Polars pipelines clean nulls, normalize timestamps/IDs, and compute derived metrics (usage, cost proxies, quality scores, etc.).
3. **Load** — Results land in PostgreSQL (staging then curated/aggregate tables) under transactional or controlled batch writes.
4. **Migrate** — Alembic keeps schema versions explicit across environments.
5. **Serve (API)** — FastAPI services query PostgreSQL and return JSON for clients and automation.
6. **Serve (UI)** — Streamlit pages call the API (preferred) or shared read helpers and render Plotly visualizations.
7. **Observe** — Structured application logs record job success/failure, request latency, and configuration errors.

Happy path: *source → ETL → PostgreSQL → FastAPI / Streamlit → consumer*.

---

## Scalability considerations

| Concern | Current approach | Growth path |
|---------|------------------|-------------|
| **ETL volume** | Batch Polars jobs | Chunked files, lazy scans, parallel workers; optional object storage for raw archives |
| **Write contention** | Single DB writer during loads | Staging tables + merge/upsert; schedule loads off peak |
| **Read latency** | Aggregates + indexes | Materialized views, partitioning by time, read replicas |
| **API load** | Single FastAPI process | Multiple Uvicorn workers; reverse proxy; cache hot aggregates |
| **Dashboard** | Single Streamlit instance | Keep dashboard read-only against API; scale API/DB first |
| **Schema change** | Alembic migrations | Expand/contract migrations; avoid long locks on large tables |

Design principle: keep expensive computation in ETL and pre-aggregates so the API remains a thin, cacheable read layer.

---

## Security considerations

- **Secrets** — Credentials and connection strings come from environment variables (see `.env.example`). Never commit `.env` or hardcode paths/passwords.
- **Fail fast** — Missing required config should raise a clear error at startup, not fail mid-request with opaque messages.
- **Least privilege** — DB users for ETL (write) and API/dashboard (read-heavy) should be separable in production.
- **Network** — Compose binds services for local use; production should place PostgreSQL on a private network and expose only the API (and optionally the dashboard) through controlled ingress.
- **Input validation** — FastAPI/Pydantic validates request payloads; ETL parsers reject malformed rows before load.
- **SQL safety** — Prefer parameterized SQLAlchemy queries; avoid string-built SQL.
- **Dashboard exposure** — Treat Streamlit as an internal tool unless auth and TLS are added; do not assume it is safe on the public internet by default.

---

## Observability and logging

- **Standard library `logging`** — Operational output uses `logging`, not `print`.
- **Structured context** — Log ETL job name, row counts, duration, and failure reason; log API method, path, status, and latency where useful.
- **Levels** — `INFO` for successful lifecycle events; `WARNING` for recoverable anomalies (skipped rows); `ERROR`/`EXCEPTION` for failed loads or unhandled errors.
- **Correlation** — Prefer a request or job ID in log records so API and batch runs can be traced across components.
- **Health** — API health/readiness endpoints should verify process liveness and, when appropriate, DB connectivity.
- **Future hooks** — Metrics (request rate, ETL duration, error counts) and distributed tracing can attach later without changing the modular layout; keep instrumentation at service boundaries.

---

## Package layout (reference)

```
app/          FastAPI application (API, core, db, services)
etl/          parsers, transformers, loaders
dashboard/    Streamlit pages and components
tests/        pytest suite
docs/         project documentation
docker/       container-related assets
```

Business logic belongs in services, domain modules, and ETL transforms—not in route handlers or Streamlit page scripts.

---

## Summary

The platform is a classic analytics pipeline with a modern Python stack: **Polars for ETL**, **PostgreSQL as system of record**, **FastAPI for programmatic access**, and **Streamlit for interactive analysis**, orchestrated locally with **Docker Compose**. The architecture favors clear module boundaries, environment-based configuration, and pre-aggregation so the system can grow from demo data to production-scale telemetry without rewriting the core design.
`)