from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.continuous_compliance import (
    ComplianceDriftVectorEnum,
    ComplianceDriftSeverityEnum,
    ComplianceDriftStatusEnum,
)


# ── Continuous Compliance Profile Schemas ──────────────────────────────────

class ContinuousComplianceProfileBase(BaseModel):
    profile_name: str = Field("Default Enterprise Assurance Profile", max_length=100)
    is_enabled: bool = True
    evaluation_cadence_hours: int = Field(6, ge=1, le=168)
    drift_critical_threshold: float = Field(20.0, ge=0.0, le=100.0)
    drift_high_threshold: float = Field(15.0, ge=0.0, le=100.0)
    min_control_health_score: float = Field(70.0, ge=0.0, le=100.0)
    max_evidence_age_days: int = Field(90, ge=1, le=730)
    max_open_finding_sla_breach_count: int = Field(0, ge=0)
    auto_trigger_capa_on_critical_drift: bool = True


class ContinuousComplianceProfileUpdate(BaseModel):
    profile_name: Optional[str] = Field(None, max_length=100)
    is_enabled: Optional[bool] = None
    evaluation_cadence_hours: Optional[int] = Field(None, ge=1, le=168)
    drift_critical_threshold: Optional[float] = Field(None, ge=0.0, le=100.0)
    drift_high_threshold: Optional[float] = Field(None, ge=0.0, le=100.0)
    min_control_health_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    max_evidence_age_days: Optional[int] = Field(None, ge=1, le=730)
    max_open_finding_sla_breach_count: Optional[int] = Field(None, ge=0)
    auto_trigger_capa_on_critical_drift: Optional[bool] = None


class ContinuousComplianceProfileResponse(ContinuousComplianceProfileBase):
    id: int
    organization_id: int
    last_evaluated_at: Optional[datetime] = None
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Compliance Drift Schemas ───────────────────────────────────────────────

class ComplianceDriftRecordResponse(BaseModel):
    id: int
    organization_id: int
    organization_control_id: Optional[int] = None
    drift_code: str
    drift_vector: ComplianceDriftVectorEnum
    severity: ComplianceDriftSeverityEnum
    status: ComplianceDriftStatusEnum
    title: str
    description: str
    root_cause_metric: str
    baseline_value: Optional[float] = None
    observed_value: Optional[float] = None
    remediation_plan_id: Optional[int] = None
    detected_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Continuous Assurance Snapshot & Posture Schemas ────────────────────────

class UnifiedAssurancePostureResponse(BaseModel):
    overall_assurance_score: float
    controls_assurance_score: float
    evidence_pipeline_score: float
    regulatory_compliance_score: float
    remediation_sla_score: float
    cloud_identity_posture_score: float
    harmonized_frameworks_score: float
    active_drift_count: int
    critical_drift_count: int
    pillar_breakdown: Dict[str, Any]
    framework_compliance_breakdown: Dict[str, Any]
    last_evaluated_at: datetime
    calculation_version: str = "1.0"


class ContinuousAssuranceSnapshotCreate(BaseModel):
    snapshot_code: str = Field(..., max_length=64)


class ContinuousAssuranceSnapshotResponse(BaseModel):
    id: int
    organization_id: int
    snapshot_code: str
    captured_at: datetime
    overall_assurance_score: float
    controls_assurance_score: float
    evidence_pipeline_score: float
    regulatory_compliance_score: float
    remediation_sla_score: float
    cloud_identity_posture_score: float
    harmonized_frameworks_score: float
    active_drift_count: int
    critical_drift_count: int
    pillar_breakdown: Dict[str, Any]
    framework_compliance_breakdown: Dict[str, Any]
    data_hash_sha256: str
    calculation_version: str
    created_by_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
