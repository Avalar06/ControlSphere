import io
from tests.conftest import get_token_headers


def test_authenticated_evidence_download(client, analyst_user, seeded_framework):
    headers = get_token_headers(analyst_user)
    ctrl_id = client.get("/api/v1/controls", headers=headers).json()[0]["id"]

    content = b"%PDF-1.4 Top Secret Firewall Rules and Export"
    files = {"file": ("firewall_rules.pdf", io.BytesIO(content), "application/pdf")}
    ev_id = client.post(
        "/api/v1/evidence/upload",
        headers=headers,
        data={"organization_control_id": str(ctrl_id), "title": "Firewall Rules"},
        files=files,
    ).json()["id"]

    # Download
    download_res = client.get(f"/api/v1/evidence/{ev_id}/download", headers=headers)
    assert download_res.status_code == 200
    assert download_res.content == content
    assert "attachment" in download_res.headers["Content-Disposition"]
    assert "firewall_rules.pdf" in download_res.headers["Content-Disposition"]
    assert download_res.headers["Content-Type"] == "application/pdf"


def test_cross_tenant_download_rejected(client, analyst_user, meridian_admin_user, seeded_framework):
    apex_headers = get_token_headers(analyst_user)
    ctrl_id = client.get("/api/v1/controls", headers=apex_headers).json()[0]["id"]

    content = b"%PDF-1.4 Apex Confidential Financial Systems Review"
    files = {"file": ("apex_financials.pdf", io.BytesIO(content), "application/pdf")}
    ev_id = client.post(
        "/api/v1/evidence/upload",
        headers=apex_headers,
        data={"organization_control_id": str(ctrl_id), "title": "Apex Financial Evidence"},
        files=files,
    ).json()["id"]

    # Meridian admin attempts to download Apex evidence
    meridian_headers = get_token_headers(meridian_admin_user)
    download_res = client.get(f"/api/v1/evidence/{ev_id}/download", headers=meridian_headers)
    assert download_res.status_code == 404
    assert "not found or inaccessible in your organization" in download_res.json()["detail"]


def test_unauthenticated_download_rejected(client, analyst_user, seeded_framework):
    headers = get_token_headers(analyst_user)
    ctrl_id = client.get("/api/v1/controls", headers=headers).json()[0]["id"]

    files = {"file": ("report.pdf", io.BytesIO(b"%PDF-1.4 Report"), "application/pdf")}
    ev_id = client.post(
        "/api/v1/evidence/upload",
        headers=headers,
        data={"organization_control_id": str(ctrl_id), "title": "Report"},
        files=files,
    ).json()["id"]

    # No token provided
    res = client.get(f"/api/v1/evidence/{ev_id}/download")
    assert res.status_code == 401