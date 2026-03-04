from pathlib import Path


def test_deploy_version_trace_runbook_contains_required_checklist():
    doc = Path("docs/testing/DEPLOY_VERSION_TRACE_DEBUG_RUNBOOK.md")
    assert doc.exists(), "Runbook fehlt: docs/testing/DEPLOY_VERSION_TRACE_DEBUG_RUNBOOK.md"

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
    required = [
        "Post-deploy verification (version + trace-debug)",
        "TRACE_DEBUG_EXPECT_ENABLED",
        "python3 scripts/check_deploy_version_trace.py",
        "DEPLOY_VERIFY_OUTPUT_JSON",
    ]

    missing = [snippet for snippet in required if snippet not in text]
    assert not missing, f"deploy.yml fehlt Post-Deploy-Verifikation: {missing}"


def test_deploy_workflow_guards_against_container_name_mismatches():
    workflow = Path(".github/workflows/deploy.yml")
    assert workflow.exists(), "Workflow fehlt: .github/workflows/deploy.yml"

    text = workflow.read_text(encoding="utf-8")
    required = [
        "Container '$container' not found for service '$service'. Fallback to single taskdef container",
        "Container '$container' not found for service '$service'. Available containers",
        "Taskdef update failed for service '$service' container",
    ]

    missing = [snippet for snippet in required if snippet not in text]
    assert not missing, f"deploy.yml fehlt Container-Mismatch-Guardrail: {missing}"


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

    assert text.index("Validate required deploy environment keys (vars + secrets)") < text.index(
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
    assert not missing, f"DEPLOYMENT_AWS.md fehlt Container-Auflösungs-Hinweis: {missing}"


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
    assert not missing, f"DEPLOYMENT_AWS.md fehlt Pflicht-Secret-Dokumentation: {missing}"


def test_deploy_workflow_uses_deploy_gate_runner_with_rollback_snapshot():
    workflow = Path(".github/workflows/deploy.yml")
    assert workflow.exists(), "Workflow fehlt: .github/workflows/deploy.yml"

    text = workflow.read_text(encoding="utf-8")
    required = [
        "Snapshot pre-deploy stable task definitions (rollback hint)",
        "steps.rollback_snapshot.outputs.api_previous_taskdef",
        "steps.rollback_snapshot.outputs.ui_previous_taskdef",
        "DEPLOY_GATE_ROLLBACK_MODE",
        "./scripts/run_deploy_gate.sh",
    ]

    missing = [snippet for snippet in required if snippet not in text]
    assert not missing, f"deploy.yml fehlt Deploy-Gate-Rollback-Verdrahtung: {missing}"


def test_deploy_workflow_wires_database_reachability_gate_inputs():
    workflow = Path(".github/workflows/deploy.yml")
    assert workflow.exists(), "Workflow fehlt: .github/workflows/deploy.yml"

    text = workflow.read_text(encoding="utf-8")
    required = [
        "Deploy gate: API /health + GUI /gui + DB reachability",
        "SERVICE_DB_HEALTH_DETAILS_URL",
        "DEPLOY_GATE_DB_DETAILS_URL",
        "DB_DETAILS_URL=\"${SERVICE_API_BASE_URL%/}/health/details\"",
    ]

    missing = [snippet for snippet in required if snippet not in text]
    assert not missing, f"deploy.yml fehlt DB-Reachability-Gate-Verdrahtung: {missing}"


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
    assert not missing, f"DEPLOYMENT_AWS.md fehlt DB-Reachability-Gate-Dokumentation: {missing}"
