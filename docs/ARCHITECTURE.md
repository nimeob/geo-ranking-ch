# Architektur — geo-ranking-ch

> **Status:** Frühe Planungsphase. Dieses Dokument beschreibt die angestrebte Zielarchitektur und wird laufend aktualisiert, sobald Implementierungsentscheidungen getroffen werden.

---

## Überblick

`geo-ranking-ch` verarbeitet Schweizer Geodaten und berechnet Rankings auf Basis konfigurierbarer Kriterien (z. B. Bevölkerungsdichte, Infrastruktur, Erreichbarkeit).

```
┌──────────────────────────────────────────────────────────────┐
│                        geo-ranking-ch                        │
│                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────────────┐ │
│  │  Datenquellen│───▶│  Processing │───▶│  Ranking/Output  │ │
│  │  (Geodaten) │    │  (ETL/Score)│    │  (API/Export)    │ │
│  └─────────────┘    └─────────────┘    └──────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

## Komponenten

> **Hinweis:** Alle Komponenten sind **zu verifizieren / noch nicht implementiert** — sofern nicht anders markiert.

### 1. Datenquellen

| Quelle | Typ | Status |
|---|---|---|
| swisstopo / geo.admin.ch | REST API / WFS | zu verifizieren |
| Bundesamt für Statistik (BFS) | Datei-Download (CSV/JSON) | zu verifizieren |
| OpenStreetMap | Overpass API / PBF | zu verifizieren |

### 2. Verarbeitungs-Pipeline

- **Ingest:** Laden von Rohdaten aus öffentlichen Quellen
- **Transform:** Normalisierung, Geocodierung, Feature-Extraktion
- **Score:** Berechnung des Rankings nach definierten Metriken
- **Store:** Persistierung der Ergebnisse (S3 / Datenbank — zu verifizieren)

### 3. Ausgabe / API

- Art des Outputs (REST API / statisches JSON / Dashboard): **zu verifizieren**
- Hosting-Modell: **zu verifizieren** (Lambda + API Gateway / ECS / S3 Static)

---

## AWS-Infrastruktur (Ist-Stand)

> Verifizierte Werte via `aws sts get-caller-identity` und `aws` CLI (Stand: 2026-02-25).

| Parameter | Wert |
|---|---|
| AWS Account | `523234426229` |
| Region | `eu-central-1` (Frankfurt) |
| IAM Deploy-User | `swisstopo-api-deploy` |
| Spezifische geo-ranking-ch Ressourcen | **nicht gefunden** (zu verifizieren) |

Es wurden keine dedizierten AWS-Ressourcen für `geo-ranking-ch` identifiziert. Im selben Account existieren swisstopo-Dev-Ressourcen (ECS Cluster `swisstopo-dev`, ECR `swisstopo-dev-api`, S3 `swisstopo-dev-523234426229`). Diese sind dem Schwesterprojekt zuzuordnen.

**Mögliche Szenarien (zu klären):**
1. Das Deployment ist noch nicht provisioniert (frühe Projektphase)
2. Ressourcen existieren unter einem anderen AWS-Profil / Account
3. Das Projekt teilt Infrastruktur mit swisstopo (Mono-Repo-/Multi-Service-Pattern)

Detailliertes Runbook: [`DEPLOYMENT_AWS.md`](DEPLOYMENT_AWS.md)

---

## Technologie-Stack

| Layer | Technologie | Status |
|---|---|---|
| Sprache | Python (angenommen) | zu verifizieren |
| Infrastruktur | AWS (eu-central-1) | verifiziert (Account) |
| IaC | CDK / Terraform / CloudFormation | zu verifizieren |
| CI/CD | GitHub Actions | geplant (Placeholder vorhanden) |
| Container | Docker / ECR | zu verifizieren |

---

## Datenfluss (Zielzustand)

```
Externe Quellen          AWS                        Clients
     │                    │                            │
     │  HTTP/FTP          │                            │
     ├──────────────▶ Lambda/ECS ──▶ S3/RDS ──▶ API GW ──▶ Endnutzer
     │               (Ingest+ETL)  (Storage)  (Output)
     │
  swisstopo / BFS / OSM
```

---

## Offene Entscheidungen

- [ ] Technologie-Stack final definieren (Sprache, Frameworks)
- [ ] Hosting-Modell wählen (Serverless vs. Container vs. Static)
- [ ] IaC-Tool auswählen (CDK empfohlen, konsistent mit swisstopo-Kontext)
- [ ] Datenquellen und Update-Frequenz festlegen
- [ ] Output-Format definieren (API / statisch / beide)
- [ ] Datenschutz-Assessment (öffentliche Daten vs. personenbezogen)
