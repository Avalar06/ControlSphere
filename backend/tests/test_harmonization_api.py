from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.control import ImplementationStatusEnum, OrganizationControl
from app.models.framework import FrameworkSubcategory
from app.models.harmonization import (
    CommonControlDomainEnum,
    CommonControlMapping,
    RationalizationStatusEnum,
    RationalizedCommonControl,
)
from tests.conftest import get_token_headers


class TestHarmonizationAPI:

    def test_common_control_filter_by_domain_and_status(
        self, client: TestClient, db: Session, admin_user, org_apex
    ):
        """Common controls can be filtered by domain and status."""
        admin_headers = get_token_headers(admin_user)

        cc1 = RationalizedCommonControl(
            organization_id=org_apex.id,
            common_control_code="CCF-IAM-10",
            title="IAM Control",
            description="Identity and access control",
            domain=CommonControlDomainEnum.IDENTITY_ACCESS,
            rationalization_status=RationalizationStatusEnum.ACTIVE,
        )
        cc2 = RationalizedCommonControl(
            organization_id=org_apex.id,
            common_control_code="CCF-CRYPTO-10",
            title="Crypto Control",
            description="Cryptographic standard",
            domain=CommonControlDomainEnum.CRYPTOGRAPHY,
            rationalization_status=RationalizationStatusEnum.RETIRED,
            deprecation_reason="Replaced",
        )
        db.add_all([cc1, cc2])
        db.commit()

        # Filter by domain
        res_iam = client.get("/api/v1/harmonization/common-controls?domain=IDENTITY_ACCESS", headers=admin_headers)
        assert res_iam.status_code == 200
        items = res_iam.json()
        assert len(items) == 1
        assert items[0]["common_control_code"] == "CCF-IAM-10"

        # Filter by status
        res_retired = client.get("/api/v1/harmonization/common-controls?status=RETIRED", headers=admin_headers)
        assert res_retired.status_code == 200
        items_ret = res_retired.json()
        assert len(items_ret) == 1
        assert items_ret[0]["common_control_code"] == "CCF-CRYPTO-10"

    def test_common_control_patch_endpoint(
        self, client: TestClient, db: Session, admin_user, org_apex
    ):
        """PATCH updates individual common control attributes."""
        admin_headers = get_token_headers(admin_user)
        cc = RationalizedCommonControl(
            organization_id=org_apex.id,
            common_control_code="CCF-PATCH-01",
            title="Original Title",
            description="Original Description",
            domain=CommonControlDomainEnum.GOVERNANCE_RISK,
        )
        db.add(cc)
        db.commit()

        patch_res = client.patch(
            f"/api/v1/harmonization/common-controls/{cc.id}",
            json={"title": "Updated Title"},
            headers=admin_headers,
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["title"] == "Updated Title"
        assert patch_res.json()["description"] == "Original Description"

    def test_list_common_control_mappings_endpoint(
        self, client: TestClient, db: Session, admin_user, org_apex, seeded_framework
    ):
        """GET /common-controls/{id}/mappings returns linked organization controls."""
        admin_headers = get_token_headers(admin_user)
        subcat = seeded_framework.functions[0].categories[0].subcategories[0]
        ctrl = OrganizationControl(organization_id=org_apex.id, subcategory_id=subcat.id)
        db.add(ctrl)

        cc = RationalizedCommonControl(
            organization_id=org_apex.id,
            common_control_code="CCF-LIST-MAP-01",
            title="Mapping List Test",
            description="Testing listing mappings",
            domain=CommonControlDomainEnum.GOVERNANCE_RISK,
        )
        db.add(cc)
        db.commit()

        mapping = CommonControlMapping(
            organization_id=org_apex.id,
            rationalized_common_control_id=cc.id,
            organization_control_id=ctrl.id,
            weight=2.5,
        )
        db.add(mapping)
        db.commit()

        res = client.get(f"/api/v1/harmonization/common-controls/{cc.id}/mappings", headers=admin_headers)
        assert res.status_code == 200
        mappings = res.json()
        assert len(mappings) == 1
        assert mappings[0]["weight"] == 2.5
        assert mappings[0]["organization_control_id"] == ctrl.id

    def test_evaluate_single_framework_endpoint(
        self, client: TestClient, db: Session, admin_user, seeded_framework
    ):
        """POST /frameworks/{framework_id}/evaluate executes evaluation and returns snapshot."""
        admin_headers = get_token_headers(admin_user)
        res = client.post(
            f"/api/v1/harmonization/frameworks/{seeded_framework.id}/evaluate",
            headers=admin_headers,
        )
        assert res.status_code == 201
        data = res.json()
        assert data["framework_id"] == seeded_framework.id
        assert data["calculation_version"] == "v1.0"
        assert "coverage_percentage" in data
        assert "compliance_health_score" in data

    def test_framework_detailed_posture_endpoint(
        self, client: TestClient, db: Session, admin_user, seeded_framework
    ):
        """GET /frameworks/{framework_id}/posture returns detailed matrix breakdown."""
        admin_headers = get_token_headers(admin_user)
        res = client.get(
            f"/api/v1/harmonization/frameworks/{seeded_framework.id}/posture",
            headers=admin_headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert "overview" in data
        assert "subcategories" in data
        assert len(data["subcategories"]) > 0
        first_subcat = data["subcategories"][0]
        assert "subcategory_identifier" in first_subcat
        assert "is_directly_covered" in first_subcat
        assert "is_crosswalk_covered" in first_subcat
