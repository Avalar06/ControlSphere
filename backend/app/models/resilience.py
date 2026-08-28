from datetime import datetime, timezone
import enum
from sqlalchemy import (
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
# Phase 13: RESILIENCE-GRC Domain Enums
# ─────────────────────────────────────────────────────────────────────────────

class BiaStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    ARCHIVED = "ARCHIVED"


class CriticalityTierEnum(str, enum.Enum):
    TIER_1 = "TIER_1"  # Mission Critical (<4h RTO)
    TIER_2 = "TIER_2"  # Business Critical (<24h RTO)
    TIER_3 = "TIER_3"  # Operational / Important (<72h RTO)
    TIER_4 = "TIER_4"  # Non-Critical / Administrative (>72h RTO)


class DependencyTypeEnum(str, enum.Enum):
    VENDOR = "VENDOR"
    CONTROL = "CONTROL"


# ─────────────────────────────────────────────────────────────────────────────
# 1. BUSINESS PROCESS MODEL
# ─────────────────────────────────────────────────────────────────────────────

class BusinessProcess(Base):
    """Authoritative organizational business process catalog entity."""
    __tablename__ = "business_processes"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    owner_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    criticality_tier = Column(
        Enum(CriticalityTierEnum),
        nullable=False,
        default=CriticalityTierEnum.TIER_3,
        index=True,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    organization = relationship("Organization")
    owner = relationship("User", foreign_keys=[owner_id])
    impact_analyses = relationship(
        "BusinessImpactAnalysis",
        back_populates="process",
        cascade="all, delete-orphan",
        order_by="BusinessImpactAnalysis.version.desc()",
    )
    dependencies = relationship(
        "ProcessDependency",
        back_populates="process",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_business_process_org_name"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. BUSINESS IMPACT ANALYSIS (BIA) MODEL
# ─────────────────────────────────────────────────────────────────────────────

class BusinessImpactAnalysis(Base):
    """Governed, versioned, immutable Business Impact Analysis baseline."""
    __tablename__ = "business_impact_analyses"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    process_id = Column(
        Integer,
        ForeignKey("business_processes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(
        Enum(BiaStatusEnum),
        nullable=False,
        default=BiaStatusEnum.DRAFT,
        index=True,
    )
    version = Column(Integer, nullable=False, default=1)

    # Operational Downtime Thresholds (Hours)
    rto_hours = Column(Float, nullable=False, default=4.0)
    rpo_hours = Column(Float, nullable=False, default=1.0)
    mtd_hours = Column(Float, nullable=False, default=24.0)

    # Financial Disruption Parameters (USD)
    hourly_downtime_cost = Column(Float, nullable=False, default=10000.0)
    fixed_outage_cost = Column(Float, nullable=False, default=5000.0)

    # Governance & Four-Eyes
    requested_by_id = Column(
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
    approved_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    organization = relationship("Organization")
    process = relationship("BusinessProcess", back_populates="impact_analyses")
    requested_by = relationship("User", foreign_keys=[requested_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])

    __table_args__ = (
        CheckConstraint("rto_hours <= mtd_hours", name="chk_bia_rto_lte_mtd"),
        CheckConstraint("rto_hours >= 0", name="chk_bia_rto_nonneg"),
        CheckConstraint("rpo_hours >= 0", name="chk_bia_rpo_nonneg"),
        CheckConstraint("mtd_hours >= 0", name="chk_bia_mtd_nonneg"),
        CheckConstraint("hourly_downtime_cost >= 0", name="chk_bia_hourly_cost_nonneg"),
        CheckConstraint("fixed_outage_cost >= 0", name="chk_bia_fixed_cost_nonneg"),
        UniqueConstraint("process_id", "version", name="uq_bia_process_version"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. PROCESS DEPENDENCY MODEL (Polymorphic Linkage)
# ─────────────────────────────────────────────────────────────────────────────

class ProcessDependency(Base):
    """Cross-module dependency mapping (Phase 9 Vendor, Phase 2 Control)."""
    __tablename__ = "process_dependencies"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    process_id = Column(
        Integer,
        ForeignKey("business_processes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dependency_type = Column(
        Enum(DependencyTypeEnum),
        nullable=False,
        index=True,
    )
    dependency_id = Column(Integer, nullable=False, index=True)
    notes = Column(String(255), nullable=True)

    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    organization = relationship("Organization")
    process = relationship("BusinessProcess", back_populates="dependencies")

    __table_args__ = (
        UniqueConstraint(
            "process_id",
            "dependency_type",
            "dependency_id",
            name="uq_process_dependency",
        ),
    )
