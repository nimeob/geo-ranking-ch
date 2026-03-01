# Minimum-Compliance-Set — Policy-Metadaten-Contract v1

_Status: freigegeben (Repo-Baseline)_  
_Gültig ab: 2026-03-01_  
_Bezug: Issue #539_

## Zweck

Dieser Contract beschreibt das **technische Runtime-Metadatenmodell v1** für Compliance-Policies.
Er konkretisiert die Pflichtfelder aus dem Policy-Standard (`docs/compliance/POLICY_STANDARD_V1.md`) für die maschinelle Validierung in `src/compliance/policy_metadata.py`.

## Contract-Schema (v1)

Pflichtfelder (alle `required`):

| Feld | Typ | Regel | Beispiel |
|---|---|---|---|
| `policy_id` | `string` | muss mit `POL-` starten | `POL-RETDEL-001` |
| `version` | `string` | Regex `^v\d+\.\d+$` | `v1.0` |
| `begruendung` | `string` | non-empty (trimmed) | `Regulatorische Mindestanforderungen konsolidiert` |
| `wirksam_ab` | `string` | ISO-Datum `YYYY-MM-DD` | `2026-03-01` |
| `impact_referenz` | `string` | Präfix: `https://`, `http://`, `issue:` oder `#` | `https://github.com/nimeob/geo-ranking-ch/issues/539` |

## Normatives JSON-Beispiel (gültig)

```json
{
  "policy_id": "POL-RETDEL-001",
  "version": "v1.0",
  "begruendung": "Regulatorische Mindestanforderungen konsolidiert",
  "wirksam_ab": "2026-03-01",
  "impact_referenz": "https://github.com/nimeob/geo-ranking-ch/issues/539"
}
```

## Beispielartefakte (Repo)

- `docs/compliance/examples/policy-metadata.v1.valid-url.json`
- `docs/compliance/examples/policy-metadata.v1.valid-issue-ref.json`
- `docs/compliance/examples/policy-metadata.v1.invalid-missing-impact-ref.json`

Die Artefakte sind so gewählt, dass sowohl gültige (`URL`, `issue:`-Referenz) als auch negative Pfade (`missing required field`) reproduzierbar getestet werden können.

## Validierungsreferenz

- Runtime-Validierung: `src/compliance/policy_metadata.py`
- Regressionstests (Modell): `tests/test_compliance_policy_metadata_model.py`
- Regressionstests (Contract + Beispiele): `tests/test_compliance_policy_metadata_contract_docs.py`

## Abgrenzung / Nicht-Ziele

- Dieser Contract deckt bewusst nur den technischen Kern-Envelope für Runtime-Validierung ab.
- Erweiterte Governance-Metadaten (z. B. `owner_role`, `approved_by_role`, `review_intervall`) bleiben fachliche Pflicht im Policy-Standard und werden in separaten Work-Packages technisch erzwungen.

## Nachweis

- Backlog-Sync: `docs/BACKLOG.md`
- Claim-/Umsetzungshistorie: `https://github.com/nimeob/geo-ranking-ch/issues/539`
