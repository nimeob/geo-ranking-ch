# Webservice Result-Path Coverage Inventory (BL-XX.2 / Issue #250)

Stand: 2026-02-27

## Scope

Analysiert wurden die Resultpfade des produktiven Webservice-Einstiegspunkts `src/web_service.py`:

- `Handler.do_GET` (`/health`, `/version`, unknown)
- `Handler.do_POST` (`/analyze`, Auth, Inputvalidierung, Fehler-Mapping)
- Request-/Routing-Helfer mit Laufzeitwirkung (`_normalized_path`, `_request_id`, `_extract_bearer_token`, `_extract_request_options`, `_extract_preferences`, `_as_positive_finite_number`, `_resolve_port`)
- Response-Shape-Helfer (`_grouped_api_result`)

## Coverage-Matrix (OK/NOK)

| Funktion / Pfad | Resultpfad | Erwartung | Evidenz (Tests) | Status |
|---|---|---|---|---|
| `GET /health` | Healthy response | `200`, `ok=true` | `test_health_and_version`, `test_health_and_version_accept_trailing_slash_and_query`, `test_health_and_version_accept_double_slashes` | ✅ covered |
| `GET /version` | Version response | `200`, `service/version` vorhanden | `test_health_and_version`, `test_health_and_version_accept_trailing_slash_and_query`, `test_health_and_version_accept_double_slashes` | ✅ covered |
| `GET <unknown>` | Not found | `404`, `error=not_found` | `test_not_found`, `test_dev_health_version_not_found` | ✅ covered |
| `POST /analyze` + gültige Auth + valide Payload | Happy path | `200`, `ok=true`, grouped result | `test_analyze_happy_path` | ✅ covered |
| `POST /analyze` + Trailing slash/query/double slashes | Pfadnormalisierung | `200` | `test_analyze_accepts_trailing_slash_and_query`, `test_analyze_accepts_double_slashes_and_query` | ✅ covered |
| `POST /analyze` ohne/mit falscher Auth | Unauthorized | `401`, `error=unauthorized` | `test_auth_required_for_analyze`, `test_auth_rejects_malformed_bearer_headers`, `test_dev_analyze_with_optional_auth` | ✅ covered |
| Authorization Header Parsing | Bearer tolerant / malformed rejected | gültig: `200`, ungültig: `401` | `test_auth_accepts_case_insensitive_bearer_and_trimmed_whitespace`, `test_auth_rejects_malformed_bearer_headers` | ✅ covered |
| `intelligence_mode` Validation | Unsupported mode | `400`, `error=bad_request` | `test_bad_request_invalid_mode`, `test_analyze_accepts_case_insensitive_mode_with_whitespace` | ✅ covered |
| `options` Envelope Validation | object required, unknown keys additive noop | `200` bzw. `400` | `test_analyze_ignores_unknown_options_keys_as_additive_noop`, `test_bad_request_options_must_be_object_when_provided` | ✅ covered |
| `preferences` Envelope Validation | valid profile / enum+weight guards | `200` bzw. `400` | `test_analyze_accepts_valid_preferences_profile`, `test_bad_request_preferences_must_be_object_when_provided`, `test_bad_request_preferences_reject_invalid_enums_and_weights` | ✅ covered |
| Personalization Runtime States | `active` / `deactivated` / `partial` | `200` + status konsistent | `test_analyze_runtime_personalization_changes_personalized_score`, `test_analyze_runtime_personalization_fallback_without_preferences`, `test_analyze_runtime_personalization_partial_when_zero_intensity` | ✅ covered |
| Body/JSON Validation | empty/malformed/utf8/object required | `400`, `error=bad_request` | `test_bad_request_empty_body`, `test_bad_request_invalid_json_and_body_edgecases` | ✅ covered |
| Timeout/Internal Mapping | fault injection mapping | `504 timeout`, `500 internal` | `test_timeout_and_internal_are_mapped` | ✅ covered |
| Request-ID Selection (POST) | primary/fallback aliases + sanitizer | `request_id` Echo in Body/Header | `test_request_id_echoed_for_analyze_paths` + alle `test_request_id_*` Fälle | ✅ covered |
| `POST` unknown path (`/analyze` only) | Not found (POST route) | `404`, `error=not_found` | `test_post_not_found_for_unknown_route` | ✅ covered |
| `AddressIntelError` Mapping | Domainfehler auf 422 | `422`, `error=address_intel` | `test_timeout_address_intel_and_internal_are_mapped` | ✅ covered |
| Request-ID Echo auf GET-Endpunkten | Header-Echo auf `/health`/`/version` | `X-Request-Id` konsistent | `test_get_endpoints_echo_request_id` | ✅ covered |
| `_resolve_port` mit ungültigen Inputs | Invalid `PORT/WEB_PORT` handling | Fail-fast/Fehlerpfad | `tests/test_web_service_port_resolution.py` | ✅ covered |

## Gap-Liste (Status nach #251)

Die in #250 identifizierten Lücken sind mit #251 geschlossen:

- ✅ POST unknown route (`404 not_found`) abgedeckt
- ✅ `AddressIntelError -> 422` deterministisch abgedeckt
- ✅ Request-ID-Echo auf GET-Endpunkten (`/health`, `/version`) abgedeckt
- ✅ `_resolve_port` Invalid-Input-Pfade abgedeckt

## Verifizierter Testlauf

```bash
python3 -m pytest -q tests/test_web_e2e.py tests/test_web_service_grouped_response.py tests/test_web_e2e_dev.py tests/test_web_service_port_resolution.py
# Ergebnis: 47 passed, 2 skipped, 27 subtests passed
```
