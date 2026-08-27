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
# Phase 11: Governed Remediation Domain Enums
# ─────────────────────────────────────────────────────────────────────────────

class RemediationSourceTypeEnum(str, enum.Enum):
    FINDING = "FINDING"
    CCM_DRIFT = "CCM_DRIFT"
    SECURITY_INCIDENT = "SECURITY_INCIDENT"
    TPRM_ASSESSMENT = "TPRM_ASSESSMENT"
    AUDIT = "AUDIT"


class RemediationRootCauseClassificationEnum(str, enum.Enum):
    CONTROL_DEFICIENCY = "CONTROL_DEFICIENCY"
    CONFIGURATION_DRIFT = "CONFIGURATION_DRIFT"
    HUMAN_ERROR = "HUMAN_ERROR"
    VENDOR_DEFAULT = "VENDOR_DEFAULT"
    ARCHITECTURAL_GAP = "ARCHITECTURAL_GAP"


class RemediationStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    IN_EXECUTION = "IN_EXECUTION"
    PENDING_VALIDATION = "PENDING_VALIDATION"
    VERIFIED_CLOSED = "VERIFIED_CLOSED"
    CANCELLED = "CANCELLED"


class RemediationSeverityEnum(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class TaskStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class EvidenceVerificationStatusEnum(str, enum.Enum):
    SUBMITTED = "SUBMITTED"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"


class ReTestResultEnum(str, enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"


class SlaStatusEnum(str, enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    ON_TRACK = "ON_TRACK"
    AT_RISK = "AT_RISK"
    BREACHED = "BREACHED"
    COMPLETED_ON_TIME = "COMPLETED_ON_TIME"
    COMPLETED_LATE = "COMPLETED_LATE"


# ─────────────────────────────────────────────────────────────────────────────
# Model 1: RemediationPlan (CAPA Root)
# ─────────────────────────────────────────────────────────────────────────────

class RemediationPlan(Base):
    __tablename__ = "remediation_plans"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan_code = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    problem_statement = Column(Text, nullable=False)
    root_cause_classification = Column(
        Enum(RemediationRootCauseClassificationEnum), nullable=False, index=True
    )
    source_type = Column(Enum(RemediationSourceTypeEnum), nullable=False, index=True)

    # Dedicated Nullable FKs for Authoritative Sources (ON DELETE RESTRICT)
    finding_id = Column(
        Integer, ForeignKey("findings.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    compliance_drift_alert_id = Column(
        Integer,
        ForeignKey("compliance_drift_alerts.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    security_incident_id = Column(
        Integer,
        ForeignKey("security_incidents.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    vendor_assessment_id = Column(
        Integer,
        ForeignKey("vendor_assessments.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    audit_id = Column(
        Integer, ForeignKey("audits.id", ondelete="RESTRICT"), nullable=True, index=True
    )

    severity = Column(
        Enum(RemediationSeverityEnum),
        default=RemediationSeverityEnum.MEDIUM,
        nullable=False,
        index=True,
    )
    status = Column(
        Enum(RemediationStatusEnum),
        default=RemediationStatusEnum.DRAFT,
        nullable=False,
        index=True,
    )

    # Actor Ownership & Lifecycle Governance
    plan_owner_id = Column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    approved_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    approved_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    target_completion_at = Column(DateTime(timezone=True), nullable=True, index=True)

    # Verification & Closure Governance
    verified_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verification_notes = Column(Text, nullable=True)
    cancellation_notes = Column(Text, nullable=True)
    validation_attempts_count = Column(Integer, default=0, nullable=False)

    # Authoritative Calculated Telemetry
    rei_score = Column(Float, nullable=True)
    ttr_hours = Column(Float, nullable=True)
    is_immutable = Column(Boolean, default=False, nullable=False)

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

    # Constraints
    __table_args__ = (
        UniqueConstraint("organization_id", "plan_code", name="uq_remediation_org_plan_code"),
        CheckConstraint(
            """(
                (CASE WHEN finding_id IS NOT NULL THEN 1 ELSE 0 END) +
                (CASE WHEN compliance_drift_alert_id IS NOT NULL THEN 1 ELSE 0 END) +
                (CASE WHEN security_incident_id IS NOT NULL THEN 1 ELSE 0 END) +
                (CASE WHEN vendor_assessment_id IS NOT NULL THEN 1 ELSE 0 END) +
                (CASE WHEN audit_id IS NOT NULL THEN 1 ELSE 0 END)
            ) = 1""",
            name="chk_remediation_single_source",
        ),
        CheckConstraint(
            "validation_attempts_count >= 0", name="chk_remediation_validation_attempts_positive"
        ),
        CheckConstraint(
            "rei_score IS NULL OR (rei_score >= 0.0 AND rei_score <= 100.0)",
            name="chk_remediation_rei_range",
        ),
        CheckConstraint("ttr_hours IS NULL OR ttr_hours >= 0.0", name="chk_remediation_ttr_positive"),
    )

    # Relationships
    organization = relationship("Organization")
    plan_owner = relationship("User", foreign_keys=[plan_owner_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    verified_by = relationship("User", foreign_keys=[verified_by_id])

    finding = relationship("Finding", foreign_keys=[finding_id])
    compliance_drift_alert = relationship(
        "ComplianceDriftAlert", foreign_keys=[compliance_drift_alert_id]
    )
    security_incident = relationship("SecurityIncident", foreign_keys=[security_incident_id])
    vendor_assessment = relationship("VendorAssessment", foreign_keys=[vendor_assessment_id])
    audit = relationship("Audit", foreign_keys=[audit_id])

    tasks = relationship(
        "RemediationTask",
        back_populates="remediation_plan",
        cascade="all, delete-orphan",
        order_by="RemediationTask.task_seq",
    )
    retest_records = relationship(
        "RemediationReTestRecord",
        back_populates="remediation_plan",
        cascade="all, delete-orphan",
        order_by="RemediationReTestRecord.created_at",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Model 2: RemediationTask (Atomic Implementation Step)
# ─────────────────────────────────────────────────────────────────────────────

class RemediationTask(Base):
    __tablename__ = "remediation_tasks"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    remediation_plan_id = Column(
        Integer, ForeignKey("remediation_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_seq = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    assignee_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    due_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(
        Enum(TaskStatusEnum),
        default=TaskStatusEnum.PENDING,
        nullable=False,
        index=True,
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)
    implementation_notes = Column(Text, nullable=True)

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
        UniqueConstraint("remediation_plan_id", "task_seq", name="uq_remediation_task_plan_seq"),
        CheckConstraint("task_seq >= 1", name="chk_remediation_task_seq_positive"),
    )

    # Relationships
    remediation_plan = relationship("RemediationPlan", back_populates="tasks")
    assignee = relationship("User", foreign_keys=[assignee_id])
    evidence_links = relationship(
        "RemediationEvidenceLink",
        back_populates="task",
        cascade="all, delete-orphan",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Model 3: RemediationEvidenceLink (Evidence Binding)
# ─────────────────────────────────────────────────────────────────────────────

class RemediationEvidenceLink(Base):
    __tablename__ = "remediation_evidence_links"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    remediation_task_id = Column(
        Integer, ForeignKey("remediation_tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    evidence_id = Column(
        Integer, ForeignKey("evidence_items.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    verification_status = Column(
        Enum(EvidenceVerificationStatusEnum),
        default=EvidenceVerificationStatusEnum.SUBMITTED,
        nullable=False,
    )
    notes = Column(Text, nullable=True)

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
        UniqueConstraint("remediation_task_id", "evidence_id", name="uq_remediation_task_evidence"),
    )

    # Relationships
    task = relationship("RemediationTask", back_populates="evidence_links")
    evidence = relationship("EvidenceItem", foreign_keys=[evidence_id])


# ─────────────────────────────────────────────────────────────────────────────
# Model 4: RemediationReTestRecord (Empirical Validation)
# ─────────────────────────────────────────────────────────────────────────────

class RemediationReTestRecord(Base):
    __tablename__ = "remediation_retest_records"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    remediation_plan_id = Column(
        Integer, ForeignKey("remediation_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    test_executed_at = Column(DateTime(timezone=True), nullable=False)
    tester_id = Column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    test_result = Column(Enum(ReTestResultEnum), nullable=False, index=True)
    metric_observed_value = Column(Float, nullable=True)
    evidence_id = Column(
        Integer, ForeignKey("evidence_items.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    validation_narrative = Column(Text, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    remediation_plan = relationship("RemediationPlan", back_populates="retest_records")
    tester = relationship("User", foreign_keys=[tester_id])
    evidence = relationship("EvidenceItem", foreign_keys=[evidence_id])
