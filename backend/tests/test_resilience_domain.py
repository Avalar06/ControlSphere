import pytest
from fastapi import HTTPException

from app.models.control import OrganizationControl, ImplementationStatusEnum, PriorityEnum
from app.models.framework import Framework, FrameworkFunction, FrameworkCategory, FrameworkSubcategory
from app.models.organization import Organization
from app.models.resilience import (
    BiaStatusEnum,
    BusinessImpactAnalysis,
    BusinessProcess,
    CriticalityTierEnum,
    DependencyTypeEnum,
    ProcessDependency,
)
from app.models.tprm import Vendor, VendorStatusEnum, VendorTierEnum
from app.models.user import User
from app.schemas.resilience import (
    BusinessImpactAnalysisBase,
    BusinessImpactAnalysisCreate,
    BusinessProcessCreate,
    BusinessProcessUpdate,
    ProcessDependencyCreate,
)
from app.services.resilience_service import (
    ResilienceService,
    calculate_projected_outage_loss,
)


@pytest.fixture
def resilience_fixture(db):
    """Setup multi-tenant test fixtures for Phase 13 domain verification."""
    org1 = Organization(name="Resilience Apex Corp", slug="apex-resilience-1")
    org2 = Organization(name="Resilience Meridian Ltd", slug="meridian-resilience-2")
    db.add_all([org1, org2])
    db.commit()

    analyst1 = User(
        organization_id=org1.id,
        email="analyst@apex.com",
        hashed_password="hash",
        full_name="Apex BCM Analyst",
        role="GRC_ANALYST",
        is_active=True,
    )
    manager1 = User(
        organization_id=org1.id,
        email="manager@apex.com",
        hashed_password="hash",
        full_name="Apex Resilience Manager",
        role="MANAGER",
        is_active=True,
    )
    foreign_user = User(
        organization_id=org2.id,
        email="user@meridian.com",
        hashed_password="hash",
        full_name="Meridian User",
        role="MANAGER",
        is_active=True,
    )
    db.add_all([analyst1, manager1, foreign_user])
    db.commit()

    # Framework & Control in org1
    fw = Framework(identifier="ISO22301", name="ISO 22301:2019", description="BCMS")
    db.add(fw)
    db.commit()

    fn = FrameworkFunction(framework_id=fw.id, identifier="BC", name="Business Continuity")
    db.add(fn)
    db.commit()

    cat = FrameworkCategory(function_id=fn.id, identifier="BC.OP", name="Operational Planning")
    db.add(cat)
    db.commit()

    sub = FrameworkSubcategory(
        category_id=cat.id,
        identifier="BC.OP.1",
        title="BIA & Risk Strategy",
        description="Continuity requirements and BIA operational guidelines",
    )
    db.add(sub)
    db.commit()

    ctrl1 = OrganizationControl(
        organization_id=org1.id,
        subcategory_id=sub.id,
        status=ImplementationStatusEnum.IMPLEMENTED,
        priority=PriorityEnum.CRITICAL,
        implementation_statement="Daily backups replicated to secondary zone",
        notes="Automated snapshotting and replication control",
    )
    db.add(ctrl1)

    # Vendor in org1 & org2
    vendor1 = Vendor(
        organization_id=org1.id,
        legal_name="Apex Cloud Infrastructure",
        vendor_code="VND-APEX-01",
        calculated_tier=VendorTierEnum.TIER_1_CRITICAL,
        vendor_status=VendorStatusEnum.ACTIVE,
    )
    vendor_foreign = Vendor(
        organization_id=org2.id,
        legal_name="Meridian SaaS Provider",
        vendor_code="VND-MER-01",
        calculated_tier=VendorTierEnum.TIER_1_CRITICAL,
        vendor_status=VendorStatusEnum.ACTIVE,
    )
    db.add_all([vendor1, vendor_foreign])
    db.commit()

    return {
        "org1": org1,
        "org2": org2,
        "analyst1": analyst1,
        "manager1": manager1,
        "foreign_user": foreign_user,
        "control1": ctrl1,
        "vendor1": vendor1,
        "vendor_foreign": vendor_foreign,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1. DETERMINISTIC CALCULATION ENGINE TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_calculate_projected_outage_loss_standard():
    res = calculate_projected_outage_loss(
        duration_hours=6.5,
        hourly_downtime_cost=15000.0,
        fixed_outage_cost=5000.0,
    )
    assert res["duration_hours"] == 6.5
    assert res["fixed_outage_cost"] == 5000.0
    assert res["hourly_downtime_cost"] == 15000.0
    assert res["variable_outage_cost"] == 97500.0
    assert res["total_projected_loss"] == 102500.0


def test_calculate_projected_outage_loss_zero_duration():
    res = calculate_projected_outage_loss(
        duration_hours=0.0,
        hourly_downtime_cost=20000.0,
        fixed_outage_cost=10000.0,
    )
    assert res["variable_outage_cost"] == 0.0
    assert res["total_projected_loss"] == 10000.0


def test_calculate_projected_outage_loss_zero_fixed_cost():
    res = calculate_projected_outage_loss(
        duration_hours=4.0,
        hourly_downtime_cost=12500.0,
        fixed_outage_cost=0.0,
    )
    assert res["fixed_outage_cost"] == 0.0
    assert res["variable_outage_cost"] == 50000.0
    assert res["total_projected_loss"] == 50000.0


def test_calculate_projected_outage_loss_negative_validation():
    with pytest.raises(ValueError, match="non-negative"):
        calculate_projected_outage_loss(-1.0, 1000.0, 500.0)

    with pytest.raises(ValueError, match="non-negative"):
        calculate_projected_outage_loss(5.0, -1000.0, 500.0)

    with pytest.raises(ValueError, match="non-negative"):
        calculate_projected_outage_loss(5.0, 1000.0, -500.0)


# ─────────────────────────────────────────────────────────────────────────────
# 2. BUSINESS PROCESS CATALOG TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_create_business_process_success(db, resilience_fixture):
    fix = resilience_fixture
    payload = BusinessProcessCreate(
        name="Global Payment Processing",
        description="Core financial gateway processing real-time credit card transactions",
        criticality_tier=CriticalityTierEnum.TIER_1,
    )
    proc = ResilienceService.create_business_process(
        db=db,
        organization_id=fix["org1"].id,
        data=payload,
        user_id=fix["analyst1"].id,
    )
    assert proc.id is not None
    assert proc.name == "Global Payment Processing"
    assert proc.criticality_tier == CriticalityTierEnum.TIER_1
    assert proc.owner_id == fix["analyst1"].id
    assert proc.organization_id == fix["org1"].id


def test_create_business_process_duplicate_name_rejected(db, resilience_fixture):
    fix = resilience_fixture
    payload = BusinessProcessCreate(
        name="Order Fulfillment Pipeline",
        description="Warehouse dispatch",
        criticality_tier=CriticalityTierEnum.TIER_2,
    )
    ResilienceService.create_business_process(
        db=db,
        organization_id=fix["org1"].id,
        data=payload,
        user_id=fix["analyst1"].id,
    )

    # Attempt duplicate in same tenant
    with pytest.raises(HTTPException) as exc_info:
        ResilienceService.create_business_process(
            db=db,
            organization_id=fix["org1"].id,
            data=BusinessProcessCreate(name="  order fulfillment pipeline  "),
            user_id=fix["analyst1"].id,
        )
    assert exc_info.value.status_code == 409

    # Same name in different tenant allowed
    proc_org2 = ResilienceService.create_business_process(
        db=db,
        organization_id=fix["org2"].id,
        data=payload,
        user_id=fix["foreign_user"].id,
    )
    assert proc_org2.organization_id == fix["org2"].id


def test_update_business_process(db, resilience_fixture):
    fix = resilience_fixture
    proc = ResilienceService.create_business_process(
        db=db,
        organization_id=fix["org1"].id,
        data=BusinessProcessCreate(
            name="HR Onboarding Portal",
            description="Employee access provisioning",
            criticality_tier=CriticalityTierEnum.TIER_4,
        ),
        user_id=fix["analyst1"].id,
    )

    updated = ResilienceService.update_business_process(
        db=db,
        organization_id=fix["org1"].id,
        process_id=proc.id,
        data=BusinessProcessUpdate(
            description="Automated employee access and background checks",
            criticality_tier=CriticalityTierEnum.TIER_3,
        ),
        user_id=fix["manager1"].id,
    )
    assert updated.description == "Automated employee access and background checks"
    assert updated.criticality_tier == CriticalityTierEnum.TIER_3


def test_get_and_list_business_processes(db, resilience_fixture):
    fix = resilience_fixture
    p1 = ResilienceService.create_business_process(
        db=db,
        organization_id=fix["org1"].id,
        data=BusinessProcessCreate(name="Customer Auth Service", criticality_tier=CriticalityTierEnum.TIER_1),
        user_id=fix["analyst1"].id,
    )
    p2 = ResilienceService.create_business_process(
        db=db,
        organization_id=fix["org1"].id,
        data=BusinessProcessCreate(name="Marketing Campaign Analytics", criticality_tier=CriticalityTierEnum.TIER_4),
        user_id=fix["analyst1"].id,
    )

    retrieved = ResilienceService.get_business_process(db, fix["org1"].id, p1.id)
    assert retrieved.id == p1.id

    # Filter by tier
    tier1_list = ResilienceService.list_business_processes(
        db=db, organization_id=fix["org1"].id, criticality_tier=CriticalityTierEnum.TIER_1
    )
    assert len(tier1_list) >= 1
    assert all(p.criticality_tier == CriticalityTierEnum.TIER_1 for p in tier1_list)

    # Search
    search_list = ResilienceService.list_business_processes(
        db=db, organization_id=fix["org1"].id, search="Auth Service"
    )
    assert len(search_list) == 1
    assert search_list[0].id == p1.id


# ─────────────────────────────────────────────────────────────────────────────
# 3. BUSINESS IMPACT ANALYSIS (BIA) LIFECYCLE & GOVERNANCE TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_draft_bia_success_and_versioning(db, resilience_fixture):
    fix = resilience_fixture
    proc = ResilienceService.create_business_process(
        db=db,
        organization_id=fix["org1"].id,
        data=BusinessProcessCreate(name="ERP Inventory Sync", criticality_tier=CriticalityTierEnum.TIER_2),
        user_id=fix["analyst1"].id,
    )

    bia1 = ResilienceService.draft_bia(
        db=db,
        organization_id=fix["org1"].id,
        data=BusinessImpactAnalysisCreate(
            process_id=proc.id,
            rto_hours=4.0,
            rpo_hours=1.0,
            mtd_hours=12.0,
            hourly_downtime_cost=25000.0,
            fixed_outage_cost=10000.0,
            notes="Initial Q1 BIA baseline draft",
        ),
        user_id=fix["analyst1"].id,
    )
    assert bia1.id is not None
    assert bia1.version == 1
    assert bia1.status == BiaStatusEnum.DRAFT
    assert bia1.requested_by_id == fix["analyst1"].id

    # Draft version 2
    bia2 = ResilienceService.draft_bia(
        db=db,
        organization_id=fix["org1"].id,
        data=BusinessImpactAnalysisCreate(
            process_id=proc.id,
            rto_hours=2.0,
            rpo_hours=0.5,
            mtd_hours=8.0,
            hourly_downtime_cost=30000.0,
            fixed_outage_cost=15000.0,
            notes="Q2 revised BIA tightening RTO",
        ),
        user_id=fix["analyst1"].id,
    )
    assert bia2.version == 2
    assert bia2.status == BiaStatusEnum.DRAFT


def test_bia_validation_rto_exceeding_mtd_rejected(db, resilience_fixture):
    fix = resilience_fixture
    proc = ResilienceService.create_business_process(
        db=db,
        organization_id=fix["org1"].id,
        data=BusinessProcessCreate(name="Payroll Batch Generator"),
        user_id=fix["analyst1"].id,
    )

    # Pydantic schema validation
    with pytest.raises(ValueError, match="cannot exceed Maximum Tolerable Downtime"):
        BusinessImpactAnalysisCreate(
            process_id=proc.id,
            rto_hours=48.0,
            rpo_hours=2.0,
            mtd_hours=24.0,  # Invalid: RTO > MTD
        )


def test_four_eyes_approval_self_approval_rejected(db, resilience_fixture):
    fix = resilience_fixture
    proc = ResilienceService.create_business_process(
        db=db,
        organization_id=fix["org1"].id,
        data=BusinessProcessCreate(name="Claims Settlement Engine"),
        user_id=fix["analyst1"].id,
    )

    bia = ResilienceService.draft_bia(
        db=db,
        organization_id=fix["org1"].id,
        data=BusinessImpactAnalysisCreate(
            process_id=proc.id,
            rto_hours=6.0,
            mtd_hours=24.0,
            hourly_downtime_cost=10000.0,
        ),
        user_id=fix["analyst1"].id,
    )

    # Requester attempting to approve own BIA -> 403 Forbidden
    with pytest.raises(HTTPException) as exc_info:
        ResilienceService.approve_bia(
            db=db,
            organization_id=fix["org1"].id,
            bia_id=bia.id,
            user_id=fix["analyst1"].id,  # Self approval
        )
    assert exc_info.value.status_code == 403
    assert "Four-eyes governance violation" in str(exc_info.value.detail)


def test_four_eyes_approval_success_and_atomic_superseding(db, resilience_fixture):
    fix = resilience_fixture
    proc = ResilienceService.create_business_process(
        db=db,
        organization_id=fix["org1"].id,
        data=BusinessProcessCreate(name="E-Commerce Storefront"),
        user_id=fix["analyst1"].id,
    )

    # V1 Draft and Approval
    v1_draft = ResilienceService.draft_bia(
        db=db,
        organization_id=fix["org1"].id,
        data=BusinessImpactAnalysisCreate(
            process_id=proc.id,
            rto_hours=4.0,
            mtd_hours=12.0,
            hourly_downtime_cost=50000.0,
        ),
        user_id=fix["analyst1"].id,
    )
    v1_approved = ResilienceService.approve_bia(
        db=db,
        organization_id=fix["org1"].id,
        bia_id=v1_draft.id,
        user_id=fix["manager1"].id,
        notes="Approved for Production Operations",
    )
    assert v1_approved.status == BiaStatusEnum.ACTIVE
    assert v1_approved.approved_by_id == fix["manager1"].id
    assert v1_approved.approved_at is not None

    # V2 Draft and Approval by manager
    v2_draft = ResilienceService.draft_bia(
        db=db,
        organization_id=fix["org1"].id,
        data=BusinessImpactAnalysisCreate(
            process_id=proc.id,
            rto_hours=2.0,
            mtd_hours=8.0,
            hourly_downtime_cost=75000.0,
        ),
        user_id=fix["analyst1"].id,
    )
    v2_approved = ResilienceService.approve_bia(
        db=db,
        organization_id=fix["org1"].id,
        bia_id=v2_draft.id,
        user_id=fix["manager1"].id,
    )
    assert v2_approved.status == BiaStatusEnum.ACTIVE

    # Check V1 atomically transitioned to SUPERSEDED
    db.refresh(v1_approved)
    assert v1_approved.status == BiaStatusEnum.SUPERSEDED


def test_reapproving_active_or_superseded_rejected(db, resilience_fixture):
    fix = resilience_fixture
    proc = ResilienceService.create_business_process(
        db=db,
        organization_id=fix["org1"].id,
        data=BusinessProcessCreate(name="Credit Scoring Gateway"),
        user_id=fix["analyst1"].id,
    )
    draft = ResilienceService.draft_bia(
        db=db,
        organization_id=fix["org1"].id,
        data=BusinessImpactAnalysisCreate(process_id=proc.id),
        user_id=fix["analyst1"].id,
    )
    approved = ResilienceService.approve_bia(
        db=db,
        organization_id=fix["org1"].id,
        bia_id=draft.id,
        user_id=fix["manager1"].id,
    )

    with pytest.raises(HTTPException) as exc_info:
        ResilienceService.approve_bia(
            db=db,
            organization_id=fix["org1"].id,
            bia_id=approved.id,
            user_id=fix["manager1"].id,
        )
    assert exc_info.value.status_code == 409


def test_archive_draft_bia(db, resilience_fixture):
    fix = resilience_fixture
    proc = ResilienceService.create_business_process(
        db=db,
        organization_id=fix["org1"].id,
        data=BusinessProcessCreate(name="Vendor Invoice Ingestion"),
        user_id=fix["analyst1"].id,
    )
    draft = ResilienceService.draft_bia(
        db=db,
        organization_id=fix["org1"].id,
        data=BusinessImpactAnalysisCreate(process_id=proc.id),
        user_id=fix["analyst1"].id,
    )

    archived = ResilienceService.archive_draft_bia(
        db=db,
        organization_id=fix["org1"].id,
        bia_id=draft.id,
        user_id=fix["analyst1"].id,
    )
    assert archived.status == BiaStatusEnum.ARCHIVED

    # Attempting to archive active baseline rejected
    draft2 = ResilienceService.draft_bia(
        db=db,
        organization_id=fix["org1"].id,
        data=BusinessImpactAnalysisCreate(process_id=proc.id),
        user_id=fix["analyst1"].id,
    )
    active_bia = ResilienceService.approve_bia(
        db=db,
        organization_id=fix["org1"].id,
        bia_id=draft2.id,
        user_id=fix["manager1"].id,
    )
    with pytest.raises(HTTPException) as exc_info:
        ResilienceService.archive_draft_bia(
            db=db,
            organization_id=fix["org1"].id,
            bia_id=active_bia.id,
            user_id=fix["manager1"].id,
        )
    assert exc_info.value.status_code == 409


# ─────────────────────────────────────────────────────────────────────────────
# 4. CROSS-MODULE PROCESS DEPENDENCY TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_add_and_remove_vendor_dependency(db, resilience_fixture):
    fix = resilience_fixture
    proc = ResilienceService.create_business_process(
        db=db,
        organization_id=fix["org1"].id,
        data=BusinessProcessCreate(name="Production Workloads"),
        user_id=fix["analyst1"].id,
    )

    dep = ResilienceService.add_process_dependency(
        db=db,
        organization_id=fix["org1"].id,
        data=ProcessDependencyCreate(
            process_id=proc.id,
            dependency_type=DependencyTypeEnum.VENDOR,
            dependency_id=fix["vendor1"].id,
            notes="Critical cloud infrastructure provider hosting cluster",
        ),
        user_id=fix["analyst1"].id,
    )
    assert dep.id is not None
    assert dep.dependency_type == DependencyTypeEnum.VENDOR
    assert dep.dependency_id == fix["vendor1"].id

    # Duplicate dependency rejected
    with pytest.raises(HTTPException) as exc_info:
        ResilienceService.add_process_dependency(
            db=db,
            organization_id=fix["org1"].id,
            data=ProcessDependencyCreate(
                process_id=proc.id,
                dependency_type=DependencyTypeEnum.VENDOR,
                dependency_id=fix["vendor1"].id,
            ),
            user_id=fix["analyst1"].id,
        )
    assert exc_info.value.status_code == 409

    # Remove dependency
    ResilienceService.remove_process_dependency(
        db=db,
        organization_id=fix["org1"].id,
        dependency_id=dep.id,
        user_id=fix["analyst1"].id,
    )
    check_dep = db.query(ProcessDependency).filter(ProcessDependency.id == dep.id).first()
    assert check_dep is None


def test_add_control_dependency(db, resilience_fixture):
    fix = resilience_fixture
    proc = ResilienceService.create_business_process(
        db=db,
        organization_id=fix["org1"].id,
        data=BusinessProcessCreate(name="Database Cluster"),
        user_id=fix["analyst1"].id,
    )

    dep = ResilienceService.add_process_dependency(
        db=db,
        organization_id=fix["org1"].id,
        data=ProcessDependencyCreate(
            process_id=proc.id,
            dependency_type=DependencyTypeEnum.CONTROL,
            dependency_id=fix["control1"].id,
            notes="Automated snapshotting and replication control",
        ),
        user_id=fix["analyst1"].id,
    )
    assert dep.dependency_type == DependencyTypeEnum.CONTROL
    assert dep.dependency_id == fix["control1"].id


def test_foreign_vendor_dependency_rejected(db, resilience_fixture):
    fix = resilience_fixture
    proc = ResilienceService.create_business_process(
        db=db,
        organization_id=fix["org1"].id,
        data=BusinessProcessCreate(name="Apex Web Portal"),
        user_id=fix["analyst1"].id,
    )

    # Foreign vendor from org2
    with pytest.raises(HTTPException) as exc_info:
        ResilienceService.add_process_dependency(
            db=db,
            organization_id=fix["org1"].id,
            data=ProcessDependencyCreate(
                process_id=proc.id,
                dependency_type=DependencyTypeEnum.VENDOR,
                dependency_id=fix["vendor_foreign"].id,
            ),
            user_id=fix["analyst1"].id,
        )
    assert exc_info.value.status_code == 404
    assert "not found in tenant organization" in str(exc_info.value.detail)


# ─────────────────────────────────────────────────────────────────────────────
# 5. MULTI-TENANT ISOLATION & SECURITY TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_cross_tenant_process_access_rejected(db, resilience_fixture):
    fix = resilience_fixture
    proc_org1 = ResilienceService.create_business_process(
        db=db,
        organization_id=fix["org1"].id,
        data=BusinessProcessCreate(name="Apex Secret Process"),
        user_id=fix["analyst1"].id,
    )

    # Foreign org2 user attempts to read org1 process
    with pytest.raises(HTTPException) as exc_info:
        ResilienceService.get_business_process(
            db=db,
            organization_id=fix["org2"].id,  # Foreign tenant
            process_id=proc_org1.id,
        )
    assert exc_info.value.status_code == 404


def test_cross_tenant_draft_bia_rejected(db, resilience_fixture):
    fix = resilience_fixture
    proc_org1 = ResilienceService.create_business_process(
        db=db,
        organization_id=fix["org1"].id,
        data=BusinessProcessCreate(name="Apex Protected Workflow"),
        user_id=fix["analyst1"].id,
    )

    # Foreign org2 user attempts to draft BIA for org1 process
    with pytest.raises(HTTPException) as exc_info:
        ResilienceService.draft_bia(
            db=db,
            organization_id=fix["org2"].id,
            data=BusinessImpactAnalysisCreate(process_id=proc_org1.id),
            user_id=fix["foreign_user"].id,
        )
    assert exc_info.value.status_code == 404


def test_cross_tenant_approve_bia_rejected(db, resilience_fixture):
    fix = resilience_fixture
    proc_org1 = ResilienceService.create_business_process(
        db=db,
        organization_id=fix["org1"].id,
        data=BusinessProcessCreate(name="Apex Sensitive Function"),
        user_id=fix["analyst1"].id,
    )
    draft_org1 = ResilienceService.draft_bia(
        db=db,
        organization_id=fix["org1"].id,
        data=BusinessImpactAnalysisCreate(process_id=proc_org1.id),
        user_id=fix["analyst1"].id,
    )

    # Foreign org2 manager attempts to approve org1 BIA
    with pytest.raises(HTTPException) as exc_info:
        ResilienceService.approve_bia(
            db=db,
            organization_id=fix["org2"].id,
            bia_id=draft_org1.id,
            user_id=fix["foreign_user"].id,
        )
    assert exc_info.value.status_code == 404


def test_list_process_bias(db, resilience_fixture):
    fix = resilience_fixture
    proc = ResilienceService.create_business_process(
        db=db,
        organization_id=fix["org1"].id,
        data=BusinessProcessCreate(name="BIA Listing Workflow"),
        user_id=fix["analyst1"].id,
    )
    b1 = ResilienceService.draft_bia(
        db=db,
        organization_id=fix["org1"].id,
        data=BusinessImpactAnalysisCreate(process_id=proc.id, rto_hours=6.0, mtd_hours=12.0),
        user_id=fix["analyst1"].id,
    )
    b2 = ResilienceService.draft_bia(
        db=db,
        organization_id=fix["org1"].id,
        data=BusinessImpactAnalysisCreate(process_id=proc.id, rto_hours=4.0, mtd_hours=8.0),
        user_id=fix["analyst1"].id,
    )

    bias = ResilienceService.list_process_bias(db=db, organization_id=fix["org1"].id, process_id=proc.id)
    assert len(bias) == 2
    assert bias[0].version == 2
    assert bias[1].version == 1


def test_bia_zero_cost_edge_case(db, resilience_fixture):
    fix = resilience_fixture
    proc = ResilienceService.create_business_process(
        db=db,
        organization_id=fix["org1"].id,
        data=BusinessProcessCreate(name="Internal Wiki Documentation"),
        user_id=fix["analyst1"].id,
    )
    bia = ResilienceService.draft_bia(
        db=db,
        organization_id=fix["org1"].id,
        data=BusinessImpactAnalysisCreate(
            process_id=proc.id,
            rto_hours=72.0,
            rpo_hours=24.0,
            mtd_hours=168.0,
            hourly_downtime_cost=0.0,
            fixed_outage_cost=0.0,
            notes="Zero direct monetary loss for non-critical internal wiki",
        ),
        user_id=fix["analyst1"].id,
    )
    assert bia.hourly_downtime_cost == 0.0
    assert bia.fixed_outage_cost == 0.0


def test_audit_event_generation_on_resilience_operations(db, resilience_fixture):
    from app.models.audit_log import AuditLog

    fix = resilience_fixture
    proc = ResilienceService.create_business_process(
        db=db,
        organization_id=fix["org1"].id,
        data=BusinessProcessCreate(name="Audit Logging Test Process"),
        user_id=fix["analyst1"].id,
    )

    bia = ResilienceService.draft_bia(
        db=db,
        organization_id=fix["org1"].id,
        data=BusinessImpactAnalysisCreate(process_id=proc.id),
        user_id=fix["analyst1"].id,
    )

    ResilienceService.approve_bia(
        db=db,
        organization_id=fix["org1"].id,
        bia_id=bia.id,
        user_id=fix["manager1"].id,
    )

    dep = ResilienceService.add_process_dependency(
        db=db,
        organization_id=fix["org1"].id,
        data=ProcessDependencyCreate(
            process_id=proc.id,
            dependency_type=DependencyTypeEnum.VENDOR,
            dependency_id=fix["vendor1"].id,
        ),
        user_id=fix["analyst1"].id,
    )

    ResilienceService.remove_process_dependency(
        db=db,
        organization_id=fix["org1"].id,
        dependency_id=dep.id,
        user_id=fix["analyst1"].id,
    )

    # Verify audit log entries
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.organization_id == fix["org1"].id)
        .all()
    )
    actions = [log.action for log in logs]
    assert "BUSINESS_PROCESS_CREATED" in actions
    assert "BIA_DRAFTED" in actions
    assert "BIA_APPROVED" in actions
    assert "PROCESS_DEPENDENCY_ADDED" in actions
    assert "PROCESS_DEPENDENCY_REMOVED" in actions


def test_remove_nonexistent_and_cross_tenant_dependency(db, resilience_fixture):
    fix = resilience_fixture
    proc = ResilienceService.create_business_process(
        db=db,
        organization_id=fix["org1"].id,
        data=BusinessProcessCreate(name="Security Monitoring Pipeline"),
        user_id=fix["analyst1"].id,
    )
    dep = ResilienceService.add_process_dependency(
        db=db,
        organization_id=fix["org1"].id,
        data=ProcessDependencyCreate(
            process_id=proc.id,
            dependency_type=DependencyTypeEnum.CONTROL,
            dependency_id=fix["control1"].id,
        ),
        user_id=fix["analyst1"].id,
    )

    # Nonexistent dependency ID
    with pytest.raises(HTTPException) as exc_info:
        ResilienceService.remove_process_dependency(
            db=db,
            organization_id=fix["org1"].id,
            dependency_id=999999,
            user_id=fix["analyst1"].id,
        )
    assert exc_info.value.status_code == 404

    # Foreign tenant attempting to remove dependency
    with pytest.raises(HTTPException) as exc_info:
        ResilienceService.remove_process_dependency(
            db=db,
            organization_id=fix["org2"].id,
            dependency_id=dep.id,
            user_id=fix["foreign_user"].id,
        )
    assert exc_info.value.status_code == 404


def test_outage_cost_calculation_schemas():
    from app.schemas.resilience import OutageCostCalculationRequest, OutageCostCalculationResult

    req = OutageCostCalculationRequest(
        duration_hours=12.0,
        hourly_downtime_cost=8000.0,
        fixed_outage_cost=2500.0,
    )
    raw = calculate_projected_outage_loss(
        duration_hours=req.duration_hours,
        hourly_downtime_cost=req.hourly_downtime_cost,
        fixed_outage_cost=req.fixed_outage_cost,
    )
    res = OutageCostCalculationResult(**raw)
    assert res.duration_hours == 12.0
    assert res.fixed_outage_cost == 2500.0
    assert res.hourly_downtime_cost == 8000.0
    assert res.variable_outage_cost == 96000.0
    assert res.total_projected_loss == 98500.0
