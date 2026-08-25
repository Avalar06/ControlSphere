from tests.conftest import get_token_headers


def test_list_controls_creates_defaults(client, admin_user, seeded_framework):
    headers = get_token_headers(admin_user)
    response = client.get(f"/api/v1/controls?framework_id={seeded_framework.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["organization_id"] == admin_user.organization_id
    assert data[0]["status"] == "NOT_STARTED"


def test_update_control_status_and_notes(client, analyst_user, seeded_framework):
    headers = get_token_headers(analyst_user)
    # First list to get control ID
    list_res = client.get("/api/v1/controls", headers=headers)
    assert list_res.status_code == 200
    ctrl = list_res.json()[0]

    # Update control
    update_res = client.patch(
        f"/api/v1/controls/{ctrl['id']}",
        headers=headers,
        json={
            "status": "IMPLEMENTED",
            "priority": "HIGH",
            "implementation_statement": "MFA enforced through corporate IdP.",
            "notes": "Reviewed and validated by SecOps.",
        },
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["status"] == "IMPLEMENTED"
    assert updated_data["priority"] == "HIGH"
    assert updated_data["implementation_statement"] == "MFA enforced through corporate IdP."


def test_viewer_cannot_update_control(client, viewer_user, seeded_framework, admin_user):
    # Ensure control exists via admin
    admin_headers = get_token_headers(admin_user)
    list_res = client.get("/api/v1/controls", headers=admin_headers)
    ctrl = list_res.json()[0]

    # Viewer attempt to update
    viewer_headers = get_token_headers(viewer_user)
    update_res = client.patch(
        f"/api/v1/controls/{ctrl['id']}",
        headers=viewer_headers,
        json={"status": "IMPLEMENTED"},
    )
    assert update_res.status_code == 403


def test_cross_tenant_control_isolation(client, admin_user, meridian_admin_user, seeded_framework):
    admin_headers = get_token_headers(admin_user)
    list_res = client.get("/api/v1/controls", headers=admin_headers)
    apex_ctrl = list_res.json()[0]

    # Meridian admin attempts to update Apex control
    meridian_headers = get_token_headers(meridian_admin_user)
    meridian_update = client.patch(
        f"/api/v1/controls/{apex_ctrl['id']}",
        headers=meridian_headers,
        json={"status": "IMPLEMENTED"},
    )
    assert meridian_update.status_code == 404


def test_control_assign_foreign_org_owner_rejected(client, admin_user, meridian_admin_user, seeded_framework):
    admin_headers = get_token_headers(admin_user)
    list_res = client.get("/api/v1/controls", headers=admin_headers)
    ctrl = list_res.json()[0]

    response = client.patch(
        f"/api/v1/controls/{ctrl['id']}",
        headers=admin_headers,
        json={"owner_id": meridian_admin_user.id},
    )
    assert response.status_code == 400
    assert "does not belong to your organization" in response.json()["detail"]


def test_framework_progress_calculation(client, analyst_user, seeded_framework):
    headers = get_token_headers(analyst_user)
    # Get controls and update some statuses
    list_res = client.get("/api/v1/controls", headers=headers)
    controls = list_res.json()
    
    # Update first 2 to IMPLEMENTED
    for c in controls[:2]:
        client.patch(
            f"/api/v1/controls/{c['id']}",
            headers=headers,
            json={"status": "IMPLEMENTED"},
        )
    
    # Update next 2 to PARTIALLY_IMPLEMENTED
    for c in controls[2:4]:
        client.patch(
            f"/api/v1/controls/{c['id']}",
            headers=headers,
            json={"status": "PARTIALLY_IMPLEMENTED"},
        )

    # Check progress endpoint
    prog_res = client.get(f"/api/v1/frameworks/{seeded_framework.id}/progress", headers=headers)
    assert prog_res.status_code == 200
    prog = prog_res.json()
    assert prog["implemented_count"] == 2
    assert prog["partially_implemented_count"] == 2
    assert prog["compliance_score_pct"] > 0
    assert "GV" in prog["by_function"]