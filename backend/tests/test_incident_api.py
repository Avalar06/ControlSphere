from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.control import OrganizationControl
from app.models.incident import (
    DisclosureStatusEnum,
    DisclosureTriggerTypeEnum,
    IncidentCategoryEnum,
    IncidentControlRelationshipEnum,
    IncidentSeverityEnum,
    IncidentStatusEnum,
    RegulatorEnum,
    RootCauseClassificationEnum,
    SecurityIncident,
    TimelineEventSourceEnum,
    TimelineEventTypeEnum,
)
from app.models.monitoring import (
    ComplianceDriftAlert,
    DriftAlertSeverityEnum,
    DriftAlertStatusEnum,
    DriftAlertTypeEnum,
)
from app.models.tprm import Vendor, VendorEngagement, VendorStatusEnum
from app.models.user import User
from tests.conftest import get_token_headers


class TestIncidentAPI:
    """Comprehensive REST API and Cross-Module Integration Test Suite for Phase 10."""

    def test_incident_creation_and_retrieval(self, client: TestClient, db: Session, admin_user: User):
        """Test POST /api/v1/incidents and GET /api/v1/incidents/{id}."""
        headers = get_token_headers(admin_user)
        now_iso = datetime.now(timezone.utc).isoformat()

        payload = {
            "incident_code": "INC-API-001",
            "title": "Unauthorized S3 Bucket Access",
            "description": "Publicly accessible bucket detected containing raw telemetry logs.",
            "severity": "HIGH",
            "category": "DATA_BREACH",
            "detected_at": now_iso,
            "affected_record_count": 5000,
            "financial_impact_estimate": 12000.0,
        }

        # 1. Create Incident
        res = client.post("/api/v1/incidents", json=payload, headers=headers)
        assert res.status_code == 201
        data = res.json()
        assert data["incident_code"] == "INC-API-001"
        assert data["status"] == "DECLARED"
        assert data["incident_commander_id"] == admin_user.id
        incident_id = data["id"]

        # 2. Get Incident Detail
        res_detail = client.get(f"/api/v1/incidents/{incident_id}", headers=headers)
        assert res_detail.status_code == 200
        detail = res_detail.json()
        assert detail["id"] == incident_id
        assert detail["title"] == "Unauthorized S3 Bucket Access"
        assert len(detail["timeline_events"]) == 1
        assert detail["timeline_events"][0]["event_type"] == "DETECTION"

    def test_incident_list_and_filtering(self, client: TestClient, db: Session, admin_user: User):
        """Test GET /api/v1/incidents with status, severity, category filters."""
        headers = get_token_headers(admin_user)
        now_iso = datetime.now(timezone.utc).isoformat()

        client.post(
            "/api/v1/incidents",
            json={
                "incident_code": "INC-FILTER-1",
                "title": "Critical Ransomware Outbreak",
                "description": "Active ransomware spreading via SMB.",
                "severity": "CRITICAL",
                "category": "RANSOMWARE",
                "detected_at": now_iso,
            },
            headers=headers,
        )
        client.post(
            "/api/v1/incidents",
            json={
                "incident_code": "INC-FILTER-2",
                "title": "Low Severity Phishing Email",
                "description": "Phishing campaign caught by gateway filter.",
                "severity": "LOW",
                "category": "OTHER",
                "detected_at": now_iso,
            },
            headers=headers,
        )

        # Filter by CRITICAL
        res_crit = client.get("/api/v1/incidents?severity=CRITICAL", headers=headers)
        assert res_crit.status_code == 200
        assert any(i["incident_code"] == "INC-FILTER-1" for i in res_crit.json())
        assert not any(i["incident_code"] == "INC-FILTER-2" for i in res_crit.json())

        # Filter by search
        res_search = client.get("/api/v1/incidents?search=Phishing", headers=headers)
        assert res_search.status_code == 200
        assert len(res_search.json()) >= 1
        assert res_search.json()[0]["incident_code"] == "INC-FILTER-2"

    def test_incident_overview_telemetry(self, client: TestClient, db: Session, admin_user: User):
        """Test GET /api/v1/incidents/overview returns aggregated telemetry."""
        headers = get_token_headers(admin_user)
        res = client.get("/api/v1/incidents/overview", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "total_incidents" in data
        assert "open_incidents" in data
        assert "status_distribution" in data
        assert "severity_distribution" in data

    def test_incident_metadata_update(self, client: TestClient, db: Session, admin_user: User):
        """Test PATCH /api/v1/incidents/{id}."""
        headers = get_token_headers(admin_user)
        now_iso = datetime.now(timezone.utc).isoformat()

        res_create = client.post(
            "/api/v1/incidents",
            json={
                "incident_code": "INC-UPDATE-01",
                "title": "Initial Title",
                "description": "Initial description.",
                "severity": "MEDIUM",
                "category": "OTHER",
                "detected_at": now_iso,
            },
            headers=headers,
        )
        incident_id = res_create.json()["id"]

        # Patch metadata
        patch_payload = {
            "title": "Updated Threat Intel Title",
            "severity": "HIGH",
            "financial_impact_estimate": 75000.0,
            "root_cause_classification": "CONFIGURATION_DRIFT",
        }
        res_patch = client.patch(f"/api/v1/incidents/{incident_id}", json=patch_payload, headers=headers)
        assert res_patch.status_code == 200
        data = res_patch.json()
        assert data["title"] == "Updated Threat Intel Title"
        assert data["severity"] == "HIGH"
        assert data["financial_impact_estimate"] == 75000.0
        assert data["root_cause_classification"] == "CONFIGURATION_DRIFT"

    def test_incident_lifecycle_progressive_transitions(self, client: TestClient, db: Session, admin_user: User):
        """Test progressive lifecycle progression via POST /api/v1/incidents/{id}/transition."""
        headers = get_token_headers(admin_user)
        now_iso = datetime.now(timezone.utc).isoformat()

        res_create = client.post(
            "/api/v1/incidents",
            json={
                "incident_code": "INC-TRANS-01",
                "title": "State Progression Test",
                "description": "Testing lifecycle API.",
                "severity": "MEDIUM",
                "category": "DATA_BREACH",
                "detected_at": now_iso,
            },
            headers=headers,
        )
        incident_id = res_create.json()["id"]

        # 1. DECLARED -> TRIAGED
        res1 = client.post(f"/api/v1/incidents/{incident_id}/transition", json={"target_status": "TRIAGED"}, headers=headers)
        assert res1.status_code == 200
        assert res1.json()["status"] == "TRIAGED"

        # 2. TRIAGED -> CONTAINED
        res2 = client.post(f"/api/v1/incidents/{incident_id}/transition", json={"target_status": "CONTAINED"}, headers=headers)
        assert res2.status_code == 200
        assert res2.json()["status"] == "CONTAINED"
        assert res2.json()["contained_at"] is not None

        # 3. CONTAINED -> ERADICATED
        res3 = client.post(f"/api/v1/incidents/{incident_id}/transition", json={"target_status": "ERADICATED"}, headers=headers)
        assert res3.status_code == 200
        assert res3.json()["status"] == "ERADICATED"

        # 4. ERADICATED -> RECOVERED
        res4 = client.post(f"/api/v1/incidents/{incident_id}/transition", json={"target_status": "RECOVERED"}, headers=headers)
        assert res4.status_code == 200
        assert res4.json()["status"] == "RECOVERED"

        # 5. RECOVERED -> POST_MORTEM
        res5 = client.post(f"/api/v1/incidents/{incident_id}/transition", json={"target_status": "POST_MORTEM"}, headers=headers)
        assert res5.status_code == 200
        assert res5.json()["status"] == "POST_MORTEM"

    def test_illegal_lifecycle_jump_rejected(self, client: TestClient, db: Session, admin_user: User):
        """Test illegal status transition is rejected with 400 Bad Request."""
        headers = get_token_headers(admin_user)
        now_iso = datetime.now(timezone.utc).isoformat()

        res_create = client.post(
            "/api/v1/incidents",
            json={
                "incident_code": "INC-BAD-TRANS",
                "title": "Bad Transition Test",
                "description": "Testing illegal jump.",
                "severity": "LOW",
                "category": "OTHER",
                "detected_at": now_iso,
            },
            headers=headers,
        )
        incident_id = res_create.json()["id"]

        # DECLARED -> RECOVERED is illegal
        res_illegal = client.post(
            f"/api/v1/incidents/{incident_id}/transition",
            json={"target_status": "RECOVERED"},
            headers=headers,
        )
        assert res_illegal.status_code == 400
        assert "Invalid incident lifecycle transition" in res_illegal.json()["detail"]

    def test_sec_materiality_determination(self, client: TestClient, db: Session, admin_user: User):
        """Test POST /api/v1/incidents/{id}/materiality auto-triggers SEC 8-K disclosure with business days."""
        headers = get_token_headers(admin_user)
        now_iso = datetime.now(timezone.utc).isoformat()

        res_create = client.post(
            "/api/v1/incidents",
            json={
                "incident_code": "INC-SEC-API",
                "title": "Material SEC 8-K Incident",
                "description": "Compromise of customer account database.",
                "severity": "CRITICAL",
                "category": "DATA_BREACH",
                "detected_at": now_iso,
            },
            headers=headers,
        )
        incident_id = res_create.json()["id"]

        # Set materiality
        res_mat = client.post(
            f"/api/v1/incidents/{incident_id}/materiality",
            json={"is_material": True, "materiality_notes": "Significant impact to shareholder value and business continuity."},
            headers=headers,
        )
        assert res_mat.status_code == 200
        assert res_mat.json()["is_material"] is True
        assert res_mat.json()["materiality_determined_at"] is not None

        # Check Disclosures
        res_disc = client.get(f"/api/v1/incidents/{incident_id}/disclosures", headers=headers)
        assert res_disc.status_code == 200
        disclosures = res_disc.json()
        assert len(disclosures) == 1
        assert disclosures[0]["regulator"] == "SEC_8K"
        assert disclosures[0]["calculation_version"] == "1.0_business_days"

    def test_timeline_append_and_read(self, client: TestClient, db: Session, admin_user: User):
        """Test POST and GET /api/v1/incidents/{id}/timeline."""
        headers = get_token_headers(admin_user)
        now = datetime.now(timezone.utc)

        res_create = client.post(
            "/api/v1/incidents",
            json={
                "incident_code": "INC-TIME-API",
                "title": "Timeline API Test",
                "description": "Testing timeline routes.",
                "severity": "MEDIUM",
                "category": "UNAUTHORIZED_ACCESS",
                "detected_at": now.isoformat(),
            },
            headers=headers,
        )
        incident_id = res_create.json()["id"]

        # Append timeline event
        event_payload = {
            "event_type": "CONTAINMENT_ACTION",
            "event_occurred_at": (now + timedelta(minutes=20)).isoformat(),
            "description": "Revoked compromised AWS IAM credentials and rotated secrets.",
            "source": "MANUAL_ENTRY",
        }
        res_event = client.post(f"/api/v1/incidents/{incident_id}/timeline", json=event_payload, headers=headers)
        assert res_event.status_code == 201
        assert res_event.json()["event_type"] == "CONTAINMENT_ACTION"

        # List timeline
        res_list = client.get(f"/api/v1/incidents/{incident_id}/timeline", headers=headers)
        assert res_list.status_code == 200
        events = res_list.json()
        assert len(events) == 2  # 1 initial detection + 1 containment
        assert events[1]["description"] == "Revoked compromised AWS IAM credentials and rotated secrets."

    def test_control_linkage_and_unlinkage(self, client: TestClient, db: Session, admin_user: User, org_apex, seeded_framework):
        """Test POST and DELETE /api/v1/incidents/{id}/controls."""
        headers = get_token_headers(admin_user)
        now_iso = datetime.now(timezone.utc).isoformat()

        # Create control
        subcat = seeded_framework.functions[0].categories[0].subcategories[0]
        ctrl = OrganizationControl(organization_id=org_apex.id, subcategory_id=subcat.id)
        db.add(ctrl)
        db.commit()
        db.refresh(ctrl)

        res_create = client.post(
            "/api/v1/incidents",
            json={
                "incident_code": "INC-CTRL-API",
                "title": "Control Linkage Test",
                "description": "Testing control links.",
                "severity": "HIGH",
                "category": "DATA_BREACH",
                "detected_at": now_iso,
            },
            headers=headers,
        )
        incident_id = res_create.json()["id"]

        # Link Control
        res_link = client.post(
            f"/api/v1/incidents/{incident_id}/controls",
            json={
                "organization_control_id": ctrl.id,
                "relationship_type": "FAILED_CONTROL",
                "notes": "MFA enforcement failed due to legacy bypass rule.",
            },
            headers=headers,
        )
        assert res_link.status_code == 201
        link_id = res_link.json()["id"]

        # Unlink Control
        res_unlink = client.delete(f"/api/v1/incidents/{incident_id}/controls/{link_id}", headers=headers)
        assert res_unlink.status_code == 204

    def test_vendor_linkage_and_unlinkage(self, client: TestClient, db: Session, admin_user: User, org_apex):
        """Test POST and DELETE /api/v1/incidents/{id}/vendors."""
        headers = get_token_headers(admin_user)
        now_iso = datetime.now(timezone.utc).isoformat()

        vendor = Vendor(organization_id=org_apex.id, vendor_code="VND-INC-01", legal_name="Snowflake Inc")
        db.add(vendor)
        db.commit()
        db.refresh(vendor)

        res_create = client.post(
            "/api/v1/incidents",
            json={
                "incident_code": "INC-VND-API",
                "title": "Vendor Linkage Test",
                "description": "Testing vendor links.",
                "severity": "CRITICAL",
                "category": "SUPPLY_CHAIN_COMPROMISE",
                "detected_at": now_iso,
            },
            headers=headers,
        )
        incident_id = res_create.json()["id"]

        # Link Vendor
        res_link = client.post(
            f"/api/v1/incidents/{incident_id}/vendors",
            json={
                "vendor_id": vendor.id,
                "is_vendor_originated": True,
                "notes": "Breach originated via compromised vendor integration token.",
            },
            headers=headers,
        )
        assert res_link.status_code == 201
        link_id = res_link.json()["id"]

        # Unlink Vendor
        res_unlink = client.delete(f"/api/v1/incidents/{incident_id}/vendors/{link_id}", headers=headers)
        assert res_unlink.status_code == 204

    def test_regulatory_disclosure_workflow(self, client: TestClient, db: Session, admin_user: User):
        """Test evaluate, notify, and exempt disclosure workflow."""
        headers = get_token_headers(admin_user)
        now = datetime.now(timezone.utc)

        res_create = client.post(
            "/api/v1/incidents",
            json={
                "incident_code": "INC-DISC-API",
                "title": "Regulatory Notification API Test",
                "description": "Testing disclosure workflow.",
                "severity": "CRITICAL",
                "category": "DATA_BREACH",
                "detected_at": now.isoformat(),
            },
            headers=headers,
        )
        incident_id = res_create.json()["id"]

        # 1. Evaluate GDPR
        res_eval = client.post(
            f"/api/v1/incidents/{incident_id}/disclosures",
            json={
                "regulator": "GDPR_DPA",
                "trigger_type": "INCIDENT_DETECTION",
                "triggered_at": now.isoformat(),
            },
            headers=headers,
        )
        assert res_eval.status_code == 201
        disc_id = res_eval.json()["id"]
        assert res_eval.json()["status"] == "PENDING"

        # 2. Record Notification
        res_notify = client.post(
            f"/api/v1/incidents/disclosures/{disc_id}/notify",
            json={
                "notification_reference_code": "DPA-FRA-2026-00412",
                "disclosure_notes": "CNIL online breach notification submitted.",
            },
            headers=headers,
        )
        assert res_notify.status_code == 200
        assert res_notify.json()["status"] == "NOTIFIED"
        assert res_notify.json()["notification_reference_code"] == "DPA-FRA-2026-00412"

        # 3. Evaluate NYDFS and Exempt
        res_eval2 = client.post(
            f"/api/v1/incidents/{incident_id}/disclosures",
            json={
                "regulator": "NYDFS",
                "trigger_type": "INCIDENT_DETECTION",
                "triggered_at": now.isoformat(),
            },
            headers=headers,
        )
        disc_id2 = res_eval2.json()["id"]

        res_exempt = client.post(
            f"/api/v1/incidents/disclosures/{disc_id2}/exempt",
            json={
                "exemption_reason": "No NYDFS-regulated financial institution data stored in impacted cluster.",
            },
            headers=headers,
        )
        assert res_exempt.status_code == 200
        assert res_exempt.json()["status"] == "NOT_APPLICABLE"

    def test_four_eyes_closure_and_separation_of_duties(
        self, client: TestClient, db: Session, admin_user: User, analyst_user: User, org_apex
    ):
        """Test four-eyes closure: commander cannot close, manager can close."""
        from app.core.security import get_password_hash
        from app.core.permissions import RoleEnum

        manager_user = User(
            email="manager@apexfinancial.com",
            hashed_password=get_password_hash("ManagerPass123!"),
            full_name="Victoria Sterling",
            role=RoleEnum.MANAGER,
            is_active=True,
            organization_id=org_apex.id,
        )
        db.add(manager_user)
        db.commit()
        db.refresh(manager_user)

        admin_headers = get_token_headers(admin_user)
        manager_headers = get_token_headers(manager_user)
        now_iso = datetime.now(timezone.utc).isoformat()

        res_create = client.post(
            "/api/v1/incidents",
            json={
                "incident_code": "INC-4EYES-API",
                "title": "Four Eyes Closure Test",
                "description": "Commander cannot close own incident.",
                "severity": "HIGH",
                "category": "INSIDER_THREAT",
                "detected_at": now_iso,
            },
            headers=admin_headers,
        )
        incident_id = res_create.json()["id"]

        # Progress to POST_MORTEM
        client.post(f"/api/v1/incidents/{incident_id}/transition", json={"target_status": "TRIAGED"}, headers=admin_headers)
        client.post(f"/api/v1/incidents/{incident_id}/transition", json={"target_status": "CONTAINED"}, headers=admin_headers)
        client.post(f"/api/v1/incidents/{incident_id}/transition", json={"target_status": "ERADICATED"}, headers=admin_headers)
        client.post(f"/api/v1/incidents/{incident_id}/transition", json={"target_status": "RECOVERED"}, headers=admin_headers)
        client.post(f"/api/v1/incidents/{incident_id}/transition", json={"target_status": "POST_MORTEM"}, headers=admin_headers)

        # 1. Commander (admin_user) attempts to close -> 403 Forbidden
        res_self_close = client.post(
            f"/api/v1/incidents/{incident_id}/close",
            json={"closure_notes": "Admin closing own incident."},
            headers=admin_headers,
        )
        assert res_self_close.status_code == 403
        assert "Separation of duties violation" in res_self_close.json()["detail"]

        # 2. Independent Manager closes -> 200 OK
        res_mgr_close = client.post(
            f"/api/v1/incidents/{incident_id}/close",
            json={
                "closure_notes": "Incident independently reviewed and verified by CISO management.",
                "lessons_learned": "Enforce mandatory dual authorization for privileged service account credentials.",
                "root_cause_classification": "CONTROL_FAILURE",
            },
            headers=manager_headers,
        )
        assert res_mgr_close.status_code == 200
        assert res_mgr_close.json()["status"] == "CLOSED"
        assert res_mgr_close.json()["closed_by_id"] == manager_user.id

        # 3. Attempt mutation after CLOSED -> 409 Conflict
        res_mutate = client.patch(
            f"/api/v1/incidents/{incident_id}",
            json={"title": "Mutating Closed Incident"},
            headers=admin_headers,
        )
        assert res_mutate.status_code == 409

    def test_ccm_drift_alert_integration(self, client: TestClient, db: Session, admin_user: User, org_apex, seeded_framework):
        """Test creating an incident linked to an existing Phase 7 ComplianceDriftAlert."""
        headers = get_token_headers(admin_user)
        now = datetime.now(timezone.utc)

        subcat = seeded_framework.functions[0].categories[0].subcategories[0]
        ctrl = OrganizationControl(organization_id=org_apex.id, subcategory_id=subcat.id)
        db.add(ctrl)
        db.commit()

        alert = ComplianceDriftAlert(
            organization_id=org_apex.id,
            organization_control_id=ctrl.id,
            alert_type=DriftAlertTypeEnum.CONTROL_DEGRADED,
            severity=DriftAlertSeverityEnum.CRITICAL,
            status=DriftAlertStatusEnum.ACTIVE,
            title="Continuous check failed: Root AWS access key generated",
            description="Continuous check failed: Root AWS access key generated.",
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        res = client.post(
            "/api/v1/incidents",
            json={
                "incident_code": "INC-CCM-DRIFT-01",
                "title": "Incident from CCM Drift Alert",
                "description": "Root access key compromise alert promoted to security incident.",
                "severity": "CRITICAL",
                "category": "UNAUTHORIZED_ACCESS",
                "detected_at": now.isoformat(),
                "compliance_drift_alert_id": alert.id,
            },
            headers=headers,
        )
        assert res.status_code == 201
        data = res.json()
        assert data["compliance_drift_alert_id"] == alert.id
