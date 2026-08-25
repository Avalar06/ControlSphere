from typing import Optional
from sqlalchemy.orm import Session
from app.core.security import verify_password, create_access_token
from app.models.user import User
from app.services.audit_service import AuditService
from app.services.user_service import UserService


class AuthService:
    @staticmethod
    def authenticate(
        db: Session,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[User]:
        user = UserService.get_by_email(db, email=email)
        if not user:
            return None

        if not verify_password(password, user.hashed_password):
            # Log failed authentication attempt
            AuditService.log(
                db=db,
                organization_id=user.organization_id,
                actor_id=user.id,
                actor_email=user.email,
                action="auth.login.failed",
                resource_type="AUTH",
                status="FAILURE",
                ip_address=ip_address,
                user_agent=user_agent,
                details={"reason": "invalid_credentials"},
            )
            return None

        if not user.is_active:
            AuditService.log(
                db=db,
                organization_id=user.organization_id,
                actor_id=user.id,
                actor_email=user.email,
                action="auth.login.inactive",
                resource_type="AUTH",
                status="FAILURE",
                ip_address=ip_address,
                user_agent=user_agent,
                details={"reason": "account_inactive"},
            )
            return None

        # Log successful login
        AuditService.log(
            db=db,
            organization_id=user.organization_id,
            actor_id=user.id,
            actor_email=user.email,
            action="auth.login.success",
            resource_type="AUTH",
            status="SUCCESS",
            ip_address=ip_address,
            user_agent=user_agent,
            details={"role": user.role.value},
        )

        return user

    @staticmethod
    def create_user_token(user: User) -> str:
        return create_access_token(
            subject=user.id,
            organization_id=user.organization_id,
            role=user.role.value,
        )