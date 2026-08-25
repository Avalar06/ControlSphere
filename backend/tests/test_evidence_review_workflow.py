import io
from tests.conftest import get_token_headers


def test_full_evidence_review_workflow(client, analyst_user, auditor_user, seeded_framework):
    analyst_headers = get_token_headers(analyst_user)
    ctrl_id = client.get("/api/v1/controls", headers=analyst_headers).json()[0]["id"]

    # 1. Upload evidence
    pdf_bytes = b"%PDF-1.4 Access Control Policy Sign-off Document"
    files = {"file": ("signoff.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    upload_res = client.post(
        "/api/v1/evidence/upload",
        headers=analyst_headers,
        data={"organization_control_id": str(ctrl_id), "title": "CISO Sign-off"},
        files=files,
    )
    assert upload_res.status_code == 201
    ev_id = upload_res.json()["id"]
    assert upload_res.json()["status"] == "UPLOADED"

    # 2. Submit for review
    submit_res = client.post(f"/api/v1/evidence/{ev_id}/submit-review", headers=analyst_headers)
    assert submit_res.status_code == 200
    assert submit_res.json()["status"] == "UNDER_REVIEW"

    # 3. Auditor reviews and ACCEPTS evidence
    auditor_headers = get_token_headers(auditor_user)
    review_res = client.post(
        f"/api/v1/evidence/{ev_id}/review",
        headers=auditor_headers,
        json={
            "decision": "ACCEPT",
            "review_notes": "Verified authentic cryptographic signature of CISO.",
        },
    )
    assert review_res.status_code == 200
    data = review_res.json()
    assert data["status"] == "ACCEPTED"
    assert len(data["reviews"]) == 1
    assert data["reviews"][0]["decision"] == "ACCEPT"
    assert data["reviews"][0]["reviewer"]["email"] == auditor_user.email


def test_reject_evidence_requires_rejection_reason(client, analyst_user, auditor_user, seeded_framework):
    analyst_headers = get_token_headers(analyst_user)
    ctrl_id = client.get("/api/v1/controls", headers=analyst_headers).json()[0]["id"]

    files = {"file": ("config.txt", io.BytesIO(b"MFA=False\nTLS=1.0"), "text/plain")}
    ev_id = client.post(
        "/api/v1/evidence/upload",
        headers=analyst_headers,
        data={"organization_control_id": str(ctrl_id), "title": "Flawed Config"},
        files=files,
    ).json()["id"]

    client.post(f"/api/v1/evidence/{ev_id}/submit-review", headers=analyst_headers)

    auditor_headers = get_token_headers(auditor_user)

    # Attempt rejection without reason (fails)
    res_no_reason = client.post(
        f"/api/v1/evidence/{ev_id}/review",
        headers=auditor_headers,
        json={"decision": "REJECT"},
    )
    assert res_no_reason.status_code == 400
    assert "Rejection reason is required" in res_no_reason.json()["detail"]

    # Rejection with reason (succeeds)
    res_with_reason = client.post(
        f"/api/v1/evidence/{ev_id}/review",
        headers=auditor_headers,
        json={
            "decision": "REJECT",
            "rejection_reason": "Configuration shows MFA is disabled and outdated TLS 1.0 in use.",
        },
    )
    assert res_with_reason.status_code == 200
    assert res_with_reason.json()["status"] == "REJECTED"
    assert res_with_reason.json()["reviews"][0]["rejection_reason"] is not None


def test_viewer_cannot_review_evidence(client, analyst_user, viewer_user, seeded_framework):
    analyst_headers = get_token_headers(analyst_user)
    ctrl_id = client.get("/api/v1/controls", headers=analyst_headers).json()[0]["id"]

    files = {"file": ("audit.pdf", io.BytesIO(b"%PDF-1.4 Audit Evidence"), "application/pdf")}
    ev_id = client.post(
        "/api/v1/evidence/upload",
        headers=analyst_headers,
        data={"organization_control_id": str(ctrl_id), "title": "Audit Evidence"},
        files=files,
    ).json()["id"]

    viewer_headers = get_token_headers(viewer_user)
    res = client.post(
        f"/api/v1/evidence/{ev_id}/review",
        headers=viewer_headers,
        json={"decision": "ACCEPT"},
    )
    assert res.status_code == 403