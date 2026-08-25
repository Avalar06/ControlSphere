from datetime import date, timedelta
import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User
from tests.conftest import get_token_headers


def test_phase4_complete_audit_trail(
    client: TestClient, analyst_user: User, auditor_user: User, db: Session, seeded_framework
):
    headers = get_token_headers(analyst_user)
    auditor_headers = get_token_headers(auditor_user)
    controls = client.get("/api/v1/controls", headers=headers).json()
    ctrl_id = controls[0]["id"]

    # 1. Assessment Creation & Completion Events
    res_ass = client.post(
        "/api/v1/assessments",
        headers=headers,
        json={"organization_control_id": ctrl_id, "summary": "Audit test assessment."},
    )
    ass_id = res_ass.json()["id"]

    client.post(f"/api/v1/assessments/{ass_id}/start", headers=headers)
    client.post(
        f"/api/v1/assessments/{ass_id}/complete",
        headers=headers,
        json={"conclusion": "PARTIALLY_EFFECTIVE", "summary": "Completed with partial gaps."},
    )

    # 2. Finding Creation, Status Transition, Validation, and Acceptance Events
    res_find = client.post(
        "/api/v1/findings",
        headers=headers,
        json={
            "organization_control_id": ctrl_id,
            "title": "Audit Finding Test",
            "description": "Gap found.",
            "recommendation": "Fix it.",
            "impact": 3,
            "likelihood": 3,
        },
    )
    find_id = res_find.json()["id"]

    client.post(
        f"/api/v1/findings/{find_id}/status",
        headers=headers,
        json={"status": "IN_REMEDIATION", "notes": "Working on it."},
    )

    client.post(
        f"/api/v1/findings/{find_id}/status",
        headers=headers,
        json={"status": "PENDING_VALIDATION", "resolution": "Applied fix."},
    )

    client.post(
        f"/api/v1/findings/{find_id}/validate",
        headers=headers,
        json={"is_valid": True, "validation_notes": "Fix confirmed."},
    )

    client.post(
        f"/api/v1/findings/{find_id}/status",
        headers=headers,
        json={"status": "CLOSED", "notes": "Closing ticket."},
    )

    # 3. Auditor reads Audit Logs and verifies generated actions
    res_logs = client.get("/api/v1/audit-logs", headers=auditor_headers)
    assert res_logs.status_code == 200
    logs = res_logs.json()

    actions = [l["action"] for l in logs]
    assert "assessment.create" in actions
    assert "assessment.start" in actions
    assert "assessment.complete" in actions
    assert "finding.create" in actions
    assert "finding.status.change" in actions
    assert "finding.resolve" in actions
    assert "finding.close" in actions
