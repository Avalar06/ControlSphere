from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.control import ImplementationStatusEnum, OrganizationControl
from app.models.framework import FrameworkSubcategory
from app.models.harmonization import (
    CommonControlDomainEnum,
    CommonControlMapping,
    FrameworkCrosswalkMapping,
    RationalizationStatusEnum,
    RationalizedCommonControl,
)
from tests.conftest import get_token_headers


class TestHarmonizationLifecycle:

    def test_list_and_create_crosswalks(self, client: TestClient, db: Session, admin_user, seeded_framework):
        """Admin can list and create global normative crosswalk mappings."""
        admin_headers = get_token_headers(admin_user)
        subcats = seeded_framework.functions[0].categories[0].subcategories
        subcat1 = subcats[0]
        subcat2 = subcats[1]

        # 1. Create crosswalk
        payload = {
            "source_subcategory_id": subcat1.id,
            "target_subcategory_id": subcat2.id,
            "mapping_type": "EXACT",
            "confidence_score": 1.0,
            "bidirectional": True,
            "rationale": "Direct operational alignment",
        }
        res = client.post("/api/v1/harmonization/crosswalks", json=payload, headers=admin_headers)
        assert res.status_code == 201
        data = res.json()
        assert data["source_subcategory_id"] == subcat1.id
        assert data["target_subcategory_id"] == subcat2.id
        assert data["confidence_score"] == 1.0

        # 2. List crosswalks
        res_list = client.get("/api/v1/harmonization/crosswalks", headers=admin_headers)
        assert res_list.status_code == 200
        items = res_list.json()
        assert len(items) >= 1

    def test_common_control_crud_lifecycle(self, client: TestClient, db: Session, admin_user):
        """Full CRUD on rationalized common controls with code uniqueness enforcement."""
        admin_headers = get_token_headers(admin_user)

        # 1. Create common control
        create_payload = {
            "common_control_code": "CCF-CRYPTO-01",
            "title": "Data-at-Rest & In-Transit Cryptography",
            "description": "Standardized enterprise cryptographic controls",
            "domain": "CRYPTOGRAPHY",
            "rationalization_status": "ACTIVE",
            "owner_id": admin_user.id,
        }
        res = client.post("/api/v1/harmonization/common-controls", json=create_payload, headers=admin_headers)
        assert res.status_code == 201
        cc_id = res.json()["id"]
        assert res.json()["common_control_code"] == "CCF-CRYPTO-01"
        assert res.json()["inherited_health_score"] == 100.0  # Zero links = 100.0

        # 2. Duplicate code in same org rejected
        dup_res = client.post("/api/v1/harmonization/common-controls", json=create_payload, headers=admin_headers)
        assert dup_res.status_code == 409

        # 3. Update common control
        update_payload = {
            "title": "Data Cryptography Standard",
            "rationalization_status": "RETIRED",
            "deprecation_reason": "Superseded by CCF-CRYPTO-02",
        }
        update_res = client.put(f"/api/v1/harmonization/common-controls/{cc_id}", json=update_payload, headers=admin_headers)
        assert update_res.status_code == 200
        assert update_res.json()["title"] == "Data Cryptography Standard"
        assert update_res.json()["rationalization_status"] == "RETIRED"

    def test_mapping_lifecycle_and_health_recalculation(
        self, client: TestClient, db: Session, admin_user, org_apex, seeded_framework
    ):
        """Mapping and unmapping organization controls dynamically recalculates common control health."""
        admin_headers = get_token_headers(admin_user)
        subcat = seeded_framework.functions[0].categories[0].subcategories[0]
        ctrl = OrganizationControl(
            organization_id=org_apex.id,
            subcategory_id=subcat.id,
            status=ImplementationStatusEnum.IMPLEMENTED,
        )
        db.add(ctrl)
        db.commit()
        db.refresh(ctrl)

        # Create common control
        cc = RationalizedCommonControl(
            organization_id=org_apex.id,
            common_control_code="CCF-MAP-01",
            title="Mapped Test Control",
            description="Testing mapping workflow",
            domain=CommonControlDomainEnum.GOVERNANCE_RISK,
        )
        db.add(cc)
        db.commit()
        db.refresh(cc)

        # 1. Map control
        map_payload = {
            "organization_control_id": ctrl.id,
            "weight": 1.5,
        }
        map_res = client.post(
            f"/api/v1/harmonization/common-controls/{cc.id}/mappings",
            json=map_payload,
            headers=admin_headers,
        )
        assert map_res.status_code == 201
        assert map_res.json()["organization_control_id"] == ctrl.id

        # 2. Get detail with mappings
        detail_res = client.get(
            f"/api/v1/harmonization/common-controls/{cc.id}",
            headers=admin_headers,
        )
        assert detail_res.status_code == 200
        assert detail_res.json()["mapped_controls_count"] == 1
        assert len(detail_res.json()["mappings"]) == 1

        # 3. Unmap control
        unmap_res = client.delete(
            f"/api/v1/harmonization/common-controls/{cc.id}/mappings/{ctrl.id}",
            headers=admin_headers,
        )
        assert unmap_res.status_code == 204

    def test_evaluate_and_posture_endpoints(self, client: TestClient, db: Session, admin_user, seeded_framework):
        """Evaluation endpoint executes multi-framework calculation and creates immutable snapshots."""
        admin_headers = get_token_headers(admin_user)

        # 1. Trigger evaluation
        eval_res = client.post("/api/v1/harmonization/evaluate", headers=admin_headers)
        assert eval_res.status_code == 200
        eval_data = eval_res.json()
        assert eval_data["evaluated_frameworks"] >= 1
        assert eval_data["snapshots_created"] >= 1

        # 2. Query posture overview
        posture_res = client.get("/api/v1/harmonization/posture", headers=admin_headers)
        assert posture_res.status_code == 200
        posture_data = posture_res.json()
        assert len(posture_data["frameworks"]) >= 1
        assert "coverage_percentage" in posture_data["frameworks"][0]
        assert "compliance_health_score" in posture_data["frameworks"][0]

        # 3. Query historical snapshots
        snap_res = client.get("/api/v1/harmonization/snapshots", headers=admin_headers)
        assert snap_res.status_code == 200
        snaps = snap_res.json()
        assert len(snaps) >= 1
        assert snaps[0]["calculation_version"] == "v1.0"
