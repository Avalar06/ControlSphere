"""
tests/test_phase6_audit.py — Phase 6 audit opinion, closure, and multi-entity integration tests.
"""
import pytest
from sqlalchemy.orm import Session
from tests.conftest import get_token_headers
from app.core.permissions import RoleEnum
from app.core.security import get_password_hash
from app.models.user import User
from app.models.control import OrganizationControl, ImplementationStatusEnum, PriorityEnum
from app.models.evidence import EvidenceItem, EvidenceStatusEnum


def make_audit(client, headers, **kwargs):
    payload = {
        "title": "Opinion & Closure Test Audit",
        "objective": "Full end-to-end audit workflow including opinion issuance and closure",
        "audit_type": "INTERNAL",
    }
    payload.update(kwargs)
    resp = client.post("/api/v1/audits", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def advance_to_status(client, headers, audit_id, target_status):
    transitions = ["INITIATED", "FIELDWORK", "REVIEW", "REPORTING", "COMPLETED"]
    for s in transitions:
        resp = client.post(f"/api/v1/audits/{audit_id}/status", json={"status": s}, headers=headers)
        assert resp.status_code == 200, f"Failed to advance to {s}: {resp.text}"
        if s == target_status:
            break


class TestAuditOpinion:
    def test_admin_can_issue_opinion(self, client, admin_user, seeded_framework):
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)
        advance_to_status(client, headers, audit["id"], "REVIEW")

        resp = client.post(
            f"/api/v1/audits/{audit['id']}/opinion",
            json={"opinion": "UNQUALIFIED", "opinion_notes": "All controls are effectively implemented and no material gaps were found."},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["opinion"] == "UNQUALIFIED"
        assert data["opinion_issued_by_id"] is not None
        assert data["opinion_issued_at"] is not None

    def test_opinion_requires_review_or_later_status(self, client, admin_user, seeded_framework):
        """Cannot issue opinion while in PLANNED or INITIATED status."""
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)  # PLANNED
        resp = client.post(
            f"/api/v1/audits/{audit['id']}/opinion",
            json={"opinion": "UNQUALIFIED", "opinion_notes": "Premature opinion attempt on a planned audit."},
            headers=headers,
        )
        assert resp.status_code == 400
        assert "REVIEW" in resp.json()["detail"] or "status" in resp.json()["detail"].lower()

    def test_cannot_issue_unissued_opinion(self, client, admin_user, seeded_framework):
        """Cannot formally issue UNISSUED as an opinion."""
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)
        advance_to_status(client, headers, audit["id"], "REVIEW")
        resp = client.post(
            f"/api/v1/audits/{audit['id']}/opinion",
            json={"opinion": "UNISSUED"},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_lead_auditor_cannot_issue_own_opinion(self, client, admin_user, auditor_user, seeded_framework, db, org_apex):
        """Separation of duties: lead auditor cannot approve their own engagement."""
        admin_headers = get_token_headers(admin_user)
        auditor_headers = get_token_headers(auditor_user)

        # Admin creates audit and assigns auditor as lead
        resp = client.post(
            "/api/v1/audits",
            json={
                "title": "Self-Opinion Test",
                "objective": "Test separation of duties in audit opinion issuance workflow",
                "audit_type": "INTERNAL",
                "lead_auditor_id": auditor_user.id,
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201
        audit_id = resp.json()["id"]

        # Advance audit to REVIEW
        for s in ["INITIATED", "FIELDWORK", "REVIEW"]:
            r = client.post(f"/api/v1/audits/{audit_id}/status", json={"status": s}, headers=admin_headers)
            assert r.status_code == 200

        # Auditor attempts to issue opinion on their own engagement
        resp = client.post(
            f"/api/v1/audits/{audit_id}/opinion",
            json={"opinion": "UNQUALIFIED", "opinion_notes": "Self-reviewing my own audit engagement."},
            headers=auditor_headers,
        )
        assert resp.status_code == 400
        assert "separation of duties" in resp.json()["detail"].lower() or "lead auditor" in resp.json()["detail"].lower()

    def test_viewer_cannot_issue_opinion(self, client, viewer_user, admin_user, seeded_framework):
        admin_headers = get_token_headers(admin_user)
        audit = make_audit(client, admin_headers)
        advance_to_status(client, admin_headers, audit["id"], "REVIEW")

        viewer_headers = get_token_headers(viewer_user)
        resp = client.post(
            f"/api/v1/audits/{audit['id']}/opinion",
            json={"opinion": "QUALIFIED", "opinion_notes": "Unauthorized opinion attempt by viewer."},
            headers=viewer_headers,
        )
        assert resp.status_code == 403

    def test_all_valid_opinions_accepted(self, client, admin_user, seeded_framework):
        headers = get_token_headers(admin_user)
        for opinion_value in ["UNQUALIFIED", "QUALIFIED", "ADVERSE", "DISCLAIMER"]:
            audit = make_audit(client, headers, title=f"Opinion Test {opinion_value}")
            advance_to_status(client, headers, audit["id"], "REVIEW")
            resp = client.post(
                f"/api/v1/audits/{audit['id']}/opinion",
                json={"opinion": opinion_value, "opinion_notes": f"Issuing {opinion_value} opinion for validation test."},
                headers=headers,
            )
            assert resp.status_code == 200, f"Failed for opinion {opinion_value}: {resp.text}"
            assert resp.json()["opinion"] == opinion_value


class TestAuditClosure:
    def test_full_workflow_to_closure(self, client, admin_user, seeded_framework):
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)
        audit_id = audit["id"]
        advance_to_status(client, headers, audit_id, "COMPLETED")

        resp = client.post(
            f"/api/v1/audits/{audit_id}/close",
            json={"closure_notes": "All fieldwork, review, and reporting are complete. No outstanding items."},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "CLOSED"
        assert data["closed_at"] is not None
        assert data["closed_by_id"] is not None

    def test_viewer_cannot_close_audit(self, client, viewer_user, admin_user, seeded_framework):
        admin_headers = get_token_headers(admin_user)
        audit = make_audit(client, admin_headers)
        advance_to_status(client, admin_headers, audit["id"], "COMPLETED")

        viewer_headers = get_token_headers(viewer_user)
        resp = client.post(
            f"/api/v1/audits/{audit['id']}/close",
            json={"closure_notes": "Unauthorized viewer closure attempt."},
            headers=viewer_headers,
        )
        assert resp.status_code == 403

    def test_closure_requires_notes(self, client, admin_user, seeded_framework):
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)
        advance_to_status(client, headers, audit["id"], "COMPLETED")
        resp = client.post(
            f"/api/v1/audits/{audit['id']}/close",
            json={"closure_notes": "    "},
            headers=headers,
        )
        # Notes too short after strip — should fail validation
        assert resp.status_code in (400, 422)

    def test_cannot_close_already_closed_audit(self, client, admin_user, seeded_framework):
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)
        audit_id = audit["id"]
        advance_to_status(client, headers, audit_id, "COMPLETED")
        client.post(
            f"/api/v1/audits/{audit_id}/close",
            json={"closure_notes": "First closure."},
            headers=headers,
        )
        resp2 = client.post(
            f"/api/v1/audits/{audit_id}/close",
            json={"closure_notes": "Second closure attempt."},
            headers=headers,
        )
        assert resp2.status_code == 400


class TestAuditTenantIsolation:
    def test_org_cannot_see_other_orgs_audits(self, client, admin_user, meridian_admin_user, seeded_framework):
        apex_headers = get_token_headers(admin_user)
        meridian_headers = get_token_headers(meridian_admin_user)

        # Create audit in apex
        resp = client.post(
            "/api/v1/audits",
            json={"title": "Apex Secret Audit", "objective": "Sensitive apex internal audit objective", "audit_type": "INTERNAL"},
            headers=apex_headers,
        )
        apex_audit_id = resp.json()["id"]

        # Meridian cannot read apex's audit
        resp2 = client.get(f"/api/v1/audits/{apex_audit_id}", headers=meridian_headers)
        assert resp2.status_code == 404

    def test_audit_list_is_tenant_scoped(self, client, admin_user, meridian_admin_user, seeded_framework):
        apex_headers = get_token_headers(admin_user)
        meridian_headers = get_token_headers(meridian_admin_user)

        client.post("/api/v1/audits", json={"title": "Apex Audit", "objective": "Apex audit objective long enough", "audit_type": "INTERNAL"}, headers=apex_headers)
        client.post("/api/v1/audits", json={"title": "Meridian Audit", "objective": "Meridian audit objective long enough", "audit_type": "INTERNAL"}, headers=meridian_headers)

        apex_list = client.get("/api/v1/audits", headers=apex_headers).json()
        meridian_list = client.get("/api/v1/audits", headers=meridian_headers).json()

        apex_titles = [a["title"] for a in apex_list]
        meridian_titles = [a["title"] for a in meridian_list]

        assert "Apex Audit" in apex_titles
        assert "Meridian Audit" not in apex_titles
        assert "Meridian Audit" in meridian_titles
        assert "Apex Audit" not in meridian_titles
