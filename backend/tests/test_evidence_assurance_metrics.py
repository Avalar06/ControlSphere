import io
from tests.conftest import get_token_headers


def test_deterministic_evidence_coverage_calculation(client, analyst_user, auditor_user, seeded_framework):
    analyst_headers = get_token_headers(analyst_user)
    auditor_headers = get_token_headers(auditor_user)
    ctrl_id = client.get("/api/v1/controls", headers=analyst_headers).json()[0]["id"]

    # Create 2 mandatory requirements
    req1 = client.post(
        "/api/v1/evidence/requirements",
        headers=analyst_headers,
        json={"organization_control_id": ctrl_id, "title": "Req 1: Policy", "is_required": True},
    ).json()

    req2 = client.post(
        "/api/v1/evidence/requirements",
        headers=analyst_headers,
        json={"organization_control_id": ctrl_id, "title": "Req 2: Log", "is_required": True},
    ).json()

    # Initial assurance metrics (0% coverage)
    assure_init = client.get(f"/api/v1/evidence/controls/{ctrl_id}/assurance", headers=analyst_headers).json()
    assert assure_init["required_count"] == 2
    assert assure_init["accepted_count"] == 0
    assert assure_init["evidence_coverage_pct"] == 0.0

    # Upload and accept evidence for Requirement 1
    files1 = {"file": ("req1.pdf", io.BytesIO(b"%PDF-1.4 Req 1 Policy Doc"), "application/pdf")}
    ev1 = client.post(
        "/api/v1/evidence/upload",
        headers=analyst_headers,
        data={
            "organization_control_id": str(ctrl_id),
            "evidence_requirement_id": str(req1["id"]),
            "title": "Req 1 Evidence",
        },
        files=files1,
    ).json()

    client.post(f"/api/v1/evidence/{ev1['id']}/submit-review", headers=analyst_headers)
    client.post(
        f"/api/v1/evidence/{ev1['id']}/review",
        headers=auditor_headers,
        json={"decision": "ACCEPT"},
    )

    # Coverage should now be 50.0% (1 of 2 mandatory requirements satisfied)
    assure_half = client.get(f"/api/v1/evidence/controls/{ctrl_id}/assurance", headers=analyst_headers).json()
    assert assure_half["accepted_count"] == 1
    assert assure_half["evidence_coverage_pct"] == 50.0

    # Control implementation status must remain unaffected by evidence acceptance!
    ctrl_after = client.get(f"/api/v1/controls/{ctrl_id}", headers=analyst_headers).json()
    assert ctrl_after["status"] == "NOT_STARTED"


def test_organization_aggregate_evidence_stats(client, analyst_user, seeded_framework):
    headers = get_token_headers(analyst_user)
    stats_res = client.get("/api/v1/evidence/stats", headers=headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert "total_evidence_items" in stats
    assert "accepted_count" in stats
    assert "pending_review_count" in stats
    assert "overall_coverage_pct" in stats