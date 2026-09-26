import os
import tempfile
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.cloudsec import (
    CloudAsset,
    CloudAssetTypeEnum,
    CloudCriticalityEnum,
    CloudEnvironmentEnum,
    CloudLifecycleStateEnum,
    CloudPostureStatusEnum,
    CloudProviderEnum,
)
from app.models.control import ImplementationStatusEnum, OrganizationControl
from app.models.evidence import EvidenceItem, EvidenceStatusEnum
from app.models.framework import (
    Framework,
    FrameworkCategory,
    FrameworkFunction,
    FrameworkSubcategory,
)
from app.models.organization import Organization
from app.models.privacy import (
    ProcessingActivity,
    ProcessingLegalBasis,
    ProcessingLifecycleState,
)
from app.models.regulatory import (
    RegulatoryApplicabilityEnum,
    RegulatoryComplianceStatusEnum,
    RegulatoryMandate,
    RegulatoryObligation,
    RegulatorySource,
)
from app.models.user import User


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def dg_api_env(db: Session, client: TestClient):
    # Organization A
    org_a = Organization(name="Tenant Alpha DG", slug="alpha-dg")
    # Organization B (Foreign Tenant)
    org_b = Organization(name="Tenant Beta DG", slug="beta-dg")
    db.add_all([org_a, org_b])
    db.flush()

    user_admin_a = User(
        organization_id=org_a.id,
        email="admin@alpha-dg.example.com",
        full_name="Alpha Admin",
        hashed_password="hash",
        role="ADMIN",
        is_active=True,
    )
    user_mgr_a = User(
        organization_id=org_a.id,
        email="mgr@alpha-dg.example.com",
        full_name="Alpha Manager",
        hashed_password="hash",
        role="MANAGER",
        is_active=True,
    )
    user_analyst_a = User(
        organization_id=org_a.id,
        email="analyst@alpha-dg.example.com",
        full_name="Alpha GRC Analyst",
        hashed_password="hash",
        role="GRC_ANALYST",
        is_active=True,
    )
    user_sec_a = User(
        organization_id=org_a.id,
        email="sec@alpha-dg.example.com",
        full_name="Alpha Sec Analyst",
        hashed_password="hash",
        role="SECURITY_ANALYST",
        is_active=True,
    )
    user_auditor_a = User(
        organization_id=org_a.id,
        email="auditor@alpha-dg.example.com",
        full_name="Alpha Auditor",
        hashed_password="hash",
        role="AUDITOR",
        is_active=True,
    )
    user_viewer_a = User(
        organization_id=org_a.id,
        email="viewer@alpha-dg.example.com",
        full_name="Alpha Viewer",
        hashed_password="hash",
        role="VIEWER",
        is_active=True,
    )
    user_inactive_a = User(
        organization_id=org_a.id,
        email="inactive@alpha-dg.example.com",
        full_name="Alpha Inactive",
        hashed_password="hash",
        role="GRC_ANALYST",
        is_active=False,
    )

    user_admin_b = User(
        organization_id=org_b.id,
        email="admin@beta-dg.example.com",
        full_name="Beta Admin",
        hashed_password="hash",
        role="ADMIN",
        is_active=True,
    )
    db.add_all(
        [
            user_admin_a,
            user_mgr_a,
            user_analyst_a,
            user_sec_a,
            user_auditor_a,
            user_viewer_a,
            user_inactive_a,
            user_admin_b,
        ]
    )
    db.flush()

    # Framework & Subcategory
    fw = db.query(Framework).filter_by(identifier="DG-API-FW").first()
    if not fw:
        fw = Framework(identifier="DG-API-FW", name="Data Gov Framework", version="1.0")
        db.add(fw)
        db.flush()
        fn = FrameworkFunction(framework_id=fw.id, identifier="PR", name="Protect")
        db.add(fn)
        db.flush()
        cat = FrameworkCategory(function_id=fn.id, identifier="PR.DS", name="Data Security")
        db.add(cat)
        db.flush()
        sub_a = FrameworkSubcategory(
            category_id=cat.id,
            identifier="PR.DS-DG-01",
            title="Data at Rest Encryption",
            description="Data at rest is protected",
        )
        sub_b = FrameworkSubcategory(
            category_id=cat.id,
            identifier="PR.DS-DG-02",
            title="Data in Transit Encryption",
            description="Data in transit is protected",
        )
        db.add_all([sub_a, sub_b])
        db.flush()
    else:
        sub_a = db.query(FrameworkSubcategory).filter_by(identifier="PR.DS-DG-01").first()
        sub_b = db.query(FrameworkSubcategory).filter_by(identifier="PR.DS-DG-02").first()

    ctrl_a = OrganizationControl(
        organization_id=org_a.id,
        subcategory_id=sub_a.id,
        status=ImplementationStatusEnum.IMPLEMENTED,
        owner_id=user_mgr_a.id,
    )
    ctrl_b = OrganizationControl(
        organization_id=org_b.id,
        subcategory_id=sub_b.id,
        status=ImplementationStatusEnum.IMPLEMENTED,
        owner_id=user_admin_b.id,
    )
    db.add_all([ctrl_a, ctrl_b])
    db.flush()

    ev_accepted_a = EvidenceItem(
        organization_id=org_a.id,
        organization_control_id=ctrl_a.id,
        uploaded_by_id=user_analyst_a.id,
        title="Org A Destruction Certificate",
        original_filename="cert_a.pdf",
        stored_filename="stored_cert_a.pdf",
        file_extension="pdf",
        content_type="application/pdf",
        file_size=4096,
        sha256_hash="1" * 64,
        storage_key="ev/cert_a.pdf",
        status=EvidenceStatusEnum.ACCEPTED,
    )
    ev_rejected_a = EvidenceItem(
        organization_id=org_a.id,
        organization_control_id=ctrl_a.id,
        uploaded_by_id=user_analyst_a.id,
        title="Org A Rejected Evidence",
        original_filename="rej_a.pdf",
        stored_filename="stored_rej_a.pdf",
        file_extension="pdf",
        content_type="application/pdf",
        file_size=1024,
        sha256_hash="2" * 64,
        storage_key="ev/rej_a.pdf",
        status=EvidenceStatusEnum.REJECTED,
    )
    ev_superseded_a = EvidenceItem(
        organization_id=org_a.id,
        organization_control_id=ctrl_a.id,
        uploaded_by_id=user_analyst_a.id,
        title="Org A Superseded Evidence",
        original_filename="sup_a.pdf",
        stored_filename="stored_sup_a.pdf",
        file_extension="pdf",
        content_type="application/pdf",
        file_size=1024,
        sha256_hash="3" * 64,
        storage_key="ev/sup_a.pdf",
        status=EvidenceStatusEnum.SUPERSEDED,
    )
    ev_accepted_b = EvidenceItem(
        organization_id=org_b.id,
        organization_control_id=ctrl_b.id,
        uploaded_by_id=user_admin_b.id,
        title="Org B Evidence",
        original_filename="cert_b.pdf",
        stored_filename="stored_cert_b.pdf",
        file_extension="pdf",
        content_type="application/pdf",
        file_size=4096,
        sha256_hash="4" * 64,
        storage_key="ev/cert_b.pdf",
        status=EvidenceStatusEnum.ACCEPTED,
    )
    db.add_all([ev_accepted_a, ev_rejected_a, ev_superseded_a, ev_accepted_b])
    db.flush()

    cloud_a = CloudAsset(
        organization_id=org_a.id,
        asset_code="CLD-ALPHA-01",
        provider=CloudProviderEnum.AWS,
        account_id="111122223333",
        region="us-east-1",
        resource_type=CloudAssetTypeEnum.S3_BUCKET,
        resource_arn="arn:aws:s3:::alpha-bucket",
        resource_name="alpha-bucket",
        environment=CloudEnvironmentEnum.PRODUCTION,
        criticality=CloudCriticalityEnum.CRITICAL,
        posture_status=CloudPostureStatusEnum.COMPLIANT,
        posture_score=98.0,
        blast_radius_score=12.0,
        lifecycle_state=CloudLifecycleStateEnum.ACTIVE,
        is_internet_facing=False,
        encryption_enabled=True,
        owner_id=user_admin_a.id,
    )
    cloud_drifted_a = CloudAsset(
        organization_id=org_a.id,
        asset_code="CLD-ALPHA-DRIFT",
        provider=CloudProviderEnum.AWS,
        account_id="111122223333",
        region="us-east-1",
        resource_type=CloudAssetTypeEnum.S3_BUCKET,
        resource_arn="arn:aws:s3:::alpha-drifted-bucket",
        resource_name="alpha-drifted-bucket",
        environment=CloudEnvironmentEnum.PRODUCTION,
        criticality=CloudCriticalityEnum.HIGH,
        posture_status=CloudPostureStatusEnum.NON_COMPLIANT,
        posture_score=25.0,
        blast_radius_score=90.0,
        lifecycle_state=CloudLifecycleStateEnum.ACTIVE,
        is_internet_facing=True,
        encryption_enabled=False,
        owner_id=user_admin_a.id,
    )
    cloud_b = CloudAsset(
        organization_id=org_b.id,
        asset_code="CLD-BETA-01",
        provider=CloudProviderEnum.AWS,
        account_id="999988887777",
        region="eu-west-1",
        resource_type=CloudAssetTypeEnum.S3_BUCKET,
        resource_arn="arn:aws:s3:::beta-bucket",
        resource_name="beta-bucket",
        environment=CloudEnvironmentEnum.PRODUCTION,
        criticality=CloudCriticalityEnum.HIGH,
        posture_status=CloudPostureStatusEnum.COMPLIANT,
        posture_score=100.0,
        blast_radius_score=5.0,
        lifecycle_state=CloudLifecycleStateEnum.ACTIVE,
        is_internet_facing=False,
        encryption_enabled=True,
        owner_id=user_admin_b.id,
    )
    db.add_all([cloud_a, cloud_drifted_a, cloud_b])
    db.flush()

    ropa_a = ProcessingActivity(
        organization_id=org_a.id,
        activity_code="ROPA-ALPHA-01",
        name="Alpha Customer Onboarding",
        purpose_description="KYC and identity verification",
        legal_basis=ProcessingLegalBasis.LEGAL_OBLIGATION,
        data_subject_categories="CUSTOMERS",
        personal_data_categories="IDENTITY,FINANCIAL",
        lifecycle_state=ProcessingLifecycleState.ACTIVE,
        owner_id=user_mgr_a.id,
    )
    ropa_b = ProcessingActivity(
        organization_id=org_b.id,
        activity_code="ROPA-BETA-01",
        name="Beta Analytics",
        purpose_description="Internal analytics",
        legal_basis=ProcessingLegalBasis.LEGITIMATE_INTERESTS,
        data_subject_categories="CUSTOMERS",
        personal_data_categories="BEHAVIORAL",
        lifecycle_state=ProcessingLifecycleState.ACTIVE,
        owner_id=user_admin_b.id,
    )
    db.add_all([ropa_a, ropa_b])
    db.flush()

    reg_src_a = RegulatorySource(
        organization_id=org_a.id,
        source_code="EU-GDPR-ALPHA",
        name="EDPB Alpha",
        jurisdiction="EU",
    )
    db.add(reg_src_a)
    db.flush()
    mandate_a = RegulatoryMandate(
        organization_id=org_a.id,
        source_id=reg_src_a.id,
        mandate_code="GDPR-ALPHA-2016",
        title="General Data Protection Regulation",
        short_name="GDPR",
        jurisdiction="EU",
    )
    db.add(mandate_a)
    db.flush()
    obligation_a = RegulatoryObligation(
        organization_id=org_a.id,
        mandate_id=mandate_a.id,
        obligation_code="GDPR-ART-32-ALPHA",
        title="Security of Processing",
        description="Encryption and confidentiality of personal data",
        article_reference="Article 32",
        applicability=RegulatoryApplicabilityEnum.APPLICABLE,
        organization_control_id=ctrl_a.id,
        compliance_status=RegulatoryComplianceStatusEnum.COMPLIANT,
    )
    db.add(obligation_a)
    db.commit()

    def _tok(u: User) -> str:
        role_str = u.role.value if hasattr(u.role, "value") else str(u.role)
        return create_access_token(
            subject=u.id,
            organization_id=u.organization_id,
            role=role_str,
        )

    tokens = {
        "admin_a": _tok(user_admin_a),
        "mgr_a": _tok(user_mgr_a),
        "analyst_a": _tok(user_analyst_a),
        "sec_a": _tok(user_sec_a),
        "auditor_a": _tok(user_auditor_a),
        "viewer_a": _tok(user_viewer_a),
        "admin_b": _tok(user_admin_b),
    }

    return {
        "org_a": org_a,
        "org_b": org_b,
        "users_a": {
            "admin": user_admin_a,
            "mgr": user_mgr_a,
            "analyst": user_analyst_a,
            "sec": user_sec_a,
            "auditor": user_auditor_a,
            "viewer": user_viewer_a,
            "inactive": user_inactive_a,
        },
        "users_b": {"admin": user_admin_b},
        "ctrl_a": ctrl_a,
        "ctrl_b": ctrl_b,
        "ev_accepted_a": ev_accepted_a,
        "ev_rejected_a": ev_rejected_a,
        "ev_superseded_a": ev_superseded_a,
        "ev_accepted_b": ev_accepted_b,
        "cloud_a": cloud_a,
        "cloud_drifted_a": cloud_drifted_a,
        "cloud_b": cloud_b,
        "ropa_a": ropa_a,
        "ropa_b": ropa_b,
        "tokens": tokens,
    }


def _create_active_scheme(client: TestClient, creator_headers: dict, approver_headers: dict, code: str = "SCH-STD-01", version: int = 1):
    res = client.post(
        "/api/v1/data-governance/schemes",
        json={
            "scheme_code": code,
            "name": f"Enterprise Classification {code} v{version}",
            "description": "Standard 5-tier scheme",
            "version": version,
            "is_default": True,
        },
        headers=creator_headers,
    )
    assert res.status_code == 201
    scheme_id = res.json()["id"]

    levels_spec = [
        ("L1-PUB", "Public", 1, "PUBLIC", False, False),
        ("L2-INT", "Internal", 2, "INTERNAL", True, False),
        ("L3-CONF", "Confidential", 3, "CONFIDENTIAL", True, False),
        ("L4-PII", "Restricted PII", 4, "RESTRICTED_PII", True, True),
        ("L5-PHI", "Special Category PHI", 5, "SPECIAL_CATEGORY_SENSITIVE_PHI", True, True),
    ]
    for l_code, l_name, rank, sens, enc_rest, four_eyes in levels_spec:
        r_lvl = client.post(
            f"/api/v1/data-governance/schemes/{scheme_id}/levels",
            json={
                "level_code": l_code,
                "name": l_name,
                "ordinal_rank": rank,
                "mapped_sensitivity_level": sens,
                "requires_encryption_at_rest": enc_rest,
                "requires_encryption_in_transit": True,
                "requires_four_eyes_approval": four_eyes,
            },
            headers=creator_headers,
        )
        assert r_lvl.status_code == 201

    sub = client.post(
        f"/api/v1/data-governance/schemes/{scheme_id}/submit",
        headers=creator_headers,
    )
    assert sub.status_code == 200
    app = client.post(
        f"/api/v1/data-governance/schemes/{scheme_id}/approve",
        headers=approver_headers,
    )
    assert app.status_code == 200
    return app.json()


# ─────────────────────────────────────────────────────────────────────────────
# 1. AUTHENTICATION & 6-ROLE RBAC MATRIX (SEC-B3-01 to SEC-B3-04)
# ─────────────────────────────────────────────────────────────────────────────

def test_sec_b3_01_to_04_unauthenticated_and_rbac_matrix(client: TestClient, dg_api_env):
    """SEC-B3-01 to SEC-B3-04: Unauthenticated 401 and strict 6-role RBAC enforcement."""
    # SEC-B3-01: Unauthenticated request -> 401
    assert client.get("/api/v1/data-governance/summary").status_code == 401
    assert client.get("/api/v1/data-governance/assets").status_code == 401

    h_viewer = auth_header(dg_api_env["tokens"]["viewer_a"])
    h_auditor = auth_header(dg_api_env["tokens"]["auditor_a"])
    h_sec = auth_header(dg_api_env["tokens"]["sec_a"])
    h_analyst = auth_header(dg_api_env["tokens"]["analyst_a"])
    h_mgr = auth_header(dg_api_env["tokens"]["mgr_a"])

    # Viewer and Auditor can read summary & assets
    assert client.get("/api/v1/data-governance/summary", headers=h_viewer).status_code == 200
    assert client.get("/api/v1/data-governance/summary", headers=h_auditor).status_code == 200

    # SEC-B3-02: Viewer / Auditor / Security Analyst attempting POST /schemes or POST /assets -> 403
    scheme_payload = {"scheme_code": "SCH-RBAC-01", "name": "RBAC Scheme"}
    assert client.post("/api/v1/data-governance/schemes", json=scheme_payload, headers=h_viewer).status_code == 403
    assert client.post("/api/v1/data-governance/schemes", json=scheme_payload, headers=h_auditor).status_code == 403
    assert client.post("/api/v1/data-governance/schemes", json=scheme_payload, headers=h_sec).status_code == 403

    asset_payload = {
        "asset_code": "DA-RBAC-01",
        "name": "RBAC Asset",
        "description": "Testing RBAC",
    }
    assert client.post("/api/v1/data-governance/assets", json=asset_payload, headers=h_viewer).status_code == 403
    assert client.post("/api/v1/data-governance/assets", json=asset_payload, headers=h_auditor).status_code == 403
    assert client.post("/api/v1/data-governance/assets", json=asset_payload, headers=h_sec).status_code == 403

    # Create active scheme and asset via GRC_ANALYST + MANAGER
    scheme = _create_active_scheme(client, h_analyst, h_mgr, "SCH-RBAC-MAIN")
    l4_id = [lvl["id"] for lvl in scheme["levels"] if lvl["mapped_sensitivity_level"] == "RESTRICTED_PII"][0]

    r_asset = client.post("/api/v1/data-governance/assets", json=asset_payload, headers=h_analyst)
    assert r_asset.status_code == 201
    asset_id = r_asset.json()["id"]

    # SECURITY_ANALYST has DATA_GOV_CLASSIFY & DATA_GOV_LINEAGE_MANAGE, so can submit classification
    r_class = client.post(
        f"/api/v1/data-governance/assets/{asset_id}/classifications",
        json={
            "scheme_id": scheme["id"],
            "level_id": l4_id,
            "justification": "Security analyst classification submission for restricted PII store.",
            "require_approval": True,
        },
        headers=h_sec,
    )
    assert r_class.status_code == 201
    rec_id = r_class.json()["id"]

    # SEC-B3-03: GRC_ANALYST or SECURITY_ANALYST attempting POST /classifications/{id}/approve -> 403
    assert (
        client.post(f"/api/v1/data-governance/classifications/{rec_id}/approve", headers=h_analyst).status_code == 403
    )
    assert (
        client.post(f"/api/v1/data-governance/classifications/{rec_id}/approve", headers=h_sec).status_code == 403
    )

    # SEC-B3-04: SECURITY_ANALYST attempting POST /assets/{id}/ownership or POST /retire -> 403
    assert (
        client.post(
            f"/api/v1/data-governance/assets/{asset_id}/ownership",
            json={
                "owner_id": dg_api_env["users_a"]["mgr"].id,
                "justification": "Attempted ownership transfer by sec analyst",
            },
            headers=h_sec,
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/data-governance/assets/{asset_id}/retire",
            json={
                "disposal_method": "CRYPTOGRAPHIC_ERASURE",
                "retirement_evidence_id": dg_api_env["ev_accepted_a"].id,
                "retirement_notes": "Attempted retirement finalization by sec analyst",
            },
            headers=h_sec,
        ).status_code
        == 403
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. MULTI-TENANT ISOLATION (SEC-B3-05 to SEC-B3-10)
# ─────────────────────────────────────────────────────────────────────────────

def test_sec_b3_05_to_10_multi_tenant_isolation(client: TestClient, dg_api_env):
    """SEC-B3-05 to SEC-B3-10: Cross-tenant reads and foreign-key injections return HTTP 404."""
    h_analyst_a = auth_header(dg_api_env["tokens"]["analyst_a"])
    h_mgr_a = auth_header(dg_api_env["tokens"]["mgr_a"])
    h_admin_b = auth_header(dg_api_env["tokens"]["admin_b"])

    scheme_a = _create_active_scheme(client, h_analyst_a, h_mgr_a, "SCH-ALPHA-ISO")
    level_a_id = scheme_a["levels"][0]["id"]

    asset_a = client.post(
        "/api/v1/data-governance/assets",
        json={
            "asset_code": "DA-ALPHA-01",
            "name": "Alpha Asset 1",
            "description": "Primary Alpha asset",
        },
        headers=h_analyst_a,
    ).json()

    asset_b = client.post(
        "/api/v1/data-governance/assets",
        json={
            "asset_code": "DA-BETA-01",
            "name": "Beta Asset 1",
            "description": "Primary Beta asset",
        },
        headers=h_admin_b,
    ).json()

    # SEC-B3-05: Tenant B reads/mutates Tenant A scheme or asset -> 404
    assert client.get(f"/api/v1/data-governance/schemes/{scheme_a['id']}", headers=h_admin_b).status_code == 404
    assert client.get(f"/api/v1/data-governance/assets/{asset_a['id']}", headers=h_admin_b).status_code == 404
    assert (
        client.put(
            f"/api/v1/data-governance/assets/{asset_a['id']}",
            json={"name": "Hijacked"},
            headers=h_admin_b,
        ).status_code
        == 404
    )

    # SEC-B3-06: Tenant A creates lineage edge referencing Tenant B asset -> 404
    assert (
        client.post(
            "/api/v1/data-governance/lineage-edges",
            json={
                "edge_code": "LIN-CROSS-TENANT",
                "source_data_asset_id": asset_a["id"],
                "target_data_asset_id": asset_b["id"],
                "relationship_type": "ETL_TRANSFORMATION",
                "transformation_summary": "Cross-tenant exfiltration attempt",
            },
            headers=h_analyst_a,
        ).status_code
        == 404
    )

    # SEC-B3-07: Tenant A links DataAsset to Tenant B ProcessingActivity, OrganizationControl, EvidenceItem, CloudAsset -> 404
    assert (
        client.post(
            f"/api/v1/data-governance/assets/{asset_a['id']}/processing-links",
            json={"processing_activity_id": dg_api_env["ropa_b"].id, "usage_role": "PRIMARY_SOURCE"},
            headers=h_analyst_a,
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/data-governance/assets/{asset_a['id']}/control-links",
            json={
                "organization_control_id": dg_api_env["ctrl_b"].id,
                "control_objective": "ENCRYPTION_AT_REST",
            },
            headers=h_analyst_a,
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/data-governance/assets/{asset_a['id']}/evidence-links",
            json={
                "evidence_item_id": dg_api_env["ev_accepted_b"].id,
                "evidence_purpose": "CLASSIFICATION_JUSTIFICATION",
            },
            headers=h_analyst_a,
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/data-governance/assets/{asset_a['id']}/cloud-links",
            json={"cloud_asset_id": dg_api_env["cloud_b"].id, "hosting_role": "PRIMARY_STORE"},
            headers=h_analyst_a,
        ).status_code
        == 404
    )

    # SEC-B3-08: Tenant A assigns owner_id or steward_id belonging to Tenant B user -> 404
    assert (
        client.post(
            f"/api/v1/data-governance/assets/{asset_a['id']}/ownership",
            json={
                "owner_id": dg_api_env["users_b"]["admin"].id,
                "justification": "Assigning foreign tenant owner",
            },
            headers=h_analyst_a,
        ).status_code
        == 404
    )

    # SEC-B3-09: Tenant B classifies Tenant B asset using Tenant A scheme/level -> 404
    assert (
        client.post(
            f"/api/v1/data-governance/assets/{asset_b['id']}/classifications",
            json={
                "scheme_id": scheme_a["id"],
                "level_id": level_a_id,
                "justification": "Cross-tenant scheme injection attempt.",
            },
            headers=h_admin_b,
        ).status_code
        == 404
    )

    # SEC-B3-10: Tenant B queries classifications of Tenant A asset -> 404
    assert (
        client.get(f"/api/v1/data-governance/assets/{asset_a['id']}/classifications", headers=h_admin_b).status_code
        == 404
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. MASS ASSIGNMENT & INPUT VALIDATION (SEC-B3-11 to SEC-B3-15)
# ─────────────────────────────────────────────────────────────────────────────

def test_sec_b3_11_to_15_mass_assignment_and_legacy_downgrade_bypass(client: TestClient, dg_api_env):
    """SEC-B3-11 to SEC-B3-15: extra='forbid' rejects injected fields and legacy endpoint blocks unapproved downgrades."""
    h_analyst = auth_header(dg_api_env["tokens"]["analyst_a"])
    h_mgr = auth_header(dg_api_env["tokens"]["mgr_a"])

    # SEC-B3-11: Injecting organization_id in request body -> 422
    assert (
        client.post(
            "/api/v1/data-governance/assets",
            json={
                "organization_id": 9999,
                "asset_code": "DA-MASS-01",
                "name": "Mass Assign 1",
            },
            headers=h_analyst,
        ).status_code
        == 422
    )

    # SEC-B3-12: Injecting status='APPROVED', approved_by_id, provenance_hash -> 422
    assert (
        client.post(
            "/api/v1/data-governance/assets/1/classifications",
            json={
                "scheme_id": 1,
                "level_id": 1,
                "justification": "Valid length justification",
                "status": "APPROVED",
                "approved_by_id": 1,
            },
            headers=h_analyst,
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/data-governance/lineage-edges",
            json={
                "edge_code": "LIN-FORGE-01",
                "source_data_asset_id": 1,
                "target_data_asset_id": 2,
                "provenance_hash": "f" * 64,
            },
            headers=h_analyst,
        ).status_code
        == 422
    )

    # SEC-B3-13: Injecting unexpected unknown field is_admin -> 422
    assert (
        client.post(
            "/api/v1/data-governance/schemes",
            json={
                "scheme_code": "SCH-PROTO",
                "name": "Proto Scheme",
                "is_admin": True,
            },
            headers=h_analyst,
        ).status_code
        == 422
    )

    # SEC-B3-14: Creating governed asset with initial_lifecycle_state="ACTIVE" or "RETIRED" -> 422
    assert (
        client.post(
            "/api/v1/data-governance/assets",
            json={
                "asset_code": "DA-JUMP-ACTIVE",
                "name": "Jump Active",
                "initial_lifecycle_state": "ACTIVE",
            },
            headers=h_analyst,
        ).status_code
        == 422
    )

    # SEC-B3-15: Direct sensitivity downgrade via legacy PUT /api/v1/privacy/data-assets/{id} on governed classified asset -> 409
    scheme = _create_active_scheme(client, h_analyst, h_mgr, "SCH-LEGACY-GUARD")
    l4_id = [lvl["id"] for lvl in scheme["levels"] if lvl["mapped_sensitivity_level"] == "RESTRICTED_PII"][0]

    asset = client.post(
        "/api/v1/data-governance/assets",
        json={
            "asset_code": "DA-LEGACY-GUARD",
            "name": "Governed PII Asset",
        },
        headers=h_analyst,
    ).json()

    rec = client.post(
        f"/api/v1/data-governance/assets/{asset['id']}/classifications",
        json={
            "scheme_id": scheme["id"],
            "level_id": l4_id,
            "justification": "Initial restricted PII classification.",
        },
        headers=h_analyst,
    ).json()
    client.post(f"/api/v1/data-governance/classifications/{rec['id']}/approve", headers=h_mgr)

    # Attempt to downgrade sensitivity directly via Phase 16 legacy endpoint
    r_legacy_downgrade = client.put(
        f"/api/v1/privacy/data-assets/{asset['id']}",
        json={"data_sensitivity_level": "PUBLIC"},
        headers=h_mgr,
    )
    assert r_legacy_downgrade.status_code == 422
    assert "classification approval workflow" in r_legacy_downgrade.json()["detail"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# 4. SCHEME INTEGRITY & CLASSIFICATION FOUR-EYES (SEC-B3-16 to SEC-B3-25)
# ─────────────────────────────────────────────────────────────────────────────

def test_sec_b3_16_to_25_scheme_and_classification_four_eyes(client: TestClient, dg_api_env):
    """SEC-B3-16 to SEC-B3-25: Scheme rank validation, immutability, Four-Eyes SoD, and downgrade lock."""
    h_analyst = auth_header(dg_api_env["tokens"]["analyst_a"])
    h_mgr = auth_header(dg_api_env["tokens"]["mgr_a"])
    h_admin = auth_header(dg_api_env["tokens"]["admin_a"])

    # SEC-B3-16: Non-monotonic ordinal_rank (rank 2 mapped to RESTRICTED_PII, rank 3 mapped to PUBLIC) -> 422
    bad_scheme = client.post(
        "/api/v1/data-governance/schemes",
        json={"scheme_code": "SCH-BAD-RANK", "name": "Inverted Ranks"},
        headers=h_analyst,
    ).json()
    client.post(
        f"/api/v1/data-governance/schemes/{bad_scheme['id']}/levels",
        json={
            "level_code": "L1",
            "name": "High Sensitivity Low Rank",
            "ordinal_rank": 2,
            "mapped_sensitivity_level": "RESTRICTED_PII",
        },
        headers=h_analyst,
    )
    r_bad_rank = client.post(
        f"/api/v1/data-governance/schemes/{bad_scheme['id']}/levels",
        json={
            "level_code": "L2",
            "name": "Low Sensitivity High Rank",
            "ordinal_rank": 3,
            "mapped_sensitivity_level": "PUBLIC",
        },
        headers=h_analyst,
    )
    assert r_bad_rank.status_code == 422

    # SEC-B3-17: Self-approval of scheme by creator (even if creator is MANAGER) -> 403
    mgr_scheme = client.post(
        "/api/v1/data-governance/schemes",
        json={"scheme_code": "SCH-MGR-SELF", "name": "Manager Created Scheme", "version": 1},
        headers=h_mgr,
    ).json()
    client.post(
        f"/api/v1/data-governance/schemes/{mgr_scheme['id']}/levels",
        json={"level_code": "L1", "name": "Public", "ordinal_rank": 1, "mapped_sensitivity_level": "PUBLIC"},
        headers=h_mgr,
    )
    client.post(
        f"/api/v1/data-governance/schemes/{mgr_scheme['id']}/levels",
        json={"level_code": "L2", "name": "Internal", "ordinal_rank": 2, "mapped_sensitivity_level": "INTERNAL"},
        headers=h_mgr,
    )
    client.post(f"/api/v1/data-governance/schemes/{mgr_scheme['id']}/submit", headers=h_mgr)
    r_self_scheme = client.post(f"/api/v1/data-governance/schemes/{mgr_scheme['id']}/approve", headers=h_mgr)
    assert r_self_scheme.status_code == 403

    # Approve via ADMIN (different user)
    r_admin_app = client.post(f"/api/v1/data-governance/schemes/{mgr_scheme['id']}/approve", headers=h_admin)
    assert r_admin_app.status_code == 200
    mgr_scheme = r_admin_app.json()

    # SEC-B3-18: Adding level to ACTIVE scheme -> 409
    r_add_active = client.post(
        f"/api/v1/data-governance/schemes/{mgr_scheme['id']}/levels",
        json={
            "level_code": "L3",
            "name": "Confidential",
            "ordinal_rank": 3,
            "mapped_sensitivity_level": "CONFIDENTIAL",
        },
        headers=h_analyst,
    )
    assert r_add_active.status_code == 409

    # Create a newer version v2 of SCH-MGR-SELF and approve it -> v1 becomes SUPERSEDED
    mgr_scheme_v2 = _create_active_scheme(client, h_mgr, h_admin, "SCH-MGR-SELF", version=2)

    # SEC-B3-19: Submitting classification against SUPERSEDED scheme v1 -> 422
    asset = client.post(
        "/api/v1/data-governance/assets",
        json={"asset_code": "DA-CLASS-01", "name": "Classification Test Asset"},
        headers=h_analyst,
    ).json()
    r_sup_scheme = client.post(
        f"/api/v1/data-governance/assets/{asset['id']}/classifications",
        json={
            "scheme_id": mgr_scheme["id"],
            "level_id": mgr_scheme["levels"][0]["id"],
            "justification": "Trying superseded scheme.",
        },
        headers=h_analyst,
    )
    assert r_sup_scheme.status_code == 422

    # SEC-B3-23: Submitting classification with level_id belonging to a different scheme -> 422
    assert (
        client.post(
            f"/api/v1/data-governance/assets/{asset['id']}/classifications",
            json={
                "scheme_id": mgr_scheme_v2["id"],
                "level_id": mgr_scheme["levels"][0]["id"],
                "justification": "Cross-scheme level mismatch.",
            },
            headers=h_analyst,
        ).status_code
        == 422
    )

    l1_v2 = [l["id"] for l in mgr_scheme_v2["levels"] if l["mapped_sensitivity_level"] == "PUBLIC"][0]
    l4_v2 = [l["id"] for l in mgr_scheme_v2["levels"] if l["mapped_sensitivity_level"] == "RESTRICTED_PII"][0]

    # SEC-B3-20: Self-approval of classification record by requester (mgr submits and tries to approve) -> 403
    rec_mgr = client.post(
        f"/api/v1/data-governance/assets/{asset['id']}/classifications",
        json={
            "scheme_id": mgr_scheme_v2["id"],
            "level_id": l4_v2,
            "justification": "Manager initial classification as Restricted PII.",
        },
        headers=h_mgr,
    ).json()
    assert (
        client.post(f"/api/v1/data-governance/classifications/{rec_mgr['id']}/approve", headers=h_mgr).status_code
        == 403
    )

    # SEC-B3-21: Rejecting classification record with empty rejection_reason -> 422
    assert (
        client.post(
            f"/api/v1/data-governance/classifications/{rec_mgr['id']}/reject",
            json={"rejection_reason": "   "},
            headers=h_admin,
        ).status_code
        == 422
    )

    # Approve initial RESTRICTED_PII classification via ADMIN
    assert (
        client.post(f"/api/v1/data-governance/classifications/{rec_mgr['id']}/approve", headers=h_admin).status_code
        == 200
    )

    # SEC-B3-22: Submitting classification with blank/short justification -> 422
    assert (
        client.post(
            f"/api/v1/data-governance/assets/{asset['id']}/classifications",
            json={
                "scheme_id": mgr_scheme_v2["id"],
                "level_id": l1_v2,
                "justification": "   ",
            },
            headers=h_analyst,
        ).status_code
        == 422
    )

    # SEC-B3-24: Pending downgrade must NOT lower DataAsset.data_sensitivity_level before approval
    downgrade_rec = client.post(
        f"/api/v1/data-governance/assets/{asset['id']}/classifications",
        json={
            "scheme_id": mgr_scheme_v2["id"],
            "level_id": l1_v2,
            "justification": "Dataset sanitized of all PII fields and verified.",
        },
        headers=h_analyst,
    ).json()
    assert downgrade_rec["change_type"] == "DOWNGRADE"
    assert downgrade_rec["status"] == "PENDING_APPROVAL"
    dossier_mid = client.get(f"/api/v1/data-governance/assets/{asset['id']}", headers=h_analyst).json()
    assert dossier_mid["asset"]["data_sensitivity_level"] == "RESTRICTED_PII"
    assert dossier_mid["asset"]["classification_status"] == "PENDING_APPROVAL"

    # SEC-B3-25: Submitting a second classification while one is already PENDING_APPROVAL -> 409
    assert (
        client.post(
            f"/api/v1/data-governance/assets/{asset['id']}/classifications",
            json={
                "scheme_id": mgr_scheme_v2["id"],
                "level_id": l1_v2,
                "justification": "Concurrent classification request while one is pending.",
            },
            headers=h_analyst,
        ).status_code
        == 409
    )

    # Approve downgrade via MANAGER -> sensitivity now updates to PUBLIC
    client.post(f"/api/v1/data-governance/classifications/{downgrade_rec['id']}/approve", headers=h_mgr)
    dossier_after = client.get(f"/api/v1/data-governance/assets/{asset['id']}", headers=h_analyst).json()
    assert dossier_after["asset"]["data_sensitivity_level"] == "PUBLIC"
    assert dossier_after["asset"]["classification_status"] == "APPROVED"


# ─────────────────────────────────────────────────────────────────────────────
# 5. DATA LINEAGE DAG CYCLES & SENSITIVITY GATING (SEC-B3-26 to SEC-B3-31)
# ─────────────────────────────────────────────────────────────────────────────

def test_sec_b3_26_to_31_lineage_dag_and_sensitivity_flow(client: TestClient, dg_api_env):
    """SEC-B3-26 to SEC-B3-31: Self-loop, 2-hop/multi-hop cycles, sensitivity flow gating, Four-Eyes approval."""
    h_analyst = auth_header(dg_api_env["tokens"]["analyst_a"])
    h_mgr = auth_header(dg_api_env["tokens"]["mgr_a"])
    h_admin = auth_header(dg_api_env["tokens"]["admin_a"])

    def _mk_asset(code: str, sens: str):
        r = client.post(
            "/api/v1/data-governance/assets",
            json={
                "asset_code": code,
                "name": f"Asset {code}",
                "data_sensitivity_level": sens,
            },
            headers=h_analyst,
        )
        assert r.status_code == 201
        return r.json()

    a1 = _mk_asset("DA-LIN-A1", "RESTRICTED_PII")
    a2 = _mk_asset("DA-LIN-A2", "RESTRICTED_PII")
    a3 = _mk_asset("DA-LIN-A3", "RESTRICTED_PII")
    a4 = _mk_asset("DA-LIN-A4", "RESTRICTED_PII")
    pub_target = _mk_asset("DA-LIN-PUB", "PUBLIC")
    conf_target = _mk_asset("DA-LIN-CONF", "CONFIDENTIAL")

    # SEC-B3-26: Self-loop lineage edge (A1 -> A1) -> 422
    assert (
        client.post(
            "/api/v1/data-governance/lineage-edges",
            json={
                "edge_code": "LIN-SELF-01",
                "source_data_asset_id": a1["id"],
                "target_data_asset_id": a1["id"],
                "relationship_type": "ETL_TRANSFORMATION",
                "transformation_summary": "Self loop",
            },
            headers=h_analyst,
        ).status_code
        == 422
    )

    # Create A1 -> A2 -> A3 -> A4
    assert (
        client.post(
            "/api/v1/data-governance/lineage-edges",
            json={
                "edge_code": "LIN-12",
                "source_data_asset_id": a1["id"],
                "target_data_asset_id": a2["id"],
                "relationship_type": "ETL_TRANSFORMATION",
                "transformation_summary": "A1 to A2",
            },
            headers=h_analyst,
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/data-governance/lineage-edges",
            json={
                "edge_code": "LIN-23",
                "source_data_asset_id": a2["id"],
                "target_data_asset_id": a3["id"],
                "relationship_type": "ETL_TRANSFORMATION",
                "transformation_summary": "A2 to A3",
            },
            headers=h_analyst,
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/data-governance/lineage-edges",
            json={
                "edge_code": "LIN-34",
                "source_data_asset_id": a3["id"],
                "target_data_asset_id": a4["id"],
                "relationship_type": "ETL_TRANSFORMATION",
                "transformation_summary": "A3 to A4",
            },
            headers=h_analyst,
        ).status_code
        == 201
    )

    # SEC-B3-27: 2-hop cycle (A2 -> A1) and 3-hop cycle (A3 -> A1) -> 422
    assert (
        client.post(
            "/api/v1/data-governance/lineage-edges",
            json={
                "edge_code": "LIN-21-CYCLE",
                "source_data_asset_id": a2["id"],
                "target_data_asset_id": a1["id"],
            },
            headers=h_analyst,
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/data-governance/lineage-edges",
            json={
                "edge_code": "LIN-31-CYCLE",
                "source_data_asset_id": a3["id"],
                "target_data_asset_id": a1["id"],
            },
            headers=h_analyst,
        ).status_code
        == 422
    )

    # SEC-B3-28: Multi-hop cycle (A4 -> A1) -> 422
    assert (
        client.post(
            "/api/v1/data-governance/lineage-edges",
            json={
                "edge_code": "LIN-41-CYCLE",
                "source_data_asset_id": a4["id"],
                "target_data_asset_id": a1["id"],
            },
            headers=h_analyst,
        ).status_code
        == 422
    )

    # SEC-B3-29: Unmasked RESTRICTED_PII -> PUBLIC -> 422
    assert (
        client.post(
            "/api/v1/data-governance/lineage-edges",
            json={
                "edge_code": "LIN-PII-PUB-UNMASKED",
                "source_data_asset_id": a1["id"],
                "target_data_asset_id": pub_target["id"],
                "is_masked_or_anonymized": False,
                "transformation_summary": "Unmasked PII to public bucket",
            },
            headers=h_analyst,
        ).status_code
        == 422
    )

    # SEC-B3-30: RESTRICTED_PII -> CONFIDENTIAL without transformation_summary -> 422; with masking + summary -> 201 PENDING_APPROVAL
    assert (
        client.post(
            "/api/v1/data-governance/lineage-edges",
            json={
                "edge_code": "LIN-PII-CONF-NOTX",
                "source_data_asset_id": a1["id"],
                "target_data_asset_id": conf_target["id"],
                "is_masked_or_anonymized": True,
            },
            headers=h_analyst,
        ).status_code
        == 422
    )
    r_masked = client.post(
        "/api/v1/data-governance/lineage-edges",
        json={
            "edge_code": "LIN-PII-CONF-MASKED",
            "source_data_asset_id": a1["id"],
            "target_data_asset_id": conf_target["id"],
            "relationship_type": "AGGREGATION",
            "transformation_summary": "Tokenized PII to Confidential analytics mart",
            "is_masked_or_anonymized": True,
        },
        headers=h_mgr,
    )
    assert r_masked.status_code == 201
    masked_edge = r_masked.json()
    assert masked_edge["status"] == "PENDING_APPROVAL"

    # SEC-B3-31: Self-approval of lineage edge by creator (mgr created it, tries to approve) -> 403
    assert (
        client.post(f"/api/v1/data-governance/lineage-edges/{masked_edge['id']}/approve", headers=h_mgr).status_code
        == 403
    )
    # Approve via ADMIN -> 200
    assert (
        client.post(f"/api/v1/data-governance/lineage-edges/{masked_edge['id']}/approve", headers=h_admin).status_code
        == 200
    )


# ─────────────────────────────────────────────────────────────────────────────
# 6. OWNERSHIP, LIFECYCLE & RETIREMENT PREREQUISITES (SEC-B3-32 to SEC-B3-41, SEC-B3-45)
# ─────────────────────────────────────────────────────────────────────────────

def test_sec_b3_32_to_41_and_45_ownership_and_retirement(client: TestClient, dg_api_env):
    """SEC-B3-32 to SEC-B3-41, SEC-B3-45: Ownership SoD, inactive user block, retirement gates, and retired lock."""
    h_analyst = auth_header(dg_api_env["tokens"]["analyst_a"])
    h_mgr = auth_header(dg_api_env["tokens"]["mgr_a"])
    h_admin = auth_header(dg_api_env["tokens"]["admin_a"])

    scheme = _create_active_scheme(client, h_analyst, h_mgr, "SCH-LIFE-01")
    l3_id = [lvl["id"] for lvl in scheme["levels"] if lvl["mapped_sensitivity_level"] == "CONFIDENTIAL"][0]

    # Create DISCOVERED asset
    disc = client.post(
        "/api/v1/data-governance/assets",
        json={
            "asset_code": "DA-LIFE-01",
            "name": "Lifecycle Governed Asset",
            "initial_lifecycle_state": "DISCOVERED",
        },
        headers=h_analyst,
    ).json()
    asset_id = disc["id"]

    # SEC-B3-36: Activating asset before classification is APPROVED -> 422
    assert client.post(f"/api/v1/data-governance/assets/{asset_id}/activate", headers=h_analyst).status_code == 422

    # SEC-B3-32: Assigning inactive user as owner or steward -> 422
    assert (
        client.post(
            f"/api/v1/data-governance/assets/{asset_id}/register",
            json={
                "owner_id": dg_api_env["users_a"]["inactive"].id,
                "steward_id": dg_api_env["users_a"]["analyst"].id,
            },
            headers=h_analyst,
        ).status_code
        == 422
    )

    # Register with valid active owner & steward
    reg = client.post(
        f"/api/v1/data-governance/assets/{asset_id}/register",
        json={
            "owner_id": dg_api_env["users_a"]["analyst"].id,
            "steward_id": dg_api_env["users_a"]["sec"].id,
        },
        headers=h_analyst,
    )
    assert reg.status_code == 200
    assert reg.json()["lifecycle_state"] == "REGISTERED"

    # Classify & approve -> CLASSIFIED -> activate -> ACTIVE
    rec = client.post(
        f"/api/v1/data-governance/assets/{asset_id}/classifications",
        json={
            "scheme_id": scheme["id"],
            "level_id": l3_id,
            "justification": "Confidential classification for lifecycle test.",
        },
        headers=h_analyst,
    ).json()
    act = client.post(f"/api/v1/data-governance/assets/{asset_id}/activate", headers=h_analyst)
    assert act.status_code == 200
    assert act.json()["lifecycle_state"] == "ACTIVE"

    # Request ownership transfer on ACTIVE asset (requires approval)
    own_req = client.post(
        f"/api/v1/data-governance/assets/{asset_id}/ownership",
        json={
            "owner_id": dg_api_env["users_a"]["mgr"].id,
            "justification": "Transferring ownership to Governance Manager",
            "require_approval": True,
        },
        headers=h_mgr,
    )
    assert own_req.status_code == 200
    assert own_req.json()["owner_transfer_status"] == "PENDING_TRANSFER"

    # SEC-B3-34: Requesting second ownership transfer while one is already PENDING_APPROVAL -> 409
    assert (
        client.post(
            f"/api/v1/data-governance/assets/{asset_id}/ownership",
            json={
                "owner_id": dg_api_env["users_a"]["admin"].id,
                "justification": "Concurrent ownership transfer request",
                "require_approval": True,
            },
            headers=h_analyst,
        ).status_code
        == 409
    )

    # SEC-B3-33: Self-approval of ownership transfer by requester (mgr requested, mgr tries to approve) -> 403
    assert (
        client.post(f"/api/v1/data-governance/assets/{asset_id}/ownership/approve", headers=h_mgr).status_code == 403
    )
    # Approve ownership transfer via ADMIN -> 200
    own_app = client.post(f"/api/v1/data-governance/assets/{asset_id}/ownership/approve", headers=h_admin)
    assert own_app.status_code == 200
    assert own_app.json()["owner_id"] == dg_api_env["users_a"]["mgr"].id
    assert own_app.json()["owner_transfer_status"] == "APPROVED"

    # SEC-B3-37: Retiring CONFIDENTIAL asset without retirement_evidence_id -> 422
    assert (
        client.post(
            f"/api/v1/data-governance/assets/{asset_id}/retire-request",
            json={
                "disposal_method": "CRYPTOGRAPHIC_ERASURE",
                "retirement_evidence_id": None,
                "retirement_notes": "Trying to retire confidential asset without evidence",
            },
            headers=h_analyst,
        ).status_code
        == 422
    )

    # SEC-B3-38: Retiring asset with disposal_method="NONE" -> 422
    assert (
        client.post(
            f"/api/v1/data-governance/assets/{asset_id}/retire-request",
            json={
                "disposal_method": "NONE",
                "retirement_evidence_id": dg_api_env["ev_accepted_a"].id,
                "retirement_notes": "Trying to retire with NONE disposal method",
            },
            headers=h_analyst,
        ).status_code
        == 422
    )

    # SEC-B3-39: Retiring asset with REJECTED or SUPERSEDED EvidenceItem -> 422
    assert (
        client.post(
            f"/api/v1/data-governance/assets/{asset_id}/retire-request",
            json={
                "disposal_method": "CRYPTOGRAPHIC_ERASURE",
                "retirement_evidence_id": dg_api_env["ev_rejected_a"].id,
                "retirement_notes": "Using rejected evidence",
            },
            headers=h_analyst,
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"/api/v1/data-governance/assets/{asset_id}/retire-request",
            json={
                "disposal_method": "CRYPTOGRAPHIC_ERASURE",
                "retirement_evidence_id": dg_api_env["ev_superseded_a"].id,
                "retirement_notes": "Using superseded evidence",
            },
            headers=h_analyst,
        ).status_code
        == 422
    )

    # Submit valid retirement request (by mgr)
    ret_req = client.post(
        f"/api/v1/data-governance/assets/{asset_id}/retire-request",
        json={
            "disposal_method": "CRYPTOGRAPHIC_ERASURE",
            "retirement_evidence_id": dg_api_env["ev_accepted_a"].id,
            "retirement_notes": "Valid retirement request with destruction certificate",
        },
        headers=h_mgr,
    )
    assert ret_req.status_code == 200
    assert ret_req.json()["lifecycle_state"] == "DEPRECATED"

    # SEC-B3-40: Self-approval of retirement by requester (mgr requested, mgr tries to finalize) -> 403
    assert (
        client.post(
            f"/api/v1/data-governance/assets/{asset_id}/retire",
            json={
                "disposal_method": "CRYPTOGRAPHIC_ERASURE",
                "retirement_evidence_id": dg_api_env["ev_accepted_a"].id,
                "retirement_notes": "Manager attempting self-approval of retirement",
            },
            headers=h_mgr,
        ).status_code
        == 403
    )

    # Finalize retirement via ADMIN -> RETIRED
    ret_app = client.post(
        f"/api/v1/data-governance/assets/{asset_id}/retire",
        json={
            "disposal_method": "CRYPTOGRAPHIC_ERASURE",
            "retirement_evidence_id": dg_api_env["ev_accepted_a"].id,
            "retirement_notes": "Admin finalized retirement with destruction certificate",
        },
        headers=h_admin,
    )
    assert ret_app.status_code == 200
    assert ret_app.json()["lifecycle_state"] == "RETIRED"

    downstream_asset = client.post(
        "/api/v1/data-governance/assets",
        json={"asset_code": "DA-LIFE-DOWN-02", "name": "Downstream Asset"},
        headers=h_analyst,
    ).json()

    # SEC-B3-35 & SEC-B3-41: Mutating, re-classifying, or linking a RETIRED asset -> 409; self-restoring by retirer -> 403
    assert (
        client.put(
            f"/api/v1/data-governance/assets/{asset_id}",
            json={"name": "Mutate Retired"},
            headers=h_admin,
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/v1/data-governance/assets/{asset_id}/ownership",
            json={
                "owner_id": dg_api_env["users_a"]["analyst"].id,
                "justification": "Try transfer retired",
            },
            headers=h_admin,
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/v1/data-governance/assets/{asset_id}/classifications",
            json={
                "scheme_id": scheme["id"],
                "level_id": l3_id,
                "justification": "Try classify retired",
            },
            headers=h_analyst,
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/v1/data-governance/lineage-edges",
            json={
                "edge_code": "LIN-RET-FAIL",
                "source_data_asset_id": asset_id,
                "target_data_asset_id": downstream_asset["id"],
            },
            headers=h_analyst,
        ).status_code
        == 409
    )
    # Self-restoration by the admin who retired it -> 403
    assert (
        client.post(
            f"/api/v1/data-governance/assets/{asset_id}/restore",
            json={"restoration_justification": "Admin trying to self-restore retired asset"},
            headers=h_admin,
        ).status_code
        == 403
    )

    # SEC-B3-45: Mutating or deleting a RETIRED asset via legacy Phase 16 /api/v1/privacy/data-assets/{id} -> 409
    assert (
        client.put(
            f"/api/v1/privacy/data-assets/{asset_id}",
            json={"name": "Legacy Mutate Retired"},
            headers=h_admin,
        ).status_code
        == 409
    )
    assert client.delete(f"/api/v1/privacy/data-assets/{asset_id}", headers=h_admin).status_code == 409


# ─────────────────────────────────────────────────────────────────────────────
# 7. IMMUTABILITY (405), CONCURRENCY & IDEMPOTENCY (409) (SEC-B3-42 to SEC-B3-44)
# ─────────────────────────────────────────────────────────────────────────────

def test_sec_b3_42_to_44_immutability_and_idempotency(client: TestClient, dg_api_env):
    """SEC-B3-42 to SEC-B3-44: 405 Method Not Allowed on immutable records and 409 on duplicates/replays."""
    h_analyst = auth_header(dg_api_env["tokens"]["analyst_a"])
    h_mgr = auth_header(dg_api_env["tokens"]["mgr_a"])

    # SEC-B3-42: PUT/DELETE on /classifications/{id} or /lineage-edges/{id} -> 405
    assert client.put("/api/v1/data-governance/classifications/1", headers=h_mgr).status_code == 405
    assert client.delete("/api/v1/data-governance/classifications/1", headers=h_mgr).status_code == 405
    assert client.put("/api/v1/data-governance/lineage-edges/1", headers=h_mgr).status_code == 405
    assert client.delete("/api/v1/data-governance/lineage-edges/1", headers=h_mgr).status_code == 405

    # SEC-B3-43: Duplicate scheme_code+version, duplicate asset_code, duplicate links -> 409
    scheme = _create_active_scheme(client, h_analyst, h_mgr, "SCH-IDEMP-01")
    assert (
        client.post(
            "/api/v1/data-governance/schemes",
            json={"scheme_code": "SCH-IDEMP-01", "name": "Dup Scheme", "version": 1},
            headers=h_analyst,
        ).status_code
        == 409
    )

    a1 = client.post(
        "/api/v1/data-governance/assets",
        json={"asset_code": "DA-IDEMP-01", "name": "Idemp Asset 1"},
        headers=h_analyst,
    ).json()
    a2 = client.post(
        "/api/v1/data-governance/assets",
        json={"asset_code": "DA-IDEMP-02", "name": "Idemp Asset 2"},
        headers=h_analyst,
    ).json()

    # Duplicate asset_code -> 409
    assert (
        client.post(
            "/api/v1/data-governance/assets",
            json={"asset_code": "DA-IDEMP-01", "name": "Dup Asset"},
            headers=h_analyst,
        ).status_code
        == 409
    )

    # Duplicate cloud link -> 409
    assert (
        client.post(
            f"/api/v1/data-governance/assets/{a1['id']}/cloud-links",
            json={"cloud_asset_id": dg_api_env["cloud_a"].id, "hosting_role": "PRIMARY_STORE"},
            headers=h_analyst,
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/v1/data-governance/assets/{a1['id']}/cloud-links",
            json={"cloud_asset_id": dg_api_env["cloud_a"].id, "hosting_role": "BACKUP_ARCHIVE"},
            headers=h_analyst,
        ).status_code
        == 409
    )

    # Duplicate processing link -> 409
    assert (
        client.post(
            f"/api/v1/data-governance/assets/{a1['id']}/processing-links",
            json={"processing_activity_id": dg_api_env["ropa_a"].id, "usage_role": "PRIMARY_SOURCE"},
            headers=h_analyst,
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/v1/data-governance/assets/{a1['id']}/processing-links",
            json={"processing_activity_id": dg_api_env["ropa_a"].id, "usage_role": "PRIMARY_SOURCE"},
            headers=h_analyst,
        ).status_code
        == 409
    )

    # Duplicate control link -> 409
    assert (
        client.post(
            f"/api/v1/data-governance/assets/{a1['id']}/control-links",
            json={"organization_control_id": dg_api_env["ctrl_a"].id, "control_objective": "ENCRYPTION_AT_REST"},
            headers=h_analyst,
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/v1/data-governance/assets/{a1['id']}/control-links",
            json={"organization_control_id": dg_api_env["ctrl_a"].id, "control_objective": "ACCESS_CONTROL"},
            headers=h_analyst,
        ).status_code
        == 409
    )

    # Duplicate evidence link -> 409
    assert (
        client.post(
            f"/api/v1/data-governance/assets/{a1['id']}/evidence-links",
            json={
                "evidence_item_id": dg_api_env["ev_accepted_a"].id,
                "evidence_purpose": "CLASSIFICATION_JUSTIFICATION",
            },
            headers=h_analyst,
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/v1/data-governance/assets/{a1['id']}/evidence-links",
            json={
                "evidence_item_id": dg_api_env["ev_accepted_a"].id,
                "evidence_purpose": "CLASSIFICATION_JUSTIFICATION",
            },
            headers=h_analyst,
        ).status_code
        == 409
    )

    # SEC-B3-44: Double-approving an already approved classification record or lineage edge -> 409
    l4_id = [lvl["id"] for lvl in scheme["levels"] if lvl["mapped_sensitivity_level"] == "RESTRICTED_PII"][0]
    rec = client.post(
        f"/api/v1/data-governance/assets/{a1['id']}/classifications",
        json={
            "scheme_id": scheme["id"],
            "level_id": l4_id,
            "justification": "Restricted PII classification requiring approval",
            "require_approval": True,
        },
        headers=h_analyst,
    ).json()
    assert client.post(f"/api/v1/data-governance/classifications/{rec['id']}/approve", headers=h_mgr).status_code == 200
    assert client.post(f"/api/v1/data-governance/classifications/{rec['id']}/approve", headers=h_mgr).status_code == 409

    edge = client.post(
        "/api/v1/data-governance/lineage-edges",
        json={
            "edge_code": "LIN-IDEMP-01",
            "source_data_asset_id": a1["id"],
            "target_data_asset_id": a2["id"],
            "relationship_type": "ETL_TRANSFORMATION",
            "transformation_summary": "A1 to A2 masked",
            "is_masked_or_anonymized": True,
            "require_approval": True,
        },
        headers=h_analyst,
    ).json()
    assert client.post(f"/api/v1/data-governance/lineage-edges/{edge['id']}/approve", headers=h_mgr).status_code == 200
    assert client.post(f"/api/v1/data-governance/lineage-edges/{edge['id']}/approve", headers=h_mgr).status_code == 409


# ─────────────────────────────────────────────────────────────────────────────
# 8. DOSSIER, REGULATORY TRACEABILITY, CLOUD DRIFT, SUMMARY & PHASE 16 COMPAT
# ─────────────────────────────────────────────────────────────────────────────

def test_dossier_regulatory_traceability_and_phase16_compatibility(client: TestClient, dg_api_env):
    """Verify dossier cloud posture alignment, regulatory traceability, summary KPIs, and Phase 16 compatibility."""
    h_analyst = auth_header(dg_api_env["tokens"]["analyst_a"])
    h_mgr = auth_header(dg_api_env["tokens"]["mgr_a"])

    # 1. Phase 16 /api/v1/privacy/data-assets create and list remain 100% compatible
    r_p16 = client.post(
        "/api/v1/privacy/data-assets",
        json={
            "asset_code": "DA-P16-COMPAT",
            "name": "Phase 16 Legacy Data Asset",
            "description": "Created via Phase 16 endpoint",
            "data_sensitivity_level": "RESTRICTED_PII",
            "data_volume_range": "100K-1M",
            "storage_type": "RDS",
            "hosting_jurisdiction": "EU",
            "is_encrypted_at_rest": True,
            "is_encrypted_in_transit": True,
            "is_pseudonymized": False,
            "retention_period_months": 36,
            "owner_id": dg_api_env["users_a"]["mgr"].id,
        },
        headers=h_mgr,
    )
    assert r_p16.status_code == 201
    p16_id = r_p16.json()["id"]

    # Link p16 asset to drifted cloud asset, RoPA, and control
    assert (
        client.post(
            f"/api/v1/data-governance/assets/{p16_id}/cloud-links",
            json={"cloud_asset_id": dg_api_env["cloud_drifted_a"].id, "hosting_role": "REPLICA_STORE"},
            headers=h_analyst,
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/v1/data-governance/assets/{p16_id}/processing-links",
            json={"processing_activity_id": dg_api_env["ropa_a"].id, "usage_role": "PRIMARY_SOURCE"},
            headers=h_analyst,
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/v1/data-governance/assets/{p16_id}/control-links",
            json={"organization_control_id": dg_api_env["ctrl_a"].id, "control_objective": "ENCRYPTION_AT_REST"},
            headers=h_analyst,
        ).status_code
        == 201
    )

    # Dossier reflects cloud posture drift, encryption mismatch, RoPA, Control, and Regulatory Obligation
    r_dossier = client.get(f"/api/v1/data-governance/assets/{p16_id}", headers=h_analyst)
    assert r_dossier.status_code == 200
    dossier = r_dossier.json()
    assert dossier["asset"]["lifecycle_state"] == "ACTIVE"
    assert dossier["asset"]["classification_status"] == "APPROVED"
    assert dossier["cloud_alignment"]["cloud_posture_aligned"] is False
    assert "CLOUD_ENCRYPTION_MISMATCH" in dossier["cloud_alignment"]["mismatch_flags"]
    assert "CLOUD_PUBLIC_EXPOSURE_MISMATCH" in dossier["cloud_alignment"]["mismatch_flags"]
    assert len(dossier["processing_links"]) == 1
    assert len(dossier["control_links"]) == 1
    assert len(dossier["cloud_links"]) == 1
    assert len(dossier["regulatory_obligations"]) == 1
    assert dossier["regulatory_obligations"][0]["obligation_code"] == "GDPR-ART-32-ALPHA"

    # Summary KPIs reflect total assets, cloud mismatch, and processing links
    r_sum = client.get("/api/v1/data-governance/summary", headers=h_analyst)
    assert r_sum.status_code == 200
    summary = r_sum.json()
    assert summary["total_assets"] >= 1
    assert summary["cloud_posture_mismatch_count"] >= 1
    assert summary["processing_linked_assets_count"] >= 1


# ─────────────────────────────────────────────────────────────────────────────
# 9. ALEMBIC MIGRATION REVERSIBILITY (0023 -> 0024 -> 0023 -> 0024)
# ─────────────────────────────────────────────────────────────────────────────

def test_alembic_migration_0024_upgrade_downgrade_reversibility():
    """Verify Alembic migration 0024 -> 0023 -> 0024 -> 0023 -> 0024 executes cleanly on an isolated DB."""
    from app.core.config import settings
    from app.db.base import Base

    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    alembic_ini = os.path.join(backend_dir, "alembic.ini")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "alembic_b3_test.db")
        db_url = f"sqlite:///{db_path}"

        cfg = Config(alembic_ini)
        cfg.set_main_option("script_location", os.path.join(backend_dir, "alembic"))
        cfg.set_main_option("sqlalchemy.url", db_url)

        old_settings_url = settings.DATABASE_URL
        settings.DATABASE_URL = db_url
        try:
            # Initialize baseline tables and stamp at 0024
            engine = create_engine(db_url)
            Base.metadata.create_all(bind=engine)
            engine.dispose()
            command.stamp(cfg, "0024")

            expected_new_tables = {
                "data_classification_schemes",
                "data_classification_levels",
                "data_classification_records",
                "data_lineage_edges",
                "data_asset_cloud_links",
                "data_asset_processing_links",
                "data_asset_control_links",
                "data_asset_evidence_links",
            }

            # Downgrade 0024 -> 0023
            command.downgrade(cfg, "0023")
            engine = create_engine(db_url)
            insp = inspect(engine)
            tables_at_0023 = set(insp.get_table_names())
            assert "data_assets" in tables_at_0023
            assert expected_new_tables.isdisjoint(tables_at_0023)
            da_cols_0023 = {c["name"] for c in insp.get_columns("data_assets")}
            assert "lifecycle_state" not in da_cols_0023
            assert "classification_status" not in da_cols_0023
            assert "retirement_evidence_id" not in da_cols_0023
            engine.dispose()

            # Upgrade 0023 -> 0024
            command.upgrade(cfg, "0024")
            engine = create_engine(db_url)
            insp = inspect(engine)
            tables_at_0024 = set(insp.get_table_names())
            assert expected_new_tables.issubset(tables_at_0024)
            da_cols_0024 = {c["name"] for c in insp.get_columns("data_assets")}
            assert "lifecycle_state" in da_cols_0024
            assert "classification_status" in da_cols_0024
            assert "retirement_evidence_id" in da_cols_0024
            engine.dispose()

            # Second Downgrade 0024 -> 0023
            command.downgrade(cfg, "0023")
            engine = create_engine(db_url)
            insp = inspect(engine)
            assert expected_new_tables.isdisjoint(set(insp.get_table_names()))
            engine.dispose()

            # Re-upgrade 0023 -> 0024
            command.upgrade(cfg, "0024")
            engine = create_engine(db_url)
            tables_reupgraded = set(inspect(engine).get_table_names())
            assert expected_new_tables.issubset(tables_reupgraded)
            engine.dispose()
        finally:
            settings.DATABASE_URL = old_settings_url


# ─────────────────────────────────────────────────────────────────────────────
# 10. GRANULAR ADVERSARIAL VECTOR VERIFICATION (SEC-B3-01 THROUGH SEC-B3-45)
# ─────────────────────────────────────────────────────────────────────────────

def test_sec_b3_01_unauthenticated_endpoints_rejected(client: TestClient):
    assert client.get("/api/v1/data-governance/summary").status_code == 401
    assert client.get("/api/v1/data-governance/schemes").status_code == 401
    assert client.get("/api/v1/data-governance/assets").status_code == 401
    assert client.get("/api/v1/data-governance/lineage-edges").status_code == 401


def test_sec_b3_02_viewer_and_auditor_read_only_enforcement(client: TestClient, dg_api_env):
    for role_key in ("viewer_a", "auditor_a"):
        headers = auth_header(dg_api_env["tokens"][role_key])
        assert client.get("/api/v1/data-governance/summary", headers=headers).status_code == 200
        assert client.get("/api/v1/data-governance/assets", headers=headers).status_code == 200
        assert (
            client.post(
                "/api/v1/data-governance/assets",
                json={"asset_code": f"DA-RO-{role_key}", "name": "Blocked"},
                headers=headers,
            ).status_code
            == 403
        )


def test_sec_b3_03_security_analyst_cannot_create_schemes_or_assets(client: TestClient, dg_api_env):
    h_sec = auth_header(dg_api_env["tokens"]["sec_a"])
    assert (
        client.post(
            "/api/v1/data-governance/schemes",
            json={"scheme_code": "SCH-SEC-BLK", "name": "Blocked"},
            headers=h_sec,
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/data-governance/assets",
            json={"asset_code": "DA-SEC-BLK", "name": "Blocked"},
            headers=h_sec,
        ).status_code
        == 403
    )


def test_sec_b3_04_grc_analyst_cannot_approve_scheme(client: TestClient, dg_api_env):
    h_analyst = auth_header(dg_api_env["tokens"]["analyst_a"])
    s = client.post(
        "/api/v1/data-governance/schemes",
        json={"scheme_code": "SCH-NOAPP", "name": "No Approve"},
        headers=h_analyst,
    ).json()
    assert client.post(f"/api/v1/data-governance/schemes/{s['id']}/approve", headers=h_analyst).status_code == 403


def test_sec_b3_05_foreign_tenant_scheme_detail_returns_404(client: TestClient, dg_api_env):
    h_analyst_a = auth_header(dg_api_env["tokens"]["analyst_a"])
    h_admin_b = auth_header(dg_api_env["tokens"]["admin_b"])
    s = client.post(
        "/api/v1/data-governance/schemes",
        json={"scheme_code": "SCH-TEN-404", "name": "Tenant A Scheme"},
        headers=h_analyst_a,
    ).json()
    assert client.get(f"/api/v1/data-governance/schemes/{s['id']}", headers=h_admin_b).status_code == 404


def test_sec_b3_06_foreign_tenant_asset_dossier_returns_404(client: TestClient, dg_api_env):
    h_analyst_a = auth_header(dg_api_env["tokens"]["analyst_a"])
    h_admin_b = auth_header(dg_api_env["tokens"]["admin_b"])
    a = client.post(
        "/api/v1/data-governance/assets",
        json={"asset_code": "DA-TEN-404", "name": "Tenant A Asset"},
        headers=h_analyst_a,
    ).json()
    assert client.get(f"/api/v1/data-governance/assets/{a['id']}", headers=h_admin_b).status_code == 404


def test_sec_b3_07_foreign_tenant_lineage_edge_detail_returns_404(client: TestClient, dg_api_env):
    h_analyst_a = auth_header(dg_api_env["tokens"]["analyst_a"])
    h_admin_b = auth_header(dg_api_env["tokens"]["admin_b"])
    a1 = client.post(
        "/api/v1/data-governance/assets",
        json={"asset_code": "DA-L404-1", "name": "A1"},
        headers=h_analyst_a,
    ).json()
    a2 = client.post(
        "/api/v1/data-governance/assets",
        json={"asset_code": "DA-L404-2", "name": "A2"},
        headers=h_analyst_a,
    ).json()
    edge = client.post(
        "/api/v1/data-governance/lineage-edges",
        json={
            "edge_code": "LIN-404-EDGE",
            "source_data_asset_id": a1["id"],
            "target_data_asset_id": a2["id"],
            "require_approval": True,
        },
        headers=h_analyst_a,
    ).json()
    assert client.post(f"/api/v1/data-governance/lineage-edges/{edge['id']}/approve", headers=h_admin_b).status_code == 404
    assert (
        client.post(
            f"/api/v1/data-governance/lineage-edges/{edge['id']}/revoke",
            json={"revocation_reason": "Foreign tenant revoke attempt"},
            headers=h_admin_b,
        ).status_code
        == 404
    )


def test_sec_b3_08_foreign_tenant_steward_injection_returns_404(client: TestClient, dg_api_env):
    h_analyst_a = auth_header(dg_api_env["tokens"]["analyst_a"])
    r = client.post(
        "/api/v1/data-governance/assets",
        json={
            "asset_code": "DA-FOR-STEW",
            "name": "Foreign Steward Attempt",
            "steward_id": dg_api_env["users_b"]["admin"].id,
        },
        headers=h_analyst_a,
    )
    assert r.status_code == 404


def test_sec_b3_09_foreign_tenant_cloud_asset_on_create_returns_404(client: TestClient, dg_api_env):
    h_analyst_a = auth_header(dg_api_env["tokens"]["analyst_a"])
    r = client.post(
        "/api/v1/data-governance/assets",
        json={
            "asset_code": "DA-FOR-CLD",
            "name": "Foreign Cloud Attempt",
            "cloud_asset_id": dg_api_env["cloud_b"].id,
        },
        headers=h_analyst_a,
    )
    assert r.status_code == 404


def test_sec_b3_10_summary_endpoint_strictly_tenant_scoped(client: TestClient, dg_api_env):
    h_analyst_a = auth_header(dg_api_env["tokens"]["analyst_a"])
    h_admin_b = auth_header(dg_api_env["tokens"]["admin_b"])
    client.post(
        "/api/v1/data-governance/assets",
        json={"asset_code": "DA-SUM-ISO-A", "name": "Org A Asset"},
        headers=h_analyst_a,
    )
    sum_b = client.get("/api/v1/data-governance/summary", headers=h_admin_b).json()
    assert sum_b["total_assets"] == 0


def test_sec_b3_11_extra_forbid_on_asset_update(client: TestClient, dg_api_env):
    h_analyst = auth_header(dg_api_env["tokens"]["analyst_a"])
    a = client.post(
        "/api/v1/data-governance/assets",
        json={"asset_code": "DA-UPD-FORBID", "name": "Forbid Update"},
        headers=h_analyst,
    ).json()
    # Attempting to inject data_sensitivity_level or lifecycle_state in PUT /assets/{id} -> 422
    assert (
        client.put(
            f"/api/v1/data-governance/assets/{a['id']}",
            json={"data_sensitivity_level": "PUBLIC"},
            headers=h_analyst,
        ).status_code
        == 422
    )
    assert (
        client.put(
            f"/api/v1/data-governance/assets/{a['id']}",
            json={"lifecycle_state": "RETIRED"},
            headers=h_analyst,
        ).status_code
        == 422
    )


def test_sec_b3_12_extra_forbid_on_ownership_and_retirement_payloads(client: TestClient, dg_api_env):
    h_analyst = auth_header(dg_api_env["tokens"]["analyst_a"])
    assert (
        client.post(
            "/api/v1/data-governance/assets/1/ownership",
            json={
                "owner_id": 1,
                "justification": "Valid text",
                "owner_transfer_status": "APPROVED",
            },
            headers=h_analyst,
        ).status_code
        == 422
    )


def test_sec_b3_13_whitespace_only_codes_and_names_rejected(client: TestClient, dg_api_env):
    h_analyst = auth_header(dg_api_env["tokens"]["analyst_a"])
    assert (
        client.post(
            "/api/v1/data-governance/schemes",
            json={"scheme_code": "   ", "name": "   "},
            headers=h_analyst,
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/data-governance/assets",
            json={"asset_code": "   ", "name": "   "},
            headers=h_analyst,
        ).status_code
        == 422
    )


def test_sec_b3_14_ordinal_rank_bounds_enforced(client: TestClient, dg_api_env):
    h_analyst = auth_header(dg_api_env["tokens"]["analyst_a"])
    s = client.post(
        "/api/v1/data-governance/schemes",
        json={"scheme_code": "SCH-BOUNDS", "name": "Bounds Scheme"},
        headers=h_analyst,
    ).json()
    assert (
        client.post(
            f"/api/v1/data-governance/schemes/{s['id']}/levels",
            json={
                "level_code": "L0",
                "name": "Zero Rank",
                "ordinal_rank": 0,
                "mapped_sensitivity_level": "PUBLIC",
            },
            headers=h_analyst,
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"/api/v1/data-governance/schemes/{s['id']}/levels",
            json={
                "level_code": "L99",
                "name": "Too High Rank",
                "ordinal_rank": 99,
                "mapped_sensitivity_level": "PUBLIC",
            },
            headers=h_analyst,
        ).status_code
        == 422
    )


def test_sec_b3_15_duplicate_ordinal_rank_or_level_code_in_scheme_returns_409(client: TestClient, dg_api_env):
    h_analyst = auth_header(dg_api_env["tokens"]["analyst_a"])
    s = client.post(
        "/api/v1/data-governance/schemes",
        json={"scheme_code": "SCH-DUPLVL", "name": "Dup Level Scheme"},
        headers=h_analyst,
    ).json()
    assert (
        client.post(
            f"/api/v1/data-governance/schemes/{s['id']}/levels",
            json={
                "level_code": "L1",
                "name": "Public",
                "ordinal_rank": 1,
                "mapped_sensitivity_level": "PUBLIC",
            },
            headers=h_analyst,
        ).status_code
        == 201
    )
    # Same rank -> 409
    assert (
        client.post(
            f"/api/v1/data-governance/schemes/{s['id']}/levels",
            json={
                "level_code": "L2",
                "name": "Also Rank 1",
                "ordinal_rank": 1,
                "mapped_sensitivity_level": "PUBLIC",
            },
            headers=h_analyst,
        ).status_code
        == 409
    )


def test_sec_b3_16_submitting_scheme_with_fewer_than_two_levels_rejected(client: TestClient, dg_api_env):
    h_analyst = auth_header(dg_api_env["tokens"]["analyst_a"])
    s = client.post(
        "/api/v1/data-governance/schemes",
        json={"scheme_code": "SCH-ONELVL", "name": "Single Level Scheme"},
        headers=h_analyst,
    ).json()
    client.post(
        f"/api/v1/data-governance/schemes/{s['id']}/levels",
        json={
            "level_code": "L1",
            "name": "Public",
            "ordinal_rank": 1,
            "mapped_sensitivity_level": "PUBLIC",
        },
        headers=h_analyst,
    )
    assert client.post(f"/api/v1/data-governance/schemes/{s['id']}/submit", headers=h_analyst).status_code == 422


def test_sec_b3_17_approving_draft_unsubmitted_scheme_rejected(client: TestClient, dg_api_env):
    h_analyst = auth_header(dg_api_env["tokens"]["analyst_a"])
    h_mgr = auth_header(dg_api_env["tokens"]["mgr_a"])
    s = client.post(
        "/api/v1/data-governance/schemes",
        json={"scheme_code": "SCH-UNSUB", "name": "Unsubmitted Scheme"},
        headers=h_analyst,
    ).json()
    assert client.post(f"/api/v1/data-governance/schemes/{s['id']}/approve", headers=h_mgr).status_code == 409


def test_sec_b3_18_classification_rejection_restores_status_and_blocks_double_reject(client: TestClient, dg_api_env):
    h_mgr = auth_header(dg_api_env["tokens"]["mgr_a"])
    h_admin = auth_header(dg_api_env["tokens"]["admin_a"])
    scheme = _create_active_scheme(client, h_mgr, h_admin, "SCH-REJ-TEST")
    l4_id = [lvl["id"] for lvl in scheme["levels"] if lvl["mapped_sensitivity_level"] == "RESTRICTED_PII"][0]
    a = client.post(
        "/api/v1/data-governance/assets",
        json={"asset_code": "DA-REJ-01", "name": "Reject Test Asset"},
        headers=h_mgr,
    ).json()
    rec = client.post(
        f"/api/v1/data-governance/assets/{a['id']}/classifications",
        json={
            "scheme_id": scheme["id"],
            "level_id": l4_id,
            "justification": "Manager requesting restricted PII classification",
        },
        headers=h_mgr,
    ).json()
    # Admin rejects -> 200
    rej = client.post(
        f"/api/v1/data-governance/classifications/{rec['id']}/reject",
        json={"rejection_reason": "Insufficient data element inventory attached"},
        headers=h_admin,
    )
    assert rej.status_code == 200
    assert rej.json()["status"] == "REJECTED"
    # Double rejection blocked (409)
    assert (
        client.post(
            f"/api/v1/data-governance/classifications/{rec['id']}/reject",
            json={"rejection_reason": "Trying to reject again"},
            headers=h_admin,
        ).status_code
        == 409
    )


def test_sec_b3_19_special_category_phi_forces_four_eyes_and_updates_status(client: TestClient, dg_api_env):
    h_analyst = auth_header(dg_api_env["tokens"]["analyst_a"])
    h_mgr = auth_header(dg_api_env["tokens"]["mgr_a"])
    scheme = _create_active_scheme(client, h_analyst, h_mgr, "SCH-PHI-TEST")
    l5_id = [
        lvl["id"]
        for lvl in scheme["levels"]
        if lvl["mapped_sensitivity_level"] == "SPECIAL_CATEGORY_SENSITIVE_PHI"
    ][0]
    a = client.post(
        "/api/v1/data-governance/assets",
        json={
            "asset_code": "DA-PHI-01",
            "name": "Patient Telemetry Store",
            "is_encrypted_at_rest": True,
        },
        headers=h_analyst,
    ).json()
    rec = client.post(
        f"/api/v1/data-governance/assets/{a['id']}/classifications",
        json={
            "scheme_id": scheme["id"],
            "level_id": l5_id,
            "justification": "Contains clinical biometric telemetry (PHI)",
        },
        headers=h_analyst,
    ).json()
    assert rec["status"] == "PENDING_APPROVAL"
    client.post(f"/api/v1/data-governance/classifications/{rec['id']}/approve", headers=h_mgr)
    dossier = client.get(f"/api/v1/data-governance/assets/{a['id']}", headers=h_analyst).json()
    assert dossier["asset"]["data_sensitivity_level"] == "SPECIAL_CATEGORY_SENSITIVE_PHI"
    assert dossier["asset"]["classification_status"] == "APPROVED"


def test_sec_b3_20_lineage_edge_revocation_clears_cycle_constraint(client: TestClient, dg_api_env):
    h_analyst = auth_header(dg_api_env["tokens"]["analyst_a"])
    a1 = client.post(
        "/api/v1/data-governance/assets",
        json={"asset_code": "DA-REV-A1", "name": "Rev A1"},
        headers=h_analyst,
    ).json()
    a2 = client.post(
        "/api/v1/data-governance/assets",
        json={"asset_code": "DA-REV-A2", "name": "Rev A2"},
        headers=h_analyst,
    ).json()
    e12 = client.post(
        "/api/v1/data-governance/lineage-edges",
        json={
            "edge_code": "LIN-REV-12",
            "source_data_asset_id": a1["id"],
            "target_data_asset_id": a2["id"],
        },
        headers=h_analyst,
    ).json()
    # While e12 is ACTIVE, a2 -> a1 is a cycle (422)
    assert (
        client.post(
            "/api/v1/data-governance/lineage-edges",
            json={
                "edge_code": "LIN-REV-21",
                "source_data_asset_id": a2["id"],
                "target_data_asset_id": a1["id"],
            },
            headers=h_analyst,
        ).status_code
        == 422
    )
    # Revoke e12 -> now a2 -> a1 is permitted (201)
    assert (
        client.post(
            f"/api/v1/data-governance/lineage-edges/{e12['id']}/revoke",
            json={"revocation_reason": "Reversing pipeline direction"},
            headers=h_analyst,
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/data-governance/lineage-edges",
            json={
                "edge_code": "LIN-REV-21",
                "source_data_asset_id": a2["id"],
                "target_data_asset_id": a1["id"],
            },
            headers=h_analyst,
        ).status_code
        == 201
    )


def test_sec_b3_21_double_revoking_lineage_edge_returns_409(client: TestClient, dg_api_env):
    h_analyst = auth_header(dg_api_env["tokens"]["analyst_a"])
    a1 = client.post(
        "/api/v1/data-governance/assets",
        json={"asset_code": "DA-DREV-1", "name": "DRev 1"},
        headers=h_analyst,
    ).json()
    a2 = client.post(
        "/api/v1/data-governance/assets",
        json={"asset_code": "DA-DREV-2", "name": "DRev 2"},
        headers=h_analyst,
    ).json()
    edge = client.post(
        "/api/v1/data-governance/lineage-edges",
        json={
            "edge_code": "LIN-DREV",
            "source_data_asset_id": a1["id"],
            "target_data_asset_id": a2["id"],
        },
        headers=h_analyst,
    ).json()
    assert (
        client.post(
            f"/api/v1/data-governance/lineage-edges/{edge['id']}/revoke",
            json={"revocation_reason": "First revocation"},
            headers=h_analyst,
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/data-governance/lineage-edges/{edge['id']}/revoke",
            json={"revocation_reason": "Second revocation"},
            headers=h_analyst,
        ).status_code
        == 409
    )


def test_sec_b3_22_registering_already_registered_asset_returns_409(client: TestClient, dg_api_env):
    h_analyst = auth_header(dg_api_env["tokens"]["analyst_a"])
    a = client.post(
        "/api/v1/data-governance/assets",
        json={
            "asset_code": "DA-REG-409",
            "name": "Already Registered",
            "initial_lifecycle_state": "REGISTERED",
        },
        headers=h_analyst,
    ).json()
    assert (
        client.post(
            f"/api/v1/data-governance/assets/{a['id']}/register",
            json={"steward_id": dg_api_env["users_a"]["sec"].id},
            headers=h_analyst,
        ).status_code
        == 409
    )


def test_sec_b3_23_approving_ownership_when_none_pending_returns_409(client: TestClient, dg_api_env):
    h_analyst = auth_header(dg_api_env["tokens"]["analyst_a"])
    h_mgr = auth_header(dg_api_env["tokens"]["mgr_a"])
    a = client.post(
        "/api/v1/data-governance/assets",
        json={"asset_code": "DA-NOPEND-OWN", "name": "No Pending Transfer"},
        headers=h_analyst,
    ).json()
    assert client.post(f"/api/v1/data-governance/assets/{a['id']}/ownership/approve", headers=h_mgr).status_code == 409


def test_sec_b3_24_restoring_non_retired_asset_returns_409(client: TestClient, dg_api_env):
    h_analyst = auth_header(dg_api_env["tokens"]["analyst_a"])
    h_mgr = auth_header(dg_api_env["tokens"]["mgr_a"])
    a = client.post(
        "/api/v1/data-governance/assets",
        json={"asset_code": "DA-NORESTORE", "name": "Not Retired"},
        headers=h_analyst,
    ).json()
    assert (
        client.post(
            f"/api/v1/data-governance/assets/{a['id']}/restore",
            json={"restoration_justification": "Trying to restore non-retired asset"},
            headers=h_mgr,
        ).status_code
        == 409
    )


def test_sec_b3_25_classifying_discovered_unregistered_asset_returns_422(client: TestClient, dg_api_env):
    h_analyst = auth_header(dg_api_env["tokens"]["analyst_a"])
    h_mgr = auth_header(dg_api_env["tokens"]["mgr_a"])
    scheme = _create_active_scheme(client, h_analyst, h_mgr, "SCH-DISC-CLS")
    l1_id = scheme["levels"][0]["id"]
    a = client.post(
        "/api/v1/data-governance/assets",
        json={
            "asset_code": "DA-DISC-CLS",
            "name": "Discovered Cannot Classify Before Register",
            "initial_lifecycle_state": "DISCOVERED",
        },
        headers=h_analyst,
    ).json()
    assert (
        client.post(
            f"/api/v1/data-governance/assets/{a['id']}/classifications",
            json={
                "scheme_id": scheme["id"],
                "level_id": l1_id,
                "justification": "Trying to classify discovered asset before registration",
            },
            headers=h_analyst,
        ).status_code
        == 422
    )


def test_sec_b3_26_linking_rejected_evidence_to_asset_returns_422(client: TestClient, dg_api_env):
    h_analyst = auth_header(dg_api_env["tokens"]["analyst_a"])
    a = client.post(
        "/api/v1/data-governance/assets",
        json={"asset_code": "DA-REJ-EVLINK", "name": "Rejected Evidence Link"},
        headers=h_analyst,
    ).json()
    assert (
        client.post(
            f"/api/v1/data-governance/assets/{a['id']}/evidence-links",
            json={
                "evidence_item_id": dg_api_env["ev_rejected_a"].id,
                "evidence_purpose": "CLASSIFICATION_JUSTIFICATION",
            },
            headers=h_analyst,
        ).status_code
        == 422
    )


def test_sec_b3_27_filtering_assets_and_lineage_edges_by_query_params(client: TestClient, dg_api_env):
    h_analyst = auth_header(dg_api_env["tokens"]["analyst_a"])
    a1 = client.post(
        "/api/v1/data-governance/assets",
        json={
            "asset_code": "DA-FLT-01",
            "name": "Filter Asset 1",
            "data_sensitivity_level": "CONFIDENTIAL",
        },
        headers=h_analyst,
    ).json()
    a2 = client.post(
        "/api/v1/data-governance/assets",
        json={
            "asset_code": "DA-FLT-02",
            "name": "Filter Asset 2",
            "data_sensitivity_level": "CONFIDENTIAL",
        },
        headers=h_analyst,
    ).json()
    client.post(
        "/api/v1/data-governance/lineage-edges",
        json={
            "edge_code": "LIN-FLT-12",
            "source_data_asset_id": a1["id"],
            "target_data_asset_id": a2["id"],
        },
        headers=h_analyst,
    )
    r_assets = client.get(
        "/api/v1/data-governance/assets?lifecycle_state=REGISTERED&sensitivity_level=CONFIDENTIAL",
        headers=h_analyst,
    )
    assert r_assets.status_code == 200
    assert any(x["id"] == a1["id"] for x in r_assets.json())

    r_edges = client.get(
        f"/api/v1/data-governance/lineage-edges?status=ACTIVE&asset_id={a1['id']}",
        headers=h_analyst,
    )
    assert r_edges.status_code == 200
    assert len(r_edges.json()) == 1


