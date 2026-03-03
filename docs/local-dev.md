# Local Development Guide

**Issue:** [#833](https://github.com/nimeob/geo-ranking-ch/issues/833) — INFRA-DB-0.wp4
**Stand:** 2026-03-02

This guide covers how to run a local Postgres instance for development and testing — without needing access to the staging RDS.

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Docker | ≥ 24 | With Compose v2 plugin (`docker compose`) |
| `psql` (optional) | any | Only needed for direct host-side SQL; `db-local.sh psql` uses the container's client |
| `bash` | ≥ 4 | macOS ships bash 3; install via `brew install bash` or just use `sh` compat mode |

---

## Quick Start (TL;DR)

```bash
# 1. Clone and enter repo
git clone https://github.com/nimeob/geo-ranking-ch.git
cd geo-ranking-ch

# 2. Create your local .env
cp .env.example .env
# Edit .env if needed (defaults work out of the box)

# 3. Start Postgres
./scripts/db-local.sh start

# 4. Apply schema migrations
./scripts/db-local.sh migrate

# 5. Smoke check
docker compose -f docker-compose.dev.yml exec postgres \
  pg_isready -U georanking -d georanking_dev
# Expected: localhost:5432 - accepting connections
```

---

## Detailed Steps

### Step 1 — Environment Setup

Copy the template and review defaults:

```bash
cp .env.example .env
```

Key variables in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_DB` | `georanking_dev` | Database name |
| `POSTGRES_USER` | `georanking` | DB user |
| `POSTGRES_PASSWORD` | `dev_only_change_me` | **Local only — never use in staging** |
| `POSTGRES_PORT` | `5432` | Host port (change if 5432 is in use) |
| `DATABASE_URL` | `postgresql://georanking:dev_only_change_me@localhost:5432/georanking_dev` | Full DSN for application code |

> ⚠️ **Never commit `.env`** — it's in `.gitignore`. Only `.env.example` is versioned.

### Step 2 — Start the DB

```bash
./scripts/db-local.sh start
```

This runs `docker compose -f docker-compose.dev.yml up -d` and waits until Postgres reports healthy.

Expected output:
```
🐘 Starting local dev Postgres...
⏳ Waiting for Postgres to be healthy...
✅ Postgres is ready.
  DSN: postgresql://georanking:<pass>@localhost:5432/georanking_dev
  Tip: Run ./scripts/db-local.sh migrate to apply schema migrations.
```

### Step 3 — Apply Migrations

```bash
./scripts/db-local.sh migrate
```

By default this delegates to `scripts/db-migrate.py --apply` (DB migration runner from #813, source: `db/migrations/*.sql`).
If `db-migrate.py` is not available, `db-local.sh` falls back to applying `docs/sql/*.sql` directly via `psql`.

Current migration files (runner path):
- `db/migrations/001_core_schema.sql` — Core tables (organizations, users, memberships, api_keys)
- `db/migrations/002_async_jobs_schema.sql` — Async jobs + events
- `db/migrations/003_async_jobs_results.sql` — Result metadata / payload pointers

Expected output (example):
```
🔄 Applying SQL migrations (via db-migrate.py)...
✅ Postgres is ready.
Applying 3 migration(s)...
  → 001_core_schema ... ✓
  → 002_async_jobs_schema ... ✓
  → 003_async_jobs_results ... ✓
✅ 3 migration(s) applied successfully.
```

### Step 4 — Smoke Check

```bash
# Health: pg_isready
docker compose -f docker-compose.dev.yml exec postgres \
  pg_isready -U georanking -d georanking_dev
# ✅ Expected: localhost:5432 - accepting connections

# Verify tables
./scripts/db-local.sh psql
```

In psql:
```sql
\dt
-- Should list: organizations, users, memberships, api_keys, jobs, job_events
\q
```

---

## Common Commands

```bash
# Start
./scripts/db-local.sh start

# Stop (data preserved)
./scripts/db-local.sh stop

# Full reset — DESTROYS all data, starts clean
./scripts/db-local.sh reset

# Container status
./scripts/db-local.sh status

# Apply migrations
./scripts/db-local.sh migrate

# Open psql shell
./scripts/db-local.sh psql
```

---

## Troubleshooting

### Port 5432 already in use

Change `POSTGRES_PORT` in `.env`:
```bash
POSTGRES_PORT=5433
DATABASE_URL=postgresql://georanking:dev_only_change_me@localhost:5433/georanking_dev
```
Then restart: `./scripts/db-local.sh stop && ./scripts/db-local.sh start`.

### Container won't start / stays unhealthy

```bash
# Check logs
docker compose -f docker-compose.dev.yml logs postgres

# Full reset
./scripts/db-local.sh reset
```

### `pg_isready` fails from host (not in container)

The healthcheck runs inside the container. From the host, use:
```bash
# Requires psql installed on host
psql "postgresql://georanking:dev_only_change_me@localhost:5432/georanking_dev" -c "SELECT 1;"
```

Or use the container's client via `./scripts/db-local.sh psql`.

---

## Architecture Notes

- **Local:** `docker-compose.dev.yml` → Postgres 16 Alpine → volume `georanking_dev_pgdata`
- **Staging:** AWS RDS Postgres (provisioned via `infra/terraform/staging_db.tf`, see [STAGING_DB_RUNBOOK.md](STAGING_DB_RUNBOOK.md))
- **Migrations:** currently manual `psql` against `.sql` files; a proper migration runner (Flyway/Alembic) is tracked in [#813](https://github.com/nimeob/geo-ranking-ch/issues/813)

---

## Related Issues & Docs

- [#825](https://github.com/nimeob/geo-ranking-ch/issues/825) — Terraform staging RDS skeleton
- [#826](https://github.com/nimeob/geo-ranking-ch/issues/826) — ECS secrets wiring
- [#827](https://github.com/nimeob/geo-ranking-ch/issues/827) — Staging DB runbook
- [#813](https://github.com/nimeob/geo-ranking-ch/issues/813) — Postgres migration runner (blocked on #804)
- [STAGING_DB_RUNBOOK.md](STAGING_DB_RUNBOOK.md) — Staging DB apply + smoke
