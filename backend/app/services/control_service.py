from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session, joinedload
from app.models.control import ImplementationStatusEnum, OrganizationControl, PriorityEnum
from app.models.framework import (
    Framework,
    FrameworkCategory,
    FrameworkFunction,
    FrameworkSubcategory,
)
from app.models.policy import PolicyControlMapping
from app.schemas.control import OrganizationControlUpdate


class ControlService:
    @staticmethod
    def ensure_org_controls(db: Session, organization_id: int) -> None:
        """Ensure all subcategories have an organization control record for this tenant."""
        all_subcats = db.query(FrameworkSubcategory).all()
        existing_subcat_ids = set(
            row[0]
            for row in db.query(OrganizationControl.subcategory_id)
            .filter(OrganizationControl.organization_id == organization_id)
            .all()
        )

        new_controls = []
        for subcat in all_subcats:
            if subcat.id not in existing_subcat_ids:
                new_controls.append(
                    OrganizationControl(
                        organization_id=organization_id,
                        subcategory_id=subcat.id,
                        status=ImplementationStatusEnum.NOT_STARTED,
                        priority=PriorityEnum.MEDIUM,
                    )
                )
        if new_controls:
            db.add_all(new_controls)
            db.commit()

    @staticmethod
    def list_controls(
        db: Session,
        organization_id: int,
        framework_id: Optional[int] = None,
        function_id: Optional[int] = None,
        category_id: Optional[int] = None,
        status: Optional[ImplementationStatusEnum] = None,
        priority: Optional[PriorityEnum] = None,
        owner_id: Optional[int] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        # Ensure controls exist
        ControlService.ensure_org_controls(db, organization_id)

        query = (
            db.query(
                OrganizationControl,
                FrameworkSubcategory,
                FrameworkCategory,
                FrameworkFunction,
            )
            .join(FrameworkSubcategory, OrganizationControl.subcategory_id == FrameworkSubcategory.id)
            .join(FrameworkCategory, FrameworkSubcategory.category_id == FrameworkCategory.id)
            .join(FrameworkFunction, FrameworkCategory.function_id == FrameworkFunction.id)
            .filter(OrganizationControl.organization_id == organization_id)
            .options(joinedload(OrganizationControl.owner))
        )

        if framework_id:
            query = query.filter(FrameworkFunction.framework_id == framework_id)
        if function_id:
            query = query.filter(FrameworkFunction.id == function_id)
        if category_id:
            query = query.filter(FrameworkCategory.id == category_id)
        if status:
            query = query.filter(OrganizationControl.status == status)
        if priority:
            query = query.filter(OrganizationControl.priority == priority)
        if owner_id:
            query = query.filter(OrganizationControl.owner_id == owner_id)
        if search:
            pattern = f"%{search}%"
            query = query.filter(
                (FrameworkSubcategory.identifier.ilike(pattern))
                | (FrameworkSubcategory.title.ilike(pattern))
                | (FrameworkSubcategory.description.ilike(pattern))
            )

        rows = (
            query.order_by(
                FrameworkFunction.display_order.asc(),
                FrameworkCategory.display_order.asc(),
                FrameworkSubcategory.display_order.asc(),
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

        results = []
        for ctrl, subcat, cat, fn in rows:
            mapped_count = (
                db.query(PolicyControlMapping)
                .filter(
                    PolicyControlMapping.organization_id == organization_id,
                    PolicyControlMapping.subcategory_id == subcat.id,
                )
                .count()
            )
            results.append({
                "id": ctrl.id,
                "organization_id": ctrl.organization_id,
                "subcategory_id": ctrl.subcategory_id,
                "status": ctrl.status,
                "priority": ctrl.priority,
                "owner_id": ctrl.owner_id,
                "target_date": ctrl.target_date,
                "review_date": ctrl.review_date,
                "implementation_statement": ctrl.implementation_statement,
                "notes": ctrl.notes,
                "created_at": ctrl.created_at,
                "updated_at": ctrl.updated_at,
                "subcategory": subcat,
                "owner": ctrl.owner,
                "function_identifier": fn.identifier,
                "function_name": fn.name,
                "category_identifier": cat.identifier,
                "category_name": cat.name,
                "mapped_policies_count": mapped_count,
            })

        return results

    @staticmethod
    def get_control_by_id(
        db: Session, control_id: int, organization_id: int
    ) -> Optional[Dict[str, Any]]:
        row = (
            db.query(
                OrganizationControl,
                FrameworkSubcategory,
                FrameworkCategory,
                FrameworkFunction,
            )
            .join(FrameworkSubcategory, OrganizationControl.subcategory_id == FrameworkSubcategory.id)
            .join(FrameworkCategory, FrameworkSubcategory.category_id == FrameworkCategory.id)
            .join(FrameworkFunction, FrameworkCategory.function_id == FrameworkFunction.id)
            .filter(
                OrganizationControl.id == control_id,
                OrganizationControl.organization_id == organization_id,
            )
            .options(joinedload(OrganizationControl.owner))
            .first()
        )
        if not row:
            return None

        ctrl, subcat, cat, fn = row
        mapped_count = (
            db.query(PolicyControlMapping)
            .filter(
                PolicyControlMapping.organization_id == organization_id,
                PolicyControlMapping.subcategory_id == subcat.id,
            )
            .count()
        )

        return {
            "id": ctrl.id,
            "organization_id": ctrl.organization_id,
            "subcategory_id": ctrl.subcategory_id,
            "status": ctrl.status,
            "priority": ctrl.priority,
            "owner_id": ctrl.owner_id,
            "target_date": ctrl.target_date,
            "review_date": ctrl.review_date,
            "implementation_statement": ctrl.implementation_statement,
            "notes": ctrl.notes,
            "created_at": ctrl.created_at,
            "updated_at": ctrl.updated_at,
            "subcategory": subcat,
            "owner": ctrl.owner,
            "function_identifier": fn.identifier,
            "function_name": fn.name,
            "category_identifier": cat.identifier,
            "category_name": cat.name,
            "mapped_policies_count": mapped_count,
        }

    @staticmethod
    def update_control(
        db: Session, control_id: int, organization_id: int, obj_in: OrganizationControlUpdate
    ) -> Optional[OrganizationControl]:
        ctrl = (
            db.query(OrganizationControl)
            .filter(
                OrganizationControl.id == control_id,
                OrganizationControl.organization_id == organization_id,
            )
            .first()
        )
        if not ctrl:
            return None

        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(ctrl, field, value)

        db.add(ctrl)
        db.commit()
        db.refresh(ctrl)
        return ctrl

    @staticmethod
    def calculate_framework_progress(
        db: Session, framework_id: int, organization_id: int
    ) -> Optional[Dict[str, Any]]:
        fw = db.query(Framework).filter(Framework.id == framework_id).first()
        if not fw:
            return None

        ControlService.ensure_org_controls(db, organization_id)

        rows = (
            db.query(OrganizationControl, FrameworkFunction)
            .join(FrameworkSubcategory, OrganizationControl.subcategory_id == FrameworkSubcategory.id)
            .join(FrameworkCategory, FrameworkSubcategory.category_id == FrameworkCategory.id)
            .join(FrameworkFunction, FrameworkCategory.function_id == FrameworkFunction.id)
            .filter(
                FrameworkFunction.framework_id == framework_id,
                OrganizationControl.organization_id == organization_id,
            )
            .all()
        )

        total = len(rows)
        counts = {
            "IMPLEMENTED": 0,
            "PARTIALLY_IMPLEMENTED": 0,
            "IN_PROGRESS": 0,
            "NOT_STARTED": 0,
            "NOT_APPLICABLE": 0,
            "NEEDS_REVIEW": 0,
        }

        by_fn: Dict[str, Dict[str, Any]] = {}

        for ctrl, fn in rows:
            fn_key = fn.identifier
            if fn_key not in by_fn:
                by_fn[fn_key] = {
                    "name": fn.name,
                    "total": 0,
                    "implemented": 0,
                    "partially_implemented": 0,
                    "in_progress": 0,
                    "not_started": 0,
                    "score_pct": 0.0,
                }

            by_fn[fn_key]["total"] += 1
            st = ctrl.status.value
            counts[st] = counts.get(st, 0) + 1

            if ctrl.status == ImplementationStatusEnum.IMPLEMENTED:
                by_fn[fn_key]["implemented"] += 1
            elif ctrl.status == ImplementationStatusEnum.PARTIALLY_IMPLEMENTED:
                by_fn[fn_key]["partially_implemented"] += 1
            elif ctrl.status == ImplementationStatusEnum.IN_PROGRESS:
                by_fn[fn_key]["in_progress"] += 1
            elif ctrl.status == ImplementationStatusEnum.NOT_STARTED:
                by_fn[fn_key]["not_started"] += 1

        # Calculate percentages
        applicable_count = total - counts["NOT_APPLICABLE"]
        if applicable_count > 0:
            effective_score = (counts["IMPLEMENTED"] * 1.0) + (counts["PARTIALLY_IMPLEMENTED"] * 0.5)
            compliance_score_pct = round((effective_score / applicable_count) * 100.0, 1)
        else:
            compliance_score_pct = 0.0

        for fn_key, fn_stats in by_fn.items():
            if fn_stats["total"] > 0:
                fn_effective = (fn_stats["implemented"] * 1.0) + (fn_stats["partially_implemented"] * 0.5)
                fn_stats["score_pct"] = round((fn_effective / fn_stats["total"]) * 100.0, 1)

        return {
            "framework_id": fw.id,
            "framework_identifier": fw.identifier,
            "framework_name": fw.name,
            "total_controls": total,
            "implemented_count": counts["IMPLEMENTED"],
            "partially_implemented_count": counts["PARTIALLY_IMPLEMENTED"],
            "in_progress_count": counts["IN_PROGRESS"],
            "not_started_count": counts["NOT_STARTED"],
            "not_applicable_count": counts["NOT_APPLICABLE"],
            "needs_review_count": counts["NEEDS_REVIEW"],
            "compliance_score_pct": compliance_score_pct,
            "by_function": by_fn,
        }