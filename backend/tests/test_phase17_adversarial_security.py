from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.permissions import RoleEnum
from app.core.security import get_password_hash
from app.models.organization import Organization
from app.models.user import User
from app.models.resilience import BusinessProcess, CriticalityTierEnum
from app.models.ai_governance import AISystem, AISystemTypeEnum, AIRegulatoryTierEnum, AIHostingTypeEnum
from app.models.tprm import Vendor, VendorTierEnum
from app.models.remediation import RemediationPlan, RemediationSourceTypeEnum
from app.models.exposure import VulnerabilityExposure, ExposureSeverityEnum
from tests.conftest import get_token_headers


@pytest.fixture
def adv_p17_fixture(db: Session, org_apex: Organization, org_meridian: Organization):
    """Setup multi-tenant organizations and adversarial actors for Phase 17 ADV test suite."""
    # Apex Users (Tenant A)
    apex_admin = User(
        email="adv17_admin@apex.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Apex Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_manager = User(
        email="adv17_manager@apex.com",
        hashed_password=get_password_hash("ManagerPass123!"),
        full_name="Apex Manager",
        role=RoleEnum.MANAGER,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_grc_analyst = User(
        email="adv17_grc_analyst@apex.com",
        hashed_password=get_password_hash("GrcAnalystPass123!"),
        full_name="Apex GRC Analyst",
        role=RoleEnum.GRC_ANALYST,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_sec_analyst = User(
        email="adv17_sec_analyst@apex.com",
        hashed_password=get_password_hash("SecAnalystPass123!"),
        full_name="Apex Sec Analyst",
        role=RoleEnum.SECURITY_ANALYST,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_auditor = User(
        email="adv17_auditor@apex.com",
        hashed_password=get_password_hash("AuditorPass123!"),
        full_name="Apex Auditor",
        role=RoleEnum.AUDITOR,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_viewer = User(
        email="adv17_viewer@apex.com",
        hashed_password=get_password_hash("ViewerPass123!"),
        full_name="Apex Viewer",
        role=RoleEnum.VIEWER,
        is_active=True,
        organization_id=org_apex.id,
    )

    # Meridian Users (Tenant B - Adversary)
    meridian_admin = User(
        email="adv17_admin@meridian.com",
        hashed_password=get_password_hash("MeridianAdmin123!"),
        full_name="Meridian Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_meridian.id,
    )
    meridian_analyst = User(
        email="adv17_analyst@meridian.com",
        hashed_password=get_password_hash("MeridianAnalyst123!"),
        full_name="Meridian Analyst",
        role=RoleEnum.GRC_ANALYST,
        is_active=True,
        organization_id=org_meridian.id,
    )

    db.add_all([
        apex_admin,
        apex_manager,
        apex_grc_analyst,
        apex_sec_analyst,
        apex_auditor,
        apex_viewer,
        meridian_admin,
        meridian_analyst,
    ])
    db.commit()

    return {
        "org_apex": org_apex,
        "org_meridian": org_meridian,
        "apex_admin": apex_admin,
        "apex_manager": apex_manager,
        "apex_grc_analyst": apex_grc_analyst,
        "apex_sec_analyst": apex_sec_analyst,
        "apex_auditor": apex_auditor,
        "apex_viewer": apex_viewer,
        "meridian_admin": meridian_admin,
        "meridian_analyst": meridian_analyst,
    }


# ─── 1. Cross-Tenant Direct Resource Access (Vectors 01 - 05) ──────────────────

def test_adv_p17_01_cross_tenant_product_read(client: TestClient, adv_p17_fixture):
    """ADV-P17-01: Cross-Tenant Product Read -> 404 Not Found."""
    apex_analyst = adv_p17_fixture["apex_grc_analyst"]
    meridian_analyst = adv_p17_fixture["meridian_analyst"]
    apex_headers = get_token_headers(apex_analyst)
    meridian_headers = get_token_headers(meridian_analyst)

    # Apex creates product
    prod_res = client.post(
        "/api/v1/supply-chain/products",
        json={"product_code": "APEX-PROD-01", "name": "Apex Core App"},
        headers=apex_headers,
    )
    prod_id = prod_res.json()["id"]

    # Meridian attempts to read Apex product
    cross_res = client.get(f"/api/v1/supply-chain/products/{prod_id}", headers=meridian_headers)
    assert cross_res.status_code == 404


def test_adv_p17_02_cross_tenant_product_update(client: TestClient, adv_p17_fixture):
    """ADV-P17-02: Cross-Tenant Product Update -> 404 Not Found."""
    apex_analyst = adv_p17_fixture["apex_grc_analyst"]
    meridian_analyst = adv_p17_fixture["meridian_analyst"]
    apex_headers = get_token_headers(apex_analyst)
    meridian_headers = get_token_headers(meridian_analyst)

    prod_res = client.post(
        "/api/v1/supply-chain/products",
        json={"product_code": "APEX-PROD-02", "name": "Apex Secure Vault"},
        headers=apex_headers,
    )
    prod_id = prod_res.json()["id"]

    # Meridian attempts to update Apex product
    cross_res = client.put(
        f"/api/v1/supply-chain/products/{prod_id}",
        json={"name": "Tampered Vault Name"},
        headers=meridian_headers,
    )
    assert cross_res.status_code == 404


def test_adv_p17_03_cross_tenant_product_deletion(client: TestClient, adv_p17_fixture):
    """ADV-P17-03: Cross-Tenant Product Deletion -> 404 Not Found."""
    apex_analyst = adv_p17_fixture["apex_grc_analyst"]
    meridian_admin = adv_p17_fixture["meridian_admin"]
    apex_headers = get_token_headers(apex_analyst)
    meridian_headers = get_token_headers(meridian_admin)

    prod_res = client.post(
        "/api/v1/supply-chain/products",
        json={"product_code": "APEX-PROD-03", "name": "Apex API Gateway"},
        headers=apex_headers,
    )
    prod_id = prod_res.json()["id"]

    # Meridian attempts to delete Apex product
    cross_res = client.delete(f"/api/v1/supply-chain/products/{prod_id}", headers=meridian_headers)
    assert cross_res.status_code == 404


def test_adv_p17_04_cross_tenant_sbom_ingestion(client: TestClient, adv_p17_fixture):
    """ADV-P17-04: Cross-Tenant SBOM Ingestion -> 404 Not Found."""
    apex_analyst = adv_p17_fixture["apex_grc_analyst"]
    meridian_analyst = adv_p17_fixture["meridian_analyst"]
    apex_headers = get_token_headers(apex_analyst)
    meridian_headers = get_token_headers(meridian_analyst)

    prod_res = client.post(
        "/api/v1/supply-chain/products",
        json={"product_code": "APEX-PROD-04", "name": "Apex Microservice"},
        headers=apex_headers,
    )
    prod_id = prod_res.json()["id"]

    # Meridian attempts to ingest SBOM onto Apex product
    cross_res = client.post(
        f"/api/v1/supply-chain/products/{prod_id}/sboms",
        json={
            "software_product_id": prod_id,
            "sbom_code": "MALICIOUS-SBOM-01",
            "version": "1.0",
            "sha256_hash": "c" * 64,
        },
        headers=meridian_headers,
    )
    assert cross_res.status_code == 404


def test_adv_p17_05_cross_tenant_component_access(client: TestClient, adv_p17_fixture):
    """ADV-P17-05: Cross-Tenant Component Access -> 404 Not Found."""
    apex_analyst = adv_p17_fixture["apex_grc_analyst"]
    meridian_analyst = adv_p17_fixture["meridian_analyst"]
    apex_headers = get_token_headers(apex_analyst)
    meridian_headers = get_token_headers(meridian_analyst)

    # Apex creates product, SBOM, component
    p_res = client.post(
        "/api/v1/supply-chain/products",
        json={"product_code": "APEX-PROD-05", "name": "Apex Service"},
        headers=apex_headers,
    )
    prod_id = p_res.json()["id"]

    s_res = client.post(
        f"/api/v1/supply-chain/products/{prod_id}/sboms",
        json={
            "software_product_id": prod_id,
            "sbom_code": "APEX-SBOM-05",
            "version": "1.0",
            "sha256_hash": "d" * 64,
        },
        headers=apex_headers,
    )
    sbom_id = s_res.json()["id"]

    c_res = client.post(
        f"/api/v1/supply-chain/sboms/{sbom_id}/components",
        json={
            "sbom_document_id": sbom_id,
            "component_name": "apex-internal-lib",
            "version": "1.0.0",
            "purl": "pkg:npm/apex-internal-lib@1.0.0",
        },
        headers=apex_headers,
    )
    comp_id = c_res.json()["id"]

    # Meridian attempts to access Apex SBOM components
    cross_list_res = client.get(f"/api/v1/supply-chain/sboms/{sbom_id}/components", headers=meridian_headers)
    assert cross_list_res.status_code == 404

    # Meridian attempts to access Apex component directly
    cross_comp_res = client.get(f"/api/v1/supply-chain/components/{comp_id}", headers=meridian_headers)
    assert cross_comp_res.status_code == 404


# ─── 2. Client Injection & Unauthorized Role Mutations (Vectors 06 - 08) ────────

def test_adv_p17_06_client_org_id_injection(client: TestClient, adv_p17_fixture):
    """ADV-P17-06: Client Org ID Injection -> Server ignores client org ID, binds JWT org."""
    apex_analyst = adv_p17_fixture["apex_grc_analyst"]
    org_apex = adv_p17_fixture["org_apex"]
    headers = get_token_headers(apex_analyst)

    # Attempt to inject arbitrary organization_id in body
    payload = {
        "organization_id": 99999,
        "product_code": "APEX-INJECT-01",
        "name": "Injection Test Product",
    }
    res = client.post("/api/v1/supply-chain/products", json=payload, headers=headers)
    assert res.status_code == 201
    assert res.json()["organization_id"] == org_apex.id
    assert res.json()["organization_id"] != 99999


def test_adv_p17_07_unauthorized_product_creation(client: TestClient, adv_p17_fixture):
    """ADV-P17-07: Unauthorized Product Creation (VIEWER / AUDITOR) -> 403 Forbidden."""
    viewer = adv_p17_fixture["apex_viewer"]
    auditor = adv_p17_fixture["apex_auditor"]
    viewer_headers = get_token_headers(viewer)
    auditor_headers = get_token_headers(auditor)

    payload = {"product_code": "UNAUTH-PROD", "name": "Unauthorized App"}

    v_res = client.post("/api/v1/supply-chain/products", json=payload, headers=viewer_headers)
    assert v_res.status_code == 403

    a_res = client.post("/api/v1/supply-chain/products", json=payload, headers=auditor_headers)
    assert a_res.status_code == 403


def test_adv_p17_08_unauthorized_sbom_ingestion(client: TestClient, adv_p17_fixture):
    """ADV-P17-08: Unauthorized SBOM Ingestion (VIEWER / AUDITOR) -> 403 Forbidden."""
    admin = adv_p17_fixture["apex_admin"]
    viewer = adv_p17_fixture["apex_viewer"]
    admin_headers = get_token_headers(admin)
    viewer_headers = get_token_headers(viewer)

    p_res = client.post(
        "/api/v1/supply-chain/products",
        json={"product_code": "APEX-PROD-08", "name": "App 08"},
        headers=admin_headers,
    )
    prod_id = p_res.json()["id"]

    # Viewer attempts SBOM ingestion
    v_res = client.post(
        f"/api/v1/supply-chain/products/{prod_id}/sboms",
        json={
            "software_product_id": prod_id,
            "sbom_code": "VIEWER-SBOM",
            "version": "1.0",
            "sha256_hash": "e" * 64,
        },
        headers=viewer_headers,
    )
    assert v_res.status_code == 403


# ─── 3. Four-Eyes Segregation of Duties & Replay Attacks (Vectors 09 - 11) ─────

def test_adv_p17_09_four_eyes_exemption_self_review(client: TestClient, adv_p17_fixture):
    """ADV-P17-09: Four-Eyes Exemption Self-Review -> 422 Unprocessable Entity."""
    analyst = adv_p17_fixture["apex_grc_analyst"]
    manager = adv_p17_fixture["apex_manager"]
    analyst_headers = get_token_headers(analyst)
    mgr_headers = get_token_headers(manager)

    p_res = client.post(
        "/api/v1/supply-chain/products",
        json={"product_code": "PROD-SOD-09", "name": "App 09"},
        headers=analyst_headers,
    )
    prod_id = p_res.json()["id"]

    s_res = client.post(
        f"/api/v1/supply-chain/products/{prod_id}/sboms",
        json={"software_product_id": prod_id, "sbom_code": "SBOM-09", "version": "1.0", "sha256_hash": "f" * 64},
        headers=analyst_headers,
    )
    sbom_id = s_res.json()["id"]

    c_res = client.post(
        f"/api/v1/supply-chain/sboms/{sbom_id}/components",
        json={
            "sbom_document_id": sbom_id,
            "component_name": "legacy-dep",
            "version": "1.0.0",
            "purl": "pkg:npm/legacy-dep@1.0.0",
            "declared_license": "Proprietary",
        },
        headers=analyst_headers,
    )
    comp_id = c_res.json()["id"]

    # Manager requests exemption
    ex_res = client.post(
        "/api/v1/supply-chain/exemptions",
        json={
            "exemption_code": "EX-SOD-09",
            "software_product_id": prod_id,
            "component_id": comp_id,
            "reason": "Business critical dependency justification",
            "compensating_controls": "Perimeter network isolation",
        },
        headers=mgr_headers,
    )
    ex_id = ex_res.json()["id"]

    # Manager attempts to approve their OWN requested exemption -> 422
    self_rev = client.post(
        f"/api/v1/supply-chain/exemptions/{ex_id}/review",
        json={"decision": "APPROVED", "reviewer_notes": "Self review approved"},
        headers=mgr_headers,
    )
    assert self_rev.status_code == 422
    assert "Segregation of Duties" in self_rev.json()["detail"]


def test_adv_p17_10_spoofed_reviewer_identity_injection(client: TestClient, adv_p17_fixture):
    """ADV-P17-10: Spoofed Reviewer Identity Injection -> Body field ignored, derives from JWT."""
    analyst = adv_p17_fixture["apex_grc_analyst"]
    manager = adv_p17_fixture["apex_manager"]
    analyst_headers = get_token_headers(analyst)
    manager_headers = get_token_headers(manager)

    p_res = client.post(
        "/api/v1/supply-chain/products",
        json={"product_code": "PROD-SPOOF-10", "name": "App 10"},
        headers=analyst_headers,
    )
    prod_id = p_res.json()["id"]

    s_res = client.post(
        f"/api/v1/supply-chain/products/{prod_id}/sboms",
        json={"software_product_id": prod_id, "sbom_code": "SBOM-10", "version": "1.0", "sha256_hash": "0" * 64},
        headers=analyst_headers,
    )
    sbom_id = s_res.json()["id"]

    c_res = client.post(
        f"/api/v1/supply-chain/sboms/{sbom_id}/components",
        json={
            "sbom_document_id": sbom_id,
            "component_name": "dep-10",
            "version": "1.0.0",
            "purl": "pkg:npm/dep-10@1.0.0",
        },
        headers=analyst_headers,
    )
    comp_id = c_res.json()["id"]

    ex_res = client.post(
        "/api/v1/supply-chain/exemptions",
        json={
            "exemption_code": "EX-SPOOF-10",
            "software_product_id": prod_id,
            "component_id": comp_id,
            "reason": "Business critical dependency justification",
            "compensating_controls": "Compensating controls detail",
        },
        headers=analyst_headers,
    )
    ex_id = ex_res.json()["id"]

    # Manager approves, injecting fake reviewer_id = 99999
    rev_res = client.post(
        f"/api/v1/supply-chain/exemptions/{ex_id}/review",
        json={"decision": "APPROVED", "reviewer_notes": "Valid review notes", "reviewer_id": 99999},
        headers=manager_headers,
    )
    assert rev_res.status_code == 200
    assert rev_res.json()["reviewed_by_id"] == manager.id
    assert rev_res.json()["reviewed_by_id"] != 99999


def test_adv_p17_11_finalized_exemption_replay_attack(client: TestClient, adv_p17_fixture):
    """ADV-P17-11: Finalized Exemption Replay Attack -> 409 Conflict."""
    admin = adv_p17_fixture["apex_admin"]
    analyst = adv_p17_fixture["apex_grc_analyst"]
    manager = adv_p17_fixture["apex_manager"]
    analyst_headers = get_token_headers(analyst)
    manager_headers = get_token_headers(manager)
    admin_headers = get_token_headers(admin)

    p_res = client.post(
        "/api/v1/supply-chain/products",
        json={"product_code": "PROD-REPLAY-11", "name": "App 11"},
        headers=analyst_headers,
    )
    prod_id = p_res.json()["id"]

    s_res = client.post(
        f"/api/v1/supply-chain/products/{prod_id}/sboms",
        json={"software_product_id": prod_id, "sbom_code": "SBOM-11", "version": "1.0", "sha256_hash": "1" * 64},
        headers=analyst_headers,
    )
    sbom_id = s_res.json()["id"]

    c_res = client.post(
        f"/api/v1/supply-chain/sboms/{sbom_id}/components",
        json={
            "sbom_document_id": sbom_id,
            "component_name": "dep-11",
            "version": "1.0.0",
            "purl": "pkg:npm/dep-11@1.0.0",
        },
        headers=analyst_headers,
    )
    comp_id = c_res.json()["id"]

    ex_res = client.post(
        "/api/v1/supply-chain/exemptions",
        json={
            "exemption_code": "EX-REPLAY-11",
            "software_product_id": prod_id,
            "component_id": comp_id,
            "reason": "Business critical dependency justification",
            "compensating_controls": "Compensating controls detail",
        },
        headers=analyst_headers,
    )
    ex_id = ex_res.json()["id"]

    # 1st review -> APPROVED
    client.post(
        f"/api/v1/supply-chain/exemptions/{ex_id}/review",
        json={"decision": "APPROVED", "reviewer_notes": "First valid approval"},
        headers=manager_headers,
    )

    # Replay review -> 409 Conflict
    replay_res = client.post(
        f"/api/v1/supply-chain/exemptions/{ex_id}/review",
        json={"decision": "REJECTED", "reviewer_notes": "Replay decision attempt"},
        headers=admin_headers,
    )
    assert replay_res.status_code == 409


# ─── 4. Lifecycle & Immutability Violations (Vectors 12 - 14) ──────────────────

def test_adv_p17_12_retired_product_mutation_lockout(client: TestClient, adv_p17_fixture):
    """ADV-P17-12: Retired Product Mutation Lockout -> 400 Bad Request."""
    admin = adv_p17_fixture["apex_admin"]
    headers = get_token_headers(admin)

    p_res = client.post(
        "/api/v1/supply-chain/products",
        json={"product_code": "PROD-LOCK-12", "name": "App 12"},
        headers=headers,
    )
    prod_id = p_res.json()["id"]

    # Transition to ACTIVE then RETIRED
    client.patch(f"/api/v1/supply-chain/products/{prod_id}/status", json={"lifecycle_state": "ACTIVE"}, headers=headers)
    client.patch(f"/api/v1/supply-chain/products/{prod_id}/status", json={"lifecycle_state": "RETIRED"}, headers=headers)

    # Attempt mutation on retired product
    mut_res = client.put(
        f"/api/v1/supply-chain/products/{prod_id}",
        json={"name": "Mutated Name on Retired Product"},
        headers=headers,
    )
    assert mut_res.status_code == 400
    assert "Governance Immutability Lock" in mut_res.json()["detail"]


def test_adv_p17_13_illegal_state_machine_transition(client: TestClient, adv_p17_fixture):
    """ADV-P17-13: Illegal State Machine Transition (DRAFT -> RETIRED directly) -> 422 Unprocessable Entity."""
    admin = adv_p17_fixture["apex_admin"]
    headers = get_token_headers(admin)

    p_res = client.post(
        "/api/v1/supply-chain/products",
        json={"product_code": "PROD-ILLEGAL-13", "name": "App 13"},
        headers=headers,
    )
    prod_id = p_res.json()["id"]

    # Illegal jump: DRAFT -> RETIRED
    illegal_res = client.patch(
        f"/api/v1/supply-chain/products/{prod_id}/status",
        json={"lifecycle_state": "RETIRED"},
        headers=headers,
    )
    assert illegal_res.status_code == 422


def test_adv_p17_14_active_product_direct_deletion(client: TestClient, adv_p17_fixture):
    """ADV-P17-14: Active Product Direct Deletion -> 400 Bad Request."""
    admin = adv_p17_fixture["apex_admin"]
    headers = get_token_headers(admin)

    p_res = client.post(
        "/api/v1/supply-chain/products",
        json={"product_code": "PROD-ACTIVE-14", "name": "App 14"},
        headers=headers,
    )
    prod_id = p_res.json()["id"]

    client.patch(f"/api/v1/supply-chain/products/{prod_id}/status", json={"lifecycle_state": "ACTIVE"}, headers=headers)

    # Attempt delete on ACTIVE product
    del_res = client.delete(f"/api/v1/supply-chain/products/{prod_id}", headers=headers)
    assert del_res.status_code == 400


# ─── 5. Cross-Module Foreign Key Escapes (Vectors 15 - 17) ─────────────────────

def test_adv_p17_15_cross_tenant_foreign_key_escape(client: TestClient, db: Session, adv_p17_fixture):
    """ADV-P17-15: Cross-Tenant Foreign Key Escape (business_process_id) -> 404 Not Found."""
    apex_analyst = adv_p17_fixture["apex_grc_analyst"]
    meridian_admin = adv_p17_fixture["meridian_admin"]
    org_meridian = adv_p17_fixture["org_meridian"]
    apex_headers = get_token_headers(apex_analyst)

    # Meridian business process
    bp_meridian = BusinessProcess(
        organization_id=org_meridian.id,
        owner_id=meridian_admin.id,
        name="Meridian Critical Process",
        criticality_tier=CriticalityTierEnum.TIER_1,
    )
    db.add(bp_meridian)
    db.commit()

    # Apex attempts to bind Meridian's process ID
    payload = {
        "product_code": "APEX-ESCAPE-15",
        "name": "Escaping Product",
        "business_process_id": bp_meridian.id,
    }
    res = client.post("/api/v1/supply-chain/products", json=payload, headers=apex_headers)
    assert res.status_code == 404


def test_adv_p17_16_cross_tenant_ai_system_linkage(client: TestClient, db: Session, adv_p17_fixture):
    """ADV-P17-16: Cross-Tenant AI System Linkage -> 404 Not Found."""
    apex_analyst = adv_p17_fixture["apex_grc_analyst"]
    meridian_admin = adv_p17_fixture["meridian_admin"]
    org_meridian = adv_p17_fixture["org_meridian"]
    apex_headers = get_token_headers(apex_analyst)

    # Meridian AI System
    ai_meridian = AISystem(
        organization_id=org_meridian.id,
        system_code="AI-SYS-MER-001",
        name="Meridian LLM",
        system_type=AISystemTypeEnum.LLM_APPLICATION,
        regulatory_tier=AIRegulatoryTierEnum.HIGH_RISK,
        hosting_type=AIHostingTypeEnum.CLOUD_THIRD_PARTY,
        owner_id=meridian_admin.id,
    )
    db.add(ai_meridian)
    db.commit()

    payload = {
        "product_code": "APEX-AI-ESCAPE-16",
        "name": "AI Product Escape",
        "ai_system_id": ai_meridian.id,
    }
    res = client.post("/api/v1/supply-chain/products", json=payload, headers=apex_headers)
    assert res.status_code == 404


def test_adv_p17_17_cross_tenant_vendor_escape(client: TestClient, db: Session, adv_p17_fixture):
    """ADV-P17-17: Cross-Tenant Vendor Escape -> 404 Not Found."""
    apex_analyst = adv_p17_fixture["apex_grc_analyst"]
    org_meridian = adv_p17_fixture["org_meridian"]
    apex_headers = get_token_headers(apex_analyst)

    # Meridian Vendor
    vendor_meridian = Vendor(
        organization_id=org_meridian.id,
        vendor_code="VEND-MER-001",
        legal_name="Meridian Foreign Vendor",
    )
    db.add(vendor_meridian)
    db.commit()

    payload = {
        "product_code": "APEX-VENDOR-ESCAPE-17",
        "name": "Vendor Product Escape",
        "vendor_id": vendor_meridian.id,
    }
    res = client.post("/api/v1/supply-chain/products", json=payload, headers=apex_headers)
    assert res.status_code == 404


# ─── 6. Parameter Tampering & Boundary Violations (Vectors 18 - 22) ────────────

def test_adv_p17_18_negative_score_parameter_injection(client: TestClient, adv_p17_fixture):
    """ADV-P17-18: Negative Score Parameter Injection -> 422 Unprocessable Entity."""
    analyst = adv_p17_fixture["apex_grc_analyst"]
    headers = get_token_headers(analyst)

    # Negative CVSS score in calculate-preview
    neg_res = client.post(
        "/api/v1/supply-chain/components/calculate-preview",
        json={"cvss_scores": [-5.0]},
        headers=headers,
    )
    assert neg_res.status_code == 422

    # Excessive CVSS score (> 10.0)
    excess_res = client.post(
        "/api/v1/supply-chain/components/calculate-preview",
        json={"cvss_scores": [15.0]},
        headers=headers,
    )
    assert excess_res.status_code == 422


def test_adv_p17_19_out_of_range_dependency_depth(client: TestClient, adv_p17_fixture):
    """ADV-P17-19: Out-of-Range Dependency Depth (< 1) -> 422 Unprocessable Entity."""
    analyst = adv_p17_fixture["apex_grc_analyst"]
    headers = get_token_headers(analyst)

    p_res = client.post(
        "/api/v1/supply-chain/products",
        json={"product_code": "PROD-DEPTH-19", "name": "Depth Test App"},
        headers=headers,
    )
    prod_id = p_res.json()["id"]

    s_res = client.post(
        f"/api/v1/supply-chain/products/{prod_id}/sboms",
        json={"software_product_id": prod_id, "sbom_code": "SBOM-19", "version": "1.0", "sha256_hash": "2" * 64},
        headers=headers,
    )
    sbom_id = s_res.json()["id"]

    # Dependency depth = 0 is invalid
    c_res = client.post(
        f"/api/v1/supply-chain/sboms/{sbom_id}/components",
        json={
            "sbom_document_id": sbom_id,
            "component_name": "depth-zero-lib",
            "version": "1.0.0",
            "purl": "pkg:npm/depth-zero-lib@1.0.0",
            "dependency_depth": 0,
        },
        headers=headers,
    )
    assert c_res.status_code == 422


def test_adv_p17_20_duplicate_product_code_collision(client: TestClient, adv_p17_fixture):
    """ADV-P17-20: Duplicate Product Code Collision -> 409 Conflict."""
    analyst = adv_p17_fixture["apex_grc_analyst"]
    headers = get_token_headers(analyst)

    payload = {"product_code": "DUP-PROD-20", "name": "App 20 A"}
    res1 = client.post("/api/v1/supply-chain/products", json=payload, headers=headers)
    assert res1.status_code == 201

    # Duplicate code in same organization
    res2 = client.post(
        "/api/v1/supply-chain/products",
        json={"product_code": "DUP-PROD-20", "name": "App 20 B"},
        headers=headers,
    )
    assert res2.status_code == 409


def test_adv_p17_21_duplicate_sbom_code_collision(client: TestClient, adv_p17_fixture):
    """ADV-P17-21: Duplicate SBOM Code Collision -> 409 Conflict."""
    analyst = adv_p17_fixture["apex_grc_analyst"]
    headers = get_token_headers(analyst)

    p_res = client.post(
        "/api/v1/supply-chain/products",
        json={"product_code": "PROD-SBOM-DUP-21", "name": "App 21"},
        headers=headers,
    )
    prod_id = p_res.json()["id"]

    payload = {
        "software_product_id": prod_id,
        "sbom_code": "DUP-SBOM-21",
        "version": "1.0",
        "sha256_hash": "3" * 64,
    }
    res1 = client.post(f"/api/v1/supply-chain/products/{prod_id}/sboms", json=payload, headers=headers)
    assert res1.status_code == 201

    res2 = client.post(f"/api/v1/supply-chain/products/{prod_id}/sboms", json=payload, headers=headers)
    assert res2.status_code == 409


def test_adv_p17_22_tampered_cryptographic_hash_length(client: TestClient, adv_p17_fixture):
    """ADV-P17-22: Tampered Cryptographic Hash Length -> 422 Unprocessable Entity."""
    analyst = adv_p17_fixture["apex_grc_analyst"]
    headers = get_token_headers(analyst)

    p_res = client.post(
        "/api/v1/supply-chain/products",
        json={"product_code": "PROD-HASH-22", "name": "App 22"},
        headers=headers,
    )
    prod_id = p_res.json()["id"]

    # Short hash
    short_res = client.post(
        f"/api/v1/supply-chain/products/{prod_id}/sboms",
        json={
            "software_product_id": prod_id,
            "sbom_code": "SHORT-HASH-SBOM",
            "version": "1.0",
            "sha256_hash": "abc123short",
        },
        headers=headers,
    )
    assert short_res.status_code == 422

    # Non-hex characters
    nonhex_res = client.post(
        f"/api/v1/supply-chain/products/{prod_id}/sboms",
        json={
            "software_product_id": prod_id,
            "sbom_code": "NONHEX-HASH-SBOM",
            "version": "1.0",
            "sha256_hash": "z" * 64,
        },
        headers=headers,
    )
    assert nonhex_res.status_code == 422


# ─── 7. Policy Enforcement & Audit Integrity (Vectors 23 - 25) ─────────────────

def test_adv_p17_23_prohibited_license_policy_bypass(client: TestClient, adv_p17_fixture):
    """ADV-P17-23: Prohibited License Policy Bypass -> Server flags is_license_prohibited = True."""
    admin = adv_p17_fixture["apex_admin"]
    analyst = adv_p17_fixture["apex_grc_analyst"]
    admin_headers = get_token_headers(admin)
    analyst_headers = get_token_headers(analyst)

    # 1. Admin defines prohibited license policy for AGPL-3.0-only
    client.post(
        "/api/v1/supply-chain/policies",
        json={
            "license_identifier": "AGPL-3.0-only",
            "name": "Affero GPL v3",
            "category": "STRONG_COPYLEFT",
            "is_prohibited": True,
            "risk_penalty_points": 30.0,
        },
        headers=admin_headers,
    )

    # 2. Product and SBOM
    p_res = client.post(
        "/api/v1/supply-chain/products",
        json={"product_code": "PROD-LIC-23", "name": "App 23"},
        headers=analyst_headers,
    )
    prod_id = p_res.json()["id"]

    s_res = client.post(
        f"/api/v1/supply-chain/products/{prod_id}/sboms",
        json={"software_product_id": prod_id, "sbom_code": "SBOM-23", "version": "1.0", "sha256_hash": "4" * 64},
        headers=analyst_headers,
    )
    sbom_id = s_res.json()["id"]

    # 3. Analyst submits component with is_license_prohibited=False attempt
    c_res = client.post(
        f"/api/v1/supply-chain/sboms/{sbom_id}/components",
        json={
            "sbom_document_id": sbom_id,
            "component_name": "agpl-module",
            "version": "3.1.0",
            "purl": "pkg:npm/agpl-module@3.1.0",
            "declared_license": "AGPL-3.0-only",
            "license_category": "STRONG_COPYLEFT",
            "is_license_prohibited": False,  # Client attempting to bypass policy
        },
        headers=analyst_headers,
    )
    assert c_res.status_code == 201
    # Server enforces policy lookup and sets True
    assert c_res.json()["is_license_prohibited"] is True


def test_adv_p17_24_short_audit_justification_submission(client: TestClient, adv_p17_fixture):
    """ADV-P17-24: Short Audit Justification Submission (< 5 chars) -> 422 Unprocessable Entity."""
    analyst = adv_p17_fixture["apex_grc_analyst"]
    manager = adv_p17_fixture["apex_manager"]
    analyst_headers = get_token_headers(analyst)
    mgr_headers = get_token_headers(manager)

    p_res = client.post(
        "/api/v1/supply-chain/products",
        json={"product_code": "PROD-SHORT-24", "name": "App 24"},
        headers=analyst_headers,
    )
    prod_id = p_res.json()["id"]

    s_res = client.post(
        f"/api/v1/supply-chain/products/{prod_id}/sboms",
        json={"software_product_id": prod_id, "sbom_code": "SBOM-24", "version": "1.0", "sha256_hash": "5" * 64},
        headers=analyst_headers,
    )
    sbom_id = s_res.json()["id"]

    c_res = client.post(
        f"/api/v1/supply-chain/sboms/{sbom_id}/components",
        json={"sbom_document_id": sbom_id, "component_name": "dep-24", "version": "1.0", "purl": "pkg:npm/dep-24@1.0"},
        headers=analyst_headers,
    )
    comp_id = c_res.json()["id"]

    ex_res = client.post(
        "/api/v1/supply-chain/exemptions",
        json={
            "exemption_code": "EX-24",
            "software_product_id": prod_id,
            "component_id": comp_id,
            "reason": "Valid detailed reason justification for exemption",
            "compensating_controls": "Valid compensating controls",
        },
        headers=analyst_headers,
    )
    ex_id = ex_res.json()["id"]

    # Short reviewer notes (< 5 chars, e.g. "ok") -> 422
    rev_res = client.post(
        f"/api/v1/supply-chain/exemptions/{ex_id}/review",
        json={"decision": "APPROVED", "reviewer_notes": "ok"},
        headers=mgr_headers,
    )
    assert rev_res.status_code == 422


def test_adv_p17_25_unauthenticated_endpoint_infiltration(client: TestClient):
    """ADV-P17-25: Unauthenticated Endpoint Infiltration -> 401 Unauthorized."""
    # Attempt access without Bearer token
    res = client.get("/api/v1/supply-chain/summary/posture")
    assert res.status_code == 401
