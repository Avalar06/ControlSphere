from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.permissions import RoleEnum
from app.core.security import get_password_hash
from app.models.organization import Organization
from app.models.user import User
from app.models.cloudsec import CloudAsset, CloudAssetTypeEnum, CloudProviderEnum
from tests.conftest import get_token_headers


@pytest.fixture
def p19_adv_fixture(db: Session, org_apex: Organization, org_meridian: Organization):
    """Setup adversarial test harness with two isolated tenants and various roles."""
    apex_admin = User(
        email="p19_apex_admin@apex.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Apex Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_manager = User(
        email="p19_apex_manager@apex.com",
        hashed_password=get_password_hash("ManagerPass123!"),
        full_name="Apex Manager",
        role=RoleEnum.MANAGER,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_viewer = User(
        email="p19_apex_viewer@apex.com",
        hashed_password=get_password_hash("ViewerPass123!"),
        full_name="Apex Viewer",
        role=RoleEnum.VIEWER,
        is_active=True,
        organization_id=org_apex.id,
    )
    meridian_admin = User(
        email="p19_meridian_admin@meridian.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Meridian Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_meridian.id,
    )

    db.add_all([apex_admin, apex_manager, apex_viewer, meridian_admin])
    db.commit()
    for u in [apex_admin, apex_manager, apex_viewer, meridian_admin]:
        db.refresh(u)

    return {
        "apex_admin": apex_admin,
        "apex_manager": apex_manager,
        "apex_viewer": apex_viewer,
        "meridian_admin": meridian_admin,
        "org_apex": org_apex,
        "org_meridian": org_meridian,
    }


def _seed_meridian_identity(client: TestClient, meridian_admin: User) -> int:
    headers = get_token_headers(meridian_admin)
    res = client.post(
        "/api/v1/identity-governance/identities",
        json={
            "identity_code": "MERIDIAN-EMP-001",
            "email": "cfo@meridian.com",
            "full_name": "Meridian CFO",
            "identity_type": "WORKFORCE_EMPLOYEE",
        },
        headers=headers,
    )
    return res.json()["id"]


def _seed_meridian_asset(client: TestClient, meridian_admin: User) -> int:
    headers = get_token_headers(meridian_admin)
    res = client.post(
        "/api/v1/cloud-security/assets",
        json={
            "asset_code": "MERIDIAN-S3-P19",
            "provider": "AWS",
            "account_id": "999888777666",
            "region": "eu-central-1",
            "resource_type": "S3_BUCKET",
            "resource_arn": "arn:aws:s3:::meridian-p19-bucket",
            "resource_name": "meridian-p19-bucket",
        },
        headers=headers,
    )
    return res.json()["id"]


def test_adv_p19_01_cross_tenant_identity_read(client: TestClient, p19_adv_fixture):
    """ADV-P19-01: Tenant A cannot read Tenant B's governed identity (404 Concealment)."""
    f = p19_adv_fixture
    meridian_id = _seed_meridian_identity(client, f["meridian_admin"])
    apex_headers = get_token_headers(f["apex_admin"])

    res = client.get(f"/api/v1/identity-governance/identities/{meridian_id}", headers=apex_headers)
    assert res.status_code == 404


def test_adv_p19_02_cross_tenant_identity_update(client: TestClient, p19_adv_fixture):
    """ADV-P19-02: Tenant A cannot update Tenant B's governed identity (404 Concealment)."""
    f = p19_adv_fixture
    meridian_id = _seed_meridian_identity(client, f["meridian_admin"])
    apex_headers = get_token_headers(f["apex_admin"])

    res = client.patch(
        f"/api/v1/identity-governance/identities/{meridian_id}",
        json={"full_name": "Tampered Name"},
        headers=apex_headers,
    )
    assert res.status_code == 404


def test_adv_p19_03_cross_tenant_identity_deletion(client: TestClient, p19_adv_fixture):
    """ADV-P19-03: Tenant A cannot delete Tenant B's governed identity (404 Concealment)."""
    f = p19_adv_fixture
    meridian_id = _seed_meridian_identity(client, f["meridian_admin"])
    apex_headers = get_token_headers(f["apex_admin"])

    res = client.delete(f"/api/v1/identity-governance/identities/{meridian_id}", headers=apex_headers)
    assert res.status_code == 404


def test_adv_p19_04_cross_tenant_entitlement_assignment(client: TestClient, p19_adv_fixture):
    """ADV-P19-04: Tenant A cannot assign entitlements to Tenant B's identity (404 Not Found)."""
    f = p19_adv_fixture
    meridian_id = _seed_meridian_identity(client, f["meridian_admin"])
    apex_headers = get_token_headers(f["apex_admin"])

    # Create apex entitlement
    ent_res = client.post(
        "/api/v1/identity-governance/entitlements",
        json={
            "entitlement_code": "ENT-APEX-ATTACK",
            "name": "Apex Entitlement",
            "resource_name": "Res",
            "permission_scope": "Scope",
        },
        headers=apex_headers,
    )
    ent_id = ent_res.json()["id"]

    res = client.post(
        f"/api/v1/identity-governance/identities/{meridian_id}/assignments",
        json={"entitlement_id": ent_id},
        headers=apex_headers,
    )
    assert res.status_code == 404


def test_adv_p19_05_cross_tenant_access_campaign_read(client: TestClient, p19_adv_fixture):
    """ADV-P19-05: Tenant A cannot read Tenant B's access campaign (404 Concealment)."""
    f = p19_adv_fixture
    meridian_headers = get_token_headers(f["meridian_admin"])
    apex_headers = get_token_headers(f["apex_admin"])

    camp_res = client.post(
        "/api/v1/identity-governance/campaigns",
        json={
            "campaign_code": "MERIDIAN-SECRET-CAMP",
            "title": "Meridian Secret Review",
            "deadline": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        },
        headers=meridian_headers,
    )
    camp_id = camp_res.json()["id"]

    res = client.get(f"/api/v1/identity-governance/campaigns/{camp_id}", headers=apex_headers)
    assert res.status_code == 404


def test_adv_p19_06_cross_tenant_campaign_item_review_attempt(client: TestClient, p19_adv_fixture):
    """ADV-P19-06: Tenant A cannot review Tenant B's campaign certification items (404 Concealment)."""
    f = p19_adv_fixture
    meridian_headers = get_token_headers(f["meridian_admin"])
    apex_headers = get_token_headers(f["apex_admin"])

    # Seed Meridian identity, entitlement, assignment, and campaign
    m_id = _seed_meridian_identity(client, f["meridian_admin"])
    m_ent = client.post(
        "/api/v1/identity-governance/entitlements",
        json={
            "entitlement_code": "MERIDIAN-CONFIDENTIAL",
            "name": "Meridian Conf",
            "resource_name": "Vault",
            "permission_scope": "Read",
        },
        headers=meridian_headers,
    ).json()["id"]

    client.post(
        f"/api/v1/identity-governance/identities/{m_id}/assignments",
        json={"entitlement_id": m_ent},
        headers=meridian_headers,
    )

    camp_res = client.post(
        "/api/v1/identity-governance/campaigns",
        json={
            "campaign_code": "MERIDIAN-CAMP-02",
            "title": "Meridian Review 02",
            "deadline": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        },
        headers=meridian_headers,
    )
    items = client.get(f"/api/v1/identity-governance/campaigns/{camp_res.json()['id']}/items", headers=meridian_headers).json()
    item_id = items[0]["id"]

    # Apex attempts to review Meridian's item
    res = client.post(
        f"/api/v1/identity-governance/certifications/{item_id}/review",
        json={"decision": "REVOKED"},
        headers=apex_headers,
    )
    assert res.status_code == 404


def test_adv_p19_07_cross_tenant_jit_request_submission(client: TestClient, p19_adv_fixture):
    """ADV-P19-07: Tenant A cannot submit a JIT request for Tenant B's identity."""
    f = p19_adv_fixture
    meridian_id = _seed_meridian_identity(client, f["meridian_admin"])
    apex_headers = get_token_headers(f["apex_admin"])

    ent_res = client.post(
        "/api/v1/identity-governance/entitlements",
        json={
            "entitlement_code": "ENT-APEX-JIT-TEST",
            "name": "Apex JIT",
            "resource_name": "Res",
            "permission_scope": "Scope",
        },
        headers=apex_headers,
    )

    res = client.post(
        "/api/v1/identity-governance/jit-requests",
        json={
            "request_code": "JIT-CROSS-SUBMIT-01",
            "identity_id": meridian_id,
            "entitlement_id": ent_res.json()["id"],
            "requested_duration_minutes": 60,
            "business_justification": "Cross tenant injection attempt",
        },
        headers=apex_headers,
    )
    assert res.status_code == 404


def test_adv_p19_08_cross_tenant_jit_request_review_attempt(client: TestClient, p19_adv_fixture):
    """ADV-P19-08: Tenant A cannot approve Tenant B's JIT access request."""
    f = p19_adv_fixture
    meridian_headers = get_token_headers(f["meridian_admin"])
    apex_headers = get_token_headers(f["apex_admin"])

    m_id = _seed_meridian_identity(client, f["meridian_admin"])
    m_ent = client.post(
        "/api/v1/identity-governance/entitlements",
        json={
            "entitlement_code": "MERIDIAN-DB-ACCESS",
            "name": "DB Access",
            "resource_name": "DB",
            "permission_scope": "Write",
        },
        headers=meridian_headers,
    ).json()["id"]

    jit_res = client.post(
        "/api/v1/identity-governance/jit-requests",
        json={
            "request_code": "JIT-MERIDIAN-001",
            "identity_id": m_id,
            "entitlement_id": m_ent,
            "requested_duration_minutes": 60,
            "business_justification": "DB Maintenance",
        },
        headers=meridian_headers,
    )
    req_id = jit_res.json()["id"]

    # Apex attempts to approve
    res = client.post(
        f"/api/v1/identity-governance/jit-requests/{req_id}/review",
        json={"approved": True},
        headers=apex_headers,
    )
    assert res.status_code == 404


def test_adv_p19_09_four_eyes_self_certification_violation(client: TestClient, p19_adv_fixture):
    """ADV-P19-09: Four-Eyes SoD rule strictly blocks users from certifying themselves (422)."""
    f = p19_adv_fixture
    apex_admin_headers = get_token_headers(f["apex_admin"])

    # Create identity linked to apex_admin
    id_res = client.post(
        "/api/v1/identity-governance/identities",
        json={
            "identity_code": "ID-APEX-ADMIN-SELF",
            "email": "apex_admin_self@apex.com",
            "full_name": "Apex Admin Self",
            "user_id": f["apex_admin"].id,
        },
        headers=apex_admin_headers,
    )
    ident_id = id_res.json()["id"]

    ent_res = client.post(
        "/api/v1/identity-governance/entitlements",
        json={
            "entitlement_code": "ENT-SELF-CERT",
            "name": "Self Cert Ent",
            "resource_name": "Res",
            "permission_scope": "Scope",
        },
        headers=apex_admin_headers,
    )
    ent_id = ent_res.json()["id"]

    client.post(
        f"/api/v1/identity-governance/identities/{ident_id}/assignments",
        json={"entitlement_id": ent_id},
        headers=apex_admin_headers,
    )

    camp_res = client.post(
        "/api/v1/identity-governance/campaigns",
        json={
            "campaign_code": "CAMP-SELF-TEST",
            "title": "Self Cert Test Campaign",
            "deadline": (datetime.now(timezone.utc) + timedelta(days=10)).isoformat(),
        },
        headers=apex_admin_headers,
    )
    items = client.get(f"/api/v1/identity-governance/campaigns/{camp_res.json()['id']}/items", headers=apex_admin_headers).json()
    item_id = items[0]["id"]

    # Admin attempts self-certification
    res = client.post(
        f"/api/v1/identity-governance/certifications/{item_id}/review",
        json={"decision": "CERTIFIED"},
        headers=apex_admin_headers,
    )
    assert res.status_code == 422
    assert "four-eyes" in res.json()["detail"].lower()


def test_adv_p19_10_four_eyes_jit_self_approval_violation(client: TestClient, p19_adv_fixture):
    """ADV-P19-10: Four-Eyes SoD rule strictly blocks requesters from approving their own JIT request (422)."""
    f = p19_adv_fixture
    apex_admin_headers = get_token_headers(f["apex_admin"])

    id_res = client.post(
        "/api/v1/identity-governance/identities",
        json={
            "identity_code": "ID-JIT-SELF-01",
            "email": "jit_self@apex.com",
            "full_name": "JIT Self",
        },
        headers=apex_admin_headers,
    )
    ent_res = client.post(
        "/api/v1/identity-governance/entitlements",
        json={
            "entitlement_code": "ENT-JIT-SELF",
            "name": "JIT Self Ent",
            "resource_name": "Res",
            "permission_scope": "Scope",
        },
        headers=apex_admin_headers,
    )

    jit_res = client.post(
        "/api/v1/identity-governance/jit-requests",
        json={
            "request_code": "JIT-SELF-REQ-01",
            "identity_id": id_res.json()["id"],
            "entitlement_id": ent_res.json()["id"],
            "requested_duration_minutes": 60,
            "business_justification": "Self elevation test",
        },
        headers=apex_admin_headers,
    )
    req_id = jit_res.json()["id"]

    # Admin requested, so Admin cannot approve
    res = client.post(
        f"/api/v1/identity-governance/jit-requests/{req_id}/review",
        json={"approved": True},
        headers=apex_admin_headers,
    )
    assert res.status_code == 422
    assert "four-eyes" in res.json()["detail"].lower()


def test_adv_p19_11_finalized_campaign_decision_replay_lockout(client: TestClient, p19_adv_fixture):
    """ADV-P19-11: Decisions in finalized access campaigns are immutable (409 Conflict)."""
    f = p19_adv_fixture
    apex_admin_headers = get_token_headers(f["apex_admin"])
    apex_mgr_headers = get_token_headers(f["apex_manager"])

    id_res = client.post(
        "/api/v1/identity-governance/identities",
        json={
            "identity_code": "ID-LOCK-CAMP-01",
            "email": "lock_camp@apex.com",
            "full_name": "Lock Camp",
        },
        headers=apex_admin_headers,
    )
    ent_res = client.post(
        "/api/v1/identity-governance/entitlements",
        json={
            "entitlement_code": "ENT-LOCK-CAMP",
            "name": "Lock Ent",
            "resource_name": "Res",
            "permission_scope": "Scope",
        },
        headers=apex_admin_headers,
    )
    client.post(
        f"/api/v1/identity-governance/identities/{id_res.json()['id']}/assignments",
        json={"entitlement_id": ent_res.json()["id"]},
        headers=apex_admin_headers,
    )

    camp_res = client.post(
        "/api/v1/identity-governance/campaigns",
        json={
            "campaign_code": "CAMP-FINALIZE-LOCK",
            "title": "Finalize Lock Test",
            "deadline": (datetime.now(timezone.utc) + timedelta(days=10)).isoformat(),
        },
        headers=apex_admin_headers,
    )
    camp_id = camp_res.json()["id"]
    items = client.get(f"/api/v1/identity-governance/campaigns/{camp_id}/items", headers=apex_mgr_headers).json()
    item_id = items[0]["id"]

    # Finalize campaign
    client.post(f"/api/v1/identity-governance/campaigns/{camp_id}/finalize", headers=apex_mgr_headers)

    # Attempt to review item after campaign is finalized
    res = client.post(
        f"/api/v1/identity-governance/certifications/{item_id}/review",
        json={"decision": "CERTIFIED"},
        headers=apex_mgr_headers,
    )
    assert res.status_code == 409


def test_adv_p19_12_jit_request_terminal_state_re_review(client: TestClient, p19_adv_fixture):
    """ADV-P19-12: Approved or rejected JIT requests cannot be re-reviewed (409 Conflict)."""
    f = p19_adv_fixture
    apex_admin_headers = get_token_headers(f["apex_admin"])
    apex_mgr_headers = get_token_headers(f["apex_manager"])

    id_res = client.post(
        "/api/v1/identity-governance/identities",
        json={
            "identity_code": "ID-JIT-TERM-01",
            "email": "jit_term@apex.com",
            "full_name": "JIT Term",
        },
        headers=apex_admin_headers,
    )
    ent_res = client.post(
        "/api/v1/identity-governance/entitlements",
        json={
            "entitlement_code": "ENT-JIT-TERM",
            "name": "JIT Term Ent",
            "resource_name": "Res",
            "permission_scope": "Scope",
        },
        headers=apex_admin_headers,
    )
    jit_res = client.post(
        "/api/v1/identity-governance/jit-requests",
        json={
            "request_code": "JIT-TERM-REQ-01",
            "identity_id": id_res.json()["id"],
            "entitlement_id": ent_res.json()["id"],
            "requested_duration_minutes": 60,
            "business_justification": "Terminal state test",
        },
        headers=apex_admin_headers,
    )
    req_id = jit_res.json()["id"]

    # Manager approves
    client.post(
        f"/api/v1/identity-governance/jit-requests/{req_id}/review",
        json={"approved": True},
        headers=apex_mgr_headers,
    )

    # Re-review attempt
    res = client.post(
        f"/api/v1/identity-governance/jit-requests/{req_id}/review",
        json={"approved": False},
        headers=apex_mgr_headers,
    )
    assert res.status_code == 409


def test_adv_p19_13_active_identity_direct_deletion_attempt(client: TestClient, p19_adv_fixture):
    """ADV-P19-13: Active identities cannot be directly deleted without suspension (400 Bad Request)."""
    f = p19_adv_fixture
    apex_admin_headers = get_token_headers(f["apex_admin"])

    id_res = client.post(
        "/api/v1/identity-governance/identities",
        json={
            "identity_code": "ID-ACT-DEL-01",
            "email": "act_del@apex.com",
            "full_name": "Active Delete",
        },
        headers=apex_admin_headers,
    )
    ident_id = id_res.json()["id"]

    res = client.delete(f"/api/v1/identity-governance/identities/{ident_id}", headers=apex_admin_headers)
    assert res.status_code == 400


def test_adv_p19_14_unauthorized_identity_creation_by_viewer(client: TestClient, p19_adv_fixture):
    """ADV-P19-14: Viewer role cannot create governed identities (403 Forbidden)."""
    f = p19_adv_fixture
    viewer_headers = get_token_headers(f["apex_viewer"])

    res = client.post(
        "/api/v1/identity-governance/identities",
        json={
            "identity_code": "ID-VIEWER-FORBID",
            "email": "viewer_forbid@apex.com",
            "full_name": "Viewer Forbid",
        },
        headers=viewer_headers,
    )
    assert res.status_code == 403


def test_adv_p19_15_unauthorized_campaign_launch_by_viewer(client: TestClient, p19_adv_fixture):
    """ADV-P19-15: Viewer role cannot launch certification campaigns (403 Forbidden)."""
    f = p19_adv_fixture
    viewer_headers = get_token_headers(f["apex_viewer"])

    res = client.post(
        "/api/v1/identity-governance/campaigns",
        json={
            "campaign_code": "CAMP-VIEWER-FORBID",
            "title": "Viewer Forbid",
            "deadline": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
        },
        headers=viewer_headers,
    )
    assert res.status_code == 403


def test_adv_p19_16_unauthorized_jit_approval_by_viewer(client: TestClient, p19_adv_fixture):
    """ADV-P19-16: Viewer role cannot approve JIT requests (403 Forbidden)."""
    f = p19_adv_fixture
    viewer_headers = get_token_headers(f["apex_viewer"])

    res = client.post(
        "/api/v1/identity-governance/jit-requests/1/review",
        json={"approved": True},
        headers=viewer_headers,
    )
    assert res.status_code == 403


def test_adv_p19_17_cross_tenant_user_id_account_linkage_escape(client: TestClient, p19_adv_fixture):
    """ADV-P19-17: Cannot link governed identity to platform user from foreign tenant (404 Not Found)."""
    f = p19_adv_fixture
    apex_headers = get_token_headers(f["apex_admin"])

    res = client.post(
        "/api/v1/identity-governance/identities",
        json={
            "identity_code": "ID-CROSS-USER-01",
            "email": "cross_user@apex.com",
            "full_name": "Cross User",
            "user_id": f["meridian_admin"].id,  # Foreign tenant User ID
        },
        headers=apex_headers,
    )
    assert res.status_code == 404


def test_adv_p19_18_cross_tenant_cloud_asset_linkage_escape(client: TestClient, p19_adv_fixture):
    """ADV-P19-18: Cannot link governed identity to cloud asset from foreign tenant (404 Not Found)."""
    f = p19_adv_fixture
    meridian_asset_id = _seed_meridian_asset(client, f["meridian_admin"])
    apex_headers = get_token_headers(f["apex_admin"])

    res = client.post(
        "/api/v1/identity-governance/identities",
        json={
            "identity_code": "ID-CROSS-ASSET-01",
            "email": "cross_asset@apex.com",
            "full_name": "Cross Asset",
            "cloud_asset_id": meridian_asset_id,  # Foreign tenant Cloud Asset
        },
        headers=apex_headers,
    )
    assert res.status_code == 404


def test_adv_p19_19_duplicate_identity_code_collision(client: TestClient, p19_adv_fixture):
    """ADV-P19-19: Duplicate identity code in same tenant yields 409 Conflict."""
    f = p19_adv_fixture
    apex_headers = get_token_headers(f["apex_admin"])

    payload = {
        "identity_code": "ID-DUP-CODE-01",
        "email": "dup1@apex.com",
        "full_name": "Dup 1",
    }
    r1 = client.post("/api/v1/identity-governance/identities", json=payload, headers=apex_headers)
    assert r1.status_code == 201

    payload["email"] = "dup2@apex.com"
    r2 = client.post("/api/v1/identity-governance/identities", json=payload, headers=apex_headers)
    assert r2.status_code == 409


def test_adv_p19_20_duplicate_identity_email_collision(client: TestClient, p19_adv_fixture):
    """ADV-P19-20: Duplicate identity email in same tenant yields 409 Conflict."""
    f = p19_adv_fixture
    apex_headers = get_token_headers(f["apex_admin"])

    payload = {
        "identity_code": "ID-DUP-EMAIL-01",
        "email": "same_email@apex.com",
        "full_name": "Same Email 1",
    }
    r1 = client.post("/api/v1/identity-governance/identities", json=payload, headers=apex_headers)
    assert r1.status_code == 201

    payload["identity_code"] = "ID-DUP-EMAIL-02"
    r2 = client.post("/api/v1/identity-governance/identities", json=payload, headers=apex_headers)
    assert r2.status_code == 409


def test_adv_p19_21_duplicate_entitlement_code_collision(client: TestClient, p19_adv_fixture):
    """ADV-P19-21: Duplicate entitlement code in same tenant yields 409 Conflict."""
    f = p19_adv_fixture
    apex_headers = get_token_headers(f["apex_admin"])

    payload = {
        "entitlement_code": "ENT-DUP-CODE-01",
        "name": "Dup Ent 1",
        "resource_name": "Res",
        "permission_scope": "Scope",
    }
    r1 = client.post("/api/v1/identity-governance/entitlements", json=payload, headers=apex_headers)
    assert r1.status_code == 201

    r2 = client.post("/api/v1/identity-governance/entitlements", json=payload, headers=apex_headers)
    assert r2.status_code == 409


def test_adv_p19_22_sod_policy_identical_entitlements_rejection(client: TestClient, p19_adv_fixture):
    """ADV-P19-22: SoD policy cannot have identical entitlement_a and entitlement_b (422)."""
    f = p19_adv_fixture
    apex_headers = get_token_headers(f["apex_admin"])

    ent_res = client.post(
        "/api/v1/identity-governance/entitlements",
        json={
            "entitlement_code": "ENT-SOD-SAME",
            "name": "Same Ent",
            "resource_name": "Res",
            "permission_scope": "Scope",
        },
        headers=apex_headers,
    )
    ent_id = ent_res.json()["id"]

    res = client.post(
        "/api/v1/identity-governance/sod-policies",
        json={
            "policy_code": "SOD-SAME-ERR",
            "name": "Invalid Same Policy",
            "entitlement_a_id": ent_id,
            "entitlement_b_id": ent_id,
        },
        headers=apex_headers,
    )
    assert res.status_code == 422


def test_adv_p19_23_client_identity_risk_score_manipulation(client: TestClient, p19_adv_fixture):
    """ADV-P19-23: Injected client risk_score is ignored in favor of server calculation."""
    f = p19_adv_fixture
    apex_headers = get_token_headers(f["apex_admin"])

    res = client.post(
        "/api/v1/identity-governance/identities",
        json={
            "identity_code": "ID-FORGE-RISK-01",
            "email": "forge_risk@apex.com",
            "full_name": "Forge Risk",
            "is_privileged": True,
            "mfa_enabled": False,
            "risk_score": 0.00,  # Malicious attempt to forge clean score
        },
        headers=apex_headers,
    )
    assert res.status_code == 201
    # Server calculates 0 + 30 (priv) - 0 (no mfa) = 30.00
    assert res.json()["risk_score"] == 30.00


def test_adv_p19_24_client_zero_trust_score_manipulation(client: TestClient, p19_adv_fixture):
    """ADV-P19-24: Injected zero_trust_assurance_score is ignored in favor of server calculation."""
    f = p19_adv_fixture
    apex_headers = get_token_headers(f["apex_admin"])

    id_res = client.post(
        "/api/v1/identity-governance/identities",
        json={
            "identity_code": "ID-ZT-FORGE-01",
            "email": "zt_forge@apex.com",
            "full_name": "ZT Forge",
        },
        headers=apex_headers,
    )
    ident_id = id_res.json()["id"]

    res = client.post(
        f"/api/v1/identity-governance/identities/{ident_id}/zero-trust",
        json={
            "assessment_code": "ZT-FORGE-001",
            "device_health_score": 0.0,
            "auth_strength_score": 0.0,
            "context_risk_score": 100.0,
            "behavioral_anomaly_score": 100.0,
            "zero_trust_assurance_score": 100.0,  # Forged clean score
        },
        headers=apex_headers,
    )
    assert res.status_code == 201
    # Server calculates 0.00 -> UNTRUSTED
    assert res.json()["zero_trust_assurance_score"] == 0.00
    assert res.json()["trust_level"] == "UNTRUSTED"


def test_adv_p19_25_unauthenticated_identity_endpoint_infiltration(client: TestClient):
    """ADV-P19-25: Unauthenticated access to Identity Governance endpoints yields 401 Unauthorized."""
    assert client.get("/api/v1/identity-governance/identities").status_code == 401
    assert client.post("/api/v1/identity-governance/identities", json={}).status_code == 401
    assert client.get("/api/v1/identity-governance/posture/summary").status_code == 401
