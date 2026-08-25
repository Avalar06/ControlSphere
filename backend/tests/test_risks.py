import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User
from tests.conftest import get_token_headers


def test_create_and_list_risks(
    client: TestClient, analyst_user: User, db: Session, seeded_framework
):
    headers = get_token_headers(analyst_user)

    # 1. Create Risk
    res_create = client.post(
        "/api/v1/risks",
        headers=headers,
        json={
            "title": "Unpatched Kubernetes Node Zero-Day",
            "description": "Critical remote code execution vulnerability in container runtime.",
            "risk_category": "CYBERSECURITY",
            "risk_source": "THREAT_INTELLIGENCE",
            "inherent_impact": 5,
            "inherent_likelihood": 4,
            "target_risk_band": "MODERATE",
            "treatment_strategy": "MITIGATE",
            "treatment_plan": "Apply emergency kernel patch across all node pools within 24h.",
        },
    )
    assert res_create.status_code == 201
    data = res_create.json()
    assert data["title"] == "Unpatched Kubernetes Node Zero-Day"
    # Deterministic scoring: 5 * 4 = 20 (CRITICAL)
    assert data["inherent_score"] == 20
    assert data["inherent_band"] == "CRITICAL"
    assert data["appetite_status"] == "ABOVE_APPETITE"
    assert data["status"] == "IDENTIFIED"
    risk_id = data["id"]

    # 2. List Risks
    res_list = client.get("/api/v1/risks?inherent_band=CRITICAL", headers=headers)
    assert res_list.status_code == 200
    items = res_list.json()
    assert len(items) >= 1
    assert items[0]["id"] == risk_id

    # 3. Get Heatmap Data
    res_heatmap = client.get("/api/v1/risks/heatmap", headers=headers)
    assert res_heatmap.status_code == 200
    heatmap = res_heatmap.json()
    assert len(heatmap) == 25
    target_cell = next(c for c in heatmap if c["likelihood"] == 4 and c["impact"] == 5)
    assert target_cell["count"] >= 1
    assert target_cell["score"] == 20
    assert target_cell["band"] == "CRITICAL"

    # 4. Get Stats
    res_stats = client.get("/api/v1/risks/stats", headers=headers)
    assert res_stats.status_code == 200
    stats = res_stats.json()
    assert stats["total_risks"] >= 1
    assert stats["critical_inherent_count"] >= 1
    assert stats["above_appetite_count"] >= 1


def test_update_risk_residual_scoring(
    client: TestClient, analyst_user: User, db: Session, seeded_framework
):
    headers = get_token_headers(analyst_user)

    # 1. Create Risk
    res_create = client.post(
        "/api/v1/risks",
        headers=headers,
        json={
            "title": "Phishing Credential Harvesting",
            "description": "Spear phishing campaign targeting finance department.",
            "risk_category": "CYBERSECURITY",
            "inherent_impact": 4,
            "inherent_likelihood": 4,
        },
    )
    risk_id = res_create.json()["id"]

    # 2. Update with residual score after FIDO2 MFA enforcement
    res_patch = client.patch(
        f"/api/v1/risks/{risk_id}",
        headers=headers,
        json={
            "residual_impact": 2,
            "residual_likelihood": 1,
            "treatment_strategy": "MITIGATE",
            "treatment_plan": "Hardware security keys distributed to 100% of finance staff.",
        },
    )
    assert res_patch.status_code == 200
    patched = res_patch.json()
    # Residual: 2 * 1 = 2 (LOW)
    assert patched["residual_score"] == 2
    assert patched["residual_band"] == "LOW"
    assert patched["appetite_status"] == "WITHIN_APPETITE"


def test_link_control_and_finding_to_risk(
    client: TestClient, analyst_user: User, db: Session, seeded_framework
):
    headers = get_token_headers(analyst_user)
    controls = client.get("/api/v1/controls", headers=headers).json()
    ctrl_id = controls[0]["id"]

    # Create finding
    res_find = client.post(
        "/api/v1/findings",
        headers=headers,
        json={
            "organization_control_id": ctrl_id,
            "title": "Deficient Access Review Process",
            "description": "Quarterly access reviews missed for 2 consecutive cycles.",
            "recommendation": "Automate reviews in IAM portal.",
        },
    )
    find_id = res_find.json()["id"]

    # Create risk
    res_risk = client.post(
        "/api/v1/risks",
        headers=headers,
        json={
            "title": "Privilege Creep & Unauthorized Access",
            "description": "Accumulation of excessive permissions over time.",
        },
    )
    risk_id = res_risk.json()["id"]

    # 1. Link Control to Risk
    res_link_ctrl = client.post(
        f"/api/v1/risks/{risk_id}/controls",
        headers=headers,
        json={"organization_control_id": ctrl_id},
    )
    assert res_link_ctrl.status_code == 201

    # 2. Link Finding to Risk
    res_link_find = client.post(
        f"/api/v1/risks/{risk_id}/findings",
        headers=headers,
        json={"finding_id": find_id},
    )
    assert res_link_find.status_code == 201

    # 3. Get Risk Detail
    res_detail = client.get(f"/api/v1/risks/{risk_id}", headers=headers)
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert len(detail["control_links"]) == 1
    assert len(detail["finding_links"]) == 1
    assert detail["control_links"][0]["organization_control_id"] == ctrl_id
    assert detail["finding_links"][0]["finding_id"] == find_id

    # 4. Unlink Control & Finding
    res_unlink_ctrl = client.delete(f"/api/v1/risks/{risk_id}/controls/{ctrl_id}", headers=headers)
    assert res_unlink_ctrl.status_code == 204

    res_unlink_find = client.delete(f"/api/v1/risks/{risk_id}/findings/{find_id}", headers=headers)
    assert res_unlink_find.status_code == 204
