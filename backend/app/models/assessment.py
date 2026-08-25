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


class AssessmentMethodEnum(str, enum.Enum):
    EXAMINATION = "EXAMINATION"
    INTERVIEW = "INTERVIEW"
    TESTING = "TESTING"
    AUTOMATED_VERIFICATION = "AUTOMATED_VERIFICATION"
    COMBINED = "COMBINED"


class AssessmentStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    SUPERSEDED = "SUPERSEDED"


class AssessmentConclusionEnum(str, enum.Enum):
    EFFECTIVE = "EFFECTIVE"
    PARTIALLY_EFFECTIVE = "PARTIALLY_EFFECTIVE"
    INEFFECTIVE = "INEFFECTIVE"
    NOT_ASSESSED = "NOT_ASSESSED"


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_control_id = Column(Integer, ForeignKey("organization_controls.id", ondelete="CASCADE"), nullable=False, index=True)
    assessor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    assessment_method = Column(Enum(AssessmentMethodEnum), default=AssessmentMethodEnum.EXAMINATION, nullable=False)
    assessment_scope = Column(Text, nullable=True)
    assessment_date = Column(Date, default=date.today, nullable=False)

    status = Column(Enum(AssessmentStatusEnum), default=AssessmentStatusEnum.DRAFT, nullable=False, index=True)
    conclusion = Column(Enum(AssessmentConclusionEnum), default=AssessmentConclusionEnum.NOT_ASSESSED, nullable=False, index=True)

    summary = Column(Text, nullable=True)
    limitations = Column(Text, nullable=True)

    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    organization = relationship("Organization")
    organization_control = relationship("OrganizationControl", backref="assessments")
    assessor = relationship("User", foreign_keys=[assessor_id])
    evidence_links = relationship("AssessmentEvidence", back_populates="assessment", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="assessment")


class AssessmentEvidence(Base):
    __tablename__ = "assessment_evidence"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_id = Column(Integer, ForeignKey("evidence_items.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("assessment_id", "evidence_id", name="uq_assessment_evidence"),
    )

    organization = relationship("Organization")
    assessment = relationship("Assessment", back_populates="evidence_links")
    evidence = relationship("EvidenceItem")
    created_by = relationship("User", foreign_keys=[created_by_id])
