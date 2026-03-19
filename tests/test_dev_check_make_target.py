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
    assert (
        "check_bl31_service_boundaries.py --src-dir src" in readme
    ), "README.md muss den Boundary-Guard im dev-check Ablauf dokumentieren."
    assert (
        "check_bl31_service_boundaries.py --src-dir src" in contributing
    ), "CONTRIBUTING.md muss den Boundary-Guard im dev-check Ablauf dokumentieren."


def test_dev_check_script_runs_boundary_guard_before_compileall() -> None:
    script = Path("scripts/check_dev_quality_gate.sh").read_text(encoding="utf-8")

    boundary_snippet = "scripts/check_bl31_service_boundaries.py --src-dir src"
    compileall_snippet = "-m compileall -q ${TYPECHECK_TARGETS}"

    assert (
        boundary_snippet in script
    ), "dev-check Script muss den Boundary-Guard ausführen."
    assert (
        compileall_snippet in script
    ), "dev-check Script muss compileall weiter ausführen."
    assert script.index(boundary_snippet) < script.index(
        compileall_snippet
    ), "Boundary-Guard muss vor compileall laufen, damit Architekturfehler früh fail-closed auffallen."
