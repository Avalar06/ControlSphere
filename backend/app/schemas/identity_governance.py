from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.identity_governance import (
    AssignmentTypeEnum,
    CampaignStatusEnum,
    CampaignTypeEnum,
    CertificationDecisionEnum,
    EmploymentStatusEnum,
    IdentityRiskBandEnum,
    IdentityTypeEnum,
    JITApprovalStatusEnum,
    SoDPolicySeverityEnum,
    SoDViolationStatusEnum,
    SystemTypeEnum,
    TrustLevelEnum,
)


# ─── 1. Governed Identity Schemas ──────────────────────────────────────────────

class GovernedIdentityBase(BaseModel):
    identity_code: str = Field(..., min_length=2, max_length=64, description="Unique identity code, e.g. ID-EMP-001")
    email: str = Field(..., min_length=3, max_length=255, description="Primary email or UPN")
    full_name: str = Field(..., min_length=2, max_length=255)
    identity_type: IdentityTypeEnum = IdentityTypeEnum.WORKFORCE_EMPLOYEE
    department: Optional[str] = None
    employment_status: EmploymentStatusEnum = EmploymentStatusEnum.ACTIVE
    is_privileged: bool = False
    mfa_enabled: bool = True
    cloud_asset_id: Optional[int] = None
    user_id: Optional[int] = None


class GovernedIdentityCreate(GovernedIdentityBase):
    pass


class GovernedIdentityUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    department: Optional[str] = None
    employment_status: Optional[EmploymentStatusEnum] = None
    is_privileged: Optional[bool] = None
    mfa_enabled: Optional[bool] = None
    cloud_asset_id: Optional[int] = None
    user_id: Optional[int] = None


class GovernedIdentityResponse(GovernedIdentityBase):
    id: int
    organization_id: int
    risk_score: float
    risk_band: IdentityRiskBandEnum
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── 2. Entitlement Schemas ────────────────────────────────────────────────────

class IdentityEntitlementBase(BaseModel):
    entitlement_code: str = Field(..., min_length=2, max_length=64)
    name: str = Field(..., min_length=2, max_length=255)
    system_type: SystemTypeEnum = SystemTypeEnum.AWS_IAM
    resource_name: str = Field(..., min_length=2, max_length=255)
    permission_scope: str = Field(..., min_length=2, max_length=128)
    is_privileged: bool = False
    is_high_risk: bool = False
    risk_weight: float = Field(1.00, ge=1.0, le=5.0)
    description: Optional[str] = None


class IdentityEntitlementCreate(IdentityEntitlementBase):
    pass


class IdentityEntitlementResponse(IdentityEntitlementBase):
    id: int
    organization_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EntitlementAssignmentCreate(BaseModel):
    entitlement_id: int
    assignment_type: AssignmentTypeEnum = AssignmentTypeEnum.DIRECT
    expires_at: Optional[datetime] = None


class EntitlementAssignmentResponse(BaseModel):
    id: int
    organization_id: int
    identity_id: int
    entitlement_id: int
    assigned_at: datetime
    expires_at: Optional[datetime] = None
    assignment_type: AssignmentTypeEnum
    is_active: bool
    entitlement: Optional[IdentityEntitlementResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ─── 3. Access Certification Schemas (Four-Eyes SoD) ───────────────────────────

class AccessCertificationCampaignCreate(BaseModel):
    campaign_code: str = Field(..., min_length=2, max_length=64)
    title: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    campaign_type: CampaignTypeEnum = CampaignTypeEnum.PERIODIC_USER_ACCESS_REVIEW
    deadline: datetime


class AccessCertificationCampaignResponse(BaseModel):
    id: int
    organization_id: int
    campaign_code: str
    title: str
    description: Optional[str] = None
    campaign_type: CampaignTypeEnum
    status: CampaignStatusEnum
    total_items_count: int
    certified_items_count: int
    revoked_items_count: int
    deadline: datetime
    finalized_at: Optional[datetime] = None
    created_by_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AccessCertificationItemReview(BaseModel):
    decision: CertificationDecisionEnum
    decision_justification: Optional[str] = None
    remediation_plan_id: Optional[int] = None


class AccessCertificationItemResponse(BaseModel):
    id: int
    organization_id: int
    campaign_id: int
    identity_id: int
    entitlement_id: int
    decision: CertificationDecisionEnum
    decision_justification: Optional[str] = None
    reviewer_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    is_sod_violation: bool
    remediation_plan_id: Optional[int] = None
    identity: Optional[GovernedIdentityResponse] = None
    entitlement: Optional[IdentityEntitlementResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ─── 4. JIT Access Request Schemas (Four-Eyes SoD) ──────────────────────────────

class JITAccessRequestCreate(BaseModel):
    request_code: str = Field(..., min_length=2, max_length=64)
    identity_id: int
    entitlement_id: int
    requested_duration_minutes: int = Field(60, ge=15, le=480)
    business_justification: str = Field(..., min_length=10, max_length=1000)


class JITAccessReviewRequest(BaseModel):
    approved: bool
    notes: Optional[str] = None


class JITAccessRequestResponse(BaseModel):
    id: int
    organization_id: int
    request_code: str
    identity_id: int
    entitlement_id: int
    requested_duration_minutes: int
    business_justification: str
    approval_status: JITApprovalStatusEnum
    requested_by_id: int
    approved_by_id: Optional[int] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── 5. Zero Trust Assurance Schemas ───────────────────────────────────────────

class ZeroTrustAssessmentCreate(BaseModel):
    assessment_code: str = Field(..., min_length=2, max_length=64)
    device_health_score: float = Field(100.0, ge=0.0, le=100.0)
    auth_strength_score: float = Field(100.0, ge=0.0, le=100.0)
    context_risk_score: float = Field(0.0, ge=0.0, le=100.0)
    behavioral_anomaly_score: float = Field(0.0, ge=0.0, le=100.0)


class ZeroTrustPreviewRequest(BaseModel):
    device_health_score: float = Field(100.0, ge=0.0, le=100.0)
    auth_strength_score: float = Field(100.0, ge=0.0, le=100.0)
    context_risk_score: float = Field(0.0, ge=0.0, le=100.0)
    behavioral_anomaly_score: float = Field(0.0, ge=0.0, le=100.0)


class ZeroTrustPreviewResponse(BaseModel):
    zero_trust_assurance_score: float
    trust_level: TrustLevelEnum
    breakdown: Dict[str, float]


class ZeroTrustAssessmentResponse(BaseModel):
    id: int
    organization_id: int
    assessment_code: str
    identity_id: int
    device_health_score: float
    auth_strength_score: float
    context_risk_score: float
    behavioral_anomaly_score: float
    zero_trust_assurance_score: float
    trust_level: TrustLevelEnum
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── 6. SoD Conflict Policies & Violations ──────────────────────────────────────

class SoDConflictPolicyCreate(BaseModel):
    policy_code: str = Field(..., min_length=2, max_length=64)
    name: str = Field(..., min_length=2, max_length=255)
    entitlement_a_id: int
    entitlement_b_id: int
    severity: SoDPolicySeverityEnum = SoDPolicySeverityEnum.HIGH
    description: Optional[str] = None


class SoDConflictPolicyResponse(BaseModel):
    id: int
    organization_id: int
    policy_code: str
    name: str
    entitlement_a_id: int
    entitlement_b_id: int
    severity: SoDPolicySeverityEnum
    description: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SoDConflictViolationResponse(BaseModel):
    id: int
    organization_id: int
    identity_id: int
    policy_id: int
    status: SoDViolationStatusEnum
    remediation_plan_id: Optional[int] = None
    detected_at: datetime
    resolved_at: Optional[datetime] = None
    policy: Optional[SoDConflictPolicyResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ─── 7. Identity Governance Posture Summary ────────────────────────────────────

class IdentityPostureSummaryResponse(BaseModel):
    total_identities: int
    privileged_identities_count: int
    high_risk_identities_count: int
    active_sod_violations_count: int
    pending_certifications_count: int
    pending_jit_requests_count: int
    average_identity_risk_score: float
    average_zero_trust_score: float
    identity_type_distribution: Dict[str, int]
    system_entitlement_distribution: Dict[str, int]
