from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session, joinedload
from app.models.framework import FrameworkSubcategory
from app.models.policy import (
    Policy,
    PolicyControlMapping,
    PolicyStatusEnum,
    PolicyTypeEnum,
    PolicyVersion,
)
from app.schemas.policy import PolicyCreate, PolicyUpdate, PolicyVersionCreate


class PolicyService:
    @staticmethod
    def list_policies(
        db: Session,
        organization_id: int,
        status: Optional[PolicyStatusEnum] = None,
        policy_type: Optional[PolicyTypeEnum] = None,
        owner_id: Optional[int] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        query = (
            db.query(Policy)
            .filter(Policy.organization_id == organization_id)
            .options(joinedload(Policy.owner), joinedload(Policy.versions))
        )

        if status:
            query = query.filter(Policy.status == status)
        if policy_type:
            query = query.filter(Policy.policy_type == policy_type)
        if owner_id:
            query = query.filter(Policy.owner_id == owner_id)
        if search:
            query = query.filter(
                (Policy.title.ilike(f"%{search}%"))
                | (Policy.description.ilike(f"%{search}%"))
            )

        policies = query.order_by(Policy.updated_at.desc()).offset(skip).limit(limit).all()

        results = []
        for pol in policies:
            latest_version = pol.versions[0] if pol.versions else None
            # Fetch mapped subcategories
            mapped_subcats = (
                db.query(FrameworkSubcategory)
                .join(PolicyControlMapping, PolicyControlMapping.subcategory_id == FrameworkSubcategory.id)
                .filter(
                    PolicyControlMapping.organization_id == organization_id,
                    PolicyControlMapping.policy_id == pol.id,
                )
                .all()
            )
            results.append({
                "id": pol.id,
                "organization_id": pol.organization_id,
                "title": pol.title,
                "description": pol.description,
                "policy_type": pol.policy_type,
                "status": pol.status,
                "owner_id": pol.owner_id,
                "effective_date": pol.effective_date,
                "review_date": pol.review_date,
                "created_at": pol.created_at,
                "updated_at": pol.updated_at,
                "owner": pol.owner,
                "current_version": latest_version,
                "total_versions": len(pol.versions),
                "mapped_subcategories": mapped_subcats,
            })

        return results

    @staticmethod
    def get_policy_by_id(
        db: Session, policy_id: int, organization_id: int
    ) -> Optional[Dict[str, Any]]:
        pol = (
            db.query(Policy)
            .filter(
                Policy.id == policy_id,
                Policy.organization_id == organization_id,
            )
            .options(
                joinedload(Policy.owner),
                joinedload(Policy.versions).joinedload(PolicyVersion.created_by),
            )
            .first()
        )
        if not pol:
            return None

        mapped_subcats = (
            db.query(FrameworkSubcategory)
            .join(PolicyControlMapping, PolicyControlMapping.subcategory_id == FrameworkSubcategory.id)
            .filter(
                PolicyControlMapping.organization_id == organization_id,
                PolicyControlMapping.policy_id == pol.id,
            )
            .all()
        )

        latest_version = pol.versions[0] if pol.versions else None

        return {
            "id": pol.id,
            "organization_id": pol.organization_id,
            "title": pol.title,
            "description": pol.description,
            "policy_type": pol.policy_type,
            "status": pol.status,
            "owner_id": pol.owner_id,
            "effective_date": pol.effective_date,
            "review_date": pol.review_date,
            "created_at": pol.created_at,
            "updated_at": pol.updated_at,
            "owner": pol.owner,
            "current_version": latest_version,
            "total_versions": len(pol.versions),
            "versions": pol.versions,
            "mapped_subcategories": mapped_subcats,
        }

    @staticmethod
    def create_policy(
        db: Session, obj_in: PolicyCreate, organization_id: int, created_by_id: Optional[int]
    ) -> Policy:
        pol = Policy(
            organization_id=organization_id,
            title=obj_in.title,
            description=obj_in.description,
            policy_type=obj_in.policy_type,
            status=PolicyStatusEnum.DRAFT,
            owner_id=obj_in.owner_id or created_by_id,
            effective_date=obj_in.effective_date,
            review_date=obj_in.review_date,
        )
        db.add(pol)
        db.commit()
        db.refresh(pol)

        # Create initial Version 1
        v1 = PolicyVersion(
            policy_id=pol.id,
            version_number=1,
            content=obj_in.initial_content,
            change_summary="Initial drafted version",
            created_by_id=created_by_id,
        )
        db.add(v1)

        # Map initial subcategories
        for subcat_id in obj_in.mapped_subcategory_ids:
            # Verify subcategory exists
            sub = db.query(FrameworkSubcategory).filter(FrameworkSubcategory.id == subcat_id).first()
            if sub:
                mapping = PolicyControlMapping(
                    organization_id=organization_id,
                    policy_id=pol.id,
                    subcategory_id=sub.id,
                )
                db.add(mapping)

        db.commit()
        db.refresh(pol)
        return pol

    @staticmethod
    def update_policy(
        db: Session, policy_id: int, organization_id: int, obj_in: PolicyUpdate
    ) -> Optional[Policy]:
        pol = (
            db.query(Policy)
            .filter(
                Policy.id == policy_id,
                Policy.organization_id == organization_id,
            )
            .first()
        )
        if not pol:
            return None

        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(pol, field, value)

        db.add(pol)
        db.commit()
        db.refresh(pol)
        return pol

    @staticmethod
    def create_policy_version(
        db: Session,
        policy_id: int,
        organization_id: int,
        obj_in: PolicyVersionCreate,
        created_by_id: Optional[int],
    ) -> Optional[PolicyVersion]:
        pol = (
            db.query(Policy)
            .filter(
                Policy.id == policy_id,
                Policy.organization_id == organization_id,
            )
            .first()
        )
        if not pol:
            return None

        # Calculate next version number
        latest_ver = (
            db.query(PolicyVersion)
            .filter(PolicyVersion.policy_id == policy_id)
            .order_by(PolicyVersion.version_number.desc())
            .first()
        )
        next_ver_num = (latest_ver.version_number + 1) if latest_ver else 1

        new_version = PolicyVersion(
            policy_id=pol.id,
            version_number=next_ver_num,
            content=obj_in.content,
            change_summary=obj_in.change_summary,
            created_by_id=created_by_id,
        )
        db.add(new_version)
        db.commit()
        db.refresh(new_version)
        return new_version

    @staticmethod
    def update_policy_status(
        db: Session, policy_id: int, organization_id: int, new_status: PolicyStatusEnum
    ) -> Optional[Policy]:
        pol = (
            db.query(Policy)
            .filter(
                Policy.id == policy_id,
                Policy.organization_id == organization_id,
            )
            .first()
        )
        if not pol:
            return None

        # State transition validation
        valid_transitions = {
            PolicyStatusEnum.DRAFT: [PolicyStatusEnum.UNDER_REVIEW, PolicyStatusEnum.ARCHIVED],
            PolicyStatusEnum.UNDER_REVIEW: [PolicyStatusEnum.APPROVED, PolicyStatusEnum.DRAFT, PolicyStatusEnum.ARCHIVED],
            PolicyStatusEnum.APPROVED: [PolicyStatusEnum.PUBLISHED, PolicyStatusEnum.UNDER_REVIEW, PolicyStatusEnum.ARCHIVED],
            PolicyStatusEnum.PUBLISHED: [PolicyStatusEnum.UNDER_REVIEW, PolicyStatusEnum.ARCHIVED],
            PolicyStatusEnum.ARCHIVED: [PolicyStatusEnum.DRAFT],
        }

        allowed = valid_transitions.get(pol.status, [])
        if new_status not in allowed:
            raise ValueError(
                f"Invalid policy state transition from {pol.status.value} to {new_status.value}. Allowed next states: {[s.value for s in allowed]}"
            )

        pol.status = new_status
        db.add(pol)
        db.commit()
        db.refresh(pol)
        return pol

    @staticmethod
    def add_control_mapping(
        db: Session, policy_id: int, organization_id: int, subcategory_id: int
    ) -> Optional[PolicyControlMapping]:
        pol = (
            db.query(Policy)
            .filter(
                Policy.id == policy_id,
                Policy.organization_id == organization_id,
            )
            .first()
        )
        if not pol:
            return None

        sub = db.query(FrameworkSubcategory).filter(FrameworkSubcategory.id == subcategory_id).first()
        if not sub:
            raise ValueError(f"Subcategory ID {subcategory_id} not found in framework catalog")

        existing = (
            db.query(PolicyControlMapping)
            .filter(
                PolicyControlMapping.organization_id == organization_id,
                PolicyControlMapping.policy_id == policy_id,
                PolicyControlMapping.subcategory_id == subcategory_id,
            )
            .first()
        )
        if existing:
            return existing

        mapping = PolicyControlMapping(
            organization_id=organization_id,
            policy_id=policy_id,
            subcategory_id=subcategory_id,
        )
        db.add(mapping)
        db.commit()
        db.refresh(mapping)
        return mapping

    @staticmethod
    def remove_control_mapping(
        db: Session, policy_id: int, organization_id: int, subcategory_id: int
    ) -> bool:
        mapping = (
            db.query(PolicyControlMapping)
            .filter(
                PolicyControlMapping.organization_id == organization_id,
                PolicyControlMapping.policy_id == policy_id,
                PolicyControlMapping.subcategory_id == subcategory_id,
            )
            .first()
        )
        if not mapping:
            return False

        db.delete(mapping)
        db.commit()
        return True