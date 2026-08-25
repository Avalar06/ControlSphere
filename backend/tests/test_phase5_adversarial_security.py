from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.security import get_password_hash
from app.models.organization import Organization
from app.models.user import User
from tests.conftest import get_token_headers


def test_cross_tenant_risk_idor_blocked(
    client: TestClient, analyst_user: User, db: Session, seeded_framework
):
    headers_org1 = get_token_headers(analyst_user)

    # Org 1 creates Risk
    res_risk = client.post(
        "/api/v1/risks",
        headers=headers_org1,
        json={"title": "Org 1 Confidential Risk", "description": "Desc"},
    )
    risk_id = res_risk.json()["id"]

    # Create Org 2 & user
    org2 = Organization(name="Competitor Corp", slug="competitor-corp-p5", is_active=True)
    db.add(org2)
    db.commit()
    db.refresh(org2)

    user_org2 = User(
        email="attacker@competitor-p5.com",
        hashed_password=get_password_hash("SecretPass123!"),
        full_name="Attacker User",
        role="GRC_ANALYST",
        is_active=True,
        organization_id=org2.id,
    )
    db.add(user_org2)
    db.commit()
    db.refresh(user_org2)

    headers_org2 = get_token_headers(user_org2)

    # 1. Org 2 tries to GET Org 1 Risk (IDOR) -> 404
    res_get = client.get(f"/api/v1/risks/{risk_id}", headers=headers_org2)
    assert res_get.status_code == 404

    # 2. Org 2 tries to PATCH Org 1 Risk -> 404
    res_patch = client.patch(
        f"/api/v1/risks/{risk_id}",
        headers=headers_org2,
        json={"title": "Attacker overwrite"},
    )
    assert res_patch.status_code == 404

    # 3. Org 2 tries to accept risk for Org 1 -> 404
    res_acc = client.post(
        f"/api/v1/risks/{risk_id}/risk-acceptance",
        headers=headers_org2,
        json={"justification": "Attacker accept"},
    )
    assert res_acc.status_code == 404


def test_cross_tenant_exception_idor_blocked(
    client: TestClient, analyst_user: User, db: Session, seeded_framework
):
    headers_org1 = get_token_headers(analyst_user)
    expiry = date.today() + timedelta(days=30)

    # Org 1 creates Exception
    res_exc = client.post(
        "/api/v1/exceptions",
        headers=headers_org1,
        json={
            "title": "Org 1 Confidential Exception",
            "description": "Desc",
            "justification": "Justification",
            "expiry_date": expiry.isoformat(),
        },
    )
    exc_id = res_exc.json()["id"]

    # Create Org 2 & user
    org2 = Organization(name="Competitor Corp Exc", slug="competitor-corp-exc", is_active=True)
    db.add(org2)
    db.commit()
    db.refresh(org2)

    user_org2 = User(
        email="attacker@competitor-exc.com",
        hashed_password=get_password_hash("SecretPass123!"),
        full_name="Attacker User",
        role="GRC_ANALYST",
        is_active=True,
        organization_id=org2.id,
    )
    db.add(user_org2)
    db.commit()
    db.refresh(user_org2)

    headers_org2 = get_token_headers(user_org2)

    # 1. Org 2 tries to GET Org 1 Exception -> 404
    res_get = client.get(f"/api/v1/exceptions/{exc_id}", headers=headers_org2)
    assert res_get.status_code == 404

    # 2. Org 2 tries to APPROVE Org 1 Exception -> 404
    res_app = client.post(
        f"/api/v1/exceptions/{exc_id}/approve",
        headers=headers_org2,
        json={"approval_notes": "Sabotage"},
    )
    assert res_app.status_code == 404


def test_foreign_and_inactive_user_assignment_blocked_on_risk_and_exception(
    client: TestClient, analyst_user: User, db: Session, seeded_framework
):
    headers_org1 = get_token_headers(analyst_user)

    # Create foreign tenant user
    org_other = Organization(name="External Org P5", slug="external-org-p5", is_active=True)
    db.add(org_other)
    db.commit()
    db.refresh(org_other)

    foreign_user = User(
        email="foreign_p5@external.com",
        hashed_password=get_password_hash("SecretPass123!"),
        full_name="Foreign User",
        role="GRC_ANALYST",
        is_active=True,
        organization_id=org_other.id,
    )
    db.add(foreign_user)

    # Create inactive user in Org 1
    inactive_user = User(
        email="inactive_p5@myorg.com",
        hashed_password=get_password_hash("SecretPass123!"),
        full_name="Inactive Employee",
        role="SECURITY_ANALYST",
        is_active=False,
        organization_id=analyst_user.organization_id,
    )
    db.add(inactive_user)
    db.commit()

    # 1. Foreign risk owner blocked
    res_risk_foreign = client.post(
        "/api/v1/risks",
        headers=headers_org1,
        json={"title": "Risk Foreign Owner", "description": "Desc", "owner_id": foreign_user.id},
    )
    assert res_risk_foreign.status_code == 400
    assert "Owner ID" in res_risk_foreign.json()["detail"]

    # 2. Inactive risk owner blocked
    res_risk_inactive = client.post(
        "/api/v1/risks",
        headers=headers_org1,
        json={"title": "Risk Inactive Owner", "description": "Desc", "owner_id": inactive_user.id},
    )
    assert res_risk_inactive.status_code == 400
    assert "inactive" in res_risk_inactive.json()["detail"].lower()

    # 3. Foreign exception reviewer blocked
    expiry = date.today() + timedelta(days=30)
    res_exc_foreign = client.post(
        "/api/v1/exceptions",
        headers=headers_org1,
        json={
            "title": "Exception Foreign Reviewer",
            "description": "Desc",
            "justification": "Justification",
            "expiry_date": expiry.isoformat(),
            "reviewer_id": foreign_user.id,
        },
    )
    assert res_exc_foreign.status_code == 400
    assert "Reviewer ID" in res_exc_foreign.json()["detail"]


def test_risk_score_tampering_authoritative_recalculation(
    client: TestClient, analyst_user: User, db: Session, seeded_framework
):
    headers = get_token_headers(analyst_user)

    # Client tries to send fake inherent_score=25, inherent_band=CRITICAL with impact=1, likelihood=1
    res_tamper = client.post(
        "/api/v1/risks",
        headers=headers,
        json={
            "title": "Tampered Risk",
            "description": "Desc",
            "inherent_impact": 1,
            "inherent_likelihood": 1,
            "inherent_score": 25,
            "inherent_band": "CRITICAL",
        },
    )
    assert res_tamper.status_code == 201
    created = res_tamper.json()
    # Backend overrides with authoritative score: 1 * 1 = 1 (LOW)
    assert created["inherent_score"] == 1
    assert created["inherent_band"] == "LOW"
    risk_id = created["id"]

    # Patch with impact=5, likelihood=5 -> recomputed to 25 (CRITICAL)
    res_patch = client.patch(
        f"/api/v1/risks/{risk_id}",
        headers=headers,
        json={"inherent_impact": 5, "inherent_likelihood": 5},
    )
    assert res_patch.status_code == 200
    patched = res_patch.json()
    assert patched["inherent_score"] == 25
    assert patched["inherent_band"] == "CRITICAL"
