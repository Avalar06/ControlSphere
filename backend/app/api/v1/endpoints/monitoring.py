from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_permission
from app.core.permissions import Permission
from app.models.monitoring import (
    ControlHealthStatusEnum,
    DriftAlertSeverityEnum,
    DriftAlertStatusEnum,
    DriftAlertTypeEnum,
    EvaluationTriggerEnum,
)
from app.models.user import User
from app.schemas.monitoring import (
    ComplianceDriftAlertDismiss,
    ComplianceDriftAlertResolve,
    ComplianceDriftAlertResponse,
    ControlHealthSnapshotResponse,
    ControlHealthSummaryResponse,
    EvaluationRunResponse,
    MonitoringConfigResponse,
    MonitoringConfigUpdate,
    MonitoringOverviewResponse,
)
from app.services.audit_service import AuditService
from app.services.monitoring_service import MonitoringService

router = APIRouter()


@router.get("/overview", response_model=MonitoringOverviewResponse)
def get_monitoring_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MONITORING_READ)),
) -> Any:
    """Get aggregate continuous monitoring metrics, health scores, and drift counts."""
    return MonitoringService.get_overview(db=db, organization_id=current_user.organization_id)


@router.get("/controls", response_model=List[ControlHealthSummaryResponse])
def list_control_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MONITORING_READ)),
    status: Optional[ControlHealthStatusEnum] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> Any:
    """List controls with their current deterministic health scores and drift telemetry."""
    return MonitoringService.list_control_health(
        db=db,
        organization_id=current_user.organization_id,
        status=status,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.get("/controls/{control_id}/history", response_model=List[ControlHealthSnapshotResponse])
def get_control_health_history(
    control_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MONITORING_READ)),
    limit: int = Query(30, ge=1, le=100),
) -> Any:
    """Get chronological health snapshot history for a specific control."""
    try:
        return MonitoringService.get_control_history(
            db=db,
            organization_id=current_user.organization_id,
            control_id=control_id,
            limit=limit,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/evaluate", response_model=EvaluationRunResponse)
def trigger_evaluation_run(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MONITORING_EXECUTE)),
) -> Any:
    """Execute a comprehensive, deterministic health evaluation run across all organization controls."""
    result = MonitoringService.evaluate_organization(
        db=db,
        organization_id=current_user.organization_id,
        trigger=EvaluationTriggerEnum.MANUAL,
    )

    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="monitoring.evaluate",
        resource_type="organization",
        actor_email=current_user.email,
        actor_id=current_user.id,
        resource_id=str(current_user.organization_id),
        details={
            "evaluated_controls": result.evaluated_controls_count,
            "alerts_generated": result.alerts_generated_count,
            "average_health_score": result.average_health_score,
        },
    )
    return result


@router.get("/alerts", response_model=List[ComplianceDriftAlertResponse])
def list_compliance_drift_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MONITORING_READ)),
    status: Optional[DriftAlertStatusEnum] = Query(None),
    severity: Optional[DriftAlertSeverityEnum] = Query(None),
    alert_type: Optional[DriftAlertTypeEnum] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> Any:
    """List compliance drift alerts with optional status and severity filtering."""
    return MonitoringService.list_alerts(
        db=db,
        organization_id=current_user.organization_id,
        status=status,
        severity=severity,
        alert_type=alert_type,
        skip=skip,
        limit=limit,
    )


@router.post("/alerts/{alert_id}/acknowledge", response_model=ComplianceDriftAlertResponse)
def acknowledge_drift_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MONITORING_ALERT_ACTION)),
) -> Any:
    """Acknowledge an active compliance drift alert."""
    try:
        alert = MonitoringService.acknowledge_alert(
            db=db,
            organization_id=current_user.organization_id,
            alert_id=alert_id,
            user_id=current_user.id,
        )
        AuditService.log(
            db=db,
            organization_id=current_user.organization_id,
            action="monitoring.alert_acknowledge",
            resource_type="compliance_drift_alert",
            actor_email=current_user.email,
            actor_id=current_user.id,
            resource_id=str(alert.id),
            details={"alert_type": alert.alert_type.value, "severity": alert.severity.value},
        )
        return alert
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/alerts/{alert_id}/resolve", response_model=ComplianceDriftAlertResponse)
def resolve_drift_alert(
    alert_id: int,
    obj_in: ComplianceDriftAlertResolve,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MONITORING_ALERT_ACTION)),
) -> Any:
    """Formally resolve a compliance drift alert with mandatory remediation notes."""
    try:
        alert = MonitoringService.resolve_alert(
            db=db,
            organization_id=current_user.organization_id,
            alert_id=alert_id,
            user_id=current_user.id,
            obj_in=obj_in,
        )
        AuditService.log(
            db=db,
            organization_id=current_user.organization_id,
            action="monitoring.alert_resolve",
            resource_type="compliance_drift_alert",
            actor_email=current_user.email,
            actor_id=current_user.id,
            resource_id=str(alert.id),
            details={
                "alert_type": alert.alert_type.value,
                "notes": obj_in.resolution_notes,
            },
        )
        return alert
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/alerts/{alert_id}/dismiss", response_model=ComplianceDriftAlertResponse)
def dismiss_drift_alert(
    alert_id: int,
    obj_in: ComplianceDriftAlertDismiss,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MONITORING_ALERT_ACTION)),
) -> Any:
    """Dismiss an active compliance drift alert with mandatory justification."""
    try:
        alert = MonitoringService.dismiss_alert(
            db=db,
            organization_id=current_user.organization_id,
            alert_id=alert_id,
            user_id=current_user.id,
            obj_in=obj_in,
        )
        AuditService.log(
            db=db,
            organization_id=current_user.organization_id,
            action="monitoring.alert_dismiss",
            resource_type="compliance_drift_alert",
            actor_email=current_user.email,
            actor_id=current_user.id,
            resource_id=str(alert.id),
            details={
                "alert_type": alert.alert_type.value,
                "justification": obj_in.justification,
            },
        )
        return alert
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/config", response_model=MonitoringConfigResponse)
def get_monitoring_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MONITORING_READ)),
) -> Any:
    """Get organization continuous monitoring configuration and thresholds."""
    return MonitoringService.get_or_create_config(db=db, organization_id=current_user.organization_id)


@router.patch("/config", response_model=MonitoringConfigResponse)
def update_monitoring_config(
    obj_in: MonitoringConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MONITORING_MANAGE)),
) -> Any:
    """Update continuous monitoring evaluation schedule and threshold parameters."""
    cfg = MonitoringService.update_config(
        db=db,
        organization_id=current_user.organization_id,
        obj_in=obj_in,
    )
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="monitoring.config_update",
        resource_type="monitoring_schedule",
        actor_email=current_user.email,
        actor_id=current_user.id,
        resource_id=str(cfg.id),
        details=obj_in.model_dump(exclude_unset=True),
    )
    return cfg
