from typing import Generator, List, Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.permissions import RoleEnum, Permission, has_permission
from app.db.base import SessionLocal
from app.models.user import User
from app.schemas.token import TokenPayload
from app.services.audit_service import AuditService

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/access-token",
    auto_error=False,
)


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_client_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def get_user_agent(request: Request) -> Optional[str]:
    return request.headers.get("User-Agent")


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme),
) -> User:
    if not token:
        # Check authorization header manually in case Bearer prefix is passed
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id_str: str = payload.get("sub")
        org_id: int = payload.get("org_id")
        if user_id_str is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token_data = TokenPayload(sub=user_id_str, org_id=org_id, role=payload.get("role"))
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials or token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == int(token_data.sub)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account",
        )
    if user.organization_id != token_data.org_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Organization mismatch in token",
        )
    return user


def require_roles(*allowed_roles: RoleEnum):
    def role_checker(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if current_user.role not in allowed_roles:
            # Audit log authorization failure
            ip = get_client_ip(request)
            ua = get_user_agent(request)
            AuditService.log(
                db=db,
                organization_id=current_user.organization_id,
                actor_id=current_user.id,
                actor_email=current_user.email,
                action="auth.forbidden",
                resource_type="ENDPOINT",
                status="UNAUTHORIZED",
                ip_address=ip,
                user_agent=ua,
                details={
                    "path": request.url.path,
                    "method": request.method,
                    "user_role": current_user.role.value,
                    "required_roles": [r.value for r in allowed_roles],
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required role: {[r.value for r in allowed_roles]}",
            )
        return current_user

    return role_checker


def require_permission(permission: Permission):
    def permission_checker(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if not has_permission(current_user.role, permission):
            ip = get_client_ip(request)
            ua = get_user_agent(request)
            AuditService.log(
                db=db,
                organization_id=current_user.organization_id,
                actor_id=current_user.id,
                actor_email=current_user.email,
                action="auth.forbidden",
                resource_type="PERMISSION",
                status="UNAUTHORIZED",
                ip_address=ip,
                user_agent=ua,
                details={
                    "path": request.url.path,
                    "method": request.method,
                    "required_permission": permission.value,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required permission: {permission.value}",
            )
        return current_user

    return permission_checker