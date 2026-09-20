from datetime import datetime, timezone, date
import enum
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.models.risk import RiskCategoryEnum


# ─────────────────────────────────────────────────────────────────────────────
# Domain Enums for Batch 2: KRI-APPETITE-GRC
# ─────────────────────────────────────────────────────────────────────────────

class AppetiteStatementStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    SUPERSEDED = "SUPERSEDED"


class KriFrequencyEnum(str, enum.Enum):
    HOURLY = "HOURLY"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"


class KriDirectionEnum(str, enum.Enum):
    LOWER_IS_BETTER = "LOWER_IS_BETTER"
    HIGHER_IS_BETTER = "HIGHER_IS_BETTER"
    WITHIN_RANGE = "WITHIN_RANGE"


class KriStatusEnum(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    STALE_DATA = "STALE_DATA"


class KriEvaluationStatusEnum(str, enum.Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class KriSourceTypeEnum(str, enum.Enum):
    MANUAL_ENTRY = "MANUAL_ENTRY"
    RISK_REVALUATION = "RISK_REVALUATION"
    QUANTRISK_SIMULATION = "QUANTRISK_SIMULATION"
    CCM_HEALTH_CHECK = "CCM_HEALTH_CHECK"
    EVIDENCE_PIPELINE = "EVIDENCE_PIPELINE"
    COMPLIANCE_DRIFT = "COMPLIANCE_DRIFT"
    INTEGRATION_SYNC = "INTEGRATION_SYNC"


class BreachStatusEnum(str, enum.Enum):
    DETECTED = "DETECTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ESCALATED = "ESCALATED"
    RECOVERED = "RECOVERED"
    CLOSED = "CLOSED"


# ─────────────────────────────────────────────────────────────────────────────
# 1. RISK APPETITE STATEMENTS (Strategic / Organizational Policy Layer)
# ─────────────────────────────────────────────────────────────────────────────

class RiskAppetiteStatement(Base):
    """Board-approved organizational risk appetite policy statements per category."""
    __tablename__ = "risk_appetite_statements"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    statement_code = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    executive_summary = Column(Text, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    status = Column(
        Enum(AppetiteStatementStatusEnum),
        nullable=False,
        default=AppetiteStatementStatusEnum.DRAFT,
        index=True,
    )

    # Category Risk Appetite Bands: e.g. {"CYBERSECURITY": "LOW", "OPERATIONAL": "MODERATE"}
    category_appetites = Column(JSON, nullable=False, default=dict)

    # Optional Linkage to QuantRisk Financial Risk Appetite (Phase 12 authority)
    financial_risk_appetite_id = Column(
        Integer,
        ForeignKey("financial_risk_appetites.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Four-Eyes Governance Attributions
    requested_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    approved_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    approved_at = Column(DateTime(timezone=True), nullable=True)

    effective_from = Column(Date, nullable=False, index=True)
    review_cadence_months = Column(Integer, nullable=False, default=12)

    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id", "statement_code", name="uq_appetite_statement_code_per_tenant"
        ),
    )

    # Relationships
    organization = relationship("Organization")
    financial_risk_appetite = relationship("FinancialRiskAppetite")
    requested_by = relationship("User", foreign_keys=[requested_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])


# ─────────────────────────────────────────────────────────────────────────────
# 2. KEY RISK INDICATORS (Metric Definition Layer)
# ─────────────────────────────────────────────────────────────────────────────

class KeyRiskIndicator(Base):
    """Authoritative KRI definitions, metadata, and denormalized operational status."""
    __tablename__ = "key_risk_indicators"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kri_code = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    risk_category = Column(Enum(RiskCategoryEnum), nullable=False, index=True)
    unit_of_measure = Column(String(32), nullable=False)  # e.g., "PERCENTAGE", "COUNT", "USD"
    frequency = Column(
        Enum(KriFrequencyEnum), nullable=False, default=KriFrequencyEnum.DAILY, index=True
    )
    direction = Column(
        Enum(KriDirectionEnum), nullable=False, default=KriDirectionEnum.LOWER_IS_BETTER, index=True
    )
    status = Column(
        Enum(KriStatusEnum), nullable=False, default=KriStatusEnum.ACTIVE, index=True
    )
    owner_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Server-Authoritative Denormalized Latest Telemetry
    latest_value = Column(Float, nullable=True)
    latest_observed_at = Column(DateTime(timezone=True), nullable=True, index=True)
    latest_evaluation_status = Column(
        Enum(KriEvaluationStatusEnum),
        nullable=False,
        default=KriEvaluationStatusEnum.NORMAL,
        index=True,
    )

    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "kri_code", name="uq_kri_code_per_tenant"),
    )

    # Relationships
    organization = relationship("Organization")
    owner = relationship("User", foreign_keys=[owner_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    thresholds = relationship("KriThreshold", back_populates="kri", cascade="all, delete-orphan")
    observations = relationship("KriObservation", back_populates="kri", cascade="all, delete-orphan")
    breaches = relationship("KriBreachRecord", back_populates="kri", cascade="all, delete-orphan")
    risk_links = relationship("KriRiskLink", back_populates="kri", cascade="all, delete-orphan")


# ─────────────────────────────────────────────────────────────────────────────
# 3. KRI THRESHOLDS (Tolerance Boundaries & Versioning)
# ─────────────────────────────────────────────────────────────────────────────

class KriThreshold(Base):
    """Versioned amber/red tolerance thresholds governing KRI evaluations."""
    __tablename__ = "kri_thresholds"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kri_id = Column(
        Integer, ForeignKey("key_risk_indicators.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=True, index=True)

    # Threshold limits for LOWER_IS_BETTER and HIGHER_IS_BETTER
    warning_threshold = Column(Float, nullable=False)   # Amber boundary
    critical_threshold = Column(Float, nullable=False)  # Red / Breach boundary

    # Threshold bounds for WITHIN_RANGE
    range_min_warning = Column(Float, nullable=True)
    range_max_warning = Column(Float, nullable=True)
    range_min_critical = Column(Float, nullable=True)
    range_max_critical = Column(Float, nullable=True)

    effective_from = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    effective_to = Column(DateTime(timezone=True), nullable=True)

    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("kri_id", "version", name="uq_kri_threshold_version"),
    )

    # Relationships
    organization = relationship("Organization")
    kri = relationship("KeyRiskIndicator", back_populates="thresholds")
    created_by = relationship("User", foreign_keys=[created_by_id])


# ─────────────────────────────────────────────────────────────────────────────
# 4. KRI OBSERVATIONS (Append-Only Immutable Telemetry)
# ─────────────────────────────────────────────────────────────────────────────

class KriObservation(Base):
    """Append-only immutable time-series observations with SHA-256 provenance digest."""
    __tablename__ = "kri_observations"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kri_id = Column(
        Integer, ForeignKey("key_risk_indicators.id", ondelete="CASCADE"), nullable=False, index=True
    )
    observed_value = Column(Float, nullable=False)
    unit = Column(String(32), nullable=False)
    observed_at = Column(DateTime(timezone=True), nullable=False, index=True)
    source_type = Column(
        Enum(KriSourceTypeEnum), nullable=False, default=KriSourceTypeEnum.MANUAL_ENTRY, index=True
    )
    source_identifier = Column(String(128), nullable=True)
    notes = Column(Text, nullable=True)
    idempotency_key = Column(String(64), nullable=True, index=True)

    # Cryptographic integrity digest over canonical representation
    data_hash_sha256 = Column(String(64), nullable=False, index=True)

    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    organization = relationship("Organization")
    kri = relationship("KeyRiskIndicator", back_populates="observations")
    created_by = relationship("User", foreign_keys=[created_by_id])


# ─────────────────────────────────────────────────────────────────────────────
# 5. KRI BREACH RECORDS (Governed Tolerance Violation State Machine)
# ─────────────────────────────────────────────────────────────────────────────

class KriBreachRecord(Base):
    """Governed state machine event tracking active and historical KRI breaches."""
    __tablename__ = "kri_breach_records"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kri_id = Column(
        Integer, ForeignKey("key_risk_indicators.id", ondelete="CASCADE"), nullable=False, index=True
    )
    breach_code = Column(String(64), nullable=False, index=True)
    threshold_id = Column(
        Integer, ForeignKey("kri_thresholds.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    trigger_observation_id = Column(
        Integer, ForeignKey("kri_observations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    latest_observation_id = Column(
        Integer, ForeignKey("kri_observations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status = Column(
        Enum(BreachStatusEnum), nullable=False, default=BreachStatusEnum.DETECTED, index=True
    )

    breach_value = Column(Float, nullable=False)
    peak_value = Column(Float, nullable=False)
    detected_at = Column(DateTime(timezone=True), nullable=False, index=True)
    last_evaluated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    escalated_at = Column(DateTime(timezone=True), nullable=True)
    escalated_finding_id = Column(
        Integer, ForeignKey("findings.id", ondelete="SET NULL"), nullable=True, index=True
    )

    recovered_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    closed_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    closure_notes = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "organization_id", "breach_code", name="uq_kri_breach_code_per_tenant"
        ),
    )

    # Relationships
    organization = relationship("Organization")
    kri = relationship("KeyRiskIndicator", back_populates="breaches")
    threshold = relationship("KriThreshold")
    trigger_observation = relationship("KriObservation", foreign_keys=[trigger_observation_id])
    latest_observation = relationship("KriObservation", foreign_keys=[latest_observation_id])
    acknowledged_by = relationship("User", foreign_keys=[acknowledged_by_id])
    closed_by = relationship("User", foreign_keys=[closed_by_id])
    escalated_finding = relationship("Finding", foreign_keys=[escalated_finding_id])


# ─────────────────────────────────────────────────────────────────────────────
# 6. KRI RISK LINKS (Many-to-Many Association with Correlation Weights)
# ─────────────────────────────────────────────────────────────────────────────

class KriRiskLink(Base):
    """Many-to-many linkage between KRIs and operational risks with governed correlation weight."""
    __tablename__ = "kri_risk_links"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kri_id = Column(
        Integer, ForeignKey("key_risk_indicators.id", ondelete="CASCADE"), nullable=False, index=True
    )
    risk_id = Column(
        Integer, ForeignKey("risks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    correlation_weight = Column(Float, nullable=False, default=1.0)  # Range: [-1.0, 1.0]
    notes = Column(Text, nullable=True)

    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("kri_id", "risk_id", name="uq_kri_risk_link"),
        CheckConstraint(
            "correlation_weight >= -1.0 AND correlation_weight <= 1.0",
            name="chk_kri_risk_correlation_weight",
        ),
    )

    # Relationships
    organization = relationship("Organization")
    kri = relationship("KeyRiskIndicator", back_populates="risk_links")
    risk = relationship("Risk")
    created_by = relationship("User", foreign_keys=[created_by_id])
