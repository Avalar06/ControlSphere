from datetime import timedelta
from jose import jwt
from app.core.config import settings
from app.core.security import create_access_token
from tests.conftest import get_token_headers


def test_login_success_json(client, admin_user):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": admin_user.email, "password": "AdminPassword123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_success_form(client, admin_user):
    response = client.post(
        "/api/v1/auth/access-token",
        data={"username": admin_user.email, "password": "AdminPassword123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_password(client, admin_user):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": admin_user.email, "password": "WrongPassword123!"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_login_nonexistent_user(client, org_apex):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "unknown@apexfinancial.com", "password": "AnyPassword!"},
    )
    assert response.status_code == 401


def test_read_current_user_me(client, admin_user):
    headers = get_token_headers(admin_user)
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == admin_user.email
    assert data["role"] == "ADMIN"
    assert "permissions" in data
    assert "user:create" in data["permissions"]
    assert data["organization_id"] == admin_user.organization_id


def test_unauthenticated_me_access(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_expired_token_rejected(client, admin_user):
    expired_token = create_access_token(
        subject=admin_user.id,
        organization_id=admin_user.organization_id,
        role=admin_user.role.value,
        expires_delta=timedelta(minutes=-10),  # expired 10 minutes ago
    )
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


def test_tampered_token_signature_rejected(client, admin_user):
    tampered_token = jwt.encode(
        {"sub": str(admin_user.id), "org_id": admin_user.organization_id, "role": "ADMIN"},
        "wrong_secret_key_used_by_attacker",
        algorithm=settings.ALGORITHM,
    )
    headers = {"Authorization": f"Bearer {tampered_token}"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401


def test_malformed_auth_header_rejected(client):
    response = client.get("/api/v1/auth/me", headers={"Authorization": "InvalidHeaderFormat"})
    assert response.status_code == 401


def test_password_length_validation_on_creation(client, admin_user):
    headers = get_token_headers(admin_user)
    # Password too short (<8 chars)
    res_short = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "email": "shortpass@apexfinancial.com",
            "password": "123",
            "full_name": "Short Pass User",
            "role": "VIEWER",
        },
    )
    assert res_short.status_code == 422