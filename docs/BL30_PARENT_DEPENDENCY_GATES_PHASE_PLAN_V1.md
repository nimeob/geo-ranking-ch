> **Diese Datei wurde konsolidiert.** Aktuelle kanonische Version: [BACKLOG.md](BACKLOG.md)

---

# BL-30.parent.wp1 — Dependency-Gates + Reihenfolgeplan v1 (Issue #509)

## Zweck
Diese v1-Doku definiert die verbindlichen Eintrittsbedingungen und die oldest-first Reihenfolge für den verbleibenden BL-30.2-Pfad (Shop/Payment/Entitlements), damit die Umsetzung additiv auf dem bestehenden BL-20/BL-30.1 Unterbau bleibt.

## Gate-Matrix (GO / HOLD / BLOCKED)

| Gate | Referenz | Erwartung für GO | HOLD/BLOCKED-Kriterium | Aktueller Stand (2026-03-01) |
| --- | --- | --- | --- | --- |
| Forward-Compatibility-Guardrails | #6 | API-first Contract bleibt additiv (kein Breaking Rewrite), bestehende Antwortstruktur stabil | Breaking Contract-Änderungen oder Rebuild-Pfad erforderlich | **GO** |
| Capability-/Packaging-Bridge | #127 | Entitlement-/Capability-Kopplung für UI/API ist als Brücke definiert und referenzierbar | Brücken-Semantik unklar oder nicht nachweisbar | **GO** |
| GTM-Entscheid Sprint | #457 | GTM-Validierung freigegeben; monetarisierungsseitige Priorisierung ist entschieden | #457 offen/blocked oder ohne klare Entscheidung für BL-30.2 | **BLOCKED** |

## Entscheidungslogik
1. **Wenn ein Gate auf BLOCKED steht:** keine Implementierung auf BL-30.2-Leaves starten.
2. **Wenn alle Gates GO sind:** Umsetzung strict oldest-first nach Leaf-Reihenfolge.
3. **Bei HOLD:** nur vorbereitende Doku-/Planungsarbeiten ohne Runtime-/Contract-Eingriff.

## Reihenfolge-/Phasenplan (BL-30.2)

### Phase 0 — Gate-Check (pro Slot)
- Prüfen, ob #457 auf GO steht.
- Prüfen, ob #6/#127 weiterhin additiv erfüllt sind.

### Phase 1 — Leaf #465 (oldest-first)
- Entitlement-Contract v1 und Gate-Semantik konsolidieren.
- Keine Umsetzung von Checkout-Lifecycle-Details vor Abschluss von #465.

### Phase 2 — Leaf #466
- Checkout-/Lifecycle-Contract und idempotenter Entitlement-Sync.
- Nur nach abgeschlossenem #465 starten.

## Operative Regel
- Für BL-30.2 gilt bis zur Entblockung durch #457: **Status BLOCKED**.
- Nach Entblockung gilt zwingend: **#465 -> #466** (kein Überspringen, keine Parallelisierung).

## Nachweis / Referenzen
- Parent: #128
- BL-30.2 Parent: #106
- BL-30.2 Leaves: #465, #466
- GTM-Gate: #457
- Guardrails/Bridge: #6, #127
