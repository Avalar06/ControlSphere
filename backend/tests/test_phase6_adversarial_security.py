"""
tests/test_phase6_adversarial_security.py — Phase 6 adversarial security tests.

Attack surface coverage:
  ADV-P6-01: Cross-tenant IDOR — read foreign audit by ID
  ADV-P6-02: Cross-tenant IDOR — modify foreign audit
  ADV-P6-03: Cross-tenant FK injection — link foreign control to scope
  ADV-P6-04: Cross-tenant FK injection — link foreign finding
  ADV-P6-05: Cross-tenant FK injection — link foreign evidence
  ADV-P6-06: Closed audit immutability
  ADV-P6-07: Self-approval prohibition (four-eyes)
  ADV-P6-08: Invalid lifecycle transition prevention
  ADV-P6-09: Premature opinion issuance (PLANNED/INITIATED status)
  ADV-P6-10: Superseded evidence cannot be linked to procedures
  ADV-P6-11: Unauthenticated access blocked
  ADV-P6-12: Insufficient permissions blocked at every write endpoint
"""
import pytest
from sqlalchemy.orm import Session
from tests.conftest import get_token_headers
from app.models.control import OrganizationControl, ImplementationStatusEnum, PriorityEnum
from app.models.evidence import EvidenceItem, EvidenceStatusEnum
from app.models.finding import Finding, FindingTypeEnum, FindingSeverityEnum
from app.models.user import User
from app.core.permissions import RoleEnum


# ─── Helpers ─────────────────────────────────────────────────────────────────

def create_apex_audit(client, headers, **kw):
    payload = {"title": "Apex Audit", "objective": "Security adversarial test audit objective", "audit_type": "INTERNAL"}
    payload.update(kw)
    r = client.post("/api/v1/audits", json=payload, headers=headers)
    assert r.status_code == 201
    return r.json()


def make_control(db, org_id, subcat_id, status=ImplementationStatusEnum.IMPLEMENTED):
    ctrl = OrganizationControl(organization_id=org_id, subcategory_id=subcat_id, status=status, priority=PriorityEnum.HIGH)
    db.add(ctrl); db.commit(); db.refresh(ctrl)
    return ctrl


def make_evidence(db, org_id, ctrl_id, status=EvidenceStatusEnum.ACCEPTED):
    ev = EvidenceItem(
        organization_id=org_id, organization_control_id=ctrl_id, title="Sec Ev",
        original_filename="sec.pdf", stored_filename="sec_stored.pdf", file_extension="pdf",
        content_type="application/pdf", file_size=1024, sha256_hash="c" * 64,
        storage_key=f"org_{org_id}/sec.pdf", status=status,
    )
    db.add(ev); db.commit(); db.refresh(ev)
    return ev


def make_finding(db, org_id, ctrl_id):
    f = Finding(
        organization_id=org_id, organization_control_id=ctrl_id, title="Sec Finding",
        description="A security adversarial test finding for isolation verification",
        recommendation="Isolate and fix the security finding in appropriate scope.",
        finding_type=FindingTypeEnum.CONTROL_GAP, severity=FindingSeverityEnum.HIGH,
        impact=4, likelihood=3, risk_score=12, risk_band="HIGH",
    )
    db.add(f); db.commit(); db.refresh(f)
    return f


def advance_audit(client, headers, audit_id, target):
    for s in ["INITIATED", "FIELDWORK", "REVIEW", "REPORTING", "COMPLETED"]:
        r = client.post(f"/api/v1/audits/{audit_id}/status", json={"status": s}, headers=headers)
        assert r.status_code == 200
        if s == target:
            break


# ─── Tests ───────────────────────────────────────────────────────────────────

class TestPhase6AdversarialSecurity:
    def test_adv_p6_01_cross_tenant_idor_read(
        self, client, admin_user, meridian_admin_user, seeded_framework
    ):
        """ADV-P6-01: Meridian cannot read Apex's audit by guessing its ID."""
        apex_h = get_token_headers(admin_user)
        meridian_h = get_token_headers(meridian_admin_user)
        audit = create_apex_audit(client, apex_h)

        resp = client.get(f"/api/v1/audits/{audit['id']}", headers=meridian_h)
        assert resp.status_code == 404

    def test_adv_p6_02_cross_tenant_idor_modify(
        self, client, admin_user, meridian_admin_user, seeded_framework
    ):
        """ADV-P6-02: Meridian cannot modify Apex's audit."""
        apex_h = get_token_headers(admin_user)
        meridian_h = get_token_headers(meridian_admin_user)
        audit = create_apex_audit(client, apex_h)

        resp = client.patch(
            f"/api/v1/audits/{audit['id']}",
            json={"summary": "Cross-tenant modification attempt"},
            headers=meridian_h,
        )
        assert resp.status_code == 404

    def test_adv_p6_03_cross_tenant_scope_injection(
        self, client, admin_user, meridian_admin_user, seeded_framework, db, org_meridian
    ):
        """ADV-P6-03: Cannot inject foreign tenant's control into audit scope."""
        apex_h = get_token_headers(admin_user)
        subcat = db.query(__import__("app.models.framework", fromlist=["FrameworkSubcategory"]).FrameworkSubcategory).first()
        meridian_ctrl = make_control(db, org_meridian.id, subcat.id)

        audit = create_apex_audit(client, apex_h)
        resp = client.post(
            f"/api/v1/audits/{audit['id']}/scope",
            json={"organization_control_id": meridian_ctrl.id},
            headers=apex_h,
        )
        assert resp.status_code == 400

    def test_adv_p6_04_cross_tenant_finding_injection(
        self, client, admin_user, meridian_admin_user, seeded_framework, db, org_apex, org_meridian
    ):
        """ADV-P6-04: Cannot link a foreign tenant finding to an audit."""
        apex_h = get_token_headers(admin_user)
        subcat = db.query(__import__("app.models.framework", fromlist=["FrameworkSubcategory"]).FrameworkSubcategory).first()
        meridian_ctrl = make_control(db, org_meridian.id, subcat.id)
        meridian_finding = make_finding(db, org_meridian.id, meridian_ctrl.id)

        audit = create_apex_audit(client, apex_h)
        resp = client.post(
            f"/api/v1/audits/{audit['id']}/findings",
            json={"finding_id": meridian_finding.id},
            headers=apex_h,
        )
        assert resp.status_code == 400

    def test_adv_p6_05_cross_tenant_evidence_injection(
        self, client, admin_user, seeded_framework, db, org_apex, org_meridian
    ):
        """ADV-P6-05: Cannot link foreign evidence to a procedure."""
        apex_h = get_token_headers(admin_user)
        subcat = db.query(__import__("app.models.framework", fromlist=["FrameworkSubcategory"]).FrameworkSubcategory).first()
        apex_ctrl = make_control(db, org_apex.id, subcat.id)
        meridian_ctrl = make_control(db, org_meridian.id, subcat.id)
        meridian_ev = make_evidence(db, org_meridian.id, meridian_ctrl.id)

        audit = create_apex_audit(client, apex_h)
        proc_resp = client.post(
            f"/api/v1/audits/{audit['id']}/procedures",
            json={"title": "Test procedure", "result": "NOT_STARTED"},
            headers=apex_h,
        )
        proc_id = proc_resp.json()["id"]

        resp = client.post(
            f"/api/v1/audits/{audit['id']}/procedures/{proc_id}/evidence",
            json={"evidence_id": meridian_ev.id},
            headers=apex_h,
        )
        assert resp.status_code == 400

    def test_adv_p6_06_closed_audit_immutability(
        self, client, admin_user, seeded_framework
    ):
        """ADV-P6-06: Closed audits are entirely immutable."""
        h = get_token_headers(admin_user)
        audit = create_apex_audit(client, h)
        audit_id = audit["id"]
        advance_audit(client, h, audit_id, "COMPLETED")
        client.post(f"/api/v1/audits/{audit_id}/close", json={"closure_notes": "Formally closed"}, headers=h)

        # Cannot PATCH
        r1 = client.patch(f"/api/v1/audits/{audit_id}", json={"summary": "Attempt update"}, headers=h)
        assert r1.status_code == 400

        # Cannot change status
        r2 = client.post(f"/api/v1/audits/{audit_id}/status", json={"status": "COMPLETED"}, headers=h)
        assert r2.status_code == 400

        # Cannot re-close
        r3 = client.post(f"/api/v1/audits/{audit_id}/close", json={"closure_notes": "Second closure"}, headers=h)
        assert r3.status_code == 400

    def test_adv_p6_07_self_approval_prohibition(
        self, client, admin_user, auditor_user, seeded_framework, db, org_apex
    ):
        """ADV-P6-07: Lead auditor cannot issue opinion on their own engagement."""
        admin_h = get_token_headers(admin_user)
        auditor_h = get_token_headers(auditor_user)

        resp = client.post(
            "/api/v1/audits",
            json={
                "title": "Self-Approval Test",
                "objective": "Test four-eyes control in audit opinion workflow",
                "audit_type": "INTERNAL",
                "lead_auditor_id": auditor_user.id,
            },
            headers=admin_h,
        )
        audit_id = resp.json()["id"]

        # Admin advances lifecycle
        for s in ["INITIATED", "FIELDWORK", "REVIEW"]:
            client.post(f"/api/v1/audits/{audit_id}/status", json={"status": s}, headers=admin_h)

        # Auditor (lead) attempts to issue their own opinion
        r = client.post(
            f"/api/v1/audits/{audit_id}/opinion",
            json={"opinion": "UNQUALIFIED", "opinion_notes": "Self-approving my own audit for convenience."},
            headers=auditor_h,
        )
        assert r.status_code == 400
        assert "separation of duties" in r.json()["detail"].lower() or "lead auditor" in r.json()["detail"].lower()

    def test_adv_p6_08_invalid_lifecycle_skip(
        self, client, admin_user, seeded_framework
    ):
        """ADV-P6-08: Cannot skip lifecycle stages."""
        h = get_token_headers(admin_user)
        audit = create_apex_audit(client, h)
        audit_id = audit["id"]

        # PLANNED → COMPLETED (skip all intermediate stages)
        r = client.post(f"/api/v1/audits/{audit_id}/status", json={"status": "COMPLETED"}, headers=h)
        assert r.status_code == 400

        # PLANNED → REPORTING
        r2 = client.post(f"/api/v1/audits/{audit_id}/status", json={"status": "REPORTING"}, headers=h)
        assert r2.status_code == 400

        # PLANNED → CLOSED
        r3 = client.post(f"/api/v1/audits/{audit_id}/status", json={"status": "CLOSED"}, headers=h)
        assert r3.status_code == 400

    def test_adv_p6_09_premature_opinion(
        self, client, admin_user, seeded_framework
    ):
        """ADV-P6-09: Cannot issue opinion on PLANNED or INITIATED audit."""
        h = get_token_headers(admin_user)

        # PLANNED
        audit = create_apex_audit(client, h)
        r = client.post(
            f"/api/v1/audits/{audit['id']}/opinion",
            json={"opinion": "UNQUALIFIED", "opinion_notes": "Premature opinion on planned audit."},
            headers=h,
        )
        assert r.status_code == 400

        # INITIATED
        client.post(f"/api/v1/audits/{audit['id']}/status", json={"status": "INITIATED"}, headers=h)
        r2 = client.post(
            f"/api/v1/audits/{audit['id']}/opinion",
            json={"opinion": "QUALIFIED", "opinion_notes": "Premature opinion on initiated audit."},
            headers=h,
        )
        assert r2.status_code == 400

    def test_adv_p6_10_superseded_evidence_blocked(
        self, client, admin_user, seeded_framework, db, org_apex
    ):
        """ADV-P6-10: Superseded evidence cannot be linked to audit procedures."""
        h = get_token_headers(admin_user)
        audit = create_apex_audit(client, h)
        proc_resp = client.post(
            f"/api/v1/audits/{audit['id']}/procedures",
            json={"title": "Superseded Evidence Test", "result": "NOT_STARTED"},
            headers=h,
        )
        proc_id = proc_resp.json()["id"]

        subcat = db.query(__import__("app.models.framework", fromlist=["FrameworkSubcategory"]).FrameworkSubcategory).first()
        ctrl = make_control(db, org_apex.id, subcat.id)
        ev = make_evidence(db, org_apex.id, ctrl.id, status=EvidenceStatusEnum.SUPERSEDED)

        r = client.post(
            f"/api/v1/audits/{audit['id']}/procedures/{proc_id}/evidence",
            json={"evidence_id": ev.id},
            headers=h,
        )
        assert r.status_code == 400
        assert "superseded" in r.json()["detail"].lower()

    def test_adv_p6_11_unauthenticated_access_blocked(self, client, seeded_framework):
        """ADV-P6-11: No audit endpoints accessible without authentication."""
        # GET list
        assert client.get("/api/v1/audits").status_code == 401
        # POST create
        assert client.post("/api/v1/audits", json={"title": "X", "objective": "Y", "audit_type": "INTERNAL"}).status_code == 401
        # GET detail
        assert client.get("/api/v1/audits/1").status_code == 401

    def test_adv_p6_12_insufficient_permissions_blocked(
        self, client, viewer_user, admin_user, seeded_framework
    ):
        """ADV-P6-12: Viewer (read-only) is blocked from all write operations."""
        admin_h = get_token_headers(admin_user)
        viewer_h = get_token_headers(viewer_user)
        audit = create_apex_audit(client, admin_h)
        audit_id = audit["id"]

        # Cannot create audit
        r1 = client.post("/api/v1/audits", json={"title": "X", "objective": "Y" * 15, "audit_type": "INTERNAL"}, headers=viewer_h)
        assert r1.status_code == 403

        # Cannot update
        r2 = client.patch(f"/api/v1/audits/{audit_id}", json={"summary": "X"}, headers=viewer_h)
        assert r2.status_code == 403

        # Cannot change status
        r3 = client.post(f"/api/v1/audits/{audit_id}/status", json={"status": "INITIATED"}, headers=viewer_h)
        assert r3.status_code == 403

        # Cannot add scope
        r4 = client.post(f"/api/v1/audits/{audit_id}/scope", json={"organization_control_id": 1}, headers=viewer_h)
        assert r4.status_code == 403

        # Cannot create procedure
        r5 = client.post(f"/api/v1/audits/{audit_id}/procedures", json={"title": "X", "result": "NOT_STARTED"}, headers=viewer_h)
        assert r5.status_code == 403

        # Can still read
        r6 = client.get(f"/api/v1/audits/{audit_id}", headers=viewer_h)
        assert r6.status_code == 200

    def test_adv_p6_13_mass_assignment_protection(
        self, client, admin_user, seeded_framework
    ):
        """ADV-P6-13: Client-supplied authoritative fields (organization_id, status, closed_at, opinion) are ignored/overridden."""
        h = get_token_headers(admin_user)
        # Attempt to create an audit already in COMPLETED status with spoofed org_id and opinion
        resp = client.post(
            "/api/v1/audits",
            json={
                "title": "Mass Assignment Spoof Attempt",
                "objective": "Attempt to bypass lifecycle on creation by supplying status COMPLETED",
                "audit_type": "INTERNAL",
                "organization_id": 99999,
                "status": "COMPLETED",
                "opinion": "UNQUALIFIED",
                "closed_at": "2026-01-01T00:00:00Z",
            },
            headers=h,
        )
        assert resp.status_code == 201
        data = resp.json()
        # Must belong to admin's real organization and start in PLANNED status
        assert data["organization_id"] == admin_user.organization_id
        assert data["status"] == "PLANNED"
        assert data["opinion"] == "UNISSUED"
        assert data["closed_at"] is None

    def test_adv_p6_14_cross_audit_procedure_idor(
        self, client, admin_user, seeded_framework
    ):
        """ADV-P6-14: Procedure belonging to Audit A cannot be accessed or modified via Audit B's endpoint."""
        h = get_token_headers(admin_user)
        audit_a = create_apex_audit(client, h, title="Audit Alpha")
        audit_b = create_apex_audit(client, h, title="Audit Beta")

        proc_resp = client.post(
            f"/api/v1/audits/{audit_a['id']}/procedures",
            json={"title": "Alpha Procedure", "result": "NOT_STARTED"},
            headers=h,
        )
        proc_a_id = proc_resp.json()["id"]

        # Attempt to update Alpha's procedure through Beta's endpoint
        resp = client.patch(
            f"/api/v1/audits/{audit_b['id']}/procedures/{proc_a_id}",
            json={"result": "PASSED", "actual_result": "IDOR exploit attempt"},
            headers=h,
        )
        assert resp.status_code == 404

    def test_adv_p6_15_cross_tenant_lead_auditor_injection(
        self, client, admin_user, meridian_admin_user, seeded_framework
    ):
        """ADV-P6-15: Cannot assign foreign tenant user as lead auditor on audit creation or update."""
        apex_h = get_token_headers(admin_user)
        # Attempt to create with foreign lead auditor
        r1 = client.post(
            "/api/v1/audits",
            json={
                "title": "Foreign Lead Injection",
                "objective": "Attempt to assign foreign tenant user as lead auditor",
                "audit_type": "INTERNAL",
                "lead_auditor_id": meridian_admin_user.id,
            },
            headers=apex_h,
        )
        assert r1.status_code == 400

        # Attempt to update existing audit with foreign lead auditor
        audit = create_apex_audit(client, apex_h)
        r2 = client.patch(
            f"/api/v1/audits/{audit['id']}",
            json={"lead_auditor_id": meridian_admin_user.id},
            headers=apex_h,
        )
        assert r2.status_code == 400

    def test_adv_p6_16_role_permission_matrix_enforcement(
        self, client, db, org_apex, seeded_framework, admin_user, analyst_user, auditor_user, viewer_user
    ):
        """ADV-P6-16: Verify complete role enforcement matrix across all audit actions."""
        from app.core.security import get_password_hash
        # Create MANAGER user
        manager_user = User(
            email="manager@apexfinancial.com",
            hashed_password=get_password_hash("ManagerPass123!"),
            full_name="Governance Manager",
            role=RoleEnum.MANAGER,
            is_active=True,
            organization_id=org_apex.id,
        )
        db.add(manager_user)
        db.commit()
        db.refresh(manager_user)

        admin_h = get_token_headers(admin_user)
        analyst_h = get_token_headers(analyst_user)
        auditor_h = get_token_headers(auditor_user)
        manager_h = get_token_headers(manager_user)
        viewer_h = get_token_headers(viewer_user)

        # 1. GRC Analyst can manage/execute audits
        r_analyst = client.post(
            "/api/v1/audits",
            json={"title": "Analyst Audit", "objective": "Analyst created audit objective", "audit_type": "INTERNAL"},
            headers=analyst_h,
        )
        assert r_analyst.status_code == 201

        # 2. Manager cannot create (audit:manage not in MANAGER perms), but can approve/close
        r_mgr_create = client.post(
            "/api/v1/audits",
            json={"title": "Manager Audit", "objective": "Manager audit objective long enough", "audit_type": "INTERNAL"},
            headers=manager_h,
        )
        assert r_mgr_create.status_code == 403

        # 3. Manager can close COMPLETED audit (audit:close)
        audit = create_apex_audit(client, admin_h, title="Closure Test Audit")
        advance_audit(client, admin_h, audit["id"], "COMPLETED")
        r_mgr_close = client.post(
            f"/api/v1/audits/{audit['id']}/close",
            json={"closure_notes": "Manager closing with audit:close permission."},
            headers=manager_h,
        )
        assert r_mgr_close.status_code == 200
        assert r_mgr_close.json()["status"] == "CLOSED"
