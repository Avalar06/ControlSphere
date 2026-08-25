from tests.conftest import get_token_headers


def test_list_frameworks(client, admin_user, seeded_framework):
    headers = get_token_headers(admin_user)
    response = client.get("/api/v1/frameworks", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    nist = data[0]
    assert nist["identifier"] == "NIST-CSF-2.0"
    assert nist["total_functions"] == 6
    assert nist["total_categories"] == 22
    assert nist["total_subcategories"] > 0


def test_get_framework_by_id(client, viewer_user, seeded_framework):
    headers = get_token_headers(viewer_user)
    response = client.get(f"/api/v1/frameworks/{seeded_framework.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["identifier"] == "NIST-CSF-2.0"
    assert data["version"] == "2.0"


def test_get_framework_tree(client, analyst_user, seeded_framework):
    headers = get_token_headers(analyst_user)
    response = client.get(f"/api/v1/frameworks/{seeded_framework.id}/tree", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["identifier"] == "NIST-CSF-2.0"
    assert len(data["functions"]) == 6
    func_identifiers = [f["identifier"] for f in data["functions"]]
    assert func_identifiers == ["GV", "ID", "PR", "DE", "RS", "RC"]


def test_unauthenticated_framework_access(client, seeded_framework):
    response = client.get(f"/api/v1/frameworks/{seeded_framework.id}")
    assert response.status_code == 401


def test_invalid_framework_id(client, admin_user):
    headers = get_token_headers(admin_user)
    response = client.get("/api/v1/frameworks/99999", headers=headers)
    assert response.status_code == 404