# GUI Mobile UX Smoke (Issue #1016)

## Kontext
- Issue: [#1016](https://github.com/nimeob/geo-ranking-ch/issues/1016)
- Verwandt: [#1015](https://github.com/nimeob/geo-ranking-ch/issues/1015), [#981](https://github.com/nimeob/geo-ranking-ch/issues/981)

## Ziel
Regression-Schutz für zwei Mobile-Web-Kernbereiche:

1. **Burger-Menü UX** (Toggle, Overlay/Backdrop, Click-Outside, Body-Scroll-Lock)
2. **Pinch-Zoom Smoothness-Basischeck** (kein starker Main-Thread-Jank + Zoom-Änderung erfolgt)

## Reproduktion
Voraussetzungen:
- lokaler GUI-Service erreichbar (`PORT=8877 python3 -m src.api.web_service`)
- Node.js + `playwright` installiert

Smoke ausführen:

```bash
node scripts/run_issue_1016_mobile_ux_smoke.mjs
```

Optionales Ziel setzen:

```bash
BASE_URL="http://127.0.0.1:8877/gui" node scripts/run_issue_1016_mobile_ux_smoke.mjs
```

## Evidence
Der Smoke erzeugt pro Lauf:

- `reports/evidence/issue-1016-mobile-ux-smoke-<timestamp>.json`
- `reports/evidence/issue-1016-mobile-ux-<timestamp>.png`

### Lauf 2026-03-03
- Target: `http://127.0.0.1:8877/gui`
- JSON: `reports/evidence/issue-1016-mobile-ux-smoke-20260303T220059Z.json`
- Screenshot: `reports/evidence/issue-1016-mobile-ux-20260303T220059Z.png`

## Prüfkriterien (DoD-Bezug)
- **Menü reagiert konsistent auf Mobile**
  - `aria-expanded`, `aria-hidden`, Backdrop-Sichtbarkeit und Body-Scroll-Lock wechseln synchron
- **Pinch-Zoom wirkt flüssiger**
  - Zoom-Level steigt nach Pinch-Geste
  - keine Long-Tasks > 50ms im Kernpfad des synthetischen Pinch-Smokes
- **Smoke-Test deckt Kerninteraktionen ab**
  - Burger open/close + Pinch-Smoke in einem reproduzierbaren Script
