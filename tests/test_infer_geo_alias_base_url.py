from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


MODULE_PATH = Path("scripts/smoke/infer_geo_alias_base_url.py")


def _load_module():
    spec = importlib.util.spec_from_file_location("infer_geo_alias_base_url", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_prefers_geo_ranking_alias_from_canonical_hosts():
    module = _load_module()

    alias_url = module.infer_geo_alias_base_url(
        service_app_base_url="https://www.dev.georanking.ch",
        canonical_origin="https://www.dev.georanking.ch",
        canonical_hosts="www.dev.georanking.ch,www.dev.geo-ranking.ch",
    )

    assert alias_url == "https://www.dev.geo-ranking.ch"


def test_infers_geo_alias_when_canonical_hosts_missing():
    module = _load_module()

    alias_url = module.infer_geo_alias_base_url(
        service_app_base_url="https://www.dev.georanking.ch",
        canonical_origin="",
        canonical_hosts="",
    )

    assert alias_url == "https://www.dev.geo-ranking.ch"


def test_preserves_scheme_from_canonical_origin_override():
    module = _load_module()

    alias_url = module.infer_geo_alias_base_url(
        service_app_base_url="https://www.dev.georanking.ch",
        canonical_origin="http://www.dev.georanking.ch",
        canonical_hosts="",
    )

    assert alias_url == "http://www.dev.geo-ranking.ch"


def test_handles_canonical_hosts_with_urls_and_ports():
    module = _load_module()

    alias_url = module.infer_geo_alias_base_url(
        service_app_base_url="https://www.dev.georanking.ch",
        canonical_origin="https://www.dev.georanking.ch",
        canonical_hosts="https://www.dev.georanking.ch:443, https://www.dev.geo-ranking.ch",
    )

    assert alias_url == "https://www.dev.geo-ranking.ch"


def test_prefers_tls_valid_alias_when_hostname_check_is_required():
    module = _load_module()
    probed: list[str] = []

    def _validator(host: str, timeout_seconds: float) -> bool:
        assert timeout_seconds == 2.5
        probed.append(host)
        return host == "www.dev.geo-ranking.ch"

    alias_url = module.infer_geo_alias_base_url(
        service_app_base_url="https://www.dev.georanking.ch",
        canonical_origin="https://www.dev.georanking.ch",
        canonical_hosts="dev.geo-ranking.ch,www.dev.geo-ranking.ch",
        require_tls_hostname_match=True,
        probe_timeout_seconds=2.5,
        tls_hostname_validator=_validator,
    )

    assert alias_url == "https://www.dev.geo-ranking.ch"
    assert probed == ["dev.geo-ranking.ch", "www.dev.geo-ranking.ch"]


def test_returns_empty_when_all_aliases_fail_tls_hostname_check():
    module = _load_module()

    alias_url = module.infer_geo_alias_base_url(
        service_app_base_url="https://www.dev.georanking.ch",
        canonical_origin="https://www.dev.georanking.ch",
        canonical_hosts="dev.geo-ranking.ch,dev.georanking.ch",
        require_tls_hostname_match=True,
        tls_hostname_validator=lambda host, timeout_seconds: False,
    )

    assert alias_url == ""


def test_returns_empty_when_no_alias_can_be_derived():
    module = _load_module()

    alias_url = module.infer_geo_alias_base_url(
        service_app_base_url="https://example.com",
        canonical_origin="",
        canonical_hosts="example.com",
    )

    assert alias_url == ""


def test_main_prints_empty_line_when_alias_missing(capsys):
    module = _load_module()

    exit_code = module.main(
        [
            "--service-app-base-url",
            "https://example.com",
            "--canonical-hosts",
            "example.com",
        ]
    )

    assert exit_code == 0
    assert capsys.readouterr().out == "\n"
