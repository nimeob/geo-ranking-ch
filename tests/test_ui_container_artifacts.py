from pathlib import Path
import json
import re


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE_UI = REPO_ROOT / "Dockerfile.ui"
TASKDEF_UI = REPO_ROOT / "infra" / "ecs" / "taskdef.swisstopo-dev-ui.json"


def test_ui_dockerfile_defines_build_args_and_runtime_env() -> None:
    content = DOCKERFILE_UI.read_text(encoding="utf-8")

    assert "ARG UI_PORT=8080" in content
    assert "ARG APP_VERSION=dev" in content
    assert "ARG UI_API_BASE_URL=" in content

    assert re.search(r"ENV[\s\S]*PORT=\$\{UI_PORT\}", content)
    assert re.search(r"ENV[\s\S]*APP_VERSION=\$\{APP_VERSION\}", content)
    assert re.search(r"ENV[\s\S]*UI_API_BASE_URL=\$\{UI_API_BASE_URL\}", content)

    assert re.search(r"apt-get\s+install[^\n]*\bcurl\b", content)
    assert 'CMD ["python", "-m", "src.ui_service"]' in content


def test_ui_task_definition_template_exists_with_healthcheck_and_ui_repo() -> None:
    payload = json.loads(TASKDEF_UI.read_text(encoding="utf-8"))

    assert payload["family"] == "swisstopo-dev-ui"
    assert payload["requiresCompatibilities"] == ["FARGATE"]
    assert payload["containerDefinitions"], "containerDefinitions darf nicht leer sein"

    container = payload["containerDefinitions"][0]
    assert container["name"] == "swisstopo-dev-ui"
    assert "swisstopo-dev-ui" in container["image"]
    assert container["healthCheck"]["command"][1] == "curl -fsS http://localhost:8080/healthz || exit 1"

    env = {item["name"]: item["value"] for item in container.get("environment", [])}
    assert "APP_VERSION" in env
    assert "UI_API_BASE_URL" in env
