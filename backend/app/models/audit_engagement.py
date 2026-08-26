from datetime import datetime, timezone, date
import enum
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app.db.base import Base


class AuditTypeEnum(str, enum.Enum):
    INTERNAL = "INTERNAL"
    EXTERNAL = "EXTERNAL"
    REGULATORY = "REGULATORY"
    COMPLIANCE = "COMPLIANCE"
    OPERATIONAL = "OPERATIONAL"
    TECHNICAL = "TECHNICAL"
    THIRD_PARTY = "THIRD_PARTY"


class AuditStatusEnum(str, enum.Enum):
    PLANNED = "PLANNED"
    INITIATED = "INITIATED"
    FIELDWORK = "FIELDWORK"
    REVIEW = "REVIEW"
    REPORTING = "REPORTING"
    COMPLETED = "COMPLETED"
    CLOSED = "CLOSED"


class ProcedureResultEnum(str, enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    PASSED = "PASSED"
    PARTIALLY_PASSED = "PARTIALLY_PASSED"
    FAILED = "FAILED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class AuditOpinionEnum(str, enum.Enum):
    UNISSUED = "UNISSUED"
    UNQUALIFIED = "UNQUALIFIED"
    QUALIFIED = "QUALIFIED"
    ADVERSE = "ADVERSE"
    DISCLAIMER = "DISCLAIMER"


# ─────────────────────────────────────────────────────────────────────────────
# Core Audit Entity
# ─────────────────────────────────────────────────────────────────────────────
class Audit(Base):
    __tablename__ = "audits"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)

    title = Column(String(255), nullable=False, index=True)
    audit_type = Column(Enum(AuditTypeEnum), default=AuditTypeEnum.INTERNAL, nullable=False, index=True)
    audit_reference = Column(String(100), nullable=True, index=True)  # e.g., "AUD-2026-001"

    objective = Column(Text, nullable=False)
    scope_description = Column(Text, nullable=True)
    methodology = Column(Text, nullable=True)
    limitations = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)

    # Framework reference (optional link to a specific framework)
    framework_id = Column(Integer, ForeignKey("frameworks.id", ondelete="SET NULL"), nullable=True, index=True)

    # Lead auditor and team
    lead_auditor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    audit_team_notes = Column(Text, nullable=True)

    # Dates
    planned_start_date = Column(Date, nullable=True, index=True)
    planned_end_date = Column(Date, nullable=True, index=True)
    actual_start_date = Column(Date, nullable=True)
    actual_end_date = Column(Date, nullable=True)

    # Lifecycle
    status = Column(Enum(AuditStatusEnum), default=AuditStatusEnum.PLANNED, nullable=False, index=True)

    # Audit Opinion (human-issued, never AI-generated)
    opinion = Column(Enum(AuditOpinionEnum), default=AuditOpinionEnum.UNISSUED, nullable=False, index=True)
    opinion_issued_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    opinion_issued_at = Column(DateTime(timezone=True), nullable=True)
    opinion_notes = Column(Text, nullable=True)

    # Closure
    closed_at = Column(DateTime(timezone=True), nullable=True)
    closed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    closure_notes = Column(Text, nullable=True)

    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    organization = relationship("Organization")
    framework = relationship("Framework")
    lead_auditor = relationship("User", foreign_keys=[lead_auditor_id])
    opinion_issued_by = relationship("User", foreign_keys=[opinion_issued_by_id])
    closed_by = relationship("User", foreign_keys=[closed_by_id])
    created_by = relationship("User", foreign_keys=[created_by_id])

    scope_controls = relationship("AuditScopeControl", back_populates="audit", cascade="all, delete-orphan")
    procedures = relationship("AuditProcedure", back_populates="audit", cascade="all, delete-orphan", order_by="AuditProcedure.created_at")
    finding_links = relationship("AuditFindingLink", back_populates="audit", cascade="all, delete-orphan")


# ─────────────────────────────────────────────────────────────────────────────
# Audit Scope — which controls are in scope for this audit
# ─────────────────────────────────────────────────────────────────────────────
class AuditScopeControl(Base):
    __tablename__ = "audit_scope_controls"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    audit_id = Column(Integer, ForeignKey("audits.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_control_id = Column(Integer, ForeignKey("organization_controls.id", ondelete="CASCADE"), nullable=False, index=True)
    scope_notes = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("audit_id", "organization_control_id", name="uq_audit_scope_control"),
    )

    organization = relationship("Organization")
    audit = relationship("Audit", back_populates="scope_controls")
    organization_control = relationship("OrganizationControl")
    created_by = relationship("User", foreign_keys=[created_by_id])


# ─────────────────────────────────────────────────────────────────────────────
# Audit Procedure — a test step within an audit
# ─────────────────────────────────────────────────────────────────────────────
class AuditProcedure(Base):
    __tablename__ = "audit_procedures"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    audit_id = Column(Integer, ForeignKey("audits.id", ondelete="CASCADE"), nullable=False, index=True)

    # Optional linkage to a specific control in scope
    organization_control_id = Column(Integer, ForeignKey("organization_controls.id", ondelete="SET NULL"), nullable=True, index=True)

    title = Column(String(255), nullable=False, index=True)
    objective = Column(Text, nullable=True)
    test_steps = Column(Text, nullable=True)
    expected_result = Column(Text, nullable=True)
    actual_result = Column(Text, nullable=True)
    assessment_method = Column(String(100), nullable=True)  # e.g., "Inspection", "Interview", "Observation", "Reperformance"

    # Execution
    result = Column(Enum(ProcedureResultEnum), default=ProcedureResultEnum.NOT_STARTED, nullable=False, index=True)
    execution_notes = Column(Text, nullable=True)
    limitations = Column(Text, nullable=True)

    tester_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    execution_date = Column(Date, nullable=True)

    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    organization = relationship("Organization")
    audit = relationship("Audit", back_populates="procedures")
    organization_control = relationship("OrganizationControl")
    tester = relationship("User", foreign_keys=[tester_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    evidence_links = relationship("AuditProcedureEvidence", back_populates="procedure", cascade="all, delete-orphan")


# ─────────────────────────────────────────────────────────────────────────────
# Audit Procedure Evidence — links EvidenceItem to a procedure (no file dup)
# ─────────────────────────────────────────────────────────────────────────────
class AuditProcedureEvidence(Base):
    __tablename__ = "audit_procedure_evidence"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    procedure_id = Column(Integer, ForeignKey("audit_procedures.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_id = Column(Integer, ForeignKey("evidence_items.id", ondelete="CASCADE"), nullable=False, index=True)
    link_notes = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("procedure_id", "evidence_id", name="uq_audit_procedure_evidence"),
    )

    organization = relationship("Organization")
    procedure = relationship("AuditProcedure", back_populates="evidence_links")
    evidence = relationship("EvidenceItem")
    created_by = relationship("User", foreign_keys=[created_by_id])


# ─────────────────────────────────────────────────────────────────────────────
# Audit Finding Link — links existing Finding to an audit
# ─────────────────────────────────────────────────────────────────────────────
class AuditFindingLink(Base):
    __tablename__ = "audit_finding_links"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    audit_id = Column(Integer, ForeignKey("audits.id", ondelete="CASCADE"), nullable=False, index=True)
    finding_id = Column(Integer, ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True)

    # Which procedure generated/identified this finding (optional traceability)
    source_procedure_id = Column(Integer, ForeignKey("audit_procedures.id", ondelete="SET NULL"), nullable=True)

    link_notes = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("audit_id", "finding_id", name="uq_audit_finding_link"),
    )

    organization = relationship("Organization")
    audit = relationship("Audit", back_populates="finding_links")
    finding = relationship("Finding")
    source_procedure = relationship("AuditProcedure")
    created_by = relationship("User", foreign_keys=[created_by_id])
