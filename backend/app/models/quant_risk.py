from datetime import datetime, timezone
import enum
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


# ─────────────────────────────────────────────────────────────────────────────
# Phase 12: QUANTUM-GRC Domain Enums
# ─────────────────────────────────────────────────────────────────────────────

class ScenarioStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"
    ARCHIVED = "ARCHIVED"


class ThreatActorCategoryEnum(str, enum.Enum):
    CYBERCRIMINAL = "CYBERCRIMINAL"
    NATION_STATE = "NATION_STATE"
    INSIDER = "INSIDER"
    HACKTIVIST = "HACKTIVIST"
    ACCIDENTAL = "ACCIDENTAL"


class AppetiteStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    SUPERSEDED = "SUPERSEDED"


class AppetiteBreachStateEnum(str, enum.Enum):
    WITHIN_APPETITE = "WITHIN_APPETITE"
    EXCEEDS_ALE = "EXCEEDS_ALE"
    EXCEEDS_VAR = "EXCEEDS_VAR"
    EXCEEDS_BOTH = "EXCEEDS_BOTH"


# ─────────────────────────────────────────────────────────────────────────────
# 1. QUANTITATIVE RISK SCENARIO MODEL
# ─────────────────────────────────────────────────────────────────────────────

class QuantitativeRiskScenario(Base):
    """Authoritative financial loss model and FAIR-inspired scenario entity."""
    __tablename__ = "quant_risk_scenarios"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scenario_code = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(
        Enum(ScenarioStatusEnum),
        nullable=False,
        default=ScenarioStatusEnum.DRAFT,
        index=True,
    )
    threat_actor_category = Column(
        Enum(ThreatActorCategoryEnum),
        nullable=False,
        default=ThreatActorCategoryEnum.CYBERCRIMINAL,
        index=True,
    )

    # Cross-Module Upstream Linkages
    risk_id = Column(
        Integer,
        ForeignKey("risks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    organization_control_id = Column(
        Integer,
        ForeignKey("organization_controls.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    vendor_id = Column(
        Integer,
        ForeignKey("vendors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Beta-PERT Threat & Loss Parameters
    tef_min = Column(Float, nullable=False, default=0.0)
    tef_mode = Column(Float, nullable=False, default=1.0)
    tef_max = Column(Float, nullable=False, default=5.0)
    tcap = Column(Float, nullable=False, default=0.5)

    pl_min = Column(Float, nullable=False, default=0.0)
    pl_mode = Column(Float, nullable=False, default=10000.0)
    pl_max = Column(Float, nullable=False, default=50000.0)

    sl_min = Column(Float, nullable=False, default=0.0)
    sl_mode = Column(Float, nullable=False, default=5000.0)
    sl_max = Column(Float, nullable=False, default=20000.0)
    slop = Column(Float, nullable=False, default=0.5)

    # Server-Authoritative Computed Metrics
    control_strength = Column(Float, nullable=False, default=0.0)
    vulnerability_factor = Column(Float, nullable=False, default=0.0)
    loss_event_frequency = Column(Float, nullable=False, default=0.0)
    single_loss_expectancy = Column(Float, nullable=False, default=0.0)
    annualized_loss_expectancy = Column(Float, nullable=False, default=0.0)
    var_95_parametric = Column(Float, nullable=True)
    var_99_parametric = Column(Float, nullable=True)
    var_95_empirical = Column(Float, nullable=True)
    var_99_empirical = Column(Float, nullable=True)

    # Governance, Snapshots & Immutability
    is_immutable = Column(Boolean, nullable=False, default=False)
    is_ccm_stale = Column(Boolean, nullable=False, default=False)
    calculation_version = Column(String(32), nullable=False, default="2026.12.1")
    input_snapshot_hash = Column(String(64), nullable=True)
    calculated_at = Column(DateTime(timezone=True), nullable=True)

    created_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "scenario_code",
            name="uq_quant_scenario_code_per_tenant",
        ),
        CheckConstraint(
            "tef_min >= 0 AND tef_min <= tef_mode AND tef_mode <= tef_max",
            name="chk_tef_pert_order",
        ),
        CheckConstraint(
            "pl_min >= 0 AND pl_min <= pl_mode AND pl_mode <= pl_max",
            name="chk_pl_pert_order",
        ),
        CheckConstraint(
            "sl_min >= 0 AND sl_min <= sl_mode AND sl_mode <= sl_max",
            name="chk_sl_pert_order",
        ),
        CheckConstraint("tcap >= 0.0 AND tcap <= 1.0", name="chk_tcap_range"),
        CheckConstraint("slop >= 0.0 AND slop <= 1.0", name="chk_slop_range"),
        CheckConstraint(
            "control_strength >= 0.0 AND control_strength <= 1.0",
            name="chk_cs_range",
        ),
        CheckConstraint(
            "vulnerability_factor >= 0.0 AND vulnerability_factor <= 1.0",
            name="chk_vuln_range",
        ),
        CheckConstraint(
            "loss_event_frequency >= 0.0",
            name="chk_lef_non_negative",
        ),
        CheckConstraint(
            "single_loss_expectancy >= 0.0",
            name="chk_sle_non_negative",
        ),
        CheckConstraint(
            "annualized_loss_expectancy >= 0.0",
            name="chk_ale_non_negative",
        ),
    )

    # Relationships
    organization = relationship("Organization")
    created_by = relationship("User", foreign_keys=[created_by_id])
    risk = relationship("Risk", foreign_keys=[risk_id])
    organization_control = relationship("OrganizationControl", foreign_keys=[organization_control_id])
    vendor = relationship("Vendor", foreign_keys=[vendor_id])
    simulation_runs = relationship(
        "QuantitativeSimulationRun",
        back_populates="scenario",
        cascade="all, delete-orphan",
        order_by="desc(QuantitativeSimulationRun.simulated_at)",
    )
    rosi_analyses = relationship(
        "RosiAnalysis",
        back_populates="scenario",
        cascade="all, delete-orphan",
        order_by="desc(RosiAnalysis.created_at)",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. QUANTITATIVE SIMULATION RUN MODEL
# ─────────────────────────────────────────────────────────────────────────────

class QuantitativeSimulationRun(Base):
    """Immutable record of an empirical Monte Carlo trial execution."""
    __tablename__ = "quant_simulation_runs"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scenario_id = Column(
        Integer,
        ForeignKey("quant_risk_scenarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    trial_count = Column(Integer, nullable=False, default=10000)
    simulation_seed = Column(Integer, nullable=False)
    algorithm_version = Column(String(32), nullable=False, default="SIM_PERT_V1")

    mean_loss = Column(Float, nullable=False)
    variance_loss = Column(Float, nullable=False)
    std_dev_loss = Column(Float, nullable=False)

    percentile_10 = Column(Float, nullable=False)
    percentile_50 = Column(Float, nullable=False)
    percentile_90 = Column(Float, nullable=False)
    percentile_95 = Column(Float, nullable=False)
    percentile_99 = Column(Float, nullable=False)

    simulated_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    simulated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        CheckConstraint(
            "trial_count >= 100 AND trial_count <= 50000",
            name="chk_simulation_trial_count_bounds",
        ),
        CheckConstraint("mean_loss >= 0.0", name="chk_sim_mean_non_negative"),
        CheckConstraint(
            "percentile_10 >= 0.0 AND percentile_10 <= percentile_50 AND percentile_50 <= percentile_90 AND percentile_90 <= percentile_95 AND percentile_95 <= percentile_99",
            name="chk_sim_percentiles_order",
        ),
    )

    # Relationships
    organization = relationship("Organization")
    scenario = relationship("QuantitativeRiskScenario", back_populates="simulation_runs")
    simulated_by = relationship("User", foreign_keys=[simulated_by_id])


# ─────────────────────────────────────────────────────────────────────────────
# 3. RETURN ON SECURITY INVESTMENT (ROSI) ANALYSIS MODEL
# ─────────────────────────────────────────────────────────────────────────────

class RosiAnalysis(Base):
    """Return on Security Investment evaluation linked to Phase 11 Remediation."""
    __tablename__ = "rosi_analyses"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scenario_id = Column(
        Integer,
        ForeignKey("quant_risk_scenarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    remediation_plan_id = Column(
        Integer,
        ForeignKey("remediation_plans.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    remediation_cost = Column(Float, nullable=False)
    current_ale = Column(Float, nullable=False)
    projected_ale = Column(Float, nullable=False)
    risk_reduction_ale = Column(Float, nullable=False)
    net_economic_benefit = Column(Float, nullable=False)
    rosi_percentage = Column(Float, nullable=False)

    created_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        CheckConstraint("remediation_cost > 0.0", name="chk_rosi_remediation_cost_positive"),
        CheckConstraint("current_ale >= 0.0", name="chk_rosi_current_ale_non_negative"),
        CheckConstraint("projected_ale >= 0.0", name="chk_rosi_projected_ale_non_negative"),
    )

    # Relationships
    organization = relationship("Organization")
    scenario = relationship("QuantitativeRiskScenario", back_populates="rosi_analyses")
    remediation_plan = relationship("RemediationPlan")
    created_by = relationship("User", foreign_keys=[created_by_id])


# ─────────────────────────────────────────────────────────────────────────────
# 4. FINANCIAL RISK APPETITE MODEL
# ─────────────────────────────────────────────────────────────────────────────

class FinancialRiskAppetite(Base):
    """Board-approved financial risk threshold and four-eyes appetite governance."""
    __tablename__ = "financial_risk_appetites"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version = Column(Integer, nullable=False, default=1)
    ale_limit = Column(Float, nullable=False)
    var_95_limit = Column(Float, nullable=False)
    status = Column(
        Enum(AppetiteStatusEnum),
        nullable=False,
        default=AppetiteStatusEnum.DRAFT,
        index=True,
    )
    notes = Column(Text, nullable=True)

    # Four-Eyes Governance Attributions
    requested_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    approved_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    approved_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "version",
            name="uq_appetite_version_per_tenant",
        ),
        CheckConstraint("ale_limit >= 0.0", name="chk_appetite_ale_limit_non_negative"),
        CheckConstraint("var_95_limit >= 0.0", name="chk_appetite_var_limit_non_negative"),
    )

    # Relationships
    organization = relationship("Organization")
    requested_by = relationship("User", foreign_keys=[requested_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
