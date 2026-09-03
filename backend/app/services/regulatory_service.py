import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.regulatory import (
    RegulatorySource,
    RegulatoryMandate,
    RegulatoryVersion,
    RegulatoryObligation,
    RegulatoryChangeEvent,
    RegulatoryImpactAssessment,
    RegulatoryAuthorityTypeEnum,
    RegulatoryTrustTierEnum,
    RegulatoryEnforceabilityEnum,
    RegulatoryMandateStatusEnum,
    RegulatoryApplicabilityEnum,
    RegulatoryComplianceStatusEnum,
    RegulatoryChangeTypeEnum,
    RegulatoryChangeSeverityEnum,
    RegulatoryChangeStatusEnum,
    RegulatoryImpactLevelEnum,
    RegulatoryImpactStatusEnum,
)
from app.models.control import OrganizationControl
from app.models.policy import Policy
from app.schemas.regulatory import (
    RegulatorySourceCreate,
    RegulatorySourceUpdate,
    RegulatoryMandateCreate,
    RegulatoryMandateUpdate,
    RegulatoryObligationCreate,
    RegulatoryObligationUpdate,
    RegulatoryChangeEventCreate,
    RegulatoryChangeReviewRequest,
    RegulatoryChangeApproveRequest,
    RegulatoryChangeDismissRequest,
)
from app.models.user import User
from app.services.audit_service import AuditService


class RegulatoryService:
    """Enterprise service governing regulatory intelligence, statutory mandates, obligations, and Four-Eyes change review."""

    @staticmethod
    def _audit_log(
        db: Session,
        organization_id: int,
        action: str,
        resource_type: str,
        actor_id: Optional[int] = None,
        resource_id: Optional[int] = None,
        details: Optional[Dict] = None,
    ) -> None:
        user = db.query(User).filter(User.id == actor_id).first() if actor_id else None
        actor_email = user.email if user else "system@controlsphere.internal"
        AuditService.log(
            db=db,
            organization_id=organization_id,
            action=action,
            resource_type=resource_type,
            actor_email=actor_email,
            actor_id=actor_id,
            resource_id=str(resource_id) if resource_id is not None else None,
            details=details or {},
        )

    @staticmethod
    def _compute_sha256(raw_text: str) -> str:
        return hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    # ── Regulatory Sources ──────────────────────────────────────────────────

    @staticmethod
    def list_sources(
        db: Session,
        organization_id: int,
        skip: int = 0,
        limit: int = 100,
        authority_type: Optional[RegulatoryAuthorityTypeEnum] = None,
    ) -> List[RegulatorySource]:
        query = db.query(RegulatorySource).filter(RegulatorySource.organization_id == organization_id)
        if authority_type:
            query = query.filter(RegulatorySource.authority_type == authority_type)
        return query.order_by(RegulatorySource.name.asc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_source(db: Session, organization_id: int, source_id: int) -> Optional[RegulatorySource]:
        return db.query(RegulatorySource).filter(
            RegulatorySource.id == source_id,
            RegulatorySource.organization_id == organization_id,
        ).first()

    @staticmethod
    def create_source(
        db: Session,
        organization_id: int,
        source_in: RegulatorySourceCreate,
        current_user_id: int,
    ) -> RegulatorySource:
        existing = db.query(RegulatorySource).filter(
            RegulatorySource.organization_id == organization_id,
            RegulatorySource.source_code == source_in.source_code,
        ).first()
        if existing:
            raise ValueError(f"Regulatory source with code '{source_in.source_code}' already exists.")

        source = RegulatorySource(
            organization_id=organization_id,
            source_code=source_in.source_code,
            name=source_in.name,
            authority_type=source_in.authority_type,
            jurisdiction=source_in.jurisdiction,
            website_url=source_in.website_url,
            trust_tier=source_in.trust_tier,
            description=source_in.description,
            is_active=source_in.is_active,
        )
        db.add(source)
        db.commit()
        db.refresh(source)

        RegulatoryService._audit_log(
            db=db,
            organization_id=organization_id,
            actor_id=current_user_id,
            action="CREATE",
            resource_type="RegulatorySource",
            resource_id=source.id,
            details={"source_code": source.source_code, "name": source.name},
        )
        return source

    # ── Regulatory Mandates ─────────────────────────────────────────────────

    @staticmethod
    def list_mandates(
        db: Session,
        organization_id: int,
        skip: int = 0,
        limit: int = 100,
        status: Optional[RegulatoryMandateStatusEnum] = None,
    ) -> List[RegulatoryMandate]:
        query = db.query(RegulatoryMandate).filter(RegulatoryMandate.organization_id == organization_id)
        if status:
            query = query.filter(RegulatoryMandate.status == status)
        return query.order_by(RegulatoryMandate.mandate_code.asc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_mandate(db: Session, organization_id: int, mandate_id: int) -> Optional[RegulatoryMandate]:
        return db.query(RegulatoryMandate).filter(
            RegulatoryMandate.id == mandate_id,
            RegulatoryMandate.organization_id == organization_id,
        ).first()

    @staticmethod
    def create_mandate(
        db: Session,
        organization_id: int,
        mandate_in: RegulatoryMandateCreate,
        current_user_id: int,
    ) -> RegulatoryMandate:
        source = db.query(RegulatorySource).filter(
            RegulatorySource.id == mandate_in.source_id,
            RegulatorySource.organization_id == organization_id,
        ).first()
        if not source:
            raise ValueError("Regulatory source not found in this organization.")

        existing = db.query(RegulatoryMandate).filter(
            RegulatoryMandate.organization_id == organization_id,
            RegulatoryMandate.mandate_code == mandate_in.mandate_code,
        ).first()
        if existing:
            raise ValueError(f"Regulatory mandate with code '{mandate_in.mandate_code}' already exists.")

        mandate = RegulatoryMandate(
            organization_id=organization_id,
            source_id=mandate_in.source_id,
            mandate_code=mandate_in.mandate_code,
            title=mandate_in.title,
            short_name=mandate_in.short_name,
            legal_citation=mandate_in.legal_citation,
            jurisdiction=mandate_in.jurisdiction,
            enforceability_level=mandate_in.enforceability_level,
            status=mandate_in.status,
            framework_id=mandate_in.framework_id,
            description=mandate_in.description,
            effective_date=mandate_in.effective_date,
            sunset_date=mandate_in.sunset_date,
            created_by_id=current_user_id,
        )
        db.add(mandate)
        db.commit()
        db.refresh(mandate)

        RegulatoryService._audit_log(
            db=db,
            organization_id=organization_id,
            actor_id=current_user_id,
            action="CREATE",
            resource_type="RegulatoryMandate",
            resource_id=mandate.id,
            details={"mandate_code": mandate.mandate_code, "title": mandate.title},
        )
        return mandate

    # ── Regulatory Obligations ──────────────────────────────────────────────

    @staticmethod
    def list_obligations(
        db: Session,
        organization_id: int,
        mandate_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[RegulatoryObligation]:
        query = db.query(RegulatoryObligation).filter(RegulatoryObligation.organization_id == organization_id)
        if mandate_id:
            query = query.filter(RegulatoryObligation.mandate_id == mandate_id)
        return query.order_by(RegulatoryObligation.obligation_code.asc()).offset(skip).limit(limit).all()

    @staticmethod
    def create_obligation(
        db: Session,
        organization_id: int,
        obligation_in: RegulatoryObligationCreate,
        current_user_id: int,
    ) -> RegulatoryObligation:
        mandate = db.query(RegulatoryMandate).filter(
            RegulatoryMandate.id == obligation_in.mandate_id,
            RegulatoryMandate.organization_id == organization_id,
        ).first()
        if not mandate:
            raise ValueError("Regulatory mandate not found in this organization.")

        if obligation_in.organization_control_id:
            control = db.query(OrganizationControl).filter(
                OrganizationControl.id == obligation_in.organization_control_id,
                OrganizationControl.organization_id == organization_id,
            ).first()
            if not control:
                raise ValueError("Target organization control not found in this organization.")

        existing = db.query(RegulatoryObligation).filter(
            RegulatoryObligation.organization_id == organization_id,
            RegulatoryObligation.mandate_id == obligation_in.mandate_id,
            RegulatoryObligation.obligation_code == obligation_in.obligation_code,
        ).first()
        if existing:
            raise ValueError(f"Regulatory obligation '{obligation_in.obligation_code}' already exists for this mandate.")

        obligation = RegulatoryObligation(
            organization_id=organization_id,
            mandate_id=obligation_in.mandate_id,
            version_id=obligation_in.version_id,
            obligation_code=obligation_in.obligation_code,
            title=obligation_in.title,
            description=obligation_in.description,
            article_reference=obligation_in.article_reference,
            applicability=obligation_in.applicability,
            organization_control_id=obligation_in.organization_control_id,
            compliance_status=obligation_in.compliance_status,
        )
        db.add(obligation)
        db.commit()
        db.refresh(obligation)

        RegulatoryService._audit_log(
            db=db,
            organization_id=organization_id,
            actor_id=current_user_id,
            action="CREATE",
            resource_type="RegulatoryObligation",
            resource_id=obligation.id,
            details={"obligation_code": obligation.obligation_code, "mandate_id": obligation.mandate_id},
        )
        return obligation

    # ── Regulatory Change Events & Four-Eyes Workflow ───────────────────────

    @staticmethod
    def list_changes(
        db: Session,
        organization_id: int,
        mandate_id: Optional[int] = None,
        status: Optional[RegulatoryChangeStatusEnum] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[RegulatoryChangeEvent]:
        query = db.query(RegulatoryChangeEvent).filter(RegulatoryChangeEvent.organization_id == organization_id)
        if mandate_id:
            query = query.filter(RegulatoryChangeEvent.mandate_id == mandate_id)
        if status:
            query = query.filter(RegulatoryChangeEvent.status == status)
        return query.order_by(RegulatoryChangeEvent.official_publication_date.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_change(db: Session, organization_id: int, change_id: int) -> Optional[RegulatoryChangeEvent]:
        return db.query(RegulatoryChangeEvent).filter(
            RegulatoryChangeEvent.id == change_id,
            RegulatoryChangeEvent.organization_id == organization_id,
        ).first()

    @staticmethod
    def stage_change_event(
        db: Session,
        organization_id: int,
        change_in: RegulatoryChangeEventCreate,
        current_user_id: int,
    ) -> RegulatoryChangeEvent:
        mandate = db.query(RegulatoryMandate).filter(
            RegulatoryMandate.id == change_in.mandate_id,
            RegulatoryMandate.organization_id == organization_id,
        ).first()
        if not mandate:
            raise ValueError("Regulatory mandate not found in this organization.")

        # Compute content hash server-side from title + summary + date
        computed_hash = RegulatoryService._compute_sha256(
            f"{change_in.title}|{change_in.raw_summary}|{change_in.official_publication_date.isoformat()}"
        )

        existing_hash = db.query(RegulatoryChangeEvent).filter(
            RegulatoryChangeEvent.organization_id == organization_id,
            RegulatoryChangeEvent.content_hash_sha256 == computed_hash,
        ).first()
        if existing_hash:
            raise ValueError(f"Duplicate regulatory change payload detected. Hash: {computed_hash}")

        existing_code = db.query(RegulatoryChangeEvent).filter(
            RegulatoryChangeEvent.organization_id == organization_id,
            RegulatoryChangeEvent.change_code == change_in.change_code,
        ).first()
        if existing_code:
            raise ValueError(f"Regulatory change code '{change_in.change_code}' already exists.")

        change_event = RegulatoryChangeEvent(
            organization_id=organization_id,
            mandate_id=change_in.mandate_id,
            change_code=change_in.change_code,
            title=change_in.title,
            change_type=change_in.change_type,
            severity=change_in.severity,
            status=RegulatoryChangeStatusEnum.STAGED,
            official_publication_date=change_in.official_publication_date,
            enforcement_date=change_in.enforcement_date,
            source_url=change_in.source_url,
            content_hash_sha256=computed_hash,
            raw_summary=change_in.raw_summary,
            created_by_id=current_user_id,
        )
        db.add(change_event)
        db.commit()
        db.refresh(change_event)

        RegulatoryService._audit_log(
            db=db,
            organization_id=organization_id,
            actor_id=current_user_id,
            action="STAGE_REGULATORY_CHANGE",
            resource_type="RegulatoryChangeEvent",
            resource_id=change_event.id,
            details={"change_code": change_event.change_code, "severity": change_event.severity.value},
        )
        return change_event

    @staticmethod
    def review_change_event(
        db: Session,
        organization_id: int,
        change_id: int,
        review_in: RegulatoryChangeReviewRequest,
        reviewer_id: int,
    ) -> Tuple[RegulatoryChangeEvent, RegulatoryImpactAssessment]:
        change_event = RegulatoryService.get_change(db, organization_id, change_id)
        if not change_event:
            raise ValueError("Regulatory change event not found.")

        if change_event.status not in [RegulatoryChangeStatusEnum.STAGED, RegulatoryChangeStatusEnum.UNDER_REVIEW, RegulatoryChangeStatusEnum.VALIDATED]:
            raise ValueError(f"Cannot review change event in status '{change_event.status.value}'.")

        # Validate impacted control IDs belong to tenant
        if review_in.impacted_control_ids:
            for cid in review_in.impacted_control_ids:
                ctrl = db.query(OrganizationControl).filter(
                    OrganizationControl.id == cid,
                    OrganizationControl.organization_id == organization_id,
                ).first()
                if not ctrl:
                    raise ValueError(f"Impacted control ID {cid} not found in this organization.")

        # Create or update Impact Assessment
        assessment_code = f"IMP-{change_event.change_code}"
        assessment = db.query(RegulatoryImpactAssessment).filter(
            RegulatoryImpactAssessment.organization_id == organization_id,
            RegulatoryImpactAssessment.change_event_id == change_event.id,
        ).first()

        controls_json = json.dumps(review_in.impacted_control_ids) if review_in.impacted_control_ids else None
        policies_json = json.dumps(review_in.impacted_policy_ids) if review_in.impacted_policy_ids else None

        if not assessment:
            assessment = RegulatoryImpactAssessment(
                organization_id=organization_id,
                change_event_id=change_event.id,
                assessment_code=assessment_code,
                title=f"Impact Assessment for {change_event.change_code}",
                impact_level=review_in.impact_level,
                status=RegulatoryImpactStatusEnum.SUBMITTED,
                impacted_control_ids=controls_json,
                impacted_policy_ids=policies_json,
                gap_analysis_summary=review_in.gap_analysis_summary,
                action_plan=review_in.action_plan,
                created_by_id=reviewer_id,
                reviewed_by_id=reviewer_id,
            )
            db.add(assessment)
        else:
            assessment.impact_level = review_in.impact_level
            assessment.status = RegulatoryImpactStatusEnum.SUBMITTED
            assessment.impacted_control_ids = controls_json
            assessment.impacted_policy_ids = policies_json
            assessment.gap_analysis_summary = review_in.gap_analysis_summary
            assessment.action_plan = review_in.action_plan
            assessment.reviewed_by_id = reviewer_id

        change_event.status = RegulatoryChangeStatusEnum.REVIEWED
        change_event.review_notes = review_in.review_notes
        db.commit()
        db.refresh(change_event)
        db.refresh(assessment)

        RegulatoryService._audit_log(
            db=db,
            organization_id=organization_id,
            actor_id=reviewer_id,
            action="REVIEW_REGULATORY_CHANGE",
            resource_type="RegulatoryChangeEvent",
            resource_id=change_event.id,
            details={"status": change_event.status.value, "impact_level": assessment.impact_level.value},
        )
        return change_event, assessment

    @staticmethod
    def approve_change_event(
        db: Session,
        organization_id: int,
        change_id: int,
        approve_in: RegulatoryChangeApproveRequest,
        approver_id: int,
    ) -> RegulatoryChangeEvent:
        change_event = RegulatoryService.get_change(db, organization_id, change_id)
        if not change_event:
            raise ValueError("Regulatory change event not found.")

        # Strict Four-Eyes check: creator cannot approve own change
        if change_event.created_by_id == approver_id:
            raise ValueError("Four-Eyes Violation: The creator of a regulatory change event cannot approve it.")

        if change_event.status != RegulatoryChangeStatusEnum.REVIEWED:
            raise ValueError(f"Cannot approve change event in status '{change_event.status.value}'. Must be 'REVIEWED'.")

        assessment = db.query(RegulatoryImpactAssessment).filter(
            RegulatoryImpactAssessment.organization_id == organization_id,
            RegulatoryImpactAssessment.change_event_id == change_event.id,
        ).first()
        if assessment:
            # Four-Eyes check on impact assessment as well
            if assessment.created_by_id == approver_id:
                raise ValueError("Four-Eyes Violation: Author of the regulatory impact assessment cannot approve it.")
            assessment.status = RegulatoryImpactStatusEnum.APPROVED
            assessment.approved_by_id = approver_id
            assessment.approved_at = datetime.now(timezone.utc)

        change_event.status = RegulatoryChangeStatusEnum.APPROVED
        change_event.approved_by_id = approver_id
        change_event.approved_at = datetime.now(timezone.utc)
        if approve_in.review_notes:
            change_event.review_notes = f"{change_event.review_notes or ''}\nApproval Notes: {approve_in.review_notes}".strip()

        db.commit()
        db.refresh(change_event)

        RegulatoryService._audit_log(
            db=db,
            organization_id=organization_id,
            actor_id=approver_id,
            action="APPROVE_REGULATORY_CHANGE",
            resource_type="RegulatoryChangeEvent",
            resource_id=change_event.id,
            details={"approved_at": change_event.approved_at.isoformat()},
        )
        return change_event

    @staticmethod
    def dismiss_change_event(
        db: Session,
        organization_id: int,
        change_id: int,
        dismiss_in: RegulatoryChangeDismissRequest,
        current_user_id: int,
    ) -> RegulatoryChangeEvent:
        change_event = RegulatoryService.get_change(db, organization_id, change_id)
        if not change_event:
            raise ValueError("Regulatory change event not found.")

        if change_event.status in [RegulatoryChangeStatusEnum.APPROVED, RegulatoryChangeStatusEnum.ACTIVE]:
            raise ValueError(f"Cannot dismiss regulatory change event in '{change_event.status.value}' status.")

        change_event.status = RegulatoryChangeStatusEnum.DISMISSED
        change_event.dismissal_reason = dismiss_in.dismissal_reason
        db.commit()
        db.refresh(change_event)

        RegulatoryService._audit_log(
            db=db,
            organization_id=organization_id,
            actor_id=current_user_id,
            action="DISMISS_REGULATORY_CHANGE",
            resource_type="RegulatoryChangeEvent",
            resource_id=change_event.id,
            details={"dismissal_reason": dismiss_in.dismissal_reason},
        )
        return change_event
