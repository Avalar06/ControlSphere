from datetime import datetime, timezone
import enum
from sqlalchemy import (
    Boolean,
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
# Enums for Phase 23: Continuous-GRC
# ─────────────────────────────────────────────────────────────────────────────

class ComplianceDriftVectorEnum(str, enum.Enum):
    CCM_HEALTH_DEGRADATION = "CCM_HEALTH_DEGRADATION"
    INTEGRATION_PIPELINE_FAILURE = "INTEGRATION_PIPELINE_FAILURE"
    REGULATORY_CHANGE_EXPOSURE = "REGULATORY_CHANGE_EXPOSURE"
    FINDING_SLA_BREACH = "FINDING_SLA_BREACH"
    HARMONIZED_FRAMEWORK_GAP = "HARMONIZED_FRAMEWORK_GAP"


class ComplianceDriftSeverityEnum(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ComplianceDriftStatusEnum(str, enum.Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    REMEDIATION_TRIGGERED = "REMEDIATION_TRIGGERED"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


# ─────────────────────────────────────────────────────────────────────────────
# Models for Phase 23: Continuous-GRC
# ─────────────────────────────────────────────────────────────────────────────

class ContinuousComplianceProfile(Base):
    """Tenant-level orchestration policy setting continuous assurance thresholds and evaluation cadence."""
    __tablename__ = "continuous_compliance_profiles"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    profile_name = Column(
        String(100), nullable=False, default="Default Enterprise Assurance Profile"
    )
    is_enabled = Column(Boolean, nullable=False, default=True)
    evaluation_cadence_hours = Column(Integer, nullable=False, default=6)
    drift_critical_threshold = Column(Float, nullable=False, default=20.0)
    drift_high_threshold = Column(Float, nullable=False, default=15.0)
    min_control_health_score = Column(Float, nullable=False, default=70.0)
    max_evidence_age_days = Column(Integer, nullable=False, default=90)
    max_open_finding_sla_breach_count = Column(Integer, nullable=False, default=0)
    auto_trigger_capa_on_critical_drift = Column(Boolean, nullable=False, default=True)
    last_evaluated_at = Column(DateTime(timezone=True), nullable=True)
    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    organization = relationship("Organization")
    created_by = relationship("User", foreign_keys=[created_by_id])


class ComplianceDriftRecord(Base):
    """Multi-dimensional enterprise compliance drift detected across the 5 authoritative vectors."""
    __tablename__ = "compliance_drift_records"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_control_id = Column(
        Integer, ForeignKey("organization_controls.id", ondelete="CASCADE"), nullable=True, index=True
    )
    drift_code = Column(String(64), nullable=False, index=True)
    drift_vector = Column(
        Enum(ComplianceDriftVectorEnum, name="compliancedriftvectorenum"),
        nullable=False,
        index=True,
    )
    severity = Column(
        Enum(ComplianceDriftSeverityEnum, name="compliancedriftseverityenum"),
        nullable=False,
        index=True,
    )
    status = Column(
        Enum(ComplianceDriftStatusEnum, name="compliancedriftstatusenum"),
        nullable=False,
        default=ComplianceDriftStatusEnum.OPEN,
        index=True,
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    root_cause_metric = Column(String(255), nullable=False)
    baseline_value = Column(Float, nullable=True)
    observed_value = Column(Float, nullable=True)
    remediation_plan_id = Column(
        Integer, ForeignKey("remediation_plans.id", ondelete="SET NULL"), nullable=True, index=True
    )
    detected_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "drift_code", name="uq_comp_drift_org_code"),
    )

    organization = relationship("Organization")
    organization_control = relationship("OrganizationControl")
    remediation_plan = relationship("RemediationPlan")
    resolved_by = relationship("User", foreign_keys=[resolved_by_id])


class ContinuousAssuranceSnapshot(Base):
    """Immutable point-in-time cryptographic summary of enterprise continuous compliance posture."""
    __tablename__ = "continuous_assurance_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    snapshot_code = Column(String(64), nullable=False, index=True)
    captured_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    overall_assurance_score = Column(Float, nullable=False)
    controls_assurance_score = Column(Float, nullable=False)
    evidence_pipeline_score = Column(Float, nullable=False)
    regulatory_compliance_score = Column(Float, nullable=False)
    remediation_sla_score = Column(Float, nullable=False)
    cloud_identity_posture_score = Column(Float, nullable=False)
    harmonized_frameworks_score = Column(Float, nullable=False)
    active_drift_count = Column(Integer, nullable=False, default=0)
    critical_drift_count = Column(Integer, nullable=False, default=0)
    pillar_breakdown = Column(Text, nullable=False)  # JSON dict string
    framework_compliance_breakdown = Column(Text, nullable=False)  # JSON dict string
    data_hash_sha256 = Column(String(64), nullable=False)
    calculation_version = Column(String(20), nullable=False, default="1.0")
    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "snapshot_code", name="uq_assur_snap_org_code"),
    )

    organization = relationship("Organization")
    created_by = relationship("User", foreign_keys=[created_by_id])
