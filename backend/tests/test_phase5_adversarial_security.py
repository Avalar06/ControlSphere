from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.security import get_password_hash
from app.models.control import OrganizationControl
from app.models.finding import Finding, FindingStatusEnum, FindingTypeEnum
from app.models.organization import Organization
from app.models.policy import Policy, PolicyStatusEnum
from app.models.risk import Risk, RiskCategoryEnum, RiskSourceEnum, RiskStatusEnum, RiskTreatmentStrategyEnum
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


def test_cross_tenant_idor_in_exception_update_patch(
    client: TestClient, analyst_user: User, db: Session, seeded_framework
):
    headers_org1 = get_token_headers(analyst_user)
    expiry = date.today() + timedelta(days=45)

    # Org 1 creates Exception
    res_exc = client.post(
        "/api/v1/exceptions",
        headers=headers_org1,
        json={
            "title": "Org 1 Exception For Update Test",
            "description": "Desc",
            "justification": "Valid justification",
            "expiry_date": expiry.isoformat(),
        },
    )
    exc_id = res_exc.json()["id"]

    # Create Org 2 and create control & policy in Org 2
    org2 = Organization(name="Target Corp Exc IDOR", slug="target-corp-exc-idor", is_active=True)
    db.add(org2)
    db.commit()
    db.refresh(org2)

    # Org 2 Control
    ctrl_org2 = OrganizationControl(
        organization_id=org2.id,
        subcategory_id=1,
        status="IMPLEMENTED",
    )
    db.add(ctrl_org2)

    # Org 2 Policy
    policy_org2 = Policy(
        organization_id=org2.id,
        title="Org 2 Secret Policy",
        status=PolicyStatusEnum.PUBLISHED,
    )
    db.add(policy_org2)
    db.commit()

    # Attempt to inject Org 2 control into Org 1 Exception via PATCH
    res_patch_ctrl = client.patch(
        f"/api/v1/exceptions/{exc_id}",
        headers=headers_org1,
        json={"linked_organization_control_id": ctrl_org2.id},
    )
    assert res_patch_ctrl.status_code == 400
    assert "not found in your organization" in res_patch_ctrl.json()["detail"]

    # Attempt to inject Org 2 policy into Org 1 Exception via PATCH
    res_patch_pol = client.patch(
        f"/api/v1/exceptions/{exc_id}",
        headers=headers_org1,
        json={"linked_policy_id": policy_org2.id},
    )
    assert res_patch_pol.status_code == 400
    assert "not found in your organization" in res_patch_pol.json()["detail"]


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


def test_closed_exception_immutability_on_compensating_controls(
    client: TestClient, analyst_user: User, db: Session, seeded_framework
):
    headers = get_token_headers(analyst_user)
    expiry = date.today() + timedelta(days=30)

    # 1. Create and close exception
    res_create = client.post(
        "/api/v1/exceptions",
        headers=headers,
        json={
            "title": "Exception for Immutability Test",
            "description": "Desc",
            "justification": "Justification",
            "expiry_date": expiry.isoformat(),
        },
    )
    exc_id = res_create.json()["id"]

    # Close exception
    res_close = client.post(
        f"/api/v1/exceptions/{exc_id}/close",
        headers=headers,
        json={"closure_notes": "Decommissioned."},
    )
    assert res_close.status_code == 200

    # Get a control ID
    controls = client.get("/api/v1/controls", headers=headers).json()
    ctrl_id = controls[0]["id"]

    # 2. Attempt to add compensating control on closed exception -> 400
    res_link = client.post(
        f"/api/v1/exceptions/{exc_id}/compensating-controls",
        headers=headers,
        json={"organization_control_id": ctrl_id},
    )
    assert res_link.status_code == 400
    assert "CLOSED" in res_link.json()["detail"]

    # 3. Attempt to modify closed exception via PATCH -> 400
    res_patch = client.patch(
        f"/api/v1/exceptions/{exc_id}",
        headers=headers,
        json={"title": "Modified Closed Exception"},
    )
    assert res_patch.status_code == 400
    assert "CLOSED" in res_patch.json()["detail"]


def test_closed_risk_immutability_on_control_and_finding_links(
    client: TestClient, analyst_user: User, db: Session, seeded_framework
):
    headers = get_token_headers(analyst_user)

    # 1. Create Risk
    res_risk = client.post(
        "/api/v1/risks",
        headers=headers,
        json={"title": "Risk for Closed Immutability", "description": "Desc"},
    )
    risk_id = res_risk.json()["id"]

    # Transition to ASSESSED -> TREATMENT_PLANNED -> MITIGATING -> MONITORING -> CLOSED
    client.post(f"/api/v1/risks/{risk_id}/status", headers=headers, json={"status": "ASSESSED"})
    client.post(f"/api/v1/risks/{risk_id}/status", headers=headers, json={"status": "TREATMENT_PLANNED"})
    client.post(f"/api/v1/risks/{risk_id}/status", headers=headers, json={"status": "MITIGATING"})
    client.post(f"/api/v1/risks/{risk_id}/status", headers=headers, json={"status": "MONITORING"})
    res_close = client.post(f"/api/v1/risks/{risk_id}/status", headers=headers, json={"status": "CLOSED"})
    assert res_close.status_code == 200

    # 2. Attempt to link control to closed risk -> 400
    controls = client.get("/api/v1/controls", headers=headers).json()
    ctrl_id = controls[0]["id"]
    res_link_ctrl = client.post(
        f"/api/v1/risks/{risk_id}/controls",
        headers=headers,
        json={"organization_control_id": ctrl_id},
    )
    assert res_link_ctrl.status_code == 400
    assert "closed risk" in res_link_ctrl.json()["detail"].lower()

    # 3. Attempt to link finding to closed risk -> 400
    res_link_fnd = client.post(
        f"/api/v1/risks/{risk_id}/findings",
        headers=headers,
        json={"finding_id": 1},
    )
    assert res_link_fnd.status_code == 400
    assert "closed risk" in res_link_fnd.json()["detail"].lower()


def test_exception_validity_window_validation(
    client: TestClient, analyst_user: User, db: Session, seeded_framework
):
    headers = get_token_headers(analyst_user)

    # 1. Expiration in the past -> rejected
    past_date = date.today() - timedelta(days=5)
    res_past = client.post(
        "/api/v1/exceptions",
        headers=headers,
        json={
            "title": "Invalid Past Expiry Exception",
            "description": "Desc",
            "justification": "Valid justification text",
            "expiry_date": past_date.isoformat(),
        },
    )
    assert res_past.status_code == 400
    assert "past" in res_past.json()["detail"].lower()

    # 2. Expiration before effective date -> rejected
    eff_date = date.today() + timedelta(days=10)
    exp_date = date.today() + timedelta(days=5)
    res_inv_dates = client.post(
        "/api/v1/exceptions",
        headers=headers,
        json={
            "title": "Invalid Inverted Dates Exception",
            "description": "Desc",
            "justification": "Valid justification text",
            "effective_date": eff_date.isoformat(),
            "expiry_date": exp_date.isoformat(),
        },
    )
    assert res_inv_dates.status_code == 400
    assert "strictly after" in res_inv_dates.json()["detail"].lower()


def test_active_heatmap_excludes_closed_risks(
    client: TestClient, analyst_user: User, db: Session, seeded_framework
):
    headers = get_token_headers(analyst_user)

    # Initial heatmap count sum
    res_hm1 = client.get("/api/v1/risks/heatmap", headers=headers)
    assert res_hm1.status_code == 200
    initial_count = sum(c["count"] for c in res_hm1.json())

    # Create a risk: Likelihood=5, Impact=5 (Cell 5,5 -> CRITICAL, Score 25)
    res_risk = client.post(
        "/api/v1/risks",
        headers=headers,
        json={
            "title": "Active Heatmap Test Risk",
            "description": "Desc",
            "inherent_impact": 5,
            "inherent_likelihood": 5,
        },
    )
    risk_id = res_risk.json()["id"]

    # Heatmap count should increase by 1
    res_hm2 = client.get("/api/v1/risks/heatmap", headers=headers)
    new_count = sum(c["count"] for c in res_hm2.json())
    assert new_count == initial_count + 1

    # Transition risk to CLOSED
    client.post(f"/api/v1/risks/{risk_id}/status", headers=headers, json={"status": "ASSESSED"})
    client.post(f"/api/v1/risks/{risk_id}/status", headers=headers, json={"status": "TREATMENT_PLANNED"})
    client.post(f"/api/v1/risks/{risk_id}/status", headers=headers, json={"status": "MITIGATING"})
    client.post(f"/api/v1/risks/{risk_id}/status", headers=headers, json={"status": "MONITORING"})
    client.post(f"/api/v1/risks/{risk_id}/status", headers=headers, json={"status": "CLOSED"})

    # Heatmap count should return to initial_count (closed risk excluded)
    res_hm3 = client.get("/api/v1/risks/heatmap", headers=headers)
    closed_hm_count = sum(c["count"] for c in res_hm3.json())
    assert closed_hm_count == initial_count


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
