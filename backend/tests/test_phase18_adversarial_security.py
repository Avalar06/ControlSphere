from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.permissions import RoleEnum
from app.core.security import get_password_hash
from app.models.organization import Organization
from app.models.user import User
from app.models.cloudsec import (
    BenchmarkFrameworkEnum,
    CloudAssetTypeEnum,
    CloudEnvironmentEnum,
    CloudProviderEnum,
    RuleSeverityEnum,
)
from app.models.audit_engagement import Audit, AuditTypeEnum
from app.models.supply_chain import SoftwareProduct, SoftwareProductTypeEnum, ProductCriticalityTierEnum, ProductLifecycleStateEnum
from app.models.remediation import (
    RemediationPlan,
    RemediationSourceTypeEnum,
    RemediationSeverityEnum,
    RemediationStatusEnum,
    RemediationRootCauseClassificationEnum,
)
from tests.conftest import get_token_headers


@pytest.fixture
def p18_adv_fixture(db: Session, org_apex: Organization, org_meridian: Organization):
    """Setup adversarial test harness with two isolated tenants and various roles."""
    apex_admin = User(
        email="p18_apex_admin@apex.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Apex Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_viewer = User(
        email="p18_apex_viewer@apex.com",
        hashed_password=get_password_hash("ViewerPass123!"),
        full_name="Apex Viewer",
        role=RoleEnum.VIEWER,
        is_active=True,
        organization_id=org_apex.id,
    )
    meridian_admin = User(
        email="p18_meridian_admin@meridian.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Meridian Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_meridian.id,
    )

    db.add_all([apex_admin, apex_viewer, meridian_admin])
    db.commit()
    for u in [apex_admin, apex_viewer, meridian_admin]:
        db.refresh(u)

    return {
        "apex_admin": apex_admin,
        "apex_viewer": apex_viewer,
        "meridian_admin": meridian_admin,
        "org_apex": org_apex,
        "org_meridian": org_meridian,
    }


def _seed_meridian_asset(client: TestClient, meridian_admin: User) -> int:
    headers = get_token_headers(meridian_admin)
    res = client.post(
        "/api/v1/cloud-security/assets",
        json={
            "asset_code": "MERIDIAN-S3-SECRET",
            "provider": "AWS",
            "account_id": "999888777666",
            "region": "eu-central-1",
            "resource_type": "S3_BUCKET",
            "resource_arn": "arn:aws:s3:::meridian-classified-vault",
            "resource_name": "meridian-classified-vault",
            "environment": "PRODUCTION",
        },
        headers=headers,
    )
    return res.json()["id"]


def test_adv_p18_01_cross_tenant_cloud_asset_read(client: TestClient, p18_adv_fixture):
    """ADV-P18-01: Tenant A cannot read Tenant B's cloud asset (404 Concealment)."""
    f = p18_adv_fixture
    meridian_asset_id = _seed_meridian_asset(client, f["meridian_admin"])
    apex_headers = get_token_headers(f["apex_admin"])

    res = client.get(f"/api/v1/cloud-security/assets/{meridian_asset_id}", headers=apex_headers)
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_adv_p18_02_cross_tenant_cloud_asset_update(client: TestClient, p18_adv_fixture):
    """ADV-P18-02: Tenant A cannot update Tenant B's cloud asset (404 Concealment)."""
    f = p18_adv_fixture
    meridian_asset_id = _seed_meridian_asset(client, f["meridian_admin"])
    apex_headers = get_token_headers(f["apex_admin"])

    res = client.patch(
        f"/api/v1/cloud-security/assets/{meridian_asset_id}",
        json={"resource_name": "hacked-by-tenant-a"},
        headers=apex_headers,
    )
    assert res.status_code == 404


def test_adv_p18_03_cross_tenant_cloud_asset_deletion(client: TestClient, p18_adv_fixture):
    """ADV-P18-03: Tenant A cannot delete Tenant B's cloud asset (404 Concealment)."""
    f = p18_adv_fixture
    meridian_asset_id = _seed_meridian_asset(client, f["meridian_admin"])
    apex_headers = get_token_headers(f["apex_admin"])

    res = client.delete(f"/api/v1/cloud-security/assets/{meridian_asset_id}", headers=apex_headers)
    assert res.status_code == 404


def test_adv_p18_04_cross_tenant_finding_injection(client: TestClient, p18_adv_fixture):
    """ADV-P18-04: Tenant A cannot record a security finding against Tenant B's asset."""
    f = p18_adv_fixture
    meridian_asset_id = _seed_meridian_asset(client, f["meridian_admin"])
    apex_headers = get_token_headers(f["apex_admin"])

    # Create global benchmark/rule
    b_res = client.post(
        "/api/v1/cloud-security/benchmarks",
        json={
            "benchmark_code": "CIS-AWS-ADV-18",
            "name": "CIS AWS",
            "version": "1.0",
            "framework": "CIS_AWS_FOUNDATIONS",
            "provider": "AWS",
        },
        headers=apex_headers,
    )
    r_res = client.post(
        "/api/v1/cloud-security/rules",
        json={
            "benchmark_id": b_res.json()["id"],
            "rule_code": "CIS-AWS-ADV-18.1",
            "title": "Test Rule",
            "description": "Desc",
            "section": "1. Sec",
        },
        headers=apex_headers,
    )

    res = client.post(
        "/api/v1/cloud-security/findings",
        json={
            "finding_code": "FIND-INJECT-01",
            "cloud_asset_id": meridian_asset_id,
            "rule_id": r_res.json()["id"],
            "evaluation_status": "FAILED",
        },
        headers=apex_headers,
    )
    assert res.status_code == 404


def test_adv_p18_05_cross_tenant_drift_injection(client: TestClient, p18_adv_fixture):
    """ADV-P18-05: Tenant A cannot inject drift events onto Tenant B's asset."""
    f = p18_adv_fixture
    meridian_asset_id = _seed_meridian_asset(client, f["meridian_admin"])
    apex_headers = get_token_headers(f["apex_admin"])

    res = client.post(
        "/api/v1/cloud-security/drifts",
        json={
            "drift_code": "DRIFT-INJECT-01",
            "cloud_asset_id": meridian_asset_id,
            "attribute_path": "securityGroup.rules",
            "baseline_value": "80",
            "drifted_value": "0",
        },
        headers=apex_headers,
    )
    assert res.status_code == 404


def test_adv_p18_06_cross_tenant_iam_blast_radius_injection(client: TestClient, p18_adv_fixture):
    """ADV-P18-06: Tenant A cannot run blast radius analysis against Tenant B's asset."""
    f = p18_adv_fixture
    meridian_asset_id = _seed_meridian_asset(client, f["meridian_admin"])
    apex_headers = get_token_headers(f["apex_admin"])

    res = client.post(
        "/api/v1/cloud-security/blast-radius",
        json={
            "analysis_code": "BLAST-INJECT-01",
            "cloud_asset_id": meridian_asset_id,
            "iam_principal_arn": "arn:aws:iam::111:role/AttackerRole",
            "effective_permissions_count": 10,
        },
        headers=apex_headers,
    )
    assert res.status_code == 404


def test_adv_p18_07_client_org_id_tampering(client: TestClient, p18_adv_fixture):
    """ADV-P18-07: Injected organization_id in request body is ignored (bound to JWT)."""
    f = p18_adv_fixture
    apex_headers = get_token_headers(f["apex_admin"])

    res = client.post(
        "/api/v1/cloud-security/assets",
        json={
            "asset_code": "CLOUD-ORG-TAMPER-01",
            "organization_id": f["org_meridian"].id,  # Malicious attempt to forge tenant
            "provider": "AWS",
            "account_id": "112233445566",
            "region": "us-east-1",
            "resource_type": "S3_BUCKET",
            "resource_arn": "arn:aws:s3:::tamper-bucket",
            "resource_name": "tamper-bucket",
        },
        headers=apex_headers,
    )
    assert res.status_code == 201
    assert res.json()["organization_id"] == f["org_apex"].id


def test_adv_p18_08_unauthorized_cloud_asset_creation_by_viewer(client: TestClient, p18_adv_fixture):
    """ADV-P18-08: Viewer role cannot create cloud assets (403 Forbidden)."""
    f = p18_adv_fixture
    viewer_headers = get_token_headers(f["apex_viewer"])

    res = client.post(
        "/api/v1/cloud-security/assets",
        json={
            "asset_code": "CLOUD-VIEWER-ATTEMPT",
            "provider": "AWS",
            "account_id": "112233445566",
            "region": "us-east-1",
            "resource_type": "S3_BUCKET",
            "resource_arn": "arn:aws:s3:::viewer-bucket",
            "resource_name": "viewer-bucket",
        },
        headers=viewer_headers,
    )
    assert res.status_code == 403


def test_adv_p18_09_unauthorized_benchmark_rule_mutation(client: TestClient, p18_adv_fixture):
    """ADV-P18-09: Viewer role cannot create benchmark rules (403 Forbidden)."""
    f = p18_adv_fixture
    viewer_headers = get_token_headers(f["apex_viewer"])

    res = client.post(
        "/api/v1/cloud-security/rules",
        json={
            "benchmark_id": 1,
            "rule_code": "CIS-RULE-VIEWER",
            "title": "Title",
            "description": "Desc",
            "section": "Sec",
        },
        headers=viewer_headers,
    )
    assert res.status_code == 403


def test_adv_p18_10_decommissioned_cloud_asset_mutation_lockout(client: TestClient, p18_adv_fixture):
    """ADV-P18-10: Decommissioned assets are immutable and block mutations (400 Bad Request)."""
    f = p18_adv_fixture
    apex_headers = get_token_headers(f["apex_admin"])

    create_res = client.post(
        "/api/v1/cloud-security/assets",
        json={
            "asset_code": "CLOUD-DECOM-LOCK-01",
            "provider": "AWS",
            "account_id": "112233445566",
            "region": "us-east-1",
            "resource_type": "S3_BUCKET",
            "resource_arn": "arn:aws:s3:::lock-bucket",
            "resource_name": "lock-bucket",
        },
        headers=apex_headers,
    )
    asset_id = create_res.json()["id"]

    # Decommission
    client.post(
        f"/api/v1/cloud-security/assets/{asset_id}/status",
        json={"lifecycle_state": "DECOMMISSIONED"},
        headers=apex_headers,
    )

    # Attempt patch on decommissioned asset
    res = client.patch(
        f"/api/v1/cloud-security/assets/{asset_id}",
        json={"resource_name": "new-name"},
        headers=apex_headers,
    )
    assert res.status_code == 400
    assert "immutable" in res.json()["detail"].lower()


def test_adv_p18_11_illegal_lifecycle_state_machine_transition(client: TestClient, p18_adv_fixture):
    """ADV-P18-11: Attempting illegal state transition from DECOMMISSIONED returns 422."""
    f = p18_adv_fixture
    apex_headers = get_token_headers(f["apex_admin"])

    create_res = client.post(
        "/api/v1/cloud-security/assets",
        json={
            "asset_code": "CLOUD-STATE-JUMP-01",
            "provider": "AWS",
            "account_id": "112233445566",
            "region": "us-east-1",
            "resource_type": "S3_BUCKET",
            "resource_arn": "arn:aws:s3:::state-jump-bucket",
            "resource_name": "state-jump-bucket",
        },
        headers=apex_headers,
    )
    asset_id = create_res.json()["id"]

    client.post(
        f"/api/v1/cloud-security/assets/{asset_id}/status",
        json={"lifecycle_state": "DECOMMISSIONED"},
        headers=apex_headers,
    )

    # Illegal attempt: DECOMMISSIONED -> ACTIVE
    res = client.post(
        f"/api/v1/cloud-security/assets/{asset_id}/status",
        json={"lifecycle_state": "ACTIVE"},
        headers=apex_headers,
    )
    assert res.status_code == 422


def test_adv_p18_12_active_cloud_asset_direct_deletion_attempt(client: TestClient, p18_adv_fixture):
    """ADV-P18-12: Active cloud asset cannot be deleted directly (400 Bad Request)."""
    f = p18_adv_fixture
    apex_headers = get_token_headers(f["apex_admin"])

    create_res = client.post(
        "/api/v1/cloud-security/assets",
        json={
            "asset_code": "CLOUD-ACTIVE-DEL-01",
            "provider": "AWS",
            "account_id": "112233445566",
            "region": "us-east-1",
            "resource_type": "EC2_INSTANCE",
            "resource_arn": "arn:aws:ec2:us-east-1:112233445566:instance/i-act",
            "resource_name": "act-server",
        },
        headers=apex_headers,
    )
    asset_id = create_res.json()["id"]

    res = client.delete(f"/api/v1/cloud-security/assets/{asset_id}", headers=apex_headers)
    assert res.status_code == 400


def test_adv_p18_13_cross_tenant_software_product_foreign_key_escape(client: TestClient, db: Session, p18_adv_fixture):
    """ADV-P18-13: Cannot link cloud asset to another tenant's software product (404 Not Found)."""
    f = p18_adv_fixture
    # Create software product in Meridian
    meridian_prod = SoftwareProduct(
        organization_id=f["org_meridian"].id,
        product_code="PROD-MERIDIAN-001",
        name="Meridian Secret App",
        owner_id=f["meridian_admin"].id,
    )
    db.add(meridian_prod)
    db.commit()
    db.refresh(meridian_prod)

    apex_headers = get_token_headers(f["apex_admin"])
    res = client.post(
        "/api/v1/cloud-security/assets",
        json={
            "asset_code": "CLOUD-CROSS-PROD-01",
            "provider": "AWS",
            "account_id": "112233445566",
            "region": "us-east-1",
            "resource_type": "EC2_INSTANCE",
            "resource_arn": "arn:aws:ec2:us-east-1:112233445566:instance/i-crossprod",
            "resource_name": "crossprod-server",
            "software_product_id": meridian_prod.id,  # Foreign tenant product ID
        },
        headers=apex_headers,
    )
    assert res.status_code == 404


def test_adv_p18_14_cross_tenant_remediation_plan_foreign_key_escape(client: TestClient, db: Session, p18_adv_fixture):
    """ADV-P18-14: Cannot link cloud asset to another tenant's remediation plan (404 Not Found)."""
    f = p18_adv_fixture
    meridian_audit = Audit(
        organization_id=f["org_meridian"].id,
        title="Meridian Audit",
        audit_type=AuditTypeEnum.INTERNAL,
        objective="Verify security compliance",
        lead_auditor_id=f["meridian_admin"].id,
    )
    db.add(meridian_audit)
    db.commit()
    db.refresh(meridian_audit)

    # Create remediation plan in Meridian
    meridian_plan = RemediationPlan(
        organization_id=f["org_meridian"].id,
        plan_code="REM-MERIDIAN-001",
        title="Meridian Internal Fix",
        problem_statement="Problem details",
        root_cause_classification=RemediationRootCauseClassificationEnum.CONFIGURATION_DRIFT,
        source_type=RemediationSourceTypeEnum.AUDIT,
        audit_id=meridian_audit.id,
        plan_owner_id=f["meridian_admin"].id,
    )
    db.add(meridian_plan)
    db.commit()
    db.refresh(meridian_plan)

    apex_headers = get_token_headers(f["apex_admin"])
    res = client.post(
        "/api/v1/cloud-security/assets",
        json={
            "asset_code": "CLOUD-CROSS-REM-01",
            "provider": "AWS",
            "account_id": "112233445566",
            "region": "us-east-1",
            "resource_type": "EC2_INSTANCE",
            "resource_arn": "arn:aws:ec2:us-east-1:112233445566:instance/i-crossrem",
            "resource_name": "crossrem-server",
            "remediation_plan_id": meridian_plan.id,
        },
        headers=apex_headers,
    )
    assert res.status_code == 404


def test_adv_p18_15_duplicate_asset_code_collision(client: TestClient, p18_adv_fixture):
    """ADV-P18-15: Attempting duplicate asset code in the same tenant yields 409 Conflict."""
    f = p18_adv_fixture
    apex_headers = get_token_headers(f["apex_admin"])

    payload = {
        "asset_code": "CLOUD-DUP-CODE-01",
        "provider": "AWS",
        "account_id": "112233445566",
        "region": "us-east-1",
        "resource_type": "S3_BUCKET",
        "resource_arn": "arn:aws:s3:::dup-code-bucket-1",
        "resource_name": "dup-bucket-1",
    }
    r1 = client.post("/api/v1/cloud-security/assets", json=payload, headers=apex_headers)
    assert r1.status_code == 201

    payload["resource_arn"] = "arn:aws:s3:::dup-code-bucket-2"
    r2 = client.post("/api/v1/cloud-security/assets", json=payload, headers=apex_headers)
    assert r2.status_code == 409


def test_adv_p18_16_duplicate_resource_arn_collision(client: TestClient, p18_adv_fixture):
    """ADV-P18-16: Attempting duplicate resource ARN in the same tenant yields 409 Conflict."""
    f = p18_adv_fixture
    apex_headers = get_token_headers(f["apex_admin"])

    payload = {
        "asset_code": "CLOUD-DUP-ARN-01",
        "provider": "AWS",
        "account_id": "112233445566",
        "region": "us-east-1",
        "resource_type": "S3_BUCKET",
        "resource_arn": "arn:aws:s3:::same-arn-bucket",
        "resource_name": "same-arn-bucket",
    }
    r1 = client.post("/api/v1/cloud-security/assets", json=payload, headers=apex_headers)
    assert r1.status_code == 201

    payload["asset_code"] = "CLOUD-DUP-ARN-02"
    r2 = client.post("/api/v1/cloud-security/assets", json=payload, headers=apex_headers)
    assert r2.status_code == 409


def test_adv_p18_17_client_posture_score_injection_bypass(client: TestClient, p18_adv_fixture):
    """ADV-P18-17: Client-injected posture_score is ignored in favor of server authority."""
    f = p18_adv_fixture
    apex_headers = get_token_headers(f["apex_admin"])

    res = client.post(
        "/api/v1/cloud-security/assets",
        json={
            "asset_code": "CLOUD-SCORE-INJECT-01",
            "provider": "AWS",
            "account_id": "112233445566",
            "region": "us-east-1",
            "resource_type": "S3_BUCKET",
            "resource_arn": "arn:aws:s3:::score-inject-bucket",
            "resource_name": "score-inject-bucket",
            "posture_score": 12.34,  # Malicious forged client score
        },
        headers=apex_headers,
    )
    assert res.status_code == 201
    # Server sets baseline to 100.00
    assert res.json()["posture_score"] == 100.00


def test_adv_p18_18_client_blast_radius_injection_bypass(client: TestClient, p18_adv_fixture):
    """ADV-P18-18: Client-injected blast_radius_index is ignored in favor of server calculation."""
    f = p18_adv_fixture
    apex_headers = get_token_headers(f["apex_admin"])

    create_res = client.post(
        "/api/v1/cloud-security/assets",
        json={
            "asset_code": "CLOUD-BLAST-INJECT-01",
            "provider": "AWS",
            "account_id": "112233445566",
            "region": "us-east-1",
            "resource_type": "S3_BUCKET",
            "resource_arn": "arn:aws:s3:::blast-inject-bucket",
            "resource_name": "blast-inject-bucket",
        },
        headers=apex_headers,
    )
    asset_id = create_res.json()["id"]

    res = client.post(
        "/api/v1/cloud-security/blast-radius",
        json={
            "analysis_code": "BLAST-FORGED-01",
            "cloud_asset_id": asset_id,
            "iam_principal_arn": "arn:aws:iam::112233445566:role/TestRole",
            "effective_permissions_count": 2,
            "admin_privilege_granted": False,
            "cross_account_access": False,
            "data_access_scope": "METADATA_ONLY",
            "blast_radius_index": 99.99,  # Forged client score
        },
        headers=apex_headers,
    )
    assert res.status_code == 201
    # Server calculates 2 * 1.5 + 0 = 3.00
    assert res.json()["blast_radius_index"] == 3.00


def test_adv_p18_19_negative_out_of_range_permissions_count(client: TestClient, p18_adv_fixture):
    """ADV-P18-19: Negative effective permissions count in blast radius is rejected with 422."""
    f = p18_adv_fixture
    apex_headers = get_token_headers(f["apex_admin"])

    res = client.post(
        "/api/v1/cloud-security/blast-radius/preview",
        json={"effective_permissions_count": -10},
        headers=apex_headers,
    )
    assert res.status_code == 422


def test_adv_p18_20_cross_tenant_finding_read_isolation(client: TestClient, p18_adv_fixture):
    """ADV-P18-20: Tenant A cannot view Tenant B's security findings."""
    f = p18_adv_fixture
    meridian_headers = get_token_headers(f["meridian_admin"])
    apex_headers = get_token_headers(f["apex_admin"])

    # Seed Meridian asset & finding
    asset_res = client.post(
        "/api/v1/cloud-security/assets",
        json={
            "asset_code": "MERIDIAN-ISOL-ASSET",
            "provider": "AWS",
            "account_id": "999888777666",
            "region": "us-east-1",
            "resource_type": "S3_BUCKET",
            "resource_arn": "arn:aws:s3:::meridian-isol-bucket",
            "resource_name": "meridian-isol-bucket",
        },
        headers=meridian_headers,
    )
    b_res = client.post(
        "/api/v1/cloud-security/benchmarks",
        json={
            "benchmark_code": "CIS-AWS-ISOL",
            "name": "CIS AWS",
            "version": "1.0",
            "framework": "CIS_AWS_FOUNDATIONS",
            "provider": "AWS",
        },
        headers=meridian_headers,
    )
    r_res = client.post(
        "/api/v1/cloud-security/rules",
        json={
            "benchmark_id": b_res.json()["id"],
            "rule_code": "CIS-AWS-ISOL.1",
            "title": "Title",
            "description": "Desc",
            "section": "Sec",
        },
        headers=meridian_headers,
    )
    client.post(
        "/api/v1/cloud-security/findings",
        json={
            "finding_code": "MERIDIAN-SECRET-FIND",
            "cloud_asset_id": asset_res.json()["id"],
            "rule_id": r_res.json()["id"],
            "evaluation_status": "FAILED",
        },
        headers=meridian_headers,
    )

    # Apex queries findings
    apex_findings = client.get("/api/v1/cloud-security/findings", headers=apex_headers).json()
    for f_item in apex_findings:
        assert f_item["finding_code"] != "MERIDIAN-SECRET-FIND"


def test_adv_p18_21_cross_tenant_drift_read_isolation(client: TestClient, p18_adv_fixture):
    """ADV-P18-21: Tenant A cannot view Tenant B's configuration drift records."""
    f = p18_adv_fixture
    meridian_headers = get_token_headers(f["meridian_admin"])
    apex_headers = get_token_headers(f["apex_admin"])

    asset_res = client.post(
        "/api/v1/cloud-security/assets",
        json={
            "asset_code": "MERIDIAN-DRIFT-ASSET",
            "provider": "AWS",
            "account_id": "999888777666",
            "region": "us-east-1",
            "resource_type": "S3_BUCKET",
            "resource_arn": "arn:aws:s3:::meridian-drift-bucket",
            "resource_name": "meridian-drift-bucket",
        },
        headers=meridian_headers,
    )
    client.post(
        "/api/v1/cloud-security/drifts",
        json={
            "drift_code": "MERIDIAN-CONF-DRIFT-01",
            "cloud_asset_id": asset_res.json()["id"],
            "attribute_path": "tags.environment",
            "baseline_value": "prod",
            "drifted_value": "dev",
        },
        headers=meridian_headers,
    )

    apex_drifts = client.get("/api/v1/cloud-security/drifts", headers=apex_headers).json()
    for d in apex_drifts:
        assert d["drift_code"] != "MERIDIAN-CONF-DRIFT-01"


def test_adv_p18_22_finding_risk_score_manipulation_ignored(client: TestClient, p18_adv_fixture):
    """ADV-P18-22: Client-supplied risk_score on findings is recalculated server-side."""
    f = p18_adv_fixture
    apex_headers = get_token_headers(f["apex_admin"])

    asset_res = client.post(
        "/api/v1/cloud-security/assets",
        json={
            "asset_code": "CLOUD-FIND-SCORE-01",
            "provider": "AWS",
            "account_id": "112233445566",
            "region": "us-east-1",
            "resource_type": "S3_BUCKET",
            "resource_arn": "arn:aws:s3:::find-score-bucket",
            "resource_name": "find-score-bucket",
        },
        headers=apex_headers,
    )
    b_res = client.post(
        "/api/v1/cloud-security/benchmarks",
        json={
            "benchmark_code": "CIS-AWS-SCORE-CHECK",
            "name": "CIS AWS",
            "version": "1.0",
            "framework": "CIS_AWS_FOUNDATIONS",
            "provider": "AWS",
        },
        headers=apex_headers,
    )
    r_res = client.post(
        "/api/v1/cloud-security/rules",
        json={
            "benchmark_id": b_res.json()["id"],
            "rule_code": "CIS-AWS-SCORE.1",
            "title": "Title",
            "description": "Desc",
            "section": "Sec",
            "severity": "CRITICAL",
        },
        headers=apex_headers,
    )
    f_res = client.post(
        "/api/v1/cloud-security/findings",
        json={
            "finding_code": "FIND-SCORE-TEST-01",
            "cloud_asset_id": asset_res.json()["id"],
            "rule_id": r_res.json()["id"],
            "evaluation_status": "FAILED",
            "severity": "CRITICAL",
            "risk_score": 0.01,  # Injected low score
        },
        headers=apex_headers,
    )
    assert f_res.status_code == 201
    # Server assigns 90.00 for CRITICAL
    assert f_res.json()["risk_score"] == 90.00


def test_adv_p18_23_duplicate_benchmark_code_collision(client: TestClient, p18_adv_fixture):
    """ADV-P18-23: Duplicate benchmark code registration yields 409 Conflict."""
    f = p18_adv_fixture
    apex_headers = get_token_headers(f["apex_admin"])

    payload = {
        "benchmark_code": "CIS-BENCH-COLLISION-01",
        "name": "CIS Benchmark",
        "version": "1.0",
        "framework": "CIS_AWS_FOUNDATIONS",
        "provider": "AWS",
    }
    r1 = client.post("/api/v1/cloud-security/benchmarks", json=payload, headers=apex_headers)
    assert r1.status_code == 201

    r2 = client.post("/api/v1/cloud-security/benchmarks", json=payload, headers=apex_headers)
    assert r2.status_code == 409


def test_adv_p18_24_duplicate_rule_code_collision(client: TestClient, p18_adv_fixture):
    """ADV-P18-24: Duplicate benchmark check rule code yields 409 Conflict."""
    f = p18_adv_fixture
    apex_headers = get_token_headers(f["apex_admin"])

    b_res = client.post(
        "/api/v1/cloud-security/benchmarks",
        json={
            "benchmark_code": "CIS-RULE-COLL-BENCH",
            "name": "CIS Benchmark",
            "version": "1.0",
            "framework": "CIS_AWS_FOUNDATIONS",
            "provider": "AWS",
        },
        headers=apex_headers,
    )
    rule_payload = {
        "benchmark_id": b_res.json()["id"],
        "rule_code": "CIS-RULE-UNIQUE-01",
        "title": "Rule 1",
        "description": "Desc",
        "section": "Sec",
    }
    r1 = client.post("/api/v1/cloud-security/rules", json=rule_payload, headers=apex_headers)
    assert r1.status_code == 201

    r2 = client.post("/api/v1/cloud-security/rules", json=rule_payload, headers=apex_headers)
    assert r2.status_code == 409


def test_adv_p18_25_unauthenticated_cloudsec_endpoint_infiltration(client: TestClient):
    """ADV-P18-25: Unauthenticated access to CloudSec endpoints yields 401 Unauthorized."""
    assert client.get("/api/v1/cloud-security/assets").status_code == 401
    assert client.post("/api/v1/cloud-security/assets", json={}).status_code == 401
    assert client.get("/api/v1/cloud-security/posture/summary").status_code == 401
