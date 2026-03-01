> **Diese Datei wurde konsolidiert.** Aktuelle kanonische Version: [ARCHITECTURE.md](ARCHITECTURE.md)

---

# BL-30.parent.wp2 — Rebuild-vs-Ausbau-Guardrails + API-first Anschluss v1 (Issue #510)

## Zweck
Diese Doku konsolidiert die verbindlichen Guardrails gegen "Rebuild statt Ausbau" für BL-30 und macht den API-first-/Contract-Stabilitätsanschluss für den verbleibenden BL-30.2-Pfad (#465/#466) testbar.

## Rebuild-vs-Ausbau Guardrails je BL-30-Teilstream

| Teilstream | Ausbaupfad (erlaubt) | Rebuild-Pfad (verboten) | Verbindlicher Guardrail |
| --- | --- | --- | --- |
| BL-30.1 Pricing/Packaging | Additive Tier-/Limit-Metadaten auf bestehendem Analyze-Contract | Neues proprietäres Antwortschema nur für Pricing | Bestehende Analyze-Antwort bleibt kanonisch; Pricing nur über additive Felder + Doku-Referenzen |
| BL-30.2 Shop/Payment/Entitlements | Entitlement-Gating als additive Capability-/Status-Projektion | Checkout ersetzt Kernfluss oder spaltet eigene API-Welt ab | Checkout ist nachgelagerter Capability-Provider; Analysefluss bleibt führend |
| BL-30.3 Deep-Mode | Optionales Add-on über vorhandene `/analyze`-Orchestrierung | Separater Deep-Mode-Service als Pflichtpfad | Deep-Mode bleibt optional (`requested/allowed`), deterministischer Fallback auf Standard |
| BL-30.4 HTML5-UI | UI-Schicht nutzt bestehende API-Contracts | UI-getriebene Sonder-API ohne Contract-Sync | UI darf keine exklusiven API-Felder erzwingen; Contract-v1 ist Source of Truth |
| BL-30.5 Map-Intelligence | Kartenfluss mappt additiv in bestehende Ergebnisstruktur | Zweites, inkompatibles Karten-Response-Modell | `result.data.modules.*` bleibt additive Erweiterungszone |
| BL-30.6 Mobile Geolocation | Mobile Status/Felder als optionale Erweiterung | Mobiler Sonder-Endpoint mit abweichender Semantik | Mobile integriert in bestehenden Analyze-/Status-Contract, kein Branching-Contract |

## API-first Anschluss für BL-30.2 (testbar, verpflichtend)

### Pflichtmarker (normativ)
1. **BL30_API_FIRST_NO_BREAKING_CHANGES**  
   BL-30.2-Leaves dürfen keine bestehenden Pflichtfelder entfernen/umbenennen; nur additive Felder erlaubt.
2. **BL30_ENTITLEMENT_SCHEMA_ADDITIVE_ONLY**  
   Entitlement-/Capability-Zustände müssen unter bestehenden Status/Capabilities-Strukturen projiziert werden.
3. **BL30_CHECKOUT_IDEMPOTENCY_REQUIRED**  
   Checkout-/Lifecycle-Sequenzen müssen idempotent sein und dürfen Analyze-Aufrufe nicht in einen nicht-wiederholbaren Zustand überführen.
4. **BL30_RUNTIME_FALLBACK_TO_STANDARD**  
   Bei Entitlement-/Payment-Störungen bleibt Standard-Analyze verfügbar (kein globaler Hard-Fail).

### Verifikationspfad vor Merge von #465/#466
- Contract-Regression: `tests/test_api_contract_v1.py`
- Kompatibilitäts-Regression: `tests/test_contract_compatibility_regression.py`
- BL-30 Parent Guardrail-Regression: `tests/test_bl30_parent_rebuild_vs_ausbau_guardrails_docs.py`

## Operative Merge-Policy für BL-30.2
- Reihenfolge bleibt verbindlich: **#465 -> #466** (oldest-first, nach Entblockung durch #457).
- Jeder BL-30.2-PR braucht einen kurzen "Guardrail-Check" im PR-Body mit Verweis auf alle vier Pflichtmarker.
- Wenn ein Pflichtmarker nicht erfüllt ist, wird der PR nicht gemerged (Status: HOLD/BLOCKED).

## Referenzen
- Parent-Issue: #128
- Vorarbeit Gates/Phasen: `docs/BL30_PARENT_DEPENDENCY_GATES_PHASE_PLAN_V1.md` (#509)
- BL-30.2-Leaves: #465, #466
- GTM-Gate: #457
- Forward-Compatibility-/Bridge-Guardrails: #6, #127
