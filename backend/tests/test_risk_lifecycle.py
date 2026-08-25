import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User
from tests.conftest import get_token_headers


def test_risk_lifecycle_full_happy_path(
    client: TestClient, analyst_user: User, db: Session, seeded_framework
):
    headers = get_token_headers(analyst_user)

    # 1. IDENTIFIED
    res_create = client.post(
        "/api/v1/risks",
        headers=headers,
        json={"title": "Lifecycle Test Risk", "description": "Desc"},
    )
    risk_id = res_create.json()["id"]
    assert res_create.json()["status"] == "IDENTIFIED"

    # 2. IDENTIFIED -> ASSESSED
    res_ass = client.post(
        f"/api/v1/risks/{risk_id}/status",
        headers=headers,
        json={"status": "ASSESSED", "notes": "Risk assessment completed."},
    )
    assert res_ass.status_code == 200
    assert res_ass.json()["status"] == "ASSESSED"

    # 3. ASSESSED -> TREATMENT_PLANNED
    res_tp = client.post(
        f"/api/v1/risks/{risk_id}/status",
        headers=headers,
        json={"status": "TREATMENT_PLANNED", "notes": "Mitigation roadmap defined."},
    )
    assert res_tp.status_code == 200
    assert res_tp.json()["status"] == "TREATMENT_PLANNED"

    # 4. TREATMENT_PLANNED -> MITIGATING
    res_mit = client.post(
        f"/api/v1/risks/{risk_id}/status",
        headers=headers,
        json={"status": "MITIGATING", "notes": "Controls being rolled out."},
    )
    assert res_mit.status_code == 200
    assert res_mit.json()["status"] == "MITIGATING"

    # 5. MITIGATING -> MONITORING
    res_mon = client.post(
        f"/api/v1/risks/{risk_id}/status",
        headers=headers,
        json={"status": "MONITORING", "notes": "Controls operational, monitoring residual risk."},
    )
    assert res_mon.status_code == 200
    assert res_mon.json()["status"] == "MONITORING"

    # 6. MONITORING -> CLOSED
    res_close = client.post(
        f"/api/v1/risks/{risk_id}/status",
        headers=headers,
        json={"status": "CLOSED", "notes": "Residual risk verified within appetite. Closed."},
    )
    assert res_close.status_code == 200
    assert res_close.json()["status"] == "CLOSED"

    # 7. CLOSED risks cannot transition or be modified
    res_reopen = client.post(
        f"/api/v1/risks/{risk_id}/status",
        headers=headers,
        json={"status": "IDENTIFIED"},
    )
    assert res_reopen.status_code == 400

    res_patch_closed = client.patch(
        f"/api/v1/risks/{risk_id}",
        headers=headers,
        json={"title": "Trying to edit closed risk"},
    )
    assert res_patch_closed.status_code == 400


def test_risk_lifecycle_invalid_transitions_blocked(
    client: TestClient, analyst_user: User, db: Session, seeded_framework
):
    headers = get_token_headers(analyst_user)

    # 1. Create Risk (IDENTIFIED)
    res_create = client.post(
        "/api/v1/risks",
        headers=headers,
        json={"title": "Invalid Transition Test Risk", "description": "Desc"},
    )
    risk_id = res_create.json()["id"]

    # IDENTIFIED -> CLOSED must be BLOCKED
    res_id_close = client.post(
        f"/api/v1/risks/{risk_id}/status",
        headers=headers,
        json={"status": "CLOSED"},
    )
    assert res_id_close.status_code == 400

    # IDENTIFIED -> MONITORING must be BLOCKED
    res_id_mon = client.post(
        f"/api/v1/risks/{risk_id}/status",
        headers=headers,
        json={"status": "MONITORING"},
    )
    assert res_id_mon.status_code == 400

    # Transition to ASSESSED
    client.post(f"/api/v1/risks/{risk_id}/status", headers=headers, json={"status": "ASSESSED"})

    # ASSESSED -> IDENTIFIED (backwards) must be BLOCKED
    res_back = client.post(
        f"/api/v1/risks/{risk_id}/status",
        headers=headers,
        json={"status": "IDENTIFIED"},
    )
    assert res_back.status_code == 400
