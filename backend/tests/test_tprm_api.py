from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.control import ImplementationStatusEnum, OrganizationControl
from app.models.evidence import EvidenceItem, EvidenceStatusEnum, EvidenceTypeEnum
from app.models.harmonization import CommonControlDomainEnum, RationalizedCommonControl
from app.models.tprm import (
    BusinessCriticalityEnum,
    DataClassificationEnum,
    EngagementStatusEnum,
    HostingModelEnum,
    NetworkConnectivityEnum,
    PiiFinancialAccessEnum,
    Vendor,
    VendorAssessment,
    VendorAssessmentItem,
    VendorAssessmentStatusEnum,
    VendorAssessmentTypeEnum,
    VendorDocumentTypeEnum,
    VendorEngagement,
    VendorEvidenceLink,
    VendorResponseStatusEnum,
    VendorRiskBandEnum,
    VendorStatusEnum,
    VendorTierEnum,
)
from app.models.user import User
from tests.conftest import get_token_headers


class TestTPRMAPI:
    """End-to-end API lifecycle and RBAC verification for Phase 9 TPRM."""

    def test_vendor_crud_lifecycle(self, client: TestClient, db: Session, admin_user):
        """Test full Vendor CRUD: create, read, list, update, overview."""
        headers = get_token_headers(admin_user)

        # 1. Create
        create_payload = {
            "vendor_code": "VND-API-01",
            "legal_name": "Datadog Inc",
            "trade_name": "Datadog",
        }
        res_create = client.post("/api/v1/vendors", json=create_payload, headers=headers)
        assert res_create.status_code == 201
        data = res_create.json()
        assert data["vendor_code"] == "VND-API-01"
        assert data["vendor_status"] == "PROSPECT"
        v_id = data["id"]

        # 2. Get by ID
        res_get = client.get(f"/api/v1/vendors/{v_id}", headers=headers)
        assert res_get.status_code == 200
        assert res_get.json()["legal_name"] == "Datadog Inc"

        # 3. List
        res_list = client.get("/api/v1/vendors", headers=headers)
        assert res_list.status_code == 200
        assert len(res_list.json()) >= 1

        # 4. Update metadata
        res_update = client.patch(
            f"/api/v1/vendors/{v_id}",
            json={"trade_name": "Datadog Cloud"},
            headers=headers,
        )
        assert res_update.status_code == 200
        assert res_update.json()["trade_name"] == "Datadog Cloud"

        # 5. Overview
        res_overview = client.get("/api/v1/vendors/overview", headers=headers)
        assert res_overview.status_code == 200
        ov_data = res_overview.json()
        assert ov_data["total_vendors"] >= 1

    def test_assessment_submit_reject_and_approve_workflow(
        self, client: TestClient, db: Session, admin_user, analyst_user, org_apex
    ):
        """Test assessment lifecycle: DRAFT -> SUBMITTED (IN_REVIEW) -> REJECTED -> SUBMITTED -> APPROVED."""
        analyst_headers = get_token_headers(analyst_user)
        admin_headers = get_token_headers(admin_user)

        # 1. Create vendor
        res_v = client.post(
            "/api/v1/vendors",
            json={"vendor_code": "VND-FLOW-01", "legal_name": "Flow Vendor"},
            headers=admin_headers,
        )
        assert res_v.status_code == 201
        v_id = res_v.json()["id"]

        # Transition vendor to DUE_DILIGENCE
        client.patch(f"/api/v1/vendors/{v_id}", json={"vendor_status": "DUE_DILIGENCE"}, headers=admin_headers)

        # 2. Create Assessment by Analyst
        asm_payload = {
            "assessment_code": "ASM-FLOW-01",
            "title": "Security Due Diligence",
            "assessment_type": "INITIAL_DUE_DILIGENCE",
            "items": [
                {"question_key": "MFA_01", "question_text": "Is MFA required for all users?", "weight": 2.0},
                {"question_key": "ENC_01", "question_text": "Is data encrypted at rest?", "weight": 1.0},
            ],
        }
        res_asm = client.post(f"/api/v1/vendors/{v_id}/assessments", json=asm_payload, headers=analyst_headers)
        assert res_asm.status_code == 201
        asm_data = res_asm.json()
        asm_id = asm_data["id"]
        item1_id = asm_data["items"][0]["id"]
        item2_id = asm_data["items"][1]["id"]

        # 3. Fill Questionnaire Items
        patch_items_payload = {
            str(item1_id): {"response_status": "COMPLIANT", "vendor_response_text": "Okta MFA Enforced"},
            str(item2_id): {"response_status": "PARTIALLY_COMPLIANT", "vendor_response_text": "AES-256 in DB"},
        }
        res_items = client.patch(
            f"/api/v1/vendors/assessments/{asm_id}/items",
            json=patch_items_payload,
            headers=analyst_headers,
        )
        assert res_items.status_code == 200
        # Score = (2.0*1.0 + 1.0*0.5) / 3.0 * 100 = 2.5 / 3.0 * 100 = 83.3%
        assert res_items.json()["calculated_score"] == 83.3

        # 4. Submit for review (transitions DRAFT -> SUBMITTED)
        res_sub = client.post(f"/api/v1/vendors/assessments/{asm_id}/submit", headers=analyst_headers)
        assert res_sub.status_code == 200
        assert res_sub.json()["status"] == "SUBMITTED"

        # Attempt to approve directly from SUBMITTED -> Must fail (must be IN_REVIEW)
        res_early_appr = client.post(
            f"/api/v1/vendors/assessments/{asm_id}/approve",
            json={"review_notes": "Early approval attempt"},
            headers=admin_headers,
        )
        assert res_early_appr.status_code == 400

        # Start review (transitions SUBMITTED -> IN_REVIEW)
        res_start = client.post(f"/api/v1/vendors/assessments/{asm_id}/start-review", headers=admin_headers)
        assert res_start.status_code == 200
        assert res_start.json()["status"] == "IN_REVIEW"

        # 5. Reject by Admin (Manager) (transitions IN_REVIEW -> DRAFT)
        res_rej = client.post(
            f"/api/v1/vendors/assessments/{asm_id}/reject",
            json={"rejection_reason": "Need SOC 2 report attached"},
            headers=admin_headers,
        )
        assert res_rej.status_code == 200
        assert res_rej.json()["status"] == "DRAFT"

        # 6. Re-submit by Analyst (DRAFT -> SUBMITTED)
        res_sub2 = client.post(f"/api/v1/vendors/assessments/{asm_id}/submit", headers=analyst_headers)
        assert res_sub2.status_code == 200
        assert res_sub2.json()["status"] == "SUBMITTED"

        # Start review again (SUBMITTED -> IN_REVIEW)
        res_start2 = client.post(f"/api/v1/vendors/assessments/{asm_id}/start-review", headers=admin_headers)
        assert res_start2.status_code == 200
        assert res_start2.json()["status"] == "IN_REVIEW"

        # 7. Approve by Admin (Manager) (IN_REVIEW -> APPROVED)
        res_appr = client.post(
            f"/api/v1/vendors/assessments/{asm_id}/approve",
            json={"review_notes": "SOC 2 attached and verified"},
            headers=admin_headers,
        )
        assert res_appr.status_code == 200
        assert res_appr.json()["status"] == "APPROVED"
        assert res_appr.json()["reviewer_id"] == admin_user.id

        # Attempt to modify approved assessment -> Must fail
        res_mutate = client.patch(
            f"/api/v1/vendors/assessments/{asm_id}/items",
            json={str(item1_id): {"response_status": "NON_COMPLIANT"}},
            headers=analyst_headers,
        )
        assert res_mutate.status_code == 400

        # 8. Now vendor can transition to APPROVED
        res_v_appr = client.patch(
            f"/api/v1/vendors/{v_id}",
            json={"vendor_status": "APPROVED"},
            headers=admin_headers,
        )
        assert res_v_appr.status_code == 200
        assert res_v_appr.json()["vendor_status"] == "APPROVED"

    def test_vendor_risk_posture_telemetry(
        self, client: TestClient, db: Session, admin_user, analyst_user, org_apex
    ):
        """Test GET /api/v1/vendors/{id}/risk-posture returns complete telemetry."""
        admin_headers = get_token_headers(admin_user)
        analyst_headers = get_token_headers(analyst_user)

        # Create vendor
        res_v = client.post(
            "/api/v1/vendors",
            json={"vendor_code": "VND-POS-01", "legal_name": "Telemetry Vendor"},
            headers=admin_headers,
        )
        v_id = res_v.json()["id"]

        # Create critical engagement
        eng_payload = {
            "engagement_code": "ENG-POS-01",
            "engagement_name": "Core Banking SaaS",
            "criticality": "CRITICAL",
            "data_classification": "RESTRICTED",
            "hosting_model": "MULTI_TENANT_SAAS",
            "network_connectivity": "DIRECT_API_VPN_DB",
            "pii_access": "DIRECT_PCI_PII_PHI",
        }
        res_eng = client.post(f"/api/v1/vendors/{v_id}/engagements", json=eng_payload, headers=admin_headers)
        assert res_eng.status_code == 201

        # Query posture
        res_pos = client.get(f"/api/v1/vendors/{v_id}/risk-posture", headers=analyst_headers)
        assert res_pos.status_code == 200
        pos_data = res_pos.json()
        assert pos_data["inherent"]["inherent_risk_score"] == 100.0
        assert pos_data["inherent"]["calculated_tier"] == "TIER_1_CRITICAL"
        assert pos_data["residual"]["risk_floor"] == 20.0
