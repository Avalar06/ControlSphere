from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.privacy import (
    DataSensitivityLevel,
    DPIARiskBand,
    JurisdictionRiskTier,
    PrivacyApprovalStatus,
    ProcessingLegalBasis,
    ProcessingLifecycleState,
    TransferMechanism,
)


# ─── Data Asset Schemas ────────────────────────────────────────────────────────

class DataAssetBase(BaseModel):
    asset_code: str = Field(..., min_length=2, max_length=64, description="Unique asset code, e.g. DA-001")
    name: str = Field(..., min_length=2, max_length=255, description="Data asset / store name")
    description: Optional[str] = None
    data_sensitivity_level: DataSensitivityLevel = DataSensitivityLevel.INTERNAL
    data_volume_range: str = Field("LOW", description="Volume tier: LOW (<10k), MEDIUM (10k-1M), HIGH (>1M)")
    storage_type: str = Field("POSTGRES_DB", max_length=64)
    hosting_jurisdiction: str = Field("EU_EEA", max_length=64)
    is_encrypted_at_rest: bool = True
    is_encrypted_in_transit: bool = True
    is_pseudonymized: bool = False
    retention_period_months: Optional[int] = Field(12, ge=1, le=1200)

    # Cross-Module Links
    business_process_id: Optional[int] = None
    ai_system_id: Optional[int] = None
    vendor_id: Optional[int] = None


class DataAssetCreate(DataAssetBase):
    pass


class DataAssetUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    data_sensitivity_level: Optional[DataSensitivityLevel] = None
    data_volume_range: Optional[str] = None
    storage_type: Optional[str] = None
    hosting_jurisdiction: Optional[str] = None
    is_encrypted_at_rest: Optional[bool] = None
    is_encrypted_in_transit: Optional[bool] = None
    is_pseudonymized: Optional[bool] = None
    retention_period_months: Optional[int] = Field(None, ge=1, le=1200)
    business_process_id: Optional[int] = None
    ai_system_id: Optional[int] = None
    vendor_id: Optional[int] = None


class DataAssetResponse(DataAssetBase):
    id: int
    organization_id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── Processing Activity (RoPA) Schemas ────────────────────────────────────────

class ProcessingActivityBase(BaseModel):
    activity_code: str = Field(..., min_length=2, max_length=64, description="Unique RoPA code, e.g. ROPA-HR-001")
    name: str = Field(..., min_length=2, max_length=255, description="Activity name")
    purpose_description: str = Field(..., min_length=5, description="GDPR Art 30 processing purpose")
    legal_basis: ProcessingLegalBasis
    data_subject_categories: str = Field(..., description="Categories of data subjects (comma-separated or JSON string)")
    personal_data_categories: str = Field(..., description="Categories of personal data processed")

    is_special_category_data: bool = False
    is_automated_decision_making: bool = False
    is_large_scale_monitoring: bool = False
    is_vulnerable_subjects: bool = False
    is_cross_border_transfer: bool = False

    transfer_mechanism: TransferMechanism = TransferMechanism.NONE_INTRA_EEA
    destination_country: Optional[str] = Field(None, max_length=64)
    security_measures_summary: Optional[str] = None
    data_controller_name: Optional[str] = Field(None, max_length=255)

    # Cross-Module Links
    business_process_id: Optional[int] = None
    ai_system_id: Optional[int] = None
    vendor_id: Optional[int] = None


class ProcessingActivityCreate(ProcessingActivityBase):
    pass


class ProcessingActivityUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    purpose_description: Optional[str] = Field(None, min_length=5)
    legal_basis: Optional[ProcessingLegalBasis] = None
    data_subject_categories: Optional[str] = None
    personal_data_categories: Optional[str] = None
    is_special_category_data: Optional[bool] = None
    is_automated_decision_making: Optional[bool] = None
    is_large_scale_monitoring: Optional[bool] = None
    is_vulnerable_subjects: Optional[bool] = None
    is_cross_border_transfer: Optional[bool] = None
    transfer_mechanism: Optional[TransferMechanism] = None
    destination_country: Optional[str] = None
    security_measures_summary: Optional[str] = None
    data_controller_name: Optional[str] = None
    business_process_id: Optional[int] = None
    ai_system_id: Optional[int] = None
    vendor_id: Optional[int] = None


class ProcessingActivityStatusUpdate(BaseModel):
    lifecycle_state: ProcessingLifecycleState
    notes: Optional[str] = None


class ProcessingActivityResponse(ProcessingActivityBase):
    id: int
    organization_id: int
    lifecycle_state: ProcessingLifecycleState
    dpo_approval_status: PrivacyApprovalStatus
    owner_id: int
    approved_by_dpo_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── DPIA Assessment Schemas ───────────────────────────────────────────────────

class DPIABase(BaseModel):
    assessment_code: str = Field(..., min_length=2, max_length=64, description="Unique DPIA code, e.g. DPIA-001")
    processing_activity_id: int

    # Subjective/Assessment inputs (0.0 - 100.0)
    necessity_proportionality_score: float = Field(100.0, ge=0.0, le=100.0)
    data_subject_rights_score: float = Field(100.0, ge=0.0, le=100.0)
    safeguards_mitigation_score: float = Field(0.0, ge=0.0, le=100.0)

    # Risk Trigger Flags
    automated_decision_making_risk: bool = False
    large_scale_monitoring_risk: bool = False
    vulnerable_subjects_risk: bool = False
    prior_consultation_required: bool = False

    remediation_plan_id: Optional[int] = None


class DPIACreate(DPIABase):
    pass


class DPIAUpdate(BaseModel):
    necessity_proportionality_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    data_subject_rights_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    safeguards_mitigation_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    automated_decision_making_risk: Optional[bool] = None
    large_scale_monitoring_risk: Optional[bool] = None
    vulnerable_subjects_risk: Optional[bool] = None
    prior_consultation_required: Optional[bool] = None
    remediation_plan_id: Optional[int] = None


class DPIAReviewRequest(BaseModel):
    decision: PrivacyApprovalStatus = Field(..., description="APPROVED or REJECTED")
    recommendation_notes: str = Field(..., min_length=5, description="DPO recommendation and audit commentary")


class DPIAResponse(DPIABase):
    id: int
    organization_id: int
    inherent_risk_score: float
    residual_risk_score: float
    risk_band: DPIARiskBand
    dpo_consultation_status: PrivacyApprovalStatus
    dpo_recommendation_notes: Optional[str] = None
    dpo_reviewed_by_id: Optional[int] = None
    dpo_reviewed_at: Optional[datetime] = None
    created_by_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── Data Transfer Assessment Schemas ──────────────────────────────────────────

class DataTransferBase(BaseModel):
    transfer_code: str = Field(..., min_length=2, max_length=64, description="Unique transfer code, e.g. TIA-US-001")
    processing_activity_id: int
    source_country: str = Field("EU_EEA", max_length=64)
    destination_country: str = Field(..., min_length=2, max_length=64)
    destination_jurisdiction_tier: JurisdictionRiskTier = JurisdictionRiskTier.MODERATE_SAFEGUARDS_REQUIRED
    transfer_mechanism: TransferMechanism = TransferMechanism.STANDARD_CONTRACTUAL_CLAUSES_SCC

    supplementary_safeguards_description: Optional[str] = None
    supplementary_measures_score: float = Field(0.0, ge=0.0, le=30.0)
    government_access_risk_score: float = Field(50.0, ge=0.0, le=100.0)
    legal_remedies_score: float = Field(50.0, ge=0.0, le=100.0)
    audit_notes: Optional[str] = None


class DataTransferCreate(DataTransferBase):
    pass


class DataTransferUpdate(BaseModel):
    destination_country: Optional[str] = Field(None, min_length=2, max_length=64)
    destination_jurisdiction_tier: Optional[JurisdictionRiskTier] = None
    transfer_mechanism: Optional[TransferMechanism] = None
    supplementary_safeguards_description: Optional[str] = None
    supplementary_measures_score: Optional[float] = Field(None, ge=0.0, le=30.0)
    government_access_risk_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    legal_remedies_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    audit_notes: Optional[str] = None


class DataTransferReviewRequest(BaseModel):
    decision: PrivacyApprovalStatus = Field(..., description="APPROVED or REJECTED")
    reviewer_notes: str = Field(..., min_length=5, description="Review commentary")


class DataTransferResponse(DataTransferBase):
    id: int
    organization_id: int
    transfer_risk_index: float
    approval_status: PrivacyApprovalStatus
    requested_by_id: int
    approved_by_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── Posture Summary Schema ────────────────────────────────────────────────────

class PrivacyPostureSummaryResponse(BaseModel):
    total_data_assets: int
    total_processing_activities: int
    active_ropa_count: int
    high_risk_processing_count: int
    cross_border_transfers_count: int
    pending_dpia_approvals: int
    pending_transfer_approvals: int
    average_residual_risk_score: float
    risk_band_distribution: Dict[str, int]
    legal_basis_distribution: Dict[str, int]
    sensitivity_distribution: Dict[str, int]


# ─── Calculation Preview Schemas ───────────────────────────────────────────────

class DPIACalculatePreviewRequest(BaseModel):
    sensitivity_level: DataSensitivityLevel = DataSensitivityLevel.INTERNAL
    volume_tier: str = "LOW"
    is_special_category: bool = False
    automated_decision_making_risk: bool = False
    large_scale_monitoring_risk: bool = False
    vulnerable_subjects_risk: bool = False
    safeguards_mitigation_score: float = Field(0.0, ge=0.0, le=100.0)
    has_threat_exposure: bool = False


class DPIACalculatePreviewResponse(BaseModel):
    inherent_risk_score: float
    residual_risk_score: float
    risk_band: DPIARiskBand
    prior_consultation_required: bool


class DataTransferCalculatePreviewRequest(BaseModel):
    destination_jurisdiction_tier: JurisdictionRiskTier = JurisdictionRiskTier.MODERATE_SAFEGUARDS_REQUIRED
    transfer_mechanism: TransferMechanism = TransferMechanism.STANDARD_CONTRACTUAL_CLAUSES_SCC
    supplementary_measures_score: float = Field(0.0, ge=0.0, le=30.0)


class DataTransferCalculatePreviewResponse(BaseModel):
    transfer_risk_index: float
