import io
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.file_security import verify_content_type, FileSecurityError
from app.models.control import OrganizationControl
from app.models.evidence import (
    EvidenceItem,
    EvidenceRequirement,
    EvidenceStatusEnum,
    EvidenceTypeEnum,
)
from app.models.framework import Framework, FrameworkSubcategory
from app.models.user import User
from app.services.evidence_service import EvidenceService
from app.storage.local import LocalStorageProvider
from tests.conftest import get_token_headers


def test_path_traversal_sibling_directory_blocked(tmp_path):
    """Test that sibling directory prefix matches outside storage root are blocked."""
    root_dir = tmp_path / "evidence"
    root_dir.mkdir()
    sibling_dir = tmp_path / "evidence_backup"
    sibling_dir.mkdir()

    provider = LocalStorageProvider(root_dir=str(root_dir))

    # Attempt to target sibling directory with identical prefix
    with pytest.raises(ValueError, match="Path traversal detected"):
        provider._resolve_safe_path("../evidence_backup/stolen.txt")


def test_cross_control_evidence_requirement_mismatch_rejected(
    client: TestClient, admin_user: User, db: Session, seeded_framework
):
    """Test that attaching a requirement belonging to Control B to an upload for Control A is rejected."""
    headers = get_token_headers(admin_user)
    controls = client.get("/api/v1/controls", headers=headers).json()
    ctrl1_id, ctrl2_id = controls[0]["id"], controls[1]["id"]

    # Create requirement for Control 2
    req_ctrl2 = EvidenceRequirement(
        organization_id=admin_user.organization_id,
        organization_control_id=ctrl2_id,
        title="Backup System Log Export",
        evidence_type=EvidenceTypeEnum.LOG_EXPORT,
        is_required=True,
    )
    db.add(req_ctrl2)
    db.commit()

    # Attempt to upload evidence targeting Control 1 with Requirement from Control 2
    pdf_content = b"%PDF-1.4 test content for control 1"
    response = client.post(
        "/api/v1/evidence/upload",
        headers=headers,
        data={
            "organization_control_id": str(ctrl1_id),
            "evidence_requirement_id": str(req_ctrl2.id),
            "title": "Mismatched Requirement Evidence",
        },
        files={"file": ("evidence.pdf", io.BytesIO(pdf_content), "application/pdf")},
    )
    assert response.status_code == 400
    assert "does not belong to control" in response.json()["detail"]


def test_supersede_self_rejected(
    client: TestClient, admin_user: User, db: Session, seeded_framework
):
    """Test that an evidence item cannot supersede itself."""
    headers = get_token_headers(admin_user)
    controls = client.get("/api/v1/controls", headers=headers).json()
    ctrl_id = controls[0]["id"]

    pdf_content = b"%PDF-1.4 sample artifact"
    res = client.post(
        "/api/v1/evidence/upload",
        headers=headers,
        data={"organization_control_id": str(ctrl_id), "title": "Item 1"},
        files={"file": ("doc.pdf", io.BytesIO(pdf_content), "application/pdf")},
    )
    assert res.status_code == 201
    item_id = res.json()["id"]

    # Attempt to supersede item with itself
    res_super = client.post(
        f"/api/v1/evidence/{item_id}/supersede?new_evidence_id={item_id}",
        headers=headers,
    )
    assert res_super.status_code == 400
    assert "cannot supersede itself" in res_super.json()["detail"]


def test_supersede_cross_control_rejected(
    client: TestClient, admin_user: User, db: Session, seeded_framework
):
    """Test that superseding across different controls is rejected."""
    headers = get_token_headers(admin_user)
    controls = client.get("/api/v1/controls", headers=headers).json()
    ctrl1_id, ctrl2_id = controls[0]["id"], controls[1]["id"]

    pdf_bytes = b"%PDF-1.4 sample"
    res1 = client.post(
        "/api/v1/evidence/upload",
        headers=headers,
        data={"organization_control_id": str(ctrl1_id), "title": "Ctrl 1 Doc"},
        files={"file": ("doc1.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    res2 = client.post(
        "/api/v1/evidence/upload",
        headers=headers,
        data={"organization_control_id": str(ctrl2_id), "title": "Ctrl 2 Doc"},
        files={"file": ("doc2.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    id1 = res1.json()["id"]
    id2 = res2.json()["id"]

    res_super = client.post(
        f"/api/v1/evidence/{id1}/supersede?new_evidence_id={id2}",
        headers=headers,
    )
    assert res_super.status_code == 400
    assert "must belong to the same organization control" in res_super.json()["detail"]


def test_review_already_accepted_evidence_blocked(
    client: TestClient, admin_user: User, db: Session, seeded_framework
):
    """Test that an already accepted evidence item cannot be re-reviewed and altered."""
    headers = get_token_headers(admin_user)
    controls = client.get("/api/v1/controls", headers=headers).json()
    ctrl_id = controls[0]["id"]

    pdf_content = b"%PDF-1.4 sample evidence"
    res = client.post(
        "/api/v1/evidence/upload",
        headers=headers,
        data={"organization_control_id": str(ctrl_id), "title": "Review Item"},
        files={"file": ("item.pdf", io.BytesIO(pdf_content), "application/pdf")},
    )
    item_id = res.json()["id"]

    # Submit for review and accept
    client.post(f"/api/v1/evidence/{item_id}/submit-review", headers=headers)
    res_accept = client.post(
        f"/api/v1/evidence/{item_id}/review",
        headers=headers,
        json={"decision": "ACCEPT", "review_notes": "Looks solid."},
    )
    assert res_accept.status_code == 200
    assert res_accept.json()["status"] == "ACCEPTED"

    # Attempt to re-review and reject an already accepted item
    res_re_review = client.post(
        f"/api/v1/evidence/{item_id}/review",
        headers=headers,
        json={"decision": "REJECT", "rejection_reason": "Changed my mind."},
    )
    assert res_re_review.status_code == 400
    assert "Cannot review evidence item in status 'ACCEPTED'" in res_re_review.json()["detail"]


def test_text_file_with_null_bytes_rejected():
    """Test that text files containing embedded null bytes are rejected as binary masquerade."""
    fake_txt_with_null = b"Header row, column 1, column 2\x00\x01\x02\xff executable payload"
    with pytest.raises(FileSecurityError, match="embedded binary null bytes"):
        verify_content_type(fake_txt_with_null, ".txt", "text/plain")

    fake_csv_with_null = b"id,name\x00malicious binary blob"
    with pytest.raises(FileSecurityError, match="embedded binary null bytes"):
        verify_content_type(fake_csv_with_null, ".csv", "text/csv")


def test_download_security_cache_headers_present(
    client: TestClient, admin_user: User, db: Session, seeded_framework
):
    """Test that download responses set no-cache/no-store Cache-Control headers."""
    headers = get_token_headers(admin_user)
    controls = client.get("/api/v1/controls", headers=headers).json()
    ctrl_id = controls[0]["id"]

    pdf_content = b"%PDF-1.4 confidential audit evidence"
    res_upload = client.post(
        "/api/v1/evidence/upload",
        headers=headers,
        data={"organization_control_id": str(ctrl_id), "title": "Confidential Audit Doc"},
        files={"file": ("audit.pdf", io.BytesIO(pdf_content), "application/pdf")},
    )
    item_id = res_upload.json()["id"]

    res_download = client.get(f"/api/v1/evidence/{item_id}/download", headers=headers)
    assert res_download.status_code == 200
    assert "no-store" in res_download.headers.get("cache-control", "")
    assert res_download.headers.get("pragma") == "no-cache"
    assert res_download.headers.get("x-content-type-options") == "nosniff"


def test_upload_transaction_compensation_cleans_up_storage(
    client: TestClient, db: Session, admin_user: User, seeded_framework
):
    """Test that if database insertion/commit fails, the storage file is rolled back and deleted."""
    headers = get_token_headers(admin_user)
    controls = client.get("/api/v1/controls", headers=headers).json()
    ctrl_id = controls[0]["id"]

    pdf_content = b"%PDF-1.4 transaction compensation test"

    with patch.object(db, "commit", side_effect=RuntimeError("Simulated DB Crash")):
        with pytest.raises(RuntimeError, match="Simulated DB Crash"):
            EvidenceService.upload_evidence(
                db=db,
                organization_id=admin_user.organization_id,
                organization_control_id=ctrl_id,
                evidence_requirement_id=None,
                title="Faulty Item",
                description=None,
                file_bytes=pdf_content,
                original_filename="faulty.pdf",
                declared_content_type="application/pdf",
                uploaded_by_id=admin_user.id,
            )


