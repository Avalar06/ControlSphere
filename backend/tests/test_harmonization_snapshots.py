from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.harmonization import FrameworkComplianceSnapshot
from tests.conftest import get_token_headers


class TestHarmonizationSnapshots:

    def test_snapshot_creation_and_query_endpoints(
        self, client: TestClient, db: Session, admin_user, seeded_framework
    ):
        """Create snapshots and query via list, framework-scoped list, and single-id endpoints."""
        admin_headers = get_token_headers(admin_user)

        # 1. Trigger snapshot creation
        res_create = client.post(
            f"/api/v1/harmonization/frameworks/{seeded_framework.id}/evaluate",
            headers=admin_headers,
        )
        assert res_create.status_code == 201
        snap_id = res_create.json()["id"]
        assert res_create.json()["calculation_version"] == "v1.0"

        # 2. Get single snapshot
        res_get = client.get(f"/api/v1/harmonization/snapshots/{snap_id}", headers=admin_headers)
        assert res_get.status_code == 200
        assert res_get.json()["id"] == snap_id
        assert res_get.json()["calculation_version"] == "v1.0"

        # 3. List snapshots for specific framework
        res_fw_list = client.get(
            f"/api/v1/harmonization/frameworks/{seeded_framework.id}/snapshots",
            headers=admin_headers,
        )
        assert res_fw_list.status_code == 200
        assert len(res_fw_list.json()) >= 1
        assert res_fw_list.json()[0]["framework_id"] == seeded_framework.id

        # 4. List all snapshots
        res_all = client.get("/api/v1/harmonization/snapshots", headers=admin_headers)
        assert res_all.status_code == 200
        assert len(res_all.json()) >= 1

    def test_snapshot_immutability_patch_and_delete_return_405(
        self, client: TestClient, db: Session, admin_user, org_apex, seeded_framework
    ):
        """Snapshots are strictly immutable. Attempting to PATCH or DELETE a snapshot returns 405 Method Not Allowed."""
        admin_headers = get_token_headers(admin_user)

        snap = FrameworkComplianceSnapshot(
            organization_id=org_apex.id,
            framework_id=seeded_framework.id,
            calculation_version="v1.0",
            coverage_percentage=50.0,
            compliance_health_score=50.0,
        )
        db.add(snap)
        db.commit()
        db.refresh(snap)

        # Attempt PATCH
        res_patch = client.patch(
            f"/api/v1/harmonization/snapshots/{snap.id}",
            json={"coverage_percentage": 100.0},
            headers=admin_headers,
        )
        assert res_patch.status_code == 405

        # Attempt DELETE
        res_delete = client.delete(
            f"/api/v1/harmonization/snapshots/{snap.id}",
            headers=admin_headers,
        )
        assert res_delete.status_code == 405

    def test_foreign_snapshot_returns_404(
        self, client: TestClient, db: Session, admin_user, org_meridian, seeded_framework
    ):
        """Querying a snapshot from another tenant returns 404 Not Found."""
        admin_headers = get_token_headers(admin_user)

        foreign_snap = FrameworkComplianceSnapshot(
            organization_id=org_meridian.id,
            framework_id=seeded_framework.id,
            calculation_version="v1.0",
            coverage_percentage=80.0,
            compliance_health_score=85.0,
        )
        db.add(foreign_snap)
        db.commit()
        db.refresh(foreign_snap)

        res = client.get(f"/api/v1/harmonization/snapshots/{foreign_snap.id}", headers=admin_headers)
        assert res.status_code == 404
