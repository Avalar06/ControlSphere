from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, get_current_user, get_db, get_user_agent
from app.core.permissions import ROLE_PERMISSIONS
from app.models.user import User
from app.schemas.auth import LoginRequest
from app.schemas.token import Token
from app.schemas.user import UserProfileResponse, UserResponse
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/login", response_model=Token)
def login_json(
    request: Request,
    login_data: LoginRequest,
    db: Session = Depends(get_db),
) -> Any:
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    user = AuthService.authenticate(
        db, email=login_data.email, password=login_data.password, ip_address=ip, user_agent=ua
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {
        "access_token": AuthService.create_user_token(user),
        "token_type": "bearer",
    }


@router.post("/access-token", response_model=Token)
def login_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Any:
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    user = AuthService.authenticate(
        db, email=form_data.username, password=form_data.password, ip_address=ip, user_agent=ua
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {
        "access_token": AuthService.create_user_token(user),
        "token_type": "bearer",
    }


@router.get("/me", response_model=UserProfileResponse)
def read_current_user(
    current_user: User = Depends(get_current_user),
) -> Any:
    perms = [p.value for p in ROLE_PERMISSIONS.get(current_user.role, set())]
    user_data = UserResponse.model_validate(current_user).model_dump()
    user_data["permissions"] = perms
    return user_data