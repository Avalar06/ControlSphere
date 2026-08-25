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


class ExceptionTypeEnum(str, enum.Enum):
    CONTROL_DEVIATION = "CONTROL_DEVIATION"
    POLICY_EXCEPTION = "POLICY_EXCEPTION"
    CONFIGURATION_STANDARD = "CONFIGURATION_STANDARD"
    THIRD_PARTY_VENDOR = "THIRD_PARTY_VENDOR"
    ACCESS_CONTROL = "ACCESS_CONTROL"
    OTHER = "OTHER"


class ExceptionStatusEnum(str, enum.Enum):
    REQUESTED = "REQUESTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"
    CLOSED = "CLOSED"


class SecurityException(Base):
    __tablename__ = "security_exceptions"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)

    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    justification = Column(Text, nullable=False)  # Business / technical reason
    exception_type = Column(Enum(ExceptionTypeEnum), default=ExceptionTypeEnum.CONTROL_DEVIATION, nullable=False, index=True)
    status = Column(Enum(ExceptionStatusEnum), default=ExceptionStatusEnum.REQUESTED, nullable=False, index=True)

    # Ownership & Reviewers
    requested_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    reviewer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Validity Window & Review Dates
    requested_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    effective_date = Column(Date, nullable=True, index=True)
    expiry_date = Column(Date, nullable=False, index=True)
    review_date = Column(Date, nullable=True, index=True)

    # Risk & Evaluation
    residual_risk_level = Column(String(20), default="MODERATE", nullable=False)  # LOW, MODERATE, HIGH, CRITICAL
    approval_notes = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    closure_notes = Column(Text, nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    closed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Direct Primary Associations
    linked_organization_control_id = Column(Integer, ForeignKey("organization_controls.id", ondelete="SET NULL"), nullable=True, index=True)
    linked_policy_id = Column(Integer, ForeignKey("policies.id", ondelete="SET NULL"), nullable=True, index=True)
    linked_finding_id = Column(Integer, ForeignKey("findings.id", ondelete="SET NULL"), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    organization = relationship("Organization")
    requested_by = relationship("User", foreign_keys=[requested_by_id])
    owner = relationship("User", foreign_keys=[owner_id])
    reviewer = relationship("User", foreign_keys=[reviewer_id])
    closed_by = relationship("User", foreign_keys=[closed_by_id])

    linked_control = relationship("OrganizationControl", foreign_keys=[linked_organization_control_id])
    linked_policy = relationship("Policy", foreign_keys=[linked_policy_id])
    linked_finding = relationship("Finding", foreign_keys=[linked_finding_id])

    compensating_controls = relationship("ExceptionCompensatingControl", back_populates="exception", cascade="all, delete-orphan")


class ExceptionCompensatingControl(Base):
    __tablename__ = "exception_compensating_controls"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    exception_id = Column(Integer, ForeignKey("security_exceptions.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_control_id = Column(Integer, ForeignKey("organization_controls.id", ondelete="CASCADE"), nullable=False, index=True)
    implementation_notes = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("exception_id", "organization_control_id", name="uq_exception_control"),
    )

    organization = relationship("Organization")
    exception = relationship("SecurityException", back_populates="compensating_controls")
    organization_control = relationship("OrganizationControl")
    created_by = relationship("User", foreign_keys=[created_by_id])
