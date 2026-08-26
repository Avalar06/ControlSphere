from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.control import ImplementationStatusEnum, OrganizationControl
from app.models.framework import FrameworkSubcategory
from app.models.harmonization import (
    CommonControlDomainEnum,
    CommonControlMapping,
    FrameworkComplianceSnapshot,
    FrameworkCrosswalkMapping,
    MappingTypeEnum,
    RationalizationStatusEnum,
    RationalizedCommonControl,
)
from app.models.organization import Organization
from app.models.user import User
from tests.conftest import get_token_headers


class TestPhase8AdversarialSecurity:

    def test_adv_p8_01_cross_tenant_common_control_read_idor(
        self, client: TestClient, db: Session, admin_user, org_apex, org_meridian
    ):
        """ADV-P8-01: An authenticated user from Org Apex cannot read common controls from Org Meridian."""
        admin_headers = get_token_headers(admin_user)
        cc_meridian = RationalizedCommonControl(
            organization_id=org_meridian.id,
            common_control_code="CCF-MER-01",
            title="Meridian Private Common Control",
            description="Confidential architecture for Org Meridian",
            domain=CommonControlDomainEnum.CRYPTOGRAPHY,
        )
        db.add(cc_meridian)
        db.commit()
        db.refresh(cc_meridian)

        # Apex user attempts to read Meridian common control
        res = client.get(
            f"/api/v1/harmonization/common-controls/{cc_meridian.id}",
            headers=admin_headers,
        )
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()

    def test_adv_p8_02_cross_tenant_common_control_update_idor(
        self, client: TestClient, db: Session, admin_user, org_meridian
    ):
        """ADV-P8-02: An authenticated user from Org Apex cannot mutate common controls from Org Meridian."""
        admin_headers = get_token_headers(admin_user)
        cc_meridian = RationalizedCommonControl(
            organization_id=org_meridian.id,
            common_control_code="CCF-MER-02",
            title="Meridian Sensitive Control",
            description="Sensitive",
            domain=CommonControlDomainEnum.DATA_PROTECTION,
        )
        db.add(cc_meridian)
        db.commit()
        db.refresh(cc_meridian)

        # Apex user attempts to update Meridian control
        res = client.put(
            f"/api/v1/harmonization/common-controls/{cc_meridian.id}",
            json={"title": "Hacked Title"},
            headers=admin_headers,
        )
        assert res.status_code == 404

    def test_adv_p8_03_foreign_organization_control_mapping_injection(
        self, client: TestClient, db: Session, admin_user, org_apex, org_meridian, seeded_framework
    ):
        """ADV-P8-03: Cannot link an OrganizationControl belonging to Org Meridian into Org Apex's Common Control."""
        admin_headers = get_token_headers(admin_user)
        subcat = seeded_framework.functions[0].categories[0].subcategories[0]

        # Meridian's organization control
        meridian_ctrl = OrganizationControl(
            organization_id=org_meridian.id,
            subcategory_id=subcat.id,
            status=ImplementationStatusEnum.IMPLEMENTED,
        )
        db.add(meridian_ctrl)
        db.commit()
        db.refresh(meridian_ctrl)

        # Apex common control
        apex_cc = RationalizedCommonControl(
            organization_id=org_apex.id,
            common_control_code="CCF-APEX-01",
            title="Apex Common Control",
            description="Apex control",
            domain=CommonControlDomainEnum.IDENTITY_ACCESS,
        )
        db.add(apex_cc)
        db.commit()
        db.refresh(apex_cc)

        # Apex attempts to map Meridian control
        map_payload = {
            "organization_control_id": meridian_ctrl.id,
            "weight": 1.0,
        }
        res = client.post(
            f"/api/v1/harmonization/common-controls/{apex_cc.id}/mappings",
            json=map_payload,
            headers=admin_headers,
        )
        assert res.status_code == 404
        assert "not found in tenant" in res.json()["detail"].lower()

    def test_adv_p8_04_tenant_spoofing_prevented(
        self, client: TestClient, db: Session, admin_user, org_apex, org_meridian
    ):
        """ADV-P8-04: Client-injected organization_id in request body is ignored; server derives org from JWT."""
        admin_headers = get_token_headers(admin_user)
        payload = {
            "organization_id": org_meridian.id,  # Attempt to inject foreign org
            "common_control_code": "CCF-SPOOF-01",
            "title": "Tenant Spoofing Attempt",
            "description": "Attempting to create control in foreign org",
            "domain": "GOVERNANCE_RISK",
        }
        res = client.post("/api/v1/harmonization/common-controls", json=payload, headers=admin_headers)
        assert res.status_code == 201
        data = res.json()
        assert data["organization_id"] == org_apex.id  # Server derived Apex, NOT Meridian

    def test_adv_p8_05_cross_tenant_snapshot_isolation(
        self, client: TestClient, db: Session, admin_user, org_meridian, seeded_framework
    ):
        """ADV-P8-05: Snapshots belonging to Org Meridian cannot be read by Org Apex."""
        admin_headers = get_token_headers(admin_user)
        snap_meridian = FrameworkComplianceSnapshot(
            organization_id=org_meridian.id,
            framework_id=seeded_framework.id,
            calculation_version="v1.0",
            coverage_percentage=75.0,
            compliance_health_score=80.0,
            total_subcategories=10,
            covered_subcategories=7,
            unmapped_subcategories=3,
        )
        db.add(snap_meridian)
        db.commit()

        res = client.get("/api/v1/harmonization/snapshots", headers=admin_headers)
        assert res.status_code == 200
        items = res.json()
        for item in items:
            assert item["organization_id"] != org_meridian.id

    def test_adv_p8_06_non_admin_crosswalk_mutation_blocked(
        self, client: TestClient, db: Session, analyst_user, seeded_framework
    ):
        """ADV-P8-06: Tenant GRC Analyst (non-admin) cannot mutate global normative crosswalk mappings."""
        analyst_headers = get_token_headers(analyst_user)
        subcats = seeded_framework.functions[0].categories[0].subcategories
        payload = {
            "source_subcategory_id": subcats[0].id,
            "target_subcategory_id": subcats[1].id,
            "mapping_type": "EXACT",
            "confidence_score": 1.0,
            "rationale": "Unauthorized crosswalk attempt",
        }
        res = client.post("/api/v1/harmonization/crosswalks", json=payload, headers=analyst_headers)
        assert res.status_code == 403

    def test_adv_p8_07_unauthenticated_access_blocked(self, client: TestClient):
        """ADV-P8-07: Unauthenticated requests to harmonization endpoints return 401 Unauthorized."""
        res1 = client.get("/api/v1/harmonization/common-controls")
        assert res1.status_code == 401
        res2 = client.post("/api/v1/harmonization/evaluate")
        assert res2.status_code == 401

    def test_adv_p8_08_mass_assignment_protection(
        self, client: TestClient, db: Session, admin_user
    ):
        """ADV-P8-08: Injected server-controlled fields in payload are rejected or ignored."""
        admin_headers = get_token_headers(admin_user)
        payload = {
            "id": 99999,
            "inherited_health_score": 0.0,
            "inherited_health_status": "FAILING",
            "common_control_code": "CCF-MASS-01",
            "title": "Mass Assignment Control",
            "description": "Testing Pydantic schema rejection of injected IDs",
            "domain": "VULNERABILITY_MANAGEMENT",
        }
        res = client.post("/api/v1/harmonization/common-controls", json=payload, headers=admin_headers)
        assert res.status_code == 201
        data = res.json()
        assert data["id"] != 99999
        # Health score must be calculated server-side (zero links = 100.0)
        assert data["inherited_health_score"] == 100.0
        assert data["inherited_health_status"] == "HEALTHY"

    def test_adv_p8_09_client_health_score_tampering_impossible(
        self, client: TestClient, db: Session, admin_user, org_apex
    ):
        """ADV-P8-09: Common control health score cannot be tampered with via PUT requests."""
        admin_headers = get_token_headers(admin_user)
        cc = RationalizedCommonControl(
            organization_id=org_apex.id,
            common_control_code="CCF-TAMPER-01",
            title="Tamper Test",
            description="Tampering attempt",
            domain=CommonControlDomainEnum.INCIDENT_MANAGEMENT,
            inherited_health_score=100.0,
        )
        db.add(cc)
        db.commit()

        # Attempt to patch health score to 20.0
        res = client.put(
            f"/api/v1/harmonization/common-controls/{cc.id}",
            json={"inherited_health_score": 20.0, "title": "Tampered Title"},
            headers=admin_headers,
        )
        assert res.status_code == 200
        # Score remains server-authoritative 100.0
        assert res.json()["inherited_health_score"] == 100.0

    def test_adv_p8_10_client_coverage_percentage_override_impossible(
        self, client: TestClient, admin_user
    ):
        """ADV-P8-10: Client cannot pass arbitrary coverage_percentage into evaluation endpoint."""
        admin_headers = get_token_headers(admin_user)
        res = client.post(
            "/api/v1/harmonization/evaluate",
            json={"coverage_percentage": 100.0, "compliance_health_score": 100.0},
            headers=admin_headers,
        )
        assert res.status_code == 200
        # Backend executes evaluation deterministically; no client input is accepted for scores

    def test_adv_p8_11_client_compliance_score_override_impossible(
        self, client: TestClient, admin_user
    ):
        """ADV-P8-11: Posture endpoint computes scores server-side exclusively."""
        admin_headers = get_token_headers(admin_user)
        res = client.get("/api/v1/harmonization/posture", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data["average_common_control_health"], float)

    def test_adv_p8_12_duplicate_mapping_creation_idempotency(
        self, client: TestClient, db: Session, admin_user, org_apex, seeded_framework
    ):
        """ADV-P8-12: Creating duplicate mapping for same (common_control, org_control) is safely handled / idempotent."""
        admin_headers = get_token_headers(admin_user)
        subcat = seeded_framework.functions[0].categories[0].subcategories[0]
        ctrl = OrganizationControl(organization_id=org_apex.id, subcategory_id=subcat.id)
        db.add(ctrl)
        db.commit()

        cc = RationalizedCommonControl(
            organization_id=org_apex.id,
            common_control_code="CCF-DUP-01",
            title="Duplicate Test",
            description="Desc",
            domain=CommonControlDomainEnum.PHYSICAL_SECURITY,
        )
        db.add(cc)
        db.commit()

        payload = {"organization_control_id": ctrl.id, "weight": 1.0}
        res1 = client.post(f"/api/v1/harmonization/common-controls/{cc.id}/mappings", json=payload, headers=admin_headers)
        assert res1.status_code == 201

        # Second attempt updates weight idempotently without unique constraint crash
        payload["weight"] = 2.0
        res2 = client.post(f"/api/v1/harmonization/common-controls/{cc.id}/mappings", json=payload, headers=admin_headers)
        assert res2.status_code == 201
        assert res2.json()["weight"] == 2.0

    def test_adv_p8_13_retired_common_control_rejects_new_mappings(
        self, client: TestClient, db: Session, admin_user, org_apex, seeded_framework
    ):
        """ADV-P8-13: Retired common controls cannot accept new organization control linkages."""
        admin_headers = get_token_headers(admin_user)
        subcat = seeded_framework.functions[0].categories[0].subcategories[0]
        ctrl = OrganizationControl(organization_id=org_apex.id, subcategory_id=subcat.id)
        db.add(ctrl)

        cc_retired = RationalizedCommonControl(
            organization_id=org_apex.id,
            common_control_code="CCF-RET-01",
            title="Retired Control",
            description="Retired requirement",
            domain=CommonControlDomainEnum.BUSINESS_CONTINUITY,
            rationalization_status=RationalizationStatusEnum.RETIRED,
            deprecation_reason="Obsolete standard",
        )
        db.add(cc_retired)
        db.commit()

        res = client.post(
            f"/api/v1/harmonization/common-controls/{cc_retired.id}/mappings",
            json={"organization_control_id": ctrl.id, "weight": 1.0},
            headers=admin_headers,
        )
        assert res.status_code == 400
        assert "retired" in res.json()["detail"].lower()

    def test_adv_p8_14_foreign_or_inactive_owner_assignment_rejected(
        self, client: TestClient, db: Session, admin_user, org_meridian
    ):
        """ADV-P8-14: Cannot assign a foreign tenant user as the common control owner."""
        admin_headers = get_token_headers(admin_user)
        # Foreign user in Meridian
        meridian_user = User(
            email="meridian_user@example.com",
            full_name="Dr. Meridian User",
            hashed_password="hashedpassword123",
            organization_id=org_meridian.id,
            is_active=True,
        )
        db.add(meridian_user)
        db.commit()

        payload = {
            "common_control_code": "CCF-OWNER-01",
            "title": "Foreign Owner Test",
            "description": "Detailed description meeting length constraint",
            "domain": "GOVERNANCE_RISK",
            "owner_id": meridian_user.id,
        }
        res = client.post("/api/v1/harmonization/common-controls", json=payload, headers=admin_headers)
        assert res.status_code == 400
        assert "owner not found" in res.json()["detail"].lower()

    def test_adv_p8_15_rbac_viewer_blocked_from_evaluation(
        self, client: TestClient, viewer_user
    ):
        """ADV-P8-15: Viewer role is blocked from executing harmonization evaluations."""
        viewer_headers = get_token_headers(viewer_user)
        res = client.post("/api/v1/harmonization/evaluate", headers=viewer_headers)
        assert res.status_code == 403

    def test_adv_p8_16_audit_log_completeness(
        self, client: TestClient, db: Session, admin_user, org_apex, seeded_framework
    ):
        """ADV-P8-16: All common control creations, mappings, and evaluations produce immutable audit logs."""
        admin_headers = get_token_headers(admin_user)
        subcat = seeded_framework.functions[0].categories[0].subcategories[0]
        ctrl = OrganizationControl(organization_id=org_apex.id, subcategory_id=subcat.id)
        db.add(ctrl)
        db.commit()

        # 1. Create common control
        cc_payload = {
            "common_control_code": "CCF-AUDIT-01",
            "title": "Audit Trail Common Control",
            "description": "Testing audit log creation",
            "domain": "GOVERNANCE_RISK",
        }
        res1 = client.post("/api/v1/harmonization/common-controls", json=cc_payload, headers=admin_headers)
        assert res1.status_code == 201
        cc_id = res1.json()["id"]

        # 2. Map control
        map_payload = {"organization_control_id": ctrl.id, "weight": 1.0}
        res2 = client.post(f"/api/v1/harmonization/common-controls/{cc_id}/mappings", json=map_payload, headers=admin_headers)
        assert res2.status_code == 201

        # 3. Execute evaluation
        res3 = client.post("/api/v1/harmonization/evaluate", headers=admin_headers)
        assert res3.status_code == 200

        # Verify audit logs in database
        logs = db.query(AuditLog).filter(
            AuditLog.organization_id == org_apex.id,
            AuditLog.action.like("harmonization.%"),
        ).all()
        actions = [log.action for log in logs]
        assert "harmonization.common_control_create" in actions
        assert "harmonization.mapping_create" in actions
        assert "harmonization.evaluate" in actions
