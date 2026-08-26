from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session, joinedload

from app.models.audit_engagement import (
    Audit,
    AuditFindingLink,
    AuditOpinionEnum,
    AuditProcedure,
    AuditProcedureEvidence,
    AuditScopeControl,
    AuditStatusEnum,
    AuditTypeEnum,
    ProcedureResultEnum,
)
from app.models.control import OrganizationControl
from app.models.evidence import EvidenceItem, EvidenceStatusEnum
from app.models.exception import ExceptionStatusEnum, SecurityException
from app.models.finding import Finding, FindingSeverityEnum, FindingStatusEnum
from app.models.framework import Framework
from app.models.user import User
from app.schemas.audit_engagement import (
    AuditClosure,
    AuditCreate,
    AuditEvidenceLinkCreate,
    AuditFindingLinkCreate,
    AuditOpinionCreate,
    AuditProcedureCreate,
    AuditProcedureUpdate,
    AuditScopeAdd,
    AuditStatusUpdate,
    AuditUpdate,
)

# ─────────────────────────────────────────────────────────────────────────────
# Valid lifecycle state machine transitions
# ─────────────────────────────────────────────────────────────────────────────
_VALID_TRANSITIONS: Dict[AuditStatusEnum, List[AuditStatusEnum]] = {
    AuditStatusEnum.PLANNED: [AuditStatusEnum.INITIATED],
    AuditStatusEnum.INITIATED: [AuditStatusEnum.FIELDWORK, AuditStatusEnum.PLANNED],
    AuditStatusEnum.FIELDWORK: [AuditStatusEnum.REVIEW, AuditStatusEnum.INITIATED],
    AuditStatusEnum.REVIEW: [AuditStatusEnum.REPORTING, AuditStatusEnum.FIELDWORK],
    AuditStatusEnum.REPORTING: [AuditStatusEnum.COMPLETED, AuditStatusEnum.REVIEW],
    AuditStatusEnum.COMPLETED: [AuditStatusEnum.CLOSED],
    AuditStatusEnum.CLOSED: [],
}

# Statuses that are considered "active" / in-progress for counts
_IN_PROGRESS_STATUSES = {
    AuditStatusEnum.INITIATED,
    AuditStatusEnum.FIELDWORK,
    AuditStatusEnum.REVIEW,
    AuditStatusEnum.REPORTING,
}


class AuditEngagementService:

    # ─────────────────────────────────────────────────────────────────────────
    # LIST
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def list_audits(
        db: Session,
        organization_id: int,
        status: Optional[AuditStatusEnum] = None,
        audit_type: Optional[AuditTypeEnum] = None,
        lead_auditor_id: Optional[int] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        query = (
            db.query(Audit)
            .filter(Audit.organization_id == organization_id)
            .options(
                joinedload(Audit.lead_auditor),
                joinedload(Audit.created_by),
                joinedload(Audit.scope_controls),
                joinedload(Audit.procedures),
                joinedload(Audit.finding_links),
            )
        )
        if status:
            query = query.filter(Audit.status == status)
        if audit_type:
            query = query.filter(Audit.audit_type == audit_type)
        if lead_auditor_id:
            query = query.filter(Audit.lead_auditor_id == lead_auditor_id)
        if search:
            query = query.filter(
                (Audit.title.ilike(f"%{search}%"))
                | (Audit.audit_reference.ilike(f"%{search}%"))
                | (Audit.objective.ilike(f"%{search}%"))
            )

        audits = query.order_by(Audit.created_at.desc()).all()
        results = []
        for a in audits[skip : skip + limit]:
            results.append(_audit_to_dict(a))
        return results

    # ─────────────────────────────────────────────────────────────────────────
    # GET SINGLE
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def get_audit_by_id(
        db: Session, audit_id: int, organization_id: int
    ) -> Optional[Dict[str, Any]]:
        a = (
            db.query(Audit)
            .filter(Audit.id == audit_id, Audit.organization_id == organization_id)
            .options(
                joinedload(Audit.lead_auditor),
                joinedload(Audit.created_by),
                joinedload(Audit.opinion_issued_by),
                joinedload(Audit.closed_by),
                joinedload(Audit.framework),
                joinedload(Audit.scope_controls).joinedload(AuditScopeControl.organization_control).joinedload(OrganizationControl.subcategory),
                joinedload(Audit.scope_controls).joinedload(AuditScopeControl.created_by),
                joinedload(Audit.procedures).joinedload(AuditProcedure.tester),
                joinedload(Audit.procedures).joinedload(AuditProcedure.created_by),
                joinedload(Audit.procedures).joinedload(AuditProcedure.evidence_links),
                joinedload(Audit.finding_links).joinedload(AuditFindingLink.finding),
                joinedload(Audit.finding_links).joinedload(AuditFindingLink.created_by),
            )
            .first()
        )
        if not a:
            return None
        d = _audit_to_dict(a)
        d["scope_controls"] = [_scope_to_dict(sc) for sc in a.scope_controls]
        d["procedures"] = [_procedure_to_dict(p) for p in a.procedures]
        d["finding_links"] = [_finding_link_to_dict(fl) for fl in a.finding_links]
        return d

    # ─────────────────────────────────────────────────────────────────────────
    # CREATE
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def create_audit(
        db: Session,
        obj_in: AuditCreate,
        organization_id: int,
        creator_id: Optional[int],
    ) -> Audit:
        # Validate framework belongs globally (frameworks are global reference data)
        if obj_in.framework_id:
            fw = db.query(Framework).filter(Framework.id == obj_in.framework_id).first()
            if not fw:
                raise ValueError(f"Framework ID {obj_in.framework_id} not found.")

        # Validate lead auditor belongs to org and is active
        if obj_in.lead_auditor_id:
            _validate_user_in_org(db, obj_in.lead_auditor_id, organization_id, "Lead auditor")

        audit = Audit(
            organization_id=organization_id,
            title=obj_in.title.strip(),
            audit_type=obj_in.audit_type,
            audit_reference=obj_in.audit_reference,
            objective=obj_in.objective.strip(),
            scope_description=obj_in.scope_description,
            methodology=obj_in.methodology,
            limitations=obj_in.limitations,
            framework_id=obj_in.framework_id,
            lead_auditor_id=obj_in.lead_auditor_id,
            audit_team_notes=obj_in.audit_team_notes,
            planned_start_date=obj_in.planned_start_date,
            planned_end_date=obj_in.planned_end_date,
            status=AuditStatusEnum.PLANNED,
            opinion=AuditOpinionEnum.UNISSUED,
            created_by_id=creator_id,
        )
        db.add(audit)
        db.commit()
        db.refresh(audit)
        return audit

    # ─────────────────────────────────────────────────────────────────────────
    # UPDATE
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def update_audit(
        db: Session,
        audit_id: int,
        organization_id: int,
        obj_in: AuditUpdate,
    ) -> Optional[Audit]:
        audit = _get_audit(db, audit_id, organization_id)
        if not audit:
            return None

        if audit.status == AuditStatusEnum.CLOSED:
            raise ValueError("Cannot modify a CLOSED audit.")

        if obj_in.framework_id is not None:
            fw = db.query(Framework).filter(Framework.id == obj_in.framework_id).first()
            if not fw:
                raise ValueError(f"Framework ID {obj_in.framework_id} not found.")

        if obj_in.lead_auditor_id is not None:
            _validate_user_in_org(db, obj_in.lead_auditor_id, organization_id, "Lead auditor")

        update_data = obj_in.model_dump(exclude_unset=True)
        for k, v in update_data.items():
            setattr(audit, k, v)

        db.add(audit)
        db.commit()
        db.refresh(audit)
        return audit

    # ─────────────────────────────────────────────────────────────────────────
    # STATUS TRANSITION
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def update_status(
        db: Session,
        audit_id: int,
        organization_id: int,
        status_in: AuditStatusUpdate,
    ) -> Optional[Audit]:
        audit = _get_audit(db, audit_id, organization_id)
        if not audit:
            return None

        if audit.status == AuditStatusEnum.CLOSED:
            raise ValueError("Cannot transition a CLOSED audit.")

        allowed = _VALID_TRANSITIONS.get(audit.status, [])
        if status_in.status not in allowed:
            raise ValueError(
                f"Invalid transition '{audit.status.value}' → '{status_in.status.value}'. "
                f"Allowed: {[s.value for s in allowed]}"
            )

        audit.status = status_in.status
        # Record actual dates automatically
        if status_in.status == AuditStatusEnum.INITIATED and not audit.actual_start_date:
            from datetime import date
            audit.actual_start_date = date.today()

        db.add(audit)
        db.commit()
        db.refresh(audit)
        return audit

    # ─────────────────────────────────────────────────────────────────────────
    # ISSUE OPINION (human-authoritative, never AI)
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def issue_opinion(
        db: Session,
        audit_id: int,
        organization_id: int,
        opinion_in: AuditOpinionCreate,
        issuer_id: Optional[int],
    ) -> Optional[Audit]:
        audit = _get_audit(db, audit_id, organization_id)
        if not audit:
            return None

        if audit.status not in [AuditStatusEnum.REVIEW, AuditStatusEnum.REPORTING, AuditStatusEnum.COMPLETED]:
            raise ValueError(
                f"Audit opinion can only be issued when status is REVIEW, REPORTING, or COMPLETED. "
                f"Current status: '{audit.status.value}'."
            )

        # Separation of duties: lead auditor cannot issue their own opinion
        if issuer_id and audit.lead_auditor_id and issuer_id == audit.lead_auditor_id:
            raise ValueError(
                "Separation of duties: The lead auditor cannot issue the audit opinion on their own engagement. "
                "An independent reviewer must issue the opinion."
            )

        audit.opinion = opinion_in.opinion
        audit.opinion_issued_by_id = issuer_id
        audit.opinion_issued_at = datetime.now(timezone.utc)
        audit.opinion_notes = opinion_in.opinion_notes

        db.add(audit)
        db.commit()
        db.refresh(audit)
        return audit

    # ─────────────────────────────────────────────────────────────────────────
    # CLOSE AUDIT
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def close_audit(
        db: Session,
        audit_id: int,
        organization_id: int,
        closure_in: AuditClosure,
        user_id: Optional[int],
    ) -> Optional[Audit]:
        audit = _get_audit(db, audit_id, organization_id)
        if not audit:
            return None

        if audit.status == AuditStatusEnum.CLOSED:
            raise ValueError("Audit is already closed.")

        if audit.status != AuditStatusEnum.COMPLETED:
            raise ValueError(
                f"Only COMPLETED audits can be closed. Current status: '{audit.status.value}'."
            )

        from datetime import date
        audit.status = AuditStatusEnum.CLOSED
        audit.closed_at = datetime.now(timezone.utc)
        audit.closed_by_id = user_id
        audit.closure_notes = closure_in.closure_notes.strip()
        if not audit.actual_end_date:
            audit.actual_end_date = date.today()

        db.add(audit)
        db.commit()
        db.refresh(audit)
        return audit

    # ─────────────────────────────────────────────────────────────────────────
    # SCOPE — add / remove controls
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def add_scope_control(
        db: Session,
        audit_id: int,
        obj_in: AuditScopeAdd,
        organization_id: int,
        creator_id: Optional[int],
    ) -> AuditScopeControl:
        audit = _get_audit(db, audit_id, organization_id)
        if not audit:
            raise ValueError("Audit not found in your organization.")
        if audit.status == AuditStatusEnum.CLOSED:
            raise ValueError("Cannot modify scope of a CLOSED audit.")

        ctrl = (
            db.query(OrganizationControl)
            .filter(
                OrganizationControl.id == obj_in.organization_control_id,
                OrganizationControl.organization_id == organization_id,
            )
            .first()
        )
        if not ctrl:
            raise ValueError("Control not found in your organization.")

        existing = (
            db.query(AuditScopeControl)
            .filter(
                AuditScopeControl.audit_id == audit_id,
                AuditScopeControl.organization_control_id == obj_in.organization_control_id,
            )
            .first()
        )
        if existing:
            return existing

        sc = AuditScopeControl(
            organization_id=organization_id,
            audit_id=audit_id,
            organization_control_id=obj_in.organization_control_id,
            scope_notes=obj_in.scope_notes,
            created_by_id=creator_id,
        )
        db.add(sc)
        db.commit()
        db.refresh(sc)
        return sc

    @staticmethod
    def remove_scope_control(
        db: Session,
        audit_id: int,
        organization_control_id: int,
        organization_id: int,
    ) -> bool:
        audit = _get_audit(db, audit_id, organization_id)
        if not audit:
            return False
        if audit.status == AuditStatusEnum.CLOSED:
            raise ValueError("Cannot modify scope of a CLOSED audit.")

        sc = (
            db.query(AuditScopeControl)
            .filter(
                AuditScopeControl.audit_id == audit_id,
                AuditScopeControl.organization_control_id == organization_control_id,
                AuditScopeControl.organization_id == organization_id,
            )
            .first()
        )
        if not sc:
            return False
        db.delete(sc)
        db.commit()
        return True

    @staticmethod
    def list_scope_controls(
        db: Session, audit_id: int, organization_id: int
    ) -> List[AuditScopeControl]:
        audit = _get_audit(db, audit_id, organization_id)
        if not audit:
            raise ValueError("Audit not found in your organization.")
        return (
            db.query(AuditScopeControl)
            .filter(
                AuditScopeControl.audit_id == audit_id,
                AuditScopeControl.organization_id == organization_id,
            )
            .options(joinedload(AuditScopeControl.organization_control).joinedload(OrganizationControl.subcategory))
            .all()
        )

    # ─────────────────────────────────────────────────────────────────────────
    # PROCEDURES — CRUD
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def create_procedure(
        db: Session,
        audit_id: int,
        obj_in: AuditProcedureCreate,
        organization_id: int,
        creator_id: Optional[int],
    ) -> AuditProcedure:
        audit = _get_audit(db, audit_id, organization_id)
        if not audit:
            raise ValueError("Audit not found in your organization.")
        if audit.status == AuditStatusEnum.CLOSED:
            raise ValueError("Cannot add procedures to a CLOSED audit.")

        if obj_in.organization_control_id:
            ctrl = (
                db.query(OrganizationControl)
                .filter(
                    OrganizationControl.id == obj_in.organization_control_id,
                    OrganizationControl.organization_id == organization_id,
                )
                .first()
            )
            if not ctrl:
                raise ValueError("Linked control not found in your organization.")

        if obj_in.tester_id:
            _validate_user_in_org(db, obj_in.tester_id, organization_id, "Tester")

        procedure = AuditProcedure(
            organization_id=organization_id,
            audit_id=audit_id,
            organization_control_id=obj_in.organization_control_id,
            title=obj_in.title.strip(),
            objective=obj_in.objective,
            test_steps=obj_in.test_steps,
            expected_result=obj_in.expected_result,
            actual_result=obj_in.actual_result,
            assessment_method=obj_in.assessment_method,
            result=obj_in.result,
            execution_notes=obj_in.execution_notes,
            limitations=obj_in.limitations,
            tester_id=obj_in.tester_id,
            execution_date=obj_in.execution_date,
            created_by_id=creator_id,
        )
        db.add(procedure)
        db.commit()
        db.refresh(procedure)
        return procedure

    @staticmethod
    def get_procedure(
        db: Session, audit_id: int, procedure_id: int, organization_id: int
    ) -> Optional[AuditProcedure]:
        return (
            db.query(AuditProcedure)
            .filter(
                AuditProcedure.id == procedure_id,
                AuditProcedure.audit_id == audit_id,
                AuditProcedure.organization_id == organization_id,
            )
            .options(
                joinedload(AuditProcedure.tester),
                joinedload(AuditProcedure.evidence_links).joinedload(AuditProcedureEvidence.evidence),
            )
            .first()
        )

    @staticmethod
    def update_procedure(
        db: Session,
        audit_id: int,
        procedure_id: int,
        organization_id: int,
        obj_in: AuditProcedureUpdate,
    ) -> Optional[AuditProcedure]:
        audit = _get_audit(db, audit_id, organization_id)
        if not audit:
            return None
        if audit.status == AuditStatusEnum.CLOSED:
            raise ValueError("Cannot modify procedures on a CLOSED audit.")

        procedure = (
            db.query(AuditProcedure)
            .filter(
                AuditProcedure.id == procedure_id,
                AuditProcedure.audit_id == audit_id,
                AuditProcedure.organization_id == organization_id,
            )
            .first()
        )
        if not procedure:
            return None

        if obj_in.organization_control_id is not None:
            if obj_in.organization_control_id:
                ctrl = (
                    db.query(OrganizationControl)
                    .filter(
                        OrganizationControl.id == obj_in.organization_control_id,
                        OrganizationControl.organization_id == organization_id,
                    )
                    .first()
                )
                if not ctrl:
                    raise ValueError("Linked control not found in your organization.")

        if obj_in.tester_id is not None:
            _validate_user_in_org(db, obj_in.tester_id, organization_id, "Tester")

        update_data = obj_in.model_dump(exclude_unset=True)
        for k, v in update_data.items():
            setattr(procedure, k, v)

        db.add(procedure)
        db.commit()
        db.refresh(procedure)
        return procedure

    # ─────────────────────────────────────────────────────────────────────────
    # PROCEDURE EVIDENCE — link / unlink
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def link_evidence_to_procedure(
        db: Session,
        audit_id: int,
        procedure_id: int,
        obj_in: AuditEvidenceLinkCreate,
        organization_id: int,
        creator_id: Optional[int],
    ) -> AuditProcedureEvidence:
        audit = _get_audit(db, audit_id, organization_id)
        if not audit:
            raise ValueError("Audit not found in your organization.")
        if audit.status == AuditStatusEnum.CLOSED:
            raise ValueError("Cannot link evidence to a CLOSED audit.")

        procedure = (
            db.query(AuditProcedure)
            .filter(
                AuditProcedure.id == procedure_id,
                AuditProcedure.audit_id == audit_id,
                AuditProcedure.organization_id == organization_id,
            )
            .first()
        )
        if not procedure:
            raise ValueError("Audit procedure not found.")

        # Validate evidence belongs to the same org and is not deleted
        ev = (
            db.query(EvidenceItem)
            .filter(
                EvidenceItem.id == obj_in.evidence_id,
                EvidenceItem.organization_id == organization_id,
            )
            .first()
        )
        if not ev:
            raise ValueError("Evidence item not found in your organization.")
        if ev.status == EvidenceStatusEnum.SUPERSEDED:
            raise ValueError("Cannot link superseded evidence to an audit procedure.")

        existing = (
            db.query(AuditProcedureEvidence)
            .filter(
                AuditProcedureEvidence.procedure_id == procedure_id,
                AuditProcedureEvidence.evidence_id == obj_in.evidence_id,
            )
            .first()
        )
        if existing:
            return existing

        link = AuditProcedureEvidence(
            organization_id=organization_id,
            procedure_id=procedure_id,
            evidence_id=obj_in.evidence_id,
            link_notes=obj_in.link_notes,
            created_by_id=creator_id,
        )
        db.add(link)
        db.commit()
        db.refresh(link)
        return link

    @staticmethod
    def unlink_evidence_from_procedure(
        db: Session,
        audit_id: int,
        procedure_id: int,
        evidence_id: int,
        organization_id: int,
    ) -> bool:
        audit = _get_audit(db, audit_id, organization_id)
        if not audit:
            return False
        if audit.status == AuditStatusEnum.CLOSED:
            raise ValueError("Cannot unlink evidence from a CLOSED audit.")

        link = (
            db.query(AuditProcedureEvidence)
            .filter(
                AuditProcedureEvidence.procedure_id == procedure_id,
                AuditProcedureEvidence.evidence_id == evidence_id,
                AuditProcedureEvidence.organization_id == organization_id,
            )
            .first()
        )
        if not link:
            return False
        db.delete(link)
        db.commit()
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # FINDING LINKS
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def link_finding(
        db: Session,
        audit_id: int,
        obj_in: AuditFindingLinkCreate,
        organization_id: int,
        creator_id: Optional[int],
    ) -> AuditFindingLink:
        audit = _get_audit(db, audit_id, organization_id)
        if not audit:
            raise ValueError("Audit not found in your organization.")
        if audit.status == AuditStatusEnum.CLOSED:
            raise ValueError("Cannot link findings to a CLOSED audit.")

        # Validate finding belongs to same org
        finding = (
            db.query(Finding)
            .filter(
                Finding.id == obj_in.finding_id,
                Finding.organization_id == organization_id,
            )
            .first()
        )
        if not finding:
            raise ValueError("Finding not found in your organization.")

        # Validate procedure if supplied
        if obj_in.source_procedure_id:
            proc = (
                db.query(AuditProcedure)
                .filter(
                    AuditProcedure.id == obj_in.source_procedure_id,
                    AuditProcedure.audit_id == audit_id,
                    AuditProcedure.organization_id == organization_id,
                )
                .first()
            )
            if not proc:
                raise ValueError("Source procedure not found in this audit.")

        existing = (
            db.query(AuditFindingLink)
            .filter(
                AuditFindingLink.audit_id == audit_id,
                AuditFindingLink.finding_id == obj_in.finding_id,
            )
            .first()
        )
        if existing:
            return existing

        link = AuditFindingLink(
            organization_id=organization_id,
            audit_id=audit_id,
            finding_id=obj_in.finding_id,
            source_procedure_id=obj_in.source_procedure_id,
            link_notes=obj_in.link_notes,
            created_by_id=creator_id,
        )
        db.add(link)
        db.commit()
        db.refresh(link)
        return link

    @staticmethod
    def unlink_finding(
        db: Session,
        audit_id: int,
        finding_id: int,
        organization_id: int,
    ) -> bool:
        audit = _get_audit(db, audit_id, organization_id)
        if not audit:
            return False
        if audit.status == AuditStatusEnum.CLOSED:
            raise ValueError("Cannot unlink findings from a CLOSED audit.")

        link = (
            db.query(AuditFindingLink)
            .filter(
                AuditFindingLink.audit_id == audit_id,
                AuditFindingLink.finding_id == finding_id,
                AuditFindingLink.organization_id == organization_id,
            )
            .first()
        )
        if not link:
            return False
        db.delete(link)
        db.commit()
        return True

    @staticmethod
    def list_findings(
        db: Session, audit_id: int, organization_id: int
    ) -> List[AuditFindingLink]:
        audit = _get_audit(db, audit_id, organization_id)
        if not audit:
            raise ValueError("Audit not found in your organization.")
        return (
            db.query(AuditFindingLink)
            .filter(
                AuditFindingLink.audit_id == audit_id,
                AuditFindingLink.organization_id == organization_id,
            )
            .options(joinedload(AuditFindingLink.finding))
            .all()
        )

    # ─────────────────────────────────────────────────────────────────────────
    # READINESS METRICS (all deterministic, server-side)
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def get_readiness(
        db: Session, audit_id: int, organization_id: int
    ) -> Optional[Dict[str, Any]]:
        audit = _get_audit(db, audit_id, organization_id)
        if not audit:
            return None

        # Scope
        scope_controls = (
            db.query(AuditScopeControl)
            .filter(
                AuditScopeControl.audit_id == audit_id,
                AuditScopeControl.organization_id == organization_id,
            )
            .all()
        )
        controls_in_scope = len(scope_controls)
        control_ids_in_scope = [sc.organization_control_id for sc in scope_controls]

        # Controls with at least one accepted evidence
        controls_with_evidence = 0
        controls_assessed = 0
        for ctrl_id in control_ids_in_scope:
            ev_count = (
                db.query(EvidenceItem)
                .filter(
                    EvidenceItem.organization_control_id == ctrl_id,
                    EvidenceItem.organization_id == organization_id,
                    EvidenceItem.status == EvidenceStatusEnum.ACCEPTED,
                )
                .count()
            )
            if ev_count > 0:
                controls_with_evidence += 1

            ctrl = db.query(OrganizationControl).filter(OrganizationControl.id == ctrl_id).first()
            if ctrl and ctrl.status.value in ("IMPLEMENTED", "PARTIALLY_IMPLEMENTED"):
                controls_assessed += 1

        # Procedures
        procedures = (
            db.query(AuditProcedure)
            .filter(
                AuditProcedure.audit_id == audit_id,
                AuditProcedure.organization_id == organization_id,
            )
            .all()
        )
        proc_total = len(procedures)
        proc_counts = {r: 0 for r in ProcedureResultEnum}
        for p in procedures:
            proc_counts[p.result] = proc_counts.get(p.result, 0) + 1

        proc_completed = (
            proc_counts[ProcedureResultEnum.PASSED]
            + proc_counts[ProcedureResultEnum.PARTIALLY_PASSED]
            + proc_counts[ProcedureResultEnum.FAILED]
            + proc_counts[ProcedureResultEnum.NOT_APPLICABLE]
        )

        # Findings
        finding_links = (
            db.query(AuditFindingLink)
            .filter(
                AuditFindingLink.audit_id == audit_id,
                AuditFindingLink.organization_id == organization_id,
            )
            .options(joinedload(AuditFindingLink.finding))
            .all()
        )
        findings_total = len(finding_links)
        findings_open = sum(
            1 for fl in finding_links
            if fl.finding.status not in [FindingStatusEnum.RESOLVED, FindingStatusEnum.CLOSED, FindingStatusEnum.ACCEPTED_RISK]
        )
        findings_critical = sum(
            1 for fl in finding_links
            if fl.finding.severity == FindingSeverityEnum.CRITICAL
        )
        findings_high = sum(
            1 for fl in finding_links
            if fl.finding.severity == FindingSeverityEnum.HIGH
        )
        findings_in_remediation = sum(
            1 for fl in finding_links
            if fl.finding.status == FindingStatusEnum.IN_REMEDIATION
        )

        # Active exceptions on in-scope controls
        active_exceptions = 0
        for ctrl_id in control_ids_in_scope:
            exc_count = (
                db.query(SecurityException)
                .filter(
                    SecurityException.organization_id == organization_id,
                    SecurityException.linked_organization_control_id == ctrl_id,
                    SecurityException.status.in_([
                        ExceptionStatusEnum.APPROVED,
                        ExceptionStatusEnum.ACTIVE,
                    ]),
                )
                .count()
            )
            active_exceptions += exc_count

        # ── Deterministic Readiness Score ──────────────────────────────────
        # Formula:
        #   40% — procedure completion (completed / total if total > 0)
        #   30% — evidence coverage (controls_with_evidence / controls_in_scope)
        #   20% — no open critical/high findings penalty
        #   10% — no open findings penalty
        blockers: List[str] = []

        proc_score = (proc_completed / proc_total * 100) if proc_total > 0 else 0.0
        evidence_score = (controls_with_evidence / controls_in_scope * 100) if controls_in_scope > 0 else 0.0

        critical_high = findings_critical + findings_high
        finding_penalty = 0.0
        if critical_high > 0:
            finding_penalty = min(critical_high * 5.0, 20.0)
            blockers.append(f"{critical_high} critical/high finding(s) unresolved")
        if findings_open > 0:
            finding_penalty += min(findings_open * 2.0, 10.0)
            if findings_open > 0 and critical_high == 0:
                blockers.append(f"{findings_open} open finding(s) pending remediation")

        if proc_total == 0:
            blockers.append("No audit procedures defined")
        elif proc_counts[ProcedureResultEnum.NOT_STARTED] > 0:
            blockers.append(f"{proc_counts[ProcedureResultEnum.NOT_STARTED]} procedure(s) not yet started")

        if controls_in_scope == 0:
            blockers.append("No controls added to audit scope")
        elif controls_with_evidence < controls_in_scope:
            blockers.append(f"{controls_in_scope - controls_with_evidence} in-scope control(s) lack accepted evidence")

        raw_score = (proc_score * 0.40) + (evidence_score * 0.30) - finding_penalty
        raw_score = max(0.0, min(100.0, raw_score))

        if raw_score >= 85.0:
            band = "READY"
        elif raw_score >= 60.0:
            band = "SUBSTANTIALLY_READY"
        elif raw_score >= 35.0:
            band = "PARTIALLY_READY"
        else:
            band = "NOT_READY"

        return {
            "audit_id": audit_id,
            "audit_status": audit.status,
            "controls_in_scope": controls_in_scope,
            "controls_with_evidence": controls_with_evidence,
            "controls_assessed": controls_assessed,
            "procedures_total": proc_total,
            "procedures_not_started": proc_counts[ProcedureResultEnum.NOT_STARTED],
            "procedures_in_progress": proc_counts[ProcedureResultEnum.IN_PROGRESS],
            "procedures_passed": proc_counts[ProcedureResultEnum.PASSED],
            "procedures_partially_passed": proc_counts[ProcedureResultEnum.PARTIALLY_PASSED],
            "procedures_failed": proc_counts[ProcedureResultEnum.FAILED],
            "procedures_not_applicable": proc_counts[ProcedureResultEnum.NOT_APPLICABLE],
            "procedures_completed": proc_completed,
            "findings_total": findings_total,
            "findings_open": findings_open,
            "findings_critical": findings_critical,
            "findings_high": findings_high,
            "findings_in_remediation": findings_in_remediation,
            "active_exceptions_in_scope": active_exceptions,
            "readiness_score": round(raw_score, 1),
            "readiness_band": band,
            "readiness_blockers": blockers,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # STATS
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def get_stats(db: Session, organization_id: int) -> Dict[str, Any]:
        audits = db.query(Audit).filter(Audit.organization_id == organization_id).all()
        total = len(audits)
        planned = sum(1 for a in audits if a.status == AuditStatusEnum.PLANNED)
        in_progress = sum(1 for a in audits if a.status in _IN_PROGRESS_STATUSES)
        completed = sum(1 for a in audits if a.status == AuditStatusEnum.COMPLETED)
        closed = sum(1 for a in audits if a.status == AuditStatusEnum.CLOSED)
        unissued_opinion = sum(1 for a in audits if a.opinion == AuditOpinionEnum.UNISSUED and a.status != AuditStatusEnum.PLANNED)

        # Aggregate open findings across all active audits
        audit_ids = [a.id for a in audits if a.status in _IN_PROGRESS_STATUSES]
        open_findings = 0
        critical_findings = 0
        if audit_ids:
            links = (
                db.query(AuditFindingLink)
                .filter(
                    AuditFindingLink.audit_id.in_(audit_ids),
                    AuditFindingLink.organization_id == organization_id,
                )
                .options(joinedload(AuditFindingLink.finding))
                .all()
            )
            for fl in links:
                if fl.finding.status not in [FindingStatusEnum.RESOLVED, FindingStatusEnum.CLOSED]:
                    open_findings += 1
                if fl.finding.severity == FindingSeverityEnum.CRITICAL:
                    critical_findings += 1

        return {
            "total_audits": total,
            "planned_count": planned,
            "in_progress_count": in_progress,
            "completed_count": completed,
            "closed_count": closed,
            "open_findings_across_audits": open_findings,
            "critical_findings_count": critical_findings,
            "unissued_opinion_count": unissued_opinion,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Internal Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _get_audit(db: Session, audit_id: int, organization_id: int) -> Optional[Audit]:
    return (
        db.query(Audit)
        .filter(Audit.id == audit_id, Audit.organization_id == organization_id)
        .first()
    )


def _validate_user_in_org(db: Session, user_id: int, organization_id: int, role_label: str) -> User:
    u = (
        db.query(User)
        .filter(User.id == user_id, User.organization_id == organization_id, User.is_active.is_(True))
        .first()
    )
    if not u:
        raise ValueError(f"{role_label} ID {user_id} not found or inactive in your organization.")
    return u


def _audit_to_dict(a: Audit) -> Dict[str, Any]:
    return {
        "id": a.id,
        "organization_id": a.organization_id,
        "title": a.title,
        "audit_type": a.audit_type,
        "audit_reference": a.audit_reference,
        "objective": a.objective,
        "scope_description": a.scope_description,
        "methodology": a.methodology,
        "limitations": a.limitations,
        "summary": a.summary,
        "framework_id": a.framework_id,
        "lead_auditor_id": a.lead_auditor_id,
        "audit_team_notes": a.audit_team_notes,
        "planned_start_date": a.planned_start_date,
        "planned_end_date": a.planned_end_date,
        "actual_start_date": a.actual_start_date,
        "actual_end_date": a.actual_end_date,
        "status": a.status,
        "opinion": a.opinion,
        "opinion_issued_by_id": a.opinion_issued_by_id,
        "opinion_issued_at": a.opinion_issued_at,
        "opinion_notes": a.opinion_notes,
        "closed_at": a.closed_at,
        "closed_by_id": a.closed_by_id,
        "closure_notes": a.closure_notes,
        "created_by_id": a.created_by_id,
        "created_at": a.created_at,
        "updated_at": a.updated_at,
        "scope_controls_count": len(a.scope_controls) if a.scope_controls else 0,
        "procedures_count": len(a.procedures) if a.procedures else 0,
        "findings_count": len(a.finding_links) if a.finding_links else 0,
    }


def _scope_to_dict(sc: AuditScopeControl) -> Dict[str, Any]:
    return {
        "id": sc.id,
        "audit_id": sc.audit_id,
        "organization_control_id": sc.organization_control_id,
        "scope_notes": sc.scope_notes,
        "created_by_id": sc.created_by_id,
        "created_at": sc.created_at,
    }


def _procedure_to_dict(p: AuditProcedure) -> Dict[str, Any]:
    return {
        "id": p.id,
        "audit_id": p.audit_id,
        "organization_control_id": p.organization_control_id,
        "title": p.title,
        "objective": p.objective,
        "test_steps": p.test_steps,
        "expected_result": p.expected_result,
        "actual_result": p.actual_result,
        "assessment_method": p.assessment_method,
        "result": p.result,
        "execution_notes": p.execution_notes,
        "limitations": p.limitations,
        "tester_id": p.tester_id,
        "execution_date": p.execution_date,
        "created_by_id": p.created_by_id,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
        "evidence_count": len(p.evidence_links) if p.evidence_links else 0,
    }


def _finding_link_to_dict(fl: AuditFindingLink) -> Dict[str, Any]:
    return {
        "id": fl.id,
        "audit_id": fl.audit_id,
        "finding_id": fl.finding_id,
        "source_procedure_id": fl.source_procedure_id,
        "link_notes": fl.link_notes,
        "created_by_id": fl.created_by_id,
        "created_at": fl.created_at,
    }
