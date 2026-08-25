import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog
from app.models.user import User
from tests.conftest import get_token_headers


def test_phase5_audit_logs_generated(
    client: TestClient, analyst_user: User, db: Session, seeded_framework
):
    headers = get_token_headers(analyst_user)

    # 1. Create Risk
    res_risk = client.post(
        "/api/v1/risks",
        headers=headers,
        json={"title": "Audit Test Risk", "description": "Desc"},
    )
    risk_id = res_risk.json()["id"]

    # Verify risk.create audit log
    audit_r_create = (
        db.query(AuditLog)
        .filter(AuditLog.resource_type == "RISK", AuditLog.action == "risk.create", AuditLog.resource_id == str(risk_id))
        .first()
    )
    assert audit_r_create is not None
    assert audit_r_create.actor_id == analyst_user.id
    assert audit_r_create.status == "SUCCESS"

    # 2. Risk Status Change
    client.post(
        f"/api/v1/risks/{risk_id}/status",
        headers=headers,
        json={"status": "ASSESSED"},
    )
    audit_r_status = (
        db.query(AuditLog)
        .filter(AuditLog.resource_type == "RISK", AuditLog.action == "risk.status.change", AuditLog.resource_id == str(risk_id))
        .first()
    )
    assert audit_r_status is not None

    # 3. Create Exception
    from datetime import date, timedelta
    expiry = date.today() + timedelta(days=30)
    res_exc = client.post(
        "/api/v1/exceptions",
        headers=headers,
        json={
            "title": "Audit Test Exception",
            "description": "Desc",
            "justification": "Justification",
            "expiry_date": expiry.isoformat(),
        },
    )
    exc_id = res_exc.json()["id"]

    # Verify exception.create audit log
    audit_e_create = (
        db.query(AuditLog)
        .filter(AuditLog.resource_type == "SECURITY_EXCEPTION", AuditLog.action == "exception.create", AuditLog.resource_id == str(exc_id))
        .first()
    )
    assert audit_e_create is not None
