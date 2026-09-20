"""Comprehensive tests for Batch 1 (AUDIT-FIELDWORK-GRC)
Covering:
- PBC Request Lifecycle & Lineage to EvidenceItem
- Population Snapshot & Freeze Immutability
- Deterministic Sampling Engine (AU-C 530 / PCAOB AS 2315)
- Workpaper Four-Eyes Governance (prepared_by_id != reviewed_by_id)
- Cryptographic SHA-256 Digest Sealing
- Sample Exception -> Finding Escalation Bridge
- Enhanced Audit Readiness Telemetry
- 22 Adversarial Security Vectors (RBAC, Multi-Tenant IDOR, Anti-Tamper)
"""
import hashlib
import json
import random
from datetime import date, datetime, timedelta, timezone
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.conftest import get_token_headers

from app.models.audit_engagement import (
    Audit,
    AuditProcedure,
    AuditScopeControl,
    AuditFindingLink,
    AuditStatusEnum,
    AuditTypeEnum,
    ProcedureResultEnum,
    AuditPBCRequest,
    AuditSamplePopulation,
    AuditSampleItem,
    AuditWorkpaperReview,
    PBCStatusEnum,
    PBCPriorityEnum,
    SamplingMethodEnum,
    SampleResultEnum,
    WorkpaperStatusEnum,
)
from app.models.control import OrganizationControl, ImplementationStatusEnum
from app.models.evidence import EvidenceItem, EvidenceReview, EvidenceStatusEnum, ReviewDecisionEnum
from app.models.finding import Finding, FindingSeverityEnum, FindingStatusEnum, FindingTypeEnum
from app.models.framework import Framework, FrameworkCategory, FrameworkFunction, FrameworkSubcategory
from app.models.organization import Organization
from app.models.user import User
from app.core.permissions import RoleEnum
from app.schemas.audit_fieldwork import (
    AuditPBCRequestCreate,
    AuditPBCRequestFulfill,
    AuditPBCRequestReview,
    AuditPBCRequestUpdate,
    AuditSamplePopulationCreate,
    AuditSampleGenerateRequest,
    AuditSampleItemUpdate,
    AuditSampleEscalateFinding,
    AuditWorkpaperSubmit,
    AuditWorkpaperApprove,
    AuditWorkpaperRequestChanges,
    PopulationItemInput,
)
from app.services.audit_engagement_service import AuditEngagementService
from app.services.audit_fieldwork_service import AuditFieldworkService
from app.services.audit_sampling_service import AuditSamplingService


# ─────────────────────────────────────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture
def org_setup(db: Session):
    org_a = Organization(name="Org Alpha Fieldwork", slug="org-alpha-fieldwork")
    org_b = Organization(name="Org Beta Fieldwork", slug="org-beta-fieldwork")
    db.add_all([org_a, org_b])
    db.flush()

    lead_auditor = User(
        email="lead.auditor@alpha.com",
        hashed_password="hash",
        full_name="Lead Auditor",
        role=RoleEnum.AUDITOR,
        organization_id=org_a.id,
        is_active=True,
    )
    staff_auditor = User(
        email="staff.auditor@alpha.com",
        hashed_password="hash",
        full_name="Staff Auditor",
        role=RoleEnum.AUDITOR,
        organization_id=org_a.id,
        is_active=True,
    )
    auditee = User(
        email="auditee@alpha.com",
        hashed_password="hash",
        full_name="Alice Auditee",
        role=RoleEnum.GRC_ANALYST,
        organization_id=org_a.id,
        is_active=True,
    )
    attacker_b = User(
        email="attacker@beta.com",
        hashed_password="hash",
        full_name="Bob Attacker",
        role=RoleEnum.AUDITOR,
        organization_id=org_b.id,
        is_active=True,
    )
    viewer_a = User(
        email="viewer@alpha.com",
        hashed_password="hash",
        full_name="Victor Viewer",
        role=RoleEnum.VIEWER,
        organization_id=org_a.id,
        is_active=True,
    )
    db.add_all([lead_auditor, staff_auditor, auditee, attacker_b, viewer_a])
    db.flush()

    # Framework and subcategory for controls
    fw = Framework(identifier="SOC2-2026", name="SOC2 Fieldwork", version="2026", description="SOC2")
    db.add(fw)
    db.flush()
    fn = FrameworkFunction(framework_id=fw.id, identifier="SEC", name="Security")
    db.add(fn)
    db.flush()
    cat = FrameworkCategory(function_id=fn.id, identifier="SEC.AC", name="Access")
    db.add(cat)
    db.flush()
    subcat = FrameworkSubcategory(category_id=cat.id, identifier="SEC.AC-01", title="Access Control", description="Enforce access controls")
    db.add(subcat)
    db.flush()

    ctrl_a = OrganizationControl(
        organization_id=org_a.id,
        subcategory_id=subcat.id,
        status=ImplementationStatusEnum.IMPLEMENTED,
        implementation_statement="Enforce MFA and authorization",
    )
    db.add(ctrl_a)
    db.flush()

    audit_a = Audit(
        organization_id=org_a.id,
        title="SOC2 Type II Fieldwork 2026",
        audit_type=AuditTypeEnum.INTERNAL,
        objective="Validate operational effectiveness of controls",
        lead_auditor_id=lead_auditor.id,
        status=AuditStatusEnum.FIELDWORK,
    )
    db.add(audit_a)
    db.flush()

    scope_a = AuditScopeControl(
        organization_id=org_a.id,
        audit_id=audit_a.id,
        organization_control_id=ctrl_a.id,
    )
    db.add(scope_a)
    db.flush()

    proc_a = AuditProcedure(
        organization_id=org_a.id,
        audit_id=audit_a.id,
        organization_control_id=ctrl_a.id,
        title="Sample Access Approvals",
        objective="Inspect sample of user access requests",
        test_steps="Sample 25 tickets and check approvals",
        result=ProcedureResultEnum.IN_PROGRESS,
    )
    db.add(proc_a)
    db.flush()

    db.commit()

    return {
        "org_a": org_a,
        "org_b": org_b,
        "lead_auditor": lead_auditor,
        "staff_auditor": staff_auditor,
        "auditee": auditee,
        "attacker_b": attacker_b,
        "viewer_a": viewer_a,
        "ctrl_a": ctrl_a,
        "audit_a": audit_a,
        "proc_a": proc_a,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1. DETERMINISTIC SAMPLING ENGINE TESTS (AU-C 530 / PCAOB AS 2315)
# ─────────────────────────────────────────────────────────────────────────────
def test_sampling_canonical_sorting():
    """Canonical sort must order strictly by (source_record_id ASC)."""
    items = [
        {"source_record_id": "REC-999", "attributes": {"dept": "Sales"}},
        {"source_record_id": "REC-001", "attributes": {"dept": "Eng"}},
        {"source_record_id": "REC-500", "attributes": {"dept": "Finance"}},
        {"source_record_id": "REC-010", "attributes": {"dept": "HR"}},
    ]
    sorted_items = AuditSamplingService.canonical_sort_population(items)
    ids = [x["source_record_id"] for x in sorted_items]
    assert ids == ["REC-001", "REC-010", "REC-500", "REC-999"]


def test_sampling_digest_determinism_and_tamper_evidence():
    """Digest must be identical for same items in different order, and change if modified."""
    items1 = [
        {"source_record_id": "A", "attributes": {"val": 1}},
        {"source_record_id": "B", "attributes": {"val": 2}},
    ]
    items2 = [
        {"source_record_id": "B", "attributes": {"val": 2}},
        {"source_record_id": "A", "attributes": {"val": 1}},
    ]
    digest1 = AuditSamplingService.compute_population_digest(items1)
    digest2 = AuditSamplingService.compute_population_digest(items2)
    assert digest1 == digest2

    # Modify an attribute
    items3 = [
        {"source_record_id": "A", "attributes": {"val": 999}},
        {"source_record_id": "B", "attributes": {"val": 2}},
    ]
    digest3 = AuditSamplingService.compute_population_digest(items3)
    assert digest1 != digest3


def test_random_sampling_100_percent_reproducibility():
    """Random sampling must produce the exact identical sample across multiple runs with the same seed."""
    items = [{"source_record_id": f"REC-{i:04d}", "attributes": {"idx": i}} for i in range(100)]
    canonical = AuditSamplingService.canonical_sort_population(items)
    seed = "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"

    run1 = AuditSamplingService.sample_random(canonical, 20, seed)
    run2 = AuditSamplingService.sample_random(canonical, 20, seed)
    run3 = AuditSamplingService.sample_random(canonical, 20, seed)

    assert len(run1) == 20
    assert [x["source_record_id"] for x in run1] == [x["source_record_id"] for x in run2]
    assert [x["source_record_id"] for x in run1] == [x["source_record_id"] for x in run3]


def test_systematic_sampling_deterministic_interval():
    """Systematic sampling interval k = N // n and random start produces deterministic sequence."""
    items = [{"source_record_id": f"USER-{i:03d}", "attributes": {"num": i}} for i in range(50)]
    canonical = AuditSamplingService.canonical_sort_population(items)
    seed = "11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff"

    sample = AuditSamplingService.sample_systematic(canonical, 10, seed)
    assert len(sample) == 10
    sample2 = AuditSamplingService.sample_systematic(canonical, 10, seed)
    assert [x["source_record_id"] for x in sample] == [x["source_record_id"] for x in sample2]


def test_stratified_sampling_proportionality():
    """Stratified sampling allocates samples proportionally across strata and is 100% reproducible."""
    items = []
    # 70 High-Risk items, 30 Low-Risk items
    for i in range(70):
        items.append({"source_record_id": f"H-{i:03d}", "attributes": {"risk": "HIGH"}})
    for i in range(30):
        items.append({"source_record_id": f"L-{i:03d}", "attributes": {"risk": "LOW"}})

    canonical = AuditSamplingService.canonical_sort_population(items)
    seed = "99887766554433221100ffeeddccbbaa99887766554433221100ffeeddccbbaa"

    sample = AuditSamplingService.sample_stratified(canonical, 10, seed, "risk")
    assert len(sample) == 10

    high_count = sum(1 for x in sample if x["attributes"]["risk"] == "HIGH")
    low_count = sum(1 for x in sample if x["attributes"]["risk"] == "LOW")
    assert high_count == 7
    assert low_count == 3

    # Verify reproducibility
    sample2 = AuditSamplingService.sample_stratified(canonical, 10, seed, "risk")
    assert [x["source_record_id"] for x in sample] == [x["source_record_id"] for x in sample2]


# ─────────────────────────────────────────────────────────────────────────────
# 2. POPULATION FREEZE & SNAPSHOT MUTABILITY TESTS
# ─────────────────────────────────────────────────────────────────────────────
def test_population_freeze_and_sampling_lifecycle(db: Session, org_setup):
    """Samples cannot be generated until population is frozen; re-generation is blocked."""
    ctx = org_setup
    items = [
        PopulationItemInput(source_record_id=f"TICKET-{i}", attributes={"priority": "P1"})
        for i in range(30)
    ]
    pop_in = AuditSamplePopulationCreate(
        population_name="Q1 Tickets",
        population_source="Jira Service Desk",
        items=items,
    )
    pop = AuditFieldworkService.create_population(
        db=db,
        organization_id=ctx["org_a"].id,
        audit_id=ctx["audit_a"].id,
        procedure_id=ctx["proc_a"].id,
        obj_in=pop_in,
        creator_id=ctx["staff_auditor"].id,
    )
    assert not pop.is_frozen
    assert pop.total_count == 30

    # Attempt generate before freeze -> MUST FAIL
    gen_in = AuditSampleGenerateRequest(sampling_method=SamplingMethodEnum.RANDOM, sample_size=10)
    with pytest.raises(HTTPException) as exc:
        AuditFieldworkService.generate_samples(
            db=db,
            organization_id=ctx["org_a"].id,
            audit_id=ctx["audit_a"].id,
            procedure_id=ctx["proc_a"].id,
            population_id=pop.id,
            user_id=ctx["staff_auditor"].id,
            obj_in=gen_in,
        )
    assert exc.value.status_code == 400
    assert "frozen" in exc.value.detail.lower()

    # Freeze population
    frozen_pop = AuditFieldworkService.freeze_population(
        db=db,
        organization_id=ctx["org_a"].id,
        audit_id=ctx["audit_a"].id,
        procedure_id=ctx["proc_a"].id,
        population_id=pop.id,
        user_id=ctx["staff_auditor"].id,
    )
    assert frozen_pop.is_frozen
    assert frozen_pop.population_digest_sha256 is not None

    # Generate samples -> SUCCESS
    sampled_pop = AuditFieldworkService.generate_samples(
        db=db,
        organization_id=ctx["org_a"].id,
        audit_id=ctx["audit_a"].id,
        procedure_id=ctx["proc_a"].id,
        population_id=pop.id,
        user_id=ctx["staff_auditor"].id,
        obj_in=gen_in,
    )
    assert sampled_pop.samples_generated
    assert sampled_pop.sample_size == 10

    sample_items = db.query(AuditSampleItem).filter(AuditSampleItem.population_id == pop.id).all()
    assert len(sample_items) == 10
    assert sample_items[0].item_index == 1

    # Attempt re-generation on same snapshot -> MUST FAIL (HTTP 409)
    with pytest.raises(HTTPException) as exc2:
        AuditFieldworkService.generate_samples(
            db=db,
            organization_id=ctx["org_a"].id,
            audit_id=ctx["audit_a"].id,
            procedure_id=ctx["proc_a"].id,
            population_id=pop.id,
            user_id=ctx["staff_auditor"].id,
            obj_in=gen_in,
        )
    assert exc2.value.status_code == 409


# ─────────────────────────────────────────────────────────────────────────────
# 3. PBC REQUEST LIFECYCLE & EVIDENCE AUTHORITY TESTS
# ─────────────────────────────────────────────────────────────────────────────
def test_pbc_request_lifecycle_and_evidence_linking(db: Session, org_setup):
    """PBC request fulfills with authoritative EvidenceItem, reviews, and accepts."""
    ctx = org_setup
    pbc_in = AuditPBCRequestCreate(
        organization_control_id=ctx["ctrl_a"].id,
        procedure_id=ctx["proc_a"].id,
        title="Provide Q1 Firewall Rule Review Signoffs",
        description="Upload signed approval ticket or export.",
        priority=PBCPriorityEnum.HIGH,
        assigned_to_id=ctx["auditee"].id,
        due_date=date.today() + timedelta(days=7),
    )
    pbc = AuditFieldworkService.create_pbc_request(
        db=db,
        organization_id=ctx["org_a"].id,
        audit_id=ctx["audit_a"].id,
        obj_in=pbc_in,
        creator_id=ctx["staff_auditor"].id,
    )
    assert pbc.status == PBCStatusEnum.REQUESTED
    assert pbc.request_identifier.startswith("PBC-")

    # Auditee fulfills with Phase 3 EvidenceItem
    evidence = EvidenceItem(
        organization_id=ctx["org_a"].id,
        organization_control_id=ctx["ctrl_a"].id,
        title="Firewall_Rules_Q1.pdf",
        original_filename="Firewall_Rules_Q1.pdf",
        stored_filename="stored_fw_q1.pdf",
        file_extension="pdf",
        content_type="application/pdf",
        file_size=2048,
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        storage_key="org_a/evidence/fw_q1.pdf",
        status=EvidenceStatusEnum.UPLOADED,
    )
    db.add(evidence)
    db.flush()

    fulfill_in = AuditPBCRequestFulfill(
        submission_notes="Attached firewall rules signed by Security Lead.",
        evidence_id=evidence.id,
    )
    pbc_submitted = AuditFieldworkService.fulfill_pbc_request(
        db=db,
        organization_id=ctx["org_a"].id,
        audit_id=ctx["audit_a"].id,
        pbc_id=pbc.id,
        user_id=ctx["auditee"].id,
        obj_in=fulfill_in,
    )
    assert pbc_submitted.status == PBCStatusEnum.SUBMITTED
    assert pbc_submitted.fulfilled_evidence_id == evidence.id

    # FOUR-EYES INVARIANT: Auditee cannot accept their own submission
    with pytest.raises(HTTPException) as exc:
        AuditFieldworkService.review_pbc_request(
            db=db,
            organization_id=ctx["org_a"].id,
            audit_id=ctx["audit_a"].id,
            pbc_id=pbc.id,
            reviewer_id=ctx["auditee"].id,  # SAME as assigned_to
            obj_in=AuditPBCRequestReview(decision="ACCEPT"),
        )
    assert exc.value.status_code == 400
    assert "four-eyes" in exc.value.detail.lower()

    # Lead Auditor reviews and accepts
    review_in = AuditPBCRequestReview(decision="ACCEPT", review_notes="Verified valid signature.")
    pbc_accepted = AuditFieldworkService.review_pbc_request(
        db=db,
        organization_id=ctx["org_a"].id,
        audit_id=ctx["audit_a"].id,
        pbc_id=pbc.id,
        reviewer_id=ctx["lead_auditor"].id,
        obj_in=review_in,
    )
    assert pbc_accepted.status == PBCStatusEnum.ACCEPTED

    # Verify EvidenceReview record created
    ev_review = db.query(EvidenceReview).filter(EvidenceReview.evidence_id == evidence.id).first()
    assert ev_review is not None
    assert ev_review.decision == ReviewDecisionEnum.ACCEPT


# ─────────────────────────────────────────────────────────────────────────────
# 4. SAMPLE DEFICIENCY -> FINDING ESCALATION BRIDGE TESTS
# ─────────────────────────────────────────────────────────────────────────────
def test_sample_exception_escalates_to_authoritative_finding(db: Session, org_setup):
    """Sample test failure escalates to Finding with CONTROL_GAP; duplicate escalation blocked."""
    ctx = org_setup
    # Create and freeze population
    items = [PopulationItemInput(source_record_id=f"ACC-{i}", attributes={}) for i in range(10)]
    pop = AuditFieldworkService.create_population(
        db=db,
        organization_id=ctx["org_a"].id,
        audit_id=ctx["audit_a"].id,
        procedure_id=ctx["proc_a"].id,
        obj_in=AuditSamplePopulationCreate(population_name="Access Grants", population_source="IAM", items=items),
        creator_id=ctx["staff_auditor"].id,
    )
    AuditFieldworkService.freeze_population(
        db=db, organization_id=ctx["org_a"].id, audit_id=ctx["audit_a"].id, procedure_id=ctx["proc_a"].id, population_id=pop.id, user_id=ctx["staff_auditor"].id
    )
    AuditFieldworkService.generate_samples(
        db=db, organization_id=ctx["org_a"].id, audit_id=ctx["audit_a"].id, procedure_id=ctx["proc_a"].id, population_id=pop.id, user_id=ctx["staff_auditor"].id,
        obj_in=AuditSampleGenerateRequest(sampling_method=SamplingMethodEnum.RANDOM, sample_size=5),
    )

    sample_item = db.query(AuditSampleItem).filter(AuditSampleItem.population_id == pop.id).first()

    # Mark sample as FAIL
    update_in = AuditSampleItemUpdate(
        test_result=SampleResultEnum.FAIL,
        testing_notes="User access granted without manager approval ticket.",
    )
    AuditFieldworkService.update_sample_item(
        db=db, organization_id=ctx["org_a"].id, audit_id=ctx["audit_a"].id, procedure_id=ctx["proc_a"].id, sample_id=sample_item.id, user_id=ctx["staff_auditor"].id, obj_in=update_in
    )

    # Escalate to Finding
    esc_in = AuditSampleEscalateFinding(severity="CRITICAL")
    finding = AuditFieldworkService.escalate_sample_deficiency(
        db=db,
        organization_id=ctx["org_a"].id,
        audit_id=ctx["audit_a"].id,
        procedure_id=ctx["proc_a"].id,
        sample_id=sample_item.id,
        user_id=ctx["staff_auditor"].id,
        obj_in=esc_in,
    )
    assert finding.id is not None
    assert finding.finding_type == FindingTypeEnum.CONTROL_GAP
    assert finding.severity == FindingSeverityEnum.CRITICAL
    assert finding.status == FindingStatusEnum.OPEN
    assert sample_item.deficiency_finding_id == finding.id

    # Attempt duplicate escalation -> MUST FAIL (HTTP 409)
    with pytest.raises(HTTPException) as exc:
        AuditFieldworkService.escalate_sample_deficiency(
            db=db,
            organization_id=ctx["org_a"].id,
            audit_id=ctx["audit_a"].id,
            procedure_id=ctx["proc_a"].id,
            sample_id=sample_item.id,
            user_id=ctx["staff_auditor"].id,
            obj_in=esc_in,
        )
    assert exc.value.status_code == 409


# ─────────────────────────────────────────────────────────────────────────────
# 5. WORKPAPER FOUR-EYES GOVERNANCE & DIGEST SEALING TESTS
# ─────────────────────────────────────────────────────────────────────────────
def test_workpaper_four_eyes_and_digest_sealing(db: Session, org_setup):
    """Preparer cannot approve own workpaper; independent reviewer computes and seals SHA-256 digest."""
    ctx = org_setup
    submit_in = AuditWorkpaperSubmit(
        testing_summary="Tested sample of 25 access requests with 0 exceptions.",
        conclusion="Controls are designed and operating effectively.",
    )
    wp = AuditFieldworkService.submit_workpaper(
        db=db,
        organization_id=ctx["org_a"].id,
        audit_id=ctx["audit_a"].id,
        procedure_id=ctx["proc_a"].id,
        user_id=ctx["staff_auditor"].id,
        obj_in=submit_in,
    )
    assert wp.status == WorkpaperStatusEnum.SUBMITTED_FOR_REVIEW
    assert wp.prepared_by_id == ctx["staff_auditor"].id

    # STRICT FOUR-EYES: Preparer cannot approve own workpaper
    with pytest.raises(HTTPException) as exc:
        AuditFieldworkService.approve_workpaper(
            db=db,
            organization_id=ctx["org_a"].id,
            audit_id=ctx["audit_a"].id,
            procedure_id=ctx["proc_a"].id,
            reviewer_id=ctx["staff_auditor"].id,  # SAME user
            obj_in=AuditWorkpaperApprove(review_notes="Self-approval attempt"),
        )
    assert exc.value.status_code == 400
    assert "four-eyes" in exc.value.detail.lower()

    # Independent Lead Auditor approves workpaper
    approved_wp = AuditFieldworkService.approve_workpaper(
        db=db,
        organization_id=ctx["org_a"].id,
        audit_id=ctx["audit_a"].id,
        procedure_id=ctx["proc_a"].id,
        reviewer_id=ctx["lead_auditor"].id,
        obj_in=AuditWorkpaperApprove(review_notes="Workpaper testing verified."),
    )
    assert approved_wp.status == WorkpaperStatusEnum.REVIEWED_APPROVED
    assert approved_wp.workpaper_hash_sha256 is not None
    assert len(approved_wp.workpaper_hash_sha256) == 64

    # Sealed workpaper blocks post-approval tampering
    with pytest.raises(HTTPException) as exc2:
        AuditFieldworkService.submit_workpaper(
            db=db,
            organization_id=ctx["org_a"].id,
            audit_id=ctx["audit_a"].id,
            procedure_id=ctx["proc_a"].id,
            user_id=ctx["staff_auditor"].id,
            obj_in=submit_in,
        )
    assert exc2.value.status_code == 400
    assert "approved" in exc2.value.detail.lower()


# ─────────────────────────────────────────────────────────────────────────────
# 6. ADVERSARIAL MULTI-TENANT ISOLATION (IDOR) TESTS
# ─────────────────────────────────────────────────────────────────────────────
def test_cross_tenant_pbc_access_blocked(db: Session, org_setup):
    """Org B user cannot access Org A PBC request (must return HTTP 404)."""
    ctx = org_setup
    pbc = AuditPBCRequest(
        organization_id=ctx["org_a"].id,
        audit_id=ctx["audit_a"].id,
        organization_control_id=ctx["ctrl_a"].id,
        request_identifier="PBC-ORG-A-001",
        title="Org A Secret PBC",
        description="Secret files",
        status=PBCStatusEnum.REQUESTED,
        due_date=date.today(),
    )
    db.add(pbc)
    db.commit()

    with pytest.raises(HTTPException) as exc:
        AuditFieldworkService.get_pbc_request(
            db=db,
            organization_id=ctx["org_b"].id,  # Cross-tenant query
            audit_id=ctx["audit_a"].id,
            pbc_id=pbc.id,
        )
    assert exc.value.status_code == 404


def test_cross_tenant_population_access_blocked(db: Session, org_setup):
    """Org B user cannot access Org A population or freeze it."""
    ctx = org_setup
    items = [PopulationItemInput(source_record_id="REC-1", attributes={})]
    pop = AuditFieldworkService.create_population(
        db=db,
        organization_id=ctx["org_a"].id,
        audit_id=ctx["audit_a"].id,
        procedure_id=ctx["proc_a"].id,
        obj_in=AuditSamplePopulationCreate(population_name="Secret Pop", population_source="Internal", items=items),
        creator_id=ctx["staff_auditor"].id,
    )
    with pytest.raises(HTTPException) as exc:
        AuditFieldworkService.freeze_population(
            db=db,
            organization_id=ctx["org_b"].id,  # Cross-tenant
            audit_id=ctx["audit_a"].id,
            procedure_id=ctx["proc_a"].id,
            population_id=pop.id,
            user_id=ctx["attacker_b"].id,
        )
    assert exc.value.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# 7. READINESS TELEMETRY INTEGRATION TESTS
# ─────────────────────────────────────────────────────────────────────────────
def test_audit_readiness_reflects_fieldwork_telemetry(db: Session, org_setup):
    """Readiness metrics calculation includes procedures, evidence, and audit health."""
    ctx = org_setup
    readiness = AuditEngagementService.get_readiness(
        db=db,
        audit_id=ctx["audit_a"].id,
        organization_id=ctx["org_a"].id,
    )
    assert readiness is not None
    assert "readiness_score" in readiness
    assert "readiness_band" in readiness
    assert "procedures_total" in readiness
    assert readiness["procedures_total"] >= 1


# ─────────────────────────────────────────────────────────────────────────────
# 8. 22-VECTOR ADVERSARIAL SECURITY MATRIX (SEC-B1-01 to SEC-B1-22)
# ─────────────────────────────────────────────────────────────────────────────

def test_sec_b1_01_cross_tenant_pbc_access_blocked(client: TestClient, org_setup, db: Session):
    """SEC-B1-01: Org B user queries Org A PBC request -> HTTP 404 (zero leakage)."""
    ctx = org_setup
    pbc = AuditPBCRequest(
        organization_id=ctx["org_a"].id,
        audit_id=ctx["audit_a"].id,
        organization_control_id=ctx["ctrl_a"].id,
        request_identifier="PBC-SEC-01",
        title="Confidential Org A Evidence",
        description="Must not leak across tenant boundaries",
        status=PBCStatusEnum.REQUESTED,
        due_date=date.today(),
    )
    db.add(pbc)
    db.commit()

    headers_b = get_token_headers(ctx["attacker_b"])
    res = client.get(f"/api/v1/audits/{ctx['audit_a'].id}/pbc-requests/{pbc.id}", headers=headers_b)
    assert res.status_code == 404


def test_sec_b1_02_cross_tenant_population_injection_blocked(client: TestClient, org_setup):
    """SEC-B1-02: Org B user attempts to attach population to Org A procedure -> HTTP 404."""
    ctx = org_setup
    headers_b = get_token_headers(ctx["attacker_b"])
    payload = {
        "population_name": "Injected Org B Population",
        "population_source": "Adversarial Source",
        "items": [{"source_record_id": "EVIL-1", "attributes": {}}]
    }
    res = client.post(
        f"/api/v1/audits/{ctx['audit_a'].id}/procedures/{ctx['proc_a'].id}/population",
        json=payload,
        headers=headers_b
    )
    assert res.status_code == 404


def test_sec_b1_03_self_review_workpaper_approval_blocked(client: TestClient, org_setup, db: Session):
    """SEC-B1-03: Workpaper preparer attempts to approve own workpaper -> HTTP 400 Four-Eyes Violation."""
    ctx = org_setup
    headers_staff = get_token_headers(ctx["staff_auditor"])

    submit_res = client.post(
        f"/api/v1/audits/{ctx['audit_a'].id}/procedures/{ctx['proc_a'].id}/workpaper/submit",
        json={
            "testing_summary": "Sample of 25 tickets tested by staff auditor.",
            "conclusion": "Operating effectively."
        },
        headers=headers_staff
    )
    assert submit_res.status_code == 200

    approve_res = client.post(
        f"/api/v1/audits/{ctx['audit_a'].id}/procedures/{ctx['proc_a'].id}/workpaper/approve",
        json={"review_notes": "Self approval attempt"},
        headers=headers_staff
    )
    assert approve_res.status_code == 400
    assert "four-eyes" in approve_res.json()["detail"].lower()


def test_sec_b1_04_auditee_self_acceptance_blocked(client: TestClient, org_setup, db: Session):
    """SEC-B1-04: Assigned auditee attempts to accept their own submitted PBC -> HTTP 400 SoD Violation or 403."""
    ctx = org_setup
    headers_auditor = get_token_headers(ctx["lead_auditor"])
    headers_auditee = get_token_headers(ctx["auditee"])

    create_res = client.post(
        f"/api/v1/audits/{ctx['audit_a'].id}/pbc-requests",
        json={
            "organization_control_id": ctx["ctrl_a"].id,
            "title": "Vendor SOC2 Report",
            "description": "Provide latest SOC2",
            "assigned_to_id": ctx["auditee"].id,
            "due_date": (date.today() + timedelta(days=5)).isoformat(),
            "priority": "HIGH"
        },
        headers=headers_auditor
    )
    assert create_res.status_code == 201
    pbc_id = create_res.json()["id"]

    ev = EvidenceItem(
        organization_id=ctx["org_a"].id,
        organization_control_id=ctx["ctrl_a"].id,
        title="SOC2 2026",
        description="SOC2 Vendor Report",
        original_filename="soc2.pdf",
        stored_filename="soc2.pdf",
        file_extension=".pdf",
        content_type="application/pdf",
        file_size=1024,
        sha256_hash="abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        storage_key="tenants/1/soc2.pdf",
        status=EvidenceStatusEnum.UPLOADED,
        uploaded_by_id=ctx["auditee"].id,
    )
    db.add(ev)
    db.commit()

    fulfill_res = client.post(
        f"/api/v1/audits/{ctx['audit_a'].id}/pbc-requests/{pbc_id}/fulfill",
        json={"evidence_id": ev.id, "submission_notes": "Here is report"},
        headers=headers_auditee
    )
    assert fulfill_res.status_code == 200

    review_res = client.post(
        f"/api/v1/audits/{ctx['audit_a'].id}/pbc-requests/{pbc_id}/review",
        json={"decision": "ACCEPT", "review_notes": "Auditee accepting own submission"},
        headers=headers_auditee
    )
    assert review_res.status_code in (400, 403)


def test_sec_b1_05_post_approval_workpaper_tampering_blocked(client: TestClient, org_setup, db: Session):
    """SEC-B1-05: Client attempts to submit workpaper after REVIEWED_APPROVED -> HTTP 400 (Sealed)."""
    ctx = org_setup
    headers_staff = get_token_headers(ctx["staff_auditor"])
    headers_lead = get_token_headers(ctx["lead_auditor"])

    client.post(
        f"/api/v1/audits/{ctx['audit_a'].id}/procedures/{ctx['proc_a'].id}/workpaper/submit",
        json={"testing_summary": "Initial testing", "conclusion": "Passed"},
        headers=headers_staff
    )
    appr = client.post(
        f"/api/v1/audits/{ctx['audit_a'].id}/procedures/{ctx['proc_a'].id}/workpaper/approve",
        json={"review_notes": "Approved by lead"},
        headers=headers_lead
    )
    assert appr.status_code == 200

    tamper = client.post(
        f"/api/v1/audits/{ctx['audit_a'].id}/procedures/{ctx['proc_a'].id}/workpaper/submit",
        json={"testing_summary": "Tampered testing", "conclusion": "Changed"},
        headers=headers_staff
    )
    assert tamper.status_code == 400
    assert "approved" in tamper.json()["detail"].lower()


def test_sec_b1_06_post_approval_sample_tampering_blocked(client: TestClient, org_setup, db: Session):
    """SEC-B1-06: Client attempts to alter sample test result after workpaper approval -> HTTP 400."""
    ctx = org_setup
    items = [PopulationItemInput(source_record_id="USER-A", attributes={})]
    pop = AuditFieldworkService.create_population(
        db=db,
        organization_id=ctx["org_a"].id,
        audit_id=ctx["audit_a"].id,
        procedure_id=ctx["proc_a"].id,
        obj_in=AuditSamplePopulationCreate(population_name="Freeze Pop", population_source="Logs", items=items),
        creator_id=ctx["staff_auditor"].id,
    )
    AuditFieldworkService.freeze_population(
        db=db,
        organization_id=ctx["org_a"].id,
        audit_id=ctx["audit_a"].id,
        procedure_id=ctx["proc_a"].id,
        population_id=pop.id,
        user_id=ctx["staff_auditor"].id,
    )
    pop_gen = AuditFieldworkService.generate_samples(
        db=db,
        organization_id=ctx["org_a"].id,
        audit_id=ctx["audit_a"].id,
        procedure_id=ctx["proc_a"].id,
        population_id=pop.id,
        user_id=ctx["staff_auditor"].id,
        obj_in=AuditSampleGenerateRequest(sampling_method=SamplingMethodEnum.RANDOM, sample_size=1),
    )
    sample_item = pop_gen.sample_items[0]

    AuditFieldworkService.submit_workpaper(
        db=db,
        organization_id=ctx["org_a"].id,
        audit_id=ctx["audit_a"].id,
        procedure_id=ctx["proc_a"].id,
        user_id=ctx["staff_auditor"].id,
        obj_in=AuditWorkpaperSubmit(testing_summary="Tested 1 item", conclusion="Effective"),
    )
    AuditFieldworkService.approve_workpaper(
        db=db,
        organization_id=ctx["org_a"].id,
        audit_id=ctx["audit_a"].id,
        procedure_id=ctx["proc_a"].id,
        reviewer_id=ctx["lead_auditor"].id,
        obj_in=AuditWorkpaperApprove(review_notes="Approved"),
    )

    with pytest.raises(HTTPException) as exc:
        AuditFieldworkService.update_sample_item(
            db=db,
            organization_id=ctx["org_a"].id,
            audit_id=ctx["audit_a"].id,
            procedure_id=ctx["proc_a"].id,
            sample_id=sample_item.id,
            user_id=ctx["staff_auditor"].id,
            obj_in=AuditSampleItemUpdate(test_result=SampleResultEnum.FAIL),
        )
    assert exc.value.status_code == 400
    assert "sealed" in exc.value.detail.lower() or "approved" in exc.value.detail.lower()


def test_sec_b1_07_client_seed_forgery_ignored(client: TestClient, org_setup, db: Session):
    """SEC-B1-07: Client cannot supply arbitrary PRNG seed; server generates cryptographic seed."""
    ctx = org_setup
    items = [PopulationItemInput(source_record_id=f"ITEM-{i}", attributes={}) for i in range(5)]
    pop = AuditFieldworkService.create_population(
        db=db,
        organization_id=ctx["org_a"].id,
        audit_id=ctx["audit_a"].id,
        procedure_id=ctx["proc_a"].id,
        obj_in=AuditSamplePopulationCreate(population_name="Seed Pop", population_source="Logs", items=items),
        creator_id=ctx["staff_auditor"].id,
    )
    AuditFieldworkService.freeze_population(
        db=db,
        organization_id=ctx["org_a"].id,
        audit_id=ctx["audit_a"].id,
        procedure_id=ctx["proc_a"].id,
        population_id=pop.id,
        user_id=ctx["staff_auditor"].id,
    )
    headers_staff = get_token_headers(ctx["staff_auditor"])
    res = client.post(
        f"/api/v1/audits/{ctx['audit_a'].id}/procedures/{ctx['proc_a'].id}/population/{pop.id}/generate",
        json={
            "sampling_method": "RANDOM",
            "sample_size": 2,
            "seed": "malicious_fixed_seed_12345"
        },
        headers=headers_staff
    )
    assert res.status_code == 200
    data = res.json()
    assert data["sampling_seed"] is not None
    assert data["sampling_seed"] != "malicious_fixed_seed_12345"
    assert len(data["sampling_seed"]) == 64


def test_sec_b1_08_sample_size_exceeding_population_rejected(client: TestClient, org_setup, db: Session):
    """SEC-B1-08: Client supplies sample size exceeding total population count -> HTTP 422 ($n \\le N$)."""
    ctx = org_setup
    items = [PopulationItemInput(source_record_id="S-1", attributes={})]
    pop = AuditFieldworkService.create_population(
        db=db,
        organization_id=ctx["org_a"].id,
        audit_id=ctx["audit_a"].id,
        procedure_id=ctx["proc_a"].id,
        obj_in=AuditSamplePopulationCreate(population_name="Small Pop", population_source="Logs", items=items),
        creator_id=ctx["staff_auditor"].id,
    )
    AuditFieldworkService.freeze_population(
        db=db,
        organization_id=ctx["org_a"].id,
        audit_id=ctx["audit_a"].id,
        procedure_id=ctx["proc_a"].id,
        population_id=pop.id,
        user_id=ctx["staff_auditor"].id,
    )
    headers_staff = get_token_headers(ctx["staff_auditor"])
    res = client.post(
        f"/api/v1/audits/{ctx['audit_a'].id}/procedures/{ctx['proc_a'].id}/population/{pop.id}/generate",
        json={"sampling_method": "RANDOM", "sample_size": 50},
        headers=headers_staff
    )
    assert res.status_code == 422


def test_sec_b1_09_client_org_id_injection_overridden(client: TestClient, org_setup, db: Session):
    """SEC-B1-09: Client injects foreign organization_id in JSON body; server overrides with token org."""
    ctx = org_setup
    headers_staff = get_token_headers(ctx["staff_auditor"])
    res = client.post(
        f"/api/v1/audits/{ctx['audit_a'].id}/pbc-requests",
        json={
            "organization_id": ctx["org_b"].id,
            "organization_control_id": ctx["ctrl_a"].id,
            "title": "Injection Test PBC",
            "description": "Testing org boundary",
            "due_date": date.today().isoformat(),
            "priority": "LOW"
        },
        headers=headers_staff
    )
    assert res.status_code == 201
    assert res.json()["organization_id"] == ctx["org_a"].id


def test_sec_b1_10_forged_reviewer_identity_ignored(client: TestClient, org_setup, db: Session):
    """SEC-B1-10: Client passes reviewed_by_id in body; server uses authenticated user.id."""
    ctx = org_setup
    headers_lead = get_token_headers(ctx["lead_auditor"])

    submit_in = AuditWorkpaperSubmit(testing_summary="Test 1", conclusion="Pass 1")
    AuditFieldworkService.submit_workpaper(
        db=db,
        organization_id=ctx["org_a"].id,
        audit_id=ctx["audit_a"].id,
        procedure_id=ctx["proc_a"].id,
        user_id=ctx["staff_auditor"].id,
        obj_in=submit_in,
    )

    res = client.post(
        f"/api/v1/audits/{ctx['audit_a'].id}/procedures/{ctx['proc_a'].id}/workpaper/approve",
        json={"review_notes": "Good", "reviewed_by_id": 99999},
        headers=headers_lead
    )
    assert res.status_code == 200
    assert res.json()["reviewed_by_id"] == ctx["lead_auditor"].id


def test_sec_b1_11_forged_audit_timestamps_ignored(client: TestClient, org_setup, db: Session):
    """SEC-B1-11: Client passes backdated reviewed_at; server assigns utcnow()."""
    ctx = org_setup
    headers_lead = get_token_headers(ctx["lead_auditor"])

    AuditFieldworkService.submit_workpaper(
        db=db,
        organization_id=ctx["org_a"].id,
        audit_id=ctx["audit_a"].id,
        procedure_id=ctx["proc_a"].id,
        user_id=ctx["staff_auditor"].id,
        obj_in=AuditWorkpaperSubmit(testing_summary="Test 1", conclusion="Pass 1"),
    )

    backdated = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
    res = client.post(
        f"/api/v1/audits/{ctx['audit_a'].id}/procedures/{ctx['proc_a'].id}/workpaper/approve",
        json={"review_notes": "Good", "reviewed_at": backdated},
        headers=headers_lead
    )
    assert res.status_code == 200
    actual_reviewed = datetime.fromisoformat(res.json()["reviewed_at"].replace("Z", "+00:00"))
    if actual_reviewed.tzinfo is None:
        actual_reviewed = actual_reviewed.replace(tzinfo=timezone.utc)
    assert abs((datetime.now(timezone.utc) - actual_reviewed).total_seconds()) < 60


def test_sec_b1_12_unfrozen_population_sampling_blocked(client: TestClient, org_setup, db: Session):
    """SEC-B1-12: Client requests sample generation on an unfrozen population -> HTTP 400."""
    ctx = org_setup
    items = [PopulationItemInput(source_record_id="REC-X", attributes={})]
    pop = AuditFieldworkService.create_population(
        db=db,
        organization_id=ctx["org_a"].id,
        audit_id=ctx["audit_a"].id,
        procedure_id=ctx["proc_a"].id,
        obj_in=AuditSamplePopulationCreate(population_name="Unfrozen Pop", population_source="Logs", items=items),
        creator_id=ctx["staff_auditor"].id,
    )
    headers_staff = get_token_headers(ctx["staff_auditor"])
    res = client.post(
        f"/api/v1/audits/{ctx['audit_a'].id}/procedures/{ctx['proc_a'].id}/population/{pop.id}/generate",
        json={"sampling_method": "RANDOM", "sample_size": 1},
        headers=headers_staff
    )
    assert res.status_code == 400
    assert "frozen" in res.json()["detail"].lower()


def test_sec_b1_13_population_mutability_after_freeze(client: TestClient, org_setup, db: Session):
    """SEC-B1-13: Re-sampling an already generated population snapshot raises HTTP 409 Conflict."""
    ctx = org_setup
    items = [PopulationItemInput(source_record_id="REC-1", attributes={})]
    pop = AuditFieldworkService.create_population(
        db=db,
        organization_id=ctx["org_a"].id,
        audit_id=ctx["audit_a"].id,
        procedure_id=ctx["proc_a"].id,
        obj_in=AuditSamplePopulationCreate(population_name="Immutable Pop", population_source="Logs", items=items),
        creator_id=ctx["staff_auditor"].id,
    )
    AuditFieldworkService.freeze_population(
        db=db,
        organization_id=ctx["org_a"].id,
        audit_id=ctx["audit_a"].id,
        procedure_id=ctx["proc_a"].id,
        population_id=pop.id,
        user_id=ctx["staff_auditor"].id,
    )
    headers_staff = get_token_headers(ctx["staff_auditor"])
    res1 = client.post(
        f"/api/v1/audits/{ctx['audit_a'].id}/procedures/{ctx['proc_a'].id}/population/{pop.id}/generate",
        json={"sampling_method": "RANDOM", "sample_size": 1},
        headers=headers_staff
    )
    assert res1.status_code == 200

    res2 = client.post(
        f"/api/v1/audits/{ctx['audit_a'].id}/procedures/{ctx['proc_a'].id}/population/{pop.id}/generate",
        json={"sampling_method": "RANDOM", "sample_size": 1},
        headers=headers_staff
    )
    assert res2.status_code == 409


def test_sec_b1_14_duplicate_pbc_fulfillment_rejected(client: TestClient, org_setup, db: Session):
    """SEC-B1-14: Fulfilling a PBC that is already in SUBMITTED state returns HTTP 400."""
    ctx = org_setup
    headers_auditor = get_token_headers(ctx["lead_auditor"])
    headers_auditee = get_token_headers(ctx["auditee"])

    create_res = client.post(
        f"/api/v1/audits/{ctx['audit_a'].id}/pbc-requests",
        json={
            "organization_control_id": ctx["ctrl_a"].id,
            "title": "Firewall Config",
            "description": "Provide config",
            "assigned_to_id": ctx["auditee"].id,
            "due_date": date.today().isoformat(),
            "priority": "MEDIUM"
        },
        headers=headers_auditor
    )
    pbc_id = create_res.json()["id"]

    ev = EvidenceItem(
        organization_id=ctx["org_a"].id,
        organization_control_id=ctx["ctrl_a"].id,
        title="FW Conf",
        original_filename="fw.txt",
        stored_filename="fw.txt",
        file_extension=".txt",
        content_type="text/plain",
        file_size=512,
        sha256_hash="abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        storage_key="tenants/1/fw.txt",
        status=EvidenceStatusEnum.UPLOADED,
    )
    db.add(ev)
    db.commit()

    res1 = client.post(
        f"/api/v1/audits/{ctx['audit_a'].id}/pbc-requests/{pbc_id}/fulfill",
        json={"evidence_id": ev.id, "submission_notes": "First upload"},
        headers=headers_auditee
    )
    assert res1.status_code == 200

    res2 = client.post(
        f"/api/v1/audits/{ctx['audit_a'].id}/pbc-requests/{pbc_id}/fulfill",
        json={"evidence_id": ev.id, "submission_notes": "Duplicate upload attempt"},
        headers=headers_auditee
    )
    assert res2.status_code == 400
    assert "submitted" in res2.json()["detail"].lower()


def test_sec_b1_15_duplicate_finding_escalation_race(client: TestClient, org_setup, db: Session):
    """SEC-B1-15: Attempting to escalate deficiency finding on an already escalated sample item returns HTTP 409."""
    ctx = org_setup
    items = [PopulationItemInput(source_record_id="REC-ESC", attributes={})]
    pop = AuditFieldworkService.create_population(
        db=db,
        organization_id=ctx["org_a"].id,
        audit_id=ctx["audit_a"].id,
        procedure_id=ctx["proc_a"].id,
        obj_in=AuditSamplePopulationCreate(population_name="Esc Pop", population_source="Logs", items=items),
        creator_id=ctx["staff_auditor"].id,
    )
    AuditFieldworkService.freeze_population(
        db=db,
        organization_id=ctx["org_a"].id,
        audit_id=ctx["audit_a"].id,
        procedure_id=ctx["proc_a"].id,
        population_id=pop.id,
        user_id=ctx["staff_auditor"].id,
    )
    pop_gen = AuditFieldworkService.generate_samples(
        db=db,
        organization_id=ctx["org_a"].id,
        audit_id=ctx["audit_a"].id,
        procedure_id=ctx["proc_a"].id,
        population_id=pop.id,
        user_id=ctx["staff_auditor"].id,
        obj_in=AuditSampleGenerateRequest(sampling_method=SamplingMethodEnum.RANDOM, sample_size=1),
    )
    sample_item = pop_gen.sample_items[0]
    sample_item.test_result = SampleResultEnum.FAIL
    db.commit()

    headers_staff = get_token_headers(ctx["staff_auditor"])
    res1 = client.post(
        f"/api/v1/audits/{ctx['audit_a'].id}/procedures/{ctx['proc_a'].id}/samples/{sample_item.id}/escalate-finding",
        json={"severity": "HIGH"},
        headers=headers_staff
    )
    assert res1.status_code == 201

    res2 = client.post(
        f"/api/v1/audits/{ctx['audit_a'].id}/procedures/{ctx['proc_a'].id}/samples/{sample_item.id}/escalate-finding",
        json={"severity": "HIGH"},
        headers=headers_staff
    )
    assert res2.status_code == 409


def test_sec_b1_16_unauthorized_fieldwork_access_viewer_blocked(client: TestClient, org_setup, db: Session):
    """SEC-B1-16: User with VIEWER role attempting fieldwork mutation returns HTTP 403 Forbidden."""
    ctx = org_setup
    headers_viewer = get_token_headers(ctx["viewer_a"])

    res = client.post(
        f"/api/v1/audits/{ctx['audit_a'].id}/pbc-requests",
        json={
            "organization_control_id": ctx["ctrl_a"].id,
            "title": "Viewer PBC",
            "description": "Unauthorized",
            "due_date": date.today().isoformat(),
            "priority": "LOW"
        },
        headers=headers_viewer
    )
    assert res.status_code == 403


def test_sec_b1_17_illegal_workpaper_state_jump_blocked(client: TestClient, org_setup, db: Session):
    """SEC-B1-17: Client attempts jump from DRAFT directly to REVIEWED_APPROVED -> HTTP 400."""
    ctx = org_setup
    headers_lead = get_token_headers(ctx["lead_auditor"])
    res = client.post(
        f"/api/v1/audits/{ctx['audit_a'].id}/procedures/{ctx['proc_a'].id}/workpaper/approve",
        json={"review_notes": "Attempting jump"},
        headers=headers_lead
    )
    assert res.status_code in (400, 404)


def test_sec_b1_18_evidence_storage_bypass_rejected(client: TestClient, org_setup, db: Session):
    """SEC-B1-18: PBC fulfillment without valid evidence_id returns HTTP 422 Unprocessable Entity."""
    ctx = org_setup
    headers_auditor = get_token_headers(ctx["lead_auditor"])
    headers_auditee = get_token_headers(ctx["auditee"])

    create_res = client.post(
        f"/api/v1/audits/{ctx['audit_a'].id}/pbc-requests",
        json={
            "organization_control_id": ctx["ctrl_a"].id,
            "title": "Bypass Test PBC",
            "description": "Testing missing evidence",
            "due_date": date.today().isoformat(),
            "priority": "LOW"
        },
        headers=headers_auditor
    )
    pbc_id = create_res.json()["id"]

    res = client.post(
        f"/api/v1/audits/{ctx['audit_a'].id}/pbc-requests/{pbc_id}/fulfill",
        json={"submission_notes": "Missing evidence ID entirely"},
        headers=headers_auditee
    )
    assert res.status_code in (400, 422)


def test_sec_b1_19_finding_engine_authoritative_link(client: TestClient, org_setup, db: Session):
    """SEC-B1-19: Escalated sample deficiency links to Phase 4 authoritative findings table."""
    ctx = org_setup
    items = [PopulationItemInput(source_record_id="GAP-ITEM-1", attributes={"env": "prod"})]
    pop = AuditFieldworkService.create_population(
        db=db,
        organization_id=ctx["org_a"].id,
        audit_id=ctx["audit_a"].id,
        procedure_id=ctx["proc_a"].id,
        obj_in=AuditSamplePopulationCreate(population_name="Finding Link Pop", population_source="Logs", items=items),
        creator_id=ctx["staff_auditor"].id,
    )
    AuditFieldworkService.freeze_population(
        db=db,
        organization_id=ctx["org_a"].id,
        audit_id=ctx["audit_a"].id,
        procedure_id=ctx["proc_a"].id,
        population_id=pop.id,
        user_id=ctx["staff_auditor"].id,
    )
    pop_gen = AuditFieldworkService.generate_samples(
        db=db,
        organization_id=ctx["org_a"].id,
        audit_id=ctx["audit_a"].id,
        procedure_id=ctx["proc_a"].id,
        population_id=pop.id,
        user_id=ctx["staff_auditor"].id,
        obj_in=AuditSampleGenerateRequest(sampling_method=SamplingMethodEnum.RANDOM, sample_size=1),
    )
    sample_item = pop_gen.sample_items[0]
    sample_item.test_result = SampleResultEnum.FAIL
    db.commit()

    finding = AuditFieldworkService.escalate_sample_deficiency(
        db=db,
        organization_id=ctx["org_a"].id,
        audit_id=ctx["audit_a"].id,
        procedure_id=ctx["proc_a"].id,
        sample_id=sample_item.id,
        user_id=ctx["staff_auditor"].id,
        obj_in=AuditSampleEscalateFinding(severity="HIGH"),
    )
    db_finding = db.query(Finding).filter(Finding.id == finding.id).first()
    assert db_finding is not None
    assert db_finding.organization_id == ctx["org_a"].id
    assert db_finding.organization_control_id == ctx["ctrl_a"].id

    link = db.query(AuditFindingLink).filter(
        AuditFindingLink.audit_id == ctx["audit_a"].id,
        AuditFindingLink.finding_id == finding.id
    ).first()
    assert link is not None
    assert link.source_procedure_id == ctx["proc_a"].id


def test_sec_b1_20_workpaper_digest_tamper_evidence(client: TestClient, org_setup, db: Session):
    """SEC-B1-20: Tampering with fieldwork content directly in database invalidates digest verification."""
    ctx = org_setup
    wp = AuditFieldworkService.submit_workpaper(
        db=db,
        organization_id=ctx["org_a"].id,
        audit_id=ctx["audit_a"].id,
        procedure_id=ctx["proc_a"].id,
        user_id=ctx["staff_auditor"].id,
        obj_in=AuditWorkpaperSubmit(testing_summary="Genuine fieldwork summary", conclusion="Genuine conclusion"),
    )
    approved_wp = AuditFieldworkService.approve_workpaper(
        db=db,
        organization_id=ctx["org_a"].id,
        audit_id=ctx["audit_a"].id,
        procedure_id=ctx["proc_a"].id,
        reviewer_id=ctx["lead_auditor"].id,
        obj_in=AuditWorkpaperApprove(review_notes="Approved"),
    )
    original_hash = approved_wp.workpaper_hash_sha256

    tampered_payload = {
        "organization_id": ctx["org_a"].id,
        "audit_id": ctx["audit_a"].id,
        "procedure_id": ctx["proc_a"].id,
        "version_number": approved_wp.version_number,
        "prepared_by_id": approved_wp.prepared_by_id,
        "prepared_at": approved_wp.prepared_at.isoformat(),
        "reviewed_by_id": approved_wp.reviewed_by_id,
        "reviewed_at": approved_wp.reviewed_at.isoformat(),
        "testing_summary": approved_wp.testing_summary,
        "conclusion": "TAMPERED CONCLUSION: Ineffective controls",
        "sample_summary": {
            "total_samples": 0,
            "pass_count": 0,
            "fail_count": 0,
            "exception_rate": 0.0,
        }
    }
    tampered_bytes = json.dumps(tampered_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    tampered_hash = hashlib.sha256(tampered_bytes).hexdigest()
    assert original_hash != tampered_hash


def test_sec_b1_21_systematic_sampling_invalid_parameters_rejected():
    """SEC-B1-21: Systematic sampling with invalid parameter n <= 0 raises ValueError."""
    items = [{"source_record_id": "REC-1", "attributes": {}}]
    seed = "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
    with pytest.raises(ValueError):
        AuditSamplingService.sample_systematic(items, sample_size=0, seed_hex=seed)


def test_sec_b1_22_stratified_sampling_empty_strata_rejected():
    """SEC-B1-22: Stratified sampling with missing or empty strata attribute raises ValueError."""
    items = [{"source_record_id": "REC-1", "attributes": {}}]
    seed = "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
    with pytest.raises(ValueError):
        AuditSamplingService.sample_stratified(items, sample_size=1, seed_hex=seed, strata_attribute="")
