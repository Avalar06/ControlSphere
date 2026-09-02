from datetime import datetime, timezone
import enum
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


# ─────────────────────────────────────────────────────────────────────────────
# Phase 19: IDENTITY-GRC Domain Enums
# ─────────────────────────────────────────────────────────────────────────────

class IdentityTypeEnum(str, enum.Enum):
    WORKFORCE_EMPLOYEE = "WORKFORCE_EMPLOYEE"
    CONTRACTOR = "CONTRACTOR"
    SERVICE_ACCOUNT = "SERVICE_ACCOUNT"
    MACHINE_WORKLOAD = "MACHINE_WORKLOAD"
    EXTERNAL_PARTNER = "EXTERNAL_PARTNER"


class EmploymentStatusEnum(str, enum.Enum):
    ACTIVE = "ACTIVE"
    LEAVE = "LEAVE"
    TERMINATED = "TERMINATED"
    SUSPENDED = "SUSPENDED"


class IdentityRiskBandEnum(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"


class SystemTypeEnum(str, enum.Enum):
    ACTIVE_DIRECTORY = "ACTIVE_DIRECTORY"
    OKTA = "OKTA"
    AWS_IAM = "AWS_IAM"
    AZURE_RBAC = "AZURE_RBAC"
    DATABASE_ROLE = "DATABASE_ROLE"
    SAAS_APPLICATION = "SAAS_APPLICATION"


class AssignmentTypeEnum(str, enum.Enum):
    DIRECT = "DIRECT"
    ROLE_INHERITED = "ROLE_INHERITED"
    JIT_ELEVATION = "JIT_ELEVATION"


class CampaignTypeEnum(str, enum.Enum):
    PERIODIC_USER_ACCESS_REVIEW = "PERIODIC_USER_ACCESS_REVIEW"
    PRIVILEGED_ACCESS_CERTIFICATION = "PRIVILEGED_ACCESS_CERTIFICATION"
    SOD_CONFLICT_REVIEW = "SOD_CONFLICT_REVIEW"
    TERMINATION_AUDIT = "TERMINATION_AUDIT"


class CampaignStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    IN_REVIEW = "IN_REVIEW"
    FINALIZED = "FINALIZED"
    CANCELLED = "CANCELLED"


class CertificationDecisionEnum(str, enum.Enum):
    PENDING = "PENDING"
    CERTIFIED = "CERTIFIED"
    REVOKED = "REVOKED"
    EXCEPTION_APPROVED = "EXCEPTION_APPROVED"


class JITApprovalStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class TrustLevelEnum(str, enum.Enum):
    HIGH_TRUST = "HIGH_TRUST"
    CONDITIONAL_TRUST = "CONDITIONAL_TRUST"
    LOW_TRUST = "LOW_TRUST"
    UNTRUSTED = "UNTRUSTED"


class SoDPolicySeverityEnum(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"


class SoDViolationStatusEnum(str, enum.Enum):
    ACTIVE_VIOLATION = "ACTIVE_VIOLATION"
    EXCEPTION_GRANTED = "EXCEPTION_GRANTED"
    REMEDIATED = "REMEDIATED"


# ─────────────────────────────────────────────────────────────────────────────
# 1. GOVERNED IDENTITY INVENTORY
# ─────────────────────────────────────────────────────────────────────────────

class GovernedIdentity(Base):
    """Authoritative Workforce, Service & Machine Identity Inventory Record."""
    __tablename__ = "governed_identities"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    identity_code = Column(String(64), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    identity_type = Column(
        Enum(IdentityTypeEnum),
        nullable=False,
        default=IdentityTypeEnum.WORKFORCE_EMPLOYEE,
        index=True,
    )
    department = Column(String(128), nullable=True)
    employment_status = Column(
        Enum(EmploymentStatusEnum),
        nullable=False,
        default=EmploymentStatusEnum.ACTIVE,
        index=True,
    )
    risk_score = Column(Numeric(5, 2), nullable=False, default=0.00)  # 0.00 to 100.00
    risk_band = Column(
        Enum(IdentityRiskBandEnum),
        nullable=False,
        default=IdentityRiskBandEnum.LOW,
        index=True,
    )
    is_privileged = Column(Boolean, nullable=False, default=False)
    mfa_enabled = Column(Boolean, nullable=False, default=True)

    # Cross-Module Lineage to Phase 18 (Cloud Workload) & Platform Users
    cloud_asset_id = Column(
        Integer,
        ForeignKey("cloud_assets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "identity_code", name="uq_governed_identity_tenant_code"),
        UniqueConstraint("organization_id", "email", name="uq_governed_identity_tenant_email"),
        CheckConstraint("risk_score >= 0.00 AND risk_score <= 100.00", name="chk_governed_identity_risk_score"),
    )

    # Relationships
    assignments = relationship("IdentityEntitlementAssignment", back_populates="identity", cascade="all, delete-orphan")
    certification_items = relationship("AccessCertificationItem", back_populates="identity", cascade="all, delete-orphan")
    jit_requests = relationship("JITAccessRequest", back_populates="identity", cascade="all, delete-orphan")
    zero_trust_assessments = relationship("ZeroTrustAssessment", back_populates="identity", cascade="all, delete-orphan")
    sod_violations = relationship("SoDConflictViolation", back_populates="identity", cascade="all, delete-orphan")


# ─────────────────────────────────────────────────────────────────────────────
# 2. ENTITLEMENTS & ASSIGNMENTS
# ─────────────────────────────────────────────────────────────────────────────

class IdentityEntitlement(Base):
    """Governed System Permissions, Roles, and Entitlements."""
    __tablename__ = "identity_entitlements"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entitlement_code = Column(String(64), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    system_type = Column(
        Enum(SystemTypeEnum),
        nullable=False,
        default=SystemTypeEnum.AWS_IAM,
        index=True,
    )
    resource_name = Column(String(255), nullable=False)  # e.g. "arn:aws:iam::123456789012:role/ProductionAdmin"
    permission_scope = Column(String(128), nullable=False)  # e.g. "AdministratorAccess", "BillingReader"
    is_privileged = Column(Boolean, nullable=False, default=False)
    is_high_risk = Column(Boolean, nullable=False, default=False)
    risk_weight = Column(Numeric(3, 2), nullable=False, default=1.00)  # 1.00 to 5.00
    description = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "entitlement_code", name="uq_identity_entitlement_tenant_code"),
        CheckConstraint("risk_weight >= 1.00 AND risk_weight <= 5.00", name="chk_identity_entitlement_risk_weight"),
    )

    # Relationships
    assignments = relationship("IdentityEntitlementAssignment", back_populates="entitlement", cascade="all, delete-orphan")


class IdentityEntitlementAssignment(Base):
    """Active or Expired Association between an Identity and an Entitlement."""
    __tablename__ = "identity_entitlement_assignments"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    identity_id = Column(
        Integer,
        ForeignKey("governed_identities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entitlement_id = Column(
        Integer,
        ForeignKey("identity_entitlements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assigned_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    expires_at = Column(DateTime(timezone=True), nullable=True)
    assignment_type = Column(
        Enum(AssignmentTypeEnum),
        nullable=False,
        default=AssignmentTypeEnum.DIRECT,
    )
    is_active = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("organization_id", "identity_id", "entitlement_id", name="uq_identity_entitlement_assignment"),
    )

    # Relationships
    identity = relationship("GovernedIdentity", back_populates="assignments")
    entitlement = relationship("IdentityEntitlement", back_populates="assignments")


# ─────────────────────────────────────────────────────────────────────────────
# 3. ACCESS CERTIFICATION CAMPAIGNS & ITEMS (FOUR-EYES SoD)
# ─────────────────────────────────────────────────────────────────────────────

class AccessCertificationCampaign(Base):
    """Periodic or Targeted User Access Review Campaign."""
    __tablename__ = "access_certification_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    campaign_code = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    campaign_type = Column(
        Enum(CampaignTypeEnum),
        nullable=False,
        default=CampaignTypeEnum.PERIODIC_USER_ACCESS_REVIEW,
        index=True,
    )
    status = Column(
        Enum(CampaignStatusEnum),
        nullable=False,
        default=CampaignStatusEnum.DRAFT,
        index=True,
    )
    total_items_count = Column(Integer, nullable=False, default=0)
    certified_items_count = Column(Integer, nullable=False, default=0)
    revoked_items_count = Column(Integer, nullable=False, default=0)
    deadline = Column(DateTime(timezone=True), nullable=False)
    finalized_at = Column(DateTime(timezone=True), nullable=True)
    created_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "campaign_code", name="uq_access_campaign_tenant_code"),
    )

    # Relationships
    items = relationship("AccessCertificationItem", back_populates="campaign", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[created_by_id])


class AccessCertificationItem(Base):
    """Granular entitlement line item under Four-Eyes certification."""
    __tablename__ = "access_certification_items"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    campaign_id = Column(
        Integer,
        ForeignKey("access_certification_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    identity_id = Column(
        Integer,
        ForeignKey("governed_identities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entitlement_id = Column(
        Integer,
        ForeignKey("identity_entitlements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    decision = Column(
        Enum(CertificationDecisionEnum),
        nullable=False,
        default=CertificationDecisionEnum.PENDING,
        index=True,
    )
    decision_justification = Column(Text, nullable=True)
    reviewer_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    is_sod_violation = Column(Boolean, nullable=False, default=False)
    
    # Remediation Linkage if Revoked
    remediation_plan_id = Column(
        Integer,
        ForeignKey("remediation_plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "campaign_id", "identity_id", "entitlement_id", name="uq_access_cert_item"),
    )

    # Relationships
    campaign = relationship("AccessCertificationCampaign", back_populates="items")
    identity = relationship("GovernedIdentity", back_populates="certification_items")
    entitlement = relationship("IdentityEntitlement")
    reviewer = relationship("User", foreign_keys=[reviewer_id])


# ─────────────────────────────────────────────────────────────────────────────
# 4. JUST-IN-TIME (JIT) & PRIVILEGED ACCESS GOVERNANCE (FOUR-EYES)
# ─────────────────────────────────────────────────────────────────────────────

class JITAccessRequest(Base):
    """Four-Eyes Governed Just-In-Time Elevated Privilege Request."""
    __tablename__ = "jit_access_requests"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    request_code = Column(String(64), nullable=False, index=True)
    identity_id = Column(
        Integer,
        ForeignKey("governed_identities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entitlement_id = Column(
        Integer,
        ForeignKey("identity_entitlements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_duration_minutes = Column(Integer, nullable=False, default=60)  # 15 to 480 min
    business_justification = Column(Text, nullable=False)
    approval_status = Column(
        Enum(JITApprovalStatusEnum),
        nullable=False,
        default=JITApprovalStatusEnum.PENDING,
        index=True,
    )
    requested_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    approved_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=False)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "request_code", name="uq_jit_request_tenant_code"),
        CheckConstraint("requested_duration_minutes >= 15 AND requested_duration_minutes <= 480", name="chk_jit_duration_bounds"),
    )

    # Relationships
    identity = relationship("GovernedIdentity", back_populates="jit_requests")
    entitlement = relationship("IdentityEntitlement")
    requester = relationship("User", foreign_keys=[requested_by_id])
    approver = relationship("User", foreign_keys=[approved_by_id])


# ─────────────────────────────────────────────────────────────────────────────
# 5. ZERO TRUST ASSURANCE
# ─────────────────────────────────────────────────────────────────────────────

class ZeroTrustAssessment(Base):
    """Server-Authoritative Zero Trust Identity Assurance Assessment."""
    __tablename__ = "zero_trust_assessments"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assessment_code = Column(String(64), nullable=False, index=True)
    identity_id = Column(
        Integer,
        ForeignKey("governed_identities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_health_score = Column(Numeric(5, 2), nullable=False, default=100.00)
    auth_strength_score = Column(Numeric(5, 2), nullable=False, default=100.00)
    context_risk_score = Column(Numeric(5, 2), nullable=False, default=0.00)
    behavioral_anomaly_score = Column(Numeric(5, 2), nullable=False, default=0.00)
    zero_trust_assurance_score = Column(Numeric(5, 2), nullable=False, default=100.00)
    trust_level = Column(
        Enum(TrustLevelEnum),
        nullable=False,
        default=TrustLevelEnum.HIGH_TRUST,
        index=True,
    )

    evaluated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "assessment_code", name="uq_zt_assessment_tenant_code"),
        CheckConstraint("zero_trust_assurance_score >= 0.00 AND zero_trust_assurance_score <= 100.00", name="chk_zt_assurance_score"),
    )

    # Relationships
    identity = relationship("GovernedIdentity", back_populates="zero_trust_assessments")


# ─────────────────────────────────────────────────────────────────────────────
# 6. SEGREGATION OF DUTIES (SoD) POLICIES & VIOLATIONS
# ─────────────────────────────────────────────────────────────────────────────

class SoDConflictPolicy(Base):
    """Toxic combination / Segregation of Duties conflict rule."""
    __tablename__ = "sod_conflict_policies"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    policy_code = Column(String(64), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    entitlement_a_id = Column(
        Integer,
        ForeignKey("identity_entitlements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entitlement_b_id = Column(
        Integer,
        ForeignKey("identity_entitlements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    severity = Column(
        Enum(SoDPolicySeverityEnum),
        nullable=False,
        default=SoDPolicySeverityEnum.HIGH,
    )
    description = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "policy_code", name="uq_sod_policy_tenant_code"),
    )

    # Relationships
    entitlement_a = relationship("IdentityEntitlement", foreign_keys=[entitlement_a_id])
    entitlement_b = relationship("IdentityEntitlement", foreign_keys=[entitlement_b_id])
    violations = relationship("SoDConflictViolation", back_populates="policy", cascade="all, delete-orphan")


class SoDConflictViolation(Base):
    """Active Toxic Combination detected on an identity."""
    __tablename__ = "sod_conflict_violations"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    identity_id = Column(
        Integer,
        ForeignKey("governed_identities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    policy_id = Column(
        Integer,
        ForeignKey("sod_conflict_policies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(
        Enum(SoDViolationStatusEnum),
        nullable=False,
        default=SoDViolationStatusEnum.ACTIVE_VIOLATION,
        index=True,
    )
    
    # Remediation Linkage
    remediation_plan_id = Column(
        Integer,
        ForeignKey("remediation_plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    detected_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("organization_id", "identity_id", "policy_id", name="uq_sod_violation_instance"),
    )

    # Relationships
    identity = relationship("GovernedIdentity", back_populates="sod_violations")
    policy = relationship("SoDConflictPolicy", back_populates="violations")
