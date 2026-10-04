from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.finding import FindingSeverityEnum
from app.models.tprm import (
    BusinessCriticalityEnum,
    DataClassificationEnum,
    EngagementStatusEnum,
    HostingModelEnum,
    NetworkConnectivityEnum,
    PiiFinancialAccessEnum,
    VendorAssessmentStatusEnum,
    VendorAssessmentTypeEnum,
    VendorContractStatusEnum,
    VendorContractTypeEnum,
    VendorDocumentTypeEnum,
    VendorOffboardingItemStatusEnum,
    VendorOffboardingStatusEnum,
    VendorOffboardingStepTypeEnum,
    VendorOffboardingTargetStatusEnum,
    VendorResponseStatusEnum,
    VendorRiskBandEnum,
    VendorSlaBreachSeverityEnum,
    VendorSlaBreachStatusEnum,
    VendorSlaComparisonOperatorEnum,
    VendorSlaMetricTypeEnum,
    VendorSlaObligationStatusEnum,
    VendorStatusEnum,
    VendorSubprocessorStatusEnum,
    VendorTierEnum,
)


# ─── VENDOR SCHEMAS ──────────────────────────────────────────────────────────

class VendorBase(BaseModel):
    vendor_code: str = Field(..., min_length=2, max_length=50)
    legal_name: str = Field(..., min_length=2, max_length=255)
    trade_name: Optional[str] = Field(None, max_length=255)
    business_owner_id: Optional[int] = None


class VendorCreate(VendorBase):
    pass


class VendorUpdate(BaseModel):
    legal_name: Optional[str] = Field(None, min_length=2, max_length=255)
    trade_name: Optional[str] = Field(None, max_length=255)
    vendor_status: Optional[VendorStatusEnum] = None
    business_owner_id: Optional[int] = None


class VendorTierOverride(BaseModel):
    override_tier: VendorTierEnum
    reason: str = Field(..., min_length=10, description="Mandatory justification for manual tier override")


class VendorRead(VendorBase):
    id: int
    organization_id: int
    vendor_status: VendorStatusEnum
    calculated_inherent_risk: float
    calculated_tier: VendorTierEnum
    override_tier: Optional[VendorTierEnum] = None
    tier_override_reason: Optional[str] = None
    tier_overridden_by_id: Optional[int] = None
    tier_overridden_at: Optional[datetime] = None
    effective_tier: VendorTierEnum
    residual_risk_score: float
    risk_band: VendorRiskBandEnum
    open_sla_breaches_count: int = 0
    approved_subprocessors_count: int = 0
    offboarding_completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── VENDOR ENGAGEMENT SCHEMAS ──────────────────────────────────────────────

class VendorEngagementBase(BaseModel):
    engagement_code: str = Field(..., min_length=2, max_length=50)
    engagement_name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    criticality: BusinessCriticalityEnum = BusinessCriticalityEnum.MEDIUM
    data_classification: DataClassificationEnum = DataClassificationEnum.INTERNAL
    hosting_model: HostingModelEnum = HostingModelEnum.MULTI_TENANT_SAAS
    network_connectivity: NetworkConnectivityEnum = NetworkConnectivityEnum.ISOLATED_NO_CONNECTION
    pii_access: PiiFinancialAccessEnum = PiiFinancialAccessEnum.NONE


class VendorEngagementCreate(VendorEngagementBase):
    pass


class VendorEngagementUpdate(BaseModel):
    engagement_name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    status: Optional[EngagementStatusEnum] = None
    criticality: Optional[BusinessCriticalityEnum] = None
    data_classification: Optional[DataClassificationEnum] = None
    hosting_model: Optional[HostingModelEnum] = None
    network_connectivity: Optional[NetworkConnectivityEnum] = None
    pii_access: Optional[PiiFinancialAccessEnum] = None


class VendorEngagementRead(VendorEngagementBase):
    id: int
    organization_id: int
    vendor_id: int
    status: EngagementStatusEnum
    calculated_risk_score: float
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── VENDOR ASSESSMENT ITEM SCHEMAS ─────────────────────────────────────────

class VendorAssessmentItemBase(BaseModel):
    question_key: str = Field(..., min_length=1, max_length=100)
    question_text: str = Field(..., min_length=1)
    rationalized_common_control_id: Optional[int] = None
    response_status: VendorResponseStatusEnum = VendorResponseStatusEnum.NOT_APPLICABLE
    weight: float = Field(1.0, ge=0.1, le=10.0)
    vendor_response_text: Optional[str] = None
    assessor_notes: Optional[str] = None


class VendorAssessmentItemCreate(VendorAssessmentItemBase):
    pass


class VendorAssessmentItemUpdate(BaseModel):
    response_status: Optional[VendorResponseStatusEnum] = None
    vendor_response_text: Optional[str] = None
    assessor_notes: Optional[str] = None


class VendorAssessmentItemRead(VendorAssessmentItemBase):
    id: int
    organization_id: int
    assessment_id: int
    findings_count: int
    linked_finding_id: Optional[int] = None
    linked_remediation_plan_id: Optional[int] = None
    linked_risk_id: Optional[int] = None
    escalated_by_id: Optional[int] = None
    escalated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── VENDOR ASSESSMENT SCHEMAS ──────────────────────────────────────────────

class VendorAssessmentBase(BaseModel):
    assessment_code: str = Field(..., min_length=2, max_length=50)
    title: str = Field(..., min_length=2, max_length=255)
    assessment_type: VendorAssessmentTypeEnum = VendorAssessmentTypeEnum.INITIAL_DUE_DILIGENCE
    engagement_id: Optional[int] = None
    valid_until: Optional[datetime] = None


class VendorAssessmentCreate(VendorAssessmentBase):
    items: Optional[List[VendorAssessmentItemCreate]] = None


class VendorAssessmentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    engagement_id: Optional[int] = None
    valid_until: Optional[datetime] = None


class VendorAssessmentReview(BaseModel):
    review_notes: Optional[str] = None
    rejection_reason: Optional[str] = None


class VendorAssessmentRead(VendorAssessmentBase):
    id: int
    organization_id: int
    vendor_id: int
    status: VendorAssessmentStatusEnum
    assessor_id: int
    reviewer_id: Optional[int] = None
    calculated_score: float
    review_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    items: List[VendorAssessmentItemRead] = []

    model_config = ConfigDict(from_attributes=True)


# ─── VENDOR EVIDENCE LINK SCHEMAS ───────────────────────────────────────────

class VendorEvidenceLinkCreate(BaseModel):
    evidence_id: int
    document_type: VendorDocumentTypeEnum = VendorDocumentTypeEnum.OTHER
    effective_date: datetime
    expiration_date: datetime


class VendorEvidenceLinkRead(BaseModel):
    id: int
    organization_id: int
    vendor_id: int
    evidence_id: int
    document_type: VendorDocumentTypeEnum
    effective_date: datetime
    expiration_date: datetime
    is_verified: bool
    verified_by_id: Optional[int] = None
    verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── BATCH 6: VENDOR CONTRACT SCHEMAS ───────────────────────────────────────

class VendorContractCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_code: str = Field(..., min_length=2, max_length=64)
    title: str = Field(..., min_length=3, max_length=255)
    contract_type: VendorContractTypeEnum = VendorContractTypeEnum.MSA
    engagement_id: Optional[int] = None
    effective_date: datetime
    expiry_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    auto_renew: bool = False
    notice_period_days: int = Field(30, ge=0, le=3650)
    dpa_included: bool = False
    dpa_signed_at: Optional[datetime] = None
    data_retention_days: Optional[int] = Field(None, ge=0)
    right_to_audit_clause: bool = False
    subprocessor_authorization_clause: bool = False
    exit_strategy_clause: bool = False
    incident_notification_hours_clause: Optional[int] = Field(None, ge=1, le=720)
    governing_jurisdiction: Optional[str] = Field(None, max_length=120)
    regulatory_mandates_applicable: Optional[str] = Field(None, max_length=255)
    evidence_id: Optional[int] = None

    @model_validator(mode="after")
    def _normalize_and_validate_dates(self):
        if self.expiry_date is None and self.expiration_date is not None:
            self.expiry_date = self.expiration_date
        if self.dpa_signed_at is not None:
            self.dpa_included = True
        if self.expiry_date is not None and self.expiry_date <= self.effective_date:
            raise ValueError("expiry_date must be strictly after effective_date")
        return self


class VendorContractUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(None, min_length=3, max_length=255)
    contract_type: Optional[VendorContractTypeEnum] = None
    engagement_id: Optional[int] = None
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    auto_renew: Optional[bool] = None
    notice_period_days: Optional[int] = Field(None, ge=0, le=3650)
    dpa_included: Optional[bool] = None
    dpa_signed_at: Optional[datetime] = None
    data_retention_days: Optional[int] = Field(None, ge=0)
    right_to_audit_clause: Optional[bool] = None
    subprocessor_authorization_clause: Optional[bool] = None
    exit_strategy_clause: Optional[bool] = None
    incident_notification_hours_clause: Optional[int] = Field(None, ge=1, le=720)
    governing_jurisdiction: Optional[str] = Field(None, max_length=120)
    regulatory_mandates_applicable: Optional[str] = Field(None, max_length=255)
    evidence_id: Optional[int] = None
    status: Optional[VendorContractStatusEnum] = None

    @model_validator(mode="after")
    def _normalize_update(self):
        if self.expiry_date is None and self.expiration_date is not None:
            self.expiry_date = self.expiration_date
        if self.dpa_signed_at is not None and self.dpa_included is None:
            self.dpa_included = True
        if (
            self.effective_date is not None
            and self.expiry_date is not None
            and self.expiry_date <= self.effective_date
        ):
            raise ValueError("expiry_date must be strictly after effective_date")
        return self


class VendorContractReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_notes: Optional[str] = Field(None, max_length=2000)
    rejection_reason: Optional[str] = Field(None, max_length=2000)
    reason: Optional[str] = Field(None, max_length=2000)


class VendorContractRead(BaseModel):
    id: int
    organization_id: int
    vendor_id: int
    engagement_id: Optional[int] = None
    contract_code: str
    title: str
    contract_type: VendorContractTypeEnum
    status: VendorContractStatusEnum
    effective_date: datetime
    expiry_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    auto_renew: bool
    notice_period_days: int
    dpa_included: bool
    right_to_audit_clause: bool
    subprocessor_authorization_clause: bool
    exit_strategy_clause: bool
    incident_notification_hours_clause: Optional[int] = None
    governing_jurisdiction: Optional[str] = None
    regulatory_mandates_applicable: Optional[str] = None
    evidence_id: Optional[int] = None
    evidence_sha256_snapshot: Optional[str] = None
    created_by_id: Optional[int] = None
    submitted_by_id: Optional[int] = None
    submitted_at: Optional[datetime] = None
    approved_by_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── BATCH 6: SUBPROCESSOR & FOURTH-PARTY SCHEMAS ───────────────────────────

class VendorSubprocessorCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subprocessor_code: Optional[str] = Field(None, min_length=2, max_length=64)
    subprocessor_name: str = Field(..., min_length=2, max_length=255)
    subprocessor_domain: Optional[str] = Field(None, max_length=255)
    engagement_id: Optional[int] = None
    subprocessor_vendor_id: Optional[int] = None
    linked_fourth_party_vendor_id: Optional[int] = None
    service_function: str = Field(..., min_length=3, max_length=255)
    hosting_region: str = Field("US-EAST", min_length=2, max_length=120)
    jurisdiction: str = Field("US", min_length=2, max_length=120)
    criticality: BusinessCriticalityEnum = BusinessCriticalityEnum.MEDIUM
    data_classification: DataClassificationEnum = DataClassificationEnum.INTERNAL
    pii_access: PiiFinancialAccessEnum = PiiFinancialAccessEnum.NONE
    contractual_flowdown_verified: bool = False
    evidence_id: Optional[int] = None
    linked_risk_id: Optional[int] = None

    @model_validator(mode="after")
    def _normalize_vendor_link(self):
        if self.subprocessor_vendor_id is None and self.linked_fourth_party_vendor_id is not None:
            self.subprocessor_vendor_id = self.linked_fourth_party_vendor_id
        return self


class VendorSubprocessorUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subprocessor_name: Optional[str] = Field(None, min_length=2, max_length=255)
    subprocessor_domain: Optional[str] = Field(None, max_length=255)
    engagement_id: Optional[int] = None
    subprocessor_vendor_id: Optional[int] = None
    linked_fourth_party_vendor_id: Optional[int] = None
    service_function: Optional[str] = Field(None, min_length=3, max_length=255)
    hosting_region: Optional[str] = Field(None, min_length=2, max_length=120)
    jurisdiction: Optional[str] = Field(None, min_length=2, max_length=120)
    criticality: Optional[BusinessCriticalityEnum] = None
    data_classification: Optional[DataClassificationEnum] = None
    pii_access: Optional[PiiFinancialAccessEnum] = None
    contractual_flowdown_verified: Optional[bool] = None
    evidence_id: Optional[int] = None
    linked_risk_id: Optional[int] = None

    @model_validator(mode="after")
    def _normalize_vendor_link(self):
        if self.subprocessor_vendor_id is None and self.linked_fourth_party_vendor_id is not None:
            self.subprocessor_vendor_id = self.linked_fourth_party_vendor_id
        return self


class VendorSubprocessorReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_notes: Optional[str] = Field(None, max_length=2000)
    rejection_reason: Optional[str] = Field(None, max_length=2000)
    suspension_reason: Optional[str] = Field(None, max_length=2000)
    termination_reason: Optional[str] = Field(None, max_length=2000)
    reason: Optional[str] = Field(None, max_length=2000)


class VendorSubprocessorRead(BaseModel):
    id: int
    organization_id: int
    vendor_id: int
    engagement_id: Optional[int] = None
    subprocessor_vendor_id: Optional[int] = None
    linked_fourth_party_vendor_id: Optional[int] = None
    subprocessor_code: str
    subprocessor_name: str
    normalized_fourth_party_name: Optional[str] = None
    subprocessor_domain: Optional[str] = None
    service_function: str
    hosting_region: str
    jurisdiction: str
    criticality: BusinessCriticalityEnum
    data_classification: DataClassificationEnum
    pii_access: PiiFinancialAccessEnum
    status: VendorSubprocessorStatusEnum
    contractual_flowdown_verified: bool
    evidence_id: Optional[int] = None
    evidence_sha256_snapshot: Optional[str] = None
    linked_risk_id: Optional[int] = None
    registered_by_id: Optional[int] = None
    submitted_by_id: Optional[int] = None
    submitted_at: Optional[datetime] = None
    approved_by_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    reviewed_by_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    suspension_reason: Optional[str] = None
    termination_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConcentrationRiskNodeRead(BaseModel):
    canonical_name: str
    normalized_fourth_party_name: Optional[str] = None
    subprocessor_domain: Optional[str] = None
    subprocessor_vendor_id: Optional[int] = None
    linked_fourth_party_vendor_id: Optional[int] = None
    dependent_vendor_ids: List[int]
    dependent_vendor_codes: List[str]
    dependent_vendors_count: int
    tier1_or_tier2_dependents_count: int
    dependent_tier1_tier2_count: Optional[int] = None
    max_criticality: BusinessCriticalityEnum
    hosting_regions: List[str]
    jurisdictions: List[str]
    concentration_risk_score: float
    is_single_point_of_failure: bool
    is_spof: Optional[bool] = None

    @model_validator(mode="after")
    def _populate_aliases(self):
        if self.normalized_fourth_party_name is None:
            self.normalized_fourth_party_name = self.canonical_name
        if self.linked_fourth_party_vendor_id is None:
            self.linked_fourth_party_vendor_id = self.subprocessor_vendor_id
        if self.dependent_tier1_tier2_count is None:
            self.dependent_tier1_tier2_count = self.tier1_or_tier2_dependents_count
        if self.is_spof is None:
            self.is_spof = self.is_single_point_of_failure
        return self


class ConcentrationRiskReportResponse(BaseModel):
    organization_id: Optional[int] = None
    total_subprocessors: int
    unique_fourth_parties: int
    shared_fourth_party_count: int = 0
    spof_count: int
    nodes: List[ConcentrationRiskNodeRead]
    single_point_of_failure_candidates: List[ConcentrationRiskNodeRead] = []


# ─── BATCH 6: SLA OBLIGATION & BREACH SCHEMAS ───────────────────────────────

class VendorSlaObligationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    obligation_code: str = Field(..., min_length=2, max_length=64)
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    contract_id: Optional[int] = None
    engagement_id: Optional[int] = None
    linked_organization_control_id: Optional[int] = None
    rationalized_common_control_id: Optional[int] = None
    metric_type: VendorSlaMetricTypeEnum = VendorSlaMetricTypeEnum.AVAILABILITY_PCT
    comparison_operator: VendorSlaComparisonOperatorEnum = VendorSlaComparisonOperatorEnum.GTE
    target_value: float = Field(..., ge=0.0, le=1000000.0)
    tolerance_value: Optional[float] = Field(None, ge=0.0, le=1000000.0)
    breach_threshold: Optional[float] = Field(None, ge=0.0, le=1000000.0)
    warning_threshold: Optional[float] = Field(None, ge=0.0, le=1000000.0)
    unit: str = Field("PERCENT", min_length=1, max_length=32)
    measurement_window: str = Field("MONTHLY", min_length=2, max_length=64)
    measurement_frequency_days: int = Field(30, ge=1, le=365)
    breach_severity_on_miss: VendorSlaBreachSeverityEnum = VendorSlaBreachSeverityEnum.HIGH
    contract_clause_ref: Optional[str] = Field(None, max_length=120)
    penalty_clause_summary: Optional[str] = Field(None, max_length=1000)
    effective_from: Optional[datetime] = None
    expiry_date: Optional[datetime] = None

    @model_validator(mode="after")
    def _normalize_sla_fields(self):
        if self.tolerance_value is None and self.breach_threshold is not None:
            self.tolerance_value = self.breach_threshold
        if (
            self.linked_organization_control_id is None
            and self.rationalized_common_control_id is not None
        ):
            self.linked_organization_control_id = self.rationalized_common_control_id
        return self


class VendorSlaObligationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    contract_id: Optional[int] = None
    engagement_id: Optional[int] = None
    linked_organization_control_id: Optional[int] = None
    rationalized_common_control_id: Optional[int] = None
    metric_type: Optional[VendorSlaMetricTypeEnum] = None
    comparison_operator: Optional[VendorSlaComparisonOperatorEnum] = None
    target_value: Optional[float] = Field(None, ge=0.0, le=1000000.0)
    tolerance_value: Optional[float] = Field(None, ge=0.0, le=1000000.0)
    breach_threshold: Optional[float] = Field(None, ge=0.0, le=1000000.0)
    warning_threshold: Optional[float] = Field(None, ge=0.0, le=1000000.0)
    unit: Optional[str] = Field(None, min_length=1, max_length=32)
    measurement_window: Optional[str] = Field(None, min_length=2, max_length=64)
    measurement_frequency_days: Optional[int] = Field(None, ge=1, le=365)
    breach_severity_on_miss: Optional[VendorSlaBreachSeverityEnum] = None
    contract_clause_ref: Optional[str] = Field(None, max_length=120)
    penalty_clause_summary: Optional[str] = Field(None, max_length=1000)
    effective_from: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    status: Optional[VendorSlaObligationStatusEnum] = None

    @model_validator(mode="after")
    def _normalize_sla_fields(self):
        if self.tolerance_value is None and self.breach_threshold is not None:
            self.tolerance_value = self.breach_threshold
        if (
            self.linked_organization_control_id is None
            and self.rationalized_common_control_id is not None
        ):
            self.linked_organization_control_id = self.rationalized_common_control_id
        return self


class VendorSlaObligationRead(BaseModel):
    id: int
    organization_id: int
    vendor_id: int
    contract_id: Optional[int] = None
    engagement_id: Optional[int] = None
    linked_organization_control_id: Optional[int] = None
    rationalized_common_control_id: Optional[int] = None
    obligation_code: str
    title: str
    description: Optional[str] = None
    metric_type: VendorSlaMetricTypeEnum
    comparison_operator: VendorSlaComparisonOperatorEnum
    target_value: float
    tolerance_value: Optional[float] = None
    breach_threshold: Optional[float] = None
    warning_threshold: Optional[float] = None
    unit: str
    measurement_window: str
    measurement_frequency_days: int = 30
    breach_severity_on_miss: VendorSlaBreachSeverityEnum
    contract_clause_ref: Optional[str] = None
    penalty_clause_summary: Optional[str] = None
    effective_from: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    status: VendorSlaObligationStatusEnum
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VendorSlaBreachCreate(BaseModel):
    """Input schema for SLA breach creation.
    NOTE: severity, variance_magnitude, target_value_snapshot, recorded_by_id, and
    organization_id are strictly forbidden from client input (SEC-B6-22/23/36).
    """
    model_config = ConfigDict(extra="forbid")

    obligation_id: Optional[int] = None
    sla_obligation_id: Optional[int] = None
    breach_code: Optional[str] = Field(None, min_length=2, max_length=64)
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    breach_period_start: Optional[datetime] = None
    breach_period_end: Optional[datetime] = None
    occurred_at: Optional[datetime] = None
    observed_value: float
    root_cause_summary: Optional[str] = Field(None, max_length=4000)
    service_credit_amount: Optional[float] = Field(None, ge=0.0)
    evidence_id: Optional[int] = None
    auto_escalate_to_finding: bool = False
    finding_owner_id: Optional[int] = None

    @model_validator(mode="after")
    def _normalize_breach_fields(self):
        if self.obligation_id is None and self.sla_obligation_id is not None:
            self.obligation_id = self.sla_obligation_id
        if self.obligation_id is None:
            raise ValueError("obligation_id (or sla_obligation_id) is required")
        if self.period_start is None and self.breach_period_start is not None:
            self.period_start = self.breach_period_start
        if self.period_end is None and self.breach_period_end is not None:
            self.period_end = self.breach_period_end
        return self


class VendorSlaBreachEscalateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_control_id: Optional[int] = None
    finding_title: Optional[str] = Field(None, max_length=255)
    finding_description: Optional[str] = Field(None, max_length=4000)
    create_finding: bool = True
    create_remediation_plan: bool = False
    create_risk: bool = False
    risk_statement: Optional[str] = Field(None, max_length=2000)
    inherent_likelihood: int = Field(default=3, ge=1, le=5)
    inherent_impact: int = Field(default=4, ge=1, le=5)
    finding_owner_id: Optional[int] = None
    remediation_due_date: Optional[datetime] = None


class VendorSlaBreachResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resolution_notes: str = Field(..., min_length=5, max_length=4000)
    evidence_id: Optional[int] = None
    linked_exception_id: Optional[int] = None


class VendorSlaBreachWaiveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    linked_exception_id: Optional[int] = None
    waiver_reason: Optional[str] = Field(None, min_length=3, max_length=2000)
    resolution_notes: Optional[str] = Field(None, min_length=3, max_length=2000)

    @model_validator(mode="after")
    def _normalize_waiver_reason(self):
        resolved = self.waiver_reason or self.resolution_notes
        if not resolved:
            raise ValueError("waiver_reason (or resolution_notes) is required")
        self.waiver_reason = resolved
        return self


class VendorSlaBreachReopenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: Optional[str] = Field(None, max_length=2000)


class VendorSlaBreachVerifyCloseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    closure_notes: Optional[str] = Field(None, max_length=2000)
    evidence_id: Optional[int] = None


class VendorSlaBreachRead(BaseModel):
    id: int
    organization_id: int
    vendor_id: int
    obligation_id: int
    sla_obligation_id: Optional[int] = None
    breach_code: str
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    breach_period_start: Optional[datetime] = None
    breach_period_end: Optional[datetime] = None
    occurred_at: datetime
    reported_at: datetime
    recorded_at: Optional[datetime] = None
    target_value_snapshot: float
    tolerance_value_snapshot: Optional[float] = None
    breach_threshold_snapshot: Optional[float] = None
    observed_value: float
    variance_magnitude: float = 0.0
    service_credit_amount: Optional[float] = None
    comparison_operator_snapshot: VendorSlaComparisonOperatorEnum
    severity: VendorSlaBreachSeverityEnum
    status: VendorSlaBreachStatusEnum
    root_cause_summary: Optional[str] = None
    resolution_notes: Optional[str] = None
    evidence_id: Optional[int] = None
    evidence_sha256_snapshot: Optional[str] = None
    linked_finding_id: Optional[int] = None
    linked_remediation_plan_id: Optional[int] = None
    linked_risk_id: Optional[int] = None
    linked_exception_id: Optional[int] = None
    reported_by_id: Optional[int] = None
    recorded_by_id: Optional[int] = None
    resolved_by_id: Optional[int] = None
    resolved_at: Optional[datetime] = None
    waived_by_id: Optional[int] = None
    waived_at: Optional[datetime] = None
    waiver_reason: Optional[str] = None
    closed_by_id: Optional[int] = None
    closed_at: Optional[datetime] = None
    closure_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── BATCH 6: ASSESSMENT ITEM ESCALATION SCHEMA ─────────────────────────────

class VendorAssessmentItemEscalateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_control_id: Optional[int] = None
    severity: FindingSeverityEnum = FindingSeverityEnum.HIGH
    finding_title: Optional[str] = Field(None, max_length=255)
    finding_description: Optional[str] = Field(None, max_length=4000)
    owner_id: Optional[int] = None
    finding_owner_id: Optional[int] = None
    due_date: Optional[datetime] = None
    remediation_due_date: Optional[datetime] = None
    create_finding: bool = True
    create_remediation_plan: bool = True
    create_risk: bool = False
    risk_statement: Optional[str] = Field(None, max_length=2000)
    inherent_likelihood: int = Field(default=3, ge=1, le=5)
    inherent_impact: int = Field(default=4, ge=1, le=5)
    remediation_plan_title: Optional[str] = Field(None, min_length=3, max_length=255)
    remediation_strategy: Optional[str] = Field(None, min_length=5, max_length=4000)


# ─── BATCH 6: VENDOR OFFBOARDING SCHEMAS ────────────────────────────────────

class VendorOffboardingInitiateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    offboarding_code: Optional[str] = Field(None, min_length=2, max_length=64)
    target_vendor_status: VendorOffboardingTargetStatusEnum = VendorOffboardingTargetStatusEnum.OFFBOARDED
    initiation_reason: Optional[str] = Field(None, min_length=3, max_length=4000)
    rationale: Optional[str] = Field(None, min_length=3, max_length=4000)
    reason: Optional[str] = Field(None, min_length=3, max_length=4000)
    target_completion_date: Optional[datetime] = None
    requires_data_destruction_proof: Optional[bool] = None

    @model_validator(mode="after")
    def _normalize_reason(self):
        resolved = self.initiation_reason or self.rationale or self.reason
        if not resolved:
            raise ValueError("initiation_reason (or rationale / reason) is required")
        self.initiation_reason = resolved
        return self


class VendorOffboardingItemAttestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attestation_notes: Optional[str] = Field(None, max_length=4000)
    evidence_id: Optional[int] = None
    status: Optional[VendorOffboardingItemStatusEnum] = None
    waiver_reason: Optional[str] = Field(None, max_length=4000)
    linked_exception_id: Optional[int] = None


class VendorOffboardingItemWaiveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    waiver_reason: Optional[str] = Field(None, min_length=3, max_length=4000)
    waiver_justification: Optional[str] = Field(None, min_length=3, max_length=4000)
    linked_exception_id: Optional[int] = None

    @model_validator(mode="after")
    def _normalize_waiver_reason(self):
        resolved = self.waiver_reason or self.waiver_justification
        if not resolved:
            raise ValueError("waiver_reason (or waiver_justification) is required")
        self.waiver_reason = resolved
        return self


class VendorOffboardingCompleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    closure_notes: Optional[str] = Field(None, max_length=4000)
    signoff_notes: Optional[str] = Field(None, max_length=4000)
    review_notes: Optional[str] = Field(None, max_length=4000)
    rejection_reason: Optional[str] = Field(None, max_length=4000)
    reason: Optional[str] = Field(None, max_length=4000)
    data_destruction_evidence_id: Optional[int] = None

    @model_validator(mode="after")
    def _normalize_closure_notes(self):
        if self.closure_notes is None and self.signoff_notes is not None:
            self.closure_notes = self.signoff_notes
        return self


class VendorOffboardingCancelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cancellation_reason: str = Field(..., min_length=5, max_length=4000)


class VendorOffboardingItemRead(BaseModel):
    id: int
    organization_id: int
    offboarding_record_id: int
    step_number: int = 1
    step_key: str
    step_type: VendorOffboardingStepTypeEnum
    title: str
    description: Optional[str] = None
    is_mandatory: bool
    requires_evidence: bool = False
    status: VendorOffboardingItemStatusEnum
    evidence_id: Optional[int] = None
    evidence_sha256_snapshot: Optional[str] = None
    linked_exception_id: Optional[int] = None
    attestation_notes: Optional[str] = None
    waiver_reason: Optional[str] = None
    waiver_justification: Optional[str] = None
    completed_by_id: Optional[int] = None
    completed_at: Optional[datetime] = None
    waived_by_id: Optional[int] = None
    waived_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VendorOffboardingRecordRead(BaseModel):
    id: int
    organization_id: int
    vendor_id: int
    offboarding_code: str
    target_vendor_status: VendorOffboardingTargetStatusEnum
    status: VendorOffboardingStatusEnum
    initiation_reason: str
    rationale: Optional[str] = None
    reason: Optional[str] = None
    target_completion_date: Optional[datetime] = None
    requires_data_destruction_proof: bool = False
    data_destruction_evidence_id: Optional[int] = None
    initiated_by_id: Optional[int] = None
    initiated_at: datetime
    submitted_by_id: Optional[int] = None
    submitted_at: Optional[datetime] = None
    approved_by_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    verified_by_id: Optional[int] = None
    verified_at: Optional[datetime] = None
    cancelled_by_id: Optional[int] = None
    cancelled_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    closure_notes: Optional[str] = None
    signoff_notes: Optional[str] = None
    cancellation_reason: Optional[str] = None
    signoff_hash_sha256: Optional[str] = None
    items: List[VendorOffboardingItemRead] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── TELEMETRY & POSTURE SCHEMAS ─────────────────────────────────────────────

class VendorInherentRiskBreakdown(BaseModel):
    inherent_risk_score: float
    calculated_tier: VendorTierEnum
    effective_tier: VendorTierEnum
    highest_criticality_engagement_code: Optional[str] = None
    active_engagements_count: int


class VendorResidualRiskBreakdown(BaseModel):
    inherent_risk_score: float
    latest_assessment_score: Optional[float] = None
    risk_floor: float
    base_residual_risk: float
    finding_penalties: float
    exception_penalties: float
    sla_breach_penalties: float = 0.0
    subprocessor_penalties: float = 0.0
    residual_risk_score: float
    risk_band: VendorRiskBandEnum


class VendorRiskPostureResponse(BaseModel):
    vendor_id: int
    vendor_code: str
    legal_name: str
    status: VendorStatusEnum
    inherent: VendorInherentRiskBreakdown
    residual: VendorResidualRiskBreakdown
    finding_penalties: float = 0.0
    exception_penalties: float = 0.0
    sla_breach_penalties: float = 0.0
    subprocessor_penalties: float = 0.0
    open_sla_breaches_count: int = 0
    approved_subprocessors_count: int = 0
    concentration_risk_summary: Optional[Dict[str, Any]] = None
    offboarding_status: Optional[str] = None
    engagements: List[VendorEngagementRead]
    latest_approved_assessment: Optional[VendorAssessmentRead] = None
    evidence_links: List[VendorEvidenceLinkRead]
    contracts: List[VendorContractRead] = []
    subprocessors: List[VendorSubprocessorRead] = []
    sla_obligations: List[VendorSlaObligationRead] = []
    sla_breaches: List[VendorSlaBreachRead] = []
    offboarding_records: List[VendorOffboardingRecordRead] = []
