"""
tests/test_audit_lifecycle.py — Phase 6 audit lifecycle state machine tests.
"""
import pytest
from tests.conftest import get_token_headers


def make_audit(client, headers, **kwargs):
    payload = {
        "title": "Lifecycle Test Audit",
        "objective": "Test state machine transitions for audit lifecycle",
        "audit_type": "INTERNAL",
    }
    payload.update(kwargs)
    resp = client.post("/api/v1/audits", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def transition(client, headers, audit_id: int, new_status: str) -> dict:
    resp = client.post(
        f"/api/v1/audits/{audit_id}/status",
        json={"status": new_status},
        headers=headers,
    )
    return resp


class TestAuditLifecycle:
    def test_full_forward_lifecycle(self, client, admin_user, seeded_framework):
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)
        audit_id = audit["id"]
        assert audit["status"] == "PLANNED"

        for next_status in ["INITIATED", "FIELDWORK", "REVIEW", "REPORTING", "COMPLETED"]:
            resp = transition(client, headers, audit_id, next_status)
            assert resp.status_code == 200, f"Failed transition to {next_status}: {resp.text}"
            assert resp.json()["status"] == next_status

    def test_close_completed_audit(self, client, admin_user, seeded_framework):
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)
        audit_id = audit["id"]
        for s in ["INITIATED", "FIELDWORK", "REVIEW", "REPORTING", "COMPLETED"]:
            transition(client, headers, audit_id, s)

        resp = client.post(
            f"/api/v1/audits/{audit_id}/close",
            json={"closure_notes": "All procedures complete. Audit formally closed."},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "CLOSED"

    def test_invalid_transition_planned_to_fieldwork(self, client, admin_user, seeded_framework):
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)
        audit_id = audit["id"]
        # Cannot go from PLANNED directly to FIELDWORK
        resp = transition(client, headers, audit_id, "FIELDWORK")
        assert resp.status_code == 400
        assert "Invalid transition" in resp.json()["detail"]

    def test_cannot_close_planned_audit(self, client, admin_user, seeded_framework):
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)
        resp = client.post(
            f"/api/v1/audits/{audit['id']}/close",
            json={"closure_notes": "Forced closure attempt"},
            headers=headers,
        )
        assert resp.status_code == 400

    def test_closed_audit_is_immutable(self, client, admin_user, seeded_framework):
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)
        audit_id = audit["id"]
        for s in ["INITIATED", "FIELDWORK", "REVIEW", "REPORTING", "COMPLETED"]:
            transition(client, headers, audit_id, s)
        client.post(
            f"/api/v1/audits/{audit_id}/close",
            json={"closure_notes": "Properly closed."},
            headers=headers,
        )

        # Any further transition must fail
        resp = transition(client, headers, audit_id, "COMPLETED")
        assert resp.status_code == 400

        # Update must fail
        resp2 = client.patch(
            f"/api/v1/audits/{audit_id}",
            json={"summary": "Trying to modify closed audit"},
            headers=headers,
        )
        assert resp2.status_code == 400

    def test_backward_transition_allowed(self, client, admin_user, seeded_framework):
        """Audits can step back one step in lifecycle."""
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)
        audit_id = audit["id"]
        transition(client, headers, audit_id, "INITIATED")
        transition(client, headers, audit_id, "FIELDWORK")

        # Step back to INITIATED
        resp = transition(client, headers, audit_id, "INITIATED")
        assert resp.status_code == 200
        assert resp.json()["status"] == "INITIATED"

    def test_viewer_cannot_change_status(self, client, viewer_user, admin_user, seeded_framework):
        admin_headers = get_token_headers(admin_user)
        audit = make_audit(client, admin_headers)
        viewer_headers = get_token_headers(viewer_user)
        resp = transition(client, viewer_headers, audit["id"], "INITIATED")
        assert resp.status_code == 403
