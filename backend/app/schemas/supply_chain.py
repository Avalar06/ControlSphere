from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.supply_chain import (
    ComponentEcosystemEnum,
    ExemptionApprovalStatusEnum,
    LicenseCategoryEnum,
    ProductCriticalityTierEnum,
    ProductLifecycleStateEnum,
    SBOMFormatStandardEnum,
    SBOMStatusEnum,
    SoftwareProductTypeEnum,
    SupplyChainRiskBandEnum,
)


# ─── 1. Software Product Schemas ───────────────────────────────────────────────

class SoftwareProductBase(BaseModel):
    product_code: str = Field(..., min_length=2, max_length=64, description="Unique product code, e.g. PROD-CORE-001")
    name: str = Field(..., min_length=2, max_length=255, description="Software product / application name")
    description: Optional[str] = None
    product_type: SoftwareProductTypeEnum = SoftwareProductTypeEnum.INTERNAL_APPLICATION
    criticality_tier: ProductCriticalityTierEnum = ProductCriticalityTierEnum.TIER_3_MODERATE
    business_process_id: Optional[int] = None
    ai_system_id: Optional[int] = None
    vendor_id: Optional[int] = None


class SoftwareProductCreate(SoftwareProductBase):
    pass


class SoftwareProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    product_type: Optional[SoftwareProductTypeEnum] = None
    criticality_tier: Optional[ProductCriticalityTierEnum] = None
    business_process_id: Optional[int] = None
    ai_system_id: Optional[int] = None
    vendor_id: Optional[int] = None


class SoftwareProductStatusUpdate(BaseModel):
    lifecycle_state: ProductLifecycleStateEnum
    notes: Optional[str] = None


class SoftwareProductResponse(SoftwareProductBase):
    id: int
    organization_id: int
    lifecycle_state: ProductLifecycleStateEnum
    owner_id: int
    supply_chain_exposure_index: float
    total_components_count: int
    vulnerable_components_count: int
    policy_violations_count: int
    risk_band: SupplyChainRiskBandEnum
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── 2. SBOM Document Schemas ──────────────────────────────────────────────────

class SBOMDocumentBase(BaseModel):
    sbom_code: str = Field(..., min_length=2, max_length=64, description="Unique SBOM manifest code, e.g. SBOM-CORE-001")
    version: str = Field(..., min_length=1, max_length=32, description="Semantic version, e.g. 1.0.0")
    format_standard: SBOMFormatStandardEnum = SBOMFormatStandardEnum.CYCLONEDX_JSON
    spec_version: str = Field("1.5", min_length=1, max_length=16)
    sha256_hash: str = Field(..., min_length=64, max_length=64, description="64-character SHA-256 hex digest")
    author_name: Optional[str] = Field(None, max_length=255)
    tool_name: Optional[str] = Field(None, max_length=255)


class SBOMDocumentCreate(SBOMDocumentBase):
    software_product_id: int


class SBOMDocumentResponse(SBOMDocumentBase):
    id: int
    organization_id: int
    software_product_id: int
    status: SBOMStatusEnum
    component_count: int
    created_by_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── 3. Software Component Schemas ─────────────────────────────────────────────

class SoftwareComponentBase(BaseModel):
    component_name: str = Field(..., min_length=1, max_length=255)
    version: str = Field(..., min_length=1, max_length=64)
    purl: str = Field(..., min_length=3, max_length=512, description="Package URL format, e.g. pkg:npm/axios@1.6.8")
    ecosystem: ComponentEcosystemEnum = ComponentEcosystemEnum.GENERIC
    dependency_depth: int = Field(1, ge=1, le=50, description="1 for direct dependency, 2+ for transitive")
    supplier_name: Optional[str] = Field(None, max_length=255)
    declared_license: str = Field("UNKNOWN", max_length=128)
    license_category: LicenseCategoryEnum = LicenseCategoryEnum.UNCLASSIFIED
    is_license_prohibited: bool = False


class SoftwareComponentCreate(SoftwareComponentBase):
    sbom_document_id: int


class SoftwareComponentUpdate(BaseModel):
    dependency_depth: Optional[int] = Field(None, ge=1, le=50)
    supplier_name: Optional[str] = Field(None, max_length=255)
    declared_license: Optional[str] = Field(None, max_length=128)
    license_category: Optional[LicenseCategoryEnum] = None
    is_license_prohibited: Optional[bool] = None


class SoftwareComponentResponse(SoftwareComponentBase):
    id: int
    organization_id: int
    sbom_document_id: int
    component_risk_index: float
    max_vulnerability_score: float
    vulnerabilities_count: int
    is_exempted: bool
    risk_band: SupplyChainRiskBandEnum
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── 4. Component Vulnerability Link Schemas ───────────────────────────────────

class ComponentVulnerabilityLinkBase(BaseModel):
    cve_identifier: str = Field(..., min_length=3, max_length=64, description="CVE identifier e.g. CVE-2021-44228")
    severity_score: float = Field(0.0, ge=0.0, le=10.0, description="CVSS v3.1 base score (0.0 - 10.0)")
    is_exploitable: bool = Field(False, description="Actively exploitable (EPSS > 0.20 or in CISA KEV)")
    is_reachable: bool = Field(True, description="Vulnerable code path is reachable by application")
    fix_version: Optional[str] = Field(None, max_length=64)
    vulnerability_id: Optional[int] = None
    remediation_plan_id: Optional[int] = None


class ComponentVulnerabilityLinkCreate(ComponentVulnerabilityLinkBase):
    component_id: int


class ComponentVulnerabilityLinkResponse(ComponentVulnerabilityLinkBase):
    id: int
    organization_id: int
    component_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── 5. License Compliance Policy Schemas ──────────────────────────────────────

class LicenseCompliancePolicyBase(BaseModel):
    license_identifier: str = Field(..., min_length=1, max_length=64, description="e.g. GPL-3.0-only, MIT, Apache-2.0")
    name: str = Field(..., min_length=2, max_length=255)
    category: LicenseCategoryEnum = LicenseCategoryEnum.PERMISSIVE
    is_prohibited: bool = False
    risk_penalty_points: float = Field(0.0, ge=0.0, le=30.0)
    description: Optional[str] = None


class LicenseCompliancePolicyCreate(LicenseCompliancePolicyBase):
    pass


class LicenseCompliancePolicyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    category: Optional[LicenseCategoryEnum] = None
    is_prohibited: Optional[bool] = None
    risk_penalty_points: Optional[float] = Field(None, ge=0.0, le=30.0)
    description: Optional[str] = None


class LicenseCompliancePolicyResponse(LicenseCompliancePolicyBase):
    id: int
    organization_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── 6. Supply Chain Exemption Schemas (Four-Eyes Gate) ─────────────────────────

class SupplyChainExemptionBase(BaseModel):
    exemption_code: str = Field(..., min_length=2, max_length=64, description="Unique exemption code, e.g. SC-EX-001")
    software_product_id: int
    component_id: int
    reason: str = Field(..., min_length=10, description="Detailed justification for dependency exemption")
    compensating_controls: str = Field(..., min_length=5, description="Technical mitigations and compensating safeguards")
    valid_until: Optional[datetime] = None


class SupplyChainExemptionCreate(SupplyChainExemptionBase):
    pass


class SupplyChainExemptionReviewRequest(BaseModel):
    decision: ExemptionApprovalStatusEnum
    reviewer_notes: str = Field(..., min_length=5, description="Mandatory audit commentary (min 5 chars)")


class SupplyChainExemptionResponse(SupplyChainExemptionBase):
    id: int
    organization_id: int
    requested_by_id: int
    reviewed_by_id: Optional[int] = None
    approval_status: ExemptionApprovalStatusEnum
    reviewer_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── 7. Calculation Preview Schemas (Zero Client Mathematical Authority) ──────

class ComponentCalculatePreviewRequest(BaseModel):
    cvss_scores: List[float] = Field(default_factory=list, description="List of CVSS scores (0.0 - 10.0)")
    is_any_exploitable: bool = Field(False, description="Whether any vulnerability is actively exploitable")
    dependency_depth: int = Field(1, ge=1, le=50)
    license_category: LicenseCategoryEnum = LicenseCategoryEnum.PERMISSIVE
    is_exempted: bool = False


class ComponentCalculatePreviewResponse(BaseModel):
    vulnerability_score: float
    depth_penalty_multiplier: float
    license_risk_points: float
    component_risk_index: float
    risk_band: SupplyChainRiskBandEnum


class ProductCalculatePreviewRequest(BaseModel):
    component_risk_indices: List[float] = Field(default_factory=list, description="List of CRI scores (0.0 - 100.0)")


class ProductCalculatePreviewResponse(BaseModel):
    supply_chain_exposure_index: float
    max_component_risk: float
    average_component_risk: float
    critical_components_count: int
    risk_band: SupplyChainRiskBandEnum


# ─── 8. Executive Posture Telemetry Schema ──────────────────────────────────────

class SupplyChainPostureSummaryResponse(BaseModel):
    total_software_products: int
    active_products_count: int
    total_sboms_indexed: int
    total_components_cataloged: int
    vulnerable_components_count: int
    critical_risk_components_count: int
    prohibited_license_violations_count: int
    pending_exemptions_count: int
    average_supply_chain_exposure_index: float
    criticality_distribution: Dict[str, int]
    license_category_distribution: Dict[str, int]
    risk_band_distribution: Dict[str, int]
