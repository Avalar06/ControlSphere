from datetime import date
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User
from tests.conftest import get_token_headers


def test_create_and_list_assessments(
    client: TestClient, analyst_user: User, db: Session, seeded_framework
):
    headers = get_token_headers(analyst_user)
    controls = client.get("/api/v1/controls", headers=headers).json()
    ctrl_id = controls[0]["id"]

    # 1. Create Assessment (DRAFT)
    res_create = client.post(
        "/api/v1/assessments",
        headers=headers,
        json={
            "organization_control_id": ctrl_id,
            "assessment_method": "EXAMINATION",
            "assessment_scope": "Production Kubernetes cluster identity configurations.",
            "summary": "Initial evaluation of MFA enforcement across cluster services.",
        },
    )
    assert res_create.status_code == 201
    data = res_create.json()
    assert data["status"] == "DRAFT"
    assert data["conclusion"] == "NOT_ASSESSED"
    assert data["organization_control_id"] == ctrl_id
    ass_id = data["id"]

    # 2. List Assessments
    res_list = client.get(f"/api/v1/assessments?organization_control_id={ctrl_id}", headers=headers)
    assert res_list.status_code == 200
    items = res_list.json()
    assert len(items) >= 1
    assert items[0]["id"] == ass_id


def test_assessment_lifecycle_draft_to_completed_to_superseded(
    client: TestClient, analyst_user: User, db: Session, seeded_framework
):
    headers = get_token_headers(analyst_user)
    controls = client.get("/api/v1/controls", headers=headers).json()
    ctrl_id = controls[0]["id"]

    # 1. Create Assessment
    res_create = client.post(
        "/api/v1/assessments",
        headers=headers,
        json={
            "organization_control_id": ctrl_id,
            "assessment_method": "TESTING",
            "summary": "Testing access control mechanisms.",
        },
    )
    ass_id = res_create.json()["id"]

    # 2. Start Assessment
    res_start = client.post(f"/api/v1/assessments/{ass_id}/start", headers=headers)
    assert res_start.status_code == 200
    assert res_start.json()["status"] == "IN_PROGRESS"

    # Cannot start again
    res_start_again = client.post(f"/api/v1/assessments/{ass_id}/start", headers=headers)
    assert res_start_again.status_code == 400

    # 3. Complete Assessment with invalid conclusion (NOT_ASSESSED) fails
    res_comp_invalid = client.post(
        f"/api/v1/assessments/{ass_id}/complete",
        headers=headers,
        json={"conclusion": "NOT_ASSESSED", "summary": "Finished review."},
    )
    assert res_comp_invalid.status_code == 400

    # Complete Assessment with valid conclusion
    res_comp = client.post(
        f"/api/v1/assessments/{ass_id}/complete",
        headers=headers,
        json={
            "conclusion": "EFFECTIVE",
            "summary": "All administrative access accounts require hardware security keys.",
            "limitations": "Tested on US-East region only.",
        },
    )
    assert res_comp.status_code == 200
    comp_data = res_comp.json()
    assert comp_data["status"] == "COMPLETED"
    assert comp_data["conclusion"] == "EFFECTIVE"
    assert comp_data["completed_at"] is not None

    # Completed assessment cannot be edited
    res_edit = client.patch(
        f"/api/v1/assessments/{ass_id}",
        headers=headers,
        json={"summary": "Mutated summary."},
    )
    assert res_edit.status_code == 400
    assert "Cannot edit metadata of assessment in status 'COMPLETED'" in res_edit.json()["detail"]

    # 4. Supersede Assessment
    res_super = client.post(f"/api/v1/assessments/{ass_id}/supersede", headers=headers)
    assert res_super.status_code == 200
    assert res_super.json()["status"] == "SUPERSEDED"


def test_viewer_cannot_create_or_modify_assessments(
    client: TestClient, viewer_user: User, analyst_user: User, db: Session, seeded_framework
):
    analyst_headers = get_token_headers(analyst_user)
    viewer_headers = get_token_headers(viewer_user)
    controls = client.get("/api/v1/controls", headers=analyst_headers).json()
    ctrl_id = controls[0]["id"]

    # 1. Viewer cannot create assessment
    res_create = client.post(
        "/api/v1/assessments",
        headers=viewer_headers,
        json={"organization_control_id": ctrl_id, "summary": "Viewer assessment."},
    )
    assert res_create.status_code == 403

    # 2. Analyst creates assessment
    res_ass = client.post(
        "/api/v1/assessments",
        headers=analyst_headers,
        json={"organization_control_id": ctrl_id, "summary": "Analyst assessment."},
    )
    ass_id = res_ass.json()["id"]

    # 3. Viewer can read
    res_get = client.get(f"/api/v1/assessments/{ass_id}", headers=viewer_headers)
    assert res_get.status_code == 200

    # 4. Viewer cannot update
    res_patch = client.patch(
        f"/api/v1/assessments/{ass_id}",
        headers=viewer_headers,
        json={"summary": "Hacked."},
    )
    assert res_patch.status_code == 403
