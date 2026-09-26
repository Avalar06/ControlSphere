from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_permission
from app.core.permissions import Permission
from app.models.privacy import DataSensitivityLevel
from app.models.user import User
from app.schemas.data_governance import (
    DataAssetCloudLinkCreate,
    DataAssetCloudLinkResponse,
    DataAssetControlLinkCreate,
    DataAssetControlLinkResponse,
    DataAssetDeprecateRequest,
    DataAssetEvidenceLinkCreate,
    DataAssetEvidenceLinkResponse,
    DataAssetProcessingLinkCreate,
    DataAssetProcessingLinkResponse,
    DataAssetRegisterRequest,
    DataAssetRestoreRequest,
    DataAssetRetireRequest,
    DataClassificationLevelCreate,
    DataClassificationLevelResponse,
    DataClassificationRecordResponse,
    DataClassificationRejectRequest,
    DataClassificationRequestCreate,
    DataClassificationSchemeCreate,
    DataClassificationSchemeResponse,
    DataGovernanceSummaryResponse,
    DataLineageEdgeCreate,
    DataLineageEdgeResponse,
    DataLineageEdgeRevokeRequest,
    DataOwnershipUpdateRequest,
    GovernedDataAssetCreate,
    GovernedDataAssetDossierResponse,
    GovernedDataAssetResponse,
    GovernedDataAssetUpdate,
)
from app.services.data_governance_service import DataGovernanceService

router = APIRouter()


# ─── 1. SUMMARY & TELEMETRY ───────────────────────────────────────────────────

@router.get("/summary", response_model=DataGovernanceSummaryResponse)
def get_data_governance_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.DATA_GOV_READ)),
):
    return DataGovernanceService.get_governance_summary(
        db=db,
        organization_id=current_user.organization_id,
    )


# ─── 2. CLASSIFICATION SCHEMES & LEVELS ───────────────────────────────────────

@router.post(
    "/schemes",
    response_model=DataClassificationSchemeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_classification_scheme(
    payload: DataClassificationSchemeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.DATA_GOV_MANAGE)),
):
    return DataGovernanceService.create_scheme(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        payload=payload,
    )


@router.get("/schemes", response_model=List[DataClassificationSchemeResponse])
def list_classification_schemes(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.DATA_GOV_READ)),
):
    return DataGovernanceService.list_schemes(
        db=db,
        organization_id=current_user.organization_id,
        status_filter=status_filter,
    )


@router.get("/schemes/{scheme_id}", response_model=DataClassificationSchemeResponse)
def get_classification_scheme(
    scheme_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.DATA_GOV_READ)),
):
    return DataGovernanceService.get_scheme(
        db=db,
        organization_id=current_user.organization_id,
        scheme_id=scheme_id,
    )


@router.post(
    "/schemes/{scheme_id}/levels",
    response_model=DataClassificationLevelResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_classification_level(
    scheme_id: int,
    payload: DataClassificationLevelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.DATA_GOV_MANAGE)),
):
    return DataGovernanceService.add_level_to_scheme(
        db=db,
        organization_id=current_user.organization_id,
        scheme_id=scheme_id,
        actor_id=current_user.id,
        payload=payload,
    )


@router.post("/schemes/{scheme_id}/submit", response_model=DataClassificationSchemeResponse)
def submit_classification_scheme(
    scheme_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.DATA_GOV_MANAGE)),
):
    return DataGovernanceService.submit_scheme(
        db=db,
        organization_id=current_user.organization_id,
        scheme_id=scheme_id,
        actor_id=current_user.id,
    )


@router.post("/schemes/{scheme_id}/approve", response_model=DataClassificationSchemeResponse)
def approve_classification_scheme(
    scheme_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.DATA_GOV_APPROVE)),
):
    return DataGovernanceService.approve_scheme(
        db=db,
        organization_id=current_user.organization_id,
        scheme_id=scheme_id,
        approver_id=current_user.id,
    )


# ─── 3. GOVERNED DATA ASSETS & LIFECYCLE ──────────────────────────────────────

@router.post(
    "/assets",
    response_model=GovernedDataAssetResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_governed_data_asset(
    payload: GovernedDataAssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.DATA_GOV_MANAGE)),
):
    return DataGovernanceService.create_governed_asset(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        payload=payload,
    )


@router.get("/assets", response_model=List[GovernedDataAssetResponse])
def list_governed_data_assets(
    lifecycle_state: Optional[str] = None,
    sensitivity: Optional[DataSensitivityLevel] = None,
    classification_status: Optional[str] = None,
    owner_id: Optional[int] = None,
    steward_id: Optional[int] = None,
    cloud_asset_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.DATA_GOV_READ)),
):
    return DataGovernanceService.list_governed_assets(
        db=db,
        organization_id=current_user.organization_id,
        lifecycle_state=lifecycle_state,
        sensitivity=sensitivity,
        classification_status=classification_status,
        owner_id=owner_id,
        steward_id=steward_id,
        cloud_asset_id=cloud_asset_id,
    )


@router.get("/assets/{asset_id}", response_model=GovernedDataAssetDossierResponse)
def get_governed_data_asset_dossier(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.DATA_GOV_READ)),
):
    return DataGovernanceService.get_asset_governance_dossier(
        db=db,
        organization_id=current_user.organization_id,
        asset_id=asset_id,
    )


@router.put("/assets/{asset_id}", response_model=GovernedDataAssetResponse)
def update_governed_data_asset(
    asset_id: int,
    payload: GovernedDataAssetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.DATA_GOV_MANAGE)),
):
    return DataGovernanceService.update_governed_asset(
        db=db,
        organization_id=current_user.organization_id,
        asset_id=asset_id,
        actor_id=current_user.id,
        payload=payload,
    )


@router.post("/assets/{asset_id}/register", response_model=GovernedDataAssetResponse)
def register_discovered_data_asset(
    asset_id: int,
    payload: DataAssetRegisterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.DATA_GOV_MANAGE)),
):
    return DataGovernanceService.register_discovered_asset(
        db=db,
        organization_id=current_user.organization_id,
        asset_id=asset_id,
        actor_id=current_user.id,
        payload=payload,
    )


@router.post("/assets/{asset_id}/activate", response_model=GovernedDataAssetResponse)
def activate_governed_data_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.DATA_GOV_MANAGE)),
):
    return DataGovernanceService.activate_asset(
        db=db,
        organization_id=current_user.organization_id,
        asset_id=asset_id,
        actor_id=current_user.id,
    )


# ─── 4. OWNERSHIP & STEWARDSHIP ───────────────────────────────────────────────

@router.post("/assets/{asset_id}/ownership", response_model=GovernedDataAssetResponse)
def update_asset_ownership(
    asset_id: int,
    payload: DataOwnershipUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.DATA_GOV_OWNER_MANAGE)),
):
    return DataGovernanceService.update_ownership(
        db=db,
        organization_id=current_user.organization_id,
        asset_id=asset_id,
        actor_id=current_user.id,
        payload=payload,
    )


@router.post("/assets/{asset_id}/ownership/approve", response_model=GovernedDataAssetResponse)
def approve_asset_ownership_transfer(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.DATA_GOV_APPROVE)),
):
    return DataGovernanceService.approve_ownership_transfer(
        db=db,
        organization_id=current_user.organization_id,
        asset_id=asset_id,
        approver_id=current_user.id,
    )


# ─── 5. CLASSIFICATION RECORDS & FOUR-EYES APPROVAL ───────────────────────────

@router.post(
    "/assets/{asset_id}/classifications",
    response_model=DataClassificationRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
def request_asset_classification(
    asset_id: int,
    payload: DataClassificationRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.DATA_GOV_CLASSIFY)),
):
    return DataGovernanceService.request_classification(
        db=db,
        organization_id=current_user.organization_id,
        asset_id=asset_id,
        actor_id=current_user.id,
        payload=payload,
    )


@router.get(
    "/assets/{asset_id}/classifications",
    response_model=List[DataClassificationRecordResponse],
)
def list_asset_classifications(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.DATA_GOV_READ)),
):
    return DataGovernanceService.list_asset_classifications(
        db=db,
        organization_id=current_user.organization_id,
        asset_id=asset_id,
    )


@router.post(
    "/classifications/{record_id}/approve",
    response_model=DataClassificationRecordResponse,
)
def approve_classification_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.DATA_GOV_APPROVE)),
):
    return DataGovernanceService.approve_classification(
        db=db,
        organization_id=current_user.organization_id,
        record_id=record_id,
        approver_id=current_user.id,
    )


@router.post(
    "/classifications/{record_id}/reject",
    response_model=DataClassificationRecordResponse,
)
def reject_classification_record(
    record_id: int,
    payload: DataClassificationRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.DATA_GOV_APPROVE)),
):
    return DataGovernanceService.reject_classification(
        db=db,
        organization_id=current_user.organization_id,
        record_id=record_id,
        reviewer_id=current_user.id,
        payload=payload,
    )


@router.put("/classifications/{record_id}")
def update_classification_record_not_allowed(
    record_id: int,
    current_user: User = Depends(get_current_user),
):
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="Classification records are immutable governance history and cannot be modified in-place",
    )


@router.delete("/classifications/{record_id}")
def delete_classification_record_not_allowed(
    record_id: int,
    current_user: User = Depends(get_current_user),
):
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="Classification records are immutable governance history and cannot be deleted",
    )


# ─── 6. DATA LINEAGE EDGES & PROVENANCE ───────────────────────────────────────

@router.post(
    "/lineage-edges",
    response_model=DataLineageEdgeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_lineage_edge(
    payload: DataLineageEdgeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.DATA_GOV_LINEAGE_MANAGE)),
):
    return DataGovernanceService.create_or_version_lineage_edge(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        payload=payload,
    )


@router.get("/lineage-edges", response_model=List[DataLineageEdgeResponse])
def list_lineage_edges(
    data_asset_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.DATA_GOV_READ)),
):
    return DataGovernanceService.list_lineage_edges(
        db=db,
        organization_id=current_user.organization_id,
        data_asset_id=data_asset_id,
        status_filter=status_filter,
    )


@router.post(
    "/lineage-edges/{edge_id}/approve",
    response_model=DataLineageEdgeResponse,
)
def approve_lineage_edge(
    edge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.DATA_GOV_APPROVE)),
):
    return DataGovernanceService.approve_lineage_edge(
        db=db,
        organization_id=current_user.organization_id,
        edge_id=edge_id,
        approver_id=current_user.id,
    )


@router.post(
    "/lineage-edges/{edge_id}/revoke",
    response_model=DataLineageEdgeResponse,
)
def revoke_lineage_edge(
    edge_id: int,
    payload: DataLineageEdgeRevokeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.DATA_GOV_LINEAGE_MANAGE)),
):
    return DataGovernanceService.revoke_lineage_edge(
        db=db,
        organization_id=current_user.organization_id,
        edge_id=edge_id,
        actor_id=current_user.id,
        payload=payload,
    )


@router.put("/lineage-edges/{edge_id}")
def update_lineage_edge_not_allowed(
    edge_id: int,
    current_user: User = Depends(get_current_user),
):
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="Lineage edges are versioned append-only records; submit a new version via POST /lineage-edges",
    )


@router.delete("/lineage-edges/{edge_id}")
def delete_lineage_edge_not_allowed(
    edge_id: int,
    current_user: User = Depends(get_current_user),
):
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="Lineage edges are immutable provenance records and cannot be physically deleted; use POST /revoke",
    )


# ─── 7. CROSS-DOMAIN BRIDGES (CLOUD, PROCESSING, CONTROL, EVIDENCE) ───────────

@router.post(
    "/assets/{asset_id}/cloud-links",
    response_model=DataAssetCloudLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
def link_asset_to_cloud(
    asset_id: int,
    payload: DataAssetCloudLinkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.DATA_GOV_MANAGE)),
):
    return DataGovernanceService.link_cloud_asset(
        db=db,
        organization_id=current_user.organization_id,
        asset_id=asset_id,
        actor_id=current_user.id,
        payload=payload,
    )


@router.post(
    "/assets/{asset_id}/processing-links",
    response_model=DataAssetProcessingLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
def link_asset_to_processing_activity(
    asset_id: int,
    payload: DataAssetProcessingLinkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.DATA_GOV_MANAGE)),
):
    return DataGovernanceService.link_processing_activity(
        db=db,
        organization_id=current_user.organization_id,
        asset_id=asset_id,
        actor_id=current_user.id,
        payload=payload,
    )


@router.post(
    "/assets/{asset_id}/control-links",
    response_model=DataAssetControlLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
def link_asset_to_control(
    asset_id: int,
    payload: DataAssetControlLinkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.DATA_GOV_MANAGE)),
):
    return DataGovernanceService.link_control(
        db=db,
        organization_id=current_user.organization_id,
        asset_id=asset_id,
        actor_id=current_user.id,
        payload=payload,
    )


@router.post(
    "/assets/{asset_id}/evidence-links",
    response_model=DataAssetEvidenceLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
def link_asset_to_evidence(
    asset_id: int,
    payload: DataAssetEvidenceLinkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.DATA_GOV_MANAGE)),
):
    return DataGovernanceService.link_evidence(
        db=db,
        organization_id=current_user.organization_id,
        asset_id=asset_id,
        actor_id=current_user.id,
        payload=payload,
    )


# ─── 8. DEPRECATION, RETIREMENT & RESTORATION ─────────────────────────────────

@router.post("/assets/{asset_id}/deprecate", response_model=GovernedDataAssetResponse)
def deprecate_data_asset(
    asset_id: int,
    payload: DataAssetDeprecateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.DATA_GOV_MANAGE)),
):
    return DataGovernanceService.deprecate_asset(
        db=db,
        organization_id=current_user.organization_id,
        asset_id=asset_id,
        actor_id=current_user.id,
        payload=payload,
    )


@router.post("/assets/{asset_id}/retire-request", response_model=GovernedDataAssetResponse)
def request_data_asset_retirement(
    asset_id: int,
    payload: DataAssetRetireRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.DATA_GOV_MANAGE)),
):
    return DataGovernanceService.request_retirement(
        db=db,
        organization_id=current_user.organization_id,
        asset_id=asset_id,
        actor_id=current_user.id,
        payload=payload,
    )


@router.post("/assets/{asset_id}/retire", response_model=GovernedDataAssetResponse)
def finalize_data_asset_retirement(
    asset_id: int,
    payload: DataAssetRetireRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.DATA_GOV_APPROVE)),
):
    return DataGovernanceService.finalize_retirement(
        db=db,
        organization_id=current_user.organization_id,
        asset_id=asset_id,
        approver_id=current_user.id,
        payload=payload,
    )


@router.post("/assets/{asset_id}/restore", response_model=GovernedDataAssetResponse)
def restore_retired_data_asset(
    asset_id: int,
    payload: DataAssetRestoreRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.DATA_GOV_APPROVE)),
):
    return DataGovernanceService.restore_retired_asset(
        db=db,
        organization_id=current_user.organization_id,
        asset_id=asset_id,
        approver_id=current_user.id,
        payload=payload,
    )
