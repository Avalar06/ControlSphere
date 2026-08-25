import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.organization import Organization
from app.models.user import User
from tests.conftest import get_token_headers


def test_cross_tenant_assessment_idor_blocked(
    client: TestClient, analyst_user: User, db: Session, seeded_framework
):
    headers_org1 = get_token_headers(analyst_user)
    controls = client.get("/api/v1/controls", headers=headers_org1).json()
    ctrl_id = controls[0]["id"]

    # Org 1 creates assessment
    res_ass = client.post(
        "/api/v1/assessments",
        headers=headers_org1,
        json={"organization_control_id": ctrl_id, "summary": "Org 1 Confidential Assessment"},
    )
    ass_id = res_ass.json()["id"]

    # Create Org 2 & user
    from app.core.security import get_password_hash
    org2 = Organization(name="Competitor Corp", slug="competitor-corp", is_active=True)
    db.add(org2)
    db.commit()
    db.refresh(org2)

    user_org2 = User(
        email="attacker@competitor.com",
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

    # 1. Org 2 tries to GET Org 1 Assessment (IDOR)
    res_get_idor = client.get(f"/api/v1/assessments/{ass_id}", headers=headers_org2)
    assert res_get_idor.status_code == 404

    # 2. Org 2 tries to UPDATE Org 1 Assessment
    res_patch_idor = client.patch(
        f"/api/v1/assessments/{ass_id}",
        headers=headers_org2,
        json={"summary": "Attacker overwrite."},
    )
    assert res_patch_idor.status_code == 404

    # 3. Org 2 tries to START Org 1 Assessment
    res_start_idor = client.post(f"/api/v1/assessments/{ass_id}/start", headers=headers_org2)
    assert res_start_idor.status_code == 404

    # 4. Org 2 tries to COMPLETE Org 1 Assessment
    res_comp_idor = client.post(
        f"/api/v1/assessments/{ass_id}/complete",
        headers=headers_org2,
        json={"conclusion": "INEFFECTIVE", "summary": "Attacker sabotaged."},
    )
    assert res_comp_idor.status_code == 404


def test_cross_tenant_finding_idor_blocked(
    client: TestClient, analyst_user: User, db: Session, seeded_framework
):
    headers_org1 = get_token_headers(analyst_user)
    controls = client.get("/api/v1/controls", headers=headers_org1).json()
    ctrl_id = controls[0]["id"]

    # Org 1 creates finding
    res_find = client.post(
        "/api/v1/findings",
        headers=headers_org1,
        json={
            "organization_control_id": ctrl_id,
            "title": "Org 1 Confidential Vulnerability",
            "description": "Sensitive zero-day details.",
            "recommendation": "Fix secret.",
            "impact": 5,
            "likelihood": 5,
        },
    )
    find_id = res_find.json()["id"]

    # Create Org 2 user
    from app.core.security import get_password_hash
    org2 = Organization(name="Competitor Corp 2", slug="competitor-corp-2", is_active=True)
    db.add(org2)
    db.commit()
    db.refresh(org2)

    user_org2 = User(
        email="hacker@competitor2.com",
        hashed_password=get_password_hash("SecretPass123!"),
        full_name="Hacker User",
        role="GRC_ANALYST",
        is_active=True,
        organization_id=org2.id,
    )
    db.add(user_org2)
    db.commit()
    db.refresh(user_org2)

    headers_org2 = get_token_headers(user_org2)

    # 1. Org 2 tries to GET Org 1 Finding
    res_get = client.get(f"/api/v1/findings/{find_id}", headers=headers_org2)
    assert res_get.status_code == 404

    # 2. Org 2 tries to UPDATE Org 1 Finding
    res_patch = client.patch(
        f"/api/v1/findings/{find_id}",
        headers=headers_org2,
        json={"title": "Hacked finding"},
    )
    assert res_patch.status_code == 404

    # 3. Org 2 tries to ACCEPT RISK for Org 1 Finding
    res_acc = client.post(
        f"/api/v1/findings/{find_id}/risk-acceptance",
        headers=headers_org2,
        json={"justification": "Attacker risk acceptance."},
    )
    assert res_acc.status_code == 404


def test_foreign_owner_assignment_blocked(
    client: TestClient, analyst_user: User, db: Session, seeded_framework
):
    headers_org1 = get_token_headers(analyst_user)
    controls = client.get("/api/v1/controls", headers=headers_org1).json()
    ctrl_id = controls[0]["id"]

    # Create foreign tenant user
    from app.core.security import get_password_hash
    org_other = Organization(name="External Org", slug="external-org", is_active=True)
    db.add(org_other)
    db.commit()
    db.refresh(org_other)

    foreign_user = User(
        email="foreign@external.com",
        hashed_password=get_password_hash("SecretPass123!"),
        full_name="Foreign User",
        role="GRC_ANALYST",
        is_active=True,
        organization_id=org_other.id,
    )
    db.add(foreign_user)
    db.commit()
    db.refresh(foreign_user)

    # Trying to assign foreign user as assessor
    res_ass_foreign = client.post(
        "/api/v1/assessments",
        headers=headers_org1,
        json={
            "organization_control_id": ctrl_id,
            "assessor_id": foreign_user.id,
            "summary": "Assessment with foreign assessor",
        },
    )
    assert res_ass_foreign.status_code == 400
    assert "Assessor ID" in res_ass_foreign.json()["detail"]

    # Trying to assign foreign user as finding owner
    res_find_foreign = client.post(
        "/api/v1/findings",
        headers=headers_org1,
        json={
            "organization_control_id": ctrl_id,
            "title": "Finding with foreign owner",
            "description": "Desc",
            "recommendation": "Rec",
            "owner_id": foreign_user.id,
        },
    )
    assert res_find_foreign.status_code == 400
    assert "Owner ID" in res_find_foreign.json()["detail"]
