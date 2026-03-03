from __future__ import annotations

from types import SimpleNamespace

from src.api.web_service import _resolve_request_owner_user_id


def test_resolve_owner_user_id_prefers_phase1_user() -> None:
    phase1_user = SimpleNamespace(user_id="phase1-user-123")
    oidc_claims = {"sub": "oidc-sub-abc"}

    owner = _resolve_request_owner_user_id(
        phase1_user=phase1_user,
        oidc_claims=oidc_claims,
    )

    assert owner == "phase1-user-123"


def test_resolve_owner_user_id_falls_back_to_oidc_sub() -> None:
    owner = _resolve_request_owner_user_id(
        phase1_user=None,
        oidc_claims={"sub": "oidc-sub-abc"},
    )

    assert owner == "oidc-sub-abc"


def test_resolve_owner_user_id_returns_none_without_auth_identity() -> None:
    owner = _resolve_request_owner_user_id(
        phase1_user=None,
        oidc_claims=None,
    )

    assert owner is None
