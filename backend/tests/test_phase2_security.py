from tests.conftest import get_token_headers


def test_cross_tenant_control_read_denied(client, admin_user, meridian_admin_user, seeded_framework):
    # Ensure Apex controls exist
    apex_headers = get_token_headers(admin_user)
    list_res = client.get("/api/v1/controls", headers=apex_headers)
    assert list_res.status_code == 200
    apex_ctrl = list_res.json()[0]

    # Meridian admin attempts to read Apex control by ID
    meridian_headers = get_token_headers(meridian_admin_user)
    get_res = client.get(f"/api/v1/controls/{apex_ctrl['id']}", headers=meridian_headers)
    assert get_res.status_code == 404
    assert get_res.json()["detail"] == "Control not found in your organization"


def test_cross_tenant_control_update_denied(client, admin_user, meridian_admin_user, seeded_framework):
    apex_headers = get_token_headers(admin_user)
    list_res = client.get("/api/v1/controls", headers=apex_headers)
    apex_ctrl = list_res.json()[0]

    meridian_headers = get_token_headers(meridian_admin_user)
    patch_res = client.patch(
        f"/api/v1/controls/{apex_ctrl['id']}",
        headers=meridian_headers,
        json={"status": "IMPLEMENTED"},
    )
    assert patch_res.status_code == 404


def test_control_owner_must_belong_to_same_org(client, admin_user, meridian_admin_user, seeded_framework):
    apex_headers = get_token_headers(admin_user)
    list_res = client.get("/api/v1/controls", headers=apex_headers)
    apex_ctrl = list_res.json()[0]

    patch_res = client.patch(
        f"/api/v1/controls/{apex_ctrl['id']}",
        headers=apex_headers,
        json={"owner_id": meridian_admin_user.id},
    )
    assert patch_res.status_code == 400
    assert "does not belong to your organization" in patch_res.json()["detail"]


def test_unauthorized_roles_cannot_update_control(client, admin_user, auditor_user, viewer_user, seeded_framework):
    apex_headers = get_token_headers(admin_user)
    list_res = client.get("/api/v1/controls", headers=apex_headers)
    apex_ctrl = list_res.json()[0]

    # Auditor cannot update control
    auditor_headers = get_token_headers(auditor_user)
    auditor_patch = client.patch(
        f"/api/v1/controls/{apex_ctrl['id']}",
        headers=auditor_headers,
        json={"status": "IMPLEMENTED"},
    )
    assert auditor_patch.status_code == 403

    # Viewer cannot update control
    viewer_headers = get_token_headers(viewer_user)
    viewer_patch = client.patch(
        f"/api/v1/controls/{apex_ctrl['id']}",
        headers=viewer_headers,
        json={"status": "IMPLEMENTED"},
    )
    assert viewer_patch.status_code == 403


def test_invalid_control_status_rejected(client, analyst_user, seeded_framework):
    analyst_headers = get_token_headers(analyst_user)
    list_res = client.get("/api/v1/controls", headers=analyst_headers)
    ctrl = list_res.json()[0]

    res = client.patch(
        f"/api/v1/controls/{ctrl['id']}",
        headers=analyst_headers,
        json={"status": "INVALID_HACKED_STATUS"},
    )
    assert res.status_code == 422


def test_archived_policy_cannot_be_modified(client, analyst_user):
    headers = get_token_headers(analyst_user)
    create_res = client.post(
        "/api/v1/policies",
        headers=headers,
        json={"title": "Archival Target Policy", "initial_content": "Draft"},
    )
    pol_id = create_res.json()["id"]

    # Archive the policy
    archive_res = client.post(
        f"/api/v1/policies/{pol_id}/status",
        headers=headers,
        json={"status": "ARCHIVED", "reason": "Decommissioning policy"},
    )
    assert archive_res.status_code == 200
    assert archive_res.json()["status"] == "ARCHIVED"

    # Attempt to update metadata on archived policy
    patch_res = client.patch(
        f"/api/v1/policies/{pol_id}",
        headers=headers,
        json={"title": "Modified Title"},
    )
    assert patch_res.status_code == 400
    assert "Cannot modify an archived policy" in patch_res.json()["detail"]


def test_archived_policy_cannot_create_new_version(client, analyst_user):
    headers = get_token_headers(analyst_user)
    create_res = client.post(
        "/api/v1/policies",
        headers=headers,
        json={"title": "Version Target Policy", "initial_content": "Draft"},
    )
    pol_id = create_res.json()["id"]

    client.post(
        f"/api/v1/policies/{pol_id}/status",
        headers=headers,
        json={"status": "ARCHIVED"},
    )

    ver_res = client.post(
        f"/api/v1/policies/{pol_id}/versions",
        headers=headers,
        json={"content": "New content", "change_summary": "Attempting version on archived policy"},
    )
    assert ver_res.status_code == 400
    assert "Cannot add new versions to an archived policy" in ver_res.json()["detail"]


def test_archived_policy_cannot_add_or_remove_mappings(client, analyst_user, seeded_framework):
    headers = get_token_headers(analyst_user)
    create_res = client.post(
        "/api/v1/policies",
        headers=headers,
        json={"title": "Mapping Target Policy", "initial_content": "Draft"},
    )
    pol_id = create_res.json()["id"]

    client.post(
        f"/api/v1/policies/{pol_id}/status",
        headers=headers,
        json={"status": "ARCHIVED"},
    )

    map_res = client.post(
        f"/api/v1/policies/{pol_id}/mappings",
        headers=headers,
        json={"subcategory_id": 1},
    )
    assert map_res.status_code == 400
    assert "Cannot map controls to an archived policy" in map_res.json()["detail"]

    del_res = client.delete(
        f"/api/v1/policies/{pol_id}/mappings/1",
        headers=headers,
    )
    assert del_res.status_code == 400
    assert "Cannot unmap controls from an archived policy" in del_res.json()["detail"]


def test_policy_creation_deduplicates_subcategory_ids(client, analyst_user, seeded_framework):
    headers = get_token_headers(analyst_user)
    tree_res = client.get(f"/api/v1/frameworks/{seeded_framework.id}/tree", headers=headers).json()
    subcat_id = tree_res["functions"][0]["categories"][0]["subcategories"][0]["id"]

    # Pass duplicate subcat_id in array [subcat_id, subcat_id]
    create_res = client.post(
        "/api/v1/policies",
        headers=headers,
        json={
            "title": "Deduplication Test Policy",
            "initial_content": "Content",
            "mapped_subcategory_ids": [subcat_id, subcat_id],
        },
    )
    assert create_res.status_code == 201
    data = create_res.json()
    assert len(data["mapped_subcategories"]) == 1


def test_duplicate_policy_control_mapping_is_idempotent(client, analyst_user, seeded_framework):
    headers = get_token_headers(analyst_user)
    create_res = client.post(
        "/api/v1/policies",
        headers=headers,
        json={"title": "Idempotent Map Test", "initial_content": "Content"},
    )
    pol_id = create_res.json()["id"]

    tree_res = client.get(f"/api/v1/frameworks/{seeded_framework.id}/tree", headers=headers).json()
    subcat_id = tree_res["functions"][0]["categories"][0]["subcategories"][0]["id"]

    # Map once
    map_res1 = client.post(
        f"/api/v1/policies/{pol_id}/mappings",
        headers=headers,
        json={"subcategory_id": subcat_id},
    )
    assert map_res1.status_code == 200
    assert len(map_res1.json()["mapped_subcategories"]) == 1

    # Map second time (idempotent)
    map_res2 = client.post(
        f"/api/v1/policies/{pol_id}/mappings",
        headers=headers,
        json={"subcategory_id": subcat_id},
    )
    assert map_res2.status_code == 200
    assert len(map_res2.json()["mapped_subcategories"]) == 1


def test_policy_lifecycle_rejected_transitions(client, analyst_user):
    headers = get_token_headers(analyst_user)
    create_res = client.post(
        "/api/v1/policies",
        headers=headers,
        json={"title": "Lifecycle Transition Test", "initial_content": "Content"},
    )
    pol_id = create_res.json()["id"]
    assert create_res.json()["status"] == "DRAFT"

    # 1. DRAFT -> PUBLISHED (must go through UNDER_REVIEW -> APPROVED first)
    res = client.post(f"/api/v1/policies/{pol_id}/status", headers=headers, json={"status": "PUBLISHED"})
    assert res.status_code == 400

    # 2. DRAFT -> APPROVED (must go through UNDER_REVIEW)
    res = client.post(f"/api/v1/policies/{pol_id}/status", headers=headers, json={"status": "APPROVED"})
    assert res.status_code == 400

    # Advance to PUBLISHED legitimately
    client.post(f"/api/v1/policies/{pol_id}/status", headers=headers, json={"status": "UNDER_REVIEW"})
    client.post(f"/api/v1/policies/{pol_id}/status", headers=headers, json={"status": "APPROVED"})
    client.post(f"/api/v1/policies/{pol_id}/status", headers=headers, json={"status": "PUBLISHED"})

    # 3. PUBLISHED -> DRAFT (must go through UNDER_REVIEW or ARCHIVED)
    res = client.post(f"/api/v1/policies/{pol_id}/status", headers=headers, json={"status": "DRAFT"})
    assert res.status_code == 400

    # 4. PUBLISHED -> APPROVED (cannot revert to approved directly)
    res = client.post(f"/api/v1/policies/{pol_id}/status", headers=headers, json={"status": "APPROVED"})
    assert res.status_code == 400

    # Archive policy
    client.post(f"/api/v1/policies/{pol_id}/status", headers=headers, json={"status": "ARCHIVED"})

    # 5. ARCHIVED -> PUBLISHED (cannot jump directly to published from archive)
    res = client.post(f"/api/v1/policies/{pol_id}/status", headers=headers, json={"status": "PUBLISHED"})
    assert res.status_code == 400

    # 6. ARCHIVED -> DRAFT (Valid restoration)
    res = client.post(f"/api/v1/policies/{pol_id}/status", headers=headers, json={"status": "DRAFT"})
    assert res.status_code == 200
    assert res.json()["status"] == "DRAFT"


def test_framework_catalog_has_no_mutation_endpoints(client, admin_user, seeded_framework):
    headers = get_token_headers(admin_user)
    
    post_res = client.post("/api/v1/frameworks", headers=headers, json={"name": "Hacked Framework"})
    assert post_res.status_code == 405  # Method Not Allowed

    delete_res = client.delete(f"/api/v1/frameworks/{seeded_framework.id}", headers=headers)
    assert delete_res.status_code == 405  # Method Not Allowed

    patch_res = client.patch(f"/api/v1/frameworks/{seeded_framework.id}", headers=headers, json={"name": "Hacked"})
    assert patch_res.status_code == 405  # Method Not Allowed