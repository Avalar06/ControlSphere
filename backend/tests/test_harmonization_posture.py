from datetime import datetime, timezone
import pytest
from sqlalchemy.orm import Session

from app.models.control import ImplementationStatusEnum, OrganizationControl
from app.models.framework import Framework, FrameworkCategory, FrameworkFunction, FrameworkSubcategory
from app.models.harmonization import FrameworkCrosswalkMapping, MappingTypeEnum
from app.models.monitoring import ControlHealthSnapshot, ControlHealthStatusEnum
from app.services.harmonization_service import HarmonizationService


class TestHarmonizationPosture:

    def test_multi_candidate_crosswalk_ambiguity_selects_highest_effective_health(
        self, db: Session, org_apex, seeded_framework
    ):
        """When multiple crosswalk sources target the same subcategory, the engine selects the candidate with highest effective health."""
        # Create Target Framework with 1 subcategory
        target_fw = Framework(identifier="TARGET-FW", name="Target Framework", version="1.0")
        db.add(target_fw)
        db.commit()

        fn = FrameworkFunction(framework_id=target_fw.id, identifier="T1", name="Target Function")
        db.add(fn)
        db.commit()

        cat = FrameworkCategory(function_id=fn.id, identifier="T1.1", name="Target Category")
        db.add(cat)
        db.commit()

        target_subcat = FrameworkSubcategory(
            category_id=cat.id,
            identifier="T1.1.1",
            title="Target Outcome",
            description="Outcome requirement",
        )
        db.add(target_subcat)
        db.commit()

        # Two source subcategories from seeded NIST framework
        subcats = seeded_framework.functions[0].categories[0].subcategories
        src_subcat1 = subcats[0]
        src_subcat2 = subcats[1]

        # Implement src1 with CCM health = 70.0
        ctrl1 = OrganizationControl(
            organization_id=org_apex.id,
            subcategory_id=src_subcat1.id,
            status=ImplementationStatusEnum.IMPLEMENTED,
        )
        # Implement src2 with CCM health = 90.0
        ctrl2 = OrganizationControl(
            organization_id=org_apex.id,
            subcategory_id=src_subcat2.id,
            status=ImplementationStatusEnum.IMPLEMENTED,
        )
        db.add_all([ctrl1, ctrl2])
        db.commit()

        snap1 = ControlHealthSnapshot(
            organization_id=org_apex.id,
            organization_control_id=ctrl1.id,
            health_score=70.0,
            health_status=ControlHealthStatusEnum.DEGRADED,
            evaluated_at=datetime.now(timezone.utc),
        )
        snap2 = ControlHealthSnapshot(
            organization_id=org_apex.id,
            organization_control_id=ctrl2.id,
            health_score=90.0,
            health_status=ControlHealthStatusEnum.HEALTHY,
            evaluated_at=datetime.now(timezone.utc),
        )
        db.add_all([snap1, snap2])
        db.commit()

        # Crosswalk 1: src1 -> target with confidence 1.0 (Effective health = 70.0 * 1.0 = 70.0)
        # Crosswalk 2: src2 -> target with confidence 0.90 (Effective health = 90.0 * 0.90 = 81.0)
        cw1 = FrameworkCrosswalkMapping(
            source_subcategory_id=src_subcat1.id,
            target_subcategory_id=target_subcat.id,
            mapping_type=MappingTypeEnum.EXACT,
            confidence_score=1.0,
            rationale="Candidate 1",
        )
        cw2 = FrameworkCrosswalkMapping(
            source_subcategory_id=src_subcat2.id,
            target_subcategory_id=target_subcat.id,
            mapping_type=MappingTypeEnum.SUPERSET,
            confidence_score=0.90,
            rationale="Candidate 2",
        )
        db.add_all([cw1, cw2])
        db.commit()

        overview, snapshot = HarmonizationService.calculate_framework_compliance_posture(
            db=db,
            organization_id=org_apex.id,
            framework_id=target_fw.id,
        )

        # Expected: Candidate 2 gives 81.0, Candidate 1 gives 70.0. Engine chooses 81.0!
        assert overview.total_subcategories == 1
        assert overview.crosswalk_covered_subcategories == 1
        assert overview.coverage_percentage == 100.0
        assert overview.compliance_health_score == 81.0
        assert snapshot.compliance_health_score == 81.0

    def test_confidence_threshold_boundaries_79_vs_80_vs_81(
        self, db: Session, org_apex, seeded_framework
    ):
        """Crosswalk confidence score boundary test: < 0.80 is rejected from coverage, >= 0.80 is included."""
        target_fw = Framework(identifier="BOUND-CONF-FW", name="Confidence Boundary Framework", version="1.0")
        db.add(target_fw)
        db.commit()

        fn = FrameworkFunction(framework_id=target_fw.id, identifier="B1", name="Bound Function")
        db.add(fn)
        db.commit()

        cat = FrameworkCategory(function_id=fn.id, identifier="B1.1", name="Bound Category")
        db.add(cat)
        db.commit()

        target_subcat79 = FrameworkSubcategory(category_id=cat.id, identifier="B1.1.79", title="Subcat 79", description="Desc")
        target_subcat80 = FrameworkSubcategory(category_id=cat.id, identifier="B1.1.80", title="Subcat 80", description="Desc")
        target_subcat81 = FrameworkSubcategory(category_id=cat.id, identifier="B1.1.81", title="Subcat 81", description="Desc")
        db.add_all([target_subcat79, target_subcat80, target_subcat81])
        db.commit()

        # Source control with 100.0 health
        src_subcat = seeded_framework.functions[0].categories[0].subcategories[0]
        src_ctrl = OrganizationControl(organization_id=org_apex.id, subcategory_id=src_subcat.id, status=ImplementationStatusEnum.IMPLEMENTED)
        db.add(src_ctrl)
        db.commit()

        snap = ControlHealthSnapshot(organization_id=org_apex.id, organization_control_id=src_ctrl.id, health_score=100.0)
        db.add(snap)
        db.commit()

        # Three mappings: 0.79, 0.80, 0.81
        cw79 = FrameworkCrosswalkMapping(source_subcategory_id=src_subcat.id, target_subcategory_id=target_subcat79.id, confidence_score=0.79, rationale="0.79")
        cw80 = FrameworkCrosswalkMapping(source_subcategory_id=src_subcat.id, target_subcategory_id=target_subcat80.id, confidence_score=0.80, rationale="0.80")
        cw81 = FrameworkCrosswalkMapping(source_subcategory_id=src_subcat.id, target_subcategory_id=target_subcat81.id, confidence_score=0.81, rationale="0.81")
        db.add_all([cw79, cw80, cw81])
        db.commit()

        overview, snapshot = HarmonizationService.calculate_framework_compliance_posture(
            db=db,
            organization_id=org_apex.id,
            framework_id=target_fw.id,
        )

        # 3 total subcategories
        # 0.79 is below threshold -> NOT covered
        # 0.80 and 0.81 are >= 0.80 -> covered (2 covered out of 3 = 66.7%)
        assert overview.total_subcategories == 3
        assert overview.crosswalk_covered_subcategories == 2
        assert overview.coverage_percentage == 66.7
        # Effective health = (0.0 + 80.0 + 81.0) / 3 = 161.0 / 3 = 53.666... -> 53.7
        assert overview.compliance_health_score == 53.7

    def test_ccm_health_threshold_boundaries_59_9_vs_60_0_vs_60_1(
        self, db: Session, org_apex, seeded_framework
    ):
        """Source control health boundary test: < 60.0 does not qualify for direct or inherited coverage, >= 60.0 qualifies."""
        target_fw = Framework(identifier="BOUND-HEALTH-FW", name="Health Boundary Framework", version="1.0")
        db.add(target_fw)
        db.commit()

        fn = FrameworkFunction(framework_id=target_fw.id, identifier="H1", name="Health Bound Function")
        db.add(fn)
        db.commit()

        cat = FrameworkCategory(function_id=fn.id, identifier="H1.1", name="Health Bound Category")
        db.add(cat)
        db.commit()

        # Three target subcategories
        target_subcat1 = FrameworkSubcategory(category_id=cat.id, identifier="H1.1.1", title="Direct 59.9", description="Desc")
        target_subcat2 = FrameworkSubcategory(category_id=cat.id, identifier="H1.1.2", title="Direct 60.0", description="Desc")
        target_subcat3 = FrameworkSubcategory(category_id=cat.id, identifier="H1.1.3", title="Direct 60.1", description="Desc")
        db.add_all([target_subcat1, target_subcat2, target_subcat3])
        db.commit()

        # Three direct controls
        ctrl1 = OrganizationControl(organization_id=org_apex.id, subcategory_id=target_subcat1.id, status=ImplementationStatusEnum.IMPLEMENTED)
        ctrl2 = OrganizationControl(organization_id=org_apex.id, subcategory_id=target_subcat2.id, status=ImplementationStatusEnum.IMPLEMENTED)
        ctrl3 = OrganizationControl(organization_id=org_apex.id, subcategory_id=target_subcat3.id, status=ImplementationStatusEnum.IMPLEMENTED)
        db.add_all([ctrl1, ctrl2, ctrl3])
        db.commit()

        # Snapshots: 59.9 (Fails), 60.0 (Passes), 60.1 (Passes)
        snap1 = ControlHealthSnapshot(organization_id=org_apex.id, organization_control_id=ctrl1.id, health_score=59.9)
        snap2 = ControlHealthSnapshot(organization_id=org_apex.id, organization_control_id=ctrl2.id, health_score=60.0)
        snap3 = ControlHealthSnapshot(organization_id=org_apex.id, organization_control_id=ctrl3.id, health_score=60.1)
        db.add_all([snap1, snap2, snap3])
        db.commit()

        overview, snapshot = HarmonizationService.calculate_framework_compliance_posture(
            db=db,
            organization_id=org_apex.id,
            framework_id=target_fw.id,
        )

        # 3 total subcategories
        # 59.9 is not covered because < 60.0
        # 60.0 and 60.1 are directly covered (2 / 3 = 66.7%)
        assert overview.total_subcategories == 3
        assert overview.directly_covered_subcategories == 2
        assert overview.coverage_percentage == 66.7
        # Effective health = (0.0 + 60.0 + 60.1) / 3 = 120.1 / 3 = 40.0333... -> 40.0
        assert overview.compliance_health_score == 40.0
