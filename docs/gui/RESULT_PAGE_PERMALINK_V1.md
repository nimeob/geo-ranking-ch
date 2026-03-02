# Result Page Permalink (V1)

Ziel: Eine **stabile, sharebare Result-Page** basierend auf `result_id`, die Result-Daten über den API-Permalink-Endpunkt lädt.

## URL / Deep-Link

Die UI bietet eine Result-Page unter:

- `GET /results/<result_id>`

Beispiel:

- `https://<ui-host>/results/550e8400-e29b-41d4-a716-446655440000`

## API-Abhängigkeit

Die Page lädt JSON von:

- `GET /analyze/results/<result_id>?view=latest`

Optional kann `view=requested` genutzt werden.

### API Base URL

Wenn die UI nicht am selben Origin wie die API läuft, kann der UI-Service via Env var die API umbiegen:

- `UI_API_BASE_URL=https://api.<env>.<domain>`

Dann nutzt die Result-Page automatisch:

- `https://api.<env>.<domain>/analyze/results/<result_id>`

## Auth (optional)

Falls das Deployment geschützt ist:

- Auf der Result-Page kann ein **Bearer Token** eingetragen werden.
- Das Token wird (best-effort) in `sessionStorage` gehalten.

## Lokaler Test

1) UI starten:

```bash
python -m src.ui.service
```

2) In einem zweiten Terminal ein `result_id` erzeugen (Async Smoke Test):

```bash
# Beispiel: Lokale API auf http://localhost:8081
SERVICE_API_BASE_URL="http://localhost:8081" python3 scripts/run_async_jobs_smoketest.py
```

3) Result-Page öffnen:

- `http://localhost:8080/results/<result_id>`

Hinweis: Für den lokalen UI→API Call kann auch `UI_API_BASE_URL` gesetzt werden, wenn UI/API auf unterschiedlichen Ports laufen.
