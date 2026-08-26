from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.framework import FrameworkSubcategory
from app.models.harmonization import FrameworkCrosswalkMapping, MappingTypeEnum
from tests.conftest import get_token_headers


class TestHarmonizationCrosswalk:

    def test_crosswalk_crud_lifecycle_as_admin(
        self, client: TestClient, db: Session, admin_user, seeded_framework
    ):
        """Admin can create, get, patch, and delete global normative crosswalk mappings."""
        admin_headers = get_token_headers(admin_user)
        subcats = seeded_framework.functions[0].categories[0].subcategories
        subcat1 = subcats[0]
        subcat2 = subcats[1]

        # 1. Create crosswalk
        create_payload = {
            "source_subcategory_id": subcat1.id,
            "target_subcategory_id": subcat2.id,
            "mapping_type": "EXACT",
            "confidence_score": 0.95,
            "bidirectional": True,
            "rationale": "High confidence alignment",
        }
        res_create = client.post("/api/v1/harmonization/crosswalks", json=create_payload, headers=admin_headers)
        assert res_create.status_code == 201
        cw_id = res_create.json()["id"]

        # 2. Get crosswalk by ID
        res_get = client.get(f"/api/v1/harmonization/crosswalks/{cw_id}", headers=admin_headers)
        assert res_get.status_code == 200
        assert res_get.json()["confidence_score"] == 0.95

        # 3. Patch crosswalk
        patch_payload = {
            "confidence_score": 0.98,
            "rationale": "Refined alignment",
        }
        res_patch = client.patch(f"/api/v1/harmonization/crosswalks/{cw_id}", json=patch_payload, headers=admin_headers)
        assert res_patch.status_code == 200
        assert res_patch.json()["confidence_score"] == 0.98
        assert res_patch.json()["rationale"] == "Refined alignment"

        # 4. Delete crosswalk
        res_del = client.delete(f"/api/v1/harmonization/crosswalks/{cw_id}", headers=admin_headers)
        assert res_del.status_code == 204

        # 5. Verify deleted
        res_get_deleted = client.get(f"/api/v1/harmonization/crosswalks/{cw_id}", headers=admin_headers)
        assert res_get_deleted.status_code == 404

    def test_self_crosswalk_rejected(
        self, client: TestClient, db: Session, admin_user, seeded_framework
    ):
        """Crosswalking a subcategory to itself is rejected with 400 Bad Request."""
        admin_headers = get_token_headers(admin_user)
        subcat = seeded_framework.functions[0].categories[0].subcategories[0]
        payload = {
            "source_subcategory_id": subcat.id,
            "target_subcategory_id": subcat.id,
            "mapping_type": "EXACT",
            "confidence_score": 1.0,
            "rationale": "Self crosswalk attempt",
        }
        res = client.post("/api/v1/harmonization/crosswalks", json=payload, headers=admin_headers)
        assert res.status_code == 400
        assert "itself" in res.json()["detail"].lower()

    def test_duplicate_crosswalk_rejected(
        self, client: TestClient, db: Session, admin_user, seeded_framework
    ):
        """Creating duplicate crosswalk for same (source, target) returns 409 Conflict."""
        admin_headers = get_token_headers(admin_user)
        subcats = seeded_framework.functions[0].categories[0].subcategories
        payload = {
            "source_subcategory_id": subcats[0].id,
            "target_subcategory_id": subcats[1].id,
            "mapping_type": "EXACT",
            "confidence_score": 1.0,
            "rationale": "Duplicate test",
        }
        res1 = client.post("/api/v1/harmonization/crosswalks", json=payload, headers=admin_headers)
        assert res1.status_code == 201

        res2 = client.post("/api/v1/harmonization/crosswalks", json=payload, headers=admin_headers)
        assert res2.status_code == 409

    def test_non_admin_cannot_mutate_crosswalks(
        self, client: TestClient, db: Session, analyst_user, auditor_user, viewer_user, seeded_framework
    ):
        """Non-admin roles (GRC analyst, auditor, viewer) cannot POST, PATCH, or DELETE crosswalks."""
        subcats = seeded_framework.functions[0].categories[0].subcategories
        payload = {
            "source_subcategory_id": subcats[0].id,
            "target_subcategory_id": subcats[1].id,
            "mapping_type": "EXACT",
            "confidence_score": 1.0,
            "rationale": "Unauthorized attempt",
        }

        # Analyst
        res_analyst = client.post("/api/v1/harmonization/crosswalks", json=payload, headers=get_token_headers(analyst_user))
        assert res_analyst.status_code == 403

        # Auditor
        res_auditor = client.post("/api/v1/harmonization/crosswalks", json=payload, headers=get_token_headers(auditor_user))
        assert res_auditor.status_code == 403

        # Viewer
        res_viewer = client.post("/api/v1/harmonization/crosswalks", json=payload, headers=get_token_headers(viewer_user))
        assert res_viewer.status_code == 403
