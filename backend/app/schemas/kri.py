from datetime import date, datetime, timezone, timedelta
import math
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.kri import (
    AppetiteStatementStatusEnum,
    BreachStatusEnum,
    KriDirectionEnum,
    KriEvaluationStatusEnum,
    KriFrequencyEnum,
    KriSourceTypeEnum,
    KriStatusEnum,
)
from app.models.risk import RiskCategoryEnum


# ─────────────────────────────────────────────────────────────────────────────
# 1. Risk Appetite Statement Schemas
# ─────────────────────────────────────────────────────────────────────────────

class RiskAppetiteStatementCreate(BaseModel):
    statement_code: str = Field(..., min_length=2, max_length=64)
    title: str = Field(..., min_length=3, max_length=255)
    executive_summary: str = Field(..., min_length=10)
    category_appetites: Dict[str, str] = Field(
        ...,
        description="Dictionary mapping RiskCategoryEnum values to acceptable bands: LOW, MODERATE, HIGH",
    )
    financial_risk_appetite_id: Optional[int] = None
    effective_from: date
    review_cadence_months: int = Field(12, ge=1, le=36)

    @field_validator("category_appetites")
    @classmethod
    def validate_category_appetites(cls, v: Dict[str, str]) -> Dict[str, str]:
        valid_bands = {"LOW", "MODERATE", "HIGH"}
        for cat, band in v.items():
            if band.upper() not in valid_bands:
                raise ValueError(f"Invalid appetite band '{band}' for category '{cat}'. Must be LOW, MODERATE, or HIGH.")
        return v


class RiskAppetiteStatementResponse(BaseModel):
    id: int
    organization_id: int
    statement_code: str
    title: str
    executive_summary: str
    version: int
    status: AppetiteStatementStatusEnum
    category_appetites: Dict[str, Any]
    financial_risk_appetite_id: Optional[int]
    requested_by_id: int
    approved_by_id: Optional[int]
    approved_at: Optional[datetime]
    effective_from: date
    review_cadence_months: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# 2. KRI Threshold Schemas
# ─────────────────────────────────────────────────────────────────────────────

class KriThresholdCreate(BaseModel):
    warning_threshold: float
    critical_threshold: float
    range_min_warning: Optional[float] = None
    range_max_warning: Optional[float] = None
    range_min_critical: Optional[float] = None
    range_max_critical: Optional[float] = None

    @field_validator("warning_threshold", "critical_threshold")
    @classmethod
    def check_finite_numbers(cls, v: float) -> float:
        if math.isnan(v) or math.isinf(v):
            raise ValueError("Threshold values must be finite floating-point numbers.")
        return v

    @model_validator(mode="after")
    def validate_range_thresholds(self) -> "KriThresholdCreate":
        # Check range bounds if present
        for attr in ["range_min_warning", "range_max_warning", "range_min_critical", "range_max_critical"]:
            val = getattr(self, attr)
            if val is not None and (math.isnan(val) or math.isinf(val)):
                raise ValueError(f"{attr} must be a finite number.")

        if self.range_min_warning is not None and self.range_max_warning is not None:
            if self.range_min_warning >= self.range_max_warning:
                raise ValueError("range_min_warning must be strictly less than range_max_warning.")
        if self.range_min_critical is not None and self.range_max_critical is not None:
            if self.range_min_critical >= self.range_max_critical:
                raise ValueError("range_min_critical must be strictly less than range_max_critical.")
        return self


class KriThresholdResponse(BaseModel):
    id: int
    organization_id: int
    kri_id: int
    version: int
    is_active: bool
    warning_threshold: float
    critical_threshold: float
    range_min_warning: Optional[float]
    range_max_warning: Optional[float]
    range_min_critical: Optional[float]
    range_max_critical: Optional[float]
    effective_from: datetime
    effective_to: Optional[datetime]
    created_by_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# 3. Key Risk Indicator Schemas
# ─────────────────────────────────────────────────────────────────────────────

class KeyRiskIndicatorCreate(BaseModel):
    kri_code: str = Field(..., min_length=2, max_length=64)
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=5)
    risk_category: RiskCategoryEnum
    unit_of_measure: str = Field(..., min_length=1, max_length=32)
    frequency: KriFrequencyEnum = KriFrequencyEnum.DAILY
    direction: KriDirectionEnum = KriDirectionEnum.LOWER_IS_BETTER
    owner_id: Optional[int] = None
    initial_threshold: Optional[KriThresholdCreate] = None

    @model_validator(mode="after")
    def validate_initial_threshold(self) -> "KeyRiskIndicatorCreate":
        if self.initial_threshold:
            t = self.initial_threshold
            if self.direction == KriDirectionEnum.LOWER_IS_BETTER:
                if t.warning_threshold >= t.critical_threshold:
                    raise ValueError(
                        f"For LOWER_IS_BETTER, warning_threshold ({t.warning_threshold}) "
                        f"must be strictly less than critical_threshold ({t.critical_threshold})."
                    )
            elif self.direction == KriDirectionEnum.HIGHER_IS_BETTER:
                if t.critical_threshold >= t.warning_threshold:
                    raise ValueError(
                        f"For HIGHER_IS_BETTER, critical_threshold ({t.critical_threshold}) "
                        f"must be strictly less than warning_threshold ({t.warning_threshold})."
                    )
        return self


class KeyRiskIndicatorUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = Field(None, min_length=5)
    unit_of_measure: Optional[str] = Field(None, min_length=1, max_length=32)
    frequency: Optional[KriFrequencyEnum] = None
    owner_id: Optional[int] = None
    status: Optional[KriStatusEnum] = None


class KeyRiskIndicatorResponse(BaseModel):
    id: int
    organization_id: int
    kri_code: str
    title: str
    description: str
    risk_category: RiskCategoryEnum
    unit_of_measure: str
    frequency: KriFrequencyEnum
    direction: KriDirectionEnum
    status: KriStatusEnum
    owner_id: Optional[int]
    latest_value: Optional[float]
    latest_observed_at: Optional[datetime]
    latest_evaluation_status: KriEvaluationStatusEnum
    created_by_id: int
    created_at: datetime
    updated_at: datetime
    active_threshold: Optional[KriThresholdResponse] = None

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# 4. KRI Observation Schemas
# ─────────────────────────────────────────────────────────────────────────────

class KriObservationCreate(BaseModel):
    observed_value: float
    unit: str = Field(..., min_length=1, max_length=32)
    observed_at: datetime
    source_type: KriSourceTypeEnum = KriSourceTypeEnum.MANUAL_ENTRY
    source_identifier: Optional[str] = Field(None, max_length=128)
    notes: Optional[str] = None
    idempotency_key: Optional[str] = Field(None, max_length=64)

    @field_validator("observed_value")
    @classmethod
    def validate_finite_value(cls, v: float) -> float:
        if math.isnan(v) or math.isinf(v):
            raise ValueError("Observed value must be a valid finite number.")
        return v

    @field_validator("observed_at")
    @classmethod
    def validate_not_future(cls, v: datetime) -> datetime:
        # Normalize timezone to UTC
        now_utc = datetime.now(timezone.utc)
        target = v if v.tzinfo else v.replace(tzinfo=timezone.utc)
        if target > now_utc + timedelta(seconds=60):
            raise ValueError("Observation timestamp cannot be in the future (exceeds clock skew tolerance).")
        return v


class KriObservationResponse(BaseModel):
    id: int
    organization_id: int
    kri_id: int
    observed_value: float
    unit: str
    observed_at: datetime
    source_type: KriSourceTypeEnum
    source_identifier: Optional[str]
    notes: Optional[str]
    idempotency_key: Optional[str]
    data_hash_sha256: str
    created_by_id: Optional[int]
    created_at: datetime
    evaluation_status: Optional[KriEvaluationStatusEnum] = None
    breach_id: Optional[int] = None

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# 5. KRI Breach Record Schemas
# ─────────────────────────────────────────────────────────────────────────────

class KriBreachResponse(BaseModel):
    id: int
    organization_id: int
    kri_id: int
    breach_code: str
    threshold_id: int
    trigger_observation_id: int
    latest_observation_id: int
    status: BreachStatusEnum
    breach_value: float
    peak_value: float
    detected_at: datetime
    last_evaluated_at: datetime
    acknowledged_at: Optional[datetime]
    acknowledged_by_id: Optional[int]
    escalated_at: Optional[datetime]
    escalated_finding_id: Optional[int]
    recovered_at: Optional[datetime]
    closed_at: Optional[datetime]
    closed_by_id: Optional[int]
    closure_notes: Optional[str]

    model_config = {"from_attributes": True}


class KriBreachAcknowledgeRequest(BaseModel):
    notes: Optional[str] = None


class KriBreachEscalateFindingRequest(BaseModel):
    organization_control_id: int = Field(..., description="Required authoritative control gap link.")
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    severity: Optional[str] = Field("HIGH", description="CRITICAL, HIGH, MEDIUM, LOW")


class KriBreachCloseRequest(BaseModel):
    closure_notes: str = Field(..., min_length=5, description="Required Four-Eyes justification for breach closure.")


# ─────────────────────────────────────────────────────────────────────────────
# 6. KRI Risk Link Schemas
# ─────────────────────────────────────────────────────────────────────────────

class KriRiskLinkCreate(BaseModel):
    risk_id: int
    correlation_weight: float = Field(1.0, ge=-1.0, le=1.0)
    notes: Optional[str] = None

    @field_validator("correlation_weight")
    @classmethod
    def validate_weight_range(cls, v: float) -> float:
        if math.isnan(v) or math.isinf(v):
            raise ValueError("Correlation weight must be a finite number.")
        if v < -1.0 or v > 1.0:
            raise ValueError("Correlation weight must be between -1.0 and 1.0 inclusive.")
        return round(v, 4)


class KriRiskLinkResponse(BaseModel):
    id: int
    organization_id: int
    kri_id: int
    risk_id: int
    correlation_weight: float
    notes: Optional[str]
    created_by_id: Optional[int]
    created_at: datetime
    risk_title: Optional[str] = None

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# 7. KRI Executive / Telemetry Overview Schemas
# ─────────────────────────────────────────────────────────────────────────────

class KriTelemetryOverviewResponse(BaseModel):
    total_kris: int
    normal_kris: int
    warning_kris: int
    critical_kris: int
    stale_kris: int
    active_breaches: int
    appetite_compliance_rate: float
