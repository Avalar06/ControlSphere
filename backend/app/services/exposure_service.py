from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.exposure import (
    AssetTypeEnum,
    EnvironmentEnum,
    ExceptionApprovalStatusEnum,
    ExposureAssetLink,
    ExposureException,
    ExposureSeverityEnum,
    ExposureStatusEnum,
    VulnerabilityExposure,
)
from app.models.resilience import BusinessProcess, CriticalityTierEnum
from app.models.tprm import Vendor
from app.models.control import OrganizationControl
from app.models.remediation import (
    RemediationPlan,
    RemediationStatusEnum,
    RemediationSeverityEnum,
    RemediationSourceTypeEnum,
    RemediationRootCauseClassificationEnum,
)
from app.schemas.exposure import (
    ExposureAssetLinkCreate,
    ExposureExceptionCreate,
    ExposureExceptionReviewRequest,
    VulnerabilityExposureCreate,
    VulnerabilityExposureUpdate,
)
from app.services.audit_service import AuditService


class ExposureService:
    """Authoritative Domain Engine for Threat Exposure & Vulnerability Governance (EXPOSURE-GRC)."""

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Deterministic Mathematical Calculations
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def calculate_default_sla(
        severity: ExposureSeverityEnum,
        cisa_kev: bool = False,
        base_time: Optional[datetime] = None,
    ) -> datetime:
        """Determines server-authoritative remediation SLA due date based on severity and KEV status."""
        start = base_time or datetime.now(timezone.utc)
        if severity == ExposureSeverityEnum.CRITICAL:
            days = 7 if cisa_kev else 14
        elif severity == ExposureSeverityEnum.HIGH:
            days = 30
        elif severity == ExposureSeverityEnum.MEDIUM:
            days = 60
        else:  # LOW or INFORMATIONAL
            days = 90
        return start + timedelta(days=days)

    @staticmethod
    def calculate_exposure_index(
        cvss_score: float,
        epss_score: float = 0.0,
        cisa_kev: bool = False,
        highest_process_tier: Optional[CriticalityTierEnum] = None,
    ) -> Tuple[float, float, float]:
        """Calculates deterministic Exposure Index:
        Base Score = (CVSS * 0.40) + (EPSS * 100 * 0.35) + (25.0 if KEV else 0.0)
        Blast Radius Multiplier = 1.25 (Tier 1), 1.15 (Tier 2), 1.05 (Tier 3), 1.00 (Other)
        Returns: (base_score, blast_radius_multiplier, final_exposure_index)
        """
        # Validate input boundaries
        if not (0.0 <= cvss_score <= 10.0):
            raise ValueError(f"CVSS score must be between 0.0 and 10.0 (got {cvss_score}).")
        if not (0.0 <= epss_score <= 1.0):
            raise ValueError(f"EPSS score must be between 0.0 and 1.0 (got {epss_score}).")

        base_score = (cvss_score * 0.40) + (epss_score * 100.0 * 0.35) + (25.0 if cisa_kev else 0.0)
        base_score = round(base_score, 4)

        if highest_process_tier == CriticalityTierEnum.TIER_1:
            multiplier = 1.25
        elif highest_process_tier == CriticalityTierEnum.TIER_2:
            multiplier = 1.15
        elif highest_process_tier == CriticalityTierEnum.TIER_3:
            multiplier = 1.05
        else:
            multiplier = 1.00

        final_index = min(100.0, round(base_score * multiplier, 2))
        return base_score, multiplier, final_index

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Exposure Management (CRUD & Lifecycle)
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def create_exposure(
        cls,
        db: Session,
        organization_id: int,
        data: VulnerabilityExposureCreate,
        actor_id: Optional[int] = None,
        actor_email: str = "system",
    ) -> VulnerabilityExposure:
        """Creates a new vulnerability exposure record with server-authoritative SLA and index."""
        now = datetime.now(timezone.utc)
        discovered_at = data.discovered_at or now

        # Server-authoritative SLA determination
        sla_due = data.remediation_sla_due or cls.calculate_default_sla(
            severity=data.severity,
            cisa_kev=data.cisa_kev,
            base_time=discovered_at,
        )

        # Initial exposure index (without asset links)
        _, _, initial_index = cls.calculate_exposure_index(
            cvss_score=data.cvss_score,
            epss_score=data.epss_score,
            cisa_kev=data.cisa_kev,
            highest_process_tier=None,
        )

        exposure = VulnerabilityExposure(
            organization_id=organization_id,
            cve_id=data.cve_id.strip().upper(),
            cwe_id=data.cwe_id.strip().upper() if data.cwe_id else None,
            title=data.title.strip(),
            description=data.description.strip() if data.description else None,
            cvss_score=data.cvss_score,
            cvss_vector=data.cvss_vector,
            epss_score=data.epss_score,
            cisa_kev=data.cisa_kev,
            severity=data.severity,
            status=ExposureStatusEnum.OPEN,
            exposure_index=initial_index,
            remediation_sla_due=sla_due,
            discovered_at=discovered_at,
            created_at=now,
            updated_at=now,
        )
        db.add(exposure)
        db.commit()
        db.refresh(exposure)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="EXPOSURE_INGESTED",
            resource_type="VulnerabilityExposure",
            actor_email=actor_email,
            actor_id=actor_id,
            resource_id=str(exposure.id),
            details={
                "cve_id": exposure.cve_id,
                "cvss_score": exposure.cvss_score,
                "epss_score": exposure.epss_score,
                "cisa_kev": exposure.cisa_kev,
                "severity": exposure.severity.value,
                "exposure_index": exposure.exposure_index,
                "remediation_sla_due": exposure.remediation_sla_due.isoformat(),
            },
        )
        return exposure

    @staticmethod
    def get_exposure(
        db: Session,
        organization_id: int,
        exposure_id: int,
    ) -> Optional[VulnerabilityExposure]:
        """Retrieves a single exposure strictly scoped to the tenant organization."""
        return (
            db.query(VulnerabilityExposure)
            .filter(
                VulnerabilityExposure.id == exposure_id,
                VulnerabilityExposure.organization_id == organization_id,
            )
            .first()
        )

    @staticmethod
    def list_exposures(
        db: Session,
        organization_id: int,
        severity: Optional[ExposureSeverityEnum] = None,
        status: Optional[ExposureStatusEnum] = None,
        cisa_kev: Optional[bool] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[VulnerabilityExposure]:
        """Lists exposures for the tenant with multi-attribute filtering."""
        query = db.query(VulnerabilityExposure).filter(
            VulnerabilityExposure.organization_id == organization_id
        )

        if severity:
            query = query.filter(VulnerabilityExposure.severity == severity)
        if status:
            query = query.filter(VulnerabilityExposure.status == status)
        if cisa_kev is not None:
            query = query.filter(VulnerabilityExposure.cisa_kev == cisa_kev)
        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                (VulnerabilityExposure.cve_id.ilike(term))
                | (VulnerabilityExposure.title.ilike(term))
                | (VulnerabilityExposure.cwe_id.ilike(term))
            )

        return query.order_by(VulnerabilityExposure.exposure_index.desc(), VulnerabilityExposure.id.desc()).offset(skip).limit(limit).all()

    @classmethod
    def update_exposure(
        cls,
        db: Session,
        organization_id: int,
        exposure_id: int,
        data: VulnerabilityExposureUpdate,
        actor_id: Optional[int] = None,
        actor_email: str = "system",
    ) -> VulnerabilityExposure:
        """Updates exposure telemetry and recalculates authoritative index."""
        exposure = cls.get_exposure(db, organization_id, exposure_id)
        if not exposure:
            raise ValueError(f"Vulnerability exposure #{exposure_id} not found.")

        # Immutability Check: Resolved exposures are locked
        if exposure.status == ExposureStatusEnum.RESOLVED:
            raise ValueError("Resolved exposure records are immutable and cannot be modified.")

        update_dict = data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(exposure, key, value)

        # Recalculate Exposure Index
        highest_tier = cls._get_highest_process_tier(exposure)
        _, _, new_index = cls.calculate_exposure_index(
            cvss_score=exposure.cvss_score,
            epss_score=exposure.epss_score,
            cisa_kev=exposure.cisa_kev,
            highest_process_tier=highest_tier,
        )
        exposure.exposure_index = new_index
        exposure.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(exposure)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="EXPOSURE_UPDATED",
            resource_type="VulnerabilityExposure",
            actor_email=actor_email,
            actor_id=actor_id,
            resource_id=str(exposure.id),
            details={"updated_fields": list(update_dict.keys()), "new_index": exposure.exposure_index},
        )
        return exposure

    @classmethod
    def update_exposure_status(
        cls,
        db: Session,
        organization_id: int,
        exposure_id: int,
        new_status: ExposureStatusEnum,
        actor_id: Optional[int] = None,
        actor_email: str = "system",
        notes: Optional[str] = None,
    ) -> VulnerabilityExposure:
        """Executes a governed lifecycle transition."""
        exposure = cls.get_exposure(db, organization_id, exposure_id)
        if not exposure:
            raise ValueError(f"Vulnerability exposure #{exposure_id} not found.")

        current_status = exposure.status

        # Immutability Check: Terminal status cannot be transitioned
        if current_status == ExposureStatusEnum.RESOLVED:
            raise ValueError("Cannot transition out of terminal RESOLVED status.")

        # Validate legal transition paths
        legal_transitions = {
            ExposureStatusEnum.OPEN: {
                ExposureStatusEnum.UNDER_INVESTIGATION,
                ExposureStatusEnum.REMEDIATING,
                ExposureStatusEnum.EXCEPTION_REQUESTED,
                ExposureStatusEnum.RESOLVED,
            },
            ExposureStatusEnum.UNDER_INVESTIGATION: {
                ExposureStatusEnum.OPEN,
                ExposureStatusEnum.REMEDIATING,
                ExposureStatusEnum.EXCEPTION_REQUESTED,
                ExposureStatusEnum.RESOLVED,
            },
            ExposureStatusEnum.REMEDIATING: {
                ExposureStatusEnum.UNDER_INVESTIGATION,
                ExposureStatusEnum.EXCEPTION_REQUESTED,
                ExposureStatusEnum.RESOLVED,
            },
            ExposureStatusEnum.EXCEPTION_REQUESTED: {
                ExposureStatusEnum.EXCEPTION_APPROVED,
                ExposureStatusEnum.EXCEPTION_REJECTED,
                ExposureStatusEnum.REMEDIATING,
                ExposureStatusEnum.RESOLVED,
            },
            ExposureStatusEnum.EXCEPTION_APPROVED: {
                ExposureStatusEnum.REMEDIATING,
                ExposureStatusEnum.RESOLVED,
            },
            ExposureStatusEnum.EXCEPTION_REJECTED: {
                ExposureStatusEnum.OPEN,
                ExposureStatusEnum.REMEDIATING,
                ExposureStatusEnum.RESOLVED,
            },
        }

        allowed = legal_transitions.get(current_status, set())
        if new_status not in allowed and new_status != current_status:
            raise ValueError(
                f"Illegal lifecycle transition from {current_status.value} to {new_status.value}."
            )

        exposure.status = new_status
        now = datetime.now(timezone.utc)
        exposure.updated_at = now

        if new_status == ExposureStatusEnum.RESOLVED:
            exposure.resolved_at = now

        db.commit()
        db.refresh(exposure)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="EXPOSURE_STATUS_CHANGED",
            resource_type="VulnerabilityExposure",
            actor_email=actor_email,
            actor_id=actor_id,
            resource_id=str(exposure.id),
            details={
                "from_status": current_status.value,
                "to_status": new_status.value,
                "notes": notes,
            },
        )
        return exposure

    @classmethod
    def delete_exposure(
        cls,
        db: Session,
        organization_id: int,
        exposure_id: int,
        actor_id: Optional[int] = None,
        actor_email: str = "system",
    ) -> None:
        """Deletes an exposure record (restricted to non-resolved records)."""
        exposure = cls.get_exposure(db, organization_id, exposure_id)
        if not exposure:
            raise ValueError(f"Vulnerability exposure #{exposure_id} not found.")

        if exposure.status == ExposureStatusEnum.RESOLVED:
            raise ValueError("Resolved exposure records are immutable and cannot be deleted.")

        cve_id = exposure.cve_id
        db.delete(exposure)
        db.commit()

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="EXPOSURE_DELETED",
            resource_type="VulnerabilityExposure",
            actor_email=actor_email,
            actor_id=actor_id,
            resource_id=str(exposure_id),
            details={"deleted_cve": cve_id},
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Asset & Blast Radius Linkage (Cross-Module Map)
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def link_asset(
        cls,
        db: Session,
        organization_id: int,
        exposure_id: int,
        data: ExposureAssetLinkCreate,
        actor_id: Optional[int] = None,
        actor_email: str = "system",
    ) -> ExposureAssetLink:
        """Links an asset, Phase 13 Process, Phase 9 Vendor, or Phase 2 Control to the exposure."""
        exposure = cls.get_exposure(db, organization_id, exposure_id)
        if not exposure:
            raise ValueError(f"Vulnerability exposure #{exposure_id} not found.")

        if exposure.status == ExposureStatusEnum.RESOLVED:
            raise ValueError("Cannot link assets to an immutable RESOLVED exposure record.")

        # Cross-Tenant Validation: Phase 13 Business Process
        if data.process_id:
            process = (
                db.query(BusinessProcess)
                .filter(
                    BusinessProcess.id == data.process_id,
                    BusinessProcess.organization_id == organization_id,
                )
                .first()
            )
            if not process:
                raise ValueError("Referenced Business Process does not exist in this organization.")

        # Cross-Tenant Validation: Phase 9 Vendor
        if data.vendor_id:
            vendor = (
                db.query(Vendor)
                .filter(
                    Vendor.id == data.vendor_id,
                    Vendor.organization_id == organization_id,
                )
                .first()
            )
            if not vendor:
                raise ValueError("Referenced Vendor does not exist in this organization.")

        # Cross-Tenant Validation: Phase 2 Control
        if data.control_id:
            control = (
                db.query(OrganizationControl)
                .filter(
                    OrganizationControl.id == data.control_id,
                    OrganizationControl.organization_id == organization_id,
                )
                .first()
            )
            if not control:
                raise ValueError("Referenced Organization Control does not exist in this organization.")

        link = ExposureAssetLink(
            organization_id=organization_id,
            exposure_id=exposure_id,
            asset_identifier=data.asset_identifier.strip(),
            asset_type=data.asset_type,
            environment=data.environment,
            process_id=data.process_id,
            vendor_id=data.vendor_id,
            control_id=data.control_id,
            notes=data.notes.strip() if data.notes else None,
            created_at=datetime.now(timezone.utc),
        )
        db.add(link)
        db.commit()
        db.refresh(link)

        # Update Exposure Index with new blast radius multiplier
        highest_tier = cls._get_highest_process_tier(exposure)
        _, _, new_index = cls.calculate_exposure_index(
            cvss_score=exposure.cvss_score,
            epss_score=exposure.epss_score,
            cisa_kev=exposure.cisa_kev,
            highest_process_tier=highest_tier,
        )
        exposure.exposure_index = new_index
        exposure.updated_at = datetime.now(timezone.utc)
        db.commit()

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="EXPOSURE_ASSET_LINKED",
            resource_type="ExposureAssetLink",
            actor_email=actor_email,
            actor_id=actor_id,
            resource_id=str(link.id),
            details={
                "exposure_id": exposure_id,
                "asset_identifier": link.asset_identifier,
                "process_id": link.process_id,
                "vendor_id": link.vendor_id,
                "control_id": link.control_id,
                "updated_index": exposure.exposure_index,
            },
        )
        return link

    @classmethod
    def unlink_asset(
        cls,
        db: Session,
        organization_id: int,
        link_id: int,
        actor_id: Optional[int] = None,
        actor_email: str = "system",
    ) -> None:
        """Removes an asset link and recalculates exposure blast radius."""
        link = (
            db.query(ExposureAssetLink)
            .filter(
                ExposureAssetLink.id == link_id,
                ExposureAssetLink.organization_id == organization_id,
            )
            .first()
        )
        if not link:
            raise ValueError(f"Exposure asset link #{link_id} not found.")

        exposure_id = link.exposure_id
        db.delete(link)
        db.commit()

        # Recalculate index
        exposure = cls.get_exposure(db, organization_id, exposure_id)
        if exposure and exposure.status != ExposureStatusEnum.RESOLVED:
            highest_tier = cls._get_highest_process_tier(exposure)
            _, _, new_index = cls.calculate_exposure_index(
                cvss_score=exposure.cvss_score,
                epss_score=exposure.epss_score,
                cisa_kev=exposure.cisa_kev,
                highest_process_tier=highest_tier,
            )
            exposure.exposure_index = new_index
            exposure.updated_at = datetime.now(timezone.utc)
            db.commit()

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="EXPOSURE_ASSET_UNLINKED",
            resource_type="ExposureAssetLink",
            actor_email=actor_email,
            actor_id=actor_id,
            resource_id=str(link_id),
            details={"exposure_id": exposure_id},
        )

    @staticmethod
    def list_asset_links(
        db: Session,
        organization_id: int,
        exposure_id: int,
    ) -> List[ExposureAssetLink]:
        """Lists all asset links for a given exposure."""
        return (
            db.query(ExposureAssetLink)
            .filter(
                ExposureAssetLink.exposure_id == exposure_id,
                ExposureAssetLink.organization_id == organization_id,
            )
            .all()
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Four-Eyes Exception & Deferral Governance
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def request_exception(
        cls,
        db: Session,
        organization_id: int,
        exposure_id: int,
        data: ExposureExceptionCreate,
        requested_by_id: int,
        actor_email: str = "system",
    ) -> ExposureException:
        """Submits a four-eyes governed SLA extension request."""
        exposure = cls.get_exposure(db, organization_id, exposure_id)
        if not exposure:
            raise ValueError(f"Vulnerability exposure #{exposure_id} not found.")

        if exposure.status == ExposureStatusEnum.RESOLVED:
            raise ValueError("Cannot request an exception on a RESOLVED exposure record.")

        now = datetime.now(timezone.utc)
        if data.requested_sla_due <= exposure.remediation_sla_due:
            raise ValueError("Requested SLA date must be later than the current SLA due date.")

        exception = ExposureException(
            organization_id=organization_id,
            exposure_id=exposure_id,
            requested_by_id=requested_by_id,
            status=ExceptionApprovalStatusEnum.PENDING,
            original_sla_due=exposure.remediation_sla_due,
            requested_sla_due=data.requested_sla_due,
            justification=data.justification.strip(),
            compensating_controls=data.compensating_controls.strip() if data.compensating_controls else None,
            created_at=now,
        )
        db.add(exception)

        # Transition exposure status
        exposure.status = ExposureStatusEnum.EXCEPTION_REQUESTED
        exposure.updated_at = now

        db.commit()
        db.refresh(exception)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="EXPOSURE_EXCEPTION_REQUESTED",
            resource_type="ExposureException",
            actor_email=actor_email,
            actor_id=requested_by_id,
            resource_id=str(exception.id),
            details={
                "exposure_id": exposure_id,
                "original_sla_due": exception.original_sla_due.isoformat(),
                "requested_sla_due": exception.requested_sla_due.isoformat(),
            },
        )
        return exception

    @classmethod
    def review_exception(
        cls,
        db: Session,
        organization_id: int,
        exception_id: int,
        review: ExposureExceptionReviewRequest,
        approver_id: int,
        actor_email: str = "system",
    ) -> ExposureException:
        """Reviews and approves/rejects an exception with strict Four-Eyes Segregation of Duties."""
        exception = (
            db.query(ExposureException)
            .filter(
                ExposureException.id == exception_id,
                ExposureException.organization_id == organization_id,
            )
            .first()
        )
        if not exception:
            raise ValueError(f"Exposure exception #{exception_id} not found.")

        if exception.status != ExceptionApprovalStatusEnum.PENDING:
            raise ValueError(f"Exception #{exception_id} is already in terminal state: {exception.status.value}.")

        # Four-Eyes Invariant: Requester cannot approve their own exception
        if exception.requested_by_id == approver_id:
            raise ValueError(
                "Segregation of duties violation: Exception requester cannot approve their own request."
            )

        now = datetime.now(timezone.utc)
        exception.status = review.decision
        exception.approved_by_id = approver_id
        exception.review_notes = review.review_notes.strip() if review.review_notes else None
        exception.reviewed_at = now

        # Update Exposure SLA and Status
        exposure = exception.exposure
        if review.decision == ExceptionApprovalStatusEnum.APPROVED:
            exposure.remediation_sla_due = exception.requested_sla_due
            exposure.status = ExposureStatusEnum.EXCEPTION_APPROVED
        else:
            exposure.status = ExposureStatusEnum.EXCEPTION_REJECTED

        exposure.updated_at = now

        db.commit()
        db.refresh(exception)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action=f"EXPOSURE_EXCEPTION_{review.decision.value}",
            resource_type="ExposureException",
            actor_email=actor_email,
            actor_id=approver_id,
            resource_id=str(exception.id),
            details={
                "exposure_id": exception.exposure_id,
                "decision": review.decision.value,
                "new_sla_due": exposure.remediation_sla_due.isoformat(),
            },
        )
        return exception

    @staticmethod
    def list_exceptions(
        db: Session,
        organization_id: int,
        exposure_id: Optional[int] = None,
        status: Optional[ExceptionApprovalStatusEnum] = None,
    ) -> List[ExposureException]:
        """Lists exceptions for the organization."""
        query = db.query(ExposureException).filter(ExposureException.organization_id == organization_id)
        if exposure_id:
            query = query.filter(ExposureException.exposure_id == exposure_id)
        if status:
            query = query.filter(ExposureException.status == status)
        return query.order_by(ExposureException.id.desc()).all()

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Cross-Module Remediation Orchestration (Phase 11)
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def spawn_remediation_plan(
        cls,
        db: Session,
        organization_id: int,
        exposure_id: int,
        owner_id: int,
        title: Optional[str] = None,
        finding_id: Optional[int] = None,
        actor_id: Optional[int] = None,
        actor_email: str = "system",
    ) -> RemediationPlan:
        """Instantiates a Phase 11 RemediationPlan linked to the exposure."""
        from app.models.finding import Finding, FindingTypeEnum, FindingSeverityEnum, FindingStatusEnum

        exposure = cls.get_exposure(db, organization_id, exposure_id)
        if not exposure:
            raise ValueError(f"Vulnerability exposure #{exposure_id} not found.")

        plan_title = title or f"Remediate {exposure.cve_id}: {exposure.title}"
        now = datetime.now(timezone.utc)

        # Validate or resolve a valid single source finding
        resolved_finding_id = finding_id
        if resolved_finding_id:
            fnd = db.query(Finding).filter(
                Finding.id == resolved_finding_id,
                Finding.organization_id == organization_id,
            ).first()
            if not fnd:
                raise ValueError("Referenced Finding does not exist in this organization.")
        else:
            # Check if an existing finding or control is associated
            ctrl_id = None
            for link in exposure.asset_links:
                if link.control_id:
                    ctrl_id = link.control_id
                    break
            if not ctrl_id:
                ctrl = db.query(OrganizationControl).filter(
                    OrganizationControl.organization_id == organization_id
                ).first()
                ctrl_id = ctrl.id if ctrl else None

            if ctrl_id:
                fnd_sev = (
                    FindingSeverityEnum[exposure.severity.value]
                    if exposure.severity.value in FindingSeverityEnum.__members__
                    else FindingSeverityEnum.MEDIUM
                )
                finding = Finding(
                    organization_id=organization_id,
                    organization_control_id=ctrl_id,
                    title=f"Vulnerability: {exposure.cve_id}",
                    description=f"Auto-generated finding for exposure {exposure.cve_id}: {exposure.title}",
                    recommendation="Apply vendor patch, configuration update, or compensating control.",
                    finding_type=FindingTypeEnum.TECHNICAL_GAP,
                    severity=fnd_sev,
                    status=FindingStatusEnum.IN_REMEDIATION,
                    created_at=now,
                    updated_at=now,
                )
                db.add(finding)
                db.flush()
                resolved_finding_id = finding.id

        # Map exposure severity to remediation severity
        sev_map = {
            ExposureSeverityEnum.CRITICAL: RemediationSeverityEnum.CRITICAL,
            ExposureSeverityEnum.HIGH: RemediationSeverityEnum.HIGH,
            ExposureSeverityEnum.MEDIUM: RemediationSeverityEnum.MEDIUM,
            ExposureSeverityEnum.LOW: RemediationSeverityEnum.LOW,
            ExposureSeverityEnum.INFORMATIONAL: RemediationSeverityEnum.LOW,
        }

        remediation_plan = RemediationPlan(
            organization_id=organization_id,
            plan_code=f"CAPA-EXP-{exposure.cve_id}-{exposure.id}",
            title=plan_title,
            problem_statement=f"Remediation required for {exposure.cve_id}: {exposure.title}.\n{exposure.description or ''}",
            root_cause_classification=RemediationRootCauseClassificationEnum.CONTROL_DEFICIENCY,
            source_type=RemediationSourceTypeEnum.FINDING,
            finding_id=resolved_finding_id,
            plan_owner_id=owner_id,
            severity=sev_map.get(exposure.severity, RemediationSeverityEnum.MEDIUM),
            status=RemediationStatusEnum.DRAFT,
            target_completion_at=exposure.remediation_sla_due,
            created_at=now,
            updated_at=now,
        )
        db.add(remediation_plan)
        db.flush()

        exposure.remediation_plan_id = remediation_plan.id
        exposure.status = ExposureStatusEnum.REMEDIATING
        exposure.updated_at = now

        db.commit()
        db.refresh(remediation_plan)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="EXPOSURE_REMEDIATION_SPAWNED",
            resource_type="VulnerabilityExposure",
            actor_email=actor_email,
            actor_id=actor_id,
            resource_id=str(exposure.id),
            details={"remediation_plan_id": remediation_plan.id},
        )
        return remediation_plan

    # ─────────────────────────────────────────────────────────────────────────
    # 6. Executive Posture Metrics & Aggregation
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def get_exposure_posture_summary(
        db: Session,
        organization_id: int,
    ) -> Dict[str, Any]:
        """Calculates executive threat posture telemetry."""
        exposures = db.query(VulnerabilityExposure).filter(
            VulnerabilityExposure.organization_id == organization_id
        ).all()

        total = len(exposures)
        if total == 0:
            return {
                "total_exposures": 0,
                "critical_exposures": 0,
                "high_exposures": 0,
                "cisa_kev_count": 0,
                "active_exceptions_count": 0,
                "sla_breached_count": 0,
                "sla_breach_rate_percent": 0.0,
                "average_exposure_index": 0.0,
                "severity_distribution": {},
                "status_distribution": {},
            }

        now = datetime.now(timezone.utc)
        critical_count = sum(1 for e in exposures if e.severity == ExposureSeverityEnum.CRITICAL)
        high_count = sum(1 for e in exposures if e.severity == ExposureSeverityEnum.HIGH)
        kev_count = sum(1 for e in exposures if e.cisa_kev)
        exceptions_count = sum(1 for e in exposures if e.status in (ExposureStatusEnum.EXCEPTION_REQUESTED, ExposureStatusEnum.EXCEPTION_APPROVED))
        
        # SLA breached if not resolved and now > remediation_sla_due
        breached_count = sum(
            1 for e in exposures if e.status != ExposureStatusEnum.RESOLVED and e.remediation_sla_due and now > (e.remediation_sla_due if e.remediation_sla_due.tzinfo else e.remediation_sla_due.replace(tzinfo=timezone.utc))
        )
        
        avg_index = round(sum(e.exposure_index for e in exposures) / total, 2)
        breach_rate = round((breached_count / total) * 100.0, 2)

        sev_dist: Dict[str, int] = {}
        for e in exposures:
            sev_dist[e.severity.value] = sev_dist.get(e.severity.value, 0) + 1

        status_dist: Dict[str, int] = {}
        for e in exposures:
            status_dist[e.status.value] = status_dist.get(e.status.value, 0) + 1

        return {
            "total_exposures": total,
            "critical_exposures": critical_count,
            "high_exposures": high_count,
            "cisa_kev_count": kev_count,
            "active_exceptions_count": exceptions_count,
            "sla_breached_count": breached_count,
            "sla_breach_rate_percent": breach_rate,
            "average_exposure_index": avg_index,
            "severity_distribution": sev_dist,
            "status_distribution": status_dist,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Helper Methods
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _get_highest_process_tier(exposure: VulnerabilityExposure) -> Optional[CriticalityTierEnum]:
        """Inspects all linked assets and returns the highest business process criticality tier."""
        tiers = set()
        for link in exposure.asset_links:
            if link.process and link.process.criticality_tier:
                tiers.add(link.process.criticality_tier)

        if CriticalityTierEnum.TIER_1 in tiers:
            return CriticalityTierEnum.TIER_1
        elif CriticalityTierEnum.TIER_2 in tiers:
            return CriticalityTierEnum.TIER_2
        elif CriticalityTierEnum.TIER_3 in tiers:
            return CriticalityTierEnum.TIER_3
        elif CriticalityTierEnum.TIER_4 in tiers:
            return CriticalityTierEnum.TIER_4
        return None
