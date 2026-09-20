from datetime import datetime, timezone, timedelta, date
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.control import ImplementationStatusEnum, OrganizationControl
from app.models.framework import Framework, FrameworkCategory, FrameworkFunction, FrameworkSubcategory
from app.models.kri import (
    AppetiteStatementStatusEnum,
    BreachStatusEnum,
    KeyRiskIndicator,
    KriBreachRecord,
    KriDirectionEnum,
    KriEvaluationStatusEnum,
    KriFrequencyEnum,
    KriObservation,
    KriRiskLink,
    KriSourceTypeEnum,
    KriStatusEnum,
    KriThreshold,
    RiskAppetiteStatement,
)
from app.models.organization import Organization
from app.models.quant_risk import FinancialRiskAppetite
from app.models.risk import Risk, RiskCategoryEnum
from app.models.user import User


@pytest.fixture
def kri_test_env(db: Session, client: TestClient):
    # Org A
    org_a = Organization(name="Tenant Alpha", slug="alpha")
    db.add(org_a)
    db.flush()

    user_admin_a = User(
        organization_id=org_a.id,
        email="admin@alpha.example.com",
        full_name="Alpha Admin",
        hashed_password="hash",
        role="ADMIN",
    )
    user_mgr_a = User(
        organization_id=org_a.id,
        email="mgr@alpha.example.com",
        full_name="Alpha Manager",
        hashed_password="hash",
        role="MANAGER",
    )
    user_analyst_a = User(
        organization_id=org_a.id,
        email="analyst@alpha.example.com",
        full_name="Alpha Analyst",
        hashed_password="hash",
        role="GRC_ANALYST",
    )
    user_sec_a = User(
        organization_id=org_a.id,
        email="sec@alpha.example.com",
        full_name="Alpha Sec Analyst",
        hashed_password="hash",
        role="SECURITY_ANALYST",
    )
    user_auditor_a = User(
        organization_id=org_a.id,
        email="auditor@alpha.example.com",
        full_name="Alpha Auditor",
        hashed_password="hash",
        role="AUDITOR",
    )
    user_viewer_a = User(
        organization_id=org_a.id,
        email="viewer@alpha.example.com",
        full_name="Alpha Viewer",
        hashed_password="hash",
        role="VIEWER",
    )
    db.add_all([user_admin_a, user_mgr_a, user_analyst_a, user_sec_a, user_auditor_a, user_viewer_a])
    db.flush()

    # Org B (Attacker / Foreign Tenant)
    org_b = Organization(name="Tenant Beta", slug="beta")
    db.add(org_b)
    db.flush()

    user_admin_b = User(
        organization_id=org_b.id,
        email="admin@beta.example.com",
        full_name="Beta Admin",
        hashed_password="hash",
        role="ADMIN",
    )
    db.add(user_admin_b)
    db.flush()

    # Framework and subcategories for controls
    fw = db.query(Framework).filter_by(identifier="KRI-SEC-FW").first()
    if not fw:
        fw = Framework(identifier="KRI-SEC-FW", name="KRI Framework", version="1.0")
        db.add(fw)
        db.flush()
        fn = FrameworkFunction(framework_id=fw.id, identifier="PR", name="Protect")
        db.add(fn)
        db.flush()
        cat = FrameworkCategory(function_id=fn.id, identifier="PR.AC", name="Access Control")
        db.add(cat)
        db.flush()
        subcat_a = FrameworkSubcategory(category_id=cat.id, identifier="PR.AC-01", title="Least Privilege", description="Enforce least privilege")
        subcat_b = FrameworkSubcategory(category_id=cat.id, identifier="PR.AC-02", title="Account Management", description="Manage user accounts")
        db.add_all([subcat_a, subcat_b])
        db.flush()
    else:
        subcat_a = db.query(FrameworkSubcategory).filter_by(identifier="PR.AC-01").first()
        subcat_b = db.query(FrameworkSubcategory).filter_by(identifier="PR.AC-02").first()

    # Pre-populate Org A control & risk
    ctrl_a = OrganizationControl(
        organization_id=org_a.id,
        subcategory_id=subcat_a.id,
        status=ImplementationStatusEnum.IMPLEMENTED,
        implementation_statement="Enforce least privilege access.",
    )
    risk_a = Risk(
        organization_id=org_a.id,
        title="Unauthorized Access Vulnerability",
        description="Excessive privileges in production environment.",
        risk_category=RiskCategoryEnum.CYBERSECURITY,
        inherent_impact=4,
        inherent_likelihood=4,
        inherent_score=16,
        inherent_band="HIGH",
        target_risk_band="MODERATE",
    )
    db.add_all([ctrl_a, risk_a])

    # Pre-populate Org B control & risk
    ctrl_b = OrganizationControl(
        organization_id=org_b.id,
        subcategory_id=subcat_b.id,
        status=ImplementationStatusEnum.IMPLEMENTED,
        implementation_statement="Foreign control.",
    )
    risk_b = Risk(
        organization_id=org_b.id,
        title="Beta Risk",
        description="Foreign risk.",
        risk_category=RiskCategoryEnum.OPERATIONAL,
    )
    fin_appetite_b = FinancialRiskAppetite(
        organization_id=org_b.id,
        version=1,
        ale_limit=500000.0,
        var_95_limit=1000000.0,
        requested_by_id=user_admin_b.id,
    )
    db.add_all([ctrl_b, risk_b, fin_appetite_b])
    db.commit()

    tokens = {
        "admin_a": create_access_token(
            subject=user_admin_a.id,
            organization_id=org_a.id,
            role=user_admin_a.role.value if hasattr(user_admin_a.role, "value") else str(user_admin_a.role),
        ),
        "mgr_a": create_access_token(
            subject=user_mgr_a.id,
            organization_id=org_a.id,
            role=user_mgr_a.role.value if hasattr(user_mgr_a.role, "value") else str(user_mgr_a.role),
        ),
        "analyst_a": create_access_token(
            subject=user_analyst_a.id,
            organization_id=org_a.id,
            role=user_analyst_a.role.value if hasattr(user_analyst_a.role, "value") else str(user_analyst_a.role),
        ),
        "sec_a": create_access_token(
            subject=user_sec_a.id,
            organization_id=org_a.id,
            role=user_sec_a.role.value if hasattr(user_sec_a.role, "value") else str(user_sec_a.role),
        ),
        "auditor_a": create_access_token(
            subject=user_auditor_a.id,
            organization_id=org_a.id,
            role=user_auditor_a.role.value if hasattr(user_auditor_a.role, "value") else str(user_auditor_a.role),
        ),
        "viewer_a": create_access_token(
            subject=user_viewer_a.id,
            organization_id=org_a.id,
            role=user_viewer_a.role.value if hasattr(user_viewer_a.role, "value") else str(user_viewer_a.role),
        ),
        "admin_b": create_access_token(
            subject=user_admin_b.id,
            organization_id=org_b.id,
            role=user_admin_b.role.value if hasattr(user_admin_b.role, "value") else str(user_admin_b.role),
        ),
    }

    return {
        "org_a": org_a,
        "org_b": org_b,
        "users_a": {
            "admin": user_admin_a,
            "mgr": user_mgr_a,
            "analyst": user_analyst_a,
            "sec": user_sec_a,
            "auditor": user_auditor_a,
            "viewer": user_viewer_a,
        },
        "users_b": {"admin": user_admin_b},
        "ctrl_a": ctrl_a,
        "ctrl_b": ctrl_b,
        "risk_a": risk_a,
        "risk_b": risk_b,
        "fin_appetite_b": fin_appetite_b,
        "tokens": tokens,
    }


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ─────────────────────────────────────────────────────────────────────────────
# ADVERSARIAL TEST SUITE: SEC-B2-01 through SEC-B2-30
# ─────────────────────────────────────────────────────────────────────────────

def test_sec_b2_01_cross_tenant_appetite_read(client: TestClient, kri_test_env):
    """SEC-B2-01: Cross-Tenant Appetite Read yields HTTP 404 (anti-enumeration)."""
    headers_a = auth_header(kri_test_env["tokens"]["analyst_a"])
    headers_b = auth_header(kri_test_env["tokens"]["admin_b"])

    # Org A creates statement
    payload = {
        "statement_code": "APP-ALPHA-01",
        "title": "Alpha Risk Appetite",
        "executive_summary": "Confidential internal board risk policy.",
        "category_appetites": {"CYBERSECURITY": "LOW"},
        "effective_from": "2026-01-01",
    }
    r_create = client.post("/api/v1/kri/appetite-statements", json=payload, headers=headers_a)
    assert r_create.status_code == 201
    stmt_id = r_create.json()["id"]

    # Org B attempts to read Org A statement
    r_foreign = client.get(f"/api/v1/kri/appetite-statements/{stmt_id}", headers=headers_b)
    assert r_foreign.status_code == 404


def test_sec_b2_02_cross_tenant_observation_ingestion(client: TestClient, kri_test_env):
    """SEC-B2-02: Tenant B attempts to ingest telemetry into Tenant A KRI."""
    headers_a = auth_header(kri_test_env["tokens"]["analyst_a"])
    headers_b = auth_header(kri_test_env["tokens"]["admin_b"])

    # Create KRI in Org A
    kri_payload = {
        "kri_code": "KRI-SEC-01",
        "title": "Unpatched Vulnerabilities",
        "description": "Count of critical CVEs",
        "risk_category": "CYBERSECURITY",
        "unit_of_measure": "COUNT",
        "direction": "LOWER_IS_BETTER",
        "initial_threshold": {"warning_threshold": 10.0, "critical_threshold": 25.0},
    }
    r_kri = client.post("/api/v1/kri/indicators", json=kri_payload, headers=headers_a)
    assert r_kri.status_code == 201
    kri_id = r_kri.json()["id"]

    # Org B attempts to post observation
    obs_payload = {
        "observed_value": 30.0,
        "unit": "COUNT",
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }
    r_obs = client.post(f"/api/v1/kri/indicators/{kri_id}/observations", json=obs_payload, headers=headers_b)
    assert r_obs.status_code == 404


def test_sec_b2_03_jwt_org_id_tampering(client: TestClient, kri_test_env):
    """SEC-B2-03: Injected organization_id=999 in payload is ignored; scoped to JWT."""
    headers = auth_header(kri_test_env["tokens"]["analyst_a"])
    payload = {
        "organization_id": 99999,  # Injected foreign org ID
        "statement_code": "APP-TAMPER-01",
        "title": "Tampered Appetite",
        "executive_summary": "Testing JWT override.",
        "category_appetites": {"OPERATIONAL": "MODERATE"},
        "effective_from": "2026-01-01",
    }
    res = client.post("/api/v1/kri/appetite-statements", json=payload, headers=headers)
    assert res.status_code == 201
    # Server must assign user's genuine org ID, not 99999
    assert res.json()["organization_id"] == kri_test_env["org_a"].id


def test_sec_b2_04_appetite_self_approval_blocked(client: TestClient, kri_test_env):
    """SEC-B2-04: Four-Eyes SoD blocks user from approving their own appetite statement."""
    headers_mgr = auth_header(kri_test_env["tokens"]["mgr_a"])

    # Manager creates statement
    payload = {
        "statement_code": "APP-MGR-01",
        "title": "Manager Appetite",
        "executive_summary": "Self-approval exploit attempt.",
        "category_appetites": {"FINANCIAL": "LOW"},
        "effective_from": "2026-01-01",
    }
    r_create = client.post("/api/v1/kri/appetite-statements", json=payload, headers=headers_mgr)
    assert r_create.status_code == 201
    stmt_id = r_create.json()["id"]

    # Same manager attempts to approve
    r_approve = client.post(f"/api/v1/kri/appetite-statements/{stmt_id}/approve", headers=headers_mgr)
    assert r_approve.status_code == 400
    assert "Four-Eyes Violation" in r_approve.json()["detail"]


def test_sec_b2_05_breach_self_closure_blocked(client: TestClient, kri_test_env):
    """SEC-B2-05: Analyst who acknowledged breach cannot close it."""
    headers_analyst = auth_header(kri_test_env["tokens"]["analyst_a"])
    headers_mgr = auth_header(kri_test_env["tokens"]["mgr_a"])

    # Create KRI & breach
    kri_payload = {
        "kri_code": "KRI-SOD-01",
        "title": "Failed Access Reviews",
        "description": "Delinquent reviews",
        "risk_category": "COMPLIANCE",
        "unit_of_measure": "COUNT",
        "direction": "LOWER_IS_BETTER",
        "initial_threshold": {"warning_threshold": 2.0, "critical_threshold": 5.0},
    }
    kri_id = client.post("/api/v1/kri/indicators", json=kri_payload, headers=headers_analyst).json()["id"]

    obs_payload = {
        "observed_value": 10.0,
        "unit": "COUNT",
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }
    obs_res = client.post(f"/api/v1/kri/indicators/{kri_id}/observations", json=obs_payload, headers=headers_analyst).json()
    breach_id = obs_res["breach_id"]

    # Manager acknowledges
    client.post(f"/api/v1/kri/breaches/{breach_id}/acknowledge", json={"notes": "Investigating"}, headers=headers_mgr)

    # Same manager attempts to close -> Four-Eyes violation
    r_close = client.post(
        f"/api/v1/kri/breaches/{breach_id}/close",
        json={"closure_notes": "Attempting self closure"},
        headers=headers_mgr,
    )
    assert r_close.status_code == 400
    assert "Four-Eyes Violation" in r_close.json()["detail"]


def test_sec_b2_06_kri_owner_self_closure_blocked(client: TestClient, kri_test_env):
    """SEC-B2-06: KRI owner cannot self-close breaches for their own metric."""
    headers_admin = auth_header(kri_test_env["tokens"]["admin_a"])
    headers_mgr = auth_header(kri_test_env["tokens"]["mgr_a"])
    headers_analyst = auth_header(kri_test_env["tokens"]["analyst_a"])

    mgr_id = kri_test_env["users_a"]["mgr"].id

    # Create KRI owned by Manager A
    kri_payload = {
        "kri_code": "KRI-OWNER-01",
        "title": "Owner Delinquency",
        "description": "Owner SoD test",
        "risk_category": "OPERATIONAL",
        "unit_of_measure": "COUNT",
        "owner_id": mgr_id,
        "direction": "LOWER_IS_BETTER",
        "initial_threshold": {"warning_threshold": 1.0, "critical_threshold": 3.0},
    }
    kri_id = client.post("/api/v1/kri/indicators", json=kri_payload, headers=headers_admin).json()["id"]

    # Breach
    obs_res = client.post(
        f"/api/v1/kri/indicators/{kri_id}/observations",
        json={"observed_value": 8.0, "unit": "COUNT", "observed_at": datetime.now(timezone.utc).isoformat()},
        headers=headers_analyst,
    ).json()
    breach_id = obs_res["breach_id"]

    # Analyst acknowledges
    client.post(f"/api/v1/kri/breaches/{breach_id}/acknowledge", json={"notes": "Acked"}, headers=headers_analyst)

    # Manager (who is KRI owner) attempts to close
    r_close = client.post(
        f"/api/v1/kri/breaches/{breach_id}/close",
        json={"closure_notes": "I own this KRI and want to close it"},
        headers=headers_mgr,
    )
    assert r_close.status_code == 400
    assert "KRI owner cannot self-close" in r_close.json()["detail"]


def test_sec_b2_07_forward_dated_observation_rejected(client: TestClient, kri_test_env):
    """SEC-B2-07: Observation with future timestamp (>60s) is rejected with HTTP 422."""
    headers = auth_header(kri_test_env["tokens"]["analyst_a"])
    kri_payload = {
        "kri_code": "KRI-TIME-01",
        "title": "Time Test",
        "description": "Timestamp validation",
        "risk_category": "OPERATIONAL",
        "unit_of_measure": "COUNT",
        "initial_threshold": {"warning_threshold": 5.0, "critical_threshold": 10.0},
    }
    kri_id = client.post("/api/v1/kri/indicators", json=kri_payload, headers=headers).json()["id"]

    future_time = datetime.now(timezone.utc) + timedelta(days=5)
    obs_payload = {
        "observed_value": 7.0,
        "unit": "COUNT",
        "observed_at": future_time.isoformat(),
    }
    res = client.post(f"/api/v1/kri/indicators/{kri_id}/observations", json=obs_payload, headers=headers)
    assert res.status_code == 422


def test_sec_b2_08_observation_in_place_mutation_blocked(client: TestClient, kri_test_env):
    """SEC-B2-08: Attempt to mutate observation in-place returns 405 Method Not Allowed."""
    headers = auth_header(kri_test_env["tokens"]["analyst_a"])
    res = client.put("/api/v1/kri/indicators/1/observations/1", json={"observed_value": 99.0}, headers=headers)
    assert res.status_code == 405


def test_sec_b2_09_observation_deletion_blocked(client: TestClient, kri_test_env):
    """SEC-B2-09: Attempt to delete observation returns 405 Method Not Allowed."""
    headers = auth_header(kri_test_env["tokens"]["analyst_a"])
    res = client.delete("/api/v1/kri/indicators/1/observations/1", headers=headers)
    assert res.status_code == 405


def test_sec_b2_10_replayed_ingestion_flood(client: TestClient, kri_test_env):
    """SEC-B2-10: Idempotency key de-duplicates replayed observation payloads."""
    headers = auth_header(kri_test_env["tokens"]["analyst_a"])
    kri_payload = {
        "kri_code": "KRI-IDEMP-01",
        "title": "Idempotency Test",
        "description": "Replay testing",
        "risk_category": "CYBERSECURITY",
        "unit_of_measure": "COUNT",
        "initial_threshold": {"warning_threshold": 5.0, "critical_threshold": 10.0},
    }
    kri_id = client.post("/api/v1/kri/indicators", json=kri_payload, headers=headers).json()["id"]

    now = datetime.now(timezone.utc).isoformat()
    obs_payload = {
        "observed_value": 8.0,
        "unit": "COUNT",
        "observed_at": now,
        "idempotency_key": "IDEMP-KEY-9999",
    }
    r1 = client.post(f"/api/v1/kri/indicators/{kri_id}/observations", json=obs_payload, headers=headers)
    r2 = client.post(f"/api/v1/kri/indicators/{kri_id}/observations", json=obs_payload, headers=headers)

    assert r1.status_code == 201
    assert r2.status_code == 201
    # Both responses point to identical observation ID
    assert r1.json()["id"] == r2.json()["id"]


def test_sec_b2_11_illegal_breach_transition_direct_close_blocked(client: TestClient, kri_test_env):
    """SEC-B2-11: Attempt to close freshly DETECTED breach directly returns HTTP 400."""
    headers_analyst = auth_header(kri_test_env["tokens"]["analyst_a"])
    headers_admin = auth_header(kri_test_env["tokens"]["admin_a"])

    kri_payload = {
        "kri_code": "KRI-TRANS-01",
        "title": "Transition Test",
        "description": "Testing illegal state shortcut",
        "risk_category": "OPERATIONAL",
        "unit_of_measure": "COUNT",
        "initial_threshold": {"warning_threshold": 2.0, "critical_threshold": 4.0},
    }
    kri_id = client.post("/api/v1/kri/indicators", json=kri_payload, headers=headers_analyst).json()["id"]

    obs_res = client.post(
        f"/api/v1/kri/indicators/{kri_id}/observations",
        json={"observed_value": 8.0, "unit": "COUNT", "observed_at": datetime.now(timezone.utc).isoformat()},
        headers=headers_analyst,
    ).json()
    breach_id = obs_res["breach_id"]

    # Direct close without acknowledgement or recovery
    r_close = client.post(
        f"/api/v1/kri/breaches/{breach_id}/close",
        json={"closure_notes": "Attempting illegal immediate close"},
        headers=headers_admin,
    )
    assert r_close.status_code == 400
    assert "Illegal transition" in r_close.json()["detail"]


def test_sec_b2_12_cross_tenant_risk_linkage_rejected(client: TestClient, kri_test_env):
    """SEC-B2-12: Org A attempts to link KRI to Org B Risk -> HTTP 404."""
    headers_a = auth_header(kri_test_env["tokens"]["analyst_a"])
    foreign_risk_id = kri_test_env["risk_b"].id

    kri_payload = {
        "kri_code": "KRI-LINK-01",
        "title": "Linkage Test",
        "description": "Cross tenant link",
        "risk_category": "OPERATIONAL",
        "unit_of_measure": "COUNT",
    }
    kri_id = client.post("/api/v1/kri/indicators", json=kri_payload, headers=headers_a).json()["id"]

    res = client.post(
        f"/api/v1/kri/indicators/{kri_id}/link-risk",
        json={"risk_id": foreign_risk_id, "correlation_weight": 0.5},
        headers=headers_a,
    )
    assert res.status_code == 404


def test_sec_b2_13_duplicate_finding_escalation_blocked(client: TestClient, kri_test_env):
    """SEC-B2-13: Re-escalating an already escalated breach returns HTTP 409 Conflict."""
    headers = auth_header(kri_test_env["tokens"]["analyst_a"])
    ctrl_id = kri_test_env["ctrl_a"].id

    kri_payload = {
        "kri_code": "KRI-ESC-01",
        "title": "Escalation Test",
        "description": "Duplicate escalation testing",
        "risk_category": "CYBERSECURITY",
        "unit_of_measure": "COUNT",
        "initial_threshold": {"warning_threshold": 1.0, "critical_threshold": 2.0},
    }
    kri_id = client.post("/api/v1/kri/indicators", json=kri_payload, headers=headers).json()["id"]
    obs_res = client.post(
        f"/api/v1/kri/indicators/{kri_id}/observations",
        json={"observed_value": 5.0, "unit": "COUNT", "observed_at": datetime.now(timezone.utc).isoformat()},
        headers=headers,
    ).json()
    breach_id = obs_res["breach_id"]

    # First escalation
    r1 = client.post(
        f"/api/v1/kri/breaches/{breach_id}/escalate-finding",
        json={"organization_control_id": ctrl_id, "title": "Deficiency 1"},
        headers=headers,
    )
    assert r1.status_code == 200

    # Second escalation attempt
    r2 = client.post(
        f"/api/v1/kri/breaches/{breach_id}/escalate-finding",
        json={"organization_control_id": ctrl_id, "title": "Deficiency 2"},
        headers=headers,
    )
    assert r2.status_code == 409


def test_sec_b2_14_escalation_without_control_rejected(client: TestClient, kri_test_env):
    """SEC-B2-14: Escalation without valid control ID returns HTTP 404 or 422."""
    headers = auth_header(kri_test_env["tokens"]["analyst_a"])

    kri_payload = {
        "kri_code": "KRI-ESC-02",
        "title": "Escalation Control Test",
        "description": "Missing control",
        "risk_category": "CYBERSECURITY",
        "unit_of_measure": "COUNT",
        "initial_threshold": {"warning_threshold": 1.0, "critical_threshold": 2.0},
    }
    kri_id = client.post("/api/v1/kri/indicators", json=kri_payload, headers=headers).json()["id"]
    obs_res = client.post(
        f"/api/v1/kri/indicators/{kri_id}/observations",
        json={"observed_value": 5.0, "unit": "COUNT", "observed_at": datetime.now(timezone.utc).isoformat()},
        headers=headers,
    ).json()
    breach_id = obs_res["breach_id"]

    # Non-existent control ID 99999
    res = client.post(
        f"/api/v1/kri/breaches/{breach_id}/escalate-finding",
        json={"organization_control_id": 99999, "title": "Orphan Finding"},
        headers=headers,
    )
    assert res.status_code == 404


def test_sec_b2_15_negative_threshold_inversion_rejected(client: TestClient, kri_test_env):
    """SEC-B2-15: Inverting thresholds (warning >= critical for LOWER_IS_BETTER) yields 422."""
    headers = auth_header(kri_test_env["tokens"]["analyst_a"])
    payload = {
        "kri_code": "KRI-INV-01",
        "title": "Inverted Threshold",
        "description": "Testing inversion",
        "risk_category": "OPERATIONAL",
        "unit_of_measure": "COUNT",
        "direction": "LOWER_IS_BETTER",
        "initial_threshold": {"warning_threshold": 50.0, "critical_threshold": 20.0},  # Inverted!
    }
    res = client.post("/api/v1/kri/indicators", json=payload, headers=headers)
    assert res.status_code == 422


def test_sec_b2_16_viewer_role_breach_acknowledgement_blocked(client: TestClient, kri_test_env):
    """SEC-B2-16: VIEWER role cannot acknowledge breaches -> HTTP 403."""
    headers_viewer = auth_header(kri_test_env["tokens"]["viewer_a"])
    res = client.post("/api/v1/kri/breaches/1/acknowledge", json={"notes": "Viewer Ack"}, headers=headers_viewer)
    assert res.status_code == 403


def test_sec_b2_17_auditor_role_threshold_tampering_blocked(client: TestClient, kri_test_env):
    """SEC-B2-17: AUDITOR role cannot modify thresholds -> HTTP 403."""
    headers_auditor = auth_header(kri_test_env["tokens"]["auditor_a"])
    payload = {"warning_threshold": 1.0, "critical_threshold": 2.0}
    res = client.post("/api/v1/kri/indicators/1/thresholds", json=payload, headers=headers_auditor)
    assert res.status_code == 403


def test_sec_b2_18_nan_observation_value_rejected(client: TestClient, kri_test_env):
    """SEC-B2-18: NaN observation value returns HTTP 422."""
    headers = {**auth_header(kri_test_env["tokens"]["analyst_a"]), "Content-Type": "application/json"}
    content = b'{"observed_value": "NaN", "unit": "COUNT", "observed_at": "2026-01-01T00:00:00Z"}'
    res = client.post("/api/v1/kri/indicators/1/observations", content=content, headers=headers)
    assert res.status_code == 422


def test_sec_b2_19_infinity_observation_value_rejected(client: TestClient, kri_test_env):
    """SEC-B2-19: Infinity observation value returns HTTP 422."""
    headers = {**auth_header(kri_test_env["tokens"]["analyst_a"]), "Content-Type": "application/json"}
    content = b'{"observed_value": "Infinity", "unit": "COUNT", "observed_at": "2026-01-01T00:00:00Z"}'
    res = client.post("/api/v1/kri/indicators/1/observations", content=content, headers=headers)
    assert res.status_code == 422


def test_sec_b2_20_unit_mismatch_injection_rejected(client: TestClient, kri_test_env):
    """SEC-B2-20: Mismatched unit of measure rejected with HTTP 422."""
    headers = auth_header(kri_test_env["tokens"]["analyst_a"])
    kri_payload = {
        "kri_code": "KRI-UNIT-01",
        "title": "Unit Test",
        "description": "Unit validation",
        "risk_category": "OPERATIONAL",
        "unit_of_measure": "PERCENTAGE",
        "initial_threshold": {"warning_threshold": 5.0, "critical_threshold": 10.0},
    }
    kri_id = client.post("/api/v1/kri/indicators", json=kri_payload, headers=headers).json()["id"]

    # Ingest with wrong unit "GIGABYTES"
    obs_payload = {
        "observed_value": 7.0,
        "unit": "GIGABYTES",
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }
    res = client.post(f"/api/v1/kri/indicators/{kri_id}/observations", json=obs_payload, headers=headers)
    assert res.status_code == 422
    assert "Unit mismatch" in res.json()["detail"]


def test_sec_b2_21_correlation_weight_out_of_bounds_rejected(client: TestClient, kri_test_env):
    """SEC-B2-21: Correlation weight > 1.0 or < -1.0 returns HTTP 422."""
    headers = auth_header(kri_test_env["tokens"]["analyst_a"])
    risk_id = kri_test_env["risk_a"].id

    kri_payload = {
        "kri_code": "KRI-WEIGHT-01",
        "title": "Weight Test",
        "description": "Weight validation",
        "risk_category": "OPERATIONAL",
        "unit_of_measure": "COUNT",
    }
    kri_id = client.post("/api/v1/kri/indicators", json=kri_payload, headers=headers).json()["id"]

    res = client.post(
        f"/api/v1/kri/indicators/{kri_id}/link-risk",
        json={"risk_id": risk_id, "correlation_weight": 2.5},
        headers=headers,
    )
    assert res.status_code == 422


def test_sec_b2_22_concurrent_telemetry_anti_flapping(client: TestClient, kri_test_env):
    """SEC-B2-22: Repeated critical observations maintain a single active breach record."""
    headers = auth_header(kri_test_env["tokens"]["analyst_a"])
    kri_payload = {
        "kri_code": "KRI-FLAP-01",
        "title": "Anti Flap Test",
        "description": "Flapping test",
        "risk_category": "CYBERSECURITY",
        "unit_of_measure": "COUNT",
        "initial_threshold": {"warning_threshold": 5.0, "critical_threshold": 10.0},
    }
    kri_id = client.post("/api/v1/kri/indicators", json=kri_payload, headers=headers).json()["id"]

    for val in [15.0, 20.0, 18.0, 25.0]:
        client.post(
            f"/api/v1/kri/indicators/{kri_id}/observations",
            json={"observed_value": val, "unit": "COUNT", "observed_at": datetime.now(timezone.utc).isoformat()},
            headers=headers,
        )

    # Only 1 breach record should exist
    breaches_res = client.get(f"/api/v1/kri/breaches?kri_id={kri_id}", headers=headers).json()
    assert len(breaches_res) == 1
    assert breaches_res[0]["peak_value"] == 25.0


def test_sec_b2_23_stale_data_masking_detected(db: Session, client: TestClient, kri_test_env):
    """SEC-B2-23: Stale telemetry is automatically flagged as STALE_DATA."""
    headers = auth_header(kri_test_env["tokens"]["analyst_a"])
    kri_payload = {
        "kri_code": "KRI-STALE-01",
        "title": "Stale KRI Test",
        "description": "Stale test",
        "risk_category": "OPERATIONAL",
        "unit_of_measure": "COUNT",
        "frequency": "HOURLY",  # Stale after 1.5h
        "initial_threshold": {"warning_threshold": 5.0, "critical_threshold": 10.0},
    }
    kri_id = client.post("/api/v1/kri/indicators", json=kri_payload, headers=headers).json()["id"]

    # Ingest observation dated 3 hours ago
    past_time = datetime.now(timezone.utc) - timedelta(hours=3)
    client.post(
        f"/api/v1/kri/indicators/{kri_id}/observations",
        json={"observed_value": 2.0, "unit": "COUNT", "observed_at": past_time.isoformat()},
        headers=headers,
    )

    # Fetch KRI -> auto transitions to STALE_DATA
    kri_res = client.get(f"/api/v1/kri/indicators/{kri_id}", headers=headers).json()
    assert kri_res["status"] == "STALE_DATA"


def test_sec_b2_24_provenance_hash_forgery_prevented(client: TestClient, kri_test_env):
    """SEC-B2-24: Injected client hash is ignored; server calculates authoritative SHA-256."""
    headers = auth_header(kri_test_env["tokens"]["analyst_a"])
    kri_payload = {
        "kri_code": "KRI-HASH-01",
        "title": "Hash Integrity",
        "description": "Hash test",
        "risk_category": "OPERATIONAL",
        "unit_of_measure": "COUNT",
        "initial_threshold": {"warning_threshold": 5.0, "critical_threshold": 10.0},
    }
    kri_id = client.post("/api/v1/kri/indicators", json=kri_payload, headers=headers).json()["id"]

    obs_payload = {
        "observed_value": 3.0,
        "unit": "COUNT",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "data_hash_sha256": "forged_fake_hash_12345",
    }
    res = client.post(f"/api/v1/kri/indicators/{kri_id}/observations", json=obs_payload, headers=headers)
    assert res.status_code == 201
    assert res.json()["data_hash_sha256"] != "forged_fake_hash_12345"
    assert len(res.json()["data_hash_sha256"]) == 64


def test_sec_b2_25_appetite_re_approval_blocked(client: TestClient, kri_test_env):
    """SEC-B2-25: Re-approving an already approved statement returns HTTP 400."""
    headers_analyst = auth_header(kri_test_env["tokens"]["analyst_a"])
    headers_mgr = auth_header(kri_test_env["tokens"]["mgr_a"])

    payload = {
        "statement_code": "APP-REAPP-01",
        "title": "Re-Approval Test",
        "executive_summary": "Testing re-approval.",
        "category_appetites": {"CYBERSECURITY": "LOW"},
        "effective_from": "2026-01-01",
    }
    stmt_id = client.post("/api/v1/kri/appetite-statements", json=payload, headers=headers_analyst).json()["id"]
    client.post(f"/api/v1/kri/appetite-statements/{stmt_id}/approve", headers=headers_mgr)

    # Second approval attempt
    r2 = client.post(f"/api/v1/kri/appetite-statements/{stmt_id}/approve", headers=headers_mgr)
    assert r2.status_code == 400


def test_sec_b2_26_cross_tenant_breach_query_rejected(client: TestClient, kri_test_env):
    """SEC-B2-26: Tenant B cannot query Tenant A breach record -> HTTP 404."""
    headers_a = auth_header(kri_test_env["tokens"]["analyst_a"])
    headers_b = auth_header(kri_test_env["tokens"]["admin_b"])

    kri_payload = {
        "kri_code": "KRI-CT-01",
        "title": "Cross Tenant Breach",
        "description": "Testing breach query",
        "risk_category": "CYBERSECURITY",
        "unit_of_measure": "COUNT",
        "initial_threshold": {"warning_threshold": 1.0, "critical_threshold": 2.0},
    }
    kri_id = client.post("/api/v1/kri/indicators", json=kri_payload, headers=headers_a).json()["id"]
    obs_res = client.post(
        f"/api/v1/kri/indicators/{kri_id}/observations",
        json={"observed_value": 10.0, "unit": "COUNT", "observed_at": datetime.now(timezone.utc).isoformat()},
        headers=headers_a,
    ).json()
    breach_id = obs_res["breach_id"]

    r_foreign = client.get(f"/api/v1/kri/breaches/{breach_id}", headers=headers_b)
    assert r_foreign.status_code == 404


def test_sec_b2_27_orphaned_breach_closure_without_notes_rejected(client: TestClient, kri_test_env):
    """SEC-B2-27: Closing breach with missing or empty notes returns HTTP 422."""
    headers = auth_header(kri_test_env["tokens"]["admin_a"])
    res = client.post("/api/v1/kri/breaches/1/close", json={"closure_notes": "   "}, headers=headers)
    assert res.status_code == 422


def test_sec_b2_28_inactive_kri_observation_rejected(client: TestClient, kri_test_env):
    """SEC-B2-28: Ingesting observation into INACTIVE KRI returns HTTP 400."""
    headers = auth_header(kri_test_env["tokens"]["analyst_a"])
    kri_payload = {
        "kri_code": "KRI-INACT-01",
        "title": "Inactive Test",
        "description": "Inactive KRI",
        "risk_category": "OPERATIONAL",
        "unit_of_measure": "COUNT",
        "initial_threshold": {"warning_threshold": 5.0, "critical_threshold": 10.0},
    }
    kri_id = client.post("/api/v1/kri/indicators", json=kri_payload, headers=headers).json()["id"]

    # Deactivate KRI
    client.put(f"/api/v1/kri/indicators/{kri_id}", json={"status": "INACTIVE"}, headers=headers)

    # Ingest observation
    res = client.post(
        f"/api/v1/kri/indicators/{kri_id}/observations",
        json={"observed_value": 3.0, "unit": "COUNT", "observed_at": datetime.now(timezone.utc).isoformat()},
        headers=headers,
    )
    assert res.status_code == 400
    assert "INACTIVE" in res.json()["detail"]


def test_sec_b2_29_cross_tenant_financial_appetite_link_rejected(client: TestClient, kri_test_env):
    """SEC-B2-29: Tenant A cannot link Tenant B FinancialRiskAppetite -> HTTP 404."""
    headers_a = auth_header(kri_test_env["tokens"]["analyst_a"])
    foreign_fin_id = kri_test_env["fin_appetite_b"].id

    payload = {
        "statement_code": "APP-FOREIGN-FIN-01",
        "title": "Foreign Financial Link",
        "executive_summary": "Testing foreign financial appetite link.",
        "category_appetites": {"FINANCIAL": "LOW"},
        "financial_risk_appetite_id": foreign_fin_id,
        "effective_from": "2026-01-01",
    }
    res = client.post("/api/v1/kri/appetite-statements", json=payload, headers=headers_a)
    assert res.status_code == 404


def test_sec_b2_30_historical_observation_immutability(client: TestClient, kri_test_env):
    """SEC-B2-30: Historical observations cannot be deleted or rewritten; query preserves history."""
    headers = auth_header(kri_test_env["tokens"]["analyst_a"])
    kri_payload = {
        "kri_code": "KRI-HIST-01",
        "title": "Historical Integrity",
        "description": "Testing immutable history",
        "risk_category": "OPERATIONAL",
        "unit_of_measure": "COUNT",
        "initial_threshold": {"warning_threshold": 5.0, "critical_threshold": 10.0},
    }
    kri_id = client.post("/api/v1/kri/indicators", json=kri_payload, headers=headers).json()["id"]

    for val in [1.0, 2.0, 3.0]:
        client.post(
            f"/api/v1/kri/indicators/{kri_id}/observations",
            json={"observed_value": val, "unit": "COUNT", "observed_at": datetime.now(timezone.utc).isoformat()},
            headers=headers,
        )

    history = client.get(f"/api/v1/kri/indicators/{kri_id}/observations", headers=headers).json()
    assert len(history) == 3
    values = [h["observed_value"] for h in history]
    assert 1.0 in values
    assert 2.0 in values
    assert 3.0 in values
