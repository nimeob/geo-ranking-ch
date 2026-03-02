# Async DB Cutover Runbook

**Issue:** #842 (ASYNC-DB-0.wp5)  
**Date:** 2026-03-02  
**Purpose:** Migrate async job history from the file-backed store
(`runtime/async_jobs/store.v1.json`) to Postgres, and activate the DB
backend via feature flag.

---

## Prerequisites

Before starting, verify:

- [ ] Migration 002 applied (`002_async_jobs_schema.sql` — `jobs`, `job_events`)
- [ ] Migration 003 applied (`003_async_jobs_results.sql` — `job_results`, `user_id`)
- [ ] Staging DB reachable from ECS task (see #804 / #827 Runbook)
- [ ] `DATABASE_URL` / `ASYNC_DB_URL` environment secret set in ECS task definition
- [ ] `DbAsyncJobStore` smoke-tested locally (`python3 -c "from src.shared.async_job_store_db import DbAsyncJobStore; print('ok')"`)

---

## Step 1 — Apply Migrations

```bash
# Verify pending migrations
DATABASE_URL=postgresql://... python scripts/db-migrate.py --status

# Apply (idempotent)
DATABASE_URL=postgresql://... python scripts/db-migrate.py --apply
```

Expected output: `002_async_jobs_schema` and `003_async_jobs_results` both
show status `applied`.

---

## Step 2 — Run Backfill (Dry Run First)

```bash
ASYNC_JOBS_STORE_FILE=runtime/async_jobs/store.v1.json \
  python scripts/backfill_async_jobs_to_db.py --dry-run
```

Expected output:
```
[INFO] backfill source: runtime/async_jobs/store.v1.json
[INFO] mode: dry-run
[INFO] found: N jobs, M results in store file
[OK]   N/N valid job records
[OK]   M/M valid result records
[INFO] dry-run complete — no changes made
```

---

## Step 3 — Run Backfill (Apply)

```bash
DATABASE_URL=postgresql://... \
ASYNC_JOBS_STORE_FILE=runtime/async_jobs/store.v1.json \
  python scripts/backfill_async_jobs_to_db.py --apply
```

Expected output:
```
[OK]   jobs:    N inserted, 0 skipped (already present or invalid)
[OK]   events:  E inserted, 0 skipped
[OK]   results: M inserted, 0 skipped
[INFO] backfill complete
```

The script is **idempotent** — running it a second time will show
`0 inserted, N skipped` without errors.

---

## Step 4 — Verify Row Counts in DB

```sql
SELECT COUNT(*) FROM jobs;
SELECT COUNT(*) FROM job_events;
SELECT COUNT(*) FROM job_results;
```

Compare with the `[INFO] found: N jobs, M results` output from Step 2.

---

## Step 5 — Activate DB Backend (Staging)

Set the feature flag in the ECS task definition / environment:

```
ASYNC_STORE_BACKEND=db
ASYNC_DB_URL=postgresql://user:pass@rds-staging-host/geo_ranking
```

Redeploy the staging task. After deployment:

```bash
# Smoke test: should return 200 with history from DB
curl -s -H "Authorization: Bearer <token>" \
  https://staging.geo-ranking-ch.example.com/analyze/history | jq .
```

Verify:
- [ ] Response contains `{ "ok": true, "history": [...], "total": N, "limit": 50, "offset": 0 }`
- [ ] Result permalinks (`/analyze/results/<id>`) return correct data
- [ ] Wrong-org result lookup returns 404

---

## Step 6 — Archive File Store

Once DB backend is confirmed stable in staging (≥24h), archive the file:

```bash
# Archive (do NOT delete — keep for rollback)
mv runtime/async_jobs/store.v1.json runtime/async_jobs/store.v1.json.archived-$(date +%Y%m%d)
```

Commit and push the archive rename (or note in deployment log).

---

## Rollback Plan

If DB backend causes issues:

1. Set `ASYNC_STORE_BACKEND=file` (or unset it) in ECS environment
2. Redeploy — file-backed store resumes automatically
3. Restore archived file if needed:
   ```bash
   mv runtime/async_jobs/store.v1.json.archived-YYYYMMDD runtime/async_jobs/store.v1.json
   ```
4. File store continues as before; DB rows remain (no data loss)

> **Note:** Jobs created during the DB-backend window will NOT appear in
> the file store after rollback. If continuity matters, run the backfill
> script again in reverse (DB → file) before switching back.

---

## Checklist Summary

| Step | Action | Status |
|------|--------|--------|
| 1 | Migrations 002 + 003 applied | ☐ |
| 2 | Backfill dry-run passes | ☐ |
| 3 | Backfill applied (idempotency verified) | ☐ |
| 4 | DB row counts match | ☐ |
| 5 | ASYNC_STORE_BACKEND=db activated + smoke test | ☐ |
| 6 | File store archived | ☐ |
