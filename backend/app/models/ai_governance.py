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


class AISystemTypeEnum(str, enum.Enum):
    LLM_APPLICATION = "LLM_APPLICATION"
    AGENTIC_WORKFLOW = "AGENTIC_WORKFLOW"
    EMBEDDED_ML = "EMBEDDED_ML"
    COMPUTER_VISION = "COMPUTER_VISION"
    RECOMMENDER = "RECOMMENDER"
    PREDICTIVE_ANALYTICS = "PREDICTIVE_ANALYTICS"


class AILifecycleStateEnum(str, enum.Enum):
    DEVELOPMENT = "DEVELOPMENT"
    VALIDATION = "VALIDATION"
    ETHICAL_REVIEW = "ETHICAL_REVIEW"
    APPROVED_STAGING = "APPROVED_STAGING"
    PRODUCTION = "PRODUCTION"
    DECOMMISSIONED = "DECOMMISSIONED"
    REJECTED = "REJECTED"


class AIRegulatoryTierEnum(str, enum.Enum):
    PROHIBITED = "PROHIBITED"
    HIGH_RISK = "HIGH_RISK"
    GPAI_SYSTEMIC_RISK = "GPAI_SYSTEMIC_RISK"
    LIMITED_RISK = "LIMITED_RISK"
    MINIMAL_RISK = "MINIMAL_RISK"


class AIAutonomyLevelEnum(str, enum.Enum):
    NO_AUTONOMY = "NO_AUTONOMY"
    HUMAN_IN_THE_LOOP = "HUMAN_IN_THE_LOOP"
    HUMAN_ON_THE_LOOP = "HUMAN_ON_THE_LOOP"
    FULL_AUTONOMY = "FULL_AUTONOMY"


class AIDataSensitivityEnum(str, enum.Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED_PII_PHI = "RESTRICTED_PII_PHI"


class AIHostingTypeEnum(str, enum.Enum):
    CLOUD_THIRD_PARTY = "CLOUD_THIRD_PARTY"
    ON_PREMISE_SELF_HOSTED = "ON_PREMISE_SELF_HOSTED"
    HYBRID_VPC = "HYBRID_VPC"
    EDGE_DEVICE = "EDGE_DEVICE"


class AIApprovalStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"


class AISystem(Base):
    __tablename__ = "ai_systems"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    system_code = Column(String(64), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    system_type = Column(SAEnum(AISystemTypeEnum), nullable=False)
    lifecycle_state = Column(SAEnum(AILifecycleStateEnum), nullable=False, default=AILifecycleStateEnum.DEVELOPMENT)
    regulatory_tier = Column(SAEnum(AIRegulatoryTierEnum), nullable=False)
    autonomy_level = Column(SAEnum(AIAutonomyLevelEnum), nullable=False, default=AIAutonomyLevelEnum.HUMAN_IN_THE_LOOP)
    data_sensitivity = Column(SAEnum(AIDataSensitivityEnum), nullable=False, default=AIDataSensitivityEnum.INTERNAL)
    hosting_type = Column(SAEnum(AIHostingTypeEnum), nullable=False)

    # Technical Telemetry
    foundation_model_name = Column(String(255), nullable=True)
    model_version = Column(String(64), nullable=True)
    training_data_cutoff = Column(String(32), nullable=True)
    parameters_billion = Column(Numeric(8, 2), nullable=True)
    context_window_tokens = Column(Integer, nullable=True)
    compute_flops_exponent = Column(Numeric(5, 2), nullable=True)

    # Authoritative Governance & Risk Scores
    algorithmic_risk_index = Column(Numeric(5, 2), nullable=False, default=0.00)
    eu_compliance_score = Column(Numeric(5, 2), nullable=False, default=0.00)
    is_prohibited_practice = Column(Boolean, nullable=False, default=False)
    requires_conformity_assessment = Column(Boolean, nullable=False, default=False)

    # Cross-Module Lineage
    business_process_id = Column(Integer, ForeignKey("business_processes.id", ondelete="SET NULL"), nullable=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True, index=True)
    remediation_plan_id = Column(Integer, ForeignKey("remediation_plans.id", ondelete="SET NULL"), nullable=True, index=True)

    # Ownership & Audit
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization = relationship("Organization", foreign_keys=[organization_id])
    owner = relationship("User", foreign_keys=[owner_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    business_process = relationship("BusinessProcess", foreign_keys=[business_process_id])
    vendor = relationship("Vendor", foreign_keys=[vendor_id])
    remediation_plan = relationship("RemediationPlan", foreign_keys=[remediation_plan_id])
    model_cards = relationship("AIModelCard", back_populates="ai_system", cascade="all, delete-orphan")
    deployment_approvals = relationship("AIDeploymentApproval", back_populates="ai_system", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("organization_id", "system_code", name="uq_ai_system_org_code"),
        CheckConstraint("algorithmic_risk_index >= 0.00 AND algorithmic_risk_index <= 100.00", name="chk_ai_ari_bounds"),
        CheckConstraint("eu_compliance_score >= 0.00 AND eu_compliance_score <= 100.00", name="chk_ai_eu_score_bounds"),
    )


class AIModelCard(Base):
    __tablename__ = "ai_model_cards"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    ai_system_id = Column(Integer, ForeignKey("ai_systems.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(String(32), nullable=False)

    intended_use = Column(Text, nullable=False)
    out_of_scope_uses = Column(Text, nullable=True)
    bias_mitigation_notes = Column(Text, nullable=True)
    training_data_provenance = Column(Text, nullable=True)
    synthetic_data_percentage = Column(Numeric(5, 2), nullable=False, default=0.00)

    # Safety & Accuracy Telemetry
    hallucination_rate_percent = Column(Numeric(5, 2), nullable=False, default=0.00)
    prompt_injection_resistance_score = Column(Numeric(5, 2), nullable=False, default=100.00)
    toxicity_filter_efficiency_score = Column(Numeric(5, 2), nullable=False, default=100.00)
    benchmark_eval_dataset = Column(String(255), nullable=True)
    benchmark_score = Column(Numeric(5, 2), nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization = relationship("Organization", foreign_keys=[organization_id])
    ai_system = relationship("AISystem", back_populates="model_cards", foreign_keys=[ai_system_id])

    __table_args__ = (
        UniqueConstraint("ai_system_id", "version", name="uq_model_card_system_version"),
        CheckConstraint("synthetic_data_percentage >= 0.00 AND synthetic_data_percentage <= 100.00", name="chk_synthetic_data_bounds"),
        CheckConstraint("hallucination_rate_percent >= 0.00 AND hallucination_rate_percent <= 100.00", name="chk_hallucination_bounds"),
        CheckConstraint("prompt_injection_resistance_score >= 0.00 AND prompt_injection_resistance_score <= 100.00", name="chk_prompt_injection_bounds"),
        CheckConstraint("toxicity_filter_efficiency_score >= 0.00 AND toxicity_filter_efficiency_score <= 100.00", name="chk_toxicity_filter_bounds"),
    )


class AIDeploymentApproval(Base):
    __tablename__ = "ai_deployment_approvals"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    ai_system_id = Column(Integer, ForeignKey("ai_systems.id", ondelete="CASCADE"), nullable=False, index=True)
    requested_by_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    target_environment = Column(String(32), nullable=False)
    approval_status = Column(SAEnum(AIApprovalStatusEnum), nullable=False, default=AIApprovalStatusEnum.PENDING)
    risk_acceptance_justification = Column(Text, nullable=False)
    human_oversight_measures = Column(Text, nullable=False)
    reviewer_notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization = relationship("Organization", foreign_keys=[organization_id])
    ai_system = relationship("AISystem", back_populates="deployment_approvals", foreign_keys=[ai_system_id])
    requested_by = relationship("User", foreign_keys=[requested_by_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])

    __table_args__ = (
        CheckConstraint(
            "reviewed_by_id IS NULL OR requested_by_id != reviewed_by_id",
            name="chk_ai_approval_sod",
        ),
    )
