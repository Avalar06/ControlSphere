from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.core.permissions import Permission
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
from app.models.user import User
from app.schemas.supply_chain import (
    ComponentCalculatePreviewRequest,
    ComponentCalculatePreviewResponse,
    ComponentVulnerabilityLinkCreate,
    ComponentVulnerabilityLinkResponse,
    LicenseCompliancePolicyCreate,
    LicenseCompliancePolicyResponse,
    LicenseCompliancePolicyUpdate,
    ProductCalculatePreviewRequest,
    ProductCalculatePreviewResponse,
    SBOMDocumentCreate,
    SBOMDocumentResponse,
    SoftwareComponentCreate,
    SoftwareComponentResponse,
    SoftwareComponentUpdate,
    SoftwareProductCreate,
    SoftwareProductResponse,
    SoftwareProductStatusUpdate,
    SoftwareProductUpdate,
    SupplyChainExemptionCreate,
    SupplyChainExemptionResponse,
    SupplyChainExemptionReviewRequest,
    SupplyChainPostureSummaryResponse,
)
from app.services.supply_chain_service import SupplyChainService

router = APIRouter()


# ─── 1. SOFTWARE PRODUCTS ──────────────────────────────────────────────────────

@router.post("/products", response_model=SoftwareProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: SoftwareProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SUPPLYCHAIN_MANAGE)),
):
    """Create and register a new Software Product in the Supply Chain catalog."""
    return SupplyChainService.create_product(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        data=payload,
    )


@router.get("/products", response_model=List[SoftwareProductResponse])
def list_products(
    lifecycle_state: Optional[ProductLifecycleStateEnum] = None,
    criticality_tier: Optional[ProductCriticalityTierEnum] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SUPPLYCHAIN_READ)),
):
    """List tenant-scoped software products with optional state/criticality filtering."""
    return SupplyChainService.list_products(
        db=db,
        org_id=current_user.organization_id,
        lifecycle_state=lifecycle_state,
        criticality_tier=criticality_tier,
        skip=skip,
        limit=limit,
    )


@router.get("/products/{product_id}", response_model=SoftwareProductResponse)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SUPPLYCHAIN_READ)),
):
    """Retrieve details of a single software product."""
    return SupplyChainService.get_product(
        db=db,
        org_id=current_user.organization_id,
        product_id=product_id,
    )


@router.put("/products/{product_id}", response_model=SoftwareProductResponse)
def update_product(
    product_id: int,
    payload: SoftwareProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SUPPLYCHAIN_MANAGE)),
):
    """Update metadata and properties of an existing software product."""
    return SupplyChainService.update_product(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        product_id=product_id,
        data=payload,
    )


@router.patch("/products/{product_id}/status", response_model=SoftwareProductResponse)
def update_product_status(
    product_id: int,
    payload: SoftwareProductStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SUPPLYCHAIN_MANAGE)),
):
    """Transition product lifecycle state governed by the state machine."""
    return SupplyChainService.update_product_status(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        product_id=product_id,
        status_data=payload,
    )


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SUPPLYCHAIN_MANAGE)),
):
    """Delete a software product (must not be in ACTIVE state)."""
    SupplyChainService.delete_product(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        product_id=product_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─── 2. SBOM INGESTION & REGISTRATION ──────────────────────────────────────────

@router.post("/products/{product_id}/sboms", response_model=SBOMDocumentResponse, status_code=status.HTTP_201_CREATED)
def ingest_sbom(
    product_id: int,
    payload: SBOMDocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SUPPLYCHAIN_MANAGE)),
):
    """Ingest and register a new SBOM manifest for a software product."""
    # Ensure payload product matches route
    payload.software_product_id = product_id
    return SupplyChainService.ingest_sbom(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        product_id=product_id,
        data=payload,
    )


@router.get("/products/{product_id}/sboms", response_model=List[SBOMDocumentResponse])
def list_product_sboms(
    product_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SUPPLYCHAIN_READ)),
):
    """List all SBOMs ingested for a specific software product."""
    # Ensure product belongs to organization
    SupplyChainService.get_product(db, current_user.organization_id, product_id)
    return SupplyChainService.list_sboms(
        db=db,
        org_id=current_user.organization_id,
        product_id=product_id,
        skip=skip,
        limit=limit,
    )


@router.get("/sboms/{sbom_id}", response_model=SBOMDocumentResponse)
def get_sbom(
    sbom_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SUPPLYCHAIN_READ)),
):
    """Retrieve details and metadata of an SBOM document."""
    return SupplyChainService.get_sbom(
        db=db,
        org_id=current_user.organization_id,
        sbom_id=sbom_id,
    )


# ─── 3. SOFTWARE COMPONENTS ────────────────────────────────────────────────────

@router.post("/sboms/{sbom_id}/components", response_model=SoftwareComponentResponse, status_code=status.HTTP_201_CREATED)
def add_component_to_sbom(
    sbom_id: int,
    payload: SoftwareComponentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SUPPLYCHAIN_MANAGE)),
):
    """Catalog a direct or transitive component under an SBOM document."""
    payload.sbom_document_id = sbom_id
    return SupplyChainService.add_component_to_sbom(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        sbom_id=sbom_id,
        data=payload,
    )


@router.get("/sboms/{sbom_id}/components", response_model=List[SoftwareComponentResponse])
def list_sbom_components(
    sbom_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SUPPLYCHAIN_READ)),
):
    """List components indexed within an SBOM manifest."""
    SupplyChainService.get_sbom(db, current_user.organization_id, sbom_id)
    return SupplyChainService.list_components(
        db=db,
        org_id=current_user.organization_id,
        sbom_id=sbom_id,
        skip=skip,
        limit=limit,
    )


@router.get("/components/{component_id}", response_model=SoftwareComponentResponse)
def get_component(
    component_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SUPPLYCHAIN_READ)),
):
    """Retrieve details of a software component."""
    return SupplyChainService.get_component(
        db=db,
        org_id=current_user.organization_id,
        component_id=component_id,
    )


# ─── 4. VULNERABILITY LINKING ─────────────────────────────────────────────────

@router.post("/components/{component_id}/vulnerabilities", response_model=ComponentVulnerabilityLinkResponse, status_code=status.HTTP_201_CREATED)
def add_vulnerability_link(
    component_id: int,
    payload: ComponentVulnerabilityLinkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SUPPLYCHAIN_ASSESS)),
):
    """Link a vulnerability/CVE to a software component."""
    payload.component_id = component_id
    return SupplyChainService.add_vulnerability_link(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        component_id=component_id,
        data=payload,
    )


# ─── 5. LIVE CALCULATION PREVIEWS (Zero Client Authority) ──────────────────────

@router.post("/components/calculate-preview", response_model=ComponentCalculatePreviewResponse)
def calculate_component_preview(
    payload: ComponentCalculatePreviewRequest,
    current_user: User = Depends(require_permission(Permission.SUPPLYCHAIN_READ)),
):
    """Server-authoritative live calculation preview for Component Risk Index (CRI)."""
    return SupplyChainService.calculate_component_preview(payload)


@router.post("/products/calculate-preview", response_model=ProductCalculatePreviewResponse)
def calculate_product_preview(
    payload: ProductCalculatePreviewRequest,
    current_user: User = Depends(require_permission(Permission.SUPPLYCHAIN_READ)),
):
    """Server-authoritative live calculation preview for Product Supply Chain Exposure Index (SCEI)."""
    return SupplyChainService.calculate_product_preview(payload)


# ─── 6. LICENSE POLICIES ──────────────────────────────────────────────────────

@router.post("/policies", response_model=LicenseCompliancePolicyResponse, status_code=status.HTTP_201_CREATED)
def create_license_policy(
    payload: LicenseCompliancePolicyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SUPPLYCHAIN_MANAGE)),
):
    """Define a license compliance rule/prohibition for the organization."""
    return SupplyChainService.create_license_policy(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        data=payload,
    )


@router.get("/policies", response_model=List[LicenseCompliancePolicyResponse])
def list_license_policies(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SUPPLYCHAIN_READ)),
):
    """List all organizational license compliance policies."""
    return SupplyChainService.list_license_policies(
        db=db,
        org_id=current_user.organization_id,
    )


# ─── 7. FOUR-EYES EXEMPTION GOVERNANCE ────────────────────────────────────────

@router.post("/exemptions", response_model=SupplyChainExemptionResponse, status_code=status.HTTP_201_CREATED)
def request_exemption(
    payload: SupplyChainExemptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SUPPLYCHAIN_ASSESS)),
):
    """Submit a request for supply chain risk/license exemption."""
    return SupplyChainService.request_exemption(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        data=payload,
    )


@router.get("/exemptions", response_model=List[SupplyChainExemptionResponse])
def list_exemptions(
    product_id: Optional[int] = None,
    status_filter: Optional[ExemptionApprovalStatusEnum] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SUPPLYCHAIN_READ)),
):
    """List supply chain exemptions with optional status and product filters."""
    return SupplyChainService.list_exemptions(
        db=db,
        org_id=current_user.organization_id,
        product_id=product_id,
        status_filter=status_filter,
        skip=skip,
        limit=limit,
    )


@router.get("/exemptions/{exemption_id}", response_model=SupplyChainExemptionResponse)
def get_exemption(
    exemption_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SUPPLYCHAIN_READ)),
):
    """Retrieve details of a supply chain exemption."""
    return SupplyChainService.get_exemption(
        db=db,
        org_id=current_user.organization_id,
        exemption_id=exemption_id,
    )


@router.post("/exemptions/{exemption_id}/review", response_model=SupplyChainExemptionResponse)
def review_exemption(
    exemption_id: int,
    payload: SupplyChainExemptionReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SUPPLYCHAIN_APPROVE)),
):
    """Four-Eyes approval or rejection of a supply chain exemption request."""
    return SupplyChainService.review_exemption(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        exemption_id=exemption_id,
        data=payload,
    )


# ─── 8. EXECUTIVE POSTURE TELEMETRY ───────────────────────────────────────────

@router.get("/summary/posture", response_model=SupplyChainPostureSummaryResponse)
def get_posture_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SUPPLYCHAIN_READ)),
):
    """Retrieve aggregated supply chain risk metrics and distribution telemetry."""
    return SupplyChainService.get_posture_summary(
        db=db,
        org_id=current_user.organization_id,
    )
