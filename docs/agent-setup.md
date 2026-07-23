# Agent setup — Claude Telemetry Analytics

This repository includes a **reproducible Cursor agent configuration** used to build the analytics platform. Reviewers can replicate the same assistant behavior without API keys or paid-only tooling.

## Tooling

| Component | Location | Purpose |
|-----------|----------|---------|
| Project rules | `.cursor/rules/project-rules.mdc` | Stack, architecture, and code-quality standards (always applied) |
| Dataset skill | `.cursor/skills/telemetry-dataset/SKILL.md` | JSONL schema, ETL commands, API/SQL patterns, troubleshooting |

## Reproducing the setup

1. **Clone the repository** and open it in [Cursor](https://cursor.com).
2. **Verify rules** — Cursor loads `.cursor/rules/project-rules.mdc` automatically (`alwaysApply: true`).
3. **Verify skill** — The skill at `.cursor/skills/telemetry-dataset/` is discovered from the project. Ask the agent to:
   - inspect `data/raw/telemetry_logs.jsonl`
   - run the ETL load with employee enrichment
   - explain analytics endpoints or SQL rollups
4. **Optional MCP** — No MCP servers are required for this project. If you add filesystem or database MCP tools locally, keep credentials out of the repo and document them in your private environment only.

## What the setup improves

- **Consistent stack choices** — Python 3.12, FastAPI, Polars for enrichment, PostgreSQL, Streamlit, Alembic.
- **Dataset-aware workflows** — The telemetry skill encodes JSONL shape, event normalization, and load commands so the agent does not guess file formats.
- **Interview-ready code style** — Type hints, docstrings, logging, env-based config enforced by project rules.

## Secrets policy

- Copy `.env.example` → `.env` for local credentials.
- Never commit `.env`, API keys, or personal MCP tokens.
- Docker Compose overrides `DATABASE_URL` to reach the `postgres` service.

## Suggested agent prompts

```
Inspect the first 5 records of data/raw/telemetry_logs.jsonl and summarize event types.

Load telemetry with employee enrichment and verify row counts in PostgreSQL.

Add a pytest for GET /analytics/practices without breaking existing tests.
```

## Extending the setup

To add another skill:

1. Create `.cursor/skills/<skill-name>/SKILL.md` with YAML frontmatter (`name`, `description`).
2. Document trigger scenarios and concrete commands.
3. Reference the skill from this file and `README.md`.

See Cursor docs: [Agent Skills](https://docs.cursor.com/context/skills).
