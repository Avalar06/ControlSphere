import io
from tests.conftest import get_token_headers


def test_phase3_audit_trail_coverage(client, analyst_user, admin_user, auditor_user, seeded_framework):
    analyst_headers = get_token_headers(analyst_user)
    ctrl_id = client.get("/api/v1/controls", headers=analyst_headers).json()[0]["id"]

    # 1. Create requirement -> audit log: evidence.requirement.create
    req_res = client.post(
        "/api/v1/evidence/requirements",
        headers=analyst_headers,
        json={"organization_control_id": ctrl_id, "title": "Audit Target Requirement"},
    )
    req_id = req_res.json()["id"]

    # 2. Upload file -> audit log: evidence.upload
    files = {"file": ("evidence.pdf", io.BytesIO(b"%PDF-1.4 Evidence Data"), "application/pdf")}
    ev_res = client.post(
        "/api/v1/evidence/upload",
        headers=analyst_headers,
        data={"organization_control_id": str(ctrl_id), "title": "Audit Target Evidence"},
        files=files,
    )
    ev_id = ev_res.json()["id"]

    # 3. Submit review -> audit log: evidence.submit_review
    client.post(f"/api/v1/evidence/{ev_id}/submit-review", headers=analyst_headers)

    # 4. Review accept -> audit log: evidence.accept
    auditor_headers = get_token_headers(auditor_user)
    client.post(
        f"/api/v1/evidence/{ev_id}/review",
        headers=auditor_headers,
        json={"decision": "ACCEPT", "review_notes": "Accepted by auditor."},
    )

    # 5. Download -> audit log: evidence.download
    client.get(f"/api/v1/evidence/{ev_id}/download", headers=analyst_headers)

    # Check all audit logs as admin
    admin_headers = get_token_headers(admin_user)
    audit_res = client.get("/api/v1/audit-logs?limit=50", headers=admin_headers)
    assert audit_res.status_code == 200
    actions = [log["action"] for log in audit_res.json()]

    assert "evidence.requirement.create" in actions
    assert "evidence.upload" in actions
    assert "evidence.submit_review" in actions
    assert "evidence.accept" in actions
    assert "evidence.download" in actions