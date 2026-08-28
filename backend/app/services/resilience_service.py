from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.control import OrganizationControl
from app.models.resilience import (
    BiaStatusEnum,
    BusinessImpactAnalysis,
    BusinessProcess,
    CriticalityTierEnum,
    DependencyTypeEnum,
    ProcessDependency,
)
from app.models.tprm import Vendor
from app.models.user import User
from app.schemas.resilience import (
    BusinessImpactAnalysisCreate,
    BusinessProcessCreate,
    BusinessProcessUpdate,
    ProcessDependencyCreate,
)
from app.services.audit_service import AuditService


# ─────────────────────────────────────────────────────────────────────────────
# PURE DETERMINISTIC CALCULATION ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def calculate_projected_outage_loss(
    duration_hours: float,
    hourly_downtime_cost: float,
    fixed_outage_cost: float = 0.0,
) -> Dict[str, float]:
    """
    Deterministic Financial Outage Loss Engine.
    Formula: Total Projected Loss(H) = fixed_outage_cost + (hourly_downtime_cost * H)
    """
    if duration_hours < 0.0 or hourly_downtime_cost < 0.0 or fixed_outage_cost < 0.0:
        raise ValueError("Outage duration and costs must be non-negative (>= 0.0).")

    variable_cost = round(duration_hours * hourly_downtime_cost, 2)
    fixed_cost = round(fixed_outage_cost, 2)
    total_loss = round(fixed_cost + variable_cost, 2)

    return {
        "duration_hours": round(duration_hours, 2),
        "fixed_outage_cost": fixed_cost,
        "hourly_downtime_cost": round(hourly_downtime_cost, 2),
        "variable_outage_cost": variable_cost,
        "total_projected_loss": total_loss,
    }


# ─────────────────────────────────────────────────────────────────────────────
# DOMAIN SERVICE CLASS
# ─────────────────────────────────────────────────────────────────────────────

class ResilienceService:
    """Authoritative enterprise Operational Resilience & BIA orchestration service."""

    @staticmethod
    def _get_actor_email(db: Session, actor_id: int) -> str:
        user = db.query(User).filter(User.id == actor_id).first()
        return user.email if user else "system@controlsphere.internal"

    # ── 1. Business Process Catalog Management ───────────────────────────────

    @classmethod
    def create_business_process(
        cls,
        db: Session,
        organization_id: int,
        data: BusinessProcessCreate,
        user_id: int,
    ) -> BusinessProcess:
        clean_name = data.name.strip()
        existing = (
            db.query(BusinessProcess)
            .filter(
                BusinessProcess.organization_id == organization_id,
                func.lower(BusinessProcess.name) == clean_name.lower(),
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Business process with name '{clean_name}' already exists in tenant.",
            )

        process = BusinessProcess(
            organization_id=organization_id,
            name=clean_name,
            description=data.description,
            owner_id=user_id,
            criticality_tier=data.criticality_tier,
        )
        db.add(process)
        db.commit()
        db.refresh(process)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="BUSINESS_PROCESS_CREATED",
            resource_type="BusinessProcess",
            resource_id=str(process.id),
            actor_email=cls._get_actor_email(db, user_id),
            actor_id=user_id,
            details={
                "name": process.name,
                "criticality_tier": process.criticality_tier.value,
            },
        )
        return process

    @classmethod
    def update_business_process(
        cls,
        db: Session,
        organization_id: int,
        process_id: int,
        data: BusinessProcessUpdate,
        user_id: int,
    ) -> BusinessProcess:
        process = (
            db.query(BusinessProcess)
            .filter(
                BusinessProcess.id == process_id,
                BusinessProcess.organization_id == organization_id,
            )
            .first()
        )
        if not process:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Business Process #{process_id} not found in tenant.",
            )

        if data.name is not None:
            clean_name = data.name.strip()
            if clean_name.lower() != process.name.lower():
                existing = (
                    db.query(BusinessProcess)
                    .filter(
                        BusinessProcess.organization_id == organization_id,
                        func.lower(BusinessProcess.name) == clean_name.lower(),
                    )
                    .first()
                )
                if existing:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Business process with name '{clean_name}' already exists in tenant.",
                    )
                process.name = clean_name

        if data.description is not None:
            process.description = data.description

        if data.criticality_tier is not None:
            process.criticality_tier = data.criticality_tier

        db.commit()
        db.refresh(process)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="BUSINESS_PROCESS_UPDATED",
            resource_type="BusinessProcess",
            resource_id=str(process.id),
            actor_email=cls._get_actor_email(db, user_id),
            actor_id=user_id,
            details={
                "name": process.name,
                "criticality_tier": process.criticality_tier.value,
            },
        )
        return process

    @classmethod
    def get_business_process(
        cls,
        db: Session,
        organization_id: int,
        process_id: int,
    ) -> BusinessProcess:
        process = (
            db.query(BusinessProcess)
            .filter(
                BusinessProcess.id == process_id,
                BusinessProcess.organization_id == organization_id,
            )
            .first()
        )
        if not process:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Business Process #{process_id} not found in tenant.",
            )
        return process

    @classmethod
    def list_business_processes(
        cls,
        db: Session,
        organization_id: int,
        criticality_tier: Optional[CriticalityTierEnum] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[BusinessProcess]:
        query = db.query(BusinessProcess).filter(
            BusinessProcess.organization_id == organization_id
        )
        if criticality_tier:
            query = query.filter(BusinessProcess.criticality_tier == criticality_tier)
        if search:
            query = query.filter(
                BusinessProcess.name.ilike(f"%{search}%")
                | BusinessProcess.description.ilike(f"%{search}%")
            )
        return (
            query.order_by(BusinessProcess.name.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    # ── 2. Business Impact Analysis (BIA) Lifecycle & Four-Eyes ──────────────

    @classmethod
    def draft_bia(
        cls,
        db: Session,
        organization_id: int,
        data: BusinessImpactAnalysisCreate,
        user_id: int,
    ) -> BusinessImpactAnalysis:
        process = (
            db.query(BusinessProcess)
            .filter(
                BusinessProcess.id == data.process_id,
                BusinessProcess.organization_id == organization_id,
            )
            .first()
        )
        if not process:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Business Process #{data.process_id} not found in tenant.",
            )

        if data.rto_hours > data.mtd_hours:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Recovery Time Objective ({data.rto_hours}h) cannot exceed Maximum Tolerable Downtime ({data.mtd_hours}h).",
            )

        max_ver = (
            db.query(func.max(BusinessImpactAnalysis.version))
            .filter(
                BusinessImpactAnalysis.organization_id == organization_id,
                BusinessImpactAnalysis.process_id == data.process_id,
            )
            .scalar()
        )
        next_version = (max_ver or 0) + 1

        bia = BusinessImpactAnalysis(
            organization_id=organization_id,
            process_id=data.process_id,
            status=BiaStatusEnum.DRAFT,
            version=next_version,
            rto_hours=data.rto_hours,
            rpo_hours=data.rpo_hours,
            mtd_hours=data.mtd_hours,
            hourly_downtime_cost=data.hourly_downtime_cost,
            fixed_outage_cost=data.fixed_outage_cost,
            requested_by_id=user_id,
            notes=data.notes,
        )
        db.add(bia)
        db.commit()
        db.refresh(bia)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="BIA_DRAFTED",
            resource_type="BusinessImpactAnalysis",
            resource_id=str(bia.id),
            actor_email=cls._get_actor_email(db, user_id),
            actor_id=user_id,
            details={
                "process_id": bia.process_id,
                "version": bia.version,
                "rto_hours": bia.rto_hours,
                "mtd_hours": bia.mtd_hours,
            },
        )
        return bia

    @classmethod
    def approve_bia(
        cls,
        db: Session,
        organization_id: int,
        bia_id: int,
        user_id: int,
        notes: Optional[str] = None,
    ) -> BusinessImpactAnalysis:
        bia = (
            db.query(BusinessImpactAnalysis)
            .filter(
                BusinessImpactAnalysis.id == bia_id,
                BusinessImpactAnalysis.organization_id == organization_id,
            )
            .first()
        )
        if not bia:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Business Impact Analysis #{bia_id} not found in tenant.",
            )

        if bia.status != BiaStatusEnum.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot approve BIA #{bia_id} in {bia.status.value} status. Only DRAFT records can be approved.",
            )

        # Four-Eyes Governance Rule
        if bia.requested_by_id == user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Four-eyes governance violation: The requester cannot approve their own BIA.",
            )

        # Atomically supersede previous active BIA versions for this process
        active_bias = (
            db.query(BusinessImpactAnalysis)
            .filter(
                BusinessImpactAnalysis.organization_id == organization_id,
                BusinessImpactAnalysis.process_id == bia.process_id,
                BusinessImpactAnalysis.status == BiaStatusEnum.ACTIVE,
            )
            .all()
        )
        for ab in active_bias:
            ab.status = BiaStatusEnum.SUPERSEDED

        bia.status = BiaStatusEnum.ACTIVE
        bia.approved_by_id = user_id
        bia.approved_at = datetime.now(timezone.utc)
        if notes:
            bia.notes = f"{bia.notes}\nApproval Notes: {notes}" if bia.notes else notes

        db.commit()
        db.refresh(bia)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="BIA_APPROVED",
            resource_type="BusinessImpactAnalysis",
            resource_id=str(bia.id),
            actor_email=cls._get_actor_email(db, user_id),
            actor_id=user_id,
            details={
                "process_id": bia.process_id,
                "version": bia.version,
                "requested_by_id": bia.requested_by_id,
                "approved_by_id": user_id,
            },
        )
        return bia

    @classmethod
    def archive_draft_bia(
        cls,
        db: Session,
        organization_id: int,
        bia_id: int,
        user_id: int,
    ) -> BusinessImpactAnalysis:
        bia = (
            db.query(BusinessImpactAnalysis)
            .filter(
                BusinessImpactAnalysis.id == bia_id,
                BusinessImpactAnalysis.organization_id == organization_id,
            )
            .first()
        )
        if not bia:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Business Impact Analysis #{bia_id} not found in tenant.",
            )

        if bia.status != BiaStatusEnum.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only DRAFT BIA versions can be archived. Active and superseded baselines are immutable.",
            )

        bia.status = BiaStatusEnum.ARCHIVED
        db.commit()
        db.refresh(bia)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="BIA_ARCHIVED",
            resource_type="BusinessImpactAnalysis",
            resource_id=str(bia.id),
            actor_email=cls._get_actor_email(db, user_id),
            actor_id=user_id,
            details={
                "process_id": bia.process_id,
                "version": bia.version,
            },
        )
        return bia

    @classmethod
    def get_bia(
        cls,
        db: Session,
        organization_id: int,
        bia_id: int,
    ) -> BusinessImpactAnalysis:
        bia = (
            db.query(BusinessImpactAnalysis)
            .filter(
                BusinessImpactAnalysis.id == bia_id,
                BusinessImpactAnalysis.organization_id == organization_id,
            )
            .first()
        )
        if not bia:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Business Impact Analysis #{bia_id} not found in tenant.",
            )
        return bia

    @classmethod
    def list_process_bias(
        cls,
        db: Session,
        organization_id: int,
        process_id: int,
    ) -> List[BusinessImpactAnalysis]:
        process = (
            db.query(BusinessProcess)
            .filter(
                BusinessProcess.id == process_id,
                BusinessProcess.organization_id == organization_id,
            )
            .first()
        )
        if not process:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Business Process #{process_id} not found in tenant.",
            )

        return (
            db.query(BusinessImpactAnalysis)
            .filter(
                BusinessImpactAnalysis.organization_id == organization_id,
                BusinessImpactAnalysis.process_id == process_id,
            )
            .order_by(BusinessImpactAnalysis.version.desc())
            .all()
        )

    # ── 3. Cross-Module Process Dependencies (TPRM & Controls) ───────────────

    @classmethod
    def add_process_dependency(
        cls,
        db: Session,
        organization_id: int,
        data: ProcessDependencyCreate,
        user_id: int,
    ) -> ProcessDependency:
        process = (
            db.query(BusinessProcess)
            .filter(
                BusinessProcess.id == data.process_id,
                BusinessProcess.organization_id == organization_id,
            )
            .first()
        )
        if not process:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Business Process #{data.process_id} not found in tenant.",
            )

        # Cross-Module Target Entity & Tenant Isolation Validation
        if data.dependency_type == DependencyTypeEnum.VENDOR:
            vendor = (
                db.query(Vendor)
                .filter(
                    Vendor.id == data.dependency_id,
                    Vendor.organization_id == organization_id,
                )
                .first()
            )
            if not vendor:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Vendor #{data.dependency_id} not found in tenant organization.",
                )
        elif data.dependency_type == DependencyTypeEnum.CONTROL:
            control = (
                db.query(OrganizationControl)
                .filter(
                    OrganizationControl.id == data.dependency_id,
                    OrganizationControl.organization_id == organization_id,
                )
                .first()
            )
            if not control:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Control #{data.dependency_id} not found in tenant organization.",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported dependency type: {data.dependency_type}",
            )

        # Check duplicate dependency
        existing = (
            db.query(ProcessDependency)
            .filter(
                ProcessDependency.organization_id == organization_id,
                ProcessDependency.process_id == data.process_id,
                ProcessDependency.dependency_type == data.dependency_type,
                ProcessDependency.dependency_id == data.dependency_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This dependency is already linked to the target business process.",
            )

        dep = ProcessDependency(
            organization_id=organization_id,
            process_id=data.process_id,
            dependency_type=data.dependency_type,
            dependency_id=data.dependency_id,
            notes=data.notes,
        )
        db.add(dep)
        db.commit()
        db.refresh(dep)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="PROCESS_DEPENDENCY_ADDED",
            resource_type="ProcessDependency",
            resource_id=str(dep.id),
            actor_email=cls._get_actor_email(db, user_id),
            actor_id=user_id,
            details={
                "process_id": dep.process_id,
                "dependency_type": dep.dependency_type.value,
                "dependency_id": dep.dependency_id,
            },
        )
        return dep

    @classmethod
    def remove_process_dependency(
        cls,
        db: Session,
        organization_id: int,
        dependency_id: int,
        user_id: int,
    ) -> None:
        dep = (
            db.query(ProcessDependency)
            .filter(
                ProcessDependency.id == dependency_id,
                ProcessDependency.organization_id == organization_id,
            )
            .first()
        )
        if not dep:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Process dependency #{dependency_id} not found in tenant.",
            )

        db.delete(dep)
        db.commit()

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="PROCESS_DEPENDENCY_REMOVED",
            resource_type="ProcessDependency",
            resource_id=str(dependency_id),
            actor_email=cls._get_actor_email(db, user_id),
            actor_id=user_id,
        )
