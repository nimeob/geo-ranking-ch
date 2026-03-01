# Dokumentationslücken – Priorisierung & Umsetzungsplan

> Stand: 2026-02-27  
> Scope: BL-YY.2 / Issue #265  
> Grundlage: [`docs/DOCUMENTATION_COVERAGE_INVENTORY.md`](DOCUMENTATION_COVERAGE_INVENTORY.md)

## Ziel
Aus den inventarisierten Dokumentationslücken eine priorisierte, umsetzbare Reihenfolge für die inhaltliche Ergänzung (#266) ableiten.

## Priorisierte Gap-Liste

| Priorität | Gap | Zielpublikum | Betroffener Bereich | Begründung |
|---|---|---|---|---|
| Hoch | Fehlender Address-Intel-Flow-Deep-Dive (Pipeline, Fehlerpfade, Source-Mix) | intern + integrator-nah | `src/address_intel.py`, `src/api/web_service.py` (Legacy: `src/web_service.py`), API/Operations-Doku | Höchster Hebel für Onboarding, Debugging und fachlich korrekte Interpretation der Resultate |
| Mittel | Mapping-/Transform-Regeln sind intern dokumentiert, aber ohne kompakte user-nahe Einordnung | User/Integratoren | `src/mapping_transform_rules.py`, `docs/DATA_SOURCE_FIELD_MAPPING_CH.md`, `docs/user/api-usage.md` | Reduziert Fehlinterpretationen bei Datenherkunft/-normalisierung |
| Mittel | Mehrere Kernmodule ohne Modul-Docstring (Code-Navigation) | intern (Dev/Ops) | `src/api/web_service.py` (Legacy: `src/web_service.py`), `src/address_intel.py`, `src/personalized_scoring.py`, `src/suitability_light.py`, `src/legacy_consumer_fingerprint.py` | Schnell umsetzbar; verbessert Wartbarkeit und Einstieg ohne API-Verhalten zu ändern |
| Niedrig | Utility-Layer (`geo_utils`, `gwr_codes`) ohne fokussierte User-Referenz | User (fortgeschritten) | `src/geo_utils.py`, `src/gwr_codes.py`, README/User-Doku | Der Layer ist aktuell über API-/README-Pfade indirekt nutzbar; fachlich nachgelagert |

## Umsetzungsreihenfolge für #266 (verbindlich)

1. **Address-Intel-Flow-Deep-Dive ergänzen (hoch)**
   - Zielartefakt: neue interne Doku unter `docs/` mit Datenfluss, Source-Policy je Mode und Fehler-Mapping.
2. **Mapping-Regeln user-nah erklären (mittel)**
   - Zielartefakt: kompakter Ergänzungsabschnitt in User-Doku (plus Link auf technische Tiefendoku).
3. **Modul-Docstrings nachziehen (mittel)**
   - Zielartefakt: kurze, präzise Modul-Docstrings in den identifizierten Kernmodulen.
4. **Optional: Utility-Referenz ergänzen (niedrig)**
   - Nur falls Zeit im Slot verbleibt, sonst als Follow-up belassen.

## Akzeptanzkriterien für #266 (abgeleitet)
- Die priorisierten High-/Medium-Gaps sind im Repo nachweisbar geschlossen.
- Änderungen sind zwischen interner und User-Doku konsistent verlinkt.
- Neue/angepasste Doku bleibt link-valid (bestehende Doku-Regression grün).

## Follow-up-/Abhängigkeitsstatus
- #265 liefert die Priorisierungsentscheidung.
- #266 wird damit von `status:blocked` auf `status:todo` gehoben und als nächstes Child umgesetzt.
