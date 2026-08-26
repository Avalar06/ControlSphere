from datetime import date, datetime, timedelta, timezone
import pytest
from sqlalchemy.orm import Session

from app.models.control import ImplementationStatusEnum, OrganizationControl, PriorityEnum
from app.models.evidence import EvidenceItem, EvidenceStatusEnum
from app.models.finding import Finding, FindingSeverityEnum, FindingStatusEnum, FindingTypeEnum
from app.models.monitoring import (
    ControlHealthStatusEnum,
    DriftAlertSeverityEnum,
    DriftAlertStatusEnum,
    DriftAlertTypeEnum,
    EvaluationTriggerEnum,
)
from app.services.monitoring_service import MonitoringService


class TestMonitoringEngine:

    def test_clean_control_evaluates_healthy(self, db: Session, org_apex, seeded_framework):
        """A control with accepted fresh evidence and implemented status scores 100/HEALTHY."""
        subcat = seeded_framework.functions[0].categories[0].subcategories[0]
        ctrl = OrganizationControl(
            organization_id=org_apex.id,
            subcategory_id=subcat.id,
            status=ImplementationStatusEnum.IMPLEMENTED,
            priority=PriorityEnum.HIGH,
        )
        db.add(ctrl)
        db.commit()
        db.refresh(ctrl)

        # Fresh accepted evidence
        ev = EvidenceItem(
            organization_id=org_apex.id,
            organization_control_id=ctrl.id,
            title="Fresh Policy Evidence",
            original_filename="policy.pdf",
            stored_filename="policy_123.pdf",
            file_extension=".pdf",
            content_type="application/pdf",
            file_size=1024,
            sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            storage_key="evidence/policy_123.pdf",
            status=EvidenceStatusEnum.ACCEPTED,
        )
        db.add(ev)
        db.commit()

        config = MonitoringService.get_or_create_config(db, org_apex.id)
        snapshot, gen, res = MonitoringService._evaluate_single_control(
            db=db,
            organization_id=org_apex.id,
            control=ctrl,
            config=config,
            trigger=EvaluationTriggerEnum.MANUAL,
            eval_time=datetime.now(timezone.utc),
        )

        assert snapshot.health_score == 100.0
        assert snapshot.health_status == ControlHealthStatusEnum.HEALTHY
        assert snapshot.evidence_freshness_score == 100.0
        assert snapshot.assessment_currency_score == 100.0
        assert snapshot.finding_penalty_score == 0.0
        assert snapshot.exception_penalty_score == 0.0

    def test_stale_evidence_decays_freshness(self, db: Session, org_apex, seeded_framework):
        """Evidence older than evidence_max_age_days decays freshness score."""
        subcat = seeded_framework.functions[0].categories[0].subcategories[0]
        ctrl = OrganizationControl(
            organization_id=org_apex.id,
            subcategory_id=subcat.id,
            status=ImplementationStatusEnum.IMPLEMENTED,
        )
        db.add(ctrl)
        db.commit()
        db.refresh(ctrl)

        # Evidence created 120 days ago (threshold is 90 days)
        old_date = datetime.now(timezone.utc) - timedelta(days=120)
        ev = EvidenceItem(
            organization_id=org_apex.id,
            organization_control_id=ctrl.id,
            title="Old Evidence",
            original_filename="old.pdf",
            stored_filename="old_123.pdf",
            file_extension=".pdf",
            content_type="application/pdf",
            file_size=1024,
            sha256_hash="1111c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            storage_key="evidence/old_123.pdf",
            status=EvidenceStatusEnum.ACCEPTED,
            created_at=old_date,
        )
        db.add(ev)
        db.commit()

        config = MonitoringService.get_or_create_config(db, org_apex.id)
        snapshot, gen, res = MonitoringService._evaluate_single_control(
            db=db,
            organization_id=org_apex.id,
            control=ctrl,
            config=config,
            trigger=EvaluationTriggerEnum.MANUAL,
            eval_time=datetime.now(timezone.utc),
        )

        assert snapshot.days_since_last_evidence >= 120
        assert snapshot.evidence_freshness_score < 100.0
        assert snapshot.health_score < 100.0

    def test_critical_finding_applies_penalty(self, db: Session, org_apex, seeded_framework, admin_user):
        """Open critical finding with SLA breach penalizes control health heavily."""
        subcat = seeded_framework.functions[0].categories[0].subcategories[0]
        ctrl = OrganizationControl(
            organization_id=org_apex.id,
            subcategory_id=subcat.id,
            status=ImplementationStatusEnum.IMPLEMENTED,
        )
        db.add(ctrl)
        db.commit()
        db.refresh(ctrl)

        # Critical finding created 20 days ago (critical SLA is 15 days)
        old_created = datetime.now(timezone.utc) - timedelta(days=20)
        f = Finding(
            organization_id=org_apex.id,
            organization_control_id=ctrl.id,
            title="Unpatched Remote Execution",
            description="Deficiency in host security",
            recommendation="Apply emergency patch",
            finding_type=FindingTypeEnum.TECHNICAL_GAP,
            severity=FindingSeverityEnum.CRITICAL,
            status=FindingStatusEnum.OPEN,
            created_at=old_created,
            created_by_id=admin_user.id,
        )
        db.add(f)
        db.commit()

        config = MonitoringService.get_or_create_config(db, org_apex.id)
        snapshot, gen, res = MonitoringService._evaluate_single_control(
            db=db,
            organization_id=org_apex.id,
            control=ctrl,
            config=config,
            trigger=EvaluationTriggerEnum.MANUAL,
            eval_time=datetime.now(timezone.utc),
        )

        # 20 base penalty + 10 SLA breach penalty = 30.0
        assert snapshot.finding_penalty_score == 30.0
        assert snapshot.active_findings_count == 1
        assert snapshot.critical_high_findings_count == 1
        assert snapshot.health_status in [ControlHealthStatusEnum.DEGRADED, ControlHealthStatusEnum.AT_RISK, ControlHealthStatusEnum.FAILING]
