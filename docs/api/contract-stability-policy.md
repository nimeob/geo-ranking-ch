# BL-20.1.d.wp4 — Stability Guide + Contract-Change-Policy

Stand: 2026-02-26  
Gültig für: API-Vertrag [`docs/api/contract-v1.md`](./contract-v1.md) und Feldmanifest [`docs/api/field_catalog.json`](./field_catalog.json)

## 1) Ziel

Diese Richtlinie definiert, welche API-Felder Integratoren robust voraussetzen dürfen und wie Contract-Änderungen als **Breaking** oder **Non-Breaking** klassifiziert werden.

## 2) Stabilitätsklassen (verbindlich)

| Klasse | Bedeutung | Integrator-Regel |
|---|---|---|
| `stable` | Vertraglich stabil im Rahmen von `/api/v1`; Änderungen nur rückwärtskompatibel. | Darf fest konsumiert werden. |
| `beta` | Vorläufiges Feld; Struktur/Semantik kann sich ändern. | Nur defensiv konsumieren (Feature-Flag/Fallback). |
| `internal` | Internes Spiegel-/Diagnosefeld ohne externen Stabilitätsanspruch. | Nicht als Integrationsvertrag verwenden. |

### Stabile Felder für Integratoren

- Die stabile Integrationsbasis wird über `stability: "stable"` im Feldmanifest `docs/api/field_catalog.json` festgelegt.
- Felder mit `stable` dürfen Integratoren als vertraglich belastbar behandeln.
- Felder mit `beta` oder `internal` dürfen **nicht** als harte Abhängigkeit modelliert werden.

## 3) Contract-Change-Policy

### 3.1 Non-Breaking (innerhalb `/api/v1` erlaubt)

Beispiele:

- Neues **optionales** Feld wird ergänzt.
- Neue, optionale Struktur in einem bestehenden Objekt wird ergänzt.
- Präzisere Dokumentation ohne Verhaltensänderung.
- Stabilitätsstufe `beta -> stable` (Aufwertung).

### 3.2 Breaking (für `/api/v1` unzulässig, nur via neue Hauptversion)

Beispiele:

- Entfernen oder Umbenennen eines bestehenden Felds.
- Typänderung eines bestehenden Felds (z. B. `string -> object`).
- Ein bislang optionales Feld wird verpflichtend.
- Semantikänderung, die bestehende Integrationen fachlich bricht.
- Stabilitätsstufe `stable -> beta/internal` (Abwertung).

### 3.3 Versionsregel bei Breaking Changes

Breaking Changes werden **nicht** still in `/api/v1` ausgerollt. Sie erfordern:

1. neue Hauptversion (z. B. `/api/v2`),
2. dokumentierte Migration,
3. klaren Release-Hinweis.

## 4) Changelog-/Release-Hinweisprozess

Bei jeder Contract-Änderung:

1. Änderung klassifizieren (**Non-Breaking** oder **Breaking**).
2. `docs/api/field_catalog.json` aktualisieren (`stability`, Typ, Required-Status, Shape-Zuordnung).
3. Relevante Beispielpayloads unter `docs/api/examples/**` aktualisieren.
4. Validierung lokal ausführen:
   - `python3 scripts/validate_field_catalog.py`
   - `pytest -q tests/test_api_contract_v1.py tests/test_api_field_catalog.py`
5. Änderungsnotiz in [`CHANGELOG.md`](../../CHANGELOG.md) unter `[Unreleased]` ergänzen.
6. Bei Breaking-Änderung zusätzlich explizite Migrationshinweise (alt -> neu) in den Release-Notes dokumentieren.

## 5) Referenzen

- API-Vertrag: [`docs/api/contract-v1.md`](./contract-v1.md)
- Feldmanifest: [`docs/api/field_catalog.json`](./field_catalog.json)
- Changelog: [`CHANGELOG.md`](../../CHANGELOG.md)
