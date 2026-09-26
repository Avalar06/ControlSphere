from datetime import datetime, timezone, date
import enum
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import relationship
from app.db.base import Base


class UTCDateTime(TypeDecorator):
    """DateTime TypeDecorator ensuring timezone-aware UTC datetime instances across SQLite and PostgreSQL."""
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class PolicyStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class PolicyTypeEnum(str, enum.Enum):
    ACCESS_CONTROL = "ACCESS_CONTROL"
    INFORMATION_SECURITY = "INFORMATION_SECURITY"
    INCIDENT_RESPONSE = "INCIDENT_RESPONSE"
    DATA_PROTECTION = "DATA_PROTECTION"
    RISK_MANAGEMENT = "RISK_MANAGEMENT"
    BUSINESS_CONTINUITY = "BUSINESS_CONTINUITY"
    VENDOR_MANAGEMENT = "VENDOR_MANAGEMENT"
    ACCEPTABLE_USE = "ACCEPTABLE_USE"
    CRYPTOGRAPHY = "CRYPTOGRAPHY"
    CHANGE_MANAGEMENT = "CHANGE_MANAGEMENT"
    OTHER = "OTHER"


class PolicyVersionStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    SUPERSEDED = "SUPERSEDED"
    ARCHIVED = "ARCHIVED"


class PolicyReviewStageEnum(str, enum.Enum):
    LEGAL_REVIEW = "LEGAL_REVIEW"
    SECURITY_REVIEW = "SECURITY_REVIEW"
    EXECUTIVE_APPROVAL = "EXECUTIVE_APPROVAL"


class PolicyReviewStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"


class CampaignTargetTypeEnum(str, enum.Enum):
    ALL_USERS = "ALL_USERS"
    ROLE_BASED = "ROLE_BASED"
    CUSTOM_GROUP = "CUSTOM_GROUP"


class CampaignStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class AttestationRecordStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    ATTESTED = "ATTESTED"
    OVERDUE = "OVERDUE"
    EXEMPTED = "EXEMPTED"


class Policy(Base):
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    policy_type = Column(Enum(PolicyTypeEnum), default=PolicyTypeEnum.INFORMATION_SECURITY, nullable=False, index=True)
    status = Column(Enum(PolicyStatusEnum), default=PolicyStatusEnum.DRAFT, nullable=False, index=True)
    
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    effective_date = Column(Date, nullable=True)
    review_date = Column(Date, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    organization = relationship("Organization")
    owner = relationship("User", foreign_keys=[owner_id])
    versions = relationship("PolicyVersion", back_populates="policy", cascade="all, delete-orphan", order_by="PolicyVersion.version_number.desc()")
    control_mappings = relationship("PolicyControlMapping", back_populates="policy", cascade="all, delete-orphan")
    campaigns = relationship("PolicyAttestationCampaign", back_populates="policy", cascade="all, delete-orphan")


class PolicyVersion(Base):
    __tablename__ = "policy_versions"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    policy_id = Column(Integer, ForeignKey("policies.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)  # 1, 2, 3...
    content = Column(Text, nullable=False)  # Markdown / policy text
    content_hash_sha256 = Column(String(64), nullable=True, index=True)
    change_summary = Column(String(255), nullable=False, default="Initial version")
    status = Column(Enum(PolicyVersionStatusEnum), default=PolicyVersionStatusEnum.DRAFT, nullable=False, index=True)
    effective_date = Column(Date, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("policy_id", "version_number", name="uq_policy_version_number"),
    )

    policy = relationship("Policy", back_populates="versions")
    organization = relationship("Organization")
    created_by = relationship("User", foreign_keys=[created_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    reviews = relationship("PolicyReviewWorkflow", back_populates="version", cascade="all, delete-orphan", order_by="PolicyReviewWorkflow.created_at.desc()")
    campaigns = relationship("PolicyAttestationCampaign", back_populates="version")


class PolicyReviewWorkflow(Base):
    __tablename__ = "policy_review_workflows"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    policy_id = Column(Integer, ForeignKey("policies.id", ondelete="CASCADE"), nullable=False, index=True)
    version_id = Column(Integer, ForeignKey("policy_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_code = Column(String(64), nullable=False)
    review_stage = Column(Enum(PolicyReviewStageEnum), default=PolicyReviewStageEnum.LEGAL_REVIEW, nullable=False)
    status = Column(Enum(PolicyReviewStatusEnum), default=PolicyReviewStatusEnum.PENDING, nullable=False, index=True)
    assigned_reviewer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    review_notes = Column(Text, nullable=True)
    reviewed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=True)

    __table_args__ = (
        UniqueConstraint("organization_id", "workflow_code", name="uq_pol_rev_wf_code"),
        Index("ix_pol_rev_wf_org_ver_status", "organization_id", "version_id", "status"),
    )

    organization = relationship("Organization")
    policy = relationship("Policy")
    version = relationship("PolicyVersion", back_populates="reviews")
    assigned_reviewer = relationship("User", foreign_keys=[assigned_reviewer_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    created_by = relationship("User", foreign_keys=[created_by_id])


class PolicyAttestationCampaign(Base):
    __tablename__ = "policy_attestation_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    campaign_code = Column(String(64), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    policy_id = Column(Integer, ForeignKey("policies.id", ondelete="CASCADE"), nullable=False, index=True)
    version_id = Column(Integer, ForeignKey("policy_versions.id", ondelete="RESTRICT"), nullable=False, index=True)
    policy_version_hash = Column(String(64), nullable=False)
    target_type = Column(Enum(CampaignTargetTypeEnum), default=CampaignTargetTypeEnum.ALL_USERS, nullable=False)
    target_role = Column(String(50), nullable=True)
    due_date = Column(UTCDateTime, nullable=False)
    grace_period_days = Column(Integer, default=0, nullable=False)
    status = Column(Enum(CampaignStatusEnum), default=CampaignStatusEnum.DRAFT, nullable=False, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id", ondelete="SET NULL"), nullable=True)
    total_targeted_count = Column(Integer, default=0, nullable=False)
    completed_count = Column(Integer, default=0, nullable=False)
    overdue_count = Column(Integer, default=0, nullable=False)
    reminder_sent_at = Column(UTCDateTime, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    launched_at = Column(UTCDateTime, nullable=True)
    closed_at = Column(UTCDateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("organization_id", "campaign_code", name="uq_pol_att_camp_code"),
        Index("ix_pol_camp_org_pol_status", "organization_id", "policy_id", "status"),
    )

    organization = relationship("Organization")
    policy = relationship("Policy", back_populates="campaigns")
    version = relationship("PolicyVersion", back_populates="campaigns")
    assessment = relationship("Assessment")
    created_by = relationship("User", foreign_keys=[created_by_id])
    attestation_records = relationship("UserAttestationRecord", back_populates="campaign", cascade="all, delete-orphan")


class UserAttestationRecord(Base):
    __tablename__ = "user_attestation_records"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    campaign_id = Column(Integer, ForeignKey("policy_attestation_campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    policy_id = Column(Integer, ForeignKey("policies.id", ondelete="CASCADE"), nullable=False, index=True)
    version_id = Column(Integer, ForeignKey("policy_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(Enum(AttestationRecordStatusEnum), default=AttestationRecordStatusEnum.PENDING, nullable=False, index=True)
    attested_at = Column(UTCDateTime, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    acknowledgement_text = Column(Text, nullable=True)
    comprehension_passed = Column(Boolean, default=True, nullable=False)
    attestation_receipt_hash = Column(String(64), nullable=True)
    evidence_item_id = Column(Integer, ForeignKey("evidence_items.id", ondelete="SET NULL"), nullable=True)
    exemption_exception_id = Column(Integer, ForeignKey("security_exceptions.id", ondelete="SET NULL"), nullable=True)
    exemption_reason = Column(Text, nullable=True)
    exempted_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    exempted_at = Column(UTCDateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("organization_id", "campaign_id", "user_id", name="uq_camp_user_attestation"),
        Index("ix_user_att_org_camp_status", "organization_id", "campaign_id", "status"),
    )

    organization = relationship("Organization")
    campaign = relationship("PolicyAttestationCampaign", back_populates="attestation_records")
    policy = relationship("Policy")
    version = relationship("PolicyVersion")
    user = relationship("User", foreign_keys=[user_id])
    evidence_item = relationship("EvidenceItem")
    exemption_exception = relationship("SecurityException", foreign_keys=[exemption_exception_id])
    exempted_by = relationship("User", foreign_keys=[exempted_by_id])


class PolicyControlMapping(Base):
    __tablename__ = "policy_control_mappings"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    policy_id = Column(Integer, ForeignKey("policies.id", ondelete="CASCADE"), nullable=False, index=True)
    subcategory_id = Column(Integer, ForeignKey("framework_subcategories.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("organization_id", "policy_id", "subcategory_id", name="uq_org_policy_control_mapping"),
    )

    policy = relationship("Policy", back_populates="control_mappings")
    subcategory = relationship("FrameworkSubcategory", back_populates="policy_mappings")