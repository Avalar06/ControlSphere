from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.organization import Organization
from app.schemas.organization import OrganizationCreate, OrganizationUpdate


class OrganizationService:
    @staticmethod
    def get_by_id(db: Session, org_id: int) -> Optional[Organization]:
        return db.query(Organization).filter(Organization.id == org_id).first()

    @staticmethod
    def get_by_slug(db: Session, slug: str) -> Optional[Organization]:
        return db.query(Organization).filter(Organization.slug == slug).first()

    @staticmethod
    def get_by_name(db: Session, name: str) -> Optional[Organization]:
        return db.query(Organization).filter(Organization.name == name).first()

    @staticmethod
    def create(db: Session, obj_in: OrganizationCreate) -> Organization:
        org = Organization(
            name=obj_in.name,
            slug=obj_in.slug,
            is_active=obj_in.is_active,
        )
        db.add(org)
        db.commit()
        db.refresh(org)
        return org

    @staticmethod
    def update(db: Session, db_org: Organization, obj_in: OrganizationUpdate) -> Organization:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_org, field, value)
        db.add(db_org)
        db.commit()
        db.refresh(db_org)
        return db_org

    @staticmethod
    def list_all(db: Session, skip: int = 0, limit: int = 100) -> List[Organization]:
        return db.query(Organization).offset(skip).limit(limit).all()