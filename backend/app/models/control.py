from datetime import datetime, timezone, date
import enum
from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base


class ImplementationStatusEnum(str, enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    PARTIALLY_IMPLEMENTED = "PARTIALLY_IMPLEMENTED"
    IMPLEMENTED = "IMPLEMENTED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class PriorityEnum(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class OrganizationControl(Base):
    __tablename__ = "organization_controls"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    subcategory_id = Column(Integer, ForeignKey("framework_subcategories.id", ondelete="CASCADE"), nullable=False, index=True)
    
    status = Column(Enum(ImplementationStatusEnum), default=ImplementationStatusEnum.NOT_STARTED, nullable=False, index=True)
    priority = Column(Enum(PriorityEnum), default=PriorityEnum.MEDIUM, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    target_date = Column(Date, nullable=True)
    review_date = Column(Date, nullable=True)
    implementation_statement = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("organization_id", "subcategory_id", name="uq_org_control_org_subcat"),
    )

    organization = relationship("Organization")
    subcategory = relationship("FrameworkSubcategory", back_populates="organization_controls")
    owner = relationship("User", foreign_keys=[owner_id])