import pytest
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.cloudsec import (
    BlastRadiusBandEnum,
    CloudAsset,
    CloudAssetTypeEnum,
    CloudCriticalityEnum,
    CloudEnvironmentEnum,
    CloudLifecycleStateEnum,
    CloudPostureStatusEnum,
    CloudProviderEnum,
    CloudSecurityBenchmark,
    CloudBenchmarkRule,
    CloudSecurityFinding,
    CloudConfigurationDrift,
    CloudIAMBlastRadius,
    DataAccessScopeEnum,
    DriftSeverityEnum,
    DriftStatusEnum,
    EvaluationStatusEnum,
    RuleSeverityEnum,
    BenchmarkFrameworkEnum,
)
from app.models.organization import Organization
from app.models.user import User, RoleEnum
from app.schemas.cloudsec import (
    CloudAssetCreate,
    CloudAssetStatusUpdate,
    CloudAssetUpdate,
    CloudBenchmarkRuleCreate,
    CloudConfigurationDriftCreate,
    CloudIAMBlastRadiusCreate,
    CloudSecurityBenchmarkCreate,
    CloudSecurityFindingCreate,
)
from app.services.cloudsec_service import CloudSecService


@pytest.fixture
def org_and_user(db: Session):
    ts = datetime.now().timestamp()
    org = Organization(name=f"CloudSec Test Org {ts}", slug=f"cloudsec-test-org-{ts}")
    db.add(org)
    db.commit()
    db.refresh(org)

    user = User(
        email=f"cloudsec_admin_{datetime.now().timestamp()}@example.com",
        hashed_password="hashed_pwd",
        full_name="CloudSec Admin",
        role=RoleEnum.ADMIN,
        organization_id=org.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return org, user


def test_cloud_posture_score_calculation():
    """Test deterministic calculation of Cloud Posture Score."""
    f1 = CloudSecurityFinding(severity=RuleSeverityEnum.CRITICAL, evaluation_status=EvaluationStatusEnum.FAILED)
    f2 = CloudSecurityFinding(severity=RuleSeverityEnum.HIGH, evaluation_status=EvaluationStatusEnum.FAILED)
    f3 = CloudSecurityFinding(severity=RuleSeverityEnum.LOW, evaluation_status=EvaluationStatusEnum.PASSED)

    # 100 - (25 + 15) * 1.0 = 60.0
    score_internal = CloudSecService.calculate_asset_posture_score([f1, f2, f3], is_internet_facing=False)
    assert score_internal == 60.00

    # 100 - (25 + 15) * 1.3 = 100 - 52.0 = 48.0
    score_public = CloudSecService.calculate_asset_posture_score([f1, f2, f3], is_internet_facing=True)
    assert score_public == 48.00


def test_cloud_posture_boundary_clamping():
    """Test lower boundary clamping of posture score at 0.00."""
    massive_findings = [
        CloudSecurityFinding(severity=RuleSeverityEnum.CRITICAL, evaluation_status=EvaluationStatusEnum.FAILED)
        for _ in range(10)
    ]
    score = CloudSecService.calculate_asset_posture_score(massive_findings, is_internet_facing=True)
    assert score == 0.00


def test_iam_blast_radius_formula():
    """Test IAM blast radius scoring and severity band categorization."""
    # Low risk
    score_low, band_low, bd_low = CloudSecService.calculate_iam_blast_radius(
        effective_permissions_count=5,
        admin_privilege_granted=False,
        cross_account_access=False,
        data_access_scope=DataAccessScopeEnum.METADATA_ONLY,
    )
    assert score_low == 7.50
    assert band_low == BlastRadiusBandEnum.LOW

    # Critical risk
    score_crit, band_crit, bd_crit = CloudSecService.calculate_iam_blast_radius(
        effective_permissions_count=50,
        admin_privilege_granted=True,
        cross_account_access=True,
        data_access_scope=DataAccessScopeEnum.FULL_DATASTORE,
    )
    # min(30, 75) + 50 + 20 + 30 = 130 -> clamped to 100.0
    assert score_crit == 100.00
    assert band_crit == BlastRadiusBandEnum.CRITICAL


def test_drift_score_mapping():
    """Test drift severity score mapping."""
    assert CloudSecService.calculate_drift_score(DriftSeverityEnum.CRITICAL) == 90.00
    assert CloudSecService.calculate_drift_score(DriftSeverityEnum.HIGH) == 70.00
    assert CloudSecService.calculate_drift_score(DriftSeverityEnum.MEDIUM) == 40.00
    assert CloudSecService.calculate_drift_score(DriftSeverityEnum.LOW) == 15.00


def test_cloud_asset_lifecycle_transitions(db: Session, org_and_user):
    """Test governed lifecycle state transitions for cloud assets."""
    org, user = org_and_user

    data = CloudAssetCreate(
        asset_code="AWS-S3-TEST-001",
        provider=CloudProviderEnum.AWS,
        account_id="123456789012",
        region="us-east-1",
        resource_type=CloudAssetTypeEnum.S3_BUCKET,
        resource_arn="arn:aws:s3:::test-bucket-001",
        resource_name="test-bucket-001",
        environment=CloudEnvironmentEnum.PRODUCTION,
        criticality=CloudCriticalityEnum.HIGH,
        is_internet_facing=False,
        encryption_enabled=True,
    )
    asset = CloudSecService.create_asset(db, org.id, user.id, data)
    assert asset.lifecycle_state == CloudLifecycleStateEnum.ACTIVE

    # ACTIVE -> MAINTENANCE
    CloudSecService.update_asset_status(
        db, org.id, user.id, asset.id, CloudAssetStatusUpdate(lifecycle_state=CloudLifecycleStateEnum.MAINTENANCE)
    )
    db.refresh(asset)
    assert asset.lifecycle_state == CloudLifecycleStateEnum.MAINTENANCE

    # MAINTENANCE -> DECOMMISSIONED
    CloudSecService.update_asset_status(
        db, org.id, user.id, asset.id, CloudAssetStatusUpdate(lifecycle_state=CloudLifecycleStateEnum.DECOMMISSIONED)
    )
    db.refresh(asset)
    assert asset.lifecycle_state == CloudLifecycleStateEnum.DECOMMISSIONED

    # DECOMMISSIONED is terminal
    with pytest.raises(HTTPException) as exc:
        CloudSecService.update_asset_status(
            db, org.id, user.id, asset.id, CloudAssetStatusUpdate(lifecycle_state=CloudLifecycleStateEnum.ACTIVE)
        )
    assert exc.value.status_code == 422


def test_active_asset_deletion_protection(db: Session, org_and_user):
    """Active cloud assets cannot be deleted without decommissioning first."""
    org, user = org_and_user

    data = CloudAssetCreate(
        asset_code="AWS-EC2-TEST-002",
        provider=CloudProviderEnum.AWS,
        account_id="123456789012",
        region="us-east-1",
        resource_type=CloudAssetTypeEnum.EC2_INSTANCE,
        resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-123456789",
        resource_name="prod-web-01",
        environment=CloudEnvironmentEnum.PRODUCTION,
        criticality=CloudCriticalityEnum.CRITICAL,
    )
    asset = CloudSecService.create_asset(db, org.id, user.id, data)

    with pytest.raises(HTTPException) as exc:
        CloudSecService.delete_asset(db, org.id, user.id, asset.id)
    assert exc.value.status_code == 400


def test_finding_creation_and_posture_recalculation(db: Session, org_and_user):
    """Recording a finding triggers automatic server-side posture score recalculation."""
    org, user = org_and_user

    # Create benchmark and rule
    bench = CloudSecService.create_benchmark(
        db,
        CloudSecurityBenchmarkCreate(
            benchmark_code="CIS-AWS-1.5",
            name="CIS AWS Foundations Benchmark",
            version="1.5.0",
            framework=BenchmarkFrameworkEnum.CIS_AWS_FOUNDATIONS,
            provider=CloudProviderEnum.AWS,
        ),
    )
    rule = CloudSecService.create_rule(
        db,
        CloudBenchmarkRuleCreate(
            benchmark_id=bench.id,
            rule_code="CIS-AWS-1.16",
            title="Ensure IAM policies do not grant full administrative privileges",
            description="Full admin access poses critical risk",
            section="1. IAM",
            severity=RuleSeverityEnum.CRITICAL,
        ),
    )

    asset = CloudSecService.create_asset(
        db,
        org.id,
        user.id,
        CloudAssetCreate(
            asset_code="AWS-IAM-TEST-003",
            provider=CloudProviderEnum.AWS,
            account_id="123456789012",
            region="global",
            resource_type=CloudAssetTypeEnum.IAM_ROLE,
            resource_arn="arn:aws:iam::123456789012:role/AdminRole",
            resource_name="AdminRole",
            is_internet_facing=False,
        ),
    )
    assert float(asset.posture_score) == 100.00

    # Record Critical FAILED finding (-25)
    finding = CloudSecService.record_finding(
        db,
        org.id,
        user.id,
        CloudSecurityFindingCreate(
            finding_code="FIND-AWS-001",
            cloud_asset_id=asset.id,
            rule_id=rule.id,
            evaluation_status=EvaluationStatusEnum.FAILED,
            severity=RuleSeverityEnum.CRITICAL,
        ),
    )
    db.refresh(asset)
    assert float(asset.posture_score) == 75.00
    assert asset.posture_status == CloudPostureStatusEnum.DEVIATED
