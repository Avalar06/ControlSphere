from datetime import datetime, timezone
import enum
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from app.db.base import Base


class EvidenceTypeEnum(str, enum.Enum):
    DOCUMENT = "DOCUMENT"
    CONFIGURATION = "CONFIGURATION"
    LOG_EXPORT = "LOG_EXPORT"
    SCREENSHOT = "SCREENSHOT"
    POLICY_DOCUMENT = "POLICY_DOCUMENT"
    AUDIT_REPORT = "AUDIT_REPORT"
    OTHER = "OTHER"


class EvidenceStatusEnum(str, enum.Enum):
    UPLOADED = "UPLOADED"
    UNDER_REVIEW = "UNDER_REVIEW"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


class ReviewDecisionEnum(str, enum.Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"


class EvidenceRequirement(Base):
    __tablename__ = "evidence_requirements"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_control_id = Column(Integer, ForeignKey("organization_controls.id", ondelete="CASCADE"), nullable=False, index=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    evidence_type = Column(Enum(EvidenceTypeEnum), default=EvidenceTypeEnum.DOCUMENT, nullable=False, index=True)
    is_required = Column(Boolean, default=True, nullable=False)
    guidance = Column(Text, nullable=True)

    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    organization = relationship("Organization")
    organization_control = relationship("OrganizationControl", backref="evidence_requirements")
    created_by = relationship("User", foreign_keys=[created_by_id])
    evidence_items = relationship("EvidenceItem", back_populates="requirement", cascade="all, delete-orphan")


class EvidenceItem(Base):
    __tablename__ = "evidence_items"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_control_id = Column(Integer, ForeignKey("organization_controls.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_requirement_id = Column(Integer, ForeignKey("evidence_requirements.id", ondelete="SET NULL"), nullable=True, index=True)

    uploaded_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    file_extension = Column(String(20), nullable=False)
    content_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)  # in bytes
    sha256_hash = Column(String(64), nullable=False, index=True)
    storage_key = Column(String(500), nullable=False)

    status = Column(Enum(EvidenceStatusEnum), default=EvidenceStatusEnum.UPLOADED, nullable=False, index=True)
    superseded_by_id = Column(Integer, ForeignKey("evidence_items.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    organization = relationship("Organization")
    organization_control = relationship("OrganizationControl", backref="evidence_items")
    requirement = relationship("EvidenceRequirement", back_populates="evidence_items")
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id])
    reviews = relationship("EvidenceReview", back_populates="evidence", cascade="all, delete-orphan", order_by="EvidenceReview.reviewed_at.desc()")
    superseded_by = relationship("EvidenceItem", remote_side=[id], foreign_keys=[superseded_by_id])


class EvidenceReview(Base):
    __tablename__ = "evidence_reviews"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_id = Column(Integer, ForeignKey("evidence_items.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    decision = Column(Enum(ReviewDecisionEnum), nullable=False, index=True)
    review_notes = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    organization = relationship("Organization")
    evidence = relationship("EvidenceItem", back_populates="reviews")
    reviewer = relationship("User", foreign_keys=[reviewer_id])