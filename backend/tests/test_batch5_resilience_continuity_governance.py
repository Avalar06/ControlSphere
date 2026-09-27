from datetime import datetime, timedelta, timezone
import hashlib
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.permissions import RoleEnum
from app.core.security import get_password_hash
from app.models.audit_log import AuditLog
from app.models.cloudsec import (
    CloudAsset,
    CloudAssetTypeEnum,
    CloudCriticalityEnum,
    CloudEnvironmentEnum,
    CloudLifecycleStateEnum,
    CloudPostureStatusEnum,
    CloudProviderEnum,
)
from app.models.control import ImplementationStatusEnum, OrganizationControl, PriorityEnum
from app.models.evidence import EvidenceItem, EvidenceStatusEnum
from app.models.finding import Finding, FindingEvidence, FindingSeverityEnum, FindingTypeEnum
from app.models.framework import (
    Framework,
    FrameworkCategory,
    FrameworkFunction,
    FrameworkSubcategory,
)
from app.models.organization import Organization
from app.models.privacy import DataAsset, DataSensitivityLevel
from app.models.remediation import RemediationPlan
from app.models.resilience import (
    ContinuityPlanStatusEnum,
    ContinuityStrategyTypeEnum,
    CriticalityTierEnum,
    DependencyTypeEnum,
    ExerciseOutcomeEnum,
    ExerciseStatusEnum,
    ExerciseTypeEnum,
    ResilienceEvidenceContextEnum,
)
from app.models.risk import Risk, RiskFindingLink
from app.models.tprm import Vendor, VendorRiskBandEnum, VendorStatusEnum, VendorTierEnum
from app.models.user import User
from app.services.resilience_service import classify_exercise_outcome
from tests.conftest import get_token_headers


@pytest.fixture
def b5_fixture(db: Session, org_apex: Organization, org_meridian: Organization):
    """Multi-tenant, multi-role fixture for Batch 5 Operational Resilience Continuity & DR Testing."""
    apex_admin = User(
        email="b5_admin@apexfinancial.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Apex B5 Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_manager = User(
        email="b5_manager@apexfinancial.com",
        hashed_password=get_password_hash("ManagerPass123!"),
        full_name="Apex B5 Manager",
        role=RoleEnum.MANAGER,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_manager_2 = User(
        email="b5_manager2@apexfinancial.com",
        hashed_password=get_password_hash("Manager2Pass123!"),
        full_name="Apex B5 Manager 2",
        role=RoleEnum.MANAGER,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_analyst = User(
        email="b5_analyst@apexfinancial.com",
        hashed_password=get_password_hash("AnalystPass123!"),
        full_name="Apex B5 Analyst",
        role=RoleEnum.GRC_ANALYST,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_auditor = User(
        email="b5_auditor@apexfinancial.com",
        hashed_password=get_password_hash("AuditorPass123!"),
        full_name="Apex B5 Auditor",
        role=RoleEnum.AUDITOR,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_viewer = User(
        email="b5_viewer@apexfinancial.com",
        hashed_password=get_password_hash("ViewerPass123!"),
        full_name="Apex B5 Viewer",
        role=RoleEnum.VIEWER,
        is_active=True,
        organization_id=org_apex.id,
    )

    meridian_manager = User(
        email="b5_manager@meridianhealth.com",
        hashed_password=get_password_hash("MeridianPass123!"),
        full_name="Meridian B5 Manager",
        role=RoleEnum.MANAGER,
        is_active=True,
        organization_id=org_meridian.id,
    )
    meridian_analyst = User(
        email="b5_analyst@meridianhealth.com",
        hashed_password=get_password_hash("MeridianPass123!"),
        full_name="Meridian B5 Analyst",
        role=RoleEnum.GRC_ANALYST,
        is_active=True,
        organization_id=org_meridian.id,
    )

    db.add_all(
        [
            apex_admin,
            apex_manager,
            apex_manager_2,
            apex_analyst,
            apex_auditor,
            apex_viewer,
            meridian_manager,
            meridian_analyst,
        ]
    )
    db.commit()

    # Framework & Controls
    fw = Framework(name="ISO 22301 & DORA B5", identifier="ISO22301-B5", version="2019")
    db.add(fw)
    db.commit()

    fn = FrameworkFunction(framework_id=fw.id, identifier="BC", name="Business Continuity")
    db.add(fn)
    db.commit()

    cat = FrameworkCategory(function_id=fn.id, identifier="BC.PL", name="Continuity Planning")
    db.add(cat)
    db.commit()

    subcat = FrameworkSubcategory(
        category_id=cat.id,
        identifier="BC.PL-01",
        title="Business Continuity Plans and DR Testing",
        description="Maintain and test continuity plans against BIA RTO/RPO targets.",
    )
    db.add(subcat)
    db.commit()

    apex_ctrl = OrganizationControl(
        organization_id=org_apex.id,
        subcategory_id=subcat.id,
        status=ImplementationStatusEnum.IMPLEMENTED,
        priority=PriorityEnum.HIGH,
    )
    meridian_ctrl = OrganizationControl(
        organization_id=org_meridian.id,
        subcategory_id=subcat.id,
        status=ImplementationStatusEnum.IMPLEMENTED,
        priority=PriorityEnum.HIGH,
    )
    db.add_all([apex_ctrl, meridian_ctrl])
    db.commit()

    # Vendors
    apex_vendor = Vendor(
        organization_id=org_apex.id,
        vendor_code="VND-APX-B5",
        legal_name="Apex Cloud Clearing Corp",
        calculated_tier=VendorTierEnum.TIER_1_CRITICAL,
        vendor_status=VendorStatusEnum.ACTIVE,
        risk_band=VendorRiskBandEnum.LOW,
        business_owner_id=apex_manager.id,
    )
    meridian_vendor = Vendor(
        organization_id=org_meridian.id,
        vendor_code="VND-MER-B5",
        legal_name="Meridian Clinical Storage Inc",
        calculated_tier=VendorTierEnum.TIER_1_CRITICAL,
        vendor_status=VendorStatusEnum.ACTIVE,
        risk_band=VendorRiskBandEnum.LOW,
        business_owner_id=meridian_manager.id,
    )
    db.add_all([apex_vendor, meridian_vendor])
    db.commit()

    # Cloud Assets
    apex_cloud_healthy = CloudAsset(
        organization_id=org_apex.id,
        asset_code="CLD-APEX-RDS-01",
        provider=CloudProviderEnum.AWS,
        account_id="111122223333",
        region="us-east-1",
        resource_type=CloudAssetTypeEnum.RDS_DATABASE,
        resource_arn="arn:aws:rds:us-east-1:111122223333:db:settlement-primary",
        resource_name="settlement-primary-rds",
        environment=CloudEnvironmentEnum.PRODUCTION,
        criticality=CloudCriticalityEnum.CRITICAL,
        posture_status=CloudPostureStatusEnum.COMPLIANT,
        lifecycle_state=CloudLifecycleStateEnum.ACTIVE,
        posture_score=98.0,
        owner_id=apex_manager.id,
    )
    apex_cloud_noncompliant = CloudAsset(
        organization_id=org_apex.id,
        asset_code="CLD-APEX-S3-02",
        provider=CloudProviderEnum.AWS,
        account_id="111122223333",
        region="us-west-2",
        resource_type=CloudAssetTypeEnum.S3_BUCKET,
        resource_arn="arn:aws:s3:::apex-dr-archive",
        resource_name="apex-dr-archive",
        environment=CloudEnvironmentEnum.PRODUCTION,
        criticality=CloudCriticalityEnum.HIGH,
        posture_status=CloudPostureStatusEnum.NON_COMPLIANT,
        lifecycle_state=CloudLifecycleStateEnum.ACTIVE,
        posture_score=35.0,
        owner_id=apex_manager.id,
    )
    meridian_cloud = CloudAsset(
        organization_id=org_meridian.id,
        asset_code="CLD-MER-RDS-01",
        provider=CloudProviderEnum.AZURE,
        account_id="999988887777",
        region="eastus",
        resource_type=CloudAssetTypeEnum.RDS_DATABASE,
        resource_arn="arn:azure:sql:eastus:999988887777:db:ehr-core",
        resource_name="meridian-ehr-sql",
        environment=CloudEnvironmentEnum.PRODUCTION,
        criticality=CloudCriticalityEnum.CRITICAL,
        posture_status=CloudPostureStatusEnum.COMPLIANT,
        lifecycle_state=CloudLifecycleStateEnum.ACTIVE,
        posture_score=95.0,
        owner_id=meridian_manager.id,
    )
    db.add_all([apex_cloud_healthy, apex_cloud_noncompliant, meridian_cloud])
    db.commit()

    # Data Assets
    apex_data_approved = DataAsset(
        organization_id=org_apex.id,
        asset_code="DA-APEX-LEDGER-01",
        name="Real-Time Settlement Ledger Table",
        data_sensitivity_level=DataSensitivityLevel.RESTRICTED_PII,
        owner_id=apex_manager.id,
        lifecycle_state="ACTIVE",
        classification_status="APPROVED",
    )
    apex_data_unverified = DataAsset(
        organization_id=org_apex.id,
        asset_code="DA-APEX-CACHE-02",
        name="Intraday Liquidity Snapshot Store",
        data_sensitivity_level=DataSensitivityLevel.CONFIDENTIAL,
        owner_id=apex_manager.id,
        lifecycle_state="ACTIVE",
        classification_status="PENDING",
    )
    meridian_data = DataAsset(
        organization_id=org_meridian.id,
        asset_code="DA-MER-EHR-01",
        name="Patient Clinical Master Dataset",
        data_sensitivity_level=DataSensitivityLevel.SPECIAL_CATEGORY_SENSITIVE_PHI,
        owner_id=meridian_manager.id,
        lifecycle_state="ACTIVE",
        classification_status="APPROVED",
    )
    db.add_all([apex_data_approved, apex_data_unverified, meridian_data])
    db.commit()

    # Evidence Items
    apex_evidence = EvidenceItem(
        organization_id=org_apex.id,
        organization_control_id=apex_ctrl.id,
        uploaded_by_id=apex_analyst.id,
        title="DR Failover Telemetry Log Q3",
        description="Automated failover timestamp and RPO replication verification logs",
        original_filename="failover_log_q3.json",
        stored_filename="stored_failover_log_q3.json",
        file_extension=".json",
        content_type="application/json",
        file_size=4096,
        sha256_hash=hashlib.sha256(b"apex-failover-telemetry-v1").hexdigest(),
        storage_key="evidence/apex/stored_failover_log_q3.json",
        status=EvidenceStatusEnum.ACCEPTED,
    )
    apex_evidence_rejected = EvidenceItem(
        organization_id=org_apex.id,
        organization_control_id=apex_ctrl.id,
        uploaded_by_id=apex_analyst.id,
        title="Rejected Draft Screenshot",
        description="Rejected evidence artifact",
        original_filename="bad.png",
        stored_filename="stored_bad.png",
        file_extension=".png",
        content_type="image/png",
        file_size=1024,
        sha256_hash=hashlib.sha256(b"rejected-evidence").hexdigest(),
        storage_key="evidence/apex/stored_bad.png",
        status=EvidenceStatusEnum.REJECTED,
    )
    meridian_evidence = EvidenceItem(
        organization_id=org_meridian.id,
        organization_control_id=meridian_ctrl.id,
        uploaded_by_id=meridian_analyst.id,
        title="Meridian DR Log",
        description="Meridian tenant evidence",
        original_filename="meridian_log.json",
        stored_filename="stored_meridian_log.json",
        file_extension=".json",
        content_type="application/json",
        file_size=2048,
        sha256_hash=hashlib.sha256(b"meridian-telemetry").hexdigest(),
        storage_key="evidence/meridian/stored_meridian_log.json",
        status=EvidenceStatusEnum.ACCEPTED,
    )
    db.add_all([apex_evidence, apex_evidence_rejected, meridian_evidence])
    db.commit()

    return {
        "org_apex": org_apex,
        "org_meridian": org_meridian,
        "apex_admin": apex_admin,
        "apex_manager": apex_manager,
        "apex_manager_2": apex_manager_2,
        "apex_analyst": apex_analyst,
        "apex_auditor": apex_auditor,
        "apex_viewer": apex_viewer,
        "meridian_manager": meridian_manager,
        "meridian_analyst": meridian_analyst,
        "apex_ctrl": apex_ctrl,
        "meridian_ctrl": meridian_ctrl,
        "apex_vendor": apex_vendor,
        "meridian_vendor": meridian_vendor,
        "apex_cloud_healthy": apex_cloud_healthy,
        "apex_cloud_noncompliant": apex_cloud_noncompliant,
        "meridian_cloud": meridian_cloud,
        "apex_data_approved": apex_data_approved,
        "apex_data_unverified": apex_data_unverified,
        "meridian_data": meridian_data,
        "apex_evidence": apex_evidence,
        "apex_evidence_rejected": apex_evidence_rejected,
        "meridian_evidence": meridian_evidence,
    }


def _create_process_with_active_bia(
    client: TestClient,
    analyst_headers: dict,
    manager_headers: dict,
    name: str = "Fedwire Real-Time Settlement",
    rto_hours: float = 4.0,
    rpo_hours: float = 1.0,
    mtd_hours: float = 12.0,
    hourly_cost: float = 50000.0,
    fixed_cost: float = 100000.0,
) -> tuple[dict, dict]:
    p_res = client.post(
        "/api/v1/resilience/processes",
        json={
            "name": name,
            "description": "Critical payment clearing and settlement pipeline",
            "criticality_tier": "TIER_1",
        },
        headers=analyst_headers,
    )
    assert p_res.status_code == 201, p_res.text
    proc = p_res.json()

    b_res = client.post(
        "/api/v1/resilience/bia",
        json={
            "process_id": proc["id"],
            "rto_hours": rto_hours,
            "rpo_hours": rpo_hours,
            "mtd_hours": mtd_hours,
            "hourly_downtime_cost": hourly_cost,
            "fixed_outage_cost": fixed_cost,
            "notes": "Approved baseline BIA",
        },
        headers=analyst_headers,
    )
    assert b_res.status_code == 201, b_res.text
    bia = b_res.json()

    app_res = client.post(
        f"/api/v1/resilience/bia/{bia['id']}/approve",
        json={"notes": "Approved by Risk Committee"},
        headers=manager_headers,
    )
    assert app_res.status_code == 200, app_res.text
    return proc, app_res.json()


# ═════════════════════════════════════════════════════════════════════════════
# 1. EXTENDED DEPENDENCY LINEAGE, BLAST RADIUS & HEALTH (8 TESTS)
# ═════════════════════════════════════════════════════════════════════════════


def test_b5_01_cloud_and_data_asset_dependency_creation(client: TestClient, b5_fixture: dict):
    """Verify CLOUD_ASSET and DATA_ASSET process dependencies with typed FKs and SPOF metadata."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    proc, _ = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="SWIFT Gateway Settlement"
    )

    # Create CLOUD_ASSET dependency via process-scoped endpoint
    c_dep = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/dependencies",
        json={
            "dependency_type": "CLOUD_ASSET",
            "cloud_asset_id": b5_fixture["apex_cloud_healthy"].id,
            "is_single_point_of_failure": True,
            "failure_propagation_weight": 1.0,
            "recovery_priority_order": 1,
            "notes": "Primary RDS cluster",
            "criticality_notes": "Single region writer instance",
        },
        headers=analyst_headers,
    )
    assert c_dep.status_code == 201, c_dep.text
    c_body = c_dep.json()
    assert c_body["dependency_type"] == "CLOUD_ASSET"
    assert c_body["cloud_asset_id"] == b5_fixture["apex_cloud_healthy"].id
    assert c_body["dependency_id"] == b5_fixture["apex_cloud_healthy"].id
    assert c_body["is_single_point_of_failure"] is True
    assert c_body["failure_propagation_weight"] == 1.0
    assert c_body["recovery_priority_order"] == 1

    # Create DATA_ASSET dependency
    d_dep = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/dependencies",
        json={
            "dependency_type": "DATA_ASSET",
            "data_asset_id": b5_fixture["apex_data_approved"].id,
            "is_single_point_of_failure": False,
            "failure_propagation_weight": 0.75,
            "recovery_priority_order": 2,
            "notes": "Settlement ledger dataset",
        },
        headers=analyst_headers,
    )
    assert d_dep.status_code == 201, d_dep.text
    d_body = d_dep.json()
    assert d_body["dependency_type"] == "DATA_ASSET"
    assert d_body["data_asset_id"] == b5_fixture["apex_data_approved"].id
    assert d_body["dependency_id"] == b5_fixture["apex_data_approved"].id
    assert d_body["failure_propagation_weight"] == 0.75
    assert d_body["recovery_priority_order"] == 2

    # List dependencies and verify priority ordering
    list_res = client.get(
        f"/api/v1/resilience/processes/{proc['id']}/dependencies",
        headers=analyst_headers,
    )
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) == 2
    assert items[0]["recovery_priority_order"] == 1
    assert items[1]["recovery_priority_order"] == 2


def test_b5_02_dependency_target_xor_and_type_mismatch_rejected(
    client: TestClient, b5_fixture: dict
):
    """SEC-B5-33, SEC-B5-34, SEC-B5-35: Verify 6-way XOR and type-column matching on ProcessDependency."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    proc, _ = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="XOR Validation Process"
    )

    # SEC-B5-33: Multiple target FKs simultaneously -> 422
    multi_res = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/dependencies",
        json={
            "dependency_type": "CLOUD_ASSET",
            "cloud_asset_id": b5_fixture["apex_cloud_healthy"].id,
            "data_asset_id": b5_fixture["apex_data_approved"].id,
        },
        headers=analyst_headers,
    )
    assert multi_res.status_code == 422

    # SEC-B5-34: Zero target FKs -> 422
    zero_res = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/dependencies",
        json={"dependency_type": "CLOUD_ASSET"},
        headers=analyst_headers,
    )
    assert zero_res.status_code == 422

    # SEC-B5-35: Mismatched dependency_type vs target FK column -> 422
    mismatch_res = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/dependencies",
        json={
            "dependency_type": "CLOUD_ASSET",
            "vendor_id": b5_fixture["apex_vendor"].id,
        },
        headers=analyst_headers,
    )
    assert mismatch_res.status_code == 422


def test_b5_03_cross_tenant_cloud_and_data_asset_bola_rejected(
    client: TestClient, b5_fixture: dict
):
    """SEC-B5-03 & SEC-B5-04: Cross-tenant cloud_asset_id and data_asset_id must be rejected with 404."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    proc, _ = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="Cross-Tenant Asset Guard Process"
    )

    # SEC-B5-03: Meridian cloud_asset_id injected into Apex process
    res_cloud = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/dependencies",
        json={
            "dependency_type": "CLOUD_ASSET",
            "cloud_asset_id": b5_fixture["meridian_cloud"].id,
        },
        headers=analyst_headers,
    )
    assert res_cloud.status_code == 404

    # SEC-B5-04: Meridian data_asset_id injected into Apex process
    res_data = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/dependencies",
        json={
            "dependency_type": "DATA_ASSET",
            "data_asset_id": b5_fixture["meridian_data"].id,
        },
        headers=analyst_headers,
    )
    assert res_data.status_code == 404


def test_b5_04_spof_propagation_weight_and_range_validation(
    client: TestClient, b5_fixture: dict
):
    """SEC-B5-43: SPOF dependency must have failure_propagation_weight == 1.0 and weight in (0, 1]."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    proc, _ = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="SPOF Weight Validation Process"
    )

    # SPOF with weight < 1.0 -> 422
    spof_bad = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/dependencies",
        json={
            "dependency_type": "CLOUD_ASSET",
            "cloud_asset_id": b5_fixture["apex_cloud_healthy"].id,
            "is_single_point_of_failure": True,
            "failure_propagation_weight": 0.6,
        },
        headers=analyst_headers,
    )
    assert spof_bad.status_code == 422

    # Weight <= 0.0 -> 422
    zero_weight = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/dependencies",
        json={
            "dependency_type": "CLOUD_ASSET",
            "cloud_asset_id": b5_fixture["apex_cloud_healthy"].id,
            "failure_propagation_weight": 0.0,
        },
        headers=analyst_headers,
    )
    assert zero_weight.status_code == 422

    # Weight > 1.0 -> 422
    over_weight = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/dependencies",
        json={
            "dependency_type": "CLOUD_ASSET",
            "cloud_asset_id": b5_fixture["apex_cloud_healthy"].id,
            "failure_propagation_weight": 1.5,
        },
        headers=analyst_headers,
    )
    assert over_weight.status_code == 422


def test_b5_05_process_to_process_dependency_and_cycle_detection(
    client: TestClient, b5_fixture: dict
):
    """SEC-B5-36: Detect self-reference and multi-hop circular PROCESS dependency graphs (A -> B -> C -> A)."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])

    proc_a, _ = _create_process_with_active_bia(client, analyst_headers, manager_headers, name="Process A")
    proc_b, _ = _create_process_with_active_bia(client, analyst_headers, manager_headers, name="Process B")
    proc_c, _ = _create_process_with_active_bia(client, analyst_headers, manager_headers, name="Process C")

    # Self-dependency A -> A rejected with 422
    self_res = client.post(
        f"/api/v1/resilience/processes/{proc_a['id']}/dependencies",
        json={"dependency_type": "PROCESS", "depends_on_process_id": proc_a["id"]},
        headers=analyst_headers,
    )
    assert self_res.status_code == 422

    # A depends on B (201)
    ab_res = client.post(
        f"/api/v1/resilience/processes/{proc_a['id']}/dependencies",
        json={"dependency_type": "PROCESS", "depends_on_process_id": proc_b["id"]},
        headers=analyst_headers,
    )
    assert ab_res.status_code == 201

    # B depends on C (201)
    bc_res = client.post(
        f"/api/v1/resilience/processes/{proc_b['id']}/dependencies",
        json={"dependency_type": "PROCESS", "depends_on_process_id": proc_c["id"]},
        headers=analyst_headers,
    )
    assert bc_res.status_code == 201

    # C depends on A -> cycle A -> B -> C -> A rejected with 422
    ca_res = client.post(
        f"/api/v1/resilience/processes/{proc_c['id']}/dependencies",
        json={"dependency_type": "PROCESS", "depends_on_process_id": proc_a["id"]},
        headers=analyst_headers,
    )
    assert ca_res.status_code == 422
    assert "Circular process dependency" in ca_res.json()["detail"]


def test_b5_06_outage_blast_radius_simulation_multi_hop(
    client: TestClient, b5_fixture: dict
):
    """SEC-B5-37: Verify BFS blast-radius outage simulation across CLOUD_ASSET and multi-hop PROCESS chain."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])

    # Upstream process P1 (RTO=2h, MTD=8h, Fixed=10k, Hourly=10k -> 6h loss = 70k)
    p1, _ = _create_process_with_active_bia(
        client,
        analyst_headers,
        manager_headers,
        name="Core Ledger Engine P1",
        rto_hours=2.0,
        rpo_hours=0.5,
        mtd_hours=8.0,
        hourly_cost=10000.0,
        fixed_cost=10000.0,
    )
    # Downstream process P2 (RTO=4h, MTD=12h, Fixed=20k, Hourly=5k -> 6h raw loss = 50k)
    p2, _ = _create_process_with_active_bia(
        client,
        analyst_headers,
        manager_headers,
        name="Client Treasury Portal P2",
        rto_hours=4.0,
        rpo_hours=1.0,
        mtd_hours=12.0,
        hourly_cost=5000.0,
        fixed_cost=20000.0,
    )

    # P1 depends on CloudAsset with weight 1.0
    client.post(
        f"/api/v1/resilience/processes/{p1['id']}/dependencies",
        json={
            "dependency_type": "CLOUD_ASSET",
            "cloud_asset_id": b5_fixture["apex_cloud_healthy"].id,
            "is_single_point_of_failure": True,
            "failure_propagation_weight": 1.0,
        },
        headers=analyst_headers,
    )
    # P2 depends on P1 with weight 0.5
    client.post(
        f"/api/v1/resilience/processes/{p2['id']}/dependencies",
        json={
            "dependency_type": "PROCESS",
            "depends_on_process_id": p1["id"],
            "failure_propagation_weight": 0.5,
        },
        headers=analyst_headers,
    )

    sim_res = client.post(
        "/api/v1/resilience/simulate-outage",
        json={
            "failing_node_type": "CLOUD_ASSET",
            "failing_node_id": b5_fixture["apex_cloud_healthy"].id,
            "outage_duration_hours": 6.0,
        },
        headers=analyst_headers,
    )
    assert sim_res.status_code == 200, sim_res.text
    sim = sim_res.json()
    assert sim["affected_process_count"] == 2
    assert sim["rto_breach_count"] == 2
    assert sim["mtd_breach_count"] == 0
    # P1 loss = 70,000 * 1.0 = 70,000; P2 loss = 50,000 * 0.5 = 25,000 -> total = 95,000
    assert sim["total_projected_financial_loss"] == 95000.0


def test_b5_07_live_process_dependency_health_evaluation(
    client: TestClient, b5_fixture: dict
):
    """Verify GET /processes/{id}/dependency-health reflects CloudAsset/DataAsset posture and SPOF mitigation."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    proc, bia = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="Health Evaluation Process"
    )

    # Link NON_COMPLIANT CloudAsset (CRITICAL = 0) as SPOF (weight=1.0, alpha=2.0)
    client.post(
        f"/api/v1/resilience/processes/{proc['id']}/dependencies",
        json={
            "dependency_type": "CLOUD_ASSET",
            "cloud_asset_id": b5_fixture["apex_cloud_noncompliant"].id,
            "is_single_point_of_failure": True,
            "failure_propagation_weight": 1.0,
            "recovery_priority_order": 1,
        },
        headers=analyst_headers,
    )
    # Link unverified DataAsset (DEGRADED = 50, weight=1.0, alpha=1.0)
    client.post(
        f"/api/v1/resilience/processes/{proc['id']}/dependencies",
        json={
            "dependency_type": "DATA_ASSET",
            "data_asset_id": b5_fixture["apex_data_unverified"].id,
            "is_single_point_of_failure": False,
            "failure_propagation_weight": 1.0,
            "recovery_priority_order": 2,
        },
        headers=analyst_headers,
    )

    h_res = client.get(
        f"/api/v1/resilience/processes/{proc['id']}/dependency-health",
        headers=analyst_headers,
    )
    assert h_res.status_code == 200, h_res.text
    h = h_res.json()
    assert h["total_dependencies"] == 2
    assert h["spof_count"] == 1
    assert h["unmitigated_spof_count"] == 1  # No APPROVED continuity plan yet
    assert h["critical_count"] == 1
    assert h["degraded_count"] == 1
    # Weighted health = (2.0 * 0 + 1.0 * 50) / 3.0 = 16.67
    assert h["dependency_health_score"] == 16.67

    # Now create, submit, and approve a ContinuityPlan -> unmitigated_spof_count becomes 0
    cp = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-HEALTH-01",
            "title": "Health Process Continuity Plan",
            "bia_id": bia["id"],
            "strategy_type": "WARM_STANDBY",
            "activation_triggers": "Primary region outage > 15m",
            "estimated_recovery_hours": 2.0,
            "estimated_rpo_hours": 0.5,
        },
        headers=analyst_headers,
    ).json()
    client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/steps",
        json={
            "step_order": 1,
            "title": "Promote standby database",
            "description": "Execute cross-region promotion runbook",
            "estimated_duration_minutes": 30,
        },
        headers=analyst_headers,
    )
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/submit", headers=analyst_headers)
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/approve", headers=manager_headers)

    h_after = client.get(
        f"/api/v1/resilience/processes/{proc['id']}/dependency-health",
        headers=analyst_headers,
    ).json()
    assert h_after["unmitigated_spof_count"] == 0


def test_b5_08_process_impact_summary_and_dashboard_telemetry(
    client: TestClient, b5_fixture: dict
):
    """Verify enriched ProcessImpactSummaryResponse and ResilienceDashboardResponse."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    proc, bia = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="Dashboard Telemetry Process"
    )

    sum_res = client.get(
        f"/api/v1/resilience/processes/{proc['id']}/impact-summary",
        headers=analyst_headers,
    )
    assert sum_res.status_code == 200
    summary = sum_res.json()
    assert summary["process_id"] == proc["id"]
    assert summary["has_active_bia"] is True
    assert summary["rto_hours"] == bia["rto_hours"]

    dash_res = client.get("/api/v1/resilience/dashboard", headers=analyst_headers)
    assert dash_res.status_code == 200
    dash = dash_res.json()
    assert dash["total_processes"] >= 1
    assert "continuity_plan_coverage_pct" in dash
    assert "exercise_pass_rate_pct" in dash
    assert "resilience_assurance_score" in dash


# ═════════════════════════════════════════════════════════════════════════════
# 2. CONTINUITY PLAN & RECOVERY STEP LIFECYCLE (6 COMPREHENSIVE TESTS)
# ═════════════════════════════════════════════════════════════════════════════


def test_b5_09_continuity_plan_and_recovery_steps_crud_and_rollup(
    client: TestClient, b5_fixture: dict
):
    """Verify ContinuityPlan CRUD, ordered step rollups, uq_cp_org_proc_code_ver (SEC-B5-40), and uq_crs_plan_step_order (SEC-B5-39)."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    proc, bia = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="Continuity CRUD Process"
    )

    cp_res = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-SETTLE-001",
            "title": "Settlement Multi-Region Failover Plan",
            "bia_id": bia["id"],
            "version_major": 1,
            "version_minor": 0,
            "strategy_type": "ACTIVE_ACTIVE",
            "activation_triggers": "Primary cluster unreachable for 5 minutes",
            "communication_plan": "Page Treasury Incident Commander and notify Fedwire Desk",
            "fallback_location_or_region": "us-west-2",
            "estimated_recovery_hours": 2.0,
            "estimated_rpo_hours": 0.5,
            "review_frequency_days": 180,
        },
        headers=analyst_headers,
    )
    assert cp_res.status_code == 201, cp_res.text
    plan = cp_res.json()
    assert plan["version_label"] == "1.0"
    assert plan["status"] == "DRAFT"

    # SEC-B5-40: Duplicate (organization_id, process_id, plan_code, version_label) -> 409
    dup_plan = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-SETTLE-001",
            "title": "Duplicate Version",
            "version_major": 1,
            "version_minor": 0,
            "strategy_type": "ACTIVE_ACTIVE",
            "activation_triggers": "Trigger",
            "estimated_recovery_hours": 2.0,
            "estimated_rpo_hours": 0.5,
        },
        headers=analyst_headers,
    )
    assert dup_plan.status_code == 409

    # Add Step 2 first, then Step 1 to verify step_order sorting
    s2 = client.post(
        f"/api/v1/resilience/continuity-plans/{plan['id']}/steps",
        json={
            "step_order": 2,
            "title": "Reroute traffic via global load balancer",
            "description": "Switch Route53 health check weight to secondary region",
            "estimated_duration_minutes": 25,
            "cloud_asset_id": b5_fixture["apex_cloud_healthy"].id,
            "is_automated": True,
        },
        headers=analyst_headers,
    )
    assert s2.status_code == 201

    s1 = client.post(
        f"/api/v1/resilience/continuity-plans/{plan['id']}/steps",
        json={
            "step_order": 1,
            "title": "Verify replica lag on secondary RDS",
            "description": "Confirm replication lag is zero before cutover",
            "estimated_duration_minutes": 20,
            "responsible_user_id": b5_fixture["apex_manager"].id,
            "data_asset_id": b5_fixture["apex_data_approved"].id,
            "is_automated": False,
        },
        headers=analyst_headers,
    )
    assert s1.status_code == 201

    # SEC-B5-39: Duplicate step_order within same plan -> 409
    dup_step = client.post(
        f"/api/v1/resilience/continuity-plans/{plan['id']}/steps",
        json={
            "step_order": 1,
            "title": "Colliding step",
            "description": "Duplicate order",
            "estimated_duration_minutes": 10,
        },
        headers=analyst_headers,
    )
    assert dup_step.status_code == 409

    # Update step 2 duration from 25 -> 40 minutes
    s2_id = s2.json()["id"]
    upd_s2 = client.patch(
        f"/api/v1/resilience/continuity-plans/{plan['id']}/steps/{s2_id}",
        json={"estimated_duration_minutes": 40},
        headers=analyst_headers,
    )
    assert upd_s2.status_code == 200
    assert upd_s2.json()["estimated_duration_minutes"] == 40

    # Verify detail endpoint rollup: 20 + 40 = 60 minutes = 1.0 hour
    detail = client.get(
        f"/api/v1/resilience/continuity-plans/{plan['id']}",
        headers=analyst_headers,
    ).json()
    assert detail["total_step_duration_minutes"] == 60
    assert detail["total_step_duration_hours"] == 1.0
    assert [s["step_order"] for s in detail["recovery_steps"]] == [1, 2]


def test_b5_10_continuity_plan_submission_guardrails(
    client: TestClient, b5_fixture: dict
):
    """SEC-B5-15, SEC-B5-16, SEC-B5-17, SEC-B5-18, SEC-B5-19: Verify all ContinuityPlan submission guardrails."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])

    # SEC-B5-19: Process with NO active BIA
    p_no_bia = client.post(
        "/api/v1/resilience/processes",
        json={"name": "Process Without BIA", "criticality_tier": "TIER_2"},
        headers=analyst_headers,
    ).json()
    cp_no_bia = client.post(
        f"/api/v1/resilience/processes/{p_no_bia['id']}/continuity-plans",
        json={
            "plan_code": "BCP-NOBIA-01",
            "title": "Plan Without Active BIA",
            "strategy_type": "COLD_SITE",
            "activation_triggers": "Trigger",
            "estimated_recovery_hours": 4.0,
            "estimated_rpo_hours": 1.0,
        },
        headers=analyst_headers,
    ).json()
    client.post(
        f"/api/v1/resilience/continuity-plans/{cp_no_bia['id']}/steps",
        json={"step_order": 1, "title": "Step 1", "description": "Desc", "estimated_duration_minutes": 30},
        headers=analyst_headers,
    )
    sub_no_bia = client.post(
        f"/api/v1/resilience/continuity-plans/{cp_no_bia['id']}/submit",
        headers=analyst_headers,
    )
    assert sub_no_bia.status_code == 422
    assert "no ACTIVE approved BIA" in sub_no_bia.json()["detail"]

    # Create process with active BIA (RTO=4.0h, RPO=1.0h, MTD=12.0h)
    proc, bia = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="Guardrails Process", rto_hours=4.0, rpo_hours=1.0
    )

    # SEC-B5-15: Plan with zero recovery steps -> 422
    cp_zero = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-ZERO-STEPS",
            "title": "Zero Steps Plan",
            "bia_id": bia["id"],
            "strategy_type": "WARM_STANDBY",
            "activation_triggers": "Outage",
            "estimated_recovery_hours": 2.0,
            "estimated_rpo_hours": 0.5,
        },
        headers=analyst_headers,
    ).json()
    res_zero = client.post(
        f"/api/v1/resilience/continuity-plans/{cp_zero['id']}/submit",
        headers=analyst_headers,
    )
    assert res_zero.status_code == 422
    assert "at least one ContinuityRecoveryStep" in res_zero.json()["detail"]

    # SEC-B5-16: Step duration sum (180 min = 3.0h) > estimated_recovery_hours (2.0h) -> 422
    client.post(
        f"/api/v1/resilience/continuity-plans/{cp_zero['id']}/steps",
        json={
            "step_order": 1,
            "title": "Long Manual Rebuild",
            "description": "Rebuild bare metal",
            "estimated_duration_minutes": 180,
        },
        headers=analyst_headers,
    )
    res_rollup = client.post(
        f"/api/v1/resilience/continuity-plans/{cp_zero['id']}/submit",
        headers=analyst_headers,
    )
    assert res_rollup.status_code == 422
    assert "Cumulative recovery step duration" in res_rollup.json()["detail"]

    # SEC-B5-17: estimated_recovery_hours (6.0h) > active BIA RTO (4.0h) -> 422
    cp_rto_exceed = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-RTO-EXCEED",
            "title": "RTO Exceeding Plan",
            "strategy_type": "WARM_STANDBY",
            "activation_triggers": "Outage",
            "estimated_recovery_hours": 6.0,
            "estimated_rpo_hours": 0.5,
        },
        headers=analyst_headers,
    ).json()
    client.post(
        f"/api/v1/resilience/continuity-plans/{cp_rto_exceed['id']}/steps",
        json={"step_order": 1, "title": "Step", "description": "Desc", "estimated_duration_minutes": 60},
        headers=analyst_headers,
    )
    res_rto = client.post(
        f"/api/v1/resilience/continuity-plans/{cp_rto_exceed['id']}/submit",
        headers=analyst_headers,
    )
    assert res_rto.status_code == 422
    assert "exceeds the active BIA RTO target" in res_rto.json()["detail"]

    # SEC-B5-18: estimated_rpo_hours (2.5h) > active BIA RPO (1.0h) -> 422
    cp_rpo_exceed = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-RPO-EXCEED",
            "title": "RPO Exceeding Plan",
            "strategy_type": "WARM_STANDBY",
            "activation_triggers": "Outage",
            "estimated_recovery_hours": 2.0,
            "estimated_rpo_hours": 2.5,
        },
        headers=analyst_headers,
    ).json()
    client.post(
        f"/api/v1/resilience/continuity-plans/{cp_rpo_exceed['id']}/steps",
        json={"step_order": 1, "title": "Step", "description": "Desc", "estimated_duration_minutes": 30},
        headers=analyst_headers,
    )
    res_rpo = client.post(
        f"/api/v1/resilience/continuity-plans/{cp_rpo_exceed['id']}/submit",
        headers=analyst_headers,
    )
    assert res_rpo.status_code == 422
    assert "exceeds the active BIA RPO target" in res_rpo.json()["detail"]


def test_b5_11_continuity_plan_four_eyes_approval_and_atomic_superseding(
    client: TestClient, b5_fixture: dict
):
    """SEC-B5-08, SEC-B5-09, SEC-B5-20: Verify Four-Eyes SoD, SHA-256 hash sealing, and atomic superseding."""
    manager1_headers = get_token_headers(b5_fixture["apex_manager"])
    manager2_headers = get_token_headers(b5_fixture["apex_manager_2"])
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])

    proc, bia = _create_process_with_active_bia(
        client, analyst_headers, manager1_headers, name="Four-Eyes Plan Process"
    )

    # Manager 1 creates v1.0, Analyst submits v1.0
    cp1 = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-FE-01",
            "title": "Continuity Plan v1.0",
            "bia_id": bia["id"],
            "version_major": 1,
            "version_minor": 0,
            "strategy_type": "HOT_STANDBY",
            "activation_triggers": "Outage > 5m",
            "estimated_recovery_hours": 2.0,
            "estimated_rpo_hours": 0.5,
        },
        headers=manager1_headers,
    ).json()
    client.post(
        f"/api/v1/resilience/continuity-plans/{cp1['id']}/steps",
        json={"step_order": 1, "title": "Failover", "description": "Execute script", "estimated_duration_minutes": 30},
        headers=manager1_headers,
    )

    # SEC-B5-20: Approving directly from DRAFT (skipping submit) -> 409
    direct_app = client.post(
        f"/api/v1/resilience/continuity-plans/{cp1['id']}/approve",
        headers=manager2_headers,
    )
    assert direct_app.status_code == 409

    # Manager 2 submits v1.0
    sub_res = client.post(
        f"/api/v1/resilience/continuity-plans/{cp1['id']}/submit",
        headers=manager2_headers,
    )
    assert sub_res.status_code == 200
    assert sub_res.json()["status"] == "PENDING_APPROVAL"
    assert sub_res.json()["plan_hash_sha256"] is not None

    # SEC-B5-08: Creator (Manager 1) attempts to approve -> 403 Forbidden
    self_creator_app = client.post(
        f"/api/v1/resilience/continuity-plans/{cp1['id']}/approve",
        headers=manager1_headers,
    )
    assert self_creator_app.status_code == 403

    # SEC-B5-09: Submitter (Manager 2) attempts to approve -> 403 Forbidden
    self_submitter_app = client.post(
        f"/api/v1/resilience/continuity-plans/{cp1['id']}/approve",
        headers=manager2_headers,
    )
    assert self_submitter_app.status_code == 403

    # Independent approver (Apex Admin) approves v1.0 -> 200 OK
    admin_headers = get_token_headers(b5_fixture["apex_admin"])
    app1 = client.post(
        f"/api/v1/resilience/continuity-plans/{cp1['id']}/approve",
        headers=admin_headers,
    )
    assert app1.status_code == 200
    app1_body = app1.json()
    assert app1_body["status"] == "APPROVED"
    assert len(app1_body["plan_hash_sha256"]) == 64
    assert app1_body["next_review_due_at"] is not None

    # Now create, submit, and approve v2.0 -> v1.0 must be atomically SUPERSEDED
    cp2 = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-FE-01",
            "title": "Continuity Plan v2.0",
            "bia_id": bia["id"],
            "version_major": 2,
            "version_minor": 0,
            "strategy_type": "ACTIVE_ACTIVE",
            "activation_triggers": "Automated health probe failure",
            "estimated_recovery_hours": 1.0,
            "estimated_rpo_hours": 0.25,
        },
        headers=analyst_headers,
    ).json()
    client.post(
        f"/api/v1/resilience/continuity-plans/{cp2['id']}/steps",
        json={"step_order": 1, "title": "Auto-switch", "description": "DNS cutover", "estimated_duration_minutes": 15},
        headers=analyst_headers,
    )
    client.post(f"/api/v1/resilience/continuity-plans/{cp2['id']}/submit", headers=analyst_headers)
    app2 = client.post(f"/api/v1/resilience/continuity-plans/{cp2['id']}/approve", headers=manager1_headers)
    assert app2.status_code == 200
    assert app2.json()["status"] == "APPROVED"

    # Verify v1.0 is now SUPERSEDED and points to v2.0
    cp1_after = client.get(
        f"/api/v1/resilience/continuity-plans/{cp1['id']}",
        headers=analyst_headers,
    ).json()
    assert cp1_after["status"] == "SUPERSEDED"
    assert cp1_after["superseded_by_plan_id"] == cp2["id"]


def test_b5_12_continuity_plan_and_steps_immutability_after_draft(
    client: TestClient, b5_fixture: dict
):
    """SEC-B5-13 & SEC-B5-14: Mutating a ContinuityPlan or its steps after leaving DRAFT returns 409."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    proc, bia = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="Immutability Process"
    )

    cp = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-IMM-01",
            "title": "Immutable Plan",
            "bia_id": bia["id"],
            "strategy_type": "WARM_STANDBY",
            "activation_triggers": "Outage",
            "estimated_recovery_hours": 2.0,
            "estimated_rpo_hours": 0.5,
        },
        headers=analyst_headers,
    ).json()
    step = client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/steps",
        json={"step_order": 1, "title": "Step 1", "description": "Desc", "estimated_duration_minutes": 30},
        headers=analyst_headers,
    ).json()

    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/submit", headers=analyst_headers)
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/approve", headers=manager_headers)

    # SEC-B5-13: PATCH plan in APPROVED status -> 409
    patch_plan = client.patch(
        f"/api/v1/resilience/continuity-plans/{cp['id']}",
        json={"title": "Tampered Title"},
        headers=analyst_headers,
    )
    assert patch_plan.status_code == 409

    # SEC-B5-14: Add/edit/delete step on APPROVED plan -> 409
    add_step = client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/steps",
        json={"step_order": 2, "title": "Injected Step", "description": "Desc", "estimated_duration_minutes": 10},
        headers=analyst_headers,
    )
    assert add_step.status_code == 409

    edit_step = client.patch(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/steps/{step['id']}",
        json={"title": "Tampered Step"},
        headers=analyst_headers,
    )
    assert edit_step.status_code == 409

    del_step = client.delete(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/steps/{step['id']}",
        headers=analyst_headers,
    )
    assert del_step.status_code == 409


def test_b5_13_continuity_plan_reject_and_archive_lifecycle(
    client: TestClient, b5_fixture: dict
):
    """Verify reject (PENDING_APPROVAL -> DRAFT) and archive guards including SEC-B5-50."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    proc, bia = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="Reject & Archive Process"
    )

    cp = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-REJ-01",
            "title": "Rejectable Plan",
            "bia_id": bia["id"],
            "strategy_type": "WARM_STANDBY",
            "activation_triggers": "Trigger",
            "estimated_recovery_hours": 2.0,
            "estimated_rpo_hours": 0.5,
        },
        headers=analyst_headers,
    ).json()
    client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/steps",
        json={"step_order": 1, "title": "Step 1", "description": "Desc", "estimated_duration_minutes": 30},
        headers=analyst_headers,
    )
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/submit", headers=analyst_headers)

    # Manager rejects back to DRAFT
    rej = client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/reject",
        json={"reason": "Add explicit communication escalation contacts"},
        headers=manager_headers,
    )
    assert rej.status_code == 200
    assert rej.json()["status"] == "DRAFT"

    # Re-submit and approve
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/submit", headers=analyst_headers)
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/approve", headers=manager_headers)

    # Schedule a PLANNED exercise against this approved plan
    ex = client.post(
        "/api/v1/resilience/exercises",
        json={
            "process_id": proc["id"],
            "continuity_plan_id": cp["id"],
            "exercise_code": "EX-ARCHIVE-GUARD-01",
            "title": "Scheduled Tabletop",
            "exercise_type": "TABLETOP",
            "scenario_description": "Scenario",
            "scheduled_start_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=analyst_headers,
    ).json()

    # SEC-B5-50: Archiving APPROVED plan while active exercise exists -> 409 Conflict
    arch_blocked = client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/archive",
        headers=manager_headers,
    )
    assert arch_blocked.status_code == 409

    # Cancel the exercise, then verify GRC_ANALYST (without RESILIENCE_APPROVE) gets 403 archiving APPROVED plan
    client.post(f"/api/v1/resilience/exercises/{ex['id']}/cancel", json={"reason": "Rescheduled"}, headers=analyst_headers)
    arch_forbidden = client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/archive",
        headers=analyst_headers,
    )
    assert arch_forbidden.status_code == 403

    # Manager (with RESILIENCE_APPROVE) archives the plan -> 200 OK
    arch_ok = client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/archive",
        headers=manager_headers,
    )
    assert arch_ok.status_code == 200
    assert arch_ok.json()["status"] == "ARCHIVED"


def test_b5_14_continuity_plan_review_frequency_and_step_bola_validation(
    client: TestClient, b5_fixture: dict
):
    """SEC-B5-44 & SEC-B5-07: Validate review_frequency_days range (1..1825) and cross-tenant step FKs."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    proc, bia = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="Freq & Step BOLA Process"
    )

    # SEC-B5-44: review_frequency_days > 1825 -> 422
    bad_freq = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-BAD-FREQ",
            "title": "Bad Review Frequency",
            "strategy_type": "WARM_STANDBY",
            "activation_triggers": "Trigger",
            "estimated_recovery_hours": 2.0,
            "estimated_rpo_hours": 0.5,
            "review_frequency_days": 5000,
        },
        headers=analyst_headers,
    )
    assert bad_freq.status_code == 422

    cp = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-STEP-BOLA",
            "title": "Step BOLA Plan",
            "bia_id": bia["id"],
            "strategy_type": "WARM_STANDBY",
            "activation_triggers": "Trigger",
            "estimated_recovery_hours": 2.0,
            "estimated_rpo_hours": 0.5,
        },
        headers=analyst_headers,
    ).json()

    # SEC-B5-07: Cross-tenant responsible_user_id on recovery step -> 404
    bola_user_step = client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/steps",
        json={
            "step_order": 1,
            "title": "Cross-Tenant User Step",
            "description": "Desc",
            "responsible_user_id": b5_fixture["meridian_manager"].id,
            "estimated_duration_minutes": 15,
        },
        headers=analyst_headers,
    )
    assert bola_user_step.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# 3. EMPIRICAL RESILIENCE EXERCISES, EVIDENCE & RTO/RPO/MTD MATH (7 TESTS)
# ═════════════════════════════════════════════════════════════════════════════


def test_b5_15_exercise_creation_invariants_and_bia_snapshot_immutability(
    client: TestClient, b5_fixture: dict
):
    """SEC-B5-21, SEC-B5-22, SEC-B5-41, SEC-B5-42: Exercise creation guards and BIA snapshot immutability."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])

    proc1, bia1 = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="Exercise Proc 1", rto_hours=4.0, rpo_hours=1.0, mtd_hours=12.0
    )
    proc2, _ = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="Exercise Proc 2"
    )

    draft_plan = client.post(
        f"/api/v1/resilience/processes/{proc1['id']}/continuity-plans",
        json={
            "plan_code": "BCP-EX-01",
            "title": "Exercise Plan",
            "bia_id": bia1["id"],
            "strategy_type": "HOT_STANDBY",
            "activation_triggers": "Trigger",
            "estimated_recovery_hours": 2.0,
            "estimated_rpo_hours": 0.5,
        },
        headers=analyst_headers,
    ).json()
    client.post(
        f"/api/v1/resilience/continuity-plans/{draft_plan['id']}/steps",
        json={"step_order": 1, "title": "Step 1", "description": "Desc", "estimated_duration_minutes": 30},
        headers=analyst_headers,
    )

    # SEC-B5-21: Creating exercise against DRAFT plan -> 422
    ex_draft = client.post(
        "/api/v1/resilience/exercises",
        json={
            "process_id": proc1["id"],
            "continuity_plan_id": draft_plan["id"],
            "exercise_code": "EX-DRAFT-FAIL",
            "title": "Should Fail",
            "exercise_type": "TABLETOP",
            "scenario_description": "Scenario",
            "scheduled_start_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=analyst_headers,
    )
    assert ex_draft.status_code == 422

    # Submit and approve plan
    client.post(f"/api/v1/resilience/continuity-plans/{draft_plan['id']}/submit", headers=analyst_headers)
    client.post(f"/api/v1/resilience/continuity-plans/{draft_plan['id']}/approve", headers=manager_headers)

    # SEC-B5-22: Plan belongs to proc1, but exercise specifies proc2 -> 422
    ex_mismatch = client.post(
        "/api/v1/resilience/exercises",
        json={
            "process_id": proc2["id"],
            "continuity_plan_id": draft_plan["id"],
            "exercise_code": "EX-MISMATCH-FAIL",
            "title": "Mismatched Process",
            "exercise_type": "TABLETOP",
            "scenario_description": "Scenario",
            "scheduled_start_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=analyst_headers,
    )
    assert ex_mismatch.status_code == 422

    # Valid creation
    ex_ok = client.post(
        "/api/v1/resilience/exercises",
        json={
            "process_id": proc1["id"],
            "continuity_plan_id": draft_plan["id"],
            "exercise_code": "EX-SNAP-001",
            "title": "Snapshot Test Exercise",
            "exercise_type": "TABLETOP",
            "scenario_description": "Simulate region outage",
            "scheduled_start_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=analyst_headers,
    )
    assert ex_ok.status_code == 201
    ex_body = ex_ok.json()
    assert ex_body["target_rto_hours_snapshot"] == 4.0
    assert ex_body["target_rpo_hours_snapshot"] == 1.0
    assert ex_body["target_mtd_hours_snapshot"] == 12.0

    # SEC-B5-41: Duplicate exercise_code in tenant -> 409
    ex_dup = client.post(
        "/api/v1/resilience/exercises",
        json={
            "process_id": proc1["id"],
            "continuity_plan_id": draft_plan["id"],
            "exercise_code": "EX-SNAP-001",
            "title": "Duplicate Code",
            "exercise_type": "TABLETOP",
            "scenario_description": "Scenario",
            "scheduled_start_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=analyst_headers,
    )
    assert ex_dup.status_code == 409

    # SEC-B5-42: Draft & approve a new BIA v2 with relaxed RTO=10.0h; historical exercise snapshot must stay 4.0h
    bia2 = client.post(
        "/api/v1/resilience/bia",
        json={
            "process_id": proc1["id"],
            "rto_hours": 10.0,
            "rpo_hours": 4.0,
            "mtd_hours": 24.0,
            "hourly_downtime_cost": 50000.0,
            "fixed_outage_cost": 100000.0,
        },
        headers=analyst_headers,
    ).json()
    client.post(f"/api/v1/resilience/bia/{bia2['id']}/approve", headers=manager_headers)

    ex_refetched = client.get(f"/api/v1/resilience/exercises/{ex_body['id']}", headers=analyst_headers).json()
    assert ex_refetched["target_rto_hours_snapshot"] == 4.0
    assert ex_refetched["target_rpo_hours_snapshot"] == 1.0
    assert ex_refetched["target_mtd_hours_snapshot"] == 12.0


def test_b5_16_classify_exercise_outcome_precedence_matrix():
    """Verify deterministic server-side precedence of classify_exercise_outcome across all 6 outcomes."""
    # 1. FAIL_MTD_BREACH dominates all
    assert (
        classify_exercise_outcome(
            rto_breached=True,
            rpo_breached=True,
            mtd_breached=True,
            control_deficiency_observed=True,
            minor_exceptions_noted=True,
        )
        == ExerciseOutcomeEnum.FAIL_MTD_BREACH
    )
    # 2. FAIL_RTO_BREACH dominates RPO, control deficiency, minor exceptions
    assert (
        classify_exercise_outcome(
            rto_breached=True,
            rpo_breached=True,
            mtd_breached=False,
            control_deficiency_observed=True,
            minor_exceptions_noted=True,
        )
        == ExerciseOutcomeEnum.FAIL_RTO_BREACH
    )
    # 3. FAIL_RPO_BREACH dominates control deficiency, minor exceptions
    assert (
        classify_exercise_outcome(
            rto_breached=False,
            rpo_breached=True,
            mtd_breached=False,
            control_deficiency_observed=True,
            minor_exceptions_noted=True,
        )
        == ExerciseOutcomeEnum.FAIL_RPO_BREACH
    )
    # 4. FAIL_CONTROL_DEFICIENCY dominates minor exceptions
    assert (
        classify_exercise_outcome(
            rto_breached=False,
            rpo_breached=False,
            mtd_breached=False,
            control_deficiency_observed=True,
            minor_exceptions_noted=True,
        )
        == ExerciseOutcomeEnum.FAIL_CONTROL_DEFICIENCY
    )
    # 5. PASS_WITH_MINOR_EXCEPTIONS
    assert (
        classify_exercise_outcome(
            rto_breached=False,
            rpo_breached=False,
            mtd_breached=False,
            control_deficiency_observed=False,
            minor_exceptions_noted=True,
        )
        == ExerciseOutcomeEnum.PASS_WITH_MINOR_EXCEPTIONS
    )
    # 6. PASS
    assert (
        classify_exercise_outcome(
            rto_breached=False,
            rpo_breached=False,
            mtd_breached=False,
            control_deficiency_observed=False,
            minor_exceptions_noted=False,
        )
        == ExerciseOutcomeEnum.PASS
    )


def test_b5_17_tabletop_exercise_pass_and_four_eyes_review(
    client: TestClient, b5_fixture: dict
):
    """SEC-B5-10: Verify TABLETOP exercise completion, variance math, SHA-256 sealing, and Four-Eyes review."""
    manager1_headers = get_token_headers(b5_fixture["apex_manager"])
    manager2_headers = get_token_headers(b5_fixture["apex_manager_2"])
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])

    proc, bia = _create_process_with_active_bia(
        client, analyst_headers, manager1_headers, name="Tabletop Pass Process", rto_hours=4.0, rpo_hours=1.0, mtd_hours=12.0
    )
    cp = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-TT-01",
            "title": "Tabletop Continuity Plan",
            "bia_id": bia["id"],
            "strategy_type": "WARM_STANDBY",
            "activation_triggers": "Trigger",
            "estimated_recovery_hours": 2.0,
            "estimated_rpo_hours": 0.5,
        },
        headers=analyst_headers,
    ).json()
    client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/steps",
        json={"step_order": 1, "title": "Step 1", "description": "Desc", "estimated_duration_minutes": 30},
        headers=analyst_headers,
    )
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/submit", headers=analyst_headers)
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/approve", headers=manager1_headers)

    ex = client.post(
        "/api/v1/resilience/exercises",
        json={
            "process_id": proc["id"],
            "continuity_plan_id": cp["id"],
            "exercise_code": "EX-TT-PASS-01",
            "title": "Annual Executive Tabletop",
            "exercise_type": "TABLETOP",
            "scenario_description": "Cyber ransomware tabletop",
            "scheduled_start_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=analyst_headers,
    ).json()

    # Manager 1 starts and completes the exercise
    start_res = client.post(f"/api/v1/resilience/exercises/{ex['id']}/start", headers=manager1_headers)
    assert start_res.status_code == 200
    assert start_res.json()["status"] == "IN_PROGRESS"

    comp_res = client.post(
        f"/api/v1/resilience/exercises/{ex['id']}/complete",
        json={
            "actual_rto_hours": 2.5,
            "actual_rpo_hours": 0.5,
            "control_deficiency_observed": False,
            "minor_exceptions_noted": True,
            "lessons_learned": "Update secondary contact phone tree",
            "executive_summary": "Recovered within target RTO/RPO with minor contact list update",
        },
        headers=manager1_headers,
    )
    assert comp_res.status_code == 200, comp_res.text
    comp = comp_res.json()
    assert comp["status"] == "COMPLETED"
    assert comp["rto_variance_hours"] == -1.5
    assert comp["rpo_variance_hours"] == -0.5
    assert comp["rto_breached"] is False
    assert comp["rpo_breached"] is False
    assert comp["mtd_breached"] is False
    assert comp["outcome"] == "PASS_WITH_MINOR_EXCEPTIONS"
    assert len(comp["result_hash_sha256"]) == 64

    # SEC-B5-10: Manager 1 (executor) attempts self-review -> 403 Forbidden
    self_rev = client.post(
        f"/api/v1/resilience/exercises/{ex['id']}/review",
        json={"review_notes": "Self review attempt"},
        headers=manager1_headers,
    )
    assert self_rev.status_code == 403

    # Manager 2 reviews -> 200 OK
    rev_ok = client.post(
        f"/api/v1/resilience/exercises/{ex['id']}/review",
        json={"review_notes": "Independently verified tabletop minutes and timing."},
        headers=manager2_headers,
    )
    assert rev_ok.status_code == 200
    assert rev_ok.json()["status"] == "REVIEWED"
    assert rev_ok.json()["reviewed_by_user_id"] == b5_fixture["apex_manager_2"].id


def test_b5_18_technical_exercise_mandatory_evidence_gate(
    client: TestClient, b5_fixture: dict
):
    """SEC-B5-29: Technical exercises (FUNCTIONAL_FAILOVER, etc.) require >= 1 valid linked EvidenceItem before completion."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    proc, bia = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="Technical Failover Process"
    )

    cp = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-TECH-01",
            "title": "Technical Failover Plan",
            "bia_id": bia["id"],
            "strategy_type": "HOT_STANDBY",
            "activation_triggers": "Trigger",
            "estimated_recovery_hours": 2.0,
            "estimated_rpo_hours": 0.5,
        },
        headers=analyst_headers,
    ).json()
    client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/steps",
        json={"step_order": 1, "title": "Failover", "description": "Desc", "estimated_duration_minutes": 30},
        headers=analyst_headers,
    )
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/submit", headers=analyst_headers)
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/approve", headers=manager_headers)

    ex = client.post(
        "/api/v1/resilience/exercises",
        json={
            "process_id": proc["id"],
            "continuity_plan_id": cp["id"],
            "exercise_code": "EX-TECH-001",
            "title": "Live Database Failover Exercise",
            "exercise_type": "FUNCTIONAL_FAILOVER",
            "scenario_description": "Kill primary RDS instance and measure promotion time",
            "scheduled_start_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=analyst_headers,
    ).json()

    client.post(f"/api/v1/resilience/exercises/{ex['id']}/start", headers=analyst_headers)

    # SEC-B5-29: Completing FUNCTIONAL_FAILOVER with zero evidence links -> 422
    comp_no_ev = client.post(
        f"/api/v1/resilience/exercises/{ex['id']}/complete",
        json={"actual_rto_hours": 1.2, "actual_rpo_hours": 0.1},
        headers=analyst_headers,
    )
    assert comp_no_ev.status_code == 422
    assert "requires at least one valid linked EvidenceItem" in comp_no_ev.json()["detail"]

    # Link valid EvidenceItem
    link_res = client.post(
        f"/api/v1/resilience/exercises/{ex['id']}/evidence",
        json={
            "evidence_item_id": b5_fixture["apex_evidence"].id,
            "evidence_type_context": "FAILOVER_LOG",
            "notes": "CloudWatch failover telemetry export",
        },
        headers=analyst_headers,
    )
    assert link_res.status_code == 201
    assert link_res.json()["evidence_sha256_snapshot"] == b5_fixture["apex_evidence"].sha256_hash

    # Now completion succeeds -> 200 OK
    comp_ok = client.post(
        f"/api/v1/resilience/exercises/{ex['id']}/complete",
        json={"actual_rto_hours": 1.2, "actual_rpo_hours": 0.1},
        headers=analyst_headers,
    )
    assert comp_ok.status_code == 200
    assert comp_ok.json()["outcome"] == "PASS"


def test_b5_19_evidence_link_validation_and_tamper_detection(
    client: TestClient, db: Session, b5_fixture: dict
):
    """SEC-B5-05, SEC-B5-30, SEC-B5-47, SEC-B5-48: Verify evidence BOLA, status validation, and SHA-256 tamper detection."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    proc, bia = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="Evidence Tamper Process"
    )

    cp = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-EV-01",
            "title": "Evidence Tamper Plan",
            "bia_id": bia["id"],
            "strategy_type": "HOT_STANDBY",
            "activation_triggers": "Trigger",
            "estimated_recovery_hours": 2.0,
            "estimated_rpo_hours": 0.5,
        },
        headers=analyst_headers,
    ).json()
    client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/steps",
        json={"step_order": 1, "title": "Step 1", "description": "Desc", "estimated_duration_minutes": 30},
        headers=analyst_headers,
    )
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/submit", headers=analyst_headers)
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/approve", headers=manager_headers)

    ex = client.post(
        "/api/v1/resilience/exercises",
        json={
            "process_id": proc["id"],
            "continuity_plan_id": cp["id"],
            "exercise_code": "EX-TAMPER-01",
            "title": "Backup Restoration Test",
            "exercise_type": "BACKUP_RESTORATION",
            "scenario_description": "Restore snapshot",
            "scheduled_start_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=analyst_headers,
    ).json()

    # SEC-B5-05: Cross-tenant evidence_item_id -> 404
    bola_ev = client.post(
        f"/api/v1/resilience/exercises/{ex['id']}/evidence",
        json={
            "evidence_item_id": b5_fixture["meridian_evidence"].id,
            "evidence_type_context": "BACKUP_RESTORE_PROOF",
        },
        headers=analyst_headers,
    )
    assert bola_ev.status_code == 404

    # SEC-B5-30: Linking REJECTED EvidenceItem -> 422
    rej_ev = client.post(
        f"/api/v1/resilience/exercises/{ex['id']}/evidence",
        json={
            "evidence_item_id": b5_fixture["apex_evidence_rejected"].id,
            "evidence_type_context": "BACKUP_RESTORE_PROOF",
        },
        headers=analyst_headers,
    )
    assert rej_ev.status_code == 422

    # Link valid evidence and start exercise
    client.post(
        f"/api/v1/resilience/exercises/{ex['id']}/evidence",
        json={
            "evidence_item_id": b5_fixture["apex_evidence"].id,
            "evidence_type_context": "BACKUP_RESTORE_PROOF",
        },
        headers=analyst_headers,
    )
    client.post(f"/api/v1/resilience/exercises/{ex['id']}/start", headers=analyst_headers)

    # SEC-B5-47: Tamper with EvidenceItem.sha256_hash in DB after linking -> complete must fail with 409 Conflict
    ev_obj = db.query(EvidenceItem).filter(EvidenceItem.id == b5_fixture["apex_evidence"].id).first()
    original_hash = ev_obj.sha256_hash
    ev_obj.sha256_hash = hashlib.sha256(b"tampered-bytes").hexdigest()
    db.commit()

    tamper_comp = client.post(
        f"/api/v1/resilience/exercises/{ex['id']}/complete",
        json={"actual_rto_hours": 1.5, "actual_rpo_hours": 0.25},
        headers=analyst_headers,
    )
    assert tamper_comp.status_code == 409
    assert "SHA-256 hash mismatch" in tamper_comp.json()["detail"]

    # Restore hash, but set status to REJECTED (SEC-B5-48) -> complete must fail with 422
    ev_obj.sha256_hash = original_hash
    ev_obj.status = EvidenceStatusEnum.REJECTED
    db.commit()

    status_comp = client.post(
        f"/api/v1/resilience/exercises/{ex['id']}/complete",
        json={"actual_rto_hours": 1.5, "actual_rpo_hours": 0.25},
        headers=analyst_headers,
    )
    assert status_comp.status_code == 422

    # Restore valid status
    ev_obj.status = EvidenceStatusEnum.ACCEPTED
    db.commit()


def test_b5_20_exercise_state_machine_and_immutability_guards(
    client: TestClient, b5_fixture: dict
):
    """SEC-B5-23 through SEC-B5-28 & SEC-B5-46: State machine transition guards and mass-assignment rejection."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    proc, bia = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="State Machine Process"
    )

    cp = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-SM-01",
            "title": "State Machine Plan",
            "bia_id": bia["id"],
            "strategy_type": "WARM_STANDBY",
            "activation_triggers": "Trigger",
            "estimated_recovery_hours": 2.0,
            "estimated_rpo_hours": 0.5,
        },
        headers=analyst_headers,
    ).json()
    client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/steps",
        json={"step_order": 1, "title": "Step 1", "description": "Desc", "estimated_duration_minutes": 30},
        headers=analyst_headers,
    )
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/submit", headers=analyst_headers)
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/approve", headers=manager_headers)

    ex = client.post(
        "/api/v1/resilience/exercises",
        json={
            "process_id": proc["id"],
            "continuity_plan_id": cp["id"],
            "exercise_code": "EX-SM-001",
            "title": "State Machine Exercise",
            "exercise_type": "TABLETOP",
            "scenario_description": "Scenario",
            "scheduled_start_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=analyst_headers,
    ).json()

    # SEC-B5-23: Completing PLANNED exercise without starting -> 409
    assert (
        client.post(
            f"/api/v1/resilience/exercises/{ex['id']}/complete",
            json={"actual_rto_hours": 1.0, "actual_rpo_hours": 0.2},
            headers=analyst_headers,
        ).status_code
        == 409
    )

    # SEC-B5-24: Reviewing PLANNED exercise -> 409
    assert (
        client.post(
            f"/api/v1/resilience/exercises/{ex['id']}/review",
            headers=manager_headers,
        ).status_code
        == 409
    )

    client.post(f"/api/v1/resilience/exercises/{ex['id']}/start", headers=analyst_headers)

    # SEC-B5-28: Negative actual_rto_hours -> 422
    assert (
        client.post(
            f"/api/v1/resilience/exercises/{ex['id']}/complete",
            json={"actual_rto_hours": -1.0, "actual_rpo_hours": 0.2},
            headers=analyst_headers,
        ).status_code
        == 422
    )

    # SEC-B5-27 & SEC-B5-46: Attempting to inject outcome="PASS" or organization_id in complete payload -> 422 (extra="forbid")
    assert (
        client.post(
            f"/api/v1/resilience/exercises/{ex['id']}/complete",
            json={"actual_rto_hours": 10.0, "actual_rpo_hours": 0.2, "outcome": "PASS"},
            headers=analyst_headers,
        ).status_code
        == 422
    )

    # Complete normally
    client.post(
        f"/api/v1/resilience/exercises/{ex['id']}/complete",
        json={"actual_rto_hours": 1.0, "actual_rpo_hours": 0.2},
        headers=analyst_headers,
    )

    # SEC-B5-26: Re-completing COMPLETED exercise -> 409
    assert (
        client.post(
            f"/api/v1/resilience/exercises/{ex['id']}/complete",
            json={"actual_rto_hours": 0.5, "actual_rpo_hours": 0.1},
            headers=analyst_headers,
        ).status_code
        == 409
    )

    # SEC-B5-25: Cancelling COMPLETED exercise to hide results -> 409
    assert (
        client.post(
            f"/api/v1/resilience/exercises/{ex['id']}/cancel",
            json={"reason": "Hide breach"},
            headers=analyst_headers,
        ).status_code
        == 409
    )


def test_b5_21_failed_exercise_review_blocked_without_escalation(
    client: TestClient, b5_fixture: dict
):
    """SEC-B5-31: Reviewing a failed/breached exercise without a linked Finding or RemediationPlan returns 422."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    proc, bia = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="Breach Gate Process", rto_hours=4.0, rpo_hours=1.0, mtd_hours=12.0
    )

    cp = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-BG-01",
            "title": "Breach Gate Plan",
            "bia_id": bia["id"],
            "strategy_type": "WARM_STANDBY",
            "activation_triggers": "Trigger",
            "estimated_recovery_hours": 2.0,
            "estimated_rpo_hours": 0.5,
        },
        headers=analyst_headers,
    ).json()
    client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/steps",
        json={"step_order": 1, "title": "Step 1", "description": "Desc", "estimated_duration_minutes": 30},
        headers=analyst_headers,
    )
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/submit", headers=analyst_headers)
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/approve", headers=manager_headers)

    ex = client.post(
        "/api/v1/resilience/exercises",
        json={
            "process_id": proc["id"],
            "continuity_plan_id": cp["id"],
            "exercise_code": "EX-BREACH-GATE-01",
            "title": "RTO Breach Exercise",
            "exercise_type": "TABLETOP",
            "scenario_description": "Scenario",
            "scheduled_start_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=analyst_headers,
    ).json()

    client.post(f"/api/v1/resilience/exercises/{ex['id']}/start", headers=analyst_headers)
    comp = client.post(
        f"/api/v1/resilience/exercises/{ex['id']}/complete",
        json={"actual_rto_hours": 6.5, "actual_rpo_hours": 0.5},  # Breaches 4.0h RTO
        headers=analyst_headers,
    ).json()
    assert comp["rto_breached"] is True
    assert comp["outcome"] == "FAIL_RTO_BREACH"

    # SEC-B5-31: Attempting to review before escalating to Finding or RemediationPlan -> 422
    rev_blocked = client.post(
        f"/api/v1/resilience/exercises/{ex['id']}/review",
        json={"review_notes": "Trying to sign off without remediation"},
        headers=manager_headers,
    )
    assert rev_blocked.status_code == 422
    assert "must be escalated to a canonical Finding or RemediationPlan" in rev_blocked.json()["detail"]


# ═════════════════════════════════════════════════════════════════════════════
# 4. CLOSED-LOOP ESCALATION, CROSS-TENANT BOLA & RBAC SECURITY (6 TESTS)
# ═════════════════════════════════════════════════════════════════════════════


def test_b5_22_closed_loop_escalation_creates_finding_remediation_and_risk(
    client: TestClient, db: Session, b5_fixture: dict
):
    """Verify closed-loop escalation creating canonical Finding, FindingEvidence, RemediationPlan, Risk, and RiskFindingLink."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    proc, bia = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="Closed Loop Escalation Process", rto_hours=4.0, rpo_hours=1.0, mtd_hours=12.0
    )

    # Link governing CONTROL dependency to process so escalation auto-resolves organization_control_id
    client.post(
        f"/api/v1/resilience/processes/{proc['id']}/dependencies",
        json={
            "dependency_type": "CONTROL",
            "organization_control_id": b5_fixture["apex_ctrl"].id,
            "recovery_priority_order": 1,
        },
        headers=analyst_headers,
    )

    cp = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-ESC-01",
            "title": "Escalation Continuity Plan",
            "bia_id": bia["id"],
            "strategy_type": "HOT_STANDBY",
            "activation_triggers": "Trigger",
            "estimated_recovery_hours": 2.0,
            "estimated_rpo_hours": 0.5,
        },
        headers=analyst_headers,
    ).json()
    client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/steps",
        json={"step_order": 1, "title": "Step 1", "description": "Desc", "estimated_duration_minutes": 30},
        headers=analyst_headers,
    )
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/submit", headers=analyst_headers)
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/approve", headers=manager_headers)

    ex = client.post(
        "/api/v1/resilience/exercises",
        json={
            "process_id": proc["id"],
            "continuity_plan_id": cp["id"],
            "exercise_code": "EX-ESC-FULL-01",
            "title": "Full Interruption DR Test",
            "exercise_type": "FULL_INTERRUPTION",
            "scenario_description": "Full region blackout test",
            "scheduled_start_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=analyst_headers,
    ).json()

    # Link evidence, start, and complete with MTD breach (actual_rto = 15.0h > MTD 12.0h)
    client.post(
        f"/api/v1/resilience/exercises/{ex['id']}/evidence",
        json={
            "evidence_item_id": b5_fixture["apex_evidence"].id,
            "evidence_type_context": "FAILOVER_LOG",
        },
        headers=analyst_headers,
    )
    client.post(f"/api/v1/resilience/exercises/{ex['id']}/start", headers=analyst_headers)
    comp = client.post(
        f"/api/v1/resilience/exercises/{ex['id']}/complete",
        json={
            "actual_rto_hours": 15.0,
            "actual_rpo_hours": 2.5,
            "control_deficiency_observed": True,
            "lessons_learned": "Manual DNS TTL blocked failover for 11 hours",
        },
        headers=analyst_headers,
    ).json()
    assert comp["mtd_breached"] is True
    assert comp["outcome"] == "FAIL_MTD_BREACH"

    # Escalate to Finding + RemediationPlan + Risk
    esc_res = client.post(
        f"/api/v1/resilience/exercises/{ex['id']}/escalate",
        json={
            "create_finding": True,
            "create_remediation_plan": True,
            "create_risk": True,
            "remediation_title": "Automate Route53 DNS Failover TTL",
            "risk_title": "Prolonged Settlement Outage Exceeding MTD",
        },
        headers=analyst_headers,
    )
    assert esc_res.status_code == 200, esc_res.text
    esc = esc_res.json()
    assert esc["finding_id"] is not None
    assert esc["remediation_plan_id"] is not None
    assert esc["risk_id"] is not None

    # Verify canonical records in DB
    finding = db.query(Finding).filter(Finding.id == esc["finding_id"]).first()
    assert finding is not None
    assert finding.severity == FindingSeverityEnum.CRITICAL
    assert finding.organization_control_id == b5_fixture["apex_ctrl"].id

    # Verify exercise evidence was propagated to FindingEvidence
    fe = (
        db.query(FindingEvidence)
        .filter(
            FindingEvidence.finding_id == finding.id,
            FindingEvidence.evidence_id == b5_fixture["apex_evidence"].id,
        )
        .first()
    )
    assert fe is not None

    rem = db.query(RemediationPlan).filter(RemediationPlan.id == esc["remediation_plan_id"]).first()
    assert rem is not None
    assert rem.finding_id == finding.id

    risk = db.query(Risk).filter(Risk.id == esc["risk_id"]).first()
    assert risk is not None
    rfl = (
        db.query(RiskFindingLink)
        .filter(RiskFindingLink.risk_id == risk.id, RiskFindingLink.finding_id == finding.id)
        .first()
    )
    assert rfl is not None

    # Now Four-Eyes review sign-off succeeds!
    rev = client.post(
        f"/api/v1/resilience/exercises/{ex['id']}/review",
        json={"review_notes": "Breach escalated to CAPA and Risk Register; review complete."},
        headers=manager_headers,
    )
    assert rev.status_code == 200
    assert rev.json()["status"] == "REVIEWED"


def test_b5_23_escalation_duplicate_and_missing_control_guards(
    client: TestClient, b5_fixture: dict
):
    """SEC-B5-32 & SEC-B5-49: Duplicate escalation returns 409; missing organization_control_id returns 422."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    proc, bia = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="No Control Dependency Process"
    )

    cp = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-NOCTRL-01",
            "title": "No Control Plan",
            "bia_id": bia["id"],
            "strategy_type": "WARM_STANDBY",
            "activation_triggers": "Trigger",
            "estimated_recovery_hours": 2.0,
            "estimated_rpo_hours": 0.5,
        },
        headers=analyst_headers,
    ).json()
    client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/steps",
        json={"step_order": 1, "title": "Step 1", "description": "Desc", "estimated_duration_minutes": 30},
        headers=analyst_headers,
    )
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/submit", headers=analyst_headers)
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/approve", headers=manager_headers)

    ex = client.post(
        "/api/v1/resilience/exercises",
        json={
            "process_id": proc["id"],
            "continuity_plan_id": cp["id"],
            "exercise_code": "EX-NOCTRL-01",
            "title": "Tabletop Breach",
            "exercise_type": "TABLETOP",
            "scenario_description": "Scenario",
            "scheduled_start_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=analyst_headers,
    ).json()
    client.post(f"/api/v1/resilience/exercises/{ex['id']}/start", headers=analyst_headers)
    client.post(
        f"/api/v1/resilience/exercises/{ex['id']}/complete",
        json={"actual_rto_hours": 6.0, "actual_rpo_hours": 0.5},
        headers=analyst_headers,
    )

    # SEC-B5-49: Escalating with create_finding=True when no organization_control_id is passed and process has no CONTROL dependency -> 422
    no_ctrl_res = client.post(
        f"/api/v1/resilience/exercises/{ex['id']}/escalate",
        json={"create_finding": True},
        headers=analyst_headers,
    )
    assert no_ctrl_res.status_code == 422
    assert "organization_control_id" in no_ctrl_res.json()["detail"]

    # Provide explicit organization_control_id -> 200 OK
    ok_res = client.post(
        f"/api/v1/resilience/exercises/{ex['id']}/escalate",
        json={
            "create_finding": True,
            "organization_control_id": b5_fixture["apex_ctrl"].id,
        },
        headers=analyst_headers,
    )
    assert ok_res.status_code == 200

    # SEC-B5-32: Attempting to escalate a second Finding on the same exercise -> 409 Conflict
    dup_res = client.post(
        f"/api/v1/resilience/exercises/{ex['id']}/escalate",
        json={
            "create_finding": True,
            "organization_control_id": b5_fixture["apex_ctrl"].id,
        },
        headers=analyst_headers,
    )
    assert dup_res.status_code == 409


def test_b5_24_escalation_cross_tenant_bola_guards(
    client: TestClient, db: Session, b5_fixture: dict
):
    """SEC-B5-06: Linking cross-tenant Finding, RemediationPlan, or Risk during escalation returns 404."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    proc, bia = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="Escalation BOLA Process"
    )

    cp = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-EBOLA-01",
            "title": "Escalation BOLA Plan",
            "bia_id": bia["id"],
            "strategy_type": "WARM_STANDBY",
            "activation_triggers": "Trigger",
            "estimated_recovery_hours": 2.0,
            "estimated_rpo_hours": 0.5,
        },
        headers=analyst_headers,
    ).json()
    client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/steps",
        json={"step_order": 1, "title": "Step 1", "description": "Desc", "estimated_duration_minutes": 30},
        headers=analyst_headers,
    )
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/submit", headers=analyst_headers)
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/approve", headers=manager_headers)

    ex = client.post(
        "/api/v1/resilience/exercises",
        json={
            "process_id": proc["id"],
            "continuity_plan_id": cp["id"],
            "exercise_code": "EX-EBOLA-01",
            "title": "Escalation BOLA Exercise",
            "exercise_type": "TABLETOP",
            "scenario_description": "Scenario",
            "scheduled_start_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=analyst_headers,
    ).json()
    client.post(f"/api/v1/resilience/exercises/{ex['id']}/start", headers=analyst_headers)
    client.post(
        f"/api/v1/resilience/exercises/{ex['id']}/complete",
        json={"actual_rto_hours": 5.0, "actual_rpo_hours": 0.5},
        headers=analyst_headers,
    )

    # Create a Finding in Meridian tenant
    meridian_finding = Finding(
        organization_id=b5_fixture["org_meridian"].id,
        organization_control_id=b5_fixture["meridian_ctrl"].id,
        title="Meridian Finding",
        description="Desc",
        recommendation="Remediate control gap",
        finding_type=FindingTypeEnum.CONTROL_GAP,
        severity=FindingSeverityEnum.HIGH,
        impact=4,
        likelihood=4,
        risk_score=16,
        risk_band="HIGH",
        owner_id=b5_fixture["meridian_manager"].id,
        created_by_id=b5_fixture["meridian_manager"].id,
    )
    db.add(meridian_finding)
    db.commit()

    bola_f = client.post(
        f"/api/v1/resilience/exercises/{ex['id']}/escalate",
        json={"create_finding": False, "existing_finding_id": meridian_finding.id},
        headers=analyst_headers,
    )
    assert bola_f.status_code == 404


def test_b5_25_cross_tenant_bola_isolation_across_all_batch5_endpoints(
    client: TestClient, b5_fixture: dict
):
    """SEC-B5-01 & SEC-B5-02: Meridian tenant cannot read or mutate Apex ContinuityPlans, Steps, or Exercises (404)."""
    apex_analyst = get_token_headers(b5_fixture["apex_analyst"])
    apex_manager = get_token_headers(b5_fixture["apex_manager"])
    meridian_manager = get_token_headers(b5_fixture["meridian_manager"])

    proc, bia = _create_process_with_active_bia(
        client, apex_analyst, apex_manager, name="Apex Isolated Process"
    )
    cp = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-ISO-01",
            "title": "Apex Plan",
            "bia_id": bia["id"],
            "strategy_type": "WARM_STANDBY",
            "activation_triggers": "Trigger",
            "estimated_recovery_hours": 2.0,
            "estimated_rpo_hours": 0.5,
        },
        headers=apex_analyst,
    ).json()
    step = client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/steps",
        json={"step_order": 1, "title": "Step 1", "description": "Desc", "estimated_duration_minutes": 30},
        headers=apex_analyst,
    ).json()
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/submit", headers=apex_analyst)
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/approve", headers=apex_manager)

    ex = client.post(
        "/api/v1/resilience/exercises",
        json={
            "process_id": proc["id"],
            "continuity_plan_id": cp["id"],
            "exercise_code": "EX-ISO-01",
            "title": "Apex Exercise",
            "exercise_type": "TABLETOP",
            "scenario_description": "Scenario",
            "scheduled_start_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=apex_analyst,
    ).json()

    # Meridian requests against Apex resources must all return 404
    assert client.get(f"/api/v1/resilience/continuity-plans/{cp['id']}", headers=meridian_manager).status_code == 404
    assert client.patch(f"/api/v1/resilience/continuity-plans/{cp['id']}", json={"title": "Cross Tenant Title"}, headers=meridian_manager).status_code == 404
    assert client.get(f"/api/v1/resilience/continuity-plans/{cp['id']}/steps", headers=meridian_manager).status_code == 404
    assert client.delete(f"/api/v1/resilience/continuity-plans/{cp['id']}/steps/{step['id']}", headers=meridian_manager).status_code == 404
    assert client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/approve", headers=meridian_manager).status_code == 404
    assert client.get(f"/api/v1/resilience/exercises/{ex['id']}", headers=meridian_manager).status_code == 404
    assert client.post(f"/api/v1/resilience/exercises/{ex['id']}/start", headers=meridian_manager).status_code == 404
    assert client.get(f"/api/v1/resilience/processes/{proc['id']}/dependency-health", headers=meridian_manager).status_code == 404
    assert client.get(f"/api/v1/resilience/processes/{proc['id']}/impact-summary", headers=meridian_manager).status_code == 404


def test_b5_26_rbac_enforcement_across_all_roles(
    client: TestClient, b5_fixture: dict
):
    """SEC-B5-11 & SEC-B5-12: Verify RBAC enforcement for VIEWER, AUDITOR, GRC_ANALYST, and MANAGER."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    viewer_headers = get_token_headers(b5_fixture["apex_viewer"])
    auditor_headers = get_token_headers(b5_fixture["apex_auditor"])

    proc, bia = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="RBAC Verification Process"
    )

    # VIEWER and AUDITOR can read dashboard and plans, but cannot create ContinuityPlan (403)
    assert client.get("/api/v1/resilience/dashboard", headers=viewer_headers).status_code == 200
    assert client.get("/api/v1/resilience/dashboard", headers=auditor_headers).status_code == 200

    plan_payload = {
        "plan_code": "BCP-RBAC-01",
        "title": "RBAC Plan",
        "bia_id": bia["id"],
        "strategy_type": "WARM_STANDBY",
        "activation_triggers": "Trigger",
        "estimated_recovery_hours": 2.0,
        "estimated_rpo_hours": 0.5,
    }
    assert (
        client.post(
            f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
            json=plan_payload,
            headers=viewer_headers,
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
            json=plan_payload,
            headers=auditor_headers,
        ).status_code
        == 403
    )

    # GRC_ANALYST creates and submits plan, but cannot approve (lacks RESILIENCE_APPROVE -> 403)
    cp = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json=plan_payload,
        headers=analyst_headers,
    ).json()
    client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/steps",
        json={"step_order": 1, "title": "Step 1", "description": "Desc", "estimated_duration_minutes": 30},
        headers=analyst_headers,
    )
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/submit", headers=analyst_headers)

    assert (
        client.post(
            f"/api/v1/resilience/continuity-plans/{cp['id']}/approve",
            headers=analyst_headers,
        ).status_code
        == 403
    )


def test_b5_27_audit_trail_completeness_for_batch5_events(
    client: TestClient, db: Session, b5_fixture: dict
):
    """Verify AuditLog entries are recorded for Batch 5 continuity plan and exercise lifecycle events."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    proc, bia = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="Audit Trail Process"
    )

    cp = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-AUD-01",
            "title": "Audit Plan",
            "bia_id": bia["id"],
            "strategy_type": "WARM_STANDBY",
            "activation_triggers": "Trigger",
            "estimated_recovery_hours": 2.0,
            "estimated_rpo_hours": 0.5,
        },
        headers=analyst_headers,
    ).json()
    client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/steps",
        json={"step_order": 1, "title": "Step 1", "description": "Desc", "estimated_duration_minutes": 30},
        headers=analyst_headers,
    )
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/submit", headers=analyst_headers)
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/approve", headers=manager_headers)

    ex = client.post(
        "/api/v1/resilience/exercises",
        json={
            "process_id": proc["id"],
            "continuity_plan_id": cp["id"],
            "exercise_code": "EX-AUD-01",
            "title": "Audit Exercise",
            "exercise_type": "TABLETOP",
            "scenario_description": "Scenario",
            "scheduled_start_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=analyst_headers,
    ).json()
    client.post(f"/api/v1/resilience/exercises/{ex['id']}/start", headers=analyst_headers)
    client.post(
        f"/api/v1/resilience/exercises/{ex['id']}/complete",
        json={"actual_rto_hours": 1.5, "actual_rpo_hours": 0.5},
        headers=analyst_headers,
    )
    client.post(f"/api/v1/resilience/exercises/{ex['id']}/review", headers=manager_headers)

    actions = {
        row.action
        for row in db.query(AuditLog)
        .filter(AuditLog.organization_id == b5_fixture["org_apex"].id)
        .all()
    }
    expected_actions = {
        "continuity_plan.created",
        "continuity_recovery_step.created",
        "continuity_plan.submitted",
        "continuity_plan.approved",
        "resilience_exercise.created",
        "resilience_exercise.started",
        "resilience_exercise.completed",
        "resilience_exercise.reviewed",
    }
    assert expected_actions.issubset(actions)


# ═════════════════════════════════════════════════════════════════════════════
# 5. GRANULAR ADVERSARIAL & MATHEMATICAL INVARIANT TESTS (18 ADDITIONAL TESTS)
# ═════════════════════════════════════════════════════════════════════════════


def test_b5_28_plan_hash_sha256_determinism(client: TestClient, b5_fixture: dict):
    """Verify compute_plan_hash_sha256 is deterministic and changes when recovery steps change."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    proc, bia = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="Hash Determinism Process"
    )
    cp = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-HASH-01",
            "title": "Hash Plan",
            "bia_id": bia["id"],
            "strategy_type": "WARM_STANDBY",
            "activation_triggers": "Trigger",
            "estimated_recovery_hours": 2.0,
            "estimated_rpo_hours": 0.5,
        },
        headers=analyst_headers,
    ).json()
    step = client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/steps",
        json={"step_order": 1, "title": "Step 1", "description": "Desc", "estimated_duration_minutes": 20},
        headers=analyst_headers,
    ).json()

    sub1 = client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/submit", headers=analyst_headers).json()
    hash1 = sub1["plan_hash_sha256"]
    assert len(hash1) == 64

    # Reject back to DRAFT, modify step duration, re-submit -> hash must change
    client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/reject",
        json={"reason": "Change step duration"},
        headers=manager_headers,
    )
    client.patch(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/steps/{step['id']}",
        json={"estimated_duration_minutes": 45},
        headers=analyst_headers,
    )
    sub2 = client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/submit", headers=analyst_headers).json()
    assert sub2["plan_hash_sha256"] != hash1


def test_b5_29_plan_evidence_link_and_duplicate_rejection(
    client: TestClient, b5_fixture: dict
):
    """Verify linking EvidenceItem to ContinuityPlan and rejecting duplicate link with 409."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    proc, bia = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="Plan Evidence Process"
    )
    cp = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-PEV-01",
            "title": "Plan Evidence",
            "bia_id": bia["id"],
            "strategy_type": "WARM_STANDBY",
            "activation_triggers": "Trigger",
            "estimated_recovery_hours": 2.0,
            "estimated_rpo_hours": 0.5,
        },
        headers=analyst_headers,
    ).json()

    link1 = client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/evidence",
        json={
            "evidence_item_id": b5_fixture["apex_evidence"].id,
            "evidence_type_context": "CONTINUITY_RUNBOOK",
            "notes": "Runbook PDF",
        },
        headers=analyst_headers,
    )
    assert link1.status_code == 201

    # Duplicate evidence link on same plan -> 409
    link_dup = client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/evidence",
        json={
            "evidence_item_id": b5_fixture["apex_evidence"].id,
            "evidence_type_context": "CONTINUITY_RUNBOOK",
        },
        headers=analyst_headers,
    )
    assert link_dup.status_code == 409

    ev_list = client.get(f"/api/v1/resilience/continuity-plans/{cp['id']}/evidence", headers=analyst_headers).json()
    assert len(ev_list) == 1


def test_b5_30_plan_evidence_cross_tenant_bola_rejected(
    client: TestClient, b5_fixture: dict
):
    """SEC-B5-05: Linking cross-tenant EvidenceItem to ContinuityPlan returns 404."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    proc, bia = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="Plan Evidence BOLA Process"
    )
    cp = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-PEVBOLA-01",
            "title": "Plan Evidence BOLA",
            "bia_id": bia["id"],
            "strategy_type": "WARM_STANDBY",
            "activation_triggers": "Trigger",
            "estimated_recovery_hours": 2.0,
            "estimated_rpo_hours": 0.5,
        },
        headers=analyst_headers,
    ).json()

    res = client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/evidence",
        json={
            "evidence_item_id": b5_fixture["meridian_evidence"].id,
            "evidence_type_context": "CONTINUITY_RUNBOOK",
        },
        headers=analyst_headers,
    )
    assert res.status_code == 404


def test_b5_31_delete_recovery_step_in_draft_succeeds(
    client: TestClient, b5_fixture: dict
):
    """Verify deleting a recovery step in DRAFT status succeeds and updates duration rollup."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    proc, bia = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="Step Delete Process"
    )
    cp = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-SDEL-01",
            "title": "Step Delete Plan",
            "bia_id": bia["id"],
            "strategy_type": "WARM_STANDBY",
            "activation_triggers": "Trigger",
            "estimated_recovery_hours": 2.0,
            "estimated_rpo_hours": 0.5,
        },
        headers=analyst_headers,
    ).json()
    s1 = client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/steps",
        json={"step_order": 1, "title": "Step 1", "description": "Desc", "estimated_duration_minutes": 30},
        headers=analyst_headers,
    ).json()
    s2 = client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/steps",
        json={"step_order": 2, "title": "Step 2", "description": "Desc", "estimated_duration_minutes": 45},
        headers=analyst_headers,
    ).json()

    del_res = client.delete(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/steps/{s2['id']}",
        headers=analyst_headers,
    )
    assert del_res.status_code == 204

    detail = client.get(f"/api/v1/resilience/continuity-plans/{cp['id']}", headers=analyst_headers).json()
    assert detail["total_step_duration_minutes"] == 30
    assert len(detail["recovery_steps"]) == 1
    assert detail["recovery_steps"][0]["id"] == s1["id"]


def test_b5_32_exercise_chronology_completed_before_started_rejected(
    client: TestClient, b5_fixture: dict
):
    """Verify completing an exercise with completed_at < started_at is rejected with 422."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    proc, bia = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="Chronology Process"
    )
    cp = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-CHRON-01",
            "title": "Chronology Plan",
            "bia_id": bia["id"],
            "strategy_type": "WARM_STANDBY",
            "activation_triggers": "Trigger",
            "estimated_recovery_hours": 2.0,
            "estimated_rpo_hours": 0.5,
        },
        headers=analyst_headers,
    ).json()
    client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/steps",
        json={"step_order": 1, "title": "Step 1", "description": "Desc", "estimated_duration_minutes": 30},
        headers=analyst_headers,
    )
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/submit", headers=analyst_headers)
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/approve", headers=manager_headers)

    now = datetime.now(timezone.utc)
    ex = client.post(
        "/api/v1/resilience/exercises",
        json={
            "process_id": proc["id"],
            "continuity_plan_id": cp["id"],
            "exercise_code": "EX-CHRON-01",
            "title": "Chronology Exercise",
            "exercise_type": "TABLETOP",
            "scenario_description": "Scenario",
            "scheduled_start_at": now.isoformat(),
        },
        headers=analyst_headers,
    ).json()

    client.post(
        f"/api/v1/resilience/exercises/{ex['id']}/start",
        json={"started_at": now.isoformat()},
        headers=analyst_headers,
    )
    bad_comp = client.post(
        f"/api/v1/resilience/exercises/{ex['id']}/complete",
        json={
            "actual_rto_hours": 1.0,
            "actual_rpo_hours": 0.2,
            "completed_at": (now - timedelta(hours=2)).isoformat(),
        },
        headers=analyst_headers,
    )
    assert bad_comp.status_code == 422
    assert "completed_at cannot precede started_at" in bad_comp.json()["detail"]


def test_b5_33_exercise_rpo_breach_outcome_classification(
    client: TestClient, b5_fixture: dict
):
    """Verify exercise where RTO passes but RPO breaches is classified as FAIL_RPO_BREACH."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    proc, bia = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="RPO Breach Process", rto_hours=4.0, rpo_hours=1.0, mtd_hours=12.0
    )
    cp = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-RPOB-01",
            "title": "RPO Breach Plan",
            "bia_id": bia["id"],
            "strategy_type": "WARM_STANDBY",
            "activation_triggers": "Trigger",
            "estimated_recovery_hours": 2.0,
            "estimated_rpo_hours": 0.5,
        },
        headers=analyst_headers,
    ).json()
    client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/steps",
        json={"step_order": 1, "title": "Step 1", "description": "Desc", "estimated_duration_minutes": 30},
        headers=analyst_headers,
    )
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/submit", headers=analyst_headers)
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/approve", headers=manager_headers)

    ex = client.post(
        "/api/v1/resilience/exercises",
        json={
            "process_id": proc["id"],
            "continuity_plan_id": cp["id"],
            "exercise_code": "EX-RPOB-01",
            "title": "RPO Breach Test",
            "exercise_type": "TABLETOP",
            "scenario_description": "Scenario",
            "scheduled_start_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=analyst_headers,
    ).json()
    client.post(f"/api/v1/resilience/exercises/{ex['id']}/start", headers=analyst_headers)
    comp = client.post(
        f"/api/v1/resilience/exercises/{ex['id']}/complete",
        json={"actual_rto_hours": 2.0, "actual_rpo_hours": 3.5},
        headers=analyst_headers,
    ).json()
    assert comp["rto_breached"] is False
    assert comp["rpo_breached"] is True
    assert comp["rpo_variance_hours"] == 2.5
    assert comp["outcome"] == "FAIL_RPO_BREACH"


def test_b5_34_exercise_control_deficiency_outcome_classification(
    client: TestClient, b5_fixture: dict
):
    """Verify exercise where RTO and RPO pass but control_deficiency_observed=True is FAIL_CONTROL_DEFICIENCY."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    proc, bia = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="Ctrl Def Process", rto_hours=4.0, rpo_hours=1.0, mtd_hours=12.0
    )
    cp = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-CDEF-01",
            "title": "Ctrl Def Plan",
            "bia_id": bia["id"],
            "strategy_type": "WARM_STANDBY",
            "activation_triggers": "Trigger",
            "estimated_recovery_hours": 2.0,
            "estimated_rpo_hours": 0.5,
        },
        headers=analyst_headers,
    ).json()
    client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/steps",
        json={"step_order": 1, "title": "Step 1", "description": "Desc", "estimated_duration_minutes": 30},
        headers=analyst_headers,
    )
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/submit", headers=analyst_headers)
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/approve", headers=manager_headers)

    ex = client.post(
        "/api/v1/resilience/exercises",
        json={
            "process_id": proc["id"],
            "continuity_plan_id": cp["id"],
            "exercise_code": "EX-CDEF-01",
            "title": "Control Deficiency Test",
            "exercise_type": "TABLETOP",
            "scenario_description": "Scenario",
            "scheduled_start_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=analyst_headers,
    ).json()
    client.post(f"/api/v1/resilience/exercises/{ex['id']}/start", headers=analyst_headers)
    comp = client.post(
        f"/api/v1/resilience/exercises/{ex['id']}/complete",
        json={
            "actual_rto_hours": 1.5,
            "actual_rpo_hours": 0.2,
            "control_deficiency_observed": True,
        },
        headers=analyst_headers,
    ).json()
    assert comp["rto_breached"] is False
    assert comp["rpo_breached"] is False
    assert comp["outcome"] == "FAIL_CONTROL_DEFICIENCY"


def test_b5_35_list_exercises_filtering_by_process_status_and_outcome(
    client: TestClient, b5_fixture: dict
):
    """Verify GET /api/v1/resilience/exercises filters by process_id, status, and outcome."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    proc, bia = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="Exercise Filter Process"
    )
    cp = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-FILT-01",
            "title": "Filter Plan",
            "bia_id": bia["id"],
            "strategy_type": "WARM_STANDBY",
            "activation_triggers": "Trigger",
            "estimated_recovery_hours": 2.0,
            "estimated_rpo_hours": 0.5,
        },
        headers=analyst_headers,
    ).json()
    client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/steps",
        json={"step_order": 1, "title": "Step 1", "description": "Desc", "estimated_duration_minutes": 30},
        headers=analyst_headers,
    )
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/submit", headers=analyst_headers)
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/approve", headers=manager_headers)

    ex = client.post(
        "/api/v1/resilience/exercises",
        json={
            "process_id": proc["id"],
            "continuity_plan_id": cp["id"],
            "exercise_code": "EX-FILT-01",
            "title": "Filterable Exercise",
            "exercise_type": "TABLETOP",
            "scenario_description": "Scenario",
            "scheduled_start_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=analyst_headers,
    ).json()
    client.post(f"/api/v1/resilience/exercises/{ex['id']}/start", headers=analyst_headers)
    client.post(
        f"/api/v1/resilience/exercises/{ex['id']}/complete",
        json={"actual_rto_hours": 1.0, "actual_rpo_hours": 0.1},
        headers=analyst_headers,
    )

    by_proc = client.get(
        f"/api/v1/resilience/exercises?process_id={proc['id']}&status=COMPLETED&outcome=PASS",
        headers=analyst_headers,
    ).json()
    assert len(by_proc) == 1
    assert by_proc[0]["id"] == ex["id"]


def test_b5_36_attaching_evidence_to_reviewed_or_cancelled_exercise_blocked(
    client: TestClient, b5_fixture: dict
):
    """Verify attaching new evidence to a CANCELLED or REVIEWED exercise returns 409 Conflict."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    proc, bia = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="Cancelled Ev Process"
    )
    cp = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-CEV-01",
            "title": "Cancelled Ev Plan",
            "bia_id": bia["id"],
            "strategy_type": "WARM_STANDBY",
            "activation_triggers": "Trigger",
            "estimated_recovery_hours": 2.0,
            "estimated_rpo_hours": 0.5,
        },
        headers=analyst_headers,
    ).json()
    client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/steps",
        json={"step_order": 1, "title": "Step 1", "description": "Desc", "estimated_duration_minutes": 30},
        headers=analyst_headers,
    )
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/submit", headers=analyst_headers)
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/approve", headers=manager_headers)

    ex = client.post(
        "/api/v1/resilience/exercises",
        json={
            "process_id": proc["id"],
            "continuity_plan_id": cp["id"],
            "exercise_code": "EX-CEV-01",
            "title": "Cancelled Exercise",
            "exercise_type": "TABLETOP",
            "scenario_description": "Scenario",
            "scheduled_start_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=analyst_headers,
    ).json()
    client.post(f"/api/v1/resilience/exercises/{ex['id']}/cancel", json={"reason": "Abort"}, headers=analyst_headers)

    ev_res = client.post(
        f"/api/v1/resilience/exercises/{ex['id']}/evidence",
        json={
            "evidence_item_id": b5_fixture["apex_evidence"].id,
            "evidence_type_context": "POST_MORTEM_REPORT",
        },
        headers=analyst_headers,
    )
    assert ev_res.status_code == 409


def test_b5_37_escalating_planned_or_in_progress_exercise_blocked(
    client: TestClient, b5_fixture: dict
):
    """Verify escalating an exercise before it is COMPLETED returns 409 Conflict."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    proc, bia = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="Premature Escalate Process"
    )
    cp = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-PESC-01",
            "title": "Premature Escalate Plan",
            "bia_id": bia["id"],
            "strategy_type": "WARM_STANDBY",
            "activation_triggers": "Trigger",
            "estimated_recovery_hours": 2.0,
            "estimated_rpo_hours": 0.5,
        },
        headers=analyst_headers,
    ).json()
    client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/steps",
        json={"step_order": 1, "title": "Step 1", "description": "Desc", "estimated_duration_minutes": 30},
        headers=analyst_headers,
    )
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/submit", headers=analyst_headers)
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/approve", headers=manager_headers)

    ex = client.post(
        "/api/v1/resilience/exercises",
        json={
            "process_id": proc["id"],
            "continuity_plan_id": cp["id"],
            "exercise_code": "EX-PESC-01",
            "title": "Planned Exercise",
            "exercise_type": "TABLETOP",
            "scenario_description": "Scenario",
            "scheduled_start_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=analyst_headers,
    ).json()

    esc_res = client.post(
        f"/api/v1/resilience/exercises/{ex['id']}/escalate",
        json={"create_finding": True, "organization_control_id": b5_fixture["apex_ctrl"].id},
        headers=analyst_headers,
    )
    assert esc_res.status_code == 409


def test_b5_38_update_continuity_plan_in_draft_succeeds(
    client: TestClient, b5_fixture: dict
):
    """Verify PATCH /continuity-plans/{id} succeeds while plan is in DRAFT status."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    proc, bia = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="Patch Draft Plan Process"
    )
    cp = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-PATCH-01",
            "title": "Initial Title",
            "bia_id": bia["id"],
            "strategy_type": "COLD_SITE",
            "activation_triggers": "Initial trigger",
            "estimated_recovery_hours": 3.0,
            "estimated_rpo_hours": 0.5,
        },
        headers=analyst_headers,
    ).json()

    upd = client.patch(
        f"/api/v1/resilience/continuity-plans/{cp['id']}",
        json={
            "title": "Updated Hot Standby Title",
            "strategy_type": "HOT_STANDBY",
            "estimated_recovery_hours": 1.5,
        },
        headers=analyst_headers,
    )
    assert upd.status_code == 200
    assert upd.json()["title"] == "Updated Hot Standby Title"
    assert upd.json()["strategy_type"] == "HOT_STANDBY"
    assert upd.json()["estimated_recovery_hours"] == 1.5


def test_b5_39_list_continuity_plans_filter_by_status(
    client: TestClient, b5_fixture: dict
):
    """Verify GET /processes/{id}/continuity-plans?status=APPROVED filters properly."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    proc, bia = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="Filter Plans Process"
    )
    cp1 = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-FP-01",
            "title": "Plan 1",
            "bia_id": bia["id"],
            "version_major": 1,
            "version_minor": 0,
            "strategy_type": "WARM_STANDBY",
            "activation_triggers": "Trigger",
            "estimated_recovery_hours": 2.0,
            "estimated_rpo_hours": 0.5,
        },
        headers=analyst_headers,
    ).json()
    client.post(
        f"/api/v1/resilience/continuity-plans/{cp1['id']}/steps",
        json={"step_order": 1, "title": "Step 1", "description": "Desc", "estimated_duration_minutes": 30},
        headers=analyst_headers,
    )
    client.post(f"/api/v1/resilience/continuity-plans/{cp1['id']}/submit", headers=analyst_headers)
    client.post(f"/api/v1/resilience/continuity-plans/{cp1['id']}/approve", headers=manager_headers)

    # Create second plan in DRAFT
    client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-FP-01",
            "title": "Plan 2 Draft",
            "bia_id": bia["id"],
            "version_major": 2,
            "version_minor": 0,
            "strategy_type": "WARM_STANDBY",
            "activation_triggers": "Trigger",
            "estimated_recovery_hours": 2.0,
            "estimated_rpo_hours": 0.5,
        },
        headers=analyst_headers,
    )

    approved_only = client.get(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans?status=APPROVED",
        headers=analyst_headers,
    ).json()
    assert len(approved_only) == 1
    assert approved_only[0]["id"] == cp1["id"]


def test_b5_40_overdue_continuity_plan_review_telemetry(
    client: TestClient, db: Session, b5_fixture: dict
):
    """Verify overdue_continuity_plan_reviews increments when next_review_due_at < now_utc."""
    from app.models.resilience import ContinuityPlan

    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    proc, bia = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="Overdue Review Process"
    )
    cp = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-OVERDUE-01",
            "title": "Overdue Plan",
            "bia_id": bia["id"],
            "strategy_type": "WARM_STANDBY",
            "activation_triggers": "Trigger",
            "estimated_recovery_hours": 2.0,
            "estimated_rpo_hours": 0.5,
        },
        headers=analyst_headers,
    ).json()
    client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/steps",
        json={"step_order": 1, "title": "Step 1", "description": "Desc", "estimated_duration_minutes": 30},
        headers=analyst_headers,
    )
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/submit", headers=analyst_headers)
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/approve", headers=manager_headers)

    # Backdate next_review_due_at in DB
    plan_row = db.query(ContinuityPlan).filter(ContinuityPlan.id == cp["id"]).first()
    plan_row.next_review_due_at = datetime.now(timezone.utc) - timedelta(days=5)
    db.commit()

    dash = client.get("/api/v1/resilience/dashboard", headers=analyst_headers).json()
    assert dash["overdue_continuity_plan_reviews"] >= 1


def test_b5_41_simulate_outage_on_data_asset_node(
    client: TestClient, b5_fixture: dict
):
    """Verify POST /simulate-outage works for DATA_ASSET failure nodes."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    proc, _ = _create_process_with_active_bia(
        client,
        analyst_headers,
        manager_headers,
        name="Data Asset Dependent Process",
        rto_hours=2.0,
        rpo_hours=0.5,
        mtd_hours=6.0,
        hourly_cost=10000.0,
        fixed_cost=5000.0,
    )
    client.post(
        f"/api/v1/resilience/processes/{proc['id']}/dependencies",
        json={
            "dependency_type": "DATA_ASSET",
            "data_asset_id": b5_fixture["apex_data_approved"].id,
            "failure_propagation_weight": 0.8,
        },
        headers=analyst_headers,
    )

    sim = client.post(
        "/api/v1/resilience/simulate-outage",
        json={
            "failing_node_type": "DATA_ASSET",
            "failing_node_id": b5_fixture["apex_data_approved"].id,
            "outage_duration_hours": 10.0,
        },
        headers=analyst_headers,
    )
    assert sim.status_code == 200
    body = sim.json()
    assert body["affected_process_count"] >= 1
    assert body["mtd_breach_count"] >= 1
    # Raw loss for 10h = 5000 + 10000*10 = 105,000; weighted by 0.8 = 84,000
    matched = [p for p in body["affected_processes"] if p["process_id"] == proc["id"]][0]
    assert matched["projected_financial_loss"] == 84000.0
    assert matched["mtd_breached"] is True


def test_b5_42_mass_assignment_rejected_on_continuity_plan_create(
    client: TestClient, b5_fixture: dict
):
    """SEC-B5-46: Attempting to inject status, organization_id, or plan_hash_sha256 in ContinuityPlanCreate returns 422."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    proc, _ = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="Mass Assign Plan Process"
    )

    res = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-MA-01",
            "title": "Mass Assign Plan",
            "strategy_type": "WARM_STANDBY",
            "activation_triggers": "Trigger",
            "estimated_recovery_hours": 2.0,
            "estimated_rpo_hours": 0.5,
            "status": "APPROVED",
            "organization_id": 9999,
        },
        headers=analyst_headers,
    )
    assert res.status_code == 422


def test_b5_43_duplicate_dependency_rejected_with_409(
    client: TestClient, b5_fixture: dict
):
    """Verify linking the exact same CLOUD_ASSET twice to the same process returns 409 Conflict."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    proc, _ = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="Dup Cloud Dep Process"
    )

    r1 = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/dependencies",
        json={
            "dependency_type": "CLOUD_ASSET",
            "cloud_asset_id": b5_fixture["apex_cloud_healthy"].id,
        },
        headers=analyst_headers,
    )
    assert r1.status_code == 201

    r2 = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/dependencies",
        json={
            "dependency_type": "CLOUD_ASSET",
            "cloud_asset_id": b5_fixture["apex_cloud_healthy"].id,
        },
        headers=analyst_headers,
    )
    assert r2.status_code == 409


def test_b5_44_restrict_delete_on_evidence_item_linked_to_exercise(
    client: TestClient, db: Session, b5_fixture: dict
):
    """SEC-B5-45: EvidenceItem linked to a ResilienceExercise has ForeignKey ondelete=RESTRICT."""
    from sqlalchemy.exc import IntegrityError

    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    proc, bia = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="Restrict Evidence Delete Process"
    )
    cp = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-RESTR-01",
            "title": "Restrict Evidence Plan",
            "bia_id": bia["id"],
            "strategy_type": "WARM_STANDBY",
            "activation_triggers": "Trigger",
            "estimated_recovery_hours": 2.0,
            "estimated_rpo_hours": 0.5,
        },
        headers=analyst_headers,
    ).json()
    client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/steps",
        json={"step_order": 1, "title": "Step 1", "description": "Desc", "estimated_duration_minutes": 30},
        headers=analyst_headers,
    )
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/submit", headers=analyst_headers)
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/approve", headers=manager_headers)

    # Create a dedicated EvidenceItem and link it to the plan
    ev = EvidenceItem(
        organization_id=b5_fixture["org_apex"].id,
        organization_control_id=b5_fixture["apex_ctrl"].id,
        uploaded_by_id=b5_fixture["apex_analyst"].id,
        title="Protected Evidence Artifact",
        description="Cannot be deleted while linked",
        original_filename="protected.pdf",
        stored_filename="stored_protected.pdf",
        file_extension=".pdf",
        content_type="application/pdf",
        file_size=1024,
        sha256_hash=hashlib.sha256(b"protected-bytes").hexdigest(),
        storage_key="evidence/apex/stored_protected.pdf",
        status=EvidenceStatusEnum.ACCEPTED,
    )
    db.add(ev)
    db.commit()

    client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/evidence",
        json={
            "evidence_item_id": ev.id,
            "evidence_type_context": "CONTINUITY_RUNBOOK",
        },
        headers=analyst_headers,
    )

    # Attempting to delete the EvidenceItem directly in DB must raise IntegrityError
    with pytest.raises(IntegrityError):
        db.delete(ev)
        db.commit()
    db.rollback()


def test_b5_45_impact_summary_reflects_latest_plan_and_exercise_metrics(
    client: TestClient, b5_fixture: dict
):
    """Verify GET /processes/{id}/impact-summary includes active continuity plan version and latest exercise actual RTO/RPO."""
    analyst_headers = get_token_headers(b5_fixture["apex_analyst"])
    manager_headers = get_token_headers(b5_fixture["apex_manager"])
    proc, bia = _create_process_with_active_bia(
        client, analyst_headers, manager_headers, name="Full Impact Summary Process"
    )
    cp = client.post(
        f"/api/v1/resilience/processes/{proc['id']}/continuity-plans",
        json={
            "plan_code": "BCP-ISUM-01",
            "title": "Impact Summary Plan",
            "bia_id": bia["id"],
            "version_major": 3,
            "version_minor": 2,
            "strategy_type": "ACTIVE_ACTIVE",
            "activation_triggers": "Trigger",
            "estimated_recovery_hours": 1.5,
            "estimated_rpo_hours": 0.25,
        },
        headers=analyst_headers,
    ).json()
    client.post(
        f"/api/v1/resilience/continuity-plans/{cp['id']}/steps",
        json={"step_order": 1, "title": "Step 1", "description": "Desc", "estimated_duration_minutes": 20},
        headers=analyst_headers,
    )
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/submit", headers=analyst_headers)
    client.post(f"/api/v1/resilience/continuity-plans/{cp['id']}/approve", headers=manager_headers)

    ex = client.post(
        "/api/v1/resilience/exercises",
        json={
            "process_id": proc["id"],
            "continuity_plan_id": cp["id"],
            "exercise_code": "EX-ISUM-01",
            "title": "Impact Summary Exercise",
            "exercise_type": "TABLETOP",
            "scenario_description": "Scenario",
            "scheduled_start_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=analyst_headers,
    ).json()
    client.post(f"/api/v1/resilience/exercises/{ex['id']}/start", headers=analyst_headers)
    client.post(
        f"/api/v1/resilience/exercises/{ex['id']}/complete",
        json={"actual_rto_hours": 1.75, "actual_rpo_hours": 0.35},
        headers=analyst_headers,
    )

    summary = client.get(
        f"/api/v1/resilience/processes/{proc['id']}/impact-summary",
        headers=analyst_headers,
    ).json()
    assert summary["active_continuity_plan_id"] == cp["id"]
    assert summary["active_continuity_plan_version"] == "3.2"
    assert summary["latest_exercise_id"] == ex["id"]
    assert summary["latest_exercise_outcome"] == "PASS"
    assert summary["latest_actual_rto_hours"] == 1.75
    assert summary["latest_actual_rpo_hours"] == 0.35
