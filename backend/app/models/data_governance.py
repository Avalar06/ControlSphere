from datetime import datetime, timezone
import enum
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.models.privacy import DataSensitivityLevel


# ─────────────────────────────────────────────────────────────────────────────
# Batch 3: DATA-GOVERNANCE-GRC Domain Enums
# ─────────────────────────────────────────────────────────────────────────────

class DataAssetTypeEnum(str, enum.Enum):
    DATABASE_TABLE = "DATABASE_TABLE"
    DATA_LAKE_DATASET = "DATA_LAKE_DATASET"
    OBJECT_STORAGE_BUCKET = "OBJECT_STORAGE_BUCKET"
    DOCUMENT_REPOSITORY = "DOCUMENT_REPOSITORY"
    MESSAGE_STREAM = "MESSAGE_STREAM"
    API_FEED = "API_FEED"
    FEATURE_STORE = "FEATURE_STORE"
    ARCHIVE_BACKUP = "ARCHIVE_BACKUP"


class DataAssetLifecycleEnum(str, enum.Enum):
    DISCOVERED = "DISCOVERED"
    REGISTERED = "REGISTERED"
    CLASSIFIED = "CLASSIFIED"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    RETIRED = "RETIRED"


class DataClassificationSchemeStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class DataClassificationApprovalStatusEnum(str, enum.Enum):
    UNCLASSIFIED = "UNCLASSIFIED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class DataClassificationChangeTypeEnum(str, enum.Enum):
    INITIAL = "INITIAL"
    UPGRADE = "UPGRADE"
    DOWNGRADE = "DOWNGRADE"
    REVALIDATION = "REVALIDATION"


class DataClassificationRecordStatusEnum(str, enum.Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


class DataDisposalMethodEnum(str, enum.Enum):
    CRYPTOGRAPHIC_ERASURE = "CRYPTOGRAPHIC_ERASURE"
    SECURE_OVERWRITE = "SECURE_OVERWRITE"
    PHYSICAL_DESTRUCTION = "PHYSICAL_DESTRUCTION"
    ANONYMIZATION = "ANONYMIZATION"
    NONE = "NONE"


class DataLineageRelationshipTypeEnum(str, enum.Enum):
    INGESTION = "INGESTION"
    ETL_TRANSFORMATION = "ETL_TRANSFORMATION"
    REPLICATION = "REPLICATION"
    AGGREGATION = "AGGREGATION"
    EXPORT_SHARE = "EXPORT_SHARE"
    AI_TRAINING_FEED = "AI_TRAINING_FEED"
    ARCHIVE_FEED = "ARCHIVE_FEED"


class DataLineageStatusEnum(str, enum.Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    REVOKED = "REVOKED"


class DataCloudHostingRoleEnum(str, enum.Enum):
    PRIMARY_STORE = "PRIMARY_STORE"
    REPLICA_STORE = "REPLICA_STORE"
    BACKUP_ARCHIVE = "BACKUP_ARCHIVE"
    PROCESSING_COMPUTE = "PROCESSING_COMPUTE"
    ENCRYPTION_KEY_VAULT = "ENCRYPTION_KEY_VAULT"


class DataProcessingUsageRoleEnum(str, enum.Enum):
    PRIMARY_SOURCE = "PRIMARY_SOURCE"
    INTERMEDIATE_STORE = "INTERMEDIATE_STORE"
    OUTPUT_SINK = "OUTPUT_SINK"
    ARCHIVAL_STORE = "ARCHIVAL_STORE"


class DataControlObjectiveEnum(str, enum.Enum):
    ENCRYPTION_AT_REST = "ENCRYPTION_AT_REST"
    ENCRYPTION_IN_TRANSIT = "ENCRYPTION_IN_TRANSIT"
    ACCESS_CONTROL = "ACCESS_CONTROL"
    RETENTION_ENFORCEMENT = "RETENTION_ENFORCEMENT"
    DLP_MONITORING = "DLP_MONITORING"
    BACKUP_RECOVERY = "BACKUP_RECOVERY"
    DISPOSAL_VERIFICATION = "DISPOSAL_VERIFICATION"


class DataEvidencePurposeEnum(str, enum.Enum):
    CLASSIFICATION_JUSTIFICATION = "CLASSIFICATION_JUSTIFICATION"
    ENCRYPTION_ATTESTATION = "ENCRYPTION_ATTESTATION"
    LINEAGE_VALIDATION = "LINEAGE_VALIDATION"
    RETENTION_DISPOSAL_CERTIFICATE = "RETENTION_DISPOSAL_CERTIFICATE"
    STEWARDSHIP_AUDIT = "STEWARDSHIP_AUDIT"


class DataOwnerTransferStatusEnum(str, enum.Enum):
    NONE = "NONE"
    PENDING_TRANSFER = "PENDING_TRANSFER"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


# ─────────────────────────────────────────────────────────────────────────────
# 1. DATA CLASSIFICATION SCHEME
# ─────────────────────────────────────────────────────────────────────────────

class DataClassificationScheme(Base):
    """Organization-scoped configurable classification taxonomy with Four-Eyes activation."""
    __tablename__ = "data_classification_schemes"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scheme_code = Column(String(64), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    status = Column(
        String(32),
        nullable=False,
        default=DataClassificationSchemeStatusEnum.DRAFT.value,
        server_default="DRAFT",
        index=True,
    )
    is_default = Column(Boolean, nullable=False, default=False, server_default="0")

    created_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    approved_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    approved_at = Column(DateTime(timezone=True), nullable=True)

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

    organization = relationship("Organization", foreign_keys=[organization_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    levels = relationship(
        "DataClassificationLevel",
        back_populates="scheme",
        cascade="all, delete-orphan",
        order_by="DataClassificationLevel.ordinal_rank.asc()",
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "scheme_code", "version", name="uq_class_scheme_org_code_ver"),
        CheckConstraint("version >= 1", name="ck_class_scheme_version_pos"),
        CheckConstraint(
            "approved_by_id IS NULL OR created_by_id != approved_by_id",
            name="ck_class_scheme_sod",
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. DATA CLASSIFICATION LEVEL
# ─────────────────────────────────────────────────────────────────────────────

class DataClassificationLevel(Base):
    """Ordered classification level within a scheme, mapped to Phase 16 DataSensitivityLevel."""
    __tablename__ = "data_classification_levels"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scheme_id = Column(
        Integer,
        ForeignKey("data_classification_schemes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    level_code = Column(String(64), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    ordinal_rank = Column(Integer, nullable=False)
    mapped_sensitivity_level = Column(
        SAEnum(DataSensitivityLevel),
        nullable=False,
        default=DataSensitivityLevel.INTERNAL,
    )
    requires_encryption_at_rest = Column(Boolean, nullable=False, default=True, server_default="1")
    requires_encryption_in_transit = Column(Boolean, nullable=False, default=True, server_default="1")
    requires_four_eyes_approval = Column(Boolean, nullable=False, default=False, server_default="0")
    default_retention_months = Column(Integer, nullable=True)
    required_disposal_method = Column(String(64), nullable=True)

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

    organization = relationship("Organization", foreign_keys=[organization_id])
    scheme = relationship("DataClassificationScheme", back_populates="levels", foreign_keys=[scheme_id])

    __table_args__ = (
        UniqueConstraint("scheme_id", "level_code", name="uq_class_level_scheme_code"),
        UniqueConstraint("scheme_id", "ordinal_rank", name="uq_class_level_scheme_rank"),
        CheckConstraint("ordinal_rank >= 1 AND ordinal_rank <= 10", name="ck_class_level_rank_bounds"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. DATA CLASSIFICATION RECORD (IMMUTABLE GOVERNANCE LEDGER)
# ─────────────────────────────────────────────────────────────────────────────

class DataClassificationRecord(Base):
    """Append-only versioned classification history and Four-Eyes approval record."""
    __tablename__ = "data_classification_records"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    data_asset_id = Column(
        Integer,
        ForeignKey("data_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version = Column(Integer, nullable=False, default=1, server_default="1")
    scheme_id = Column(
        Integer,
        ForeignKey("data_classification_schemes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    level_id = Column(
        Integer,
        ForeignKey("data_classification_levels.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    previous_level_id = Column(
        Integer,
        ForeignKey("data_classification_levels.id", ondelete="SET NULL"),
        nullable=True,
    )
    previous_sensitivity_level = Column(SAEnum(DataSensitivityLevel), nullable=True)
    new_sensitivity_level = Column(SAEnum(DataSensitivityLevel), nullable=False)
    change_type = Column(String(32), nullable=False, index=True)
    status = Column(String(32), nullable=False, index=True)
    justification = Column(Text, nullable=False)

    requested_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    approved_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    effective_from = Column(DateTime(timezone=True), nullable=True)
    effective_to = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    organization = relationship("Organization", foreign_keys=[organization_id])
    data_asset = relationship("DataAsset", foreign_keys=[data_asset_id])
    scheme = relationship("DataClassificationScheme", foreign_keys=[scheme_id])
    level = relationship("DataClassificationLevel", foreign_keys=[level_id])
    requested_by = relationship("User", foreign_keys=[requested_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])

    __table_args__ = (
        UniqueConstraint("data_asset_id", "version", name="uq_class_record_asset_version"),
        CheckConstraint("version >= 1", name="ck_class_record_version_pos"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. DATA LINEAGE EDGE (DIRECTED DAG & PROVENANCE LEDGER)
# ─────────────────────────────────────────────────────────────────────────────

class DataLineageEdge(Base):
    """Append-only versioned directed data lineage edge with SHA-256 provenance digest."""
    __tablename__ = "data_lineage_edges"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    edge_code = Column(String(64), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    source_data_asset_id = Column(
        Integer,
        ForeignKey("data_assets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    target_data_asset_id = Column(
        Integer,
        ForeignKey("data_assets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    relationship_type = Column(String(32), nullable=False, index=True)
    transformation_summary = Column(Text, nullable=True)
    field_mapping_manifest = Column(JSON, nullable=True)
    is_encrypted_in_transit = Column(Boolean, nullable=False, default=True, server_default="1")
    is_masked_or_anonymized = Column(Boolean, nullable=False, default=False, server_default="0")

    processing_activity_id = Column(
        Integer,
        ForeignKey("processing_activities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    cloud_asset_id = Column(
        Integer,
        ForeignKey("cloud_assets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    status = Column(String(32), nullable=False, index=True)
    provenance_hash = Column(String(64), nullable=False, index=True)

    created_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    approved_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    approved_at = Column(DateTime(timezone=True), nullable=True)
    revoked_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revocation_reason = Column(Text, nullable=True)

    effective_from = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    effective_to = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    organization = relationship("Organization", foreign_keys=[organization_id])
    source_asset = relationship("DataAsset", foreign_keys=[source_data_asset_id])
    target_asset = relationship("DataAsset", foreign_keys=[target_data_asset_id])
    processing_activity = relationship("ProcessingActivity", foreign_keys=[processing_activity_id])
    cloud_asset = relationship("CloudAsset", foreign_keys=[cloud_asset_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    revoked_by = relationship("User", foreign_keys=[revoked_by_id])

    __table_args__ = (
        UniqueConstraint("organization_id", "edge_code", "version", name="uq_lineage_edge_org_code_ver"),
        CheckConstraint("source_data_asset_id != target_data_asset_id", name="ck_lineage_no_self_loop"),
        CheckConstraint("version >= 1", name="ck_lineage_version_pos"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5. CROSS-DOMAIN BRIDGE TABLES (CLOUD, PROCESSING, CONTROL, EVIDENCE)
# ─────────────────────────────────────────────────────────────────────────────

class DataAssetCloudLink(Base):
    """Authoritative M:N relationship between logical DataAsset and physical/cloud CloudAsset."""
    __tablename__ = "data_asset_cloud_links"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    data_asset_id = Column(
        Integer,
        ForeignKey("data_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cloud_asset_id = Column(
        Integer,
        ForeignKey("cloud_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    hosting_role = Column(
        String(32),
        nullable=False,
        default=DataCloudHostingRoleEnum.PRIMARY_STORE.value,
        server_default="PRIMARY_STORE",
    )
    notes = Column(Text, nullable=True)
    linked_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    data_asset = relationship("DataAsset", foreign_keys=[data_asset_id])
    cloud_asset = relationship("CloudAsset", foreign_keys=[cloud_asset_id])

    __table_args__ = (
        UniqueConstraint("organization_id", "data_asset_id", "cloud_asset_id", name="uq_data_asset_cloud_link"),
    )


class DataAssetProcessingLink(Base):
    """Authoritative M:N relationship between DataAsset and Phase 16 ProcessingActivity (RoPA)."""
    __tablename__ = "data_asset_processing_links"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    data_asset_id = Column(
        Integer,
        ForeignKey("data_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    processing_activity_id = Column(
        Integer,
        ForeignKey("processing_activities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    usage_role = Column(
        String(32),
        nullable=False,
        default=DataProcessingUsageRoleEnum.PRIMARY_SOURCE.value,
        server_default="PRIMARY_SOURCE",
    )
    notes = Column(Text, nullable=True)
    linked_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    data_asset = relationship("DataAsset", foreign_keys=[data_asset_id])
    processing_activity = relationship("ProcessingActivity", foreign_keys=[processing_activity_id])

    __table_args__ = (
        UniqueConstraint("organization_id", "data_asset_id", "processing_activity_id", name="uq_data_asset_processing_link"),
    )


class DataAssetControlLink(Base):
    """Authoritative M:N relationship between DataAsset and Phase 2 OrganizationControl."""
    __tablename__ = "data_asset_control_links"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    data_asset_id = Column(
        Integer,
        ForeignKey("data_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_control_id = Column(
        Integer,
        ForeignKey("organization_controls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    control_objective = Column(
        String(32),
        nullable=False,
        default=DataControlObjectiveEnum.ENCRYPTION_AT_REST.value,
        server_default="ENCRYPTION_AT_REST",
    )
    is_mandatory = Column(Boolean, nullable=False, default=True, server_default="1")
    coverage_notes = Column(Text, nullable=True)
    linked_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    data_asset = relationship("DataAsset", foreign_keys=[data_asset_id])
    organization_control = relationship("OrganizationControl", foreign_keys=[organization_control_id])

    __table_args__ = (
        UniqueConstraint("organization_id", "data_asset_id", "organization_control_id", name="uq_data_asset_control_link"),
    )


class DataAssetEvidenceLink(Base):
    """Authoritative M:N relationship between DataAsset and Phase 3 EvidenceItem."""
    __tablename__ = "data_asset_evidence_links"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    data_asset_id = Column(
        Integer,
        ForeignKey("data_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evidence_item_id = Column(
        Integer,
        ForeignKey("evidence_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evidence_purpose = Column(
        String(64),
        nullable=False,
        default=DataEvidencePurposeEnum.CLASSIFICATION_JUSTIFICATION.value,
        server_default="CLASSIFICATION_JUSTIFICATION",
    )
    notes = Column(Text, nullable=True)
    linked_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    data_asset = relationship("DataAsset", foreign_keys=[data_asset_id])
    evidence_item = relationship("EvidenceItem", foreign_keys=[evidence_item_id])

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "data_asset_id",
            "evidence_item_id",
            "evidence_purpose",
            name="uq_data_asset_evidence_link",
        ),
    )
