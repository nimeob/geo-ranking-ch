# Entitlements & Capabilities v1 — Modell, Evaluation, Enforcement

Stand: 2026-03-01  
Issue: #627 (Parent: #577)

> **Ziel:** Ein v1-Modell, das Entitlements/Capabilities so definiert, dass spätere Implementierung (API-Enforcement, Billing-Sync, UI-Gating, Async-Jobs) **parallelisierbar** ist.

## 0) Kanonische Referenzen (nicht duplizieren)

- Gate-Katalog + API-Felder + Billing-Lifecycle (kanonisch): [`docs/api/entitlements-v1.md`](api/entitlements-v1.md)
- Entitlement-/Billing-Lifecycle (Details): [`docs/api/entitlement-billing-lifecycle-v1.md`](api/entitlement-billing-lifecycle-v1.md)
- Pricing-/Tier-Matrix (Inputs): [`docs/PRICING_TIER_LIMIT_MATRIX_V1.md`](PRICING_TIER_LIMIT_MATRIX_V1.md)

Dieses Dokument ergänzt bewusst:
- klare **Begriffsabgrenzung** (entitlement vs capability vs limit vs feature-flag)
- ein **Datenmodell-Sketch** (Scopes + Keys + Values)
- eine **Evaluationslogik** (Request → effektive Gates → Entscheidung)
- konkrete **Capability-Beispiele** inkl. Semantik

## 1) Begriffe (v1)

### Entitlement
Ein **Entitlement** ist ein *maschinell auswertbarer* Wert, der aus Plan/Billing/Overrides abgeleitet wird und eine **Norm** für die Laufzeit setzt.

- Beispiele: `entitlement.requests.monthly=5000`, `entitlement.requests.rate_limit=60/min`, `entitlement.analyze.max_runtime_seconds=30`.
- Typen: integer/string/enum/bool (Implementationsdetails: JSON vs. typed columns).

### Capability
Eine **Capability** ist eine *produktive Fähigkeit*, die im Runtime-Pfad als **allow/deny** (oder als Profil-Level) gilt.

- Beispiele: `capability.analyze.async=true`, `capability.exports.enabled=false`, `capability.trace.debug=yes|optional|no`.

> Vereinfachungsregel v1: Capabilities können als Entitlement-Keys modelliert werden (`capability.*`), solange Semantik klar bleibt.

### Limit
Ein **Limit** ist ein Entitlement, das quantitativ wirkt (Quota/Rate/Budget).

- Beispiele: Monatsquota, Rate-Limit, Token-/Zeitbudget.

### Feature-Flag
Ein **Feature-Flag** ist ein *Engineering-Enablement* (rollout/experiment) und **nicht** per se ein kundenseitiges Recht.

- Flags dürfen Entitlements *nicht* ersetzen.
- Reihenfolge v1:
  1) Feature-Flag entscheidet „ist Feature in dieser Deployment-Umgebung aktiv?“
  2) Entitlement/Capability entscheidet „darf dieser Tenant es nutzen?“

## 2) Scopes (Org/User/API-Key) + Datenmodell-Sketch

### Scopes
- **Org-scope (Default):** Monetization-/Billing-getrieben, Primärtenant.
- **User-scope (optional):** Seats/Benutzerlimits (z. B. UI-Access, Export-Rollen).
- **API-Key-scope (optional):** feinere Limits/Policies pro Key (z. B. restriktiveres Rate-Limit als Org-Default).

### Logisches Datenmodell (v1 Zielbild)
Siehe auch: [`docs/DATA_MODEL_v1.md`](DATA_MODEL_v1.md).

**Tabelle `entitlements` (logisch):**
- `org_id` (Tenant-Anker)
- `subscription_id` (Quelle Plan/Lifecycle)
- `key` (z. B. `entitlement.requests.monthly`, `capability.trace.debug`)
- `value` (string/number/json)
- `source` (`plan|override|migration|support`)
- `effective_from`, `effective_to` (optional)

**Erweiterung für Scopes (v1+):**
- entweder zusätzliche Spalten `scope_type`, `scope_id`
- oder separate Tabellen (`user_entitlements`, `api_key_entitlements`)

> No-regrets Default: zuerst Org-scope sauber; user/api-key-scope nur einführen, wenn ein konkretes Feature es zwingend braucht.

## 3) Evaluation: Request → effektive Gates → Entscheidung

### Inputs (v1)
- Billing-/Plan-Zustand (Plan-Tier, Lifecycle State)
- Org-spezifische Overrides (Support/Trial/Grace-Policy)
- Usage/Metering (Remaining Quota)
- Request-Kontext (Route, Actor: user/api_key/system, async vs sync)

### Prioritätsregel (normativ, fail-safe)
1. **Plan-Baseline**
2. **Org-Overrides** (z. B. Support-Override)
3. **Lifecycle-Constraints** (Grace/Past-Due etc.)

**Konfliktregel:** *engste Einschränkung gewinnt* (fail-safe).

### Pseudocode (v1)

```python
from dataclasses import dataclass

@dataclass
class GateDecision:
    allowed: bool
    reason: str | None = None
    effective: dict[str, object] | None = None


def evaluate_entitlements(request_ctx) -> dict[str, object]:
    # 1) Load baseline plan entitlements (static catalog)
    baseline = load_plan_entitlements(request_ctx.plan_tier)

    # 2) Apply org overrides (support/trial)
    overrides = load_org_overrides(request_ctx.org_id)
    effective = merge_entitlements(baseline, overrides)

    # 3) Apply lifecycle constraints (grace/past_due/canceled)
    constraints = lifecycle_constraints(request_ctx.billing_state)
    effective = apply_constraints_fail_safe(effective, constraints)

    # 4) Derive usage-backed fields (remaining quota)
    usage = read_usage_rollups(
        org_id=request_ctx.org_id,
        window="monthly",
        metric_key="requests.analyze",
    )
    effective["entitlement.requests.monthly_remaining"] = max(
        0,
        int(effective.get("entitlement.requests.monthly", 0)) - int(usage.get("count", 0)),
    )

    return effective


def authorize_request(request_ctx) -> GateDecision:
    ent = evaluate_entitlements(request_ctx)

    # Example: async analyze gate
    if request_ctx.is_async_requested:
        if not bool(ent.get("capability.analyze.async", False)):
            return GateDecision(False, reason="not_entitled", effective=ent)

    # Example: monthly quota
    if int(ent.get("entitlement.requests.monthly_remaining", 0)) <= 0:
        return GateDecision(False, reason="quota_exhausted", effective=ent)

    return GateDecision(True, effective=ent)
```

## 4) Enforcement-Orte (API / Worker / UI)

### API Layer (Source of Truth)
- **Muss** alle sicherheits-/kostenrelevanten Gates serverseitig durchsetzen.
- Liefert additiv `result.status.entitlements.*` und `result.status.capabilities.*` (siehe `docs/api/entitlements-v1.md`).

**Konkreter Bestand (heute):** Deep-Mode Gate/Evaluation ist in `src/api/web_service.py` implementiert (Requested/Allowed/Quota/Budget, deterministische `fallback_reason`).

### Worker / Async Pipeline
- Muss die **gleichen** Gates beachten (z. B. Token-/Zeitbudgets, Retention, Export-Enablement).
- Darf sich nicht auf UI-Checks verlassen.

### UI
- Darf nur „optimistisch“ ausblenden/anzeigen (UX), aber nie als Autorisierung gelten.

## 5) Konkrete Capability-/Entitlement-Beispiele (mind. 5)

1. **`capability.analyze.async`** (bool)
   - Semantik: Tenant darf Async-Mode anfordern (`options.async_mode.requested=true`).
   - Enforcement: API Layer (Request-Accept), Worker Pipeline (Job-Dispatch).

2. **`entitlement.analyze.max_runtime_seconds`** (int)
   - Semantik: Obergrenze für Sync-Analyse; darüber muss Async genutzt oder abgebrochen werden.
   - Enforcement: API Layer (Timeout/Budget).

3. **`entitlement.requests.monthly`** (int)
   - Semantik: monatliches Analyse-Quota (Org-scope).
   - Enforcement: API Layer (vor Ausführung), Usage-Rollup (Window).

4. **`entitlement.requests.rate_limit_per_minute`** (int)
   - Semantik: Burst-Limit (Org/API-Key-scope möglich).
   - Enforcement: Edge/WAF primär, API-Fallback sekundär.

5. **`capability.exports.enabled`** (bool)
   - Semantik: Export-Endpoints/GUI-Export verfügbar (z. B. PDF/CSV).
   - Enforcement: API Layer (Endpoint guard), UI (hide).

6. **`capability.trace.debug`** (enum `no|optional|yes`)
   - Semantik: Zugriff auf Trace-/Debug-Endpunkte; kann auch rollen-/environment-abhängig sein.
   - Enforcement: API Layer (AuthZ + Entitlement), Audit.

## 6) Schnittstellen zu Billing/Plan/Subscription

- Plan/Tier definiert Baseline (siehe Gate-Katalog).
- Billing-Lifecycle modifiziert effektive Gates (Grace/Past-Due etc.).
- Provider-Sync muss idempotent sein (siehe `docs/api/entitlements-v1.md` / Billing-Lifecycle-Doku).

## 7) Offene Fragen (v1)

- Brauchen wir **user-scope entitlements** früh (Seat-/Role-Limits), oder reicht `memberships.role` v1?
- Sollen `capability.*` strikt bool/enum sein, und `entitlement.*` strikt numerisch? (Queryability)
- Wo liegt der kanonische Ort für Override-Policy (Support-Runbook vs. Domain-Doc)?
