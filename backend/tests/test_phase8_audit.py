from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.control import ImplementationStatusEnum, OrganizationControl
from app.models.framework import FrameworkSubcategory
from tests.conftest import get_token_headers


class TestPhase8Audit:

    def test_complete_harmonization_audit_trail(
        self, client: TestClient, db: Session, admin_user, org_apex, seeded_framework
    ):
        """Verify that all 9 Phase 8 audit events are recorded in the immutable audit log table."""
        admin_headers = get_token_headers(admin_user)
        subcats = seeded_framework.functions[0].categories[0].subcategories
        subcat1 = subcats[0]
        subcat2 = subcats[1]

        ctrl = OrganizationControl(organization_id=org_apex.id, subcategory_id=subcat1.id)
        db.add(ctrl)
        db.commit()

        # 1. CROSSWALK_CREATED
        cw_res = client.post(
            "/api/v1/harmonization/crosswalks",
            json={
                "source_subcategory_id": subcat1.id,
                "target_subcategory_id": subcat2.id,
                "mapping_type": "EXACT",
                "confidence_score": 1.0,
                "rationale": "Audit test crosswalk",
            },
            headers=admin_headers,
        )
        assert cw_res.status_code == 201
        cw_id = cw_res.json()["id"]

        # 2. CROSSWALK_UPDATED
        client.patch(
            f"/api/v1/harmonization/crosswalks/{cw_id}",
            json={"confidence_score": 0.95},
            headers=admin_headers,
        )

        # 3. COMMON_CONTROL_CREATED
        cc_res = client.post(
            "/api/v1/harmonization/common-controls",
            json={
                "common_control_code": "CCF-AUDIT-ALL-01",
                "title": "Audit Full Test",
                "description": "Verifying all audit events",
                "domain": "GOVERNANCE_RISK",
            },
            headers=admin_headers,
        )
        assert cc_res.status_code == 201
        cc_id = cc_res.json()["id"]

        # 4. COMMON_CONTROL_UPDATED
        client.patch(
            f"/api/v1/harmonization/common-controls/{cc_id}",
            json={"title": "Audit Full Test Updated"},
            headers=admin_headers,
        )

        # 5. COMMON_CONTROL_MAPPING_CREATED
        client.post(
            f"/api/v1/harmonization/common-controls/{cc_id}/mappings",
            json={"organization_control_id": ctrl.id, "weight": 1.0},
            headers=admin_headers,
        )

        # 6. COMMON_CONTROL_MAPPING_REMOVED
        client.delete(
            f"/api/v1/harmonization/common-controls/{cc_id}/mappings/{ctrl.id}",
            headers=admin_headers,
        )

        # 7. CROSSWALK_DELETED
        client.delete(
            f"/api/v1/harmonization/crosswalks/{cw_id}",
            headers=admin_headers,
        )

        # 8 & 9. FRAMEWORK_EVALUATION_EXECUTED and COMPLIANCE_SNAPSHOT_CREATED
        eval_res = client.post(
            f"/api/v1/harmonization/frameworks/{seeded_framework.id}/evaluate",
            headers=admin_headers,
        )
        assert eval_res.status_code == 201

        # Query and assert all 9 audit events
        logs = db.query(AuditLog).filter(
            AuditLog.organization_id == org_apex.id,
        ).all()
        actions = set(log.action for log in logs)

        expected_actions = {
            "CROSSWALK_CREATED",
            "CROSSWALK_UPDATED",
            "CROSSWALK_DELETED",
            "COMMON_CONTROL_CREATED",
            "COMMON_CONTROL_UPDATED",
            "COMMON_CONTROL_MAPPING_CREATED",
            "COMMON_CONTROL_MAPPING_REMOVED",
            "FRAMEWORK_EVALUATION_EXECUTED",
            "COMPLIANCE_SNAPSHOT_CREATED",
        }
        for exp in expected_actions:
            assert exp in actions, f"Expected audit action {exp} not found in audit logs: {actions}"
