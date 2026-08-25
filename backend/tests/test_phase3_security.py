import io
from tests.conftest import get_token_headers


def test_cross_tenant_evidence_read_and_mutation_denied(client, analyst_user, meridian_admin_user, seeded_framework):
    apex_headers = get_token_headers(analyst_user)
    ctrl_id = client.get("/api/v1/controls", headers=apex_headers).json()[0]["id"]

    # Apex uploads evidence
    files = {"file": ("apex_evidence.pdf", io.BytesIO(b"%PDF-1.4 Apex Data"), "application/pdf")}
    ev = client.post(
        "/api/v1/evidence/upload",
        headers=apex_headers,
        data={"organization_control_id": str(ctrl_id), "title": "Apex Evidence"},
        files=files,
    ).json()
    ev_id = ev["id"]

    meridian_headers = get_token_headers(meridian_admin_user)

    # 1. Meridian cannot get Apex evidence
    get_res = client.get(f"/api/v1/evidence/{ev_id}", headers=meridian_headers)
    assert get_res.status_code == 404

    # 2. Meridian cannot patch Apex evidence
    patch_res = client.patch(
        f"/api/v1/evidence/{ev_id}",
        headers=meridian_headers,
        json={"title": "Hacked Title"},
    )
    assert patch_res.status_code == 404

    # 3. Meridian cannot review Apex evidence
    review_res = client.post(
        f"/api/v1/evidence/{ev_id}/review",
        headers=meridian_headers,
        json={"decision": "ACCEPT"},
    )
    assert review_res.status_code == 400 or review_res.status_code == 404

    # 4. Meridian cannot download Apex evidence
    dl_res = client.get(f"/api/v1/evidence/{ev_id}/download", headers=meridian_headers)
    assert dl_res.status_code == 404


def test_file_security_oversized_file(client, analyst_user, seeded_framework):
    headers = get_token_headers(analyst_user)
    ctrl_id = client.get("/api/v1/controls", headers=headers).json()[0]["id"]

    # 26 MB file (exceeds 25 MB limit)
    large_bytes = b"%PDF-" + b"0" * (26 * 1024 * 1024)
    files = {"file": ("oversized.pdf", io.BytesIO(large_bytes), "application/pdf")}
    res = client.post(
        "/api/v1/evidence/upload",
        headers=headers,
        data={"organization_control_id": str(ctrl_id), "title": "Oversized Document"},
        files=files,
    )
    assert res.status_code == 400
    assert "exceeds maximum allowed limit" in res.json()["detail"]


def test_file_security_unsafe_and_absolute_path_filenames(client, analyst_user, seeded_framework):
    headers = get_token_headers(analyst_user)
    ctrl_id = client.get("/api/v1/controls", headers=headers).json()[0]["id"]

    # Windows absolute path filename with script injection characters
    unsafe_name = "C:\\Windows\\System32\\<script>alert(1)</script>.pdf"
    files = {"file": (unsafe_name, io.BytesIO(b"%PDF-1.4 Valid Header"), "application/pdf")}
    res = client.post(
        "/api/v1/evidence/upload",
        headers=headers,
        data={"organization_control_id": str(ctrl_id), "title": "Sanitization Test"},
        files=files,
    )
    assert res.status_code == 201
    orig_saved = res.json()["original_filename"]
    assert ":" not in orig_saved
    assert "<" not in orig_saved
    assert ">" not in orig_saved
    assert "\\" not in orig_saved
    assert orig_saved.endswith(".pdf")


def test_rbac_evidence_permissions(client, viewer_user, auditor_user, analyst_user, admin_user, seeded_framework):
    analyst_headers = get_token_headers(analyst_user)
    ctrl_id = client.get("/api/v1/controls", headers=analyst_headers).json()[0]["id"]

    # 1. Viewer cannot upload evidence
    viewer_headers = get_token_headers(viewer_user)
    files = {"file": ("test.pdf", io.BytesIO(b"%PDF-1.4 Data"), "application/pdf")}
    upload_res = client.post(
        "/api/v1/evidence/upload",
        headers=viewer_headers,
        data={"organization_control_id": str(ctrl_id), "title": "Viewer Upload"},
        files=files,
    )
    assert upload_res.status_code == 403

    # 2. Analyst uploads evidence
    ev = client.post(
        "/api/v1/evidence/upload",
        headers=analyst_headers,
        data={"organization_control_id": str(ctrl_id), "title": "Analyst Upload"},
        files=files,
    ).json()

    # 3. Viewer cannot submit for review
    submit_res = client.post(f"/api/v1/evidence/{ev['id']}/submit-review", headers=viewer_headers)
    assert submit_res.status_code == 403

    # 4. Viewer cannot edit metadata
    patch_res = client.patch(f"/api/v1/evidence/{ev['id']}", headers=viewer_headers, json={"title": "Hacked"})
    assert patch_res.status_code == 403

    # 5. Auditor can read and review
    auditor_headers = get_token_headers(auditor_user)
    client.post(f"/api/v1/evidence/{ev['id']}/submit-review", headers=analyst_headers)
    rev_res = client.post(
        f"/api/v1/evidence/{ev['id']}/review",
        headers=auditor_headers,
        json={"decision": "ACCEPT", "review_notes": "Auditor accepted."},
    )
    assert rev_res.status_code == 200
    assert rev_res.json()["status"] == "ACCEPTED"