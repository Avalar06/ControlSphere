from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.integration import (
    IntegrationProviderTypeEnum,
    IntegrationAuthTypeEnum,
    IntegrationConnectionStatusEnum,
    EvidenceCollectorTypeEnum,
    CollectionRunStatusEnum,
    CollectionValidationStatusEnum,
)


# ── Integration Provider Schemas ───────────────────────────────────────────

class IntegrationProviderBase(BaseModel):
    provider_type: IntegrationProviderTypeEnum
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    auth_type: IntegrationAuthTypeEnum = IntegrationAuthTypeEnum.API_KEY
    supported_scopes: List[str]
    allowed_domains: List[str]
    is_enabled: bool = True


class IntegrationProviderResponse(BaseModel):
    id: int
    provider_type: IntegrationProviderTypeEnum
    name: str
    description: Optional[str] = None
    auth_type: IntegrationAuthTypeEnum
    supported_scopes: List[str]
    allowed_domains: List[str]
    is_enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Integration Connection Schemas ─────────────────────────────────────────

class IntegrationConnectionBase(BaseModel):
    provider_id: int
    connection_code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=255)
    base_url: Optional[str] = Field(None, max_length=500)
    granted_scopes: List[str]


class IntegrationConnectionCreate(IntegrationConnectionBase):
    pass


class IntegrationConnectionUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    base_url: Optional[str] = Field(None, max_length=500)
    granted_scopes: Optional[List[str]] = None
    status: Optional[IntegrationConnectionStatusEnum] = None


class IntegrationConnectionResponse(BaseModel):
    id: int
    organization_id: int
    provider_id: int
    connection_code: str
    name: str
    status: IntegrationConnectionStatusEnum
    base_url: Optional[str] = None
    granted_scopes: List[str]
    last_health_check_at: Optional[datetime] = None
    last_health_status: Optional[str] = None
    last_error_message: Optional[str] = None
    is_credential_configured: bool = False
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Integration Credential Schemas ─────────────────────────────────────────

class IntegrationCredentialCreate(BaseModel):
    auth_type: IntegrationAuthTypeEnum
    credentials: Dict[str, Any] = Field(..., description="Sensitive credential dictionary encrypted at rest")


class IntegrationCredentialResponse(BaseModel):
    key_id: str
    auth_type: IntegrationAuthTypeEnum
    version: int
    is_configured: bool = True
    rotated_at: Optional[datetime] = None
    created_at: datetime


# ── Evidence Collection Job Schemas ────────────────────────────────────────

class EvidenceCollectionJobBase(BaseModel):
    connection_id: int
    organization_control_id: int
    evidence_requirement_id: Optional[int] = None
    job_code: str = Field(..., max_length=64)
    title: str = Field(..., max_length=255)
    collector_type: EvidenceCollectorTypeEnum
    collection_parameters: Optional[Dict[str, Any]] = None
    frequency_hours: int = Field(24, ge=1, le=8760)
    is_enabled: bool = True
    max_payload_bytes: int = Field(10485760, ge=1024, le=52428800)  # Max 50MB


class EvidenceCollectionJobCreate(EvidenceCollectionJobBase):
    pass


class EvidenceCollectionJobUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    collection_parameters: Optional[Dict[str, Any]] = None
    frequency_hours: Optional[int] = Field(None, ge=1, le=8760)
    is_enabled: Optional[bool] = None
    max_payload_bytes: Optional[int] = Field(None, ge=1024, le=52428800)


class EvidenceCollectionJobResponse(BaseModel):
    id: int
    organization_id: int
    connection_id: int
    organization_control_id: int
    evidence_requirement_id: Optional[int] = None
    job_code: str
    title: str
    collector_type: EvidenceCollectorTypeEnum
    collection_parameters: Optional[Dict[str, Any]] = None
    frequency_hours: int
    is_enabled: bool
    max_payload_bytes: int
    last_run_at: Optional[datetime] = None
    last_run_status: Optional[str] = None
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Evidence Collection Run Schemas ────────────────────────────────────────

class EvidenceCollectionRunResponse(BaseModel):
    id: int
    organization_id: int
    job_id: int
    connection_id: int
    evidence_item_id: Optional[int] = None
    run_code: str
    status: CollectionRunStatusEnum
    started_at: datetime
    completed_at: Optional[datetime] = None
    source_system: str
    source_identifier: str
    source_version: Optional[str] = None
    observed_at: datetime
    records_collected_count: int
    payload_sha256: Optional[str] = None
    validation_status: CollectionValidationStatusEnum
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    provenance_manifest: Optional[Dict[str, Any]] = None
    triggered_by_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
