from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.privacy import DataSensitivityLevel
from app.models.data_governance import (
    DataAssetLifecycleEnum,
    DataAssetTypeEnum,
    DataClassificationApprovalStatusEnum,
    DataClassificationChangeTypeEnum,
    DataClassificationRecordStatusEnum,
    DataClassificationSchemeStatusEnum,
    DataCloudHostingRoleEnum,
    DataControlObjectiveEnum,
    DataDisposalMethodEnum,
    DataEvidencePurposeEnum,
    DataLineageRelationshipTypeEnum,
    DataLineageStatusEnum,
    DataOwnerTransferStatusEnum,
    DataProcessingUsageRoleEnum,
)


def _strip_str(v: Any) -> Any:
    if isinstance(v, str):
        return v.strip()
    return v


# ─────────────────────────────────────────────────────────────────────────────
# 1. CLASSIFICATION SCHEME & LEVEL SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class DataClassificationLevelCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level_code: str = Field(..., min_length=2, max_length=64)
    name: str = Field(..., min_length=2, max_length=128)
    description: Optional[str] = None
    ordinal_rank: int = Field(..., ge=1, le=10)
    mapped_sensitivity_level: DataSensitivityLevel
    requires_encryption_at_rest: bool = True
    requires_encryption_in_transit: bool = True
    requires_four_eyes_approval: bool = False
    default_retention_months: Optional[int] = Field(None, ge=1, le=1200)
    required_disposal_method: Optional[DataDisposalMethodEnum] = None

    @field_validator("level_code", "name", mode="before")
    @classmethod
    def strip_text(cls, v: Any) -> Any:
        return _strip_str(v)


class DataClassificationLevelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    scheme_id: int
    level_code: str
    name: str
    description: Optional[str] = None
    ordinal_rank: int
    mapped_sensitivity_level: DataSensitivityLevel
    requires_encryption_at_rest: bool
    requires_encryption_in_transit: bool
    requires_four_eyes_approval: bool
    default_retention_months: Optional[int] = None
    required_disposal_method: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DataClassificationSchemeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scheme_code: str = Field(..., min_length=2, max_length=64)
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    version: int = Field(1, ge=1, le=1000)
    is_default: bool = False

    @field_validator("scheme_code", "name", mode="before")
    @classmethod
    def strip_text(cls, v: Any) -> Any:
        return _strip_str(v)


class DataClassificationSchemeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    scheme_code: str
    name: str
    description: Optional[str] = None
    version: int
    status: str
    is_default: bool
    created_by_id: int
    approved_by_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    levels: List[DataClassificationLevelResponse] = []
    created_at: datetime
    updated_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# 2. GOVERNED DATA ASSET SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class GovernedDataAssetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_code: str = Field(..., min_length=2, max_length=64)
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    asset_type: DataAssetTypeEnum = DataAssetTypeEnum.DATABASE_TABLE
    initial_lifecycle_state: DataAssetLifecycleEnum = DataAssetLifecycleEnum.REGISTERED
    data_sensitivity_level: DataSensitivityLevel = DataSensitivityLevel.INTERNAL
    data_volume_range: str = Field("LOW", min_length=2, max_length=64)
    storage_type: str = Field("POSTGRES_DB", min_length=2, max_length=64)
    hosting_jurisdiction: str = Field("EU_EEA", min_length=2, max_length=64)
    is_encrypted_at_rest: bool = True
    is_encrypted_in_transit: bool = True
    is_pseudonymized: bool = False
    retention_period_months: Optional[int] = Field(12, ge=1, le=1200)

    owner_id: Optional[int] = None
    steward_id: Optional[int] = None
    cloud_asset_id: Optional[int] = None
    business_process_id: Optional[int] = None
    ai_system_id: Optional[int] = None
    vendor_id: Optional[int] = None

    @field_validator("asset_code", "name", "storage_type", "hosting_jurisdiction", mode="before")
    @classmethod
    def strip_text(cls, v: Any) -> Any:
        return _strip_str(v)


class GovernedDataAssetUpdate(BaseModel):
    """Strict metadata update schema — excludes sensitivity, classification, owner, and lifecycle."""
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    asset_type: Optional[DataAssetTypeEnum] = None
    data_volume_range: Optional[str] = Field(None, min_length=2, max_length=64)
    storage_type: Optional[str] = Field(None, min_length=2, max_length=64)
    hosting_jurisdiction: Optional[str] = Field(None, min_length=2, max_length=64)
    is_encrypted_at_rest: Optional[bool] = None
    is_encrypted_in_transit: Optional[bool] = None
    is_pseudonymized: Optional[bool] = None
    retention_period_months: Optional[int] = Field(None, ge=1, le=1200)
    business_process_id: Optional[int] = None
    ai_system_id: Optional[int] = None
    vendor_id: Optional[int] = None

    @field_validator("name", "storage_type", "hosting_jurisdiction", mode="before")
    @classmethod
    def strip_text(cls, v: Any) -> Any:
        return _strip_str(v)


class GovernedDataAssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    asset_code: str
    name: str
    description: Optional[str] = None
    asset_type: str
    lifecycle_state: str
    data_sensitivity_level: DataSensitivityLevel
    data_volume_range: str
    storage_type: str
    hosting_jurisdiction: str
    is_encrypted_at_rest: bool
    is_encrypted_in_transit: bool
    is_pseudonymized: bool
    retention_period_months: Optional[int] = None

    owner_id: int
    steward_id: Optional[int] = None
    cloud_asset_id: Optional[int] = None
    business_process_id: Optional[int] = None
    ai_system_id: Optional[int] = None
    vendor_id: Optional[int] = None

    classification_scheme_id: Optional[int] = None
    classification_level_id: Optional[int] = None
    classification_status: str
    classified_by_id: Optional[int] = None
    classification_approved_by_id: Optional[int] = None
    classification_approved_at: Optional[datetime] = None
    last_reviewed_at: Optional[datetime] = None

    owner_transfer_status: str = "NONE"
    pending_owner_id: Optional[int] = None
    owner_transfer_requested_by_id: Optional[int] = None
    owner_transfer_justification: Optional[str] = None

    deprecation_notes: Optional[str] = None
    disposal_method: Optional[str] = None
    retirement_requested_by_id: Optional[int] = None
    retired_by_id: Optional[int] = None
    retired_at: Optional[datetime] = None
    retirement_notes: Optional[str] = None
    retirement_evidence_id: Optional[int] = None

    created_at: datetime
    updated_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# 3. CLASSIFICATION RECORD & APPROVAL SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class DataClassificationRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scheme_id: int
    level_id: int
    justification: str = Field(..., min_length=5, max_length=2000)
    require_approval: bool = False

    @field_validator("justification", mode="before")
    @classmethod
    def strip_justification(cls, v: Any) -> Any:
        return _strip_str(v)


class DataClassificationRejectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rejection_reason: str = Field(..., min_length=5, max_length=2000)

    @field_validator("rejection_reason", mode="before")
    @classmethod
    def strip_reason(cls, v: Any) -> Any:
        return _strip_str(v)


class DataClassificationRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    data_asset_id: int
    version: int
    scheme_id: int
    level_id: int
    previous_level_id: Optional[int] = None
    previous_sensitivity_level: Optional[DataSensitivityLevel] = None
    new_sensitivity_level: DataSensitivityLevel
    change_type: str
    status: str
    justification: str
    requested_by_id: int
    approved_by_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    created_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# 4. OWNERSHIP, LIFECYCLE & RETIREMENT SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class DataOwnershipUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner_id: Optional[int] = None
    steward_id: Optional[int] = None
    justification: str = Field(..., min_length=5, max_length=2000)
    require_approval: bool = False

    @field_validator("justification", mode="before")
    @classmethod
    def strip_justification(cls, v: Any) -> Any:
        return _strip_str(v)


class DataAssetRegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner_id: Optional[int] = None
    steward_id: int
    notes: Optional[str] = None


class DataAssetDeprecateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deprecation_notes: str = Field(..., min_length=5, max_length=2000)

    @field_validator("deprecation_notes", mode="before")
    @classmethod
    def strip_notes(cls, v: Any) -> Any:
        return _strip_str(v)


class DataAssetRetireRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    disposal_method: DataDisposalMethodEnum
    retirement_notes: str = Field(..., min_length=5, max_length=2000)
    retirement_evidence_id: Optional[int] = None

    @field_validator("retirement_notes", mode="before")
    @classmethod
    def strip_notes(cls, v: Any) -> Any:
        return _strip_str(v)


class DataAssetRestoreRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    restoration_justification: str = Field(..., min_length=5, max_length=2000)

    @field_validator("restoration_justification", mode="before")
    @classmethod
    def strip_justification(cls, v: Any) -> Any:
        return _strip_str(v)


# ─────────────────────────────────────────────────────────────────────────────
# 5. DATA LINEAGE SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class DataLineageEdgeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    edge_code: str = Field(..., min_length=2, max_length=64)
    source_data_asset_id: int
    target_data_asset_id: int
    relationship_type: DataLineageRelationshipTypeEnum = DataLineageRelationshipTypeEnum.ETL_TRANSFORMATION
    transformation_summary: Optional[str] = None
    field_mapping_manifest: Optional[List[Dict[str, Any]]] = None
    is_encrypted_in_transit: bool = True
    is_masked_or_anonymized: bool = False
    processing_activity_id: Optional[int] = None
    cloud_asset_id: Optional[int] = None
    require_approval: bool = False

    @field_validator("edge_code", "transformation_summary", mode="before")
    @classmethod
    def strip_text(cls, v: Any) -> Any:
        return _strip_str(v)


class DataLineageEdgeRevokeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revocation_reason: str = Field(..., min_length=5, max_length=2000)

    @field_validator("revocation_reason", mode="before")
    @classmethod
    def strip_reason(cls, v: Any) -> Any:
        return _strip_str(v)


class DataLineageEdgeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    edge_code: str
    version: int
    source_data_asset_id: int
    target_data_asset_id: int
    relationship_type: str
    transformation_summary: Optional[str] = None
    field_mapping_manifest: Optional[List[Dict[str, Any]]] = None
    is_encrypted_in_transit: bool
    is_masked_or_anonymized: bool
    processing_activity_id: Optional[int] = None
    cloud_asset_id: Optional[int] = None
    status: str
    provenance_hash: str
    created_by_id: int
    approved_by_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    revoked_by_id: Optional[int] = None
    revoked_at: Optional[datetime] = None
    revocation_reason: Optional[str] = None
    effective_from: datetime
    effective_to: Optional[datetime] = None
    created_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# 6. CROSS-DOMAIN BRIDGE SCHEMAS (CLOUD, PROCESSING, CONTROL, EVIDENCE)
# ─────────────────────────────────────────────────────────────────────────────

class DataAssetCloudLinkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cloud_asset_id: int
    hosting_role: DataCloudHostingRoleEnum = DataCloudHostingRoleEnum.PRIMARY_STORE
    notes: Optional[str] = None


class DataAssetCloudLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    data_asset_id: int
    cloud_asset_id: int
    hosting_role: str
    notes: Optional[str] = None
    linked_by_id: Optional[int] = None
    created_at: datetime


class DataAssetProcessingLinkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    processing_activity_id: int
    usage_role: DataProcessingUsageRoleEnum = DataProcessingUsageRoleEnum.PRIMARY_SOURCE
    notes: Optional[str] = None


class DataAssetProcessingLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    data_asset_id: int
    processing_activity_id: int
    usage_role: str
    notes: Optional[str] = None
    linked_by_id: Optional[int] = None
    created_at: datetime


class DataAssetControlLinkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_control_id: int
    control_objective: DataControlObjectiveEnum = DataControlObjectiveEnum.ENCRYPTION_AT_REST
    is_mandatory: bool = True
    coverage_notes: Optional[str] = None


class DataAssetControlLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    data_asset_id: int
    organization_control_id: int
    control_objective: str
    is_mandatory: bool
    coverage_notes: Optional[str] = None
    linked_by_id: Optional[int] = None
    created_at: datetime


class DataAssetEvidenceLinkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_item_id: int
    evidence_purpose: DataEvidencePurposeEnum = DataEvidencePurposeEnum.CLASSIFICATION_JUSTIFICATION
    notes: Optional[str] = None


class DataAssetEvidenceLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    data_asset_id: int
    evidence_item_id: int
    evidence_purpose: str
    notes: Optional[str] = None
    linked_by_id: Optional[int] = None
    created_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# 7. DOSSIER & POSTURE SUMMARY SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class CloudPostureAlignmentInfo(BaseModel):
    cloud_posture_aligned: bool
    linked_cloud_asset_ids: List[int]
    mismatch_flags: List[str]


class RegulatoryObligationRef(BaseModel):
    obligation_id: int
    obligation_code: str
    title: str
    mandate_id: int
    organization_control_id: Optional[int] = None
    compliance_status: str


class GovernedDataAssetDossierResponse(BaseModel):
    asset: GovernedDataAssetResponse
    owner_active: bool
    steward_active: Optional[bool] = None
    cloud_alignment: CloudPostureAlignmentInfo
    classification_history: List[DataClassificationRecordResponse]
    upstream_lineage: List[DataLineageEdgeResponse]
    downstream_lineage: List[DataLineageEdgeResponse]
    cloud_links: List[DataAssetCloudLinkResponse]
    processing_links: List[DataAssetProcessingLinkResponse]
    control_links: List[DataAssetControlLinkResponse]
    evidence_links: List[DataAssetEvidenceLinkResponse]
    regulatory_obligations: List[RegulatoryObligationRef]


class DataGovernanceSummaryResponse(BaseModel):
    total_assets: int
    active_assets: int
    discovered_unregistered_assets: int
    deprecated_assets: int
    retired_assets: int
    classified_assets_count: int
    pending_classification_approvals: int
    unclassified_assets_count: int
    restricted_or_phi_assets_count: int
    owner_coverage_pct: float
    steward_coverage_pct: float
    inactive_owner_count: int
    active_lineage_edges_count: int
    pending_lineage_approvals_count: int
    cloud_linked_assets_count: int
    cloud_posture_mismatch_count: int
    processing_linked_assets_count: int
    control_linked_assets_count: int
    evidence_linked_assets_count: int
    governance_health_score: float
    sensitivity_distribution: Dict[str, int]
    lifecycle_distribution: Dict[str, int]
