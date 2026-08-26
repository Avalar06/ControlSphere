from datetime import datetime, timezone
import pytest
from sqlalchemy.orm import Session

from app.models.control import ImplementationStatusEnum, OrganizationControl
from app.models.evidence import EvidenceItem, EvidenceStatusEnum
from app.models.framework import Framework, FrameworkCategory, FrameworkFunction, FrameworkSubcategory
from app.models.harmonization import (
    CommonControlDomainEnum,
    CommonControlMapping,
    FrameworkCrosswalkMapping,
    MappingTypeEnum,
    RationalizationStatusEnum,
    RationalizedCommonControl,
)
from app.models.monitoring import ControlHealthSnapshot, ControlHealthStatusEnum
from app.services.harmonization_service import HarmonizationService
from app.services.monitoring_service import MonitoringService


class TestHarmonizationEngine:

    def test_zero_linked_controls_common_control_evaluates_100_healthy(self, db: Session, org_apex):
        """Approved architecture rule: a common control with 0 linked organization controls scores 100.0/HEALTHY."""
        cc = RationalizedCommonControl(
            organization_id=org_apex.id,
            common_control_code="CCF-ZERO-01",
            title="Zero-Link Common Control",
            description="Control with no mappings yet",
            domain=CommonControlDomainEnum.GOVERNANCE_RISK,
            rationalization_status=RationalizationStatusEnum.ACTIVE,
        )
        db.add(cc)
        db.commit()
        db.refresh(cc)

        score, status = HarmonizationService.recalculate_common_control_health(
            db=db,
            organization_id=org_apex.id,
            common_control_id=cc.id,
        )
        assert score == 100.0
        assert status == ControlHealthStatusEnum.HEALTHY

    def test_weighted_average_inherited_health_calculation(self, db: Session, org_apex, seeded_framework):
        """Common control inherited health is the exact weighted average of linked control CCM scores."""
        subcats = seeded_framework.functions[0].categories[0].subcategories
        subcat1 = subcats[0]
        subcat2 = subcats[1]

        # Control 1: Implemented with fresh evidence -> CCM Health = 100.0
        ctrl1 = OrganizationControl(
            organization_id=org_apex.id,
            subcategory_id=subcat1.id,
            status=ImplementationStatusEnum.IMPLEMENTED,
        )
        # Control 2: Implemented without evidence -> CCM Health = 65.0 (0*0.35 + 100*0.25 + 40 = 65.0)
        ctrl2 = OrganizationControl(
            organization_id=org_apex.id,
            subcategory_id=subcat2.id,
            status=ImplementationStatusEnum.IMPLEMENTED,
        )
        db.add_all([ctrl1, ctrl2])
        db.commit()

        # Add fresh evidence to ctrl1
        ev = EvidenceItem(
            organization_id=org_apex.id,
            organization_control_id=ctrl1.id,
            title="Policy Evidence",
            original_filename="policy.pdf",
            stored_filename="policy.pdf",
            file_extension=".pdf",
            content_type="application/pdf",
            file_size=1024,
            sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            storage_key="evidence/policy.pdf",
            status=EvidenceStatusEnum.ACCEPTED,
        )
        db.add(ev)
        db.commit()

        # Snapshot for ctrl1: 100.0, Snapshot for ctrl2: 60.0
        snap1 = ControlHealthSnapshot(
            organization_id=org_apex.id,
            organization_control_id=ctrl1.id,
            health_score=100.0,
            health_status=ControlHealthStatusEnum.HEALTHY,
            evaluated_at=datetime.now(timezone.utc),
        )
        snap2 = ControlHealthSnapshot(
            organization_id=org_apex.id,
            organization_control_id=ctrl2.id,
            health_score=60.0,
            health_status=ControlHealthStatusEnum.DEGRADED,
            evaluated_at=datetime.now(timezone.utc),
        )
        db.add_all([snap1, snap2])
        db.commit()

        # Create common control
        cc = RationalizedCommonControl(
            organization_id=org_apex.id,
            common_control_code="CCF-IAM-01",
            title="Identity & Access Management",
            description="Normalized IAM requirement",
            domain=CommonControlDomainEnum.IDENTITY_ACCESS,
        )
        db.add(cc)
        db.commit()

        # Map ctrl1 with weight 2.0, ctrl2 with weight 1.0
        # Expected: (2.0 * 100.0 + 1.0 * 60.0) / (2.0 + 1.0) = 260.0 / 3.0 = 86.666... -> 86.7
        m1 = CommonControlMapping(
            organization_id=org_apex.id,
            rationalized_common_control_id=cc.id,
            organization_control_id=ctrl1.id,
            weight=2.0,
        )
        m2 = CommonControlMapping(
            organization_id=org_apex.id,
            rationalized_common_control_id=cc.id,
            organization_control_id=ctrl2.id,
            weight=1.0,
        )
        db.add_all([m1, m2])
        db.commit()

        score, status = HarmonizationService.recalculate_common_control_health(
            db=db,
            organization_id=org_apex.id,
            common_control_id=cc.id,
        )
        assert score == 86.7
        assert status == ControlHealthStatusEnum.HEALTHY

    def test_crosswalk_coverage_and_compliance_health_mathematics(self, db: Session, org_apex, seeded_framework):
        """Crosswalk inherited coverage respects confidence threshold >= 0.80 and calculates effective health."""
        # Create second target framework (e.g. ISO 27001)
        iso_fw = Framework(
            identifier="ISO-27001-2022",
            name="ISO/IEC 27001:2022",
            version="2022",
        )
        db.add(iso_fw)
        db.commit()

        fn = FrameworkFunction(framework_id=iso_fw.id, identifier="A.5", name="Organizational Controls")
        db.add(fn)
        db.commit()

        cat = FrameworkCategory(function_id=fn.id, identifier="A.5.Org", name="Policies for Information Security")
        db.add(cat)
        db.commit()

        # Target subcategories: 2 subcategories (N_F = 2)
        target_subcat1 = FrameworkSubcategory(
            category_id=cat.id,
            identifier="ISO.A.5.1",
            title="Policies for information security",
            description="Information security policies",
        )
        target_subcat2 = FrameworkSubcategory(
            category_id=cat.id,
            identifier="ISO.A.5.2",
            title="Information security roles",
            description="Role definitions",
        )
        db.add_all([target_subcat1, target_subcat2])
        db.commit()

        # Source subcategory from NIST CSF
        nist_subcat = seeded_framework.functions[0].categories[0].subcategories[0]

        # Implement NIST control with healthy score 90.0
        nist_ctrl = OrganizationControl(
            organization_id=org_apex.id,
            subcategory_id=nist_subcat.id,
            status=ImplementationStatusEnum.IMPLEMENTED,
        )
        db.add(nist_ctrl)
        db.commit()

        snap = ControlHealthSnapshot(
            organization_id=org_apex.id,
            organization_control_id=nist_ctrl.id,
            health_score=90.0,
            health_status=ControlHealthStatusEnum.HEALTHY,
            evaluated_at=datetime.now(timezone.utc),
        )
        db.add(snap)
        db.commit()

        # Crosswalk 1: nist_subcat -> target_subcat1 with high confidence 0.90 (Satisfies threshold >= 0.80)
        # Crosswalk 2: nist_subcat -> target_subcat2 with low confidence 0.70 (Fails threshold < 0.80)
        cw1 = FrameworkCrosswalkMapping(
            source_subcategory_id=nist_subcat.id,
            target_subcategory_id=target_subcat1.id,
            mapping_type=MappingTypeEnum.EXACT,
            confidence_score=0.90,
            bidirectional=True,
            rationale="Exact mapping",
        )
        cw2 = FrameworkCrosswalkMapping(
            source_subcategory_id=nist_subcat.id,
            target_subcategory_id=target_subcat2.id,
            mapping_type=MappingTypeEnum.PARTIAL,
            confidence_score=0.70,
            bidirectional=True,
            rationale="Partial correlation below threshold",
        )
        db.add_all([cw1, cw2])
        db.commit()

        overview, snapshot = HarmonizationService.calculate_framework_compliance_posture(
            db=db,
            organization_id=org_apex.id,
            framework_id=iso_fw.id,
            eval_time=datetime.now(timezone.utc),
        )

        # Total subcategories = 2
        # Directly covered = 0
        # Crosswalk covered = 1 (target_subcat1 covered via cw1; target_subcat2 not covered because cw2 < 0.80)
        # Total covered = 1
        # Coverage % = 1 / 2 * 100 = 50.0%
        # Effective health of target_subcat1 = 90.0 * 0.90 = 81.0
        # Effective health of target_subcat2 = 0.0
        # Compliance score = (81.0 + 0.0) / 2 = 40.5%
        assert overview.total_subcategories == 2
        assert overview.directly_covered_subcategories == 0
        assert overview.crosswalk_covered_subcategories == 1
        assert overview.total_covered_subcategories == 1
        assert overview.coverage_percentage == 50.0
        assert overview.compliance_health_score == 40.5
        assert snapshot.calculation_version == "v1.0"
        assert snapshot.coverage_percentage == 50.0
        assert snapshot.compliance_health_score == 40.5
