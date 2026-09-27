from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.finding import FindingSeverityEnum, FindingTypeEnum
from app.models.remediation import RemediationRootCauseClassificationEnum
from app.models.resilience import (
    BiaStatusEnum,
    ContinuityPlanStatusEnum,
    ContinuityStrategyTypeEnum,
    CriticalityTierEnum,
    DependencyTypeEnum,
    ExerciseOutcomeEnum,
    ExerciseStatusEnum,
    ExerciseTypeEnum,
    ResilienceEvidenceContextEnum,
)
from app.schemas.user import UserResponse


def _normalize_enum_str(val: Any) -> Any:
    if isinstance(val, str):
        return val.strip().upper()
    return val


# ─────────────────────────────────────────────────────────────────────────────
# 1. BUSINESS PROCESS SCHEMAS (Phase 13 Preserved)
# ─────────────────────────────────────────────────────────────────────────────

class BusinessProcessBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Unique business process name")
    description: Optional[str] = Field(default=None, description="Detailed function and scope description")
    criticality_tier: CriticalityTierEnum = Field(
        default=CriticalityTierEnum.TIER_3,
        description="Organizational criticality classification tier",
    )


class BusinessProcessCreate(BusinessProcessBase):
    pass


class BusinessProcessUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    description: Optional[str] = None
    criticality_tier: Optional[CriticalityTierEnum] = None


# ─────────────────────────────────────────────────────────────────────────────
# 2. BUSINESS IMPACT ANALYSIS (BIA) SCHEMAS (Phase 13 Preserved)
# ─────────────────────────────────────────────────────────────────────────────

class BusinessImpactAnalysisBase(BaseModel):
    rto_hours: float = Field(
        default=4.0,
        ge=0.0,
        description="Recovery Time Objective in hours (must be <= MTD)",
    )
    rpo_hours: float = Field(
        default=1.0,
        ge=0.0,
        description="Recovery Point Objective in hours",
    )
    mtd_hours: float = Field(
        default=24.0,
        ge=0.0,
        description="Maximum Tolerable Downtime in hours",
    )
    hourly_downtime_cost: float = Field(
        default=10000.0,
        ge=0.0,
        description="Financial disruption loss per downtime hour in USD",
    )
    fixed_outage_cost: float = Field(
        default=5000.0,
        ge=0.0,
        description="Fixed initial disruption/incident cost in USD",
    )
    notes: Optional[str] = Field(default=None, description="Justification and impact context notes")

    @model_validator(mode="after")
    def validate_rto_mtd(self) -> "BusinessImpactAnalysisBase":
        if self.rto_hours > self.mtd_hours:
            raise ValueError(
                f"Invalid downtime thresholds: Recovery Time Objective ({self.rto_hours}h) "
                f"cannot exceed Maximum Tolerable Downtime ({self.mtd_hours}h)."
            )
        return self


class BusinessImpactAnalysisCreate(BusinessImpactAnalysisBase):
    process_id: int = Field(..., description="Target business process ID")


class BusinessImpactAnalysisApproveRequest(BaseModel):
    notes: Optional[str] = Field(default=None, description="Formal approval review notes")


class BusinessImpactAnalysisRead(BusinessImpactAnalysisBase):
    id: int
    organization_id: int
    process_id: int
    status: BiaStatusEnum
    version: int

    requested_by_id: int
    approved_by_id: Optional[int] = None
    approved_at: Optional[datetime] = None

    created_at: datetime
    updated_at: datetime

    requested_by: Optional[UserResponse] = None
    approved_by: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# 3. PROCESS DEPENDENCY SCHEMAS (Extended for Batch 5)
# ─────────────────────────────────────────────────────────────────────────────

class ProcessDependencyCreate(BaseModel):
    process_id: Optional[int] = Field(default=None, description="Target business process ID")
    dependency_type: DependencyTypeEnum = Field(
        ...,
        description="Type of dependency: VENDOR, CONTROL, CLOUD_ASSET, DATA_ASSET, or PROCESS",
    )
    dependency_id: Optional[int] = Field(
        default=None,
        description="Target entity ID in tenant (backward-compatible with Phase 13)",
    )
    vendor_id: Optional[int] = Field(default=None, description="Target Vendor ID")
    organization_control_id: Optional[int] = Field(default=None, description="Target OrganizationControl ID")
    cloud_asset_id: Optional[int] = Field(default=None, description="Target CloudAsset ID")
    data_asset_id: Optional[int] = Field(default=None, description="Target DataAsset ID")
    depends_on_process_id: Optional[int] = Field(default=None, description="Target upstream BusinessProcess ID")
    is_single_point_of_failure: bool = Field(default=False, description="Whether dependency is an SPOF")
    failure_propagation_weight: float = Field(
        default=1.0,
        gt=0.0,
        le=1.0,
        description="Outage propagation weight in (0.0, 1.0]",
    )
    recovery_priority_order: int = Field(
        default=1,
        ge=1,
        description="Recovery sequence priority (>= 1)",
    )
    notes: Optional[str] = Field(default=None, max_length=255, description="Contextual dependency notes")
    criticality_notes: Optional[str] = Field(default=None, description="Detailed SPOF/resilience notes")

    @field_validator("dependency_type", mode="before")
    @classmethod
    def normalize_dep_type(cls, v: Any) -> Any:
        return _normalize_enum_str(v)

    @model_validator(mode="after")
    def validate_dependency_targets(self) -> "ProcessDependencyCreate":
        if self.is_single_point_of_failure and self.failure_propagation_weight < 1.0:
            raise ValueError(
                "Single-point-of-failure (SPOF) dependency must have failure_propagation_weight == 1.0."
            )

        typed_map = {
            DependencyTypeEnum.VENDOR: self.vendor_id,
            DependencyTypeEnum.CONTROL: self.organization_control_id,
            DependencyTypeEnum.CLOUD_ASSET: self.cloud_asset_id,
            DependencyTypeEnum.DATA_ASSET: self.data_asset_id,
            DependencyTypeEnum.PROCESS: self.depends_on_process_id,
        }
        non_null_typed = [(k, v) for k, v in typed_map.items() if v is not None]

        if len(non_null_typed) > 1:
            raise ValueError(
                "Target XOR violation: cannot specify multiple typed target foreign keys simultaneously."
            )

        if len(non_null_typed) == 1:
            matched_type, matched_id = non_null_typed[0]
            if matched_type != self.dependency_type:
                raise ValueError(
                    f"Dependency type {self.dependency_type.value} does not match supplied target column for {matched_type.value}."
                )
            if self.dependency_id is not None and self.dependency_id != matched_id:
                raise ValueError("Conflicting dependency_id and typed target foreign key.")
            self.dependency_id = matched_id
        else:
            if self.dependency_id is None:
                raise ValueError("A target dependency ID must be provided.")
            if self.dependency_type == DependencyTypeEnum.VENDOR:
                self.vendor_id = self.dependency_id
            elif self.dependency_type == DependencyTypeEnum.CONTROL:
                self.organization_control_id = self.dependency_id
            elif self.dependency_type == DependencyTypeEnum.CLOUD_ASSET:
                self.cloud_asset_id = self.dependency_id
            elif self.dependency_type == DependencyTypeEnum.DATA_ASSET:
                self.data_asset_id = self.dependency_id
            elif self.dependency_type == DependencyTypeEnum.PROCESS:
                self.depends_on_process_id = self.dependency_id

        return self


class ProcessDependencyRead(BaseModel):
    id: int
    organization_id: int
    process_id: int
    dependency_type: DependencyTypeEnum
    dependency_id: int
    vendor_id: Optional[int] = None
    organization_control_id: Optional[int] = None
    cloud_asset_id: Optional[int] = None
    data_asset_id: Optional[int] = None
    depends_on_process_id: Optional[int] = None
    is_single_point_of_failure: bool = False
    failure_propagation_weight: float = 1.0
    recovery_priority_order: int = 1
    notes: Optional[str] = None
    criticality_notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# 4. BUSINESS PROCESS READ WITH RELATIONSHIPS
# ─────────────────────────────────────────────────────────────────────────────

class BusinessProcessRead(BusinessProcessBase):
    id: int
    organization_id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime

    owner: Optional[UserResponse] = None
    active_bia: Optional[BusinessImpactAnalysisRead] = None
    dependencies: List[ProcessDependencyRead] = []

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# 5. DETERMINISTIC OUTAGE CALCULATION & BLAST-RADIUS SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class OutageCostCalculationRequest(BaseModel):
    duration_hours: float = Field(..., ge=0.0, description="Downtime outage duration in hours")
    hourly_downtime_cost: float = Field(..., ge=0.0, description="Hourly variable loss in USD")
    fixed_outage_cost: float = Field(default=0.0, ge=0.0, description="Initial fixed loss in USD")


class OutageCostCalculationResult(BaseModel):
    duration_hours: float
    fixed_outage_cost: float
    hourly_downtime_cost: float
    variable_outage_cost: float
    total_projected_loss: float


class OutageSimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    failing_node_type: DependencyTypeEnum
    failing_node_id: int = Field(..., ge=1)
    outage_duration_hours: float = Field(..., gt=0.0, le=8760.0)

    @field_validator("failing_node_type", mode="before")
    @classmethod
    def normalize_node_type(cls, v: Any) -> Any:
        return _normalize_enum_str(v)


class OutageSimulationAffectedProcess(BaseModel):
    process_id: int
    process_name: str
    criticality_tier: CriticalityTierEnum
    hop_distance: int
    effective_propagation_weight: float
    projected_financial_loss: float
    rto_breached: bool
    mtd_breached: bool


class OutageSimulationResponse(BaseModel):
    failing_node_type: DependencyTypeEnum
    failing_node_id: int
    outage_duration_hours: float
    affected_process_count: int
    tier_1_affected_count: int
    rto_breach_count: int
    mtd_breach_count: int
    total_projected_financial_loss: float
    affected_processes: List[OutageSimulationAffectedProcess]


# ─────────────────────────────────────────────────────────────────────────────
# 6. CONTINUITY RECOVERY STEP SCHEMAS (Batch 5)
# ─────────────────────────────────────────────────────────────────────────────

class ContinuityRecoveryStepCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_order: int = Field(..., ge=1)
    title: str = Field(..., min_length=2, max_length=255)
    description: str = Field(..., min_length=2)
    responsible_role_or_team: Optional[str] = Field(default=None, max_length=128)
    responsible_user_id: Optional[int] = None
    estimated_duration_minutes: int = Field(default=15, ge=0)
    cloud_asset_id: Optional[int] = None
    data_asset_id: Optional[int] = None
    vendor_id: Optional[int] = None
    organization_control_id: Optional[int] = None
    verification_criteria: Optional[str] = None
    is_automated: bool = False


class ContinuityRecoveryStepUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_order: Optional[int] = Field(default=None, ge=1)
    title: Optional[str] = Field(default=None, min_length=2, max_length=255)
    description: Optional[str] = Field(default=None, min_length=2)
    responsible_role_or_team: Optional[str] = Field(default=None, max_length=128)
    responsible_user_id: Optional[int] = None
    estimated_duration_minutes: Optional[int] = Field(default=None, ge=0)
    cloud_asset_id: Optional[int] = None
    data_asset_id: Optional[int] = None
    vendor_id: Optional[int] = None
    organization_control_id: Optional[int] = None
    verification_criteria: Optional[str] = None
    is_automated: Optional[bool] = None


class ContinuityRecoveryStepResponse(BaseModel):
    id: int
    organization_id: int
    continuity_plan_id: int
    step_order: int
    title: str
    description: str
    responsible_role_or_team: Optional[str] = None
    responsible_user_id: Optional[int] = None
    estimated_duration_minutes: int
    cloud_asset_id: Optional[int] = None
    data_asset_id: Optional[int] = None
    vendor_id: Optional[int] = None
    organization_control_id: Optional[int] = None
    verification_criteria: Optional[str] = None
    is_automated: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# 7. RESILIENCE EVIDENCE LINK SCHEMAS (Batch 5)
# ─────────────────────────────────────────────────────────────────────────────

class ResilienceEvidenceLinkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_item_id: int = Field(..., ge=1)
    evidence_type_context: ResilienceEvidenceContextEnum
    notes: Optional[str] = None

    @field_validator("evidence_type_context", mode="before")
    @classmethod
    def normalize_context(cls, v: Any) -> Any:
        return _normalize_enum_str(v)


class ResilienceEvidenceLinkResponse(BaseModel):
    id: int
    organization_id: int
    continuity_plan_id: Optional[int] = None
    exercise_id: Optional[int] = None
    evidence_item_id: int
    evidence_type_context: ResilienceEvidenceContextEnum
    evidence_sha256_snapshot: str
    notes: Optional[str] = None
    linked_by_user_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# 8. CONTINUITY PLAN SCHEMAS (Batch 5)
# ─────────────────────────────────────────────────────────────────────────────

class ContinuityPlanCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_code: str = Field(..., min_length=2, max_length=64)
    title: str = Field(..., min_length=2, max_length=255)
    bia_id: Optional[int] = None
    version_major: int = Field(default=1, ge=1)
    version_minor: int = Field(default=0, ge=0)
    strategy_type: ContinuityStrategyTypeEnum
    activation_triggers: str = Field(..., min_length=2)
    communication_plan: Optional[str] = None
    fallback_location_or_region: Optional[str] = Field(default=None, max_length=255)
    estimated_recovery_hours: float = Field(..., ge=0.0)
    estimated_rpo_hours: float = Field(..., ge=0.0)
    review_frequency_days: int = Field(default=365, ge=1, le=1825)

    @field_validator("strategy_type", mode="before")
    @classmethod
    def normalize_strategy(cls, v: Any) -> Any:
        return _normalize_enum_str(v)


class ContinuityPlanUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(default=None, min_length=2, max_length=255)
    bia_id: Optional[int] = None
    strategy_type: Optional[ContinuityStrategyTypeEnum] = None
    activation_triggers: Optional[str] = Field(default=None, min_length=2)
    communication_plan: Optional[str] = None
    fallback_location_or_region: Optional[str] = Field(default=None, max_length=255)
    estimated_recovery_hours: Optional[float] = Field(default=None, ge=0.0)
    estimated_rpo_hours: Optional[float] = Field(default=None, ge=0.0)
    review_frequency_days: Optional[int] = Field(default=None, ge=1, le=1825)

    @field_validator("strategy_type", mode="before")
    @classmethod
    def normalize_strategy(cls, v: Any) -> Any:
        return _normalize_enum_str(v)


class ContinuityPlanRejectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(..., min_length=2)


class ContinuityPlanResponse(BaseModel):
    id: int
    organization_id: int
    process_id: int
    bia_id: Optional[int] = None
    plan_code: str
    title: str
    version_major: int
    version_minor: int
    version_label: str
    status: ContinuityPlanStatusEnum
    strategy_type: ContinuityStrategyTypeEnum
    activation_triggers: str
    communication_plan: Optional[str] = None
    fallback_location_or_region: Optional[str] = None
    estimated_recovery_hours: float
    estimated_rpo_hours: float
    review_frequency_days: int
    next_review_due_at: Optional[datetime] = None
    plan_hash_sha256: Optional[str] = None
    created_by_user_id: Optional[int] = None
    submitted_by_user_id: Optional[int] = None
    submitted_at: Optional[datetime] = None
    approved_by_user_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    superseded_by_plan_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ContinuityPlanDetailResponse(ContinuityPlanResponse):
    recovery_steps: List[ContinuityRecoveryStepResponse] = []
    total_step_duration_minutes: int = 0
    total_step_duration_hours: float = 0.0
    evidence_links: List[ResilienceEvidenceLinkResponse] = []


# ─────────────────────────────────────────────────────────────────────────────
# 9. RESILIENCE EXERCISE & ESCALATION SCHEMAS (Batch 5)
# ─────────────────────────────────────────────────────────────────────────────

class ResilienceExerciseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    process_id: int = Field(..., ge=1)
    continuity_plan_id: int = Field(..., ge=1)
    exercise_code: str = Field(..., min_length=2, max_length=64)
    title: str = Field(..., min_length=2, max_length=255)
    exercise_type: ExerciseTypeEnum
    scenario_description: str = Field(..., min_length=2)
    scope_notes: Optional[str] = None
    scheduled_start_at: datetime
    triggered_by_incident_id: Optional[int] = None

    @field_validator("exercise_type", mode="before")
    @classmethod
    def normalize_ex_type(cls, v: Any) -> Any:
        return _normalize_enum_str(v)


class ResilienceExerciseStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    started_at: Optional[datetime] = None


class ResilienceExerciseCompleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actual_rto_hours: float = Field(..., ge=0.0)
    actual_rpo_hours: float = Field(..., ge=0.0)
    control_deficiency_observed: bool = False
    minor_exceptions_noted: bool = False
    lessons_learned: Optional[str] = None
    executive_summary: Optional[str] = None
    completed_at: Optional[datetime] = None


class ResilienceExerciseReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_notes: Optional[str] = None


class ResilienceExerciseCancelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: Optional[str] = None


class ExerciseEscalationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    existing_finding_id: Optional[int] = None
    create_finding: bool = True
    organization_control_id: Optional[int] = None
    finding_title: Optional[str] = Field(default=None, max_length=255)
    finding_description: Optional[str] = None
    finding_recommendation: Optional[str] = None
    finding_type: Optional[FindingTypeEnum] = None
    finding_severity: Optional[FindingSeverityEnum] = None

    existing_remediation_plan_id: Optional[int] = None
    create_remediation_plan: bool = False
    remediation_title: Optional[str] = Field(default=None, max_length=255)
    remediation_description: Optional[str] = None
    remediation_owner_user_id: Optional[int] = None
    remediation_due_date: Optional[datetime] = None
    root_cause_classification: Optional[RemediationRootCauseClassificationEnum] = None
    root_cause_analysis: Optional[str] = None

    existing_risk_id: Optional[int] = None
    create_risk: bool = False
    risk_title: Optional[str] = Field(default=None, max_length=255)

    @field_validator("finding_type", "finding_severity", "root_cause_classification", mode="before")
    @classmethod
    def normalize_enums(cls, v: Any) -> Any:
        return _normalize_enum_str(v)


class ResilienceExerciseResponse(BaseModel):
    id: int
    organization_id: int
    process_id: int
    continuity_plan_id: int
    bia_id: Optional[int] = None
    exercise_code: str
    title: str
    exercise_type: ExerciseTypeEnum
    status: ExerciseStatusEnum
    scenario_description: str
    scope_notes: Optional[str] = None
    scheduled_start_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None

    target_rto_hours_snapshot: float
    target_rpo_hours_snapshot: float
    target_mtd_hours_snapshot: float

    actual_rto_hours: Optional[float] = None
    actual_rpo_hours: Optional[float] = None
    rto_variance_hours: Optional[float] = None
    rpo_variance_hours: Optional[float] = None

    rto_breached: bool
    rpo_breached: bool
    mtd_breached: bool
    control_deficiency_observed: bool

    outcome: Optional[ExerciseOutcomeEnum] = None
    lessons_learned: Optional[str] = None
    executive_summary: Optional[str] = None
    review_notes: Optional[str] = None
    result_hash_sha256: Optional[str] = None

    planned_by_user_id: Optional[int] = None
    executed_by_user_id: Optional[int] = None
    reviewed_by_user_id: Optional[int] = None

    finding_id: Optional[int] = None
    remediation_plan_id: Optional[int] = None
    risk_id: Optional[int] = None
    triggered_by_incident_id: Optional[int] = None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResilienceExerciseDetailResponse(ResilienceExerciseResponse):
    evidence_links: List[ResilienceEvidenceLinkResponse] = []


# ─────────────────────────────────────────────────────────────────────────────
# 10. DEPENDENCY HEALTH, IMPACT SUMMARY & DASHBOARD SCHEMAS (Batch 5)
# ─────────────────────────────────────────────────────────────────────────────

class DependencyHealthItem(BaseModel):
    dependency_id: int
    dependency_type: DependencyTypeEnum
    target_id: int
    target_name: str
    health_status: str  # HEALTHY, DEGRADED, CRITICAL
    health_score: float
    is_single_point_of_failure: bool
    failure_propagation_weight: float
    recovery_priority_order: int
    status_detail: str


class ProcessDependencyHealthResponse(BaseModel):
    process_id: int
    process_name: str
    dependency_health_score: float
    total_dependencies: int
    spof_count: int
    unmitigated_spof_count: int
    healthy_count: int
    degraded_count: int
    critical_count: int
    dependencies: List[DependencyHealthItem]


class ProcessImpactSummaryResponse(BaseModel):
    process_id: int
    process_name: str
    criticality_tier: CriticalityTierEnum
    has_active_bia: bool
    active_bia_id: Optional[int] = None
    rto_hours: Optional[float] = None
    rpo_hours: Optional[float] = None
    mtd_hours: Optional[float] = None
    projected_24h_loss: float = 0.0
    total_dependencies: int = 0
    spof_count: int = 0
    unmitigated_spof_count: int = 0
    dependency_health_score: float = 100.0
    active_continuity_plan_id: Optional[int] = None
    active_continuity_plan_version: Optional[str] = None
    latest_exercise_id: Optional[int] = None
    latest_exercise_outcome: Optional[str] = None
    latest_actual_rto_hours: Optional[float] = None
    latest_actual_rpo_hours: Optional[float] = None


class ResilienceDashboardResponse(BaseModel):
    total_processes: int = 0
    active_processes: int = 0
    tier_1_processes: int = 0
    processes_with_approved_bia: int = 0
    bia_coverage_pct: float = 0.0
    total_dependencies: int = 0
    single_point_of_failure_count: int = 0
    max_24h_financial_exposure: float = 0.0
    tier_breakdown: Dict[str, int] = {}

    # Batch 5 Continuity & Empirical Exercise Telemetry
    processes_with_approved_continuity_plan: int = 0
    continuity_plan_coverage_pct: float = 0.0
    overdue_continuity_plan_reviews: int = 0
    total_exercises: int = 0
    completed_or_reviewed_exercises: int = 0
    exercise_pass_rate_pct: float = 0.0
    rto_breach_exercise_count: int = 0
    rpo_breach_exercise_count: int = 0
    mtd_breach_exercise_count: int = 0
    unmitigated_spof_count: int = 0
    average_dependency_health_score: float = 100.0
    resilience_assurance_score: float = 0.0
