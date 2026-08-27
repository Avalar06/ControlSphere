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
def adv_p12_fixture(db: Session, org_apex: Organization, org_meridian: Organization):
    """Fixture with Apex and Meridian organizations, users across roles, and foundational GRC entities."""
    # Apex users
    apex_manager = User(
        email="manager@apexfinancial.com",
        hashed_password=get_password_hash("ManagerPass123!"),
        full_name="Apex Manager",
        role=RoleEnum.MANAGER,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_analyst = User(
        email="analyst_p12@apexfinancial.com",
        hashed_password=get_password_hash("AnalystPass123!"),
        full_name="Apex Analyst",
        role=RoleEnum.GRC_ANALYST,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_viewer = User(
        email="viewer_p12@apexfinancial.com",
        hashed_password=get_password_hash("ViewerPass123!"),
        full_name="Apex Viewer",
        role=RoleEnum.VIEWER,
        is_active=True,
        organization_id=org_apex.id,
    )

    # Meridian users
    meridian_manager = User(
        email="manager@meridianhealth.com",
        hashed_password=get_password_hash("MeridianPass123!"),
        full_name="Meridian Manager",
        role=RoleEnum.MANAGER,
        is_active=True,
        organization_id=org_meridian.id,
    )
    meridian_analyst = User(
        email="analyst@meridianhealth.com",
        hashed_password=get_password_hash("MeridianPass123!"),
        full_name="Meridian Analyst",
        role=RoleEnum.GRC_ANALYST,
        is_active=True,
        organization_id=org_meridian.id,
    )

    db.add_all([apex_manager, apex_analyst, apex_viewer, meridian_manager, meridian_analyst])
    db.commit()

    # Framework and Controls
    fw = Framework(name="NIST CSF 2.0", identifier="NIST-CSF", version="2.0")
    db.add(fw)
    db.commit()

    fn = FrameworkFunction(framework_id=fw.id, identifier="PR", name="Protect")
    db.add(fn)
    db.commit()

    cat = FrameworkCategory(function_id=fn.id, identifier="PR.AC", name="Identity Management")
    db.add(cat)
    db.commit()

    subcat = FrameworkSubcategory(category_id=cat.id, identifier="PR.AC-01", title="Identities managed", description="Desc")
    db.add(subcat)
    db.commit()

    apex_ctrl = OrganizationControl(
        organization_id=org_apex.id,
        subcategory_id=subcat.id,
        status=ImplementationStatusEnum.IMPLEMENTED,
        priority=PriorityEnum.HIGH,
    )
    meridian_ctrl = OrganizationControl(
        organization_id=org_meridian.id,
        subcategory_id=subcat.id,
        status=ImplementationStatusEnum.IMPLEMENTED,
        priority=PriorityEnum.HIGH,
    )
    db.add_all([apex_ctrl, meridian_ctrl])
    db.commit()

    # Phase 5 Risks
    apex_risk = Risk(
        organization_id=org_apex.id,
        title="Apex Ransomware",
        description="Ransomware threat",
        risk_category=RiskCategoryEnum.CYBERSECURITY,
        risk_source=RiskSourceEnum.THREAT_INTELLIGENCE,
    )
    meridian_risk = Risk(
        organization_id=org_meridian.id,
        title="Meridian Ransomware",
        description="Ransomware threat",
        risk_category=RiskCategoryEnum.CYBERSECURITY,
        risk_source=RiskSourceEnum.THREAT_INTELLIGENCE,
    )
    db.add_all([apex_risk, meridian_risk])
    db.commit()

    # Phase 9 Vendors
    apex_vendor = Vendor(
        organization_id=org_apex.id,
        vendor_code="VND-APX-01",
        legal_name="Apex Cloud Provider",
        calculated_tier=VendorTierEnum.TIER_1_CRITICAL,
        vendor_status=VendorStatusEnum.ACTIVE,
    )
    meridian_vendor = Vendor(
        organization_id=org_meridian.id,
        vendor_code="VND-MER-01",
        legal_name="Meridian Cloud Provider",
        calculated_tier=VendorTierEnum.TIER_1_CRITICAL,
        vendor_status=VendorStatusEnum.ACTIVE,
    )
    db.add_all([apex_vendor, meridian_vendor])
    db.commit()

    # Phase 4 Findings
    apex_finding = Finding(
        organization_id=org_apex.id,
        organization_control_id=apex_ctrl.id,
        title="Apex Finding",
        description="Desc",
        recommendation="Fix",
        severity=FindingSeverityEnum.HIGH,
        status=FindingStatusEnum.OPEN,
    )
    meridian_finding = Finding(
        organization_id=org_meridian.id,
        organization_control_id=meridian_ctrl.id,
        title="Meridian Finding",
        description="Desc",
        recommendation="Fix",
        severity=FindingSeverityEnum.HIGH,
        status=FindingStatusEnum.OPEN,
    )
    db.add_all([apex_finding, meridian_finding])
    db.commit()

    # Phase 11 Remediation Plans
    apex_plan = RemediationPlan(
        organization_id=org_apex.id,
        plan_code="CAPA-APX-01",
        title="Apex CAPA",
        problem_statement="Problem",
        root_cause_classification=RemediationRootCauseClassificationEnum.CONTROL_DEFICIENCY,
        source_type=RemediationSourceTypeEnum.FINDING,
        finding_id=apex_finding.id,
        severity=RemediationSeverityEnum.HIGH,
        status=RemediationStatusEnum.APPROVED,
        plan_owner_id=apex_analyst.id,
        approved_by_id=apex_manager.id,
        rei_score=50.0,
    )
    meridian_plan = RemediationPlan(
        organization_id=org_meridian.id,
        plan_code="CAPA-MER-01",
        title="Meridian CAPA",
        problem_statement="Problem",
        root_cause_classification=RemediationRootCauseClassificationEnum.CONTROL_DEFICIENCY,
        source_type=RemediationSourceTypeEnum.FINDING,
        finding_id=meridian_finding.id,
        severity=RemediationSeverityEnum.HIGH,
        status=RemediationStatusEnum.APPROVED,
        plan_owner_id=meridian_analyst.id,
        approved_by_id=meridian_manager.id,
        rei_score=50.0,
    )
    db.add_all([apex_plan, meridian_plan])
    db.commit()

    return {
        "org_apex": org_apex,
        "org_meridian": org_meridian,
        "apex_manager": apex_manager,
        "apex_analyst": apex_analyst,
        "apex_viewer": apex_viewer,
        "meridian_manager": meridian_manager,
        "meridian_analyst": meridian_analyst,
        "apex_ctrl": apex_ctrl,
        "meridian_ctrl": meridian_ctrl,
        "apex_risk": apex_risk,
        "meridian_risk": meridian_risk,
        "apex_vendor": apex_vendor,
        "meridian_vendor": meridian_vendor,
        "apex_plan": apex_plan,
        "meridian_plan": meridian_plan,
    }


# ─── ADV-P12-01: Cross-Tenant Scenario Read (IDOR) ───────────────────────────

def test_adv_p12_01_cross_tenant_scenario_read(client: TestClient, db: Session, adv_p12_fixture):
    """ADV-P12-01: Meridian analyst attempts to read Apex scenario via IDOR -> HTTP 404."""
    apex_sc = QuantitativeRiskScenario(
        organization_id=adv_p12_fixture["org_apex"].id,
        scenario_code="QRS-APEX-IDOR",
        title="Apex Scenario",
        description="Private",
        created_by_id=adv_p12_fixture["apex_analyst"].id,
    )
    db.add(apex_sc)
    db.commit()

    headers = get_token_headers(adv_p12_fixture["meridian_analyst"])
    resp = client.get(f"/api/v1/quant-risk/scenarios/{apex_sc.id}", headers=headers)
    assert resp.status_code == 404


# ─── ADV-P12-02: Cross-Tenant Scenario Mutation ──────────────────────────────

def test_adv_p12_02_cross_tenant_scenario_mutation(client: TestClient, db: Session, adv_p12_fixture):
    """ADV-P12-02: Meridian manager attempts to update Apex scenario -> HTTP 404."""
    apex_sc = QuantitativeRiskScenario(
        organization_id=adv_p12_fixture["org_apex"].id,
        scenario_code="QRS-APEX-MUT",
        title="Apex Scenario",
        description="Private",
        created_by_id=adv_p12_fixture["apex_analyst"].id,
    )
    db.add(apex_sc)
    db.commit()

    headers = get_token_headers(adv_p12_fixture["meridian_manager"])
    resp = client.put(
        f"/api/v1/quant-risk/scenarios/{apex_sc.id}",
        headers=headers,
        json={"title": "Hacked Title"},
    )
    assert resp.status_code == 404


# ─── ADV-P12-03: Foreign Phase 5 Risk ID Injection ───────────────────────────

def test_adv_p12_03_foreign_risk_id_injection(client: TestClient, adv_p12_fixture):
    """ADV-P12-03: Apex analyst attempts to link Meridian risk ID to Apex scenario -> HTTP 404."""
    headers = get_token_headers(adv_p12_fixture["apex_analyst"])
    resp = client.post(
        "/api/v1/quant-risk/scenarios",
        headers=headers,
        json={
            "scenario_code": "QRS-APEX-RISK-INJ",
            "title": "Cross Risk Injection",
            "description": "Valid scenario description",
            "risk_id": adv_p12_fixture["meridian_risk"].id,
        },
    )
    assert resp.status_code == 404


# ─── ADV-P12-04: Foreign Phase 2 Control ID Injection ────────────────────────

def test_adv_p12_04_foreign_control_id_injection(client: TestClient, adv_p12_fixture):
    """ADV-P12-04: Apex analyst attempts to link Meridian control ID -> HTTP 404."""
    headers = get_token_headers(adv_p12_fixture["apex_analyst"])
    resp = client.post(
        "/api/v1/quant-risk/scenarios",
        headers=headers,
        json={
            "scenario_code": "QRS-APEX-CTRL-INJ",
            "title": "Cross Control Injection",
            "description": "Valid scenario description",
            "organization_control_id": adv_p12_fixture["meridian_ctrl"].id,
        },
    )
    assert resp.status_code == 404


# ─── ADV-P12-05: Foreign Phase 9 Vendor ID Injection ─────────────────────────

def test_adv_p12_05_foreign_vendor_id_injection(client: TestClient, adv_p12_fixture):
    """ADV-P12-05: Apex analyst attempts to link Meridian vendor ID -> HTTP 404."""
    headers = get_token_headers(adv_p12_fixture["apex_analyst"])
    resp = client.post(
        "/api/v1/quant-risk/scenarios",
        headers=headers,
        json={
            "scenario_code": "QRS-APEX-VND-INJ",
            "title": "Cross Vendor Injection",
            "description": "Valid scenario description",
            "vendor_id": adv_p12_fixture["meridian_vendor"].id,
        },
    )
    assert resp.status_code == 404


# ─── ADV-P12-06: Foreign Phase 11 Plan ID in ROSI ────────────────────────────

def test_adv_p12_06_foreign_plan_id_in_rosi(client: TestClient, db: Session, adv_p12_fixture):
    """ADV-P12-06: Apex analyst attempts to compute ROSI against Meridian Remediation Plan -> HTTP 404."""
    apex_sc = QuantitativeRiskScenario(
        organization_id=adv_p12_fixture["org_apex"].id,
        scenario_code="QRS-APEX-ROSI-SC",
        title="Apex Scenario",
        description="Desc",
        created_by_id=adv_p12_fixture["apex_analyst"].id,
        annualized_loss_expectancy=100000.0,
        single_loss_expectancy=50000.0,
        control_strength=0.5,
    )
    db.add(apex_sc)
    db.commit()

    headers = get_token_headers(adv_p12_fixture["apex_analyst"])
    resp = client.post(
        f"/api/v1/quant-risk/scenarios/{apex_sc.id}/rosi",
        headers=headers,
        json={
            "remediation_plan_id": adv_p12_fixture["meridian_plan"].id,
            "remediation_cost": 25000.0,
        },
    )
    assert resp.status_code == 404


# ─── ADV-P12-07: Organization ID Spoofing in Payload ─────────────────────────

def test_adv_p12_07_organization_id_spoofing(client: TestClient, db: Session, adv_p12_fixture):
    """ADV-P12-07: Client supplies foreign organization_id in payload; server enforces JWT tenant."""
    headers = get_token_headers(adv_p12_fixture["apex_analyst"])
    resp = client.post(
        "/api/v1/quant-risk/scenarios",
        headers=headers,
        json={
            "scenario_code": "QRS-APEX-SPOOF",
            "title": "Spoof Attempt",
            "description": "Valid scenario description",
            "organization_id": adv_p12_fixture["org_meridian"].id,
        },
    )
    assert resp.status_code == 201
    created_id = resp.json()["id"]
    db_sc = db.query(QuantitativeRiskScenario).filter(QuantitativeRiskScenario.id == created_id).first()
    assert db_sc.organization_id == adv_p12_fixture["org_apex"].id


# ─── ADV-P12-08: Client Injection of Financial Metrics ───────────────────────

def test_adv_p12_08_client_injection_financial_metrics(client: TestClient, db: Session, adv_p12_fixture):
    """ADV-P12-08: Client passes forged ALE/SLE/LEF in payload; server computes authority values."""
    headers = get_token_headers(adv_p12_fixture["apex_analyst"])
    resp = client.post(
        "/api/v1/quant-risk/scenarios",
        headers=headers,
        json={
            "scenario_code": "QRS-APEX-METRIC-INJ",
            "title": "Metric Injection",
            "description": "Valid scenario description",
            "annualized_loss_expectancy": 99999999.0,
            "single_loss_expectancy": 88888888.0,
            "loss_event_frequency": 77777777.0,
            "tef_min": 1.0,
            "tef_mode": 1.0,
            "tef_max": 1.0,
            "tcap": 0.5,
            "pl_min": 1000.0,
            "pl_mode": 1000.0,
            "pl_max": 1000.0,
            "slop": 0.0,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    # Server calculates authoritative ALE: LEF(0.25) * SLE(1000) = 250.0
    assert data["annualized_loss_expectancy"] != 99999999.0
    assert data["annualized_loss_expectancy"] == 250.0


# ─── ADV-P12-09: Client Control Strength Injection ───────────────────────────

def test_adv_p12_09_client_control_strength_injection(client: TestClient, adv_p12_fixture):
    """ADV-P12-09: Client passes forged control_strength; server calculates from control & findings."""
    headers = get_token_headers(adv_p12_fixture["apex_analyst"])
    resp = client.post(
        "/api/v1/quant-risk/scenarios",
        headers=headers,
        json={
            "scenario_code": "QRS-APEX-CS-INJ",
            "title": "CS Injection",
            "description": "Valid scenario description",
            "control_strength": 0.99,
            "organization_control_id": adv_p12_fixture["apex_ctrl"].id,
        },
    )
    assert resp.status_code == 201
    # Base control strength without CCM is 0.70; with 1 HIGH finding (-0.15) -> 0.70 * 0.85 = 0.595
    assert resp.json()["control_strength"] != 0.99


# ─── ADV-P12-10: Inverted Loss Ranges (a > m or m > b) ───────────────────────

def test_adv_p12_10_inverted_pert_loss_ranges(client: TestClient, adv_p12_fixture):
    """ADV-P12-10: Inverted PERT boundaries fail validation with HTTP 422."""
    headers = get_token_headers(adv_p12_fixture["apex_analyst"])

    # min > mode
    resp1 = client.post(
        "/api/v1/quant-risk/scenarios",
        headers=headers,
        json={"scenario_code": "QRS-INV-1", "title": "T", "description": "D", "pl_min": 5000.0, "pl_mode": 2000.0, "pl_max": 10000.0},
    )
    assert resp1.status_code == 422

    # mode > max
    resp2 = client.post(
        "/api/v1/quant-risk/scenarios",
        headers=headers,
        json={"scenario_code": "QRS-INV-2", "title": "T", "description": "D", "tef_min": 1.0, "tef_mode": 10.0, "tef_max": 5.0},
    )
    assert resp2.status_code == 422


# ─── ADV-P12-11: Negative Frequency or Loss Amounts ──────────────────────────

def test_adv_p12_11_negative_frequency_or_loss_amounts(client: TestClient, adv_p12_fixture):
    """ADV-P12-11: Negative financial loss or frequency values rejected with HTTP 422."""
    headers = get_token_headers(adv_p12_fixture["apex_analyst"])
    resp = client.post(
        "/api/v1/quant-risk/scenarios",
        headers=headers,
        json={"scenario_code": "QRS-NEG-1", "title": "T", "description": "D", "pl_min": -1000.0},
    )
    assert resp.status_code == 422


# ─── ADV-P12-12: Risk Appetite Self-Approval Violation ───────────────────────

def test_adv_p12_12_appetite_self_approval_violation(client: TestClient, adv_p12_fixture):
    """ADV-P12-12: Requester manager attempting to approve their own appetite fails with HTTP 403."""
    headers = get_token_headers(adv_p12_fixture["apex_manager"])
    # 1. Create appetite as manager
    create_resp = client.post(
        "/api/v1/quant-risk/appetites",
        headers=headers,
        json={"ale_limit": 50000.0, "var_95_limit": 150000.0},
    )
    assert create_resp.status_code == 201
    appetite_id = create_resp.json()["id"]

    # 2. Self-approval attempt
    approve_resp = client.post(
        f"/api/v1/quant-risk/appetites/{appetite_id}/approve",
        headers=headers,
    )
    assert approve_resp.status_code == 403


# ─── ADV-P12-13: Direct Mutation of Historical Simulation ───────────────────

def test_adv_p12_13_historical_simulation_mutation_protection(client: TestClient, db: Session, adv_p12_fixture):
    """ADV-P12-13: Historical simulation runs cannot be mutated (PUT/PATCH return 405 Method Not Allowed)."""
    apex_sc = QuantitativeRiskScenario(
        organization_id=adv_p12_fixture["org_apex"].id,
        scenario_code="QRS-APEX-SIM-MUT",
        title="Apex Scenario",
        description="Desc",
        created_by_id=adv_p12_fixture["apex_analyst"].id,
    )
    db.add(apex_sc)
    db.commit()

    sim_run = QuantitativeSimulationRun(
        organization_id=adv_p12_fixture["org_apex"].id,
        scenario_id=apex_sc.id,
        trial_count=1000,
        simulation_seed=42,
        algorithm_version="SIM_PERT_V1",
        mean_loss=5000.0,
        variance_loss=10000.0,
        std_dev_loss=100.0,
        percentile_10=1000.0,
        percentile_50=4000.0,
        percentile_90=8000.0,
        percentile_95=9500.0,
        percentile_99=12000.0,
        simulated_by_id=adv_p12_fixture["apex_analyst"].id,
    )
    db.add(sim_run)
    db.commit()

    headers = get_token_headers(adv_p12_fixture["apex_manager"])
    put_resp = client.put(f"/api/v1/quant-risk/simulations/{sim_run.id}", headers=headers, json={"mean_loss": 0.0})
    assert put_resp.status_code == 405

    patch_resp = client.patch(f"/api/v1/quant-risk/simulations/{sim_run.id}", headers=headers, json={"mean_loss": 0.0})
    assert patch_resp.status_code == 405


# ─── ADV-P12-14: Unauthorized Simulation Execution (Viewer) ──────────────────

def test_adv_p12_14_unauthorized_simulation_execution_viewer(client: TestClient, db: Session, adv_p12_fixture):
    """ADV-P12-14: Viewer role attempting to execute simulation fails with HTTP 403."""
    apex_sc = QuantitativeRiskScenario(
        organization_id=adv_p12_fixture["org_apex"].id,
        scenario_code="QRS-APEX-VIEWER-EXEC",
        title="Apex Scenario",
        description="Desc",
        created_by_id=adv_p12_fixture["apex_analyst"].id,
    )
    db.add(apex_sc)
    db.commit()

    headers = get_token_headers(adv_p12_fixture["apex_viewer"])
    resp = client.post(
        f"/api/v1/quant-risk/scenarios/{apex_sc.id}/simulate",
        headers=headers,
        json={"trial_count": 500},
    )
    assert resp.status_code == 403


# ─── ADV-P12-15: Zero or Negative Remediation Cost in ROSI ───────────────────

def test_adv_p12_15_zero_or_negative_remediation_cost(client: TestClient, db: Session, adv_p12_fixture):
    """ADV-P12-15: Zero or negative remediation cost in ROSI fails with HTTP 422."""
    apex_sc = QuantitativeRiskScenario(
        organization_id=adv_p12_fixture["org_apex"].id,
        scenario_code="QRS-APEX-ROSI-ZERO",
        title="Apex Scenario",
        description="Desc",
        created_by_id=adv_p12_fixture["apex_analyst"].id,
    )
    db.add(apex_sc)
    db.commit()

    headers = get_token_headers(adv_p12_fixture["apex_analyst"])
    resp_zero = client.post(
        f"/api/v1/quant-risk/scenarios/{apex_sc.id}/rosi",
        headers=headers,
        json={"remediation_plan_id": adv_p12_fixture["apex_plan"].id, "remediation_cost": 0.0},
    )
    assert resp_zero.status_code == 422

    resp_neg = client.post(
        f"/api/v1/quant-risk/scenarios/{apex_sc.id}/rosi",
        headers=headers,
        json={"remediation_plan_id": adv_p12_fixture["apex_plan"].id, "remediation_cost": -500.0},
    )
    assert resp_neg.status_code == 422


# ─── ADV-P12-16: Stale CCM Telemetry Exploitation ────────────────────────────

def test_adv_p12_16_stale_ccm_telemetry_handling(client: TestClient, db: Session, adv_p12_fixture):
    """ADV-P12-16: Stale Phase 7 CCM telemetry (>30 days) is detected, flagged, and safely processed."""
    # Add snapshot 40 days old
    stale_snap = ControlHealthSnapshot(
        organization_id=adv_p12_fixture["org_apex"].id,
        organization_control_id=adv_p12_fixture["apex_ctrl"].id,
        health_score=90.0,
        health_status=ControlHealthStatusEnum.HEALTHY,
        evaluated_at=datetime.now(timezone.utc) - timedelta(days=40),
    )
    db.add(stale_snap)
    db.commit()

    headers = get_token_headers(adv_p12_fixture["apex_analyst"])
    resp = client.post(
        "/api/v1/quant-risk/scenarios",
        headers=headers,
        json={
            "scenario_code": "QRS-APEX-STALE-CCM",
            "title": "Stale Scenario",
            "description": "Valid scenario description",
            "organization_control_id": adv_p12_fixture["apex_ctrl"].id,
        },
    )
    assert resp.status_code == 201
    assert resp.json()["is_ccm_stale"] is True


# ─── ADV-P12-17: Cross-Tenant Appetite Modification ──────────────────────────

def test_adv_p12_17_cross_tenant_appetite_modification(client: TestClient, db: Session, adv_p12_fixture):
    """ADV-P12-17: Meridian manager attempts to approve Apex financial risk appetite -> HTTP 404."""
    apex_appetite = FinancialRiskAppetite(
        organization_id=adv_p12_fixture["org_apex"].id,
        version=1,
        ale_limit=50000.0,
        var_95_limit=150000.0,
        status=AppetiteStatusEnum.DRAFT,
        requested_by_id=adv_p12_fixture["apex_analyst"].id,
    )
    db.add(apex_appetite)
    db.commit()

    headers = get_token_headers(adv_p12_fixture["meridian_manager"])
    resp = client.post(
        f"/api/v1/quant-risk/appetites/{apex_appetite.id}/approve",
        headers=headers,
    )
    assert resp.status_code == 404


# ─── ADV-P12-18: Non-Existent Upstream Reference ID ──────────────────────────

def test_adv_p12_18_non_existent_upstream_reference(client: TestClient, adv_p12_fixture):
    """ADV-P12-18: Non-existent control/risk/vendor returns HTTP 404."""
    headers = get_token_headers(adv_p12_fixture["apex_analyst"])
    resp = client.post(
        "/api/v1/quant-risk/scenarios",
        headers=headers,
        json={
            "scenario_code": "QRS-NON-EXIST",
            "title": "Non-existent",
            "description": "Valid scenario description",
            "organization_control_id": 999999,
        },
    )
    assert resp.status_code == 404


# ─── ADV-P12-19: Mutation of Frozen Baseline Scenario ────────────────────────

def test_adv_p12_19_mutation_of_frozen_scenario(client: TestClient, db: Session, adv_p12_fixture):
    """ADV-P12-19: Updating a frozen scenario baseline fails with HTTP 409 Conflict."""
    apex_sc = QuantitativeRiskScenario(
        organization_id=adv_p12_fixture["org_apex"].id,
        scenario_code="QRS-FROZEN-TEST",
        title="Frozen Scenario",
        description="Desc",
        status=ScenarioStatusEnum.FROZEN,
        is_immutable=True,
        created_by_id=adv_p12_fixture["apex_analyst"].id,
    )
    db.add(apex_sc)
    db.commit()

    headers = get_token_headers(adv_p12_fixture["apex_analyst"])
    resp = client.put(
        f"/api/v1/quant-risk/scenarios/{apex_sc.id}",
        headers=headers,
        json={"title": "Attempted Edit"},
    )
    assert resp.status_code == 409


# ─── ADV-P12-20: Simulation Trial Count Exhaustion (>50k or <100) ────────────

def test_adv_p12_20_simulation_trial_bounds_exhaustion(client: TestClient, db: Session, adv_p12_fixture):
    """ADV-P12-20: Trial counts outside [100, 50,000] fail schema validation with HTTP 422."""
    apex_sc = QuantitativeRiskScenario(
        organization_id=adv_p12_fixture["org_apex"].id,
        scenario_code="QRS-SIM-BOUNDS",
        title="Scenario",
        description="Desc",
        created_by_id=adv_p12_fixture["apex_analyst"].id,
    )
    db.add(apex_sc)
    db.commit()

    headers = get_token_headers(adv_p12_fixture["apex_analyst"])

    # Trial count > 50,000 (Resource exhaustion vector)
    resp_high = client.post(
        f"/api/v1/quant-risk/scenarios/{apex_sc.id}/simulate",
        headers=headers,
        json={"trial_count": 100000},
    )
    assert resp_high.status_code == 422

    # Trial count < 100
    resp_low = client.post(
        f"/api/v1/quant-risk/scenarios/{apex_sc.id}/simulate",
        headers=headers,
        json={"trial_count": 10},
    )
    assert resp_low.status_code == 422