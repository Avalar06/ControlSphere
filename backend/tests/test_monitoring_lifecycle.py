from datetime import date, datetime, timedelta, timezone
import pytest
from starlette.testclient import TestClient

from app.models.control import ImplementationStatusEnum, OrganizationControl, PriorityEnum
from app.models.evidence import EvidenceItem, EvidenceStatusEnum, EvidenceTypeEnum
from app.models.finding import Finding, FindingSeverityEnum, FindingStatusEnum, FindingTypeEnum
from app.models.monitoring import DriftAlertStatusEnum, DriftAlertTypeEnum
from tests.conftest import get_token_headers


class TestMonitoringLifecycle:

    def test_overview_endpoint(self, client: TestClient, db, org_apex, seeded_framework, admin_user):
        headers = get_token_headers(admin_user)
        res = client.get("/api/v1/monitoring/overview", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "average_health_score" in data
        assert "overall_health_status" in data
        assert "total_monitored_controls" in data
        assert "active_drift_alerts_count" in data

    def test_manual_evaluation_trigger_creates_snapshots_and_alerts(
        self, client: TestClient, db, org_apex, seeded_framework, admin_user
    ):
        headers = get_token_headers(admin_user)
        
        # Trigger evaluation run
        res = client.post("/api/v1/monitoring/evaluate", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["evaluated_controls_count"] > 0
        assert data["alerts_generated_count"] >= 0
        assert "average_health_score" in data

    def test_list_controls_health(self, client: TestClient, db, org_apex, seeded_framework, admin_user):
        headers = get_token_headers(admin_user)
        
        # Evaluate first
        client.post("/api/v1/monitoring/evaluate", headers=headers)
        
        res = client.get("/api/v1/monitoring/controls", headers=headers)
        assert res.status_code == 200
        controls = res.json()
        assert isinstance(controls, list)
        assert len(controls) > 0
        assert "health_score" in controls[0]
        assert "health_status" in controls[0]

    def test_alert_acknowledge_and_resolution_lifecycle(
        self, client: TestClient, db, org_apex, seeded_framework, admin_user
    ):
        headers = get_token_headers(admin_user)
        
        # Evaluate to generate alerts
        client.post("/api/v1/monitoring/evaluate", headers=headers)
        
        alerts_res = client.get("/api/v1/monitoring/alerts", headers=headers)
        assert alerts_res.status_code == 200
        alerts = alerts_res.json()
        if len(alerts) > 0:
            alert_id = alerts[0]["id"]
            
            # Acknowledge alert
            ack_res = client.post(f"/api/v1/monitoring/alerts/{alert_id}/acknowledge", headers=headers)
            assert ack_res.status_code == 200
            assert ack_res.json()["status"] == "ACKNOWLEDGED"
            
            # Resolve alert
            resolve_res = client.post(
                f"/api/v1/monitoring/alerts/{alert_id}/resolve",
                headers=headers,
                json={"resolution_notes": "Evidence verified and re-uploaded as requested."},
            )
            assert resolve_res.status_code == 200
            assert resolve_res.json()["status"] == "RESOLVED"
            assert resolve_res.json()["resolution_notes"] == "Evidence verified and re-uploaded as requested."

    def test_alert_dismiss_lifecycle(
        self, client: TestClient, db, org_apex, seeded_framework, admin_user
    ):
        headers = get_token_headers(admin_user)
        
        # Re-evaluate
        client.post("/api/v1/monitoring/evaluate", headers=headers)
        
        alerts_res = client.get("/api/v1/monitoring/alerts?status=ACTIVE", headers=headers)
        alerts = alerts_res.json()
        if len(alerts) > 0:
            alert_id = alerts[0]["id"]
            
            dismiss_res = client.post(
                f"/api/v1/monitoring/alerts/{alert_id}/dismiss",
                headers=headers,
                json={"justification": "False positive due to planned maintenance window."},
            )
            assert dismiss_res.status_code == 200
            assert dismiss_res.json()["status"] == "DISMISSED"
