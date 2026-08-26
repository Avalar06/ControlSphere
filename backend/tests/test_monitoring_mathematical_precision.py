from datetime import datetime, timezone
import pytest
from sqlalchemy.orm import Session

from app.models.control import ImplementationStatusEnum, OrganizationControl
from app.models.evidence import EvidenceItem, EvidenceStatusEnum
from app.models.finding import Finding, FindingSeverityEnum, FindingStatusEnum, FindingTypeEnum
from app.models.monitoring import ControlHealthStatusEnum, EvaluationTriggerEnum
from app.services.monitoring_service import MonitoringService


class TestMonitoringMathematicalPrecision:

    def test_health_band_boundaries_exact(self, db: Session, org_apex, seeded_framework, admin_user):
        """Verify strict mathematical boundary precision for all 4 health bands:
        HEALTHY: [80.0, 100.0]
        DEGRADED: [60.0, 79.9]
        AT_RISK: [40.0, 59.9]
        FAILING: [0.0, 39.9]
        """
        subcat = seeded_framework.functions[0].categories[0].subcategories[0]
        ctrl = OrganizationControl(
            organization_id=org_apex.id,
            subcategory_id=subcat.id,
            status=ImplementationStatusEnum.IMPLEMENTED,
        )
        db.add(ctrl)
        db.commit()
        db.refresh(ctrl)

        config = MonitoringService.get_or_create_config(db, org_apex.id)

        # 1. Baseline: No evidence (E=0), Implemented (A=100), No penalties (P=0)
        # Score = (0 * 0.35) + (100 * 0.25) + (40 - 0) = 25.0 + 40.0 = 65.0 -> DEGRADED
        s1, _, _ = MonitoringService._evaluate_single_control(
            db, org_apex.id, ctrl, config, EvaluationTriggerEnum.MANUAL, datetime.now(timezone.utc)
        )
        assert s1.health_score == 65.0
        assert s1.health_status == ControlHealthStatusEnum.DEGRADED

        # 2. Add fresh accepted evidence (E=100) -> Score = 35 + 25 + 40 = 100.0 -> HEALTHY
        ev = EvidenceItem(
            organization_id=org_apex.id,
            organization_control_id=ctrl.id,
            title="Boundary Test Evidence",
            original_filename="test.pdf",
            stored_filename="test.pdf",
            file_extension=".pdf",
            content_type="application/pdf",
            file_size=100,
            sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            storage_key="evidence/test.pdf",
            status=EvidenceStatusEnum.ACCEPTED,
        )
        db.add(ev)
        db.commit()

        s2, _, _ = MonitoringService._evaluate_single_control(
            db, org_apex.id, ctrl, config, EvaluationTriggerEnum.MANUAL, datetime.now(timezone.utc)
        )
        assert s2.health_score == 100.0
        assert s2.health_status == ControlHealthStatusEnum.HEALTHY

        # 3. Add 1 Critical finding (penalty 20) -> Score = 35 + 25 + (40 - 20) = 80.0 -> Exact HEALTHY boundary
        f1 = Finding(
            organization_id=org_apex.id,
            organization_control_id=ctrl.id,
            title="Critical boundary",
            description="Desc",
            recommendation="Rec",
            finding_type=FindingTypeEnum.TECHNICAL_GAP,
            severity=FindingSeverityEnum.CRITICAL,
            status=FindingStatusEnum.OPEN,
            created_at=datetime.now(timezone.utc),
            created_by_id=admin_user.id,
        )
        db.add(f1)
        db.commit()

        s3, _, _ = MonitoringService._evaluate_single_control(
            db, org_apex.id, ctrl, config, EvaluationTriggerEnum.MANUAL, datetime.now(timezone.utc)
        )
        assert s3.health_score == 80.0
        assert s3.health_status == ControlHealthStatusEnum.HEALTHY

        # 4. Add 1 Low finding (penalty 1) -> Total penalty 21 -> Score = 35 + 25 + (40 - 21) = 79.0 -> DEGRADED
        f2 = Finding(
            organization_id=org_apex.id,
            organization_control_id=ctrl.id,
            title="Low boundary",
            description="Desc",
            recommendation="Rec",
            finding_type=FindingTypeEnum.POLICY_GAP,
            severity=FindingSeverityEnum.LOW,
            status=FindingStatusEnum.OPEN,
            created_at=datetime.now(timezone.utc),
            created_by_id=admin_user.id,
        )
        db.add(f2)
        db.commit()

        s4, _, _ = MonitoringService._evaluate_single_control(
            db, org_apex.id, ctrl, config, EvaluationTriggerEnum.MANUAL, datetime.now(timezone.utc)
        )
        assert s4.health_score == 79.0
        assert s4.health_status == ControlHealthStatusEnum.DEGRADED
