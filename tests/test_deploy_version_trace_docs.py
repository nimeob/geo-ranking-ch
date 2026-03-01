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
