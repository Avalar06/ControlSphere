from app.models.audit_log import AuditLog
from tests.conftest import get_token_headers


def test_login_creates_audit_log(db, client, admin_user):
    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={"email": admin_user.email, "password": "AdminPassword123!"},
    )
    assert response.status_code == 200

    # Verify audit log in DB
    log = (
        db.query(AuditLog)
        .filter(AuditLog.actor_email == admin_user.email, AuditLog.action == "auth.login.success")
        .first()
    )
    assert log is not None
    assert log.organization_id == admin_user.organization_id
    assert log.status == "SUCCESS"


def test_failed_login_creates_audit_log(db, client, admin_user):
    client.post(
        "/api/v1/auth/login",
        json={"email": admin_user.email, "password": "WrongPassword123!"},
    )

    log = (
        db.query(AuditLog)
        .filter(AuditLog.actor_email == admin_user.email, AuditLog.action == "auth.login.failed")
        .first()
    )
    assert log is not None
    assert log.status == "FAILURE"


def test_user_creation_creates_audit_log(db, client, admin_user):
    headers = get_token_headers(admin_user)
    client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "email": "audit.test@apexfinancial.com",
            "password": "TestPassword123!",
            "full_name": "Audit Test User",
            "role": "VIEWER",
        },
    )

    log = (
        db.query(AuditLog)
        .filter(AuditLog.action == "user.create")
        .first()
    )
    assert log is not None
    assert log.actor_email == admin_user.email
    assert log.resource_type == "USER"


def test_forbidden_access_creates_audit_log(db, client, viewer_user):
    headers = get_token_headers(viewer_user)
    client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "email": "forbidden@apexfinancial.com",
            "password": "TestPassword123!",
            "full_name": "Forbidden Test",
            "role": "VIEWER",
        },
    )

    log = (
        db.query(AuditLog)
        .filter(AuditLog.actor_email == viewer_user.email, AuditLog.action == "auth.forbidden")
        .first()
    )
    assert log is not None
    assert log.status == "UNAUTHORIZED"