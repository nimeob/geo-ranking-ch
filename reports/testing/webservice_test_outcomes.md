# Webservice Test Outcomes (BL-XX.4 / Issue #252)

Stand: 2026-02-27

Command:
```bash
python3 -m pytest -q --junitxml reports/testing/webservice_test_outcomes.junit.xml tests/test_web_e2e.py tests/test_web_service_grouped_response.py tests/test_web_service_port_resolution.py tests/test_remote_smoke_script.py tests/test_remote_stability_script.py tests/test_web_e2e_dev.py
```

- Passed: **141**
- Skipped: **2**
- Failed: **0**
- Errors: **0**

## Testcase Outcomes

| Testcase | Outcome | Time (s) | Note |
|---|---|---:|---|
| `tests.test_web_e2e.TestWebServiceE2E::test_analyze_accepts_case_insensitive_mode_with_whitespace` | passed | 0.213 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_analyze_accepts_double_slashes_and_query` | passed | 0.002 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_analyze_accepts_trailing_slash_and_query` | passed | 0.001 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_analyze_accepts_valid_preferences_profile` | passed | 0.002 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_analyze_happy_path` | passed | 0.002 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_analyze_ignores_unknown_options_keys_as_additive_noop` | passed | 0.001 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_analyze_runtime_personalization_changes_personalized_score` | passed | 0.002 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_analyze_runtime_personalization_fallback_without_preferences` | passed | 0.001 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_analyze_runtime_personalization_partial_when_zero_intensity` | passed | 0.001 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_auth_accepts_case_insensitive_bearer_and_trimmed_whitespace` | passed | 0.002 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_auth_rejects_malformed_bearer_headers` | passed | 0.002 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_auth_required_for_analyze` | passed | 0.001 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_bad_request_empty_body` | passed | 0.001 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_bad_request_invalid_json_and_body_edgecases` | passed | 0.003 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_bad_request_invalid_mode` | passed | 0.001 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_bad_request_non_finite_timeout` | passed | 0.001 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_bad_request_options_must_be_object_when_provided` | passed | 0.003 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_bad_request_preferences_must_be_object_when_provided` | passed | 0.003 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_bad_request_preferences_reject_invalid_enums_and_weights` | passed | 0.011 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_get_endpoints_echo_request_id` | passed | 0.001 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_health_and_version` | passed | 0.001 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_health_and_version_accept_double_slashes` | passed | 0.001 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_health_and_version_accept_trailing_slash_and_query` | passed | 0.001 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_not_found` | passed | 0.001 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_post_not_found_for_unknown_route` | passed | 0.001 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_request_id_accepts_lowercase_underscore_primary_header_alias` | passed | 0.001 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_request_id_accepts_short_primary_header_alias` | passed | 0.001 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_request_id_accepts_short_primary_underscore_header_alias` | passed | 0.001 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_request_id_accepts_underscore_primary_header` | passed | 0.001 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_request_id_echoed_for_analyze_paths` | passed | 0.001 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_request_id_falls_back_to_correlation_header_when_primary_contains_control_chars` | passed | 0.001 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_request_id_falls_back_to_correlation_header_when_primary_contains_delimiters` | passed | 0.001 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_request_id_falls_back_to_correlation_header_when_primary_contains_embedded_whitespace` | passed | 0.001 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_request_id_falls_back_to_correlation_header_when_primary_contains_non_ascii` | passed | 0.001 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_request_id_falls_back_to_correlation_header_when_primary_is_blank` | passed | 0.001 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_request_id_falls_back_to_correlation_header_when_primary_is_too_long` | passed | 0.001 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_request_id_falls_back_to_correlation_when_underscore_primary_is_invalid` | passed | 0.001 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_request_id_falls_back_to_short_correlation_alias` | passed | 0.001 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_request_id_falls_back_to_short_underscore_correlation_alias` | passed | 0.001 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_request_id_falls_back_to_underscore_correlation_header` | passed | 0.001 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_request_id_prefers_valid_underscore_primary_when_hyphen_primary_is_invalid` | passed | 0.001 |  |
| `tests.test_web_e2e.TestWebServiceE2E::test_timeout_address_intel_and_internal_are_mapped` | passed | 0.005 |  |
| `tests.test_web_e2e.TestWebServiceEnvPortFallback::test_health_works_with_web_port_fallback` | passed | 0.207 |  |
| `tests.test_web_service_grouped_response.TestGroupedApiResult::test_separates_status_from_data_and_groups_by_source` | passed | 0.001 |  |
| `tests.test_web_service_port_resolution.TestResolvePort::test_falls_back_to_web_port_when_port_missing_or_blank` | passed | 0.001 |  |
| `tests.test_web_service_port_resolution.TestResolvePort::test_prefers_port_when_set` | passed | 0.000 |  |
| `tests.test_web_service_port_resolution.TestResolvePort::test_raises_value_error_for_invalid_port_inputs` | passed | 0.001 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_accepts_boolean_request_id_echo_flag_aliases` | passed | 0.550 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_accepts_correlation_header_alias_for_request_id_mode` | passed | 0.293 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_accepts_correlation_header_underscore_alias_for_request_id_mode` | passed | 0.327 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_accepts_lowercase_correlation_underscore_alias_for_request_id_mode` | passed | 0.348 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_accepts_lowercase_request_underscore_alias_for_request_id_mode` | passed | 0.324 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_accepts_request_header_alias_for_request_id_mode` | passed | 0.322 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_accepts_request_header_underscore_alias_for_request_id_mode` | passed | 0.321 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_accepts_short_correlation_header_alias_for_request_id_mode` | passed | 0.310 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_accepts_short_correlation_underscore_alias_for_request_id_mode` | passed | 0.301 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_accepts_short_request_header_alias_for_request_id_mode` | passed | 0.301 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_accepts_short_request_header_underscore_alias_for_request_id_mode` | passed | 0.325 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_accepts_uppercase_http_scheme` | passed | 0.331 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_fails_without_token_when_auth_enabled` | passed | 0.308 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_generates_unique_default_request_id_when_system_time_is_constant` | passed | 0.668 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_handles_combined_scheme_case_reverse_suffix_chain_slash_and_whitespace` | passed | 0.321 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_handles_combined_scheme_case_suffix_chain_slash_and_whitespace` | passed | 0.310 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_normalizes_base_url_when_analyze_suffix_is_provided` | passed | 0.312 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_normalizes_base_url_when_health_suffix_is_provided` | passed | 0.293 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_normalizes_chained_analyze_and_health_suffixes` | passed | 0.324 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_normalizes_chained_health_and_analyze_suffixes` | passed | 0.304 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_normalizes_redundant_trailing_slashes_after_suffix_chain` | passed | 0.329 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_normalizes_repeated_forward_suffix_chain_with_internal_double_slash` | passed | 0.346 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_normalizes_repeated_health_analyze_suffix_chain` | passed | 0.312 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_normalizes_repeated_reverse_suffix_chain_with_internal_double_slash` | passed | 0.335 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_normalizes_repeated_reverse_suffix_chain_with_scheme_case_and_whitespace` | passed | 0.337 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_normalizes_smoke_mode_case_before_validation` | passed | 0.323 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_normalizes_suffixes_case_insensitively` | passed | 0.325 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_passes_with_valid_token` | passed | 0.331 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_rejects_base_url_with_embedded_whitespace` | passed | 0.024 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_rejects_base_url_with_non_numeric_port` | passed | 0.254 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_rejects_base_url_with_out_of_range_port` | passed | 0.250 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_rejects_base_url_with_query_or_fragment` | passed | 0.227 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_rejects_base_url_with_userinfo` | passed | 0.241 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_rejects_curl_max_time_below_smoke_timeout` | passed | 0.215 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_rejects_dev_api_auth_token_with_control_characters` | passed | 0.275 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_rejects_dev_api_auth_token_with_embedded_whitespace` | passed | 0.284 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_rejects_invalid_base_url_scheme` | passed | 0.237 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_rejects_invalid_request_id_echo_flag` | passed | 0.215 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_rejects_invalid_request_id_header_mode` | passed | 0.206 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_rejects_invalid_retry_count` | passed | 0.189 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_rejects_invalid_retry_delay` | passed | 0.215 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_rejects_invalid_smoke_timeout` | passed | 0.193 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_rejects_non_finite_curl_max_time` | passed | 0.197 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_rejects_non_finite_smoke_timeout` | passed | 0.173 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_rejects_output_json_path_when_parent_is_file` | passed | 0.036 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_rejects_output_json_path_when_target_is_directory` | passed | 0.034 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_rejects_output_json_path_with_control_characters` | passed | 0.032 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_rejects_request_id_header_mode_with_control_characters` | passed | 0.181 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_rejects_request_id_header_mode_with_embedded_whitespace` | passed | 0.217 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_rejects_request_id_longer_than_128_chars` | passed | 0.153 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_rejects_request_id_with_control_characters` | passed | 0.135 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_rejects_request_id_with_delimiters` | passed | 0.145 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_rejects_request_id_with_embedded_whitespace` | passed | 0.152 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_rejects_request_id_with_non_ascii_characters` | passed | 0.163 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_rejects_smoke_query_with_control_characters` | passed | 0.120 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_rejects_whitespace_only_base_url` | passed | 0.012 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_rejects_whitespace_only_dev_api_auth_token` | passed | 0.279 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_rejects_whitespace_only_output_json_path` | passed | 0.030 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_rejects_whitespace_only_request_id` | passed | 0.130 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_rejects_whitespace_only_request_id_header_mode` | passed | 0.204 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_rejects_whitespace_only_smoke_query` | passed | 0.115 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_supports_correlation_header_mode_for_request_id_echo` | passed | 0.289 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_trims_dev_api_auth_token_before_request` | passed | 0.328 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_trims_output_json_path_before_writing_curl_error_report` | passed | 0.288 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_trims_request_id_before_validation_and_echo_check` | passed | 0.295 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_trims_request_id_echo_flag_before_validation` | passed | 0.337 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_trims_request_id_header_mode_before_validation` | passed | 0.282 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_trims_retry_count_and_delay_before_validation` | passed | 0.306 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_trims_smoke_mode_before_validation` | passed | 0.303 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_trims_smoke_query_before_request` | passed | 0.300 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_trims_tab_wrapped_base_url_and_header_mode` | passed | 0.310 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_trims_timeout_and_curl_max_time_before_validation` | passed | 0.323 |  |
| `tests.test_remote_smoke_script.TestRemoteSmokeScript::test_smoke_script_trims_whitespace_around_base_url` | passed | 0.301 |  |
| `tests.test_remote_stability_script.TestRemoteStabilityScript::test_stability_runner_accepts_false_alias_for_stop_on_first_fail` | passed | 1.190 |  |
| `tests.test_remote_stability_script.TestRemoteStabilityScript::test_stability_runner_accepts_health_suffix_in_base_url` | passed | 0.772 |  |
| `tests.test_remote_stability_script.TestRemoteStabilityScript::test_stability_runner_accepts_true_alias_for_stop_on_first_fail` | passed | 0.402 |  |
| `tests.test_remote_stability_script.TestRemoteStabilityScript::test_stability_runner_creates_missing_report_parent_directories` | passed | 0.790 |  |
| `tests.test_remote_stability_script.TestRemoteStabilityScript::test_stability_runner_marks_missing_smoke_report_as_failure_even_with_rc_zero` | passed | 0.100 |  |
| `tests.test_remote_stability_script.TestRemoteStabilityScript::test_stability_runner_marks_non_pass_report_as_failure_even_with_rc_zero` | passed | 0.113 |  |
| `tests.test_remote_stability_script.TestRemoteStabilityScript::test_stability_runner_passes_for_two_successful_runs` | passed | 0.750 |  |
| `tests.test_remote_stability_script.TestRemoteStabilityScript::test_stability_runner_rejects_invalid_stop_on_first_fail_flag` | passed | 0.085 |  |
| `tests.test_remote_stability_script.TestRemoteStabilityScript::test_stability_runner_rejects_report_path_when_parent_is_file` | passed | 0.076 |  |
| `tests.test_remote_stability_script.TestRemoteStabilityScript::test_stability_runner_rejects_report_path_when_target_is_directory` | passed | 0.078 |  |
| `tests.test_remote_stability_script.TestRemoteStabilityScript::test_stability_runner_rejects_report_path_with_control_characters` | passed | 0.072 |  |
| `tests.test_remote_stability_script.TestRemoteStabilityScript::test_stability_runner_rejects_smoke_script_override_when_path_is_directory` | passed | 0.085 |  |
| `tests.test_remote_stability_script.TestRemoteStabilityScript::test_stability_runner_rejects_smoke_script_override_with_control_characters` | passed | 0.070 |  |
| `tests.test_remote_stability_script.TestRemoteStabilityScript::test_stability_runner_rejects_whitespace_only_report_path` | passed | 0.054 |  |
| `tests.test_remote_stability_script.TestRemoteStabilityScript::test_stability_runner_rejects_whitespace_only_smoke_script_override` | passed | 0.057 |  |
| `tests.test_remote_stability_script.TestRemoteStabilityScript::test_stability_runner_resolves_relative_smoke_script_override_from_foreign_cwd` | passed | 0.435 |  |
| `tests.test_remote_stability_script.TestRemoteStabilityScript::test_stability_runner_stops_on_first_failure_when_configured` | passed | 0.382 |  |
| `tests.test_remote_stability_script.TestRemoteStabilityScript::test_stability_runner_trims_numeric_flags_before_validation` | passed | 0.755 |  |
| `tests.test_remote_stability_script.TestRemoteStabilityScript::test_stability_runner_trims_report_path_before_write` | passed | 0.755 |  |
| `tests.test_remote_stability_script.TestRemoteStabilityScript::test_stability_runner_trims_smoke_script_override_before_exec` | passed | 0.419 |  |
| `tests.test_remote_stability_script.TestRemoteStabilityScript::test_stability_runner_trims_tab_wrapped_flags_before_validation` | passed | 0.754 |  |
| `tests.test_web_e2e_dev.TestWebServiceE2EDev::test_dev_analyze_with_optional_auth` | skipped | 0.000 | DEV_BASE_URL nicht gesetzt |
| `tests.test_web_e2e_dev.TestWebServiceE2EDev::test_dev_health_version_not_found` | skipped | 0.000 | DEV_BASE_URL nicht gesetzt |
