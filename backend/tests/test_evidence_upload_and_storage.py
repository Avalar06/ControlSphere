import hashlib
import io
from tests.conftest import get_token_headers


def test_valid_pdf_evidence_upload(client, analyst_user, seeded_framework):
    headers = get_token_headers(analyst_user)
    ctrl_id = client.get("/api/v1/controls", headers=headers).json()[0]["id"]

    pdf_content = b"%PDF-1.4 Mock Security Architecture Diagram and Data Flow Document"
    expected_sha256 = hashlib.sha256(pdf_content).hexdigest().lower()

    files = {"file": ("Architecture_Overview.pdf", io.BytesIO(pdf_content), "application/pdf")}
    data = {
        "organization_control_id": str(ctrl_id),
        "title": "Architecture Overview PDF",
        "description": "Verified network boundaries.",
    }

    res = client.post("/api/v1/evidence/upload", headers=headers, data=data, files=files)
    assert res.status_code == 201
    item = res.json()
    assert item["title"] == "Architecture Overview PDF"
    assert item["original_filename"] == "Architecture_Overview.pdf"
    assert item["file_extension"] == ".pdf"
    assert item["content_type"] == "application/pdf"
    assert item["file_size"] == len(pdf_content)
    assert item["sha256_hash"] == expected_sha256
    assert item["status"] == "UPLOADED"


def test_valid_png_evidence_upload(client, analyst_user, seeded_framework):
    headers = get_token_headers(analyst_user)
    ctrl_id = client.get("/api/v1/controls", headers=headers).json()[0]["id"]

    png_content = b"\x89PNG\r\n\x1a\nMock PNG Binary Stream"
    files = {"file": ("mfa_screen.png", io.BytesIO(png_content), "image/png")}
    data = {"organization_control_id": str(ctrl_id), "title": "MFA Screenshot"}

    res = client.post("/api/v1/evidence/upload", headers=headers, data=data, files=files)
    assert res.status_code == 201
    assert res.json()["file_extension"] == ".png"
    assert res.json()["content_type"] == "image/png"


def test_reject_zero_byte_empty_file(client, analyst_user, seeded_framework):
    headers = get_token_headers(analyst_user)
    ctrl_id = client.get("/api/v1/controls", headers=headers).json()[0]["id"]

    files = {"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}
    data = {"organization_control_id": str(ctrl_id), "title": "Empty File"}

    res = client.post("/api/v1/evidence/upload", headers=headers, data=data, files=files)
    assert res.status_code == 400
    assert "Zero-byte empty files cannot be accepted" in res.json()["detail"]


def test_reject_unsupported_file_extension(client, analyst_user, seeded_framework):
    headers = get_token_headers(analyst_user)
    ctrl_id = client.get("/api/v1/controls", headers=headers).json()[0]["id"]

    files = {"file": ("exploit.exe", io.BytesIO(b"MZ_executable_payload"), "application/x-msdownload")}
    data = {"organization_control_id": str(ctrl_id), "title": "Executable File"}

    res = client.post("/api/v1/evidence/upload", headers=headers, data=data, files=files)
    assert res.status_code == 400
    assert "Unsupported file extension" in res.json()["detail"]


def test_reject_mime_magic_byte_mismatch(client, analyst_user, seeded_framework):
    headers = get_token_headers(analyst_user)
    ctrl_id = client.get("/api/v1/controls", headers=headers).json()[0]["id"]

    # File claims to be .pdf but contains arbitrary text without %PDF- magic signature
    fake_pdf = b"This is plain text disguised as a PDF document."
    files = {"file": ("fake.pdf", io.BytesIO(fake_pdf), "application/pdf")}
    data = {"organization_control_id": str(ctrl_id), "title": "Disguised PDF"}

    res = client.post("/api/v1/evidence/upload", headers=headers, data=data, files=files)
    assert res.status_code == 400
    assert "does not match expected binary signature" in res.json()["detail"]


def test_sanitize_path_traversal_filename(client, analyst_user, seeded_framework):
    headers = get_token_headers(analyst_user)
    ctrl_id = client.get("/api/v1/controls", headers=headers).json()[0]["id"]

    pdf_content = b"%PDF-1.4 Legitimate PDF bytes"
    files = {"file": ("../../../../etc/passwd.pdf", io.BytesIO(pdf_content), "application/pdf")}
    data = {"organization_control_id": str(ctrl_id), "title": "Path Traversal Filename Test"}

    res = client.post("/api/v1/evidence/upload", headers=headers, data=data, files=files)
    assert res.status_code == 201
    # Path separators must be stripped
    assert "/" not in res.json()["original_filename"]
    assert "\\" not in res.json()["original_filename"]
    assert "passwd.pdf" in res.json()["original_filename"]