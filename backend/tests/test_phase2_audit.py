from tests.conftest import get_token_headers


def test_control_update_generates_audit_log(client, analyst_user, admin_user, seeded_framework):
    analyst_headers = get_token_headers(analyst_user)
    list_res = client.get("/api/v1/controls", headers=analyst_headers)
    ctrl = list_res.json()[0]

    # Update control status
    client.patch(
        f"/api/v1/controls/{ctrl['id']}",
        headers=analyst_headers,
        json={"status": "IMPLEMENTED"},
    )

    # Check audit log as admin
    admin_headers = get_token_headers(admin_user)
    audit_res = client.get("/api/v1/audit-logs?action=control.status.change", headers=admin_headers)
    assert audit_res.status_code == 200
    logs = audit_res.json()
    assert len(logs) >= 1
    assert logs[0]["actor_email"] == analyst_user.email
    assert logs[0]["resource_type"] == "CONTROL"


def test_policy_lifecycle_generates_audit_logs(client, analyst_user, admin_user):
    analyst_headers = get_token_headers(analyst_user)
    create_res = client.post(
        "/api/v1/policies",
        headers=analyst_headers,
        json={"title": "Audit Test Policy", "initial_content": "Content"},
    )
    pol_id = create_res.json()["id"]

    # Transition status
    client.post(
        f"/api/v1/policies/{pol_id}/status",
        headers=analyst_headers,
        json={"status": "UNDER_REVIEW"},
    )

    # Check audit logs
    admin_headers = get_token_headers(admin_user)
    audit_create = client.get("/api/v1/audit-logs?action=policy.create", headers=admin_headers)
    assert audit_create.status_code == 200
    assert len(audit_create.json()) >= 1

    audit_status = client.get("/api/v1/audit-logs?action=policy.submit_review", headers=admin_headers)
    assert audit_status.status_code == 200
    assert len(audit_status.json()) >= 1