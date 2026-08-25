import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User
from tests.conftest import get_token_headers


def test_link_and_unlink_evidence_to_finding(
    client: TestClient, analyst_user: User, db: Session, seeded_framework
):
    headers = get_token_headers(analyst_user)
    controls = client.get("/api/v1/controls", headers=headers).json()
    ctrl_id = controls[0]["id"]
    ctrl_id_other = controls[1]["id"]

    # 1. Upload evidence for ctrl_id
    res_upload = client.post(
        "/api/v1/evidence/upload",
        headers=headers,
        data={
            "organization_control_id": str(ctrl_id),
            "title": "Vulnerability Scan Result",
            "description": "Output of Nessus scanner",
        },
        files={"file": ("nessus_scan.txt", io.BytesIO(b"scan result: vulnerable endpoint found"), "text/plain")},
    )
    assert res_upload.status_code == 201
    ev_id = res_upload.json()["id"]

    # Upload evidence for ctrl_id_other
    res_upload_other = client.post(
        "/api/v1/evidence/upload",
        headers=headers,
        data={
            "organization_control_id": str(ctrl_id_other),
            "title": "Firewall Rule Table",
            "description": "Rules",
        },
        files={"file": ("fw.txt", io.BytesIO(b"firewall rules: allow all"), "text/plain")},
    )
    ev_id_other = res_upload_other.json()["id"]

    # 2. Create Finding for ctrl_id
    res_find = client.post(
        "/api/v1/findings",
        headers=headers,
        json={
            "organization_control_id": ctrl_id,
            "title": "Critical RCE in web backend",
            "description": "Identified in latest vulnerability scan.",
            "finding_type": "TECHNICAL_GAP",
            "severity": "CRITICAL",
            "impact": 5,
            "likelihood": 4,
            "recommendation": "Patch immediately.",
        },
    )
    find_id = res_find.json()["id"]

    # 3. Reject linking evidence from another control
    res_link_bad = client.post(
        f"/api/v1/findings/{find_id}/evidence",
        headers=headers,
        json={"evidence_id": ev_id_other},
    )
    assert res_link_bad.status_code == 400
    assert "Evidence item does not belong to the same control" in res_link_bad.json()["detail"]

    # 4. Successfully link valid evidence
    res_link = client.post(
        f"/api/v1/findings/{find_id}/evidence",
        headers=headers,
        json={"evidence_id": ev_id},
    )
    assert res_link.status_code == 201

    # Verify detail contains linked evidence
    res_detail = client.get(f"/api/v1/findings/{find_id}", headers=headers)
    assert res_detail.status_code == 200
    assert len(res_detail.json()["evidence_links"]) == 1

    # 5. Unlink evidence
    res_unlink = client.delete(
        f"/api/v1/findings/{find_id}/evidence/{ev_id}",
        headers=headers,
    )
    assert res_unlink.status_code == 204

    # Verify unlinked
    res_detail2 = client.get(f"/api/v1/findings/{find_id}", headers=headers)
    assert len(res_detail2.json()["evidence_links"]) == 0
