from typing import List, Optional
from sqlalchemy.orm import Session
from app.core.permissions import RoleEnum
from app.core.security import get_password_hash
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    @staticmethod
    def get_by_id(db: Session, user_id: int, organization_id: Optional[int] = None) -> Optional[User]:
        query = db.query(User).filter(User.id == user_id)
        if organization_id is not None:
            query = query.filter(User.organization_id == organization_id)
        return query.first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def count_active_admins_in_org(db: Session, organization_id: int) -> int:
        return (
            db.query(User)
            .filter(
                User.organization_id == organization_id,
                User.role == RoleEnum.ADMIN,
                User.is_active == True,
            )
            .count()
        )

    @staticmethod
    def list_by_organization(
        db: Session, organization_id: int, skip: int = 0, limit: int = 100
    ) -> List[User]:
        return (
            db.query(User)
            .filter(User.organization_id == organization_id)
            .order_by(User.id.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def create(db: Session, obj_in: UserCreate, organization_id: int) -> User:
        db_user = User(
            email=obj_in.email,
            hashed_password=get_password_hash(obj_in.password),
            full_name=obj_in.full_name,
            role=obj_in.role,
            is_active=obj_in.is_active,
            organization_id=organization_id,
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    def update(db: Session, db_user: User, obj_in: UserUpdate) -> User:
        update_data = obj_in.model_dump(exclude_unset=True)
        if "password" in update_data and update_data["password"]:
            password = update_data.pop("password")
            db_user.hashed_password = get_password_hash(password)
        for field, value in update_data.items():
            setattr(db_user, field, value)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user