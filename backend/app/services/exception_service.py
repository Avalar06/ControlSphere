from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session, joinedload
from app.core.risk_engine import calculate_exception_effective_status
from app.models.control import OrganizationControl
from app.models.exception import (
    ExceptionCompensatingControl,
    ExceptionStatusEnum,
    ExceptionTypeEnum,
    SecurityException,
)
from app.models.finding import Finding
from app.models.policy import Policy
from app.models.user import User
from app.schemas.exception import (
    ExceptionClosure,
    ExceptionCompensatingControlCreate,
    ExceptionCreate,
    ExceptionReviewAction,
    ExceptionUpdate,
)


class ExceptionService:
    @staticmethod
    def list_exceptions(
        db: Session,
        organization_id: int,
        status: Optional[ExceptionStatusEnum] = None,
        exception_type: Optional[ExceptionTypeEnum] = None,
        owner_id: Optional[int] = None,
        reviewer_id: Optional[int] = None,
        active_only: bool = False,
        expired_only: bool = False,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        query = (
            db.query(SecurityException)
            .filter(SecurityException.organization_id == organization_id)
            .options(
                joinedload(SecurityException.requested_by),
                joinedload(SecurityException.owner),
                joinedload(SecurityException.reviewer),
                joinedload(SecurityException.closed_by),
                joinedload(SecurityException.linked_control).joinedload(OrganizationControl.subcategory),
                joinedload(SecurityException.linked_policy),
                joinedload(SecurityException.linked_finding),
                joinedload(SecurityException.compensating_controls),
            )
        )

        if status:
            query = query.filter(SecurityException.status == status)
        if exception_type:
            query = query.filter(SecurityException.exception_type == exception_type)
        if owner_id:
            query = query.filter(SecurityException.owner_id == owner_id)
        if reviewer_id:
            query = query.filter(SecurityException.reviewer_id == reviewer_id)
        if search:
            query = query.filter(
                (SecurityException.title.ilike(f"%{search}%"))
                | (SecurityException.description.ilike(f"%{search}%"))
                | (SecurityException.justification.ilike(f"%{search}%"))
            )

        exceptions = query.order_by(SecurityException.created_at.desc()).all()

        results = []
        today = date.today()
        for e in exceptions:
            effective_status = calculate_exception_effective_status(
                e.status.value, e.expiry_date, e.effective_date, today
            )
            if active_only and effective_status != "ACTIVE":
                continue
            if expired_only and effective_status != "EXPIRED":
                continue

            results.append({
                "id": e.id,
                "organization_id": e.organization_id,
                "title": e.title,
                "description": e.description,
                "justification": e.justification,
                "exception_type": e.exception_type,
                "status": e.status,
                "effective_status": effective_status,
                "requested_by_id": e.requested_by_id,
                "owner_id": e.owner_id,
                "reviewer_id": e.reviewer_id,
                "requested_at": e.requested_at,
                "approved_at": e.approved_at,
                "effective_date": e.effective_date,
                "expiry_date": e.expiry_date,
                "review_date": e.review_date,
                "residual_risk_level": e.residual_risk_level,
                "approval_notes": e.approval_notes,
                "rejection_reason": e.rejection_reason,
                "closure_notes": e.closure_notes,
                "closed_at": e.closed_at,
                "closed_by_id": e.closed_by_id,
                "linked_organization_control_id": e.linked_organization_control_id,
                "linked_policy_id": e.linked_policy_id,
                "linked_finding_id": e.linked_finding_id,
                "created_at": e.created_at,
                "updated_at": e.updated_at,
                "requested_by": e.requested_by,
                "owner": e.owner,
                "reviewer": e.reviewer,
                "closed_by": e.closed_by,
                "linked_control": e.linked_control,
                "linked_policy": e.linked_policy,
                "linked_finding": e.linked_finding,
                "compensating_controls_count": len(e.compensating_controls),
            })

        return results[skip : skip + limit]

    @staticmethod
    def get_exception_by_id(
        db: Session, exception_id: int, organization_id: int
    ) -> Optional[Dict[str, Any]]:
        e = (
            db.query(SecurityException)
            .filter(
                SecurityException.id == exception_id,
                SecurityException.organization_id == organization_id,
            )
            .options(
                joinedload(SecurityException.requested_by),
                joinedload(SecurityException.owner),
                joinedload(SecurityException.reviewer),
                joinedload(SecurityException.closed_by),
                joinedload(SecurityException.linked_control).joinedload(OrganizationControl.subcategory),
                joinedload(SecurityException.linked_policy),
                joinedload(SecurityException.linked_finding),
                joinedload(SecurityException.compensating_controls).joinedload(ExceptionCompensatingControl.organization_control).joinedload(OrganizationControl.subcategory),
            )
            .first()
        )
        if not e:
            return None

        effective_status = calculate_exception_effective_status(
            e.status.value, e.expiry_date, e.effective_date
        )

        return {
            "id": e.id,
            "organization_id": e.organization_id,
            "title": e.title,
            "description": e.description,
            "justification": e.justification,
            "exception_type": e.exception_type,
            "status": e.status,
            "effective_status": effective_status,
            "requested_by_id": e.requested_by_id,
            "owner_id": e.owner_id,
            "reviewer_id": e.reviewer_id,
            "requested_at": e.requested_at,
            "approved_at": e.approved_at,
            "effective_date": e.effective_date,
            "expiry_date": e.expiry_date,
            "review_date": e.review_date,
            "residual_risk_level": e.residual_risk_level,
            "approval_notes": e.approval_notes,
            "rejection_reason": e.rejection_reason,
            "closure_notes": e.closure_notes,
            "closed_at": e.closed_at,
            "closed_by_id": e.closed_by_id,
            "linked_organization_control_id": e.linked_organization_control_id,
            "linked_policy_id": e.linked_policy_id,
            "linked_finding_id": e.linked_finding_id,
            "created_at": e.created_at,
            "updated_at": e.updated_at,
            "requested_by": e.requested_by,
            "owner": e.owner,
            "reviewer": e.reviewer,
            "closed_by": e.closed_by,
            "linked_control": e.linked_control,
            "linked_policy": e.linked_policy,
            "linked_finding": e.linked_finding,
            "compensating_controls_count": len(e.compensating_controls),
            "compensating_controls": e.compensating_controls,
        }

    @staticmethod
    def create_exception(
        db: Session,
        obj_in: ExceptionCreate,
        organization_id: int,
        creator_id: Optional[int],
    ) -> SecurityException:
        # Validate owner if supplied
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

        # Validate reviewer if supplied
        if obj_in.reviewer_id:
            rev = (
                db.query(User)
                .filter(
                    User.id == obj_in.reviewer_id,
                    User.organization_id == organization_id,
                    User.is_active.is_(True),
                )
                .first()
            )
            if not rev:
                raise ValueError(f"Reviewer ID {obj_in.reviewer_id} not found or inactive in your organization.")

        # Validate linked control if supplied
        if obj_in.linked_organization_control_id:
            ctrl = (
                db.query(OrganizationControl)
                .filter(
                    OrganizationControl.id == obj_in.linked_organization_control_id,
                    OrganizationControl.organization_id == organization_id,
                )
                .first()
            )
            if not ctrl:
                raise ValueError("Linked organization control not found in your organization.")

        # Validate linked policy if supplied
        if obj_in.linked_policy_id:
            pol = (
                db.query(Policy)
                .filter(
                    Policy.id == obj_in.linked_policy_id,
                    Policy.organization_id == organization_id,
                )
                .first()
            )
            if not pol:
                raise ValueError("Linked policy not found in your organization.")

        # Validate linked finding if supplied
        if obj_in.linked_finding_id:
            fnd = (
                db.query(Finding)
                .filter(
                    Finding.id == obj_in.linked_finding_id,
                    Finding.organization_id == organization_id,
                )
                .first()
            )
            if not fnd:
                raise ValueError("Linked finding not found in your organization.")

        exc = SecurityException(
            organization_id=organization_id,
            title=obj_in.title.strip(),
            description=obj_in.description.strip(),
            justification=obj_in.justification.strip(),
            exception_type=obj_in.exception_type,
            status=ExceptionStatusEnum.REQUESTED,
            requested_by_id=creator_id,
            owner_id=obj_in.owner_id or creator_id,
            reviewer_id=obj_in.reviewer_id,
            effective_date=obj_in.effective_date or date.today(),
            expiry_date=obj_in.expiry_date,
            review_date=obj_in.review_date,
            residual_risk_level=obj_in.residual_risk_level or "MODERATE",
            linked_organization_control_id=obj_in.linked_organization_control_id,
            linked_policy_id=obj_in.linked_policy_id,
            linked_finding_id=obj_in.linked_finding_id,
        )
        db.add(exc)
        db.commit()
        db.refresh(exc)
        return exc

    @staticmethod
    def update_exception(
        db: Session,
        exception_id: int,
        organization_id: int,
        obj_in: ExceptionUpdate,
    ) -> Optional[SecurityException]:
        exc = (
            db.query(SecurityException)
            .filter(
                SecurityException.id == exception_id,
                SecurityException.organization_id == organization_id,
            )
            .first()
        )
        if not exc:
            return None

        if exc.status in [ExceptionStatusEnum.CLOSED, ExceptionStatusEnum.REJECTED]:
            raise ValueError(f"Cannot modify exception in status '{exc.status.value}'.")

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

        if obj_in.reviewer_id is not None:
            rev = (
                db.query(User)
                .filter(
                    User.id == obj_in.reviewer_id,
                    User.organization_id == organization_id,
                    User.is_active.is_(True),
                )
                .first()
            )
            if not rev:
                raise ValueError(f"Reviewer ID {obj_in.reviewer_id} not found or inactive in your organization.")

        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(exc, field, value)

        db.add(exc)
        db.commit()
        db.refresh(exc)
        return exc

    @staticmethod
    def submit_for_review(
        db: Session,
        exception_id: int,
        organization_id: int,
    ) -> Optional[SecurityException]:
        exc = (
            db.query(SecurityException)
            .filter(
                SecurityException.id == exception_id,
                SecurityException.organization_id == organization_id,
            )
            .first()
        )
        if not exc:
            return None

        if exc.status != ExceptionStatusEnum.REQUESTED:
            raise ValueError(f"Only REQUESTED exceptions can be submitted for review. Current status: '{exc.status.value}'.")

        exc.status = ExceptionStatusEnum.UNDER_REVIEW
        db.add(exc)
        db.commit()
        db.refresh(exc)
        return exc

    @staticmethod
    def approve_exception(
        db: Session,
        exception_id: int,
        organization_id: int,
        action_in: ExceptionReviewAction,
        reviewer_id: Optional[int],
    ) -> Optional[SecurityException]:
        exc = (
            db.query(SecurityException)
            .filter(
                SecurityException.id == exception_id,
                SecurityException.organization_id == organization_id,
            )
            .first()
        )
        if not exc:
            return None

        if exc.status not in [ExceptionStatusEnum.REQUESTED, ExceptionStatusEnum.UNDER_REVIEW]:
            raise ValueError(f"Cannot approve exception in status '{exc.status.value}'.")

        exc.status = ExceptionStatusEnum.APPROVED
        exc.approved_at = datetime.now(timezone.utc)
        exc.reviewer_id = reviewer_id
        if action_in.approval_notes:
            exc.approval_notes = action_in.approval_notes

        # If effective date has arrived, mark as ACTIVE immediately
        today = date.today()
        if exc.effective_date and exc.effective_date <= today:
            exc.status = ExceptionStatusEnum.ACTIVE

        db.add(exc)
        db.commit()
        db.refresh(exc)
        return exc

    @staticmethod
    def reject_exception(
        db: Session,
        exception_id: int,
        organization_id: int,
        action_in: ExceptionReviewAction,
        reviewer_id: Optional[int],
    ) -> Optional[SecurityException]:
        exc = (
            db.query(SecurityException)
            .filter(
                SecurityException.id == exception_id,
                SecurityException.organization_id == organization_id,
            )
            .first()
        )
        if not exc:
            return None

        if exc.status not in [ExceptionStatusEnum.REQUESTED, ExceptionStatusEnum.UNDER_REVIEW]:
            raise ValueError(f"Cannot reject exception in status '{exc.status.value}'.")

        exc.status = ExceptionStatusEnum.REJECTED
        exc.reviewer_id = reviewer_id
        if action_in.rejection_reason:
            exc.rejection_reason = action_in.rejection_reason

        db.add(exc)
        db.commit()
        db.refresh(exc)
        return exc

    @staticmethod
    def close_exception(
        db: Session,
        exception_id: int,
        organization_id: int,
        closure_in: ExceptionClosure,
        user_id: Optional[int],
    ) -> Optional[SecurityException]:
        exc = (
            db.query(SecurityException)
            .filter(
                SecurityException.id == exception_id,
                SecurityException.organization_id == organization_id,
            )
            .first()
        )
        if not exc:
            return None

        if exc.status == ExceptionStatusEnum.CLOSED:
            raise ValueError("Exception is already closed.")

        exc.status = ExceptionStatusEnum.CLOSED
        exc.closed_at = datetime.now(timezone.utc)
        exc.closed_by_id = user_id
        exc.closure_notes = closure_in.closure_notes.strip()

        db.add(exc)
        db.commit()
        db.refresh(exc)
        return exc

    @staticmethod
    def link_compensating_control(
        db: Session,
        exception_id: int,
        obj_in: ExceptionCompensatingControlCreate,
        organization_id: int,
        creator_id: Optional[int],
    ) -> ExceptionCompensatingControl:
        exc = (
            db.query(SecurityException)
            .filter(
                SecurityException.id == exception_id,
                SecurityException.organization_id == organization_id,
            )
            .first()
        )
        if not exc:
            raise ValueError("Security exception not found in your organization.")

        ctrl = (
            db.query(OrganizationControl)
            .filter(
                OrganizationControl.id == obj_in.organization_control_id,
                OrganizationControl.organization_id == organization_id,
            )
            .first()
        )
        if not ctrl:
            raise ValueError("Compensating control not found in your organization.")

        existing = (
            db.query(ExceptionCompensatingControl)
            .filter(
                ExceptionCompensatingControl.exception_id == exception_id,
                ExceptionCompensatingControl.organization_control_id == obj_in.organization_control_id,
            )
            .first()
        )
        if existing:
            return existing

        link = ExceptionCompensatingControl(
            organization_id=organization_id,
            exception_id=exception_id,
            organization_control_id=obj_in.organization_control_id,
            implementation_notes=obj_in.implementation_notes,
            created_by_id=creator_id,
        )
        db.add(link)
        db.commit()
        db.refresh(link)
        return link

    @staticmethod
    def unlink_compensating_control(
        db: Session,
        exception_id: int,
        organization_control_id: int,
        organization_id: int,
    ) -> bool:
        link = (
            db.query(ExceptionCompensatingControl)
            .filter(
                ExceptionCompensatingControl.exception_id == exception_id,
                ExceptionCompensatingControl.organization_control_id == organization_control_id,
                ExceptionCompensatingControl.organization_id == organization_id,
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
        exceptions = db.query(SecurityException).filter(SecurityException.organization_id == organization_id).all()
        total = len(exceptions)

        today = date.today()
        requested = sum(1 for e in exceptions if e.status == ExceptionStatusEnum.REQUESTED)
        under_review = sum(1 for e in exceptions if e.status == ExceptionStatusEnum.UNDER_REVIEW)
        rejected = sum(1 for e in exceptions if e.status == ExceptionStatusEnum.REJECTED)
        closed = sum(1 for e in exceptions if e.status == ExceptionStatusEnum.CLOSED)

        active = 0
        expired = 0
        expiring_soon = 0

        for e in exceptions:
            eff = calculate_exception_effective_status(e.status.value, e.expiry_date, e.effective_date, today)
            if eff == "ACTIVE":
                active += 1
                if e.expiry_date and 0 <= (e.expiry_date - today).days <= 14:
                    expiring_soon += 1
            elif eff == "EXPIRED":
                expired += 1

        return {
            "total_exceptions": total,
            "requested_count": requested,
            "under_review_count": under_review,
            "active_count": active,
            "expired_count": expired,
            "rejected_count": rejected,
            "closed_count": closed,
            "expiring_soon_count": expiring_soon,
        }
