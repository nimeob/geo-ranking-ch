from src.shared.gui_mvp import render_gui_mvp_html


def test_build_analyze_payload_sends_canonical_and_legacy_mode_fields() -> None:
    html = render_gui_mvp_html(app_version="test")

    assert "intelligence_mode: mode" in html
    assert "level: mode" in html
