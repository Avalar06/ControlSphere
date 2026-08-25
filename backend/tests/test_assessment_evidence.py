import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User
from tests.conftest import get_token_headers


def test_link_and_unlink_evidence_to_assessment(
    client: TestClient, analyst_user: User, db: Session, seeded_framework
):
    headers = get_token_headers(analyst_user)
    controls = client.get("/api/v1/controls", headers=headers).json()
    ctrl_id = controls[0]["id"]
    ctrl_id_other = controls[1]["id"]

    # 1. Upload evidence for ctrl_id
    file_bytes = b"IAM policy config for MFA enforcement: enabled=true"
    res_upload = client.post(
        "/api/v1/evidence/upload",
        headers=headers,
        data={
            "organization_control_id": str(ctrl_id),
            "title": "MFA IAM Policy",
            "description": "IAM policy text",
        },
        files={"file": ("iam_mfa.txt", io.BytesIO(file_bytes), "text/plain")},
    )
    assert res_upload.status_code == 201
    ev_id = res_upload.json()["id"]

    # Upload evidence for other control
    res_upload_other = client.post(
        "/api/v1/evidence/upload",
        headers=headers,
        data={
            "organization_control_id": str(ctrl_id_other),
            "title": "Log Backup Config",
            "description": "Config file",
        },
        files={"file": ("backup.txt", io.BytesIO(b"backup config: enabled"), "text/plain")},
    )
    assert res_upload_other.status_code == 201
    ev_id_other = res_upload_other.json()["id"]

    # 2. Create Assessment for ctrl_id
    res_ass = client.post(
        "/api/v1/assessments",
        headers=headers,
        json={"organization_control_id": ctrl_id, "summary": "MFA review."},
    )
    ass_id = res_ass.json()["id"]

    # 3. Reject linking evidence from different control
    res_link_bad = client.post(
        f"/api/v1/assessments/{ass_id}/evidence",
        headers=headers,
        json={"evidence_id": ev_id_other},
    )
    assert res_link_bad.status_code == 400
    assert "Evidence item does not belong to the same control" in res_link_bad.json()["detail"]

    # 4. Successfully link valid evidence
    res_link = client.post(
        f"/api/v1/assessments/{ass_id}/evidence",
        headers=headers,
        json={"evidence_id": ev_id},
    )
    assert res_link.status_code == 201

    # Duplicate link is idempotent
    res_link_dup = client.post(
        f"/api/v1/assessments/{ass_id}/evidence",
        headers=headers,
        json={"evidence_id": ev_id},
    )
    assert res_link_dup.status_code == 201

    # Check detail contains linked evidence
    res_detail = client.get(f"/api/v1/assessments/{ass_id}", headers=headers)
    assert res_detail.status_code == 200
    assert len(res_detail.json()["evidence_links"]) == 1

    # 5. Unlink evidence
    res_unlink = client.delete(
        f"/api/v1/assessments/{ass_id}/evidence/{ev_id}",
        headers=headers,
    )
    assert res_unlink.status_code == 204

    # Verify unlinked
    res_detail2 = client.get(f"/api/v1/assessments/{ass_id}", headers=headers)
    assert len(res_detail2.json()["evidence_links"]) == 0
