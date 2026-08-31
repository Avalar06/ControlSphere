from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.ai_governance import (
    AIApprovalStatusEnum,
    AIAutonomyLevelEnum,
    AIDataSensitivityEnum,
    AIHostingTypeEnum,
    AILifecycleStateEnum,
    AIRegulatoryTierEnum,
    AISystemTypeEnum,
)


class AISystemBase(BaseModel):
    system_code: str = Field(..., min_length=2, max_length=64, description="Unique system code, e.g. AI-SYS-001")
    name: str = Field(..., min_length=2, max_length=255, description="AI system name")
    description: Optional[str] = None
    system_type: AISystemTypeEnum
    regulatory_tier: AIRegulatoryTierEnum
    autonomy_level: AIAutonomyLevelEnum = AIAutonomyLevelEnum.HUMAN_IN_THE_LOOP
    data_sensitivity: AIDataSensitivityEnum = AIDataSensitivityEnum.INTERNAL
    hosting_type: AIHostingTypeEnum

    # Technical Telemetry
    foundation_model_name: Optional[str] = Field(None, max_length=255)
    model_version: Optional[str] = Field(None, max_length=64)
    training_data_cutoff: Optional[str] = Field(None, max_length=32)
    parameters_billion: Optional[float] = Field(None, ge=0.0)
    context_window_tokens: Optional[int] = Field(None, ge=0)
    compute_flops_exponent: Optional[float] = Field(None, ge=0.0)

    # Cross-Module Links
    business_process_id: Optional[int] = None
    vendor_id: Optional[int] = None
    remediation_plan_id: Optional[int] = None


class AISystemCreate(AISystemBase):
    pass


class AISystemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    system_type: Optional[AISystemTypeEnum] = None
    regulatory_tier: Optional[AIRegulatoryTierEnum] = None
    autonomy_level: Optional[AIAutonomyLevelEnum] = None
    data_sensitivity: Optional[AIDataSensitivityEnum] = None
    hosting_type: Optional[AIHostingTypeEnum] = None
    foundation_model_name: Optional[str] = Field(None, max_length=255)
    model_version: Optional[str] = Field(None, max_length=64)
    training_data_cutoff: Optional[str] = Field(None, max_length=32)
    parameters_billion: Optional[float] = Field(None, ge=0.0)
    context_window_tokens: Optional[int] = Field(None, ge=0)
    compute_flops_exponent: Optional[float] = Field(None, ge=0.0)
    business_process_id: Optional[int] = None
    vendor_id: Optional[int] = None
    remediation_plan_id: Optional[int] = None


class AISystemStatusUpdate(BaseModel):
    lifecycle_state: AILifecycleStateEnum
    notes: Optional[str] = None


class AIModelCardBase(BaseModel):
    version: str = Field(..., min_length=1, max_length=32, description="Model card version, e.g. 1.0.0")
    intended_use: str = Field(..., min_length=3, description="Operational intended use cases")
    out_of_scope_uses: Optional[str] = None
    bias_mitigation_notes: Optional[str] = None
    training_data_provenance: Optional[str] = None
    synthetic_data_percentage: float = Field(0.0, ge=0.0, le=100.0)

    # Safety & Accuracy Telemetry
    hallucination_rate_percent: float = Field(0.0, ge=0.0, le=100.0)
    prompt_injection_resistance_score: float = Field(100.0, ge=0.0, le=100.0)
    toxicity_filter_efficiency_score: float = Field(100.0, ge=0.0, le=100.0)
    benchmark_eval_dataset: Optional[str] = Field(None, max_length=255)
    benchmark_score: Optional[float] = Field(None, ge=0.0, le=100.0)


class AIModelCardCreate(AIModelCardBase):
    pass


class AIModelCardResponse(AIModelCardBase):
    id: int
    organization_id: int
    ai_system_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AIDeploymentApprovalCreate(BaseModel):
    target_environment: str = Field(..., min_length=2, max_length=32, description="Target env: STAGING or PRODUCTION")
    risk_acceptance_justification: str = Field(..., min_length=5, description="Ethical and risk justification")
    human_oversight_measures: str = Field(..., min_length=5, description="HITL governance controls in place")


class AIDeploymentApprovalReviewRequest(BaseModel):
    decision: str = Field(..., pattern="^(APPROVED|REJECTED)$")
    reviewer_notes: Optional[str] = None


class AIDeploymentApprovalResponse(BaseModel):
    id: int
    organization_id: int
    ai_system_id: int
    requested_by_id: int
    reviewed_by_id: Optional[int] = None
    target_environment: str
    approval_status: AIApprovalStatusEnum
    risk_acceptance_justification: str
    human_oversight_measures: str
    reviewer_notes: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AISystemResponse(AISystemBase):
    id: int
    organization_id: int
    lifecycle_state: AILifecycleStateEnum
    algorithmic_risk_index: float
    eu_compliance_score: float
    is_prohibited_practice: bool
    requires_conformity_assessment: bool
    owner_id: int
    approved_by_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    model_cards: List[AIModelCardResponse] = []
    deployment_approvals: List[AIDeploymentApprovalResponse] = []

    model_config = ConfigDict(from_attributes=True)


class AIIndexCalculateRequest(BaseModel):
    regulatory_tier: AIRegulatoryTierEnum
    autonomy_level: AIAutonomyLevelEnum
    data_sensitivity: AIDataSensitivityEnum
    process_tier: Optional[str] = None
    hallucination_rate_percent: float = Field(0.0, ge=0.0, le=100.0)
    prompt_injection_resistance_score: float = Field(100.0, ge=0.0, le=100.0)


class AIIndexCalculateResponse(BaseModel):
    base_risk: float
    autonomy_multiplier: float
    process_tier_multiplier: float
    safety_penalty: float
    algorithmic_risk_index: float


class AIPostureSummaryResponse(BaseModel):
    total_ai_systems: int
    high_risk_systems: int
    prohibited_systems: int
    production_systems: int
    pending_approvals_count: int
    average_algorithmic_risk_index: float
    tier_distribution: Dict[str, int]
    lifecycle_distribution: Dict[str, int]
