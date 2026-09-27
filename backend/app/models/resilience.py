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
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


# ─────────────────────────────────────────────────────────────────────────────
# Phase 13 & Batch 5: RESILIENCE-CONTINUITY-GRC Domain Enums
# ─────────────────────────────────────────────────────────────────────────────

class BiaStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    ARCHIVED = "ARCHIVED"


class CriticalityTierEnum(str, enum.Enum):
    TIER_1 = "TIER_1"  # Mission Critical (<4h RTO)
    TIER_2 = "TIER_2"  # Business Critical (<24h RTO)
    TIER_3 = "TIER_3"  # Operational / Important (<72h RTO)
    TIER_4 = "TIER_4"  # Non-Critical / Administrative (>72h RTO)


class DependencyTypeEnum(str, enum.Enum):
    VENDOR = "VENDOR"
    CONTROL = "CONTROL"
    CLOUD_ASSET = "CLOUD_ASSET"
    DATA_ASSET = "DATA_ASSET"
    PROCESS = "PROCESS"


class ContinuityPlanStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    SUPERSEDED = "SUPERSEDED"
    ARCHIVED = "ARCHIVED"


class ContinuityStrategyTypeEnum(str, enum.Enum):
    ACTIVE_ACTIVE = "ACTIVE_ACTIVE"
    ACTIVE_ACTIVE_FAILOVER = "ACTIVE_ACTIVE_FAILOVER"
    ACTIVE_PASSIVE_FAILOVER = "ACTIVE_PASSIVE_FAILOVER"
    HOT_STANDBY = "HOT_STANDBY"
    WARM_STANDBY = "WARM_STANDBY"
    COLD_SITE = "COLD_SITE"
    COLD_RESTORE_BACKUP = "COLD_RESTORE_BACKUP"
    MANUAL_WORKAROUND = "MANUAL_WORKAROUND"
    SUPPLIER_SUBSTITUTION = "SUPPLIER_SUBSTITUTION"
    ALTERNATE_VENDOR_SWITCH = "ALTERNATE_VENDOR_SWITCH"


class ExerciseTypeEnum(str, enum.Enum):
    TABLETOP = "TABLETOP"
    FUNCTIONAL_FAILOVER = "FUNCTIONAL_FAILOVER"
    FULL_INTERRUPTION = "FULL_INTERRUPTION"
    BACKUP_RESTORATION = "BACKUP_RESTORATION"
    THIRD_PARTY_RESILIENCE = "THIRD_PARTY_RESILIENCE"


class ExerciseStatusEnum(str, enum.Enum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    REVIEWED = "REVIEWED"
    CANCELLED = "CANCELLED"


class ExerciseOutcomeEnum(str, enum.Enum):
    PASS = "PASS"
    PASS_WITH_MINOR_EXCEPTIONS = "PASS_WITH_MINOR_EXCEPTIONS"
    FAIL_RTO_BREACH = "FAIL_RTO_BREACH"
    FAIL_RPO_BREACH = "FAIL_RPO_BREACH"
    FAIL_MTD_BREACH = "FAIL_MTD_BREACH"
    FAIL_CONTROL_DEFICIENCY = "FAIL_CONTROL_DEFICIENCY"


class ResilienceEvidenceContextEnum(str, enum.Enum):
    CONTINUITY_RUNBOOK = "CONTINUITY_RUNBOOK"
    RUNBOOK_DOCUMENT = "RUNBOOK_DOCUMENT"
    ARCHITECTURE_DIAGRAM = "ARCHITECTURE_DIAGRAM"
    EXERCISE_LOG = "EXERCISE_LOG"
    FAILOVER_LOG = "FAILOVER_LOG"
    FAILOVER_TELEMETRY = "FAILOVER_TELEMETRY"
    BACKUP_RESTORE_PROOF = "BACKUP_RESTORE_PROOF"
    RESTORATION_SCREENSHOT = "RESTORATION_SCREENSHOT"
    OBSERVER_SIGN_OFF = "OBSERVER_SIGN_OFF"
    SIGN_OFF_ARTIFACT = "SIGN_OFF_ARTIFACT"
    POST_MORTEM_REPORT = "POST_MORTEM_REPORT"
    POST_EXERCISE_REPORT = "POST_EXERCISE_REPORT"
    VENDOR_DR_ATTESTATION = "VENDOR_DR_ATTESTATION"


# ─────────────────────────────────────────────────────────────────────────────
# 1. BUSINESS PROCESS MODEL
# ─────────────────────────────────────────────────────────────────────────────

class BusinessProcess(Base):
    """Authoritative organizational business process catalog entity."""
    __tablename__ = "business_processes"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    owner_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    criticality_tier = Column(
        Enum(CriticalityTierEnum),
        nullable=False,
        default=CriticalityTierEnum.TIER_3,
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

    # Relationships
    organization = relationship("Organization")
    owner = relationship("User", foreign_keys=[owner_id])
    impact_analyses = relationship(
        "BusinessImpactAnalysis",
        back_populates="process",
        cascade="all, delete-orphan",
        order_by="BusinessImpactAnalysis.version.desc()",
    )
    dependencies = relationship(
        "ProcessDependency",
        back_populates="process",
        foreign_keys="ProcessDependency.process_id",
        cascade="all, delete-orphan",
    )
    continuity_plans = relationship(
        "ContinuityPlan",
        back_populates="process",
        cascade="all, delete-orphan",
        order_by="ContinuityPlan.version_major.desc(), ContinuityPlan.version_minor.desc()",
    )
    exercises = relationship(
        "ResilienceExercise",
        back_populates="process",
        cascade="all, delete-orphan",
        order_by="ResilienceExercise.scheduled_start_at.desc()",
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_business_process_org_name"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. BUSINESS IMPACT ANALYSIS (BIA) MODEL
# ─────────────────────────────────────────────────────────────────────────────

class BusinessImpactAnalysis(Base):
    """Governed, versioned, immutable Business Impact Analysis baseline."""
    __tablename__ = "business_impact_analyses"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    process_id = Column(
        Integer,
        ForeignKey("business_processes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(
        Enum(BiaStatusEnum),
        nullable=False,
        default=BiaStatusEnum.DRAFT,
        index=True,
    )
    version = Column(Integer, nullable=False, default=1)

    # Operational Downtime Thresholds (Hours)
    rto_hours = Column(Float, nullable=False, default=4.0)
    rpo_hours = Column(Float, nullable=False, default=1.0)
    mtd_hours = Column(Float, nullable=False, default=24.0)

    # Financial Disruption Parameters (USD)
    hourly_downtime_cost = Column(Float, nullable=False, default=10000.0)
    fixed_outage_cost = Column(Float, nullable=False, default=5000.0)

    # Governance & Four-Eyes
    requested_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    approved_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    approved_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

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

    # Relationships
    organization = relationship("Organization")
    process = relationship("BusinessProcess", back_populates="impact_analyses")
    requested_by = relationship("User", foreign_keys=[requested_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])

    __table_args__ = (
        CheckConstraint("rto_hours <= mtd_hours", name="chk_bia_rto_lte_mtd"),
        CheckConstraint("rto_hours >= 0", name="chk_bia_rto_nonneg"),
        CheckConstraint("rpo_hours >= 0", name="chk_bia_rpo_nonneg"),
        CheckConstraint("mtd_hours >= 0", name="chk_bia_mtd_nonneg"),
        CheckConstraint("hourly_downtime_cost >= 0", name="chk_bia_hourly_cost_nonneg"),
        CheckConstraint("fixed_outage_cost >= 0", name="chk_bia_fixed_cost_nonneg"),
        UniqueConstraint("process_id", "version", name="uq_bia_process_version"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. PROCESS DEPENDENCY MODEL (Extended Lineage & SPOF Governance)
# ─────────────────────────────────────────────────────────────────────────────

class ProcessDependency(Base):
    """Cross-module dependency mapping (Vendor, Control, CloudAsset, DataAsset, Process)."""
    __tablename__ = "process_dependencies"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    process_id = Column(
        Integer,
        ForeignKey("business_processes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dependency_type = Column(
        Enum(DependencyTypeEnum),
        nullable=False,
        index=True,
    )
    dependency_id = Column(Integer, nullable=False, index=True)
    notes = Column(String(255), nullable=True)

    # Batch 5 Typed Target Foreign Keys & Resilience Parameters
    vendor_id = Column(
        Integer,
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    organization_control_id = Column(
        Integer,
        ForeignKey("organization_controls.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    cloud_asset_id = Column(
        Integer,
        ForeignKey("cloud_assets.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    data_asset_id = Column(
        Integer,
        ForeignKey("data_assets.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    depends_on_process_id = Column(
        Integer,
        ForeignKey("business_processes.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    is_single_point_of_failure = Column(Boolean, nullable=False, default=False)
    failure_propagation_weight = Column(Float, nullable=False, default=1.0)
    recovery_priority_order = Column(Integer, nullable=False, default=1)
    criticality_notes = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    organization = relationship("Organization")
    process = relationship(
        "BusinessProcess",
        back_populates="dependencies",
        foreign_keys=[process_id],
    )
    depends_on_process = relationship(
        "BusinessProcess",
        foreign_keys=[depends_on_process_id],
    )
    vendor = relationship("Vendor", foreign_keys=[vendor_id])
    organization_control = relationship("OrganizationControl", foreign_keys=[organization_control_id])
    cloud_asset = relationship("CloudAsset", foreign_keys=[cloud_asset_id])
    data_asset = relationship("DataAsset", foreign_keys=[data_asset_id])

    __table_args__ = (
        UniqueConstraint(
            "process_id",
            "dependency_type",
            "dependency_id",
            name="uq_process_dependency",
        ),
        CheckConstraint(
            "depends_on_process_id IS NULL OR depends_on_process_id != process_id",
            name="chk_process_dependency_no_self_ref",
        ),
        CheckConstraint(
            """(
                (CASE WHEN vendor_id IS NOT NULL THEN 1 ELSE 0 END) +
                (CASE WHEN organization_control_id IS NOT NULL THEN 1 ELSE 0 END) +
                (CASE WHEN cloud_asset_id IS NOT NULL THEN 1 ELSE 0 END) +
                (CASE WHEN data_asset_id IS NOT NULL THEN 1 ELSE 0 END) +
                (CASE WHEN depends_on_process_id IS NOT NULL THEN 1 ELSE 0 END)
            ) = 1""",
            name="chk_dependency_single_target",
        ),
        CheckConstraint(
            "failure_propagation_weight > 0.0 AND failure_propagation_weight <= 1.0",
            name="chk_dep_propagation_weight",
        ),
        CheckConstraint(
            "recovery_priority_order >= 1",
            name="chk_dep_recovery_priority",
        ),
    )


def _sync_process_dependency_targets( mapper, connection, target: ProcessDependency) -> None:
    """Ensure backward-compatible sync between dependency_id and typed FK columns."""
    typed_cols = [
        target.vendor_id,
        target.organization_control_id,
        target.cloud_asset_id,
        target.data_asset_id,
        target.depends_on_process_id,
    ]
    non_null_typed = [c for c in typed_cols if c is not None]

    if len(non_null_typed) == 0 and target.dependency_id is not None and target.dependency_type is not None:
        dtype = (
            target.dependency_type.value
            if isinstance(target.dependency_type, DependencyTypeEnum)
            else str(target.dependency_type).upper()
        )
        if dtype == DependencyTypeEnum.VENDOR.value:
            target.vendor_id = target.dependency_id
        elif dtype == DependencyTypeEnum.CONTROL.value:
            target.organization_control_id = target.dependency_id
        elif dtype == DependencyTypeEnum.CLOUD_ASSET.value:
            target.cloud_asset_id = target.dependency_id
        elif dtype == DependencyTypeEnum.DATA_ASSET.value:
            target.data_asset_id = target.dependency_id
        elif dtype == DependencyTypeEnum.PROCESS.value:
            target.depends_on_process_id = target.dependency_id
    elif len(non_null_typed) == 1 and target.dependency_id is None:
        target.dependency_id = non_null_typed[0]


event.listen(ProcessDependency, "before_insert", _sync_process_dependency_targets)
event.listen(ProcessDependency, "before_update", _sync_process_dependency_targets)


# ─────────────────────────────────────────────────────────────────────────────
# 4. CONTINUITY PLAN MODEL (Batch 5)
# ─────────────────────────────────────────────────────────────────────────────

class ContinuityPlan(Base):
    """Versioned, Four-Eyes governed Business Continuity & Disaster Recovery Plan."""
    __tablename__ = "continuity_plans"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    process_id = Column(
        Integer,
        ForeignKey("business_processes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bia_id = Column(
        Integer,
        ForeignKey("business_impact_analyses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    plan_code = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    version_major = Column(Integer, nullable=False, default=1)
    version_minor = Column(Integer, nullable=False, default=0)
    version_label = Column(String(32), nullable=False, default="1.0")
    status = Column(
        Enum(ContinuityPlanStatusEnum),
        nullable=False,
        default=ContinuityPlanStatusEnum.DRAFT,
        index=True,
    )
    strategy_type = Column(
        Enum(ContinuityStrategyTypeEnum),
        nullable=False,
        index=True,
    )
    activation_triggers = Column(Text, nullable=False)
    communication_plan = Column(Text, nullable=True)
    fallback_location_or_region = Column(String(255), nullable=True)
    estimated_recovery_hours = Column(Float, nullable=False)
    estimated_rpo_hours = Column(Float, nullable=False)
    review_frequency_days = Column(Integer, nullable=False, default=365)
    next_review_due_at = Column(DateTime(timezone=True), nullable=True, index=True)
    plan_hash_sha256 = Column(String(64), nullable=True, index=True)

    created_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    submitted_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    approved_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    approved_at = Column(DateTime(timezone=True), nullable=True)
    superseded_by_plan_id = Column(
        Integer,
        ForeignKey("continuity_plans.id", ondelete="SET NULL"),
        nullable=True,
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

    # Relationships
    organization = relationship("Organization")
    process = relationship("BusinessProcess", back_populates="continuity_plans")
    bia = relationship("BusinessImpactAnalysis")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    submitted_by = relationship("User", foreign_keys=[submitted_by_user_id])
    approved_by = relationship("User", foreign_keys=[approved_by_user_id])
    recovery_steps = relationship(
        "ContinuityRecoveryStep",
        back_populates="continuity_plan",
        cascade="all, delete-orphan",
        order_by="ContinuityRecoveryStep.step_order.asc()",
    )
    evidence_links = relationship(
        "ResilienceEvidenceLink",
        back_populates="continuity_plan",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "process_id",
            "plan_code",
            "version_label",
            name="uq_cp_org_proc_code_ver",
        ),
        CheckConstraint("version_major >= 1", name="chk_cp_version_major_pos"),
        CheckConstraint("version_minor >= 0", name="chk_cp_version_minor_nonneg"),
        CheckConstraint("estimated_recovery_hours >= 0", name="chk_cp_est_recovery_nonneg"),
        CheckConstraint("estimated_rpo_hours >= 0", name="chk_cp_est_rpo_nonneg"),
        CheckConstraint(
            "review_frequency_days >= 1 AND review_frequency_days <= 1825",
            name="chk_cp_review_freq_range",
        ),
        Index("ix_cp_org_process_status", "organization_id", "process_id", "status"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5. CONTINUITY RECOVERY STEP MODEL (Batch 5)
# ─────────────────────────────────────────────────────────────────────────────

class ContinuityRecoveryStep(Base):
    """Ordered runbook recovery step within a ContinuityPlan."""
    __tablename__ = "continuity_recovery_steps"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    continuity_plan_id = Column(
        Integer,
        ForeignKey("continuity_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_order = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    responsible_role_or_team = Column(String(128), nullable=True)
    responsible_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    estimated_duration_minutes = Column(Integer, nullable=False, default=15)
    cloud_asset_id = Column(
        Integer,
        ForeignKey("cloud_assets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    data_asset_id = Column(
        Integer,
        ForeignKey("data_assets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    vendor_id = Column(
        Integer,
        ForeignKey("vendors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    organization_control_id = Column(
        Integer,
        ForeignKey("organization_controls.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    verification_criteria = Column(Text, nullable=True)
    is_automated = Column(Boolean, nullable=False, default=False)

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

    # Relationships
    organization = relationship("Organization")
    continuity_plan = relationship("ContinuityPlan", back_populates="recovery_steps")
    responsible_user = relationship("User", foreign_keys=[responsible_user_id])

    __table_args__ = (
        UniqueConstraint("continuity_plan_id", "step_order", name="uq_crs_plan_step_order"),
        CheckConstraint("step_order >= 1", name="chk_crs_step_order_pos"),
        CheckConstraint("estimated_duration_minutes >= 0", name="chk_crs_duration_nonneg"),
        Index("ix_crs_org_plan", "organization_id", "continuity_plan_id"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 6. RESILIENCE EXERCISE MODEL (Batch 5)
# ─────────────────────────────────────────────────────────────────────────────

class ResilienceExercise(Base):
    """Empirical DR / Continuity exercise execution, RTO/RPO variance & escalation record."""
    __tablename__ = "resilience_exercises"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    process_id = Column(
        Integer,
        ForeignKey("business_processes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    continuity_plan_id = Column(
        Integer,
        ForeignKey("continuity_plans.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    bia_id = Column(
        Integer,
        ForeignKey("business_impact_analyses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    exercise_code = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    exercise_type = Column(
        Enum(ExerciseTypeEnum),
        nullable=False,
        index=True,
    )
    status = Column(
        Enum(ExerciseStatusEnum),
        nullable=False,
        default=ExerciseStatusEnum.PLANNED,
        index=True,
    )
    scenario_description = Column(Text, nullable=False)
    scope_notes = Column(Text, nullable=True)

    scheduled_start_at = Column(DateTime(timezone=True), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # Immutable BIA Target Snapshots at Exercise Creation
    target_rto_hours_snapshot = Column(Float, nullable=False)
    target_rpo_hours_snapshot = Column(Float, nullable=False)
    target_mtd_hours_snapshot = Column(Float, nullable=False)

    # Empirical Execution Measurements & Server-Computed Variances
    actual_rto_hours = Column(Float, nullable=True)
    actual_rpo_hours = Column(Float, nullable=True)
    rto_variance_hours = Column(Float, nullable=True)
    rpo_variance_hours = Column(Float, nullable=True)

    rto_breached = Column(Boolean, nullable=False, default=False)
    rpo_breached = Column(Boolean, nullable=False, default=False)
    mtd_breached = Column(Boolean, nullable=False, default=False)
    control_deficiency_observed = Column(Boolean, nullable=False, default=False)

    outcome = Column(
        Enum(ExerciseOutcomeEnum),
        nullable=True,
        index=True,
    )
    lessons_learned = Column(Text, nullable=True)
    executive_summary = Column(Text, nullable=True)
    review_notes = Column(Text, nullable=True)
    result_hash_sha256 = Column(String(64), nullable=True, index=True)

    # Actors & Four-Eyes Governance
    planned_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    executed_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reviewed_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Closed-Loop GRC Escalation Linkages
    finding_id = Column(
        Integer,
        ForeignKey("findings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    remediation_plan_id = Column(
        Integer,
        ForeignKey("remediation_plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    risk_id = Column(
        Integer,
        ForeignKey("risks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    triggered_by_incident_id = Column(
        Integer,
        ForeignKey("security_incidents.id", ondelete="SET NULL"),
        nullable=True,
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

    # Relationships
    organization = relationship("Organization")
    process = relationship("BusinessProcess", back_populates="exercises")
    continuity_plan = relationship("ContinuityPlan")
    bia = relationship("BusinessImpactAnalysis")
    planned_by = relationship("User", foreign_keys=[planned_by_user_id])
    executed_by = relationship("User", foreign_keys=[executed_by_user_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_user_id])
    finding = relationship("Finding")
    remediation_plan = relationship("RemediationPlan")
    risk = relationship("Risk")
    triggered_by_incident = relationship("SecurityIncident")
    evidence_links = relationship(
        "ResilienceEvidenceLink",
        back_populates="exercise",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "exercise_code", name="uq_re_org_exercise_code"),
        CheckConstraint("target_rto_hours_snapshot >= 0", name="chk_re_target_rto_nonneg"),
        CheckConstraint("target_rpo_hours_snapshot >= 0", name="chk_re_target_rpo_nonneg"),
        CheckConstraint(
            "target_mtd_hours_snapshot >= target_rto_hours_snapshot",
            name="chk_re_target_mtd_ge_rto",
        ),
        CheckConstraint(
            "actual_rto_hours IS NULL OR actual_rto_hours >= 0",
            name="chk_re_actual_rto_nonneg",
        ),
        CheckConstraint(
            "actual_rpo_hours IS NULL OR actual_rpo_hours >= 0",
            name="chk_re_actual_rpo_nonneg",
        ),
        Index("ix_re_org_process_status", "organization_id", "process_id", "status"),
        Index("ix_re_org_outcome", "organization_id", "outcome"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 7. RESILIENCE EVIDENCE LINK MODEL (Batch 5)
# ─────────────────────────────────────────────────────────────────────────────

class ResilienceEvidenceLink(Base):
    """Cryptographically bound join record linking ContinuityPlan or ResilienceExercise to EvidenceItem."""
    __tablename__ = "resilience_evidence_links"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    continuity_plan_id = Column(
        Integer,
        ForeignKey("continuity_plans.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    exercise_id = Column(
        Integer,
        ForeignKey("resilience_exercises.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    evidence_item_id = Column(
        Integer,
        ForeignKey("evidence_items.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    evidence_type_context = Column(
        Enum(ResilienceEvidenceContextEnum),
        nullable=False,
    )
    evidence_sha256_snapshot = Column(String(64), nullable=False)
    notes = Column(Text, nullable=True)
    linked_by_user_id = Column(
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

    # Relationships
    organization = relationship("Organization")
    continuity_plan = relationship("ContinuityPlan", back_populates="evidence_links")
    exercise = relationship("ResilienceExercise", back_populates="evidence_links")
    evidence_item = relationship("EvidenceItem")
    linked_by = relationship("User", foreign_keys=[linked_by_user_id])

    __table_args__ = (
        CheckConstraint(
            """(
                (CASE WHEN continuity_plan_id IS NOT NULL THEN 1 ELSE 0 END) +
                (CASE WHEN exercise_id IS NOT NULL THEN 1 ELSE 0 END)
            ) = 1""",
            name="chk_resilience_evidence_single_subject",
        ),
        UniqueConstraint(
            "organization_id",
            "continuity_plan_id",
            "evidence_item_id",
            name="uq_rel_org_plan_evidence",
        ),
        UniqueConstraint(
            "organization_id",
            "exercise_id",
            "evidence_item_id",
            name="uq_rel_org_exercise_evidence",
        ),
    )


from sqlalchemy import select as _sa_select
from sqlalchemy.exc import IntegrityError as _SAIntegrityError
from app.models.evidence import EvidenceItem as _EvidenceItem


@event.listens_for(_EvidenceItem, "before_delete")
def _restrict_evidence_item_delete_if_linked_to_resilience(mapper, connection, target):
    rel_table = ResilienceEvidenceLink.__table__
    linked = connection.execute(
        _sa_select(rel_table.c.id).where(rel_table.c.evidence_item_id == target.id).limit(1)
    ).first()
    if linked is not None:
        raise _SAIntegrityError(
            "DELETE FROM evidence_items",
            {"id": target.id},
            Exception(
                "FOREIGN KEY constraint failed: evidence_items.id is referenced by resilience_evidence_links (RESTRICT)"
            ),
        )
