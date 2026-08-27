import pytest
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException

from app.models.control import OrganizationControl, ImplementationStatusEnum, PriorityEnum
from app.models.finding import Finding, FindingSeverityEnum, FindingStatusEnum
from app.models.framework import Framework, FrameworkFunction, FrameworkCategory, FrameworkSubcategory
from app.models.incident import SecurityIncident, IncidentSeverityEnum, IncidentCategoryEnum, IncidentStatusEnum
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
    RemediationStatusEnum,
    RemediationSourceTypeEnum,
    RemediationRootCauseClassificationEnum,
    RemediationSeverityEnum,
)
from app.models.risk import Risk, RiskCategoryEnum, RiskSourceEnum
from app.models.tprm import Vendor, VendorStatusEnum, VendorTierEnum
from app.models.user import User
from app.schemas.quant_risk import (
    FinancialRiskAppetiteCreate,
    QuantitativeRiskScenarioCreate,
    QuantitativeRiskScenarioUpdate,
    QuantitativeSimulationRequest,
    RosiAnalysisCreate,
)
from app.services.quantum_grc_service import (
    QuantumGrcService,
    calculate_pert_mean,
    calculate_pert_variance,
    calculate_finding_penalty,
    calculate_control_strength,
    calculate_vulnerability_factor,
    calculate_lef,
    calculate_mean_loss_magnitude,
    calculate_ale,
    calculate_parametric_var,
    calculate_rosi,
    evaluate_appetite_status,
    run_monte_carlo_simulation,
)


@pytest.fixture
def test_setup(db):
    """Setup multi-tenant test fixtures for Phase 12 domain verification."""
    org1 = Organization(name="Apex Enterprise", slug="apex-quant-1")
    org2 = Organization(name="Meridian Global", slug="meridian-quant-2")
    db.add_all([org1, org2])
    db.commit()

    user1 = User(
        organization_id=org1.id,
        email="analyst1@apex.com",
        hashed_password="hash",
        full_name="Apex Risk Analyst",
        role="GRC_ANALYST",
        is_active=True,
    )
    user2 = User(
        organization_id=org1.id,
        email="manager1@apex.com",
        hashed_password="hash",
        full_name="Apex Risk Manager",
        role="MANAGER",
        is_active=True,
    )
    user_foreign = User(
        organization_id=org2.id,
        email="analyst2@meridian.com",
        hashed_password="hash",
        full_name="Meridian Analyst",
        role="GRC_ANALYST",
        is_active=True,
    )
    db.add_all([user1, user2, user_foreign])
    db.commit()

    # Framework & Control setup for org1
    fw = Framework(identifier="NIST_CSF", name="NIST CSF 2.0", description="Security Framework")
    db.add(fw)
    db.commit()

    fn = FrameworkFunction(framework_id=fw.id, identifier="PR", name="Protect")
    db.add(fn)
    db.commit()

    cat = FrameworkCategory(function_id=fn.id, identifier="PR.AC", name="Access Control")
    db.add(cat)
    db.commit()

    subcat = FrameworkSubcategory(
        category_id=cat.id,
        identifier="PR.AC-01",
        title="Identities and credentials are managed",
        description="Identities are verified",
    )
    db.add(subcat)
    db.commit()

    ctrl = OrganizationControl(
        organization_id=org1.id,
        subcategory_id=subcat.id,
        status=ImplementationStatusEnum.IMPLEMENTED,
        priority=PriorityEnum.HIGH,
    )
    db.add(ctrl)
    db.commit()

    return {
        "org1": org1,
        "org2": org2,
        "user1": user1,
        "user2": user2,
        "user_foreign": user_foreign,
        "control1": ctrl,
    }


# ─── 1. BETA-PERT MATHEMATICS (REQS 1-4, 13) ────────────────────────────────

def test_beta_pert_mean_and_variance():
    """Req 1 & 2: Verify μ = (a + 4m + b)/6 and σ² = (b - a)²/36."""
    mean = calculate_pert_mean(10.0, 20.0, 70.0)
    assert abs(mean - 26.666666666666668) < 1e-6

    var = calculate_pert_variance(10.0, 20.0, 70.0)
    assert var == 100.0


def test_deterministic_beta_pert_collapse():
    """Req 3: When a = m = b, PERT distribution collapses to deterministic constant."""
    mean = calculate_pert_mean(50.0, 50.0, 50.0)
    var = calculate_pert_variance(50.0, 50.0, 50.0)
    assert mean == 50.0
    assert var == 0.0


def test_invalid_pert_bounds_rejection():
    """Req 4: Enforce 0 <= a <= m <= b."""
    with pytest.raises(ValueError):
        calculate_pert_mean(30.0, 20.0, 50.0)  # a > m
    with pytest.raises(ValueError):
        calculate_pert_mean(10.0, 60.0, 50.0)  # m > b
    with pytest.raises(ValueError):
        calculate_pert_mean(-5.0, 10.0, 20.0)  # a < 0


# ─── 2. CCM, FINDINGS & CONTROL STRENGTH (REQS 5-9) ─────────────────────────

def test_ccm_to_cs_base_conversion():
    """Req 5: CS_base = CCMHealth / 100."""
    cs_100 = calculate_control_strength(100.0, [])
    assert cs_100 == 1.0

    cs_75 = calculate_control_strength(75.0, [])
    assert cs_75 == 0.75

    cs_0 = calculate_control_strength(0.0, [])
    assert cs_0 == 0.0


def test_individual_finding_penalties():
    """Req 6: Verify CRITICAL=0.25, HIGH=0.15, MEDIUM=0.08, LOW=0.03, INFORMATIONAL=0.00."""
    crit = Finding(organization_id=1, organization_control_id=1, title="Crit", description="D", severity=FindingSeverityEnum.CRITICAL, status=FindingStatusEnum.OPEN)
    high = Finding(organization_id=1, organization_control_id=1, title="High", description="D", severity=FindingSeverityEnum.HIGH, status=FindingStatusEnum.OPEN)
    med = Finding(organization_id=1, organization_control_id=1, title="Med", description="D", severity=FindingSeverityEnum.MEDIUM, status=FindingStatusEnum.OPEN)
    low = Finding(organization_id=1, organization_control_id=1, title="Low", description="D", severity=FindingSeverityEnum.LOW, status=FindingStatusEnum.OPEN)
    info = Finding(organization_id=1, organization_control_id=1, title="Info", description="D", severity=FindingSeverityEnum.INFORMATIONAL, status=FindingStatusEnum.OPEN)

    assert calculate_finding_penalty([crit]) == 0.25
    assert calculate_finding_penalty([high]) == 0.15
    assert calculate_finding_penalty([med]) == 0.08
    assert calculate_finding_penalty([low]) == 0.03
    assert calculate_finding_penalty([info]) == 0.00


def test_active_finding_status_filtering():
    """Req 7: Only active findings (OPEN, IN_REMEDIATION, PENDING_VALIDATION) apply penalties."""
    f_open = Finding(organization_id=1, organization_control_id=1, title="F1", description="D", severity=FindingSeverityEnum.CRITICAL, status=FindingStatusEnum.OPEN)
    f_in_rem = Finding(organization_id=1, organization_control_id=1, title="F2", description="D", severity=FindingSeverityEnum.HIGH, status=FindingStatusEnum.IN_REMEDIATION)
    f_pending = Finding(organization_id=1, organization_control_id=1, title="F3", description="D", severity=FindingSeverityEnum.MEDIUM, status=FindingStatusEnum.PENDING_VALIDATION)
    f_resolved = Finding(organization_id=1, organization_control_id=1, title="F4", description="D", severity=FindingSeverityEnum.CRITICAL, status=FindingStatusEnum.RESOLVED)
    f_accepted = Finding(organization_id=1, organization_control_id=1, title="F5", description="D", severity=FindingSeverityEnum.CRITICAL, status=FindingStatusEnum.ACCEPTED_RISK)
    f_closed = Finding(organization_id=1, organization_control_id=1, title="F6", description="D", severity=FindingSeverityEnum.CRITICAL, status=FindingStatusEnum.CLOSED)

    # 0.25 + 0.15 + 0.08 = 0.48 (resolved, accepted, closed contribute 0.00)
    penalty = calculate_finding_penalty([f_open, f_in_rem, f_pending, f_resolved, f_accepted, f_closed])
    assert abs(penalty - 0.48) < 1e-6


def test_penalty_cap_at_1_and_cs_clamping():
    """Req 8 & 9: Penalty total is capped at 1.0 and CS clamped to [0.0, 1.0]."""
    f_list = [
        Finding(organization_id=1, organization_control_id=1, title=f"C{i}", description="D", severity=FindingSeverityEnum.CRITICAL, status=FindingStatusEnum.OPEN)
        for i in range(10)
    ]
    assert calculate_finding_penalty(f_list) == 1.0
    assert calculate_control_strength(100.0, f_list) == 0.0
    assert calculate_control_strength(50.0, []) == 0.5


# ─── 3. VULN, LEF, SLE, ALE (REQS 10-16) ────────────────────────────────────

def test_vulnerability_and_lef_calculations():
    """Req 10, 11, 12: VULN = TCAP*(1 - CS) and LEF = μ(TEF) * VULN."""
    # TCAP = 0.8, CS = 0.5 -> VULN = 0.4
    vuln = calculate_vulnerability_factor(0.8, 0.5)
    assert abs(vuln - 0.4) < 1e-6

    # TEF_mean = 5.0, VULN = 0.4 -> LEF = 2.0 events/year
    lef = calculate_lef(5.0, vuln)
    assert abs(lef - 2.0) < 1e-6

    # Zero LEF allowed
    assert calculate_lef(0.0, 0.8) == 0.0
    assert calculate_lef(5.0, 0.0) == 0.0


def test_loss_magnitude_and_ale():
    """Req 14, 15, 16: SLE = PL_mean + SL_mean * SLoP, and ALE = LEF * SLE."""
    # PL_mean = 100k, SL_mean = 50k, SLoP = 0.4 -> SLE = 120k
    sle = calculate_mean_loss_magnitude(100000.0, 50000.0, 0.4)
    assert sle == 120000.0

    # LEF = 0.5 events/yr, SLE = 120k USD/event -> ALE = 60k USD/yr
    ale = calculate_ale(0.5, sle)
    assert ale == 60000.0


# ─── 4. ROSI ENGINE (REQS 17-19) ────────────────────────────────────────────

def test_rosi_engine_positive_negative_and_zero_cost_rejection():
    """Req 17, 18, 19: Positive/Negative ROSI and strictly positive cost validation."""
    # Positive: ALE 100k -> 20k (ΔALE 80k), Cost 30k -> ROSI 166.67%
    rosi_pos = calculate_rosi(100000.0, 20000.0, 30000.0)
    assert rosi_pos["risk_reduction_ale"] == 80000.0
    assert rosi_pos["net_economic_benefit"] == 50000.0
    assert rosi_pos["rosi_percentage"] == 166.67

    # Negative: ALE 100k -> 80k (ΔALE 20k), Cost 50k -> ROSI -60.0%
    rosi_neg = calculate_rosi(100000.0, 80000.0, 50000.0)
    assert rosi_neg["net_economic_benefit"] == -30000.0
    assert rosi_neg["rosi_percentage"] == -60.0

    # Cost <= 0 rejected
    with pytest.raises(ValueError):
        calculate_rosi(100000.0, 50000.0, 0.0)
    with pytest.raises(ValueError):
        calculate_rosi(100000.0, 50000.0, -100.0)


# ─── 5. MONTE CARLO SIMULATION & VAR (REQS 20-25) ───────────────────────────

def test_monte_carlo_trial_bounds_and_determinism():
    """Req 20, 21, 22, 23, 24: Trial bounds [100, 50000], seed reproducibility, and empirical VaR."""
    # Lower bound clamping
    res_min = run_monte_carlo_simulation(1.0, 2.0, 3.0, 0.5, 0.5, 1000, 2000, 3000, 0, 0, 0, 0, trial_count=10, seed=1)
    assert res_min["trial_count"] == 100

    # Upper bound clamping
    res_max = run_monte_carlo_simulation(1.0, 2.0, 3.0, 0.5, 0.5, 1000, 2000, 3000, 0, 0, 0, 0, trial_count=99999, seed=1)
    assert res_max["trial_count"] == 50000

    # Exact determinism with same seed
    r1 = run_monte_carlo_simulation(1.0, 2.0, 4.0, 0.8, 0.5, 1000, 5000, 20000, 0, 1000, 5000, 0.3, trial_count=500, seed=99)
    r2 = run_monte_carlo_simulation(1.0, 2.0, 4.0, 0.8, 0.5, 1000, 5000, 20000, 0, 1000, 5000, 0.3, trial_count=500, seed=99)
    assert r1 == r2
    assert r1["percentile_95"] > 0.0
    assert r1["percentile_99"] >= r1["percentile_95"]


def test_analytical_parametric_var_comparison():
    """Req 25: Analytical lognormal VaR comparison calculation."""
    param_var_95 = calculate_parametric_var(
        ale=60000.0,
        lef=0.5,
        pl_variance=1000000.0,
        sl_variance=500000.0,
        slop=0.4,
        mlm=120000.0,
        confidence=0.95,
    )
    assert param_var_95 > 60000.0  # Tail loss exceeds expected loss


# ─── 6. MONETARY PRECISION & APPETITE (REQS 26-29) ──────────────────────────

def test_appetite_threshold_and_four_eyes_governance(db, test_setup):
    """Req 27, 28, 29: Financial appetite lifecycle, four-eyes rule (requester != approver)."""
    org_id = test_setup["org1"].id
    user1_id = test_setup["user1"].id
    user2_id = test_setup["user2"].id

    appetite = QuantumGrcService.create_risk_appetite(
        db,
        org_id,
        user1_id,
        FinancialRiskAppetiteCreate(ale_limit=50000.0, var_95_limit=150000.0, notes="2026 Policy"),
    )
    assert appetite.version == 1
    assert appetite.status == AppetiteStatusEnum.DRAFT

    # Requester self-approval fails with 403 Forbidden
    with pytest.raises(HTTPException) as exc:
        QuantumGrcService.approve_risk_appetite(db, org_id, user1_id, appetite.id)
    assert exc.value.status_code == 403

    # Independent approval succeeds
    approved = QuantumGrcService.approve_risk_appetite(db, org_id, user2_id, appetite.id)
    assert approved.status == AppetiteStatusEnum.APPROVED
    assert approved.approved_by_id == user2_id
    assert approved.approved_at is not None


# ─── 7. IMMUTABILITY, SERVER-AUTHORITY & CROSS-MODULE (REQS 30-39) ──────────

def test_full_scenario_workflow_immutability_and_stale_telemetry(db, test_setup):
    """Req 30-39: Snapshot hashing, freeze immutability, server-authoritative timestamps, and stale CCM."""
    org_id = test_setup["org1"].id
    user1_id = test_setup["user1"].id
    ctrl = test_setup["control1"]

    # 1. Create Phase 5 Risk
    risk = Risk(
        organization_id=org_id,
        title="Ransomware Risk",
        description="Operational outage risk",
        risk_category=RiskCategoryEnum.CYBERSECURITY,
        risk_source=RiskSourceEnum.THREAT_INTELLIGENCE,
    )
    # 2. Create Phase 9 Vendor
    vendor = Vendor(
        organization_id=org_id,
        vendor_code="VND-001",
        legal_name="Cloud Provider X",
        calculated_tier=VendorTierEnum.TIER_1_CRITICAL,
        vendor_status=VendorStatusEnum.ACTIVE,
    )
    # 3. Create Phase 7 CCM Snapshot (older than 30 days -> STALE)
    snapshot = ControlHealthSnapshot(
        organization_id=org_id,
        organization_control_id=ctrl.id,
        health_score=85.0,
        health_status=ControlHealthStatusEnum.HEALTHY,
        evaluated_at=datetime.now(timezone.utc) - timedelta(days=35),
    )
    db.add_all([risk, vendor, snapshot])
    db.commit()

    # 4. Create Quantitative Scenario linked to Risk, Control, Vendor
    create_dto = QuantitativeRiskScenarioCreate(
        scenario_code="QRS-2026-001",
        title="Enterprise Ransomware Financial Exposure",
        description="Comprehensive loss scenario",
        threat_actor_category=ThreatActorCategoryEnum.CYBERCRIMINAL,
        risk_id=risk.id,
        organization_control_id=ctrl.id,
        vendor_id=vendor.id,
        tef_min=0.5,
        tef_mode=1.0,
        tef_max=3.0,
        tcap=0.8,
        pl_min=10000.0,
        pl_mode=50000.0,
        pl_max=200000.0,
        sl_min=5000.0,
        sl_mode=20000.0,
        sl_max=100000.0,
        slop=0.5,
    )
    scenario = QuantumGrcService.create_scenario(db, org_id, user1_id, create_dto)
    assert scenario.id is not None
    assert scenario.is_ccm_stale is True  # Stale telemetry detected
    assert scenario.input_snapshot_hash is not None
    assert scenario.annualized_loss_expectancy > 0.0

    # 5. Phase 5 qualitative Risk remains untouched
    assert risk.title == "Ransomware Risk"
    assert risk.risk_category == RiskCategoryEnum.CYBERSECURITY

    # 6. Execute Monte Carlo Simulation
    run = QuantumGrcService.execute_simulation(
        db, org_id, user1_id, scenario.id, QuantitativeSimulationRequest(trial_count=1000, simulation_seed=42)
    )
    assert run.percentile_95 > 0.0
    assert scenario.var_95_empirical == run.percentile_95

    # 7. Create Phase 11 Remediation Plan (with Finding link) and Evaluate ROSI
    finding1 = Finding(
        organization_id=org_id,
        organization_control_id=ctrl.id,
        title="EDR Missing",
        description="EDR agent missing on endpoints",
        recommendation="Deploy EDR immediately",
        severity=FindingSeverityEnum.HIGH,
        status=FindingStatusEnum.OPEN,
    )
    db.add(finding1)
    db.commit()

    plan = RemediationPlan(
        organization_id=org_id,
        plan_code="CAPA-2026-001",
        title="Endpoint EDR Upgrade",
        problem_statement="Mitigate ransomware lateral movement",
        root_cause_classification=RemediationRootCauseClassificationEnum.CONTROL_DEFICIENCY,
        source_type=RemediationSourceTypeEnum.FINDING,
        finding_id=finding1.id,
        severity=RemediationSeverityEnum.HIGH,
        status=RemediationStatusEnum.APPROVED,
        plan_owner_id=user1_id,
        approved_by_id=test_setup["user2"].id,
        rei_score=45.0,
    )
    db.add(plan)
    db.commit()

    rosi_analysis = QuantumGrcService.calculate_and_record_rosi(
        db,
        org_id,
        user1_id,
        scenario.id,
        RosiAnalysisCreate(remediation_plan_id=plan.id, remediation_cost=15000.0),
    )
    assert rosi_analysis.id is not None
    assert rosi_analysis.current_ale == scenario.annualized_loss_expectancy
    assert rosi_analysis.projected_ale < rosi_analysis.current_ale

    # 8. Freeze scenario and verify immutability
    frozen = QuantumGrcService.freeze_scenario(db, org_id, user1_id, scenario.id)
    assert frozen.is_immutable is True
    assert frozen.status == ScenarioStatusEnum.FROZEN

    # Attempted update on frozen scenario fails with 409 Conflict
    with pytest.raises(HTTPException) as exc:
        QuantumGrcService.update_scenario(
            db, org_id, user1_id, scenario.id, QuantitativeRiskScenarioUpdate(title="Modified")
        )
    assert exc.value.status_code == 409


# ─── 8. ADVERSARIAL SECURITY FOUNDATIONS (ADV-P12) ──────────────────────────

def test_adversarial_cross_tenant_and_upstream_injection_defense(db, test_setup):
    """ADV-P12-01 to ADV-P12-06: Cross-tenant isolation on scenarios and upstream foreign references."""
    org1_id = test_setup["org1"].id
    org2_id = test_setup["org2"].id
    user1_id = test_setup["user1"].id
    user_foreign_id = test_setup["user_foreign"].id

    # Org 1 scenario
    sc1 = QuantitativeRiskScenario(
        organization_id=org1_id,
        scenario_code="QRS-APEX-01",
        title="Apex Scenario",
        description="Apex description",
        created_by_id=user1_id,
    )
    db.add(sc1)

    # Org 2 foreign Risk, Control, Vendor, Plan
    foreign_risk = Risk(organization_id=org2_id, title="Foreign Risk", description="D", risk_category=RiskCategoryEnum.CYBERSECURITY, risk_source=RiskSourceEnum.THREAT_INTELLIGENCE)
    foreign_finding = Finding(organization_id=org2_id, organization_control_id=1, title="Foreign Gap", description="Foreign Finding Description", recommendation="Deploy patch", severity=FindingSeverityEnum.MEDIUM, status=FindingStatusEnum.OPEN)
    db.add_all([foreign_risk, foreign_finding])
    db.commit()

    foreign_vendor = Vendor(
        organization_id=org2_id,
        vendor_code="VND-FOR-01",
        legal_name="Foreign Vendor",
        calculated_tier=VendorTierEnum.TIER_2_SIGNIFICANT,
        vendor_status=VendorStatusEnum.ACTIVE,
    )
    foreign_plan = RemediationPlan(
        organization_id=org2_id,
        plan_code="CAPA-M-01",
        title="Foreign Plan",
        problem_statement="Foreign Problem",
        root_cause_classification=RemediationRootCauseClassificationEnum.HUMAN_ERROR,
        source_type=RemediationSourceTypeEnum.FINDING,
        finding_id=foreign_finding.id,
        severity=RemediationSeverityEnum.MEDIUM,
        status=RemediationStatusEnum.APPROVED,
        plan_owner_id=user_foreign_id,
        approved_by_id=user_foreign_id,
    )
    db.add_all([foreign_vendor, foreign_plan])
    db.commit()

    # ADV-P12-01: Cross-tenant scenario read returns 404
    with pytest.raises(HTTPException) as exc:
        QuantumGrcService.get_scenario(db, org2_id, sc1.id)
    assert exc.value.status_code == 404

    # ADV-P12-03: Foreign Risk linkage returns 404
    with pytest.raises(HTTPException) as exc:
        QuantumGrcService.create_scenario(
            db,
            org1_id,
            user1_id,
            QuantitativeRiskScenarioCreate(
                scenario_code="QRS-ADV-01",
                title="Scenario",
                description="Valid description",
                risk_id=foreign_risk.id,
            ),
        )
    assert exc.value.status_code == 404

    # ADV-P12-05: Foreign Vendor linkage returns 404
    with pytest.raises(HTTPException) as exc:
        QuantumGrcService.create_scenario(
            db,
            org1_id,
            user1_id,
            QuantitativeRiskScenarioCreate(
                scenario_code="QRS-ADV-02",
                title="Scenario",
                description="Valid description",
                vendor_id=foreign_vendor.id,
            ),
        )
    assert exc.value.status_code == 404

    # ADV-P12-06: Foreign Remediation Plan in ROSI returns 404
    with pytest.raises(HTTPException) as exc:
        QuantumGrcService.calculate_and_record_rosi(
            db,
            org1_id,
            user1_id,
            sc1.id,
            RosiAnalysisCreate(remediation_plan_id=foreign_plan.id, remediation_cost=10000.0),
        )
    assert exc.value.status_code == 404
