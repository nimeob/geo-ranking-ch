# `dev` → `staging` → `prod` Promotion-Strategie — BL-09

Stand: 2026-02-25

## 1) Zielarchitektur je Umgebung

## Grundsätze

- Gleiches Deploy-Muster in allen Umgebungen: Container in ECR, Rollout via ECS Service.
- Trennung von Konfiguration/Secrets pro Umgebung.
- Keine direkte Promotion nach `prod` ohne vorherigen `staging`-Nachweis.

## Zielbild-Matrix

| Bereich | `dev` | `staging` | `prod` |
|---|---|---|---|
| Zweck | schnelle Iteration | produktionsnahe Verifikation | Nutzer-/Business-Betrieb |
| ECS Cluster | `swisstopo-dev` (bestehend) | `swisstopo-staging` (neu) | `swisstopo-prod` (neu) |
| Ingress | Übergangsweise direkt; Ziel ALB | ALB + WAF verpflichtend | ALB + WAF verpflichtend |
| Domain | optional | `api.staging.<domain>` | `api.<domain>` |
| DNS/TLS | optional | Route53 + ACM | Route53 + ACM |
| AuthN/AuthZ `/analyze` | intern/controlled | verpflichtend | verpflichtend |
| Monitoring | Basis aktiv (BL-08) | vollständige Alarmierung | vollständige Alarmierung + On-call |
| Datenhaltung | stateless | stateless oder kontrolliert persistent | je Produktbedarf persistent + Backup-Policy |

---

## 2) Promotion-Pfad

## Release-Artefakt

Ein Release wird über **Image-Digest** (nicht nur Tag) identifiziert.

- Build in CI erzeugt Image in ECR
- Digest wird als Promotion-Referenz verwendet
- dieselbe Revision wird durch Umgebungen promoted

## Pipeline-Schritte

1. **Build + Test (`main`):** Unit-Tests, Lint, Container Build, Push nach ECR.
2. **Deploy `dev`:** automatisiert; Smoke-Test auf `/health`.
3. **Gate G1 (`dev` → `staging`):**
   - letzter `dev` Deploy grün
   - keine offenen P0-Incidents
   - manuelle Freigabe
4. **Deploy `staging`:** per `workflow_dispatch` oder Promotion-Workflow mit fixem Digest.
5. **Gate G2 (`staging` → `prod`):**
   - Smoke-Test + funktionaler Check in `staging` grün
   - Security-Gate (AuthN aktiv, Secrets gesetzt, WAF aktiv)
   - Monitoring-Gate (Alarme + Empfänger getestet)
   - manuelle Freigabe durch Owner
6. **Deploy `prod`:** kontrolliert (manual approval required).

---

## 3) Rollback- und Freigabeprozess

## Rollback (alle Umgebungen)

Primärstrategie: ECS Service auf vorherige stabile Task-Definition zurücksetzen.

```bash
aws ecs update-service \
  --region <region> \
  --cluster <cluster> \
  --service <service> \
  --task-definition <family:revision>
```

## Freigabe-Regeln

- `dev`: automatische Freigabe via CI-Erfolg.
- `staging`: manuelle Freigabe durch Maintainer.
- `prod`: Vier-Augen-Prinzip (Owner + zweiter Reviewer) und dokumentierter Change-Record.

## Abbruchkriterien während Deploy

Deploy wird abgebrochen bzw. zurückgerollt bei:
- `services-stable` timeout/failure,
- Smoke-Test-Fehler (`/health` nicht 200),
- Alarmzustand `ALARM` für Service-Ausfall oder 5xx-Rate.

---

## 4) Vorbedingungen vor erstem `staging`/`prod` Aufbau

1. BL-05 Zielbild (ALB/Route53) technisch umgesetzt.
2. BL-07 Security Controls aktiv (AuthN + Secret-Handling).
3. BL-08 End-to-End Alarmzustellung bestätigt (mind. ein Subscriber bestätigt).
4. IaC-Erweiterung für `staging`/`prod` im Repo versioniert.

Bis diese Punkte erfüllt sind, bleibt die Strategie **vorbereitet**, aber nicht produktiv aktiviert.
