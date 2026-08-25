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


class RiskCategoryEnum(str, enum.Enum):
    CYBERSECURITY = "CYBERSECURITY"
    COMPLIANCE = "COMPLIANCE"
    OPERATIONAL = "OPERATIONAL"
    FINANCIAL = "FINANCIAL"
    STRATEGIC = "STRATEGIC"
    REPUTATIONAL = "REPUTATIONAL"
    THIRD_PARTY = "THIRD_PARTY"
    LEGAL = "LEGAL"


class RiskSourceEnum(str, enum.Enum):
    INTERNAL_AUDIT = "INTERNAL_AUDIT"
    EXTERNAL_AUDIT = "EXTERNAL_AUDIT"
    THREAT_INTELLIGENCE = "THREAT_INTELLIGENCE"
    VULNERABILITY_ASSESSMENT = "VULNERABILITY_ASSESSMENT"
    INCIDENT = "INCIDENT"
    VENDOR_ASSESSMENT = "VENDOR_ASSESSMENT"
    REGULATORY_CHANGE = "REGULATORY_CHANGE"
    BUSINESS_OPERATION = "BUSINESS_OPERATION"


class RiskStatusEnum(str, enum.Enum):
    IDENTIFIED = "IDENTIFIED"
    ASSESSED = "ASSESSED"
    TREATMENT_PLANNED = "TREATMENT_PLANNED"
    MITIGATING = "MITIGATING"
    MONITORING = "MONITORING"
    ACCEPTED = "ACCEPTED"
    CLOSED = "CLOSED"


class RiskTreatmentStrategyEnum(str, enum.Enum):
    MITIGATE = "MITIGATE"
    TRANSFER = "TRANSFER"
    AVOID = "AVOID"
    ACCEPT = "ACCEPT"
    NOT_SPECIFIED = "NOT_SPECIFIED"


class Risk(Base):
    __tablename__ = "risks"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)

    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    risk_category = Column(Enum(RiskCategoryEnum), default=RiskCategoryEnum.CYBERSECURITY, nullable=False, index=True)
    risk_source = Column(Enum(RiskSourceEnum), default=RiskSourceEnum.INTERNAL_AUDIT, nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Inherent Risk Evaluation (1-5)
    inherent_impact = Column(Integer, default=3, nullable=False)  # 1-5
    inherent_likelihood = Column(Integer, default=3, nullable=False)  # 1-5
    inherent_score = Column(Integer, default=9, nullable=False, index=True)  # 1-25
    inherent_band = Column(String(20), default="MODERATE", nullable=False, index=True)  # LOW, MODERATE, HIGH, CRITICAL

    # Residual Risk Evaluation (1-5, after controls/treatments)
    residual_impact = Column(Integer, nullable=True)  # 1-5
    residual_likelihood = Column(Integer, nullable=True)  # 1-5
    residual_score = Column(Integer, nullable=True, index=True)  # 1-25
    residual_band = Column(String(20), nullable=True, index=True)  # LOW, MODERATE, HIGH, CRITICAL

    # Risk Appetite Alignment
    target_risk_band = Column(String(20), default="MODERATE", nullable=False)  # LOW, MODERATE, HIGH
    appetite_status = Column(String(20), default="WITHIN_APPETITE", nullable=False, index=True)  # WITHIN_APPETITE, NEAR_LIMIT, ABOVE_APPETITE

    # Lifecycle & Treatment
    status = Column(Enum(RiskStatusEnum), default=RiskStatusEnum.IDENTIFIED, nullable=False, index=True)
    treatment_strategy = Column(Enum(RiskTreatmentStrategyEnum), default=RiskTreatmentStrategyEnum.NOT_SPECIFIED, nullable=False, index=True)
    treatment_plan = Column(Text, nullable=True)
    treatment_owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    treatment_due_date = Column(Date, nullable=True, index=True)
    review_date = Column(Date, nullable=True, index=True)

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
    owner = relationship("User", foreign_keys=[owner_id])
    treatment_owner = relationship("User", foreign_keys=[treatment_owner_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    risk_accepted_by = relationship("User", foreign_keys=[risk_accepted_by_id])

    control_links = relationship("RiskControlLink", back_populates="risk", cascade="all, delete-orphan")
    finding_links = relationship("RiskFindingLink", back_populates="risk", cascade="all, delete-orphan")


class RiskControlLink(Base):
    __tablename__ = "risk_control_links"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    risk_id = Column(Integer, ForeignKey("risks.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_control_id = Column(Integer, ForeignKey("organization_controls.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("risk_id", "organization_control_id", name="uq_risk_control_link"),
    )

    organization = relationship("Organization")
    risk = relationship("Risk", back_populates="control_links")
    organization_control = relationship("OrganizationControl")
    created_by = relationship("User", foreign_keys=[created_by_id])


class RiskFindingLink(Base):
    __tablename__ = "risk_finding_links"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    risk_id = Column(Integer, ForeignKey("risks.id", ondelete="CASCADE"), nullable=False, index=True)
    finding_id = Column(Integer, ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("risk_id", "finding_id", name="uq_risk_finding_link"),
    )

    organization = relationship("Organization")
    risk = relationship("Risk", back_populates="finding_links")
    finding = relationship("Finding")
    created_by = relationship("User", foreign_keys=[created_by_id])
