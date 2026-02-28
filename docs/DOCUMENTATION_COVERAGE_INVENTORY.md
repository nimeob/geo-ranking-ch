# Dokumentationsabdeckung – Inventar (Code + intern + User)

> Stand: 2026-02-27  
> Scope: BL-YY.1 / Issue #264

## Ziel
Dieses Dokument inventarisiert die vorhandene Dokumentationsabdeckung für die zentralen Funktionsbereiche (Code, interne Doku, User-Doku) und markiert offensichtliche Lücken für die nachgelagerte Gap-Priorisierung (#265).

## Methodik
1. Relevante Kernmodule unter `src/` identifiziert.
2. Vorhandene interne Dokumentation (`docs/*.md`, API-/Operations-/Mapping-Dokus) zugeordnet.
3. Vorhandene User-Dokumentation (`docs/user/*.md`, README-Abschnitte) zugeordnet.
4. Offensichtliche Lücken als `Gap` markiert (Inventarisierung, noch keine Priorisierung).

## Inventar nach Funktionsbereich

| Funktionsbereich | Relevanter Code | Interne Doku vorhanden | User-Doku vorhanden | Gap-Hinweis |
|---|---|---|---|---|
| API Runtime / Request-Handling | `src/api/web_service.py` (Legacy-Wrapper: `src/web_service.py`) | `docs/api/contract-v1.md`, `docs/api/contract-stability-policy.md`, `docs/OPERATIONS.md`, `docs/testing/WEB_SERVICE_RESULT_PATH_COVERAGE.md` | `docs/user/api-usage.md`, `docs/user/troubleshooting.md`, README API-Abschnitte | **Niedrig** – starke Coverage vorhanden; Modul-Docstring im kanonischen API-Entrypoint fehlt als schnelle Code-Orientierung |
| Address Intelligence / Aggregation | `src/address_intel.py` | `docs/api/scoring_methodology.md`, `docs/BACKLOG.md` (Implementierungsnachweise) | `docs/user/api-usage.md`, README CLI-Usage | **Mittel** – kein dedizierter Architektur-/Flow-Deep-Dive für Address-Intel-Pipeline |
| Geodaten-Utilities / CH-Lookups | `src/geo_utils.py`, `src/gwr_codes.py` | `docs/DATA_SOURCE_FIELD_MAPPING_CH.md`, `docs/DATA_SOURCE_INVENTORY_CH.md` | README (CLI-Beispiele), `docs/user/api-usage.md` (indirekt über `/analyze`) | **Mittel** – keine fokussierte User-Referenz für Utility-Layer (nur indirekte Nutzung) |
| Preference-/Personalization-Scoring | `src/personalized_scoring.py`, `src/suitability_light.py` | `docs/api/scoring_methodology.md`, `docs/api/contract-v1.md`, `docs/api/field-reference-v1.md` | `docs/user/api-usage.md`, `docs/user/explainability-v2-integrator-guide.md` | **Niedrig** – Methodik gut dokumentiert; Modul-Docstrings in beiden Dateien fehlen |
| Source-Mapping & Transform-Regeln | `src/mapping_transform_rules.py` | `docs/DATA_SOURCE_FIELD_MAPPING_CH.md`, `docs/mapping/source-field-mapping.ch.v1.json`, `docs/mapping/source-field-mapping.schema.json` | README (technischer Überblick) | **Mittel** – user-nahe Erklärung der Mapping-Regeln fehlt (nur intern/technisch vorhanden) |
| Legacy-Fallback / Fingerprint-Audit | `src/legacy_consumer_fingerprint.py` | `docs/LEGACY_IAM_USER_READINESS.md`, `docs/LEGACY_CONSUMER_INVENTORY.md`, `docs/OPENCLAW_OIDC_FIRST_FALLBACK_PLAN.md` | praktisch keine direkte Endnutzer-Doku (internes Ops-Thema) | **Niedrig (fachlich ok)** – als internes Thema ausreichend; Modul-Docstring fehlt |

## Datei-/Artefakt-Inventar (kompakt)

### Interne Doku (Top-Level)
- `docs/ARCHITECTURE.md`
- `docs/OPERATIONS.md`
- `docs/VISION_PRODUCT.md`
- `docs/DATA_SOURCE_INVENTORY_CH.md`
- `docs/DATA_SOURCE_FIELD_MAPPING_CH.md`
- `docs/api/contract-v1.md`
- `docs/api/contract-stability-policy.md`
- `docs/api/scoring_methodology.md`
- `docs/testing/WEB_SERVICE_RESULT_PATH_COVERAGE.md`

### User-Doku
- `docs/user/README.md`
- `docs/user/getting-started.md`
- `docs/user/configuration-env.md`
- `docs/user/api-usage.md`
- `docs/user/troubleshooting.md`
- `docs/user/operations-runbooks.md`
- `docs/user/explainability-v2-integrator-guide.md`

## Offensichtliche Lücken (nur Identifikation)
- Kein dedizierter End-to-End-Flow-Deep-Dive für `address_intel` (Pipeline/Fehlerpfade/Source-Mix) als eigenständiges Doku-Artefakt.
- Mehrere Kernmodule ohne Modul-Docstring (`src/api/web_service.py` inkl. Legacy-Wrapper `src/web_service.py`, `address_intel.py`, `personalized_scoring.py`, `suitability_light.py`, `legacy_consumer_fingerprint.py`).
- Mapping-/Transform-Regeln sind intern gut dokumentiert, aber ohne kompakte user-nahe Einordnung.

## Nächste Schritte
- Gap-Priorisierung und Umsetzungsreihenfolge in #265 festhalten.
- Auf Basis der priorisierten Gaps fehlende Inhalte in #266 ergänzen.
