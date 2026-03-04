import json
from pathlib import Path


def test_package_json_exposes_dev_smoke_entrypoint() -> None:
    package_json = json.loads(Path("package.json").read_text(encoding="utf-8"))
    scripts = package_json.get("scripts", {})

    assert (
        scripts.get("dev:smoke") == "./scripts/run_dev_smoke_bundle.sh"
    ), "package.json muss den DX-Entrypoint `npm run dev:smoke` auf das Bundle-Script mappen."


def test_dev_smoke_bundle_script_includes_required_checks_and_summary() -> None:
    script = Path("scripts/run_dev_smoke_bundle.sh")
    assert script.exists(), "run_dev_smoke_bundle.sh fehlt."

    text = script.read_text(encoding="utf-8")

    required_snippets = [
        'run_step "lint" run_lint',
        'run_step "typecheck" run_typecheck',
        'run_step "smoke" run_smoke_subset',
        "check_bl334_split_smokes.sh",
        "compileall -q",
        "[dev:smoke] summary",
        "exit 1",
    ]

    missing = [snippet for snippet in required_snippets if snippet not in text]
    assert not missing, f"dev:smoke-Bundle unvollständig, fehlend: {missing}"


def test_docs_reference_npm_dev_smoke_bundle() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    contributing = Path("CONTRIBUTING.md").read_text(encoding="utf-8")

    assert (
        "npm run dev:smoke" in readme
    ), "README.md muss den DX-Entrypoint `npm run dev:smoke` erwähnen."
    assert (
        "npm run dev:smoke" in contributing
    ), "CONTRIBUTING.md muss den DX-Entrypoint `npm run dev:smoke` erwähnen."
