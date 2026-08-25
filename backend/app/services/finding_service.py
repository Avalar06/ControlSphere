from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from app.core.risk_engine import calculate_overdue_status, calculate_risk_score
from app.models.assessment import Assessment
from app.models.control import OrganizationControl
from app.models.evidence import EvidenceItem
from app.models.finding import (
    Finding,
    FindingEvidence,
    FindingSeverityEnum,
    FindingStatusEnum,
    FindingTypeEnum,
)
from app.models.user import User
from app.schemas.finding import (
    FindingCreate,
    FindingRiskAcceptance,
    FindingStatusUpdate,
    FindingUpdate,
    FindingValidation,
)


class FindingService:
    @staticmethod
    def list_findings(
        db: Session,
        organization_id: int,
        organization_control_id: Optional[int] = None,
        assessment_id: Optional[int] = None,
        owner_id: Optional[int] = None,
        status: Optional[FindingStatusEnum] = None,
        severity: Optional[FindingSeverityEnum] = None,
        finding_type: Optional[FindingTypeEnum] = None,
        risk_band: Optional[str] = None,
        overdue_only: bool = False,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        query = (
            db.query(Finding)
            .filter(Finding.organization_id == organization_id)
            .options(
                joinedload(Finding.owner),
                joinedload(Finding.created_by),
                joinedload(Finding.resolved_by),
                joinedload(Finding.closed_by),
                joinedload(Finding.risk_accepted_by),
                joinedload(Finding.organization_control).joinedload(OrganizationControl.subcategory),
                joinedload(Finding.assessment),
                joinedload(Finding.evidence_links),
            )
        )

        if organization_control_id:
            query = query.filter(Finding.organization_control_id == organization_control_id)
        if assessment_id:
            query = query.filter(Finding.assessment_id == assessment_id)
        if owner_id:
            query = query.filter(Finding.owner_id == owner_id)
        if status:
            query = query.filter(Finding.status == status)
        if severity:
            query = query.filter(Finding.severity == severity)
        if finding_type:
            query = query.filter(Finding.finding_type == finding_type)
        if risk_band:
            query = query.filter(Finding.risk_band == risk_band)
        if search:
            query = query.filter(
                (Finding.title.ilike(f"%{search}%"))
                | (Finding.description.ilike(f"%{search}%"))
                | (Finding.recommendation.ilike(f"%{search}%"))
            )

        findings = query.order_by(Finding.risk_score.desc(), Finding.created_at.desc()).all()

        results = []
        today = date.today()
        for f in findings:
            overdue = calculate_overdue_status(f.status, f.due_date, today)
            if overdue_only and overdue != "OVERDUE":
                continue

            ctrl_id = f.organization_control.subcategory.identifier if f.organization_control and f.organization_control.subcategory else None
            ctrl_title = f.organization_control.subcategory.title if f.organization_control and f.organization_control.subcategory else None
            ass_summary = f.assessment.summary if f.assessment else None

            results.append({
                "id": f.id,
                "organization_id": f.organization_id,
                "organization_control_id": f.organization_control_id,
                "assessment_id": f.assessment_id,
                "title": f.title,
                "description": f.description,
                "finding_type": f.finding_type,
                "severity": f.severity,
                "impact": f.impact,
                "likelihood": f.likelihood,
                "risk_score": f.risk_score,
                "risk_band": f.risk_band,
                "recommendation": f.recommendation,
                "root_cause": f.root_cause,
                "owner_id": f.owner_id,
                "due_date": f.due_date,
                "overdue_status": overdue,
                "status": f.status,
                "remediation_plan": f.remediation_plan,
                "remediation_notes": f.remediation_notes,
                "resolution": f.resolution,
                "resolved_at": f.resolved_at,
                "resolved_by_id": f.resolved_by_id,
                "closed_at": f.closed_at,
                "closed_by_id": f.closed_by_id,
                "risk_acceptance_justification": f.risk_acceptance_justification,
                "risk_accepted_at": f.risk_accepted_at,
                "risk_accepted_by_id": f.risk_accepted_by_id,
                "risk_acceptance_expiry": f.risk_acceptance_expiry,
                "created_by_id": f.created_by_id,
                "created_at": f.created_at,
                "updated_at": f.updated_at,
                "owner": f.owner,
                "created_by": f.created_by,
                "resolved_by": f.resolved_by,
                "closed_by": f.closed_by,
                "risk_accepted_by": f.risk_accepted_by,
                "control_identifier": ctrl_id,
                "control_title": ctrl_title,
                "assessment_summary": ass_summary,
                "evidence_count": len(f.evidence_links),
            })

        return results[skip : skip + limit]

    @staticmethod
    def get_finding_by_id(
        db: Session, finding_id: int, organization_id: int
    ) -> Optional[Dict[str, Any]]:
        f = (
            db.query(Finding)
            .filter(
                Finding.id == finding_id,
                Finding.organization_id == organization_id,
            )
            .options(
                joinedload(Finding.owner),
                joinedload(Finding.created_by),
                joinedload(Finding.resolved_by),
                joinedload(Finding.closed_by),
                joinedload(Finding.risk_accepted_by),
                joinedload(Finding.organization_control).joinedload(OrganizationControl.subcategory),
                joinedload(Finding.assessment),
                joinedload(Finding.evidence_links).joinedload(FindingEvidence.evidence),
            )
            .first()
        )
        if not f:
            return None

        overdue = calculate_overdue_status(f.status, f.due_date)
        ctrl_id = f.organization_control.subcategory.identifier if f.organization_control and f.organization_control.subcategory else None
        ctrl_title = f.organization_control.subcategory.title if f.organization_control and f.organization_control.subcategory else None
        ass_summary = f.assessment.summary if f.assessment else None

        return {
            "id": f.id,
            "organization_id": f.organization_id,
            "organization_control_id": f.organization_control_id,
            "assessment_id": f.assessment_id,
            "title": f.title,
            "description": f.description,
            "finding_type": f.finding_type,
            "severity": f.severity,
            "impact": f.impact,
            "likelihood": f.likelihood,
            "risk_score": f.risk_score,
            "risk_band": f.risk_band,
            "recommendation": f.recommendation,
            "root_cause": f.root_cause,
            "owner_id": f.owner_id,
            "due_date": f.due_date,
            "overdue_status": overdue,
            "status": f.status,
            "remediation_plan": f.remediation_plan,
            "remediation_notes": f.remediation_notes,
            "resolution": f.resolution,
            "resolved_at": f.resolved_at,
            "resolved_by_id": f.resolved_by_id,
            "closed_at": f.closed_at,
            "closed_by_id": f.closed_by_id,
            "risk_acceptance_justification": f.risk_acceptance_justification,
            "risk_accepted_at": f.risk_accepted_at,
            "risk_accepted_by_id": f.risk_accepted_by_id,
            "risk_acceptance_expiry": f.risk_acceptance_expiry,
            "created_by_id": f.created_by_id,
            "created_at": f.created_at,
            "updated_at": f.updated_at,
            "owner": f.owner,
            "created_by": f.created_by,
            "resolved_by": f.resolved_by,
            "closed_by": f.closed_by,
            "risk_accepted_by": f.risk_accepted_by,
            "control_identifier": ctrl_id,
            "control_title": ctrl_title,
            "assessment_summary": ass_summary,
            "evidence_count": len(f.evidence_links),
            "evidence_links": f.evidence_links,
        }

    @staticmethod
    def create_finding(
        db: Session,
        obj_in: FindingCreate,
        organization_id: int,
        creator_id: Optional[int],
    ) -> Finding:
        # Validate control
        ctrl = (
            db.query(OrganizationControl)
            .filter(
                OrganizationControl.id == obj_in.organization_control_id,
                OrganizationControl.organization_id == organization_id,
            )
            .first()
        )
        if not ctrl:
            raise ValueError(f"Organization control ID {obj_in.organization_control_id} not found in your organization.")

        # Validate assessment if supplied
        if obj_in.assessment_id:
            ass = (
                db.query(Assessment)
                .filter(
                    Assessment.id == obj_in.assessment_id,
                    Assessment.organization_id == organization_id,
                )
                .first()
            )
            if not ass:
                raise ValueError(f"Assessment ID {obj_in.assessment_id} not found in your organization.")
            if ass.organization_control_id != obj_in.organization_control_id:
                raise ValueError("Assessment does not belong to the specified control.")

        # Validate owner if supplied
        if obj_in.owner_id:
            owner = (
                db.query(User)
                .filter(
                    User.id == obj_in.owner_id,
                    User.organization_id == organization_id,
                )
                .first()
            )
            if not owner:
                raise ValueError(f"Owner ID {obj_in.owner_id} not found in your organization.")

        # Deterministic Risk Calculation
        score, band = calculate_risk_score(obj_in.impact, obj_in.likelihood)

        finding = Finding(
            organization_id=organization_id,
            organization_control_id=obj_in.organization_control_id,
            assessment_id=obj_in.assessment_id,
            title=obj_in.title.strip(),
            description=obj_in.description.strip(),
            finding_type=obj_in.finding_type,
            severity=obj_in.severity,
            impact=obj_in.impact,
            likelihood=obj_in.likelihood,
            risk_score=score,
            risk_band=band,
            recommendation=obj_in.recommendation.strip(),
            root_cause=obj_in.root_cause.strip() if obj_in.root_cause else None,
            owner_id=obj_in.owner_id,
            due_date=obj_in.due_date,
            status=FindingStatusEnum.OPEN,
            remediation_plan=obj_in.remediation_plan,
            created_by_id=creator_id,
        )
        db.add(finding)
        db.commit()
        db.refresh(finding)
        return finding

    @staticmethod
    def update_finding(
        db: Session,
        finding_id: int,
        organization_id: int,
        obj_in: FindingUpdate,
    ) -> Optional[Finding]:
        finding = (
            db.query(Finding)
            .filter(
                Finding.id == finding_id,
                Finding.organization_id == organization_id,
            )
            .first()
        )
        if not finding:
            return None

        if finding.status == FindingStatusEnum.CLOSED:
            raise ValueError("Closed findings cannot be modified.")

        if obj_in.owner_id is not None:
            owner = (
                db.query(User)
                .filter(
                    User.id == obj_in.owner_id,
                    User.organization_id == organization_id,
                )
                .first()
            )
            if not owner:
                raise ValueError(f"Owner ID {obj_in.owner_id} not found in your organization.")

        update_data = obj_in.model_dump(exclude_unset=True)

        # Recalculate deterministic risk if impact or likelihood updated
        new_impact = update_data.get("impact", finding.impact)
        new_likelihood = update_data.get("likelihood", finding.likelihood)
        if "impact" in update_data or "likelihood" in update_data:
            score, band = calculate_risk_score(new_impact, new_likelihood)
            finding.risk_score = score
            finding.risk_band = band

        for field, value in update_data.items():
            setattr(finding, field, value)

        db.add(finding)
        db.commit()
        db.refresh(finding)
        return finding

    @staticmethod
    def update_status(
        db: Session,
        finding_id: int,
        organization_id: int,
        status_in: FindingStatusUpdate,
        user_id: Optional[int],
    ) -> Optional[Finding]:
        finding = (
            db.query(Finding)
            .filter(
                Finding.id == finding_id,
                Finding.organization_id == organization_id,
            )
            .first()
        )
        if not finding:
            return None

        target = status_in.status
        current = finding.status

        # Transition validation rules
        if current == FindingStatusEnum.CLOSED:
            raise ValueError("Closed findings cannot transition to another status.")

        if target == FindingStatusEnum.IN_REMEDIATION:
            if current not in [FindingStatusEnum.OPEN, FindingStatusEnum.PENDING_VALIDATION]:
                raise ValueError(f"Cannot transition to IN_REMEDIATION from '{current.value}'.")

        elif target == FindingStatusEnum.PENDING_VALIDATION:
            if current not in [FindingStatusEnum.IN_REMEDIATION, FindingStatusEnum.OPEN]:
                raise ValueError(f"Cannot submit for validation from status '{current.value}'.")
            if not status_in.resolution and not finding.resolution:
                raise ValueError("A documented resolution is required when submitting a finding for validation.")

        elif target == FindingStatusEnum.CLOSED:
            if current not in [FindingStatusEnum.RESOLVED, FindingStatusEnum.ACCEPTED_RISK]:
                raise ValueError(f"Findings must be RESOLVED or ACCEPTED_RISK before closing. Current status: '{current.value}'.")
            finding.closed_at = datetime.now(timezone.utc)
            finding.closed_by_id = user_id

        elif target == FindingStatusEnum.RESOLVED:
            # Requires explicit validation workflow
            raise ValueError("Use the authoritative validation workflow (/validate) to resolve a finding.")

        elif target == FindingStatusEnum.ACCEPTED_RISK:
            # Requires explicit risk acceptance workflow
            raise ValueError("Use the formal risk acceptance workflow (/risk-acceptance) to accept finding risk.")

        if status_in.notes:
            finding.remediation_notes = (finding.remediation_notes or "") + f"\n[{datetime.now(timezone.utc).isoformat()}] {status_in.notes}"
        if status_in.resolution:
            finding.resolution = status_in.resolution

        finding.status = target
        db.add(finding)
        db.commit()
        db.refresh(finding)
        return finding

    @staticmethod
    def validate_finding(
        db: Session,
        finding_id: int,
        organization_id: int,
        validation_in: FindingValidation,
        validator_id: Optional[int],
    ) -> Optional[Finding]:
        finding = (
            db.query(Finding)
            .filter(
                Finding.id == finding_id,
                Finding.organization_id == organization_id,
            )
            .first()
        )
        if not finding:
            return None

        if finding.status != FindingStatusEnum.PENDING_VALIDATION:
            raise ValueError(f"Only findings in PENDING_VALIDATION can be validated. Current status: '{finding.status.value}'.")

        note_prefix = f"[{datetime.now(timezone.utc).isoformat()}] Validation {'PASSED' if validation_in.is_valid else 'FAILED'}: {validation_in.validation_notes}"
        finding.remediation_notes = (finding.remediation_notes or "") + f"\n{note_prefix}"

        if validation_in.is_valid:
            finding.status = FindingStatusEnum.RESOLVED
            finding.resolved_at = datetime.now(timezone.utc)
            finding.resolved_by_id = validator_id
        else:
            # Transition back to remediation for further action
            finding.status = FindingStatusEnum.IN_REMEDIATION

        db.add(finding)
        db.commit()
        db.refresh(finding)
        return finding

    @staticmethod
    def accept_risk(
        db: Session,
        finding_id: int,
        organization_id: int,
        risk_in: FindingRiskAcceptance,
        acceptor_id: Optional[int],
    ) -> Optional[Finding]:
        finding = (
            db.query(Finding)
            .filter(
                Finding.id == finding_id,
                Finding.organization_id == organization_id,
            )
            .first()
        )
        if not finding:
            return None

        if finding.status == FindingStatusEnum.CLOSED:
            raise ValueError("Cannot perform risk acceptance on a closed finding.")

        finding.status = FindingStatusEnum.ACCEPTED_RISK
        finding.risk_acceptance_justification = risk_in.justification.strip()
        finding.risk_acceptance_expiry = risk_in.expiry_date
        finding.risk_accepted_at = datetime.now(timezone.utc)
        finding.risk_accepted_by_id = acceptor_id

        db.add(finding)
        db.commit()
        db.refresh(finding)
        return finding

    @staticmethod
    def link_evidence(
        db: Session,
        finding_id: int,
        evidence_id: int,
        organization_id: int,
        created_by_id: Optional[int],
    ) -> FindingEvidence:
        finding = (
            db.query(Finding)
            .filter(
                Finding.id == finding_id,
                Finding.organization_id == organization_id,
            )
            .first()
        )
        if not finding:
            raise ValueError("Finding not found in your organization.")

        if finding.status == FindingStatusEnum.CLOSED:
            raise ValueError("Cannot link evidence to a closed finding.")

        evidence = (
            db.query(EvidenceItem)
            .filter(
                EvidenceItem.id == evidence_id,
                EvidenceItem.organization_id == organization_id,
            )
            .first()
        )
        if not evidence:
            raise ValueError("Evidence item not found in your organization.")

        # Cross-control verification: evidence must belong to the same control
        if evidence.organization_control_id != finding.organization_control_id:
            raise ValueError("Evidence item does not belong to the same control as the finding.")

        # Prevent duplicate linkage
        existing = (
            db.query(FindingEvidence)
            .filter(
                FindingEvidence.finding_id == finding_id,
                FindingEvidence.evidence_id == evidence_id,
            )
            .first()
        )
        if existing:
            return existing

        link = FindingEvidence(
            organization_id=organization_id,
            finding_id=finding_id,
            evidence_id=evidence_id,
            created_by_id=created_by_id,
        )
        db.add(link)
        db.commit()
        db.refresh(link)
        return link

    @staticmethod
    def unlink_evidence(
        db: Session,
        finding_id: int,
        evidence_id: int,
        organization_id: int,
    ) -> bool:
        finding = (
            db.query(Finding)
            .filter(
                Finding.id == finding_id,
                Finding.organization_id == organization_id,
            )
            .first()
        )
        if not finding:
            return False

        if finding.status == FindingStatusEnum.CLOSED:
            raise ValueError("Cannot unlink evidence from a closed finding.")

        link = (
            db.query(FindingEvidence)
            .filter(
                FindingEvidence.finding_id == finding_id,
                FindingEvidence.evidence_id == evidence_id,
                FindingEvidence.organization_id == organization_id,
            )
            .first()
        )
        if not link:
            return False

        db.delete(link)
        db.commit()
        return True

    @staticmethod
    def get_stats(db: Session, organization_id: int) -> Dict[str, Any]:
        findings = (
            db.query(Finding)
            .filter(Finding.organization_id == organization_id)
            .all()
        )

        total = len(findings)
        open_cnt = sum(1 for f in findings if f.status == FindingStatusEnum.OPEN)
        in_rem = sum(1 for f in findings if f.status == FindingStatusEnum.IN_REMEDIATION)
        pending_val = sum(1 for f in findings if f.status == FindingStatusEnum.PENDING_VALIDATION)
        resolved = sum(1 for f in findings if f.status == FindingStatusEnum.RESOLVED)
        accepted_risk = sum(1 for f in findings if f.status == FindingStatusEnum.ACCEPTED_RISK)
        closed = sum(1 for f in findings if f.status == FindingStatusEnum.CLOSED)

        crit = sum(1 for f in findings if f.severity == FindingSeverityEnum.CRITICAL)
        high = sum(1 for f in findings if f.severity == FindingSeverityEnum.HIGH)
        med = sum(1 for f in findings if f.severity == FindingSeverityEnum.MEDIUM)
        low = sum(1 for f in findings if f.severity == FindingSeverityEnum.LOW)
        info = sum(1 for f in findings if f.severity == FindingSeverityEnum.INFORMATIONAL)

        today = date.today()
        overdue_cnt = 0
        due_soon_cnt = 0
        on_track_cnt = 0

        for f in findings:
            status_calc = calculate_overdue_status(f.status, f.due_date, today)
            if status_calc == "OVERDUE":
                overdue_cnt += 1
            elif status_calc == "DUE_SOON":
                due_soon_cnt += 1
            elif status_calc == "ON_TRACK":
                on_track_cnt += 1

        return {
            "total_findings": total,
            "open_count": open_cnt,
            "in_remediation_count": in_rem,
            "pending_validation_count": pending_val,
            "resolved_count": resolved,
            "accepted_risk_count": accepted_risk,
            "closed_count": closed,
            "critical_count": crit,
            "high_count": high,
            "medium_count": med,
            "low_count": low,
            "informational_count": info,
            "overdue_count": overdue_cnt,
            "due_soon_count": due_soon_cnt,
            "on_track_count": on_track_cnt,
        }
