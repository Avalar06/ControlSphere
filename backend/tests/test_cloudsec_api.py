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
    CloudCriticalityEnum,
    CloudEnvironmentEnum,
    CloudLifecycleStateEnum,
    CloudPostureStatusEnum,
    CloudProviderEnum,
    DataAccessScopeEnum,
    DriftSeverityEnum,
    DriftStatusEnum,
    EvaluationStatusEnum,
    RuleSeverityEnum,
)
from tests.conftest import get_token_headers


@pytest.fixture
def cs_api_fixture(db: Session, org_apex: Organization, org_meridian: Organization):
    """Setup multi-tenant organizations and users across roles for CloudSec API testing."""
    admin = User(
        email="cs_admin@apex.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="CloudSec Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_apex.id,
    )
    manager = User(
        email="cs_manager@apex.com",
        hashed_password=get_password_hash("ManagerPass123!"),
        full_name="CloudSec Manager",
        role=RoleEnum.MANAGER,
        is_active=True,
        organization_id=org_apex.id,
    )
    sec_analyst = User(
        email="cs_sec_analyst@apex.com",
        hashed_password=get_password_hash("SecAnalystPass123!"),
        full_name="CloudSec Sec Analyst",
        role=RoleEnum.SECURITY_ANALYST,
        is_active=True,
        organization_id=org_apex.id,
    )
    viewer = User(
        email="cs_viewer@apex.com",
        hashed_password=get_password_hash("ViewerPass123!"),
        full_name="CloudSec Viewer",
        role=RoleEnum.VIEWER,
        is_active=True,
        organization_id=org_apex.id,
    )
    meridian_admin = User(
        email="cs_admin@meridian.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Meridian Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_meridian.id,
    )

    db.add_all([admin, manager, sec_analyst, viewer, meridian_admin])
    db.commit()
    for u in [admin, manager, sec_analyst, viewer, meridian_admin]:
        db.refresh(u)

    return {
        "admin": admin,
        "manager": manager,
        "sec_analyst": sec_analyst,
        "viewer": viewer,
        "meridian_admin": meridian_admin,
        "org_apex": org_apex,
        "org_meridian": org_meridian,
    }


def test_create_and_get_cloud_asset_api(client: TestClient, cs_api_fixture):
    users = cs_api_fixture
    headers = get_token_headers(users["admin"])

    payload = {
        "asset_code": "CLOUD-AWS-S3-001",
        "provider": "AWS",
        "account_id": "112233445566",
        "region": "us-east-1",
        "resource_type": "S3_BUCKET",
        "resource_arn": "arn:aws:s3:::apex-secure-vault",
        "resource_name": "apex-secure-vault",
        "environment": "PRODUCTION",
        "criticality": "CRITICAL",
        "is_internet_facing": False,
        "encryption_enabled": True,
    }

    res = client.post("/api/v1/cloud-security/assets", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["asset_code"] == "CLOUD-AWS-S3-001"
    assert data["posture_status"] == "COMPLIANT"
    assert data["posture_score"] == 100.00
    asset_id = data["id"]

    # Read back
    res_get = client.get(f"/api/v1/cloud-security/assets/{asset_id}", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["resource_arn"] == "arn:aws:s3:::apex-secure-vault"


def test_list_and_filter_cloud_assets_api(client: TestClient, cs_api_fixture):
    users = cs_api_fixture
    headers = get_token_headers(users["admin"])

    # Create 2 assets
    client.post(
        "/api/v1/cloud-security/assets",
        json={
            "asset_code": "CLOUD-AWS-EC2-001",
            "provider": "AWS",
            "account_id": "112233445566",
            "region": "us-east-1",
            "resource_type": "EC2_INSTANCE",
            "resource_arn": "arn:aws:ec2:us-east-1:112233445566:instance/i-001",
            "resource_name": "app-server-01",
            "environment": "PRODUCTION",
        },
        headers=headers,
    )
    client.post(
        "/api/v1/cloud-security/assets",
        json={
            "asset_code": "CLOUD-AZURE-VM-001",
            "provider": "AZURE",
            "account_id": "sub-123",
            "region": "westeurope",
            "resource_type": "EC2_INSTANCE",
            "resource_arn": "/subscriptions/sub-123/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm01",
            "resource_name": "azure-vm-01",
            "environment": "DEVELOPMENT",
        },
        headers=headers,
    )

    res_all = client.get("/api/v1/cloud-security/assets", headers=headers)
    assert res_all.status_code == 200
    assert len(res_all.json()) >= 2

    res_aws = client.get("/api/v1/cloud-security/assets?provider=AWS", headers=headers)
    assert res_aws.status_code == 200
    for a in res_aws.json():
        assert a["provider"] == "AWS"


def test_update_and_lifecycle_transition_cloud_asset_api(client: TestClient, cs_api_fixture):
    users = cs_api_fixture
    headers = get_token_headers(users["admin"])

    create_res = client.post(
        "/api/v1/cloud-security/assets",
        json={
            "asset_code": "CLOUD-GCP-K8S-001",
            "provider": "GCP",
            "account_id": "gcp-prod-proj",
            "region": "us-central1",
            "resource_type": "KUBERNETES_CLUSTER",
            "resource_arn": "//container.googleapis.com/projects/gcp-prod-proj/zones/us-central1-a/clusters/prod-gke",
            "resource_name": "prod-gke",
        },
        headers=headers,
    )
    asset_id = create_res.json()["id"]

    # Patch resource metadata
    patch_res = client.patch(
        f"/api/v1/cloud-security/assets/{asset_id}",
        json={"resource_name": "prod-gke-renamed", "is_internet_facing": True},
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["resource_name"] == "prod-gke-renamed"
    assert patch_res.json()["is_internet_facing"] == True

    # Transition to DECOMMISSIONED
    stat_res = client.post(
        f"/api/v1/cloud-security/assets/{asset_id}/status",
        json={"lifecycle_state": "DECOMMISSIONED", "notes": "Workload migrated to serverless"},
        headers=headers,
    )
    assert stat_res.status_code == 200
    assert stat_res.json()["lifecycle_state"] == "DECOMMISSIONED"


def test_delete_cloud_asset_api(client: TestClient, cs_api_fixture):
    users = cs_api_fixture
    headers = get_token_headers(users["admin"])

    create_res = client.post(
        "/api/v1/cloud-security/assets",
        json={
            "asset_code": "CLOUD-AWS-RDS-DEL",
            "provider": "AWS",
            "account_id": "112233445566",
            "region": "us-east-1",
            "resource_type": "RDS_DATABASE",
            "resource_arn": "arn:aws:rds:us-east-1:112233445566:db:temp-db",
            "resource_name": "temp-db",
        },
        headers=headers,
    )
    asset_id = create_res.json()["id"]

    # Active asset delete rejected
    del_fail = client.delete(f"/api/v1/cloud-security/assets/{asset_id}", headers=headers)
    assert del_fail.status_code == 400

    # Decommission first
    client.post(
        f"/api/v1/cloud-security/assets/{asset_id}/status",
        json={"lifecycle_state": "DECOMMISSIONED"},
        headers=headers,
    )

    del_ok = client.delete(f"/api/v1/cloud-security/assets/{asset_id}", headers=headers)
    assert del_ok.status_code == 204


def test_benchmarks_and_rules_api(client: TestClient, cs_api_fixture):
    users = cs_api_fixture
    headers = get_token_headers(users["admin"])

    b_res = client.post(
        "/api/v1/cloud-security/benchmarks",
        json={
            "benchmark_code": "CIS-AZURE-2.0",
            "name": "CIS Microsoft Azure Foundations Benchmark",
            "version": "2.0.0",
            "framework": "CIS_AZURE_FOUNDATIONS",
            "provider": "AZURE",
        },
        headers=headers,
    )
    assert b_res.status_code == 201
    bench_id = b_res.json()["id"]

    r_res = client.post(
        "/api/v1/cloud-security/rules",
        json={
            "benchmark_id": bench_id,
            "rule_code": "CIS-AZURE-3.1",
            "title": "Ensure Storage Account Access Keys are Periodically Regenerated",
            "description": "Access key rotation mitigates credential theft",
            "section": "3. Storage",
            "severity": "HIGH",
        },
        headers=headers,
    )
    assert r_res.status_code == 201
    assert r_res.json()["rule_code"] == "CIS-AZURE-3.1"


def test_findings_and_evaluations_api(client: TestClient, cs_api_fixture):
    users = cs_api_fixture
    headers_admin = get_token_headers(users["admin"])
    headers_sec = get_token_headers(users["sec_analyst"])

    # Create asset, bench, rule
    asset_res = client.post(
        "/api/v1/cloud-security/assets",
        json={
            "asset_code": "CLOUD-AWS-FIND-01",
            "provider": "AWS",
            "account_id": "112233445566",
            "region": "us-east-1",
            "resource_type": "SECURITY_GROUP",
            "resource_arn": "arn:aws:ec2:us-east-1:112233445566:security-group/sg-01",
            "resource_name": "sg-open-ssh",
        },
        headers=headers_admin,
    )
    asset_id = asset_res.json()["id"]

    b_res = client.post(
        "/api/v1/cloud-security/benchmarks",
        json={
            "benchmark_code": "CIS-AWS-4.0",
            "name": "CIS AWS Benchmark v4",
            "version": "4.0.0",
            "framework": "CIS_AWS_FOUNDATIONS",
            "provider": "AWS",
        },
        headers=headers_admin,
    )
    r_res = client.post(
        "/api/v1/cloud-security/rules",
        json={
            "benchmark_id": b_res.json()["id"],
            "rule_code": "CIS-AWS-4.1",
            "title": "Ensure no security groups allow ingress from 0.0.0.0/0 to port 22",
            "description": "Public SSH",
            "section": "4. Networking",
            "severity": "CRITICAL",
        },
        headers=headers_admin,
    )

    # Record finding using sec analyst
    f_res = client.post(
        "/api/v1/cloud-security/findings",
        json={
            "finding_code": "FIND-AWS-SSH-01",
            "cloud_asset_id": asset_id,
            "rule_id": r_res.json()["id"],
            "evaluation_status": "FAILED",
            "severity": "CRITICAL",
            "actual_value": "port 22 open to 0.0.0.0/0",
            "expected_value": "port 22 restricted to corporate CIDR",
        },
        headers=headers_sec,
    )
    assert f_res.status_code == 201
    assert f_res.json()["risk_score"] == 90.00


def test_drift_events_api(client: TestClient, cs_api_fixture):
    users = cs_api_fixture
    headers_admin = get_token_headers(users["admin"])
    headers_sec = get_token_headers(users["sec_analyst"])

    asset_res = client.post(
        "/api/v1/cloud-security/assets",
        json={
            "asset_code": "CLOUD-AWS-DRIFT-01",
            "provider": "AWS",
            "account_id": "112233445566",
            "region": "us-east-1",
            "resource_type": "S3_BUCKET",
            "resource_arn": "arn:aws:s3:::drift-bucket-01",
            "resource_name": "drift-bucket-01",
        },
        headers=headers_admin,
    )
    asset_id = asset_res.json()["id"]

    drift_res = client.post(
        "/api/v1/cloud-security/drifts",
        json={
            "drift_code": "DRIFT-S3-001",
            "cloud_asset_id": asset_id,
            "attribute_path": "publicAccessBlock.blockPublicAcls",
            "baseline_value": "true",
            "drifted_value": "false",
            "drift_severity": "HIGH",
        },
        headers=headers_sec,
    )
    assert drift_res.status_code == 201
    assert drift_res.json()["drift_score"] == 70.00


def test_iam_blast_radius_and_preview_api(client: TestClient, cs_api_fixture):
    users = cs_api_fixture
    headers = get_token_headers(users["admin"])

    # Preview endpoint
    prev_res = client.post(
        "/api/v1/cloud-security/blast-radius/preview",
        json={
            "effective_permissions_count": 20,
            "admin_privilege_granted": True,
            "cross_account_access": True,
            "data_access_scope": "FULL_DATASTORE",
        },
        headers=headers,
    )
    assert prev_res.status_code == 200
    assert prev_res.json()["blast_radius_index"] == 100.00
    assert prev_res.json()["risk_band"] == "CRITICAL"


def test_cloudsec_posture_summary_api(client: TestClient, cs_api_fixture):
    users = cs_api_fixture
    headers = get_token_headers(users["viewer"])

    res = client.get("/api/v1/cloud-security/posture/summary", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "total_cloud_assets" in data
    assert "average_posture_score" in data
