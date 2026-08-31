from datetime import datetime, timezone
import enum
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

from app.db.base import Base


# ─────────────────────────────────────────────────────────────────────────────
# Phase 14: EXPOSURE-GRC Domain Enums
# ─────────────────────────────────────────────────────────────────────────────

class ExposureSeverityEnum(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"


class ExposureStatusEnum(str, enum.Enum):
    OPEN = "OPEN"
    UNDER_INVESTIGATION = "UNDER_INVESTIGATION"
    REMEDIATING = "REMEDIATING"
    EXCEPTION_REQUESTED = "EXCEPTION_REQUESTED"
    EXCEPTION_APPROVED = "EXCEPTION_APPROVED"
    EXCEPTION_REJECTED = "EXCEPTION_REJECTED"
    RESOLVED = "RESOLVED"


class AssetTypeEnum(str, enum.Enum):
    SERVER = "SERVER"
    DATABASE = "DATABASE"
    CLOUD_SERVICE = "CLOUD_SERVICE"
    NETWORK_DEVICE = "NETWORK_DEVICE"
    APPLICATION = "APPLICATION"


class EnvironmentEnum(str, enum.Enum):
    PRODUCTION = "PRODUCTION"
    STAGING = "STAGING"
    DEVELOPMENT = "DEVELOPMENT"


class ExceptionApprovalStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


# ─────────────────────────────────────────────────────────────────────────────
# 1. VULNERABILITY EXPOSURE MODEL
# ─────────────────────────────────────────────────────────────────────────────

class VulnerabilityExposure(Base):
    """Authoritative Threat Exposure & Vulnerability catalog record."""
    __tablename__ = "vulnerability_exposures"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cve_id = Column(String(50), nullable=False, index=True)
    cwe_id = Column(String(50), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    cvss_score = Column(Float, nullable=False, default=0.0)
    cvss_vector = Column(String(150), nullable=True)
    epss_score = Column(Float, nullable=False, default=0.0)
    cisa_kev = Column(Boolean, nullable=False, default=False)
    severity = Column(
        Enum(ExposureSeverityEnum),
        nullable=False,
        default=ExposureSeverityEnum.MEDIUM,
        index=True,
    )
    status = Column(
        Enum(ExposureStatusEnum),
        nullable=False,
        default=ExposureStatusEnum.OPEN,
        index=True,
    )
    exposure_index = Column(Float, nullable=False, default=0.0)
    remediation_sla_due = Column(DateTime(timezone=True), nullable=False)
    remediation_plan_id = Column(
        Integer,
        ForeignKey("remediation_plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    discovered_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)
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

    # Relationships
    organization = relationship("Organization")
    remediation_plan = relationship("RemediationPlan")
    asset_links = relationship(
        "ExposureAssetLink",
        back_populates="exposure",
        cascade="all, delete-orphan",
        order_by="ExposureAssetLink.id",
    )
    exceptions = relationship(
        "ExposureException",
        back_populates="exposure",
        cascade="all, delete-orphan",
        order_by="ExposureException.id.desc()",
    )

    __table_args__ = (
        CheckConstraint(
            "cvss_score >= 0.0 AND cvss_score <= 10.0",
            name="chk_exposure_cvss_bounds",
        ),
        CheckConstraint(
            "epss_score >= 0.0 AND epss_score <= 1.0",
            name="chk_exposure_epss_bounds",
        ),
        CheckConstraint(
            "exposure_index >= 0.0 AND exposure_index <= 100.0",
            name="chk_exposure_index_bounds",
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. EXPOSURE ASSET LINK MODEL (BLAST RADIUS & CROSS-MODULE MAP)
# ─────────────────────────────────────────────────────────────────────────────

class ExposureAssetLink(Base):
    """Associates an exposed technical asset with Business Processes, Vendors, and Controls."""
    __tablename__ = "exposure_asset_links"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exposure_id = Column(
        Integer,
        ForeignKey("vulnerability_exposures.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset_identifier = Column(String(255), nullable=False, index=True)
    asset_type = Column(
        Enum(AssetTypeEnum),
        nullable=False,
        default=AssetTypeEnum.SERVER,
    )
    environment = Column(
        Enum(EnvironmentEnum),
        nullable=False,
        default=EnvironmentEnum.PRODUCTION,
    )
    process_id = Column(
        Integer,
        ForeignKey("business_processes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    vendor_id = Column(
        Integer,
        ForeignKey("vendors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    control_id = Column(
        Integer,
        ForeignKey("organization_controls.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    exposure = relationship("VulnerabilityExposure", back_populates="asset_links")
    process = relationship("BusinessProcess")
    vendor = relationship("Vendor")
    control = relationship("OrganizationControl")

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "exposure_id",
            "asset_identifier",
            "process_id",
            "vendor_id",
            "control_id",
            name="uq_exposure_asset_link",
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. EXPOSURE EXCEPTION MODEL (FOUR-EYES SLA DEFERRAL GOVERNANCE)
# ─────────────────────────────────────────────────────────────────────────────

class ExposureException(Base):
    """Four-eyes governed SLA extension and risk deferral request."""
    __tablename__ = "exposure_exceptions"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exposure_id = Column(
        Integer,
        ForeignKey("vulnerability_exposures.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    approved_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status = Column(
        Enum(ExceptionApprovalStatusEnum),
        nullable=False,
        default=ExceptionApprovalStatusEnum.PENDING,
        index=True,
    )
    original_sla_due = Column(DateTime(timezone=True), nullable=False)
    requested_sla_due = Column(DateTime(timezone=True), nullable=False)
    justification = Column(Text, nullable=False)
    compensating_controls = Column(Text, nullable=True)
    review_notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    exposure = relationship("VulnerabilityExposure", back_populates="exceptions")
    requested_by = relationship("User", foreign_keys=[requested_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])

    __table_args__ = (
        CheckConstraint(
            "requested_by_id != approved_by_id",
            name="chk_exposure_exception_four_eyes",
        ),
    )
