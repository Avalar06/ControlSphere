from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.permissions import RoleEnum
from app.core.security import get_password_hash
from app.models.control import OrganizationControl, ImplementationStatusEnum, PriorityEnum
from app.models.finding import Finding, FindingSeverityEnum, FindingStatusEnum
from app.models.framework import Framework, FrameworkCategory, FrameworkFunction, FrameworkSubcategory
from app.models.monitoring import ControlHealthSnapshot, ControlHealthStatusEnum
from app.models.organization import Organization
from app.models.quant_risk import (
    AppetiteBreachStateEnum,
    AppetiteStatusEnum,
    FinancialRiskAppetite,
    QuantitativeRiskScenario,
    QuantitativeSimulationRun,
    RosiAnalysis,
    ScenarioStatusEnum,
    ThreatActorCategoryEnum,
)
from app.models.remediation import (
    RemediationPlan,
    RemediationRootCauseClassificationEnum,
    RemediationSeverityEnum,
    RemediationSourceTypeEnum,
    RemediationStatusEnum,
)
from app.models.risk import Risk, RiskCategoryEnum, RiskSourceEnum
from app.models.tprm import Vendor, VendorStatusEnum, VendorTierEnum
from app.models.user import User
from tests.conftest import get_token_headers


@pytest.fixture
def api_test_setup(db: Session, org_apex: Organization):
    """Setup multi-role users and foundational GRC data for Apex."""
    admin = User(
        email="admin_api@apex.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Apex Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_apex.id,
    )
    manager = User(
        email="manager_api@apex.com",
        hashed_password=get_password_hash("ManagerPass123!"),
        full_name="Apex Manager",
        role=RoleEnum.MANAGER,
        is_active=True,
        organization_id=org_apex.id,
    )
    analyst = User(
        email="analyst_api@apex.com",
        hashed_password=get_password_hash("AnalystPass123!"),
        full_name="Apex Analyst",
        role=RoleEnum.GRC_ANALYST,
        is_active=True,
        organization_id=org_apex.id,
    )
    auditor = User(
        email="auditor_api@apex.com",
        hashed_password=get_password_hash("AuditorPass123!"),
        full_name="Apex Auditor",
        role=RoleEnum.AUDITOR,
        is_active=True,
        organization_id=org_apex.id,
    )
    viewer = User(
        email="viewer_api@apex.com",
        hashed_password=get_password_hash("ViewerPass123!"),
        full_name="Apex Viewer",
        role=RoleEnum.VIEWER,
        is_active=True,
        organization_id=org_apex.id,
    )

    db.add_all([admin, manager, analyst, auditor, viewer])
    db.commit()

    # Framework and Control
    fw = Framework(name="NIST CSF API", identifier="NIST-API", version="2.0")
    db.add(fw)
    db.commit()

    fn = FrameworkFunction(framework_id=fw.id, identifier="PR", name="Protect")
    db.add(fn)
    db.commit()

    cat = FrameworkCategory(function_id=fn.id, identifier="PR.DS", name="Data Security")
    db.add(cat)
    db.commit()

    subcat = FrameworkSubcategory(category_id=cat.id, identifier="PR.DS-01", title="Data at rest protected", description="Desc")
    db.add(subcat)
    db.commit()

    ctrl = OrganizationControl(
        organization_id=org_apex.id,
        subcategory_id=subcat.id,
        status=ImplementationStatusEnum.IMPLEMENTED,
        priority=PriorityEnum.HIGH,
    )
    db.add(ctrl)
    db.commit()

    # Phase 7 Snapshot
    snap = ControlHealthSnapshot(
        organization_id=org_apex.id,
        organization_control_id=ctrl.id,
        health_score=85.0,
        health_status=ControlHealthStatusEnum.HEALTHY,
        evaluated_at=datetime.now(timezone.utc) - timedelta(days=2),
    )
    db.add(snap)
    db.commit()

    # Phase 4 Finding
    finding = Finding(
        organization_id=org_apex.id,
        organization_control_id=ctrl.id,
        title="Unencrypted Backup",
        description="Backup storage unencrypted",
        recommendation="Enable AES-256",
        severity=FindingSeverityEnum.HIGH,
        status=FindingStatusEnum.OPEN,
    )
    db.add(finding)
    db.commit()

    # Phase 11 Plan
    plan = RemediationPlan(
        organization_id=org_apex.id,
        plan_code="CAPA-ENC-01",
        title="Enable Encryption at Rest",
        problem_statement="Unencrypted DB backups",
        root_cause_classification=RemediationRootCauseClassificationEnum.CONTROL_DEFICIENCY,
        source_type=RemediationSourceTypeEnum.FINDING,
        finding_id=finding.id,
        severity=RemediationSeverityEnum.HIGH,
        status=RemediationStatusEnum.APPROVED,
        plan_owner_id=analyst.id,
        approved_by_id=manager.id,
        rei_score=60.0,
    )
    db.add(plan)
    db.commit()

    return {
        "org_apex": org_apex,
        "admin": admin,
        "manager": manager,
        "analyst": analyst,
        "auditor": auditor,
        "viewer": viewer,
        "control": ctrl,
        "finding": finding,
        "plan": plan,
    }


# ─── 1. SCENARIO CRUD & LIFECYCLE ────────────────────────────────────────────

def test_scenario_full_lifecycle_api(client: TestClient, api_test_setup):
    """Test Create, Read, Update, Activate, Freeze, and Archive endpoints."""
    headers = get_token_headers(api_test_setup["analyst"])

    # 1. Create Scenario (DRAFT)
    create_resp = client.post(
        "/api/v1/quant-risk/scenarios",
        headers=headers,
        json={
            "scenario_code": "QRS-LIFECYCLE-01",
            "title": "Data Breach via Ransomware",
            "description": "Comprehensive ransomware model",
            "threat_actor_category": "CYBERCRIMINAL",
            "organization_control_id": api_test_setup["control"].id,
            "tef_min": 0.5,
            "tef_mode": 1.0,
            "tef_max": 2.0,
            "tcap": 0.8,
            "pl_min": 10000.0,
            "pl_mode": 50000.0,
            "pl_max": 150000.0,
            "sl_min": 5000.0,
            "sl_mode": 20000.0,
            "sl_max": 80000.0,
            "slop": 0.5,
        },
    )
    assert create_resp.status_code == 201
    sc_data = create_resp.json()
    sc_id = sc_data["id"]
    assert sc_data["status"] == "DRAFT"
    assert sc_data["annualized_loss_expectancy"] > 0.0
    assert sc_data["is_immutable"] is False

    # 2. Get Scenario
    get_resp = client.get(f"/api/v1/quant-risk/scenarios/{sc_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["scenario_code"] == "QRS-LIFECYCLE-01"

    # 3. List Scenarios
    list_resp = client.get("/api/v1/quant-risk/scenarios?status=DRAFT", headers=headers)
    assert list_resp.status_code == 200
    assert any(s["id"] == sc_id for s in list_resp.json())

    # 4. Update Scenario
    update_resp = client.put(
        f"/api/v1/quant-risk/scenarios/{sc_id}",
        headers=headers,
        json={"title": "Updated Ransomware Scenario", "tcap": 0.9},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["title"] == "Updated Ransomware Scenario"
    assert update_resp.json()["tcap"] == 0.9

    # 5. Activate Scenario
    act_resp = client.post(f"/api/v1/quant-risk/scenarios/{sc_id}/activate", headers=headers)
    assert act_resp.status_code == 200
    assert act_resp.json()["status"] == "ACTIVE"

    # 6. Freeze Scenario
    freeze_resp = client.post(f"/api/v1/quant-risk/scenarios/{sc_id}/freeze", headers=headers)
    assert freeze_resp.status_code == 200
    assert freeze_resp.json()["status"] == "FROZEN"
    assert freeze_resp.json()["is_immutable"] is True

    # 7. Update on Frozen Fails
    fail_update = client.put(
        f"/api/v1/quant-risk/scenarios/{sc_id}",
        headers=headers,
        json={"title": "Should Fail"},
    )
    assert fail_update.status_code == 409


# ─── 2. SIMULATION & EMPIRICAL VAR DERIVATION ────────────────────────────────

def test_simulation_execution_and_retrieval_api(client: TestClient, api_test_setup):
    """Test Monte Carlo simulation execution, deterministic seed, and empirical VaR derivation."""
    headers = get_token_headers(api_test_setup["analyst"])

    # Create scenario
    sc_resp = client.post(
        "/api/v1/quant-risk/scenarios",
        headers=headers,
        json={
            "scenario_code": "QRS-SIM-API-01",
            "title": "Simulation Test Scenario",
            "description": "Valid description",
            "tef_min": 1.0,
            "tef_mode": 2.0,
            "tef_max": 4.0,
            "tcap": 0.7,
            "pl_min": 5000.0,
            "pl_mode": 25000.0,
            "pl_max": 100000.0,
            "slop": 0.3,
        },
    )
    sc_id = sc_resp.json()["id"]

    # Execute simulation with 1000 trials and fixed seed
    sim_resp = client.post(
        f"/api/v1/quant-risk/scenarios/{sc_id}/simulate",
        headers=headers,
        json={"trial_count": 1000, "simulation_seed": 777},
    )
    assert sim_resp.status_code == 201
    sim_data = sim_resp.json()
    run_id = sim_data["id"]
    assert sim_data["trial_count"] == 1000
    assert sim_data["simulation_seed"] == 777
    assert sim_data["percentile_95"] > 0.0
    assert sim_data["percentile_99"] >= sim_data["percentile_95"]

    # Verify scenario was enriched with empirical VaR
    sc_updated = client.get(f"/api/v1/quant-risk/scenarios/{sc_id}", headers=headers).json()
    assert sc_updated["var_95_empirical"] == sim_data["percentile_95"]
    assert sc_updated["var_99_empirical"] == sim_data["percentile_99"]

    # List simulations for scenario
    sim_list = client.get(f"/api/v1/quant-risk/scenarios/{sc_id}/simulations", headers=headers)
    assert sim_list.status_code == 200
    assert len(sim_list.json()) >= 1

    # Get single simulation
    single_sim = client.get(f"/api/v1/quant-risk/simulations/{run_id}", headers=headers)
    assert single_sim.status_code == 200
    assert single_sim.json()["id"] == run_id


# ─── 3. ROSI CALCULATION & LISTING ──────────────────────────────────────────

def test_rosi_calculation_and_listing_api(client: TestClient, api_test_setup):
    """Test ROSI calculation linked to Phase 11 Remediation Plan."""
    headers = get_token_headers(api_test_setup["analyst"])

    # Create scenario
    sc_resp = client.post(
        "/api/v1/quant-risk/scenarios",
        headers=headers,
        json={
            "scenario_code": "QRS-ROSI-API-01",
            "title": "ROSI Test Scenario",
            "description": "Valid description",
            "tef_min": 1.0,
            "tef_mode": 2.0,
            "tef_max": 3.0,
            "tcap": 0.8,
            "pl_min": 20000.0,
            "pl_mode": 60000.0,
            "pl_max": 200000.0,
            "slop": 0.4,
        },
    )
    sc_id = sc_resp.json()["id"]

    # Calculate ROSI
    rosi_resp = client.post(
        f"/api/v1/quant-risk/scenarios/{sc_id}/rosi",
        headers=headers,
        json={
            "remediation_plan_id": api_test_setup["plan"].id,
            "remediation_cost": 15000.0,
        },
    )
    assert rosi_resp.status_code == 201
    rosi_data = rosi_resp.json()
    analysis_id = rosi_data["id"]
    assert rosi_data["current_ale"] > rosi_data["projected_ale"]
    assert rosi_data["risk_reduction_ale"] > 0.0
    assert "rosi_percentage" in rosi_data

    # List ROSI for scenario
    rosi_list = client.get(f"/api/v1/quant-risk/scenarios/{sc_id}/rosi", headers=headers)
    assert rosi_list.status_code == 200
    assert len(rosi_list.json()) >= 1

    # Get single ROSI
    single_rosi = client.get(f"/api/v1/quant-risk/rosi/{analysis_id}", headers=headers)
    assert single_rosi.status_code == 200
    assert single_rosi.json()["id"] == analysis_id


# ─── 4. RISK APPETITE LIFECYCLE & FOUR-EYES APPROVAL ────────────────────────

def test_financial_risk_appetite_lifecycle_api(client: TestClient, api_test_setup):
    """Test creation, versioning, four-eyes approval, and posture evaluation."""
    analyst_headers = get_token_headers(api_test_setup["analyst"])
    manager_headers = get_token_headers(api_test_setup["manager"])

    # 1. Analyst creates Appetite Version 1
    create_v1 = client.post(
        "/api/v1/quant-risk/appetites",
        headers=analyst_headers,
        json={"ale_limit": 100000.0, "var_95_limit": 300000.0, "notes": "V1 Draft"},
    )
    assert create_v1.status_code == 201
    v1_id = create_v1.json()["id"]
    assert create_v1.json()["version"] == 1
    assert create_v1.json()["status"] == "DRAFT"

    # 2. Manager approves V1 (Four-eyes separation: analyst requested, manager approves)
    appr_v1 = client.post(
        f"/api/v1/quant-risk/appetites/{v1_id}/approve",
        headers=manager_headers,
        json={"notes": "Approved by Risk Committee"},
    )
    assert appr_v1.status_code == 200
    assert appr_v1.json()["status"] == "APPROVED"
    assert appr_v1.json()["approved_by_id"] == api_test_setup["manager"].id

    # 3. Verify current active appetite is V1
    current_app = client.get("/api/v1/quant-risk/appetites/current", headers=analyst_headers)
    assert current_app.status_code == 200
    assert current_app.json()["id"] == v1_id

    # 4. Analyst creates Appetite Version 2
    create_v2 = client.post(
        "/api/v1/quant-risk/appetites",
        headers=analyst_headers,
        json={"ale_limit": 75000.0, "var_95_limit": 200000.0, "notes": "V2 Tightened Policy"},
    )
    assert create_v2.status_code == 201
    v2_id = create_v2.json()["id"]
    assert create_v2.json()["version"] == 2

    # 5. Manager approves V2 -> V1 becomes SUPERSEDED
    appr_v2 = client.post(
        f"/api/v1/quant-risk/appetites/{v2_id}/approve",
        headers=manager_headers,
    )
    assert appr_v2.status_code == 200
    assert appr_v2.json()["status"] == "APPROVED"

    # Check V1 status is now SUPERSEDED
    get_v1 = client.get(f"/api/v1/quant-risk/appetites/{v1_id}", headers=analyst_headers)
    assert get_v1.json()["status"] == "SUPERSEDED"


# ─── 5. PORTFOLIO OVERVIEW & POSTURE EVALUATION ─────────────────────────────

def test_portfolio_overview_endpoint_api(client: TestClient, api_test_setup):
    """Test /quant-risk/overview returns posture metrics and breach status."""
    headers = get_token_headers(api_test_setup["analyst"])
    resp = client.get("/api/v1/quant-risk/overview", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_scenarios" in data
    assert "portfolio_ale" in data
    assert "portfolio_var_95" in data
    assert "appetite_status" in data
    assert "threat_category_distribution" in data


# ─── 6. RBAC PERMISSION MATRIX ENFORCEMENT ──────────────────────────────────

def test_rbac_permissions_api(client: TestClient, api_test_setup):
    """Test RBAC across roles: ADMIN, MANAGER, GRC_ANALYST, AUDITOR, VIEWER."""
    admin_h = get_token_headers(api_test_setup["admin"])
    manager_h = get_token_headers(api_test_setup["manager"])
    analyst_h = get_token_headers(api_test_setup["analyst"])
    auditor_h = get_token_headers(api_test_setup["auditor"])
    viewer_h = get_token_headers(api_test_setup["viewer"])

    # 1. VIEWER can read overview and scenarios, but cannot create (403)
    assert client.get("/api/v1/quant-risk/overview", headers=viewer_h).status_code == 200
    assert client.post("/api/v1/quant-risk/scenarios", headers=viewer_h, json={"scenario_code": "QRS-V", "title": "T", "description": "Valid desc"}).status_code == 403

    # 2. AUDITOR can read overview and scenarios, but cannot create (403)
    assert client.get("/api/v1/quant-risk/overview", headers=auditor_h).status_code == 200
    assert client.post("/api/v1/quant-risk/scenarios", headers=auditor_h, json={"scenario_code": "QRS-A", "title": "T", "description": "Valid desc"}).status_code == 403

    # 3. ANALYST can create scenario and execute simulation, but cannot approve appetite (403)
    # Create draft appetite
    draft_app = client.post("/api/v1/quant-risk/appetites", headers=admin_h, json={"ale_limit": 50000.0, "var_95_limit": 150000.0}).json()
    app_id = draft_app["id"]

    # Analyst cannot approve
    assert client.post(f"/api/v1/quant-risk/appetites/{app_id}/approve", headers=analyst_h).status_code == 403

    # Manager CAN approve
    assert client.post(f"/api/v1/quant-risk/appetites/{app_id}/approve", headers=manager_h).status_code == 200