import pytest
from starlette.testclient import TestClient

from tests.conftest import get_token_headers


class TestMonitoringConfig:

    def test_get_default_config(self, client: TestClient, org_apex, admin_user):
        headers = get_token_headers(admin_user)
        res = client.get("/api/v1/monitoring/config", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["evidence_max_age_days"] == 90
        assert data["assessment_max_age_days"] == 180
        assert data["finding_sla_critical_days"] == 15
        assert data["is_enabled"] is True

    def test_update_config_as_manager(self, client: TestClient, db, org_apex, admin_user):
        from app.models.user import User
        from app.core.permissions import RoleEnum
        from app.core.security import get_password_hash

        mgr = User(
            email="mgr_ccm@apexfinancial.com",
            hashed_password=get_password_hash("MgrPass123!"),
            full_name="CCM Manager",
            role=RoleEnum.MANAGER,
            is_active=True,
            organization_id=org_apex.id,
        )
        db.add(mgr)
        db.commit()

        headers = get_token_headers(mgr)
        res = client.patch(
            "/api/v1/monitoring/config",
            headers=headers,
            json={
                "evidence_max_age_days": 60,
                "finding_sla_critical_days": 7,
                "frequency_hours": 12,
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["evidence_max_age_days"] == 60
        assert data["finding_sla_critical_days"] == 7
        assert data["frequency_hours"] == 12

    def test_viewer_cannot_update_config(self, client: TestClient, viewer_user):
        headers = get_token_headers(viewer_user)
        res = client.patch(
            "/api/v1/monitoring/config",
            headers=headers,
            json={"evidence_max_age_days": 30},
        )
        assert res.status_code == 403
