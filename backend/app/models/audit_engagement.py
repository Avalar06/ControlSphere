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


# ── Batch 1: Fieldwork & Sampling Enums ──────────────────────────────────────
class PBCStatusEnum(str, enum.Enum):
    REQUESTED = "REQUESTED"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class PBCPriorityEnum(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SamplingMethodEnum(str, enum.Enum):
    RANDOM = "RANDOM"
    SYSTEMATIC = "SYSTEMATIC"
    STRATIFIED = "STRATIFIED"


class SampleResultEnum(str, enum.Enum):
    PENDING = "PENDING"
    PASS = "PASS"
    FAIL = "FAIL"
    EXCEPTION = "EXCEPTION"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class WorkpaperStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED_FOR_REVIEW = "SUBMITTED_FOR_REVIEW"
    REVIEWED_APPROVED = "REVIEWED_APPROVED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"


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

    has_sampling = Column(Boolean, default=False, nullable=False)
    workpaper_status = Column(String(50), default="DRAFT", nullable=False)

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
    workpapers = relationship("AuditWorkpaperReview", back_populates="procedure", cascade="all, delete-orphan", order_by="AuditWorkpaperReview.version_number.desc()")
    populations = relationship("AuditSamplePopulation", back_populates="procedure", cascade="all, delete-orphan", order_by="AuditSamplePopulation.version_number.desc()")
    pbc_requests = relationship("AuditPBCRequest", back_populates="procedure")


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


# ─────────────────────────────────────────────────────────────────────────────
# Batch 1 Model 1: Audit PBC Request
# ─────────────────────────────────────────────────────────────────────────────
class AuditPBCRequest(Base):
    __tablename__ = "audit_pbc_requests"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    audit_id = Column(Integer, ForeignKey("audits.id", ondelete="CASCADE"), nullable=False, index=True)
    procedure_id = Column(Integer, ForeignKey("audit_procedures.id", ondelete="SET NULL"), nullable=True, index=True)
    organization_control_id = Column(Integer, ForeignKey("organization_controls.id", ondelete="CASCADE"), nullable=False, index=True)

    request_identifier = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(Enum(PBCStatusEnum), default=PBCStatusEnum.REQUESTED, nullable=False, index=True)
    priority = Column(Enum(PBCPriorityEnum), default=PBCPriorityEnum.MEDIUM, nullable=False)

    assigned_to_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    due_date = Column(Date, nullable=False, index=True)

    # Fulfillment through authoritative Phase 3 EvidenceItem
    fulfilled_evidence_id = Column(Integer, ForeignKey("evidence_items.id", ondelete="SET NULL"), nullable=True, index=True)
    submission_notes = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)

    # Four-Eyes Review
    reviewed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("organization_id", "request_identifier", name="uq_pbc_org_identifier"),
    )

    organization = relationship("Organization")
    audit = relationship("Audit", backref="pbc_requests")
    procedure = relationship("AuditProcedure", back_populates="pbc_requests")
    organization_control = relationship("OrganizationControl")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    fulfilled_evidence = relationship("EvidenceItem", foreign_keys=[fulfilled_evidence_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
    created_by = relationship("User", foreign_keys=[created_by_id])


# ─────────────────────────────────────────────────────────────────────────────
# Batch 1 Model 2: Audit Sample Population (Snapshot)
# ─────────────────────────────────────────────────────────────────────────────
class AuditSamplePopulation(Base):
    __tablename__ = "audit_sample_populations"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    audit_id = Column(Integer, ForeignKey("audits.id", ondelete="CASCADE"), nullable=False, index=True)
    procedure_id = Column(Integer, ForeignKey("audit_procedures.id", ondelete="CASCADE"), nullable=False, index=True)

    population_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    population_source = Column(String(255), nullable=False)
    total_count = Column(Integer, nullable=False)
    version_number = Column(Integer, default=1, nullable=False)

    # Freeze state & canonical digest
    is_frozen = Column(Boolean, default=False, nullable=False, index=True)
    frozen_at = Column(DateTime(timezone=True), nullable=True)
    frozen_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    population_digest_sha256 = Column(String(64), nullable=True)
    population_data_json = Column(Text, nullable=True)

    # Sampling methodology & deterministic seed
    sampling_method = Column(Enum(SamplingMethodEnum), default=SamplingMethodEnum.RANDOM, nullable=False)
    sampling_seed = Column(String(64), nullable=True)
    sample_size = Column(Integer, nullable=False)
    sample_parameters_json = Column(Text, nullable=True)

    samples_generated = Column(Boolean, default=False, nullable=False)
    generated_at = Column(DateTime(timezone=True), nullable=True)

    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("procedure_id", "version_number", name="uq_population_proc_version"),
    )

    organization = relationship("Organization")
    audit = relationship("Audit", backref="sample_populations")
    procedure = relationship("AuditProcedure", back_populates="populations")
    frozen_by = relationship("User", foreign_keys=[frozen_by_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    sample_items = relationship("AuditSampleItem", back_populates="population", cascade="all, delete-orphan", order_by="AuditSampleItem.item_index")


# ─────────────────────────────────────────────────────────────────────────────
# Batch 1 Model 3: Audit Sample Item
# ─────────────────────────────────────────────────────────────────────────────
class AuditSampleItem(Base):
    __tablename__ = "audit_sample_items"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    population_id = Column(Integer, ForeignKey("audit_sample_populations.id", ondelete="CASCADE"), nullable=False, index=True)

    item_index = Column(Integer, nullable=False)  # 1-indexed
    source_record_id = Column(String(255), nullable=False, index=True)
    item_attributes_json = Column(Text, nullable=False)

    # Evaluation
    test_result = Column(Enum(SampleResultEnum), default=SampleResultEnum.PENDING, nullable=False, index=True)
    testing_notes = Column(Text, nullable=True)
    tested_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    tested_at = Column(DateTime(timezone=True), nullable=True)

    # Linkage to Phase 3 Evidence and Phase 4 Finding
    evidence_item_id = Column(Integer, ForeignKey("evidence_items.id", ondelete="SET NULL"), nullable=True)
    deficiency_finding_id = Column(Integer, ForeignKey("findings.id", ondelete="SET NULL"), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("population_id", "item_index", name="uq_sample_pop_item"),
    )

    organization = relationship("Organization")
    population = relationship("AuditSamplePopulation", back_populates="sample_items")
    tested_by = relationship("User", foreign_keys=[tested_by_id])
    evidence_item = relationship("EvidenceItem", foreign_keys=[evidence_item_id])
    deficiency_finding = relationship("Finding", foreign_keys=[deficiency_finding_id])


# ─────────────────────────────────────────────────────────────────────────────
# Batch 1 Model 4: Audit Workpaper Review (Four-Eyes Signoff)
# ─────────────────────────────────────────────────────────────────────────────
class AuditWorkpaperReview(Base):
    __tablename__ = "audit_workpaper_reviews"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    audit_id = Column(Integer, ForeignKey("audits.id", ondelete="CASCADE"), nullable=False, index=True)
    procedure_id = Column(Integer, ForeignKey("audit_procedures.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, default=1, nullable=False)

    status = Column(Enum(WorkpaperStatusEnum), default=WorkpaperStatusEnum.DRAFT, nullable=False, index=True)
    testing_summary = Column(Text, nullable=False)
    conclusion = Column(Text, nullable=False)

    # Four-Eyes Governance Attributions
    prepared_by_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    prepared_at = Column(DateTime(timezone=True), nullable=False)

    reviewed_by_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True, index=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Sealed SHA-256 Digest upon Approval
    workpaper_hash_sha256 = Column(String(64), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("procedure_id", "version_number", name="uq_workpaper_proc_version"),
    )

    organization = relationship("Organization")
    audit = relationship("Audit", backref="workpaper_reviews")
    procedure = relationship("AuditProcedure", back_populates="workpapers")
    prepared_by = relationship("User", foreign_keys=[prepared_by_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
