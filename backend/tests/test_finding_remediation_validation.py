from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User
from tests.conftest import get_token_headers


def test_finding_remediation_validation_workflow_pass_and_close(
    client: TestClient, analyst_user: User, db: Session, seeded_framework
):
    headers = get_token_headers(analyst_user)
    controls = client.get("/api/v1/controls", headers=headers).json()
    ctrl_id = controls[0]["id"]

    # 1. Create Finding (OPEN)
    res_create = client.post(
        "/api/v1/findings",
        headers=headers,
        json={
            "organization_control_id": ctrl_id,
            "title": "Weak Session Timeout",
            "description": "Admin session timeout is set to 24 hours.",
            "finding_type": "CONTROL_GAP",
            "severity": "MEDIUM",
            "impact": 3,
            "likelihood": 2,
            "recommendation": "Reduce session timeout to 15 minutes of inactivity.",
        },
    )
    assert res_create.status_code == 201
    f_id = res_create.json()["id"]

    # 2. Transition to IN_REMEDIATION
    res_in_rem = client.post(
        f"/api/v1/findings/{f_id}/status",
        headers=headers,
        json={"status": "IN_REMEDIATION", "notes": "Configuring auth service idle timeout."},
    )
    assert res_in_rem.status_code == 200
    assert res_in_rem.json()["status"] == "IN_REMEDIATION"

    # Cannot jump directly to RESOLVED without validation endpoint
    res_jump = client.post(
        f"/api/v1/findings/{f_id}/status",
        headers=headers,
        json={"status": "RESOLVED"},
    )
    assert res_jump.status_code == 400

    # 3. Submit for PENDING_VALIDATION with resolution
    res_val_sub = client.post(
        f"/api/v1/findings/{f_id}/status",
        headers=headers,
        json={
            "status": "PENDING_VALIDATION",
            "resolution": "Updated application.yaml `session.max_idle_minutes: 15` and deployed to staging.",
            "notes": "Ready for security verification.",
        },
    )
    assert res_val_sub.status_code == 200
    assert res_val_sub.json()["status"] == "PENDING_VALIDATION"

    # 4. Authoritative Validation: PASS
    res_val_pass = client.post(
        f"/api/v1/findings/{f_id}/validate",
        headers=headers,
        json={
            "is_valid": True,
            "validation_notes": "Verified session expires after 15 minutes idle in staging.",
        },
    )
    assert res_val_pass.status_code == 200
    assert res_val_pass.json()["status"] == "RESOLVED"
    assert res_val_pass.json()["resolved_at"] is not None

    # 5. Close Finding
    res_close = client.post(
        f"/api/v1/findings/{f_id}/status",
        headers=headers,
        json={"status": "CLOSED", "notes": "Closed following staging validation."},
    )
    assert res_close.status_code == 200
    assert res_close.json()["status"] == "CLOSED"
    assert res_close.json()["closed_at"] is not None

    # Closed finding cannot be modified
    res_edit_closed = client.patch(
        f"/api/v1/findings/{f_id}",
        headers=headers,
        json={"title": "Trying to edit closed finding"},
    )
    assert res_edit_closed.status_code == 400


def test_finding_validation_failure_returns_to_in_remediation(
    client: TestClient, analyst_user: User, db: Session, seeded_framework
):
    headers = get_token_headers(analyst_user)
    controls = client.get("/api/v1/controls", headers=headers).json()
    ctrl_id = controls[0]["id"]

    # 1. Create and submit finding for validation
    res_create = client.post(
        "/api/v1/findings",
        headers=headers,
        json={
            "organization_control_id": ctrl_id,
            "title": "Hardcoded API Key in frontend bundle",
            "description": "Found dev API key in JS source map.",
            "finding_type": "TECHNICAL_GAP",
            "severity": "HIGH",
            "impact": 4,
            "likelihood": 3,
            "recommendation": "Remove key and invalidate in provider portal.",
        },
    )
    f_id = res_create.json()["id"]

    client.post(
        f"/api/v1/findings/{f_id}/status",
        headers=headers,
        json={"status": "IN_REMEDIATION"},
    )
    client.post(
        f"/api/v1/findings/{f_id}/status",
        headers=headers,
        json={"status": "PENDING_VALIDATION", "resolution": "Removed from source map."},
    )

    # 2. Authoritative Validation: FAIL (key was not rotated)
    res_val_fail = client.post(
        f"/api/v1/findings/{f_id}/validate",
        headers=headers,
        json={
            "is_valid": False,
            "validation_notes": "Key removed from bundle, but old key is still active in Stripe dashboard.",
        },
    )
    assert res_val_fail.status_code == 200
    assert res_val_fail.json()["status"] == "IN_REMEDIATION"


def test_risk_acceptance_branch(
    client: TestClient, analyst_user: User, viewer_user: User, db: Session, seeded_framework
):
    headers = get_token_headers(analyst_user)
    viewer_headers = get_token_headers(viewer_user)
    controls = client.get("/api/v1/controls", headers=headers).json()
    ctrl_id = controls[0]["id"]

    # 1. Create Finding
    res_create = client.post(
        "/api/v1/findings",
        headers=headers,
        json={
            "organization_control_id": ctrl_id,
            "title": "Legacy System Operating System Support",
            "description": "Legacy mainframe runs older OS release until Q4 migration.",
            "finding_type": "TECHNICAL_GAP",
            "severity": "MEDIUM",
            "impact": 3,
            "likelihood": 2,
            "recommendation": "Migrate to cloud-native database.",
        },
    )
    f_id = res_create.json()["id"]

    # 2. Viewer cannot perform risk acceptance (requires RISK_MANAGE)
    res_viewer_acc = client.post(
        f"/api/v1/findings/{f_id}/risk-acceptance",
        headers=viewer_headers,
        json={
            "justification": "I accept this risk.",
            "expiry_date": (date.today() + timedelta(days=90)).isoformat(),
        },
    )
    assert res_viewer_acc.status_code == 403

    # 3. Analyst (with RISK_MANAGE) accepts risk with justification and expiry date
    res_accept = client.post(
        f"/api/v1/findings/{f_id}/risk-acceptance",
        headers=headers,
        json={
            "justification": "Mainframe is isolated in air-gapped VLAN with full network packet capture. Migration planned for November 2026.",
            "expiry_date": (date.today() + timedelta(days=90)).isoformat(),
        },
    )
    assert res_accept.status_code == 200
    acc_data = res_accept.json()
    assert acc_data["status"] == "ACCEPTED_RISK"
    assert acc_data["risk_accepted_at"] is not None
    assert "Mainframe is isolated" in acc_data["risk_acceptance_justification"]
