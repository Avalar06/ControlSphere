from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.cloudsec import (
    BenchmarkFrameworkEnum,
    BlastRadiusBandEnum,
    CloudAssetTypeEnum,
    CloudCriticalityEnum,
    CloudEnvironmentEnum,
    CloudLifecycleStateEnum,
    CloudPostureStatusEnum,
    CloudProviderEnum,
    DataAccessScopeEnum,
    DriftSeverityEnum,
    DriftStatusEnum,
    EvaluationStatusEnum,
    RuleSeverityEnum,
)


# ─── 1. Cloud Asset Schemas ────────────────────────────────────────────────────

class CloudAssetBase(BaseModel):
    asset_code: str = Field(..., min_length=2, max_length=64, description="Unique cloud asset code, e.g. CLOUD-AWS-S3-001")
    provider: CloudProviderEnum = CloudProviderEnum.AWS
    account_id: str = Field(..., min_length=2, max_length=128, description="AWS Account ID, Azure Subscription ID, or GCP Project ID")
    region: str = Field(..., min_length=2, max_length=64, description="Cloud Region, e.g. us-east-1, westeurope")
    resource_type: CloudAssetTypeEnum
    resource_arn: str = Field(..., min_length=5, max_length=512, description="Cloud resource identifier / ARN / URI")
    resource_name: str = Field(..., min_length=2, max_length=255, description="Human-readable resource name")
    environment: CloudEnvironmentEnum = CloudEnvironmentEnum.PRODUCTION
    criticality: CloudCriticalityEnum = CloudCriticalityEnum.HIGH
    is_internet_facing: bool = False
    encryption_enabled: bool = True
    software_product_id: Optional[int] = None
    remediation_plan_id: Optional[int] = None
    tags: Optional[str] = None
    configuration_metadata: Optional[str] = None


class CloudAssetCreate(CloudAssetBase):
    pass


class CloudAssetUpdate(BaseModel):
    resource_name: Optional[str] = Field(None, min_length=2, max_length=255)
    environment: Optional[CloudEnvironmentEnum] = None
    criticality: Optional[CloudCriticalityEnum] = None
    is_internet_facing: Optional[bool] = None
    encryption_enabled: Optional[bool] = None
    software_product_id: Optional[int] = None
    remediation_plan_id: Optional[int] = None
    tags: Optional[str] = None
    configuration_metadata: Optional[str] = None


class CloudAssetStatusUpdate(BaseModel):
    lifecycle_state: CloudLifecycleStateEnum
    notes: Optional[str] = None


class CloudAssetResponse(CloudAssetBase):
    id: int
    organization_id: int
    posture_status: CloudPostureStatusEnum
    posture_score: float
    blast_radius_score: float
    lifecycle_state: CloudLifecycleStateEnum
    owner_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── 2. Cloud Benchmark & Rule Schemas ─────────────────────────────────────────

class CloudSecurityBenchmarkBase(BaseModel):
    benchmark_code: str = Field(..., min_length=2, max_length=64)
    name: str = Field(..., min_length=2, max_length=255)
    version: str = Field(..., min_length=1, max_length=32)
    framework: BenchmarkFrameworkEnum
    provider: CloudProviderEnum
    description: Optional[str] = None
    is_active: bool = True


class CloudSecurityBenchmarkCreate(CloudSecurityBenchmarkBase):
    pass


class CloudBenchmarkRuleBase(BaseModel):
    rule_code: str = Field(..., min_length=2, max_length=64)
    title: str = Field(..., min_length=2, max_length=255)
    description: str
    section: str = Field(..., min_length=1, max_length=128)
    severity: RuleSeverityEnum = RuleSeverityEnum.HIGH
    rationale: Optional[str] = None
    remediation_guidance: Optional[str] = None
    control_id: Optional[int] = None


class CloudBenchmarkRuleCreate(CloudBenchmarkRuleBase):
    benchmark_id: int


class CloudBenchmarkRuleResponse(CloudBenchmarkRuleBase):
    id: int
    benchmark_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CloudSecurityBenchmarkResponse(CloudSecurityBenchmarkBase):
    id: int
    total_rules_count: int
    rules: List[CloudBenchmarkRuleResponse] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── 3. Cloud Security Findings Schemas ────────────────────────────────────────

class CloudSecurityFindingCreate(BaseModel):
    finding_code: str = Field(..., min_length=2, max_length=64)
    cloud_asset_id: int
    rule_id: int
    evaluation_status: EvaluationStatusEnum = EvaluationStatusEnum.FAILED
    severity: RuleSeverityEnum = RuleSeverityEnum.HIGH
    actual_value: Optional[str] = None
    expected_value: Optional[str] = None
    remediation_plan_id: Optional[int] = None


class CloudSecurityFindingResponse(BaseModel):
    id: int
    organization_id: int
    finding_code: str
    cloud_asset_id: int
    rule_id: int
    evaluation_status: EvaluationStatusEnum
    severity: RuleSeverityEnum
    risk_score: float
    actual_value: Optional[str] = None
    expected_value: Optional[str] = None
    remediation_plan_id: Optional[int] = None
    evaluated_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ─── 4. Cloud Configuration Drift Schemas ──────────────────────────────────────

class CloudConfigurationDriftCreate(BaseModel):
    drift_code: str = Field(..., min_length=2, max_length=64)
    cloud_asset_id: int
    attribute_path: str = Field(..., min_length=2, max_length=255)
    baseline_value: str
    drifted_value: str
    drift_severity: DriftSeverityEnum = DriftSeverityEnum.HIGH


class CloudConfigurationDriftResponse(BaseModel):
    id: int
    organization_id: int
    drift_code: str
    cloud_asset_id: int
    attribute_path: str
    baseline_value: str
    drifted_value: str
    drift_severity: DriftSeverityEnum
    drift_score: float
    status: DriftStatusEnum
    detected_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ─── 5. IAM Blast Radius Schemas ───────────────────────────────────────────────

class CloudIAMBlastRadiusCreate(BaseModel):
    analysis_code: str = Field(..., min_length=2, max_length=64)
    cloud_asset_id: int
    iam_principal_arn: str = Field(..., min_length=5, max_length=512)
    effective_permissions_count: int = Field(1, ge=0, le=10000)
    admin_privilege_granted: bool = False
    cross_account_access: bool = False
    data_access_scope: DataAccessScopeEnum = DataAccessScopeEnum.RESTRICTED_READ


class CloudIAMBlastRadiusPreviewRequest(BaseModel):
    effective_permissions_count: int = Field(1, ge=0, le=10000)
    admin_privilege_granted: bool = False
    cross_account_access: bool = False
    data_access_scope: DataAccessScopeEnum = DataAccessScopeEnum.RESTRICTED_READ


class CloudIAMBlastRadiusPreviewResponse(BaseModel):
    blast_radius_index: float
    risk_band: BlastRadiusBandEnum
    breakdown: Dict[str, float]


class CloudIAMBlastRadiusResponse(BaseModel):
    id: int
    organization_id: int
    analysis_code: str
    cloud_asset_id: int
    iam_principal_arn: str
    effective_permissions_count: int
    admin_privilege_granted: bool
    cross_account_access: bool
    data_access_scope: DataAccessScopeEnum
    blast_radius_index: float
    risk_band: BlastRadiusBandEnum
    analyzed_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── 6. Posture Summary & Executive Telemetry ──────────────────────────────────

class CloudPostureSummaryResponse(BaseModel):
    total_cloud_assets: int
    compliant_assets_count: int
    non_compliant_assets_count: int
    deviated_assets_count: int
    total_open_findings: int
    critical_findings_count: int
    active_drifts_count: int
    average_posture_score: float
    average_blast_radius_score: float
    provider_distribution: Dict[str, int]
    environment_distribution: Dict[str, int]
