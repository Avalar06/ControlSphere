from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    id: int
    timestamp: datetime
    organization_id: int
    actor_id: Optional[int] = None
    actor_email: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    status: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class AuditLogFilter(BaseModel):
    action: Optional[str] = None
    resource_type: Optional[str] = None
    actor_email: Optional[str] = None
    status: Optional[str] = None
    limit: int = 50
    offset: int = 0