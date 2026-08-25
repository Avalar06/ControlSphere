from datetime import datetime, timezone, date
import enum
from sqlalchemy import (
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


class FindingTypeEnum(str, enum.Enum):
    CONTROL_GAP = "CONTROL_GAP"
    EVIDENCE_GAP = "EVIDENCE_GAP"
    POLICY_GAP = "POLICY_GAP"
    PROCESS_GAP = "PROCESS_GAP"
    TECHNICAL_GAP = "TECHNICAL_GAP"
    OTHER = "OTHER"


class FindingSeverityEnum(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"


class FindingStatusEnum(str, enum.Enum):
    OPEN = "OPEN"
    IN_REMEDIATION = "IN_REMEDIATION"
    PENDING_VALIDATION = "PENDING_VALIDATION"
    RESOLVED = "RESOLVED"
    ACCEPTED_RISK = "ACCEPTED_RISK"
    CLOSED = "CLOSED"


class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_control_id = Column(Integer, ForeignKey("organization_controls.id", ondelete="CASCADE"), nullable=False, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id", ondelete="SET NULL"), nullable=True, index=True)

    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    finding_type = Column(Enum(FindingTypeEnum), default=FindingTypeEnum.CONTROL_GAP, nullable=False, index=True)
    severity = Column(Enum(FindingSeverityEnum), default=FindingSeverityEnum.MEDIUM, nullable=False, index=True)

    # Deterministic Risk Evaluation (1 to 5)
    impact = Column(Integer, default=3, nullable=False)  # 1-5
    likelihood = Column(Integer, default=3, nullable=False)  # 1-5
    risk_score = Column(Integer, default=9, nullable=False, index=True)  # impact * likelihood (1-25)
    risk_band = Column(String(20), default="MODERATE", nullable=False, index=True)  # LOW, MODERATE, HIGH, CRITICAL

    recommendation = Column(Text, nullable=False)
    root_cause = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    due_date = Column(Date, nullable=True, index=True)

    # Remediation Workflow
    status = Column(Enum(FindingStatusEnum), default=FindingStatusEnum.OPEN, nullable=False, index=True)
    remediation_plan = Column(Text, nullable=True)
    remediation_notes = Column(Text, nullable=True)
    resolution = Column(Text, nullable=True)

    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    closed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Formal Risk Acceptance
    risk_acceptance_justification = Column(Text, nullable=True)
    risk_accepted_at = Column(DateTime(timezone=True), nullable=True)
    risk_accepted_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    risk_acceptance_expiry = Column(Date, nullable=True)

    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    organization = relationship("Organization")
    organization_control = relationship("OrganizationControl", backref="findings")
    assessment = relationship("Assessment", back_populates="findings")
    owner = relationship("User", foreign_keys=[owner_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    resolved_by = relationship("User", foreign_keys=[resolved_by_id])
    closed_by = relationship("User", foreign_keys=[closed_by_id])
    risk_accepted_by = relationship("User", foreign_keys=[risk_accepted_by_id])
    evidence_links = relationship("FindingEvidence", back_populates="finding", cascade="all, delete-orphan")


class FindingEvidence(Base):
    __tablename__ = "finding_evidence"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    finding_id = Column(Integer, ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_id = Column(Integer, ForeignKey("evidence_items.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("finding_id", "evidence_id", name="uq_finding_evidence"),
    )

    organization = relationship("Organization")
    finding = relationship("Finding", back_populates="evidence_links")
    evidence = relationship("EvidenceItem")
    created_by = relationship("User", foreign_keys=[created_by_id])
