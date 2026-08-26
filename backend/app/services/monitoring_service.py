from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session, joinedload

from app.models.control import ImplementationStatusEnum, OrganizationControl
from app.models.evidence import EvidenceItem, EvidenceStatusEnum
from app.models.exception import ExceptionStatusEnum, SecurityException
from app.models.finding import Finding, FindingSeverityEnum, FindingStatusEnum
from app.models.framework import FrameworkSubcategory, FrameworkCategory, FrameworkFunction
from app.models.monitoring import (
    ComplianceDriftAlert,
    ControlHealthSnapshot,
    ControlHealthStatusEnum,
    DriftAlertSeverityEnum,
    DriftAlertStatusEnum,
    DriftAlertTypeEnum,
    EvaluationTriggerEnum,
    MonitoringSchedule,
)
from app.schemas.monitoring import (
    ComplianceDriftAlertDismiss,
    ComplianceDriftAlertResolve,
    ControlHealthSummaryResponse,
    EvaluationRunResponse,
    MonitoringConfigUpdate,
    MonitoringOverviewResponse,
)
from app.services.control_service import ControlService


def _to_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class MonitoringService:

    # ─────────────────────────────────────────────────────────────────────────
    # CONFIGURATION
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def get_or_create_config(db: Session, organization_id: int) -> MonitoringSchedule:
        cfg = (
            db.query(MonitoringSchedule)
            .filter(MonitoringSchedule.organization_id == organization_id)
            .first()
        )
        if not cfg:
            cfg = MonitoringSchedule(
                organization_id=organization_id,
                frequency_hours=24,
                is_enabled=True,
                evidence_max_age_days=90,
                assessment_max_age_days=180,
                exception_warning_window_days=14,
                finding_sla_critical_days=15,
                finding_sla_high_days=30,
            )
            db.add(cfg)
            db.commit()
            db.refresh(cfg)
        return cfg

    @staticmethod
    def update_config(
        db: Session, organization_id: int, obj_in: MonitoringConfigUpdate
    ) -> MonitoringSchedule:
        cfg = MonitoringService.get_or_create_config(db, organization_id)
        data = obj_in.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(cfg, k, v)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
        return cfg

    # ─────────────────────────────────────────────────────────────────────────
    # CORE EVALUATION ENGINE
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def evaluate_organization(
        db: Session,
        organization_id: int,
        trigger: EvaluationTriggerEnum = EvaluationTriggerEnum.MANUAL,
    ) -> EvaluationRunResponse:
        config = MonitoringService.get_or_create_config(db, organization_id)
        now = datetime.now(timezone.utc)

        # Ensure controls exist for organization
        ControlService.ensure_org_controls(db=db, organization_id=organization_id)
        controls = (
            db.query(OrganizationControl)
            .filter(OrganizationControl.organization_id == organization_id)
            .all()
        )

        evaluated_count = len(controls)
        total_score = 0.0
        alerts_generated = 0
        alerts_resolved = 0

        for ctrl in controls:
            snapshot, generated, resolved = MonitoringService._evaluate_single_control(
                db=db,
                organization_id=organization_id,
                control=ctrl,
                config=config,
                trigger=trigger,
                eval_time=now,
            )
            total_score += snapshot.health_score
            alerts_generated += generated
            alerts_resolved += resolved

        avg_score = round(total_score / evaluated_count, 2) if evaluated_count > 0 else 100.0

        config.last_run_at = now
        config.last_run_status = "SUCCESS"
        db.add(config)
        db.commit()

        return EvaluationRunResponse(
            evaluated_controls_count=evaluated_count,
            alerts_generated_count=alerts_generated,
            alerts_auto_resolved_count=alerts_resolved,
            average_health_score=avg_score,
            evaluated_at=now,
        )

    @staticmethod
    def _evaluate_single_control(
        db: Session,
        organization_id: int,
        control: OrganizationControl,
        config: MonitoringSchedule,
        trigger: EvaluationTriggerEnum,
        eval_time: datetime,
    ) -> Tuple[ControlHealthSnapshot, int, int]:
        now = _to_utc(eval_time) or datetime.now(timezone.utc)
        today = now.date()

        # 1. Evidence Freshness
        accepted_evidence = (
            db.query(EvidenceItem)
            .filter(
                EvidenceItem.organization_control_id == control.id,
                EvidenceItem.organization_id == organization_id,
                EvidenceItem.status == EvidenceStatusEnum.ACCEPTED,
            )
            .order_by(EvidenceItem.created_at.desc())
            .all()
        )
        accepted_count = len(accepted_evidence)

        days_since_evidence: Optional[int] = None
        evidence_freshness_score = 0.0

        if accepted_count > 0:
            latest_ev = accepted_evidence[0]
            ev_time = _to_utc(latest_ev.created_at)
            delta = (now - ev_time).days if ev_time else 0
            days_since_evidence = max(0, delta)
            if days_since_evidence <= config.evidence_max_age_days:
                evidence_freshness_score = 100.0
            else:
                # Linear decay over 2x max age
                decay_window = config.evidence_max_age_days
                overage = days_since_evidence - config.evidence_max_age_days
                decay_ratio = max(0.0, 1.0 - (overage / decay_window))
                evidence_freshness_score = round(decay_ratio * 100.0, 1)

        # 2. Assessment Currency
        assessment_currency_score = 0.0
        days_since_assessment: Optional[int] = None

        if control.status == ImplementationStatusEnum.IMPLEMENTED:
            assessment_currency_score = 100.0
            if control.updated_at:
                ctrl_time = _to_utc(control.updated_at)
                days_since_assessment = max(0, (now - ctrl_time).days) if ctrl_time else 0
                if days_since_assessment > config.assessment_max_age_days:
                    assessment_currency_score = 60.0
        elif control.status == ImplementationStatusEnum.PARTIALLY_IMPLEMENTED:
            assessment_currency_score = 50.0
        elif control.status in [ImplementationStatusEnum.IN_PROGRESS, ImplementationStatusEnum.NEEDS_REVIEW]:
            assessment_currency_score = 25.0
        else:
            assessment_currency_score = 0.0

        # 3. Active Findings & SLA Penalties
        open_findings = (
            db.query(Finding)
            .filter(
                Finding.organization_control_id == control.id,
                Finding.organization_id == organization_id,
                Finding.status.notin_([
                    FindingStatusEnum.RESOLVED,
                    FindingStatusEnum.CLOSED,
                    FindingStatusEnum.ACCEPTED_RISK,
                ]),
            )
            .all()
        )
        active_findings_count = len(open_findings)
        critical_high_count = 0
        finding_penalty = 0.0

        for f in open_findings:
            f_time = _to_utc(f.created_at)
            f_age_days = (now - f_time).days if f_time else 0
            if f.severity == FindingSeverityEnum.CRITICAL:
                critical_high_count += 1
                finding_penalty += 20.0
                if f_age_days > config.finding_sla_critical_days:
                    finding_penalty += 10.0  # SLA breach penalty
            elif f.severity == FindingSeverityEnum.HIGH:
                critical_high_count += 1
                finding_penalty += 10.0
                if f_age_days > config.finding_sla_high_days:
                    finding_penalty += 5.0
            elif f.severity == FindingSeverityEnum.MEDIUM:
                finding_penalty += 4.0
            else:
                finding_penalty += 1.0

        # 4. Active Exceptions
        active_exceptions = (
            db.query(SecurityException)
            .filter(
                SecurityException.linked_organization_control_id == control.id,
                SecurityException.organization_id == organization_id,
                SecurityException.status.in_([
                    ExceptionStatusEnum.APPROVED,
                    ExceptionStatusEnum.ACTIVE,
                ]),
            )
            .all()
        )
        active_exceptions_count = len(active_exceptions)
        exception_penalty = 0.0

        for exc in active_exceptions:
            if exc.expiry_date and exc.expiry_date < today:
                exception_penalty += 15.0  # Expired active exception
            else:
                exception_penalty += 5.0

        # 5. Calculate Deterministic Health Score
        raw_score = (
            (evidence_freshness_score * 0.35)
            + (assessment_currency_score * 0.25)
            + (40.0 - min(40.0, finding_penalty + exception_penalty))
        )
        health_score = round(max(0.0, min(100.0, raw_score)), 1)

        if health_score >= 80.0:
            health_status = ControlHealthStatusEnum.HEALTHY
        elif health_score >= 60.0:
            health_status = ControlHealthStatusEnum.DEGRADED
        elif health_score >= 40.0:
            health_status = ControlHealthStatusEnum.AT_RISK
        else:
            health_status = ControlHealthStatusEnum.FAILING

        # 6. Save Snapshot
        snapshot = ControlHealthSnapshot(
            organization_id=organization_id,
            organization_control_id=control.id,
            health_score=health_score,
            health_status=health_status,
            evidence_freshness_score=evidence_freshness_score,
            assessment_currency_score=assessment_currency_score,
            finding_penalty_score=round(finding_penalty, 1),
            exception_penalty_score=round(exception_penalty, 1),
            active_findings_count=active_findings_count,
            critical_high_findings_count=critical_high_count,
            active_exceptions_count=active_exceptions_count,
            accepted_evidence_count=accepted_count,
            days_since_last_evidence=days_since_evidence,
            days_since_last_assessment=days_since_assessment,
            evaluated_at=now,
            evaluation_trigger=trigger,
        )
        db.add(snapshot)

        # 7. Evaluate and generate compliance drift alerts
        generated, resolved = MonitoringService._sync_drift_alerts(
            db=db,
            organization_id=organization_id,
            control=control,
            config=config,
            health_status=health_status,
            days_since_evidence=days_since_evidence,
            days_since_assessment=days_since_assessment,
            open_findings=open_findings,
            active_exceptions=active_exceptions,
            today=today,
            now=now,
        )

        db.commit()
        db.refresh(snapshot)
        return snapshot, generated, resolved

    # ─────────────────────────────────────────────────────────────────────────
    # DRIFT ALERTS LOGIC
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _sync_drift_alerts(
        db: Session,
        organization_id: int,
        control: OrganizationControl,
        config: MonitoringSchedule,
        health_status: ControlHealthStatusEnum,
        days_since_evidence: Optional[int],
        days_since_assessment: Optional[int],
        open_findings: List[Finding],
        active_exceptions: List[SecurityException],
        today: date,
        now: datetime,
    ) -> Tuple[int, int]:
        generated = 0
        resolved = 0

        # Helper to create alert if not already active
        def create_drift_alert(
            alert_type: DriftAlertTypeEnum,
            severity: DriftAlertSeverityEnum,
            title: str,
            description: str,
            remediation: str,
        ):
            nonlocal generated
            existing = (
                db.query(ComplianceDriftAlert)
                .filter(
                    ComplianceDriftAlert.organization_id == organization_id,
                    ComplianceDriftAlert.organization_control_id == control.id,
                    ComplianceDriftAlert.alert_type == alert_type,
                    ComplianceDriftAlert.status.in_([
                        DriftAlertStatusEnum.ACTIVE,
                        DriftAlertStatusEnum.ACKNOWLEDGED,
                    ]),
                )
                .first()
            )
            if not existing:
                alert = ComplianceDriftAlert(
                    organization_id=organization_id,
                    organization_control_id=control.id,
                    alert_type=alert_type,
                    severity=severity,
                    status=DriftAlertStatusEnum.ACTIVE,
                    title=title,
                    description=description,
                    remediation_guidance=remediation,
                    created_at=now,
                    updated_at=now,
                )
                db.add(alert)
                generated += 1

        # Check A: Evidence Missing or Expired
        if days_since_evidence is None:
            create_drift_alert(
                alert_type=DriftAlertTypeEnum.EVIDENCE_MISSING,
                severity=DriftAlertSeverityEnum.HIGH,
                title=f"Control #{control.id} lacks accepted evidence",
                description="No verified evidence items have been submitted or accepted for this control.",
                remediation="Upload and review relevant policy or implementation artifacts in the Evidence Repository.",
            )
        elif days_since_evidence > config.evidence_max_age_days:
            create_drift_alert(
                alert_type=DriftAlertTypeEnum.EVIDENCE_EXPIRED,
                severity=DriftAlertSeverityEnum.MEDIUM,
                title=f"Evidence for Control #{control.id} is stale ({days_since_evidence}d old)",
                description=f"Accepted evidence exceeds the maximum age threshold of {config.evidence_max_age_days} days.",
                remediation="Request updated evidence from control owner and conduct recertification review.",
            )

        # Check B: Critical Finding SLA Breach
        for f in open_findings:
            f_time = _to_utc(f.created_at)
            f_age = (now - f_time).days if f_time else 0
            if f.severity == FindingSeverityEnum.CRITICAL and f_age > config.finding_sla_critical_days:
                create_drift_alert(
                    alert_type=DriftAlertTypeEnum.CRITICAL_FINDING_SLA_BREACH,
                    severity=DriftAlertSeverityEnum.CRITICAL,
                    title=f"Critical Finding #{f.id} breached SLA ({f_age}d / {config.finding_sla_critical_days}d max)",
                    description=f"Critical finding '{f.title}' has exceeded organization remediation SLA.",
                    remediation="Escalate to security leadership for emergency remediation or risk exception filing.",
                )

        # Check C: Exception Expiring Soon or Expired
        for exc in active_exceptions:
            if exc.expiry_date:
                days_to_expiry = (exc.expiry_date - today).days
                if days_to_expiry < 0:
                    create_drift_alert(
                        alert_type=DriftAlertTypeEnum.EXCEPTION_EXPIRED,
                        severity=DriftAlertSeverityEnum.HIGH,
                        title=f"Security Exception #{exc.id} has expired",
                        description=f"Exception '{exc.title}' expired on {exc.expiry_date} but control deviation remains active.",
                        remediation="Review control compliance immediately or submit a formal exception renewal request.",
                    )
                elif days_to_expiry <= config.exception_warning_window_days:
                    create_drift_alert(
                        alert_type=DriftAlertTypeEnum.EXCEPTION_EXPIRING_SOON,
                        severity=DriftAlertSeverityEnum.MEDIUM,
                        title=f"Security Exception #{exc.id} expiring in {days_to_expiry} days",
                        description=f"Exception '{exc.title}' is nearing its expiration date ({exc.expiry_date}).",
                        remediation="Plan control remediation completion or initiate renewal review.",
                    )

        # Check D: Control Degraded Status
        if health_status in [ControlHealthStatusEnum.AT_RISK, ControlHealthStatusEnum.FAILING]:
            create_drift_alert(
                alert_type=DriftAlertTypeEnum.CONTROL_DEGRADED,
                severity=DriftAlertSeverityEnum.HIGH if health_status == ControlHealthStatusEnum.AT_RISK else DriftAlertSeverityEnum.CRITICAL,
                title=f"Control #{control.id} health degraded to {health_status.value}",
                description="Cumulative findings, stale evidence, or expired exceptions have dropped control health below acceptable threshold.",
                remediation="Inspect control telemetry breakdown and prioritize remediation actions.",
            )

        return generated, resolved

    # ─────────────────────────────────────────────────────────────────────────
    # OVERVIEW & REPORTING
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def get_overview(db: Session, organization_id: int) -> MonitoringOverviewResponse:
        ControlService.ensure_org_controls(db=db, organization_id=organization_id)
        controls = (
            db.query(OrganizationControl)
            .filter(OrganizationControl.organization_id == organization_id)
            .all()
        )
        total_controls = len(controls)
        control_ids = [c.id for c in controls]

        # Get latest snapshot for each control
        latest_snapshots: List[ControlHealthSnapshot] = []
        for cid in control_ids:
            s = (
                db.query(ControlHealthSnapshot)
                .filter(
                    ControlHealthSnapshot.organization_id == organization_id,
                    ControlHealthSnapshot.organization_control_id == cid,
                )
                .order_by(ControlHealthSnapshot.evaluated_at.desc())
                .first()
            )
            if s:
                latest_snapshots.append(s)

        healthy = sum(1 for s in latest_snapshots if s.health_status == ControlHealthStatusEnum.HEALTHY)
        degraded = sum(1 for s in latest_snapshots if s.health_status == ControlHealthStatusEnum.DEGRADED)
        at_risk = sum(1 for s in latest_snapshots if s.health_status == ControlHealthStatusEnum.AT_RISK)
        failing = sum(1 for s in latest_snapshots if s.health_status == ControlHealthStatusEnum.FAILING)

        avg_score = (
            round(sum(s.health_score for s in latest_snapshots) / len(latest_snapshots), 1)
            if latest_snapshots
            else 100.0
        )

        if avg_score >= 80.0:
            overall_status = ControlHealthStatusEnum.HEALTHY
        elif avg_score >= 60.0:
            overall_status = ControlHealthStatusEnum.DEGRADED
        elif avg_score >= 40.0:
            overall_status = ControlHealthStatusEnum.AT_RISK
        else:
            overall_status = ControlHealthStatusEnum.FAILING

        # Alerts count
        active_alerts = (
            db.query(ComplianceDriftAlert)
            .filter(
                ComplianceDriftAlert.organization_id == organization_id,
                ComplianceDriftAlert.status.in_([
                    DriftAlertStatusEnum.ACTIVE,
                    DriftAlertStatusEnum.ACKNOWLEDGED,
                ]),
            )
            .all()
        )
        crit_alerts = sum(1 for a in active_alerts if a.severity == DriftAlertSeverityEnum.CRITICAL)
        high_alerts = sum(1 for a in active_alerts if a.severity == DriftAlertSeverityEnum.HIGH)
        med_alerts = sum(1 for a in active_alerts if a.severity == DriftAlertSeverityEnum.MEDIUM)
        low_alerts = sum(1 for a in active_alerts if a.severity == DriftAlertSeverityEnum.LOW or a.severity == DriftAlertSeverityEnum.INFO)

        freshness_agg = (
            round(sum(s.evidence_freshness_score for s in latest_snapshots) / len(latest_snapshots), 1)
            if latest_snapshots
            else 100.0
        )
        currency_agg = (
            round(sum(s.assessment_currency_score for s in latest_snapshots) / len(latest_snapshots), 1)
            if latest_snapshots
            else 100.0
        )

        last_run = (
            latest_snapshots[0].evaluated_at if latest_snapshots else None
        )

        return MonitoringOverviewResponse(
            average_health_score=avg_score,
            overall_health_status=overall_status,
            total_monitored_controls=total_controls,
            healthy_controls_count=healthy,
            degraded_controls_count=degraded,
            at_risk_controls_count=at_risk,
            failing_controls_count=failing,
            active_drift_alerts_count=len(active_alerts),
            critical_drift_alerts_count=crit_alerts,
            high_drift_alerts_count=high_alerts,
            medium_drift_alerts_count=med_alerts,
            low_drift_alerts_count=low_alerts,
            evidence_freshness_aggregate_pct=freshness_agg,
            controls_assessed_currency_pct=currency_agg,
            last_evaluation_run=last_run,
        )

    @staticmethod
    def list_control_health(
        db: Session,
        organization_id: int,
        status: Optional[ControlHealthStatusEnum] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ControlHealthSummaryResponse]:
        ControlService.ensure_org_controls(db=db, organization_id=organization_id)
        controls = (
            db.query(OrganizationControl)
            .filter(OrganizationControl.organization_id == organization_id)
            .options(
                joinedload(OrganizationControl.subcategory).joinedload(FrameworkSubcategory.category).joinedload(FrameworkCategory.function)
            )
            .all()
        )

        results: List[ControlHealthSummaryResponse] = []
        for ctrl in controls:
            latest = (
                db.query(ControlHealthSnapshot)
                .filter(
                    ControlHealthSnapshot.organization_id == organization_id,
                    ControlHealthSnapshot.organization_control_id == ctrl.id,
                )
                .order_by(ControlHealthSnapshot.evaluated_at.desc())
                .first()
            )

            alerts_count = (
                db.query(ComplianceDriftAlert)
                .filter(
                    ComplianceDriftAlert.organization_id == organization_id,
                    ComplianceDriftAlert.organization_control_id == ctrl.id,
                    ComplianceDriftAlert.status.in_([
                        DriftAlertStatusEnum.ACTIVE,
                        DriftAlertStatusEnum.ACKNOWLEDGED,
                    ]),
                )
                .count()
            )

            subcat = ctrl.subcategory
            cat = subcat.category if subcat else None
            fn = cat.function if cat else None
            code = subcat.identifier if subcat else f"CTRL-{ctrl.id}"
            title = subcat.title if subcat else f"Control #{ctrl.id}"

            h_status = latest.health_status if latest else ControlHealthStatusEnum.HEALTHY
            if status and h_status != status:
                continue

            if search:
                s_lower = search.lower()
                if s_lower not in code.lower() and s_lower not in title.lower():
                    continue

            results.append(
                ControlHealthSummaryResponse(
                    organization_control_id=ctrl.id,
                    control_code=code,
                    control_title=title,
                    category_code=cat.identifier if cat else None,
                    function_code=fn.identifier if fn else None,
                    implementation_status=ctrl.status.value,
                    health_score=latest.health_score if latest else 100.0,
                    health_status=h_status,
                    evidence_freshness_score=latest.evidence_freshness_score if latest else 100.0,
                    assessment_currency_score=latest.assessment_currency_score if latest else 100.0,
                    finding_penalty_score=latest.finding_penalty_score if latest else 0.0,
                    exception_penalty_score=latest.exception_penalty_score if latest else 0.0,
                    active_findings_count=latest.active_findings_count if latest else 0,
                    critical_high_findings_count=latest.critical_high_findings_count if latest else 0,
                    active_exceptions_count=latest.active_exceptions_count if latest else 0,
                    accepted_evidence_count=latest.accepted_evidence_count if latest else 0,
                    days_since_last_evidence=latest.days_since_last_evidence if latest else None,
                    days_since_last_assessment=latest.days_since_last_assessment if latest else None,
                    last_evaluated_at=latest.evaluated_at if latest else None,
                    active_drift_alerts_count=alerts_count,
                )
            )

        # Sort by health_score asc (worst health first)
        results.sort(key=lambda x: x.health_score)
        return results[skip : skip + limit]

    @staticmethod
    def get_control_history(
        db: Session, organization_id: int, control_id: int, limit: int = 30
    ) -> List[ControlHealthSnapshot]:
        # Validate control belongs to tenant
        ctrl = (
            db.query(OrganizationControl)
            .filter(
                OrganizationControl.id == control_id,
                OrganizationControl.organization_id == organization_id,
            )
            .first()
        )
        if not ctrl:
            raise ValueError("Control not found in your organization.")

        return (
            db.query(ControlHealthSnapshot)
            .filter(
                ControlHealthSnapshot.organization_id == organization_id,
                ControlHealthSnapshot.organization_control_id == control_id,
            )
            .order_by(ControlHealthSnapshot.evaluated_at.desc())
            .limit(limit)
            .all()
        )

    # ─────────────────────────────────────────────────────────────────────────
    # ALERTS MANAGEMENT
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def list_alerts(
        db: Session,
        organization_id: int,
        status: Optional[DriftAlertStatusEnum] = None,
        severity: Optional[DriftAlertSeverityEnum] = None,
        alert_type: Optional[DriftAlertTypeEnum] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ComplianceDriftAlert]:
        q = (
            db.query(ComplianceDriftAlert)
            .filter(ComplianceDriftAlert.organization_id == organization_id)
            .options(
                joinedload(ComplianceDriftAlert.organization_control),
                joinedload(ComplianceDriftAlert.acknowledged_by),
                joinedload(ComplianceDriftAlert.resolved_by),
            )
        )
        if status:
            q = q.filter(ComplianceDriftAlert.status == status)
        if severity:
            q = q.filter(ComplianceDriftAlert.severity == severity)
        if alert_type:
            q = q.filter(ComplianceDriftAlert.alert_type == alert_type)

        return q.order_by(ComplianceDriftAlert.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def acknowledge_alert(
        db: Session, organization_id: int, alert_id: int, user_id: int
    ) -> ComplianceDriftAlert:
        alert = (
            db.query(ComplianceDriftAlert)
            .filter(
                ComplianceDriftAlert.id == alert_id,
                ComplianceDriftAlert.organization_id == organization_id,
            )
            .first()
        )
        if not alert:
            raise ValueError("Alert not found in your organization.")
        if alert.status in [DriftAlertStatusEnum.RESOLVED, DriftAlertStatusEnum.DISMISSED]:
            raise ValueError(f"Cannot acknowledge a {alert.status.value} alert.")

        alert.status = DriftAlertStatusEnum.ACKNOWLEDGED
        alert.acknowledged_by_id = user_id
        alert.acknowledged_at = datetime.now(timezone.utc)
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return alert

    @staticmethod
    def resolve_alert(
        db: Session,
        organization_id: int,
        alert_id: int,
        user_id: int,
        obj_in: ComplianceDriftAlertResolve,
    ) -> ComplianceDriftAlert:
        alert = (
            db.query(ComplianceDriftAlert)
            .filter(
                ComplianceDriftAlert.id == alert_id,
                ComplianceDriftAlert.organization_id == organization_id,
            )
            .first()
        )
        if not alert:
            raise ValueError("Alert not found in your organization.")
        if alert.status == DriftAlertStatusEnum.RESOLVED:
            raise ValueError("Alert is already resolved.")

        alert.status = DriftAlertStatusEnum.RESOLVED
        alert.resolved_by_id = user_id
        alert.resolved_at = datetime.now(timezone.utc)
        alert.resolution_notes = obj_in.resolution_notes.strip()
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return alert

    @staticmethod
    def dismiss_alert(
        db: Session,
        organization_id: int,
        alert_id: int,
        user_id: int,
        obj_in: ComplianceDriftAlertDismiss,
    ) -> ComplianceDriftAlert:
        alert = (
            db.query(ComplianceDriftAlert)
            .filter(
                ComplianceDriftAlert.id == alert_id,
                ComplianceDriftAlert.organization_id == organization_id,
            )
            .first()
        )
        if not alert:
            raise ValueError("Alert not found in your organization.")
        if alert.status in [DriftAlertStatusEnum.RESOLVED, DriftAlertStatusEnum.DISMISSED]:
            raise ValueError(f"Cannot dismiss an alert with status {alert.status.value}.")

        alert.status = DriftAlertStatusEnum.DISMISSED
        alert.resolved_by_id = user_id
        alert.resolved_at = datetime.now(timezone.utc)
        alert.resolution_notes = f"Dismissed: {obj_in.justification.strip()}"
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return alert
