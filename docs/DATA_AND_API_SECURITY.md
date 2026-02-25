# Datenhaltung & API-Sicherheitskonzept (`dev`) — BL-06 + BL-07

Stand: 2026-02-25

## 1) Entscheidung Datenhaltung (BL-06)

## Entscheidung

Für den aktuellen Scope wird **keine persistente Datenbank** (weder RDS noch DynamoDB) in `dev` eingeführt.

Der Service bleibt vorerst **stateless**:
- Request rein → Analyse → Response raus
- keine persistente Ablage von Nutzlasten oder Ergebnissen
- Deployments/Rollbacks ohne Datenmigrationspfad

## Begründung

- Aktueller Endpoint-Scope (`/analyze`) benötigt keine langlebige fachliche Entität.
- Frühe Persistenz erhöht Betriebsaufwand (Backups, IAM, Kosten, Migrationen) ohne direkten MVP-Nutzen.
- Stateless-Betrieb beschleunigt Iteration und reduziert Risiko in `dev`.

## Konsequenzen

- Kein historisches Query-/Result-Caching über Restarts hinweg.
- Kein Audit-Trail auf Datenbankebene.
- Performance hängt von Upstream-APIs + Laufzeit pro Request ab.

## Falls Persistenz nötig wird (vordefinierter Pfad)

**Präferenz: DynamoDB vor RDS** für den ersten Persistenzschritt.

Minimaldesign (wenn Trigger eintritt):
- Tabelle `swisstopo-dev-analysis-cache`
- Partition Key: `request_hash`
- Attribute: `created_at`, `ttl_epoch`, `response_payload`, `source_version`
- TTL aktiv (z. B. 24–72h)
- On-demand Capacity (kein Throughput-Tuning als Startblocker)

Betriebsfolgen:
- zusätzliche IAM-Rechte für Task-Role
- TTL-/Kosten-Monitoring
- definierte Invalidierungsstrategie bei Modell-/Logikwechsel

## Trigger für Einführung einer DB

DB-Einführung wird erst gestartet, wenn mindestens einer der Trigger erfüllt ist:
1. Wiederholte identische Queries erzeugen relevante Kosten/Latenz.
2. Fachlicher Bedarf an historischer Nachvollziehbarkeit entsteht.
3. Produkt-Features benötigen gespeicherten Zustand (z. B. Jobs, User-Profile, Freigabestatus).

---

## 2) API-Sicherheitskonzept für `/analyze` (BL-07)

## AuthN/AuthZ-Ansatz

### Kurzfristig (`dev`, aktueller Stand)
- Endpoint ist technisch erreichbar, aber als **nicht öffentliches Entwickler-Interface** zu behandeln.
- Zugriffe nur aus kontrolliertem Kontext (interne Nutzung / bekannte Clients).
- Keine Secrets/Tokens im Code oder in Repo-Dateien.

### Zielbild (vor öffentlicher Nutzung)
1. **Durchsetzungspunkt am Edge:** ALB + AWS WAF (siehe BL-05 Zielbild).
2. **Client-Authentisierung:** Machine-to-Machine Token (Bearer/API-Key) aus Secret Manager/SSM.
3. **Autorisierung:** Scope-basiert mindestens auf Endpoint-Ebene (`analyze:invoke`).
4. **Defense in depth:** optional zusätzlicher Token-Check in App-Schicht.

## Rate-Limit-Strategie

### Durchsetzungspunkt (beschlossen)
- **Primär:** AWS WAF Rate-based Rule vor ALB (pro IP/Label).
- **Sekundär (Fallback für frühes dev):** optionales App-seitiges Soft-Limit als Schutz vor Fehlkonfiguration/Looping-Clients.

### Startwerte (MVP-Richtwert)
- Burst tolerant, aber geschützt gegen Dauerlast:
  - pro Quell-IP: z. B. 100 Requests / 5 Minuten (WAF-Rule)
  - strenger für `/analyze` als für `/health` und `/version`

## Mindestanforderungen Secret-/Token-Handling

1. **Speicherung:** nur in AWS Secrets Manager oder SSM Parameter Store (`SecureString`).
2. **Transport:** nur TLS (HTTPS), keine Token in Query-Parametern.
3. **Nutzung:** Injection via ECS Task-Definition `secrets`, nicht als Klartext in Images.
4. **Logging:** Token niemals loggen; Header/Secrets maskieren.
5. **Rotation:** definierter Rotationszyklus und Dual-Key-Rollover (alt+neu Übergangsfenster).
6. **IAM:** Least-Privilege auf Secret-Pfade; nur Runtime-Role mit Lesezugriff.

---

## 3) Umsetzungsreihenfolge (risikoarm)

1. BL-08 Monitoring/Alerting-Basis stabilisieren (inkl. Alarmkanal).
2. Bei Ingress-Umstellung (ALB) WAF Rate-based Rule aktivieren.
3. Token-basierte AuthN für `/analyze` aktivieren (Edge + optional App-Layer).
4. Erst bei Triggern aus Abschnitt 1 Persistenz (DynamoDB-first) ergänzen.
