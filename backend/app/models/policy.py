from datetime import datetime, timezone, date
import enum
from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base


class PolicyStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class PolicyTypeEnum(str, enum.Enum):
    ACCESS_CONTROL = "ACCESS_CONTROL"
    INFORMATION_SECURITY = "INFORMATION_SECURITY"
    INCIDENT_RESPONSE = "INCIDENT_RESPONSE"
    DATA_PROTECTION = "DATA_PROTECTION"
    RISK_MANAGEMENT = "RISK_MANAGEMENT"
    BUSINESS_CONTINUITY = "BUSINESS_CONTINUITY"
    VENDOR_MANAGEMENT = "VENDOR_MANAGEMENT"
    ACCEPTABLE_USE = "ACCEPTABLE_USE"
    CRYPTOGRAPHY = "CRYPTOGRAPHY"
    CHANGE_MANAGEMENT = "CHANGE_MANAGEMENT"
    OTHER = "OTHER"


class Policy(Base):
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    policy_type = Column(Enum(PolicyTypeEnum), default=PolicyTypeEnum.INFORMATION_SECURITY, nullable=False, index=True)
    status = Column(Enum(PolicyStatusEnum), default=PolicyStatusEnum.DRAFT, nullable=False, index=True)
    
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    effective_date = Column(Date, nullable=True)
    review_date = Column(Date, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    organization = relationship("Organization")
    owner = relationship("User", foreign_keys=[owner_id])
    versions = relationship("PolicyVersion", back_populates="policy", cascade="all, delete-orphan", order_by="PolicyVersion.version_number.desc()")
    control_mappings = relationship("PolicyControlMapping", back_populates="policy", cascade="all, delete-orphan")


class PolicyVersion(Base):
    __tablename__ = "policy_versions"

    id = Column(Integer, primary_key=True, index=True)
    policy_id = Column(Integer, ForeignKey("policies.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)  # 1, 2, 3...
    content = Column(Text, nullable=False)  # Markdown / policy text
    change_summary = Column(String(255), nullable=False, default="Initial version")
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("policy_id", "version_number", name="uq_policy_version_number"),
    )

    policy = relationship("Policy", back_populates="versions")
    created_by = relationship("User", foreign_keys=[created_by_id])


class PolicyControlMapping(Base):
    __tablename__ = "policy_control_mappings"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    policy_id = Column(Integer, ForeignKey("policies.id", ondelete="CASCADE"), nullable=False, index=True)
    subcategory_id = Column(Integer, ForeignKey("framework_subcategories.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("organization_id", "policy_id", "subcategory_id", name="uq_org_policy_control_mapping"),
    )

    policy = relationship("Policy", back_populates="control_mappings")
    subcategory = relationship("FrameworkSubcategory", back_populates="policy_mappings")