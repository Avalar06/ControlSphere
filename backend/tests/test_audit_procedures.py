"""
tests/test_audit_procedures.py — Phase 6 audit procedure CRUD and evidence linking tests.
"""
import io
import pytest
from sqlalchemy.orm import Session
from tests.conftest import get_token_headers
from app.models.control import OrganizationControl, ImplementationStatusEnum, PriorityEnum
from app.models.evidence import EvidenceItem, EvidenceStatusEnum


def make_audit(client, headers, **kwargs):
    payload = {
        "title": "Procedures Test Audit",
        "objective": "Testing audit procedure management end-to-end",
        "audit_type": "INTERNAL",
    }
    payload.update(kwargs)
    resp = client.post("/api/v1/audits", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def make_control(db: Session, org_id: int, subcat_id: int) -> OrganizationControl:
    ctrl = OrganizationControl(
        organization_id=org_id,
        subcategory_id=subcat_id,
        status=ImplementationStatusEnum.IMPLEMENTED,
        priority=PriorityEnum.HIGH,
    )
    db.add(ctrl)
    db.commit()
    db.refresh(ctrl)
    return ctrl


def make_evidence(db: Session, org_id: int, ctrl_id: int) -> EvidenceItem:
    ev = EvidenceItem(
        organization_id=org_id,
        organization_control_id=ctrl_id,
        title="Access Log Export 2026-Q2",
        original_filename="access_logs_q2.pdf",
        stored_filename="access_logs_q2_abc123.pdf",
        file_extension="pdf",
        content_type="application/pdf",
        file_size=204800,
        sha256_hash="a" * 64,
        storage_key=f"org_{org_id}/access_logs.pdf",
        status=EvidenceStatusEnum.ACCEPTED,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


def make_procedure(client, headers, audit_id: int, **kwargs) -> dict:
    payload = {
        "title": "Test Patch Management Controls",
        "objective": "Verify patch management procedures are effective",
        "test_steps": "1. Review patch policy. 2. Inspect recent patch logs.",
        "expected_result": "All systems patched within SLA.",
        "result": "NOT_STARTED",
    }
    payload.update(kwargs)
    resp = client.post(f"/api/v1/audits/{audit_id}/procedures", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestAuditProcedures:
    def test_create_procedure(self, client, admin_user, seeded_framework):
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)
        proc = make_procedure(client, headers, audit["id"])
        assert proc["title"] == "Test Patch Management Controls"
        assert proc["result"] == "NOT_STARTED"
        assert proc["audit_id"] == audit["id"]

    def test_list_procedures(self, client, admin_user, seeded_framework):
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)
        make_procedure(client, headers, audit["id"])
        make_procedure(client, headers, audit["id"], title="Test Access Controls")
        resp = client.get(f"/api/v1/audits/{audit['id']}/procedures", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_update_procedure_result(self, client, admin_user, seeded_framework):
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)
        proc = make_procedure(client, headers, audit["id"])

        resp = client.patch(
            f"/api/v1/audits/{audit['id']}/procedures/{proc['id']}",
            json={"result": "PASSED", "actual_result": "All patches applied within 48h."},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["result"] == "PASSED"
        assert data["actual_result"] == "All patches applied within 48h."

    def test_viewer_cannot_create_procedure(self, client, viewer_user, admin_user, seeded_framework):
        admin_headers = get_token_headers(admin_user)
        audit = make_audit(client, admin_headers)
        viewer_headers = get_token_headers(viewer_user)
        resp = client.post(
            f"/api/v1/audits/{audit['id']}/procedures",
            json={"title": "Blocked", "result": "NOT_STARTED"},
            headers=viewer_headers,
        )
        assert resp.status_code == 403

    def test_procedure_title_required(self, client, admin_user, seeded_framework):
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)
        resp = client.post(
            f"/api/v1/audits/{audit['id']}/procedures",
            json={"result": "NOT_STARTED"},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_cross_tenant_control_cannot_be_linked_to_procedure(
        self, client, admin_user, meridian_admin_user, seeded_framework, db, org_apex, org_meridian
    ):
        apex_headers = get_token_headers(admin_user)
        subcat = db.query(__import__("app.models.framework", fromlist=["FrameworkSubcategory"]).FrameworkSubcategory).first()
        meridian_ctrl = make_control(db, org_meridian.id, subcat.id)

        audit = make_audit(client, apex_headers)
        resp = client.post(
            f"/api/v1/audits/{audit['id']}/procedures",
            json={
                "title": "Cross-Tenant Procedure",
                "result": "NOT_STARTED",
                "organization_control_id": meridian_ctrl.id,
            },
            headers=apex_headers,
        )
        assert resp.status_code == 400


class TestAuditProcedureEvidence:
    def test_link_evidence_to_procedure(self, client, admin_user, seeded_framework, db, org_apex):
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)
        proc = make_procedure(client, headers, audit["id"])

        subcat = db.query(__import__("app.models.framework", fromlist=["FrameworkSubcategory"]).FrameworkSubcategory).first()
        ctrl = make_control(db, org_apex.id, subcat.id)
        ev = make_evidence(db, org_apex.id, ctrl.id)

        resp = client.post(
            f"/api/v1/audits/{audit['id']}/procedures/{proc['id']}/evidence",
            json={"evidence_id": ev.id, "link_notes": "Primary evidence for this test"},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["evidence_id"] == ev.id
        assert data["procedure_id"] == proc["id"]

    def test_cannot_link_cross_tenant_evidence(self, client, admin_user, meridian_admin_user, seeded_framework, db, org_apex, org_meridian):
        apex_headers = get_token_headers(admin_user)
        subcat = db.query(__import__("app.models.framework", fromlist=["FrameworkSubcategory"]).FrameworkSubcategory).first()
        apex_ctrl = make_control(db, org_apex.id, subcat.id)
        meridian_ctrl = make_control(db, org_meridian.id, subcat.id)
        meridian_ev = make_evidence(db, org_meridian.id, meridian_ctrl.id)

        audit = make_audit(client, apex_headers)
        proc = make_procedure(client, apex_headers, audit["id"])

        resp = client.post(
            f"/api/v1/audits/{audit['id']}/procedures/{proc['id']}/evidence",
            json={"evidence_id": meridian_ev.id},
            headers=apex_headers,
        )
        assert resp.status_code == 400

    def test_cannot_link_superseded_evidence(self, client, admin_user, seeded_framework, db, org_apex):
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)
        proc = make_procedure(client, headers, audit["id"])

        subcat = db.query(__import__("app.models.framework", fromlist=["FrameworkSubcategory"]).FrameworkSubcategory).first()
        ctrl = make_control(db, org_apex.id, subcat.id)
        ev = make_evidence(db, org_apex.id, ctrl.id)
        ev.status = EvidenceStatusEnum.SUPERSEDED
        db.commit()

        resp = client.post(
            f"/api/v1/audits/{audit['id']}/procedures/{proc['id']}/evidence",
            json={"evidence_id": ev.id},
            headers=headers,
        )
        assert resp.status_code == 400
        assert "superseded" in resp.json()["detail"].lower()

    def test_unlink_evidence_from_procedure(self, client, admin_user, seeded_framework, db, org_apex):
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)
        proc = make_procedure(client, headers, audit["id"])

        subcat = db.query(__import__("app.models.framework", fromlist=["FrameworkSubcategory"]).FrameworkSubcategory).first()
        ctrl = make_control(db, org_apex.id, subcat.id)
        ev = make_evidence(db, org_apex.id, ctrl.id)

        client.post(
            f"/api/v1/audits/{audit['id']}/procedures/{proc['id']}/evidence",
            json={"evidence_id": ev.id},
            headers=headers,
        )
        resp = client.delete(
            f"/api/v1/audits/{audit['id']}/procedures/{proc['id']}/evidence/{ev.id}",
            headers=headers,
        )
        assert resp.status_code == 204

    def test_link_evidence_duplicate_is_idempotent(self, client, admin_user, seeded_framework, db, org_apex):
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)
        proc = make_procedure(client, headers, audit["id"])

        subcat = db.query(__import__("app.models.framework", fromlist=["FrameworkSubcategory"]).FrameworkSubcategory).first()
        ctrl = make_control(db, org_apex.id, subcat.id)
        ev = make_evidence(db, org_apex.id, ctrl.id)

        r1 = client.post(f"/api/v1/audits/{audit['id']}/procedures/{proc['id']}/evidence", json={"evidence_id": ev.id}, headers=headers)
        r2 = client.post(f"/api/v1/audits/{audit['id']}/procedures/{proc['id']}/evidence", json={"evidence_id": ev.id}, headers=headers)
        assert r1.status_code in (200, 201)
        assert r2.status_code in (200, 201)
        # Same record returned
        assert r1.json()["id"] == r2.json()["id"]
