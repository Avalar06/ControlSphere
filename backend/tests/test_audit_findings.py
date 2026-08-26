"""
tests/test_audit_findings.py — Phase 6 audit finding link tests.
"""
import pytest
from sqlalchemy.orm import Session
from tests.conftest import get_token_headers
from app.models.control import OrganizationControl, ImplementationStatusEnum, PriorityEnum
from app.models.finding import Finding, FindingTypeEnum, FindingSeverityEnum


def make_audit(client, headers, **kwargs):
    payload = {
        "title": "Findings Test Audit",
        "objective": "Testing audit finding linkage and management",
        "audit_type": "INTERNAL",
    }
    payload.update(kwargs)
    resp = client.post("/api/v1/audits", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def make_control(db: Session, org_id: int, subcat_id: int) -> OrganizationControl:
    ctrl = OrganizationControl(
        organization_id=org_id,
        subcategory_id=subcat_id,
        status=ImplementationStatusEnum.IN_PROGRESS,
        priority=PriorityEnum.HIGH,
    )
    db.add(ctrl)
    db.commit()
    db.refresh(ctrl)
    return ctrl


def make_finding(db: Session, org_id: int, ctrl_id: int) -> Finding:
    f = Finding(
        organization_id=org_id,
        organization_control_id=ctrl_id,
        title="Missing patch policy",
        description="Formal patch management policy is absent",
        recommendation="Create, approve, and enforce a patch management policy.",
        finding_type=FindingTypeEnum.POLICY_GAP,
        severity=FindingSeverityEnum.HIGH,
        impact=4,
        likelihood=3,
        risk_score=12,
        risk_band="HIGH",
    )
    db.add(f)
    db.commit()
    db.refresh(f)
    return f


class TestAuditFindings:
    def test_link_finding_to_audit(self, client, admin_user, seeded_framework, db, org_apex):
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)
        subcat = db.query(__import__("app.models.framework", fromlist=["FrameworkSubcategory"]).FrameworkSubcategory).first()
        ctrl = make_control(db, org_apex.id, subcat.id)
        finding = make_finding(db, org_apex.id, ctrl.id)

        resp = client.post(
            f"/api/v1/audits/{audit['id']}/findings",
            json={"finding_id": finding.id, "link_notes": "Identified during fieldwork"},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["finding_id"] == finding.id
        assert data["audit_id"] == audit["id"]

    def test_list_finding_links(self, client, admin_user, seeded_framework, db, org_apex):
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)
        subcat = db.query(__import__("app.models.framework", fromlist=["FrameworkSubcategory"]).FrameworkSubcategory).first()
        ctrl = make_control(db, org_apex.id, subcat.id)
        finding = make_finding(db, org_apex.id, ctrl.id)
        client.post(f"/api/v1/audits/{audit['id']}/findings", json={"finding_id": finding.id}, headers=headers)

        resp = client.get(f"/api/v1/audits/{audit['id']}/findings", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_unlink_finding(self, client, admin_user, seeded_framework, db, org_apex):
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)
        subcat = db.query(__import__("app.models.framework", fromlist=["FrameworkSubcategory"]).FrameworkSubcategory).first()
        ctrl = make_control(db, org_apex.id, subcat.id)
        finding = make_finding(db, org_apex.id, ctrl.id)
        client.post(f"/api/v1/audits/{audit['id']}/findings", json={"finding_id": finding.id}, headers=headers)

        resp = client.delete(f"/api/v1/audits/{audit['id']}/findings/{finding.id}", headers=headers)
        assert resp.status_code == 204

        resp2 = client.get(f"/api/v1/audits/{audit['id']}/findings", headers=headers)
        assert len(resp2.json()) == 0

    def test_cross_tenant_finding_cannot_be_linked(self, client, admin_user, meridian_admin_user, seeded_framework, db, org_apex, org_meridian):
        apex_headers = get_token_headers(admin_user)
        subcat = db.query(__import__("app.models.framework", fromlist=["FrameworkSubcategory"]).FrameworkSubcategory).first()
        apex_ctrl = make_control(db, org_apex.id, subcat.id)
        meridian_ctrl = make_control(db, org_meridian.id, subcat.id)
        meridian_finding = make_finding(db, org_meridian.id, meridian_ctrl.id)

        audit = make_audit(client, apex_headers)
        resp = client.post(
            f"/api/v1/audits/{audit['id']}/findings",
            json={"finding_id": meridian_finding.id},
            headers=apex_headers,
        )
        assert resp.status_code == 400

    def test_duplicate_finding_link_is_idempotent(self, client, admin_user, seeded_framework, db, org_apex):
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)
        subcat = db.query(__import__("app.models.framework", fromlist=["FrameworkSubcategory"]).FrameworkSubcategory).first()
        ctrl = make_control(db, org_apex.id, subcat.id)
        finding = make_finding(db, org_apex.id, ctrl.id)

        r1 = client.post(f"/api/v1/audits/{audit['id']}/findings", json={"finding_id": finding.id}, headers=headers)
        r2 = client.post(f"/api/v1/audits/{audit['id']}/findings", json={"finding_id": finding.id}, headers=headers)
        assert r1.status_code in (200, 201)
        assert r2.status_code in (200, 201)
        assert r1.json()["id"] == r2.json()["id"]

    def test_viewer_cannot_link_finding(self, client, viewer_user, admin_user, seeded_framework, db, org_apex):
        admin_headers = get_token_headers(admin_user)
        audit = make_audit(client, admin_headers)
        subcat = db.query(__import__("app.models.framework", fromlist=["FrameworkSubcategory"]).FrameworkSubcategory).first()
        ctrl = make_control(db, org_apex.id, subcat.id)
        finding = make_finding(db, org_apex.id, ctrl.id)

        viewer_headers = get_token_headers(viewer_user)
        resp = client.post(
            f"/api/v1/audits/{audit['id']}/findings",
            json={"finding_id": finding.id},
            headers=viewer_headers,
        )
        assert resp.status_code == 403
