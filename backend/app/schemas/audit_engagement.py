from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.audit_engagement import (
    AuditOpinionEnum,
    AuditStatusEnum,
    AuditTypeEnum,
    ProcedureResultEnum,
)


# ─────────────────────────────────────────────────────────────────────────────
# Audit Schemas
# ─────────────────────────────────────────────────────────────────────────────
class AuditCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    audit_type: AuditTypeEnum = AuditTypeEnum.INTERNAL
    audit_reference: Optional[str] = Field(None, max_length=100)
    objective: str = Field(..., min_length=10)
    scope_description: Optional[str] = None
    methodology: Optional[str] = None
    limitations: Optional[str] = None
    framework_id: Optional[int] = None
    lead_auditor_id: Optional[int] = None
    audit_team_notes: Optional[str] = None
    planned_start_date: Optional[date] = None
    planned_end_date: Optional[date] = None

    @model_validator(mode="after")
    def validate_dates(self) -> "AuditCreate":
        if self.planned_start_date and self.planned_end_date:
            if self.planned_end_date < self.planned_start_date:
                raise ValueError("planned_end_date must be on or after planned_start_date.")
        return self


class AuditUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    audit_type: Optional[AuditTypeEnum] = None
    audit_reference: Optional[str] = Field(None, max_length=100)
    objective: Optional[str] = Field(None, min_length=10)
    scope_description: Optional[str] = None
    methodology: Optional[str] = None
    limitations: Optional[str] = None
    summary: Optional[str] = None
    framework_id: Optional[int] = None
    lead_auditor_id: Optional[int] = None
    audit_team_notes: Optional[str] = None
    planned_start_date: Optional[date] = None
    planned_end_date: Optional[date] = None
    actual_start_date: Optional[date] = None
    actual_end_date: Optional[date] = None


class AuditStatusUpdate(BaseModel):
    status: AuditStatusEnum
    notes: Optional[str] = None


class AuditOpinionCreate(BaseModel):
    opinion: AuditOpinionEnum = Field(
        ...,
        description="Human-authoritative audit opinion. Never AI-generated."
    )
    opinion_notes: Optional[str] = Field(None, min_length=10)

    @field_validator("opinion")
    @classmethod
    def opinion_not_unissued(cls, v: AuditOpinionEnum) -> AuditOpinionEnum:
        if v == AuditOpinionEnum.UNISSUED:
            raise ValueError("Cannot formally issue an UNISSUED opinion. Choose a substantive opinion.")
        return v


class AuditClosure(BaseModel):
    closure_notes: str = Field(..., min_length=5)


class AuditResponse(BaseModel):
    id: int
    organization_id: int
    title: str
    audit_type: AuditTypeEnum
    audit_reference: Optional[str]
    objective: str
    scope_description: Optional[str]
    methodology: Optional[str]
    limitations: Optional[str]
    summary: Optional[str]
    framework_id: Optional[int]
    lead_auditor_id: Optional[int]
    audit_team_notes: Optional[str]
    planned_start_date: Optional[date]
    planned_end_date: Optional[date]
    actual_start_date: Optional[date]
    actual_end_date: Optional[date]
    status: AuditStatusEnum
    opinion: AuditOpinionEnum
    opinion_issued_by_id: Optional[int]
    opinion_issued_at: Optional[datetime]
    opinion_notes: Optional[str]
    closed_at: Optional[datetime]
    closed_by_id: Optional[int]
    closure_notes: Optional[str]
    created_by_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    # Computed counts
    scope_controls_count: int = 0
    procedures_count: int = 0
    findings_count: int = 0

    model_config = {"from_attributes": True}


class AuditDetailResponse(AuditResponse):
    scope_controls: List[Any] = []
    procedures: List[Any] = []
    finding_links: List[Any] = []

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Audit Scope Schemas
# ─────────────────────────────────────────────────────────────────────────────
class AuditScopeAdd(BaseModel):
    organization_control_id: int
    scope_notes: Optional[str] = None


class AuditScopeResponse(BaseModel):
    id: int
    audit_id: int
    organization_control_id: int
    scope_notes: Optional[str]
    created_by_id: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Audit Procedure Schemas
# ─────────────────────────────────────────────────────────────────────────────
class AuditProcedureCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    objective: Optional[str] = None
    test_steps: Optional[str] = None
    expected_result: Optional[str] = None
    actual_result: Optional[str] = None
    assessment_method: Optional[str] = Field(None, max_length=100)
    result: ProcedureResultEnum = ProcedureResultEnum.NOT_STARTED
    execution_notes: Optional[str] = None
    limitations: Optional[str] = None
    organization_control_id: Optional[int] = None
    tester_id: Optional[int] = None
    execution_date: Optional[date] = None


class AuditProcedureUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    objective: Optional[str] = None
    test_steps: Optional[str] = None
    expected_result: Optional[str] = None
    actual_result: Optional[str] = None
    assessment_method: Optional[str] = Field(None, max_length=100)
    result: Optional[ProcedureResultEnum] = None
    execution_notes: Optional[str] = None
    limitations: Optional[str] = None
    organization_control_id: Optional[int] = None
    tester_id: Optional[int] = None
    execution_date: Optional[date] = None


class AuditProcedureResponse(BaseModel):
    id: int
    audit_id: int
    organization_control_id: Optional[int]
    title: str
    objective: Optional[str]
    test_steps: Optional[str]
    expected_result: Optional[str]
    actual_result: Optional[str]
    assessment_method: Optional[str]
    result: ProcedureResultEnum
    execution_notes: Optional[str]
    limitations: Optional[str]
    tester_id: Optional[int]
    execution_date: Optional[date]
    created_by_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    evidence_count: int = 0

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Audit Procedure Evidence Schemas
# ─────────────────────────────────────────────────────────────────────────────
class AuditEvidenceLinkCreate(BaseModel):
    evidence_id: int
    link_notes: Optional[str] = None


class AuditEvidenceLinkResponse(BaseModel):
    id: int
    procedure_id: int
    evidence_id: int
    link_notes: Optional[str]
    created_by_id: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Audit Finding Link Schemas
# ─────────────────────────────────────────────────────────────────────────────
class AuditFindingLinkCreate(BaseModel):
    finding_id: int
    source_procedure_id: Optional[int] = None
    link_notes: Optional[str] = None


class AuditFindingLinkResponse(BaseModel):
    id: int
    audit_id: int
    finding_id: int
    source_procedure_id: Optional[int]
    link_notes: Optional[str]
    created_by_id: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Readiness Metrics Schema
# ─────────────────────────────────────────────────────────────────────────────
class AuditReadinessResponse(BaseModel):
    audit_id: int
    audit_status: AuditStatusEnum
    # Scope
    controls_in_scope: int
    controls_with_evidence: int
    controls_assessed: int
    # Procedures
    procedures_total: int
    procedures_not_started: int
    procedures_in_progress: int
    procedures_passed: int
    procedures_partially_passed: int
    procedures_failed: int
    procedures_not_applicable: int
    procedures_completed: int  # passed + partially_passed + failed + n/a
    # Findings
    findings_total: int
    findings_open: int
    findings_critical: int
    findings_high: int
    findings_in_remediation: int
    # Risk linkage
    active_exceptions_in_scope: int
    # Readiness Score
    readiness_score: float  # 0.0 – 100.0 percent
    readiness_band: str  # "NOT_READY", "PARTIALLY_READY", "SUBSTANTIALLY_READY", "READY"
    readiness_blockers: List[str]

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Stats Schema
# ─────────────────────────────────────────────────────────────────────────────
class AuditStatsResponse(BaseModel):
    total_audits: int
    planned_count: int
    in_progress_count: int
    completed_count: int
    closed_count: int
    open_findings_across_audits: int
    critical_findings_count: int
    unissued_opinion_count: int

    model_config = {"from_attributes": True}
