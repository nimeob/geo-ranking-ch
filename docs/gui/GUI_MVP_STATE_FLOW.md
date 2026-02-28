# BL-20.6 — GUI-MVP (Adresse + Kartenklick + Result-Panel)

## Zielbild

Die GUI-MVP unter `GET /gui` bildet jetzt den vollständigen MVP-Flow für BL-20.6 ab:

> Source-Stand seit BL-334.3: kanonisch `src/ui/gui_mvp.py` (Legacy-Wrapper `src/gui_mvp.py` bleibt kompatibel).

- Kernnavigation (`Input`, `Karte`, `Result-Panel`)
- API-first Adresseingabe via `POST /analyze`
- Kartenklick-Flow via `POST /analyze` mit `coordinates.lat/lon` + `snap_mode=ch_bounds`
- reproduzierbarer UI-State-Flow: `idle -> loading -> success|error`
- sichtbare Kernfaktoren (Top-Faktoren aus Explainability) und rohe JSON-Antwort

## Struktur

1. **Input-Panel**
   - Adresse, Intelligence-Mode, optionaler API-Token
   - Submit triggert deterministisch eine Analyze-Anfrage
2. **Kartenpanel**
   - klickbare CH-Bounds-Fläche (WGS84-Bounds als expliziter Rahmen)
   - Klick setzt Marker und startet unmittelbar dieselbe Analyze-Pipeline über Koordinateninput
   - Keyboard-Fallback (`Enter`/`Space`) triggert Center-Analyse für Accessibility
3. **Result-Panel**
   - Status-Pill pro State
   - Request-ID + Input-Metadaten
   - Fehlerbox für API-/Netzwerkfehler
   - Kernfaktoren-Liste (`top 4` nach |contribution|)
   - Roh-JSON zur transparenten MVP-Diagnose

## State-Flow (technisch)

Frontend-State (clientseitig):

- `phase`: `idle | loading | success | error`
- `lastRequestId`: korrelierbare Request-ID aus API-Response
- `lastPayload`: letzte JSON-Antwort (oder Fehlerobjekt)
- `lastError`: menschenlesbare Fehlermeldung
- `lastInput`: letzter Input-Kontext (Adresse oder Kartenpunkt)
- `coreFactors`: extrahierte Top-Faktoren aus Explainability

Transitions:

- `idle -> loading` beim Submit oder Kartenklick
- `loading -> success` bei `HTTP 2xx` + `ok=true`
- `loading -> error` bei API-Fehler, Auth-Fehler oder Netzwerkfehler
- `error -> loading` beim nächsten Submit/Kartenklick (clean retry)

## Manuelle E2E-Prüfung (BL-20.6.b)

Durchgeführt am **2026-02-28** (lokal):

1. `python3 -m src.web_service` gestartet
2. `GET /gui` geöffnet
3. Kartenklick auf Surface ausgelöst
4. Verifiziert:
   - Marker wird gesetzt
   - Request geht über `coordinates.lat/lon`
   - Status wechselt `loading -> success`
   - Result-Panel zeigt Request-ID + Kernfaktoren + JSON

Hinweis: Die Regression für ausgelieferte GUI-Marker läuft zusätzlich über `tests/test_web_service_gui_mvp.py`.

## Forward-Compatibility (BL-30)

Die GUI bleibt bewusst **API-first**: keine UI-exklusive Fachlogik, alle fachlichen Ergebnisse kommen aus `POST /analyze`. Der Kartenklick nutzt denselben Backend-Contract wie zukünftige Mobile-/HTML5-Clients (nur anderer Input-Kanal), wodurch BL-30.4/30.6 ohne Rewrite anschließen kann. Die Kernfaktoren-Darstellung wertet Explainability additiv aus mehreren möglichen Pfaden aus, sodass zukünftige Schema-Erweiterungen die bestehende UI nicht brechen.
