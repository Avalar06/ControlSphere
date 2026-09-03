from datetime import datetime, timezone, date
import enum
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


# ─────────────────────────────────────────────────────────────────────────────
# Phase 20: EXECUTIVE-GRC Domain Enums
# ─────────────────────────────────────────────────────────────────────────────

class DossierTypeEnum(str, enum.Enum):
    BOARD_SUMMARY = "BOARD_SUMMARY"
    REGULATORY_SUBMISSION = "REGULATORY_SUBMISSION"
    ANNUAL_COMPLIANCE = "ANNUAL_COMPLIANCE"
    TARGETED_AUDIT_PACKAGE = "TARGETED_AUDIT_PACKAGE"


class DossierStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    COMPILED = "COMPILED"
    UNDER_REVIEW = "UNDER_REVIEW"
    FINALIZED = "FINALIZED"
    ARCHIVED = "ARCHIVED"


class BriefingStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED_FOR_REVIEW = "SUBMITTED_FOR_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


class ExportFormatEnum(str, enum.Enum):
    PDF = "PDF"
    JSON = "JSON"


class ArtifactTypeEnum(str, enum.Enum):
    DOSSIER_PACKAGE = "DOSSIER_PACKAGE"
    EXECUTIVE_BRIEFING = "EXECUTIVE_BRIEFING"
    POSTURE_SNAPSHOT = "POSTURE_SNAPSHOT"


# ─────────────────────────────────────────────────────────────────────────────
# 1. EXECUTIVE SNAPSHOTS (Immutable point-in-time posture & cryptographic hash)
# ─────────────────────────────────────────────────────────────────────────────

class ExecutiveSnapshot(Base):
    """Tenant-scoped immutable point-in-time cross-module posture snapshot."""
    __tablename__ = "executive_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    snapshot_code = Column(String(64), nullable=False, index=True)
    calculated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # Deterministic Higher-Order Executive Aggregate Metrics
    overall_posture_score = Column(Float, nullable=False, default=0.0)
    inherent_risk_index = Column(Float, nullable=False, default=0.0)
    residual_risk_index = Column(Float, nullable=False, default=0.0)
    financial_exposure_ale = Column(Float, nullable=False, default=0.0)
    var_95_exposure = Column(Float, nullable=False, default=0.0)
    audit_readiness_index = Column(Float, nullable=False, default=0.0)
    remediation_sla_health_score = Column(Float, nullable=False, default=0.0)

    # Detailed Domain Breakdowns and Top Material Items
    framework_compliance_summary = Column(JSON, nullable=False, default=dict)
    domain_posture_breakdown = Column(JSON, nullable=False, default=dict)
    top_risks_snapshot = Column(JSON, nullable=False, default=list)
    critical_findings_snapshot = Column(JSON, nullable=False, default=list)

    # Audit Lineage Manifest
    source_manifest = Column(JSON, nullable=False, default=dict)

    # Cryptographic Digest (SHA-256 over canonicalized metadata, metrics, and manifest)
    data_hash_sha256 = Column(String(64), nullable=False, index=True)

    created_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "snapshot_code", name="uq_executive_snapshot_org_code"),
    )

    # Relationships
    organization = relationship("Organization")
    created_by = relationship("User", foreign_keys=[created_by_id])
    briefings = relationship("ExecutiveBriefing", back_populates="snapshot")
    export_artifacts = relationship("ExecutiveExportArtifact", back_populates="snapshot")


# ─────────────────────────────────────────────────────────────────────────────
# 2. EXECUTIVE DOSSIERS (Multi-framework regulatory compliance package)
# ─────────────────────────────────────────────────────────────────────────────

class ExecutiveDossier(Base):
    """Multi-framework regulatory compliance dossier package manifest."""
    __tablename__ = "executive_dossiers"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dossier_code = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    dossier_type = Column(
        Enum(DossierTypeEnum),
        nullable=False,
        default=DossierTypeEnum.BOARD_SUMMARY,
        index=True,
    )
    status = Column(
        Enum(DossierStatusEnum),
        nullable=False,
        default=DossierStatusEnum.DRAFT,
        index=True,
    )

    # Framework Scope & Telemetry Snapshot Link
    scope_framework_ids = Column(JSON, nullable=False, default=list)
    snapshot_id = Column(
        Integer,
        ForeignKey("executive_snapshots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Narrative Content
    executive_summary = Column(Text, nullable=True)
    regulatory_commentary = Column(Text, nullable=True)
    compiled_sections = Column(JSON, nullable=True, default=dict)

    # Governance Actor Attributions (Four-Eyes Separated)
    compiled_at = Column(DateTime(timezone=True), nullable=True)
    compiled_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    finalized_at = Column(DateTime(timezone=True), nullable=True)
    finalized_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "dossier_code", name="uq_executive_dossier_org_code"),
    )

    # Relationships
    organization = relationship("Organization")
    snapshot = relationship("ExecutiveSnapshot")
    created_by = relationship("User", foreign_keys=[created_by_id])
    compiled_by = relationship("User", foreign_keys=[compiled_by_id])
    finalized_by = relationship("User", foreign_keys=[finalized_by_id])
    export_artifacts = relationship("ExecutiveExportArtifact", back_populates="dossier")


# ─────────────────────────────────────────────────────────────────────────────
# 3. EXECUTIVE BRIEFINGS (Periodic board briefings with Four-Eyes sign-off)
# ─────────────────────────────────────────────────────────────────────────────

class ExecutiveBriefing(Base):
    """Governed executive and board briefing record with period-over-period delta analysis."""
    __tablename__ = "executive_briefings"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    briefing_code = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    reporting_period_start = Column(Date, nullable=False, index=True)
    reporting_period_end = Column(Date, nullable=False, index=True)

    status = Column(
        Enum(BriefingStatusEnum),
        nullable=False,
        default=BriefingStatusEnum.DRAFT,
        index=True,
    )
    snapshot_id = Column(
        Integer,
        ForeignKey("executive_snapshots.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Narrative & Recommendations
    executive_summary = Column(Text, nullable=False)
    key_achievements = Column(JSON, nullable=False, default=list)
    emerging_risks = Column(JSON, nullable=False, default=list)
    strategic_recommendations = Column(Text, nullable=True)
    period_over_period_deltas = Column(JSON, nullable=False, default=dict)

    # Four-Eyes Governance Attributions
    generated_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    approved_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    approved_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "briefing_code", name="uq_executive_briefing_org_code"),
    )

    # Relationships
    organization = relationship("Organization")
    snapshot = relationship("ExecutiveSnapshot", back_populates="briefings")
    generated_by = relationship("User", foreign_keys=[generated_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    export_artifacts = relationship("ExecutiveExportArtifact", back_populates="briefing")


# ─────────────────────────────────────────────────────────────────────────────
# 4. FORENSIC EXPORT ARTIFACTS (Retention-Safe PDF/JSON Exports)
# ─────────────────────────────────────────────────────────────────────────────

class ExecutiveExportArtifact(Base):
    """Forensic export artifact catalog record with SHA-256 integrity verification."""
    __tablename__ = "executive_export_artifacts"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    export_code = Column(String(64), nullable=False, index=True)
    export_format = Column(
        Enum(ExportFormatEnum),
        nullable=False,
        default=ExportFormatEnum.PDF,
        index=True,
    )
    artifact_type = Column(
        Enum(ArtifactTypeEnum),
        nullable=False,
        index=True,
    )

    # Linkages to Parent Entities (RESTRICT to prevent silent cascade loss)
    dossier_id = Column(
        Integer,
        ForeignKey("executive_dossiers.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    briefing_id = Column(
        Integer,
        ForeignKey("executive_briefings.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    snapshot_id = Column(
        Integer,
        ForeignKey("executive_snapshots.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    # Storage and File Integrity
    storage_key = Column(String(512), nullable=False)
    original_filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    sha256_checksum = Column(String(64), nullable=False, index=True)

    generated_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    generated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "export_code", name="uq_executive_export_org_code"),
    )

    # Relationships
    organization = relationship("Organization")
    dossier = relationship("ExecutiveDossier", back_populates="export_artifacts")
    briefing = relationship("ExecutiveBriefing", back_populates="export_artifacts")
    snapshot = relationship("ExecutiveSnapshot", back_populates="export_artifacts")
    generated_by = relationship("User", foreign_keys=[generated_by_id])
