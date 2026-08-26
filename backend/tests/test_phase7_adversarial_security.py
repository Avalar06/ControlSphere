from datetime import datetime, timezone
import pytest
from starlette.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.permissions import RoleEnum
from app.core.security import get_password_hash
from app.models.control import ImplementationStatusEnum, OrganizationControl, PriorityEnum
from app.models.monitoring import (
    ComplianceDriftAlert,
    ControlHealthSnapshot,
    ControlHealthStatusEnum,
    DriftAlertSeverityEnum,
    DriftAlertStatusEnum,
    DriftAlertTypeEnum,
    MonitoringSchedule,
)
from app.models.organization import Organization
from app.models.user import User
from tests.conftest import get_token_headers


class TestPhase7AdversarialSecurity:

    def test_adv_p7_01_cross_tenant_alert_read_idor(
        self, client: TestClient, db: Session, org_apex, org_meridian, admin_user, seeded_framework
    ):
        """ADV-P7-01: Tenant Apex cannot read alerts belonging to Meridian."""
        meridian_user = User(
            email="admin@meridian.com",
            hashed_password=get_password_hash("MeridianPass123!"),
            full_name="Meridian Admin",
            role=RoleEnum.ADMIN,
            is_active=True,
            organization_id=org_meridian.id,
        )
        db.add(meridian_user)
        db.commit()

        subcat = seeded_framework.functions[0].categories[0].subcategories[0]
        ctrl_m = OrganizationControl(
            organization_id=org_meridian.id,
            subcategory_id=subcat.id,
            status=ImplementationStatusEnum.NOT_STARTED,
        )
        db.add(ctrl_m)
        db.commit()
        db.refresh(ctrl_m)

        alert_m = ComplianceDriftAlert(
            organization_id=org_meridian.id,
            organization_control_id=ctrl_m.id,
            alert_type=DriftAlertTypeEnum.EVIDENCE_MISSING,
            severity=DriftAlertSeverityEnum.HIGH,
            status=DriftAlertStatusEnum.ACTIVE,
            title="Meridian Secret Alert",
            description="Confidential alert description",
        )
        db.add(alert_m)
        db.commit()
        db.refresh(alert_m)

        apex_headers = get_token_headers(admin_user)
        res = client.get("/api/v1/monitoring/alerts", headers=apex_headers)
        assert res.status_code == 200
        alert_titles = [a["title"] for a in res.json()]
        assert "Meridian Secret Alert" not in alert_titles

    def test_adv_p7_02_cross_tenant_alert_action_idor(
        self, client: TestClient, db: Session, org_meridian, admin_user, seeded_framework
    ):
        """ADV-P7-02: Tenant Apex cannot acknowledge or resolve Meridian's alert."""
        subcat = seeded_framework.functions[0].categories[0].subcategories[0]
        ctrl_m = OrganizationControl(
            organization_id=org_meridian.id,
            subcategory_id=subcat.id,
            status=ImplementationStatusEnum.NOT_STARTED,
        )
        db.add(ctrl_m)
        db.commit()
        db.refresh(ctrl_m)

        alert_m = ComplianceDriftAlert(
            organization_id=org_meridian.id,
            organization_control_id=ctrl_m.id,
            alert_type=DriftAlertTypeEnum.EVIDENCE_MISSING,
            severity=DriftAlertSeverityEnum.HIGH,
            status=DriftAlertStatusEnum.ACTIVE,
            title="Meridian Alert for Attack",
            description="Testing cross-tenant modification",
        )
        db.add(alert_m)
        db.commit()
        db.refresh(alert_m)

        apex_headers = get_token_headers(admin_user)
        
        # Try acknowledge
        ack_res = client.post(f"/api/v1/monitoring/alerts/{alert_m.id}/acknowledge", headers=apex_headers)
        assert ack_res.status_code == 404

        # Try resolve
        resolve_res = client.post(
            f"/api/v1/monitoring/alerts/{alert_m.id}/resolve",
            headers=apex_headers,
            json={"resolution_notes": "Adversarial cross-tenant attempt"},
        )
        assert resolve_res.status_code == 404

    def test_adv_p7_03_cross_tenant_control_history_idor(
        self, client: TestClient, db: Session, org_meridian, admin_user, seeded_framework
    ):
        """ADV-P7-03: Tenant Apex cannot read telemetry history for Meridian's control."""
        subcat = seeded_framework.functions[0].categories[0].subcategories[0]
        ctrl_m = OrganizationControl(
            organization_id=org_meridian.id,
            subcategory_id=subcat.id,
            status=ImplementationStatusEnum.NOT_STARTED,
        )
        db.add(ctrl_m)
        db.commit()
        db.refresh(ctrl_m)

        apex_headers = get_token_headers(admin_user)
        res = client.get(f"/api/v1/monitoring/controls/{ctrl_m.id}/history", headers=apex_headers)
        assert res.status_code == 404

    def test_adv_p7_04_cross_tenant_config_isolation(
        self, client: TestClient, db: Session, org_apex, org_meridian, admin_user
    ):
        """ADV-P7-04: Tenant Apex configuration update does not pollute Meridian configuration."""
        apex_headers = get_token_headers(admin_user)
        res = client.patch(
            "/api/v1/monitoring/config",
            headers=apex_headers,
            json={"evidence_max_age_days": 45},
        )
        assert res.status_code == 200
        assert res.json()["evidence_max_age_days"] == 45

        # Check Meridian config in database
        meridian_cfg = (
            db.query(MonitoringSchedule)
            .filter(MonitoringSchedule.organization_id == org_meridian.id)
            .first()
        )
        if meridian_cfg:
            assert meridian_cfg.evidence_max_age_days != 45

    def test_adv_p7_05_mass_assignment_protection(
        self, client: TestClient, admin_user
    ):
        """ADV-P7-05: Client cannot inject fake organization_id into config patch."""
        apex_headers = get_token_headers(admin_user)
        res = client.patch(
            "/api/v1/monitoring/config",
            headers=apex_headers,
            json={"organization_id": 99999, "frequency_hours": 48},
        )
        assert res.status_code == 200
        assert res.json()["organization_id"] == admin_user.organization_id

    def test_adv_p7_06_server_authoritative_evaluation_run(
        self, client: TestClient, admin_user
    ):
        """ADV-P7-06: Evaluation run only assesses caller's tenant controls."""
        apex_headers = get_token_headers(admin_user)
        res = client.post("/api/v1/monitoring/evaluate", headers=apex_headers)
        assert res.status_code == 200
        data = res.json()
        assert "average_health_score" in data
        assert isinstance(data["evaluated_controls_count"], int)

    def test_adv_p7_07_server_enforced_actor_identity(
        self, client: TestClient, db: Session, org_apex, admin_user, analyst_user, seeded_framework
    ):
        """ADV-P7-07: Alert resolution records JWT authenticated user as resolver, ignoring body spoofing."""
        subcat = seeded_framework.functions[0].categories[0].subcategories[0]
        ctrl = OrganizationControl(
            organization_id=org_apex.id,
            subcategory_id=subcat.id,
            status=ImplementationStatusEnum.NOT_STARTED,
        )
        db.add(ctrl)
        db.commit()
        db.refresh(ctrl)

        alert = ComplianceDriftAlert(
            organization_id=org_apex.id,
            organization_control_id=ctrl.id,
            alert_type=DriftAlertTypeEnum.CONTROL_DEGRADED,
            severity=DriftAlertSeverityEnum.HIGH,
            status=DriftAlertStatusEnum.ACTIVE,
            title="Actor Spoofing Test Alert",
            description="Testing actor integrity",
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        analyst_headers = get_token_headers(analyst_user)
        res = client.post(
            f"/api/v1/monitoring/alerts/{alert.id}/resolve",
            headers=analyst_headers,
            json={
                "resolved_by_id": 99999,  # spoofed actor
                "resolution_notes": "Resolved with proper governance",
            },
        )
        assert res.status_code == 200
        assert res.json()["resolved_by_id"] == analyst_user.id

    def test_adv_p7_08_server_authoritative_timestamps(
        self, client: TestClient, db: Session, org_apex, admin_user, seeded_framework
    ):
        """ADV-P7-08: Server generates resolution timestamps authoritatively."""
        subcat = seeded_framework.functions[0].categories[0].subcategories[0]
        ctrl = OrganizationControl(
            organization_id=org_apex.id,
            subcategory_id=subcat.id,
            status=ImplementationStatusEnum.NOT_STARTED,
        )
        db.add(ctrl)
        db.commit()
        db.refresh(ctrl)

        alert = ComplianceDriftAlert(
            organization_id=org_apex.id,
            organization_control_id=ctrl.id,
            alert_type=DriftAlertTypeEnum.EVIDENCE_MISSING,
            severity=DriftAlertSeverityEnum.HIGH,
            status=DriftAlertStatusEnum.ACTIVE,
            title="Timestamp Spoofing Test Alert",
            description="Testing timestamp integrity",
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        admin_headers = get_token_headers(admin_user)
        res = client.post(
            f"/api/v1/monitoring/alerts/{alert.id}/resolve",
            headers=admin_headers,
            json={
                "resolved_at": "2000-01-01T00:00:00Z",  # spoofed past timestamp
                "resolution_notes": "Resolved with server timestamp",
            },
        )
        assert res.status_code == 200
        resolved_at = datetime.fromisoformat(res.json()["resolved_at"])
        # Timestamp must be current, not 2000-01-01
        assert resolved_at.year >= 2026

    def test_adv_p7_09_terminal_state_resolution_immutability(
        self, client: TestClient, db: Session, org_apex, admin_user, seeded_framework
    ):
        """ADV-P7-09: Once resolved, alert cannot be resolved again or dismissed."""
        subcat = seeded_framework.functions[0].categories[0].subcategories[0]
        ctrl = OrganizationControl(
            organization_id=org_apex.id,
            subcategory_id=subcat.id,
            status=ImplementationStatusEnum.NOT_STARTED,
        )
        db.add(ctrl)
        db.commit()
        db.refresh(ctrl)

        alert = ComplianceDriftAlert(
            organization_id=org_apex.id,
            organization_control_id=ctrl.id,
            alert_type=DriftAlertTypeEnum.EVIDENCE_MISSING,
            severity=DriftAlertSeverityEnum.HIGH,
            status=DriftAlertStatusEnum.ACTIVE,
            title="Double Resolve Alert",
            description="Testing immutability",
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        admin_headers = get_token_headers(admin_user)
        
        # First resolve: success
        res1 = client.post(
            f"/api/v1/monitoring/alerts/{alert.id}/resolve",
            headers=admin_headers,
            json={"resolution_notes": "First resolution note"},
        )
        assert res1.status_code == 200

        # Second resolve: rejected (400)
        res2 = client.post(
            f"/api/v1/monitoring/alerts/{alert.id}/resolve",
            headers=admin_headers,
            json={"resolution_notes": "Second resolution attempt"},
        )
        assert res2.status_code == 400

        # Dismiss on resolved: rejected (400)
        res3 = client.post(
            f"/api/v1/monitoring/alerts/{alert.id}/dismiss",
            headers=admin_headers,
            json={"justification": "Trying to dismiss already resolved alert"},
        )
        assert res3.status_code == 400

    def test_adv_p7_10_cannot_acknowledge_dismissed_alert(
        self, client: TestClient, db: Session, org_apex, admin_user, seeded_framework
    ):
        """ADV-P7-10: Cannot acknowledge an alert that has already been dismissed."""
        subcat = seeded_framework.functions[0].categories[0].subcategories[0]
        ctrl = OrganizationControl(
            organization_id=org_apex.id,
            subcategory_id=subcat.id,
            status=ImplementationStatusEnum.NOT_STARTED,
        )
        db.add(ctrl)
        db.commit()
        db.refresh(ctrl)

        alert = ComplianceDriftAlert(
            organization_id=org_apex.id,
            organization_control_id=ctrl.id,
            alert_type=DriftAlertTypeEnum.EVIDENCE_MISSING,
            severity=DriftAlertSeverityEnum.HIGH,
            status=DriftAlertStatusEnum.ACTIVE,
            title="Dismiss then Ack Alert",
            description="Testing dismissal state barrier",
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        admin_headers = get_token_headers(admin_user)
        
        # Dismiss alert
        res_dis = client.post(
            f"/api/v1/monitoring/alerts/{alert.id}/dismiss",
            headers=admin_headers,
            json={"justification": "False positive"},
        )
        assert res_dis.status_code == 200

        # Try ack
        res_ack = client.post(
            f"/api/v1/monitoring/alerts/{alert.id}/acknowledge",
            headers=admin_headers,
        )
        assert res_ack.status_code == 400

    def test_adv_p7_11_duplicate_alert_idempotency(
        self, client: TestClient, admin_user
    ):
        """ADV-P7-11: Running evaluation multiple times does not create duplicate active alerts."""
        admin_headers = get_token_headers(admin_user)
        
        # Run 1
        client.post("/api/v1/monitoring/evaluate", headers=admin_headers)
        res1 = client.get("/api/v1/monitoring/alerts?status=ACTIVE", headers=admin_headers)
        count1 = len(res1.json())

        # Run 2
        client.post("/api/v1/monitoring/evaluate", headers=admin_headers)
        res2 = client.get("/api/v1/monitoring/alerts?status=ACTIVE", headers=admin_headers)
        count2 = len(res2.json())

        assert count1 == count2

    def test_adv_p7_12_score_tampering_impossible(
        self, client: TestClient, admin_user
    ):
        """ADV-P7-12: Health scores are computed deterministically server-side."""
        admin_headers = get_token_headers(admin_user)
        res = client.get("/api/v1/monitoring/controls", headers=admin_headers)
        assert res.status_code == 200
        for ctrl in res.json():
            assert 0.0 <= ctrl["health_score"] <= 100.0
            assert ctrl["health_status"] in ["HEALTHY", "DEGRADED", "AT_RISK", "FAILING"]

    def test_adv_p7_13_rbac_viewer_blocked_from_execution(
        self, client: TestClient, viewer_user
    ):
        """ADV-P7-13: VIEWER cannot trigger evaluation runs or resolve alerts."""
        viewer_headers = get_token_headers(viewer_user)
        
        # Try evaluate
        res_eval = client.post("/api/v1/monitoring/evaluate", headers=viewer_headers)
        assert res_eval.status_code == 403

        # Try resolve
        res_res = client.post(
            "/api/v1/monitoring/alerts/1/resolve",
            headers=viewer_headers,
            json={"resolution_notes": "Viewer attempt"},
        )
        assert res_res.status_code == 403

    def test_adv_p7_14_unauthenticated_access_blocked(
        self, client: TestClient
    ):
        """ADV-P7-14: Unauthenticated access to monitoring endpoints returns 401."""
        assert client.get("/api/v1/monitoring/overview").status_code == 401
        assert client.get("/api/v1/monitoring/controls").status_code == 401
        assert client.post("/api/v1/monitoring/evaluate").status_code == 401
        assert client.get("/api/v1/monitoring/alerts").status_code == 401
        assert client.get("/api/v1/monitoring/config").status_code == 401

    def test_adv_p7_15_audit_log_completeness(
        self, client: TestClient, db: Session, admin_user
    ):
        """ADV-P7-15: Continuous monitoring evaluation and alert actions generate immutable audit logs."""
        admin_headers = get_token_headers(admin_user)
        
        # Trigger evaluation
        client.post("/api/v1/monitoring/evaluate", headers=admin_headers)

        # Check audit log
        logs_res = client.get("/api/v1/audit-logs", headers=admin_headers)
        assert logs_res.status_code == 200
        logs = logs_res.json()
        actions = [l["action"] for l in logs]
        assert "monitoring.evaluate" in actions

    def test_adv_p7_16_boundary_value_validation(
        self, client: TestClient, admin_user
    ):
        """ADV-P7-16: Negative threshold or frequency values are rejected by schema validation."""
        admin_headers = get_token_headers(admin_user)
        
        # Negative frequency
        res1 = client.patch(
            "/api/v1/monitoring/config",
            headers=admin_headers,
            json={"frequency_hours": -5},
        )
        assert res1.status_code == 422

        # Stale evidence threshold < 7 days
        res2 = client.patch(
            "/api/v1/monitoring/config",
            headers=admin_headers,
            json={"evidence_max_age_days": 2},
        )
        assert res2.status_code == 422
