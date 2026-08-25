from typing import Optional
from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    org_id: Optional[int] = None
    role: Optional[str] = None
    exp: Optional[int] = None