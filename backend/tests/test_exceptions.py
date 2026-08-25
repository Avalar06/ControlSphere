from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User
from tests.conftest import get_token_headers


def test_exception_lifecycle_and_approval(
    client: TestClient, analyst_user: User, admin_user: User, viewer_user: User, db: Session, seeded_framework
):
    analyst_headers = get_token_headers(analyst_user)
    admin_headers = get_token_headers(admin_user)
    viewer_headers = get_token_headers(viewer_user)
    controls = client.get("/api/v1/controls", headers=analyst_headers).json()
    ctrl_id = controls[0]["id"]

    # 1. Request Exception (REQUESTED)
    expiry = date.today() + timedelta(days=90)
    res_create = client.post(
        "/api/v1/exceptions",
        headers=analyst_headers,
        json={
            "title": "Exception for Legacy Backup Agent",
            "description": "Legacy server cannot run EDR sensor without kernel panic.",
            "justification": "Air-gapped database server with no direct internet connectivity.",
            "exception_type": "CONTROL_DEVIATION",
            "linked_organization_control_id": ctrl_id,
            "expiry_date": expiry.isoformat(),
            "residual_risk_level": "MODERATE",
        },
    )
    assert res_create.status_code == 201
    exc_data = res_create.json()
    assert exc_data["status"] == "REQUESTED"
    assert exc_data["effective_status"] == "REQUESTED"
    exc_id = exc_data["id"]

    # 2. Submit for Review: REQUESTED -> UNDER_REVIEW
    res_sub = client.post(
        f"/api/v1/exceptions/{exc_id}/submit-review",
        headers=analyst_headers,
    )
    assert res_sub.status_code == 200
    assert res_sub.json()["status"] == "UNDER_REVIEW"

    # 3. Viewer cannot approve exception (requires EXCEPTION_APPROVE)
    res_viewer_app = client.post(
        f"/api/v1/exceptions/{exc_id}/approve",
        headers=viewer_headers,
        json={"approval_notes": "Viewer approves."},
    )
    assert res_viewer_app.status_code == 403

    # 4. Requester self-approval blocked (Four-Eyes governance)
    res_self_app = client.post(
        f"/api/v1/exceptions/{exc_id}/approve",
        headers=analyst_headers,
        json={"approval_notes": "I approve my own request."},
    )
    assert res_self_app.status_code == 400
    assert "Self-approval prohibited" in res_self_app.json()["detail"]

    # 5. Independent Admin approves exception: UNDER_REVIEW -> ACTIVE
    res_app = client.post(
        f"/api/v1/exceptions/{exc_id}/approve",
        headers=admin_headers,
        json={"approval_notes": "Approved with compensating network firewall rule."},
    )
    assert res_app.status_code == 200
    approved_data = res_app.json()
    assert approved_data["status"] in ["APPROVED", "ACTIVE"]
    assert approved_data["effective_status"] == "ACTIVE"
    assert approved_data["approved_at"] is not None

    # 6. Link Compensating Control
    res_link = client.post(
        f"/api/v1/exceptions/{exc_id}/compensating-controls",
        headers=analyst_headers,
        json={
            "organization_control_id": ctrl_id,
            "implementation_notes": "Strict network isolation applied on ingress switch.",
        },
    )
    assert res_link.status_code == 201

    # 7. Close Exception
    res_close = client.post(
        f"/api/v1/exceptions/{exc_id}/close",
        headers=analyst_headers,
        json={"closure_notes": "Server decommissioned."},
    )
    assert res_close.status_code == 200
    assert res_close.json()["status"] == "CLOSED"
    assert res_close.json()["effective_status"] == "CLOSED"


def test_exception_rejection_workflow(
    client: TestClient, analyst_user: User, admin_user: User, db: Session, seeded_framework
):
    analyst_headers = get_token_headers(analyst_user)
    admin_headers = get_token_headers(admin_user)
    expiry = date.today() + timedelta(days=30)

    # 1. Create exception
    res_create = client.post(
        "/api/v1/exceptions",
        headers=analyst_headers,
        json={
            "title": "Disable MFA for Shared Admin Account",
            "description": "Team wants single shared account without MFA.",
            "justification": "Convenience for weekend operations.",
            "exception_type": "ACCESS_CONTROL",
            "expiry_date": expiry.isoformat(),
        },
    )
    exc_id = res_create.json()["id"]

    # 2. Rejection without mandatory reason (< 5 chars) is rejected
    res_empty_reject = client.post(
        f"/api/v1/exceptions/{exc_id}/reject",
        headers=admin_headers,
        json={"rejection_reason": "No"},
    )
    assert res_empty_reject.status_code == 400
    assert "minimum 5 characters" in res_empty_reject.json()["detail"]

    # 3. Reject exception with valid reason
    res_reject = client.post(
        f"/api/v1/exceptions/{exc_id}/reject",
        headers=admin_headers,
        json={"rejection_reason": "Violation of fundamental security baseline. Shared accounts are strictly prohibited."},
    )
    assert res_reject.status_code == 200
    assert res_reject.json()["status"] == "REJECTED"
    assert "Shared accounts are strictly prohibited" in res_reject.json()["rejection_reason"]
