from datetime import datetime, timezone, timedelta
import hashlib
import json
import math
import random
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.models.control import OrganizationControl
from app.models.finding import Finding, FindingSeverityEnum, FindingStatusEnum
from app.models.monitoring import ControlHealthSnapshot
from app.models.quant_risk import (
    AppetiteBreachStateEnum,
    AppetiteStatusEnum,
    FinancialRiskAppetite,
    QuantitativeRiskScenario,
    QuantitativeSimulationRun,
    RosiAnalysis,
    ScenarioStatusEnum,
)
from app.models.remediation import RemediationPlan
from app.models.risk import Risk
from app.models.tprm import Vendor
from app.models.user import User
from app.schemas.quant_risk import (
    FinancialRiskAppetiteCreate,
    QuantitativeRiskScenarioCreate,
    QuantitativeRiskScenarioUpdate,
    QuantitativeSimulationRequest,
    RosiAnalysisCreate,
)
from app.services.audit_service import AuditService

# Version Constants
CALCULATION_VERSION = "2026.12.1"
ALGORITHM_VERSION = "SIM_PERT_V1"
RULE_VERSION = "PENALTY_RULE_2026_1"


# ─────────────────────────────────────────────────────────────────────────────
# PURE DETERMINISTIC MATHEMATICAL FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def calculate_pert_mean(min_val: float, mode_val: float, max_val: float) -> float:
    """Calculate Beta-PERT expected value: μ = (min + 4*mode + max) / 6."""
    if not (0.0 <= min_val <= mode_val <= max_val):
        raise ValueError(f"Invalid PERT parameters: {min_val} <= {mode_val} <= {max_val} violated.")
    return (min_val + 4.0 * mode_val + max_val) / 6.0


def calculate_pert_variance(min_val: float, mode_val: float, max_val: float) -> float:
    """Calculate Beta-PERT variance: σ² = (max - min)² / 36."""
    if not (0.0 <= min_val <= mode_val <= max_val):
        raise ValueError(f"Invalid PERT parameters: {min_val} <= {mode_val} <= {max_val} violated.")
    return ((max_val - min_val) ** 2) / 36.0


def calculate_finding_penalty(findings: List[Finding]) -> float:
    """
    Calculate severity-weighted active finding deductions.
    Rule: PENALTY_RULE_2026_1.
    Active Statuses: OPEN, IN_REMEDIATION, PENDING_VALIDATION.
    Weights: CRITICAL=0.25, HIGH=0.15, MEDIUM=0.08, LOW=0.03, INFORMATIONAL=0.00.
    Total penalty is capped at 1.0.
    """
    active_statuses = {
        FindingStatusEnum.OPEN,
        FindingStatusEnum.IN_REMEDIATION,
        FindingStatusEnum.PENDING_VALIDATION,
    }
    weights = {
        FindingSeverityEnum.CRITICAL: 0.25,
        FindingSeverityEnum.HIGH: 0.15,
        FindingSeverityEnum.MEDIUM: 0.08,
        FindingSeverityEnum.LOW: 0.03,
        FindingSeverityEnum.INFORMATIONAL: 0.00,
    }

    total_penalty = 0.0
    for f in findings:
        if f.status in active_statuses:
            total_penalty += weights.get(f.severity, 0.0)

    return min(1.0, total_penalty)


def calculate_control_strength(
    base_ccm_score: Optional[float],
    active_findings: List[Finding],
    base_status: Optional[str] = None,
) -> float:
    """
    Compute normalized Control Strength CS ∈ [0.0, 1.0].
    CS = clamp(CS_base * (1.0 - Penalty_total), 0.0, 1.0)
    """
    if base_ccm_score is not None:
        cs_base = max(0.0, min(100.0, base_ccm_score)) / 100.0
    elif base_status:
        mapping = {
            "IMPLEMENTED": 0.70,
            "PARTIALLY_IMPLEMENTED": 0.40,
            "PLANNED": 0.10,
            "NOT_APPLICABLE": 0.00,
        }
        cs_base = mapping.get(base_status.upper(), 0.50)
    else:
        cs_base = 0.50

    penalty = calculate_finding_penalty(active_findings)
    cs = cs_base * (1.0 - penalty)
    return max(0.0, min(1.0, cs))


def calculate_vulnerability_factor(tcap: float, cs: float) -> float:
    """
    Compute Vulnerability Factor VULN ∈ [0.0, 1.0].
    VULN = clamp(TCAP * (1.0 - CS), 0.0, 1.0)
    """
    clamped_tcap = max(0.0, min(1.0, tcap))
    clamped_cs = max(0.0, min(1.0, cs))
    return max(0.0, min(1.0, clamped_tcap * (1.0 - clamped_cs)))


def calculate_lef(tef_mean: float, vuln_factor: float) -> float:
    """Loss Event Frequency LEF = TEF_mean * VULN [events/year]."""
    return max(0.0, tef_mean * vuln_factor)


def calculate_mean_loss_magnitude(pl_mean: float, sl_mean: float, slop: float) -> float:
    """Single Loss Expectancy SLE = Mean Loss Magnitude = PL_mean + (SL_mean * SLoP)."""
    expected_sl = max(0.0, sl_mean) * max(0.0, min(1.0, slop))
    return max(0.0, pl_mean) + expected_sl


def calculate_ale(lef: float, sle: float) -> float:
    """Annualized Loss Expectancy ALE = LEF * SLE [USD/year]."""
    return max(0.0, lef * sle)


def calculate_parametric_var(
    ale: float,
    lef: float,
    pl_variance: float,
    sl_variance: float,
    slop: float,
    mlm: float,
    confidence: float = 0.95,
) -> float:
    """
    Analytical Lognormal Value at Risk comparison metric.
    """
    if ale <= 0.0 or lef <= 0.0:
        return 0.0

    mu_loss = ale
    var_loss = lef * (pl_variance + slop * sl_variance) + lef * (mlm**2)

    if var_loss <= 0.0 or mu_loss <= 0.0:
        return mu_loss

    sigma_sq_ln = math.log(1.0 + (var_loss / (mu_loss**2)))
    sigma_ln = math.sqrt(sigma_sq_ln)
    mu_ln = math.log(mu_loss) - 0.5 * sigma_sq_ln

    z_map = {0.90: 1.281552, 0.95: 1.644853, 0.99: 2.326348}
    z = z_map.get(confidence, 1.644853)

    return math.exp(mu_ln + z * sigma_ln)


def sample_pert(
    rng: random.Random, min_val: float, mode_val: float, max_val: float
) -> float:
    """Sample a random variate from a Beta-PERT distribution using pure stdlib."""
    if min_val == max_val:
        return min_val
    if min_val > max_val or mode_val < min_val or mode_val > max_val:
        return mode_val

    # Beta-PERT shape parameters
    range_val = max_val - min_val
    alpha = 1.0 + 4.0 * (mode_val - min_val) / range_val
    beta_param = 1.0 + 4.0 * (max_val - mode_val) / range_val

    # Pure standard library betavariate
    sample_beta = rng.betavariate(alpha, beta_param)
    return min_val + sample_beta * range_val


def sample_poisson(rng: random.Random, lam: float) -> int:
    """Sample an integer event count from a Poisson distribution."""
    if lam <= 0.0:
        return 0
    if lam > 500.0:
        # Normal approximation for large lambda
        val = rng.gauss(lam, math.sqrt(lam))
        return max(0, int(round(val)))

    # Knuth algorithm
    l_val = math.exp(-lam)
    k = 0
    p = 1.0
    while p > l_val:
        k += 1
        p *= rng.random()
    return k - 1


def run_monte_carlo_simulation(
    tef_min: float,
    tef_mode: float,
    tef_max: float,
    tcap: float,
    cs: float,
    pl_min: float,
    pl_mode: float,
    pl_max: float,
    sl_min: float,
    sl_mode: float,
    sl_max: float,
    slop: float,
    trial_count: int = 10000,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Run empirical Monte Carlo simulation for annual financial loss distributions.
    Enforces resource exhaustion constraints (100 <= trial_count <= 50,000).
    """
    clamped_trials = max(100, min(50000, trial_count))
    actual_seed = seed if seed is not None else random.randint(1, 10000000)
    rng = random.Random(actual_seed)

    vuln = calculate_vulnerability_factor(tcap, cs)
    annual_losses: List[float] = []

    for _ in range(clamped_trials):
        annual_tef = sample_pert(rng, tef_min, tef_mode, tef_max)
        effective_lambda = annual_tef * vuln
        event_count = sample_poisson(rng, effective_lambda)

        trial_loss = 0.0
        for _ in range(event_count):
            event_pl = sample_pert(rng, pl_min, pl_mode, pl_max)
            event_sl = 0.0
            if rng.random() < slop:
                event_sl = sample_pert(rng, sl_min, sl_mode, sl_max)
            trial_loss += max(0.0, event_pl + event_sl)

        annual_losses.append(trial_loss)

    annual_losses.sort()
    n = len(annual_losses)

    def get_percentile(p: float) -> float:
        if n == 0:
            return 0.0
        idx = int(math.ceil((p / 100.0) * n)) - 1
        return annual_losses[max(0, min(n - 1, idx))]

    mean_loss = sum(annual_losses) / n
    variance_loss = sum((x - mean_loss) ** 2 for x in annual_losses) / n
    std_dev_loss = math.sqrt(variance_loss)

    return {
        "trial_count": clamped_trials,
        "simulation_seed": actual_seed,
        "mean_loss": round(mean_loss, 2),
        "variance_loss": round(variance_loss, 2),
        "std_dev_loss": round(std_dev_loss, 2),
        "percentile_10": round(get_percentile(10.0), 2),
        "percentile_50": round(get_percentile(50.0), 2),
        "percentile_90": round(get_percentile(90.0), 2),
        "percentile_95": round(get_percentile(95.0), 2),
        "percentile_99": round(get_percentile(99.0), 2),
    }


def calculate_rosi(
    current_ale: float, projected_ale: float, remediation_cost: float
) -> Dict[str, float]:
    """
    Return on Security Investment Engine.
    ROSI = ((ALE_current - ALE_projected - RemediationCost) / RemediationCost) * 100%
    """
    if remediation_cost <= 0.0:
        raise ValueError("Remediation cost must be strictly positive (> 0.0).")

    risk_reduction = current_ale - projected_ale
    net_benefit = risk_reduction - remediation_cost
    rosi_pct = (net_benefit / remediation_cost) * 100.0

    return {
        "current_ale": round(current_ale, 2),
        "projected_ale": round(projected_ale, 2),
        "risk_reduction_ale": round(risk_reduction, 2),
        "net_economic_benefit": round(net_benefit, 2),
        "rosi_percentage": round(rosi_pct, 2),
    }


def evaluate_appetite_status(
    ale: float,
    var_95: float,
    ale_limit: float,
    var_95_limit: float,
) -> AppetiteBreachStateEnum:
    """Evaluate financial loss exposures against board risk appetite."""
    exceeds_ale = ale > ale_limit
    exceeds_var = var_95 > var_95_limit

    if exceeds_ale and exceeds_var:
        return AppetiteBreachStateEnum.EXCEEDS_BOTH
    elif exceeds_ale:
        return AppetiteBreachStateEnum.EXCEEDS_ALE
    elif exceeds_var:
        return AppetiteBreachStateEnum.EXCEEDS_VAR
    return AppetiteBreachStateEnum.WITHIN_APPETITE


# ─────────────────────────────────────────────────────────────────────────────
# DOMAIN SERVICE CLASS
# ─────────────────────────────────────────────────────────────────────────────

class QuantumGrcService:
    """Authoritative enterprise quantitative cyber risk & ROSI orchestration service."""

    @staticmethod
    def _get_actor_email(db: Session, actor_id: int) -> str:
        user = db.query(User).filter(User.id == actor_id).first()
        return user.email if user else "system@controlsphere.internal"

    @staticmethod
    def _compute_snapshot_hash(data_dict: Dict[str, Any]) -> str:
        serialized = json.dumps(data_dict, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def _resolve_control_telemetry(
        db: Session, org_id: int, control_id: Optional[int]
    ) -> Tuple[float, bool, List[Finding]]:
        """
        Query Phase 7 CCM telemetry and Phase 4 active findings for an OrganizationControl.
        Returns: (base_ccm_score, is_stale, active_findings)
        """
        if not control_id:
            return 50.0, False, []

        control = (
            db.query(OrganizationControl)
            .filter(
                OrganizationControl.id == control_id,
                OrganizationControl.organization_id == org_id,
            )
            .first()
        )
        if not control:
            return 50.0, False, []

        # 1. Fetch latest Phase 7 CCM health snapshot
        snapshot = (
            db.query(ControlHealthSnapshot)
            .filter(
                ControlHealthSnapshot.organization_control_id == control_id,
                ControlHealthSnapshot.organization_id == org_id,
            )
            .order_by(desc(ControlHealthSnapshot.evaluated_at))
            .first()
        )

        is_stale = False
        if snapshot:
            now = datetime.now(timezone.utc)
            snapshot_time = snapshot.evaluated_at
            if snapshot_time.tzinfo is None:
                snapshot_time = snapshot_time.replace(tzinfo=timezone.utc)
            if (now - snapshot_time) > timedelta(days=30):
                is_stale = True
            base_score = float(snapshot.health_score)
        else:
            is_stale = True
            status_val = control.status.value if control.status else "PLANNED"
            base_score = 70.0 if status_val == "IMPLEMENTED" else 40.0

        # 2. Fetch active findings
        active_statuses = [
            FindingStatusEnum.OPEN,
            FindingStatusEnum.IN_REMEDIATION,
            FindingStatusEnum.PENDING_VALIDATION,
        ]
        findings = (
            db.query(Finding)
            .filter(
                Finding.organization_control_id == control_id,
                Finding.organization_id == org_id,
                Finding.status.in_(active_statuses),
            )
            .all()
        )

        return base_score, is_stale, findings

    # ─── 1. SCENARIO MANAGEMENT ───────────────────────────────────────────────

    @classmethod
    def create_scenario(
        cls,
        db: Session,
        org_id: int,
        user_id: int,
        data: QuantitativeRiskScenarioCreate,
    ) -> QuantitativeRiskScenario:
        """Create and calculate a new Quantitative Risk Scenario."""
        # 1. Validate upstream entity tenant isolation
        if data.risk_id:
            risk = (
                db.query(Risk)
                .filter(Risk.id == data.risk_id, Risk.organization_id == org_id)
                .first()
            )
            if not risk:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Referenced Risk #{data.risk_id} not found in tenant organization.",
                )

        if data.organization_control_id:
            ctrl = (
                db.query(OrganizationControl)
                .filter(
                    OrganizationControl.id == data.organization_control_id,
                    OrganizationControl.organization_id == org_id,
                )
                .first()
            )
            if not ctrl:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Referenced Control #{data.organization_control_id} not found in tenant organization.",
                )

        if data.vendor_id:
            vendor = (
                db.query(Vendor)
                .filter(Vendor.id == data.vendor_id, Vendor.organization_id == org_id)
                .first()
            )
            if not vendor:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Referenced Vendor #{data.vendor_id} not found in tenant organization.",
                )

        # Check unique scenario code per tenant
        existing = (
            db.query(QuantitativeRiskScenario)
            .filter(
                QuantitativeRiskScenario.organization_id == org_id,
                QuantitativeRiskScenario.scenario_code == data.scenario_code,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Scenario code '{data.scenario_code}' already exists in tenant.",
            )

        # 2. Ingest CCM telemetry & findings
        base_score, is_stale, findings = cls._resolve_control_telemetry(
            db, org_id, data.organization_control_id
        )

        # 3. Perform server-authoritative calculations
        cs = calculate_control_strength(base_score, findings)
        vuln = calculate_vulnerability_factor(data.tcap, cs)

        tef_mean = calculate_pert_mean(data.tef_min, data.tef_mode, data.tef_max)
        lef = calculate_lef(tef_mean, vuln)

        pl_mean = calculate_pert_mean(data.pl_min, data.pl_mode, data.pl_max)
        sl_mean = calculate_pert_mean(data.sl_min, data.sl_mode, data.sl_max)
        mlm = calculate_mean_loss_magnitude(pl_mean, sl_mean, data.slop)
        sle = mlm
        ale = calculate_ale(lef, sle)

        pl_var = calculate_pert_variance(data.pl_min, data.pl_mode, data.pl_max)
        sl_var = calculate_pert_variance(data.sl_min, data.sl_mode, data.sl_max)
        var_95_p = calculate_parametric_var(ale, lef, pl_var, sl_var, data.slop, mlm, 0.95)
        var_99_p = calculate_parametric_var(ale, lef, pl_var, sl_var, data.slop, mlm, 0.99)

        snapshot_hash = cls._compute_snapshot_hash({
            "code": data.scenario_code,
            "tef": (data.tef_min, data.tef_mode, data.tef_max),
            "tcap": data.tcap,
            "pl": (data.pl_min, data.pl_mode, data.pl_max),
            "sl": (data.sl_min, data.sl_mode, data.sl_max),
            "slop": data.slop,
            "cs": cs,
            "calc_version": CALCULATION_VERSION,
        })

        scenario = QuantitativeRiskScenario(
            organization_id=org_id,
            scenario_code=data.scenario_code,
            title=data.title,
            description=data.description,
            status=ScenarioStatusEnum.DRAFT,
            threat_actor_category=data.threat_actor_category,
            risk_id=data.risk_id,
            organization_control_id=data.organization_control_id,
            vendor_id=data.vendor_id,
            tef_min=data.tef_min,
            tef_mode=data.tef_mode,
            tef_max=data.tef_max,
            tcap=data.tcap,
            pl_min=data.pl_min,
            pl_mode=data.pl_mode,
            pl_max=data.pl_max,
            sl_min=data.sl_min,
            sl_mode=data.sl_mode,
            sl_max=data.sl_max,
            slop=data.slop,
            control_strength=round(cs, 4),
            vulnerability_factor=round(vuln, 4),
            loss_event_frequency=round(lef, 4),
            single_loss_expectancy=round(sle, 2),
            annualized_loss_expectancy=round(ale, 2),
            var_95_parametric=round(var_95_p, 2),
            var_99_parametric=round(var_99_p, 2),
            is_immutable=False,
            is_ccm_stale=is_stale,
            calculation_version=CALCULATION_VERSION,
            input_snapshot_hash=snapshot_hash,
            calculated_at=datetime.now(timezone.utc),
            created_by_id=user_id,
        )

        db.add(scenario)
        db.commit()
        db.refresh(scenario)

        AuditService.log(
            db=db,
            organization_id=org_id,
            action="QUANTRISK_SCENARIO_CREATED",
            resource_type="QuantitativeRiskScenario",
            actor_email=cls._get_actor_email(db, user_id),
            actor_id=user_id,
            resource_id=str(scenario.id),
            details={
                "scenario_code": scenario.scenario_code,
                "ale": scenario.annualized_loss_expectancy,
                "lef": scenario.loss_event_frequency,
            },
        )

        return scenario

    @classmethod
    def get_scenario(
        cls, db: Session, org_id: int, scenario_id: int
    ) -> QuantitativeRiskScenario:
        """Fetch a single scenario enforcing tenant isolation."""
        scenario = (
            db.query(QuantitativeRiskScenario)
            .filter(
                QuantitativeRiskScenario.id == scenario_id,
                QuantitativeRiskScenario.organization_id == org_id,
            )
            .first()
        )
        if not scenario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Quantitative Risk Scenario #{scenario_id} not found.",
            )
        return scenario

    @classmethod
    def update_scenario(
        cls,
        db: Session,
        org_id: int,
        user_id: int,
        scenario_id: int,
        data: QuantitativeRiskScenarioUpdate,
    ) -> QuantitativeRiskScenario:
        """Update mutable scenario fields and recalculate server metrics."""
        scenario = cls.get_scenario(db, org_id, scenario_id)

        if scenario.is_immutable or scenario.status == ScenarioStatusEnum.FROZEN:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Frozen quantitative scenarios are immutable and cannot be modified.",
            )

        # Update input fields if supplied
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(scenario, field, value)

        # Ingest CCM & recalculate metrics
        base_score, is_stale, findings = cls._resolve_control_telemetry(
            db, org_id, scenario.organization_control_id
        )

        cs = calculate_control_strength(base_score, findings)
        vuln = calculate_vulnerability_factor(scenario.tcap, cs)

        tef_mean = calculate_pert_mean(
            scenario.tef_min, scenario.tef_mode, scenario.tef_max
        )
        lef = calculate_lef(tef_mean, vuln)

        pl_mean = calculate_pert_mean(scenario.pl_min, scenario.pl_mode, scenario.pl_max)
        sl_mean = calculate_pert_mean(scenario.sl_min, scenario.sl_mode, scenario.sl_max)
        mlm = calculate_mean_loss_magnitude(pl_mean, sl_mean, scenario.slop)
        sle = mlm
        ale = calculate_ale(lef, sle)

        pl_var = calculate_pert_variance(
            scenario.pl_min, scenario.pl_mode, scenario.pl_max
        )
        sl_var = calculate_pert_variance(
            scenario.sl_min, scenario.sl_mode, scenario.sl_max
        )
        var_95_p = calculate_parametric_var(
            ale, lef, pl_var, sl_var, scenario.slop, mlm, 0.95
        )
        var_99_p = calculate_parametric_var(
            ale, lef, pl_var, sl_var, scenario.slop, mlm, 0.99
        )

        snapshot_hash = cls._compute_snapshot_hash({
            "code": scenario.scenario_code,
            "tef": (scenario.tef_min, scenario.tef_mode, scenario.tef_max),
            "tcap": scenario.tcap,
            "pl": (scenario.pl_min, scenario.pl_mode, scenario.pl_max),
            "sl": (scenario.sl_min, scenario.sl_mode, scenario.sl_max),
            "slop": scenario.slop,
            "cs": cs,
            "calc_version": CALCULATION_VERSION,
        })

        scenario.control_strength = round(cs, 4)
        scenario.vulnerability_factor = round(vuln, 4)
        scenario.loss_event_frequency = round(lef, 4)
        scenario.single_loss_expectancy = round(sle, 2)
        scenario.annualized_loss_expectancy = round(ale, 2)
        scenario.var_95_parametric = round(var_95_p, 2)
        scenario.var_99_parametric = round(var_99_p, 2)
        scenario.is_ccm_stale = is_stale
        scenario.input_snapshot_hash = snapshot_hash
        scenario.calculated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(scenario)

        AuditService.log(
            db=db,
            organization_id=org_id,
            action="QUANTRISK_SCENARIO_UPDATED",
            resource_type="QuantitativeRiskScenario",
            actor_email=cls._get_actor_email(db, user_id),
            actor_id=user_id,
            resource_id=str(scenario.id),
            details={"ale": scenario.annualized_loss_expectancy},
        )

        return scenario

    @classmethod
    def freeze_scenario(
        cls, db: Session, org_id: int, user_id: int, scenario_id: int
    ) -> QuantitativeRiskScenario:
        """Freeze a scenario baseline into an immutable record."""
        scenario = cls.get_scenario(db, org_id, scenario_id)
        if scenario.status == ScenarioStatusEnum.FROZEN:
            return scenario

        scenario.status = ScenarioStatusEnum.FROZEN
        scenario.is_immutable = True
        db.commit()
        db.refresh(scenario)

        AuditService.log(
            db=db,
            organization_id=org_id,
            action="QUANTRISK_SCENARIO_FROZEN",
            resource_type="QuantitativeRiskScenario",
            actor_email=cls._get_actor_email(db, user_id),
            actor_id=user_id,
            resource_id=str(scenario.id),
            details={"scenario_code": scenario.scenario_code},
        )
        return scenario

    # ─── 2. EMPIRICAL SIMULATION EXECUTION ─────────────────────────────────────

    @classmethod
    def execute_simulation(
        cls,
        db: Session,
        org_id: int,
        user_id: int,
        scenario_id: int,
        request: QuantitativeSimulationRequest,
    ) -> QuantitativeSimulationRun:
        """Run empirical Monte Carlo simulation for a scenario and persist immutable run."""
        scenario = cls.get_scenario(db, org_id, scenario_id)

        sim_results = run_monte_carlo_simulation(
            tef_min=scenario.tef_min,
            tef_mode=scenario.tef_mode,
            tef_max=scenario.tef_max,
            tcap=scenario.tcap,
            cs=scenario.control_strength,
            pl_min=scenario.pl_min,
            pl_mode=scenario.pl_mode,
            pl_max=scenario.pl_max,
            sl_min=scenario.sl_min,
            sl_mode=scenario.sl_mode,
            sl_max=scenario.sl_max,
            slop=scenario.slop,
            trial_count=request.trial_count,
            seed=request.simulation_seed,
        )

        run = QuantitativeSimulationRun(
            organization_id=org_id,
            scenario_id=scenario.id,
            trial_count=sim_results["trial_count"],
            simulation_seed=sim_results["simulation_seed"],
            algorithm_version=ALGORITHM_VERSION,
            mean_loss=sim_results["mean_loss"],
            variance_loss=sim_results["variance_loss"],
            std_dev_loss=sim_results["std_dev_loss"],
            percentile_10=sim_results["percentile_10"],
            percentile_50=sim_results["percentile_50"],
            percentile_90=sim_results["percentile_90"],
            percentile_95=sim_results["percentile_95"],
            percentile_99=sim_results["percentile_99"],
            simulated_by_id=user_id,
            simulated_at=datetime.now(timezone.utc),
        )

        # Update empirical VaR on scenario
        scenario.var_95_empirical = sim_results["percentile_95"]
        scenario.var_99_empirical = sim_results["percentile_99"]

        db.add(run)
        db.commit()
        db.refresh(run)

        AuditService.log(
            db=db,
            organization_id=org_id,
            action="QUANTRISK_SIMULATION_EXECUTED",
            resource_type="QuantitativeSimulationRun",
            actor_email=cls._get_actor_email(db, user_id),
            actor_id=user_id,
            resource_id=str(run.id),
            details={
                "scenario_code": scenario.scenario_code,
                "trials": run.trial_count,
                "var_95": run.percentile_95,
            },
        )

        return run

    # ─── 3. ROSI ANALYSIS ─────────────────────────────────────────────────────

    @classmethod
    def calculate_and_record_rosi(
        cls,
        db: Session,
        org_id: int,
        user_id: int,
        scenario_id: int,
        data: RosiAnalysisCreate,
    ) -> RosiAnalysis:
        """Compute and persist Return on Security Investment for a remediation plan."""
        scenario = cls.get_scenario(db, org_id, scenario_id)

        # Validate remediation plan in tenant
        plan = (
            db.query(RemediationPlan)
            .filter(
                RemediationPlan.id == data.remediation_plan_id,
                RemediationPlan.organization_id == org_id,
            )
            .first()
        )
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Remediation Plan #{data.remediation_plan_id} not found in tenant.",
            )

        # Determine projected control strength
        if data.projected_control_strength_delta is not None:
            projected_cs = min(
                1.0, scenario.control_strength + data.projected_control_strength_delta
            )
        elif plan.rei_score is not None:
            projected_cs = min(
                1.0, scenario.control_strength + (plan.rei_score / 200.0)
            )
        else:
            projected_cs = min(1.0, scenario.control_strength + 0.30)

        # Compute projected ALE
        proj_vuln = calculate_vulnerability_factor(scenario.tcap, projected_cs)
        tef_mean = calculate_pert_mean(
            scenario.tef_min, scenario.tef_mode, scenario.tef_max
        )
        proj_lef = calculate_lef(tef_mean, proj_vuln)
        projected_ale = calculate_ale(proj_lef, scenario.single_loss_expectancy)

        rosi_result = calculate_rosi(
            current_ale=scenario.annualized_loss_expectancy,
            projected_ale=projected_ale,
            remediation_cost=data.remediation_cost,
        )

        analysis = RosiAnalysis(
            organization_id=org_id,
            scenario_id=scenario.id,
            remediation_plan_id=plan.id,
            remediation_cost=data.remediation_cost,
            current_ale=rosi_result["current_ale"],
            projected_ale=rosi_result["projected_ale"],
            risk_reduction_ale=rosi_result["risk_reduction_ale"],
            net_economic_benefit=rosi_result["net_economic_benefit"],
            rosi_percentage=rosi_result["rosi_percentage"],
            created_by_id=user_id,
            created_at=datetime.now(timezone.utc),
        )

        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        AuditService.log(
            db=db,
            organization_id=org_id,
            action="QUANTRISK_ROSI_CALCULATED",
            resource_type="RosiAnalysis",
            actor_email=cls._get_actor_email(db, user_id),
            actor_id=user_id,
            resource_id=str(analysis.id),
            details={
                "scenario_code": scenario.scenario_code,
                "rosi_pct": analysis.rosi_percentage,
                "net_benefit": analysis.net_economic_benefit,
            },
        )

        return analysis

    # ─── 4. FINANCIAL RISK APPETITE ───────────────────────────────────────────

    @classmethod
    def create_risk_appetite(
        cls,
        db: Session,
        org_id: int,
        user_id: int,
        data: FinancialRiskAppetiteCreate,
    ) -> FinancialRiskAppetite:
        """Create a new draft Financial Risk Appetite version."""
        # Get next version number
        latest_version = (
            db.query(func.max(FinancialRiskAppetite.version))
            .filter(FinancialRiskAppetite.organization_id == org_id)
            .scalar()
            or 0
        )

        appetite = FinancialRiskAppetite(
            organization_id=org_id,
            version=latest_version + 1,
            ale_limit=round(data.ale_limit, 2),
            var_95_limit=round(data.var_95_limit, 2),
            status=AppetiteStatusEnum.DRAFT,
            notes=data.notes,
            requested_by_id=user_id,
            created_at=datetime.now(timezone.utc),
        )

        db.add(appetite)
        db.commit()
        db.refresh(appetite)

        AuditService.log(
            db=db,
            organization_id=org_id,
            action="QUANTRISK_APPETITE_CREATED",
            resource_type="FinancialRiskAppetite",
            actor_email=cls._get_actor_email(db, user_id),
            actor_id=user_id,
            resource_id=str(appetite.id),
            details={"version": appetite.version, "ale_limit": appetite.ale_limit},
        )

        return appetite

    @classmethod
    def approve_risk_appetite(
        cls,
        db: Session,
        org_id: int,
        user_id: int,
        appetite_id: int,
        notes: Optional[str] = None,
    ) -> FinancialRiskAppetite:
        """
        Formally approve a Financial Risk Appetite with four-eyes separation of duties.
        Requester != Approver.
        """
        appetite = (
            db.query(FinancialRiskAppetite)
            .filter(
                FinancialRiskAppetite.id == appetite_id,
                FinancialRiskAppetite.organization_id == org_id,
            )
            .first()
        )
        if not appetite:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Financial Risk Appetite #{appetite_id} not found.",
            )

        if appetite.status == AppetiteStatusEnum.APPROVED:
            return appetite

        # Four-eyes separation of duties check
        if appetite.requested_by_id == user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Four-eyes separation violation: Requester cannot approve their own financial risk appetite.",
            )

        # Supersede currently approved appetite versions
        db.query(FinancialRiskAppetite).filter(
            FinancialRiskAppetite.organization_id == org_id,
            FinancialRiskAppetite.status == AppetiteStatusEnum.APPROVED,
        ).update({"status": AppetiteStatusEnum.SUPERSEDED})

        appetite.status = AppetiteStatusEnum.APPROVED
        appetite.approved_by_id = user_id
        appetite.approved_at = datetime.now(timezone.utc)
        if notes:
            appetite.notes = (appetite.notes or "") + f"\n[Approval Note]: {notes}"

        db.commit()
        db.refresh(appetite)

        AuditService.log(
            db=db,
            organization_id=org_id,
            action="QUANTRISK_APPETITE_APPROVED",
            resource_type="FinancialRiskAppetite",
            actor_email=cls._get_actor_email(db, user_id),
            actor_id=user_id,
            resource_id=str(appetite.id),
            details={"version": appetite.version, "ale_limit": appetite.ale_limit},
        )

        return appetite

    @classmethod
    def get_active_appetite(
        cls, db: Session, org_id: int
    ) -> Optional[FinancialRiskAppetite]:
        """Fetch currently approved appetite threshold for tenant."""
        return (
            db.query(FinancialRiskAppetite)
            .filter(
                FinancialRiskAppetite.organization_id == org_id,
                FinancialRiskAppetite.status == AppetiteStatusEnum.APPROVED,
            )
            .first()
        )
