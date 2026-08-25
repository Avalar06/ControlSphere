from tests.conftest import get_token_headers


def test_create_policy_with_initial_version(client, analyst_user, seeded_framework):
    headers = get_token_headers(analyst_user)
    response = client.post(
        "/api/v1/policies",
        headers=headers,
        json={
            "title": "Access Control Policy",
            "description": "Governs user access and MFA.",
            "policy_type": "ACCESS_CONTROL",
            "initial_content": "# Access Control Policy\n\nMandatory MFA for all users.",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Access Control Policy"
    assert data["status"] == "DRAFT"
    assert data["total_versions"] == 1
    assert data["current_version"]["version_number"] == 1
    assert "Mandatory MFA" in data["current_version"]["content"]


def test_update_policy_metadata(client, analyst_user):
    headers = get_token_headers(analyst_user)
    create_res = client.post(
        "/api/v1/policies",
        headers=headers,
        json={
            "title": "Initial Title",
            "initial_content": "Content v1",
        },
    )
    pol_id = create_res.json()["id"]

    update_res = client.patch(
        f"/api/v1/policies/{pol_id}",
        headers=headers,
        json={"title": "Updated Title", "description": "Updated Description"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["title"] == "Updated Title"
    assert update_res.json()["description"] == "Updated Description"


def test_create_policy_new_version(client, analyst_user):
    headers = get_token_headers(analyst_user)
    create_res = client.post(
        "/api/v1/policies",
        headers=headers,
        json={
            "title": "Password Policy",
            "initial_content": "# v1: 8 character min",
        },
    )
    pol_id = create_res.json()["id"]

    # Create version 2
    v2_res = client.post(
        f"/api/v1/policies/{pol_id}/versions",
        headers=headers,
        json={
            "content": "# v2: 14 character min with MFA requirement",
            "change_summary": "Elevated password length to 14 characters",
        },
    )
    assert v2_res.status_code == 201
    v2_data = v2_res.json()
    assert v2_data["version_number"] == 2
    assert "14 character" in v2_data["content"]

    # Verify policy reflects total_versions = 2
    get_res = client.get(f"/api/v1/policies/{pol_id}", headers=headers)
    assert get_res.json()["total_versions"] == 2
    assert get_res.json()["current_version"]["version_number"] == 2


def test_policy_status_state_machine(client, analyst_user):
    headers = get_token_headers(analyst_user)
    create_res = client.post(
        "/api/v1/policies",
        headers=headers,
        json={"title": "State Test Policy", "initial_content": "Content"},
    )
    pol_id = create_res.json()["id"]
    assert create_res.json()["status"] == "DRAFT"

    # DRAFT -> UNDER_REVIEW (Valid)
    review_res = client.post(
        f"/api/v1/policies/{pol_id}/status",
        headers=headers,
        json={"status": "UNDER_REVIEW", "reason": "Ready for CISO review"},
    )
    assert review_res.status_code == 200
    assert review_res.json()["status"] == "UNDER_REVIEW"

    # UNDER_REVIEW -> APPROVED (Valid)
    approve_res = client.post(
        f"/api/v1/policies/{pol_id}/status",
        headers=headers,
        json={"status": "APPROVED", "reason": "Approved by CISO"},
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "APPROVED"

    # APPROVED -> PUBLISHED (Valid)
    publish_res = client.post(
        f"/api/v1/policies/{pol_id}/status",
        headers=headers,
        json={"status": "PUBLISHED", "reason": "Published to organization"},
    )
    assert publish_res.status_code == 200
    assert publish_res.json()["status"] == "PUBLISHED"

    # PUBLISHED -> DRAFT (Invalid direct transition)
    invalid_res = client.post(
        f"/api/v1/policies/{pol_id}/status",
        headers=headers,
        json={"status": "DRAFT"},
    )
    assert invalid_res.status_code == 400


def test_policy_control_mapping(client, analyst_user, seeded_framework):
    headers = get_token_headers(analyst_user)
    create_res = client.post(
        "/api/v1/policies",
        headers=headers,
        json={"title": "Encryption Policy", "initial_content": "AES-256 only"},
    )
    pol_id = create_res.json()["id"]

    # Get a subcategory ID
    fw_tree = client.get(f"/api/v1/frameworks/{seeded_framework.id}/tree", headers=headers).json()
    subcat_id = fw_tree["functions"][0]["categories"][0]["subcategories"][0]["id"]

    # Map subcategory
    map_res = client.post(
        f"/api/v1/policies/{pol_id}/mappings",
        headers=headers,
        json={"subcategory_id": subcat_id},
    )
    assert map_res.status_code == 200
    assert len(map_res.json()["mapped_subcategories"]) == 1

    # Delete mapping
    del_res = client.delete(f"/api/v1/policies/{pol_id}/mappings/{subcat_id}", headers=headers)
    assert del_res.status_code == 200
    assert len(del_res.json()["mapped_subcategories"]) == 0


def test_cross_tenant_policy_isolation(client, analyst_user, meridian_admin_user):
    apex_headers = get_token_headers(analyst_user)
    create_res = client.post(
        "/api/v1/policies",
        headers=apex_headers,
        json={"title": "Apex Confidential Policy", "initial_content": "Apex Secret"},
    )
    apex_pol_id = create_res.json()["id"]

    # Meridian admin attempts to read Apex policy
    meridian_headers = get_token_headers(meridian_admin_user)
    get_res = client.get(f"/api/v1/policies/{apex_pol_id}", headers=meridian_headers)
    assert get_res.status_code == 404

    # Meridian admin attempts to update Apex policy
    patch_res = client.patch(
        f"/api/v1/policies/{apex_pol_id}",
        headers=meridian_headers,
        json={"title": "Tampered Title"},
    )
    assert patch_res.status_code == 404


def test_viewer_cannot_create_policy(client, viewer_user):
    headers = get_token_headers(viewer_user)
    response = client.post(
        "/api/v1/policies",
        headers=headers,
        json={"title": "Unauthorized Policy", "initial_content": "Content"},
    )
    assert response.status_code == 403