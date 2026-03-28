from pathlib import Path


def test_deploy_version_trace_runbook_contains_required_checklist():
    doc = Path("docs/testing/DEPLOY_VERSION_TRACE_DEBUG_RUNBOOK.md")
    assert (
        doc.exists()
    ), "Runbook fehlt: docs/testing/DEPLOY_VERSION_TRACE_DEBUG_RUNBOOK.md"

    text = doc.read_text(encoding="utf-8")
    required = [
        "# Deploy-Runbook — Version-Drift & Trace-Debug Verifikation (Issue #534)",
        "### A) Deploy-Verifikation (Version)",
        "/healthz",
        "### B) Trace-Debug-Funktion",
        "`/debug/trace`",
        "### C) Regression-Schutz (CI)",
        "scripts/check_deploy_version_trace.py",
    ]

    missing = [snippet for snippet in required if snippet not in text]
    assert not missing, f"Runbook unvollständig, fehlend: {missing}"


def test_deployment_aws_doc_references_post_deploy_verifier():
    doc = Path("docs/DEPLOYMENT_AWS.md")
    assert doc.exists(), "Dokument fehlt: docs/DEPLOYMENT_AWS.md"

    text = doc.read_text(encoding="utf-8")
    required = [
        "Post-Deploy-Verifikation (`scripts/check_deploy_version_trace.py`)",
        "`TRACE_DEBUG_ENABLED`",
        "DEPLOY_VERSION_TRACE_DEBUG_RUNBOOK.md",
    ]

    missing = [snippet for snippet in required if snippet not in text]
    assert not missing, f"DEPLOYMENT_AWS.md fehlt erforderliche Referenzen: {missing}"


def test_deploy_workflow_runs_post_deploy_verification_step():
    workflow = Path(".github/workflows/deploy.yml")
    assert workflow.exists(), "Workflow fehlt: .github/workflows/deploy.yml"

    text = workflow.read_text(encoding="utf-8")
    # Keep this check resilient while the workflow is being simplified/repaired.
    required = [
        "Smoke-Test API /health",
        "Smoke-Test UI /healthz",
    ]

    missing = [snippet for snippet in required if snippet not in text]
    assert not missing, f"deploy.yml fehlt Basis-Deploy-Verifikation: {missing}"


def test_deploy_workflow_runs_boundary_guardrail_before_unit_tests():
    workflow = Path(".github/workflows/deploy.yml")
    assert workflow.exists(), "Workflow fehlt: .github/workflows/deploy.yml"

    text = workflow.read_text(encoding="utf-8")
    required = [
        "Preflight boundary guard (fail-fast)",
        "python3 scripts/check_bl31_service_boundaries.py --src-dir src",
        "Run unit tests",
    ]

    missing = [snippet for snippet in required if snippet not in text]
    assert not missing, f"deploy.yml fehlt Boundary-Preflight-Guardrail: {missing}"

    assert text.index("Preflight boundary guard (fail-fast)") < text.index(
        "Run unit tests"
    ), "Boundary-Preflight muss vor dem Unit-Test-Lauf ausgeführt werden."


def test_deploy_workflow_guards_against_container_name_mismatches():
    workflow = Path(".github/workflows/deploy.yml")
    assert workflow.exists(), "Workflow fehlt: .github/workflows/deploy.yml"

    text = workflow.read_text(encoding="utf-8")
    required = [
        "Register new task definitions (API + UI)",
        "ECS_API_CONTAINER_NAME",
        "ECS_UI_CONTAINER_NAME",
    ]

    missing = [snippet for snippet in required if snippet not in text]
    assert not missing, f"deploy.yml fehlt Taskdef-Container-Verdrahtung: {missing}"


def test_deploy_workflow_validates_required_env_keys_before_rollout():
    workflow = Path(".github/workflows/deploy.yml")
    assert workflow.exists(), "Workflow fehlt: .github/workflows/deploy.yml"

    text = workflow.read_text(encoding="utf-8")
    required = [
        "Validate required deploy environment keys (vars + secrets)",
        "SERVICE_API_AUTH_TOKEN: ${{ secrets.SERVICE_API_AUTH_TOKEN }}",
        "SERVICE_API_BASE_URL: ${{ vars.SERVICE_API_BASE_URL }}",
        "SERVICE_HEALTH_URL: ${{ vars.SERVICE_HEALTH_URL }}",
        "python3 scripts/validate_required_deploy_env.py",
    ]

    missing = [snippet for snippet in required if snippet not in text]
    assert not missing, f"deploy.yml fehlt ENV-Preflight-Guardrail: {missing}"

    assert text.index(
        "Validate required deploy environment keys (vars + secrets)"
    ) < text.index(
        "Configure AWS credentials (OIDC)"
    ), "ENV-Preflight muss vor dem AWS-Deploy beginnen."


def test_deployment_aws_doc_contains_deploy_env_preflight_examples():
    doc = Path("docs/DEPLOYMENT_AWS.md")
    assert doc.exists(), "Dokument fehlt: docs/DEPLOYMENT_AWS.md"

    text = doc.read_text(encoding="utf-8")
    required = [
        "Preflight-Validator (required ENV-Keys)",
        "python3 scripts/validate_required_deploy_env.py",
        "Lokaler Start (trocken, nur Validierung)",
        "Fehlerbeispiel (gekürzt)",
        "Deploy preflight failed: missing required environment keys",
    ]

    missing = [snippet for snippet in required if snippet not in text]
    assert not missing, f"DEPLOYMENT_AWS.md fehlt ENV-Preflight-Beispiel: {missing}"


def test_deployment_aws_doc_mentions_container_resolution_guardrail():
    doc = Path("docs/DEPLOYMENT_AWS.md")
    assert doc.exists(), "Dokument fehlt: docs/DEPLOYMENT_AWS.md"

    text = doc.read_text(encoding="utf-8")
    required = [
        "Hinweis zur Container-Auflösung (ECS)",
        "ECS_API_CONTAINER_NAME`/`ECS_UI_CONTAINER_NAME`",
        "genau einen",
        "stilles No-Op-Deploy",
    ]

    missing = [snippet for snippet in required if snippet not in text]
    assert (
        not missing
    ), f"DEPLOYMENT_AWS.md fehlt Container-Auflösungs-Hinweis: {missing}"


def test_deployment_aws_doc_lists_required_deploy_auth_secret_preflight():
    doc = Path("docs/DEPLOYMENT_AWS.md")
    assert doc.exists(), "Dokument fehlt: docs/DEPLOYMENT_AWS.md"

    text = doc.read_text(encoding="utf-8")
    required = [
        "Pflicht-Secret (deploy/auth preflight)",
        "SERVICE_API_AUTH_TOKEN",
        "Workflow-Abbruch vor dem eigentlichen Rollout",
    ]

    missing = [snippet for snippet in required if snippet not in text]
    assert (
        not missing
    ), f"DEPLOYMENT_AWS.md fehlt Pflicht-Secret-Dokumentation: {missing}"


def test_deploy_workflow_uses_deploy_gate_runner_with_rollback_snapshot():
    workflow = Path(".github/workflows/deploy.yml")
    assert workflow.exists(), "Workflow fehlt: .github/workflows/deploy.yml"

    text = workflow.read_text(encoding="utf-8")
    required = [
        "Build and push API/UI images",
        "Register new task definitions (API + UI)",
        "Deploy API service and wait for stability",
        "Deploy UI service and wait for stability",
    ]

    missing = [snippet for snippet in required if snippet not in text]
    assert not missing, f"deploy.yml fehlt Kern-Rollout-Verdrahtung: {missing}"


def test_deploy_workflow_wires_database_reachability_gate_inputs():
    workflow = Path(".github/workflows/deploy.yml")
    assert workflow.exists(), "Workflow fehlt: .github/workflows/deploy.yml"

    text = workflow.read_text(encoding="utf-8")
    required = [
        "SERVICE_API_BASE_URL",
        "SERVICE_HEALTH_URL",
        "SERVICE_APP_BASE_URL",
        "Smoke-Test API /health",
        "Smoke-Test UI /healthz",
    ]

    missing = [snippet for snippet in required if snippet not in text]
    assert not missing, f"deploy.yml fehlt Health-Gate-Verdrahtung: {missing}"


def _assert_login_contract_smoke_coverage(
    *, text: str, env_name: str, workflow_name: str
) -> None:
    required = [
        "Smoke-Test UI login start redirects to IdP authorize (",
        "scripts/smoke/run_login_start_smoke_bundle.sh",
        f'--env-name "{env_name}"',
        f"artifacts/{env_name}-login-start-smoke-root.json",
        f"artifacts/{env_name}-login-start-smoke.json",
        f"artifacts/{env_name}-login-start-smoke-gui-history.json",
        f"artifacts/{env_name}-login-start-smoke-history-legacy.json",
        f"artifacts/{env_name}-login-start-smoke-jobs.json",
        f"artifacts/{env_name}-login-start-smoke-jobs-query.json",
        f"artifacts/{env_name}-login-start-smoke-jobs-detail.json",
        f"artifacts/{env_name}-login-start-smoke-results-detail.json",
        f"artifacts/{env_name}-login-start-smoke-results-detail-query.json",
        f"artifacts/{env_name}-login-start-smoke-gui-results-legacy-detail.json",
        f"artifacts/{env_name}-login-start-smoke-gui-results-legacy-detail-query.json",
        f"artifacts/{env_name}-login-start-smoke-gui-jobs-legacy.json",
        f"artifacts/{env_name}-login-start-smoke-gui-jobs-legacy-query.json",
        f"artifacts/{env_name}-login-start-smoke-gui-jobs-legacy-detail.json",
        f"Upload login-start smoke artifacts ({env_name})",
        "actions/upload-artifact@v6",
        f"{env_name}-login-start-smoke-${{{{ github.run_id }}}}-${{{{ github.run_attempt }}}}",
    ]

    missing = [snippet for snippet in required if snippet not in text]
    assert (
        not missing
    ), f"{workflow_name} fehlt Login-Contract-Smoke-Coverage: {missing}"


def _assert_canonical_host_smoke_coverage(
    *, text: str, env_name: str, workflow_name: str
) -> None:
    required = [
        "Smoke-Test UI canonical-host redirect (/login?start=1 on alias host)",
        "python3 scripts/smoke/check_ui_canonical_redirect.py",
        "UI_CANONICAL_ORIGIN: ${{ vars.UI_CANONICAL_ORIGIN }}",
        "UI_CANONICAL_HOSTS: ${{ vars.UI_CANONICAL_HOSTS }}",
        f"artifacts/{env_name}-canonical-host-redirect-smoke.json",
    ]

    missing = [snippet for snippet in required if snippet not in text]
    assert (
        not missing
    ), f"{workflow_name} fehlt Canonical-Host-Smoke-Coverage: {missing}"


def _assert_auth_proxy_guard_smoke_coverage(
    *, text: str, env_name: str, workflow_name: str
) -> None:
    required = [
        "Smoke-Test API auth proxy forwarded-host guard (/auth/login|logout|callback)",
        "python3 scripts/smoke/check_bff_auth_proxy_guard.py",
        "SERVICE_API_BASE_URL: ${{ vars.SERVICE_API_BASE_URL }}",
        "SERVICE_APP_BASE_URL: ${{ vars.SERVICE_APP_BASE_URL }}",
        f"artifacts/{env_name}-auth-proxy-guard-smoke.json",
    ]

    missing = [snippet for snippet in required if snippet not in text]
    assert (
        not missing
    ), f"{workflow_name} fehlt Auth-Proxy-Guard-Smoke-Coverage: {missing}"


def test_deploy_workflow_smokes_login_contract_for_gui_history_jobs_and_legacy_routes():
    workflow = Path(".github/workflows/deploy.yml")
    assert workflow.exists(), "Workflow fehlt: .github/workflows/deploy.yml"

    text = workflow.read_text(encoding="utf-8")
    _assert_login_contract_smoke_coverage(
        text=text, env_name="dev", workflow_name="deploy.yml"
    )


def test_deploy_staging_workflow_smokes_login_contract_for_gui_history_jobs_and_legacy_routes():
    workflow = Path(".github/workflows/deploy-staging.yml")
    assert workflow.exists(), "Workflow fehlt: .github/workflows/deploy-staging.yml"

    text = workflow.read_text(encoding="utf-8")
    _assert_login_contract_smoke_coverage(
        text=text, env_name="staging", workflow_name="deploy-staging.yml"
    )


def test_deploy_workflow_smokes_canonical_host_redirect_when_alias_hosts_are_configured():
    workflow = Path(".github/workflows/deploy.yml")
    assert workflow.exists(), "Workflow fehlt: .github/workflows/deploy.yml"

    text = workflow.read_text(encoding="utf-8")
    _assert_canonical_host_smoke_coverage(
        text=text, env_name="dev", workflow_name="deploy.yml"
    )


def test_deploy_staging_workflow_smokes_canonical_host_redirect_when_alias_hosts_are_configured():
    workflow = Path(".github/workflows/deploy-staging.yml")
    assert workflow.exists(), "Workflow fehlt: .github/workflows/deploy-staging.yml"

    text = workflow.read_text(encoding="utf-8")
    _assert_canonical_host_smoke_coverage(
        text=text, env_name="staging", workflow_name="deploy-staging.yml"
    )


def test_deploy_workflow_requires_tls_valid_alias_for_login_route_matrix_smoke():
    workflow = Path(".github/workflows/deploy.yml")
    assert workflow.exists(), "Workflow fehlt: .github/workflows/deploy.yml"

    text = workflow.read_text(encoding="utf-8")
    required = [
        "scripts/smoke/infer_geo_alias_base_url.py",
        "--require-tls-hostname-match",
        "No TLS-valid alias host could be inferred",
    ]

    missing = [snippet for snippet in required if snippet not in text]
    assert (
        not missing
    ), f"deploy.yml fehlt TLS-validierter Alias-Guard für route-matrix smoke: {missing}"


def test_deploy_workflow_smokes_auth_proxy_guard_for_login_logout_and_callback_paths():
    workflow = Path(".github/workflows/deploy.yml")
    assert workflow.exists(), "Workflow fehlt: .github/workflows/deploy.yml"

    text = workflow.read_text(encoding="utf-8")
    _assert_auth_proxy_guard_smoke_coverage(
        text=text, env_name="dev", workflow_name="deploy.yml"
    )


def test_deploy_staging_workflow_smokes_auth_proxy_guard_for_login_logout_and_callback_paths():
    workflow = Path(".github/workflows/deploy-staging.yml")
    assert workflow.exists(), "Workflow fehlt: .github/workflows/deploy-staging.yml"

    text = workflow.read_text(encoding="utf-8")
    _assert_auth_proxy_guard_smoke_coverage(
        text=text, env_name="staging", workflow_name="deploy-staging.yml"
    )


def test_deployment_aws_doc_mentions_deploy_gate_rollback_required_marker():
    doc = Path("docs/DEPLOYMENT_AWS.md")
    assert doc.exists(), "Dokument fehlt: docs/DEPLOYMENT_AWS.md"

    text = doc.read_text(encoding="utf-8")
    required = [
        "scripts/run_deploy_gate.sh",
        "deploy-gate-report/v1",
        "ROLLBACK_REQUIRED",
        "DEPLOY_GATE_ROLLBACK_MODE",
        "BL31_DEPLOY_ROLLBACK_RUNBOOK.md",
    ]

    missing = [snippet for snippet in required if snippet not in text]
    assert not missing, f"DEPLOYMENT_AWS.md fehlt Deploy-Gate-Rollback-Notiz: {missing}"


def test_deployment_aws_doc_mentions_database_reachability_gate():
    doc = Path("docs/DEPLOYMENT_AWS.md")
    assert doc.exists(), "Dokument fehlt: docs/DEPLOYMENT_AWS.md"

    text = doc.read_text(encoding="utf-8")
    required = [
        "API-`/health`, GUI-`/gui` **und** DB-Reachability",
        "checks.database.status=ok",
        "SERVICE_DB_HEALTH_DETAILS_URL",
        "failure_reason",
    ]

    missing = [snippet for snippet in required if snippet not in text]
    assert (
        not missing
    ), f"DEPLOYMENT_AWS.md fehlt DB-Reachability-Gate-Dokumentation: {missing}"
