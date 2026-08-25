from app.models.audit_log import AuditLog
from app.services.audit_service import AuditService
from tests.conftest import get_token_headers


def test_user_list_tenant_isolation(client, admin_user, meridian_admin_user):
    headers_apex = get_token_headers(admin_user)
    response_apex = client.get("/api/v1/users", headers=headers_apex)
    assert response_apex.status_code == 200
    apex_user_emails = [u["email"] for u in response_apex.json()]
    assert admin_user.email in apex_user_emails
    assert meridian_admin_user.email not in apex_user_emails

    headers_meridian = get_token_headers(meridian_admin_user)
    response_meridian = client.get("/api/v1/users", headers=headers_meridian)
    assert response_meridian.status_code == 200
    meridian_user_emails = [u["email"] for u in response_meridian.json()]
    assert meridian_admin_user.email in meridian_user_emails
    assert admin_user.email not in meridian_user_emails


def test_cannot_access_other_tenant_user_by_id(client, admin_user, meridian_admin_user):
    headers_apex = get_token_headers(admin_user)
    response = client.get(f"/api/v1/users/{meridian_admin_user.id}", headers=headers_apex)
    assert response.status_code == 404
    assert "User not found in your organization" in response.json()["detail"]


def test_cannot_modify_other_tenant_user(client, admin_user, meridian_admin_user):
    headers_apex = get_token_headers(admin_user)
    response = client.patch(
        f"/api/v1/users/{meridian_admin_user.id}",
        headers=headers_apex,
        json={"full_name": "Tampered Account Name"},
    )
    assert response.status_code == 404


def test_audit_logs_tenant_isolation(db, client, admin_user, meridian_admin_user, org_apex, org_meridian):
    # Log an event in Apex
    AuditService.log(
        db=db,
        organization_id=org_apex.id,
        actor_id=admin_user.id,
        actor_email=admin_user.email,
        action="apex.action",
        resource_type="TEST",
    )
    # Log an event in Meridian
    AuditService.log(
        db=db,
        organization_id=org_meridian.id,
        actor_id=meridian_admin_user.id,
        actor_email=meridian_admin_user.email,
        action="meridian.action",
        resource_type="TEST",
    )

    headers_apex = get_token_headers(admin_user)
    res_apex = client.get("/api/v1/audit-logs", headers=headers_apex)
    assert res_apex.status_code == 200
    actions_apex = [log["action"] for log in res_apex.json()]
    assert "apex.action" in actions_apex
    assert "meridian.action" not in actions_apex