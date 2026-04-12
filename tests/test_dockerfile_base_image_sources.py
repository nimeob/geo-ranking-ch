from pathlib import Path


EXPECTED_BASE_IMAGE = "public.ecr.aws/docker/library/python:3.12-slim"


def _first_non_empty_line(path: Path) -> str:
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line:
            return line
    raise AssertionError(f"{path} is empty")


def test_api_dockerfile_uses_public_ecr_python_base_image():
    first_line = _first_non_empty_line(Path("Dockerfile"))
    assert first_line == f"FROM {EXPECTED_BASE_IMAGE}"


def test_ui_dockerfile_uses_public_ecr_python_base_image():
    first_line = _first_non_empty_line(Path("Dockerfile.ui"))
    assert first_line == f"FROM {EXPECTED_BASE_IMAGE}"
