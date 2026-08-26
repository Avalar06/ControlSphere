"""
tests/test_audit_scope.py — Phase 6 audit scope management tests.
"""
import pytest
from sqlalchemy.orm import Session
from tests.conftest import get_token_headers
from app.models.control import OrganizationControl, ImplementationStatusEnum, PriorityEnum


def make_audit(client, headers, **kwargs):
    payload = {
        "title": "Scope Test Audit",
        "objective": "Testing audit scope management features",
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
        priority=PriorityEnum.MEDIUM,
    )
    db.add(ctrl)
    db.commit()
    db.refresh(ctrl)
    return ctrl


class TestAuditScope:
    def test_add_control_to_scope(self, client, admin_user, seeded_framework, db, org_apex):
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)
        subcat = db.query(__import__("app.models.framework", fromlist=["FrameworkSubcategory"]).FrameworkSubcategory).first()
        ctrl = make_control(db, org_apex.id, subcat.id)

        resp = client.post(
            f"/api/v1/audits/{audit['id']}/scope",
            json={"organization_control_id": ctrl.id, "scope_notes": "High priority control"},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["organization_control_id"] == ctrl.id
        assert data["audit_id"] == audit["id"]

    def test_list_audit_scope(self, client, admin_user, seeded_framework, db, org_apex):
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)
        subcat = db.query(__import__("app.models.framework", fromlist=["FrameworkSubcategory"]).FrameworkSubcategory).first()
        ctrl = make_control(db, org_apex.id, subcat.id)

        client.post(
            f"/api/v1/audits/{audit['id']}/scope",
            json={"organization_control_id": ctrl.id},
            headers=headers,
        )

        resp = client.get(f"/api/v1/audits/{audit['id']}/scope", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_add_duplicate_scope_control_is_idempotent(self, client, admin_user, seeded_framework, db, org_apex):
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)
        subcat = db.query(__import__("app.models.framework", fromlist=["FrameworkSubcategory"]).FrameworkSubcategory).first()
        ctrl = make_control(db, org_apex.id, subcat.id)

        # Add twice
        r1 = client.post(f"/api/v1/audits/{audit['id']}/scope", json={"organization_control_id": ctrl.id}, headers=headers)
        r2 = client.post(f"/api/v1/audits/{audit['id']}/scope", json={"organization_control_id": ctrl.id}, headers=headers)
        # Both succeed idempotently
        assert r1.status_code in (200, 201)
        assert r2.status_code in (200, 201)

        # Still only one entry
        resp = client.get(f"/api/v1/audits/{audit['id']}/scope", headers=headers)
        assert len(resp.json()) == 1

    def test_remove_control_from_scope(self, client, admin_user, seeded_framework, db, org_apex):
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)
        subcat = db.query(__import__("app.models.framework", fromlist=["FrameworkSubcategory"]).FrameworkSubcategory).first()
        ctrl = make_control(db, org_apex.id, subcat.id)

        client.post(f"/api/v1/audits/{audit['id']}/scope", json={"organization_control_id": ctrl.id}, headers=headers)

        resp = client.delete(f"/api/v1/audits/{audit['id']}/scope/{ctrl.id}", headers=headers)
        assert resp.status_code == 204

        resp2 = client.get(f"/api/v1/audits/{audit['id']}/scope", headers=headers)
        assert len(resp2.json()) == 0

    def test_cross_tenant_control_cannot_be_added_to_scope(self, client, admin_user, meridian_admin_user, seeded_framework, db, org_meridian):
        """Control from org_meridian cannot be added to an apex audit."""
        apex_headers = get_token_headers(admin_user)
        meridian_headers = get_token_headers(meridian_admin_user)

        # Create meridian's own control
        subcat = db.query(__import__("app.models.framework", fromlist=["FrameworkSubcategory"]).FrameworkSubcategory).first()
        meridian_ctrl = make_control(db, org_meridian.id, subcat.id)

        # Create audit in apex
        audit = make_audit(client, apex_headers)

        # Apex admin tries to add meridian's control to their audit
        resp = client.post(
            f"/api/v1/audits/{audit['id']}/scope",
            json={"organization_control_id": meridian_ctrl.id},
            headers=apex_headers,
        )
        assert resp.status_code == 400

    def test_viewer_cannot_add_scope(self, client, viewer_user, admin_user, seeded_framework, db, org_apex):
        admin_headers = get_token_headers(admin_user)
        audit = make_audit(client, admin_headers)
        subcat = db.query(__import__("app.models.framework", fromlist=["FrameworkSubcategory"]).FrameworkSubcategory).first()
        ctrl = make_control(db, org_apex.id, subcat.id)

        viewer_headers = get_token_headers(viewer_user)
        resp = client.post(
            f"/api/v1/audits/{audit['id']}/scope",
            json={"organization_control_id": ctrl.id},
            headers=viewer_headers,
        )
        assert resp.status_code == 403

    def test_cannot_modify_scope_of_closed_audit(self, client, admin_user, seeded_framework, db, org_apex):
        headers = get_token_headers(admin_user)
        audit = make_audit(client, headers)
        audit_id = audit["id"]

        # Progress to CLOSED
        for s in ["INITIATED", "FIELDWORK", "REVIEW", "REPORTING", "COMPLETED"]:
            client.post(f"/api/v1/audits/{audit_id}/status", json={"status": s}, headers=headers)
        client.post(f"/api/v1/audits/{audit_id}/close", json={"closure_notes": "Final closure"}, headers=headers)

        subcat = db.query(__import__("app.models.framework", fromlist=["FrameworkSubcategory"]).FrameworkSubcategory).first()
        ctrl = make_control(db, org_apex.id, subcat.id)
        resp = client.post(
            f"/api/v1/audits/{audit_id}/scope",
            json={"organization_control_id": ctrl.id},
            headers=headers,
        )
        assert resp.status_code == 400
