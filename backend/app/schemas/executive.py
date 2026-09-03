from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.executive import (
    ArtifactTypeEnum,
    BriefingStatusEnum,
    DossierStatusEnum,
    DossierTypeEnum,
    ExportFormatEnum,
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Executive Telemetry Schemas
# ─────────────────────────────────────────────────────────────────────────────

class DomainPostureItem(BaseModel):
    domain_key: str
    domain_name: str
    score: float
    weight: float
    status: str
    summary: Dict[str, Any] = Field(default_factory=dict)


class TopRiskItem(BaseModel):
    id: int
    title: str
    risk_category: str
    inherent_score: int
    residual_score: Optional[int] = None
    appetite_status: str


class CriticalFindingItem(BaseModel):
    id: int
    title: str
    severity: str
    status: str
    due_date: Optional[date] = None
    owner_name: Optional[str] = None


class ExecutiveTelemetryResponse(BaseModel):
    overall_posture_score: float
    inherent_risk_index: float
    residual_risk_index: float
    risk_reduction_percentage: float
    financial_exposure_ale: float
    var_95_exposure: float
    financial_appetite_utilization_pct: float
    audit_readiness_index: float
    remediation_sla_health_score: float
    framework_compliance_summary: Dict[str, Any] = Field(default_factory=dict)
    domain_posture_breakdown: Dict[str, Any] = Field(default_factory=dict)
    top_risks: List[TopRiskItem] = Field(default_factory=list)
    critical_findings: List[CriticalFindingItem] = Field(default_factory=list)
    calculated_at: datetime


class ExecutiveTrendDataPoint(BaseModel):
    timestamp: datetime
    overall_posture_score: float
    inherent_risk_index: float
    residual_risk_index: float
    financial_exposure_ale: float
    audit_readiness_index: float
    remediation_sla_health_score: float


class ExecutiveTrendsResponse(BaseModel):
    window_days: int
    data_points: List[ExecutiveTrendDataPoint] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Executive Snapshot Schemas
# ─────────────────────────────────────────────────────────────────────────────

class ExecutiveSnapshotCreate(BaseModel):
    snapshot_code: str = Field(..., min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_\-\.]+$")
    notes: Optional[str] = None


class ExecutiveSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    snapshot_code: str
    calculated_at: datetime
    overall_posture_score: float
    inherent_risk_index: float
    residual_risk_index: float
    financial_exposure_ale: float
    var_95_exposure: float
    audit_readiness_index: float
    remediation_sla_health_score: float
    framework_compliance_summary: Dict[str, Any]
    domain_posture_breakdown: Dict[str, Any]
    top_risks_snapshot: List[Any]
    critical_findings_snapshot: List[Any]
    source_manifest: Dict[str, Any]
    data_hash_sha256: str
    created_by_id: int
    created_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# 3. Executive Dossier Schemas
# ─────────────────────────────────────────────────────────────────────────────

class ExecutiveDossierCreate(BaseModel):
    dossier_code: str = Field(..., min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_\-\.]+$")
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    dossier_type: DossierTypeEnum = DossierTypeEnum.BOARD_SUMMARY
    scope_framework_ids: List[int] = Field(default_factory=list)
    snapshot_id: Optional[int] = None
    executive_summary: Optional[str] = None
    regulatory_commentary: Optional[str] = None


class ExecutiveDossierUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    scope_framework_ids: Optional[List[int]] = None
    snapshot_id: Optional[int] = None
    executive_summary: Optional[str] = None
    regulatory_commentary: Optional[str] = None


class ExecutiveDossierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    dossier_code: str
    title: str
    description: Optional[str] = None
    dossier_type: DossierTypeEnum
    status: DossierStatusEnum
    scope_framework_ids: List[int]
    snapshot_id: Optional[int] = None
    executive_summary: Optional[str] = None
    regulatory_commentary: Optional[str] = None
    compiled_sections: Optional[Dict[str, Any]] = None
    compiled_at: Optional[datetime] = None
    compiled_by_id: Optional[int] = None
    finalized_at: Optional[datetime] = None
    finalized_by_id: Optional[int] = None
    created_by_id: int
    created_at: datetime
    updated_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# 4. Executive Briefing Schemas
# ─────────────────────────────────────────────────────────────────────────────

class ExecutiveBriefingCreate(BaseModel):
    briefing_code: str = Field(..., min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_\-\.]+$")
    title: str = Field(..., min_length=3, max_length=255)
    reporting_period_start: date
    reporting_period_end: date
    snapshot_id: int
    executive_summary: str = Field(..., min_length=10)
    key_achievements: List[str] = Field(default_factory=list)
    emerging_risks: List[str] = Field(default_factory=list)
    strategic_recommendations: Optional[str] = None


class ExecutiveBriefingReview(BaseModel):
    approved: bool
    review_notes: Optional[str] = None


class ExecutiveBriefingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    briefing_code: str
    title: str
    reporting_period_start: date
    reporting_period_end: date
    status: BriefingStatusEnum
    snapshot_id: int
    executive_summary: str
    key_achievements: List[str]
    emerging_risks: List[str]
    strategic_recommendations: Optional[str] = None
    period_over_period_deltas: Dict[str, Any] = Field(default_factory=dict)
    generated_by_id: int
    approved_by_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# 5. Forensic Export Artifact Schemas
# ─────────────────────────────────────────────────────────────────────────────

class ExecutiveExportArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    export_code: str
    export_format: ExportFormatEnum
    artifact_type: ArtifactTypeEnum
    dossier_id: Optional[int] = None
    briefing_id: Optional[int] = None
    snapshot_id: Optional[int] = None
    storage_key: str
    original_filename: str
    mime_type: str
    file_size_bytes: int
    sha256_checksum: str
    generated_by_id: int
    generated_at: datetime
