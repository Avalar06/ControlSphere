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
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class SoftwareProductTypeEnum(str, enum.Enum):
    INTERNAL_APPLICATION = "INTERNAL_APPLICATION"
    MICROSERVICE = "MICROSERVICE"
    COMMERCIAL_COTS = "COMMERCIAL_COTS"
    FIRMWARE_IOT = "FIRMWARE_IOT"
    AI_MODEL_PIPELINE = "AI_MODEL_PIPELINE"
    OPEN_SOURCE_LIBRARY = "OPEN_SOURCE_LIBRARY"


class ProductCriticalityTierEnum(str, enum.Enum):
    TIER_1_CRITICAL = "TIER_1_CRITICAL"
    TIER_2_MAJOR = "TIER_2_MAJOR"
    TIER_3_MODERATE = "TIER_3_MODERATE"
    TIER_4_LOW = "TIER_4_LOW"


class ProductLifecycleStateEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    RETIRED = "RETIRED"


class SBOMFormatStandardEnum(str, enum.Enum):
    CYCLONEDX_JSON = "CYCLONEDX_JSON"
    CYCLONEDX_XML = "CYCLONEDX_XML"
    SPDX_JSON = "SPDX_JSON"
    SPDX_TAG_VALUE = "SPDX_TAG_VALUE"
    CUSTOM_JSON = "CUSTOM_JSON"


class SBOMStatusEnum(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    ARCHIVED = "ARCHIVED"


class ComponentEcosystemEnum(str, enum.Enum):
    NPM = "NPM"
    PYPI = "PYPI"
    MAVEN = "MAVEN"
    GO = "GO"
    CARGO = "CARGO"
    NUGET = "NUGET"
    DOCKER = "DOCKER"
    COMPOSER = "COMPOSER"
    GENERIC = "GENERIC"


class LicenseCategoryEnum(str, enum.Enum):
    PERMISSIVE = "PERMISSIVE"
    WEAK_COPYLEFT = "WEAK_COPYLEFT"
    STRONG_COPYLEFT = "STRONG_COPYLEFT"
    PROHIBITED = "PROHIBITED"
    UNCLASSIFIED = "UNCLASSIFIED"


class ExemptionApprovalStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class SupplyChainRiskBandEnum(str, enum.Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"
    CRITICAL = "CRITICAL"


class SoftwareProduct(Base):
    __tablename__ = "software_products"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_code = Column(String(64), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    product_type = Column(
        SAEnum(SoftwareProductTypeEnum, name="softwareproducttypeenum"),
        nullable=False,
        default=SoftwareProductTypeEnum.INTERNAL_APPLICATION,
    )
    criticality_tier = Column(
        SAEnum(ProductCriticalityTierEnum, name="productcriticalitytierenum"),
        nullable=False,
        default=ProductCriticalityTierEnum.TIER_3_MODERATE,
    )
    lifecycle_state = Column(
        SAEnum(ProductLifecycleStateEnum, name="productlifecyclestateenum"),
        nullable=False,
        default=ProductLifecycleStateEnum.DRAFT,
        index=True,
    )
    owner_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Cross-Module Lineage Links
    business_process_id = Column(
        Integer,
        ForeignKey("business_processes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ai_system_id = Column(
        Integer,
        ForeignKey("ai_systems.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    vendor_id = Column(
        Integer,
        ForeignKey("vendors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Server-Authoritative Metrics
    supply_chain_exposure_index = Column(Numeric(5, 2), nullable=False, default=0.0)
    total_components_count = Column(Integer, nullable=False, default=0)
    vulnerable_components_count = Column(Integer, nullable=False, default=0)
    policy_violations_count = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    organization = relationship("Organization", backref="software_products")
    owner = relationship("User", foreign_keys=[owner_id], backref="owned_software_products")
    business_process = relationship("BusinessProcess", backref="software_products")
    ai_system = relationship("AISystem", backref="software_products")
    vendor = relationship("Vendor", backref="software_products")
    sbom_documents = relationship(
        "SBOMDocument", back_populates="software_product", cascade="all, delete-orphan"
    )
    exemptions = relationship(
        "SupplyChainExemption", back_populates="software_product", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "product_code", name="uq_software_product_code_per_org"),
        CheckConstraint("supply_chain_exposure_index >= 0.0 AND supply_chain_exposure_index <= 100.0", name="chk_product_scei_range"),
    )


class SBOMDocument(Base):
    __tablename__ = "sbom_documents"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    software_product_id = Column(
        Integer,
        ForeignKey("software_products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sbom_code = Column(String(64), nullable=False, index=True)
    version = Column(String(32), nullable=False)
    format_standard = Column(
        SAEnum(SBOMFormatStandardEnum, name="sbomformatstandardenum"),
        nullable=False,
        default=SBOMFormatStandardEnum.CYCLONEDX_JSON,
    )
    spec_version = Column(String(16), nullable=False, default="1.5")
    sha256_hash = Column(String(64), nullable=False)
    author_name = Column(String(255), nullable=True)
    tool_name = Column(String(255), nullable=True)
    status = Column(
        SAEnum(SBOMStatusEnum, name="sbomstatusenum"),
        nullable=False,
        default=SBOMStatusEnum.ACTIVE,
        index=True,
    )
    component_count = Column(Integer, nullable=False, default=0)
    created_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    organization = relationship("Organization")
    software_product = relationship("SoftwareProduct", back_populates="sbom_documents")
    created_by = relationship("User", foreign_keys=[created_by_id])
    components = relationship(
        "SoftwareComponent", back_populates="sbom_document", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "sbom_code", name="uq_sbom_code_per_org"),
    )


class SoftwareComponent(Base):
    __tablename__ = "software_components"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sbom_document_id = Column(
        Integer,
        ForeignKey("sbom_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    component_name = Column(String(255), nullable=False, index=True)
    version = Column(String(64), nullable=False)
    purl = Column(String(512), nullable=False, index=True)
    ecosystem = Column(
        SAEnum(ComponentEcosystemEnum, name="componentecosystemenum"),
        nullable=False,
        default=ComponentEcosystemEnum.GENERIC,
    )
    dependency_depth = Column(Integer, nullable=False, default=1)
    supplier_name = Column(String(255), nullable=True)
    declared_license = Column(String(128), nullable=False, default="UNKNOWN")
    license_category = Column(
        SAEnum(LicenseCategoryEnum, name="licensecategoryenum"),
        nullable=False,
        default=LicenseCategoryEnum.UNCLASSIFIED,
    )
    is_license_prohibited = Column(Boolean, nullable=False, default=False)

    # Server-Authoritative Metrics
    component_risk_index = Column(Numeric(5, 2), nullable=False, default=0.0)
    max_vulnerability_score = Column(Numeric(5, 2), nullable=False, default=0.0)
    vulnerabilities_count = Column(Integer, nullable=False, default=0)
    is_exempted = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    organization = relationship("Organization")
    sbom_document = relationship("SBOMDocument", back_populates="components")
    vulnerability_links = relationship(
        "ComponentVulnerabilityLink", back_populates="component", cascade="all, delete-orphan"
    )
    exemptions = relationship(
        "SupplyChainExemption", back_populates="component", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("dependency_depth >= 1", name="chk_component_depth_positive"),
        CheckConstraint("component_risk_index >= 0.0 AND component_risk_index <= 100.0", name="chk_component_cri_range"),
    )


class ComponentVulnerabilityLink(Base):
    __tablename__ = "component_vulnerability_links"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    component_id = Column(
        Integer,
        ForeignKey("software_components.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vulnerability_id = Column(
        Integer,
        ForeignKey("vulnerability_exposures.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    cve_identifier = Column(String(64), nullable=False, index=True)
    severity_score = Column(Numeric(4, 2), nullable=False, default=0.0)
    is_exploitable = Column(Boolean, nullable=False, default=False)
    is_reachable = Column(Boolean, nullable=False, default=True)
    fix_version = Column(String(64), nullable=True)
    remediation_plan_id = Column(
        Integer,
        ForeignKey("remediation_plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    organization = relationship("Organization")
    component = relationship("SoftwareComponent", back_populates="vulnerability_links")
    vulnerability = relationship("VulnerabilityExposure", backref="component_links")
    remediation_plan = relationship("RemediationPlan", backref="component_vulnerability_links")

    __table_args__ = (
        CheckConstraint("severity_score >= 0.0 AND severity_score <= 10.0", name="chk_vuln_link_cvss_range"),
    )


class LicenseCompliancePolicy(Base):
    __tablename__ = "license_compliance_policies"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    license_identifier = Column(String(64), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    category = Column(
        SAEnum(LicenseCategoryEnum, name="licensecategoryenum_policy"),
        nullable=False,
        default=LicenseCategoryEnum.PERMISSIVE,
    )
    is_prohibited = Column(Boolean, nullable=False, default=False)
    risk_penalty_points = Column(Numeric(5, 2), nullable=False, default=0.0)
    description = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    organization = relationship("Organization")

    __table_args__ = (
        UniqueConstraint("organization_id", "license_identifier", name="uq_license_policy_per_org"),
        CheckConstraint("risk_penalty_points >= 0.0 AND risk_penalty_points <= 30.0", name="chk_license_risk_penalty_range"),
    )


class SupplyChainExemption(Base):
    __tablename__ = "supply_chain_exemptions"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exemption_code = Column(String(64), nullable=False, index=True)
    software_product_id = Column(
        Integer,
        ForeignKey("software_products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    component_id = Column(
        Integer,
        ForeignKey("software_components.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reason = Column(Text, nullable=False)
    compensating_controls = Column(Text, nullable=False)
    requested_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    reviewed_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    approval_status = Column(
        SAEnum(ExemptionApprovalStatusEnum, name="exemptionapprovalstatusenum"),
        nullable=False,
        default=ExemptionApprovalStatusEnum.PENDING,
        index=True,
    )
    reviewer_notes = Column(Text, nullable=True)
    valid_until = Column(DateTime, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    organization = relationship("Organization")
    software_product = relationship("SoftwareProduct", back_populates="exemptions")
    component = relationship("SoftwareComponent", back_populates="exemptions")
    requested_by = relationship("User", foreign_keys=[requested_by_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])

    __table_args__ = (
        UniqueConstraint("organization_id", "exemption_code", name="uq_sc_exemption_code_per_org"),
    )
