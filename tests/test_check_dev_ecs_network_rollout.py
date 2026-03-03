from __future__ import annotations

from scripts.check_dev_ecs_network_rollout import evaluate_rollout


def _service_fixture(*, subnets: list[str], assign_public_ip: str, tg_arns: list[str], rollout_state: str) -> dict:
    return {
        "serviceArn": "arn:aws:ecs:eu-central-1:123456789012:service/swisstopo-dev/swisstopo-dev-api",
        "taskDefinition": "arn:aws:ecs:eu-central-1:123456789012:task-definition/swisstopo-dev-api:1",
        "desiredCount": 1,
        "runningCount": 1,
        "networkConfiguration": {
            "awsvpcConfiguration": {
                "subnets": subnets,
                "securityGroups": ["sg-abc"],
                "assignPublicIp": assign_public_ip,
            }
        },
        "loadBalancers": [
            {"targetGroupArn": arn, "containerName": "api", "containerPort": 8080}
            for arn in tg_arns
        ],
        "deployments": [
            {
                "id": "ecs-svc/123",
                "status": "PRIMARY",
                "rolloutState": rollout_state,
                "rolloutStateReason": "reason",
                "runningCount": 1,
                "pendingCount": 0,
            }
        ],
    }


def test_evaluate_rollout_passes_with_expected_private_state() -> None:
    service = _service_fixture(
        subnets=["subnet-04d5ddec3c5b06d7a", "subnet-0cd8553a1fedbf183"],
        assign_public_ip="DISABLED",
        tg_arns=["arn:aws:elasticloadbalancing:eu-central-1:123:targetgroup/swisstopo-dev-vpc-api-tg/abc"],
        rollout_state="COMPLETED",
    )

    result = evaluate_rollout(
        service,
        expected_subnets=["subnet-0cd8553a1fedbf183", "subnet-04d5ddec3c5b06d7a"],
        expected_assign_public_ip="DISABLED",
        expected_target_group_substring="targetgroup/swisstopo-dev-vpc-api-tg/",
    )

    assert result["ok"] is True
    assert all(result["checks"].values())


def test_evaluate_rollout_fails_for_public_ip_and_wrong_target_group() -> None:
    service = _service_fixture(
        subnets=["subnet-03651caf25115a6c1", "subnet-00901e503e078e7c9"],
        assign_public_ip="ENABLED",
        tg_arns=["arn:aws:elasticloadbalancing:eu-central-1:123:targetgroup/swisstopo-dev-api-tg/xyz"],
        rollout_state="IN_PROGRESS",
    )

    result = evaluate_rollout(
        service,
        expected_subnets=["subnet-0cd8553a1fedbf183", "subnet-04d5ddec3c5b06d7a"],
        expected_assign_public_ip="DISABLED",
        expected_target_group_substring="targetgroup/swisstopo-dev-vpc-api-tg/",
    )

    assert result["ok"] is False
    assert result["checks"]["subnets_match_expected"] is False
    assert result["checks"]["assign_public_ip_matches"] is False
    assert result["checks"]["primary_rollout_completed"] is False
    assert result["checks"]["expected_target_group_attached"] is False
