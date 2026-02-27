# TLS Certificate Migration Runbook (Dev Self-Signed → Official Certificate)

## 1) Ziel und Scope

Dieses Runbook beschreibt den Übergang von **self-signed TLS in Dev** zu **offiziellen Zertifikaten** (ACM/Let's Encrypt/Corporate CA) für produktionsnahe Umgebungen.

**Nicht-Ziel:** mTLS zwischen internen AWS-Services in diesem Schritt.

---

## 2) Klare Trennung: Dev vs. Prod

### Dev (self-signed)

- Zweck: lokale/entwicklungsnahe Integrations- und Client-Trust-Tests.
- Zertifikatspfad: lokal erzeugt (z. B. via `scripts/generate_dev_tls_cert.sh`).
- Trust im Smoke-Test: explizit über `DEV_TLS_CA_CERT` (`curl --cacert`).
- Keine Verwendung für öffentliche Endpunkte.

### Prod/Stage (official cert)

- TLS-Termination an der Edge (bevorzugt ALB/Ingress).
- Zertifikat aus vertrauenswürdiger Quelle:
  - **AWS ACM** (bevorzugt für AWS-ALB)
  - **Let's Encrypt** (falls außerhalb ACM betrieben)
  - **Corporate CA** (Enterprise-Vorgabe)
- Keine self-signed Zertifikate an extern exponierten Endpunkten.

---

## 3) TLS Baseline (verbindlich)

- **Mindestversion:** TLS 1.2
- **Bevorzugt:** TLS 1.3 (wenn Plattform/Client-Matrix kompatibel)
- Unsichere Legacy-Protokolle deaktivieren (TLS 1.0/1.1).
- HSTS für öffentliche HTTPS-Endpunkte aktivieren, sobald Domain + Redirect-Strategie stabil sind.
  - Start konservativ (z. B. niedrige `max-age`) und nach Verifikation erhöhen.

---

## 4) Empfohlener Zielpfad in AWS (ALB + ACM)

1. Öffentliches Zertifikat in ACM bereitstellen (DNS-Validierung bevorzugt).
2. HTTPS-Listener (443) am ALB mit ACM-Zertifikat konfigurieren.
3. HTTP-Listener (80) auf 301/308 Redirect nach HTTPS setzen.
4. Zielgruppe/Health Checks auf TLS-Edge-kompatiblen Pfad prüfen (`/health`).
5. Deployment-/Smoke-Run gegen `https://...` durchführen.

> Anwendung selbst kann intern HTTP sprechen, wenn TLS sauber am Edge terminiert wird.

---

## 5) Rotation / Renewal (Betrieb)

### ACM-basiert

- Managed Renewal beobachten (Ablauf-Alarme/Events aktivieren).
- Vor Ablauf Funktionscheck auf Zertifikatskette + Domainabdeckung.
- Nach Rotation kurzer API-Smoke (`/health`, `/analyze`) + Header-/Auth-Check.

### Nicht-ACM (z. B. Let's Encrypt/Corporate CA)

- Automatisierte Erneuerung + Deployment-Hook verpflichtend.
- Zertifikats- und Key-Dateien niemals im Repo speichern.
- Erneuerungsfenster + owner on-call im Kalender/Runbook hinterlegen.

---

## 6) Rollback-Plan (wenn Zertifikatswechsel fehlschlägt)

1. Sofort auf letzte bekannte funktionierende Zertifikatskonfiguration zurückschalten.
2. Redirect-Regeln unverändert lassen, um HTTP/HTTPS-Split-Probleme zu vermeiden.
3. Verifizieren:
   - TLS-Handshake erfolgreich
   - `/health` = 200
   - `/analyze` mit Token-Auth = 200
4. Incident notieren (Ursache, Impact, Korrekturmaßnahme, Preventive Action).

---

## 7) Incident-Hinweise (Kurzdiagnose)

- **Handshake-Fehler:** Zertifikatskette, SAN/CN, Ablaufdatum prüfen.
- **Nur einzelne Clients betroffen:** TLS-Version/Cipher-Kompatibilität gegen Client-Matrix prüfen.
- **Redirect-Loops:** Listener-/Proxy-Regeln (`X-Forwarded-Proto`) kontrollieren.
- **401/403 nach TLS-Änderung:** Auth-Header-Weitergabe am Edge prüfen.

---

## 8) Verknüpfte Artefakte

- Dev-TLS-Helfer: `scripts/generate_dev_tls_cert.sh`
- Dev-HTTPS-Smoke: `scripts/run_remote_api_smoketest.sh` (`DEV_TLS_CA_CERT`)
- Dev-Runbook: `docs/testing/dev-self-signed-tls-smoke.md`
- Deployment-Kontext: `docs/DEPLOYMENT_AWS.md`
