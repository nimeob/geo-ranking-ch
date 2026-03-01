# BL-30.5.wp2.f1 — OSM-Tile-/ODbL-Compliance-Entscheid (v1)

Stand: 2026-03-01  
Bezug: #498 (Parent #110, Epic #128, Vorarbeit #495)

## Kontext

BL-30.5 hat mit #495 die Daten-/Lizenzmatrix v1 erstellt, aber für den produktiven Kartenbetrieb fehlte ein verbindlicher Betriebsentscheid zu:

- OSM-Tile-Bezug (public vs. produktivfähig)
- Last-/Caching-Grenzen
- ODbL-Weitergabe- und Share-Alike-Triggern
- Mindestattribution in UI/API/Export

Dieses Dokument schließt die offene Compliance-Lücke aus #495.

## 1) Verbindliche Tile-Betriebsstrategie (Decision v1)

### 1.1 Umgebungsregel

| Umgebung | Tile-Quelle | Erlaubnis | Verbindliche Grenzen |
|---|---|---|---|
| `dev` / lokale Entwicklung | `https://tile.openstreetmap.org/{z}/{x}/{y}.png` | **erlaubt** | Nur Entwicklungs-/Smoke-Use; max. `1 req/s` pro Client, kein Bulk-Prefetch |
| `staging` | bevorzugt produktionsnahe Quelle | **erlaubt** | Last-/Caching-Policy wie prod erzwingen |
| `prod` | **kein direkter Public-OSM-Tile-Endpunkt** | **verboten** | Betrieb nur über professionellen Providervertrag oder self-hosted Tile-Stack mit dokumentierten Betriebsgrenzen |

### 1.2 Produktionspfad (v1)

Für den produktiven Betrieb gilt als **verbindlicher Zielpfad**:

1. Primär: professioneller OSM-kompatibler Tile-Provider mit SLA/Usage-Vertrag.  
2. Sekundär (Fallback): self-hosted Tile-Stack, wenn Monitoring, Kapazitäts- und Update-Prozess nachweisbar sind.  
3. Public OSM-Tiles bleiben auf dev/test begrenzt und sind in prod ausdrücklich nicht zulässig.

## 2) Last- und Caching-Regeln (Mindeststandard)

### 2.1 Lastgrenzen (prod)

- Durchschnittslast Zielbereich: bis `5 req/s` pro Service-Instanz (steady state)
- Kurzzeit-Burst: bis `20 req/s` für höchstens `30s`
- Bei Überschreitung: degradierten Kartenmodus aktivieren (kein harter API-Abbruch), Ursache in Telemetrie markieren

### 2.2 Caching-Regeln

- Server-/Edge-Cache für Tiles: Ziel-TTL `>= 24h`
- Browser-Cache: Ziel-TTL `>= 1h` (bei interaktiven Sessions)
- Keine aggressive Vorab-Kachelung ganzer Regionen (kein flächiges Prefetching)
- Fehlercache bei Tile-Fehlern: kurzfristige Retry-Dämpfung (Backoff), um Endpoint-Storms zu verhindern

## 3) ODbL-Weitergabemodell (Produced Work vs. Share-Alike)

### 3.1 Produced Work (normaler UI/API-Ergebnisbetrieb)

Kartenrendering, Score-/Eignungsausgaben und Explainability-Resultate gelten im Standardfall als **Produced Work**.  
Pflicht: korrekte Attribution + nachvollziehbare Quellen-/Zeitstandsangaben.

### 3.2 Share-Alike-Trigger (kritische Fälle)

Ein potenzieller ODbL-Share-Alike-Fall ist anzunehmen, wenn wir OSM-basierte Datensätze in reproduzierbarer, extrahierbarer Form weitergeben, z. B.:

- Export eines strukturierten, längerfristig wiederverwendbaren Feature-/Segment-Datensatzes mit OSM-Ableitungen
- API-Ausgabe, die OSM-Daten in quasi-Datenbankform rekonstruktionsfähig macht

In diesen Fällen ist vor produktiver Freigabe ein expliziter Legal-/Policy-Check erforderlich und der Exportpfad bleibt bis zur Entscheidung blockiert.

## 4) Attribution-Mindestanforderungen

### 4.1 UI

- Sichtbarer Quellenhinweis im Karten-/Ergebnisbereich (inkl. OSM-Nennung bei OSM-Nutzung)
- Link auf Quellen-/Lizenzhinweis aus der Produktoberfläche erreichbar

### 4.2 API

- Antwort enthält pro Kartenmodul nachvollziehbare Quellenmetadaten (`source`, `as_of`, `license_class`)
- Bei OSM-Bezug muss ODbL-/Attribution-Hinweis maschinenlesbar transportiert werden

### 4.3 Export

- Jeder Export mit Karten-/Zufahrtsbezug enthält einen Quellen-/Lizenzblock
- Export ohne Attribution ist nicht releasefähig

## 5) Umsetzungsfolgen (verbindlich)

1. **Für BL-30.5.wp3 (#496) / Runtime-Projektion:**
   - Runtime muss `tile_strategy`/`license_class`/`attribution` konsistent in Source-Metadaten führen.
   - Degraded-State bei Tile-Limit-/Source-Problemen bleibt explizit sichtbar (kein stilles Failover).
2. **Für Deployment-Doku und Betrieb:**
   - [`docs/DEPLOYMENT_AWS.md`](../DEPLOYMENT_AWS.md) führt verbindliche Runtime-Regeln für Tile-Provider, Caching und Public-Tile-Verbot in prod.
   - Betriebschecks müssen dokumentieren, ob prod gegen erlaubte Tile-Quelle läuft.
3. **Für BL-30.5-Folgearbeit:**
   - Neue Map-/Export-Features dürfen nur mit referenzierter Compliance-Policy aus diesem Dokument freigegeben werden.

## 6) Definition-of-Done-Check (#498)

- [x] Verbindliche Tile-Betriebsstrategie inkl. Last-/Caching-Grenzen dokumentiert.
- [x] ODbL-Weitergabemodell inkl. Share-Alike-Trigger klar beschrieben.
- [x] Mindestanforderungen an Attribution in UI/API/Export festgelegt.
- [x] Umsetzungsfolgen für #496 und Deployment-Doku referenziert.
- [x] Backlog-/Test-Sync für #498 vorbereitet.
