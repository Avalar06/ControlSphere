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


# ─── BATCH 6: EXTENDED TPRM GOVERNANCE ENUMS ─────────────────────────────────

class VendorContractTypeEnum(str, enum.Enum):
    MSA = "MSA"
    DPA = "DPA"
    SLA_ADDENDUM = "SLA_ADDENDUM"
    SOW = "SOW"
    NDA = "NDA"
    BAA = "BAA"
    DORA_ICT_CONTRACT = "DORA_ICT_CONTRACT"


class VendorContractStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    TERMINATED = "TERMINATED"
    SUPERSEDED = "SUPERSEDED"


class VendorSubprocessorStatusEnum(str, enum.Enum):
    REGISTERED = "REGISTERED"
    UNDER_REVIEW = "UNDER_REVIEW"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    SUSPENDED = "SUSPENDED"
    REJECTED = "REJECTED"
    TERMINATED = "TERMINATED"


class VendorSlaMetricTypeEnum(str, enum.Enum):
    AVAILABILITY_PCT = "AVAILABILITY_PCT"
    AVAILABILITY_UPTIME = "AVAILABILITY_UPTIME"
    INCIDENT_NOTIFICATION_HOURS = "INCIDENT_NOTIFICATION_HOURS"
    VULN_REMEDIATION_DAYS = "VULN_REMEDIATION_DAYS"
    CRITICAL_VULN_REMEDIATION_DAYS = "CRITICAL_VULN_REMEDIATION_DAYS"
    HIGH_VULN_REMEDIATION_DAYS = "HIGH_VULN_REMEDIATION_DAYS"
    RTO_HOURS = "RTO_HOURS"
    RPO_HOURS = "RPO_HOURS"
    AUDIT_REPORT_DELIVERY_DAYS = "AUDIT_REPORT_DELIVERY_DAYS"
    EVIDENCE_ATTESTATION_DAYS = "EVIDENCE_ATTESTATION_DAYS"
    DATA_DELETION_DAYS = "DATA_DELETION_DAYS"
    DATA_DELETION_CERTIFICATION_DAYS = "DATA_DELETION_CERTIFICATION_DAYS"
    CUSTOM_METRIC = "CUSTOM_METRIC"


class VendorSlaComparisonOperatorEnum(str, enum.Enum):
    GTE = "GTE"
    LTE = "LTE"
    EQ = "EQ"


SlaMetricTypeEnum = VendorSlaMetricTypeEnum
SlaComparisonOperatorEnum = VendorSlaComparisonOperatorEnum


class VendorSlaObligationStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    EXPIRED = "EXPIRED"
    RETIRED = "RETIRED"
    TERMINATED = "TERMINATED"


class VendorSlaBreachSeverityEnum(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    MAJOR = "MAJOR"
    MINOR = "MINOR"


class VendorSlaBreachStatusEnum(str, enum.Enum):
    OPEN = "OPEN"
    UNDER_INVESTIGATION = "UNDER_INVESTIGATION"
    ESCALATED = "ESCALATED"
    ESCALATED_TO_FINDING = "ESCALATED_TO_FINDING"
    WAIVED = "WAIVED"
    WAIVED_BY_EXCEPTION = "WAIVED_BY_EXCEPTION"
    RESOLVED = "RESOLVED"
    VERIFIED_CLOSED = "VERIFIED_CLOSED"


class VendorOffboardingStatusEnum(str, enum.Enum):
    INITIATED = "INITIATED"
    IN_PROGRESS = "IN_PROGRESS"
    PENDING_SIGNOFF = "PENDING_SIGNOFF"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class VendorOffboardingTargetStatusEnum(str, enum.Enum):
    OFFBOARDED = "OFFBOARDED"
    TERMINATED = "TERMINATED"


class VendorOffboardingReasonEnum(str, enum.Enum):
    CONTRACT_EXPIRATION = "CONTRACT_EXPIRATION"
    STRATEGIC_REPLACEMENT = "STRATEGIC_REPLACEMENT"
    SLA_BREACH_TERMINATION = "SLA_BREACH_TERMINATION"
    SECURITY_INCIDENT = "SECURITY_INCIDENT"
    INSOLVENCY_M_AND_A = "INSOLVENCY_M_AND_A"
    MUTUAL_TERMINATION = "MUTUAL_TERMINATION"


class VendorOffboardingStepTypeEnum(str, enum.Enum):
    ACCESS_REVOCATION = "ACCESS_REVOCATION"
    DATA_DESTRUCTION_OR_RETURN = "DATA_DESTRUCTION_OR_RETURN"
    DATA_RETURN_OR_DESTRUCTION = "DATA_RETURN_OR_DESTRUCTION"
    ENGAGEMENT_TERMINATION = "ENGAGEMENT_TERMINATION"
    SUBPROCESSOR_DISCONNECT = "SUBPROCESSOR_DISCONNECT"
    EVIDENCE_ARCHIVAL = "EVIDENCE_ARCHIVAL"
    FINAL_RISK_ARCHIVE = "FINAL_RISK_ARCHIVE"
    FINANCIAL_CONTRACT_CLOSEOUT = "FINANCIAL_CONTRACT_CLOSEOUT"
    CONTRACT_TERMINATION_NOTICE = "CONTRACT_TERMINATION_NOTICE"


class VendorOffboardingItemStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    WAIVED = "WAIVED"
    WAIVED_BY_EXCEPTION = "WAIVED_BY_EXCEPTION"


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

    # Batch 6 Extended Governance Telemetry Counters
    open_sla_breaches_count = Column(Integer, nullable=False, default=0)
    approved_subprocessors_count = Column(Integer, nullable=False, default=0)
    offboarding_completed_at = Column(DateTime(timezone=True), nullable=True)

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
    contracts = relationship(
        "VendorContract", back_populates="vendor", cascade="all, delete-orphan"
    )
    subprocessors = relationship(
        "VendorSubprocessor",
        foreign_keys="VendorSubprocessor.vendor_id",
        back_populates="vendor",
        cascade="all, delete-orphan",
    )
    sla_obligations = relationship(
        "VendorSlaObligation", back_populates="vendor", cascade="all, delete-orphan"
    )
    sla_breaches = relationship(
        "VendorSlaBreach", back_populates="vendor", cascade="all, delete-orphan"
    )
    offboarding_records = relationship(
        "VendorOffboardingRecord", back_populates="vendor", cascade="all, delete-orphan"
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

    # Batch 6 Closed-Loop Escalation Linkages
    linked_finding_id = Column(
        Integer,
        ForeignKey(
            "findings.id",
            ondelete="SET NULL",
            name="fk_vendor_assessment_items_linked_finding_id_findings",
        ),
        nullable=True,
        index=True,
    )
    linked_remediation_plan_id = Column(
        Integer,
        ForeignKey(
            "remediation_plans.id",
            ondelete="SET NULL",
            name="fk_vendor_assessment_items_linked_remediation_plan_id_remediation_plans",
        ),
        nullable=True,
        index=True,
    )
    linked_risk_id = Column(
        Integer,
        ForeignKey(
            "risks.id",
            ondelete="SET NULL",
            name="fk_vendor_assessment_items_linked_risk_id_risks",
        ),
        nullable=True,
        index=True,
    )
    escalated_by_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
            name="fk_vendor_assessment_items_escalated_by_id_users",
        ),
        nullable=True,
    )
    escalated_at = Column(DateTime(timezone=True), nullable=True)

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
    linked_finding = relationship("Finding", foreign_keys=[linked_finding_id])
    linked_remediation_plan = relationship(
        "RemediationPlan", foreign_keys=[linked_remediation_plan_id]
    )
    linked_risk = relationship("Risk", foreign_keys=[linked_risk_id])
    escalated_by = relationship("User", foreign_keys=[escalated_by_id])


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


# ─── BATCH 6: VENDOR CONTRACT GOVERNANCE ─────────────────────────────────────

class VendorContract(Base):
    """Governed Vendor Contract authority (GDPR Art. 28 DPA & EU DORA Art. 30)."""
    __tablename__ = "vendor_contracts"

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

    contract_code = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    contract_type = Column(
        Enum(VendorContractTypeEnum, name="vendorcontracttypeenum"),
        nullable=False,
        default=VendorContractTypeEnum.MSA,
        index=True,
    )
    status = Column(
        Enum(VendorContractStatusEnum, name="vendorcontractstatusenum"),
        nullable=False,
        default=VendorContractStatusEnum.DRAFT,
        index=True,
    )

    effective_date = Column(DateTime(timezone=True), nullable=False, index=True)
    expiry_date = Column(DateTime(timezone=True), nullable=True, index=True)
    auto_renew = Column(Boolean, nullable=False, default=False)
    notice_period_days = Column(Integer, nullable=False, default=30)

    # Regulatory & Contractual Governance Metadata (GDPR Art. 28 / DORA Art. 30)
    dpa_included = Column(Boolean, nullable=False, default=False)
    right_to_audit_clause = Column(Boolean, nullable=False, default=False)
    subprocessor_authorization_clause = Column(Boolean, nullable=False, default=False)
    exit_strategy_clause = Column(Boolean, nullable=False, default=False)
    incident_notification_hours_clause = Column(Integer, nullable=True)
    governing_jurisdiction = Column(String(120), nullable=True)
    regulatory_mandates_applicable = Column(String(255), nullable=True)

    # Evidence & Tamper-Evident SHA-256 Digest
    evidence_id = Column(
        Integer, ForeignKey("evidence_items.id", ondelete="SET NULL"), nullable=True, index=True
    )
    evidence_sha256_snapshot = Column(String(64), nullable=True)

    # Four-Eyes Governance & Actors
    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    submitted_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    approved_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    approved_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)

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
        UniqueConstraint(
            "organization_id", "vendor_id", "contract_code", name="uq_vendor_contract_org_vendor_code"
        ),
        CheckConstraint(
            "expiry_date IS NULL OR expiry_date > effective_date",
            name="chk_vendor_contract_dates",
        ),
        CheckConstraint(
            "notice_period_days >= 0",
            name="chk_vendor_contract_notice_non_neg",
        ),
        CheckConstraint(
            "approved_by_id IS NULL OR ((created_by_id IS NULL OR approved_by_id != created_by_id) "
            "AND (submitted_by_id IS NULL OR approved_by_id != submitted_by_id))",
            name="chk_vendor_contract_four_eyes",
        ),
    )

    organization = relationship("Organization")
    vendor = relationship("Vendor", back_populates="contracts")
    engagement = relationship("VendorEngagement")
    evidence = relationship("EvidenceItem", foreign_keys=[evidence_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    submitted_by = relationship("User", foreign_keys=[submitted_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])

    @property
    def expiration_date(self):
        return self.expiry_date

    @expiration_date.setter
    def expiration_date(self, value):
        self.expiry_date = value

    @property
    def dpa_signed_at(self):
        return getattr(self, "_dpa_signed_at", self.approved_at if self.dpa_included else None)

    @dpa_signed_at.setter
    def dpa_signed_at(self, value):
        self._dpa_signed_at = value
        if value is not None:
            self.dpa_included = True

    @property
    def data_retention_days(self):
        return getattr(self, "_data_retention_days", None)

    @data_retention_days.setter
    def data_retention_days(self, value):
        self._data_retention_days = value


# ─── BATCH 6: FOURTH-PARTY SUBPROCESSOR GOVERNANCE & LINEAGE ─────────────────

class VendorSubprocessor(Base):
    """Fourth-party subprocessor lineage and concentration risk authority."""
    __tablename__ = "vendor_subprocessors"

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
    subprocessor_vendor_id = Column(
        Integer, ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True, index=True
    )

    subprocessor_code = Column(String(64), nullable=False, index=True)
    subprocessor_name = Column(String(255), nullable=False, index=True)
    subprocessor_domain = Column(String(255), nullable=True, index=True)
    service_function = Column(String(255), nullable=False)
    hosting_region = Column(String(120), nullable=False, default="US-East-1", index=True)
    jurisdiction = Column(String(120), nullable=False, default="United States")

    criticality = Column(
        Enum(BusinessCriticalityEnum), nullable=False, default=BusinessCriticalityEnum.MEDIUM, index=True
    )
    data_classification = Column(
        Enum(DataClassificationEnum), nullable=False, default=DataClassificationEnum.INTERNAL
    )
    pii_access = Column(
        Enum(PiiFinancialAccessEnum), nullable=False, default=PiiFinancialAccessEnum.NONE
    )
    status = Column(
        Enum(VendorSubprocessorStatusEnum, name="vendorsubprocessorstatusenum"),
        nullable=False,
        default=VendorSubprocessorStatusEnum.REGISTERED,
        index=True,
    )

    contractual_flowdown_verified = Column(Boolean, nullable=False, default=False)
    evidence_id = Column(
        Integer, ForeignKey("evidence_items.id", ondelete="SET NULL"), nullable=True, index=True
    )
    evidence_sha256_snapshot = Column(String(64), nullable=True)
    linked_risk_id = Column(
        Integer, ForeignKey("risks.id", ondelete="SET NULL"), nullable=True, index=True
    )

    registered_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    submitted_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    approved_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    approved_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    review_notes = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    suspension_reason = Column(Text, nullable=True)
    termination_reason = Column(Text, nullable=True)

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
        UniqueConstraint(
            "organization_id",
            "vendor_id",
            "subprocessor_code",
            name="uq_vendor_subprocessor_org_vendor_code",
        ),
        CheckConstraint(
            "subprocessor_vendor_id IS NULL OR subprocessor_vendor_id != vendor_id",
            name="chk_subprocessor_no_self_ref",
        ),
        CheckConstraint(
            "approved_by_id IS NULL OR ((registered_by_id IS NULL OR approved_by_id != registered_by_id) "
            "AND (submitted_by_id IS NULL OR approved_by_id != submitted_by_id))",
            name="chk_subprocessor_four_eyes",
        ),
    )

    organization = relationship("Organization")
    vendor = relationship("Vendor", foreign_keys=[vendor_id], back_populates="subprocessors")
    subprocessor_vendor = relationship("Vendor", foreign_keys=[subprocessor_vendor_id])
    engagement = relationship("VendorEngagement")
    evidence = relationship("EvidenceItem", foreign_keys=[evidence_id])
    linked_risk = relationship("Risk", foreign_keys=[linked_risk_id])
    registered_by = relationship("User", foreign_keys=[registered_by_id])
    submitted_by = relationship("User", foreign_keys=[submitted_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])

    @property
    def normalized_fourth_party_name(self) -> str:
        return " ".join((self.subprocessor_name or "").lower().strip().split())

    @normalized_fourth_party_name.setter
    def normalized_fourth_party_name(self, value):
        self._normalized_fourth_party_name = value

    @property
    def linked_fourth_party_vendor_id(self) -> int | None:
        return self.subprocessor_vendor_id

    @linked_fourth_party_vendor_id.setter
    def linked_fourth_party_vendor_id(self, value: int | None):
        self.subprocessor_vendor_id = value


# ─── BATCH 6: CONTRACTUAL SLA OBLIGATIONS & BREACH ASSURANCE ─────────────────

class VendorSlaObligation(Base):
    """Contractual security and operational resilience SLA obligation."""
    __tablename__ = "vendor_sla_obligations"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vendor_id = Column(
        Integer, ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contract_id = Column(
        Integer, ForeignKey("vendor_contracts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    engagement_id = Column(
        Integer, ForeignKey("vendor_engagements.id", ondelete="SET NULL"), nullable=True, index=True
    )
    linked_organization_control_id = Column(
        Integer,
        ForeignKey("organization_controls.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    obligation_code = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    metric_type = Column(
        Enum(VendorSlaMetricTypeEnum, name="vendorslametrictypeenum"),
        nullable=False,
        default=VendorSlaMetricTypeEnum.AVAILABILITY_PCT,
        index=True,
    )
    comparison_operator = Column(
        Enum(VendorSlaComparisonOperatorEnum, name="vendorslacomparisonoperatorenum"),
        nullable=False,
        default=VendorSlaComparisonOperatorEnum.GTE,
    )
    target_value = Column(Float, nullable=False)
    tolerance_value = Column(Float, nullable=True)
    unit = Column(String(32), nullable=False, default="PERCENT")
    measurement_window = Column(String(64), nullable=False, default="MONTHLY")
    measurement_frequency_days = Column(Integer, nullable=False, default=30)
    breach_severity_on_miss = Column(
        Enum(VendorSlaBreachSeverityEnum, name="vendorslabreachseverityenum"),
        nullable=False,
        default=VendorSlaBreachSeverityEnum.HIGH,
    )
    contract_clause_ref = Column(String(120), nullable=True)
    penalty_clause_summary = Column(Text, nullable=True)
    effective_from = Column(DateTime(timezone=True), nullable=True)
    expiry_date = Column(DateTime(timezone=True), nullable=True)

    status = Column(
        Enum(VendorSlaObligationStatusEnum, name="vendorslaobligationstatusenum"),
        nullable=False,
        default=VendorSlaObligationStatusEnum.ACTIVE,
        index=True,
    )

    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
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

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "vendor_id",
            "obligation_code",
            name="uq_vendor_sla_obligation_org_vendor_code",
        ),
        CheckConstraint("target_value >= 0.0", name="chk_sla_obligation_target_non_neg"),
    )

    organization = relationship("Organization")
    vendor = relationship("Vendor", back_populates="sla_obligations")
    engagement = relationship("VendorEngagement")
    contract = relationship("VendorContract")
    linked_organization_control = relationship(
        "OrganizationControl", foreign_keys=[linked_organization_control_id]
    )
    created_by = relationship("User", foreign_keys=[created_by_id])
    breaches = relationship(
        "VendorSlaBreach", back_populates="obligation", cascade="all, delete-orphan"
    )

    @property
    def breach_threshold(self) -> float | None:
        return self.tolerance_value if self.tolerance_value is not None else self.target_value

    @breach_threshold.setter
    def breach_threshold(self, value: float | None):
        self.tolerance_value = value

    @property
    def warning_threshold(self) -> float | None:
        return getattr(self, "_warning_threshold", self.tolerance_value)

    @warning_threshold.setter
    def warning_threshold(self, value: float | None):
        self._warning_threshold = value

    @property
    def rationalized_common_control_id(self) -> int | None:
        return self.linked_organization_control_id

    @rationalized_common_control_id.setter
    def rationalized_common_control_id(self, value: int | None):
        self.linked_organization_control_id = value


class VendorSlaBreach(Base):
    """Empirical SLA violation record with closed-loop Finding/CAPA/Risk escalation."""
    __tablename__ = "vendor_sla_breaches"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vendor_id = Column(
        Integer, ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    obligation_id = Column(
        Integer,
        ForeignKey("vendor_sla_obligations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    breach_code = Column(String(64), nullable=False, index=True)
    period_start = Column(DateTime(timezone=True), nullable=True)
    period_end = Column(DateTime(timezone=True), nullable=True)
    occurred_at = Column(DateTime(timezone=True), nullable=False, index=True)
    reported_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    target_value_snapshot = Column(Float, nullable=False)
    tolerance_value_snapshot = Column(Float, nullable=True)
    observed_value = Column(Float, nullable=False)
    variance_magnitude = Column(Float, nullable=False, default=0.0)
    service_credit_amount = Column(Float, nullable=True)
    comparison_operator_snapshot = Column(
        Enum(VendorSlaComparisonOperatorEnum, name="vendorslacomparisonoperatorenum"),
        nullable=False,
        default=VendorSlaComparisonOperatorEnum.GTE,
    )

    severity = Column(
        Enum(VendorSlaBreachSeverityEnum, name="vendorslabreachseverityenum"),
        nullable=False,
        default=VendorSlaBreachSeverityEnum.HIGH,
        index=True,
    )
    status = Column(
        Enum(VendorSlaBreachStatusEnum, name="vendorslabreachstatusenum"),
        nullable=False,
        default=VendorSlaBreachStatusEnum.OPEN,
        index=True,
    )

    root_cause_summary = Column(Text, nullable=True)
    resolution_notes = Column(Text, nullable=True)

    evidence_id = Column(
        Integer, ForeignKey("evidence_items.id", ondelete="SET NULL"), nullable=True, index=True
    )
    evidence_sha256_snapshot = Column(String(64), nullable=True)

    # Canonical Closed-Loop Linkages
    linked_finding_id = Column(
        Integer, ForeignKey("findings.id", ondelete="SET NULL"), nullable=True, index=True
    )
    linked_remediation_plan_id = Column(
        Integer, ForeignKey("remediation_plans.id", ondelete="SET NULL"), nullable=True, index=True
    )
    linked_risk_id = Column(
        Integer, ForeignKey("risks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    linked_exception_id = Column(
        Integer,
        ForeignKey("security_exceptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Actor Auditability (Four-Eyes Waiver & Closure)
    reported_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    resolved_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    waived_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    waived_at = Column(DateTime(timezone=True), nullable=True)
    waiver_reason = Column(Text, nullable=True)
    closed_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    closed_at = Column(DateTime(timezone=True), nullable=True)
    closure_notes = Column(Text, nullable=True)

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
        UniqueConstraint(
            "organization_id",
            "vendor_id",
            "breach_code",
            name="uq_vendor_sla_breach_org_vendor_code",
        ),
        CheckConstraint(
            "waived_by_id IS NULL OR reported_by_id IS NULL OR waived_by_id != reported_by_id",
            name="chk_sla_breach_waiver_four_eyes",
        ),
        CheckConstraint(
            "closed_by_id IS NULL OR ((reported_by_id IS NULL OR closed_by_id != reported_by_id) "
            "AND (resolved_by_id IS NULL OR closed_by_id != resolved_by_id))",
            name="chk_sla_breach_close_four_eyes",
        ),
    )

    @property
    def recorded_by_id(self) -> int | None:
        return self.reported_by_id

    @recorded_by_id.setter
    def recorded_by_id(self, value: int | None):
        self.reported_by_id = value

    @property
    def recorded_at(self):
        return self.reported_at

    @recorded_at.setter
    def recorded_at(self, value):
        self.reported_at = value

    @property
    def sla_obligation_id(self) -> int:
        return self.obligation_id

    @sla_obligation_id.setter
    def sla_obligation_id(self, value: int):
        self.obligation_id = value

    @property
    def breach_period_start(self):
        return self.period_start

    @breach_period_start.setter
    def breach_period_start(self, value):
        self.period_start = value

    @property
    def breach_period_end(self):
        return self.period_end

    @breach_period_end.setter
    def breach_period_end(self, value):
        self.period_end = value

    @property
    def breach_threshold_snapshot(self) -> float | None:
        return (
            self.tolerance_value_snapshot
            if self.tolerance_value_snapshot is not None
            else self.target_value_snapshot
        )

    @breach_threshold_snapshot.setter
    def breach_threshold_snapshot(self, value: float | None):
        self.tolerance_value_snapshot = value

    organization = relationship("Organization")
    vendor = relationship("Vendor", back_populates="sla_breaches")
    obligation = relationship("VendorSlaObligation", back_populates="breaches")
    evidence = relationship("EvidenceItem", foreign_keys=[evidence_id])
    linked_finding = relationship("Finding", foreign_keys=[linked_finding_id])
    linked_remediation_plan = relationship(
        "RemediationPlan", foreign_keys=[linked_remediation_plan_id]
    )
    linked_risk = relationship("Risk", foreign_keys=[linked_risk_id])
    linked_exception = relationship(
        "SecurityException", foreign_keys=[linked_exception_id]
    )
    reported_by = relationship("User", foreign_keys=[reported_by_id])
    resolved_by = relationship("User", foreign_keys=[resolved_by_id])
    waived_by = relationship("User", foreign_keys=[waived_by_id])
    closed_by = relationship("User", foreign_keys=[closed_by_id])


# ─── BATCH 6: GOVERNED VENDOR OFFBOARDING & CHECKLIST VERIFICATION ───────────

class VendorOffboardingRecord(Base):
    """Governed vendor exit and termination workflow with Four-Eyes sign-off."""
    __tablename__ = "vendor_offboarding_records"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vendor_id = Column(
        Integer, ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True
    )

    offboarding_code = Column(String(64), nullable=False, index=True)
    target_vendor_status = Column(
        Enum(VendorOffboardingTargetStatusEnum, name="vendoroffboardingtargetstatusenum"),
        nullable=False,
        default=VendorOffboardingTargetStatusEnum.OFFBOARDED,
    )
    status = Column(
        Enum(VendorOffboardingStatusEnum, name="vendoroffboardingstatusenum"),
        nullable=False,
        default=VendorOffboardingStatusEnum.IN_PROGRESS,
        index=True,
    )

    initiation_reason = Column(Text, nullable=False)
    target_completion_date = Column(DateTime(timezone=True), nullable=True)

    requires_data_destruction_proof = Column(Boolean, nullable=False, default=False)
    data_destruction_evidence_id = Column(
        Integer, ForeignKey("evidence_items.id", ondelete="SET NULL"), nullable=True, index=True
    )

    initiated_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    initiated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    submitted_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    submitted_at = Column(DateTime(timezone=True), nullable=True)

    approved_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    approved_at = Column(DateTime(timezone=True), nullable=True)

    verified_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    verified_at = Column(DateTime(timezone=True), nullable=True)

    cancelled_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    review_notes = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    closure_notes = Column(Text, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    signoff_hash_sha256 = Column(String(64), nullable=True)

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
        UniqueConstraint(
            "organization_id",
            "vendor_id",
            "offboarding_code",
            name="uq_vendor_offboarding_org_vendor_code",
        ),
        CheckConstraint(
            "(verified_by_id IS NULL OR ((initiated_by_id IS NULL OR verified_by_id != initiated_by_id) "
            "AND (submitted_by_id IS NULL OR verified_by_id != submitted_by_id))) "
            "AND (approved_by_id IS NULL OR ((initiated_by_id IS NULL OR approved_by_id != initiated_by_id) "
            "AND (submitted_by_id IS NULL OR approved_by_id != submitted_by_id)))",
            name="chk_offboarding_four_eyes",
        ),
    )

    organization = relationship("Organization")
    vendor = relationship("Vendor", back_populates="offboarding_records")
    data_destruction_evidence = relationship("EvidenceItem", foreign_keys=[data_destruction_evidence_id])
    initiated_by = relationship("User", foreign_keys=[initiated_by_id])
    submitted_by = relationship("User", foreign_keys=[submitted_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    verified_by = relationship("User", foreign_keys=[verified_by_id])
    cancelled_by = relationship("User", foreign_keys=[cancelled_by_id])
    items = relationship(
        "VendorOffboardingItem",
        back_populates="offboarding_record",
        cascade="all, delete-orphan",
        order_by="VendorOffboardingItem.step_number.asc(), VendorOffboardingItem.id.asc()",
    )

    @property
    def rationale(self) -> str:
        return self.initiation_reason

    @rationale.setter
    def rationale(self, value: str):
        self.initiation_reason = value

    @property
    def reason(self) -> str:
        return self.initiation_reason

    @reason.setter
    def reason(self, value: str):
        self.initiation_reason = value

    @property
    def signoff_notes(self) -> str | None:
        return self.closure_notes

    @signoff_notes.setter
    def signoff_notes(self, value: str | None):
        self.closure_notes = value


class VendorOffboardingItem(Base):
    """Ordered mandatory checklist step inside a VendorOffboardingRecord."""
    __tablename__ = "vendor_offboarding_items"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    offboarding_record_id = Column(
        Integer,
        ForeignKey("vendor_offboarding_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    step_number = Column(Integer, primary_key=False, nullable=False, default=1)
    step_key = Column(String(64), nullable=False)
    step_type = Column(
        Enum(VendorOffboardingStepTypeEnum, name="vendoroffboardingsteptypeenum"),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    is_mandatory = Column(Boolean, nullable=False, default=True)
    requires_evidence = Column(Boolean, nullable=False, default=False)
    status = Column(
        Enum(VendorOffboardingItemStatusEnum, name="vendoroffboardingitemstatusenum"),
        nullable=False,
        default=VendorOffboardingItemStatusEnum.PENDING,
        index=True,
    )

    evidence_id = Column(
        Integer, ForeignKey("evidence_items.id", ondelete="SET NULL"), nullable=True, index=True
    )
    evidence_sha256_snapshot = Column(String(64), nullable=True)
    linked_exception_id = Column(
        Integer,
        ForeignKey("security_exceptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    attestation_notes = Column(Text, nullable=True)
    waiver_reason = Column(Text, nullable=True)

    completed_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)
    waived_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    waived_at = Column(DateTime(timezone=True), nullable=True)

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
        UniqueConstraint(
            "offboarding_record_id", "step_key", name="uq_vendor_offboarding_item_step_key"
        ),
    )

    organization = relationship("Organization")
    offboarding_record = relationship("VendorOffboardingRecord", back_populates="items")
    evidence = relationship("EvidenceItem", foreign_keys=[evidence_id])
    linked_exception = relationship("SecurityException", foreign_keys=[linked_exception_id])
    completed_by = relationship("User", foreign_keys=[completed_by_id])
    waived_by = relationship("User", foreign_keys=[waived_by_id])

    @property
    def waiver_justification(self) -> str | None:
        return self.waiver_reason

    @waiver_justification.setter
    def waiver_justification(self, value: str | None):
        self.waiver_reason = value
