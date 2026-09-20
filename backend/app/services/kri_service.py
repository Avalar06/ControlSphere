from datetime import datetime, timezone, timedelta
import math
from typing import Any, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.control import OrganizationControl
from app.models.finding import Finding, FindingSeverityEnum, FindingTypeEnum
from app.models.kri import (
    AppetiteStatementStatusEnum,
    BreachStatusEnum,
    KeyRiskIndicator,
    KriBreachRecord,
    KriDirectionEnum,
    KriEvaluationStatusEnum,
    KriObservation,
    KriRiskLink,
    KriStatusEnum,
    KriThreshold,
    RiskAppetiteStatement,
)
from app.models.quant_risk import FinancialRiskAppetite
from app.models.risk import Risk
from app.models.user import User
from app.schemas.kri import (
    KeyRiskIndicatorCreate,
    KeyRiskIndicatorUpdate,
    KriBreachAcknowledgeRequest,
    KriBreachCloseRequest,
    KriBreachEscalateFindingRequest,
    KriObservationCreate,
    KriRiskLinkCreate,
    KriThresholdCreate,
    RiskAppetiteStatementCreate,
)
from app.services.audit_service import AuditService
from app.services.kri_evaluation_service import KriEvaluationService


class KriService:
    """Comprehensive domain service orchestrating KRI definitions, thresholds, observations, and breach governance."""

    @classmethod
    def _log_action(
        cls,
        db: Session,
        organization_id: int,
        actor_id: Optional[int],
        action: str,
        entity_type: str,
        entity_id: Any,
        details: Optional[dict] = None,
    ) -> None:
        user = db.query(User).filter(User.id == actor_id).first() if actor_id else None
        actor_email = user.email if user else "system@controlsphere.internal"
        AuditService.log(
            db=db,
            organization_id=organization_id,
            action=action,
            resource_type=entity_type,
            actor_email=actor_email,
            actor_id=actor_id,
            resource_id=str(entity_id) if entity_id is not None else None,
            details=details or {},
        )


    # ─────────────────────────────────────────────────────────────────────────
    # 1. Risk Appetite Statements
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def create_appetite_statement(
        cls,
        db: Session,
        organization_id: int,
        data: RiskAppetiteStatementCreate,
        actor_id: int,
    ) -> RiskAppetiteStatement:
        # Verify statement_code uniqueness per tenant
        existing = (
            db.query(RiskAppetiteStatement)
            .filter(
                RiskAppetiteStatement.organization_id == organization_id,
                RiskAppetiteStatement.statement_code == data.statement_code,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Risk appetite statement with code '{data.statement_code}' already exists.",
            )

        # Enforce tenant isolation on linked financial appetite
        if data.financial_risk_appetite_id is not None:
            fin_appetite = (
                db.query(FinancialRiskAppetite)
                .filter(
                    FinancialRiskAppetite.id == data.financial_risk_appetite_id,
                    FinancialRiskAppetite.organization_id == organization_id,
                )
                .first()
            )
            if not fin_appetite:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Financial risk appetite ID {data.financial_risk_appetite_id} not found in this organization.",
                )

        statement = RiskAppetiteStatement(
            organization_id=organization_id,
            statement_code=data.statement_code,
            title=data.title,
            executive_summary=data.executive_summary,
            version=1,
            status=AppetiteStatementStatusEnum.DRAFT,
            category_appetites=data.category_appetites,
            financial_risk_appetite_id=data.financial_risk_appetite_id,
            requested_by_id=actor_id,
            effective_from=data.effective_from,
            review_cadence_months=data.review_cadence_months,
        )
        db.add(statement)
        db.commit()
        db.refresh(statement)

        cls._log_action(
            db=db,
            organization_id=organization_id,
            actor_id=actor_id,
            action="risk_appetite_statement_created",
            entity_type="risk_appetite_statement",
            entity_id=statement.id,
            details={"statement_code": statement.statement_code, "version": statement.version},
        )
        return statement

    @classmethod
    def approve_appetite_statement(
        cls,
        db: Session,
        organization_id: int,
        statement_id: int,
        actor_id: int,
    ) -> RiskAppetiteStatement:
        statement = (
            db.query(RiskAppetiteStatement)
            .filter(
                RiskAppetiteStatement.id == statement_id,
                RiskAppetiteStatement.organization_id == organization_id,
            )
            .first()
        )
        if not statement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Risk appetite statement not found.",
            )

        # Prevent re-approving an already approved statement
        if statement.status == AppetiteStatementStatusEnum.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Statement is already approved.",
            )

        # Four-Eyes Governance: Approver must be distinct from requester
        if statement.requested_by_id == actor_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Four-Eyes Violation: Approver must be distinct from requester.",
            )

        now_utc = datetime.now(timezone.utc)

        # Atomically supersede any currently active statement for this tenant
        current_active = (
            db.query(RiskAppetiteStatement)
            .filter(
                RiskAppetiteStatement.organization_id == organization_id,
                RiskAppetiteStatement.status == AppetiteStatementStatusEnum.APPROVED,
            )
            .all()
        )
        for prev in current_active:
            prev.status = AppetiteStatementStatusEnum.SUPERSEDED
            prev.updated_at = now_utc

        statement.status = AppetiteStatementStatusEnum.APPROVED
        statement.approved_by_id = actor_id
        statement.approved_at = now_utc
        statement.updated_at = now_utc

        db.commit()
        db.refresh(statement)

        cls._log_action(
            db=db,
            organization_id=organization_id,
            actor_id=actor_id,
            action="risk_appetite_statement_approved",
            entity_type="risk_appetite_statement",
            entity_id=statement.id,
            details={"statement_code": statement.statement_code, "version": statement.version},
        )
        return statement

    @classmethod
    def list_appetite_statements(
        cls,
        db: Session,
        organization_id: int,
    ) -> List[RiskAppetiteStatement]:
        return (
            db.query(RiskAppetiteStatement)
            .filter(RiskAppetiteStatement.organization_id == organization_id)
            .order_by(RiskAppetiteStatement.version.desc(), RiskAppetiteStatement.created_at.desc())
            .all()
        )

    @classmethod
    def get_appetite_statement(
        cls,
        db: Session,
        organization_id: int,
        statement_id: int,
    ) -> RiskAppetiteStatement:
        statement = (
            db.query(RiskAppetiteStatement)
            .filter(
                RiskAppetiteStatement.id == statement_id,
                RiskAppetiteStatement.organization_id == organization_id,
            )
            .first()
        )
        if not statement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Risk appetite statement not found.",
            )
        return statement

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Key Risk Indicators & Thresholds
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def create_kri(
        cls,
        db: Session,
        organization_id: int,
        data: KeyRiskIndicatorCreate,
        actor_id: int,
    ) -> KeyRiskIndicator:
        existing = (
            db.query(KeyRiskIndicator)
            .filter(
                KeyRiskIndicator.organization_id == organization_id,
                KeyRiskIndicator.kri_code == data.kri_code,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"KRI with code '{data.kri_code}' already exists in this organization.",
            )

        kri = KeyRiskIndicator(
            organization_id=organization_id,
            kri_code=data.kri_code,
            title=data.title,
            description=data.description,
            risk_category=data.risk_category,
            unit_of_measure=data.unit_of_measure.strip().upper(),
            frequency=data.frequency,
            direction=data.direction,
            status=KriStatusEnum.ACTIVE,
            owner_id=data.owner_id,
            created_by_id=actor_id,
        )
        db.add(kri)
        db.flush()

        # If initial threshold provided, activate it
        if data.initial_threshold:
            cls.create_threshold(
                db=db,
                organization_id=organization_id,
                kri=kri,
                data=data.initial_threshold,
                actor_id=actor_id,
                is_initial=True,
            )

        db.commit()
        db.refresh(kri)

        cls._log_action(
            db=db,
            organization_id=organization_id,
            actor_id=actor_id,
            action="kri_created",
            entity_type="key_risk_indicator",
            entity_id=kri.id,
            details={"kri_code": kri.kri_code, "direction": kri.direction.value},
        )
        return kri

    @classmethod
    def create_threshold(
        cls,
        db: Session,
        organization_id: int,
        kri: KeyRiskIndicator,
        data: KriThresholdCreate,
        actor_id: int,
        is_initial: bool = False,
    ) -> KriThreshold:
        # Validate threshold parameters against KRI directionality
        if kri.direction == KriDirectionEnum.LOWER_IS_BETTER:
            if data.warning_threshold >= data.critical_threshold:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"For LOWER_IS_BETTER, warning_threshold ({data.warning_threshold}) must be strictly less than critical_threshold ({data.critical_threshold}).",
                )
        elif kri.direction == KriDirectionEnum.HIGHER_IS_BETTER:
            if data.critical_threshold >= data.warning_threshold:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"For HIGHER_IS_BETTER, critical_threshold ({data.critical_threshold}) must be strictly less than warning_threshold ({data.warning_threshold}).",
                )

        now_utc = datetime.now(timezone.utc)

        # Deactivate any previous active threshold
        previous_active = (
            db.query(KriThreshold)
            .filter(
                KriThreshold.organization_id == organization_id,
                KriThreshold.kri_id == kri.id,
                KriThreshold.is_active == True,  # noqa: E712
            )
            .all()
        )
        new_version = 1
        for prev in previous_active:
            prev.is_active = False
            prev.effective_to = now_utc
            if prev.version >= new_version:
                new_version = prev.version + 1

        threshold = KriThreshold(
            organization_id=organization_id,
            kri_id=kri.id,
            version=new_version,
            is_active=True,
            warning_threshold=data.warning_threshold,
            critical_threshold=data.critical_threshold,
            range_min_warning=data.range_min_warning,
            range_max_warning=data.range_max_warning,
            range_min_critical=data.range_min_critical,
            range_max_critical=data.range_max_critical,
            effective_from=now_utc,
            created_by_id=actor_id,
        )
        db.add(threshold)
        db.flush()

        if not is_initial:
            db.commit()
            db.refresh(threshold)
            cls._log_action(
                db=db,
                organization_id=organization_id,
                actor_id=actor_id,
                action="kri_threshold_activated",
                entity_type="kri_threshold",
                entity_id=threshold.id,
                details={"kri_code": kri.kri_code, "version": threshold.version},
            )
        return threshold

    @classmethod
    def get_kri(
        cls,
        db: Session,
        organization_id: int,
        kri_id: int,
    ) -> KeyRiskIndicator:
        kri = (
            db.query(KeyRiskIndicator)
            .filter(
                KeyRiskIndicator.id == kri_id,
                KeyRiskIndicator.organization_id == organization_id,
            )
            .first()
        )
        if not kri:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Key Risk Indicator not found.",
            )

        # Check for stale data telemetry
        if kri.status == KriStatusEnum.ACTIVE and kri.latest_observed_at is not None:
            if KriEvaluationService.check_is_stale(kri.frequency, kri.latest_observed_at):
                kri.status = KriStatusEnum.STALE_DATA
                db.commit()

        return kri

    @classmethod
    def list_kris(
        cls,
        db: Session,
        organization_id: int,
    ) -> List[KeyRiskIndicator]:
        kris = (
            db.query(KeyRiskIndicator)
            .filter(KeyRiskIndicator.organization_id == organization_id)
            .order_by(KeyRiskIndicator.kri_code.asc())
            .all()
        )
        # Check staleness on active KRIs
        needs_commit = False
        for k in kris:
            if k.status == KriStatusEnum.ACTIVE and k.latest_observed_at is not None:
                if KriEvaluationService.check_is_stale(k.frequency, k.latest_observed_at):
                    k.status = KriStatusEnum.STALE_DATA
                    needs_commit = True
        if needs_commit:
            db.commit()
        return kris

    @classmethod
    def update_kri(
        cls,
        db: Session,
        organization_id: int,
        kri_id: int,
        data: KeyRiskIndicatorUpdate,
        actor_id: int,
    ) -> KeyRiskIndicator:
        kri = cls.get_kri(db, organization_id, kri_id)

        if data.title is not None:
            kri.title = data.title
        if data.description is not None:
            kri.description = data.description
        if data.unit_of_measure is not None:
            kri.unit_of_measure = data.unit_of_measure.strip().upper()
        if data.frequency is not None:
            kri.frequency = data.frequency
        if data.owner_id is not None:
            kri.owner_id = data.owner_id
        if data.status is not None:
            kri.status = data.status

        kri.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(kri)

        cls._log_action(
            db=db,
            organization_id=organization_id,
            actor_id=actor_id,
            action="kri_updated",
            entity_type="key_risk_indicator",
            entity_id=kri.id,
            details={"kri_code": kri.kri_code},
        )
        return kri

    # ─────────────────────────────────────────────────────────────────────────
    # 3. KRI Observations & Ingestion
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def ingest_observation(
        cls,
        db: Session,
        organization_id: int,
        kri_id: int,
        data: KriObservationCreate,
        actor_id: Optional[int] = None,
    ) -> KriObservation:
        kri = cls.get_kri(db, organization_id, kri_id)

        # Reject ingestion if KRI is inactive
        if kri.status == KriStatusEnum.INACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"KRI '{kri.kri_code}' is currently INACTIVE. Ingestion rejected.",
            )

        # Unit of measure validation
        if data.unit.strip().upper() != kri.unit_of_measure.strip().upper():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unit mismatch: KRI requires '{kri.unit_of_measure}', but observation provided '{data.unit}'.",
            )

        # Future timestamp verification
        now_utc = datetime.now(timezone.utc)
        obs_utc = (
            data.observed_at
            if data.observed_at.tzinfo
            else data.observed_at.replace(tzinfo=timezone.utc)
        )
        if obs_utc > now_utc + timedelta(seconds=60):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Observation timestamp cannot be in the future beyond 60 seconds clock skew tolerance.",
            )

        # Idempotency check: Return existing record if already ingested with same key
        if data.idempotency_key:
            existing_obs = (
                db.query(KriObservation)
                .filter(
                    KriObservation.organization_id == organization_id,
                    KriObservation.kri_id == kri_id,
                    KriObservation.idempotency_key == data.idempotency_key,
                )
                .first()
            )
            if existing_obs:
                return existing_obs

        # Active threshold lookup
        active_threshold = (
            db.query(KriThreshold)
            .filter(
                KriThreshold.organization_id == organization_id,
                KriThreshold.kri_id == kri.id,
                KriThreshold.is_active == True,  # noqa: E712
            )
            .first()
        )
        if not active_threshold:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"KRI '{kri.kri_code}' has no active threshold configured. Please set a threshold before ingesting observations.",
            )

        # Compute tamper-evident SHA-256 digest
        digest = KriEvaluationService.compute_observation_digest(
            kri_id=kri.id,
            value=data.observed_value,
            unit=data.unit,
            observed_at=obs_utc,
            source_type=data.source_type.value,
            source_identifier=data.source_identifier,
        )

        observation = KriObservation(
            organization_id=organization_id,
            kri_id=kri.id,
            observed_value=data.observed_value,
            unit=data.unit.strip().upper(),
            observed_at=obs_utc,
            source_type=data.source_type,
            source_identifier=data.source_identifier,
            notes=data.notes,
            idempotency_key=data.idempotency_key,
            data_hash_sha256=digest,
            created_by_id=actor_id,
        )
        db.add(observation)
        db.flush()

        # Deterministic evaluation against active threshold
        eval_status = KriEvaluationService.evaluate_observation(
            direction=kri.direction,
            threshold=active_threshold,
            observed_value=data.observed_value,
        )

        # Update latest denormalized telemetry on KRI
        kri.latest_value = data.observed_value
        kri.latest_observed_at = obs_utc
        kri.latest_evaluation_status = eval_status
        kri.status = KriStatusEnum.ACTIVE  # Ingestion refreshes active status
        kri.updated_at = now_utc

        # Process breach lifecycle and anti-flapping hysteresis
        breach = KriEvaluationService.process_breach_lifecycle_and_hysteresis(
            db=db,
            kri=kri,
            threshold=active_threshold,
            observation=observation,
            eval_status=eval_status,
            actor_id=actor_id,
        )

        db.commit()
        db.refresh(observation)

        # Attach non-persistent evaluation annotations for API response
        observation.evaluation_status = eval_status
        observation.breach_id = breach.id if breach else None

        cls._log_action(
            db=db,
            organization_id=organization_id,
            actor_id=actor_id,
            action="kri_observation_ingested",
            entity_type="kri_observation",
            entity_id=observation.id,
            details={
                "kri_code": kri.kri_code,
                "value": observation.observed_value,
                "eval_status": eval_status.value,
            },
        )
        return observation

    @classmethod
    def list_observations(
        cls,
        db: Session,
        organization_id: int,
        kri_id: int,
        limit: int = 50,
    ) -> List[KriObservation]:
        cls.get_kri(db, organization_id, kri_id)
        return (
            db.query(KriObservation)
            .filter(
                KriObservation.organization_id == organization_id,
                KriObservation.kri_id == kri_id,
            )
            .order_by(KriObservation.observed_at.desc(), KriObservation.created_at.desc())
            .limit(limit)
            .all()
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 4. KRI Risk Linkages (Many-to-Many with Correlation Metadata)
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def link_risk(
        cls,
        db: Session,
        organization_id: int,
        kri_id: int,
        data: KriRiskLinkCreate,
        actor_id: int,
    ) -> KriRiskLink:
        kri = cls.get_kri(db, organization_id, kri_id)

        # Enforce tenant isolation on linked Risk (HTTP 404 on cross-tenant)
        risk = (
            db.query(Risk)
            .filter(
                Risk.id == data.risk_id,
                Risk.organization_id == organization_id,
            )
            .first()
        )
        if not risk:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Risk ID {data.risk_id} not found in this organization.",
            )

        # Prevent duplicate link
        existing = (
            db.query(KriRiskLink)
            .filter(
                KriRiskLink.organization_id == organization_id,
                KriRiskLink.kri_id == kri_id,
                KriRiskLink.risk_id == data.risk_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This KRI is already linked to the specified Risk.",
            )

        link = KriRiskLink(
            organization_id=organization_id,
            kri_id=kri.id,
            risk_id=risk.id,
            correlation_weight=data.correlation_weight,
            notes=data.notes,
            created_by_id=actor_id,
        )
        db.add(link)
        db.commit()
        db.refresh(link)

        cls._log_action(
            db=db,
            organization_id=organization_id,
            actor_id=actor_id,
            action="kri_risk_linked",
            entity_type="kri_risk_link",
            entity_id=link.id,
            details={
                "kri_code": kri.kri_code,
                "risk_id": risk.id,
                "correlation_weight": link.correlation_weight,
            },
        )
        return link

    @classmethod
    def unlink_risk(
        cls,
        db: Session,
        organization_id: int,
        kri_id: int,
        risk_id: int,
        actor_id: int,
    ) -> None:
        link = (
            db.query(KriRiskLink)
            .filter(
                KriRiskLink.organization_id == organization_id,
                KriRiskLink.kri_id == kri_id,
                KriRiskLink.risk_id == risk_id,
            )
            .first()
        )
        if not link:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Risk linkage not found.",
            )

        db.delete(link)
        db.commit()

        cls._log_action(
            db=db,
            organization_id=organization_id,
            actor_id=actor_id,
            action="kri_risk_unlinked",
            entity_type="kri_risk_link",
            entity_id=link.id,
            details={"kri_id": kri_id, "risk_id": risk_id},
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 5. KRI Breach Governance Lifecycle & Four-Eyes Signoff
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def list_breaches(
        cls,
        db: Session,
        organization_id: int,
        kri_id: Optional[int] = None,
        status_filter: Optional[BreachStatusEnum] = None,
    ) -> List[KriBreachRecord]:
        query = db.query(KriBreachRecord).filter(
            KriBreachRecord.organization_id == organization_id
        )
        if kri_id is not None:
            query = query.filter(KriBreachRecord.kri_id == kri_id)
        if status_filter is not None:
            query = query.filter(KriBreachRecord.status == status_filter)
        return query.order_by(KriBreachRecord.detected_at.desc()).all()

    @classmethod
    def get_breach(
        cls,
        db: Session,
        organization_id: int,
        breach_id: int,
    ) -> KriBreachRecord:
        breach = (
            db.query(KriBreachRecord)
            .filter(
                KriBreachRecord.id == breach_id,
                KriBreachRecord.organization_id == organization_id,
            )
            .first()
        )
        if not breach:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="KRI breach record not found.",
            )
        return breach

    @classmethod
    def acknowledge_breach(
        cls,
        db: Session,
        organization_id: int,
        breach_id: int,
        data: KriBreachAcknowledgeRequest,
        actor_id: int,
    ) -> KriBreachRecord:
        breach = cls.get_breach(db, organization_id, breach_id)

        # State transition validation: must be DETECTED
        if breach.status != BreachStatusEnum.DETECTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot acknowledge breach currently in '{breach.status.value}' state. Must be DETECTED.",
            )

        now_utc = datetime.now(timezone.utc)
        breach.status = BreachStatusEnum.ACKNOWLEDGED
        breach.acknowledged_at = now_utc
        breach.acknowledged_by_id = actor_id
        breach.last_evaluated_at = now_utc

        db.commit()
        db.refresh(breach)

        cls._log_action(
            db=db,
            organization_id=organization_id,
            actor_id=actor_id,
            action="kri_breach_acknowledged",
            entity_type="kri_breach_record",
            entity_id=breach.id,
            details={"breach_code": breach.breach_code},
        )
        return breach

    @classmethod
    def escalate_breach_to_finding(
        cls,
        db: Session,
        organization_id: int,
        breach_id: int,
        data: KriBreachEscalateFindingRequest,
        actor_id: int,
    ) -> KriBreachRecord:
        breach = cls.get_breach(db, organization_id, breach_id)

        # Check for duplicate escalation
        if breach.escalated_finding_id is not None or breach.status == BreachStatusEnum.ESCALATED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Breach has already been escalated to an authoritative Finding.",
            )

        # State validation: can escalate from DETECTED, ACKNOWLEDGED, or RECOVERED
        if breach.status == BreachStatusEnum.CLOSED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot escalate an already CLOSED breach.",
            )

        # Verify authoritative control gap exists in this tenant
        control = (
            db.query(OrganizationControl)
            .filter(
                OrganizationControl.id == data.organization_control_id,
                OrganizationControl.organization_id == organization_id,
            )
            .first()
        )
        if not control:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Organization control ID {data.organization_control_id} not found in this organization.",
            )

        severity_val = getattr(
            FindingSeverityEnum,
            (data.severity or "HIGH").upper(),
            FindingSeverityEnum.HIGH,
        )

        # Create authoritative Phase 4 Finding (zero duplicate finding tables)
        finding = Finding(
            organization_id=organization_id,
            organization_control_id=control.id,
            title=data.title or f"KRI Tolerance Breach: {breach.breach_code}",
            description=data.description
            or f"Automated deficiency finding escalated from KRI breach {breach.breach_code} (Peak observed: {breach.peak_value}).",
            finding_type=FindingTypeEnum.CONTROL_GAP,
            severity=severity_val,
            impact=4,
            likelihood=4,
            risk_score=16,
            recommendation=data.recommendation if hasattr(data, "recommendation") and data.recommendation else "Remediate control gap and restore KRI operating threshold.",
        )
        db.add(finding)
        db.flush()

        now_utc = datetime.now(timezone.utc)
        breach.status = BreachStatusEnum.ESCALATED
        breach.escalated_at = now_utc
        breach.escalated_finding_id = finding.id
        breach.last_evaluated_at = now_utc

        db.commit()
        db.refresh(breach)

        cls._log_action(
            db=db,
            organization_id=organization_id,
            actor_id=actor_id,
            action="kri_breach_escalated_to_finding",
            entity_type="kri_breach_record",
            entity_id=breach.id,
            details={"breach_code": breach.breach_code, "finding_id": finding.id},
        )
        return breach

    @classmethod
    def close_breach(
        cls,
        db: Session,
        organization_id: int,
        breach_id: int,
        data: KriBreachCloseRequest,
        actor_id: int,
    ) -> KriBreachRecord:
        breach = cls.get_breach(db, organization_id, breach_id)
        kri = cls.get_kri(db, organization_id, breach.kri_id)

        # Prevent closing already closed breaches
        if breach.status == BreachStatusEnum.CLOSED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Breach is already CLOSED.",
            )

        # Illegal state transition: Cannot close a freshly DETECTED breach directly without review
        if breach.status == BreachStatusEnum.DETECTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Illegal transition: Cannot close a freshly DETECTED breach without acknowledgement or recovery.",
            )

        # Four-Eyes Check 1: Breach closer cannot be the acknowledging analyst
        if breach.acknowledged_by_id is not None and breach.acknowledged_by_id == actor_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Four-Eyes Violation: Breach closer must be distinct from acknowledging analyst.",
            )

        # Four-Eyes Check 2: KRI owner cannot self-close breaches for their own metric
        if kri.owner_id is not None and kri.owner_id == actor_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Four-Eyes Violation: KRI owner cannot self-close breaches for their own metric.",
            )

        now_utc = datetime.now(timezone.utc)
        breach.status = BreachStatusEnum.CLOSED
        breach.closed_at = now_utc
        breach.closed_by_id = actor_id
        breach.closure_notes = data.closure_notes.strip()
        breach.last_evaluated_at = now_utc

        db.commit()
        db.refresh(breach)

        cls._log_action(
            db=db,
            organization_id=organization_id,
            actor_id=actor_id,
            action="kri_breach_closed",
            entity_type="kri_breach_record",
            entity_id=breach.id,
            details={"breach_code": breach.breach_code, "closure_notes": breach.closure_notes},
        )
        return breach

    # ─────────────────────────────────────────────────────────────────────────
    # 6. Executive & Telemetry Aggregates
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def get_telemetry_overview(
        cls,
        db: Session,
        organization_id: int,
    ):
        kris = cls.list_kris(db, organization_id)
        total_kris = len(kris)

        normal_kris = sum(1 for k in kris if k.latest_evaluation_status == KriEvaluationStatusEnum.NORMAL)
        warning_kris = sum(1 for k in kris if k.latest_evaluation_status == KriEvaluationStatusEnum.WARNING)
        critical_kris = sum(1 for k in kris if k.latest_evaluation_status == KriEvaluationStatusEnum.CRITICAL)
        stale_kris = sum(1 for k in kris if k.status == KriStatusEnum.STALE_DATA)

        active_breaches = (
            db.query(KriBreachRecord)
            .filter(
                KriBreachRecord.organization_id == organization_id,
                KriBreachRecord.status.in_(
                    [
                        BreachStatusEnum.DETECTED,
                        BreachStatusEnum.ACKNOWLEDGED,
                        BreachStatusEnum.ESCALATED,
                    ]
                ),
            )
            .count()
        )

        total_risks = db.query(Risk).filter(Risk.organization_id == organization_id).count()
        within_appetite_risks = (
            db.query(Risk)
            .filter(
                Risk.organization_id == organization_id,
                Risk.appetite_status == "WITHIN_APPETITE",
            )
            .count()
        )

        compliance_rate = (
            round((within_appetite_risks / total_risks) * 100.0, 2)
            if total_risks > 0
            else 100.0
        )

        return {
            "total_kris": total_kris,
            "normal_kris": normal_kris,
            "warning_kris": warning_kris,
            "critical_kris": critical_kris,
            "stale_kris": stale_kris,
            "active_breaches": active_breaches,
            "appetite_compliance_rate": compliance_rate,
        }
