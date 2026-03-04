from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path("scripts/validate_required_deploy_env.py")


def _load_module():
    spec = importlib.util.spec_from_file_location("validate_required_deploy_env", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _base_env() -> dict[str, str]:
    return {
        "ECS_CLUSTER": "swisstopo-dev",
        "ECS_API_SERVICE": "swisstopo-dev-api",
        "ECS_UI_SERVICE": "swisstopo-dev-ui",
        "ECS_API_CONTAINER_NAME": "api",
        "ECS_UI_CONTAINER_NAME": "ui",
        "ECR_API_REPOSITORY": "swisstopo-dev-api",
        "ECR_UI_REPOSITORY": "swisstopo-dev-ui",
        "SERVICE_APP_BASE_URL": "https://app.dev.example",
        "SERVICE_API_AUTH_TOKEN": "token",
        "SERVICE_API_BASE_URL": "https://api.dev.example",
        "SERVICE_HEALTH_URL": "",
    }


def test_collect_missing_keys_passes_with_required_values():
    module = _load_module()

    missing = module.collect_missing_keys(_base_env())
    assert missing == []


def test_collect_missing_keys_reports_all_missing_with_auth_and_urls():
    module = _load_module()
    env = _base_env()
    env["ECS_CLUSTER"] = ""
    env["SERVICE_API_AUTH_TOKEN"] = "   "
    env["SERVICE_API_BASE_URL"] = ""
    env["SERVICE_HEALTH_URL"] = "   "

    missing_names = [entry.name for entry in module.collect_missing_keys(env)]

    assert "ECS_CLUSTER" in missing_names
    assert "SERVICE_API_AUTH_TOKEN" in missing_names
    assert "SERVICE_API_BASE_URL or SERVICE_HEALTH_URL" in missing_names


def test_collect_missing_keys_accepts_health_url_without_api_base_url():
    module = _load_module()
    env = _base_env()
    env["SERVICE_API_BASE_URL"] = ""
    env["SERVICE_HEALTH_URL"] = "https://api.dev.example/health"

    missing_names = [entry.name for entry in module.collect_missing_keys(env)]
    assert "SERVICE_API_BASE_URL or SERVICE_HEALTH_URL" not in missing_names


def test_run_returns_non_zero_and_prints_fix_hints(capsys):
    module = _load_module()
    env = _base_env()
    env["ECR_UI_REPOSITORY"] = ""

    rc = module.run(env)
    captured = capsys.readouterr()

    assert rc == 1
    assert "Deploy preflight failed" in captured.out
    assert "ECR_UI_REPOSITORY" in captured.out
    assert "Fix hint" in captured.out
