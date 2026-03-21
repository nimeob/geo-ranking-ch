from __future__ import annotations

from src.api.web_service import Handler


def test_job_visible_for_owner_accepts_legacy_user_id_org_id_fields() -> None:
    job_record = {
        "user_id": "user-123",
        "org_id": "default-org",
    }

    assert Handler._job_visible_for_owner(
        job_record,
        owner_user_id="user-123",
        owner_org_id="default-org",
    )


def test_result_visible_for_owner_accepts_legacy_user_id_org_id_fields() -> None:
    result_record = {
        "user_id": "user-123",
        "org_id": "default-org",
    }

    assert Handler._result_visible_for_owner(
        result_record,
        owner_user_id="user-123",
        owner_org_id="default-org",
    )


def test_job_visible_for_owner_rejects_other_user() -> None:
    job_record = {
        "user_id": "user-abc",
        "org_id": "default-org",
    }

    assert not Handler._job_visible_for_owner(
        job_record,
        owner_user_id="user-123",
        owner_org_id="default-org",
    )
