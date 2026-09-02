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
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


# ─────────────────────────────────────────────────────────────────────────────
# Phase 18: CLOUDSEC-GRC Domain Enums
# ─────────────────────────────────────────────────────────────────────────────

class CloudProviderEnum(str, enum.Enum):
    AWS = "AWS"
    AZURE = "AZURE"
    GCP = "GCP"
    OCI = "OCI"
    ALIBABA = "ALIBABA"


class CloudAssetTypeEnum(str, enum.Enum):
    S3_BUCKET = "S3_BUCKET"
    IAM_ROLE = "IAM_ROLE"
    EC2_INSTANCE = "EC2_INSTANCE"
    KUBERNETES_CLUSTER = "KUBERNETES_CLUSTER"
    RDS_DATABASE = "RDS_DATABASE"
    KEY_VAULT = "KEY_VAULT"
    SECURITY_GROUP = "SECURITY_GROUP"
    SERVERLESS_FUNCTION = "SERVERLESS_FUNCTION"
    CONTAINER_REGISTRY = "CONTAINER_REGISTRY"
    VIRTUAL_NETWORK = "VIRTUAL_NETWORK"


class CloudEnvironmentEnum(str, enum.Enum):
    PRODUCTION = "PRODUCTION"
    STAGING = "STAGING"
    DEVELOPMENT = "DEVELOPMENT"
    SANDBOX = "SANDBOX"


class CloudCriticalityEnum(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class CloudPostureStatusEnum(str, enum.Enum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    DEVIATED = "DEVIATED"
    UNASSESSED = "UNASSESSED"


class CloudLifecycleStateEnum(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PROVISIONING = "PROVISIONING"
    MAINTENANCE = "MAINTENANCE"
    DECOMMISSIONED = "DECOMMISSIONED"


class BenchmarkFrameworkEnum(str, enum.Enum):
    CIS_AWS_FOUNDATIONS = "CIS_AWS_FOUNDATIONS"
    CIS_AZURE_FOUNDATIONS = "CIS_AZURE_FOUNDATIONS"
    CIS_GCP_FOUNDATIONS = "CIS_GCP_FOUNDATIONS"
    NIST_SP_800_53_CLOUD = "NIST_SP_800_53_CLOUD"
    SOC2_CLOUD_SECURITY = "SOC2_CLOUD_SECURITY"


class RuleSeverityEnum(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class EvaluationStatusEnum(str, enum.Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    SUPPRESSED = "SUPPRESSED"
    REMEDIATED = "REMEDIATED"


class DriftSeverityEnum(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class DriftStatusEnum(str, enum.Enum):
    DETECTED = "DETECTED"
    ACCEPTED_CHANGE = "ACCEPTED_CHANGE"
    REMEDIATING = "REMEDIATING"
    REVERTED = "REVERTED"


class DataAccessScopeEnum(str, enum.Enum):
    FULL_DATASTORE = "FULL_DATASTORE"
    RESTRICTED_READ = "RESTRICTED_READ"
    METADATA_ONLY = "METADATA_ONLY"


class BlastRadiusBandEnum(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"


# ─────────────────────────────────────────────────────────────────────────────
# 1. CLOUD ASSET MODEL
# ─────────────────────────────────────────────────────────────────────────────

class CloudAsset(Base):
    """Authoritative Multi-Cloud Asset Catalog & Configuration Posture Record."""
    __tablename__ = "cloud_assets"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset_code = Column(String(64), nullable=False, index=True)
    provider = Column(
        Enum(CloudProviderEnum),
        nullable=False,
        default=CloudProviderEnum.AWS,
        index=True,
    )
    account_id = Column(String(128), nullable=False, index=True)  # AWS Account ID, Azure Subscription ID, GCP Project
    region = Column(String(64), nullable=False)
    resource_type = Column(
        Enum(CloudAssetTypeEnum),
        nullable=False,
        index=True,
    )
    resource_arn = Column(String(512), nullable=False, index=True)
    resource_name = Column(String(255), nullable=False)
    environment = Column(
        Enum(CloudEnvironmentEnum),
        nullable=False,
        default=CloudEnvironmentEnum.PRODUCTION,
        index=True,
    )
    criticality = Column(
        Enum(CloudCriticalityEnum),
        nullable=False,
        default=CloudCriticalityEnum.HIGH,
    )
    posture_status = Column(
        Enum(CloudPostureStatusEnum),
        nullable=False,
        default=CloudPostureStatusEnum.UNASSESSED,
        index=True,
    )
    posture_score = Column(Numeric(5, 2), nullable=False, default=100.00)  # 0.00 to 100.00 (100 = full compliance)
    blast_radius_score = Column(Numeric(5, 2), nullable=False, default=0.00)  # 0.00 to 100.00 (0 = minimal impact)
    lifecycle_state = Column(
        Enum(CloudLifecycleStateEnum),
        nullable=False,
        default=CloudLifecycleStateEnum.ACTIVE,
        index=True,
    )
    is_internet_facing = Column(Boolean, nullable=False, default=False)
    encryption_enabled = Column(Boolean, nullable=False, default=True)
    owner_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Cross-Module Traceability
    software_product_id = Column(
        Integer,
        ForeignKey("software_products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    remediation_plan_id = Column(
        Integer,
        ForeignKey("remediation_plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    tags = Column(Text, nullable=True)  # JSON-encoded key-values
    configuration_metadata = Column(Text, nullable=True)  # JSON-encoded sanitized state

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
        UniqueConstraint("organization_id", "asset_code", name="uq_cloud_asset_tenant_code"),
        UniqueConstraint("organization_id", "resource_arn", name="uq_cloud_asset_tenant_arn"),
        CheckConstraint("posture_score >= 0.00 AND posture_score <= 100.00", name="chk_cloud_asset_posture_score"),
        CheckConstraint("blast_radius_score >= 0.00 AND blast_radius_score <= 100.00", name="chk_cloud_asset_blast_radius_score"),
    )

    # Relationships
    findings = relationship("CloudSecurityFinding", back_populates="cloud_asset", cascade="all, delete-orphan")
    drifts = relationship("CloudConfigurationDrift", back_populates="cloud_asset", cascade="all, delete-orphan")
    blast_radii = relationship("CloudIAMBlastRadius", back_populates="cloud_asset", cascade="all, delete-orphan")


# ─────────────────────────────────────────────────────────────────────────────
# 2. CLOUD BENCHMARKS & CIS RULES
# ─────────────────────────────────────────────────────────────────────────────

class CloudSecurityBenchmark(Base):
    """Authoritative CIS and Cloud Security Benchmark standard."""
    __tablename__ = "cloud_security_benchmarks"

    id = Column(Integer, primary_key=True, index=True)
    benchmark_code = Column(String(64), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    version = Column(String(32), nullable=False)
    framework = Column(
        Enum(BenchmarkFrameworkEnum),
        nullable=False,
        index=True,
    )
    provider = Column(
        Enum(CloudProviderEnum),
        nullable=False,
        index=True,
    )
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    total_rules_count = Column(Integer, nullable=False, default=0)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    rules = relationship("CloudBenchmarkRule", back_populates="benchmark", cascade="all, delete-orphan")


class CloudBenchmarkRule(Base):
    """Granular benchmark security check rule."""
    __tablename__ = "cloud_benchmark_rules"

    id = Column(Integer, primary_key=True, index=True)
    benchmark_id = Column(
        Integer,
        ForeignKey("cloud_security_benchmarks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_code = Column(String(64), nullable=False, unique=True, index=True)  # e.g. CIS-AWS-1.16
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    section = Column(String(128), nullable=False)  # e.g. "1. Identity and Access Management"
    severity = Column(
        Enum(RuleSeverityEnum),
        nullable=False,
        default=RuleSeverityEnum.HIGH,
    )
    rationale = Column(Text, nullable=True)
    remediation_guidance = Column(Text, nullable=True)
    
    # NIST CSF / Control Mapping
    control_id = Column(
        Integer,
        ForeignKey("framework_subcategories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    benchmark = relationship("CloudSecurityBenchmark", back_populates="rules")
    findings = relationship("CloudSecurityFinding", back_populates="rule")


# ─────────────────────────────────────────────────────────────────────────────
# 3. CLOUD SECURITY FINDINGS (EVALUATIONS)
# ─────────────────────────────────────────────────────────────────────────────

class CloudSecurityFinding(Base):
    """CSPM Evaluation Finding against a Cloud Asset."""
    __tablename__ = "cloud_security_findings"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    finding_code = Column(String(64), nullable=False, index=True)
    cloud_asset_id = Column(
        Integer,
        ForeignKey("cloud_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_id = Column(
        Integer,
        ForeignKey("cloud_benchmark_rules.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    evaluation_status = Column(
        Enum(EvaluationStatusEnum),
        nullable=False,
        default=EvaluationStatusEnum.FAILED,
        index=True,
    )
    severity = Column(
        Enum(RuleSeverityEnum),
        nullable=False,
        default=RuleSeverityEnum.HIGH,
        index=True,
    )
    risk_score = Column(Numeric(5, 2), nullable=False, default=50.00)
    actual_value = Column(Text, nullable=True)
    expected_value = Column(Text, nullable=True)
    
    # Remediation Linkage
    remediation_plan_id = Column(
        Integer,
        ForeignKey("remediation_plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    evaluated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("organization_id", "finding_code", name="uq_cloud_finding_tenant_code"),
        CheckConstraint("risk_score >= 0.00 AND risk_score <= 100.00", name="chk_cloud_finding_risk_score"),
    )

    # Relationships
    cloud_asset = relationship("CloudAsset", back_populates="findings")
    rule = relationship("CloudBenchmarkRule", back_populates="findings")


# ─────────────────────────────────────────────────────────────────────────────
# 4. CONFIGURATION DRIFT EVENTS
# ─────────────────────────────────────────────────────────────────────────────

class CloudConfigurationDrift(Base):
    """Drift detection event comparing running cloud state with governed baseline."""
    __tablename__ = "cloud_configuration_drifts"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    drift_code = Column(String(64), nullable=False, index=True)
    cloud_asset_id = Column(
        Integer,
        ForeignKey("cloud_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attribute_path = Column(String(255), nullable=False)  # e.g. "ingress_rules[0].cidr_ip"
    baseline_value = Column(Text, nullable=False)
    drifted_value = Column(Text, nullable=False)
    drift_severity = Column(
        Enum(DriftSeverityEnum),
        nullable=False,
        default=DriftSeverityEnum.HIGH,
        index=True,
    )
    drift_score = Column(Numeric(5, 2), nullable=False, default=50.00)
    status = Column(
        Enum(DriftStatusEnum),
        nullable=False,
        default=DriftStatusEnum.DETECTED,
        index=True,
    )

    detected_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("organization_id", "drift_code", name="uq_cloud_drift_tenant_code"),
        CheckConstraint("drift_score >= 0.00 AND drift_score <= 100.00", name="chk_cloud_drift_score"),
    )

    # Relationships
    cloud_asset = relationship("CloudAsset", back_populates="drifts")


# ─────────────────────────────────────────────────────────────────────────────
# 5. CLOUD IAM BLAST RADIUS ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

class CloudIAMBlastRadius(Base):
    """IAM Principal Privilege & Cloud Resource Blast Radius quantification."""
    __tablename__ = "cloud_iam_blast_radii"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    analysis_code = Column(String(64), nullable=False, index=True)
    cloud_asset_id = Column(
        Integer,
        ForeignKey("cloud_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    iam_principal_arn = Column(String(512), nullable=False)
    effective_permissions_count = Column(Integer, nullable=False, default=1)
    admin_privilege_granted = Column(Boolean, nullable=False, default=False)
    cross_account_access = Column(Boolean, nullable=False, default=False)
    data_access_scope = Column(
        Enum(DataAccessScopeEnum),
        nullable=False,
        default=DataAccessScopeEnum.RESTRICTED_READ,
    )
    blast_radius_index = Column(Numeric(5, 2), nullable=False, default=0.00)
    risk_band = Column(
        Enum(BlastRadiusBandEnum),
        nullable=False,
        default=BlastRadiusBandEnum.LOW,
    )

    analyzed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "analysis_code", name="uq_cloud_blast_radius_tenant_code"),
        CheckConstraint("blast_radius_index >= 0.00 AND blast_radius_index <= 100.00", name="chk_cloud_blast_radius_index"),
    )

    # Relationships
    cloud_asset = relationship("CloudAsset", back_populates="blast_radii")
