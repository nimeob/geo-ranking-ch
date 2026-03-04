## Zusammenfassung

<!-- Was wurde geändert und warum? -->

## Tests / Verifikation

<!-- Konkrete Kommandos + Ergebnis eintragen -->

## Boundary-Check (verbindlich)

- [ ] Ich habe `docs/ARCHITECTURE.md` (Section „API/UI Boundary Contract (v1)“) geprüft.
- [ ] Keine neuen Cross-Layer-Imports (`src/api/*` importiert kein `src/ui/*`, `src/ui/*` importiert kein `src/api/*`).
- [ ] Neue/geänderte Routen folgen der Ownership-Matrix (API: data/service, UI: front-facing UX).
- [ ] Falls eine Ausnahme nötig war: Follow-up-Issue inkl. Migrations-/Sunset-Plan ist verlinkt.

## Checklist

- [ ] Doku aktualisiert (falls Verhalten/Contract geändert)
- [ ] Tests ergänzt/aktualisiert
- [ ] Lokale Tests ausgeführt
