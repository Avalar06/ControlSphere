from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.cloudsec import CloudAsset, CloudLifecycleStateEnum, CloudPostureStatusEnum
from app.models.control import ImplementationStatusEnum, OrganizationControl
from app.models.evidence import EvidenceItem, EvidenceStatusEnum
from app.models.finding import (
    Finding,
    FindingEvidence,
    FindingSeverityEnum,
    FindingStatusEnum,
    FindingTypeEnum,
)
from app.models.incident import SecurityIncident
from app.models.privacy import DataAsset
from app.models.remediation import (
    RemediationPlan,
    RemediationRootCauseClassificationEnum,
    RemediationSeverityEnum,
    RemediationSourceTypeEnum,
    RemediationStatusEnum,
)
from app.models.resilience import (
    BiaStatusEnum,
    BusinessImpactAnalysis,
    BusinessProcess,
    ContinuityPlan,
    ContinuityPlanStatusEnum,
    ContinuityRecoveryStep,
    CriticalityTierEnum,
    DependencyTypeEnum,
    ExerciseOutcomeEnum,
    ExerciseStatusEnum,
    ExerciseTypeEnum,
    ProcessDependency,
    ResilienceEvidenceLink,
    ResilienceExercise,
)
from app.models.risk import (
    Risk,
    RiskCategoryEnum,
    RiskFindingLink,
    RiskSourceEnum,
    RiskStatusEnum,
)
from app.models.tprm import Vendor, VendorRiskBandEnum, VendorStatusEnum
from app.models.user import User
from app.schemas.resilience import (
    BusinessImpactAnalysisCreate,
    BusinessProcessCreate,
    BusinessProcessUpdate,
    ContinuityPlanCreate,
    ContinuityPlanRejectRequest,
    ContinuityPlanUpdate,
    ContinuityRecoveryStepCreate,
    ContinuityRecoveryStepUpdate,
    DependencyHealthItem,
    ExerciseEscalationRequest,
    OutageSimulationAffectedProcess,
    OutageSimulationRequest,
    OutageSimulationResponse,
    ProcessDependencyCreate,
    ProcessDependencyHealthResponse,
    ProcessImpactSummaryResponse,
    ResilienceDashboardResponse,
    ResilienceEvidenceLinkCreate,
    ResilienceExerciseCancelRequest,
    ResilienceExerciseCompleteRequest,
    ResilienceExerciseCreate,
    ResilienceExerciseReviewRequest,
    ResilienceExerciseStartRequest,
)
from app.services.audit_service import AuditService
from app.services.executive_service import compute_canonical_sha256


# ─────────────────────────────────────────────────────────────────────────────
# PURE DETERMINISTIC CALCULATION & CLASSIFICATION FUNCTIONS
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


def classify_exercise_outcome(
    *,
    rto_breached: bool,
    rpo_breached: bool,
    mtd_breached: bool,
    control_deficiency_observed: bool,
    minor_exceptions_noted: bool = False,
) -> ExerciseOutcomeEnum:
    """
    Deterministic server-side classification of resilience exercise outcome.
    Precedence:
      1. FAIL_MTD_BREACH
      2. FAIL_RTO_BREACH
      3. FAIL_RPO_BREACH
      4. FAIL_CONTROL_DEFICIENCY
      5. PASS_WITH_MINOR_EXCEPTIONS
      6. PASS
    """
    if mtd_breached:
        return ExerciseOutcomeEnum.FAIL_MTD_BREACH
    if rto_breached:
        return ExerciseOutcomeEnum.FAIL_RTO_BREACH
    if rpo_breached:
        return ExerciseOutcomeEnum.FAIL_RPO_BREACH
    if control_deficiency_observed:
        return ExerciseOutcomeEnum.FAIL_CONTROL_DEFICIENCY
    if minor_exceptions_noted:
        return ExerciseOutcomeEnum.PASS_WITH_MINOR_EXCEPTIONS
    return ExerciseOutcomeEnum.PASS


def compute_plan_hash_sha256(
    plan: ContinuityPlan,
    steps: List[ContinuityRecoveryStep],
) -> str:
    """Computes canonical SHA-256 integrity hash over ContinuityPlan and its ordered steps."""
    payload = {
        "organization_id": plan.organization_id,
        "process_id": plan.process_id,
        "bia_id": plan.bia_id,
        "plan_code": plan.plan_code,
        "version_label": plan.version_label,
        "strategy_type": (
            plan.strategy_type.value
            if hasattr(plan.strategy_type, "value")
            else str(plan.strategy_type)
        ),
        "activation_triggers": plan.activation_triggers,
        "estimated_recovery_hours": round(float(plan.estimated_recovery_hours), 4),
        "estimated_rpo_hours": round(float(plan.estimated_rpo_hours), 4),
        "steps": [
            {
                "step_order": s.step_order,
                "title": s.title,
                "estimated_duration_minutes": int(s.estimated_duration_minutes),
                "is_automated": bool(s.is_automated),
            }
            for s in sorted(steps, key=lambda x: x.step_order)
        ],
    }
    return compute_canonical_sha256(payload)


def compute_exercise_result_hash_sha256(
    ex: ResilienceExercise,
    evidence_links: List[ResilienceEvidenceLink],
) -> str:
    """Computes canonical SHA-256 integrity hash over ResilienceExercise empirical results and evidence."""
    payload = {
        "organization_id": ex.organization_id,
        "process_id": ex.process_id,
        "continuity_plan_id": ex.continuity_plan_id,
        "bia_id": ex.bia_id,
        "exercise_code": ex.exercise_code,
        "exercise_type": (
            ex.exercise_type.value
            if hasattr(ex.exercise_type, "value")
            else str(ex.exercise_type)
        ),
        "status": ex.status.value if hasattr(ex.status, "value") else str(ex.status),
        "target_rto_hours_snapshot": round(float(ex.target_rto_hours_snapshot), 4),
        "target_rpo_hours_snapshot": round(float(ex.target_rpo_hours_snapshot), 4),
        "target_mtd_hours_snapshot": round(float(ex.target_mtd_hours_snapshot), 4),
        "actual_rto_hours": (
            round(float(ex.actual_rto_hours), 4)
            if ex.actual_rto_hours is not None
            else None
        ),
        "actual_rpo_hours": (
            round(float(ex.actual_rpo_hours), 4)
            if ex.actual_rpo_hours is not None
            else None
        ),
        "rto_breached": bool(ex.rto_breached),
        "rpo_breached": bool(ex.rpo_breached),
        "mtd_breached": bool(ex.mtd_breached),
        "outcome": (
            ex.outcome.value
            if ex.outcome is not None and hasattr(ex.outcome, "value")
            else (str(ex.outcome) if ex.outcome is not None else None)
        ),
        "executed_by_user_id": ex.executed_by_user_id,
        "reviewed_by_user_id": ex.reviewed_by_user_id,
        "evidence_hashes": sorted(
            link.evidence_sha256_snapshot for link in evidence_links
        ),
    }
    return compute_canonical_sha256(payload)


# ─────────────────────────────────────────────────────────────────────────────
# DOMAIN SERVICE CLASS
# ─────────────────────────────────────────────────────────────────────────────

class ResilienceService:
    """Authoritative enterprise Operational Resilience, Continuity Planning & DR Exercise service."""

    @staticmethod
    def _get_actor_email(db: Session, actor_id: int) -> str:
        user = db.query(User).filter(User.id == actor_id).first()
        return user.email if user else "system@controlsphere.internal"

    @staticmethod
    def _attach_active_bia(db: Session, process: BusinessProcess) -> BusinessProcess:
        active_bia = (
            db.query(BusinessImpactAnalysis)
            .filter(
                BusinessImpactAnalysis.organization_id == process.organization_id,
                BusinessImpactAnalysis.process_id == process.id,
                BusinessImpactAnalysis.status == BiaStatusEnum.ACTIVE,
            )
            .first()
        )
        setattr(process, "active_bia", active_bia)
        return process

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
        return cls._attach_active_bia(db, process)

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
        return cls._attach_active_bia(db, process)

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
        return cls._attach_active_bia(db, process)

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
        processes = (
            query.order_by(BusinessProcess.name.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        for p in processes:
            cls._attach_active_bia(db, p)
        return processes

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

    # ── 3. Extended Cross-Module Process Dependencies (Batch 5) ──────────────

    @classmethod
    def _detect_process_cycle(
        cls,
        db: Session,
        organization_id: int,
        source_process_id: int,
        target_process_id: int,
    ) -> bool:
        """DFS cycle check: returns True if source_process_id is reachable from target_process_id."""
        if source_process_id == target_process_id:
            return True
        visited: Set[int] = set()
        stack: List[int] = [target_process_id]
        while stack:
            curr = stack.pop()
            if curr == source_process_id:
                return True
            if curr in visited:
                continue
            visited.add(curr)
            upstream_edges = (
                db.query(ProcessDependency.depends_on_process_id)
                .filter(
                    ProcessDependency.organization_id == organization_id,
                    ProcessDependency.process_id == curr,
                    ProcessDependency.dependency_type == DependencyTypeEnum.PROCESS,
                    ProcessDependency.depends_on_process_id.isnot(None),
                )
                .all()
            )
            for (next_proc_id,) in upstream_edges:
                if next_proc_id and next_proc_id not in visited:
                    stack.append(next_proc_id)
        return False

    @classmethod
    def add_process_dependency(
        cls,
        db: Session,
        organization_id: int,
        data: ProcessDependencyCreate,
        user_id: int,
        process_id_override: Optional[int] = None,
    ) -> ProcessDependency:
        target_process_id = process_id_override if process_id_override is not None else data.process_id
        if not target_process_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Target business process_id is required.",
            )

        process = (
            db.query(BusinessProcess)
            .filter(
                BusinessProcess.id == target_process_id,
                BusinessProcess.organization_id == organization_id,
            )
            .first()
        )
        if not process:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Business Process #{target_process_id} not found in tenant.",
            )

        target_id = data.dependency_id
        if target_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Target dependency ID is required.",
            )

        # Cross-Module Target Entity & Tenant Isolation Validation
        if data.dependency_type == DependencyTypeEnum.VENDOR:
            vendor = (
                db.query(Vendor)
                .filter(
                    Vendor.id == target_id,
                    Vendor.organization_id == organization_id,
                )
                .first()
            )
            if not vendor:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Vendor #{target_id} not found in tenant organization.",
                )
        elif data.dependency_type == DependencyTypeEnum.CONTROL:
            control = (
                db.query(OrganizationControl)
                .filter(
                    OrganizationControl.id == target_id,
                    OrganizationControl.organization_id == organization_id,
                )
                .first()
            )
            if not control:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Control #{target_id} not found in tenant organization.",
                )
        elif data.dependency_type == DependencyTypeEnum.CLOUD_ASSET:
            cloud_asset = (
                db.query(CloudAsset)
                .filter(
                    CloudAsset.id == target_id,
                    CloudAsset.organization_id == organization_id,
                )
                .first()
            )
            if not cloud_asset:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"CloudAsset #{target_id} not found in tenant organization.",
                )
        elif data.dependency_type == DependencyTypeEnum.DATA_ASSET:
            data_asset = (
                db.query(DataAsset)
                .filter(
                    DataAsset.id == target_id,
                    DataAsset.organization_id == organization_id,
                )
                .first()
            )
            if not data_asset:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"DataAsset #{target_id} not found in tenant organization.",
                )
        elif data.dependency_type == DependencyTypeEnum.PROCESS:
            if target_id == target_process_id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="A business process cannot depend on itself.",
                )
            upstream_proc = (
                db.query(BusinessProcess)
                .filter(
                    BusinessProcess.id == target_id,
                    BusinessProcess.organization_id == organization_id,
                )
                .first()
            )
            if not upstream_proc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Upstream Business Process #{target_id} not found in tenant organization.",
                )
            if cls._detect_process_cycle(db, organization_id, target_process_id, target_id):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Circular process dependency detected in resilience dependency graph.",
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
                ProcessDependency.process_id == target_process_id,
                ProcessDependency.dependency_type == data.dependency_type,
                ProcessDependency.dependency_id == target_id,
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
            process_id=target_process_id,
            dependency_type=data.dependency_type,
            dependency_id=target_id,
            vendor_id=target_id if data.dependency_type == DependencyTypeEnum.VENDOR else None,
            organization_control_id=target_id if data.dependency_type == DependencyTypeEnum.CONTROL else None,
            cloud_asset_id=target_id if data.dependency_type == DependencyTypeEnum.CLOUD_ASSET else None,
            data_asset_id=target_id if data.dependency_type == DependencyTypeEnum.DATA_ASSET else None,
            depends_on_process_id=target_id if data.dependency_type == DependencyTypeEnum.PROCESS else None,
            is_single_point_of_failure=data.is_single_point_of_failure,
            failure_propagation_weight=1.0 if data.is_single_point_of_failure else data.failure_propagation_weight,
            recovery_priority_order=data.recovery_priority_order,
            notes=data.notes,
            criticality_notes=data.criticality_notes,
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
                "is_single_point_of_failure": dep.is_single_point_of_failure,
                "failure_propagation_weight": dep.failure_propagation_weight,
                "recovery_priority_order": dep.recovery_priority_order,
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

    # ── 4. Live Dependency Health & Blast-Radius Simulation (Batch 5) ────────

    @classmethod
    def _evaluate_single_dependency_health(
        cls,
        db: Session,
        organization_id: int,
        dep: ProcessDependency,
    ) -> DependencyHealthItem:
        dtype = dep.dependency_type
        target_id = dep.dependency_id
        target_name = f"{dtype.value} #{target_id}"
        health_status = "HEALTHY"
        health_score = 100.0
        status_detail = "Operational"

        if dtype == DependencyTypeEnum.VENDOR:
            vendor = (
                db.query(Vendor)
                .filter(Vendor.id == target_id, Vendor.organization_id == organization_id)
                .first()
            )
            if vendor:
                target_name = vendor.legal_name
                if (
                    vendor.vendor_status in (VendorStatusEnum.SUSPENDED, VendorStatusEnum.OFFBOARDED)
                    or vendor.risk_band == VendorRiskBandEnum.CRITICAL
                ):
                    health_status = "CRITICAL"
                    health_score = 0.0
                    status_detail = f"Vendor status={vendor.vendor_status.value}, risk_band={vendor.risk_band.value if vendor.risk_band else 'N/A'}"
                elif vendor.risk_band == VendorRiskBandEnum.HIGH:
                    health_status = "DEGRADED"
                    health_score = 50.0
                    status_detail = "Vendor risk_band=HIGH"
                else:
                    status_detail = f"Vendor active ({vendor.risk_band.value if vendor.risk_band else 'LOW'})"

        elif dtype == DependencyTypeEnum.CONTROL:
            ctrl = (
                db.query(OrganizationControl)
                .filter(
                    OrganizationControl.id == target_id,
                    OrganizationControl.organization_id == organization_id,
                )
                .first()
            )
            if ctrl:
                target_name = f"Control #{ctrl.id}"
                if ctrl.status == ImplementationStatusEnum.NOT_IMPLEMENTED:
                    health_status = "CRITICAL"
                    health_score = 0.0
                    status_detail = "Control NOT_IMPLEMENTED"
                elif ctrl.status == ImplementationStatusEnum.IN_PROGRESS:
                    health_status = "DEGRADED"
                    health_score = 50.0
                    status_detail = "Control IN_PROGRESS"
                else:
                    status_detail = "Control IMPLEMENTED"

        elif dtype == DependencyTypeEnum.CLOUD_ASSET:
            ca = (
                db.query(CloudAsset)
                .filter(CloudAsset.id == target_id, CloudAsset.organization_id == organization_id)
                .first()
            )
            if ca:
                target_name = getattr(ca, "resource_name", None) or f"CloudAsset #{ca.id}"
                if (
                    ca.posture_status == CloudPostureStatusEnum.NON_COMPLIANT
                    or ca.lifecycle_state == CloudLifecycleStateEnum.DECOMMISSIONED
                ):
                    health_status = "CRITICAL"
                    health_score = 0.0
                    status_detail = f"Cloud posture={ca.posture_status.value}"
                elif ca.posture_status in (
                    CloudPostureStatusEnum.DEVIATED,
                    CloudPostureStatusEnum.UNASSESSED,
                ):
                    health_status = "DEGRADED"
                    health_score = 50.0
                    status_detail = f"Cloud posture={ca.posture_status.value}"
                else:
                    status_detail = "Cloud posture COMPLIANT"

        elif dtype == DependencyTypeEnum.DATA_ASSET:
            da = (
                db.query(DataAsset)
                .filter(DataAsset.id == target_id, DataAsset.organization_id == organization_id)
                .first()
            )
            if da:
                target_name = da.name
                lstate = (da.lifecycle_state or "ACTIVE").upper()
                cstat = (da.classification_status or "APPROVED").upper()
                if lstate in ("ARCHIVED", "PURGED", "DISPOSED", "RETIRED"):
                    health_status = "CRITICAL"
                    health_score = 0.0
                    status_detail = f"DataAsset lifecycle_state={lstate}"
                elif cstat not in ("APPROVED", "VERIFIED"):
                    health_status = "DEGRADED"
                    health_score = 50.0
                    status_detail = f"DataAsset classification_status={cstat}"
                else:
                    status_detail = f"DataAsset {lstate} ({cstat})"

        elif dtype == DependencyTypeEnum.PROCESS:
            up_proc = (
                db.query(BusinessProcess)
                .filter(
                    BusinessProcess.id == target_id,
                    BusinessProcess.organization_id == organization_id,
                )
                .first()
            )
            if up_proc:
                target_name = up_proc.name
                up_bia = (
                    db.query(BusinessImpactAnalysis)
                    .filter(
                        BusinessImpactAnalysis.organization_id == organization_id,
                        BusinessImpactAnalysis.process_id == up_proc.id,
                        BusinessImpactAnalysis.status == BiaStatusEnum.ACTIVE,
                    )
                    .first()
                )
                up_plan = (
                    db.query(ContinuityPlan)
                    .filter(
                        ContinuityPlan.organization_id == organization_id,
                        ContinuityPlan.process_id == up_proc.id,
                        ContinuityPlan.status == ContinuityPlanStatusEnum.APPROVED,
                    )
                    .first()
                )
                if not up_bia or not up_plan:
                    health_status = "DEGRADED"
                    health_score = 50.0
                    status_detail = "Upstream process missing active BIA or approved Continuity Plan"
                else:
                    status_detail = "Upstream process governed"

        return DependencyHealthItem(
            dependency_id=dep.id,
            dependency_type=dtype,
            target_id=target_id,
            target_name=target_name,
            health_status=health_status,
            health_score=health_score,
            is_single_point_of_failure=bool(dep.is_single_point_of_failure),
            failure_propagation_weight=float(dep.failure_propagation_weight),
            recovery_priority_order=int(dep.recovery_priority_order),
            status_detail=status_detail,
        )

    @classmethod
    def get_process_dependency_health(
        cls,
        db: Session,
        organization_id: int,
        process_id: int,
    ) -> ProcessDependencyHealthResponse:
        process = cls.get_business_process(db, organization_id, process_id)
        deps = (
            db.query(ProcessDependency)
            .filter(
                ProcessDependency.organization_id == organization_id,
                ProcessDependency.process_id == process_id,
            )
            .order_by(ProcessDependency.recovery_priority_order.asc(), ProcessDependency.id.asc())
            .all()
        )

        items: List[DependencyHealthItem] = []
        weighted_sum = 0.0
        total_weight = 0.0
        spof_count = 0
        healthy_count = 0
        degraded_count = 0
        critical_count = 0

        for d in deps:
            item = cls._evaluate_single_dependency_health(db, organization_id, d)
            items.append(item)
            if item.is_single_point_of_failure:
                spof_count += 1
            if item.health_status == "HEALTHY":
                healthy_count += 1
            elif item.health_status == "DEGRADED":
                degraded_count += 1
            else:
                critical_count += 1

            alpha = item.failure_propagation_weight * (2.0 if item.is_single_point_of_failure else 1.0)
            weighted_sum += alpha * item.health_score
            total_weight += alpha

        dep_health_score = round(weighted_sum / total_weight, 2) if total_weight > 0 else 100.0

        approved_plan = (
            db.query(ContinuityPlan)
            .filter(
                ContinuityPlan.organization_id == organization_id,
                ContinuityPlan.process_id == process_id,
                ContinuityPlan.status == ContinuityPlanStatusEnum.APPROVED,
            )
            .first()
        )
        unmitigated_spof_count = spof_count if approved_plan is None else 0

        return ProcessDependencyHealthResponse(
            process_id=process.id,
            process_name=process.name,
            dependency_health_score=dep_health_score,
            total_dependencies=len(deps),
            spof_count=spof_count,
            unmitigated_spof_count=unmitigated_spof_count,
            healthy_count=healthy_count,
            degraded_count=degraded_count,
            critical_count=critical_count,
            dependencies=items,
        )

    @classmethod
    def simulate_outage(
        cls,
        db: Session,
        organization_id: int,
        request: OutageSimulationRequest,
    ) -> OutageSimulationResponse:
        """
        Deterministic BFS outage blast-radius simulation across VENDOR, CONTROL,
        CLOUD_ASSET, DATA_ASSET, and PROCESS dependency edges (max_depth = 10).
        """
        direct_deps = (
            db.query(ProcessDependency)
            .filter(
                ProcessDependency.organization_id == organization_id,
                ProcessDependency.dependency_type == request.failing_node_type,
                ProcessDependency.dependency_id == request.failing_node_id,
            )
            .all()
        )

        queue: deque[Tuple[int, int, float]] = deque()
        best_weight: Dict[int, Tuple[int, float]] = {}

        if request.failing_node_type == DependencyTypeEnum.PROCESS:
            root_proc = (
                db.query(BusinessProcess)
                .filter(
                    BusinessProcess.id == request.failing_node_id,
                    BusinessProcess.organization_id == organization_id,
                )
                .first()
            )
            if not root_proc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Business Process #{request.failing_node_id} not found in tenant.",
                )
            queue.append((root_proc.id, 0, 1.0))
            best_weight[root_proc.id] = (0, 1.0)

        for dep in direct_deps:
            w = float(dep.failure_propagation_weight)
            if dep.process_id not in best_weight or w > best_weight[dep.process_id][1]:
                best_weight[dep.process_id] = (1, w)
                queue.append((dep.process_id, 1, w))

        max_depth = 10
        while queue:
            curr_proc_id, hop, curr_w = queue.popleft()
            if hop >= max_depth:
                continue
            downstream_edges = (
                db.query(ProcessDependency)
                .filter(
                    ProcessDependency.organization_id == organization_id,
                    ProcessDependency.dependency_type == DependencyTypeEnum.PROCESS,
                    ProcessDependency.dependency_id == curr_proc_id,
                )
                .all()
            )
            for edge in downstream_edges:
                next_proc_id = edge.process_id
                next_w = round(curr_w * float(edge.failure_propagation_weight), 4)
                if next_proc_id not in best_weight or next_w > best_weight[next_proc_id][1]:
                    best_weight[next_proc_id] = (hop + 1, next_w)
                    queue.append((next_proc_id, hop + 1, next_w))

        affected_list: List[OutageSimulationAffectedProcess] = []
        tier_1_count = 0
        rto_breach_count = 0
        mtd_breach_count = 0
        total_loss = 0.0

        for proc_id, (hop, eff_w) in sorted(best_weight.items(), key=lambda x: (x[1][0], x[0])):
            proc = (
                db.query(BusinessProcess)
                .filter(
                    BusinessProcess.id == proc_id,
                    BusinessProcess.organization_id == organization_id,
                )
                .first()
            )
            if not proc:
                continue
            active_bia = (
                db.query(BusinessImpactAnalysis)
                .filter(
                    BusinessImpactAnalysis.organization_id == organization_id,
                    BusinessImpactAnalysis.process_id == proc.id,
                    BusinessImpactAnalysis.status == BiaStatusEnum.ACTIVE,
                )
                .first()
            )
            raw_loss = 0.0
            rto_breached = False
            mtd_breached = False
            if active_bia:
                loss_calc = calculate_projected_outage_loss(
                    duration_hours=request.outage_duration_hours,
                    hourly_downtime_cost=active_bia.hourly_downtime_cost,
                    fixed_outage_cost=active_bia.fixed_outage_cost,
                )
                raw_loss = round(loss_calc["total_projected_loss"] * eff_w, 2)
                rto_breached = request.outage_duration_hours > active_bia.rto_hours
                mtd_breached = request.outage_duration_hours > active_bia.mtd_hours

            if proc.criticality_tier == CriticalityTierEnum.TIER_1:
                tier_1_count += 1
            if rto_breached:
                rto_breach_count += 1
            if mtd_breached:
                mtd_breach_count += 1
            total_loss = round(total_loss + raw_loss, 2)

            affected_list.append(
                OutageSimulationAffectedProcess(
                    process_id=proc.id,
                    process_name=proc.name,
                    criticality_tier=proc.criticality_tier,
                    hop_distance=hop,
                    effective_propagation_weight=eff_w,
                    projected_financial_loss=raw_loss,
                    rto_breached=rto_breached,
                    mtd_breached=mtd_breached,
                )
            )

        return OutageSimulationResponse(
            failing_node_type=request.failing_node_type,
            failing_node_id=request.failing_node_id,
            outage_duration_hours=request.outage_duration_hours,
            affected_process_count=len(affected_list),
            tier_1_affected_count=tier_1_count,
            rto_breach_count=rto_breach_count,
            mtd_breach_count=mtd_breach_count,
            total_projected_financial_loss=total_loss,
            affected_processes=affected_list,
        )

    # ── 5. Continuity Plans & Recovery Steps Lifecycle (Batch 5) ─────────────

    @classmethod
    def _get_continuity_plan_or_404(
        cls,
        db: Session,
        organization_id: int,
        plan_id: int,
    ) -> ContinuityPlan:
        plan = (
            db.query(ContinuityPlan)
            .filter(
                ContinuityPlan.id == plan_id,
                ContinuityPlan.organization_id == organization_id,
            )
            .first()
        )
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Continuity Plan #{plan_id} not found in tenant.",
            )
        return plan

    @classmethod
    def list_continuity_plans(
        cls,
        db: Session,
        organization_id: int,
        process_id: int,
        status_filter: Optional[ContinuityPlanStatusEnum] = None,
    ) -> List[ContinuityPlan]:
        cls.get_business_process(db, organization_id, process_id)
        query = db.query(ContinuityPlan).filter(
            ContinuityPlan.organization_id == organization_id,
            ContinuityPlan.process_id == process_id,
        )
        if status_filter is not None:
            query = query.filter(ContinuityPlan.status == status_filter)
        return query.order_by(
            ContinuityPlan.version_major.desc(),
            ContinuityPlan.version_minor.desc(),
            ContinuityPlan.id.desc(),
        ).all()

    @classmethod
    def create_continuity_plan(
        cls,
        db: Session,
        organization_id: int,
        process_id: int,
        data: ContinuityPlanCreate,
        user_id: int,
    ) -> ContinuityPlan:
        process = cls.get_business_process(db, organization_id, process_id)

        resolved_bia_id: Optional[int] = None
        if data.bia_id is not None:
            bia = cls.get_bia(db, organization_id, data.bia_id)
            if bia.process_id != process.id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Specified BIA does not belong to the target business process.",
                )
            resolved_bia_id = bia.id
        elif getattr(process, "active_bia", None) is not None:
            resolved_bia_id = process.active_bia.id

        version_label = f"{data.version_major}.{data.version_minor}"
        clean_code = data.plan_code.strip()

        existing = (
            db.query(ContinuityPlan)
            .filter(
                ContinuityPlan.organization_id == organization_id,
                ContinuityPlan.process_id == process_id,
                ContinuityPlan.plan_code == clean_code,
                ContinuityPlan.version_label == version_label,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Continuity Plan '{clean_code}' version {version_label} already exists for this process.",
            )

        plan = ContinuityPlan(
            organization_id=organization_id,
            process_id=process_id,
            bia_id=resolved_bia_id,
            plan_code=clean_code,
            title=data.title.strip(),
            version_major=data.version_major,
            version_minor=data.version_minor,
            version_label=version_label,
            status=ContinuityPlanStatusEnum.DRAFT,
            strategy_type=data.strategy_type,
            activation_triggers=data.activation_triggers,
            communication_plan=data.communication_plan,
            fallback_location_or_region=data.fallback_location_or_region,
            estimated_recovery_hours=data.estimated_recovery_hours,
            estimated_rpo_hours=data.estimated_rpo_hours,
            review_frequency_days=data.review_frequency_days,
            created_by_user_id=user_id,
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="continuity_plan.created",
            resource_type="continuity_plan",
            resource_id=str(plan.id),
            actor_email=cls._get_actor_email(db, user_id),
            actor_id=user_id,
            details={
                "process_id": process_id,
                "plan_code": plan.plan_code,
                "version_label": plan.version_label,
                "strategy_type": plan.strategy_type.value,
            },
        )
        return plan

    @classmethod
    def get_continuity_plan_detail(
        cls,
        db: Session,
        organization_id: int,
        plan_id: int,
    ) -> Dict[str, Any]:
        plan = cls._get_continuity_plan_or_404(db, organization_id, plan_id)
        steps = (
            db.query(ContinuityRecoveryStep)
            .filter(
                ContinuityRecoveryStep.organization_id == organization_id,
                ContinuityRecoveryStep.continuity_plan_id == plan.id,
            )
            .order_by(ContinuityRecoveryStep.step_order.asc())
            .all()
        )
        evidence_links = (
            db.query(ResilienceEvidenceLink)
            .filter(
                ResilienceEvidenceLink.organization_id == organization_id,
                ResilienceEvidenceLink.continuity_plan_id == plan.id,
            )
            .order_by(ResilienceEvidenceLink.id.asc())
            .all()
        )
        total_minutes = sum(int(s.estimated_duration_minutes) for s in steps)
        total_hours = round(total_minutes / 60.0, 4)

        return {
            "id": plan.id,
            "organization_id": plan.organization_id,
            "process_id": plan.process_id,
            "bia_id": plan.bia_id,
            "plan_code": plan.plan_code,
            "title": plan.title,
            "version_major": plan.version_major,
            "version_minor": plan.version_minor,
            "version_label": plan.version_label,
            "status": plan.status,
            "strategy_type": plan.strategy_type,
            "activation_triggers": plan.activation_triggers,
            "communication_plan": plan.communication_plan,
            "fallback_location_or_region": plan.fallback_location_or_region,
            "estimated_recovery_hours": plan.estimated_recovery_hours,
            "estimated_rpo_hours": plan.estimated_rpo_hours,
            "review_frequency_days": plan.review_frequency_days,
            "next_review_due_at": plan.next_review_due_at,
            "plan_hash_sha256": plan.plan_hash_sha256,
            "created_by_user_id": plan.created_by_user_id,
            "submitted_by_user_id": plan.submitted_by_user_id,
            "submitted_at": plan.submitted_at,
            "approved_by_user_id": plan.approved_by_user_id,
            "approved_at": plan.approved_at,
            "superseded_by_plan_id": plan.superseded_by_plan_id,
            "created_at": plan.created_at,
            "updated_at": plan.updated_at,
            "recovery_steps": steps,
            "total_step_duration_minutes": total_minutes,
            "total_step_duration_hours": total_hours,
            "evidence_links": evidence_links,
        }

    @classmethod
    def update_continuity_plan(
        cls,
        db: Session,
        organization_id: int,
        plan_id: int,
        data: ContinuityPlanUpdate,
        user_id: int,
    ) -> ContinuityPlan:
        plan = cls._get_continuity_plan_or_404(db, organization_id, plan_id)
        if plan.status != ContinuityPlanStatusEnum.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot modify Continuity Plan #{plan_id} in {plan.status.value} status. Only DRAFT plans are editable.",
            )

        update_fields = data.model_dump(exclude_unset=True)
        if "bia_id" in update_fields and update_fields["bia_id"] is not None:
            bia = cls.get_bia(db, organization_id, update_fields["bia_id"])
            if bia.process_id != plan.process_id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Specified BIA does not belong to this plan's business process.",
                )

        for field, value in update_fields.items():
            setattr(plan, field, value)

        db.commit()
        db.refresh(plan)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="continuity_plan.updated",
            resource_type="continuity_plan",
            resource_id=str(plan.id),
            actor_email=cls._get_actor_email(db, user_id),
            actor_id=user_id,
            details={"updated_fields": list(update_fields.keys())},
        )
        return plan

    @classmethod
    def _validate_step_references(
        cls,
        db: Session,
        organization_id: int,
        responsible_user_id: Optional[int],
        cloud_asset_id: Optional[int],
        data_asset_id: Optional[int],
        vendor_id: Optional[int],
        organization_control_id: Optional[int],
    ) -> None:
        if responsible_user_id is not None:
            u = (
                db.query(User)
                .filter(User.id == responsible_user_id, User.organization_id == organization_id)
                .first()
            )
            if not u:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Responsible User #{responsible_user_id} not found in tenant.",
                )
        if cloud_asset_id is not None:
            ca = (
                db.query(CloudAsset)
                .filter(CloudAsset.id == cloud_asset_id, CloudAsset.organization_id == organization_id)
                .first()
            )
            if not ca:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"CloudAsset #{cloud_asset_id} not found in tenant.",
                )
        if data_asset_id is not None:
            da = (
                db.query(DataAsset)
                .filter(DataAsset.id == data_asset_id, DataAsset.organization_id == organization_id)
                .first()
            )
            if not da:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"DataAsset #{data_asset_id} not found in tenant.",
                )
        if vendor_id is not None:
            v = (
                db.query(Vendor)
                .filter(Vendor.id == vendor_id, Vendor.organization_id == organization_id)
                .first()
            )
            if not v:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Vendor #{vendor_id} not found in tenant.",
                )
        if organization_control_id is not None:
            c = (
                db.query(OrganizationControl)
                .filter(
                    OrganizationControl.id == organization_control_id,
                    OrganizationControl.organization_id == organization_id,
                )
                .first()
            )
            if not c:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"OrganizationControl #{organization_control_id} not found in tenant.",
                )

    @classmethod
    def list_recovery_steps(
        cls,
        db: Session,
        organization_id: int,
        plan_id: int,
    ) -> List[ContinuityRecoveryStep]:
        cls._get_continuity_plan_or_404(db, organization_id, plan_id)
        return (
            db.query(ContinuityRecoveryStep)
            .filter(
                ContinuityRecoveryStep.organization_id == organization_id,
                ContinuityRecoveryStep.continuity_plan_id == plan_id,
            )
            .order_by(ContinuityRecoveryStep.step_order.asc())
            .all()
        )

    @classmethod
    def create_recovery_step(
        cls,
        db: Session,
        organization_id: int,
        plan_id: int,
        data: ContinuityRecoveryStepCreate,
        user_id: int,
    ) -> ContinuityRecoveryStep:
        plan = cls._get_continuity_plan_or_404(db, organization_id, plan_id)
        if plan.status != ContinuityPlanStatusEnum.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Recovery steps can only be added while the Continuity Plan is in DRAFT status.",
            )

        cls._validate_step_references(
            db,
            organization_id,
            data.responsible_user_id,
            data.cloud_asset_id,
            data.data_asset_id,
            data.vendor_id,
            data.organization_control_id,
        )

        dup_order = (
            db.query(ContinuityRecoveryStep)
            .filter(
                ContinuityRecoveryStep.continuity_plan_id == plan_id,
                ContinuityRecoveryStep.step_order == data.step_order,
            )
            .first()
        )
        if dup_order:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Step order {data.step_order} already exists in Continuity Plan #{plan_id}.",
            )

        step = ContinuityRecoveryStep(
            organization_id=organization_id,
            continuity_plan_id=plan_id,
            step_order=data.step_order,
            title=data.title.strip(),
            description=data.description,
            responsible_role_or_team=data.responsible_role_or_team,
            responsible_user_id=data.responsible_user_id,
            estimated_duration_minutes=data.estimated_duration_minutes,
            cloud_asset_id=data.cloud_asset_id,
            data_asset_id=data.data_asset_id,
            vendor_id=data.vendor_id,
            organization_control_id=data.organization_control_id,
            verification_criteria=data.verification_criteria,
            is_automated=data.is_automated,
        )
        db.add(step)
        db.commit()
        db.refresh(step)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="continuity_recovery_step.created",
            resource_type="continuity_recovery_step",
            resource_id=str(step.id),
            actor_email=cls._get_actor_email(db, user_id),
            actor_id=user_id,
            details={
                "continuity_plan_id": plan_id,
                "step_order": step.step_order,
                "estimated_duration_minutes": step.estimated_duration_minutes,
            },
        )
        return step

    @classmethod
    def update_recovery_step(
        cls,
        db: Session,
        organization_id: int,
        plan_id: int,
        step_id: int,
        data: ContinuityRecoveryStepUpdate,
        user_id: int,
    ) -> ContinuityRecoveryStep:
        plan = cls._get_continuity_plan_or_404(db, organization_id, plan_id)
        if plan.status != ContinuityPlanStatusEnum.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Recovery steps can only be modified while the Continuity Plan is in DRAFT status.",
            )

        step = (
            db.query(ContinuityRecoveryStep)
            .filter(
                ContinuityRecoveryStep.id == step_id,
                ContinuityRecoveryStep.continuity_plan_id == plan_id,
                ContinuityRecoveryStep.organization_id == organization_id,
            )
            .first()
        )
        if not step:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recovery Step #{step_id} not found in Continuity Plan #{plan_id}.",
            )

        update_fields = data.model_dump(exclude_unset=True)
        cls._validate_step_references(
            db,
            organization_id,
            update_fields.get("responsible_user_id"),
            update_fields.get("cloud_asset_id"),
            update_fields.get("data_asset_id"),
            update_fields.get("vendor_id"),
            update_fields.get("organization_control_id"),
        )

        if "step_order" in update_fields and update_fields["step_order"] != step.step_order:
            dup = (
                db.query(ContinuityRecoveryStep)
                .filter(
                    ContinuityRecoveryStep.continuity_plan_id == plan_id,
                    ContinuityRecoveryStep.step_order == update_fields["step_order"],
                    ContinuityRecoveryStep.id != step.id,
                )
                .first()
            )
            if dup:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Step order {update_fields['step_order']} already exists in Continuity Plan #{plan_id}.",
                )

        for k, v in update_fields.items():
            setattr(step, k, v)

        db.commit()
        db.refresh(step)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="continuity_recovery_step.updated",
            resource_type="continuity_recovery_step",
            resource_id=str(step.id),
            actor_email=cls._get_actor_email(db, user_id),
            actor_id=user_id,
            details={
                "continuity_plan_id": plan_id,
                "step_order": step.step_order,
                "estimated_duration_minutes": step.estimated_duration_minutes,
            },
        )
        return step

    @classmethod
    def delete_recovery_step(
        cls,
        db: Session,
        organization_id: int,
        plan_id: int,
        step_id: int,
        user_id: int,
    ) -> None:
        plan = cls._get_continuity_plan_or_404(db, organization_id, plan_id)
        if plan.status != ContinuityPlanStatusEnum.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Recovery steps can only be deleted while the Continuity Plan is in DRAFT status.",
            )

        step = (
            db.query(ContinuityRecoveryStep)
            .filter(
                ContinuityRecoveryStep.id == step_id,
                ContinuityRecoveryStep.continuity_plan_id == plan_id,
                ContinuityRecoveryStep.organization_id == organization_id,
            )
            .first()
        )
        if not step:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recovery Step #{step_id} not found in Continuity Plan #{plan_id}.",
            )

        step_order = step.step_order
        db.delete(step)
        db.commit()

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="continuity_recovery_step.deleted",
            resource_type="continuity_recovery_step",
            resource_id=str(step_id),
            actor_email=cls._get_actor_email(db, user_id),
            actor_id=user_id,
            details={"continuity_plan_id": plan_id, "step_order": step_order},
        )

    @classmethod
    def _validate_plan_bia_and_steps_invariants(
        cls,
        db: Session,
        organization_id: int,
        plan: ContinuityPlan,
    ) -> Tuple[BusinessImpactAnalysis, List[ContinuityRecoveryStep]]:
        active_bia = (
            db.query(BusinessImpactAnalysis)
            .filter(
                BusinessImpactAnalysis.organization_id == organization_id,
                BusinessImpactAnalysis.process_id == plan.process_id,
                BusinessImpactAnalysis.status == BiaStatusEnum.ACTIVE,
            )
            .first()
        )
        if not active_bia:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cannot submit or approve a Continuity Plan when the Business Process has no ACTIVE approved BIA.",
            )

        if plan.estimated_recovery_hours > active_bia.rto_hours:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Plan estimated_recovery_hours ({plan.estimated_recovery_hours}h) exceeds "
                    f"the active BIA RTO target ({active_bia.rto_hours}h)."
                ),
            )

        if plan.estimated_rpo_hours > active_bia.rpo_hours:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Plan estimated_rpo_hours ({plan.estimated_rpo_hours}h) exceeds "
                    f"the active BIA RPO target ({active_bia.rpo_hours}h)."
                ),
            )

        steps = (
            db.query(ContinuityRecoveryStep)
            .filter(
                ContinuityRecoveryStep.organization_id == organization_id,
                ContinuityRecoveryStep.continuity_plan_id == plan.id,
            )
            .order_by(ContinuityRecoveryStep.step_order.asc())
            .all()
        )
        if len(steps) < 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Continuity Plan must have at least one ContinuityRecoveryStep before submission or approval.",
            )

        step_hours = round(sum(int(s.estimated_duration_minutes) for s in steps) / 60.0, 4)
        if step_hours > round(float(plan.estimated_recovery_hours), 4):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Cumulative recovery step duration ({step_hours}h) exceeds "
                    f"plan estimated_recovery_hours ({plan.estimated_recovery_hours}h)."
                ),
            )

        return active_bia, steps

    @classmethod
    def submit_continuity_plan(
        cls,
        db: Session,
        organization_id: int,
        plan_id: int,
        user_id: int,
    ) -> ContinuityPlan:
        plan = cls._get_continuity_plan_or_404(db, organization_id, plan_id)
        if plan.status != ContinuityPlanStatusEnum.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Only DRAFT Continuity Plans can be submitted for approval (current status: {plan.status.value}).",
            )

        active_bia, steps = cls._validate_plan_bia_and_steps_invariants(db, organization_id, plan)
        now_utc = datetime.now(timezone.utc)

        plan.bia_id = active_bia.id
        plan.status = ContinuityPlanStatusEnum.PENDING_APPROVAL
        plan.submitted_by_user_id = user_id
        plan.submitted_at = now_utc
        plan.plan_hash_sha256 = compute_plan_hash_sha256(plan, steps)

        db.commit()
        db.refresh(plan)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="continuity_plan.submitted",
            resource_type="continuity_plan",
            resource_id=str(plan.id),
            actor_email=cls._get_actor_email(db, user_id),
            actor_id=user_id,
            details={
                "plan_code": plan.plan_code,
                "version_label": plan.version_label,
                "plan_hash_sha256": plan.plan_hash_sha256,
            },
        )
        return plan

    @classmethod
    def approve_continuity_plan(
        cls,
        db: Session,
        organization_id: int,
        plan_id: int,
        user_id: int,
    ) -> ContinuityPlan:
        plan = cls._get_continuity_plan_or_404(db, organization_id, plan_id)
        if plan.status != ContinuityPlanStatusEnum.PENDING_APPROVAL:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Only PENDING_APPROVAL Continuity Plans can be approved (current status: {plan.status.value}).",
            )

        # Four-Eyes Separation of Duties: neither creator nor submitter can approve
        if user_id == plan.created_by_user_id or user_id == plan.submitted_by_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Four-eyes governance violation: plan creator or submitter cannot approve their own Continuity Plan.",
            )

        active_bia, steps = cls._validate_plan_bia_and_steps_invariants(db, organization_id, plan)
        now_utc = datetime.now(timezone.utc)

        # Atomically supersede any existing APPROVED ContinuityPlan for this process
        prior_approved = (
            db.query(ContinuityPlan)
            .filter(
                ContinuityPlan.organization_id == organization_id,
                ContinuityPlan.process_id == plan.process_id,
                ContinuityPlan.status == ContinuityPlanStatusEnum.APPROVED,
                ContinuityPlan.id != plan.id,
            )
            .all()
        )
        superseded_ids: List[int] = []
        for old_plan in prior_approved:
            old_plan.status = ContinuityPlanStatusEnum.SUPERSEDED
            old_plan.superseded_by_plan_id = plan.id
            superseded_ids.append(old_plan.id)

        plan.bia_id = active_bia.id
        plan.status = ContinuityPlanStatusEnum.APPROVED
        plan.approved_by_user_id = user_id
        plan.approved_at = now_utc
        plan.next_review_due_at = now_utc + timedelta(days=int(plan.review_frequency_days))
        plan.plan_hash_sha256 = compute_plan_hash_sha256(plan, steps)

        db.commit()
        db.refresh(plan)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="continuity_plan.approved",
            resource_type="continuity_plan",
            resource_id=str(plan.id),
            actor_email=cls._get_actor_email(db, user_id),
            actor_id=user_id,
            details={
                "plan_code": plan.plan_code,
                "version_label": plan.version_label,
                "superseded_plan_ids": superseded_ids,
                "plan_hash_sha256": plan.plan_hash_sha256,
            },
        )
        return plan

    @classmethod
    def reject_continuity_plan(
        cls,
        db: Session,
        organization_id: int,
        plan_id: int,
        data: ContinuityPlanRejectRequest,
        user_id: int,
    ) -> ContinuityPlan:
        plan = cls._get_continuity_plan_or_404(db, organization_id, plan_id)
        if plan.status != ContinuityPlanStatusEnum.PENDING_APPROVAL:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Only PENDING_APPROVAL Continuity Plans can be rejected (current status: {plan.status.value}).",
            )

        plan.status = ContinuityPlanStatusEnum.DRAFT
        plan.submitted_at = None

        db.commit()
        db.refresh(plan)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="continuity_plan.rejected",
            resource_type="continuity_plan",
            resource_id=str(plan.id),
            actor_email=cls._get_actor_email(db, user_id),
            actor_id=user_id,
            details={"plan_code": plan.plan_code, "reason": data.reason},
        )
        return plan

    @classmethod
    def archive_continuity_plan(
        cls,
        db: Session,
        organization_id: int,
        plan_id: int,
        user_id: int,
    ) -> ContinuityPlan:
        plan = cls._get_continuity_plan_or_404(db, organization_id, plan_id)
        if plan.status not in (ContinuityPlanStatusEnum.DRAFT, ContinuityPlanStatusEnum.APPROVED):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot archive Continuity Plan in {plan.status.value} status.",
            )

        if plan.status == ContinuityPlanStatusEnum.APPROVED:
            from app.core.permissions import Permission, has_permission

            caller = db.query(User).filter(User.id == user_id).first()
            if caller and not has_permission(caller.role, Permission.RESILIENCE_APPROVE):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Archiving an APPROVED Continuity Plan requires RESILIENCE_APPROVE permission.",
                )

        active_exercises = (
            db.query(ResilienceExercise)
            .filter(
                ResilienceExercise.organization_id == organization_id,
                ResilienceExercise.continuity_plan_id == plan.id,
                ResilienceExercise.status.in_(
                    [ExerciseStatusEnum.PLANNED, ExerciseStatusEnum.IN_PROGRESS]
                ),
            )
            .count()
        )
        if active_exercises > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot archive a Continuity Plan while active (PLANNED or IN_PROGRESS) exercises reference it.",
            )

        prev_status = plan.status.value
        plan.status = ContinuityPlanStatusEnum.ARCHIVED
        db.commit()
        db.refresh(plan)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="continuity_plan.archived",
            resource_type="continuity_plan",
            resource_id=str(plan.id),
            actor_email=cls._get_actor_email(db, user_id),
            actor_id=user_id,
            details={"plan_code": plan.plan_code, "previous_status": prev_status},
        )
        return plan

    # ── 6. Evidence Cryptographic Binding (Batch 5) ──────────────────────────

    @classmethod
    def _validate_evidence_item_for_link(
        cls,
        db: Session,
        organization_id: int,
        evidence_item_id: int,
    ) -> EvidenceItem:
        ev = (
            db.query(EvidenceItem)
            .filter(
                EvidenceItem.id == evidence_item_id,
                EvidenceItem.organization_id == organization_id,
            )
            .first()
        )
        if not ev:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"EvidenceItem #{evidence_item_id} not found in tenant.",
            )

        if ev.status in (EvidenceStatusEnum.REJECTED, EvidenceStatusEnum.SUPERSEDED):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Cannot bind EvidenceItem #{evidence_item_id} with status {ev.status.value}.",
            )

        expires_at = getattr(ev, "expires_at", None)
        if expires_at is not None:
            now_utc = datetime.now(timezone.utc)
            exp_dt = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)
            if exp_dt < now_utc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Cannot bind expired EvidenceItem #{evidence_item_id}.",
                )

        return ev

    @classmethod
    def list_plan_evidence(
        cls,
        db: Session,
        organization_id: int,
        plan_id: int,
    ) -> List[ResilienceEvidenceLink]:
        cls._get_continuity_plan_or_404(db, organization_id, plan_id)
        return (
            db.query(ResilienceEvidenceLink)
            .filter(
                ResilienceEvidenceLink.organization_id == organization_id,
                ResilienceEvidenceLink.continuity_plan_id == plan_id,
            )
            .order_by(ResilienceEvidenceLink.id.asc())
            .all()
        )

    @classmethod
    def link_evidence_to_plan(
        cls,
        db: Session,
        organization_id: int,
        plan_id: int,
        data: ResilienceEvidenceLinkCreate,
        user_id: int,
    ) -> ResilienceEvidenceLink:
        plan = cls._get_continuity_plan_or_404(db, organization_id, plan_id)
        ev = cls._validate_evidence_item_for_link(db, organization_id, data.evidence_item_id)

        existing = (
            db.query(ResilienceEvidenceLink)
            .filter(
                ResilienceEvidenceLink.organization_id == organization_id,
                ResilienceEvidenceLink.continuity_plan_id == plan.id,
                ResilienceEvidenceLink.evidence_item_id == ev.id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"EvidenceItem #{ev.id} is already linked to Continuity Plan #{plan.id}.",
            )

        link = ResilienceEvidenceLink(
            organization_id=organization_id,
            continuity_plan_id=plan.id,
            exercise_id=None,
            evidence_item_id=ev.id,
            evidence_type_context=data.evidence_type_context,
            evidence_sha256_snapshot=ev.sha256_hash,
            notes=data.notes,
            linked_by_user_id=user_id,
        )
        db.add(link)
        db.commit()
        db.refresh(link)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="resilience_evidence.linked",
            resource_type="resilience_evidence_link",
            resource_id=str(link.id),
            actor_email=cls._get_actor_email(db, user_id),
            actor_id=user_id,
            details={
                "subject_type": "continuity_plan",
                "subject_id": plan.id,
                "evidence_item_id": ev.id,
                "evidence_sha256_snapshot": link.evidence_sha256_snapshot,
            },
        )
        return link

    # ── 7. Resilience Exercises & Empirical RTO/RPO Evaluation (Batch 5) ─────

    @classmethod
    def _get_exercise_or_404(
        cls,
        db: Session,
        organization_id: int,
        exercise_id: int,
    ) -> ResilienceExercise:
        ex = (
            db.query(ResilienceExercise)
            .filter(
                ResilienceExercise.id == exercise_id,
                ResilienceExercise.organization_id == organization_id,
            )
            .first()
        )
        if not ex:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Resilience Exercise #{exercise_id} not found in tenant.",
            )
        return ex

    @classmethod
    def list_exercises(
        cls,
        db: Session,
        organization_id: int,
        process_id: Optional[int] = None,
        continuity_plan_id: Optional[int] = None,
        status_filter: Optional[ExerciseStatusEnum] = None,
        outcome_filter: Optional[ExerciseOutcomeEnum] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[ResilienceExercise]:
        query = db.query(ResilienceExercise).filter(
            ResilienceExercise.organization_id == organization_id
        )
        if process_id is not None:
            query = query.filter(ResilienceExercise.process_id == process_id)
        if continuity_plan_id is not None:
            query = query.filter(ResilienceExercise.continuity_plan_id == continuity_plan_id)
        if status_filter is not None:
            query = query.filter(ResilienceExercise.status == status_filter)
        if outcome_filter is not None:
            query = query.filter(ResilienceExercise.outcome == outcome_filter)

        return (
            query.order_by(
                ResilienceExercise.scheduled_start_at.desc(),
                ResilienceExercise.id.desc(),
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    @classmethod
    def get_exercise_detail(
        cls,
        db: Session,
        organization_id: int,
        exercise_id: int,
    ) -> ResilienceExercise:
        return cls._get_exercise_or_404(db, organization_id, exercise_id)

    @classmethod
    def create_exercise(
        cls,
        db: Session,
        organization_id: int,
        data: ResilienceExerciseCreate,
        user_id: int,
    ) -> ResilienceExercise:
        process = cls.get_business_process(db, organization_id, data.process_id)
        plan = cls._get_continuity_plan_or_404(db, organization_id, data.continuity_plan_id)

        if plan.process_id != process.id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Continuity Plan does not belong to the specified Business Process.",
            )

        if plan.status != ContinuityPlanStatusEnum.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Resilience Exercises can only be scheduled against an APPROVED Continuity Plan (plan status: {plan.status.value}).",
            )

        active_bia = getattr(process, "active_bia", None)
        if not active_bia:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cannot schedule a Resilience Exercise when the Business Process has no ACTIVE approved BIA.",
            )

        if data.triggered_by_incident_id is not None:
            inc = (
                db.query(SecurityIncident)
                .filter(
                    SecurityIncident.id == data.triggered_by_incident_id,
                    SecurityIncident.organization_id == organization_id,
                )
                .first()
            )
            if not inc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"SecurityIncident #{data.triggered_by_incident_id} not found in tenant.",
                )

        clean_code = data.exercise_code.strip()
        dup = (
            db.query(ResilienceExercise)
            .filter(
                ResilienceExercise.organization_id == organization_id,
                ResilienceExercise.exercise_code == clean_code,
            )
            .first()
        )
        if dup:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Resilience Exercise with code '{clean_code}' already exists in tenant.",
            )

        ex = ResilienceExercise(
            organization_id=organization_id,
            process_id=process.id,
            continuity_plan_id=plan.id,
            bia_id=active_bia.id,
            exercise_code=clean_code,
            title=data.title.strip(),
            exercise_type=data.exercise_type,
            status=ExerciseStatusEnum.PLANNED,
            scenario_description=data.scenario_description,
            scope_notes=data.scope_notes,
            scheduled_start_at=data.scheduled_start_at,
            target_rto_hours_snapshot=float(active_bia.rto_hours),
            target_rpo_hours_snapshot=float(active_bia.rpo_hours),
            target_mtd_hours_snapshot=float(active_bia.mtd_hours),
            planned_by_user_id=user_id,
            triggered_by_incident_id=data.triggered_by_incident_id,
        )
        db.add(ex)
        db.commit()
        db.refresh(ex)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="resilience_exercise.created",
            resource_type="resilience_exercise",
            resource_id=str(ex.id),
            actor_email=cls._get_actor_email(db, user_id),
            actor_id=user_id,
            details={
                "exercise_code": ex.exercise_code,
                "exercise_type": ex.exercise_type.value,
                "process_id": ex.process_id,
                "continuity_plan_id": ex.continuity_plan_id,
                "target_rto_hours_snapshot": ex.target_rto_hours_snapshot,
                "target_rpo_hours_snapshot": ex.target_rpo_hours_snapshot,
                "target_mtd_hours_snapshot": ex.target_mtd_hours_snapshot,
            },
        )
        return ex

    @classmethod
    def list_exercise_evidence(
        cls,
        db: Session,
        organization_id: int,
        exercise_id: int,
    ) -> List[ResilienceEvidenceLink]:
        cls._get_exercise_or_404(db, organization_id, exercise_id)
        return (
            db.query(ResilienceEvidenceLink)
            .filter(
                ResilienceEvidenceLink.organization_id == organization_id,
                ResilienceEvidenceLink.exercise_id == exercise_id,
            )
            .order_by(ResilienceEvidenceLink.id.asc())
            .all()
        )

    @classmethod
    def link_evidence_to_exercise(
        cls,
        db: Session,
        organization_id: int,
        exercise_id: int,
        data: ResilienceEvidenceLinkCreate,
        user_id: int,
    ) -> ResilienceEvidenceLink:
        ex = cls._get_exercise_or_404(db, organization_id, exercise_id)
        if ex.status in (ExerciseStatusEnum.REVIEWED, ExerciseStatusEnum.CANCELLED):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot attach new evidence to an exercise in {ex.status.value} status.",
            )

        ev = cls._validate_evidence_item_for_link(db, organization_id, data.evidence_item_id)

        existing = (
            db.query(ResilienceEvidenceLink)
            .filter(
                ResilienceEvidenceLink.organization_id == organization_id,
                ResilienceEvidenceLink.exercise_id == ex.id,
                ResilienceEvidenceLink.evidence_item_id == ev.id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"EvidenceItem #{ev.id} is already linked to Resilience Exercise #{ex.id}.",
            )

        link = ResilienceEvidenceLink(
            organization_id=organization_id,
            continuity_plan_id=None,
            exercise_id=ex.id,
            evidence_item_id=ev.id,
            evidence_type_context=data.evidence_type_context,
            evidence_sha256_snapshot=ev.sha256_hash,
            notes=data.notes,
            linked_by_user_id=user_id,
        )
        db.add(link)
        db.commit()
        db.refresh(link)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="resilience_evidence.linked",
            resource_type="resilience_evidence_link",
            resource_id=str(link.id),
            actor_email=cls._get_actor_email(db, user_id),
            actor_id=user_id,
            details={
                "subject_type": "resilience_exercise",
                "subject_id": ex.id,
                "evidence_item_id": ev.id,
                "evidence_sha256_snapshot": link.evidence_sha256_snapshot,
            },
        )
        return link

    @classmethod
    def _verify_exercise_evidence_integrity(
        cls,
        db: Session,
        organization_id: int,
        ex: ResilienceExercise,
    ) -> List[ResilienceEvidenceLink]:
        links = (
            db.query(ResilienceEvidenceLink)
            .filter(
                ResilienceEvidenceLink.organization_id == organization_id,
                ResilienceEvidenceLink.exercise_id == ex.id,
            )
            .order_by(ResilienceEvidenceLink.id.asc())
            .all()
        )
        for link in links:
            ev = (
                db.query(EvidenceItem)
                .filter(
                    EvidenceItem.id == link.evidence_item_id,
                    EvidenceItem.organization_id == organization_id,
                )
                .first()
            )
            if not ev:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Linked EvidenceItem #{link.evidence_item_id} no longer exists.",
                )
            if ev.sha256_hash != link.evidence_sha256_snapshot:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Linked evidence integrity check failed for EvidenceItem #{ev.id}: SHA-256 hash mismatch.",
                )
            if ev.status in (EvidenceStatusEnum.REJECTED, EvidenceStatusEnum.SUPERSEDED):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Linked EvidenceItem #{ev.id} has invalid status {ev.status.value}.",
                )
        return links

    @classmethod
    def start_exercise(
        cls,
        db: Session,
        organization_id: int,
        exercise_id: int,
        data: Optional[ResilienceExerciseStartRequest],
        user_id: int,
    ) -> ResilienceExercise:
        ex = cls._get_exercise_or_404(db, organization_id, exercise_id)
        if ex.status != ExerciseStatusEnum.PLANNED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Only PLANNED exercises can be started (current status: {ex.status.value}).",
            )

        now_utc = datetime.now(timezone.utc)
        started_at = data.started_at if (data and data.started_at) else now_utc

        ex.status = ExerciseStatusEnum.IN_PROGRESS
        ex.started_at = started_at
        ex.executed_by_user_id = user_id

        db.commit()
        db.refresh(ex)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="resilience_exercise.started",
            resource_type="resilience_exercise",
            resource_id=str(ex.id),
            actor_email=cls._get_actor_email(db, user_id),
            actor_id=user_id,
            details={
                "exercise_code": ex.exercise_code,
                "started_at": ex.started_at.isoformat() if ex.started_at else None,
            },
        )
        return ex

    @classmethod
    def complete_exercise(
        cls,
        db: Session,
        organization_id: int,
        exercise_id: int,
        data: ResilienceExerciseCompleteRequest,
        user_id: int,
    ) -> ResilienceExercise:
        ex = cls._get_exercise_or_404(db, organization_id, exercise_id)
        if ex.status != ExerciseStatusEnum.IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Only IN_PROGRESS exercises can be completed (current status: {ex.status.value}).",
            )

        now_utc = datetime.now(timezone.utc)
        completed_at = data.completed_at if data.completed_at else now_utc

        if ex.started_at is not None:
            s_dt = ex.started_at if ex.started_at.tzinfo else ex.started_at.replace(tzinfo=timezone.utc)
            c_dt = completed_at if completed_at.tzinfo else completed_at.replace(tzinfo=timezone.utc)
            if c_dt < s_dt:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid exercise chronology: completed_at cannot precede started_at.",
                )

        # Verify evidence links and enforce technical exercise evidence gate
        links = cls._verify_exercise_evidence_integrity(db, organization_id, ex)
        technical_types = {
            ExerciseTypeEnum.FUNCTIONAL_FAILOVER,
            ExerciseTypeEnum.FULL_INTERRUPTION,
            ExerciseTypeEnum.BACKUP_RESTORATION,
            ExerciseTypeEnum.THIRD_PARTY_RESILIENCE,
        }
        if ex.exercise_type in technical_types and len(links) < 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Exercise type {ex.exercise_type.value} requires at least one valid linked "
                    "EvidenceItem before completion."
                ),
            )

        actual_rto = round(float(data.actual_rto_hours), 4)
        actual_rpo = round(float(data.actual_rpo_hours), 4)
        target_rto = round(float(ex.target_rto_hours_snapshot), 4)
        target_rpo = round(float(ex.target_rpo_hours_snapshot), 4)
        target_mtd = round(float(ex.target_mtd_hours_snapshot), 4)

        rto_variance = round(actual_rto - target_rto, 4)
        rpo_variance = round(actual_rpo - target_rpo, 4)

        rto_breached = actual_rto > target_rto
        rpo_breached = actual_rpo > target_rpo
        mtd_breached = actual_rto > target_mtd

        outcome = classify_exercise_outcome(
            rto_breached=rto_breached,
            rpo_breached=rpo_breached,
            mtd_breached=mtd_breached,
            control_deficiency_observed=bool(data.control_deficiency_observed),
            minor_exceptions_noted=bool(data.minor_exceptions_noted),
        )

        ex.actual_rto_hours = actual_rto
        ex.actual_rpo_hours = actual_rpo
        ex.rto_variance_hours = rto_variance
        ex.rpo_variance_hours = rpo_variance
        ex.rto_breached = rto_breached
        ex.rpo_breached = rpo_breached
        ex.mtd_breached = mtd_breached
        ex.control_deficiency_observed = bool(data.control_deficiency_observed)
        ex.outcome = outcome
        ex.lessons_learned = data.lessons_learned
        ex.executive_summary = data.executive_summary
        ex.completed_at = completed_at
        ex.executed_by_user_id = user_id
        ex.status = ExerciseStatusEnum.COMPLETED
        ex.result_hash_sha256 = compute_exercise_result_hash_sha256(ex, links)

        db.commit()
        db.refresh(ex)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="resilience_exercise.completed",
            resource_type="resilience_exercise",
            resource_id=str(ex.id),
            actor_email=cls._get_actor_email(db, user_id),
            actor_id=user_id,
            details={
                "exercise_code": ex.exercise_code,
                "actual_rto_hours": ex.actual_rto_hours,
                "actual_rpo_hours": ex.actual_rpo_hours,
                "rto_variance_hours": ex.rto_variance_hours,
                "rpo_variance_hours": ex.rpo_variance_hours,
                "rto_breached": ex.rto_breached,
                "rpo_breached": ex.rpo_breached,
                "mtd_breached": ex.mtd_breached,
                "outcome": ex.outcome.value,
                "result_hash_sha256": ex.result_hash_sha256,
            },
        )
        return ex

    @classmethod
    def review_exercise(
        cls,
        db: Session,
        organization_id: int,
        exercise_id: int,
        data: Optional[ResilienceExerciseReviewRequest],
        user_id: int,
    ) -> ResilienceExercise:
        ex = cls._get_exercise_or_404(db, organization_id, exercise_id)
        if ex.status != ExerciseStatusEnum.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Only COMPLETED exercises can be reviewed (current status: {ex.status.value}).",
            )

        # Four-Eyes SoD: executor cannot review their own exercise
        if ex.executed_by_user_id == user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Four-eyes governance violation: exercise executor cannot review their own Resilience Exercise.",
            )

        links = cls._verify_exercise_evidence_integrity(db, organization_id, ex)

        # Verify result hash was not tampered with since completion
        expected_pre_review_hash = compute_exercise_result_hash_sha256(ex, links)
        if ex.result_hash_sha256 and ex.result_hash_sha256 != expected_pre_review_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Exercise result integrity check failed: result_hash_sha256 mismatch.",
            )

        # Failed / breached exercises must have a linked Finding or RemediationPlan before REVIEWED
        failure_outcomes = {
            ExerciseOutcomeEnum.FAIL_RTO_BREACH,
            ExerciseOutcomeEnum.FAIL_RPO_BREACH,
            ExerciseOutcomeEnum.FAIL_MTD_BREACH,
            ExerciseOutcomeEnum.FAIL_CONTROL_DEFICIENCY,
        }
        if (
            ex.rto_breached
            or ex.rpo_breached
            or ex.mtd_breached
            or ex.outcome in failure_outcomes
        ):
            if ex.finding_id is None and ex.remediation_plan_id is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        "Failed or breached Resilience Exercises must be escalated to a canonical "
                        "Finding or RemediationPlan before review sign-off."
                    ),
                )

        now_utc = datetime.now(timezone.utc)
        ex.status = ExerciseStatusEnum.REVIEWED
        ex.reviewed_by_user_id = user_id
        ex.reviewed_at = now_utc
        if data and data.review_notes is not None:
            ex.review_notes = data.review_notes
        ex.result_hash_sha256 = compute_exercise_result_hash_sha256(ex, links)

        db.commit()
        db.refresh(ex)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="resilience_exercise.reviewed",
            resource_type="resilience_exercise",
            resource_id=str(ex.id),
            actor_email=cls._get_actor_email(db, user_id),
            actor_id=user_id,
            details={
                "exercise_code": ex.exercise_code,
                "outcome": ex.outcome.value if ex.outcome else None,
                "reviewed_by_user_id": user_id,
                "result_hash_sha256": ex.result_hash_sha256,
            },
        )
        return ex

    @classmethod
    def cancel_exercise(
        cls,
        db: Session,
        organization_id: int,
        exercise_id: int,
        data: Optional[ResilienceExerciseCancelRequest],
        user_id: int,
    ) -> ResilienceExercise:
        ex = cls._get_exercise_or_404(db, organization_id, exercise_id)
        if ex.status not in (ExerciseStatusEnum.PLANNED, ExerciseStatusEnum.IN_PROGRESS):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot cancel an exercise in {ex.status.value} status. Completed or reviewed exercises are immutable.",
            )

        ex.status = ExerciseStatusEnum.CANCELLED
        if data and data.reason:
            ex.review_notes = f"Cancelled: {data.reason}"

        db.commit()
        db.refresh(ex)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="resilience_exercise.cancelled",
            resource_type="resilience_exercise",
            resource_id=str(ex.id),
            actor_email=cls._get_actor_email(db, user_id),
            actor_id=user_id,
            details={
                "exercise_code": ex.exercise_code,
                "reason": data.reason if data else None,
            },
        )
        return ex

    # ── 8. Closed-Loop Escalation to Finding, RemediationPlan & Risk (Batch 5)

    @classmethod
    def escalate_exercise_deficiency(
        cls,
        db: Session,
        organization_id: int,
        exercise_id: int,
        data: ExerciseEscalationRequest,
        user_id: int,
    ) -> ResilienceExercise:
        ex = cls._get_exercise_or_404(db, organization_id, exercise_id)
        if ex.status not in (ExerciseStatusEnum.COMPLETED, ExerciseStatusEnum.REVIEWED):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Only COMPLETED or REVIEWED exercises can be escalated (current status: {ex.status.value}).",
            )

        process = cls.get_business_process(db, organization_id, ex.process_id)
        now_utc = datetime.now(timezone.utc)

        # ── Step A: Resolve or Create Canonical Finding ─────────────────────
        resolved_finding: Optional[Finding] = None
        if data.existing_finding_id is not None:
            if ex.finding_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Exercise already has an escalated finding linked.",
                )
            f_obj = (
                db.query(Finding)
                .filter(
                    Finding.id == data.existing_finding_id,
                    Finding.organization_id == organization_id,
                )
                .first()
            )
            if not f_obj:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Finding #{data.existing_finding_id} not found in tenant.",
                )
            resolved_finding = f_obj
            ex.finding_id = f_obj.id
        elif data.create_finding:
            if ex.finding_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Exercise already has an escalated finding linked.",
                )
            # Resolve governing organization_control_id
            ctrl_id: Optional[int] = None
            if data.organization_control_id is not None:
                ctrl = (
                    db.query(OrganizationControl)
                    .filter(
                        OrganizationControl.id == data.organization_control_id,
                        OrganizationControl.organization_id == organization_id,
                    )
                    .first()
                )
                if not ctrl:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"OrganizationControl #{data.organization_control_id} not found in tenant.",
                    )
                ctrl_id = ctrl.id
            else:
                ctrl_dep = (
                    db.query(ProcessDependency)
                    .filter(
                        ProcessDependency.organization_id == organization_id,
                        ProcessDependency.process_id == ex.process_id,
                        ProcessDependency.dependency_type == DependencyTypeEnum.CONTROL,
                    )
                    .order_by(
                        ProcessDependency.recovery_priority_order.asc(),
                        ProcessDependency.id.asc(),
                    )
                    .first()
                )
                if ctrl_dep:
                    ctrl_id = ctrl_dep.organization_control_id or ctrl_dep.dependency_id

            if ctrl_id is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        "Cannot create Finding without organization_control_id: provide "
                        "organization_control_id in request or link a CONTROL dependency to the business process."
                    ),
                )

            if ex.mtd_breached:
                default_sev = FindingSeverityEnum.CRITICAL
                impact, likelihood = 5, 4
                risk_score, risk_band = 20, "CRITICAL"
                default_ftype = FindingTypeEnum.PROCESS_GAP
            elif ex.rto_breached or ex.rpo_breached:
                default_sev = FindingSeverityEnum.HIGH
                impact, likelihood = 4, 4
                risk_score, risk_band = 16, "HIGH"
                default_ftype = FindingTypeEnum.PROCESS_GAP
            else:
                default_sev = FindingSeverityEnum.MEDIUM
                impact, likelihood = 3, 3
                risk_score, risk_band = 9, "MODERATE"
                default_ftype = FindingTypeEnum.CONTROL_GAP

            f_title = (
                data.finding_title
                or f"Resilience Exercise Deficiency: {ex.exercise_code} ({process.name})"
            )
            f_desc = (
                data.finding_description
                or (
                    f"Empirical resilience exercise '{ex.title}' ({ex.exercise_code}) resulted in "
                    f"outcome {ex.outcome.value if ex.outcome else 'DEFICIENCY'}. "
                    f"Target RTO={ex.target_rto_hours_snapshot}h, Actual RTO={ex.actual_rto_hours}h; "
                    f"Target RPO={ex.target_rpo_hours_snapshot}h, Actual RPO={ex.actual_rpo_hours}h."
                )
            )
            f_rec = (
                data.finding_recommendation
                or "Update continuity runbook, remediate bottleneck recovery steps, and re-test failover within SLA."
            )

            new_finding = Finding(
                organization_id=organization_id,
                organization_control_id=ctrl_id,
                title=f_title,
                description=f_desc,
                finding_type=data.finding_type or default_ftype,
                severity=data.finding_severity or default_sev,
                impact=impact,
                likelihood=likelihood,
                risk_score=risk_score,
                risk_band=risk_band,
                recommendation=f_rec,
                root_cause=data.root_cause_analysis or ex.lessons_learned,
                owner_id=process.owner_id or user_id,
                status=FindingStatusEnum.OPEN,
                created_by_id=user_id,
            )
            db.add(new_finding)
            db.flush()
            resolved_finding = new_finding
            ex.finding_id = new_finding.id
        elif ex.finding_id is not None:
            resolved_finding = (
                db.query(Finding)
                .filter(Finding.id == ex.finding_id, Finding.organization_id == organization_id)
                .first()
            )

        # Propagate exercise evidence links to FindingEvidence
        if resolved_finding is not None:
            ex_links = (
                db.query(ResilienceEvidenceLink)
                .filter(
                    ResilienceEvidenceLink.organization_id == organization_id,
                    ResilienceEvidenceLink.exercise_id == ex.id,
                )
                .all()
            )
            for link in ex_links:
                existing_fe = (
                    db.query(FindingEvidence)
                    .filter(
                        FindingEvidence.finding_id == resolved_finding.id,
                        FindingEvidence.evidence_id == link.evidence_item_id,
                    )
                    .first()
                )
                if not existing_fe:
                    db.add(
                        FindingEvidence(
                            organization_id=organization_id,
                            finding_id=resolved_finding.id,
                            evidence_id=link.evidence_item_id,
                            created_by_id=user_id,
                        )
                    )

        # ── Step B: Resolve or Create Canonical RemediationPlan ─────────────
        if data.existing_remediation_plan_id is not None:
            if ex.remediation_plan_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Exercise already has a RemediationPlan linked.",
                )
            rem_obj = (
                db.query(RemediationPlan)
                .filter(
                    RemediationPlan.id == data.existing_remediation_plan_id,
                    RemediationPlan.organization_id == organization_id,
                )
                .first()
            )
            if not rem_obj:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"RemediationPlan #{data.existing_remediation_plan_id} not found in tenant.",
                )
            ex.remediation_plan_id = rem_obj.id
        elif data.create_remediation_plan:
            if ex.remediation_plan_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Exercise already has a RemediationPlan linked.",
                )
            if resolved_finding is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Creating a RemediationPlan requires a linked Finding (set create_finding=True or existing_finding_id).",
                )
            owner_user_id = data.remediation_owner_user_id or process.owner_id or user_id
            owner_user = (
                db.query(User)
                .filter(User.id == owner_user_id, User.organization_id == organization_id)
                .first()
            )
            if not owner_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Remediation owner User #{owner_user_id} not found in tenant.",
                )

            if ex.mtd_breached:
                rem_sev = RemediationSeverityEnum.CRITICAL
                default_due = now_utc + timedelta(days=14)
            elif ex.rto_breached or ex.rpo_breached:
                rem_sev = RemediationSeverityEnum.HIGH
                default_due = now_utc + timedelta(days=30)
            else:
                rem_sev = RemediationSeverityEnum.MEDIUM
                default_due = now_utc + timedelta(days=45)

            plan_code = f"CAPA-RES-{ex.id}-{int(now_utc.timestamp())}"
            rem_plan = RemediationPlan(
                organization_id=organization_id,
                plan_code=plan_code,
                title=(
                    data.remediation_title
                    or f"Remediate Resilience Exercise Deficiency: {ex.exercise_code}"
                ),
                problem_statement=(
                    data.remediation_description
                    or ex.lessons_learned
                    or ex.scenario_description
                ),
                root_cause_classification=(
                    data.root_cause_classification
                    or RemediationRootCauseClassificationEnum.CONTROL_DEFICIENCY
                ),
                source_type=RemediationSourceTypeEnum.FINDING,
                finding_id=resolved_finding.id,
                severity=rem_sev,
                status=RemediationStatusEnum.DRAFT,
                plan_owner_id=owner_user.id,
                target_completion_at=data.remediation_due_date or default_due,
            )
            db.add(rem_plan)
            db.flush()
            ex.remediation_plan_id = rem_plan.id
            resolved_finding.status = FindingStatusEnum.IN_REMEDIATION

        # ── Step C: Resolve or Create Canonical Risk & RiskFindingLink ──────
        resolved_risk_id: Optional[int] = ex.risk_id
        if data.existing_risk_id is not None:
            if ex.risk_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Exercise already has a Risk linked.",
                )
            r_obj = (
                db.query(Risk)
                .filter(
                    Risk.id == data.existing_risk_id,
                    Risk.organization_id == organization_id,
                )
                .first()
            )
            if not r_obj:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Risk #{data.existing_risk_id} not found in tenant.",
                )
            ex.risk_id = r_obj.id
            resolved_risk_id = r_obj.id
        elif data.create_risk:
            if ex.risk_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Exercise already has a Risk linked.",
                )
            inh_imp = 5 if ex.mtd_breached else (4 if (ex.rto_breached or ex.rpo_breached) else 3)
            inh_lik = 4 if (ex.rto_breached or ex.rpo_breached) else 3
            inh_score = inh_imp * inh_lik
            inh_band = "CRITICAL" if inh_score >= 20 else ("HIGH" if inh_score >= 12 else "MODERATE")

            new_risk = Risk(
                organization_id=organization_id,
                title=(
                    data.risk_title
                    or f"Operational Resilience Recovery Gap: {process.name} ({ex.exercise_code})"
                ),
                description=ex.scenario_description,
                risk_category=RiskCategoryEnum.OPERATIONAL,
                risk_source=RiskSourceEnum.BUSINESS_OPERATION,
                owner_id=process.owner_id or user_id,
                inherent_impact=inh_imp,
                inherent_likelihood=inh_lik,
                inherent_score=inh_score,
                inherent_band=inh_band,
                residual_impact=inh_imp,
                residual_likelihood=inh_lik,
                residual_score=inh_score,
                residual_band=inh_band,
                status=RiskStatusEnum.IDENTIFIED,
                created_by_id=user_id,
            )
            db.add(new_risk)
            db.flush()
            ex.risk_id = new_risk.id
            resolved_risk_id = new_risk.id

        if resolved_risk_id is not None and ex.finding_id is not None:
            existing_rfl = (
                db.query(RiskFindingLink)
                .filter(
                    RiskFindingLink.risk_id == resolved_risk_id,
                    RiskFindingLink.finding_id == ex.finding_id,
                )
                .first()
            )
            if not existing_rfl:
                db.add(
                    RiskFindingLink(
                        organization_id=organization_id,
                        risk_id=resolved_risk_id,
                        finding_id=ex.finding_id,
                        created_by_id=user_id,
                    )
                )

        db.commit()
        db.refresh(ex)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="resilience_exercise.escalated",
            resource_type="resilience_exercise",
            resource_id=str(ex.id),
            actor_email=cls._get_actor_email(db, user_id),
            actor_id=user_id,
            details={
                "exercise_code": ex.exercise_code,
                "finding_id": ex.finding_id,
                "remediation_plan_id": ex.remediation_plan_id,
                "risk_id": ex.risk_id,
            },
        )
        return ex

    # ── 9. Process Impact Summary & Resilience Dashboard Telemetry (Batch 5) ─

    @classmethod
    def get_process_impact_summary(
        cls,
        db: Session,
        organization_id: int,
        process_id: int,
    ) -> ProcessImpactSummaryResponse:
        process = cls.get_business_process(db, organization_id, process_id)
        active_bia = getattr(process, "active_bia", None)
        dep_health = cls.get_process_dependency_health(db, organization_id, process_id)

        projected_24h_loss = 0.0
        if active_bia:
            loss_24 = calculate_projected_outage_loss(
                duration_hours=24.0,
                hourly_downtime_cost=active_bia.hourly_downtime_cost,
                fixed_outage_cost=active_bia.fixed_outage_cost,
            )
            projected_24h_loss = loss_24["total_projected_loss"]

        active_plan = (
            db.query(ContinuityPlan)
            .filter(
                ContinuityPlan.organization_id == organization_id,
                ContinuityPlan.process_id == process.id,
                ContinuityPlan.status == ContinuityPlanStatusEnum.APPROVED,
            )
            .first()
        )

        latest_ex = (
            db.query(ResilienceExercise)
            .filter(
                ResilienceExercise.organization_id == organization_id,
                ResilienceExercise.process_id == process.id,
                ResilienceExercise.status.in_(
                    [ExerciseStatusEnum.COMPLETED, ExerciseStatusEnum.REVIEWED]
                ),
            )
            .order_by(ResilienceExercise.completed_at.desc(), ResilienceExercise.id.desc())
            .first()
        )

        return ProcessImpactSummaryResponse(
            process_id=process.id,
            process_name=process.name,
            criticality_tier=process.criticality_tier,
            has_active_bia=active_bia is not None,
            active_bia_id=active_bia.id if active_bia else None,
            rto_hours=active_bia.rto_hours if active_bia else None,
            rpo_hours=active_bia.rpo_hours if active_bia else None,
            mtd_hours=active_bia.mtd_hours if active_bia else None,
            projected_24h_loss=projected_24h_loss,
            total_dependencies=dep_health.total_dependencies,
            spof_count=dep_health.spof_count,
            unmitigated_spof_count=dep_health.unmitigated_spof_count,
            dependency_health_score=dep_health.dependency_health_score,
            active_continuity_plan_id=active_plan.id if active_plan else None,
            active_continuity_plan_version=active_plan.version_label if active_plan else None,
            latest_exercise_id=latest_ex.id if latest_ex else None,
            latest_exercise_outcome=(
                latest_ex.outcome.value if (latest_ex and latest_ex.outcome) else None
            ),
            latest_actual_rto_hours=latest_ex.actual_rto_hours if latest_ex else None,
            latest_actual_rpo_hours=latest_ex.actual_rpo_hours if latest_ex else None,
        )

    @classmethod
    def get_resilience_dashboard(
        cls,
        db: Session,
        organization_id: int,
    ) -> ResilienceDashboardResponse:
        processes = (
            db.query(BusinessProcess)
            .filter(BusinessProcess.organization_id == organization_id)
            .all()
        )
        total_processes = len(processes)
        tier_breakdown: Dict[str, int] = {
            CriticalityTierEnum.TIER_1.value: 0,
            CriticalityTierEnum.TIER_2.value: 0,
            CriticalityTierEnum.TIER_3.value: 0,
            CriticalityTierEnum.TIER_4.value: 0,
        }
        tier_1_processes = 0
        processes_with_approved_bia = 0
        processes_with_approved_plan = 0
        max_24h_financial_exposure = 0.0
        total_dependencies = 0
        spof_count = 0
        unmitigated_spof_count = 0
        health_scores: List[float] = []

        for p in processes:
            tier_breakdown[p.criticality_tier.value] = (
                tier_breakdown.get(p.criticality_tier.value, 0) + 1
            )
            if p.criticality_tier == CriticalityTierEnum.TIER_1:
                tier_1_processes += 1

            active_bia = (
                db.query(BusinessImpactAnalysis)
                .filter(
                    BusinessImpactAnalysis.organization_id == organization_id,
                    BusinessImpactAnalysis.process_id == p.id,
                    BusinessImpactAnalysis.status == BiaStatusEnum.ACTIVE,
                )
                .first()
            )
            if active_bia:
                processes_with_approved_bia += 1
                loss_24 = calculate_projected_outage_loss(
                    duration_hours=24.0,
                    hourly_downtime_cost=active_bia.hourly_downtime_cost,
                    fixed_outage_cost=active_bia.fixed_outage_cost,
                )["total_projected_loss"]
                if loss_24 > max_24h_financial_exposure:
                    max_24h_financial_exposure = loss_24

            approved_plan = (
                db.query(ContinuityPlan)
                .filter(
                    ContinuityPlan.organization_id == organization_id,
                    ContinuityPlan.process_id == p.id,
                    ContinuityPlan.status == ContinuityPlanStatusEnum.APPROVED,
                )
                .first()
            )
            if approved_plan:
                processes_with_approved_plan += 1

            dep_health = cls.get_process_dependency_health(db, organization_id, p.id)
            total_dependencies += dep_health.total_dependencies
            spof_count += dep_health.spof_count
            unmitigated_spof_count += dep_health.unmitigated_spof_count
            health_scores.append(dep_health.dependency_health_score)

        bia_coverage_pct = (
            round((processes_with_approved_bia / total_processes) * 100.0, 2)
            if total_processes > 0
            else 0.0
        )
        continuity_plan_coverage_pct = (
            round((processes_with_approved_plan / total_processes) * 100.0, 2)
            if total_processes > 0
            else 0.0
        )
        avg_dep_health = (
            round(sum(health_scores) / len(health_scores), 2)
            if health_scores
            else 100.0
        )

        now_utc = datetime.now(timezone.utc)
        approved_plans = (
            db.query(ContinuityPlan)
            .filter(
                ContinuityPlan.organization_id == organization_id,
                ContinuityPlan.status == ContinuityPlanStatusEnum.APPROVED,
            )
            .all()
        )
        overdue_reviews = 0
        for ap in approved_plans:
            if ap.next_review_due_at is not None:
                due_dt = (
                    ap.next_review_due_at
                    if ap.next_review_due_at.tzinfo
                    else ap.next_review_due_at.replace(tzinfo=timezone.utc)
                )
                if due_dt < now_utc:
                    overdue_reviews += 1

        exercises = (
            db.query(ResilienceExercise)
            .filter(ResilienceExercise.organization_id == organization_id)
            .all()
        )
        total_exercises = len(exercises)
        completed_or_reviewed = [
            e
            for e in exercises
            if e.status in (ExerciseStatusEnum.COMPLETED, ExerciseStatusEnum.REVIEWED)
        ]
        completed_count = len(completed_or_reviewed)
        passed_count = sum(
            1
            for e in completed_or_reviewed
            if e.outcome
            in (ExerciseOutcomeEnum.PASS, ExerciseOutcomeEnum.PASS_WITH_MINOR_EXCEPTIONS)
        )
        exercise_pass_rate_pct = (
            round((passed_count / completed_count) * 100.0, 2)
            if completed_count > 0
            else (100.0 if total_processes == 0 else 0.0)
        )

        rto_breach_count = sum(1 for e in completed_or_reviewed if e.rto_breached)
        rpo_breach_count = sum(1 for e in completed_or_reviewed if e.rpo_breached)
        mtd_breach_count = sum(1 for e in completed_or_reviewed if e.mtd_breached)

        resilience_assurance_score = round(
            (0.30 * bia_coverage_pct)
            + (0.30 * continuity_plan_coverage_pct)
            + (0.25 * exercise_pass_rate_pct)
            + (0.15 * avg_dep_health),
            2,
        )

        return ResilienceDashboardResponse(
            total_processes=total_processes,
            active_processes=total_processes,
            tier_1_processes=tier_1_processes,
            processes_with_approved_bia=processes_with_approved_bia,
            bia_coverage_pct=bia_coverage_pct,
            total_dependencies=total_dependencies,
            single_point_of_failure_count=spof_count,
            max_24h_financial_exposure=round(max_24h_financial_exposure, 2),
            tier_breakdown=tier_breakdown,
            processes_with_approved_continuity_plan=processes_with_approved_plan,
            continuity_plan_coverage_pct=continuity_plan_coverage_pct,
            overdue_continuity_plan_reviews=overdue_reviews,
            total_exercises=total_exercises,
            completed_or_reviewed_exercises=completed_count,
            exercise_pass_rate_pct=exercise_pass_rate_pct,
            rto_breach_exercise_count=rto_breach_count,
            rpo_breach_exercise_count=rpo_breach_count,
            mtd_breach_exercise_count=mtd_breach_count,
            unmitigated_spof_count=unmitigated_spof_count,
            average_dependency_health_score=avg_dep_health,
            resilience_assurance_score=resilience_assurance_score,
        )
