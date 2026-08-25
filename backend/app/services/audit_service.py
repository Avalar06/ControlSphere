from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog


class AuditService:
    @staticmethod
    def log(
        db: Session,
        organization_id: int,
        action: str,
        resource_type: str,
        actor_email: str,
        actor_id: Optional[int] = None,
        resource_id: Optional[str] = None,
        status: str = "SUCCESS",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Create an immutable audit log entry."""
        audit_entry = AuditLog(
            organization_id=organization_id,
            actor_id=actor_id,
            actor_email=actor_email,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            status=status,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
        )
        db.add(audit_entry)
        db.commit()
        db.refresh(audit_entry)
        return audit_entry

    @staticmethod
    def list_logs_for_org(
        db: Session,
        organization_id: int,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        actor_email: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[AuditLog]:
        """Retrieve audit logs strictly scoped to the tenant organization."""
        query = db.query(AuditLog).filter(AuditLog.organization_id == organization_id)

        if action:
            query = query.filter(AuditLog.action == action)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if actor_email:
            query = query.filter(AuditLog.actor_email.ilike(f"%{actor_email}%"))
        if status:
            query = query.filter(AuditLog.status == status)

        return (
            query.order_by(AuditLog.timestamp.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )