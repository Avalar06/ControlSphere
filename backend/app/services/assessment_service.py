from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from app.models.assessment import (
    Assessment,
    AssessmentConclusionEnum,
    AssessmentEvidence,
    AssessmentMethodEnum,
    AssessmentStatusEnum,
)
from app.models.control import OrganizationControl
from app.models.evidence import EvidenceItem
from app.models.finding import Finding
from app.models.user import User
from app.schemas.assessment import (
    AssessmentComplete,
    AssessmentCreate,
    AssessmentUpdate,
)


class AssessmentService:
    @staticmethod
    def list_assessments(
        db: Session,
        organization_id: int,
        organization_control_id: Optional[int] = None,
        assessor_id: Optional[int] = None,
        status: Optional[AssessmentStatusEnum] = None,
        conclusion: Optional[AssessmentConclusionEnum] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        query = (
            db.query(Assessment)
            .filter(Assessment.organization_id == organization_id)
            .options(
                joinedload(Assessment.assessor),
                joinedload(Assessment.organization_control).joinedload(OrganizationControl.subcategory),
                joinedload(Assessment.evidence_links),
                joinedload(Assessment.findings),
            )
        )

        if organization_control_id:
            query = query.filter(Assessment.organization_control_id == organization_control_id)
        if assessor_id:
            query = query.filter(Assessment.assessor_id == assessor_id)
        if status:
            query = query.filter(Assessment.status == status)
        if conclusion:
            query = query.filter(Assessment.conclusion == conclusion)
        if start_date:
            query = query.filter(Assessment.assessment_date >= start_date)
        if end_date:
            query = query.filter(Assessment.assessment_date <= end_date)

        assessments = query.order_by(Assessment.created_at.desc()).offset(skip).limit(limit).all()

        results = []
        for a in assessments:
            ctrl_id = a.organization_control.subcategory.identifier if a.organization_control and a.organization_control.subcategory else None
            ctrl_title = a.organization_control.subcategory.title if a.organization_control and a.organization_control.subcategory else None
            results.append({
                "id": a.id,
                "organization_id": a.organization_id,
                "organization_control_id": a.organization_control_id,
                "assessor_id": a.assessor_id,
                "assessment_method": a.assessment_method,
                "assessment_scope": a.assessment_scope,
                "assessment_date": a.assessment_date,
                "status": a.status,
                "conclusion": a.conclusion,
                "summary": a.summary,
                "limitations": a.limitations,
                "completed_at": a.completed_at,
                "created_at": a.created_at,
                "updated_at": a.updated_at,
                "assessor": a.assessor,
                "control_identifier": ctrl_id,
                "control_title": ctrl_title,
                "evidence_count": len(a.evidence_links),
                "findings_count": len(a.findings),
            })
        return results

    @staticmethod
    def get_assessment_by_id(
        db: Session, assessment_id: int, organization_id: int
    ) -> Optional[Dict[str, Any]]:
        a = (
            db.query(Assessment)
            .filter(
                Assessment.id == assessment_id,
                Assessment.organization_id == organization_id,
            )
            .options(
                joinedload(Assessment.assessor),
                joinedload(Assessment.organization_control).joinedload(OrganizationControl.subcategory),
                joinedload(Assessment.evidence_links).joinedload(AssessmentEvidence.evidence),
                joinedload(Assessment.findings),
            )
            .first()
        )
        if not a:
            return None

        ctrl_id = a.organization_control.subcategory.identifier if a.organization_control and a.organization_control.subcategory else None
        ctrl_title = a.organization_control.subcategory.title if a.organization_control and a.organization_control.subcategory else None

        return {
            "id": a.id,
            "organization_id": a.organization_id,
            "organization_control_id": a.organization_control_id,
            "assessor_id": a.assessor_id,
            "assessment_method": a.assessment_method,
            "assessment_scope": a.assessment_scope,
            "assessment_date": a.assessment_date,
            "status": a.status,
            "conclusion": a.conclusion,
            "summary": a.summary,
            "limitations": a.limitations,
            "completed_at": a.completed_at,
            "created_at": a.created_at,
            "updated_at": a.updated_at,
            "assessor": a.assessor,
            "control_identifier": ctrl_id,
            "control_title": ctrl_title,
            "evidence_count": len(a.evidence_links),
            "findings_count": len(a.findings),
            "evidence_links": a.evidence_links,
            "findings": a.findings,
        }

    @staticmethod
    def create_assessment(
        db: Session,
        obj_in: AssessmentCreate,
        organization_id: int,
        creator_id: Optional[int],
    ) -> Assessment:
        # Validate control belongs to tenant
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

        # Validate assessor belongs to same tenant and is active if provided
        if obj_in.assessor_id:
            assessor = (
                db.query(User)
                .filter(
                    User.id == obj_in.assessor_id,
                    User.organization_id == organization_id,
                    User.is_active.is_(True),
                )
                .first()
            )
            if not assessor:
                raise ValueError(f"Assessor ID {obj_in.assessor_id} not found or inactive in your organization.")

        assessment = Assessment(
            organization_id=organization_id,
            organization_control_id=obj_in.organization_control_id,
            assessor_id=obj_in.assessor_id or creator_id,
            assessment_method=obj_in.assessment_method,
            assessment_scope=obj_in.assessment_scope,
            assessment_date=obj_in.assessment_date,
            status=AssessmentStatusEnum.DRAFT,
            conclusion=AssessmentConclusionEnum.NOT_ASSESSED,
            summary=obj_in.summary,
            limitations=obj_in.limitations,
        )
        db.add(assessment)
        db.commit()
        db.refresh(assessment)
        return assessment

    @staticmethod
    def update_assessment(
        db: Session,
        assessment_id: int,
        organization_id: int,
        obj_in: AssessmentUpdate,
    ) -> Optional[Assessment]:
        assessment = (
            db.query(Assessment)
            .filter(
                Assessment.id == assessment_id,
                Assessment.organization_id == organization_id,
            )
            .first()
        )
        if not assessment:
            return None

        if assessment.status in [AssessmentStatusEnum.COMPLETED, AssessmentStatusEnum.SUPERSEDED]:
            raise ValueError(f"Cannot edit metadata of assessment in status '{assessment.status.value}'.")

        if obj_in.assessor_id is not None:
            assessor = (
                db.query(User)
                .filter(
                    User.id == obj_in.assessor_id,
                    User.organization_id == organization_id,
                    User.is_active.is_(True),
                )
                .first()
            )
            if not assessor:
                raise ValueError(f"Assessor ID {obj_in.assessor_id} not found or inactive in your organization.")

        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(assessment, field, value)

        db.add(assessment)
        db.commit()
        db.refresh(assessment)
        return assessment

    @staticmethod
    def start_assessment(
        db: Session, assessment_id: int, organization_id: int
    ) -> Optional[Assessment]:
        assessment = (
            db.query(Assessment)
            .filter(
                Assessment.id == assessment_id,
                Assessment.organization_id == organization_id,
            )
            .first()
        )
        if not assessment:
            return None

        if assessment.status != AssessmentStatusEnum.DRAFT:
            raise ValueError(f"Only DRAFT assessments can be started. Current status: '{assessment.status.value}'.")

        assessment.status = AssessmentStatusEnum.IN_PROGRESS
        db.add(assessment)
        db.commit()
        db.refresh(assessment)
        return assessment

    @staticmethod
    def complete_assessment(
        db: Session,
        assessment_id: int,
        organization_id: int,
        complete_in: AssessmentComplete,
    ) -> Optional[Assessment]:
        assessment = (
            db.query(Assessment)
            .filter(
                Assessment.id == assessment_id,
                Assessment.organization_id == organization_id,
            )
            .first()
        )
        if not assessment:
            return None

        if assessment.status != AssessmentStatusEnum.IN_PROGRESS:
            raise ValueError(f"Only IN_PROGRESS assessments can be completed. Current status: '{assessment.status.value}'.")

        if complete_in.conclusion == AssessmentConclusionEnum.NOT_ASSESSED:
            raise ValueError("A completed assessment must have an authoritative conclusion (EFFECTIVE, PARTIALLY_EFFECTIVE, or INEFFECTIVE).")

        assessment.status = AssessmentStatusEnum.COMPLETED
        assessment.conclusion = complete_in.conclusion
        assessment.summary = complete_in.summary
        if complete_in.limitations is not None:
            assessment.limitations = complete_in.limitations
        assessment.completed_at = datetime.now(timezone.utc)

        db.add(assessment)
        db.commit()
        db.refresh(assessment)
        return assessment

    @staticmethod
    def supersede_assessment(
        db: Session, assessment_id: int, organization_id: int
    ) -> Optional[Assessment]:
        assessment = (
            db.query(Assessment)
            .filter(
                Assessment.id == assessment_id,
                Assessment.organization_id == organization_id,
            )
            .first()
        )
        if not assessment:
            return None

        if assessment.status != AssessmentStatusEnum.COMPLETED:
            raise ValueError(f"Only COMPLETED assessments can be superseded. Current status: '{assessment.status.value}'.")

        assessment.status = AssessmentStatusEnum.SUPERSEDED
        db.add(assessment)
        db.commit()
        db.refresh(assessment)
        return assessment

    @staticmethod
    def link_evidence(
        db: Session,
        assessment_id: int,
        evidence_id: int,
        organization_id: int,
        created_by_id: Optional[int],
    ) -> AssessmentEvidence:
        assessment = (
            db.query(Assessment)
            .filter(
                Assessment.id == assessment_id,
                Assessment.organization_id == organization_id,
            )
            .first()
        )
        if not assessment:
            raise ValueError("Assessment not found in your organization.")

        if assessment.status in [AssessmentStatusEnum.COMPLETED, AssessmentStatusEnum.SUPERSEDED]:
            raise ValueError(f"Cannot link evidence to an assessment in status '{assessment.status.value}'.")

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
        if evidence.organization_control_id != assessment.organization_control_id:
            raise ValueError("Evidence item does not belong to the same control as the assessment.")

        # Prevent linking superseded evidence
        if evidence.status.value == "SUPERSEDED":
            raise ValueError("Cannot link superseded evidence artifact to an active assessment.")

        # Prevent duplicate linkage
        existing = (
            db.query(AssessmentEvidence)
            .filter(
                AssessmentEvidence.assessment_id == assessment_id,
                AssessmentEvidence.evidence_id == evidence_id,
            )
            .first()
        )
        if existing:
            return existing

        link = AssessmentEvidence(
            organization_id=organization_id,
            assessment_id=assessment_id,
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
        assessment_id: int,
        evidence_id: int,
        organization_id: int,
    ) -> bool:
        assessment = (
            db.query(Assessment)
            .filter(
                Assessment.id == assessment_id,
                Assessment.organization_id == organization_id,
            )
            .first()
        )
        if not assessment:
            return False

        if assessment.status in [AssessmentStatusEnum.COMPLETED, AssessmentStatusEnum.SUPERSEDED]:
            raise ValueError(f"Cannot unlink evidence from an assessment in status '{assessment.status.value}'.")

        link = (
            db.query(AssessmentEvidence)
            .filter(
                AssessmentEvidence.assessment_id == assessment_id,
                AssessmentEvidence.evidence_id == evidence_id,
                AssessmentEvidence.organization_id == organization_id,
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
        assessments = (
            db.query(Assessment)
            .filter(Assessment.organization_id == organization_id)
            .all()
        )

        total = len(assessments)
        draft = sum(1 for a in assessments if a.status == AssessmentStatusEnum.DRAFT)
        in_prog = sum(1 for a in assessments if a.status == AssessmentStatusEnum.IN_PROGRESS)
        completed = sum(1 for a in assessments if a.status == AssessmentStatusEnum.COMPLETED)
        superseded = sum(1 for a in assessments if a.status == AssessmentStatusEnum.SUPERSEDED)

        effective = sum(1 for a in assessments if a.conclusion == AssessmentConclusionEnum.EFFECTIVE)
        partially = sum(1 for a in assessments if a.conclusion == AssessmentConclusionEnum.PARTIALLY_EFFECTIVE)
        ineffective = sum(1 for a in assessments if a.conclusion == AssessmentConclusionEnum.INEFFECTIVE)
        not_assessed = sum(1 for a in assessments if a.conclusion == AssessmentConclusionEnum.NOT_ASSESSED)

        return {
            "total_assessments": total,
            "draft_count": draft,
            "in_progress_count": in_prog,
            "completed_count": completed,
            "superseded_count": superseded,
            "effective_count": effective,
            "partially_effective_count": partially,
            "ineffective_count": ineffective,
            "not_assessed_count": not_assessed,
        }
