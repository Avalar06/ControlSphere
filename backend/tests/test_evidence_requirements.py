from tests.conftest import get_token_headers


def test_create_and_list_evidence_requirements(client, analyst_user, seeded_framework):
    headers = get_token_headers(analyst_user)
    # Get a control ID
    list_ctrl = client.get("/api/v1/controls", headers=headers)
    ctrl_id = list_ctrl.json()[0]["id"]

    # Create requirement
    req_res = client.post(
        "/api/v1/evidence/requirements",
        headers=headers,
        json={
            "organization_control_id": ctrl_id,
            "title": "MFA Configuration Screenshot",
            "description": "Screenshot of IdP tenant MFA enforcement settings.",
            "evidence_type": "SCREENSHOT",
            "is_required": True,
            "guidance": "Must show Conditional Access policy with MFA requirement enabled for All Users.",
        },
    )
    assert req_res.status_code == 201
    req_data = req_res.json()
    assert req_data["title"] == "MFA Configuration Screenshot"
    assert req_data["evidence_type"] == "SCREENSHOT"
    assert req_data["is_required"] is True

    # List requirements
    list_res = client.get(f"/api/v1/evidence/requirements?organization_control_id={ctrl_id}", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1


def test_update_and_delete_evidence_requirement(client, analyst_user, seeded_framework):
    headers = get_token_headers(analyst_user)
    ctrl_id = client.get("/api/v1/controls", headers=headers).json()[0]["id"]

    create_res = client.post(
        "/api/v1/evidence/requirements",
        headers=headers,
        json={
            "organization_control_id": ctrl_id,
            "title": "Access Review Log",
            "evidence_type": "LOG_EXPORT",
        },
    )
    req_id = create_res.json()["id"]

    # Update
    patch_res = client.patch(
        f"/api/v1/evidence/requirements/{req_id}",
        headers=headers,
        json={"title": "Quarterly Access Review Log (Q3)", "is_required": False},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["title"] == "Quarterly Access Review Log (Q3)"
    assert patch_res.json()["is_required"] is False

    # Delete
    del_res = client.delete(f"/api/v1/evidence/requirements/{req_id}", headers=headers)
    assert del_res.status_code == 204

    # Verify deleted
    get_res = client.get(f"/api/v1/evidence/requirements/{req_id}", headers=headers)
    assert get_res.status_code == 404


def test_cross_tenant_evidence_requirement_isolation(client, analyst_user, meridian_admin_user, seeded_framework):
    apex_headers = get_token_headers(analyst_user)
    ctrl_id = client.get("/api/v1/controls", headers=apex_headers).json()[0]["id"]

    create_res = client.post(
        "/api/v1/evidence/requirements",
        headers=apex_headers,
        json={
            "organization_control_id": ctrl_id,
            "title": "Apex Confidential Requirement",
            "evidence_type": "DOCUMENT",
        },
    )
    req_id = create_res.json()["id"]

    # Meridian admin attempts to read Apex requirement
    meridian_headers = get_token_headers(meridian_admin_user)
    get_res = client.get(f"/api/v1/evidence/requirements/{req_id}", headers=meridian_headers)
    assert get_res.status_code == 404

    # Meridian admin attempts to update Apex requirement
    patch_res = client.patch(
        f"/api/v1/evidence/requirements/{req_id}",
        headers=meridian_headers,
        json={"title": "Tampered Requirement"},
    )
    assert patch_res.status_code == 404


def test_viewer_cannot_manage_evidence_requirements(client, viewer_user, seeded_framework, admin_user):
    admin_headers = get_token_headers(admin_user)
    ctrl_id = client.get("/api/v1/controls", headers=admin_headers).json()[0]["id"]

    viewer_headers = get_token_headers(viewer_user)
    res = client.post(
        "/api/v1/evidence/requirements",
        headers=viewer_headers,
        json={"organization_control_id": ctrl_id, "title": "Unauthorized Requirement"},
    )
    assert res.status_code == 403