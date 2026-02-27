# BL-20.6.a — GUI-MVP Grundlayout + State-Flow

## Zielbild

Der aktuelle GUI-Shell liefert einen stabilen Einstieg für die Produktoberfläche unter `GET /gui`:

- klare Kernnavigation (`Input`, `Map-Platzhalter`, `Result-Panel`)
- API-first Adresseingabe via `POST /analyze`
- reproduzierbarer UI-State-Flow: `idle -> loading -> success|error`
- sichtbare Basis-UX für Loading-/Error-Fälle inkl. Request-ID-Anzeige

## Struktur

1. **Input-Panel**
   - Adresse, Intelligence-Mode, optionaler API-Token
   - Submit triggert deterministisch eine Analyze-Anfrage
2. **Map-Platzhalter**
   - reservierter UI-Bereich für den Kartenklick-Flow aus BL-20.6.b
3. **Result-Panel**
   - Status-Pill pro State
   - Fehlerbox für API-/Netzwerkfehler
   - Roh-JSON zur transparenten MVP-Diagnose

## State-Flow (technisch)

Frontend-State (clientseitig) hält vier Felder:

- `phase`: `idle | loading | success | error`
- `lastRequestId`: korrelierbare Request-ID aus API-Response
- `lastPayload`: letzte JSON-Antwort (oder Fehlerobjekt)
- `lastError`: menschenlesbare Fehlermeldung

Transitions:

- `idle -> loading` beim Submit
- `loading -> success` bei `HTTP 2xx` + `ok=true`
- `loading -> error` bei API-Fehler, Auth-Fehler oder Netzwerkfehler
- `error -> loading` beim nächsten Submit (clean retry)

## Forward-Compatibility (BL-30)

Der Shell bleibt bewusst **API-first** und modelliert keine UI-exklusive Businesslogik; alle fachlichen Ergebnisse kommen aus `POST /analyze`. Dadurch können spätere HTML5-/Mobile-Ausbaupfade (BL-30.4/30.6) additive Felder einführen, ohne den bestehenden State-Flow zu brechen. Der Map-Bereich ist bereits als eigener Slot vorgesehen, sodass Karteninteraktion und Deep-Mode-fähige Erweiterungen modular ergänzt werden können.
