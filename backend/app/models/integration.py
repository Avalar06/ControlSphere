from datetime import datetime, timezone
import enum
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


# ─────────────────────────────────────────────────────────────────────────────
# Enums for Phase 22: Integration-GRC
# ─────────────────────────────────────────────────────────────────────────────

class IntegrationProviderTypeEnum(str, enum.Enum):
    AWS = "AWS"
    AZURE = "AZURE"
    GITHUB = "GITHUB"
    GOOGLE = "GOOGLE"
    JIRA = "JIRA"


class IntegrationAuthTypeEnum(str, enum.Enum):
    API_KEY = "API_KEY"
    OAUTH2 = "OAUTH2"
    STS_ROLE = "STS_ROLE"
    BASIC = "BASIC"


class IntegrationConnectionStatusEnum(str, enum.Enum):
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"


class EvidenceCollectorTypeEnum(str, enum.Enum):
    AWS_IAM_MFA = "AWS_IAM_MFA"
    AWS_S3_ENCRYPTION = "AWS_S3_ENCRYPTION"
    GITHUB_BRANCH_PROTECTION = "GITHUB_BRANCH_PROTECTION"
    GITHUB_SECRET_SCANNING = "GITHUB_SECRET_SCANNING"
    AZURE_USER_MFA = "AZURE_USER_MFA"
    GOOGLE_WORKSPACE_2FA = "GOOGLE_WORKSPACE_2FA"
    JIRA_SECURITY_TICKETS = "JIRA_SECURITY_TICKETS"


class CollectionRunStatusEnum(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    PARTIAL_FAILURE = "PARTIAL_FAILURE"
    FAILED = "FAILED"


class CollectionValidationStatusEnum(str, enum.Enum):
    UNVALIDATED = "UNVALIDATED"
    SYNTAX_VALIDATED = "SYNTAX_VALIDATED"
    SCHEMA_VALIDATED = "SCHEMA_VALIDATED"
    VALIDATION_FAILED = "VALIDATION_FAILED"


# ─────────────────────────────────────────────────────────────────────────────
# Models for Phase 22: Integration-GRC
# ─────────────────────────────────────────────────────────────────────────────

class IntegrationProvider(Base):
    """System-level catalog of supported technical connectors and allowed domains."""
    __tablename__ = "integration_providers"

    id = Column(Integer, primary_key=True, index=True)
    provider_type = Column(
        Enum(IntegrationProviderTypeEnum, name="integrationprovidertypeenum"),
        nullable=False,
        unique=True,
        index=True,
    )
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    auth_type = Column(
        Enum(IntegrationAuthTypeEnum, name="integrationauthtypeenum"),
        nullable=False,
        default=IntegrationAuthTypeEnum.API_KEY,
    )
    supported_scopes = Column(Text, nullable=False)  # JSON array of scopes
    allowed_domains = Column(Text, nullable=False)   # JSON array of allowlisted domains for SSRF defense
    is_enabled = Column(Boolean, nullable=False, default=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    connections = relationship("IntegrationConnection", back_populates="provider")


class IntegrationConnection(Base):
    """Tenant-scoped integration connection with explicit authorized scopes and health telemetry."""
    __tablename__ = "integration_connections"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider_id = Column(
        Integer, ForeignKey("integration_providers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    connection_code = Column(String(64), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    status = Column(
        Enum(IntegrationConnectionStatusEnum, name="integrationconnectionstatusenum"),
        nullable=False,
        default=IntegrationConnectionStatusEnum.ACTIVE,
    )
    base_url = Column(String(500), nullable=True)
    granted_scopes = Column(Text, nullable=False)  # JSON array of granted scopes
    last_health_check_at = Column(DateTime(timezone=True), nullable=True)
    last_health_status = Column(String(50), nullable=True)
    last_error_message = Column(Text, nullable=True)
    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "connection_code", name="uq_intg_conn_org_code"),
    )

    organization = relationship("Organization")
    provider = relationship("IntegrationProvider", back_populates="connections")
    created_by = relationship("User", foreign_keys=[created_by_id])
    credential = relationship("IntegrationCredential", back_populates="connection", uselist=False, cascade="all, delete-orphan")
    collection_jobs = relationship("EvidenceCollectionJob", back_populates="connection", cascade="all, delete-orphan")


class IntegrationCredential(Base):
    """Isolated, Fernet AES-256 encrypted credential container. Never returned in API GET responses."""
    __tablename__ = "integration_credentials"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    connection_id = Column(
        Integer, ForeignKey("integration_connections.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    key_id = Column(String(64), nullable=False)
    encrypted_payload = Column(Text, nullable=False)  # Fernet encrypted ciphertext of credentials dict
    auth_type = Column(
        Enum(IntegrationAuthTypeEnum, name="integrationauthtypeenum"),
        nullable=False,
    )
    version = Column(Integer, nullable=False, default=1)
    rotated_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    organization = relationship("Organization")
    connection = relationship("IntegrationConnection", back_populates="credential")


class EvidenceCollectionJob(Base):
    """Configuration mapping an integration connection to an OrganizationControl and EvidenceRequirement."""
    __tablename__ = "evidence_collection_jobs"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    connection_id = Column(
        Integer, ForeignKey("integration_connections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_control_id = Column(
        Integer, ForeignKey("organization_controls.id", ondelete="CASCADE"), nullable=False, index=True
    )
    evidence_requirement_id = Column(
        Integer, ForeignKey("evidence_requirements.id", ondelete="SET NULL"), nullable=True, index=True
    )
    job_code = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    collector_type = Column(
        Enum(EvidenceCollectorTypeEnum, name="evidencecollectortypeenum"),
        nullable=False,
    )
    collection_parameters = Column(Text, nullable=True)  # JSON dict
    frequency_hours = Column(Integer, nullable=False, default=24)
    is_enabled = Column(Boolean, nullable=False, default=True)
    max_payload_bytes = Column(Integer, nullable=False, default=10485760)  # 10MB
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    last_run_status = Column(String(50), nullable=True)
    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "job_code", name="uq_evid_job_org_code"),
    )

    organization = relationship("Organization")
    connection = relationship("IntegrationConnection", back_populates="collection_jobs")
    organization_control = relationship("OrganizationControl")
    evidence_requirement = relationship("EvidenceRequirement")
    created_by = relationship("User", foreign_keys=[created_by_id])
    runs = relationship("EvidenceCollectionRun", back_populates="job", cascade="all, delete-orphan")


class EvidenceCollectionRun(Base):
    """Immutable execution record of an evidence collection attempt with complete provenance metadata."""
    __tablename__ = "evidence_collection_runs"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id = Column(
        Integer, ForeignKey("evidence_collection_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    connection_id = Column(
        Integer, ForeignKey("integration_connections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    evidence_item_id = Column(
        Integer, ForeignKey("evidence_items.id", ondelete="SET NULL"), nullable=True, index=True
    )
    run_code = Column(String(64), nullable=False, index=True)
    status = Column(
        Enum(CollectionRunStatusEnum, name="collectionrunstatusenum"),
        nullable=False,
        default=CollectionRunStatusEnum.QUEUED,
    )
    started_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)
    source_system = Column(String(50), nullable=False)
    source_identifier = Column(String(255), nullable=False)
    source_version = Column(String(50), nullable=True)
    observed_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    records_collected_count = Column(Integer, nullable=False, default=0)
    payload_sha256 = Column(String(64), nullable=True)
    raw_payload_storage_key = Column(String(500), nullable=True)
    validation_status = Column(
        Enum(CollectionValidationStatusEnum, name="collectionvalidationstatusenum"),
        nullable=False,
        default=CollectionValidationStatusEnum.UNVALIDATED,
    )
    error_code = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    provenance_manifest = Column(Text, nullable=True)  # JSON string
    triggered_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "run_code", name="uq_evid_run_org_code"),
    )

    organization = relationship("Organization")
    job = relationship("EvidenceCollectionJob", back_populates="runs")
    connection = relationship("IntegrationConnection")
    evidence_item = relationship("EvidenceItem")
    triggered_by = relationship("User", foreign_keys=[triggered_by_id])
