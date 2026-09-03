import json
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_permission
from app.core.permissions import Permission
from app.models.user import User
from app.schemas.integration import (
    IntegrationProviderResponse,
    IntegrationConnectionCreate,
    IntegrationConnectionResponse,
    IntegrationCredentialCreate,
    IntegrationCredentialResponse,
    EvidenceCollectionJobCreate,
    EvidenceCollectionJobResponse,
    EvidenceCollectionRunResponse,
)
from app.services.integration_service import (
    IntegrationService,
    IntegrationSecurityService,
    SSRFValidationError,
    CredentialDecryptionError,
)

router = APIRouter()


# ── Providers ───────────────────────────────────────────────────────────────

@router.get("/providers", response_model=List[IntegrationProviderResponse])
def list_providers(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.INTEGRATION_READ)),
) -> Any:
    """List system integration providers with supported scopes and allowed domains."""
    providers = IntegrationService.list_providers(db)
    results = []
    for p in providers:
        results.append({
            "id": p.id,
            "provider_type": p.provider_type,
            "name": p.name,
            "description": p.description,
            "auth_type": p.auth_type,
            "supported_scopes": json.loads(p.supported_scopes),
            "allowed_domains": json.loads(p.allowed_domains),
            "is_enabled": p.is_enabled,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
        })
    return results


# ── Connections ─────────────────────────────────────────────────────────────

@router.get("/connections", response_model=List[IntegrationConnectionResponse])
def list_connections(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.INTEGRATION_READ)),
) -> Any:
    """List tenant-scoped integration connections (credentials never returned)."""
    conns = IntegrationService.list_connections(
        db=db,
        organization_id=current_user.organization_id,
        skip=skip,
        limit=limit,
    )
    results = []
    for c in conns:
        results.append({
            "id": c.id,
            "organization_id": c.organization_id,
            "provider_id": c.provider_id,
            "connection_code": c.connection_code,
            "name": c.name,
            "status": c.status,
            "base_url": c.base_url,
            "granted_scopes": json.loads(c.granted_scopes),
            "last_health_check_at": c.last_health_check_at,
            "last_health_status": c.last_health_status,
            "last_error_message": c.last_error_message,
            "is_credential_configured": bool(c.credential),
            "created_by_id": c.created_by_id,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
        })
    return results


@router.get("/connections/{id}", response_model=IntegrationConnectionResponse)
def get_connection(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.INTEGRATION_READ)),
) -> Any:
    """Get single integration connection metadata (credentials never exposed)."""
    c = IntegrationService.get_connection(db, current_user.organization_id, id)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration connection not found.")
    return {
        "id": c.id,
        "organization_id": c.organization_id,
        "provider_id": c.provider_id,
        "connection_code": c.connection_code,
        "name": c.name,
        "status": c.status,
        "base_url": c.base_url,
        "granted_scopes": json.loads(c.granted_scopes),
        "last_health_check_at": c.last_health_check_at,
        "last_health_status": c.last_health_status,
        "last_error_message": c.last_error_message,
        "is_credential_configured": bool(c.credential),
        "created_by_id": c.created_by_id,
        "created_at": c.created_at,
        "updated_at": c.updated_at,
    }


@router.post("/connections", response_model=IntegrationConnectionResponse, status_code=status.HTTP_201_CREATED)
def create_connection(
    conn_in: IntegrationConnectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.INTEGRATION_MANAGE)),
) -> Any:
    """Create a new tenant integration connection."""
    try:
        c = IntegrationService.create_connection(
            db=db,
            organization_id=current_user.organization_id,
            conn_in=conn_in,
            current_user_id=current_user.id,
        )
        return {
            "id": c.id,
            "organization_id": c.organization_id,
            "provider_id": c.provider_id,
            "connection_code": c.connection_code,
            "name": c.name,
            "status": c.status,
            "base_url": c.base_url,
            "granted_scopes": json.loads(c.granted_scopes),
            "last_health_check_at": c.last_health_check_at,
            "last_health_status": c.last_health_status,
            "last_error_message": c.last_error_message,
            "is_credential_configured": False,
            "created_by_id": c.created_by_id,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
        }
    except SSRFValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT if "already exists" in str(e) else status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/connections/{id}/credentials", response_model=IntegrationCredentialResponse)
def set_credentials(
    id: int,
    cred_in: IntegrationCredentialCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.INTEGRATION_MANAGE)),
) -> Any:
    """Set or rotate Fernet-encrypted credentials for an integration connection (never returned in responses)."""
    try:
        cred = IntegrationService.set_connection_credentials(
            db=db,
            organization_id=current_user.organization_id,
            connection_id=id,
            cred_in=cred_in,
            current_user_id=current_user.id,
        )
        return {
            "key_id": cred.key_id,
            "auth_type": cred.auth_type,
            "version": cred.version,
            "is_configured": True,
            "rotated_at": cred.rotated_at,
            "created_at": cred.created_at,
        }
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/connections/{id}/test")
def test_connection(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.INTEGRATION_EXECUTE)),
) -> Any:
    """SSRF-safe connectivity and authentication diagnostic test."""
    try:
        return IntegrationService.test_connection(
            db=db,
            organization_id=current_user.organization_id,
            connection_id=id,
            current_user_id=current_user.id,
        )
    except SSRFValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Jobs ────────────────────────────────────────────────────────────────────

@router.get("/jobs", response_model=List[EvidenceCollectionJobResponse])
def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.INTEGRATION_READ)),
) -> Any:
    """List automated evidence collection jobs."""
    jobs = IntegrationService.list_jobs(
        db=db,
        organization_id=current_user.organization_id,
        skip=skip,
        limit=limit,
    )
    results = []
    for j in jobs:
        results.append({
            "id": j.id,
            "organization_id": j.organization_id,
            "connection_id": j.connection_id,
            "organization_control_id": j.organization_control_id,
            "evidence_requirement_id": j.evidence_requirement_id,
            "job_code": j.job_code,
            "title": j.title,
            "collector_type": j.collector_type,
            "collection_parameters": json.loads(j.collection_parameters) if j.collection_parameters else None,
            "frequency_hours": j.frequency_hours,
            "is_enabled": j.is_enabled,
            "max_payload_bytes": j.max_payload_bytes,
            "last_run_at": j.last_run_at,
            "last_run_status": j.last_run_status,
            "created_by_id": j.created_by_id,
            "created_at": j.created_at,
            "updated_at": j.updated_at,
        })
    return results


@router.post("/jobs", response_model=EvidenceCollectionJobResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    job_in: EvidenceCollectionJobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.INTEGRATION_MANAGE)),
) -> Any:
    """Create a new automated evidence collection job."""
    try:
        j = IntegrationService.create_job(
            db=db,
            organization_id=current_user.organization_id,
            job_in=job_in,
            current_user_id=current_user.id,
        )
        return {
            "id": j.id,
            "organization_id": j.organization_id,
            "connection_id": j.connection_id,
            "organization_control_id": j.organization_control_id,
            "evidence_requirement_id": j.evidence_requirement_id,
            "job_code": j.job_code,
            "title": j.title,
            "collector_type": j.collector_type,
            "collection_parameters": json.loads(j.collection_parameters) if j.collection_parameters else None,
            "frequency_hours": j.frequency_hours,
            "is_enabled": j.is_enabled,
            "max_payload_bytes": j.max_payload_bytes,
            "last_run_at": j.last_run_at,
            "last_run_status": j.last_run_status,
            "created_by_id": j.created_by_id,
            "created_at": j.created_at,
            "updated_at": j.updated_at,
        }
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_409_CONFLICT if "already exists" in str(e) else status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/jobs/{id}/run", response_model=EvidenceCollectionRunResponse)
def trigger_job_run(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.INTEGRATION_EXECUTE)),
) -> Any:
    """Execute an automated technical evidence collection run."""
    try:
        r = IntegrationService.execute_collection_run(
            db=db,
            organization_id=current_user.organization_id,
            job_id=id,
            current_user_id=current_user.id,
        )
        return {
            "id": r.id,
            "organization_id": r.organization_id,
            "job_id": r.job_id,
            "connection_id": r.connection_id,
            "evidence_item_id": r.evidence_item_id,
            "run_code": r.run_code,
            "status": r.status,
            "started_at": r.started_at,
            "completed_at": r.completed_at,
            "source_system": r.source_system,
            "source_identifier": r.source_identifier,
            "source_version": r.source_version,
            "observed_at": r.observed_at,
            "records_collected_count": r.records_collected_count,
            "payload_sha256": r.payload_sha256,
            "validation_status": r.validation_status,
            "error_code": r.error_code,
            "error_message": r.error_message,
            "provenance_manifest": json.loads(r.provenance_manifest) if r.provenance_manifest else None,
            "triggered_by_id": r.triggered_by_id,
            "created_at": r.created_at,
        }
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Runs ────────────────────────────────────────────────────────────────────

@router.get("/runs", response_model=List[EvidenceCollectionRunResponse])
def list_runs(
    job_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.INTEGRATION_READ)),
) -> Any:
    """List automated evidence collection runs and provenance manifests."""
    runs = IntegrationService.list_runs(
        db=db,
        organization_id=current_user.organization_id,
        job_id=job_id,
        skip=skip,
        limit=limit,
    )
    results = []
    for r in runs:
        results.append({
            "id": r.id,
            "organization_id": r.organization_id,
            "job_id": r.job_id,
            "connection_id": r.connection_id,
            "evidence_item_id": r.evidence_item_id,
            "run_code": r.run_code,
            "status": r.status,
            "started_at": r.started_at,
            "completed_at": r.completed_at,
            "source_system": r.source_system,
            "source_identifier": r.source_identifier,
            "source_version": r.source_version,
            "observed_at": r.observed_at,
            "records_collected_count": r.records_collected_count,
            "payload_sha256": r.payload_sha256,
            "validation_status": r.validation_status,
            "error_code": r.error_code,
            "error_message": r.error_message,
            "provenance_manifest": json.loads(r.provenance_manifest) if r.provenance_manifest else None,
            "triggered_by_id": r.triggered_by_id,
            "created_at": r.created_at,
        })
    return results
