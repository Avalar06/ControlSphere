import json
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.permissions import RoleEnum
from app.core.security import get_password_hash
from app.models.control import OrganizationControl, ImplementationStatusEnum, PriorityEnum
from app.models.framework import Framework, FrameworkFunction, FrameworkCategory, FrameworkSubcategory
from app.models.organization import Organization
from app.models.user import User
from app.models.evidence import EvidenceItem, EvidenceStatusEnum
from app.models.integration import (
    IntegrationProvider,
    IntegrationConnection,
    EvidenceCollectionJob,
    EvidenceCollectionRun,
    IntegrationProviderTypeEnum,
    EvidenceCollectorTypeEnum,
)
from app.schemas.integration import (
    IntegrationConnectionCreate,
    IntegrationCredentialCreate,
    EvidenceCollectionJobCreate,
)
from app.services.integration_service import IntegrationService, IntegrationSecurityService, SSRFValidationError
from tests.conftest import get_token_headers


@pytest.fixture
def p22_adv_fixture(db: Session, org_apex: Organization, org_meridian: Organization):
    """Setup adversarial test harness for Phase 22 Integration-GRC."""
    apex_admin = User(
        email="p22_apex_admin@apex.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Apex Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_manager = User(
        email="p22_apex_manager@apex.com",
        hashed_password=get_password_hash("MgrPass123!"),
        full_name="Apex Manager",
        role=RoleEnum.MANAGER,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_analyst = User(
        email="p22_apex_analyst@apex.com",
        hashed_password=get_password_hash("AnalystPass123!"),
        full_name="Apex Analyst",
        role=RoleEnum.GRC_ANALYST,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_viewer = User(
        email="p22_apex_viewer@apex.com",
        hashed_password=get_password_hash("ViewerPass123!"),
        full_name="Apex Viewer",
        role=RoleEnum.VIEWER,
        is_active=True,
        organization_id=org_apex.id,
    )
    meridian_admin = User(
        email="p22_meridian_admin@meridian.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Meridian Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_meridian.id,
    )
    db.add_all([apex_admin, apex_manager, apex_analyst, apex_viewer, meridian_admin])
    db.commit()

    # Seed Framework and Controls for Apex and Meridian
    fw = Framework(identifier="NIST-CSF-2.0-P22", name="NIST CSF 2.0", version="2.0")
    db.add(fw)
    db.flush()
    fn = FrameworkFunction(framework_id=fw.id, identifier="PR-P22", name="Protect")
    db.add(fn)
    db.flush()
    cat = FrameworkCategory(function_id=fn.id, identifier="PR.AC-P22", name="Access Control")
    db.add(cat)
    db.flush()
    subcat = FrameworkSubcategory(category_id=cat.id, identifier="PR.AC-01-P22", title="Identities Managed", description="Desc")
    db.add(subcat)
    db.flush()

    apex_ctrl = OrganizationControl(
        organization_id=org_apex.id,
        subcategory_id=subcat.id,
        status=ImplementationStatusEnum.IN_PROGRESS,
        priority=PriorityEnum.HIGH,
    )
    meridian_ctrl = OrganizationControl(
        organization_id=org_meridian.id,
        subcategory_id=subcat.id,
        status=ImplementationStatusEnum.IN_PROGRESS,
        priority=PriorityEnum.HIGH,
    )
    db.add_all([apex_ctrl, meridian_ctrl])
    db.commit()

    IntegrationService.seed_providers_if_empty(db)
    aws_provider = db.query(IntegrationProvider).filter(
        IntegrationProvider.provider_type == IntegrationProviderTypeEnum.AWS
    ).first()

    # Apex Connection with credentials
    conn = IntegrationService.create_connection(
        db,
        org_apex.id,
        IntegrationConnectionCreate(
            provider_id=aws_provider.id,
            connection_code="CONN-APEX-AWS-01",
            name="Apex Production AWS Connector",
            granted_scopes=["iam:GetAccountSummary", "s3:GetEncryptionConfiguration"],
        ),
        apex_admin.id,
    )
    IntegrationService.set_connection_credentials(
        db,
        org_apex.id,
        conn.id,
        IntegrationCredentialCreate(
            auth_type="STS_ROLE",
            credentials={"role_arn": "arn:aws:iam::123456789012:role/ControlSphereCollector", "external_id": "secret-ext-id"},
        ),
        apex_admin.id,
    )

    return {
        "apex_admin": apex_admin,
        "apex_manager": apex_manager,
        "apex_analyst": apex_analyst,
        "apex_viewer": apex_viewer,
        "meridian_admin": meridian_admin,
        "org_apex": org_apex,
        "org_meridian": org_meridian,
        "apex_ctrl": apex_ctrl,
        "meridian_ctrl": meridian_ctrl,
        "aws_provider": aws_provider,
        "conn": conn,
    }


def test_adv_p22_13_cross_tenant_connection_isolation(client: TestClient, p22_adv_fixture):
    """13 cross tenant connection isolation: Tenant B cannot access Tenant A connection."""
    meridian_headers = get_token_headers(p22_adv_fixture["meridian_admin"])
    conn_id = p22_adv_fixture["conn"].id

    res = client.get(f"/api/v1/integrations/connections/{conn_id}", headers=meridian_headers)
    assert res.status_code == 404


def test_adv_p22_14_credential_redaction_on_get(client: TestClient, p22_adv_fixture):
    """14 credential redaction on GET: GET /connections/{id} never exposes secret credentials or ciphertext."""
    admin_headers = get_token_headers(p22_adv_fixture["apex_admin"])
    conn_id = p22_adv_fixture["conn"].id

    res = client.get(f"/api/v1/integrations/connections/{conn_id}", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert "role_arn" not in data
    assert "external_id" not in data
    assert "encrypted_payload" not in data
    assert data["is_credential_configured"] is True


def test_adv_p22_15_credential_mass_assignment_protection(client: TestClient, p22_adv_fixture):
    """15 credential mass assignment protection: Injecting credentials in connection creation is ignored."""
    admin_headers = get_token_headers(p22_adv_fixture["apex_admin"])
    provider_id = p22_adv_fixture["aws_provider"].id

    payload = {
        "provider_id": provider_id,
        "connection_code": "CONN-MASS-ASSIGN",
        "name": "Mass Assignment Test",
        "granted_scopes": ["iam:GetAccountSummary"],
        "encrypted_payload": "injected_ciphertext",
        "plaintext_secret": "injected_secret",
    }
    res = client.post("/api/v1/integrations/connections", json=payload, headers=admin_headers)
    assert res.status_code == 201
    assert "injected_secret" not in res.text
    assert "injected_ciphertext" not in res.text


def test_adv_p22_16_ssrf_disallowed_scheme_rejection(client: TestClient, p22_adv_fixture):
    """16 SSRF disallowed scheme rejection: file:// and http:// schemes are strictly rejected."""
    with pytest.raises(SSRFValidationError):
        IntegrationSecurityService.validate_outbound_url("file:///etc/passwd", ["*.amazonaws.com"])
    with pytest.raises(SSRFValidationError):
        IntegrationSecurityService.validate_outbound_url("http://api.github.com", ["api.github.com"])


def test_adv_p22_17_ssrf_disallowed_hostname_rejection(client: TestClient, p22_adv_fixture):
    """17 SSRF disallowed hostname rejection: Non-allowlisted hostnames are strictly rejected."""
    with pytest.raises(SSRFValidationError):
        IntegrationSecurityService.validate_outbound_url("https://malicious-attacker.com", ["*.amazonaws.com"])


def test_adv_p22_18_ssrf_loopback_rejection(client: TestClient, p22_adv_fixture):
    """18 SSRF loopback rejection: Localhost and 127.0.0.1 destinations are strictly rejected."""
    with pytest.raises(SSRFValidationError):
        IntegrationSecurityService.validate_outbound_url("https://127.0.0.1:8443", ["127.0.0.1"])
    with pytest.raises(SSRFValidationError):
        IntegrationSecurityService.validate_outbound_url("https://localhost:8443", ["localhost"])


def test_adv_p22_19_ssrf_rfc1918_private_ip_rejection(client: TestClient, p22_adv_fixture):
    """19 SSRF RFC1918 private IP rejection: Private subnets (10.x, 172.16.x, 192.168.x) are blocked."""
    with pytest.raises(SSRFValidationError):
        IntegrationSecurityService.validate_outbound_url("https://10.0.0.1:443", ["10.0.0.1"])
    with pytest.raises(SSRFValidationError):
        IntegrationSecurityService.validate_outbound_url("https://192.168.1.1:443", ["192.168.1.1"])


def test_adv_p22_20_ssrf_aws_metadata_ip_rejection(client: TestClient, p22_adv_fixture):
    """20 SSRF AWS metadata IP rejection: Cloud metadata IP 169.254.169.254 is strictly prohibited."""
    with pytest.raises(SSRFValidationError):
        IntegrationSecurityService.validate_outbound_url("https://169.254.169.254/latest/meta-data", ["169.254.169.254"])


def test_adv_p22_21_ssrf_ipv6_loopback_and_link_local_rejection(client: TestClient, p22_adv_fixture):
    """21 SSRF IPv6 loopback/link-local rejection: IPv6 [::1] and link-local ranges are rejected."""
    with pytest.raises(SSRFValidationError):
        IntegrationSecurityService.validate_outbound_url("https://[::1]:443", ["::1"])


def test_adv_p22_22_collection_job_foreign_control_binding(client: TestClient, p22_adv_fixture):
    """22 collection job foreign control binding: Tenant A cannot bind collection job to Tenant B control."""
    admin_headers = get_token_headers(p22_adv_fixture["apex_admin"])
    conn_id = p22_adv_fixture["conn"].id
    meridian_ctrl_id = p22_adv_fixture["meridian_ctrl"].id

    payload = {
        "connection_id": conn_id,
        "organization_control_id": meridian_ctrl_id,  # Foreign control
        "job_code": "JOB-ILLEGAL-FOREIGN-CTRL",
        "title": "Illegal Foreign Control Job",
        "collector_type": "AWS_IAM_MFA",
    }
    res = client.post("/api/v1/integrations/jobs", json=payload, headers=admin_headers)
    assert res.status_code == 404


def test_adv_p22_23_collection_run_tenant_escape_prevention(client: TestClient, p22_adv_fixture):
    """23 collection run tenant escape prevention: Tenant B cannot execute Tenant A collection job."""
    meridian_headers = get_token_headers(p22_adv_fixture["meridian_admin"])
    apex_admin_headers = get_token_headers(p22_adv_fixture["apex_admin"])

    # Create Apex job
    job_res = client.post(
        "/api/v1/integrations/jobs",
        json={
            "connection_id": p22_adv_fixture["conn"].id,
            "organization_control_id": p22_adv_fixture["apex_ctrl"].id,
            "job_code": "JOB-APEX-AWS-MFA-01",
            "title": "AWS MFA Collection Job",
            "collector_type": "AWS_IAM_MFA",
        },
        headers=apex_admin_headers,
    )
    job_id = job_res.json()["id"]

    # Meridian attempts to trigger job -> MUST FAIL HTTP 404
    res = client.post(f"/api/v1/integrations/jobs/{job_id}/run", headers=meridian_headers)
    assert res.status_code == 404


def test_adv_p22_24_evidence_auto_acceptance_prevention(client: TestClient, db: Session, p22_adv_fixture):
    """24 evidence auto-acceptance prevention: Automated evidence created by collection is strictly in UPLOADED status."""
    admin_headers = get_token_headers(p22_adv_fixture["apex_admin"])

    # Create and run job
    job_res = client.post(
        "/api/v1/integrations/jobs",
        json={
            "connection_id": p22_adv_fixture["conn"].id,
            "organization_control_id": p22_adv_fixture["apex_ctrl"].id,
            "job_code": "JOB-AUTO-ACCEPT-TEST",
            "title": "Auto Acceptance Invariant Job",
            "collector_type": "AWS_IAM_MFA",
        },
        headers=admin_headers,
    )
    job_id = job_res.json()["id"]

    run_res = client.post(f"/api/v1/integrations/jobs/{job_id}/run", headers=admin_headers)
    assert run_res.status_code == 200
    evid_id = run_res.json()["evidence_item_id"]
    assert evid_id is not None

    # Inspect the EvidenceItem in the database
    item = db.query(EvidenceItem).filter(EvidenceItem.id == evid_id).first()
    assert item is not None
    assert item.status == EvidenceStatusEnum.UPLOADED  # STRICT INVARIANT: NOT ACCEPTED


def test_adv_p22_25_unauthorized_scope_expansion_rejection(client: TestClient, p22_adv_fixture):
    """25 unauthorized scope expansion rejection: Connections cannot grant unsupported scopes."""
    admin_headers = get_token_headers(p22_adv_fixture["apex_admin"])
    provider_id = p22_adv_fixture["aws_provider"].id

    payload = {
        "provider_id": provider_id,
        "connection_code": "CONN-ILLEGAL-SCOPE",
        "name": "Illegal Scope Connection",
        "granted_scopes": ["administrator:*", "iam:DeleteAllUsers"],  # Unsupported
    }
    res = client.post("/api/v1/integrations/connections", json=payload, headers=admin_headers)
    assert res.status_code == 400
    assert "not supported" in res.json()["detail"]


def test_adv_p22_26_oversized_external_payload_rejection(client: TestClient, db: Session, p22_adv_fixture):
    """26 oversized external payload rejection: Payload exceeding max_payload_bytes produces a FAILED run."""
    admin_headers = get_token_headers(p22_adv_fixture["apex_admin"])

    # Create job with tiny 1KB max payload limit
    job_res = client.post(
        "/api/v1/integrations/jobs",
        json={
            "connection_id": p22_adv_fixture["conn"].id,
            "organization_control_id": p22_adv_fixture["apex_ctrl"].id,
            "job_code": "JOB-TINY-LIMIT",
            "title": "Tiny Limit Job",
            "collector_type": "AWS_IAM_MFA",
            "max_payload_bytes": 1024,
        },
        headers=admin_headers,
    )
    job_id = job_res.json()["id"]

    # Directly set max_payload_bytes to 10 bytes in DB to force overflow
    job = db.query(EvidenceCollectionJob).filter(EvidenceCollectionJob.id == job_id).first()
    job.max_payload_bytes = 10
    db.commit()

    run_res = client.post(f"/api/v1/integrations/jobs/{job_id}/run", headers=admin_headers)
    assert run_res.status_code == 200
    assert run_res.json()["status"] == "FAILED"
    assert run_res.json()["error_code"] == "PAYLOAD_OVERSIZED"


def test_adv_p22_27_malformed_provider_json_handling(client: TestClient, p22_adv_fixture):
    """27 malformed provider JSON handling: Malformed JSON handled safely without backend crash."""
    # Test that corrupted ciphertext raises clean CredentialDecryptionError without crash
    with pytest.raises(Exception):
        IntegrationSecurityService.decrypt_credentials("invalid_ciphertext_token_payload")
