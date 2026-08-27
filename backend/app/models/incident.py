import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.base_class import Base


# ─── ENUMS ───────────────────────────────────────────────────────────────────

class IncidentSeverityEnum(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class IncidentCategoryEnum(str, enum.Enum):
    RANSOMWARE = "RANSOMWARE"
    DATA_BREACH = "DATA_BREACH"
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"
    DENIAL_OF_SERVICE = "DENIAL_OF_SERVICE"
    INSIDER_THREAT = "INSIDER_THREAT"
    SUPPLY_CHAIN_COMPROMISE = "SUPPLY_CHAIN_COMPROMISE"
    OTHER = "OTHER"


class IncidentStatusEnum(str, enum.Enum):
    DECLARED = "DECLARED"
    TRIAGED = "TRIAGED"
    CONTAINED = "CONTAINED"
    ERADICATED = "ERADICATED"
    RECOVERED = "RECOVERED"
    POST_MORTEM = "POST_MORTEM"
    CLOSED = "CLOSED"


class RootCauseClassificationEnum(str, enum.Enum):
    CONTROL_FAILURE = "CONTROL_FAILURE"
    HUMAN_ERROR = "HUMAN_ERROR"
    ZERO_DAY = "ZERO_DAY"
    THIRD_PARTY_FAILURE = "THIRD_PARTY_FAILURE"
    CONFIGURATION_DRIFT = "CONFIGURATION_DRIFT"


class RegulatorEnum(str, enum.Enum):
    GDPR_DPA = "GDPR_DPA"
    SEC_8K = "SEC_8K"
    HHS_OCR = "HHS_OCR"
    PCI_SSC = "PCI_SSC"
    NYDFS = "NYDFS"
    STATE_AG = "STATE_AG"


class DisclosureStatusEnum(str, enum.Enum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    PENDING = "PENDING"
    DUE = "DUE"
    NOTIFIED = "NOTIFIED"
    OVERDUE = "OVERDUE"


class DisclosureTriggerTypeEnum(str, enum.Enum):
    INCIDENT_DETECTION = "INCIDENT_DETECTION"
    MATERIALITY_DETERMINATION = "MATERIALITY_DETERMINATION"
    PHI_THRESHOLD_BREACH = "PHI_THRESHOLD_BREACH"
    CDE_COMPROMISE = "CDE_COMPROMISE"
    LEGAL_DIRECTIVE = "LEGAL_DIRECTIVE"


class TimelineEventTypeEnum(str, enum.Enum):
    DETECTION = "DETECTION"
    CONTAINMENT_ACTION = "CONTAINMENT_ACTION"
    ERADICATION_STEP = "ERADICATION_STEP"
    EVIDENCE_COLLECTED = "EVIDENCE_COLLECTED"
    REGULATOR_NOTIFIED = "REGULATOR_NOTIFIED"
    COMMAND_TRANSFER = "COMMAND_TRANSFER"
    POST_MORTEM_NOTE = "POST_MORTEM_NOTE"


class TimelineEventSourceEnum(str, enum.Enum):
    MANUAL_ENTRY = "MANUAL_ENTRY"
    SYSTEM_AUTOMATION = "SYSTEM_AUTOMATION"
    CCM_DRIFT = "CCM_DRIFT"
    FORENSIC_LOG = "FORENSIC_LOG"


class IncidentControlRelationshipEnum(str, enum.Enum):
    FAILED_CONTROL = "FAILED_CONTROL"
    DEFICIENT_CONTROL = "DEFICIENT_CONTROL"
    CIRCUMVENTED_CONTROL = "CIRCUMVENTED_CONTROL"
    DETECTING_CONTROL = "DETECTING_CONTROL"


# ─── 1. SECURITY INCIDENT MODEL ──────────────────────────────────────────────

class SecurityIncident(Base):
    __tablename__ = "security_incidents"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    incident_code = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(
        Enum(IncidentSeverityEnum),
        nullable=False,
        default=IncidentSeverityEnum.MEDIUM,
        index=True,
    )
    category = Column(
        Enum(IncidentCategoryEnum),
        nullable=False,
        default=IncidentCategoryEnum.OTHER,
        index=True,
    )
    status = Column(
        Enum(IncidentStatusEnum),
        nullable=False,
        default=IncidentStatusEnum.DECLARED,
        index=True,
    )

    # Actor Attribution (Derived from JWT context)
    incident_commander_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    business_owner_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    closed_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Telemetry & Operational UTC Timestamps
    detected_at = Column(DateTime(timezone=True), nullable=False)
    declared_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    contained_at = Column(DateTime(timezone=True), nullable=True)
    eradicated_at = Column(DateTime(timezone=True), nullable=True)
    recovered_at = Column(DateTime(timezone=True), nullable=True)
    post_mortem_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    # Breach Quantification & Materiality
    affected_record_count = Column(Integer, nullable=False, default=0)
    affected_systems_summary = Column(Text, nullable=True)
    financial_impact_estimate = Column(Float, nullable=False, default=0.0)
    is_material = Column(Boolean, nullable=False, default=False)
    materiality_determined_at = Column(DateTime(timezone=True), nullable=True)
    materiality_determined_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Post-Mortem Governance & Root Cause
    root_cause_classification = Column(
        Enum(RootCauseClassificationEnum),
        nullable=True,
    )
    root_cause_narrative = Column(Text, nullable=True)
    lessons_learned = Column(Text, nullable=True)
    closure_notes = Column(Text, nullable=True)

    # Source Linkage (Phase 7 CCM)
    compliance_drift_alert_id = Column(
        Integer,
        ForeignKey("compliance_drift_alerts.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("organization_id", "incident_code", name="uq_tenant_incident_code"),
        CheckConstraint("affected_record_count >= 0", name="ck_incident_affected_records_positive"),
        CheckConstraint("financial_impact_estimate >= 0.0", name="ck_incident_financial_impact_positive"),
    )

    # Relationships
    organization = relationship("Organization")
    incident_commander = relationship("User", foreign_keys=[incident_commander_id])
    business_owner = relationship("User", foreign_keys=[business_owner_id])
    closed_by = relationship("User", foreign_keys=[closed_by_id])
    materiality_determined_by = relationship("User", foreign_keys=[materiality_determined_by_id])
    compliance_drift_alert = relationship("ComplianceDriftAlert")

    disclosures = relationship(
        "IncidentRegulatoryDisclosure",
        back_populates="incident",
        cascade="all, delete-orphan",
        order_by="IncidentRegulatoryDisclosure.id.asc()",
    )
    timeline_events = relationship(
        "IncidentTimelineEvent",
        back_populates="incident",
        cascade="all, delete-orphan",
        order_by="IncidentTimelineEvent.event_occurred_at.asc(), IncidentTimelineEvent.id.asc()",
    )
    control_links = relationship(
        "IncidentControlLink",
        back_populates="incident",
        cascade="all, delete-orphan",
    )
    vendor_links = relationship(
        "IncidentVendorLink",
        back_populates="incident",
        cascade="all, delete-orphan",
    )


# ─── 2. INCIDENT REGULATORY DISCLOSURE MODEL ─────────────────────────────────

class IncidentRegulatoryDisclosure(Base):
    __tablename__ = "incident_disclosures"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    incident_id = Column(
        Integer,
        ForeignKey("security_incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    regulator = Column(
        Enum(RegulatorEnum),
        nullable=False,
        index=True,
    )
    status = Column(
        Enum(DisclosureStatusEnum),
        nullable=False,
        default=DisclosureStatusEnum.PENDING,
        index=True,
    )

    # Versioning & Explainability
    rule_version = Column(String(16), nullable=False, default="1.0")
    calculation_version = Column(String(16), nullable=False, default="1.0")

    # Trigger & Deadlines (UTC)
    trigger_type = Column(
        Enum(DisclosureTriggerTypeEnum),
        nullable=False,
        default=DisclosureTriggerTypeEnum.INCIDENT_DETECTION,
    )
    triggered_at = Column(DateTime(timezone=True), nullable=False)
    triggered_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    deadline_at = Column(DateTime(timezone=True), nullable=False, index=True)
    notified_at = Column(DateTime(timezone=True), nullable=True)
    notified_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Evidentiary Details & Notes
    notification_reference_code = Column(String(128), nullable=True)
    exemption_reason = Column(Text, nullable=True)
    disclosure_notes = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "incident_id",
            "regulator",
            name="uq_tenant_incident_regulator",
        ),
    )

    # Relationships
    incident = relationship("SecurityIncident", back_populates="disclosures")
    organization = relationship("Organization")
    triggered_by = relationship("User", foreign_keys=[triggered_by_id])
    notified_by = relationship("User", foreign_keys=[notified_by_id])


# ─── 3. INCIDENT TIMELINE EVENT MODEL ────────────────────────────────────────

class IncidentTimelineEvent(Base):
    __tablename__ = "incident_timeline_events"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    incident_id = Column(
        Integer,
        ForeignKey("security_incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type = Column(
        Enum(TimelineEventTypeEnum),
        nullable=False,
        index=True,
    )
    event_occurred_at = Column(DateTime(timezone=True), nullable=False, index=True)
    actor_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    description = Column(Text, nullable=False)
    source = Column(
        Enum(TimelineEventSourceEnum),
        nullable=False,
        default=TimelineEventSourceEnum.MANUAL_ENTRY,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    incident = relationship("SecurityIncident", back_populates="timeline_events")
    organization = relationship("Organization")
    actor = relationship("User", foreign_keys=[actor_id])


# ─── 4. INCIDENT CONTROL LINK MODEL ──────────────────────────────────────────

class IncidentControlLink(Base):
    __tablename__ = "incident_control_links"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    incident_id = Column(
        Integer,
        ForeignKey("security_incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_control_id = Column(
        Integer,
        ForeignKey("organization_controls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relationship_type = Column(
        Enum(IncidentControlRelationshipEnum),
        nullable=False,
        default=IncidentControlRelationshipEnum.FAILED_CONTROL,
    )
    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "incident_id",
            "organization_control_id",
            name="uq_tenant_incident_control",
        ),
    )

    # Relationships
    incident = relationship("SecurityIncident", back_populates="control_links")
    organization_control = relationship("OrganizationControl")
    organization = relationship("Organization")


# ─── 5. INCIDENT VENDOR LINK MODEL ───────────────────────────────────────────

class IncidentVendorLink(Base):
    __tablename__ = "incident_vendor_links"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    incident_id = Column(
        Integer,
        ForeignKey("security_incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vendor_id = Column(
        Integer,
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vendor_engagement_id = Column(
        Integer,
        ForeignKey("vendor_engagements.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_vendor_originated = Column(Boolean, nullable=False, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "incident_id",
            "vendor_id",
            "vendor_engagement_id",
            name="uq_tenant_incident_vendor_engagement",
        ),
    )

    # Relationships
    incident = relationship("SecurityIncident", back_populates="vendor_links")
    vendor = relationship("Vendor")
    vendor_engagement = relationship("VendorEngagement")
    organization = relationship("Organization")
