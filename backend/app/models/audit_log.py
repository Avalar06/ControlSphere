from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_email = Column(String(255), nullable=False, index=True)
    
    action = Column(String(100), nullable=False, index=True)  # e.g., "auth.login", "user.create", "org.update"
    resource_type = Column(String(100), nullable=False, index=True)  # e.g., "USER", "ORGANIZATION", "AUTH"
    resource_id = Column(String(100), nullable=True, index=True)
    
    status = Column(String(50), nullable=False, default="SUCCESS")  # "SUCCESS", "FAILURE", "UNAUTHORIZED"
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    details = Column(JSON, nullable=True)

    organization = relationship("Organization", back_populates="audit_logs")
    actor = relationship("User", back_populates="audit_logs", foreign_keys=[actor_id])