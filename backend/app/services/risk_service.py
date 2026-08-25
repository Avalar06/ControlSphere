from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from app.core.risk_engine import (
    calculate_appetite_status,
    calculate_risk_score,
    calculate_treatment_overdue_status,
    generate_risk_heatmap_matrix,
)
from app.models.control import OrganizationControl
from app.models.finding import Finding
from app.models.risk import (
    Risk,
    RiskCategoryEnum,
    RiskControlLink,
    RiskFindingLink,
    RiskSourceEnum,
    RiskStatusEnum,
    RiskTreatmentStrategyEnum,
)
from app.models.user import User
from app.schemas.risk import (
    RiskAcceptance,
    RiskCreate,
    RiskStatusUpdate,
    RiskUpdate,
)


class RiskService:
    @staticmethod
    def list_risks(
        db: Session,
        organization_id: int,
        status: Optional[RiskStatusEnum] = None,
        risk_category: Optional[RiskCategoryEnum] = None,
        risk_source: Optional[RiskSourceEnum] = None,
        treatment_strategy: Optional[RiskTreatmentStrategyEnum] = None,
        inherent_band: Optional[str] = None,
        appetite_status: Optional[str] = None,
        owner_id: Optional[int] = None,
        overdue_treatment: bool = False,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        query = (
            db.query(Risk)
            .filter(Risk.organization_id == organization_id)
            .options(
                joinedload(Risk.owner),
                joinedload(Risk.treatment_owner),
                joinedload(Risk.created_by),
                joinedload(Risk.risk_accepted_by),
                joinedload(Risk.control_links),
                joinedload(Risk.finding_links),
            )
        )

        if status:
            query = query.filter(Risk.status == status)
        if risk_category:
            query = query.filter(Risk.risk_category == risk_category)
        if risk_source:
            query = query.filter(Risk.risk_source == risk_source)
        if treatment_strategy:
            query = query.filter(Risk.treatment_strategy == treatment_strategy)
        if inherent_band:
            query = query.filter(Risk.inherent_band == inherent_band)
        if appetite_status:
            query = query.filter(Risk.appetite_status == appetite_status)
        if owner_id:
            query = query.filter(Risk.owner_id == owner_id)
        if search:
            query = query.filter(
                (Risk.title.ilike(f"%{search}%"))
                | (Risk.description.ilike(f"%{search}%"))
                | (Risk.treatment_plan.ilike(f"%{search}%"))
            )

        risks = query.order_by(Risk.inherent_score.desc(), Risk.created_at.desc()).all()

        results = []
        today = date.today()
        for r in risks:
            overdue = calculate_treatment_overdue_status(r.status.value, r.treatment_due_date, today)
            if overdue_treatment and overdue != "OVERDUE":
                continue

            results.append({
                "id": r.id,
                "organization_id": r.organization_id,
                "title": r.title,
                "description": r.description,
                "risk_category": r.risk_category,
                "risk_source": r.risk_source,
                "owner_id": r.owner_id,
                "inherent_impact": r.inherent_impact,
                "inherent_likelihood": r.inherent_likelihood,
                "inherent_score": r.inherent_score,
                "inherent_band": r.inherent_band,
                "residual_impact": r.residual_impact,
                "residual_likelihood": r.residual_likelihood,
                "residual_score": r.residual_score,
                "residual_band": r.residual_band,
                "target_risk_band": r.target_risk_band,
                "appetite_status": r.appetite_status,
                "status": r.status,
                "treatment_strategy": r.treatment_strategy,
                "treatment_plan": r.treatment_plan,
                "treatment_owner_id": r.treatment_owner_id,
                "treatment_due_date": r.treatment_due_date,
                "treatment_overdue_status": overdue,
                "review_date": r.review_date,
                "risk_acceptance_justification": r.risk_acceptance_justification,
                "risk_accepted_at": r.risk_accepted_at,
                "risk_accepted_by_id": r.risk_accepted_by_id,
                "risk_acceptance_expiry": r.risk_acceptance_expiry,
                "created_by_id": r.created_by_id,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
                "owner": r.owner,
                "treatment_owner": r.treatment_owner,
                "created_by": r.created_by,
                "risk_accepted_by": r.risk_accepted_by,
                "linked_controls_count": len(r.control_links),
                "linked_findings_count": len(r.finding_links),
            })

        return results[skip : skip + limit]

    @staticmethod
    def get_risk_by_id(
        db: Session, risk_id: int, organization_id: int
    ) -> Optional[Dict[str, Any]]:
        r = (
            db.query(Risk)
            .filter(
                Risk.id == risk_id,
                Risk.organization_id == organization_id,
            )
            .options(
                joinedload(Risk.owner),
                joinedload(Risk.treatment_owner),
                joinedload(Risk.created_by),
                joinedload(Risk.risk_accepted_by),
                joinedload(Risk.control_links).joinedload(RiskControlLink.organization_control).joinedload(OrganizationControl.subcategory),
                joinedload(Risk.finding_links).joinedload(RiskFindingLink.finding),
            )
            .first()
        )
        if not r:
            return None

        overdue = calculate_treatment_overdue_status(r.status.value, r.treatment_due_date)

        return {
            "id": r.id,
            "organization_id": r.organization_id,
            "title": r.title,
            "description": r.description,
            "risk_category": r.risk_category,
            "risk_source": r.risk_source,
            "owner_id": r.owner_id,
            "inherent_impact": r.inherent_impact,
            "inherent_likelihood": r.inherent_likelihood,
            "inherent_score": r.inherent_score,
            "inherent_band": r.inherent_band,
            "residual_impact": r.residual_impact,
            "residual_likelihood": r.residual_likelihood,
            "residual_score": r.residual_score,
            "residual_band": r.residual_band,
            "target_risk_band": r.target_risk_band,
            "appetite_status": r.appetite_status,
            "status": r.status,
            "treatment_strategy": r.treatment_strategy,
            "treatment_plan": r.treatment_plan,
            "treatment_owner_id": r.treatment_owner_id,
            "treatment_due_date": r.treatment_due_date,
            "treatment_overdue_status": overdue,
            "review_date": r.review_date,
            "risk_acceptance_justification": r.risk_acceptance_justification,
            "risk_accepted_at": r.risk_accepted_at,
            "risk_accepted_by_id": r.risk_accepted_by_id,
            "risk_acceptance_expiry": r.risk_acceptance_expiry,
            "created_by_id": r.created_by_id,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
            "owner": r.owner,
            "treatment_owner": r.treatment_owner,
            "created_by": r.created_by,
            "risk_accepted_by": r.risk_accepted_by,
            "linked_controls_count": len(r.control_links),
            "linked_findings_count": len(r.finding_links),
            "control_links": r.control_links,
            "finding_links": r.finding_links,
        }

    @staticmethod
    def create_risk(
        db: Session,
        obj_in: RiskCreate,
        organization_id: int,
        creator_id: Optional[int],
    ) -> Risk:
        # Validate owner if provided
        if obj_in.owner_id:
            owner = (
                db.query(User)
                .filter(
                    User.id == obj_in.owner_id,
                    User.organization_id == organization_id,
                    User.is_active.is_(True),
                )
                .first()
            )
            if not owner:
                raise ValueError(f"Owner ID {obj_in.owner_id} not found or inactive in your organization.")

        # Validate treatment owner if provided
        if obj_in.treatment_owner_id:
            t_owner = (
                db.query(User)
                .filter(
                    User.id == obj_in.treatment_owner_id,
                    User.organization_id == organization_id,
                    User.is_active.is_(True),
                )
                .first()
            )
            if not t_owner:
                raise ValueError(f"Treatment owner ID {obj_in.treatment_owner_id} not found or inactive in your organization.")

        # Calculate deterministic inherent score & band
        inh_score, inh_band = calculate_risk_score(obj_in.inherent_impact, obj_in.inherent_likelihood)
        appetite = calculate_appetite_status(inh_score, obj_in.target_risk_band)

        risk = Risk(
            organization_id=organization_id,
            title=obj_in.title.strip(),
            description=obj_in.description.strip(),
            risk_category=obj_in.risk_category,
            risk_source=obj_in.risk_source,
            owner_id=obj_in.owner_id,
            inherent_impact=obj_in.inherent_impact,
            inherent_likelihood=obj_in.inherent_likelihood,
            inherent_score=inh_score,
            inherent_band=inh_band,
            target_risk_band=obj_in.target_risk_band or "MODERATE",
            appetite_status=appetite,
            status=RiskStatusEnum.IDENTIFIED,
            treatment_strategy=obj_in.treatment_strategy,
            treatment_plan=obj_in.treatment_plan,
            treatment_owner_id=obj_in.treatment_owner_id,
            treatment_due_date=obj_in.treatment_due_date,
            review_date=obj_in.review_date,
            created_by_id=creator_id,
        )
        db.add(risk)
        db.commit()
        db.refresh(risk)
        return risk

    @staticmethod
    def update_risk(
        db: Session,
        risk_id: int,
        organization_id: int,
        obj_in: RiskUpdate,
    ) -> Optional[Risk]:
        risk = (
            db.query(Risk)
            .filter(
                Risk.id == risk_id,
                Risk.organization_id == organization_id,
            )
            .first()
        )
        if not risk:
            return None

        if risk.status == RiskStatusEnum.CLOSED:
            raise ValueError("Closed risks cannot be modified.")

        if obj_in.owner_id is not None:
            owner = (
                db.query(User)
                .filter(
                    User.id == obj_in.owner_id,
                    User.organization_id == organization_id,
                    User.is_active.is_(True),
                )
                .first()
            )
            if not owner:
                raise ValueError(f"Owner ID {obj_in.owner_id} not found or inactive in your organization.")

        if obj_in.treatment_owner_id is not None:
            t_owner = (
                db.query(User)
                .filter(
                    User.id == obj_in.treatment_owner_id,
                    User.organization_id == organization_id,
                    User.is_active.is_(True),
                )
                .first()
            )
            if not t_owner:
                raise ValueError(f"Treatment owner ID {obj_in.treatment_owner_id} not found or inactive in your organization.")

        update_data = obj_in.model_dump(exclude_unset=True)

        # Inherent score recalculation
        new_inh_imp = update_data.get("inherent_impact", risk.inherent_impact)
        new_inh_lik = update_data.get("inherent_likelihood", risk.inherent_likelihood)
        if "inherent_impact" in update_data or "inherent_likelihood" in update_data:
            inh_score, inh_band = calculate_risk_score(new_inh_imp, new_inh_lik)
            risk.inherent_impact = new_inh_imp
            risk.inherent_likelihood = new_inh_lik
            risk.inherent_score = inh_score
            risk.inherent_band = inh_band

        # Residual score recalculation if provided
        new_res_imp = update_data.get("residual_impact", risk.residual_impact)
        new_res_lik = update_data.get("residual_likelihood", risk.residual_likelihood)
        if new_res_imp is not None and new_res_lik is not None:
            res_score, res_band = calculate_risk_score(new_res_imp, new_res_lik)
            risk.residual_impact = new_res_imp
            risk.residual_likelihood = new_res_lik
            risk.residual_score = res_score
            risk.residual_band = res_band
        elif "residual_impact" in update_data or "residual_likelihood" in update_data:
            if new_res_imp is None or new_res_lik is None:
                risk.residual_impact = None
                risk.residual_likelihood = None
                risk.residual_score = None
                risk.residual_band = None

        # Re-evaluate appetite based on residual (if available) or inherent
        target_band = update_data.get("target_risk_band", risk.target_risk_band)
        eval_score = risk.residual_score if risk.residual_score is not None else risk.inherent_score
        risk.appetite_status = calculate_appetite_status(eval_score, target_band)

        for field, value in update_data.items():
            if field not in ["inherent_impact", "inherent_likelihood", "residual_impact", "residual_likelihood"]:
                setattr(risk, field, value)

        db.add(risk)
        db.commit()
        db.refresh(risk)
        return risk

    @staticmethod
    def update_status(
        db: Session,
        risk_id: int,
        organization_id: int,
        status_in: RiskStatusUpdate,
    ) -> Optional[Risk]:
        risk = (
            db.query(Risk)
            .filter(
                Risk.id == risk_id,
                Risk.organization_id == organization_id,
            )
            .first()
        )
        if not risk:
            return None

        current = risk.status
        target = status_in.status

        # Strict State Machine Transition Matrix
        if current == RiskStatusEnum.CLOSED:
            raise ValueError("Closed risks cannot transition to another status.")

        if target == RiskStatusEnum.IDENTIFIED:
            raise ValueError("Risks cannot transition back to IDENTIFIED status.")

        elif target == RiskStatusEnum.ASSESSED:
            if current != RiskStatusEnum.IDENTIFIED:
                raise ValueError(f"Cannot transition to ASSESSED from status '{current.value}'.")

        elif target == RiskStatusEnum.TREATMENT_PLANNED:
            if current not in [RiskStatusEnum.ASSESSED, RiskStatusEnum.MONITORING]:
                raise ValueError(f"Cannot transition to TREATMENT_PLANNED from status '{current.value}'.")

        elif target == RiskStatusEnum.MITIGATING:
            if current not in [RiskStatusEnum.TREATMENT_PLANNED, RiskStatusEnum.ASSESSED]:
                raise ValueError(f"Cannot transition to MITIGATING from status '{current.value}'.")

        elif target == RiskStatusEnum.MONITORING:
            if current not in [RiskStatusEnum.MITIGATING, RiskStatusEnum.ACCEPTED]:
                raise ValueError(f"Cannot transition to MONITORING from status '{current.value}'.")

        elif target == RiskStatusEnum.ACCEPTED:
            raise ValueError("Use the formal risk acceptance workflow (/risk-acceptance) to accept risk.")

        elif target == RiskStatusEnum.CLOSED:
            if current not in [RiskStatusEnum.MONITORING, RiskStatusEnum.ACCEPTED]:
                raise ValueError(f"Risks must be in MONITORING or ACCEPTED before closing. Current status: '{current.value}'.")

        risk.status = target
        db.add(risk)
        db.commit()
        db.refresh(risk)
        return risk

    @staticmethod
    def accept_risk(
        db: Session,
        risk_id: int,
        organization_id: int,
        acceptance_in: RiskAcceptance,
        acceptor_id: Optional[int],
    ) -> Optional[Risk]:
        risk = (
            db.query(Risk)
            .filter(
                Risk.id == risk_id,
                Risk.organization_id == organization_id,
            )
            .first()
        )
        if not risk:
            return None

        if risk.status == RiskStatusEnum.IDENTIFIED:
            raise ValueError("Risks must be assessed before formal acceptance.")

        if risk.status in [RiskStatusEnum.CLOSED, RiskStatusEnum.ACCEPTED]:
            raise ValueError(f"Cannot accept risk in status '{risk.status.value}'.")

        if acceptance_in.expiry_date and acceptance_in.expiry_date <= date.today():
            raise ValueError("Risk acceptance expiry date must be in the future.")

        risk.status = RiskStatusEnum.ACCEPTED
        risk.treatment_strategy = RiskTreatmentStrategyEnum.ACCEPT
        risk.risk_acceptance_justification = acceptance_in.justification.strip()
        risk.risk_acceptance_expiry = acceptance_in.expiry_date
        risk.risk_accepted_at = datetime.now(timezone.utc)
        risk.risk_accepted_by_id = acceptor_id

        db.add(risk)
        db.commit()
        db.refresh(risk)
        return risk

    @staticmethod
    def link_control(
        db: Session,
        risk_id: int,
        organization_control_id: int,
        organization_id: int,
        creator_id: Optional[int],
    ) -> RiskControlLink:
        risk = (
            db.query(Risk)
            .filter(Risk.id == risk_id, Risk.organization_id == organization_id)
            .first()
        )
        if not risk:
            raise ValueError("Risk not found in your organization.")

        if risk.status == RiskStatusEnum.CLOSED:
            raise ValueError("Cannot link controls to a closed risk.")

        ctrl = (
            db.query(OrganizationControl)
            .filter(
                OrganizationControl.id == organization_control_id,
                OrganizationControl.organization_id == organization_id,
            )
            .first()
        )
        if not ctrl:
            raise ValueError("Organization control not found in your organization.")

        existing = (
            db.query(RiskControlLink)
            .filter(
                RiskControlLink.risk_id == risk_id,
                RiskControlLink.organization_control_id == organization_control_id,
            )
            .first()
        )
        if existing:
            return existing

        link = RiskControlLink(
            organization_id=organization_id,
            risk_id=risk_id,
            organization_control_id=organization_control_id,
            created_by_id=creator_id,
        )
        db.add(link)
        db.commit()
        db.refresh(link)
        return link

    @staticmethod
    def unlink_control(
        db: Session,
        risk_id: int,
        organization_control_id: int,
        organization_id: int,
    ) -> bool:
        risk = (
            db.query(Risk)
            .filter(Risk.id == risk_id, Risk.organization_id == organization_id)
            .first()
        )
        if not risk:
            return False

        if risk.status == RiskStatusEnum.CLOSED:
            raise ValueError("Cannot unlink controls from a closed risk.")

        link = (
            db.query(RiskControlLink)
            .filter(
                RiskControlLink.risk_id == risk_id,
                RiskControlLink.organization_control_id == organization_control_id,
                RiskControlLink.organization_id == organization_id,
            )
            .first()
        )
        if not link:
            return False

        db.delete(link)
        db.commit()
        return True

    @staticmethod
    def link_finding(
        db: Session,
        risk_id: int,
        finding_id: int,
        organization_id: int,
        creator_id: Optional[int],
    ) -> RiskFindingLink:
        risk = (
            db.query(Risk)
            .filter(Risk.id == risk_id, Risk.organization_id == organization_id)
            .first()
        )
        if not risk:
            raise ValueError("Risk not found in your organization.")

        if risk.status == RiskStatusEnum.CLOSED:
            raise ValueError("Cannot link findings to a closed risk.")

        find = (
            db.query(Finding)
            .filter(
                Finding.id == finding_id,
                Finding.organization_id == organization_id,
            )
            .first()
        )
        if not find:
            raise ValueError("Finding not found in your organization.")

        existing = (
            db.query(RiskFindingLink)
            .filter(
                RiskFindingLink.risk_id == risk_id,
                RiskFindingLink.finding_id == finding_id,
            )
            .first()
        )
        if existing:
            return existing

        link = RiskFindingLink(
            organization_id=organization_id,
            risk_id=risk_id,
            finding_id=finding_id,
            created_by_id=creator_id,
        )
        db.add(link)
        db.commit()
        db.refresh(link)
        return link

    @staticmethod
    def unlink_finding(
        db: Session,
        risk_id: int,
        finding_id: int,
        organization_id: int,
    ) -> bool:
        risk = (
            db.query(Risk)
            .filter(Risk.id == risk_id, Risk.organization_id == organization_id)
            .first()
        )
        if not risk:
            return False

        if risk.status == RiskStatusEnum.CLOSED:
            raise ValueError("Cannot unlink findings from a closed risk.")

        link = (
            db.query(RiskFindingLink)
            .filter(
                RiskFindingLink.risk_id == risk_id,
                RiskFindingLink.finding_id == finding_id,
                RiskFindingLink.organization_id == organization_id,
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
        risks = db.query(Risk).filter(Risk.organization_id == organization_id).all()
        total = len(risks)

        status_counts = {
            "identified": sum(1 for r in risks if r.status == RiskStatusEnum.IDENTIFIED),
            "assessed": sum(1 for r in risks if r.status == RiskStatusEnum.ASSESSED),
            "treatment_planned": sum(1 for r in risks if r.status == RiskStatusEnum.TREATMENT_PLANNED),
            "mitigating": sum(1 for r in risks if r.status == RiskStatusEnum.MITIGATING),
            "monitoring": sum(1 for r in risks if r.status == RiskStatusEnum.MONITORING),
            "accepted": sum(1 for r in risks if r.status == RiskStatusEnum.ACCEPTED),
            "closed": sum(1 for r in risks if r.status == RiskStatusEnum.CLOSED),
        }

        band_counts = {
            "critical": sum(1 for r in risks if r.inherent_band == "CRITICAL"),
            "high": sum(1 for r in risks if r.inherent_band == "HIGH"),
            "moderate": sum(1 for r in risks if r.inherent_band == "MODERATE"),
            "low": sum(1 for r in risks if r.inherent_band == "LOW"),
        }

        appetite_counts = {
            "above": sum(1 for r in risks if r.appetite_status == "ABOVE_APPETITE"),
            "near": sum(1 for r in risks if r.appetite_status == "NEAR_LIMIT"),
            "within": sum(1 for r in risks if r.appetite_status == "WITHIN_APPETITE"),
        }

        today = date.today()
        overdue_cnt = 0
        due_soon_cnt = 0
        total_inh = 0
        total_res = 0

        for r in risks:
            total_inh += r.inherent_score
            total_res += r.residual_score if r.residual_score is not None else r.inherent_score
            od = calculate_treatment_overdue_status(r.status.value, r.treatment_due_date, today)
            if od == "OVERDUE":
                overdue_cnt += 1
            elif od == "DUE_SOON":
                due_soon_cnt += 1

        reduction = 0.0
        if total_inh > 0:
            reduction = round(max(0.0, min(100.0, (total_inh - total_res) / total_inh * 100.0)), 1)

        return {
            "total_risks": total,
            "identified_count": status_counts["identified"],
            "assessed_count": status_counts["assessed"],
            "treatment_planned_count": status_counts["treatment_planned"],
            "mitigating_count": status_counts["mitigating"],
            "monitoring_count": status_counts["monitoring"],
            "accepted_count": status_counts["accepted"],
            "closed_count": status_counts["closed"],
            "critical_inherent_count": band_counts["critical"],
            "high_inherent_count": band_counts["high"],
            "moderate_inherent_count": band_counts["moderate"],
            "low_inherent_count": band_counts["low"],
            "above_appetite_count": appetite_counts["above"],
            "near_limit_count": appetite_counts["near"],
            "within_appetite_count": appetite_counts["within"],
            "overdue_treatments_count": overdue_cnt,
            "due_soon_treatments_count": due_soon_cnt,
            "inherent_vs_residual_reduction": reduction,
        }

    @staticmethod
    def get_heatmap(db: Session, organization_id: int) -> List[Dict[str, Any]]:
        # Heatmap represents active, unclosed risks
        risks = (
            db.query(Risk)
            .filter(
                Risk.organization_id == organization_id,
                Risk.status != RiskStatusEnum.CLOSED,
            )
            .all()
        )
        return generate_risk_heatmap_matrix(risks)
