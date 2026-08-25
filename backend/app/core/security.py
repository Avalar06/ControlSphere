from datetime import datetime, timedelta, timezone
from typing import Any, Union
import bcrypt
from jose import jwt
from app.core.config import settings

# Pre-computed dummy hash to equalize timing on non-existent user authentication
DUMMY_HASH = bcrypt.hashpw(b"ControlSphereDummyAuthPassword123!", bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def verify_dummy_password(plain_password: str) -> None:
    """Executes a dummy bcrypt check to equalize timing during authentication attempts for non-existent users."""
    try:
        bcrypt.checkpw(plain_password.encode("utf-8"), DUMMY_HASH.encode("utf-8"))
    except Exception:
        pass


def get_password_hash(password: str) -> str:
    # Ensure password does not exceed bcrypt 72 bytes limit
    pwd_bytes = password.encode("utf-8")
    if len(pwd_bytes) > 72:
        raise ValueError("Password cannot exceed 72 bytes")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def create_access_token(
    subject: Union[str, Any],
    organization_id: int,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "org_id": organization_id,
        "role": role,
        "iat": datetime.now(timezone.utc),
    }
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt