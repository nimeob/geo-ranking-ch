# Netzwerk- und Ingress-Zielbild (`dev`) — BL-05

Stand: 2026-02-25

## Entscheidungs-Übersicht

| Thema | Entscheidung | Begründung |
|---|---|---|
| VPC-Topologie | **Zielbild:** 2 Public + 2 Private Subnets in dedizierter App-VPC; ECS Tasks in Private Subnets (ohne Public IP), Ingress nur via ALB. | Reduziert direkte Angriffsfläche und trennt Ingress/Workload sauber.
| Ingress-Schicht | **Für MVP ausreichend:** ALB direkt vor dem ECS-Service. **API Gateway aktuell nicht erforderlich.** | `/analyze` ist ein einzelner HTTP-Service; ALB deckt Routing + Health Checks + TLS-Termination ab, weniger Komplexität/Kosten.
| Domain/Route53 | **dev:** keine öffentliche Custom-Domain als Pflicht. **staging/prod:** Route53 + ACM + Alias auf ALB verbindlich. | Dev soll schnell und risikoarm bleiben; produktive Endpunkte brauchen stabile DNS-/Zertifikatsführung.

---

## Verifizierter Ist-Stand (read-only)

- ECS Service `swisstopo-dev-api` läuft in VPC `vpc-05377592c517f09f4` (Default VPC).
- Service-Subnets: `subnet-03651caf25115a6c1`, `subnet-00901e503e078e7c9`, `subnet-07cfbfe0d181ed329`.
- Alle drei Subnets haben `MapPublicIpOnLaunch=true`.
- ECS Network Config setzt `assignPublicIp=ENABLED`.
- Security Group `sg-092e0616ffb0663c3` erlaubt Ingress `tcp/8080` aus `0.0.0.0/0`.
- Aktuell ist **kein ALB** und **kein API Gateway** vor dem Service konfiguriert.

Das ist für frühen MVP-Betrieb funktional, aber nicht das gewünschte Zielbild für längeren Betrieb.

---

## Zielbild (beschlossen)

### 1) VPC-Topologie

1. Dedizierte VPC für `swisstopo`-Workloads (nicht Default-VPC)
2. Mindestens 2 AZs
3. Subnets:
   - Public Subnets: nur ALB + NAT-Gateway
   - Private Subnets: ECS Tasks
4. Security Groups:
   - `alb-sg`: Ingress 443 (und optional 80→443 Redirect) aus Internet
   - `ecs-service-sg`: Ingress 8080 **nur** von `alb-sg`
5. ECS Service mit `assignPublicIp=DISABLED`

### 2) API Gateway vs. ALB

**Entscheid:** ALB direkt genügt für den aktuellen Scope.

API Gateway wird erst eingeführt, wenn mindestens einer der Punkte zutrifft:
- mehrere APIs/Backends benötigen API-Produktisierung,
- Usage Plans/API Keys als Pflicht-Control gebraucht werden,
- spezifische Gateway-Features (Request-Transformation, per-Consumer Quotas, WAF-Integration auf API-Ebene) benötigt werden.

### 3) Domain/Route53

- `dev`: kein Muss für öffentliche Domain; technischer Endpoint (ALB-DNS) ist zulässig.
- `staging`/`prod`: eigene Hostnames über Route53 + ACM verpflichtend (z. B. `api.staging.<domain>`, `api.<domain>`).
- Public-Freigabe erfolgt nur mit:
  - TLS-Zertifikat (ACM),
  - dokumentierter AuthN/AuthZ-Policy (BL-07),
  - aktivem Monitoring/Alerting (BL-08).

---

## Auswirkungen auf Folgeblöcke

- **BL-06/BL-07:** Sicherheits- und Datenhaltungsentscheidungen werden auf dem ALB-direkt-Zielbild aufgesetzt.
- **BL-08:** Alarme und Health-Checks werden auf ALB/ECS-Metriken ausgerichtet.
- **BL-09:** Promotion-Strategie übernimmt dieses Zielbild für `staging`/`prod`.
