import enum
from datetime import datetime, timezone
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

from app.db.base_class import Base


class ControlHealthStatusEnum(str, enum.Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    AT_RISK = "AT_RISK"
    FAILING = "FAILING"


class EvaluationTriggerEnum(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    MANUAL = "MANUAL"
    EVENT_DRIVEN = "EVENT_DRIVEN"


class DriftAlertTypeEnum(str, enum.Enum):
    EVIDENCE_EXPIRED = "EVIDENCE_EXPIRED"
    EVIDENCE_MISSING = "EVIDENCE_MISSING"
    ASSESSMENT_OVERDUE = "ASSESSMENT_OVERDUE"
    CRITICAL_FINDING_SLA_BREACH = "CRITICAL_FINDING_SLA_BREACH"
    EXCEPTION_EXPIRING_SOON = "EXCEPTION_EXPIRING_SOON"
    EXCEPTION_EXPIRED = "EXCEPTION_EXPIRED"
    CONTROL_DEGRADED = "CONTROL_DEGRADED"


class DriftAlertSeverityEnum(str, enum.Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DriftAlertStatusEnum(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class ControlHealthSnapshot(Base):
    """Point-in-time automated health telemetry for an Organization Control."""
    __tablename__ = "control_health_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_control_id = Column(
        Integer, ForeignKey("organization_controls.id", ondelete="CASCADE"), nullable=False, index=True
    )

    health_score = Column(Float, nullable=False, default=100.0)  # 0.0 to 100.0
    health_status = Column(
        Enum(ControlHealthStatusEnum, name="controlhealthstatusenum"),
        nullable=False,
        default=ControlHealthStatusEnum.HEALTHY,
        index=True,
    )

    evidence_freshness_score = Column(Float, nullable=False, default=100.0)
    assessment_currency_score = Column(Float, nullable=False, default=100.0)
    finding_penalty_score = Column(Float, nullable=False, default=0.0)
    exception_penalty_score = Column(Float, nullable=False, default=0.0)

    active_findings_count = Column(Integer, nullable=False, default=0)
    critical_high_findings_count = Column(Integer, nullable=False, default=0)
    active_exceptions_count = Column(Integer, nullable=False, default=0)
    accepted_evidence_count = Column(Integer, nullable=False, default=0)

    days_since_last_evidence = Column(Integer, nullable=True)
    days_since_last_assessment = Column(Integer, nullable=True)

    evaluated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    evaluation_trigger = Column(
        Enum(EvaluationTriggerEnum, name="evaluationtriggerenum"),
        nullable=False,
        default=EvaluationTriggerEnum.MANUAL,
    )

    # Relationships
    organization = relationship("Organization")
    organization_control = relationship("OrganizationControl")


class ComplianceDriftAlert(Base):
    """Actionable alert generated when continuous compliance checks fail."""
    __tablename__ = "compliance_drift_alerts"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_control_id = Column(
        Integer, ForeignKey("organization_controls.id", ondelete="CASCADE"), nullable=False, index=True
    )

    alert_type = Column(
        Enum(DriftAlertTypeEnum, name="driftalerttypeenum"), nullable=False, index=True
    )
    severity = Column(
        Enum(DriftAlertSeverityEnum, name="driftalertseverityenum"), nullable=False, index=True
    )
    status = Column(
        Enum(DriftAlertStatusEnum, name="driftalertstatusenum"),
        nullable=False,
        default=DriftAlertStatusEnum.ACTIVE,
        index=True,
    )

    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    remediation_guidance = Column(Text, nullable=True)

    # Acknowledgement & Resolution
    acknowledged_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    organization = relationship("Organization")
    organization_control = relationship("OrganizationControl")
    acknowledged_by = relationship("User", foreign_keys=[acknowledged_by_id])
    resolved_by = relationship("User", foreign_keys=[resolved_by_id])


class MonitoringSchedule(Base):
    """Tenant configuration for continuous control monitoring evaluation policies."""
    __tablename__ = "monitoring_schedules"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    frequency_hours = Column(Integer, nullable=False, default=24)
    is_enabled = Column(Boolean, nullable=False, default=True)

    # Deterministic SLA & freshness thresholds
    evidence_max_age_days = Column(Integer, nullable=False, default=90)
    assessment_max_age_days = Column(Integer, nullable=False, default=180)
    exception_warning_window_days = Column(Integer, nullable=False, default=14)
    finding_sla_critical_days = Column(Integer, nullable=False, default=15)
    finding_sla_high_days = Column(Integer, nullable=False, default=30)

    last_run_at = Column(DateTime(timezone=True), nullable=True)
    last_run_status = Column(String(50), nullable=True)

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

    # Relationships
    organization = relationship("Organization")
