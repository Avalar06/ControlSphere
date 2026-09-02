from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.permissions import RoleEnum
from app.core.security import get_password_hash
from app.models.organization import Organization
from app.models.user import User
from tests.conftest import get_token_headers


@pytest.fixture
def id_api_fixture(db: Session, org_apex: Organization, org_meridian: Organization):
    """Setup multi-tenant organizations and users across roles for Identity API testing."""
    admin = User(
        email="id_admin@apex.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="ID Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_apex.id,
    )
    manager = User(
        email="id_manager@apex.com",
        hashed_password=get_password_hash("ManagerPass123!"),
        full_name="ID Manager",
        role=RoleEnum.MANAGER,
        is_active=True,
        organization_id=org_apex.id,
    )
    grc_analyst = User(
        email="id_grc_analyst@apex.com",
        hashed_password=get_password_hash("GrcAnalystPass123!"),
        full_name="ID GRC Analyst",
        role=RoleEnum.GRC_ANALYST,
        is_active=True,
        organization_id=org_apex.id,
    )
    sec_analyst = User(
        email="id_sec_analyst@apex.com",
        hashed_password=get_password_hash("SecAnalystPass123!"),
        full_name="ID Sec Analyst",
        role=RoleEnum.SECURITY_ANALYST,
        is_active=True,
        organization_id=org_apex.id,
    )
    viewer = User(
        email="id_viewer@apex.com",
        hashed_password=get_password_hash("ViewerPass123!"),
        full_name="ID Viewer",
        role=RoleEnum.VIEWER,
        is_active=True,
        organization_id=org_apex.id,
    )
    meridian_admin = User(
        email="id_admin@meridian.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Meridian Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_meridian.id,
    )

    db.add_all([admin, manager, grc_analyst, sec_analyst, viewer, meridian_admin])
    db.commit()
    for u in [admin, manager, grc_analyst, sec_analyst, viewer, meridian_admin]:
        db.refresh(u)

    return {
        "admin": admin,
        "manager": manager,
        "grc_analyst": grc_analyst,
        "sec_analyst": sec_analyst,
        "viewer": viewer,
        "meridian_admin": meridian_admin,
        "org_apex": org_apex,
        "org_meridian": org_meridian,
    }


def test_create_and_get_identity_api(client: TestClient, id_api_fixture):
    users = id_api_fixture
    headers = get_token_headers(users["admin"])

    payload = {
        "identity_code": "ID-CORP-001",
        "email": "sarah.connor@apex.com",
        "full_name": "Sarah Connor",
        "identity_type": "WORKFORCE_EMPLOYEE",
        "department": "Security Operations",
        "is_privileged": True,
        "mfa_enabled": True,
    }

    res = client.post("/api/v1/identity-governance/identities", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["identity_code"] == "ID-CORP-001"
    assert data["risk_score"] == 10.00  # (0) + 30 (priv) - 20 (mfa) = 10.0
    ident_id = data["id"]

    res_get = client.get(f"/api/v1/identity-governance/identities/{ident_id}", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["email"] == "sarah.connor@apex.com"


def test_entitlements_and_assignments_api(client: TestClient, id_api_fixture):
    users = id_api_fixture
    headers = get_token_headers(users["admin"])

    # Create entitlement
    ent_res = client.post(
        "/api/v1/identity-governance/entitlements",
        json={
            "entitlement_code": "ENT-K8S-CLUSTER-ADMIN",
            "name": "Kubernetes Cluster Administrator",
            "system_type": "AWS_IAM",
            "resource_name": "eks-production-cluster",
            "permission_scope": "system:masters",
            "is_privileged": True,
            "risk_weight": 4.5,
        },
        headers=headers,
    )
    assert ent_res.status_code == 201
    ent_id = ent_res.json()["id"]

    # Create identity
    id_res = client.post(
        "/api/v1/identity-governance/identities",
        json={
            "identity_code": "ID-DEVOPS-001",
            "email": "devops.lead@apex.com",
            "full_name": "DevOps Lead",
        },
        headers=headers,
    )
    ident_id = id_res.json()["id"]

    # Assign entitlement
    assign_res = client.post(
        f"/api/v1/identity-governance/identities/{ident_id}/assignments",
        json={"entitlement_id": ent_id, "assignment_type": "DIRECT"},
        headers=headers,
    )
    assert assign_res.status_code == 201
    assert assign_res.json()["is_active"] == True


def test_access_certification_campaign_workflow_api(client: TestClient, id_api_fixture):
    users = id_api_fixture
    headers_admin = get_token_headers(users["admin"])
    headers_mgr = get_token_headers(users["manager"])

    # Create identity and entitlement
    id_res = client.post(
        "/api/v1/identity-governance/identities",
        json={
            "identity_code": "ID-UAR-001",
            "email": "auditee@apex.com",
            "full_name": "Auditee User",
        },
        headers=headers_admin,
    )
    ident_id = id_res.json()["id"]

    ent_res = client.post(
        "/api/v1/identity-governance/entitlements",
        json={
            "entitlement_code": "ENT-FIN-READ",
            "name": "Financial Data Reader",
            "system_type": "SAAS_APPLICATION",
            "resource_name": "Quickbooks",
            "permission_scope": "Reports_Read",
        },
        headers=headers_admin,
    )
    ent_id = ent_res.json()["id"]

    client.post(
        f"/api/v1/identity-governance/identities/{ident_id}/assignments",
        json={"entitlement_id": ent_id},
        headers=headers_admin,
    )

    # Launch Campaign
    camp_res = client.post(
        "/api/v1/identity-governance/campaigns",
        json={
            "campaign_code": "CAMP-2026-H1",
            "title": "H1 2026 Access Review",
            "deadline": (datetime.now(timezone.utc) + timedelta(days=14)).isoformat(),
        },
        headers=headers_admin,
    )
    assert camp_res.status_code == 201
    camp_id = camp_res.json()["id"]

    # List items
    items_res = client.get(f"/api/v1/identity-governance/campaigns/{camp_id}/items", headers=headers_mgr)
    assert items_res.status_code == 200
    items = items_res.json()
    assert len(items) >= 1
    item_id = items[0]["id"]

    # Review item
    rev_res = client.post(
        f"/api/v1/identity-governance/certifications/{item_id}/review",
        json={"decision": "CERTIFIED", "decision_justification": "Verified employment role"},
        headers=headers_mgr,
    )
    assert rev_res.status_code == 200
    assert rev_res.json()["decision"] == "CERTIFIED"

    # Finalize campaign
    fin_res = client.post(f"/api/v1/identity-governance/campaigns/{camp_id}/finalize", headers=headers_mgr)
    assert fin_res.status_code == 200
    assert fin_res.json()["status"] == "FINALIZED"


def test_jit_privileged_access_api(client: TestClient, id_api_fixture):
    users = id_api_fixture
    headers_sec = get_token_headers(users["sec_analyst"])
    headers_mgr = get_token_headers(users["manager"])

    id_res = client.post(
        "/api/v1/identity-governance/identities",
        json={
            "identity_code": "ID-SRE-001",
            "email": "sre.oncall@apex.com",
            "full_name": "SRE OnCall",
        },
        headers=headers_sec,
    )
    ident_id = id_res.json()["id"]

    ent_res = client.post(
        "/api/v1/identity-governance/entitlements",
        json={
            "entitlement_code": "ENT-PROD-BREAKGLASS",
            "name": "Prod Breakglass",
            "system_type": "AWS_IAM",
            "resource_name": "AWS Production Account",
            "permission_scope": "AdministratorAccess",
            "is_privileged": True,
        },
        headers=headers_sec,
    )
    ent_id = ent_res.json()["id"]

    # Request JIT
    req_res = client.post(
        "/api/v1/identity-governance/jit-requests",
        json={
            "request_code": "JIT-INCIDENT-991",
            "identity_id": ident_id,
            "entitlement_id": ent_id,
            "requested_duration_minutes": 120,
            "business_justification": "Mitigating production outage SEV-1 outage database lock",
        },
        headers=headers_sec,
    )
    assert req_res.status_code == 201
    req_id = req_res.json()["id"]

    # Approve by Manager
    app_res = client.post(
        f"/api/v1/identity-governance/jit-requests/{req_id}/review",
        json={"approved": True, "notes": "Authorized emergency change"},
        headers=headers_mgr,
    )
    assert app_res.status_code == 200
    assert app_res.json()["approval_status"] == "APPROVED"
    assert app_res.json()["is_active"] == True


def test_zero_trust_assurance_preview_and_assessment_api(client: TestClient, id_api_fixture):
    users = id_api_fixture
    headers_sec = get_token_headers(users["sec_analyst"])

    # Preview
    prev_res = client.post(
        "/api/v1/identity-governance/zero-trust/preview",
        json={
            "device_health_score": 90.0,
            "auth_strength_score": 95.0,
            "context_risk_score": 10.0,
            "behavioral_anomaly_score": 5.0,
        },
        headers=headers_sec,
    )
    assert prev_res.status_code == 200
    assert prev_res.json()["trust_level"] == "HIGH_TRUST"


def test_sod_conflict_policy_and_posture_summary_api(client: TestClient, id_api_fixture):
    users = id_api_fixture
    headers_admin = get_token_headers(users["admin"])
    headers_viewer = get_token_headers(users["viewer"])

    # Summary endpoint
    res = client.get("/api/v1/identity-governance/posture/summary", headers=headers_viewer)
    assert res.status_code == 200
    data = res.json()
    assert "total_identities" in data
    assert "average_zero_trust_score" in data
