# Presentation outline — Claude Telemetry Analytics

Brief deck or live demo structure (~5–8 minutes).

## 1. Problem

Claude Code emits rich OpenTelemetry logs (prompts, API calls, tools, errors). Product and platform teams need **actionable usage and cost insights** without querying raw JSONL by hand.

## 2. Approach

End-to-end analytics platform:

```
JSONL telemetry → ETL (validate + enrich) → PostgreSQL → FastAPI → Streamlit
```

**Key decisions:**

- Batch ETL outside the request path for predictable API latency.
- FastAPI as the metrics layer so dashboard and external clients share one source of truth.
- Employee CSV enrichment for **practice / level** rollups (user roles requirement).

## 3. Demo flow

1. `.\scripts\bootstrap.ps1` — one command to start stack, migrate, generate data, load warehouse.
2. `curl http://localhost:8000/health` — DB connectivity.
3. `curl http://localhost:8000/analytics/overview` — platform KPIs.
4. Open **http://localhost:8501** — switch personas:
   - **Executive** — KPIs + daily trends
   - **Engineering Manager** — practice & level adoption
   - **FinOps** — spend by model, practice, top users

## 4. Findings (example talking points)

After loading synthetic data (~113k events):

- Which models drive the majority of spend?
- Which practices or levels show highest adoption?
- Daily trend: is usage growing linearly or spiking on certain days?
- Top users — candidates for quota policies or enablement.

(Replace with numbers from your loaded dataset during the live demo.)

## 5. Agent-assisted development

- Cursor project rules + **telemetry-dataset skill** committed to repo.
- Agent produced ETL, API, dashboard, tests, and docs; author validated and integrated.
- See `docs/agent-setup.md` and `docs/llm-usage.md`.

## 6. Limitations & next steps

- MVP loads `api_request` facts; star schema roadmap in `docs/data-model.md`.
- No ML / streaming (optional enhancements).
- Future: CI, auth, partitioning, additional fact tables.

## 7. Q&A preparation

Be ready to explain:

- Why Streamlit does not query PostgreSQL directly.
- How `employees.csv` joins onto `dim_users`.
- How event names are normalized in the parser.
- What you would do differently with more time.
