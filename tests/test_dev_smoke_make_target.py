from pathlib import Path


def test_makefile_exposes_dev_smoke_with_preflight_checks() -> None:
    makefile = Path("Makefile")
    assert makefile.exists(), "Makefile fehlt (erwartet für den einheitlichen dev-smoke Entry-Point)."

    text = makefile.read_text(encoding="utf-8")

    required_snippets = [
        ".PHONY: dev-smoke",
        "dev-smoke:",
        "check_bl334_split_smokes.sh",
        "command -v \"$$PYTHON_BIN\"",
        "command -v \"$$CURL_BIN\"",
        "exit 2",
    ]

    missing = [snippet for snippet in required_snippets if snippet not in text]
    assert not missing, f"Makefile dev-smoke Target unvollständig, fehlend: {missing}"


def test_docs_reference_make_dev_smoke_entrypoint() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    contributing = Path("CONTRIBUTING.md").read_text(encoding="utf-8")

    assert "make dev-smoke" in readme, "README.md muss den Standard-Entry-Point make dev-smoke dokumentieren."
    assert "make dev-smoke" in contributing, "CONTRIBUTING.md muss den Standard-Entry-Point make dev-smoke dokumentieren."
