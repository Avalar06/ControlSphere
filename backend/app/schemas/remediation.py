from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.remediation import (
    EvidenceVerificationStatusEnum,
    RemediationRootCauseClassificationEnum,
    RemediationSeverityEnum,
    RemediationSourceTypeEnum,
    RemediationStatusEnum,
    ReTestResultEnum,
    SlaStatusEnum,
    TaskStatusEnum,
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Remediation Plan Schemas
# ─────────────────────────────────────────────────────────────────────────────

class RemediationPlanBase(BaseModel):
    plan_code: str = Field(..., min_length=2, max_length=64)
    title: str = Field(..., min_length=2, max_length=255)
    problem_statement: str = Field(..., min_length=5)
    root_cause_classification: RemediationRootCauseClassificationEnum
    source_type: RemediationSourceTypeEnum
    finding_id: Optional[int] = None
    compliance_drift_alert_id: Optional[int] = None
    security_incident_id: Optional[int] = None
    vendor_assessment_id: Optional[int] = None
    audit_id: Optional[int] = None
    severity: RemediationSeverityEnum = RemediationSeverityEnum.MEDIUM
    target_completion_at: Optional[datetime] = None


class RemediationPlanCreate(RemediationPlanBase):
    @model_validator(mode="after")
    def validate_single_source_linkage(self):
        sources = [
            ("FINDING", self.finding_id),
            ("CCM_DRIFT", self.compliance_drift_alert_id),
            ("SECURITY_INCIDENT", self.security_incident_id),
            ("TPRM_ASSESSMENT", self.vendor_assessment_id),
            ("AUDIT", self.audit_id),
        ]
        non_null_sources = [(name, val) for name, val in sources if val is not None]
        if len(non_null_sources) != 1:
            raise ValueError(
                f"Exactly one authoritative source must be populated. Provided: {[name for name, _ in non_null_sources]}"
            )
        matched_type, _ = non_null_sources[0]
        if self.source_type != matched_type:
            raise ValueError(
                f"source_type '{self.source_type}' does not match populated foreign key for '{matched_type}'"
            )
        return self


class RemediationPlanUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    problem_statement: Optional[str] = Field(None, min_length=5)
    root_cause_classification: Optional[RemediationRootCauseClassificationEnum] = None
    severity: Optional[RemediationSeverityEnum] = None
    target_completion_at: Optional[datetime] = None


class RemediationPlanApproveRequest(BaseModel):
    target_completion_at: Optional[datetime] = None
    notes: Optional[str] = None


class RemediationPlanCancelRequest(BaseModel):
    cancellation_notes: str = Field(
        ..., min_length=10, description="Mandatory cancellation justification notes"
    )


class RemediationPlanRejectValidationRequest(BaseModel):
    rejection_notes: str = Field(
        ..., min_length=15, description="Mandatory validation rejection and rework notes"
    )


class RemediationPlanVerifyCloseRequest(BaseModel):
    verification_notes: str = Field(
        ..., min_length=15, description="Mandatory four-eyes independent verification notes"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Remediation Task Schemas
# ─────────────────────────────────────────────────────────────────────────────

class RemediationTaskCreate(BaseModel):
    task_seq: int = Field(..., ge=1)
    title: str = Field(..., min_length=2, max_length=255)
    description: str = Field(..., min_length=5)
    assignee_id: Optional[int] = None
    due_date: Optional[datetime] = None


class RemediationTaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = Field(None, min_length=5)
    assignee_id: Optional[int] = None
    due_date: Optional[datetime] = None
    status: Optional[TaskStatusEnum] = None
    implementation_notes: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# 3. Evidence Link Schemas
# ─────────────────────────────────────────────────────────────────────────────

class RemediationEvidenceLinkCreate(BaseModel):
    evidence_id: int
    notes: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# 4. Re-Test Record Schemas
# ─────────────────────────────────────────────────────────────────────────────

class RemediationReTestCreate(BaseModel):
    test_executed_at: datetime
    test_result: ReTestResultEnum
    metric_observed_value: Optional[float] = None
    evidence_id: Optional[int] = None
    validation_narrative: str = Field(
        ..., min_length=10, description="Empirical test methodology and findings narrative"
    )

    @model_validator(mode="after")
    def validate_pass_requires_evidence(self):
        if self.test_result == ReTestResultEnum.PASS and self.evidence_id is None:
            raise ValueError("PASS re-test result strictly requires an associated evidence_id")
        return self


# ─────────────────────────────────────────────────────────────────────────────
# 5. Read / Response Schemas
# ─────────────────────────────────────────────────────────────────────────────

class RemediationEvidenceLinkRead(BaseModel):
    id: int
    organization_id: int
    remediation_task_id: int
    evidence_id: int
    verification_status: EvidenceVerificationStatusEnum
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RemediationTaskRead(BaseModel):
    id: int
    organization_id: int
    remediation_plan_id: int
    task_seq: int
    title: str
    description: str
    assignee_id: Optional[int] = None
    due_date: Optional[datetime] = None
    status: TaskStatusEnum
    completed_at: Optional[datetime] = None
    implementation_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    evidence_links: List[RemediationEvidenceLinkRead] = []

    model_config = ConfigDict(from_attributes=True)


class RemediationReTestRecordRead(BaseModel):
    id: int
    organization_id: int
    remediation_plan_id: int
    test_executed_at: datetime
    tester_id: int
    test_result: ReTestResultEnum
    metric_observed_value: Optional[float] = None
    evidence_id: Optional[int] = None
    validation_narrative: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RemediationPlanRead(BaseModel):
    id: int
    organization_id: int
    plan_code: str
    title: str
    problem_statement: str
    root_cause_classification: RemediationRootCauseClassificationEnum
    source_type: RemediationSourceTypeEnum
    finding_id: Optional[int] = None
    compliance_drift_alert_id: Optional[int] = None
    security_incident_id: Optional[int] = None
    vendor_assessment_id: Optional[int] = None
    audit_id: Optional[int] = None
    severity: RemediationSeverityEnum
    status: RemediationStatusEnum
    plan_owner_id: int
    approved_by_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    target_completion_at: Optional[datetime] = None
    verified_by_id: Optional[int] = None
    verified_at: Optional[datetime] = None
    verification_notes: Optional[str] = None
    cancellation_notes: Optional[str] = None
    validation_attempts_count: int
    rei_score: Optional[float] = None
    ttr_hours: Optional[float] = None
    is_immutable: bool
    created_at: datetime
    updated_at: datetime

    # Dynamically calculated SLA properties
    sla_status: Optional[SlaStatusEnum] = None
    remaining_hours: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class RemediationPlanDetailRead(RemediationPlanRead):
    tasks: List[RemediationTaskRead] = []
    retest_records: List[RemediationReTestRecordRead] = []


class RemediationOverviewResponse(BaseModel):
    total_plans: int
    open_plans: int
    critical_or_high_plans: int
    pending_validation_plans: int
    sla_breached_plans: int
    average_rei_score: Optional[float] = None
    average_ttr_hours: Optional[float] = None
    status_distribution: dict[str, int]
    severity_distribution: dict[str, int]
    source_distribution: dict[str, int]
    sla_distribution: dict[str, int]
