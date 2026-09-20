from datetime import datetime, date
from typing import Any, Dict, List, Optional
import enum
from pydantic import BaseModel, ConfigDict, Field


# ─────────────────────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────────────────────
class PBCStatusEnum(str, enum.Enum):
    REQUESTED = "REQUESTED"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class PBCPriorityEnum(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SamplingMethodEnum(str, enum.Enum):
    RANDOM = "RANDOM"
    SYSTEMATIC = "SYSTEMATIC"
    STRATIFIED = "STRATIFIED"


class SampleResultEnum(str, enum.Enum):
    PENDING = "PENDING"
    PASS = "PASS"
    FAIL = "FAIL"
    EXCEPTION = "EXCEPTION"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class WorkpaperStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED_FOR_REVIEW = "SUBMITTED_FOR_REVIEW"
    REVIEWED_APPROVED = "REVIEWED_APPROVED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"


# ─────────────────────────────────────────────────────────────────────────────
# PBC Schemas
# ─────────────────────────────────────────────────────────────────────────────
class AuditPBCRequestCreate(BaseModel):
    organization_control_id: int
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    procedure_id: Optional[int] = None
    request_identifier: Optional[str] = Field(None, max_length=50)
    priority: PBCPriorityEnum = PBCPriorityEnum.MEDIUM
    assigned_to_id: Optional[int] = None
    due_date: date


class AuditPBCRequestUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    assigned_to_id: Optional[int] = None
    priority: Optional[PBCPriorityEnum] = None
    due_date: Optional[date] = None


class AuditPBCRequestFulfill(BaseModel):
    submission_notes: Optional[str] = None
    evidence_id: Optional[int] = None  # If linking existing evidence


class AuditPBCRequestReview(BaseModel):
    decision: str = Field(..., description="'ACCEPT' or 'REJECT'")
    review_notes: Optional[str] = None
    rejection_reason: Optional[str] = None


class AuditPBCRequestResponse(BaseModel):
    id: int
    organization_id: int
    audit_id: int
    procedure_id: Optional[int] = None
    organization_control_id: int
    request_identifier: str
    title: str
    description: str
    status: PBCStatusEnum
    priority: PBCPriorityEnum
    assigned_to_id: Optional[int] = None
    due_date: date
    fulfilled_evidence_id: Optional[int] = None
    submission_notes: Optional[str] = None
    submitted_at: Optional[datetime] = None
    reviewed_by_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    assigned_to_name: Optional[str] = None
    reviewed_by_name: Optional[str] = None
    control_code: Optional[str] = None
    evidence_filename: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# Sampling Schemas
# ─────────────────────────────────────────────────────────────────────────────
class PopulationItemInput(BaseModel):
    source_record_id: str = Field(..., min_length=1, max_length=255)
    attributes: Dict[str, Any] = Field(default_factory=dict)


class AuditSamplePopulationCreate(BaseModel):
    population_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    population_source: str = Field(..., min_length=1, max_length=255)
    items: List[PopulationItemInput] = Field(..., min_length=1)


class AuditSampleGenerateRequest(BaseModel):
    sampling_method: SamplingMethodEnum = SamplingMethodEnum.RANDOM
    sample_size: int = Field(..., gt=0)
    strata_attribute: Optional[str] = None  # Key in attributes dict for STRATIFIED sampling


class AuditSampleItemUpdate(BaseModel):
    test_result: SampleResultEnum
    testing_notes: Optional[str] = None
    evidence_item_id: Optional[int] = None


class AuditSampleEscalateFinding(BaseModel):
    severity: Optional[str] = Field("HIGH", description="Finding severity: LOW, MEDIUM, HIGH, CRITICAL")
    title: Optional[str] = None
    description: Optional[str] = None


class AuditSampleItemResponse(BaseModel):
    id: int
    organization_id: int
    population_id: int
    item_index: int
    source_record_id: str
    item_attributes: Dict[str, Any] = Field(default_factory=dict)
    test_result: SampleResultEnum
    testing_notes: Optional[str] = None
    tested_by_id: Optional[int] = None
    tested_at: Optional[datetime] = None
    evidence_item_id: Optional[int] = None
    deficiency_finding_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditSamplePopulationResponse(BaseModel):
    id: int
    organization_id: int
    audit_id: int
    procedure_id: int
    population_name: str
    description: Optional[str] = None
    population_source: str
    total_count: int
    version_number: int
    is_frozen: bool
    frozen_at: Optional[datetime] = None
    frozen_by_id: Optional[int] = None
    population_digest_sha256: Optional[str] = None
    sampling_method: SamplingMethodEnum
    sampling_seed: Optional[str] = None
    sample_size: int
    samples_generated: bool
    generated_at: Optional[datetime] = None
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    sample_items: List[AuditSampleItemResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# Workpaper Schemas
# ─────────────────────────────────────────────────────────────────────────────
class AuditWorkpaperSubmit(BaseModel):
    testing_summary: str = Field(..., min_length=5)
    conclusion: str = Field(..., min_length=5)


class AuditWorkpaperApprove(BaseModel):
    review_notes: Optional[str] = None


class AuditWorkpaperRequestChanges(BaseModel):
    rejection_reason: str = Field(..., min_length=5)


class AuditWorkpaperResponse(BaseModel):
    id: int
    organization_id: int
    audit_id: int
    procedure_id: int
    version_number: int
    status: WorkpaperStatusEnum
    testing_summary: str
    conclusion: str
    prepared_by_id: int
    prepared_at: datetime
    reviewed_by_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    workpaper_hash_sha256: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    prepared_by_name: Optional[str] = None
    reviewed_by_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
