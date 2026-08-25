from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User
from tests.conftest import get_token_headers


def test_create_and_list_findings_with_deterministic_risk_matrix(
    client: TestClient, analyst_user: User, db: Session, seeded_framework
):
    headers = get_token_headers(analyst_user)
    controls = client.get("/api/v1/controls", headers=headers).json()
    ctrl_id = controls[0]["id"]

    # 1. Create Finding with impact=4, likelihood=5 => risk_score=20, band=CRITICAL
    res_create = client.post(
        "/api/v1/findings",
        headers=headers,
        json={
            "organization_control_id": ctrl_id,
            "title": "Unauthenticated API Endpoint",
            "description": "Public metrics endpoint exposes internal cluster topology.",
            "finding_type": "TECHNICAL_GAP",
            "severity": "CRITICAL",
            "impact": 4,
            "likelihood": 5,
            "recommendation": "Enforce mTLS and bearer token authentication.",
            "root_cause": "Misconfigured ingress routing rule.",
            "due_date": (date.today() + timedelta(days=5)).isoformat(),
            "remediation_plan": "Update ingress controller annotations.",
        },
    )
    assert res_create.status_code == 201
    f_data = res_create.json()
    assert f_data["risk_score"] == 20
    assert f_data["risk_band"] == "CRITICAL"
    assert f_data["status"] == "OPEN"
    assert f_data["overdue_status"] == "DUE_SOON"  # Within 7 days
    finding_id = f_data["id"]

    # 2. Create Finding with impact=2, likelihood=2 => risk_score=4, band=LOW
    res_low = client.post(
        "/api/v1/findings",
        headers=headers,
        json={
            "organization_control_id": ctrl_id,
            "title": "Outdated Policy Documentation",
            "description": "Policy version header references 2024 instead of 2026.",
            "finding_type": "POLICY_GAP",
            "severity": "LOW",
            "impact": 2,
            "likelihood": 2,
            "recommendation": "Update document template.",
            "due_date": (date.today() + timedelta(days=30)).isoformat(),
        },
    )
    assert res_low.status_code == 201
    assert res_low.json()["risk_score"] == 4
    assert res_low.json()["risk_band"] == "LOW"
    assert res_low.json()["overdue_status"] == "ON_TRACK"

    # 3. Create Overdue Finding
    res_overdue = client.post(
        "/api/v1/findings",
        headers=headers,
        json={
            "organization_control_id": ctrl_id,
            "title": "Expired SSL Certificate",
            "description": "Dev certificate expired yesterday.",
            "finding_type": "CONTROL_GAP",
            "severity": "HIGH",
            "impact": 3,
            "likelihood": 4,
            "recommendation": "Renew certificate via cert-manager.",
            "due_date": (date.today() - timedelta(days=2)).isoformat(),
        },
    )
    assert res_overdue.status_code == 201
    assert res_overdue.json()["overdue_status"] == "OVERDUE"

    # 4. List Findings with filters
    res_list = client.get("/api/v1/findings?risk_band=CRITICAL", headers=headers)
    assert res_list.status_code == 200
    critical_findings = res_list.json()
    assert len(critical_findings) == 1
    assert critical_findings[0]["id"] == finding_id

    # 5. List with overdue_only=True
    res_overdue_list = client.get("/api/v1/findings?overdue_only=true", headers=headers)
    assert res_overdue_list.status_code == 200
    assert len(res_overdue_list.json()) == 1
    assert res_overdue_list.json()[0]["title"] == "Expired SSL Certificate"

    # 6. Check finding stats endpoint
    res_stats = client.get("/api/v1/findings/stats", headers=headers)
    assert res_stats.status_code == 200
    stats = res_stats.json()
    assert stats["total_findings"] == 3
    assert stats["critical_count"] == 1
    assert stats["low_count"] == 1
    assert stats["overdue_count"] == 1
    assert stats["due_soon_count"] == 1
    assert stats["on_track_count"] == 1


def test_update_finding_recalculates_risk_deterministically(
    client: TestClient, analyst_user: User, db: Session, seeded_framework
):
    headers = get_token_headers(analyst_user)
    controls = client.get("/api/v1/controls", headers=headers).json()
    ctrl_id = controls[0]["id"]

    # 1. Create Finding (impact=1, likelihood=1 => score=1, band=LOW)
    res_create = client.post(
        "/api/v1/findings",
        headers=headers,
        json={
            "organization_control_id": ctrl_id,
            "title": "Minor log format discrepancy",
            "description": "Log timestamps missing timezone offset.",
            "finding_type": "PROCESS_GAP",
            "severity": "LOW",
            "impact": 1,
            "likelihood": 1,
            "recommendation": "Configure ISO-8601 formatting.",
        },
    )
    f_id = res_create.json()["id"]
    assert res_create.json()["risk_score"] == 1
    assert res_create.json()["risk_band"] == "LOW"

    # 2. Update to impact=3, likelihood=3 => score=9, band=MODERATE
    res_patch = client.patch(
        f"/api/v1/findings/{f_id}",
        headers=headers,
        json={"impact": 3, "likelihood": 3},
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["risk_score"] == 9
    assert res_patch.json()["risk_band"] == "MODERATE"
