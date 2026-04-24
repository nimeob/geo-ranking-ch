# gui-webkit-smoke Entblockung (2026-04-24T03:21:52Z)

## Blocker
- CI-Workflow `gui-webkit-smoke` (Run `24867587845`, Job `72807522857`) scheiterte im Step `Start local GUI service`.
- Root Cause: Startkommando war falsch (`python3 -m src.api.web_service`), dieses Paket ist nicht direkt ausführbar (kein `__main__`).

## Fix
- Datei: `.github/workflows/gui-webkit-smoke.yml`
- Änderung:
  - Startkommando auf den tatsächlich ausführbaren Service umgestellt:
    - `HOST=127.0.0.1 PORT=8877 APP_VERSION=dev python3 -m src.web_service`
  - Frühzeitige Exit-Erkennung eingebaut (`kill -0` PID-Check)
  - Bei Startfehler: `tail -n 200 /tmp/gui-webkit-service.log` als direkte Diagnose im selben Step
  - Stop-Step auf leisen PID-Kill gehärtet (`2>/dev/null || true`)

## Lokale Verifikation
- Start-/Healthz-Sequenz analog Workflow lokal ausgeführt: **ok**
  - `GUI service is ready`
  - `healthz check passed`

## Dev-UI Mitprüfung
- Ausgeführt:
  - `npm run smoke:gui:webkit -- --base-url https://www.dev.georanking.ch/gui`
- Evidence:
  - JSON: `reports/evidence/issue-986-webkit-smoke-20260424T032137Z.json`
  - Screenshot: `reports/evidence/issue-986-webkit-ios-20260424T032137Z.png`
- Ergebnis:
  - `ok: true`
  - `/gui` lädt, Login-Entry sichtbar, Map pinch/pan Checks bestanden.
  - Auf diesem Host lief der Check via Chromium-Fallback (native WebKit-Libs lokal fehlend); CI nutzt `playwright install --with-deps webkit` und ist davon nicht betroffen.
