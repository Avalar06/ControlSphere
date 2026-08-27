from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.incident import (
    DisclosureStatusEnum,
    DisclosureTriggerTypeEnum,
    IncidentCategoryEnum,
    IncidentControlRelationshipEnum,
    IncidentSeverityEnum,
    IncidentStatusEnum,
    RegulatorEnum,
    RootCauseClassificationEnum,
    TimelineEventSourceEnum,
    TimelineEventTypeEnum,
)


# ─── SECURITY INCIDENT SCHEMAS ───────────────────────────────────────────────

class IncidentBase(BaseModel):
    incident_code: str = Field(..., min_length=2, max_length=64)
    title: str = Field(..., min_length=2, max_length=255)
    description: str = Field(..., min_length=5)
    severity: IncidentSeverityEnum = IncidentSeverityEnum.MEDIUM
    category: IncidentCategoryEnum = IncidentCategoryEnum.OTHER
    detected_at: datetime
    business_owner_id: Optional[int] = None
    affected_record_count: int = Field(0, ge=0)
    affected_systems_summary: Optional[str] = None
    financial_impact_estimate: float = Field(0.0, ge=0.0)
    compliance_drift_alert_id: Optional[int] = None


class IncidentCreate(IncidentBase):
    declared_at: Optional[datetime] = None


class IncidentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = Field(None, min_length=5)
    severity: Optional[IncidentSeverityEnum] = None
    category: Optional[IncidentCategoryEnum] = None
    business_owner_id: Optional[int] = None
    affected_record_count: Optional[int] = Field(None, ge=0)
    affected_systems_summary: Optional[str] = None
    financial_impact_estimate: Optional[float] = Field(None, ge=0.0)
    root_cause_classification: Optional[RootCauseClassificationEnum] = None
    root_cause_narrative: Optional[str] = None
    lessons_learned: Optional[str] = None


class IncidentStatusTransition(BaseModel):
    target_status: IncidentStatusEnum
    notes: Optional[str] = None


class IncidentCloseRequest(BaseModel):
    closure_notes: str = Field(..., min_length=10, description="Mandatory management closure justification")
    lessons_learned: Optional[str] = Field(None, min_length=5)
    root_cause_classification: Optional[RootCauseClassificationEnum] = None
    root_cause_narrative: Optional[str] = None


class IncidentMaterialityUpdate(BaseModel):
    is_material: bool
    materiality_notes: Optional[str] = None


class IncidentRead(IncidentBase):
    id: int
    organization_id: int
    status: IncidentStatusEnum
    incident_commander_id: int
    closed_by_id: Optional[int] = None
    declared_at: datetime
    contained_at: Optional[datetime] = None
    eradicated_at: Optional[datetime] = None
    recovered_at: Optional[datetime] = None
    post_mortem_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    is_material: bool
    materiality_determined_at: Optional[datetime] = None
    materiality_determined_by_id: Optional[int] = None
    root_cause_classification: Optional[RootCauseClassificationEnum] = None
    root_cause_narrative: Optional[str] = None
    lessons_learned: Optional[str] = None
    closure_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── REGULATORY DISCLOSURE SCHEMAS ───────────────────────────────────────────

class IncidentRegulatoryDisclosureBase(BaseModel):
    regulator: RegulatorEnum
    trigger_type: DisclosureTriggerTypeEnum = DisclosureTriggerTypeEnum.INCIDENT_DETECTION
    triggered_at: datetime
    rule_version: str = "1.0"
    calculation_version: str = "1.0"


class IncidentRegulatoryDisclosureCreate(IncidentRegulatoryDisclosureBase):
    pass


class IncidentRegulatoryNotificationRequest(BaseModel):
    notification_reference_code: str = Field(..., min_length=2, max_length=128)
    disclosure_notes: Optional[str] = None


class IncidentRegulatoryExemptionRequest(BaseModel):
    exemption_reason: str = Field(..., min_length=10, description="Mandatory legal justification for regulatory exemption")


class IncidentRegulatoryDisclosureRead(IncidentRegulatoryDisclosureBase):
    id: int
    organization_id: int
    incident_id: int
    status: DisclosureStatusEnum
    triggered_by_id: Optional[int] = None
    deadline_at: datetime
    notified_at: Optional[datetime] = None
    notified_by_id: Optional[int] = None
    notification_reference_code: Optional[str] = None
    exemption_reason: Optional[str] = None
    disclosure_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── TIMELINE EVENT SCHEMAS ──────────────────────────────────────────────────

class IncidentTimelineEventCreate(BaseModel):
    event_type: TimelineEventTypeEnum
    event_occurred_at: datetime
    description: str = Field(..., min_length=2)
    source: TimelineEventSourceEnum = TimelineEventSourceEnum.MANUAL_ENTRY


class IncidentTimelineEventRead(BaseModel):
    id: int
    organization_id: int
    incident_id: int
    event_type: TimelineEventTypeEnum
    event_occurred_at: datetime
    actor_id: int
    description: str
    source: TimelineEventSourceEnum
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── INCIDENT CONTROL LINK SCHEMAS ───────────────────────────────────────────

class IncidentControlLinkCreate(BaseModel):
    organization_control_id: int
    relationship_type: IncidentControlRelationshipEnum = IncidentControlRelationshipEnum.FAILED_CONTROL
    notes: Optional[str] = None


class IncidentControlLinkRead(BaseModel):
    id: int
    organization_id: int
    incident_id: int
    organization_control_id: int
    relationship_type: IncidentControlRelationshipEnum
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── INCIDENT VENDOR LINK SCHEMAS ────────────────────────────────────────────

class IncidentVendorLinkCreate(BaseModel):
    vendor_id: int
    vendor_engagement_id: Optional[int] = None
    is_vendor_originated: bool = True
    notes: Optional[str] = None


class IncidentVendorLinkRead(BaseModel):
    id: int
    organization_id: int
    incident_id: int
    vendor_id: int
    vendor_engagement_id: Optional[int] = None
    is_vendor_originated: bool
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── OVERVIEW & METRICS SCHEMAS ──────────────────────────────────────────────

class IncidentOverviewResponse(BaseModel):
    total_incidents: int
    open_incidents: int
    critical_or_high_incidents: int
    material_incidents: int
    overdue_disclosures: int
    status_distribution: dict
    severity_distribution: dict
    category_distribution: dict
    average_ttc_hours: Optional[float] = None
    average_mttr_hours: Optional[float] = None


class IncidentDetailRead(IncidentRead):
    timeline_events: List[IncidentTimelineEventRead] = []
    disclosures: List[IncidentRegulatoryDisclosureRead] = []
    control_links: List[IncidentControlLinkRead] = []
    vendor_links: List[IncidentVendorLinkRead] = []
    ttc_hours: Optional[float] = None
    mttr_hours: Optional[float] = None
    incident_age_hours: Optional[float] = None
