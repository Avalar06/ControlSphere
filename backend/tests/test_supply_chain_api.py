from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.permissions import RoleEnum
from app.core.security import get_password_hash
from app.models.organization import Organization
from app.models.user import User
from app.models.supply_chain import (
    ComponentEcosystemEnum,
    ExemptionApprovalStatusEnum,
    LicenseCategoryEnum,
    ProductCriticalityTierEnum,
    ProductLifecycleStateEnum,
    SBOMFormatStandardEnum,
    SBOMStatusEnum,
    SoftwareProductTypeEnum,
    SupplyChainRiskBandEnum,
)
from app.models.resilience import BusinessProcess, CriticalityTierEnum
from app.models.ai_governance import AISystem, AISystemTypeEnum, AIRegulatoryTierEnum, AIHostingTypeEnum
from app.models.tprm import Vendor, VendorTierEnum
from app.models.remediation import RemediationPlan, RemediationSourceTypeEnum
from app.models.exposure import VulnerabilityExposure, ExposureSeverityEnum
from tests.conftest import get_token_headers


@pytest.fixture
def sc_api_fixture(db: Session, org_apex: Organization, org_meridian: Organization):
    """Setup multi-tenant organizations and users across all 6 roles for Supply Chain API testing."""
    admin = User(
        email="sc_admin@apex.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="SC Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_apex.id,
    )
    manager = User(
        email="sc_manager@apex.com",
        hashed_password=get_password_hash("ManagerPass123!"),
        full_name="SC Manager",
        role=RoleEnum.MANAGER,
        is_active=True,
        organization_id=org_apex.id,
    )
    grc_analyst = User(
        email="sc_grc_analyst@apex.com",
        hashed_password=get_password_hash("GrcAnalystPass123!"),
        full_name="SC GRC Analyst",
        role=RoleEnum.GRC_ANALYST,
        is_active=True,
        organization_id=org_apex.id,
    )
    sec_analyst = User(
        email="sc_sec_analyst@apex.com",
        hashed_password=get_password_hash("SecAnalystPass123!"),
        full_name="SC Sec Analyst",
        role=RoleEnum.SECURITY_ANALYST,
        is_active=True,
        organization_id=org_apex.id,
    )
    auditor = User(
        email="sc_auditor@apex.com",
        hashed_password=get_password_hash("AuditorPass123!"),
        full_name="SC Auditor",
        role=RoleEnum.AUDITOR,
        is_active=True,
        organization_id=org_apex.id,
    )
    viewer = User(
        email="sc_viewer@apex.com",
        hashed_password=get_password_hash("ViewerPass123!"),
        full_name="SC Viewer",
        role=RoleEnum.VIEWER,
        is_active=True,
        organization_id=org_apex.id,
    )

    # Meridian User (Tenant B)
    meridian_admin = User(
        email="sc_admin@meridian.com",
        hashed_password=get_password_hash("MeridianPass123!"),
        full_name="Meridian Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_meridian.id,
    )

    db.add_all([admin, manager, grc_analyst, sec_analyst, auditor, viewer, meridian_admin])
    db.commit()

    return {
        "org_apex": org_apex,
        "org_meridian": org_meridian,
        "admin": admin,
        "manager": manager,
        "grc_analyst": grc_analyst,
        "sec_analyst": sec_analyst,
        "auditor": auditor,
        "viewer": viewer,
        "meridian_admin": meridian_admin,
    }


# ─── 1. Product CRUD API Tests ──────────────────────────────────────────────────

def test_create_and_get_product_api(client: TestClient, sc_api_fixture):
    admin = sc_api_fixture["admin"]
    headers = get_token_headers(admin)

    # 1. Create Product
    payload = {
        "product_code": "PROD-AUTH-001",
        "name": "Identity & Access Gateway",
        "description": "Enterprise SSO and OAuth2 authorization server",
        "product_type": "INTERNAL_APPLICATION",
        "criticality_tier": "TIER_1_CRITICAL",
    }
    response = client.post("/api/v1/supply-chain/products", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["product_code"] == "PROD-AUTH-001"
    assert data["name"] == "Identity & Access Gateway"
    assert data["lifecycle_state"] == "DRAFT"
    assert data["supply_chain_exposure_index"] == 0.0
    assert data["risk_band"] == "LOW"
    product_id = data["id"]

    # 2. Get Product Detail
    get_res = client.get(f"/api/v1/supply-chain/products/{product_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == product_id


def test_list_and_filter_products_api(client: TestClient, sc_api_fixture):
    analyst = sc_api_fixture["grc_analyst"]
    headers = get_token_headers(analyst)

    # Create 2 products
    client.post(
        "/api/v1/supply-chain/products",
        json={"product_code": "PROD-LIST-1", "name": "App 1", "criticality_tier": "TIER_1_CRITICAL"},
        headers=headers,
    )
    client.post(
        "/api/v1/supply-chain/products",
        json={"product_code": "PROD-LIST-2", "name": "App 2", "criticality_tier": "TIER_3_MODERATE"},
        headers=headers,
    )

    # List all
    res = client.get("/api/v1/supply-chain/products", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) >= 2

    # Filter by criticality tier
    res_crit = client.get("/api/v1/supply-chain/products?criticality_tier=TIER_1_CRITICAL", headers=headers)
    assert res_crit.status_code == 200
    assert all(p["criticality_tier"] == "TIER_1_CRITICAL" for p in res_crit.json())


def test_update_and_lifecycle_status_transition_api(client: TestClient, sc_api_fixture):
    admin = sc_api_fixture["admin"]
    headers = get_token_headers(admin)

    # Create product
    create_res = client.post(
        "/api/v1/supply-chain/products",
        json={"product_code": "PROD-STATE-01", "name": "State Test App"},
        headers=headers,
    )
    prod_id = create_res.json()["id"]

    # Update metadata
    upd_res = client.put(
        f"/api/v1/supply-chain/products/{prod_id}",
        json={"name": "Renamed State App", "description": "Updated Description"},
        headers=headers,
    )
    assert upd_res.status_code == 200
    assert upd_res.json()["name"] == "Renamed State App"

    # Transition DRAFT -> ACTIVE
    status_res = client.patch(
        f"/api/v1/supply-chain/products/{prod_id}/status",
        json={"lifecycle_state": "ACTIVE", "notes": "Production launch approved"},
        headers=headers,
    )
    assert status_res.status_code == 200
    assert status_res.json()["lifecycle_state"] == "ACTIVE"

    # Transition ACTIVE -> DEPRECATED
    dep_res = client.patch(
        f"/api/v1/supply-chain/products/{prod_id}/status",
        json={"lifecycle_state": "DEPRECATED", "notes": "Sunset roadmap initiated"},
        headers=headers,
    )
    assert dep_res.status_code == 200
    assert dep_res.json()["lifecycle_state"] == "DEPRECATED"

    # Transition DEPRECATED -> RETIRED
    ret_res = client.patch(
        f"/api/v1/supply-chain/products/{prod_id}/status",
        json={"lifecycle_state": "RETIRED", "notes": "Permanently decommissioned"},
        headers=headers,
    )
    assert ret_res.status_code == 200
    assert ret_res.json()["lifecycle_state"] == "RETIRED"


def test_delete_product_api(client: TestClient, sc_api_fixture):
    admin = sc_api_fixture["admin"]
    headers = get_token_headers(admin)

    # Create draft product
    create_res = client.post(
        "/api/v1/supply-chain/products",
        json={"product_code": "PROD-DEL-01", "name": "Ephemeral App"},
        headers=headers,
    )
    prod_id = create_res.json()["id"]

    # Delete draft product -> 204
    del_res = client.delete(f"/api/v1/supply-chain/products/{prod_id}", headers=headers)
    assert del_res.status_code == 204

    # Verify 404 after deletion
    get_res = client.get(f"/api/v1/supply-chain/products/{prod_id}", headers=headers)
    assert get_res.status_code == 404


# ─── 2. SBOM Ingestion & Component API Tests ───────────────────────────────────

def test_sbom_ingestion_and_component_indexing_api(client: TestClient, sc_api_fixture):
    analyst = sc_api_fixture["grc_analyst"]
    headers = get_token_headers(analyst)

    # 1. Create product
    prod_res = client.post(
        "/api/v1/supply-chain/products",
        json={"product_code": "PROD-SBOM-API", "name": "Core Banking API"},
        headers=headers,
    )
    prod_id = prod_res.json()["id"]

    # 2. Ingest SBOM
    valid_sha = "a" * 64
    sbom_payload = {
        "software_product_id": prod_id,
        "sbom_code": "SBOM-BANK-V1",
        "version": "1.0.0",
        "format_standard": "CYCLONEDX_JSON",
        "spec_version": "1.5",
        "sha256_hash": valid_sha,
        "author_name": "SecOps Automation",
        "tool_name": "Syft 1.2.0",
    }
    sbom_res = client.post(f"/api/v1/supply-chain/products/{prod_id}/sboms", json=sbom_payload, headers=headers)
    assert sbom_res.status_code == 201
    sbom_id = sbom_res.json()["id"]
    assert sbom_res.json()["status"] == "ACTIVE"

    # 3. Add Component
    comp_payload = {
        "sbom_document_id": sbom_id,
        "component_name": "log4j-core",
        "version": "2.14.1",
        "purl": "pkg:maven/org.apache.logging.log4j/log4j-core@2.14.1",
        "ecosystem": "MAVEN",
        "dependency_depth": 1,
        "declared_license": "Apache-2.0",
        "license_category": "PERMISSIVE",
    }
    comp_res = client.post(f"/api/v1/supply-chain/sboms/{sbom_id}/components", json=comp_payload, headers=headers)
    assert comp_res.status_code == 201
    comp_id = comp_res.json()["id"]
    assert comp_res.json()["component_name"] == "log4j-core"

    # 4. Link Vulnerability (using Sec Analyst)
    sec_analyst = sc_api_fixture["sec_analyst"]
    sec_headers = get_token_headers(sec_analyst)

    vuln_payload = {
        "component_id": comp_id,
        "cve_identifier": "CVE-2021-44228",
        "severity_score": 10.0,
        "is_exploitable": True,
        "is_reachable": True,
        "fix_version": "2.17.1",
    }
    vuln_res = client.post(f"/api/v1/supply-chain/components/{comp_id}/vulnerabilities", json=vuln_payload, headers=sec_headers)
    assert vuln_res.status_code == 201

    # 5. Verify recalculated Component and Product risk
    comp_check = client.get(f"/api/v1/supply-chain/components/{comp_id}", headers=headers)
    assert comp_check.status_code == 200
    assert comp_check.json()["component_risk_index"] == 100.0
    assert comp_check.json()["risk_band"] == "CRITICAL"

    prod_check = client.get(f"/api/v1/supply-chain/products/{prod_id}", headers=headers)
    assert prod_check.status_code == 200
    assert prod_check.json()["supply_chain_exposure_index"] == 100.0
    assert prod_check.json()["vulnerable_components_count"] == 1


# ─── 3. License Policy & Preview Calculation API Tests ─────────────────────────

def test_license_policy_and_preview_calculations_api(client: TestClient, sc_api_fixture):
    admin = sc_api_fixture["admin"]
    headers = get_token_headers(admin)

    # 1. Create License Policy
    policy_res = client.post(
        "/api/v1/supply-chain/policies",
        json={
            "license_identifier": "AGPL-3.0-or-later",
            "name": "GNU Affero General Public License v3+",
            "category": "STRONG_COPYLEFT",
            "is_prohibited": True,
            "risk_penalty_points": 30.0,
        },
        headers=headers,
    )
    assert policy_res.status_code == 201
    assert policy_res.json()["is_prohibited"] is True

    # 2. List Policies
    list_res = client.get("/api/v1/supply-chain/policies", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # 3. Component Live Calculation Preview
    preview_req = {
        "cvss_scores": [8.5, 5.0],
        "is_any_exploitable": False,
        "dependency_depth": 2,
        "license_category": "WEAK_COPYLEFT",
        "is_exempted": False,
    }
    comp_prev = client.post("/api/v1/supply-chain/components/calculate-preview", json=preview_req, headers=headers)
    assert comp_prev.status_code == 200
    data = comp_prev.json()
    # Vscore = 85.0 + 7.5 = 92.5; Lrisk = 10.0; Depth = 1.10; CRI = (92.5 + 10.0) * 1.10 = 112.75 -> Clamped 100.0
    assert data["vulnerability_score"] == 92.5
    assert data["depth_penalty_multiplier"] == 1.10
    assert data["license_risk_points"] == 10.0
    assert data["component_risk_index"] == 100.0
    assert data["risk_band"] == "CRITICAL"

    # 4. Product Live Calculation Preview
    prod_prev_req = {
        "component_risk_indices": [80.0, 40.0],
    }
    prod_prev = client.post("/api/v1/supply-chain/products/calculate-preview", json=prod_prev_req, headers=headers)
    assert prod_prev.status_code == 200
    # SCEI = 80 * 0.60 + 60 * 0.40 = 48 + 24 = 72.0
    assert prod_prev.json()["supply_chain_exposure_index"] == 72.0
    assert prod_prev.json()["risk_band"] == "HIGH"


# ─── 4. Four-Eyes Exemption Governance API Tests ───────────────────────────────

def test_four_eyes_exemption_workflow_api(client: TestClient, sc_api_fixture):
    analyst = sc_api_fixture["grc_analyst"]
    manager = sc_api_fixture["manager"]
    analyst_headers = get_token_headers(analyst)
    manager_headers = get_token_headers(manager)

    # 1. Create Product, SBOM, and Component
    p_res = client.post(
        "/api/v1/supply-chain/products",
        json={"product_code": "PROD-EX-API", "name": "Payment Gateway"},
        headers=analyst_headers,
    )
    prod_id = p_res.json()["id"]

    s_res = client.post(
        f"/api/v1/supply-chain/products/{prod_id}/sboms",
        json={
            "software_product_id": prod_id,
            "sbom_code": "SBOM-PAY-EX",
            "version": "1.0",
            "sha256_hash": "b" * 64,
        },
        headers=analyst_headers,
    )
    sbom_id = s_res.json()["id"]

    c_res = client.post(
        f"/api/v1/supply-chain/sboms/{sbom_id}/components",
        json={
            "sbom_document_id": sbom_id,
            "component_name": "crypto-legacy",
            "version": "0.9.8",
            "purl": "pkg:npm/crypto-legacy@0.9.8",
            "declared_license": "Proprietary",
            "license_category": "PROHIBITED",
        },
        headers=analyst_headers,
    )
    comp_id = c_res.json()["id"]

    # 2. Analyst submits Exemption Request
    ex_payload = {
        "exemption_code": "EX-PAY-001",
        "software_product_id": prod_id,
        "component_id": comp_id,
        "reason": "Required for legacy banking HSM integration",
        "compensating_controls": "Strict network perimeter isolation",
    }
    ex_res = client.post("/api/v1/supply-chain/exemptions", json=ex_payload, headers=analyst_headers)
    assert ex_res.status_code == 201
    ex_id = ex_res.json()["id"]
    # 3. Analyst attempts review (Unauthorized Role) -> 403
    unauth_review = client.post(
        f"/api/v1/supply-chain/exemptions/{ex_id}/review",
        json={"decision": "APPROVED", "reviewer_notes": "Analyst approval attempt"},
        headers=analyst_headers,
    )
    assert unauth_review.status_code == 403

    # 4. Manager reviews and approves
    mgr_approve_res = client.post(
        f"/api/v1/supply-chain/exemptions/{ex_id}/review",
        json={"decision": "APPROVED", "reviewer_notes": "Reviewed and approved with HSM compensating controls"},
        headers=manager_headers,
    )
    assert mgr_approve_res.status_code == 200
    assert mgr_approve_res.json()["approval_status"] == "APPROVED"
    assert mgr_approve_res.json()["reviewed_by_id"] == manager.id

    # 5. Component CRI is halved due to exemption
    comp_check = client.get(f"/api/v1/supply-chain/components/{comp_id}", headers=analyst_headers)
    assert comp_check.status_code == 200
    assert comp_check.json()["is_exempted"] is True
    assert comp_check.json()["component_risk_index"] == 15.0  # 30.0 * 0.50 = 15.0


# ─── 5. Executive Posture Telemetry API Tests ──────────────────────────────────

def test_executive_posture_telemetry_api(client: TestClient, sc_api_fixture):
    auditor = sc_api_fixture["auditor"]
    headers = get_token_headers(auditor)

    res = client.get("/api/v1/supply-chain/summary/posture", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "total_software_products" in data
    assert "active_products_count" in data
    assert "total_sboms_indexed" in data
    assert "total_components_cataloged" in data
    assert "criticality_distribution" in data
    assert "license_category_distribution" in data
    assert "risk_band_distribution" in data
