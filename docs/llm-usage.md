# LLM usage and generated components

This project was developed with **AI-assisted tooling (Cursor Agent)** under explicit project rules and a custom dataset skill. The author owns and can explain every committed line.

## Tool used

- **Cursor IDE** with Agent mode
- **Project rules:** `.cursor/rules/project-rules.mdc`
- **Custom skill:** `.cursor/skills/telemetry-dataset/SKILL.md`

No API keys or LLM credentials are stored in the repository.

## Agent-generated or agent-assisted components

| Area | Files | Notes |
|------|-------|-------|
| ETL pipeline | `etl/run.py`, `etl/parsers/events.py`, `etl/loaders/postgres.py`, `etl/transformers/enrich.py` | CLI, validation, PostgreSQL load, Polars enrichment |
| Database | `alembic/`, `app/db/models/` | Migrations and ORM models |
| API | `app/api/routes/`, `app/services/analytics.py`, `app/api/schemas/` | Health + analytics endpoints, service layer |
| Dashboard | `dashboard/Home.py` | Streamlit + Plotly, persona views |
| Sample data | `generate_fake_data.py` | Synthetic JSONL + employees.csv |
| Tests | `tests/` | Health and analytics contract tests |
| Documentation | `README.md`, `docs/architecture.md`, `docs/data-model.md`, `docs/agent-setup.md` | Setup, architecture, agent reproduction |
| Docker | `docker-compose.yml`, `docker/*.Dockerfile` | Local stack orchestration |
| Agent config | `.cursor/rules/`, `.cursor/skills/` | Reproducible assistant tuning |

## Human-owned decisions

- **MVP scope:** Load `api_request` facts first; document full star schema as roadmap in `docs/data-model.md`.
- **API between Streamlit and PostgreSQL** — single metrics source, OpenAPI, security boundary (see README design decisions).
- **Employee enrichment** — join `employees.csv` into `dim_users` during ETL for practice/level analytics.
- **Persona-based dashboard** — Executive, Engineering Manager, FinOps views for different stakeholders.
- **Windows Docker fix** — `user: "0:0"` in Compose for bind-mount permissions (local dev).

## Problems encountered

| Problem | Resolution |
|---------|------------|
| Docker `metadata.db: read-only` on Windows | Disk space on C:; prune Docker/WSL when full |
| Bind-mount permission errors on Windows | Run api/dashboard as root in Compose for dev |
| Event name variants (`api_request` vs `claude_code.api_request`) | `etl/transformers/normalize.py` |
| `employees.csv` unused after generation | Wired into `etl.run load --employees` and analytics joins |

## What would change next

- Load additional fact tables (`user_prompt`, `tool_result`, `api_error`).
- CI pipeline (lint, pytest, migration check).
- Integration tests against ephemeral PostgreSQL.
- Materialized views for heavy dashboard queries.

## Verification without LLM

```bash
docker compose exec api pytest
docker compose exec api python -m etl.run inspect --input data/raw/telemetry_logs.jsonl --limit 3
curl http://localhost:8000/analytics/overview
```

These commands validate the deliverable independently of any AI tooling.
