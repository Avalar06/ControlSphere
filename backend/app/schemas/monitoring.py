from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.monitoring import (
    ControlHealthStatusEnum,
    DriftAlertSeverityEnum,
    DriftAlertStatusEnum,
    DriftAlertTypeEnum,
    EvaluationTriggerEnum,
)


class ControlHealthSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    organization_control_id: int
    health_score: float
    health_status: ControlHealthStatusEnum
    evidence_freshness_score: float
    assessment_currency_score: float
    finding_penalty_score: float
    exception_penalty_score: float
    active_findings_count: int
    critical_high_findings_count: int
    active_exceptions_count: int
    accepted_evidence_count: int
    days_since_last_evidence: Optional[int] = None
    days_since_last_assessment: Optional[int] = None
    evaluated_at: datetime
    evaluation_trigger: EvaluationTriggerEnum


class ControlHealthSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_control_id: int
    control_code: Optional[str] = None
    control_title: Optional[str] = None
    category_code: Optional[str] = None
    function_code: Optional[str] = None
    implementation_status: str
    health_score: float
    health_status: ControlHealthStatusEnum
    evidence_freshness_score: float
    assessment_currency_score: float
    finding_penalty_score: float
    exception_penalty_score: float
    active_findings_count: int
    critical_high_findings_count: int
    active_exceptions_count: int
    accepted_evidence_count: int
    days_since_last_evidence: Optional[int] = None
    days_since_last_assessment: Optional[int] = None
    last_evaluated_at: Optional[datetime] = None
    active_drift_alerts_count: int = 0


class ComplianceDriftAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    organization_control_id: int
    alert_type: DriftAlertTypeEnum
    severity: DriftAlertSeverityEnum
    status: DriftAlertStatusEnum
    title: str
    description: str
    remediation_guidance: Optional[str] = None
    acknowledged_by_id: Optional[int] = None
    acknowledged_at: Optional[datetime] = None
    resolved_by_id: Optional[int] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ComplianceDriftAlertResolve(BaseModel):
    resolution_notes: str = Field(..., min_length=5, max_length=2000)


class ComplianceDriftAlertDismiss(BaseModel):
    justification: str = Field(..., min_length=5, max_length=2000)


class MonitoringConfigUpdate(BaseModel):
    frequency_hours: Optional[int] = Field(None, ge=1, le=168)
    is_enabled: Optional[bool] = None
    evidence_max_age_days: Optional[int] = Field(None, ge=7, le=365)
    assessment_max_age_days: Optional[int] = Field(None, ge=30, le=730)
    exception_warning_window_days: Optional[int] = Field(None, ge=1, le=60)
    finding_sla_critical_days: Optional[int] = Field(None, ge=1, le=90)
    finding_sla_high_days: Optional[int] = Field(None, ge=1, le=180)


class MonitoringConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    frequency_hours: int
    is_enabled: bool
    evidence_max_age_days: int
    assessment_max_age_days: int
    exception_warning_window_days: int
    finding_sla_critical_days: int
    finding_sla_high_days: int
    last_run_at: Optional[datetime] = None
    last_run_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class MonitoringOverviewResponse(BaseModel):
    average_health_score: float
    overall_health_status: ControlHealthStatusEnum
    total_monitored_controls: int
    healthy_controls_count: int
    degraded_controls_count: int
    at_risk_controls_count: int
    failing_controls_count: int
    active_drift_alerts_count: int
    critical_drift_alerts_count: int
    high_drift_alerts_count: int
    medium_drift_alerts_count: int
    low_drift_alerts_count: int
    evidence_freshness_aggregate_pct: float
    controls_assessed_currency_pct: float
    last_evaluation_run: Optional[datetime] = None


class EvaluationRunResponse(BaseModel):
    evaluated_controls_count: int
    alerts_generated_count: int
    alerts_auto_resolved_count: int
    average_health_score: float
    evaluated_at: datetime
