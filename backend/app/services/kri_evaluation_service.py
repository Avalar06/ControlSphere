from datetime import datetime, timezone, timedelta
import hashlib
import json
import math
from typing import Any, Optional
from sqlalchemy.orm import Session

from app.models.kri import (
    BreachStatusEnum,
    KeyRiskIndicator,
    KriBreachRecord,
    KriDirectionEnum,
    KriEvaluationStatusEnum,
    KriFrequencyEnum,
    KriObservation,
    KriStatusEnum,
    KriThreshold,
)
from app.models.user import User
from app.services.audit_service import AuditService


class KriEvaluationService:
    """Deterministic server-authoritative KRI threshold evaluation, provenance hashing, and hysteresis engine."""

    CADENCE_INTERVALS = {
        KriFrequencyEnum.HOURLY: timedelta(hours=1),
        KriFrequencyEnum.DAILY: timedelta(days=1),
        KriFrequencyEnum.WEEKLY: timedelta(days=7),
        KriFrequencyEnum.MONTHLY: timedelta(days=30),
        KriFrequencyEnum.QUARTERLY: timedelta(days=90),
    }

    @classmethod
    def _log_action(
        cls,
        db: Session,
        organization_id: int,
        user_id: Optional[int],
        action: str,
        entity_type: str,
        entity_id: Any,
        details: Optional[dict] = None,
    ) -> None:
        user = db.query(User).filter(User.id == user_id).first() if user_id else None
        actor_email = user.email if user else "system@controlsphere.internal"
        AuditService.log(
            db=db,
            organization_id=organization_id,
            action=action,
            resource_type=entity_type,
            actor_email=actor_email,
            actor_id=user_id,
            resource_id=str(entity_id) if entity_id is not None else None,
            details=details or {},
        )

    @classmethod
    def compute_observation_digest(
        cls,
        kri_id: int,
        value: float,
        unit: str,
        observed_at: datetime,
        source_type: str,
        source_identifier: Optional[str] = None,
    ) -> str:
        """Compute SHA-256 cryptographic digest over canonical JSON serialization."""
        obs_utc = observed_at if observed_at.tzinfo else observed_at.replace(tzinfo=timezone.utc)
        payload = {
            "kri_id": int(kri_id),
            "observed_at": obs_utc.isoformat(),
            "source_identifier": str(source_identifier) if source_identifier else "",
            "source_type": str(source_type),
            "unit": str(unit).strip().upper(),
            "value": round(float(value), 6),
        }
        canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    @classmethod
    def evaluate_observation(
        cls,
        direction: KriDirectionEnum,
        threshold: KriThreshold,
        observed_value: float,
    ) -> KriEvaluationStatusEnum:
        """Server-authoritative directional evaluation with strict boundary equality."""
        if math.isnan(observed_value) or math.isinf(observed_value):
            raise ValueError("Observed value must be a finite number.")

        v = float(observed_value)

        if direction == KriDirectionEnum.LOWER_IS_BETTER:
            # Normal: v <= warning_threshold
            # Warning: warning_threshold < v <= critical_threshold
            # Critical / Breach: v > critical_threshold
            if v <= threshold.warning_threshold:
                return KriEvaluationStatusEnum.NORMAL
            elif v <= threshold.critical_threshold:
                return KriEvaluationStatusEnum.WARNING
            else:
                return KriEvaluationStatusEnum.CRITICAL

        elif direction == KriDirectionEnum.HIGHER_IS_BETTER:
            # Normal: v >= warning_threshold
            # Warning: critical_threshold <= v < warning_threshold
            # Critical / Breach: v < critical_threshold
            if v >= threshold.warning_threshold:
                return KriEvaluationStatusEnum.NORMAL
            elif v >= threshold.critical_threshold:
                return KriEvaluationStatusEnum.WARNING
            else:
                return KriEvaluationStatusEnum.CRITICAL

        elif direction == KriDirectionEnum.WITHIN_RANGE:
            # Parameterized bounds
            warn_min = (
                threshold.range_min_warning
                if threshold.range_min_warning is not None
                else threshold.warning_threshold
            )
            warn_max = (
                threshold.range_max_warning
                if threshold.range_max_warning is not None
                else threshold.critical_threshold
            )
            crit_min = (
                threshold.range_min_critical
                if threshold.range_min_critical is not None
                else warn_min - (warn_max - warn_min) * 0.5
            )
            crit_max = (
                threshold.range_max_critical
                if threshold.range_max_critical is not None
                else warn_max + (warn_max - warn_min) * 0.5
            )

            # Normal: warn_min <= v <= warn_max
            # Warning: [crit_min <= v < warn_min] or [warn_max < v <= crit_max]
            # Critical: v < crit_min or v > crit_max
            if warn_min <= v <= warn_max:
                return KriEvaluationStatusEnum.NORMAL
            elif crit_min <= v <= crit_max:
                return KriEvaluationStatusEnum.WARNING
            else:
                return KriEvaluationStatusEnum.CRITICAL

        return KriEvaluationStatusEnum.NORMAL

    @classmethod
    def check_is_stale(
        cls,
        frequency: KriFrequencyEnum,
        latest_observed_at: Optional[datetime],
        current_time: Optional[datetime] = None,
    ) -> bool:
        """Determines if KRI telemetry is stale based on 1.5x nominal cadence window."""
        if latest_observed_at is None:
            return True

        now_utc = current_time or datetime.now(timezone.utc)
        obs_utc = (
            latest_observed_at
            if latest_observed_at.tzinfo
            else latest_observed_at.replace(tzinfo=timezone.utc)
        )

        interval = cls.CADENCE_INTERVALS.get(frequency, timedelta(days=1))
        stale_threshold = 1.5 * interval

        return (now_utc - obs_utc) > stale_threshold

    @classmethod
    def process_breach_lifecycle_and_hysteresis(
        cls,
        db: Session,
        kri: KeyRiskIndicator,
        threshold: KriThreshold,
        observation: KriObservation,
        eval_status: KriEvaluationStatusEnum,
        actor_id: Optional[int] = None,
    ) -> Optional[KriBreachRecord]:
        """Apply anti-flapping hysteresis: reuse active breaches, track peak severity, transition to RECOVERED."""
        now_utc = datetime.now(timezone.utc)

        # Query for existing active breach for this KRI in this tenant
        active_breach = (
            db.query(KriBreachRecord)
            .filter(
                KriBreachRecord.organization_id == kri.organization_id,
                KriBreachRecord.kri_id == kri.id,
                KriBreachRecord.status.in_(
                    [
                        BreachStatusEnum.DETECTED,
                        BreachStatusEnum.ACKNOWLEDGED,
                        BreachStatusEnum.ESCALATED,
                    ]
                ),
            )
            .first()
        )

        if eval_status == KriEvaluationStatusEnum.CRITICAL:
            if active_breach:
                # Anti-flapping: Do not spawn duplicate breach. Update peak value and evaluation timestamp.
                active_breach.latest_observation_id = observation.id
                active_breach.last_evaluated_at = now_utc

                if kri.direction == KriDirectionEnum.LOWER_IS_BETTER:
                    if observation.observed_value > active_breach.peak_value:
                        active_breach.peak_value = observation.observed_value
                elif kri.direction == KriDirectionEnum.HIGHER_IS_BETTER:
                    if observation.observed_value < active_breach.peak_value:
                        active_breach.peak_value = observation.observed_value
                else:
                    # For range, keep whichever deviates further from middle of warn range
                    active_breach.peak_value = observation.observed_value

                db.flush()
                return active_breach
            else:
                # Spawn new breach
                breach_seq = (
                    db.query(KriBreachRecord)
                    .filter(KriBreachRecord.organization_id == kri.organization_id)
                    .count()
                    + 1
                )
                breach_code = f"BRC-{kri.kri_code}-{breach_seq:04d}"

                new_breach = KriBreachRecord(
                    organization_id=kri.organization_id,
                    kri_id=kri.id,
                    breach_code=breach_code,
                    threshold_id=threshold.id,
                    trigger_observation_id=observation.id,
                    latest_observation_id=observation.id,
                    status=BreachStatusEnum.DETECTED,
                    breach_value=observation.observed_value,
                    peak_value=observation.observed_value,
                    detected_at=now_utc,
                    last_evaluated_at=now_utc,
                )
                db.add(new_breach)
                db.flush()

                cls._log_action(
                    db=db,
                    organization_id=kri.organization_id,
                    user_id=actor_id,
                    action="kri_breach_detected",
                    entity_type="kri_breach_record",
                    entity_id=new_breach.id,
                    details={
                        "breach_code": breach_code,
                        "kri_code": kri.kri_code,
                        "breach_value": observation.observed_value,
                        "critical_threshold": threshold.critical_threshold,
                    },
                )
                return new_breach

        elif eval_status in [KriEvaluationStatusEnum.NORMAL, KriEvaluationStatusEnum.WARNING]:
            if active_breach:
                # Metric numerically recovered; transitions to RECOVERED (distinct from CLOSED)
                active_breach.status = BreachStatusEnum.RECOVERED
                active_breach.recovered_at = now_utc
                active_breach.latest_observation_id = observation.id
                active_breach.last_evaluated_at = now_utc
                db.flush()

                cls._log_action(
                    db=db,
                    organization_id=kri.organization_id,
                    user_id=actor_id,
                    action="kri_breach_recovered",
                    entity_type="kri_breach_record",
                    entity_id=active_breach.id,
                    details={
                        "breach_code": active_breach.breach_code,
                        "kri_code": kri.kri_code,
                        "recovered_value": observation.observed_value,
                    },
                )
                return active_breach

        return active_breach
