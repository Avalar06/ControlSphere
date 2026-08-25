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