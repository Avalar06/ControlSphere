import enum
from datetime import datetime, timezone
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

from app.db.base_class import Base


class VendorStatusEnum(str, enum.Enum):
    PROSPECT = "PROSPECT"
    DUE_DILIGENCE = "DUE_DILIGENCE"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    UNDER_REVIEW = "UNDER_REVIEW"
    OFFBOARDED = "OFFBOARDED"
    TERMINATED = "TERMINATED"


class VendorTierEnum(str, enum.Enum):
    TIER_1_CRITICAL = "TIER_1_CRITICAL"
    TIER_2_SIGNIFICANT = "TIER_2_SIGNIFICANT"
    TIER_3_MODERATE = "TIER_3_MODERATE"
    TIER_4_LOW = "TIER_4_LOW"


class EngagementStatusEnum(str, enum.Enum):
    PROPOSED = "PROPOSED"
    SCOPING = "SCOPING"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    TERMINATED = "TERMINATED"


class BusinessCriticalityEnum(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class DataClassificationEnum(str, enum.Enum):
    RESTRICTED = "RESTRICTED"
    CONFIDENTIAL = "CONFIDENTIAL"
    INTERNAL = "INTERNAL"
    PUBLIC = "PUBLIC"


class HostingModelEnum(str, enum.Enum):
    MULTI_TENANT_SAAS = "MULTI_TENANT_SAAS"
    DEDICATED_CLOUD = "DEDICATED_CLOUD"
    ON_PREMISE = "ON_PREMISE"


class NetworkConnectivityEnum(str, enum.Enum):
    DIRECT_API_VPN_DB = "DIRECT_API_VPN_DB"
    CORPORATE_SSO = "CORPORATE_SSO"
    ISOLATED_NO_CONNECTION = "ISOLATED_NO_CONNECTION"


class PiiFinancialAccessEnum(str, enum.Enum):
    DIRECT_PCI_PII_PHI = "DIRECT_PCI_PII_PHI"
    METADATA_ONLY = "METADATA_ONLY"
    NONE = "NONE"


class VendorAssessmentTypeEnum(str, enum.Enum):
    INITIAL_DUE_DILIGENCE = "INITIAL_DUE_DILIGENCE"
    ANNUAL_REASSESSMENT = "ANNUAL_REASSESSMENT"
    TRIGGERED_BY_INCIDENT = "TRIGGERED_BY_INCIDENT"


class VendorAssessmentStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


class VendorResponseStatusEnum(str, enum.Enum):
    COMPLIANT = "COMPLIANT"
    PARTIALLY_COMPLIANT = "PARTIALLY_COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class VendorDocumentTypeEnum(str, enum.Enum):
    SOC2_TYPE2 = "SOC2_TYPE2"
    ISO27001_CERT = "ISO27001_CERT"
    PENTEST_SUMMARY = "PENTEST_SUMMARY"
    DPA_CONTRACT = "DPA_CONTRACT"
    SIG_QUESTIONNAIRE = "SIG_QUESTIONNAIRE"
    OTHER = "OTHER"


class VendorRiskBandEnum(str, enum.Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vendor_code = Column(String(50), nullable=False, index=True)
    legal_name = Column(String(255), nullable=False)
    trade_name = Column(String(255), nullable=True)
    vendor_status = Column(
        Enum(VendorStatusEnum), nullable=False, default=VendorStatusEnum.PROSPECT
    )

    # Server-Authoritative Inherent & Tier Telemetry
    calculated_inherent_risk = Column(Float, nullable=False, default=0.0)
    calculated_tier = Column(
        Enum(VendorTierEnum), nullable=False, default=VendorTierEnum.TIER_4_LOW
    )

    # Tier Override Governance
    override_tier = Column(Enum(VendorTierEnum), nullable=True)
    tier_override_reason = Column(Text, nullable=True)
    tier_overridden_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    tier_overridden_at = Column(DateTime(timezone=True), nullable=True)

    # Server-Authoritative Residual Risk Telemetry
    residual_risk_score = Column(Float, nullable=False, default=0.0)
    risk_band = Column(
        Enum(VendorRiskBandEnum), nullable=False, default=VendorRiskBandEnum.LOW
    )

    business_owner_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    @property
    def effective_tier(self) -> VendorTierEnum:
        if self.override_tier is not None:
            return self.override_tier
        return self.calculated_tier

    __table_args__ = (
        UniqueConstraint("organization_id", "vendor_code", name="uq_vendor_org_code"),
        CheckConstraint(
            "calculated_inherent_risk >= 0.0 AND calculated_inherent_risk <= 100.0",
            name="chk_vendor_inherent_risk",
        ),
        CheckConstraint(
            "residual_risk_score >= 0.0 AND residual_risk_score <= 100.0",
            name="chk_vendor_residual_risk",
        ),
    )

    # Relationships
    organization = relationship("Organization")
    business_owner = relationship("User", foreign_keys=[business_owner_id])
    tier_overridden_by = relationship("User", foreign_keys=[tier_overridden_by_id])
    engagements = relationship(
        "VendorEngagement", back_populates="vendor", cascade="all, delete-orphan"
    )
    assessments = relationship(
        "VendorAssessment", back_populates="vendor", cascade="all, delete-orphan"
    )
    evidence_links = relationship(
        "VendorEvidenceLink", back_populates="vendor", cascade="all, delete-orphan"
    )


class VendorEngagement(Base):
    __tablename__ = "vendor_engagements"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vendor_id = Column(
        Integer, ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    engagement_code = Column(String(50), nullable=False, index=True)
    engagement_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    status = Column(
        Enum(EngagementStatusEnum), nullable=False, default=EngagementStatusEnum.PROPOSED
    )
    criticality = Column(
        Enum(BusinessCriticalityEnum), nullable=False, default=BusinessCriticalityEnum.MEDIUM
    )
    data_classification = Column(
        Enum(DataClassificationEnum), nullable=False, default=DataClassificationEnum.INTERNAL
    )
    hosting_model = Column(
        Enum(HostingModelEnum), nullable=False, default=HostingModelEnum.MULTI_TENANT_SAAS
    )
    network_connectivity = Column(
        Enum(NetworkConnectivityEnum),
        nullable=False,
        default=NetworkConnectivityEnum.ISOLATED_NO_CONNECTION,
    )
    pii_access = Column(
        Enum(PiiFinancialAccessEnum), nullable=False, default=PiiFinancialAccessEnum.NONE
    )

    calculated_risk_score = Column(Float, nullable=False, default=0.0)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "engagement_code", name="uq_engagement_org_code"),
        CheckConstraint(
            "calculated_risk_score >= 0.0 AND calculated_risk_score <= 100.0",
            name="chk_engagement_risk_score",
        ),
    )

    # Relationships
    vendor = relationship("Vendor", back_populates="engagements")
    organization = relationship("Organization")


class VendorAssessment(Base):
    __tablename__ = "vendor_assessments"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vendor_id = Column(
        Integer, ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    engagement_id = Column(
        Integer, ForeignKey("vendor_engagements.id", ondelete="SET NULL"), nullable=True, index=True
    )
    assessment_code = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    assessment_type = Column(
        Enum(VendorAssessmentTypeEnum),
        nullable=False,
        default=VendorAssessmentTypeEnum.INITIAL_DUE_DILIGENCE,
    )
    status = Column(
        Enum(VendorAssessmentStatusEnum),
        nullable=False,
        default=VendorAssessmentStatusEnum.DRAFT,
    )

    assessor_id = Column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    reviewer_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    calculated_score = Column(Float, nullable=False, default=0.0)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    submitted_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "assessment_code", name="uq_assessment_org_code"),
        CheckConstraint(
            "calculated_score >= 0.0 AND calculated_score <= 100.0",
            name="chk_assessment_score",
        ),
    )

    # Relationships
    vendor = relationship("Vendor", back_populates="assessments")
    engagement = relationship("VendorEngagement")
    assessor = relationship("User", foreign_keys=[assessor_id])
    reviewer = relationship("User", foreign_keys=[reviewer_id])
    items = relationship(
        "VendorAssessmentItem", back_populates="assessment", cascade="all, delete-orphan"
    )


class VendorAssessmentItem(Base):
    __tablename__ = "vendor_assessment_items"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assessment_id = Column(
        Integer, ForeignKey("vendor_assessments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rationalized_common_control_id = Column(
        Integer,
        ForeignKey("rationalized_common_controls.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    question_key = Column(String(100), nullable=False)
    question_text = Column(Text, nullable=False)
    response_status = Column(
        Enum(VendorResponseStatusEnum),
        nullable=False,
        default=VendorResponseStatusEnum.NOT_APPLICABLE,
    )
    weight = Column(Float, nullable=False, default=1.0)
    findings_count = Column(Integer, nullable=False, default=0)
    vendor_response_text = Column(Text, nullable=True)
    assessor_notes = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    assessment = relationship("VendorAssessment", back_populates="items")
    common_control = relationship("RationalizedCommonControl")


class VendorEvidenceLink(Base):
    __tablename__ = "vendor_evidence_links"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vendor_id = Column(
        Integer, ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    evidence_id = Column(
        Integer, ForeignKey("evidence_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_type = Column(
        Enum(VendorDocumentTypeEnum),
        nullable=False,
        default=VendorDocumentTypeEnum.OTHER,
    )
    effective_date = Column(DateTime(timezone=True), nullable=False)
    expiration_date = Column(DateTime(timezone=True), nullable=False)

    is_verified = Column(Boolean, nullable=False, default=False)
    verified_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    verified_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("vendor_id", "evidence_id", name="uq_vendor_evidence_link"),
    )

    # Relationships
    vendor = relationship("Vendor", back_populates="evidence_links")
    evidence = relationship("EvidenceItem")
    verified_by = relationship("User", foreign_keys=[verified_by_id])
