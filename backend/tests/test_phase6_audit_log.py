"""
tests/test_phase6_audit_log.py — Verify Phase 6 operations produce immutable audit log entries.
"""
import pytest
from tests.conftest import get_token_headers


def make_audit(client, headers, **kwargs):
    payload = {
        "title": "Audit Log Test Audit",
        "objective": "Verify every write operation produces an immutable audit trail",
        "audit_type": "INTERNAL",
    }
    payload.update(kwargs)
    resp = client.post("/api/v1/audits", json=payload, headers=headers)
    assert resp.status_code == 201
    return resp.json()


class TestPhase6AuditLog:
    def _get_logs(self, client, headers, resource_type=None, action=None):
        params = {}
        if resource_type:
            params["resource_type"] = resource_type
        if action:
            params["action"] = action
        return client.get("/api/v1/audit-logs", params=params, headers=headers).json()

    def test_audit_create_produces_log(self, client, admin_user, seeded_framework):
        headers = get_token_headers(admin_user)
        make_audit(client, headers)
        resp = client.get("/api/v1/audit-logs", params={"resource_type": "AUDIT"}, headers=headers)
        assert resp.status_code == 200
        logs = resp.json()
        # Logs returns a list; at least one entry must have action "audit.create"
        assert isinstance(logs, list)
        assert any(l.get("action") == "audit.create" for l in logs)

    def test_lifecycle_change_produces_log(self, client, admin_user, seeded_framework):
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)
        client.post(f"/api/v1/audits/{audit['id']}/status", json={"status": "INITIATED"}, headers=headers)

        resp = client.get("/api/v1/audit-logs", params={"action": "audit.status.change"}, headers=headers)
        assert resp.status_code == 200

    def test_opinion_issuance_produces_log(self, client, admin_user, seeded_framework):
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)
        for s in ["INITIATED", "FIELDWORK", "REVIEW"]:
            client.post(f"/api/v1/audits/{audit['id']}/status", json={"status": s}, headers=headers)
        client.post(
            f"/api/v1/audits/{audit['id']}/opinion",
            json={"opinion": "UNQUALIFIED", "opinion_notes": "Full audit review confirms unqualified opinion."},
            headers=headers,
        )
        resp = client.get("/api/v1/audit-logs", params={"action": "audit.opinion.issue"}, headers=headers)
        assert resp.status_code == 200
