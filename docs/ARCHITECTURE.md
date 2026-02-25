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

### AWS-Naming-Konvention

AWS-Ressourcen dieses Projekts heißen intern **`swisstopo`** (z. B. `swisstopo-dev`, `swisstopo-dev-api`). Das ist so gewollt — der Repo-Name `geo-ranking-ch` und das interne AWS-Naming divergieren bewusst. Die AWS-Namen sind nicht öffentlich exponiert und müssen nicht umbenannt werden.

| Ressource | Name |
|---|---|
| S3 Bucket | `swisstopo-dev-523234426229` |
| ECS Cluster | `swisstopo-dev` |
| ECS Service | `swisstopo-dev-api` |
| ECR Repository | `523234426229.dkr.ecr.eu-central-1.amazonaws.com/swisstopo-dev-api` |
| IAM Deploy-User | `arn:aws:iam::523234426229:user/swisstopo-api-deploy` |

### Umgebungen

> **Aktueller Stand:** Es existiert ausschließlich eine **`dev`-Umgebung**. `staging` und `prod` sind noch nicht aufgebaut und nicht geplant für den aktuellen Entwicklungsstand.

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
