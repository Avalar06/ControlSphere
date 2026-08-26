"""
tests/test_audit_readiness.py — Phase 6 deterministic audit readiness scoring tests.
"""
import pytest
from sqlalchemy.orm import Session
from tests.conftest import get_token_headers
from app.models.control import OrganizationControl, ImplementationStatusEnum, PriorityEnum
from app.models.evidence import EvidenceItem, EvidenceStatusEnum
from app.models.finding import Finding, FindingTypeEnum, FindingSeverityEnum, FindingStatusEnum


def make_audit(client, headers, **kwargs):
    payload = {
        "title": "Readiness Score Test Audit",
        "objective": "Validate deterministic readiness scoring algorithm end-to-end",
        "audit_type": "INTERNAL",
    }
    payload.update(kwargs)
    resp = client.post("/api/v1/audits", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def make_control(db: Session, org_id: int, subcat_id: int, status=ImplementationStatusEnum.IMPLEMENTED) -> OrganizationControl:
    ctrl = OrganizationControl(
        organization_id=org_id,
        subcategory_id=subcat_id,
        status=status,
        priority=PriorityEnum.HIGH,
    )
    db.add(ctrl)
    db.commit()
    db.refresh(ctrl)
    return ctrl


def make_evidence(db: Session, org_id: int, ctrl_id: int, status=EvidenceStatusEnum.ACCEPTED) -> EvidenceItem:
    ev = EvidenceItem(
        organization_id=org_id,
        organization_control_id=ctrl_id,
        title="Evidence Item",
        original_filename="doc.pdf",
        stored_filename="doc_stored.pdf",
        file_extension="pdf",
        content_type="application/pdf",
        file_size=102400,
        sha256_hash="b" * 64,
        storage_key=f"org_{org_id}/doc.pdf",
        status=status,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


def make_finding(db: Session, org_id: int, ctrl_id: int, severity=FindingSeverityEnum.MEDIUM) -> Finding:
    f = Finding(
        organization_id=org_id,
        organization_control_id=ctrl_id,
        title="Test Finding",
        description="A test finding for readiness scoring validation",
        recommendation="Remediate the test finding appropriately.",
        finding_type=FindingTypeEnum.CONTROL_GAP,
        severity=severity,
        impact=3,
        likelihood=3,
        risk_score=9,
        risk_band="MODERATE",
    )
    db.add(f)
    db.commit()
    db.refresh(f)
    return f


class TestAuditReadiness:
    def test_empty_audit_readiness(self, client, admin_user, seeded_framework):
        """An audit with nothing in scope has 0% readiness and specific blockers."""
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)
        resp = client.get(f"/api/v1/audits/{audit['id']}/readiness", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["readiness_score"] == 0.0
        assert data["readiness_band"] == "NOT_READY"
        assert len(data["readiness_blockers"]) > 0
        assert data["controls_in_scope"] == 0
        assert data["procedures_total"] == 0

    def test_readiness_improves_with_procedures(self, client, admin_user, seeded_framework, db, org_apex):
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)
        audit_id = audit["id"]

        subcat = db.query(__import__("app.models.framework", fromlist=["FrameworkSubcategory"]).FrameworkSubcategory).first()
        ctrl = make_control(db, org_apex.id, subcat.id)

        # Add control to scope
        client.post(f"/api/v1/audits/{audit_id}/scope", json={"organization_control_id": ctrl.id}, headers=headers)

        # Add evidence
        ev = make_evidence(db, org_apex.id, ctrl.id)

        # Create and complete a procedure
        proc_resp = client.post(
            f"/api/v1/audits/{audit_id}/procedures",
            json={"title": "Check patch records", "result": "NOT_STARTED"},
            headers=headers,
        )
        assert proc_resp.status_code == 201
        proc_id = proc_resp.json()["id"]

        client.patch(
            f"/api/v1/audits/{audit_id}/procedures/{proc_id}",
            json={"result": "PASSED", "actual_result": "All records verified"},
            headers=headers,
        )

        resp = client.get(f"/api/v1/audits/{audit_id}/readiness", headers=headers)
        data = resp.json()
        assert data["readiness_score"] > 0.0
        assert data["controls_in_scope"] == 1
        assert data["controls_with_evidence"] == 1
        assert data["procedures_passed"] == 1
        assert data["procedures_completed"] == 1

    def test_open_critical_findings_lower_readiness(self, client, admin_user, seeded_framework, db, org_apex):
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)
        audit_id = audit["id"]

        subcat = db.query(__import__("app.models.framework", fromlist=["FrameworkSubcategory"]).FrameworkSubcategory).first()
        ctrl = make_control(db, org_apex.id, subcat.id)

        # Add evidence and complete procedure
        ev = make_evidence(db, org_apex.id, ctrl.id)
        client.post(f"/api/v1/audits/{audit_id}/scope", json={"organization_control_id": ctrl.id}, headers=headers)
        proc_resp = client.post(f"/api/v1/audits/{audit_id}/procedures", json={"title": "Check", "result": "NOT_STARTED"}, headers=headers)
        client.patch(f"/api/v1/audits/{audit_id}/procedures/{proc_resp.json()['id']}", json={"result": "PASSED"}, headers=headers)

        # Get base readiness without findings
        base_resp = client.get(f"/api/v1/audits/{audit_id}/readiness", headers=headers)
        base_score = base_resp.json()["readiness_score"]

        # Link a critical finding
        critical_finding = make_finding(db, org_apex.id, ctrl.id, severity=FindingSeverityEnum.CRITICAL)
        client.post(f"/api/v1/audits/{audit_id}/findings", json={"finding_id": critical_finding.id}, headers=headers)

        penalized_resp = client.get(f"/api/v1/audits/{audit_id}/readiness", headers=headers)
        penalized_score = penalized_resp.json()["readiness_score"]
        penalized_data = penalized_resp.json()

        assert penalized_score < base_score
        assert penalized_data["findings_critical"] == 1
        assert any("critical" in b.lower() or "finding" in b.lower() for b in penalized_data["readiness_blockers"])

    def test_readiness_structure(self, client, admin_user, seeded_framework):
        """Verify all required readiness fields are present."""
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)
        resp = client.get(f"/api/v1/audits/{audit['id']}/readiness", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        required_fields = [
            "audit_id", "audit_status", "controls_in_scope", "controls_with_evidence",
            "controls_assessed", "procedures_total", "procedures_not_started",
            "procedures_in_progress", "procedures_passed", "procedures_partially_passed",
            "procedures_failed", "procedures_not_applicable", "procedures_completed",
            "findings_total", "findings_open", "findings_critical", "findings_high",
            "findings_in_remediation", "active_exceptions_in_scope",
            "readiness_score", "readiness_band", "readiness_blockers",
        ]
        for field in required_fields:
            assert field in data, f"Missing readiness field: {field}"

    def test_readiness_band_is_valid(self, client, admin_user, seeded_framework):
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)
        resp = client.get(f"/api/v1/audits/{audit['id']}/readiness", headers=headers)
        band = resp.json()["readiness_band"]
        assert band in ["NOT_READY", "PARTIALLY_READY", "SUBSTANTIALLY_READY", "READY"]

    def test_readiness_score_range(self, client, admin_user, seeded_framework):
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)
        resp = client.get(f"/api/v1/audits/{audit['id']}/readiness", headers=headers)
        score = resp.json()["readiness_score"]
        assert 0.0 <= score <= 100.0

    def test_readiness_not_found_for_wrong_org(self, client, meridian_admin_user, admin_user, seeded_framework):
        apex_headers = get_token_headers(admin_user)
        audit = make_audit(client, apex_headers)

        meridian_headers = get_token_headers(meridian_admin_user)
        resp = client.get(f"/api/v1/audits/{audit['id']}/readiness", headers=meridian_headers)
        assert resp.status_code == 404
