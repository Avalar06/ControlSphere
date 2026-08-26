from datetime import datetime, timezone
import enum
from sqlalchemy import (
    Boolean,
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
from app.models.monitoring import ControlHealthStatusEnum


class MappingTypeEnum(str, enum.Enum):
    EXACT = "EXACT"
    SUBSET = "SUBSET"
    SUPERSET = "SUPERSET"
    PARTIAL = "PARTIAL"
    CORRELATED = "CORRELATED"


class CommonControlDomainEnum(str, enum.Enum):
    IDENTITY_ACCESS = "IDENTITY_ACCESS"
    CRYPTOGRAPHY = "CRYPTOGRAPHY"
    DATA_PROTECTION = "DATA_PROTECTION"
    INCIDENT_MANAGEMENT = "INCIDENT_MANAGEMENT"
    VULNERABILITY_MANAGEMENT = "VULNERABILITY_MANAGEMENT"
    BUSINESS_CONTINUITY = "BUSINESS_CONTINUITY"
    GOVERNANCE_RISK = "GOVERNANCE_RISK"
    PHYSICAL_SECURITY = "PHYSICAL_SECURITY"
    OTHER = "OTHER"


class RationalizationStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


class FrameworkCrosswalkMapping(Base):
    """Global normative crosswalk mapping between regulatory subcategories."""
    __tablename__ = "framework_crosswalk_mappings"

    id = Column(Integer, primary_key=True, index=True)
    source_subcategory_id = Column(
        Integer,
        ForeignKey("framework_subcategories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_subcategory_id = Column(
        Integer,
        ForeignKey("framework_subcategories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mapping_type = Column(
        Enum(MappingTypeEnum),
        default=MappingTypeEnum.EXACT,
        nullable=False,
        index=True,
    )
    confidence_score = Column(Float, nullable=False, default=1.0)
    bidirectional = Column(Boolean, nullable=False, default=True)
    rationale = Column(Text, nullable=False)

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
        UniqueConstraint(
            "source_subcategory_id",
            "target_subcategory_id",
            name="uq_crosswalk_source_target",
        ),
    )

    source_subcategory = relationship(
        "FrameworkSubcategory",
        foreign_keys=[source_subcategory_id],
    )
    target_subcategory = relationship(
        "FrameworkSubcategory",
        foreign_keys=[target_subcategory_id],
    )


class RationalizedCommonControl(Base):
    """Tenant-scoped unified common control objective."""
    __tablename__ = "rationalized_common_controls"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    common_control_code = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    domain = Column(
        Enum(CommonControlDomainEnum),
        default=CommonControlDomainEnum.GOVERNANCE_RISK,
        nullable=False,
        index=True,
    )
    rationalization_status = Column(
        Enum(RationalizationStatusEnum),
        default=RationalizationStatusEnum.ACTIVE,
        nullable=False,
        index=True,
    )
    owner_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    deprecation_reason = Column(Text, nullable=True)

    # Server-derived health telemetry fields
    inherited_health_score = Column(Float, nullable=False, default=100.0)
    inherited_health_status = Column(
        Enum(ControlHealthStatusEnum),
        default=ControlHealthStatusEnum.HEALTHY,
        nullable=False,
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
        UniqueConstraint(
            "organization_id",
            "common_control_code",
            name="uq_org_common_control_code",
        ),
    )

    organization = relationship("Organization")
    owner = relationship("User", foreign_keys=[owner_id])
    mappings = relationship(
        "CommonControlMapping",
        back_populates="rationalized_common_control",
        cascade="all, delete-orphan",
    )


class CommonControlMapping(Base):
    """Tenant-scoped junction linking rationalized common controls to organization controls."""
    __tablename__ = "common_control_mappings"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rationalized_common_control_id = Column(
        Integer,
        ForeignKey("rationalized_common_controls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_control_id = Column(
        Integer,
        ForeignKey("organization_controls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    weight = Column(Float, nullable=False, default=1.0)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "rationalized_common_control_id",
            "organization_control_id",
            name="uq_cc_org_control",
        ),
    )

    rationalized_common_control = relationship(
        "RationalizedCommonControl",
        back_populates="mappings",
    )
    organization_control = relationship("OrganizationControl")


class FrameworkComplianceSnapshot(Base):
    """Tenant-scoped immutable point-in-time multi-framework compliance posture snapshot."""
    __tablename__ = "framework_compliance_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    framework_id = Column(
        Integer,
        ForeignKey("frameworks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    calculation_version = Column(String(20), nullable=False, default="v1.0")

    # Authoritative deterministic metrics
    coverage_percentage = Column(Float, nullable=False, default=0.0)
    compliance_health_score = Column(Float, nullable=False, default=0.0)
    total_subcategories = Column(Integer, nullable=False, default=0)
    covered_subcategories = Column(Integer, nullable=False, default=0)
    unmapped_subcategories = Column(Integer, nullable=False, default=0)

    evaluated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    organization = relationship("Organization")
    framework = relationship("Framework")
