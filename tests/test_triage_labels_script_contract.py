from pathlib import Path


def test_triage_labels_uses_gha_wrapper_and_single_list_fetch() -> None:
    script = Path("scripts/triage_labels.sh")
    content = script.read_text(encoding="utf-8")

    assert 'GHA_BIN="${SCRIPT_DIR}/gha"' in content
    assert '--limit "$LIMIT" --json number,title,labels' in content
    assert 'bash ./scripts/gh_app_token.sh' not in content
    assert 'gh issue view' not in content
