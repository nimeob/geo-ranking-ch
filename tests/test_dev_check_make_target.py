from pathlib import Path


def test_makefile_exposes_dev_check_target() -> None:
    makefile = Path("Makefile")
    assert (
        makefile.exists()
    ), "Makefile fehlt (erwartet für den einheitlichen dev-check Entry-Point)."

    text = makefile.read_text(encoding="utf-8")

    required_snippets = [
        ".PHONY: dev-smoke dev-check",
        "dev-check:",
        "./scripts/check_dev_quality_gate.sh",
    ]

    missing = [snippet for snippet in required_snippets if snippet not in text]
    assert not missing, f"Makefile dev-check Target unvollständig, fehlend: {missing}"


def test_docs_reference_make_dev_check_entrypoint() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    contributing = Path("CONTRIBUTING.md").read_text(encoding="utf-8")

    assert (
        "### Vor PR ausführen" in readme
    ), "README.md muss den Abschnitt 'Vor PR ausführen' enthalten."
    assert (
        "make dev-check" in readme
    ), "README.md muss den Standard-Entry-Point make dev-check dokumentieren."
    assert (
        "make dev-check" in contributing
    ), "CONTRIBUTING.md muss den Standard-Entry-Point make dev-check dokumentieren."
