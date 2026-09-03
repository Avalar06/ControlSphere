import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.continuous_compliance import (
    ContinuousComplianceProfile,
    ComplianceDriftRecord,
    ContinuousAssuranceSnapshot,
    ComplianceDriftVectorEnum,
    ComplianceDriftSeverityEnum,
    ComplianceDriftStatusEnum,
)
from app.models.control import OrganizationControl
from app.models.monitoring import ControlHealthSnapshot, ComplianceDriftAlert
from app.models.evidence import EvidenceItem, EvidenceStatusEnum
from app.models.integration import EvidenceCollectionRun, CollectionRunStatusEnum
from app.models.regulatory import (
    RegulatoryObligation,
    RegulatoryChangeEvent,
    RegulatoryChangeStatusEnum,
    RegulatoryChangeSeverityEnum,
    RegulatoryComplianceStatusEnum,
)
from app.models.finding import Finding, FindingStatusEnum
from app.models.remediation import (
    RemediationPlan,
    RemediationSourceTypeEnum,
    RemediationRootCauseClassificationEnum,
    RemediationSeverityEnum,
    RemediationStatusEnum,
)
from app.models.cloudsec import CloudSecurityFinding
from app.models.identity_governance import SoDConflictViolation
from app.models.harmonization import RationalizedCommonControl
from app.models.user import User
from app.schemas.continuous_compliance import (
    ContinuousComplianceProfileUpdate,
    ContinuousAssuranceSnapshotCreate,
)
from app.services.audit_service import AuditService


class ContinuousComplianceService:
    """Higher-order assurance orchestrator calculating authoritative enterprise continuous compliance and multi-vector drift."""

    CALCULATION_VERSION = "1.0"

    @staticmethod
    def _audit_log(
        db: Session,
        organization_id: int,
        action: str,
        resource_type: str,
        actor_id: Optional[int] = None,
        resource_id: Optional[int] = None,
        details: Optional[Dict] = None,
    ) -> None:
        user = db.query(User).filter(User.id == actor_id).first() if actor_id else None
        actor_email = user.email if user else "system@controlsphere.internal"
        AuditService.log(
            db=db,
            organization_id=organization_id,
            action=action,
            resource_type=resource_type,
            actor_email=actor_email,
            actor_id=actor_id,
            resource_id=str(resource_id) if resource_id is not None else None,
            details=details or {},
        )

    # ── Profiles ────────────────────────────────────────────────────────────

    @staticmethod
    def get_or_create_profile(
        db: Session,
        organization_id: int,
        current_user_id: Optional[int] = None,
    ) -> ContinuousComplianceProfile:
        profile = db.query(ContinuousComplianceProfile).filter(
            ContinuousComplianceProfile.organization_id == organization_id
        ).first()

        if not profile:
            profile = ContinuousComplianceProfile(
                organization_id=organization_id,
                profile_name="Default Enterprise Assurance Profile",
                is_enabled=True,
                evaluation_cadence_hours=6,
                drift_critical_threshold=20.0,
                drift_high_threshold=15.0,
                min_control_health_score=70.0,
                max_evidence_age_days=90,
                max_open_finding_sla_breach_count=0,
                auto_trigger_capa_on_critical_drift=True,
                created_by_id=current_user_id,
            )
            db.add(profile)
            db.commit()
            db.refresh(profile)
        return profile

    @staticmethod
    def update_profile(
        db: Session,
        organization_id: int,
        profile_in: ContinuousComplianceProfileUpdate,
        current_user_id: int,
    ) -> ContinuousComplianceProfile:
        profile = ContinuousComplianceService.get_or_create_profile(db, organization_id, current_user_id)

        update_data = profile_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(profile, field, value)

        db.commit()
        db.refresh(profile)

        ContinuousComplianceService._audit_log(
            db=db,
            organization_id=organization_id,
            actor_id=current_user_id,
            action="UPDATE_CONTINUOUS_COMPLIANCE_PROFILE",
            resource_type="ContinuousComplianceProfile",
            resource_id=profile.id,
            details=update_data,
        )
        return profile

    # ── Authoritative Posture Calculation ───────────────────────────────────

    @staticmethod
    def calculate_unified_assurance(
        db: Session,
        organization_id: int,
    ) -> Dict[str, Any]:
        """Server-authoritative calculation aggregating all 6 platform assurance pillars."""
        now = datetime.now(timezone.utc)

        # 1. Controls Assurance Pillar (Phase 7 CCM & Controls)
        snapshots = db.query(ControlHealthSnapshot).filter(
            ControlHealthSnapshot.organization_id == organization_id
        ).all()
        if snapshots:
            avg_health = sum(s.health_score for s in snapshots) / len(snapshots)
            controls_score = round(avg_health, 1)
        else:
            total_ctrls = db.query(OrganizationControl).filter(
                OrganizationControl.organization_id == organization_id
            ).count()
            controls_score = 100.0 if total_ctrls > 0 else 85.0

        # 2. Evidence Pipeline Pillar (Phase 3 Freshness & Phase 22 Collection Runs)
        evidence_items = db.query(EvidenceItem).filter(
            EvidenceItem.organization_id == organization_id
        ).all()
        recent_runs = db.query(EvidenceCollectionRun).filter(
            EvidenceCollectionRun.organization_id == organization_id
        ).order_by(EvidenceCollectionRun.started_at.desc()).limit(50).all()

        evidence_freshness_ratio = 1.0
        if evidence_items:
            ninety_days_ago = now - timedelta(days=90)
            fresh_count = sum(1 for e in evidence_items if e.created_at >= ninety_days_ago)
            evidence_freshness_ratio = fresh_count / len(evidence_items)

        run_success_ratio = 1.0
        if recent_runs:
            success_runs = sum(1 for r in recent_runs if r.status == CollectionRunStatusEnum.SUCCESS)
            run_success_ratio = success_runs / len(recent_runs)

        evidence_score = round((0.6 * evidence_freshness_ratio + 0.4 * run_success_ratio) * 100.0, 1)

        # 3. Regulatory Compliance Pillar (Phase 21 Obligations & Changes)
        obligations = db.query(RegulatoryObligation).filter(
            RegulatoryObligation.organization_id == organization_id
        ).all()
        unreviewed_changes = db.query(RegulatoryChangeEvent).filter(
            RegulatoryChangeEvent.organization_id == organization_id,
            RegulatoryChangeEvent.status.in_([RegulatoryChangeStatusEnum.STAGED, RegulatoryChangeStatusEnum.UNDER_REVIEW]),
        ).count()

        if obligations:
            compliant_obs = sum(1 for o in obligations if o.compliance_status == RegulatoryComplianceStatusEnum.COMPLIANT)
            reg_ratio = compliant_obs / len(obligations)
            reg_penalty = min(unreviewed_changes * 5.0, 25.0)
            regulatory_score = round(max(0.0, (reg_ratio * 100.0) - reg_penalty), 1)
        else:
            regulatory_score = round(max(70.0, 100.0 - (unreviewed_changes * 5.0)), 1)

        # 4. Remediation SLA Pillar (Phase 11 CAPA & Phase 4 Findings)
        open_findings = db.query(Finding).filter(
            Finding.organization_id == organization_id,
            Finding.status != FindingStatusEnum.CLOSED,
        ).all()
        sla_breached_count = 0
        for f in open_findings:
            if hasattr(f, "due_date") and f.due_date and f.due_date < now.date():
                sla_breached_count += 1

        remediation_penalty = min(sla_breached_count * 10.0, 50.0)
        remediation_score = round(max(0.0, 100.0 - remediation_penalty), 1)

        # 5. Cloud & Identity Posture Pillar (Phase 18 & Phase 19)
        from app.models.cloudsec import EvaluationStatusEnum
        from app.models.identity_governance import SoDViolationStatusEnum
        cloud_findings_count = db.query(CloudSecurityFinding).filter(
            CloudSecurityFinding.organization_id == organization_id,
            CloudSecurityFinding.evaluation_status == EvaluationStatusEnum.FAILED,
        ).count()
        sod_violations_count = db.query(SoDConflictViolation).filter(
            SoDConflictViolation.organization_id == organization_id,
            SoDConflictViolation.status == SoDViolationStatusEnum.ACTIVE_VIOLATION,
        ).count()

        cloud_id_penalty = min((cloud_findings_count * 2.0) + (sod_violations_count * 5.0), 50.0)
        cloud_identity_score = round(max(0.0, 100.0 - cloud_id_penalty), 1)

        # 6. Harmonized Frameworks Pillar (Phase 8)
        common_controls_count = db.query(RationalizedCommonControl).filter(
            RationalizedCommonControl.organization_id == organization_id
        ).count()
        harmonization_score = 95.0 if common_controls_count > 0 else 88.0

        # Weighted Composite Overall Assurance Score
        overall_score = round(
            (0.25 * controls_score)
            + (0.20 * evidence_score)
            + (0.15 * regulatory_score)
            + (0.15 * remediation_score)
            + (0.15 * cloud_identity_score)
            + (0.10 * harmonization_score),
            1,
        )

        active_drift = db.query(ComplianceDriftRecord).filter(
            ComplianceDriftRecord.organization_id == organization_id,
            ComplianceDriftRecord.status.in_([ComplianceDriftStatusEnum.OPEN, ComplianceDriftStatusEnum.ACKNOWLEDGED]),
        ).all()

        critical_drift_count = sum(1 for d in active_drift if d.severity == ComplianceDriftSeverityEnum.CRITICAL)

        pillar_breakdown = {
            "controls_assurance": {"score": controls_score, "weight": 0.25, "status": "HEALTHY" if controls_score >= 80 else "DEGRADED"},
            "evidence_pipeline": {"score": evidence_score, "weight": 0.20, "status": "HEALTHY" if evidence_score >= 80 else "DEGRADED"},
            "regulatory_compliance": {"score": regulatory_score, "weight": 0.15, "status": "HEALTHY" if regulatory_score >= 80 else "DEGRADED"},
            "remediation_sla": {"score": remediation_score, "weight": 0.15, "status": "HEALTHY" if remediation_score >= 80 else "DEGRADED"},
            "cloud_identity_posture": {"score": cloud_identity_score, "weight": 0.15, "status": "HEALTHY" if cloud_identity_score >= 80 else "DEGRADED"},
            "harmonized_frameworks": {"score": harmonization_score, "weight": 0.10, "status": "HEALTHY" if harmonization_score >= 80 else "DEGRADED"},
        }

        framework_breakdown = {
            "NIST-CSF-2.0": {"compliance_rate": round(controls_score, 1), "status": "COMPLIANT" if controls_score >= 80 else "PARTIAL"},
            "ISO-27001-2022": {"compliance_rate": round(evidence_score, 1), "status": "COMPLIANT" if evidence_score >= 80 else "PARTIAL"},
            "SOC2-TYPE-II": {"compliance_rate": round(remediation_score, 1), "status": "COMPLIANT" if remediation_score >= 80 else "PARTIAL"},
        }

        return {
            "overall_assurance_score": overall_score,
            "controls_assurance_score": controls_score,
            "evidence_pipeline_score": evidence_score,
            "regulatory_compliance_score": regulatory_score,
            "remediation_sla_score": remediation_score,
            "cloud_identity_posture_score": cloud_identity_score,
            "harmonized_frameworks_score": harmonization_score,
            "active_drift_count": len(active_drift),
            "critical_drift_count": critical_drift_count,
            "pillar_breakdown": pillar_breakdown,
            "framework_compliance_breakdown": framework_breakdown,
            "last_evaluated_at": now,
            "calculation_version": ContinuousComplianceService.CALCULATION_VERSION,
        }

    # ── Continuous Evaluation & Multi-Vector Drift Detection ───────────────

    @staticmethod
    def evaluate_continuous_compliance(
        db: Session,
        organization_id: int,
        current_user_id: int,
    ) -> Dict[str, Any]:
        """Runs on-demand continuous compliance evaluation, detects multi-vector drift, and triggers CAPA if needed."""
        profile = ContinuousComplianceService.get_or_create_profile(db, organization_id, current_user_id)
        now = datetime.now(timezone.utc)

        posture = ContinuousComplianceService.calculate_unified_assurance(db, organization_id)

        # ── Detect Multi-Vector Drift ───────────────────────────────────────
        detected_drifts: List[ComplianceDriftRecord] = []

        # Vector 1: CCM Health Degradation
        degraded_snapshots = db.query(ControlHealthSnapshot).filter(
            ControlHealthSnapshot.organization_id == organization_id,
            ControlHealthSnapshot.health_score < profile.min_control_health_score,
        ).all()
        for snap in degraded_snapshots:
            drift_code = f"DRIFT-CCM-CTRL-{snap.organization_control_id}-{int(now.timestamp())}"
            existing = db.query(ComplianceDriftRecord).filter(
                ComplianceDriftRecord.organization_id == organization_id,
                ComplianceDriftRecord.organization_control_id == snap.organization_control_id,
                ComplianceDriftRecord.drift_vector == ComplianceDriftVectorEnum.CCM_HEALTH_DEGRADATION,
                ComplianceDriftRecord.status == ComplianceDriftStatusEnum.OPEN,
            ).first()
            if not existing:
                drift = ComplianceDriftRecord(
                    organization_id=organization_id,
                    organization_control_id=snap.organization_control_id,
                    drift_code=drift_code,
                    drift_vector=ComplianceDriftVectorEnum.CCM_HEALTH_DEGRADATION,
                    severity=ComplianceDriftSeverityEnum.CRITICAL if snap.health_score < 50.0 else ComplianceDriftSeverityEnum.HIGH,
                    status=ComplianceDriftStatusEnum.OPEN,
                    title=f"Control Health Degradation on Control #{snap.organization_control_id}",
                    description=f"Health score dropped to {snap.health_score}%, below threshold {profile.min_control_health_score}%.",
                    root_cause_metric="health_score",
                    baseline_value=profile.min_control_health_score,
                    observed_value=snap.health_score,
                    detected_at=now,
                )
                db.add(drift)
                detected_drifts.append(drift)

        # Vector 2: Integration Pipeline Failures
        failed_runs = db.query(EvidenceCollectionRun).filter(
            EvidenceCollectionRun.organization_id == organization_id,
            EvidenceCollectionRun.status.in_([CollectionRunStatusEnum.FAILED, CollectionRunStatusEnum.PARTIAL_FAILURE]),
            EvidenceCollectionRun.started_at >= (now - timedelta(hours=profile.evaluation_cadence_hours)),
        ).all()
        for run in failed_runs:
            drift_code = f"DRIFT-INTG-{run.job_id}-{int(now.timestamp())}"
            existing = db.query(ComplianceDriftRecord).filter(
                ComplianceDriftRecord.organization_id == organization_id,
                ComplianceDriftRecord.drift_vector == ComplianceDriftVectorEnum.INTEGRATION_PIPELINE_FAILURE,
                ComplianceDriftRecord.root_cause_metric == f"job_{run.job_id}",
                ComplianceDriftRecord.status == ComplianceDriftStatusEnum.OPEN,
            ).first()
            if not existing:
                drift = ComplianceDriftRecord(
                    organization_id=organization_id,
                    drift_code=drift_code,
                    drift_vector=ComplianceDriftVectorEnum.INTEGRATION_PIPELINE_FAILURE,
                    severity=ComplianceDriftSeverityEnum.HIGH,
                    status=ComplianceDriftStatusEnum.OPEN,
                    title=f"Automated Evidence Collection Failure: {run.source_system}",
                    description=f"Evidence collection job failed with error: {run.error_message or 'Execution failure'}",
                    root_cause_metric=f"job_{run.job_id}",
                    detected_at=now,
                )
                db.add(drift)
                detected_drifts.append(drift)

        # Vector 3: Regulatory Change Exposure
        unaddressed_changes = db.query(RegulatoryChangeEvent).filter(
            RegulatoryChangeEvent.organization_id == organization_id,
            RegulatoryChangeEvent.status == RegulatoryChangeStatusEnum.STAGED,
            RegulatoryChangeEvent.severity.in_([RegulatoryChangeSeverityEnum.CRITICAL, RegulatoryChangeSeverityEnum.MAJOR]),
        ).all()
        for chg in unaddressed_changes:
            drift_code = f"DRIFT-REG-{chg.id}-{int(now.timestamp())}"
            existing = db.query(ComplianceDriftRecord).filter(
                ComplianceDriftRecord.organization_id == organization_id,
                ComplianceDriftRecord.drift_vector == ComplianceDriftVectorEnum.REGULATORY_CHANGE_EXPOSURE,
                ComplianceDriftRecord.root_cause_metric == f"change_{chg.id}",
                ComplianceDriftRecord.status == ComplianceDriftStatusEnum.OPEN,
            ).first()
            if not existing:
                drift = ComplianceDriftRecord(
                    organization_id=organization_id,
                    drift_code=drift_code,
                    drift_vector=ComplianceDriftVectorEnum.REGULATORY_CHANGE_EXPOSURE,
                    severity=ComplianceDriftSeverityEnum.CRITICAL if chg.severity == RegulatoryChangeSeverityEnum.CRITICAL else ComplianceDriftSeverityEnum.HIGH,
                    status=ComplianceDriftStatusEnum.OPEN,
                    title=f"Unaddressed High-Severity Regulatory Change: {chg.title}",
                    description=f"Staged regulatory change requires mandatory Four-Eyes impact assessment and review.",
                    root_cause_metric=f"change_{chg.id}",
                    detected_at=now,
                )
                db.add(drift)
                detected_drifts.append(drift)

        # Flush new drifts
        db.flush()

        # ── Auto-Trigger CAPA (Phase 11 RemediationPlan) on Critical Drift ────
        if profile.auto_trigger_capa_on_critical_drift:
            for d in detected_drifts:
                if d.severity == ComplianceDriftSeverityEnum.CRITICAL and not d.remediation_plan_id:
                    ctrl = db.query(OrganizationControl).filter(OrganizationControl.organization_id == organization_id).first()
                    ctrl_id = d.organization_control_id or (ctrl.id if ctrl else None)
                    alert_id = None
                    if ctrl_id:
                        from app.models.monitoring import DriftAlertTypeEnum, DriftAlertSeverityEnum, DriftAlertStatusEnum
                        alert = ComplianceDriftAlert(
                            organization_id=organization_id,
                            organization_control_id=ctrl_id,
                            alert_type=DriftAlertTypeEnum.CONTROL_DEGRADED,
                            severity=DriftAlertSeverityEnum.CRITICAL,
                            status=DriftAlertStatusEnum.ACTIVE,
                            title=d.title,
                            description=d.description,
                        )
                        db.add(alert)
                        db.flush()
                        alert_id = alert.id

                    if alert_id:
                        capa_code = f"CAPA-{d.drift_code}"
                        capa_plan = RemediationPlan(
                            organization_id=organization_id,
                            plan_code=capa_code,
                            title=f"CAPA: Resolve Continuous Compliance Drift ({d.title})",
                            problem_statement=d.description,
                            root_cause_classification=RemediationRootCauseClassificationEnum.CONFIGURATION_DRIFT,
                            source_type=RemediationSourceTypeEnum.CCM_DRIFT,
                            compliance_drift_alert_id=alert_id,
                            severity=RemediationSeverityEnum.CRITICAL,
                            status=RemediationStatusEnum.DRAFT,
                            plan_owner_id=current_user_id,
                        )
                        db.add(capa_plan)
                        db.flush()
                        d.remediation_plan_id = capa_plan.id
                        d.status = ComplianceDriftStatusEnum.REMEDIATION_TRIGGERED

        profile.last_evaluated_at = now
        db.commit()

        ContinuousComplianceService._audit_log(
            db=db,
            organization_id=organization_id,
            actor_id=current_user_id,
            action="EVALUATE_CONTINUOUS_COMPLIANCE",
            resource_type="ContinuousComplianceProfile",
            resource_id=profile.id,
            details={
                "overall_assurance_score": posture["overall_assurance_score"],
                "drifts_detected_count": len(detected_drifts),
            },
        )

        return posture

    # ── On-Demand Remediation Trigger ───────────────────────────────────────

    @staticmethod
    def trigger_remediation_for_drift(
        db: Session,
        organization_id: int,
        drift_id: int,
        current_user_id: int,
    ) -> Tuple[ComplianceDriftRecord, RemediationPlan]:
        """Triggers Phase 11 authoritative RemediationPlan from an active ComplianceDriftRecord."""
        drift = db.query(ComplianceDriftRecord).filter(
            ComplianceDriftRecord.id == drift_id,
            ComplianceDriftRecord.organization_id == organization_id,
        ).first()
        if not drift:
            raise ValueError("Compliance drift record not found.")

        if drift.remediation_plan_id:
            plan = db.query(RemediationPlan).filter(
                RemediationPlan.id == drift.remediation_plan_id,
                RemediationPlan.organization_id == organization_id,
            ).first()
            return drift, plan

        plan_code = f"CAPA-DRIFT-{drift.id}-{int(datetime.now(timezone.utc).timestamp())}"
        severity_map = {
            ComplianceDriftSeverityEnum.CRITICAL: RemediationSeverityEnum.CRITICAL,
            ComplianceDriftSeverityEnum.HIGH: RemediationSeverityEnum.HIGH,
            ComplianceDriftSeverityEnum.MEDIUM: RemediationSeverityEnum.MEDIUM,
            ComplianceDriftSeverityEnum.LOW: RemediationSeverityEnum.LOW,
        }

        ctrl = db.query(OrganizationControl).filter(OrganizationControl.organization_id == organization_id).first()
        ctrl_id = drift.organization_control_id or (ctrl.id if ctrl else None)
        if not ctrl_id:
            raise ValueError("Cannot trigger CAPA without an associated OrganizationControl.")

        from app.models.monitoring import DriftAlertTypeEnum, DriftAlertSeverityEnum, DriftAlertStatusEnum
        alert = ComplianceDriftAlert(
            organization_id=organization_id,
            organization_control_id=ctrl_id,
            alert_type=DriftAlertTypeEnum.CONTROL_DEGRADED,
            severity=DriftAlertSeverityEnum.CRITICAL if drift.severity == ComplianceDriftSeverityEnum.CRITICAL else DriftAlertSeverityEnum.HIGH,
            status=DriftAlertStatusEnum.ACTIVE,
            title=drift.title,
            description=drift.description,
        )
        db.add(alert)
        db.flush()

        capa_plan = RemediationPlan(
            organization_id=organization_id,
            plan_code=plan_code,
            title=f"CAPA: Remediate Drift ({drift.title})",
            problem_statement=drift.description,
            root_cause_classification=RemediationRootCauseClassificationEnum.CONTROL_DEFICIENCY,
            source_type=RemediationSourceTypeEnum.CCM_DRIFT,
            compliance_drift_alert_id=alert.id,
            severity=severity_map.get(drift.severity, RemediationSeverityEnum.MEDIUM),
            status=RemediationStatusEnum.DRAFT,
            plan_owner_id=current_user_id,
        )
        db.add(capa_plan)
        db.flush()

        drift.remediation_plan_id = capa_plan.id
        drift.status = ComplianceDriftStatusEnum.REMEDIATION_TRIGGERED
        db.commit()
        db.refresh(drift)
        db.refresh(capa_plan)

        ContinuousComplianceService._audit_log(
            db=db,
            organization_id=organization_id,
            actor_id=current_user_id,
            action="TRIGGER_DRIFT_REMEDIATION",
            resource_type="ComplianceDriftRecord",
            resource_id=drift.id,
            details={"remediation_plan_id": capa_plan.id, "plan_code": capa_plan.plan_code},
        )
        return drift, capa_plan

    # ── Immutable Assurance Snapshots ───────────────────────────────────────

    @staticmethod
    def capture_assurance_snapshot(
        db: Session,
        organization_id: int,
        snap_in: ContinuousAssuranceSnapshotCreate,
        current_user_id: int,
    ) -> ContinuousAssuranceSnapshot:
        """Captures an immutable point-in-time cryptographic summary of enterprise assurance."""
        existing = db.query(ContinuousAssuranceSnapshot).filter(
            ContinuousAssuranceSnapshot.organization_id == organization_id,
            ContinuousAssuranceSnapshot.snapshot_code == snap_in.snapshot_code,
        ).first()
        if existing:
            raise ValueError(f"Continuous assurance snapshot code '{snap_in.snapshot_code}' already exists.")

        posture = ContinuousComplianceService.calculate_unified_assurance(db, organization_id)
        now = datetime.now(timezone.utc)

        raw_payload = {
            "snapshot_code": snap_in.snapshot_code,
            "organization_id": organization_id,
            "overall_assurance_score": posture["overall_assurance_score"],
            "pillar_breakdown": posture["pillar_breakdown"],
            "captured_at": now.isoformat(),
        }
        data_hash = hashlib.sha256(json.dumps(raw_payload, sort_keys=True).encode("utf-8")).hexdigest()

        snapshot = ContinuousAssuranceSnapshot(
            organization_id=organization_id,
            snapshot_code=snap_in.snapshot_code,
            captured_at=now,
            overall_assurance_score=posture["overall_assurance_score"],
            controls_assurance_score=posture["controls_assurance_score"],
            evidence_pipeline_score=posture["evidence_pipeline_score"],
            regulatory_compliance_score=posture["regulatory_compliance_score"],
            remediation_sla_score=posture["remediation_sla_score"],
            cloud_identity_posture_score=posture["cloud_identity_posture_score"],
            harmonized_frameworks_score=posture["harmonized_frameworks_score"],
            active_drift_count=posture["active_drift_count"],
            critical_drift_count=posture["critical_drift_count"],
            pillar_breakdown=json.dumps(posture["pillar_breakdown"]),
            framework_compliance_breakdown=json.dumps(posture["framework_compliance_breakdown"]),
            data_hash_sha256=data_hash,
            calculation_version=ContinuousComplianceService.CALCULATION_VERSION,
            created_by_id=current_user_id,
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)

        ContinuousComplianceService._audit_log(
            db=db,
            organization_id=organization_id,
            actor_id=current_user_id,
            action="CAPTURE_CONTINUOUS_ASSURANCE_SNAPSHOT",
            resource_type="ContinuousAssuranceSnapshot",
            resource_id=snapshot.id,
            details={"snapshot_code": snapshot.snapshot_code, "score": snapshot.overall_assurance_score},
        )
        return snapshot

    @staticmethod
    def list_snapshots(
        db: Session,
        organization_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ContinuousAssuranceSnapshot]:
        return db.query(ContinuousAssuranceSnapshot).filter(
            ContinuousAssuranceSnapshot.organization_id == organization_id
        ).order_by(ContinuousAssuranceSnapshot.captured_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def list_drifts(
        db: Session,
        organization_id: int,
        status: Optional[ComplianceDriftStatusEnum] = None,
        vector: Optional[ComplianceDriftVectorEnum] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ComplianceDriftRecord]:
        query = db.query(ComplianceDriftRecord).filter(ComplianceDriftRecord.organization_id == organization_id)
        if status:
            query = query.filter(ComplianceDriftRecord.status == status)
        if vector:
            query = query.filter(ComplianceDriftRecord.drift_vector == vector)
        return query.order_by(ComplianceDriftRecord.detected_at.desc()).offset(skip).limit(limit).all()
