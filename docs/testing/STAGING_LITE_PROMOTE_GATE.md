# Staging-lite Promote-Gate (BL-341.wp3)

## Ziel
Reproduzierbarer Promote-Entscheid mit klaren Abort-/Rollback-Pfaden, auch ohne voll ausgebautes `staging`-Environment.

Der Gate-Runner prüft:

1. **Digest-Match** (`candidate_digest` == `approved_digest`)
2. **Smoke-Command** erfolgreich (Exit `0`)

Nur wenn beides erfüllt ist, lautet die Entscheidung `promote_ready`.

## Runner

```bash
python3 scripts/run_staging_lite_promote_gate.py \
  --candidate-digest sha256:<candidate> \
  --approved-digest sha256:<approved> \
  --smoke-command "./scripts/run_bl31_routing_tls_smoke.sh --api-base-url https://api.dev.georanking.ch --app-base-url https://www.dev.georanking.ch" \
  --artifact-dir artifacts/staging-lite
```

## Exit-Codes

- `0` → `promote_ready`
- `10` → `abort` wegen `digest_mismatch`
- `20` → `abort` wegen `smoke_failed`

## Artefakte

Der Runner schreibt pro Lauf:

- `artifacts/staging-lite/latest.json`
- `artifacts/staging-lite/latest.md`
- `artifacts/staging-lite/history/<timestamp>.json`
- `artifacts/staging-lite/history/<timestamp>.md`

## Abort-/Rollback-Regel

Bei `abort` gilt:

1. Keine Promotion ausführen.
2. Falls bereits teilweise ausgerollt wurde: service-lokalen Rollback gemäß
   [`docs/BL31_DEPLOY_ROLLBACK_RUNBOOK.md`](../BL31_DEPLOY_ROLLBACK_RUNBOOK.md) durchführen.
3. Nach Rollback Pflicht-Smoke (`/health`, `/healthz`) erneut ausführen.

## Regression

```bash
pytest -q tests/test_staging_lite_promote_gate.py
```
