from datetime import datetime
import enum
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class DataSensitivityLevel(str, enum.Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED_PII = "RESTRICTED_PII"
    SPECIAL_CATEGORY_SENSITIVE_PHI = "SPECIAL_CATEGORY_SENSITIVE_PHI"


class ProcessingLegalBasis(str, enum.Enum):
    CONSENT = "CONSENT"
    CONTRACT_PERFORMANCE = "CONTRACT_PERFORMANCE"
    LEGAL_OBLIGATION = "LEGAL_OBLIGATION"
    VITAL_INTERESTS = "VITAL_INTERESTS"
    PUBLIC_TASK = "PUBLIC_TASK"
    LEGITIMATE_INTERESTS = "LEGITIMATE_INTERESTS"


class DataSubjectCategory(str, enum.Enum):
    EMPLOYEES = "EMPLOYEES"
    CUSTOMERS = "CUSTOMERS"
    PATIENTS = "PATIENTS"
    STUDENTS = "STUDENTS"
    PROSPECTS = "PROSPECTS"
    VULNERABLE_INDIVIDUALS = "VULNERABLE_INDIVIDUALS"
    CHILDREN = "CHILDREN"
    SUPPLIERS = "SUPPLIERS"


class ProcessingLifecycleState(str, enum.Enum):
    DRAFT = "DRAFT"
    DPO_REVIEW = "DPO_REVIEW"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    ARCHIVED = "ARCHIVED"
    RETIRED = "RETIRED"


class TransferMechanism(str, enum.Enum):
    ADEQUACY_DECISION = "ADEQUACY_DECISION"
    STANDARD_CONTRACTUAL_CLAUSES_SCC = "STANDARD_CONTRACTUAL_CLAUSES_SCC"
    BINDING_CORPORATE_RULES_BCR = "BINDING_CORPORATE_RULES_BCR"
    DEROGATION_EXPLICIT_CONSENT = "DEROGATION_EXPLICIT_CONSENT"
    NONE_INTRA_EEA = "NONE_INTRA_EEA"


class JurisdictionRiskTier(str, enum.Enum):
    ADEQUATE_LOW_RISK = "ADEQUATE_LOW_RISK"
    MODERATE_SAFEGUARDS_REQUIRED = "MODERATE_SAFEGUARDS_REQUIRED"
    HIGH_RISK_SURVEILLANCE = "HIGH_RISK_SURVEILLANCE"
    PROHIBITED_TRANSFERS = "PROHIBITED_TRANSFERS"


class DPIARiskBand(str, enum.Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"
    CRITICAL = "CRITICAL"


class PrivacyApprovalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


class DataAsset(Base):
    __tablename__ = "data_assets"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_code = Column(String(64), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    data_sensitivity_level = Column(
        SAEnum(DataSensitivityLevel),
        nullable=False,
        default=DataSensitivityLevel.INTERNAL,
    )
    data_volume_range = Column(String(64), nullable=False, default="LOW")  # LOW (<10k), MEDIUM (10k-1M), HIGH (>1M)
    storage_type = Column(String(64), nullable=False, default="POSTGRES_DB")
    hosting_jurisdiction = Column(String(64), nullable=False, default="EU_EEA")

    is_encrypted_at_rest = Column(Boolean, nullable=False, default=True)
    is_encrypted_in_transit = Column(Boolean, nullable=False, default=True)
    is_pseudonymized = Column(Boolean, nullable=False, default=False)
    retention_period_months = Column(Integer, nullable=True, default=12)

    # Cross-Module Lineage
    business_process_id = Column(Integer, ForeignKey("business_processes.id", ondelete="SET NULL"), nullable=True, index=True)
    ai_system_id = Column(Integer, ForeignKey("ai_systems.id", ondelete="SET NULL"), nullable=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization = relationship("Organization", foreign_keys=[organization_id])
    business_process = relationship("BusinessProcess", foreign_keys=[business_process_id])
    ai_system = relationship("AISystem", foreign_keys=[ai_system_id])
    vendor = relationship("Vendor", foreign_keys=[vendor_id])
    owner = relationship("User", foreign_keys=[owner_id])

    __table_args__ = (
        UniqueConstraint("organization_id", "asset_code", name="uq_data_asset_org_code"),
    )


class ProcessingActivity(Base):
    __tablename__ = "processing_activities"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    activity_code = Column(String(64), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    purpose_description = Column(Text, nullable=False)

    legal_basis = Column(SAEnum(ProcessingLegalBasis), nullable=False)
    data_subject_categories = Column(Text, nullable=False)  # Comma-separated or JSON string
    personal_data_categories = Column(Text, nullable=False)  # Comma-separated or JSON string

    is_special_category_data = Column(Boolean, nullable=False, default=False)
    is_automated_decision_making = Column(Boolean, nullable=False, default=False)
    is_large_scale_monitoring = Column(Boolean, nullable=False, default=False)
    is_vulnerable_subjects = Column(Boolean, nullable=False, default=False)
    is_cross_border_transfer = Column(Boolean, nullable=False, default=False)

    transfer_mechanism = Column(
        SAEnum(TransferMechanism),
        nullable=False,
        default=TransferMechanism.NONE_INTRA_EEA,
    )
    destination_country = Column(String(64), nullable=True)
    security_measures_summary = Column(Text, nullable=True)

    lifecycle_state = Column(
        SAEnum(ProcessingLifecycleState),
        nullable=False,
        default=ProcessingLifecycleState.DRAFT,
    )
    dpo_approval_status = Column(
        SAEnum(PrivacyApprovalStatus),
        nullable=False,
        default=PrivacyApprovalStatus.PENDING,
    )

    # Cross-Module Lineage
    business_process_id = Column(Integer, ForeignKey("business_processes.id", ondelete="SET NULL"), nullable=True, index=True)
    ai_system_id = Column(Integer, ForeignKey("ai_systems.id", ondelete="SET NULL"), nullable=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True, index=True)
    data_controller_name = Column(String(255), nullable=True)

    # Ownership & DPO Sign-off
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    approved_by_dpo_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization = relationship("Organization", foreign_keys=[organization_id])
    business_process = relationship("BusinessProcess", foreign_keys=[business_process_id])
    ai_system = relationship("AISystem", foreign_keys=[ai_system_id])
    vendor = relationship("Vendor", foreign_keys=[vendor_id])
    owner = relationship("User", foreign_keys=[owner_id])
    approved_by_dpo = relationship("User", foreign_keys=[approved_by_dpo_id])
    dpia_assessments = relationship("DPIAAssessment", back_populates="processing_activity", cascade="all, delete-orphan")
    transfer_assessments = relationship("DataTransferAssessment", back_populates="processing_activity", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("organization_id", "activity_code", name="uq_processing_activity_org_code"),
    )


class DPIAAssessment(Base):
    __tablename__ = "dpia_assessments"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    assessment_code = Column(String(64), nullable=False, index=True)
    processing_activity_id = Column(Integer, ForeignKey("processing_activities.id", ondelete="CASCADE"), nullable=False, index=True)

    # Scoring Components (0.00 - 100.00)
    necessity_proportionality_score = Column(Numeric(5, 2), nullable=False, default=100.00)
    data_subject_rights_score = Column(Numeric(5, 2), nullable=False, default=100.00)
    safeguards_mitigation_score = Column(Numeric(5, 2), nullable=False, default=0.00)

    # Authoritative Calculated Scores
    inherent_risk_score = Column(Numeric(5, 2), nullable=False, default=0.00)
    residual_risk_score = Column(Numeric(5, 2), nullable=False, default=0.00)
    risk_band = Column(SAEnum(DPIARiskBand), nullable=False, default=DPIARiskBand.LOW)

    # High-Risk Flags
    automated_decision_making_risk = Column(Boolean, nullable=False, default=False)
    large_scale_monitoring_risk = Column(Boolean, nullable=False, default=False)
    vulnerable_subjects_risk = Column(Boolean, nullable=False, default=False)

    # DPO Review & Consultation
    dpo_consultation_status = Column(
        SAEnum(PrivacyApprovalStatus),
        nullable=False,
        default=PrivacyApprovalStatus.PENDING,
    )
    dpo_recommendation_notes = Column(Text, nullable=True)
    dpo_reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    dpo_reviewed_at = Column(DateTime(timezone=True), nullable=True)
    prior_consultation_required = Column(Boolean, nullable=False, default=False)

    # Cross-Module CAPA Linkage & Creator
    remediation_plan_id = Column(Integer, ForeignKey("remediation_plans.id", ondelete="SET NULL"), nullable=True, index=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization = relationship("Organization", foreign_keys=[organization_id])
    processing_activity = relationship("ProcessingActivity", back_populates="dpia_assessments", foreign_keys=[processing_activity_id])
    dpo_reviewed_by = relationship("User", foreign_keys=[dpo_reviewed_by_id])
    remediation_plan = relationship("RemediationPlan", foreign_keys=[remediation_plan_id])
    created_by = relationship("User", foreign_keys=[created_by_id])

    __table_args__ = (
        UniqueConstraint("organization_id", "assessment_code", name="uq_dpia_assessment_org_code"),
        CheckConstraint("inherent_risk_score >= 0.00 AND inherent_risk_score <= 100.00", name="chk_dpia_irs_bounds"),
        CheckConstraint("residual_risk_score >= 0.00 AND residual_risk_score <= 100.00", name="chk_dpia_rrs_bounds"),
        CheckConstraint(
            "dpo_reviewed_by_id IS NULL OR created_by_id != dpo_reviewed_by_id",
            name="chk_dpia_approval_sod",
        ),
    )


class DataTransferAssessment(Base):
    __tablename__ = "data_transfer_assessments"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    transfer_code = Column(String(64), nullable=False, index=True)
    processing_activity_id = Column(Integer, ForeignKey("processing_activities.id", ondelete="CASCADE"), nullable=False, index=True)

    source_country = Column(String(64), nullable=False, default="EU_EEA")
    destination_country = Column(String(64), nullable=False)
    destination_jurisdiction_tier = Column(
        SAEnum(JurisdictionRiskTier),
        nullable=False,
        default=JurisdictionRiskTier.MODERATE_SAFEGUARDS_REQUIRED,
    )
    transfer_mechanism = Column(
        SAEnum(TransferMechanism),
        nullable=False,
        default=TransferMechanism.STANDARD_CONTRACTUAL_CLAUSES_SCC,
    )

    supplementary_safeguards_description = Column(Text, nullable=True)
    supplementary_measures_score = Column(Numeric(5, 2), nullable=False, default=0.00)
    government_access_risk_score = Column(Numeric(5, 2), nullable=False, default=50.00)
    legal_remedies_score = Column(Numeric(5, 2), nullable=False, default=50.00)

    # Authoritative Calculated Score
    transfer_risk_index = Column(Numeric(5, 2), nullable=False, default=50.00)

    approval_status = Column(
        SAEnum(PrivacyApprovalStatus),
        nullable=False,
        default=PrivacyApprovalStatus.PENDING,
    )
    requested_by_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    audit_notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization = relationship("Organization", foreign_keys=[organization_id])
    processing_activity = relationship("ProcessingActivity", back_populates="transfer_assessments", foreign_keys=[processing_activity_id])
    requested_by = relationship("User", foreign_keys=[requested_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])

    __table_args__ = (
        UniqueConstraint("organization_id", "transfer_code", name="uq_transfer_assessment_org_code"),
        CheckConstraint("transfer_risk_index >= 0.00 AND transfer_risk_index <= 100.00", name="chk_transfer_tri_bounds"),
        CheckConstraint(
            "approved_by_id IS NULL OR requested_by_id != approved_by_id",
            name="chk_transfer_approval_sod",
        ),
    )
