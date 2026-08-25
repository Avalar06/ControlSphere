import io
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.security import get_password_hash
from app.models.organization import Organization
from app.models.user import User
from tests.conftest import get_token_headers


def test_cross_tenant_assessment_idor_blocked(
    client: TestClient, analyst_user: User, db: Session, seeded_framework
):
    headers_org1 = get_token_headers(analyst_user)
    controls = client.get("/api/v1/controls", headers=headers_org1).json()
    ctrl_id = controls[0]["id"]

    # Org 1 creates assessment
    res_ass = client.post(
        "/api/v1/assessments",
        headers=headers_org1,
        json={"organization_control_id": ctrl_id, "summary": "Org 1 Confidential Assessment"},
    )
    ass_id = res_ass.json()["id"]

    # Create Org 2 & user
    org2 = Organization(name="Competitor Corp", slug="competitor-corp", is_active=True)
    db.add(org2)
    db.commit()
    db.refresh(org2)

    user_org2 = User(
        email="attacker@competitor.com",
        hashed_password=get_password_hash("SecretPass123!"),
        full_name="Attacker User",
        role="GRC_ANALYST",
        is_active=True,
        organization_id=org2.id,
    )
    db.add(user_org2)
    db.commit()
    db.refresh(user_org2)

    headers_org2 = get_token_headers(user_org2)

    # 1. Org 2 tries to GET Org 1 Assessment (IDOR)
    res_get_idor = client.get(f"/api/v1/assessments/{ass_id}", headers=headers_org2)
    assert res_get_idor.status_code == 404

    # 2. Org 2 tries to UPDATE Org 1 Assessment
    res_patch_idor = client.patch(
        f"/api/v1/assessments/{ass_id}",
        headers=headers_org2,
        json={"summary": "Attacker overwrite."},
    )
    assert res_patch_idor.status_code == 404

    # 3. Org 2 tries to START Org 1 Assessment
    res_start_idor = client.post(f"/api/v1/assessments/{ass_id}/start", headers=headers_org2)
    assert res_start_idor.status_code == 404

    # 4. Org 2 tries to COMPLETE Org 1 Assessment
    res_comp_idor = client.post(
        f"/api/v1/assessments/{ass_id}/complete",
        headers=headers_org2,
        json={"conclusion": "INEFFECTIVE", "summary": "Attacker sabotaged."},
    )
    assert res_comp_idor.status_code == 404


def test_cross_tenant_finding_idor_blocked(
    client: TestClient, analyst_user: User, db: Session, seeded_framework
):
    headers_org1 = get_token_headers(analyst_user)
    controls = client.get("/api/v1/controls", headers=headers_org1).json()
    ctrl_id = controls[0]["id"]

    # Org 1 creates finding
    res_find = client.post(
        "/api/v1/findings",
        headers=headers_org1,
        json={
            "organization_control_id": ctrl_id,
            "title": "Org 1 Confidential Vulnerability",
            "description": "Sensitive zero-day details.",
            "recommendation": "Fix secret.",
            "impact": 5,
            "likelihood": 5,
        },
    )
    find_id = res_find.json()["id"]

    # Create Org 2 user
    org2 = Organization(name="Competitor Corp 2", slug="competitor-corp-2", is_active=True)
    db.add(org2)
    db.commit()
    db.refresh(org2)

    user_org2 = User(
        email="hacker@competitor2.com",
        hashed_password=get_password_hash("SecretPass123!"),
        full_name="Hacker User",
        role="GRC_ANALYST",
        is_active=True,
        organization_id=org2.id,
    )
    db.add(user_org2)
    db.commit()
    db.refresh(user_org2)

    headers_org2 = get_token_headers(user_org2)

    # 1. Org 2 tries to GET Org 1 Finding
    res_get = client.get(f"/api/v1/findings/{find_id}", headers=headers_org2)
    assert res_get.status_code == 404

    # 2. Org 2 tries to UPDATE Org 1 Finding
    res_patch = client.patch(
        f"/api/v1/findings/{find_id}",
        headers=headers_org2,
        json={"title": "Hacked finding"},
    )
    assert res_patch.status_code == 404

    # 3. Org 2 tries to ACCEPT RISK for Org 1 Finding
    res_acc = client.post(
        f"/api/v1/findings/{find_id}/risk-acceptance",
        headers=headers_org2,
        json={"justification": "Attacker risk acceptance."},
    )
    assert res_acc.status_code == 404


def test_foreign_and_inactive_user_assignment_blocked(
    client: TestClient, analyst_user: User, db: Session, seeded_framework
):
    headers_org1 = get_token_headers(analyst_user)
    controls = client.get("/api/v1/controls", headers=headers_org1).json()
    ctrl_id = controls[0]["id"]

    # Create foreign tenant user
    org_other = Organization(name="External Org", slug="external-org", is_active=True)
    db.add(org_other)
    db.commit()
    db.refresh(org_other)

    foreign_user = User(
        email="foreign@external.com",
        hashed_password=get_password_hash("SecretPass123!"),
        full_name="Foreign User",
        role="GRC_ANALYST",
        is_active=True,
        organization_id=org_other.id,
    )
    db.add(foreign_user)

    # Create inactive user in Org 1
    inactive_user = User(
        email="inactive@myorg.com",
        hashed_password=get_password_hash("SecretPass123!"),
        full_name="Inactive Employee",
        role="SECURITY_ANALYST",
        is_active=False,
        organization_id=analyst_user.organization_id,
    )
    db.add(inactive_user)
    db.commit()

    # 1. Foreign assessor blocked
    res_ass_foreign = client.post(
        "/api/v1/assessments",
        headers=headers_org1,
        json={"organization_control_id": ctrl_id, "assessor_id": foreign_user.id},
    )
    assert res_ass_foreign.status_code == 400
    assert "Assessor ID" in res_ass_foreign.json()["detail"]

    # 2. Inactive assessor blocked
    res_ass_inactive = client.post(
        "/api/v1/assessments",
        headers=headers_org1,
        json={"organization_control_id": ctrl_id, "assessor_id": inactive_user.id},
    )
    assert res_ass_inactive.status_code == 400
    assert "inactive" in res_ass_inactive.json()["detail"].lower()

    # 3. Foreign finding owner blocked
    res_find_foreign = client.post(
        "/api/v1/findings",
        headers=headers_org1,
        json={
            "organization_control_id": ctrl_id,
            "title": "Finding with foreign owner",
            "description": "Desc",
            "recommendation": "Rec",
            "owner_id": foreign_user.id,
        },
    )
    assert res_find_foreign.status_code == 400
    assert "Owner ID" in res_find_foreign.json()["detail"]

    # 4. Inactive finding owner blocked
    res_find_inactive = client.post(
        "/api/v1/findings",
        headers=headers_org1,
        json={
            "organization_control_id": ctrl_id,
            "title": "Finding with inactive owner",
            "description": "Desc",
            "recommendation": "Rec",
            "owner_id": inactive_user.id,
        },
    )
    assert res_find_inactive.status_code == 400
    assert "inactive" in res_find_inactive.json()["detail"].lower()


def test_assessment_lifecycle_invalid_transitions_blocked(
    client: TestClient, analyst_user: User, db: Session, seeded_framework
):
    headers = get_token_headers(analyst_user)
    controls = client.get("/api/v1/controls", headers=headers).json()
    ctrl_id = controls[0]["id"]

    # 1. Create Assessment (DRAFT)
    res_ass = client.post(
        "/api/v1/assessments",
        headers=headers,
        json={"organization_control_id": ctrl_id, "summary": "Initial draft."},
    )
    ass_id = res_ass.json()["id"]

    # DRAFT -> COMPLETED must be BLOCKED
    res_draft_to_comp = client.post(
        f"/api/v1/assessments/{ass_id}/complete",
        headers=headers,
        json={"conclusion": "EFFECTIVE", "summary": "Skipped evaluation."},
    )
    assert res_draft_to_comp.status_code == 400
    assert "Only IN_PROGRESS assessments can be completed" in res_draft_to_comp.json()["detail"]

    # DRAFT -> SUPERSEDED must be BLOCKED
    res_draft_to_super = client.post(f"/api/v1/assessments/{ass_id}/supersede", headers=headers)
    assert res_draft_to_super.status_code == 400
    assert "Only COMPLETED assessments can be superseded" in res_draft_to_super.json()["detail"]

    # Start: DRAFT -> IN_PROGRESS
    res_start = client.post(f"/api/v1/assessments/{ass_id}/start", headers=headers)
    assert res_start.status_code == 200

    # IN_PROGRESS -> SUPERSEDED must be BLOCKED
    res_inprog_to_super = client.post(f"/api/v1/assessments/{ass_id}/supersede", headers=headers)
    assert res_inprog_to_super.status_code == 400
    assert "Only COMPLETED assessments can be superseded" in res_inprog_to_super.json()["detail"]

    # IN_PROGRESS -> START again must be BLOCKED
    res_start_again = client.post(f"/api/v1/assessments/{ass_id}/start", headers=headers)
    assert res_start_again.status_code == 400

    # Complete: IN_PROGRESS -> COMPLETED
    res_comp = client.post(
        f"/api/v1/assessments/{ass_id}/complete",
        headers=headers,
        json={"conclusion": "EFFECTIVE", "summary": "Valid completed assessment."},
    )
    assert res_comp.status_code == 200

    # COMPLETED -> START must be BLOCKED
    res_comp_to_start = client.post(f"/api/v1/assessments/{ass_id}/start", headers=headers)
    assert res_comp_to_start.status_code == 400

    # COMPLETED -> COMPLETE again must be BLOCKED
    res_comp_again = client.post(
        f"/api/v1/assessments/{ass_id}/complete",
        headers=headers,
        json={"conclusion": "EFFECTIVE", "summary": "Complete again."},
    )
    assert res_comp_again.status_code == 400

    # Supersede: COMPLETED -> SUPERSEDED
    res_super = client.post(f"/api/v1/assessments/{ass_id}/supersede", headers=headers)
    assert res_super.status_code == 200

    # SUPERSEDED -> START must be BLOCKED
    res_super_to_start = client.post(f"/api/v1/assessments/{ass_id}/start", headers=headers)
    assert res_super_to_start.status_code == 400


def test_finding_lifecycle_invalid_transitions_blocked(
    client: TestClient, analyst_user: User, db: Session, seeded_framework
):
    headers = get_token_headers(analyst_user)
    controls = client.get("/api/v1/controls", headers=headers).json()
    ctrl_id = controls[0]["id"]

    # 1. Create finding (OPEN)
    res_find = client.post(
        "/api/v1/findings",
        headers=headers,
        json={
            "organization_control_id": ctrl_id,
            "title": "State Machine Test Finding",
            "description": "Desc",
            "recommendation": "Rec",
            "impact": 3,
            "likelihood": 3,
        },
    )
    f_id = res_find.json()["id"]

    # OPEN -> CLOSED must be BLOCKED
    res_open_close = client.post(
        f"/api/v1/findings/{f_id}/status",
        headers=headers,
        json={"status": "CLOSED"},
    )
    assert res_open_close.status_code == 400

    # OPEN -> PENDING_VALIDATION directly must be BLOCKED (must be IN_REMEDIATION first)
    res_open_val = client.post(
        f"/api/v1/findings/{f_id}/status",
        headers=headers,
        json={"status": "PENDING_VALIDATION", "resolution": "Bypassed remediation."},
    )
    assert res_open_val.status_code == 400
    assert "Findings must be IN_REMEDIATION" in res_open_val.json()["detail"]

    # OPEN -> RESOLVED without validation must be BLOCKED
    res_open_res = client.post(
        f"/api/v1/findings/{f_id}/status",
        headers=headers,
        json={"status": "RESOLVED"},
    )
    assert res_open_res.status_code == 400

    # Transition to IN_REMEDIATION
    client.post(
        f"/api/v1/findings/{f_id}/status",
        headers=headers,
        json={"status": "IN_REMEDIATION"},
    )

    # IN_REMEDIATION -> OPEN must be BLOCKED
    res_rem_to_open = client.post(
        f"/api/v1/findings/{f_id}/status",
        headers=headers,
        json={"status": "OPEN"},
    )
    assert res_rem_to_open.status_code == 400

    # IN_REMEDIATION -> CLOSED directly must be BLOCKED
    res_rem_close = client.post(
        f"/api/v1/findings/{f_id}/status",
        headers=headers,
        json={"status": "CLOSED"},
    )
    assert res_rem_close.status_code == 400

    # Submit for validation
    client.post(
        f"/api/v1/findings/{f_id}/status",
        headers=headers,
        json={"status": "PENDING_VALIDATION", "resolution": "Fixed issue."},
    )

    # PENDING_VALIDATION -> CLOSED directly must be BLOCKED
    res_val_close = client.post(
        f"/api/v1/findings/{f_id}/status",
        headers=headers,
        json={"status": "CLOSED"},
    )
    assert res_val_close.status_code == 400

    # Validate: PASS -> RESOLVED
    client.post(
        f"/api/v1/findings/{f_id}/validate",
        headers=headers,
        json={"is_valid": True, "validation_notes": "Passed tests."},
    )

    # RESOLVED -> OPEN must be BLOCKED
    res_res_to_open = client.post(
        f"/api/v1/findings/{f_id}/status",
        headers=headers,
        json={"status": "OPEN"},
    )
    assert res_res_to_open.status_code == 400

    # RESOLVED -> IN_REMEDIATION directly must be BLOCKED
    res_res_to_rem = client.post(
        f"/api/v1/findings/{f_id}/status",
        headers=headers,
        json={"status": "IN_REMEDIATION"},
    )
    assert res_res_to_rem.status_code == 400

    # Close: RESOLVED -> CLOSED
    res_close = client.post(
        f"/api/v1/findings/{f_id}/status",
        headers=headers,
        json={"status": "CLOSED"},
    )
    assert res_close.status_code == 200

    # CLOSED -> any status must be BLOCKED
    res_closed_to_open = client.post(
        f"/api/v1/findings/{f_id}/status",
        headers=headers,
        json={"status": "OPEN"},
    )
    assert res_closed_to_open.status_code == 400


def test_risk_acceptance_state_boundaries(
    client: TestClient, analyst_user: User, db: Session, seeded_framework
):
    headers = get_token_headers(analyst_user)
    controls = client.get("/api/v1/controls", headers=headers).json()
    ctrl_id = controls[0]["id"]

    # 1. Create finding (OPEN)
    res_find = client.post(
        "/api/v1/findings",
        headers=headers,
        json={
            "organization_control_id": ctrl_id,
            "title": "Risk Acceptance State Test",
            "description": "Desc",
            "recommendation": "Rec",
            "impact": 3,
            "likelihood": 3,
        },
    )
    f_id = res_find.json()["id"]

    # Move finding to IN_REMEDIATION -> PENDING_VALIDATION -> RESOLVED
    client.post(f"/api/v1/findings/{f_id}/status", headers=headers, json={"status": "IN_REMEDIATION"})
    client.post(f"/api/v1/findings/{f_id}/status", headers=headers, json={"status": "PENDING_VALIDATION", "resolution": "Remediated"})
    client.post(f"/api/v1/findings/{f_id}/validate", headers=headers, json={"is_valid": True, "validation_notes": "Validated"})

    # Attempt risk acceptance on RESOLVED finding -> must be BLOCKED
    res_acc_resolved = client.post(
        f"/api/v1/findings/{f_id}/risk-acceptance",
        headers=headers,
        json={"justification": "Trying to accept risk on resolved finding."},
    )
    assert res_acc_resolved.status_code == 400
    assert "Risk acceptance can only be performed on OPEN or IN_REMEDIATION findings" in res_acc_resolved.json()["detail"]


def test_cross_control_traceability_and_evidence_integrity(
    client: TestClient, analyst_user: User, db: Session, seeded_framework
):
    headers = get_token_headers(analyst_user)
    controls = client.get("/api/v1/controls", headers=headers).json()
    ctrl_a_id = controls[0]["id"]
    ctrl_b_id = controls[1]["id"]

    # 1. Upload evidence for Control A
    res_upload = client.post(
        "/api/v1/evidence/upload",
        headers=headers,
        data={"organization_control_id": str(ctrl_a_id), "title": "Control A Evidence"},
        files={"file": ("evidence_a.txt", io.BytesIO(b"Control A artifact"), "text/plain")},
    )
    ev_a_id = res_upload.json()["id"]

    # 2. Create Assessment for Control B
    res_ass_b = client.post(
        "/api/v1/assessments",
        headers=headers,
        json={"organization_control_id": ctrl_b_id, "summary": "Assessment on Control B"},
    )
    ass_b_id = res_ass_b.json()["id"]

    # Attempt: Link Evidence from Control A to Assessment of Control B -> REJECT
    res_link_cross_ass = client.post(
        f"/api/v1/assessments/{ass_b_id}/evidence",
        headers=headers,
        json={"evidence_id": ev_a_id},
    )
    assert res_link_cross_ass.status_code == 400
    assert "does not belong to the same control" in res_link_cross_ass.json()["detail"]

    # 3. Create Finding for Control B
    res_find_b = client.post(
        "/api/v1/findings",
        headers=headers,
        json={
            "organization_control_id": ctrl_b_id,
            "title": "Finding for Control B",
            "description": "Desc",
            "recommendation": "Rec",
            "impact": 2,
            "likelihood": 2,
        },
    )
    find_b_id = res_find_b.json()["id"]

    # Attempt: Link Evidence from Control A to Finding of Control B -> REJECT
    res_link_cross_find = client.post(
        f"/api/v1/findings/{find_b_id}/evidence",
        headers=headers,
        json={"evidence_id": ev_a_id},
    )
    assert res_link_cross_find.status_code == 400
    assert "does not belong to the same control" in res_link_cross_find.json()["detail"]

    # 4. Attempt: Create finding for Control B but attach to Assessment of Control A -> REJECT
    res_ass_a = client.post(
        "/api/v1/assessments",
        headers=headers,
        json={"organization_control_id": ctrl_a_id, "summary": "Assessment on Control A"},
    )
    ass_a_id = res_ass_a.json()["id"]

    res_mismatched_finding = client.post(
        "/api/v1/findings",
        headers=headers,
        json={
            "organization_control_id": ctrl_b_id,
            "assessment_id": ass_a_id,
            "title": "Mismatched Finding",
            "description": "Desc",
            "recommendation": "Rec",
            "impact": 2,
            "likelihood": 2,
        },
    )
    assert res_mismatched_finding.status_code == 400
    assert "does not belong to the specified control" in res_mismatched_finding.json()["detail"]


def test_superseded_evidence_linkage_blocked(
    client: TestClient, analyst_user: User, db: Session, seeded_framework
):
    headers = get_token_headers(analyst_user)
    controls = client.get("/api/v1/controls", headers=headers).json()
    ctrl_id = controls[0]["id"]

    # 1. Upload original evidence
    res_upload1 = client.post(
        "/api/v1/evidence/upload",
        headers=headers,
        data={"organization_control_id": str(ctrl_id), "title": "Old Log"},
        files={"file": ("old_log.txt", io.BytesIO(b"old log data"), "text/plain")},
    )
    ev_old_id = res_upload1.json()["id"]

    # 2. Upload replacement evidence
    res_upload2 = client.post(
        "/api/v1/evidence/upload",
        headers=headers,
        data={"organization_control_id": str(ctrl_id), "title": "New Log"},
        files={"file": ("new_log.txt", io.BytesIO(b"new log data"), "text/plain")},
    )
    ev_new_id = res_upload2.json()["id"]

    # 3. Supersede old evidence with new evidence
    res_super = client.post(
        f"/api/v1/evidence/{ev_old_id}/supersede?new_evidence_id={ev_new_id}",
        headers=headers,
    )
    assert res_super.status_code == 200

    # 4. Create Assessment
    res_ass = client.post(
        "/api/v1/assessments",
        headers=headers,
        json={"organization_control_id": ctrl_id, "summary": "Assessment for superseded test"},
    )
    ass_id = res_ass.json()["id"]

    # Attempt to link superseded evidence to assessment -> BLOCKED
    res_link_super_ass = client.post(
        f"/api/v1/assessments/{ass_id}/evidence",
        headers=headers,
        json={"evidence_id": ev_old_id},
    )
    assert res_link_super_ass.status_code == 400
    assert "Cannot link superseded evidence" in res_link_super_ass.json()["detail"]

    # 5. Create Finding
    res_find = client.post(
        "/api/v1/findings",
        headers=headers,
        json={
            "organization_control_id": ctrl_id,
            "title": "Finding for superseded test",
            "description": "Desc",
            "recommendation": "Rec",
            "impact": 2,
            "likelihood": 2,
        },
    )
    find_id = res_find.json()["id"]

    # Attempt to link superseded evidence to finding -> BLOCKED
    res_link_super_find = client.post(
        f"/api/v1/findings/{find_id}/evidence",
        headers=headers,
        json={"evidence_id": ev_old_id},
    )
    assert res_link_super_find.status_code == 400
    assert "Cannot link superseded evidence" in res_link_super_find.json()["detail"]


def test_risk_score_tampering_and_deterministic_recalculation(
    client: TestClient, analyst_user: User, db: Session, seeded_framework
):
    headers = get_token_headers(analyst_user)
    controls = client.get("/api/v1/controls", headers=headers).json()
    ctrl_id = controls[0]["id"]

    # 1. Tamper attempt on creation: L=1, I=1 with client claiming risk_score=25, risk_band=CRITICAL
    res_create_tamper = client.post(
        "/api/v1/findings",
        headers=headers,
        json={
            "organization_control_id": ctrl_id,
            "title": "Tampered Risk Finding",
            "description": "Desc",
            "recommendation": "Rec",
            "impact": 1,
            "likelihood": 1,
            "risk_score": 25,
            "risk_band": "CRITICAL",
        },
    )
    assert res_create_tamper.status_code == 201
    created_data = res_create_tamper.json()
    # Backend recalculates authoritative score: 1*1 = 1 (LOW)
    assert created_data["risk_score"] == 1
    assert created_data["risk_band"] == "LOW"
    f_id = created_data["id"]

    # 2. Update impact to 5, likelihood to 4 -> backend must recompute 5*4 = 20 (CRITICAL)
    res_patch = client.patch(
        f"/api/v1/findings/{f_id}",
        headers=headers,
        json={"impact": 5, "likelihood": 4},
    )
    assert res_patch.status_code == 200
    patched_data = res_patch.json()
    assert patched_data["risk_score"] == 20
    assert patched_data["risk_band"] == "CRITICAL"


def test_deterministic_risk_matrix_boundaries(
    client: TestClient, analyst_user: User, db: Session, seeded_framework
):
    from app.core.risk_engine import calculate_risk_score

    # Matrix Boundary Tests:
    # 1-4 = LOW
    assert calculate_risk_score(1, 1) == (1, "LOW")
    assert calculate_risk_score(1, 4) == (4, "LOW")
    assert calculate_risk_score(2, 2) == (4, "LOW")

    # 5-9 = MODERATE
    assert calculate_risk_score(1, 5) == (5, "MODERATE")
    assert calculate_risk_score(3, 3) == (9, "MODERATE")

    # 10-16 = HIGH
    assert calculate_risk_score(2, 5) == (10, "HIGH")
    assert calculate_risk_score(4, 4) == (16, "HIGH")

    # 17-25 = CRITICAL
    assert calculate_risk_score(4, 5) == (20, "CRITICAL")
    assert calculate_risk_score(5, 5) == (25, "CRITICAL")

    # Bounding enforcement on out-of-range values
    assert calculate_risk_score(0, 10) == (5, "MODERATE")  # bounded to 1 * 5 = 5
    assert calculate_risk_score(-5, 99) == (5, "MODERATE")  # bounded to 1 * 5 = 5


def test_overdue_due_date_calculation_logic():
    from app.core.risk_engine import calculate_overdue_status
    from app.models.finding import FindingStatusEnum

    ref_date = date(2026, 8, 25)

    # 1. Overdue: due yesterday
    assert calculate_overdue_status(FindingStatusEnum.OPEN, date(2026, 8, 24), ref_date) == "OVERDUE"

    # 2. Due today (within 7 days)
    assert calculate_overdue_status(FindingStatusEnum.OPEN, date(2026, 8, 25), ref_date) == "DUE_SOON"

    # 3. Due in 7 days
    assert calculate_overdue_status(FindingStatusEnum.IN_REMEDIATION, date(2026, 9, 1), ref_date) == "DUE_SOON"

    # 4. Due in 8 days
    assert calculate_overdue_status(FindingStatusEnum.IN_REMEDIATION, date(2026, 9, 2), ref_date) == "ON_TRACK"

    # 5. No due date
    assert calculate_overdue_status(FindingStatusEnum.OPEN, None, ref_date) == "NO_DUE_DATE"

    # 6. Terminal status (RESOLVED, ACCEPTED_RISK, CLOSED) is COMPLETED regardless of date
    assert calculate_overdue_status(FindingStatusEnum.RESOLVED, date(2020, 1, 1), ref_date) == "COMPLETED"
    assert calculate_overdue_status(FindingStatusEnum.ACCEPTED_RISK, date(2020, 1, 1), ref_date) == "COMPLETED"
    assert calculate_overdue_status(FindingStatusEnum.CLOSED, date(2020, 1, 1), ref_date) == "COMPLETED"

