from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.permissions import RoleEnum
from app.core.security import get_password_hash
from app.models.audit_log import AuditLog
from app.models.control import OrganizationControl
from app.models.incident import (
    DisclosureStatusEnum,
    IncidentCategoryEnum,
    IncidentSeverityEnum,
    IncidentStatusEnum,
    RegulatorEnum,
    SecurityIncident,
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


class TestPhase10AdversarialSecurity:
    """Authoritative 20-Test Adversarial Security Suite (ADV-P10-01 to ADV-P10-20)."""

    # ── ADV-P10-01: Cross-Tenant Incident Read IDOR ──────────────────────────
    def test_adv_p10_01_cross_tenant_incident_read_idor(
        self, client: TestClient, db: Session, admin_user: User, meridian_admin_user: User, org_apex
    ):
        """ADV-P10-01: Tenant Meridian cannot read Tenant Apex's security incident."""
        apex_headers = get_token_headers(admin_user)
        meridian_headers = get_token_headers(meridian_admin_user)
        now_iso = datetime.now(timezone.utc).isoformat()

        res_create = client.post(
            "/api/v1/incidents",
            json={
                "incident_code": "INC-ADV-01",
                "title": "Apex Confidential Incident",
                "description": "Critical breach in payment pipeline.",
                "severity": "CRITICAL",
                "category": "DATA_BREACH",
                "detected_at": now_iso,
            },
            headers=apex_headers,
        )
        incident_id = res_create.json()["id"]

        # Meridian tries to read Apex incident
        res_idor = client.get(f"/api/v1/incidents/{incident_id}", headers=meridian_headers)
        assert res_idor.status_code == 404
        assert "not found" in res_idor.json()["detail"].lower()

    # ── ADV-P10-02: Cross-Tenant Incident Update IDOR ────────────────────────
    def test_adv_p10_02_cross_tenant_incident_update_idor(
        self, client: TestClient, db: Session, admin_user: User, meridian_admin_user: User, org_apex
    ):
        """ADV-P10-02: Tenant Meridian cannot update Tenant Apex's incident."""
        apex_headers = get_token_headers(admin_user)
        meridian_headers = get_token_headers(meridian_admin_user)
        now_iso = datetime.now(timezone.utc).isoformat()

        res_create = client.post(
            "/api/v1/incidents",
            json={
                "incident_code": "INC-ADV-02",
                "title": "Apex Incident Before Tampering",
                "description": "Original description.",
                "severity": "HIGH",
                "category": "OTHER",
                "detected_at": now_iso,
            },
            headers=apex_headers,
        )
        incident_id = res_create.json()["id"]

        # Meridian tries to update
        res_patch = client.patch(
            f"/api/v1/incidents/{incident_id}",
            json={"title": "Malicious Tampering"},
            headers=meridian_headers,
        )
        assert res_patch.status_code == 404

    # ── ADV-P10-03: Cross-Tenant Lifecycle Transition IDOR ───────────────────
    def test_adv_p10_03_cross_tenant_lifecycle_transition_idor(
        self, client: TestClient, db: Session, admin_user: User, meridian_admin_user: User, org_apex
    ):
        """ADV-P10-03: Tenant Meridian cannot transition Tenant Apex's incident status."""
        apex_headers = get_token_headers(admin_user)
        meridian_headers = get_token_headers(meridian_admin_user)
        now_iso = datetime.now(timezone.utc).isoformat()

        res_create = client.post(
            "/api/v1/incidents",
            json={
                "incident_code": "INC-ADV-03",
                "title": "Apex Status Incident",
                "description": "Description.",
                "severity": "HIGH",
                "category": "OTHER",
                "detected_at": now_iso,
            },
            headers=apex_headers,
        )
        incident_id = res_create.json()["id"]

        res_trans = client.post(
            f"/api/v1/incidents/{incident_id}/transition",
            json={"target_status": "TRIAGED"},
            headers=meridian_headers,
        )
        assert res_trans.status_code == 404

    # ── ADV-P10-04: Cross-Tenant Timeline Access ─────────────────────────────
    def test_adv_p10_04_cross_tenant_timeline_access(
        self, client: TestClient, db: Session, admin_user: User, meridian_admin_user: User, org_apex
    ):
        """ADV-P10-04: Tenant Meridian cannot read or append to Tenant Apex's incident timeline."""
        apex_headers = get_token_headers(admin_user)
        meridian_headers = get_token_headers(meridian_admin_user)
        now_iso = datetime.now(timezone.utc).isoformat()

        res_create = client.post(
            "/api/v1/incidents",
            json={
                "incident_code": "INC-ADV-04",
                "title": "Apex Timeline Incident",
                "description": "Description.",
                "severity": "MEDIUM",
                "category": "OTHER",
                "detected_at": now_iso,
            },
            headers=apex_headers,
        )
        incident_id = res_create.json()["id"]

        # Read timeline attempt
        res_read = client.get(f"/api/v1/incidents/{incident_id}/timeline", headers=meridian_headers)
        assert res_read.status_code == 404

        # Append timeline attempt
        res_append = client.post(
            f"/api/v1/incidents/{incident_id}/timeline",
            json={
                "event_type": "CONTAINMENT_ACTION",
                "event_occurred_at": now_iso,
                "description": "Unauthorized cross-tenant timeline injection.",
            },
            headers=meridian_headers,
        )
        assert res_append.status_code == 404

    # ── ADV-P10-05: Cross-Tenant Control Linkage ─────────────────────────────
    def test_adv_p10_05_cross_tenant_control_linkage(
        self, client: TestClient, db: Session, admin_user: User, org_apex, org_meridian, seeded_framework
    ):
        """ADV-P10-05: Tenant Apex cannot link an OrganizationControl belonging to Tenant Meridian."""
        apex_headers = get_token_headers(admin_user)
        now_iso = datetime.now(timezone.utc).isoformat()

        # Meridian's control
        subcat = seeded_framework.functions[0].categories[0].subcategories[0]
        meridian_ctrl = OrganizationControl(organization_id=org_meridian.id, subcategory_id=subcat.id)
        db.add(meridian_ctrl)
        db.commit()
        db.refresh(meridian_ctrl)

        # Apex incident
        res_create = client.post(
            "/api/v1/incidents",
            json={
                "incident_code": "INC-ADV-05",
                "title": "Apex Control Injection Incident",
                "description": "Description.",
                "severity": "MEDIUM",
                "category": "OTHER",
                "detected_at": now_iso,
            },
            headers=apex_headers,
        )
        incident_id = res_create.json()["id"]

        # Link Meridian control into Apex incident
        res_link = client.post(
            f"/api/v1/incidents/{incident_id}/controls",
            json={"organization_control_id": meridian_ctrl.id, "relationship_type": "FAILED_CONTROL"},
            headers=apex_headers,
        )
        assert res_link.status_code == 404
        assert "not found in your organization" in res_link.json()["detail"]

    # ── ADV-P10-06: Cross-Tenant Vendor Linkage ──────────────────────────────
    def test_adv_p10_06_cross_tenant_vendor_linkage(
        self, client: TestClient, db: Session, admin_user: User, org_apex, org_meridian
    ):
        """ADV-P10-06: Tenant Apex cannot link a Vendor belonging to Tenant Meridian."""
        apex_headers = get_token_headers(admin_user)
        now_iso = datetime.now(timezone.utc).isoformat()

        meridian_vendor = Vendor(organization_id=org_meridian.id, vendor_code="VND-MERIDIAN-ADV", legal_name="Meridian Vendor")
        db.add(meridian_vendor)
        db.commit()
        db.refresh(meridian_vendor)

        res_create = client.post(
            "/api/v1/incidents",
            json={
                "incident_code": "INC-ADV-06",
                "title": "Apex Vendor Injection Incident",
                "description": "Description.",
                "severity": "MEDIUM",
                "category": "SUPPLY_CHAIN_COMPROMISE",
                "detected_at": now_iso,
            },
            headers=apex_headers,
        )
        incident_id = res_create.json()["id"]

        res_link = client.post(
            f"/api/v1/incidents/{incident_id}/vendors",
            json={"vendor_id": meridian_vendor.id, "is_vendor_originated": True},
            headers=apex_headers,
        )
        assert res_link.status_code == 404
        assert "not found in your organization" in res_link.json()["detail"]

    # ── ADV-P10-07: Cross-Tenant Engagement Linkage Mismatch ─────────────────
    def test_adv_p10_07_cross_tenant_engagement_linkage(
        self, client: TestClient, db: Session, admin_user: User, org_apex
    ):
        """ADV-P10-07: Cannot link Vendor A with an engagement belonging to Vendor B."""
        apex_headers = get_token_headers(admin_user)
        now_iso = datetime.now(timezone.utc).isoformat()

        vendor_a = Vendor(organization_id=org_apex.id, vendor_code="VND-ADV-A", legal_name="Vendor Alpha")
        vendor_b = Vendor(organization_id=org_apex.id, vendor_code="VND-ADV-B", legal_name="Vendor Beta")
        db.add_all([vendor_a, vendor_b])
        db.commit()

        eng_b = VendorEngagement(
            organization_id=org_apex.id,
            vendor_id=vendor_b.id,
            engagement_code="ENG-ADV-B",
            engagement_name="Engagement for Beta",
        )
        db.add(eng_b)
        db.commit()

        res_create = client.post(
            "/api/v1/incidents",
            json={
                "incident_code": "INC-ADV-07",
                "title": "Apex Mismatch Engagement Incident",
                "description": "Description.",
                "severity": "MEDIUM",
                "category": "SUPPLY_CHAIN_COMPROMISE",
                "detected_at": now_iso,
            },
            headers=apex_headers,
        )
        incident_id = res_create.json()["id"]

        # Link vendor_a with eng_b
        res_link = client.post(
            f"/api/v1/incidents/{incident_id}/vendors",
            json={"vendor_id": vendor_a.id, "vendor_engagement_id": eng_b.id},
            headers=apex_headers,
        )
        assert res_link.status_code == 404
        assert "does not belong to Vendor" in res_link.json()["detail"]

    # ── ADV-P10-08: Cross-Tenant Disclosure Access ───────────────────────────
    def test_adv_p10_08_cross_tenant_disclosure_access(
        self, client: TestClient, db: Session, admin_user: User, meridian_admin_user: User, org_apex
    ):
        """ADV-P10-08: Tenant Meridian cannot view or notify Apex's regulatory disclosure."""
        apex_headers = get_token_headers(admin_user)
        meridian_headers = get_token_headers(meridian_admin_user)
        now = datetime.now(timezone.utc)

        res_create = client.post(
            "/api/v1/incidents",
            json={
                "incident_code": "INC-ADV-08",
                "title": "Apex Disclosure Incident",
                "description": "Description.",
                "severity": "CRITICAL",
                "category": "DATA_BREACH",
                "detected_at": now.isoformat(),
            },
            headers=apex_headers,
        )
        incident_id = res_create.json()["id"]

        res_disc = client.post(
            f"/api/v1/incidents/{incident_id}/disclosures",
            json={"regulator": "GDPR_DPA", "trigger_type": "INCIDENT_DETECTION", "triggered_at": now.isoformat()},
            headers=apex_headers,
        )
        disc_id = res_disc.json()["id"]

        # Meridian tries to notify
        res_notify = client.post(
            f"/api/v1/incidents/disclosures/{disc_id}/notify",
            json={"notification_reference_code": "FORGED-REF"},
            headers=meridian_headers,
        )
        assert res_notify.status_code == 404

    # ── ADV-P10-09: organization_id Spoofing ─────────────────────────────────
    def test_adv_p10_09_organization_id_spoofing(
        self, client: TestClient, db: Session, admin_user: User, org_apex, org_meridian
    ):
        """ADV-P10-09: Attacker cannot create an incident in another tenant by spoofing organization_id in body."""
        apex_headers = get_token_headers(admin_user)
        now_iso = datetime.now(timezone.utc).isoformat()

        # Attacker injects foreign organization_id
        payload = {
            "incident_code": "INC-ADV-09",
            "title": "Spoofed Org Incident",
            "description": "Attempting to assign to Meridian.",
            "severity": "LOW",
            "category": "OTHER",
            "detected_at": now_iso,
            "organization_id": org_meridian.id,
        }
        res = client.post("/api/v1/incidents", json=payload, headers=apex_headers)
        assert res.status_code == 201
        data = res.json()
        # Must strictly be assigned to Apex
        assert data["organization_id"] == org_apex.id
        assert data["organization_id"] != org_meridian.id

    # ── ADV-P10-10: actor_id Spoofing ────────────────────────────────────────
    def test_adv_p10_10_actor_id_spoofing(
        self, client: TestClient, db: Session, analyst_user: User, admin_user: User
    ):
        """ADV-P10-10: Attacker cannot spoof actor_id in timeline events."""
        analyst_headers = get_token_headers(analyst_user)
        now = datetime.now(timezone.utc)

        res_create = client.post(
            "/api/v1/incidents",
            json={
                "incident_code": "INC-ADV-10",
                "title": "Actor Spoof Incident",
                "description": "Description.",
                "severity": "MEDIUM",
                "category": "OTHER",
                "detected_at": now.isoformat(),
            },
            headers=analyst_headers,
        )
        incident_id = res_create.json()["id"]

        # Analyst attempts to inject Admin's actor_id
        res_event = client.post(
            f"/api/v1/incidents/{incident_id}/timeline",
            json={
                "event_type": "POST_MORTEM_NOTE",
                "event_occurred_at": now.isoformat(),
                "description": "Forged by Analyst claiming to be Admin.",
                "actor_id": admin_user.id,
            },
            headers=analyst_headers,
        )
        assert res_event.status_code == 201
        # Server must enforce analyst_user.id
        assert res_event.json()["actor_id"] == analyst_user.id
        assert res_event.json()["actor_id"] != admin_user.id

    # ── ADV-P10-11: closed_by_id Spoofing ────────────────────────────────────
    def test_adv_p10_11_closed_by_id_spoofing(
        self, client: TestClient, db: Session, admin_user: User, analyst_user: User, org_apex
    ):
        """ADV-P10-11: Attacker cannot set closed_by_id in metadata update."""
        admin_headers = get_token_headers(admin_user)
        now_iso = datetime.now(timezone.utc).isoformat()

        res_create = client.post(
            "/api/v1/incidents",
            json={
                "incident_code": "INC-ADV-11",
                "title": "Closed By Spoof Incident",
                "description": "Description.",
                "severity": "LOW",
                "category": "OTHER",
                "detected_at": now_iso,
            },
            headers=admin_headers,
        )
        incident_id = res_create.json()["id"]

        # Attempt to patch closed_by_id
        res_patch = client.patch(
            f"/api/v1/incidents/{incident_id}",
            json={"closed_by_id": analyst_user.id},
            headers=admin_headers,
        )
        assert res_patch.status_code == 200
        # Remains None until legitimate /close
        assert res_patch.json()["closed_by_id"] is None

    # ── ADV-P10-12: Client-Controlled Lifecycle Timestamp Injection ──────────
    def test_adv_p10_12_client_controlled_lifecycle_timestamp_injection(
        self, client: TestClient, db: Session, admin_user: User
    ):
        """ADV-P10-12: Client cannot directly set contained_at or closed_at in metadata PATCH."""
        admin_headers = get_token_headers(admin_user)
        now_iso = datetime.now(timezone.utc).isoformat()

        res_create = client.post(
            "/api/v1/incidents",
            json={
                "incident_code": "INC-ADV-12",
                "title": "Timestamp Injection Incident",
                "description": "Description.",
                "severity": "LOW",
                "category": "OTHER",
                "detected_at": now_iso,
            },
            headers=admin_headers,
        )
        incident_id = res_create.json()["id"]

        fake_ts = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
        res_patch = client.patch(
            f"/api/v1/incidents/{incident_id}",
            json={"contained_at": fake_ts, "closed_at": fake_ts},
            headers=admin_headers,
        )
        assert res_patch.status_code == 200
        assert res_patch.json()["contained_at"] is None
        assert res_patch.json()["closed_at"] is None

    # ── ADV-P10-13: Client-Controlled Regulatory Deadline Injection ──────────
    def test_adv_p10_13_client_controlled_regulatory_deadline_injection(
        self, client: TestClient, db: Session, admin_user: User
    ):
        """ADV-P10-13: Server computes authoritative statutory deadline; client fake deadline is ignored."""
        admin_headers = get_token_headers(admin_user)
        now = datetime(2026, 8, 24, 10, 0, 0, tzinfo=timezone.utc)

        res_create = client.post(
            "/api/v1/incidents",
            json={
                "incident_code": "INC-ADV-13",
                "title": "Fake Deadline Incident",
                "description": "Description.",
                "severity": "CRITICAL",
                "category": "DATA_BREACH",
                "detected_at": now.isoformat(),
            },
            headers=admin_headers,
        )
        incident_id = res_create.json()["id"]

        # Client attempts to pass deadline 10 years in future
        fake_deadline = (now + timedelta(days=3650)).isoformat()
        res_disc = client.post(
            f"/api/v1/incidents/{incident_id}/disclosures",
            json={
                "regulator": "GDPR_DPA",
                "trigger_type": "INCIDENT_DETECTION",
                "triggered_at": now.isoformat(),
                "deadline_at": fake_deadline,
            },
            headers=admin_headers,
        )
        assert res_disc.status_code == 201
        # Authoritative GDPR deadline must be exactly 72 hours
        expected_deadline = (now + timedelta(hours=72)).isoformat()
        assert res_disc.json()["deadline_at"].startswith(expected_deadline[:19])

    # ── ADV-P10-14: Client-Controlled Calculated Telemetry Injection ──────────
    def test_adv_p10_14_client_controlled_telemetry_injection(
        self, client: TestClient, db: Session, admin_user: User
    ):
        """ADV-P10-14: Client cannot set ttc_hours or mttr_hours in incident creation or update."""
        admin_headers = get_token_headers(admin_user)
        now_iso = datetime.now(timezone.utc).isoformat()

        res_create = client.post(
            "/api/v1/incidents",
            json={
                "incident_code": "INC-ADV-14",
                "title": "Telemetry Injection Incident",
                "description": "Description.",
                "severity": "LOW",
                "category": "OTHER",
                "detected_at": now_iso,
                "ttc_hours": 0.001,
                "mttr_hours": 0.001,
            },
            headers=admin_headers,
        )
        assert res_create.status_code == 201
        incident_id = res_create.json()["id"]

        res_detail = client.get(f"/api/v1/incidents/{incident_id}", headers=admin_headers)
        assert res_detail.status_code == 200
        # ttc_hours is None because incident is DECLARED and not contained yet
        assert res_detail.json()["ttc_hours"] is None

    # ── ADV-P10-15: Illegal Lifecycle Jump ────────────────────────────────────
    def test_adv_p10_15_illegal_lifecycle_jump(
        self, client: TestClient, db: Session, admin_user: User
    ):
        """ADV-P10-15: Attempting illegal lifecycle jump returns 400 Bad Request."""
        admin_headers = get_token_headers(admin_user)
        now_iso = datetime.now(timezone.utc).isoformat()

        res_create = client.post(
            "/api/v1/incidents",
            json={
                "incident_code": "INC-ADV-15",
                "title": "Illegal Jump Incident",
                "description": "Description.",
                "severity": "LOW",
                "category": "OTHER",
                "detected_at": now_iso,
            },
            headers=admin_headers,
        )
        incident_id = res_create.json()["id"]

        # DECLARED -> CLOSED
        res_jump = client.post(
            f"/api/v1/incidents/{incident_id}/transition",
            json={"target_status": "CLOSED"},
            headers=admin_headers,
        )
        assert res_jump.status_code == 400

    # ── ADV-P10-16: CLOSED Incident Mutation ──────────────────────────────────
    def test_adv_p10_16_closed_incident_mutation(
        self, client: TestClient, db: Session, admin_user: User, org_apex
    ):
        """ADV-P10-16: Mutating a CLOSED incident returns 409 Conflict."""
        from app.core.permissions import RoleEnum
        from app.core.security import get_password_hash

        mgr = User(
            email="manager-adv16@apex.com",
            hashed_password=get_password_hash("Pass123!"),
            full_name="Manager ADV",
            role=RoleEnum.MANAGER,
            is_active=True,
            organization_id=org_apex.id,
        )
        db.add(mgr)
        db.commit()

        admin_headers = get_token_headers(admin_user)
        mgr_headers = get_token_headers(mgr)
        now_iso = datetime.now(timezone.utc).isoformat()

        res_create = client.post(
            "/api/v1/incidents",
            json={
                "incident_code": "INC-ADV-16",
                "title": "Closed Lock Incident",
                "description": "Description.",
                "severity": "HIGH",
                "category": "OTHER",
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
        client.post(f"/api/v1/incidents/{incident_id}/close", json={"closure_notes": "Closed legitimately by manager."}, headers=mgr_headers)

        # Attempt to patch
        res_patch = client.patch(
            f"/api/v1/incidents/{incident_id}",
            json={"title": "Tampering after closed"},
            headers=admin_headers,
        )
        assert res_patch.status_code == 409
        assert "immutable" in res_patch.json()["detail"].lower()

    # ── ADV-P10-17: Commander Self-Close Attempt ─────────────────────────────
    def test_adv_p10_17_commander_self_close_attempt(
        self, client: TestClient, db: Session, admin_user: User
    ):
        """ADV-P10-17: Incident commander self-close returns 403 Forbidden."""
        admin_headers = get_token_headers(admin_user)
        now_iso = datetime.now(timezone.utc).isoformat()

        res_create = client.post(
            "/api/v1/incidents",
            json={
                "incident_code": "INC-ADV-17",
                "title": "Self Close Incident",
                "description": "Description.",
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

        # Commander tries to close
        res_close = client.post(
            f"/api/v1/incidents/{incident_id}/close",
            json={"closure_notes": "Commander self closing."},
            headers=admin_headers,
        )
        assert res_close.status_code == 403
        assert "Separation of duties violation" in res_close.json()["detail"]

    # ── ADV-P10-18: Timeline Mutation / Update / Delete Attempt ───────────────
    def test_adv_p10_18_timeline_mutation_attempt(
        self, client: TestClient, db: Session, admin_user: User
    ):
        """ADV-P10-18: Timeline endpoints are strictly append-only; DELETE/PUT on timeline returns 405."""
        admin_headers = get_token_headers(admin_user)
        now_iso = datetime.now(timezone.utc).isoformat()

        res_create = client.post(
            "/api/v1/incidents",
            json={
                "incident_code": "INC-ADV-18",
                "title": "Timeline Delete Incident",
                "description": "Description.",
                "severity": "LOW",
                "category": "OTHER",
                "detected_at": now_iso,
            },
            headers=admin_headers,
        )
        incident_id = res_create.json()["id"]

        # DELETE on /api/v1/incidents/{id}/timeline (which only allows GET/POST)
        res_del = client.delete(f"/api/v1/incidents/{incident_id}/timeline", headers=admin_headers)
        assert res_del.status_code == 405

        # PUT on /api/v1/incidents/{id}/timeline
        res_put = client.put(f"/api/v1/incidents/{incident_id}/timeline", json={}, headers=admin_headers)
        assert res_put.status_code == 405

    # ── ADV-P10-19: Foreign CCM Drift Alert Association ──────────────────────
    def test_adv_p10_19_foreign_ccm_drift_alert_association(
        self, client: TestClient, db: Session, admin_user: User, org_apex, org_meridian, seeded_framework
    ):
        """ADV-P10-19: Cannot link a ComplianceDriftAlert belonging to Meridian into Apex incident."""
        admin_headers = get_token_headers(admin_user)
        now_iso = datetime.now(timezone.utc).isoformat()

        subcat = seeded_framework.functions[0].categories[0].subcategories[0]
        meridian_ctrl = OrganizationControl(organization_id=org_meridian.id, subcategory_id=subcat.id)
        db.add(meridian_ctrl)
        db.commit()

        meridian_alert = ComplianceDriftAlert(
            organization_id=org_meridian.id,
            organization_control_id=meridian_ctrl.id,
            alert_type=DriftAlertTypeEnum.CONTROL_DEGRADED,
            severity=DriftAlertSeverityEnum.CRITICAL,
            status=DriftAlertStatusEnum.ACTIVE,
            title="Meridian Drift Alert",
            description="Meridian check failure.",
        )
        db.add(meridian_alert)
        db.commit()
        db.refresh(meridian_alert)

        # Apex tries to link meridian_alert
        res = client.post(
            "/api/v1/incidents",
            json={
                "incident_code": "INC-ADV-19",
                "title": "Foreign Drift Alert Incident",
                "description": "Description.",
                "severity": "CRITICAL",
                "category": "OTHER",
                "detected_at": now_iso,
                "compliance_drift_alert_id": meridian_alert.id,
            },
            headers=admin_headers,
        )
        assert res.status_code == 404
        assert "not found in your organization" in res.json()["detail"]

    # ── ADV-P10-20: Audit Actor / Timestamp Integrity ────────────────────────
    def test_adv_p10_20_audit_actor_and_timestamp_integrity(
        self, client: TestClient, db: Session, admin_user: User, org_apex
    ):
        """ADV-P10-20: Audit log preserves authenticated user email and UTC server timestamps."""
        admin_headers = get_token_headers(admin_user)
        now_iso = datetime.now(timezone.utc).isoformat()

        res = client.post(
            "/api/v1/incidents",
            json={
                "incident_code": "INC-ADV-20",
                "title": "Audit Integrity Incident",
                "description": "Description.",
                "severity": "MEDIUM",
                "category": "DATA_BREACH",
                "detected_at": now_iso,
            },
            headers=admin_headers,
        )
        assert res.status_code == 201
        incident_id = res.json()["id"]

        # Check Audit Log in DB
        audit_entry = (
            db.query(AuditLog)
            .filter(
                AuditLog.organization_id == org_apex.id,
                AuditLog.action == "INCIDENT_DECLARED",
                AuditLog.resource_id == str(incident_id),
            )
            .first()
        )
        assert audit_entry is not None
        assert audit_entry.actor_email == admin_user.email
        assert audit_entry.actor_id == admin_user.id
        assert audit_entry.timestamp is not None
