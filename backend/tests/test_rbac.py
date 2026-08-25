from app.core.permissions import RoleEnum
from app.core.security import get_password_hash
from app.models.user import User
from tests.conftest import get_token_headers


def test_admin_can_create_user(client, admin_user):
    headers = get_token_headers(admin_user)
    response = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "email": "new.analyst@apexfinancial.com",
            "password": "NewUserPass123!",
            "full_name": "New GRC Analyst",
            "role": "GRC_ANALYST",
            "is_active": True,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new.analyst@apexfinancial.com"
    assert data["organization_id"] == admin_user.organization_id


def test_viewer_cannot_create_user(client, viewer_user):
    headers = get_token_headers(viewer_user)
    response = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "email": "unauthorized.create@apexfinancial.com",
            "password": "NewUserPass123!",
            "full_name": "Unauthorized User",
            "role": "GRC_ANALYST",
        },
    )
    assert response.status_code == 403


def test_grc_analyst_cannot_create_user(client, analyst_user):
    headers = get_token_headers(analyst_user)
    response = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "email": "analyst.create@apexfinancial.com",
            "password": "NewUserPass123!",
            "full_name": "Unauthorized User",
            "role": "VIEWER",
        },
    )
    assert response.status_code == 403


def test_admin_can_update_organization(client, admin_user):
    headers = get_token_headers(admin_user)
    response = client.patch(
        "/api/v1/organizations/me",
        headers=headers,
        json={"name": "Apex Financial Corporation"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Apex Financial Corporation"


def test_auditor_cannot_update_organization(client, auditor_user):
    headers = get_token_headers(auditor_user)
    response = client.patch(
        "/api/v1/organizations/me",
        headers=headers,
        json={"name": "Tampered Org Name"},
    )
    assert response.status_code == 403


def test_auditor_and_admin_can_read_audit_logs(client, admin_user, auditor_user):
    # Admin
    admin_headers = get_token_headers(admin_user)
    res_admin = client.get("/api/v1/audit-logs", headers=admin_headers)
    assert res_admin.status_code == 200

    # Auditor
    auditor_headers = get_token_headers(auditor_user)
    res_auditor = client.get("/api/v1/audit-logs", headers=auditor_headers)
    assert res_auditor.status_code == 200


def test_viewer_cannot_read_audit_logs(client, viewer_user):
    headers = get_token_headers(viewer_user)
    response = client.get("/api/v1/audit-logs", headers=headers)
    assert response.status_code == 403


def test_sole_admin_cannot_self_demote(client, admin_user):
    headers = get_token_headers(admin_user)
    response = client.patch(
        f"/api/v1/users/{admin_user.id}",
        headers=headers,
        json={"role": "VIEWER"},
    )
    assert response.status_code == 400
    assert "sole active Administrator" in response.json()["detail"]


def test_sole_admin_cannot_deactivate_self(client, admin_user):
    headers = get_token_headers(admin_user)
    response = client.patch(
        f"/api/v1/users/{admin_user.id}",
        headers=headers,
        json={"is_active": False},
    )
    assert response.status_code == 400
    assert "sole active Administrator" in response.json()["detail"]


def test_user_email_collision_prevented_on_update(client, db, admin_user, org_apex):
    # Create second user in org
    second_user = User(
        email="second.user@apexfinancial.com",
        hashed_password=get_password_hash("Password123!"),
        full_name="Second User",
        role=RoleEnum.VIEWER,
        is_active=True,
        organization_id=org_apex.id,
    )
    db.add(second_user)
    db.commit()
    db.refresh(second_user)

    headers = get_token_headers(admin_user)
    # Attempt to update second_user's email to admin_user's email
    response = client.patch(
        f"/api/v1/users/{second_user.id}",
        headers=headers,
        json={"email": admin_user.email},
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]