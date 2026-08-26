"""
tests/test_audits.py — Phase 6 Audit CRUD, lifecycle, and general workflow tests.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import get_token_headers
from app.models.framework import Framework, FrameworkFunction, FrameworkCategory, FrameworkSubcategory
from app.models.control import OrganizationControl, ImplementationStatusEnum, PriorityEnum
from app.models.finding import Finding, FindingTypeEnum, FindingSeverityEnum
from app.core.permissions import RoleEnum
from app.core.security import get_password_hash
from app.models.user import User


# ── helpers ──────────────────────────────────────────────────────────────────

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
        description="No formal patch policy exists",
        recommendation="Create and enforce a patch management policy.",
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


def create_audit(client: TestClient, headers: dict, **kwargs) -> dict:
    payload = {
        "title": "Q3 2026 Internal Audit",
        "objective": "Assess NIST CSF 2.0 implementation status",
        "audit_type": "INTERNAL",
    }
    payload.update(kwargs)
    resp = client.post("/api/v1/audits", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── tests ─────────────────────────────────────────────────────────────────────

class TestAuditCRUD:
    def test_create_audit_as_admin(self, client, admin_user, seeded_framework):
        headers = get_token_headers(admin_user)
        data = create_audit(client, headers)
        assert data["title"] == "Q3 2026 Internal Audit"
        assert data["status"] == "PLANNED"
        assert data["opinion"] == "UNISSUED"
        assert data["organization_id"] == admin_user.organization_id

    def test_create_audit_as_auditor(self, client, auditor_user, seeded_framework):
        headers = get_token_headers(auditor_user)
        data = create_audit(client, headers, title="Auditor Audit")
        assert data["status"] == "PLANNED"

    def test_viewer_cannot_create_audit(self, client, viewer_user, seeded_framework):
        headers = get_token_headers(viewer_user)
        resp = client.post(
            "/api/v1/audits",
            json={"title": "Foo", "objective": "Bar bar bar bar bar bar", "audit_type": "INTERNAL"},
            headers=headers,
        )
        assert resp.status_code == 403

    def test_unauthenticated_cannot_create_audit(self, client):
        resp = client.post(
            "/api/v1/audits",
            json={"title": "Foo", "objective": "Baz baz baz", "audit_type": "INTERNAL"},
        )
        assert resp.status_code == 401

    def test_get_audit_detail(self, client, admin_user, seeded_framework):
        headers = get_token_headers(admin_user)
        created = create_audit(client, headers)
        resp = client.get(f"/api/v1/audits/{created['id']}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == created["id"]
        assert "scope_controls" in data
        assert "procedures" in data
        assert "finding_links" in data

    def test_list_audits(self, client, admin_user, seeded_framework):
        headers = get_token_headers(admin_user)
        create_audit(client, headers, title="Audit A")
        create_audit(client, headers, title="Audit B")
        resp = client.get("/api/v1/audits", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    def test_update_audit(self, client, admin_user, seeded_framework):
        headers = get_token_headers(admin_user)
        created = create_audit(client, headers)
        resp = client.patch(
            f"/api/v1/audits/{created['id']}",
            json={"summary": "Updated summary"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["summary"] == "Updated summary"

    def test_get_nonexistent_audit_returns_404(self, client, admin_user, seeded_framework):
        headers = get_token_headers(admin_user)
        resp = client.get("/api/v1/audits/999999", headers=headers)
        assert resp.status_code == 404

    def test_audit_stats(self, client, admin_user, seeded_framework):
        headers = get_token_headers(admin_user)
        create_audit(client, headers)
        resp = client.get("/api/v1/audits/stats", headers=headers)
        assert resp.status_code == 200
        stats = resp.json()
        assert "total_audits" in stats
        assert stats["total_audits"] >= 1


class TestAuditValidation:
    def test_create_requires_title(self, client, admin_user, seeded_framework):
        headers = get_token_headers(admin_user)
        resp = client.post(
            "/api/v1/audits",
            json={"objective": "Test objective that is long enough", "audit_type": "INTERNAL"},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_objective_too_short(self, client, admin_user, seeded_framework):
        headers = get_token_headers(admin_user)
        resp = client.post(
            "/api/v1/audits",
            json={"title": "Valid Title", "objective": "Short", "audit_type": "INTERNAL"},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_invalid_planned_dates(self, client, admin_user, seeded_framework):
        headers = get_token_headers(admin_user)
        resp = client.post(
            "/api/v1/audits",
            json={
                "title": "Date Test",
                "objective": "Test date validation in audit creation",
                "audit_type": "INTERNAL",
                "planned_start_date": "2026-12-01",
                "planned_end_date": "2026-11-01",
            },
            headers=headers,
        )
        assert resp.status_code == 422
