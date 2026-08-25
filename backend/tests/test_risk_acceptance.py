from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User
from tests.conftest import get_token_headers


def test_formal_risk_acceptance_workflow(
    client: TestClient, analyst_user: User, viewer_user: User, db: Session, seeded_framework
):
    analyst_headers = get_token_headers(analyst_user)
    viewer_headers = get_token_headers(viewer_user)

    # 1. Create Risk
    res_create = client.post(
        "/api/v1/risks",
        headers=analyst_headers,
        json={
            "title": "Legacy Gateway TLS 1.0 Support",
            "description": "Legacy client integration requires TLS 1.0 until Q4 retirement.",
            "risk_category": "OPERATIONAL",
            "inherent_impact": 3,
            "inherent_likelihood": 2,
        },
    )
    risk_id = res_create.json()["id"]

    # 2. Viewer cannot accept risk (requires RISK_ACCEPT)
    res_viewer_acc = client.post(
        f"/api/v1/risks/{risk_id}/risk-acceptance",
        headers=viewer_headers,
        json={"justification": "I accept this risk."},
    )
    assert res_viewer_acc.status_code == 403

    # 3. Short justification (<5 chars) rejected
    res_short = client.post(
        f"/api/v1/risks/{risk_id}/risk-acceptance",
        headers=analyst_headers,
        json={"justification": "Ok"},
    )
    assert res_short.status_code == 422

    # 4. Analyst accepts risk
    expiry = date.today() + timedelta(days=60)
    res_accept = client.post(
        f"/api/v1/risks/{risk_id}/risk-acceptance",
        headers=analyst_headers,
        json={
            "justification": "Business critical partner contract requires TLS 1.0 endpoint until December 2026 cutover. Segmented on dedicated proxy.",
            "expiry_date": expiry.isoformat(),
        },
    )
    assert res_accept.status_code == 200
    data = res_accept.json()
    assert data["status"] == "ACCEPTED"
    assert data["treatment_strategy"] == "ACCEPT"
    assert data["risk_accepted_at"] is not None
    assert data["risk_accepted_by_id"] == analyst_user.id
    assert "Business critical partner" in data["risk_acceptance_justification"]
    assert data["risk_acceptance_expiry"] == expiry.isoformat()

    # 5. Accepted risk can be closed
    res_close = client.post(
        f"/api/v1/risks/{risk_id}/status",
        headers=analyst_headers,
        json={"status": "CLOSED", "notes": "Legacy client sunset complete."},
    )
    assert res_close.status_code == 200
    assert res_close.json()["status"] == "CLOSED"
