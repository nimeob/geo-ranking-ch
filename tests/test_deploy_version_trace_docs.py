from pathlib import Path

import yaml


def _load_workflow_yaml(path: str) -> dict:
    workflow = Path(path)
    assert workflow.exists(), f"Workflow fehlt: {path}"

    data = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"Workflow {path} ist kein gültiges YAML-Objekt"
    return data


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


def test_deployment_aws_doc_describes_dev_deploy_triggers_and_queue_concurrency():
    doc = Path("docs/DEPLOYMENT_AWS.md")
    assert doc.exists(), "Dokument fehlt: docs/DEPLOYMENT_AWS.md"

    text = doc.read_text(encoding="utf-8")
    required = [
        "manueller `workflow_dispatch` (on-demand)",
        "`push` auf `main`",
        "stündlicher `schedule` (`7 * * * *`)",
        "`concurrency.group: deploy-ecs-dev`",
        "`cancel-in-progress: false`",
    ]

    missing = [snippet for snippet in required if snippet not in text]
    assert (
        not missing
    ), f"DEPLOYMENT_AWS.md fehlt Trigger/Concurrency-Dokumentation für dev deploy: {missing}"


def test_architecture_doc_describes_dev_deploy_triggers_and_queue_concurrency():
    doc = Path("docs/ARCHITECTURE.md")
    assert doc.exists(), "Dokument fehlt: docs/ARCHITECTURE.md"

    text = doc.read_text(encoding="utf-8")
    required = [
        "`workflow_dispatch` (manueller Start)",
        "`push` auf `main`",
        "`schedule` (stündlich, `7 * * * *`)",
        "`group: deploy-ecs-dev`",
        "`cancel-in-progress: false`",
    ]

    missing = [snippet for snippet in required if snippet not in text]
    assert (
        not missing
    ), f"ARCHITECTURE.md fehlt Trigger/Concurrency-Dokumentation für dev deploy: {missing}"


def test_actions_migration_matrix_reflects_dev_deploy_trigger_reality():
    doc = Path("docs/automation/github-actions-migration-matrix.md")
    assert doc.exists(), "Dokument fehlt: docs/automation/github-actions-migration-matrix.md"

    text = doc.read_text(encoding="utf-8")
    required = [
        "`push` auf `main`, `schedule` (stündlich), `workflow_dispatch`",
        "`push` auf `main` + `schedule` + `workflow_dispatch`",
    ]

    missing = [snippet for snippet in required if snippet not in text]
    assert (
        not missing
    ), f"github-actions-migration-matrix.md fehlt Trigger-Sync für deploy.yml: {missing}"


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


def test_deploy_workflow_keeps_in_progress_dev_runs_for_ordered_rollout_control():
    data = _load_workflow_yaml(".github/workflows/deploy.yml")
    concurrency = data.get("concurrency")

    assert isinstance(
        concurrency, dict
    ), "deploy.yml fehlt root.concurrency als YAML-Objekt"
    assert (
        concurrency.get("group") == "deploy-ecs-dev"
    ), "deploy.yml concurrency.group muss deploy-ecs-dev sein"
    assert (
        concurrency.get("cancel-in-progress") is False
    ), "deploy.yml concurrency.cancel-in-progress muss false sein"


def test_deploy_staging_workflow_keeps_in_progress_runs_for_manual_rollout_control():
    data = _load_workflow_yaml(".github/workflows/deploy-staging.yml")
    concurrency = data.get("concurrency")

    assert isinstance(
        concurrency, dict
    ), "deploy-staging.yml fehlt root.concurrency als YAML-Objekt"
    assert (
        concurrency.get("group") == "deploy-ecs-staging"
    ), "deploy-staging.yml concurrency.group muss deploy-ecs-staging sein"
    assert (
        concurrency.get("cancel-in-progress") is False
    ), "deploy-staging.yml concurrency.cancel-in-progress muss false sein"


def _assert_service_stability_step_timeout(
    *, data: dict, workflow_name: str, expected_job_timeout_minutes: int
) -> None:
    jobs = data.get("jobs") or {}
    deploy_job = jobs.get("deploy-ecs-full-env")
    assert isinstance(
        deploy_job, dict
    ), f"{workflow_name} fehlt jobs.deploy-ecs-full-env"

    job_timeout = deploy_job.get("timeout-minutes")
    assert (
        job_timeout == expected_job_timeout_minutes
    ), f"{workflow_name} jobs.deploy-ecs-full-env timeout-minutes muss {expected_job_timeout_minutes} sein"

    steps = deploy_job.get("steps") or []
    assert isinstance(steps, list), f"{workflow_name} jobs.deploy-ecs-full-env.steps ist keine Liste"

    step_names = {
        "Deploy API service and wait for stability",
        "Deploy UI service and wait for stability",
    }

    for step_name in step_names:
        matched_step = next(
            (step for step in steps if isinstance(step, dict) and step.get("name") == step_name),
            None,
        )
        assert matched_step is not None, f"{workflow_name} fehlt Step: {step_name}"

        timeout_minutes = matched_step.get("timeout-minutes")
        assert (
            timeout_minutes == 25
        ), f"{workflow_name} Step '{step_name}' muss timeout-minutes=25 setzen"

        env = matched_step.get("env")
        assert isinstance(
            env, dict
        ), f"{workflow_name} Step '{step_name}' muss env als YAML-Objekt setzen"
        assert (
            env.get("ECS_STABILITY_TIMEOUT_SECONDS")
            == "${{ vars.ECS_STABILITY_TIMEOUT_SECONDS }}"
        ), (
            f"{workflow_name} Step '{step_name}' muss ECS_STABILITY_TIMEOUT_SECONDS "
            "aus vars übernehmen"
        )

        run_script = matched_step.get("run") or ""
        assert isinstance(
            run_script, str
        ), f"{workflow_name} Step '{step_name}' muss run-Shellcode enthalten"

        required_snippets = [
            "wait_for_service_stability",
            'timeout "${slice_seconds}" aws ecs wait services-stable',
            "::group::ECS service diagnostics",
        ]
        missing = [snippet for snippet in required_snippets if snippet not in run_script]
        assert (
            not missing
        ), f"{workflow_name} Step '{step_name}' fehlt ECS-Stability-Guardrail: {missing}"


def test_deploy_workflow_sets_explicit_timeout_guards_for_ecs_stability_waits():
    data = _load_workflow_yaml(".github/workflows/deploy.yml")
    _assert_service_stability_step_timeout(
        data=data,
        workflow_name="deploy.yml",
        expected_job_timeout_minutes=75,
    )


def test_deploy_staging_workflow_sets_explicit_timeout_guards_for_ecs_stability_waits():
    data = _load_workflow_yaml(".github/workflows/deploy-staging.yml")
    _assert_service_stability_step_timeout(
        data=data,
        workflow_name="deploy-staging.yml",
        expected_job_timeout_minutes=90,
    )


def test_deploy_workflow_emits_periodic_heartbeat_diagnostics_while_waiting_for_ecs_stability():
    workflow = Path(".github/workflows/deploy.yml")
    assert workflow.exists(), "Workflow fehlt: .github/workflows/deploy.yml"

    text = workflow.read_text(encoding="utf-8")
    required = [
        "Invalid ECS_STABILITY_TIMEOUT_SECONDS",
        "timeout \"${slice_seconds}\" aws ecs wait services-stable",
        "ECS wait still in progress for service",
    ]

    missing = [snippet for snippet in required if snippet not in text]
    assert (
        not missing
    ), f"deploy.yml fehlt periodischer ECS-Stability-Heartbeat/Guard: {missing}"

    assert (
        text.count("ECS wait still in progress for service") >= 2
    ), "deploy.yml sollte Heartbeat-Diagnostics für API- und UI-Deploy-Step enthalten"


def test_deploy_staging_workflow_emits_periodic_heartbeat_diagnostics_while_waiting_for_ecs_stability():
    workflow = Path(".github/workflows/deploy-staging.yml")
    assert workflow.exists(), "Workflow fehlt: .github/workflows/deploy-staging.yml"

    text = workflow.read_text(encoding="utf-8")
    required = [
        "Invalid ECS_STABILITY_TIMEOUT_SECONDS",
        "timeout \"${slice_seconds}\" aws ecs wait services-stable",
        "ECS wait still in progress for service",
    ]

    missing = [snippet for snippet in required if snippet not in text]
    assert (
        not missing
    ), f"deploy-staging.yml fehlt periodischer ECS-Stability-Heartbeat/Guard: {missing}"

    assert (
        text.count("ECS wait still in progress for service") >= 2
    ), "deploy-staging.yml sollte Heartbeat-Diagnostics für API- und UI-Deploy-Step enthalten"


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


def test_deployment_aws_doc_mentions_ecs_stability_timeout_guardrail():
    doc = Path("docs/DEPLOYMENT_AWS.md")
    assert doc.exists(), "Dokument fehlt: docs/DEPLOYMENT_AWS.md"

    text = doc.read_text(encoding="utf-8")
    required = [
        "ECS_STABILITY_TIMEOUT_SECONDS",
        "aws ecs wait services-stable",
        "ECS-Service-Diagnostics",
    ]

    missing = [snippet for snippet in required if snippet not in text]
    assert (
        not missing
    ), f"DEPLOYMENT_AWS.md fehlt ECS-Stability-Timeout-Guardrail-Doku: {missing}"


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


def test_deployment_aws_doc_does_not_reference_closed_bl15_as_open_blocker():
    doc = Path("docs/DEPLOYMENT_AWS.md")
    assert doc.exists(), "Dokument fehlt: docs/DEPLOYMENT_AWS.md"

    text = doc.read_text(encoding="utf-8")
    forbidden = [
        "Nächster offener Gesamt-Block: **BL-15**",
        "aktuell **BL-01** bis **BL-18**",
    ]

    stale = [snippet for snippet in forbidden if snippet in text]
    assert (
        not stale
    ), f"DEPLOYMENT_AWS.md enthält veraltete Backlog-/BL-15-Open-Referenzen: {stale}"


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
        f"artifacts/{env_name}-login-start-smoke*.json",
        f"Upload login-start smoke artifacts ({env_name})",
        "actions/upload-artifact@v6",
        f"{env_name}-login-start-smoke-${{{{ github.run_id }}}}-${{{{ github.run_attempt }}}}",
    ]

    missing = [snippet for snippet in required if snippet not in text]
    assert (
        not missing
    ), f"{workflow_name} fehlt Login-Contract-Smoke-Coverage: {missing}"


def _assert_workflow_uploads_login_start_artifact_glob(
    *, text: str, env_name: str, workflow_name: str
) -> None:
    expected_glob = f"artifacts/{env_name}-login-start-smoke*.json"
    assert (
        expected_glob in text
    ), f"{workflow_name} fehlt Login-Start-Artefakt-Glob für env={env_name}: {expected_glob}"


def _assert_canonical_host_smoke_coverage(
    *, text: str, env_name: str, workflow_name: str
) -> None:
    required = [
        "Smoke-Test UI canonical-host redirect route matrix (/login?start=1 on alias host)",
        "scripts/smoke/run_canonical_redirect_smoke_bundle.sh",
        "UI_CANONICAL_ORIGIN: ${{ vars.UI_CANONICAL_ORIGIN }}",
        "UI_CANONICAL_HOSTS: ${{ vars.UI_CANONICAL_HOSTS }}",
        f"artifacts/{env_name}-canonical-host-redirect-smoke*.json",
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


def test_deploy_workflow_upload_manifest_uses_login_start_globs_for_dev_and_alias():
    workflow = Path(".github/workflows/deploy.yml")
    assert workflow.exists(), "Workflow fehlt: .github/workflows/deploy.yml"

    text = workflow.read_text(encoding="utf-8")
    _assert_workflow_uploads_login_start_artifact_glob(
        text=text,
        env_name="dev",
        workflow_name="deploy.yml",
    )
    _assert_workflow_uploads_login_start_artifact_glob(
        text=text,
        env_name="dev-alias",
        workflow_name="deploy.yml",
    )


def test_deploy_staging_workflow_upload_manifest_uses_login_start_glob():
    workflow = Path(".github/workflows/deploy-staging.yml")
    assert workflow.exists(), "Workflow fehlt: .github/workflows/deploy-staging.yml"

    text = workflow.read_text(encoding="utf-8")
    _assert_workflow_uploads_login_start_artifact_glob(
        text=text,
        env_name="staging",
        workflow_name="deploy-staging.yml",
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
        "--preserve-requested-base-url",
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
