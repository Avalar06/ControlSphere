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


# ─────────────────────────────────────────────────────────────────────────────
# Enums for Phase 21: Regulatory-GRC
# ─────────────────────────────────────────────────────────────────────────────

class RegulatoryAuthorityTypeEnum(str, enum.Enum):
    GOVERNMENT = "GOVERNMENT"
    STANDARDS_BODY = "STANDARDS_BODY"
    INDUSTRY_REGULATOR = "INDUSTRY_REGULATOR"
    LEGAL_COURT = "LEGAL_COURT"
    INTERNATIONAL_AGENCY = "INTERNATIONAL_AGENCY"


class RegulatoryTrustTierEnum(str, enum.Enum):
    OFFICIAL = "OFFICIAL"
    STANDARD = "STANDARD"
    ADVISORY = "ADVISORY"


class RegulatoryEnforceabilityEnum(str, enum.Enum):
    MANDATORY = "MANDATORY"
    VOLUNTARY_STANDARD = "VOLUNTARY_STANDARD"
    GUIDELINE = "GUIDELINE"


class RegulatoryMandateStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    SUPERSEDED = "SUPERSEDED"


class RegulatoryApplicabilityEnum(str, enum.Enum):
    APPLICABLE = "APPLICABLE"
    EXEMPT = "EXEMPT"
    UNDER_EVALUATION = "UNDER_EVALUATION"


class RegulatoryComplianceStatusEnum(str, enum.Enum):
    COMPLIANT = "COMPLIANT"
    PARTIALLY_COMPLIANT = "PARTIALLY_COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class RegulatoryChangeTypeEnum(str, enum.Enum):
    NEW_MANDATE = "NEW_MANDATE"
    AMENDMENT = "AMENDMENT"
    GUIDANCE_UPDATE = "GUIDANCE_UPDATE"
    ENFORCEMENT_DATE_SHIFT = "ENFORCEMENT_DATE_SHIFT"
    REPEAL = "REPEAL"


class RegulatoryChangeSeverityEnum(str, enum.Enum):
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    ADMINISTRATIVE = "ADMINISTRATIVE"


class RegulatoryChangeStatusEnum(str, enum.Enum):
    STAGED = "STAGED"
    VALIDATED = "VALIDATED"
    UNDER_REVIEW = "UNDER_REVIEW"
    REVIEWED = "REVIEWED"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    DISMISSED = "DISMISSED"


class RegulatoryImpactLevelEnum(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NO_IMPACT = "NO_IMPACT"


class RegulatoryImpactStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    SUPERSEDED = "SUPERSEDED"


# ─────────────────────────────────────────────────────────────────────────────
# Models for Phase 21: Regulatory-GRC
# ─────────────────────────────────────────────────────────────────────────────

class RegulatorySource(Base):
    """Authoritative standard setting body or official regulatory authority."""
    __tablename__ = "regulatory_sources"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_code = Column(String(64), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    authority_type = Column(
        Enum(RegulatoryAuthorityTypeEnum, name="regulatoryauthoritytypeenum"),
        nullable=False,
        default=RegulatoryAuthorityTypeEnum.GOVERNMENT,
    )
    jurisdiction = Column(String(100), nullable=False)
    website_url = Column(String(500), nullable=True)
    trust_tier = Column(
        Enum(RegulatoryTrustTierEnum, name="regulatorytrusttierenum"),
        nullable=False,
        default=RegulatoryTrustTierEnum.OFFICIAL,
    )
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

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
        UniqueConstraint("organization_id", "source_code", name="uq_reg_source_org_code"),
    )

    organization = relationship("Organization")
    mandates = relationship("RegulatoryMandate", back_populates="source", cascade="all, delete-orphan")


class RegulatoryMandate(Base):
    """Specific statute, regulation, framework mandate, or legal instrument."""
    __tablename__ = "regulatory_mandates"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_id = Column(
        Integer, ForeignKey("regulatory_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mandate_code = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    short_name = Column(String(100), nullable=False)
    legal_citation = Column(String(255), nullable=True)
    jurisdiction = Column(String(100), nullable=False)
    enforceability_level = Column(
        Enum(RegulatoryEnforceabilityEnum, name="regulatoryenforceabilityenum"),
        nullable=False,
        default=RegulatoryEnforceabilityEnum.MANDATORY,
    )
    status = Column(
        Enum(RegulatoryMandateStatusEnum, name="regulatorymandatestatusenum"),
        nullable=False,
        default=RegulatoryMandateStatusEnum.DRAFT,
    )
    framework_id = Column(
        Integer, ForeignKey("frameworks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    description = Column(Text, nullable=True)
    effective_date = Column(Date, nullable=True)
    sunset_date = Column(Date, nullable=True)
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

    __table_args__ = (
        UniqueConstraint("organization_id", "mandate_code", name="uq_reg_mandate_org_code"),
    )

    organization = relationship("Organization")
    source = relationship("RegulatorySource", back_populates="mandates")
    framework = relationship("Framework")
    created_by = relationship("User", foreign_keys=[created_by_id])
    versions = relationship("RegulatoryVersion", back_populates="mandate", cascade="all, delete-orphan")
    obligations = relationship("RegulatoryObligation", back_populates="mandate", cascade="all, delete-orphan")
    change_events = relationship("RegulatoryChangeEvent", back_populates="mandate", cascade="all, delete-orphan")


class RegulatoryVersion(Base):
    """Immutable publication version of a regulatory mandate."""
    __tablename__ = "regulatory_versions"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mandate_id = Column(
        Integer, ForeignKey("regulatory_mandates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_code = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    published_date = Column(Date, nullable=False)
    effective_date = Column(Date, nullable=False)
    sunset_date = Column(Date, nullable=True)
    content_hash_sha256 = Column(String(64), nullable=False)
    change_summary = Column(Text, nullable=True)
    is_current = Column(Boolean, nullable=False, default=True)

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
        UniqueConstraint("organization_id", "mandate_id", "version_code", name="uq_reg_version_org_mandate_code"),
    )

    organization = relationship("Organization")
    mandate = relationship("RegulatoryMandate", back_populates="versions")


class RegulatoryObligation(Base):
    """Atomic statutory obligation mapped to authoritative organization controls."""
    __tablename__ = "regulatory_obligations"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mandate_id = Column(
        Integer, ForeignKey("regulatory_mandates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_id = Column(
        Integer, ForeignKey("regulatory_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    obligation_code = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    article_reference = Column(String(100), nullable=True)
    applicability = Column(
        Enum(RegulatoryApplicabilityEnum, name="regulatoryapplicabilityenum"),
        nullable=False,
        default=RegulatoryApplicabilityEnum.APPLICABLE,
    )
    organization_control_id = Column(
        Integer, ForeignKey("organization_controls.id", ondelete="SET NULL"), nullable=True, index=True
    )
    compliance_status = Column(
        Enum(RegulatoryComplianceStatusEnum, name="regulatorycompliancestatusenum"),
        nullable=False,
        default=RegulatoryComplianceStatusEnum.NEEDS_REVIEW,
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
        UniqueConstraint("organization_id", "mandate_id", "obligation_code", name="uq_reg_obligation_org_mandate_code"),
    )

    organization = relationship("Organization")
    mandate = relationship("RegulatoryMandate", back_populates="obligations")
    version = relationship("RegulatoryVersion")
    organization_control = relationship("OrganizationControl")


class RegulatoryChangeEvent(Base):
    """Governed regulatory change notification with formal human review lifecycle."""
    __tablename__ = "regulatory_change_events"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mandate_id = Column(
        Integer, ForeignKey("regulatory_mandates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    change_code = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    change_type = Column(
        Enum(RegulatoryChangeTypeEnum, name="regulatorychangetypeenum"),
        nullable=False,
        default=RegulatoryChangeTypeEnum.AMENDMENT,
    )
    severity = Column(
        Enum(RegulatoryChangeSeverityEnum, name="regulatorychangeseverityenum"),
        nullable=False,
        default=RegulatoryChangeSeverityEnum.MAJOR,
    )
    status = Column(
        Enum(RegulatoryChangeStatusEnum, name="regulatorychangestatusenum"),
        nullable=False,
        default=RegulatoryChangeStatusEnum.STAGED,
    )
    official_publication_date = Column(Date, nullable=False)
    enforcement_date = Column(Date, nullable=True)
    source_url = Column(String(500), nullable=True)
    content_hash_sha256 = Column(String(64), nullable=False, index=True)
    raw_summary = Column(Text, nullable=False)
    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)
    dismissal_reason = Column(Text, nullable=True)

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
        UniqueConstraint("organization_id", "change_code", name="uq_reg_change_org_code"),
        UniqueConstraint("organization_id", "content_hash_sha256", name="uq_reg_change_org_hash"),
    )

    organization = relationship("Organization")
    mandate = relationship("RegulatoryMandate", back_populates="change_events")
    created_by = relationship("User", foreign_keys=[created_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    impact_assessments = relationship("RegulatoryImpactAssessment", back_populates="change_event", cascade="all, delete-orphan")


class RegulatoryImpactAssessment(Base):
    """Four-Eyes reviewed impact analysis linking regulatory change to controls and policies."""
    __tablename__ = "regulatory_impact_assessments"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    change_event_id = Column(
        Integer, ForeignKey("regulatory_change_events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assessment_code = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    impact_level = Column(
        Enum(RegulatoryImpactLevelEnum, name="regulatoryimpactlevelenum"),
        nullable=False,
        default=RegulatoryImpactLevelEnum.MEDIUM,
    )
    status = Column(
        Enum(RegulatoryImpactStatusEnum, name="regulatoryimpactstatusenum"),
        nullable=False,
        default=RegulatoryImpactStatusEnum.DRAFT,
    )
    impacted_control_ids = Column(Text, nullable=True)  # JSON string of int IDs
    impacted_policy_ids = Column(Text, nullable=True)   # JSON string of int IDs
    gap_analysis_summary = Column(Text, nullable=False)
    action_plan = Column(Text, nullable=True)

    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False
    )
    reviewed_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at = Column(DateTime(timezone=True), nullable=True)

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
        UniqueConstraint("organization_id", "assessment_code", name="uq_reg_impact_org_code"),
    )

    organization = relationship("Organization")
    change_event = relationship("RegulatoryChangeEvent", back_populates="impact_assessments")
    created_by = relationship("User", foreign_keys=[created_by_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
