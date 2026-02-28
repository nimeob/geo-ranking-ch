from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
API_DOCKERFILE = REPO_ROOT / "Dockerfile"
UI_DOCKERFILE = REPO_ROOT / "Dockerfile.ui"
API_IGNORE = REPO_ROOT / "Dockerfile.dockerignore"
UI_IGNORE = REPO_ROOT / "Dockerfile.ui.dockerignore"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_api_container_only_copies_api_plus_shared_sources() -> None:
    content = _read(API_DOCKERFILE)

    assert "COPY src/api ./src/api" in content
    assert "COPY src/shared ./src/shared" in content
    assert "COPY src/gwr_codes.py ./src/gwr_codes.py" in content
    assert "COPY src/ui ./src/ui" not in content
    assert 'CMD ["python", "-m", "src.api.web_service"]' in content


def test_ui_container_only_copies_ui_plus_shared_sources() -> None:
    content = _read(UI_DOCKERFILE)

    assert "COPY src/ui ./src/ui" in content
    assert "COPY src/shared ./src/shared" in content
    assert "COPY src/api ./src/api" not in content
    assert 'CMD ["python", "-m", "src.ui.service"]' in content


def test_dockerfile_specific_ignore_files_enforce_service_local_contexts() -> None:
    api_ignore = _read(API_IGNORE)
    ui_ignore = _read(UI_IGNORE)

    assert api_ignore.splitlines()[0].strip() == "**"
    assert "!src/api/**" in api_ignore
    assert "!src/shared/**" in api_ignore
    assert "!src/gwr_codes.py" in api_ignore
    assert "!src/ui/**" not in api_ignore

    assert ui_ignore.splitlines()[0].strip() == "**"
    assert "!src/ui/**" in ui_ignore
    assert "!src/shared/**" in ui_ignore
    assert "!src/api/**" not in ui_ignore
