import io
from tests.conftest import get_token_headers


def test_supersede_historical_evidence(client, analyst_user, seeded_framework):
    headers = get_token_headers(analyst_user)
    ctrl_id = client.get("/api/v1/controls", headers=headers).json()[0]["id"]

    # Upload original evidence v1
    f1 = {"file": ("v1.pdf", io.BytesIO(b"%PDF-1.4 Version 1 Architecture"), "application/pdf")}
    ev1 = client.post(
        "/api/v1/evidence/upload",
        headers=headers,
        data={"organization_control_id": str(ctrl_id), "title": "Architecture v1"},
        files=f1,
    ).json()

    # Upload replacement evidence v2
    f2 = {"file": ("v2.pdf", io.BytesIO(b"%PDF-1.4 Version 2 Architecture Updated"), "application/pdf")}
    ev2 = client.post(
        "/api/v1/evidence/upload",
        headers=headers,
        data={"organization_control_id": str(ctrl_id), "title": "Architecture v2 (Updated)"},
        files=f2,
    ).json()

    # Mark v1 as superseded by v2
    super_res = client.post(
        f"/api/v1/evidence/{ev1['id']}/supersede?new_evidence_id={ev2['id']}",
        headers=headers,
    )
    assert super_res.status_code == 200
    assert super_res.json()["status"] == "SUPERSEDED"
    assert super_res.json()["superseded_by_id"] == ev2["id"]

    # Verify superseded evidence metadata cannot be modified
    patch_res = client.patch(
        f"/api/v1/evidence/{ev1['id']}",
        headers=headers,
        json={"title": "Modified Superseded Title"},
    )
    assert patch_res.status_code == 400
    assert "Cannot edit metadata of superseded historical evidence" in patch_res.json()["detail"]