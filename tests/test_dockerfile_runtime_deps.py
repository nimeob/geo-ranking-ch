from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = REPO_ROOT / "Dockerfile"


def test_dockerfile_installs_curl_for_ecs_container_healthcheck() -> None:
    """Regression-Guard: ECS task definition uses `curl` in container healthCheck command."""
    content = DOCKERFILE.read_text(encoding="utf-8")

    # Accept variants like:
    #   apt-get install -y --no-install-recommends curl
    #   apt-get install curl -y
    assert re.search(r"apt-get\s+install[^\n]*\bcurl\b", content), (
        "Dockerfile muss curl installieren, da die ECS container healthCheck-"
        "Command `curl -f http://localhost:8080/health || exit 1` verwendet."
    )
