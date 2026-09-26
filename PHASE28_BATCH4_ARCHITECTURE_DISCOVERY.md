# PHASE 28 — BATCH 4 ARCHITECTURE DISCOVERY: ENTERPRISE POLICY LIFECYCLE & WORKFORCE ATTESTATION GOVERNANCE (`POLICY-LIFECYCLE-GRC`)

**Repository**: `E:\PROJECT WORKSPACE 2\ControlSphere` (`https://github.com/Avalar06/ControlSphere.git`)  
**Branch**: `main`  
**Frozen Baseline Commit**: `9c34411f5cc4f7f5b849e457d2304ea1e9fc00bd` (`feat(batch3): implement data governance and lineage`)  
**Alembic Head**: `0024` (`0024_data_governance_and_lineage.py`)  
**Discovery Date**: `2026-09-26`  
**Task Classification**: Architecture Discovery & Implementation Boundary Specification Only (Zero Application Code Changes)

---

## 1. EXECUTIVE SUMMARY

Batch 4 (`POLICY-LIFECYCLE-GRC`) governs **Enterprise Policy Lifecycle & Workforce Attestation Governance** across the ControlSphere platform.

Repository inspection reveals a critical architectural baseline fact:
1. **Phase 2 (`0002_frameworks_controls_policies.py`)** introduced the foundational `policies`, `policy_versions`, and `policy_control_mappings` tables.
2. **Historical Phase 24 (`8b8b482` — `0021_policy_lifecycle_and_attestation.py`)** already implemented the core multi-table schema (`PolicyReviewWorkflow`, `PolicyAttestationCampaign`, `UserAttestationRecord`, and enhanced `PolicyVersion` columns), `PolicyService` (`backend/app/services/policy_service.py`, 1,094 lines), FastAPI router (`backend/app/api/v1/endpoints/policies.py`, 1,066 lines), React pages (`PoliciesPage.tsx`, `PolicyDetailPage.tsx`, `DashboardPage.tsx`), and 48 existing policy tests (`test_policies.py`, `test_phase24_api.py`, `test_phase24_adversarial_security.py`).

However, deep code-level inspection of the existing Phase 24 implementation against enterprise GRC governance invariants reveals **seven concrete architectural and security gaps** that must be hardened in Batch 4 without breaking any existing Phase 2 or Phase 24 tests:

1. **Review Workflow Replay & Decision State Machine Gap (`PolicyService.review_policy_version_workflow`)**:
   - `review_policy_version_workflow` (`backend/app/services/policy_service.py` lines 484–536) does **not** verify `wf.status == PolicyReviewStatusEnum.PENDING` or `ver.status == PolicyVersionStatusEnum.UNDER_REVIEW`, allowing an already `APPROVED` or `REJECTED` review workflow to be replayed or mutated.
   - Four-Eyes Segregation of Duties (SoD) checks `ver.created_by_id == current_user_id`, but does not verify `wf.created_by_id == current_user_id` (preventing a non-author submitter from self-approving their own review submission) or enforce assigned reviewer constraints when `wf.assigned_reviewer_id` is explicitly designated.
   - Rejecting a version (`decision == "REJECT"`) transitions `ver.status` to `ARCHIVED` without requiring non-empty `review_notes` justification.
2. **Version Deletion Immutability Gap (`PolicyService.delete_policy_version`)**:
   - `delete_policy_version` (`backend/app/services/policy_service.py` lines 579–615) only blocks deletion when a version is bound to an `ACTIVE` campaign (`CampaignStatusEnum.ACTIVE`). It currently permits deleting an `UNDER_REVIEW`, `APPROVED`, `PUBLISHED`, or `SUPERSEDED` version, or a version bound to a `COMPLETED` campaign with historical attestation records.
3. **Campaign Creation Cross-Tenant Assessment & Target Validation Gaps (`PolicyService.create_campaign`)**:
   - `create_campaign` (`backend/app/services/policy_service.py` lines 619–668) accepts an optional `assessment_id` without validating that `Assessment.organization_id == organization_id` at creation time, and accepts `target_type == ROLE_BASED` without validating that `target_role` is a valid `RoleEnum`.
4. **Campaign Lifecycle State Machine & Roster Inspection Gaps (`close_campaign`, `cancel_campaign`, `list_campaign_records`)**:
   - `close_campaign` (`backend/app/services/policy_service.py` lines 775–786) does not verify `campaign.status == CampaignStatusEnum.ACTIVE`, allowing `DRAFT` or `CANCELLED` campaigns to be marked `COMPLETED`.
   - No endpoint exists to cancel a `DRAFT` or `ACTIVE` campaign (`POST /api/v1/policies/campaigns/{campaign_id}/cancel`).
   - No endpoint exists for campaign managers or auditors to list the per-user attestation roster for a campaign (`GET /api/v1/policies/campaigns/{campaign_id}/records`).
5. **Overdue Attestation & Policy Exception Exemption Governance Gaps**:
   - `AttestationRecordStatusEnum.OVERDUE` exists in `backend/app/models/policy.py`, and `'EXEMPTED'` / `overdue_count` exist in `frontend/src/types/index.ts` (lines 192, 261), but `OVERDUE` is never computed or persisted anywhere in `policy_service.py`, and workforce exemptions backed by Phase 5 `SecurityException` (`ExceptionTypeEnum.POLICY_EXCEPTION`) are not wired into `UserAttestationRecord`.
6. **Frontend-Backend Contract Mismatch on `/api/v1/policies/my-pending-attestations`**:
   - `DashboardPage.tsx` (lines 161–164, 701–715) expects `policy_version_hash`, `policy_content`, `campaign_code`, `version_number`, and `record_id` from `GET /api/v1/policies/my-pending-attestations`, whereas `PolicyService.get_user_pending_attestations` (`policy_service.py` lines 803–826) and `UserAttestationRecordResponse` (`schemas/policy.py` lines 206–224) omit `policy_version_hash`, `policy_content`, `campaign_code`, `version_number`, and `record_id`.
7. **Enterprise Policy Telemetry & Cross-Module Posture Aggregation**:
   - No dedicated `GET /api/v1/policies/telemetry` endpoint exists to provide real-time organization-wide policy lifecycle posture, review cadence compliance, campaign completion rates, overdue attestation counts, and active policy exception counts.

Batch 4 (`POLICY-LIFECYCLE-GRC`) will **extend and harden** the existing Phase 2 / Phase 24 policy architecture in place via Alembic migration `0025_policy_lifecycle_governance_hardening.py` while preserving 100% backward compatibility with all existing tests and routes.

---

## 2. BASELINE VERIFICATION

Repository state verified via read-only git and Alembic inspection:

| Verification Check | Expected | Actual Repository State | Status |
|---|---|---|---|
| Working Directory | `E:\PROJECT WORKSPACE 2\ControlSphere` | `E:\PROJECT WORKSPACE 2\ControlSphere` | **PASS** |
| Git Branch | `main` | `main` (`git status` clean) | **PASS** |
| Batch 3 Frozen Commit (`HEAD`) | `9c34411f5cc4f7f5b849e457d2304ea1e9fc00bd` | `9c34411f5cc4f7f5b849e457d2304ea1e9fc00bd` (`feat(batch3): implement data governance and lineage`) | **PASS** |
| Batch 2 Parent Commit | `7b5c7954c33f6aca44b7a193ad91d1b384188456` | `7b5c7954c33f6aca44b7a193ad91d1b384188456` (`feat(batch2): implement kri appetite governance`) | **PASS** |
| Batch 1 Commit | `a3e9b4ab6926789479399e0e56df7138a7640c40` | `a3e9b4ab6926789479399e0e56df7138a7640c40` (`feat(batch1): implement audit fieldwork governance`) | **PASS** |
| Historical Phase 24 Commit | `8b8b482` | `8b8b482` (`feat(phase24): implement policy lifecycle and workforce attestation governance`) | **PASS** |
| Alembic Head | `0024 (head)` | `0024 (head)` (`0024_data_governance_and_lineage.py`) | **PASS** |

---

## 3. EXISTING REPOSITORY SURFACE INVENTORY

| Layer | File Path | Lines | Classification | Notes |
|---|---|---|---|---|
| **Models** | `backend/app/models/policy.py` | 261 | **EXTEND IN PLACE** | Defines `Policy`, `PolicyVersion`, `PolicyReviewWorkflow`, `PolicyAttestationCampaign`, `UserAttestationRecord`, `PolicyControlMapping` and 8 enums. |
| **Models Registry** | `backend/app/models/__init__.py` | 661 | **REUSE AS-IS** | Already imports and exports all 6 policy models and 8 policy enums (lines 16–31). |
| **Schemas** | `backend/app/schemas/policy.py` | 236 | **EXTEND & HARDEN** | Defines policy, version, review workflow, campaign, attestation, and evidence manifest schemas. Needs new schemas for exemptions, campaign records, review listing, and telemetry, plus hardened field validators. |
| **Services** | `backend/app/services/policy_service.py` | 1,094 | **EXTEND & HARDEN** | Implements `PolicyService`. Needs state-machine guards, review replay protection, version deletion immutability, overdue calculation, exemption handling, and telemetry. |
| **API Endpoints** | `backend/app/api/v1/endpoints/policies.py` | 1,066 | **EXTEND & HARDEN** | Mounted at `/api/v1/policies`. Has 19 endpoints. Needs new endpoints for campaign cancellation, campaign roster, exemption grant, review workflow listing, overdue sweep, and policy telemetry. |
| **Router Registration** | `backend/app/api/v1/api.py` | 74 | **REUSE AS-IS** | Registers `policies.router` at `prefix="/policies"` on line 41. |
| **RBAC Permissions** | `backend/app/core/permissions.py` | 528 | **REUSE AS-IS** | Defines `POLICY_READ`, `POLICY_MANAGE`, `POLICY_APPROVE`, `POLICY_CAMPAIGN_MANAGE`, `POLICY_ATTEST` (lines 48–52) across all 6 roles. |
| **Migrations** | `backend/alembic/versions/0002_frameworks_controls_policies.py` | 145 | **FROZEN HISTORICAL** | Created `policies`, `policy_versions`, `policy_control_mappings`. |
| **Migrations** | `backend/alembic/versions/0021_policy_lifecycle_and_attestation.py` | 282 | **FROZEN HISTORICAL** | Added `PolicyVersion` columns and created `policy_review_workflows`, `policy_attestation_campaigns`, `user_attestation_records`. |
| **Frontend Pages** | `frontend/src/pages/PoliciesPage.tsx` | 963 | **EXTEND IN PLACE** | Policy repository & attestation campaign management page. Needs campaign roster drawer/modal, cancel action, overdue sweep, and telemetry banner. |
| **Frontend Pages** | `frontend/src/pages/PolicyDetailPage.tsx` | 935 | **EXTEND IN PLACE** | Version viewer, side-by-side diff, Four-Eyes review modal, control mapping panel. |
| **Frontend Pages** | `frontend/src/pages/DashboardPage.tsx` | 758 | **REUSE AS-IS** | Self-service workforce attestation banner and modal consuming `/api/v1/policies/my-pending-attestations`. |
| **Frontend Types** | `frontend/src/types/index.ts` | 4,456 | **EXTEND IN PLACE** | Lines 154–320 define policy, version, workflow, campaign, and attestation interfaces. |
| **Tests** | `backend/tests/test_policies.py` | 183 | **PRESERVE 100%** | 7 foundational Phase 2 policy tests. |
| **Tests** | `backend/tests/test_phase24_api.py` | 231 | **PRESERVE 100%** | 2 end-to-end Phase 24 lifecycle and campaign tests. |
| **Tests** | `backend/tests/test_phase24_adversarial_security.py` | 1,297 | **PRESERVE 100%** | 38 adversarial security tests covering tenant isolation, hash verification, Four-Eyes SoD, evidence lineage, and comprehension checks. |

---

## 4. EXISTING POLICY MODEL & SCHEMA ANALYSIS

### 4.1 Database Models (`backend/app/models/policy.py`)

1. **`Policy` (`policies`)**:
   - `id` (PK), `organization_id` (`FK organizations.id`, `CASCADE`, indexed)
   - `title` (`String(255)`), `description` (`Text`), `policy_type` (`Enum(PolicyTypeEnum)`), `status` (`Enum(PolicyStatusEnum)`, default `DRAFT`)
   - `owner_id` (`FK users.id`, `SET NULL`), `effective_date` (`DateTime(timezone=True)`), `review_date` (`DateTime(timezone=True)`)
   - `created_at`, `updated_at`
   - Relationships: `organization`, `owner`, `versions` (ordered desc by `version_number`), `control_mappings`, `campaigns`.

2. **`PolicyVersion` (`policy_versions`)**:
   - `id` (PK), `policy_id` (`FK policies.id`, `CASCADE`), `organization_id` (`FK organizations.id`, `CASCADE`)
   - `version_number` (`Integer`, not null)
   - `content` (`Text`, not null), `change_summary` (`String(500)`)
   - `content_hash_sha256` (`String(64)`, indexed)
   - `status` (`Enum(PolicyVersionStatusEnum)`, default `DRAFT`: `DRAFT`, `UNDER_REVIEW`, `APPROVED`, `PUBLISHED`, `SUPERSEDED`, `ARCHIVED`)
   - `created_by_id` (`FK users.id`, `SET NULL`), `approved_by_id` (`FK users.id`, `SET NULL`)
   - `approved_at` (`DateTime(timezone=True)`), `effective_date` (`Date`), `created_at` (`DateTime(timezone=True)`)
   - Constraint: `UniqueConstraint("policy_id", "version_number", name="uq_policy_version_number")`.

3. **`PolicyReviewWorkflow` (`policy_review_workflows`)**:
   - `id` (PK), `organization_id` (`FK organizations.id`, `CASCADE`), `policy_id` (`FK policies.id`, `CASCADE`), `version_id` (`FK policy_versions.id`, `CASCADE`)
   - `workflow_code` (`String(64)`), `review_stage` (`Enum(PolicyReviewStageEnum)`: `LEGAL_REVIEW`, `SECURITY_REVIEW`, `EXECUTIVE_APPROVAL`)
   - `status` (`Enum(PolicyReviewStatusEnum)`: `PENDING`, `APPROVED`, `REJECTED`, `CHANGES_REQUESTED`)
   - `assigned_reviewer_id`, `review_notes`, `reviewed_by_id`, `reviewed_at`, `approved_by_id`, `approved_at`, `created_by_id`, `created_at`
   - Constraint: `UniqueConstraint("organization_id", "workflow_code", name="uq_pol_rev_wf_code")`.

4. **`PolicyAttestationCampaign` (`policy_attestation_campaigns`)**:
   - `id` (PK), `organization_id` (`FK organizations.id`, `CASCADE`), `campaign_code` (`String(64)`), `title` (`String(255)`), `description` (`Text`)
   - `policy_id` (`FK policies.id`, `CASCADE`), `version_id` (`FK policy_versions.id`, `RESTRICT`), `policy_version_hash` (`String(64)`)
   - `target_type` (`Enum(CampaignTargetTypeEnum)`: `ALL_USERS`, `ROLE_BASED`, `CUSTOM_GROUP`), `target_role` (`String(50)`)
   - `due_date` (`DateTime(timezone=True)`), `grace_period_days` (`Integer`, default `0`), `status` (`Enum(CampaignStatusEnum)`: `DRAFT`, `ACTIVE`, `COMPLETED`, `CANCELLED`)
   - `assessment_id` (`FK assessments.id`, `SET NULL`), `total_targeted_count` (`Integer`), `completed_count` (`Integer`)
   - `created_by_id`, `launched_at`, `closed_at`, `created_at`, `updated_at`
   - Constraint: `UniqueConstraint("organization_id", "campaign_code", name="uq_pol_att_camp_code")`.

5. **`UserAttestationRecord` (`user_attestation_records`)**:
   - `id` (PK), `organization_id` (`FK organizations.id`, `CASCADE`), `campaign_id` (`FK policy_attestation_campaigns.id`, `CASCADE`), `policy_id` (`FK policies.id`, `CASCADE`), `version_id` (`FK policy_versions.id`, `CASCADE`), `user_id` (`FK users.id`, `CASCADE`)
   - `status` (`Enum(AttestationRecordStatusEnum)`: `PENDING`, `ATTESTED`, `OVERDUE`)
   - `attested_at`, `ip_address`, `user_agent`, `acknowledgement_text`, `comprehension_passed` (`Boolean`), `attestation_receipt_hash` (`String(64)`), `evidence_item_id` (`FK evidence_items.id`, `SET NULL`), `created_at`
   - Constraint: `UniqueConstraint("organization_id", "campaign_id", "user_id", name="uq_camp_user_attestation")`.

6. **`PolicyControlMapping` (`policy_control_mappings`)**:
   - `id` (PK), `organization_id` (`FK organizations.id`, `CASCADE`), `policy_id` (`FK policies.id`, `CASCADE`), `subcategory_id` (`FK framework_subcategories.id`, `CASCADE`), `created_at`
   - Constraint: `UniqueConstraint("organization_id", "policy_id", "subcategory_id", name="uq_org_policy_subcategory")`.

### 4.2 Backward-Compatibility Observation on Existing Schemas

In `backend/tests/test_phase24_adversarial_security.py`:
- `test_adv_p24_04_forged_user_identity` passes `"user_id"` in the JSON body of `POST /api/v1/policies/campaigns/{campaign_id}/attest` and asserts `status_code == 200` with the server ignoring the injected `user_id`.
- `test_adv_p24_05_forged_organization_id` passes `"organization_id"` in `POST /api/v1/policies` and asserts `status_code == 201` with the server ignoring the injected `organization_id`.
- `test_adv_p24_07_forged_timestamp` passes `"attested_at"` in `POST /api/v1/policies/campaigns/{campaign_id}/attest` and asserts `status_code == 200`.
- `test_adv_p24_22_client_controlled_completion_status` passes `"status"` in `POST /api/v1/policies/campaigns/{campaign_id}/attest` and asserts `status_code == 200`.
- `test_adv_p24_35_client_organization_id_injection_ignored` passes `"organization_id"` in `POST /api/v1/policies/campaigns` and asserts `status_code == 201`.

**Architectural Rule**: Existing schemas (`PolicyCreate`, `PolicyAttestationCampaignCreate`, `UserAttestationSubmit`) MUST continue to silently ignore extra injected fields (`extra="ignore"`) so that `test_adv_p24_04`, `05`, `07`, `22`, and `35` continue to pass with zero regressions, while server-side service methods strictly derive `organization_id`, `user_id`, `status`, `attested_at`, and `attestation_receipt_hash` from authenticated context. New Batch 4 request schemas (`PolicyAttestationExemptionCreate`, `PolicyCampaignCancelRequest`) will enforce `ConfigDict(extra="forbid")`.

---

## 5. EXISTING WORKFLOW & APPROVAL INFRASTRUCTURE

### 5.1 Current Implementation in `PolicyService` (`backend/app/services/policy_service.py`)

1. **`submit_version_for_review` (lines 442–482)**:
   - Verifies `ver.status == PolicyVersionStatusEnum.DRAFT`.
   - Validates `assigned_reviewer_id` belongs to `organization_id` and is active.
   - Recomputes `ver.content_hash_sha256 = compute_canonical_policy_hash(ver.content)`.
   - Transitions `ver.status = PolicyVersionStatusEnum.UNDER_REVIEW` and `pol.status = PolicyStatusEnum.UNDER_REVIEW`.
   - Creates `PolicyReviewWorkflow` with `workflow_code = f"WF-P{policy_id}-V{ver.version_number}-{uuid4().hex[:6].upper()}"` and `status = PolicyReviewStatusEnum.PENDING`.

2. **`review_policy_version_workflow` (lines 484–536)**:
   - Enforces Four-Eyes SoD: `if decision == "APPROVE" and ver.created_by_id == current_user_id: raise ValueError("Four-Eyes Violation...")`.
   - **Gaps Identified**:
     - Missing guard: `if wf.status != PolicyReviewStatusEnum.PENDING` — currently allows re-reviewing an already decided workflow!
     - Missing guard: `if ver.status != PolicyVersionStatusEnum.UNDER_REVIEW` — currently allows reviewing a version that is no longer under review!
     - Missing submitter SoD guard: `if decision == "APPROVE" and wf.created_by_id == current_user_id` — if User A drafted the version and User B submitted it for review, User B should also be blocked from approving their own review submission!
     - Missing assigned-reviewer guard: if `wf.assigned_reviewer_id is not None` and `wf.assigned_reviewer_id != current_user_id`, only an `ADMIN` or the assigned reviewer should be permitted to record the decision.
     - Missing justification guard: `REJECT` and `REQUEST_CHANGES` decisions should require non-empty `review_notes` when enforced on review workflows, or default cleanly if not provided in legacy calls.

---

## 6. EXISTING CAMPAIGN / ATTESTATION / NOTIFICATION INFRASTRUCTURE

1. **Campaign Creation & Launch (`create_campaign`, `launch_campaign`, lines 619–773)**:
   - `create_campaign` binds `policy_id`, `version_id`, and snapshots `policy_version_hash = ver.content_hash_sha256` in `DRAFT` status.
   - `launch_campaign` verifies `campaign.status == CampaignStatusEnum.DRAFT`, resolves active organization users (`ALL_USERS` or `ROLE_BASED`), creates `UserAttestationRecord` rows with `comprehension_passed = False if campaign.assessment_id else True`, and transitions `campaign.status = CampaignStatusEnum.ACTIVE`.
2. **Personal Attestation Submission (`submit_user_attestation`, lines 829–906)**:
   - Verifies `campaign.status == CampaignStatusEnum.ACTIVE`.
   - Verifies caller has a `UserAttestationRecord` in the campaign and `record.status != AttestationRecordStatusEnum.ATTESTED`.
   - Verifies `attest_in.policy_version_hash == campaign.policy_version_hash`.
   - If `campaign.assessment_id` is set, verifies `Assessment.status == COMPLETED` and `Assessment.conclusion == EFFECTIVE`.
   - Computes deterministic SHA-256 `attestation_receipt_hash`.
   - Increments `campaign.completed_count` and auto-completes campaign when `completed_count >= total_targeted_count`.
3. **Notification Infrastructure**:
   - ControlSphere does not use a separate notification table; pending workforce actions are surfaced via `GET /api/v1/policies/my-pending-attestations` (rendered as an action banner on `DashboardPage.tsx`) and immutable `AuditLog` entries (`AuditService.log`).

---

## 7. EXISTING EVIDENCE & CONTROL MAPPING INFRASTRUCTURE

1. **Control Mapping (`PolicyControlMapping`, `policy_service.py` lines 1018–1094)**:
   - Maps `Policy` to `FrameworkSubcategory` within `organization_id` (`uq_org_policy_subcategory`).
   - Blocks adding/removing mappings when `pol.status == PolicyStatusEnum.ARCHIVED`.
2. **Phase 3 Evidence Manifest Generation (`generate_campaign_evidence`, `policy_service.py` lines 910–1014)**:
   - Serializes a deterministic key-sorted JSON manifest containing `campaign_id`, `campaign_code`, `policy_id`, `policy_version_id`, `policy_version_hash`, `total_targeted`, `total_completed`, `completion_rate`, and `attestation_receipts`.
   - Computes `manifest_sha256 = hashlib.sha256(manifest_json_bytes).hexdigest()`.
   - Resolves the primary `OrganizationControl` mapped via `PolicyControlMapping` (`order_by(OrganizationControl.id.asc()).first()`), failing with HTTP 400 if the policy has no mapped `OrganizationControl` in the tenant.
   - Writes the JSON manifest to `settings.EVIDENCE_STORAGE_ROOT/org_{organization_id}/` and creates an `EvidenceItem` with `status = EvidenceStatusEnum.UPLOADED` (never auto-accepted).
   - Links `r.evidence_item_id = evidence_item.id` on all `ATTESTED` records in the campaign.

---

## 8. EXISTING RBAC & PERMISSION MATRIX ANALYSIS

In `backend/app/core/permissions.py` (lines 48–52, 182–523), five granular policy permissions are defined and mapped:

| Permission | Enum Key | `ADMIN` | `MANAGER` | `GRC_ANALYST` | `SECURITY_ANALYST` | `AUDITOR` | `VIEWER` |
|---|---|---:|---:|---:|---:|---:|---:|
| `policy:read` | `Permission.POLICY_READ` | YES | YES | YES | YES | YES | YES |
| `policy:manage` | `Permission.POLICY_MANAGE` | YES | YES | YES | NO | NO | NO |
| `policy:approve` | `Permission.POLICY_APPROVE` | YES | YES | NO | NO | NO | NO |
| `policy:campaign_manage` | `Permission.POLICY_CAMPAIGN_MANAGE` | YES | YES | YES | NO | NO | NO |
| `policy:attest` | `Permission.POLICY_ATTEST` | YES | YES | YES | YES | YES | YES |

**Key RBAC Observations**:
- `GRC_ANALYST` holds `policy:manage` and `policy:campaign_manage` (can author policies, create draft versions, submit versions for review, create/launch campaigns, generate evidence manifests), but does **NOT** hold `policy:approve` (cannot approve/reject review workflows, cannot close campaigns, cannot grant attestation exemptions).
- `MANAGER` and `ADMIN` hold `policy:approve`, enabling them to execute Four-Eyes review decisions (subject to `created_by_id != current_user.id`), close campaigns, and grant governed attestation exemptions.
- All 6 roles hold `policy:read` and `policy:attest`, enabling universal workforce attestation participation.

---

## 9. EXISTING FRONTEND POLICY SURFACE ANALYSIS

1. **`frontend/src/pages/PoliciesPage.tsx` (963 lines)**:
   - Two-tab enterprise workspace:
     - **Tab 1 (`POLICIES`)**: Searchable/filterable policy table showing Title, Domain Type, Status badge, Active Version (`vN`), truncated SHA-256 Content Hash, Owner, Mapped Controls count, and "Author Policy" modal.
     - **Tab 2 (`CAMPAIGNS`)**: KPI summary cards (Total Campaigns, Active Campaigns, Total Targeted, Total Attestations), campaign filter bar, campaign table with progress bar, Launch button (`DRAFT`), Close button (`ACTIVE`), Evidence Manifest button, and "Create Workforce Attestation Campaign" modal.
   - **Frontend Gaps to Address in Batch 4**:
     - Missing **Policy Governance Telemetry Banner** consuming `GET /api/v1/policies/telemetry` (showing Policies Due for Review, Overdue Attestations, Active Policy Exceptions, Overall Attestation Rate).
     - Missing **Campaign Roster & Exemption Modal** (`GET /api/v1/policies/campaigns/{campaign_id}/records`) allowing campaign managers/auditors to inspect individual user attestation status (`PENDING`, `ATTESTED`, `OVERDUE`, `EXEMPTED`), cryptographic receipt hashes, and grant linked `SecurityException` exemptions (`POST /api/v1/policies/campaigns/{campaign_id}/records/{record_id}/exempt`).
     - Missing **Cancel Campaign** button (`POST /api/v1/policies/campaigns/{campaign_id}/cancel`) and **Evaluate Overdue** action (`POST /api/v1/policies/campaigns/{campaign_id}/evaluate-overdue`).
2. **`frontend/src/pages/PolicyDetailPage.tsx` (935 lines)**:
   - Displays version selector dropdown, SHA-256 content hash badge, side-by-side Markdown diff view (`isDiffMode`), "Submit for Formal Review" modal, "Review & Decide (Four-Eyes)" modal with creator self-approval warning, "Publish Version" button, Review & Approval Audit Trail list, and Mapped Controls sidebar.
3. **`frontend/src/pages/DashboardPage.tsx` (758 lines)**:
   - Fetches `/api/v1/policies/my-pending-attestations` and renders the "Mandatory Workforce Attestation Required" banner and self-service attestation modal. Once backend `/my-pending-attestations` includes `policy_version_hash`, `policy_content`, `campaign_code`, `version_number`, and `record_id`, this modal works end-to-end without requiring changes to `DashboardPage.tsx`.

---

## 10. EXISTING TEST SUITE & ADVERSARIAL COVERAGE ANALYSIS

1. **`backend/tests/test_policies.py` (7 tests)**:
   - Tests policy creation with initial v1, metadata update, new version v2 creation, policy status state machine (`DRAFT -> UNDER_REVIEW -> APPROVED -> PUBLISHED`), control mapping add/remove, cross-tenant isolation, and viewer RBAC denial.
2. **`backend/tests/test_phase24_api.py` (2 end-to-end tests)**:
   - `test_phase24_api_full_version_lifecycle`: v2 creation -> submit review -> manager approval -> publish -> verify PUBLISHED status.
   - `test_phase24_api_full_campaign_and_attestation_flow`: campaign creation -> launch -> viewer `/my-pending-attestations` -> viewer `/attest` -> campaign telemetry check -> `/evidence` manifest generation.
3. **`backend/tests/test_phase24_adversarial_security.py` (38 adversarial tests)**:
   - Covers cross-tenant policy/campaign/attestation access (`01–03`), forged user/org/hash/timestamp/campaign (`04–08`), unauthorized approval & Four-Eyes SoD (`09–11`), post-approval version immutability (`12`), hash mismatch & policy substitution (`13–14`), duplicate/replay/concurrent attestation (`15–17`), RBAC & unassigned user rejection (`18–21`), status/evidence status injection (`22–25`), XSS/SQLi (`26–27`), audit log emission (`28–29`), IDOR on `/my-pending-attestations` (`30`), timezone deadlines (`31`), comprehension assessment failure/success (`32, 37, 38`), unapproved publish block (`33`), active campaign version delete block (`34`), org injection (`35`), and deterministic evidence control lineage (`36`).

---

## 11. BATCH 4 TARGET CAPABILITY DEFINITION

Batch 4 (`POLICY-LIFECYCLE-GRC`) completes and hardens the Enterprise Policy Lifecycle & Workforce Attestation Governance module with the following authoritative capabilities:

1. **Hardened Policy Version Immutability & Deletion Protection**:
   - Block deletion of any `PolicyVersion` whose status is in `{UNDER_REVIEW, APPROVED, PUBLISHED, SUPERSEDED}` or that is referenced by any `PolicyAttestationCampaign` (regardless of campaign status) or `UserAttestationRecord`.
   - Block deleting the sole remaining version of a policy (`total_versions <= 1`).
2. **Hardened Four-Eyes Review Workflow State Machine & Replay Prevention**:
   - Block review decisions on any `PolicyReviewWorkflow` not in `PENDING` status (preventing decision replay/overwrite).
   - Block review decisions if the target `PolicyVersion` is not in `UNDER_REVIEW` status.
   - Block duplicate `PENDING` review workflows on the same `version_id` (preventing parallel conflicting review queues for the same version).
   - Enforce dual Four-Eyes SoD on `APPROVE`: `current_user_id != ver.created_by_id` AND `current_user_id != wf.created_by_id`.
   - Enforce `assigned_reviewer_id` authority: if `wf.assigned_reviewer_id` is set, only that user (or an `ADMIN` who is neither the version creator nor the workflow submitter) may record the decision.
   - Provide `GET /api/v1/policies/{policy_id}/versions/{version_id}/reviews` to list all review workflow records for a version.
3. **Hardened Campaign Creation, Cancellation, Roster Inspection & Overdue Sweeps**:
   - Validate `assessment_id` tenant ownership (`Assessment.organization_id == organization_id`) in `create_campaign` and `update_campaign`.
   - Validate `target_role` against `RoleEnum` when `target_type == CampaignTargetTypeEnum.ROLE_BASED`.
   - Block `launch_campaign` if the target user roster resolves to 0 active users (`HTTP 400`).
   - Enforce `campaign.status == CampaignStatusEnum.ACTIVE` in `close_campaign`.
   - Add `POST /api/v1/policies/campaigns/{campaign_id}/cancel` (`DRAFT` or `ACTIVE` -> `CANCELLED`, requiring `Permission.POLICY_APPROVE`).
   - Add `GET /api/v1/policies/campaigns/{campaign_id}/records` to list all `UserAttestationRecord` rows for a campaign with user identity, status, receipt hash, and exemption metadata.
   - Add `POST /api/v1/policies/campaigns/{campaign_id}/evaluate-overdue` (and automatic calculation on read) to transition `PENDING` records past `due_date + timedelta(days=grace_period_days)` to `OVERDUE` and update `campaign.overdue_count`.
4. **Policy Exception-Backed Workforce Attestation Exemptions**:
   - Extend `AttestationRecordStatusEnum` with `EXEMPTED = "EXEMPTED"`.
   - Add `POST /api/v1/policies/campaigns/{campaign_id}/records/{record_id}/exempt` (requiring `Permission.POLICY_APPROVE`), allowing a manager/admin to exempt a user from a campaign when backed by a valid, same-tenant `SecurityException` (`linked_policy_id == campaign.policy_id`, status in `{APPROVED, ACTIVE}`, not expired) and a mandatory `exemption_reason`.
   - Enforce Four-Eyes SoD on exemptions: a user cannot exempt their own attestation record (`record.user_id != current_user_id`).
   - Exempted records count toward campaign completion (`completed_count`) so 100% accounted campaigns (`ATTESTED + EXEMPTED == total_targeted_count`) can complete deterministically.
5. **Complete `/my-pending-attestations` Payload & Policy Governance Telemetry**:
   - Enrich `UserAttestationRecordResponse` and `PolicyService.get_user_pending_attestations` with `record_id`, `campaign_code`, `version_number`, `policy_version_hash`, `policy_content`, and `assessment_id` (including both `PENDING` and `OVERDUE` unattested records for `ACTIVE` campaigns).
   - Add `GET /api/v1/policies/telemetry` returning organization-wide policy lifecycle, review cadence, campaign progress, overdue attestation, and policy exception metrics.

---

## 12. DOMAIN AUTHORITY & BOUNDARY MATRIX

| Domain Entity / Capability | Authoritative Module | Batch 4 (`POLICY-LIFECYCLE-GRC`) Relationship | Mutation Authority |
|---|---|---|---|
| `Policy`, `PolicyVersion`, `PolicyReviewWorkflow`, `PolicyAttestationCampaign`, `UserAttestationRecord`, `PolicyControlMapping` | **Batch 4 (`POLICY-LIFECYCLE-GRC`)** | Primary owner and authoritative state machine | Full CRUD / lifecycle state machine within `policy_service.py` |
| `FrameworkSubcategory` (Phase 2) | **Phase 2 Frameworks** | Referenced by `PolicyControlMapping.subcategory_id` | Read-only lookup |
| `OrganizationControl` (Phase 2) | **Phase 2 Controls** | Resolved via `PolicyControlMapping` when binding campaign `EvidenceItem` | Read-only lookup |
| `EvidenceItem` (Phase 3) | **Phase 3 Evidence** | `generate_campaign_evidence` creates `EvidenceItem` in `UPLOADED` status only | Append-only creation in `UPLOADED` state; **never** auto-accepts (`ACCEPTED` belongs exclusively to Phase 3 `EvidenceReview`) |
| `Assessment` (Phase 4) | **Phase 4 Assessments** | Linked via `PolicyAttestationCampaign.assessment_id` for comprehension gating | Read-only check (`status == COMPLETED` and `conclusion == EFFECTIVE`) |
| `SecurityException` (Phase 5) | **Phase 5 Exceptions** | Linked via `SecurityException.linked_policy_id` and `UserAttestationRecord.exemption_exception_id` | Read-only validation in `policy_service.py` |
| `AuditLog` (Phase 1) | **Phase 1 Audit Trail** | Every state-mutating policy/version/workflow/campaign/attestation endpoint emits an immutable `AuditLog` | Append-only via `AuditService.log` |

---

## 13. CANONICAL DATA MODEL DESIGN

### 13.1 Additive Columns on Existing Tables (Migration `0025`)

#### Table 1: `user_attestation_records` (`UserAttestationRecord`)
| Column | Type | Nullable | Default | Constraints / Foreign Keys | Description |
|---|---|---|---|---|---|
| `exemption_exception_id` | `Integer` | `True` | `None` | `ForeignKey("security_exceptions.id", ondelete="SET NULL")` | Links an `EXEMPTED` attestation record to an approved Phase 5 `SecurityException`. |
| `exemption_reason` | `Text` | `True` | `None` | — | Mandatory justification recorded when an attestation exemption is granted. |
| `exempted_by_id` | `Integer` | `True` | `None` | `ForeignKey("users.id", ondelete="SET NULL")` | Approver (`policy:approve`) who granted the exemption (`!= user_id`). |
| `exempted_at` | `DateTime(timezone=True)` | `True` | `None` | — | Server-authoritative UTC timestamp when exemption was granted. |

*New Composite Index*: `ix_user_att_org_camp_status` on `("organization_id", "campaign_id", "status")`.

#### Table 2: `policy_attestation_campaigns` (`PolicyAttestationCampaign`)
| Column | Type | Nullable | Default | Constraints / Foreign Keys | Description |
|---|---|---|---|---|---|
| `overdue_count` | `Integer` | `False` | `0` | `server_default="0"` | Authoritative count of `OVERDUE` user attestation records in the campaign. |

*New Composite Index*: `ix_pol_camp_org_pol_status` on `("organization_id", "policy_id", "status")`.

#### Table 3: `policy_review_workflows` (`PolicyReviewWorkflow`)
| Column | Type | Nullable | Default | Constraints / Foreign Keys | Description |
|---|---|---|---|---|---|
| `updated_at` | `DateTime(timezone=True)` | `True` | `now()` | `server_default=sa.func.now()` | Timestamp of latest workflow state transition. |

*New Composite Index*: `ix_pol_rev_wf_org_ver_status` on `("organization_id", "version_id", "status")`.

---

## 14. ENUMERATION & STATE MACHINE SPECIFICATIONS

### 14.1 `PolicyVersionStatusEnum` State Machine
- **States**: `DRAFT`, `UNDER_REVIEW`, `APPROVED`, `PUBLISHED`, `SUPERSEDED`, `ARCHIVED`.
- **Allowed Transitions**:
  - `DRAFT -> UNDER_REVIEW` (via `submit_version_for_review`; locks content hash, creates `PENDING` `PolicyReviewWorkflow`).
  - `UNDER_REVIEW -> APPROVED` (via `review_policy_version_workflow` with `decision="APPROVE"`; requires `Permission.POLICY_APPROVE` and Four-Eyes SoD).
  - `UNDER_REVIEW -> DRAFT` (via `review_policy_version_workflow` with `decision="REQUEST_CHANGES"`).
  - `UNDER_REVIEW -> ARCHIVED` (via `review_policy_version_workflow` with `decision="REJECT"`).
  - `APPROVED -> PUBLISHED` (via `publish_policy_version`; transitions any prior `PUBLISHED` version of the same policy to `SUPERSEDED`).
  - `PUBLISHED -> SUPERSEDED` (automatic when a newer `APPROVED` version of the same policy is published).
- **Immutability Invariant**: Content (`content`, `change_summary`) may ONLY be modified in `DRAFT` status. Versions in `UNDER_REVIEW`, `APPROVED`, `PUBLISHED`, or `SUPERSEDED` status can NEVER be modified or deleted.

### 14.2 `PolicyReviewStatusEnum` State Machine
- **States**: `PENDING`, `APPROVED`, `REJECTED`, `CHANGES_REQUESTED`.
- **Allowed Transitions**:
  - `PENDING -> APPROVED` (`decision == "APPROVE"`)
  - `PENDING -> REJECTED` (`decision == "REJECT"`)
  - `PENDING -> CHANGES_REQUESTED` (`decision == "REQUEST_CHANGES"`)
- **Terminal State Invariant**: `APPROVED`, `REJECTED`, and `CHANGES_REQUESTED` are strictly terminal. Any attempt to call `review_policy_version_workflow` on a non-`PENDING` workflow raises `ValueError("Review workflow has already been decided and is immutable")` -> `HTTP 400`.

### 14.3 `CampaignStatusEnum` State Machine
- **States**: `DRAFT`, `ACTIVE`, `COMPLETED`, `CANCELLED`.
- **Allowed Transitions**:
  - `DRAFT -> ACTIVE` (via `launch_campaign`; requires >= 1 targeted active user in organization).
  - `DRAFT -> CANCELLED` (via `cancel_campaign`; requires `Permission.POLICY_APPROVE`).
  - `ACTIVE -> COMPLETED` (via `close_campaign` requiring `Permission.POLICY_APPROVE`, or automatic when `completed_count >= total_targeted_count`).
  - `ACTIVE -> CANCELLED` (via `cancel_campaign`; requires `Permission.POLICY_APPROVE`).
- **Terminal State Invariant**: `COMPLETED` and `CANCELLED` are strictly terminal.

### 14.4 `AttestationRecordStatusEnum` State Machine
- **States**: `PENDING`, `OVERDUE`, `ATTESTED`, `EXEMPTED`.
- **Allowed Transitions**:
  - `PENDING -> ATTESTED` (via `submit_user_attestation`).
  - `PENDING -> OVERDUE` (via `evaluate_campaign_overdue` when `now_utc > campaign.due_date + timedelta(days=campaign.grace_period_days)`).
  - `OVERDUE -> ATTESTED` (via `submit_user_attestation` while campaign remains `ACTIVE` — late attestation is recorded with actual `attested_at` UTC timestamp).
  - `PENDING -> EXEMPTED` / `OVERDUE -> EXEMPTED` (via `exempt_user_attestation` with valid `SecurityException` and Four-Eyes SoD).
- **Terminal State Invariant**: `ATTESTED` and `EXEMPTED` are strictly terminal.

---

## 15. CRYPTOGRAPHIC CONTENT HASHING & IMMUTABILITY SPECIFICATION

`compute_canonical_policy_hash(content: str) -> str` in `backend/app/services/policy_service.py` (lines 48–56):
1. Normalizes all CRLF (`\r\n`) and CR (`\r`) line endings to LF (`\n`).
2. Strips trailing horizontal whitespace per line (`[line.rstrip() for line in normalized.split("\n")]`).
3. Strips leading and trailing document whitespace (`.strip()`).
4. Encodes as UTF-8 and computes lowercase SHA-256 hex digest (`64` hex chars).

**Immutability Guarantees**:
- `PolicyVersion.content_hash_sha256` is computed on version creation (`create_policy`, `create_policy_version`), recomputed on `DRAFT` content edits (`update_policy_version`), and locked upon `submit_version_for_review`.
- When a `PolicyAttestationCampaign` is created, `campaign.policy_version_hash = ver.content_hash_sha256` is snapshotted onto the campaign row.
- When a user attests (`submit_user_attestation`), the client-supplied `policy_version_hash` must exactly match `campaign.policy_version_hash` (`HTTP 400` on mismatch).

---

## 16. FOUR-EYES REVIEW & APPROVAL GOVERNANCE SPECIFICATION

In `PolicyService.review_policy_version_workflow`:
1. **Workflow Status Guard**: `wf.status` MUST be `PolicyReviewStatusEnum.PENDING`. Otherwise raise `ValueError("Review workflow is already finalized in status '...' and cannot be re-decided")`.
2. **Version Status Guard**: `ver.status` MUST be `PolicyVersionStatusEnum.UNDER_REVIEW`. Otherwise raise `ValueError("Policy version is not in UNDER_REVIEW status")`.
3. **Assigned Reviewer Guard**: If `wf.assigned_reviewer_id is not None` and `current_user_id != wf.assigned_reviewer_id`, verify caller has `RoleEnum.ADMIN` (or raise `ValueError("Only the assigned reviewer or an administrator may decide this review workflow")`).
4. **Dual Four-Eyes Segregation of Duties (SoD) Guard on `APPROVE`**:
   - `if ver.created_by_id == current_user_id`: raise `ValueError("Four-Eyes Violation: Policy version author cannot approve their own policy version.")`
   - `if wf.created_by_id is not None and wf.created_by_id == current_user_id`: raise `ValueError("Four-Eyes Violation: Review submitter cannot approve their own review submission.")`
5. **Single Active Review Guard on `submit_version_for_review`**:
   - Before creating a new `PolicyReviewWorkflow`, verify no existing `PENDING` workflow exists for `version_id` in `organization_id`.

---

## 17. POLICY PUBLICATION, SUPERSESSION & ARCHIVAL SPECIFICATION

1. **Publication (`publish_policy_version`)**:
   - Requires `ver.status == PolicyVersionStatusEnum.APPROVED`.
   - Queries all existing `PolicyVersion` rows for `policy_id` with `status == PolicyVersionStatusEnum.PUBLISHED` and transitions them to `PolicyVersionStatusEnum.SUPERSEDED`.
   - Transitions `ver.status = PolicyVersionStatusEnum.PUBLISHED`, sets `ver.effective_date = ver.effective_date or datetime.now(timezone.utc).date()`, and sets `pol.status = PolicyStatusEnum.PUBLISHED`.
2. **Archival (`update_policy_status` to `ARCHIVED`)**:
   - Archiving a policy transitions `pol.status = PolicyStatusEnum.ARCHIVED`.
   - While archived, control mappings (`add_control_mapping`, `remove_control_mapping`), new version creation (`create_policy_version`), and new campaign creation (`create_campaign`) on that policy are blocked (`HTTP 400`).

---

## 18. WORKFORCE ATTESTATION CAMPAIGN ARCHITECTURE

1. **Creation (`create_campaign`)**:
   - Validates `pol` and `ver` belong to `organization_id` and `ver.policy_id == pol.id`.
   - Blocks creating a campaign on an `ARCHIVED` policy or `ARCHIVED` / `SUPERSEDED` version (`if pol.status == PolicyStatusEnum.ARCHIVED` or `ver.status in (PolicyVersionStatusEnum.ARCHIVED, PolicyVersionStatusEnum.SUPERSEDED)` -> `HTTP 400`). *(Note: `DRAFT`, `APPROVED`, and `PUBLISHED` versions remain allowed in `create_campaign` to preserve full backward compatibility with the 38 existing tests in `test_phase24_adversarial_security.py` and `test_phase24_api.py` which create campaigns directly on `v1` in `DRAFT` status).*
   - Validates `campaign_code` uniqueness within `organization_id`.
   - If `assessment_id` is provided, validates that `Assessment` exists in `organization_id` (`HTTP 400` if not found in organization).
   - If `target_type == CampaignTargetTypeEnum.ROLE_BASED`, validates that `target_role` is provided and is a valid `RoleEnum` value (`HTTP 400` if missing or invalid).
2. **Modification (`update_campaign`)**:
   - Allowed only while `campaign.status == CampaignStatusEnum.DRAFT`.
   - `policy_id`, `version_id`, and `policy_version_hash` are immutable after creation.
   - Validates `assessment_id` tenant ownership if updated.
3. **Launch (`launch_campaign`)**:
   - Allowed only while `campaign.status == CampaignStatusEnum.DRAFT`.
   - Resolves target active users in `organization_id`. If `len(users) == 0`, raises `ValueError("Cannot launch campaign: target audience resolved to 0 active users in your organization.")`.
   - Creates `UserAttestationRecord` rows and sets `campaign.status = CampaignStatusEnum.ACTIVE`, `campaign.launched_at = now`.
4. **Close (`close_campaign`) & Cancel (`cancel_campaign`)**:
   - `close_campaign`: Requires `campaign.status == CampaignStatusEnum.ACTIVE` (raises `ValueError` -> `HTTP 400` if `DRAFT`, `COMPLETED`, or `CANCELLED`). Sets `status = CampaignStatusEnum.COMPLETED` and `closed_at = now`.
   - `cancel_campaign`: Requires `campaign.status in (CampaignStatusEnum.DRAFT, CampaignStatusEnum.ACTIVE)` (raises `ValueError` -> `HTTP 400` if already `COMPLETED` or `CANCELLED`). Sets `status = CampaignStatusEnum.CANCELLED` and `closed_at = now`.

---

## 19. TARGET AUDIENCE RESOLUTION & SNAPSHOT SPECIFICATION

When `PolicyService.launch_campaign` executes:
- Queries `User` where `User.organization_id == organization_id` and `User.is_active.is_(True)`.
- If `campaign.target_type == CampaignTargetTypeEnum.ROLE_BASED`:
  - Filters `User.role == RoleEnum(campaign.target_role)`.
- Snapshots the resolved roster into `user_attestation_records` (`UniqueConstraint("organization_id", "campaign_id", "user_id")`) and sets `campaign.total_targeted_count = len(users)`.
- Roster membership is frozen at launch time so subsequent user additions do not retroactively invalidate completion percentages of in-flight campaigns.

---

## 20. ATTESTATION RECEIPT & TAMPER-EVIDENT AUDIT SPECIFICATION

When `PolicyService.submit_user_attestation` executes:
1. Server captures authoritative `now = datetime.now(timezone.utc)` (`now_iso = now.isoformat()`).
2. Constructs canonical pipe-delimited string:
   ```
   f"{organization_id}|{current_user_id}|{campaign.id}|{campaign.version_id}|{campaign.policy_version_hash}|{now_iso}|{client_ip or 'unknown'}"
   ```
3. Computes `receipt_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()`.
4. Stores `record.attestation_receipt_hash = receipt_hash`, `record.attested_at = now`, `record.ip_address = client_ip`, `record.user_agent = client_ua`, `record.status = AttestationRecordStatusEnum.ATTESTED`, and `record.comprehension_passed = True`.
5. Emits `AuditService.log(..., action="policy.attestation.submit", resource_type="USER_ATTESTATION", details={"campaign_id": campaign_id, "receipt_hash": receipt_hash})`.

---

## 21. COMPREHENSION QUIZ / ASSESSMENT AUTHORITY DECISION

**Decision**: **REUSE PHASE 4 `Assessment` ENGINE AS-IS (NO PARALLEL QUIZ TABLE)**.
- `PolicyAttestationCampaign.assessment_id` links to `assessments.id` (`app/models/assessment.py`).
- When `campaign.assessment_id` is non-null:
  - At campaign creation/update: `PolicyService` verifies `Assessment.id == campaign.assessment_id` and `Assessment.organization_id == organization_id`.
  - At campaign launch: `UserAttestationRecord.comprehension_passed` is initialized to `False`.
  - At attestation submission (`submit_user_attestation`): `PolicyService` verifies `assessment.status == AssessmentStatusEnum.COMPLETED` and `assessment.conclusion == AssessmentConclusionEnum.EFFECTIVE`, blocking attestation (`HTTP 400`) otherwise.

---

## 22. EVIDENCE GENERATION & PHASE 3 AUTHORITY BOUNDARY

`PolicyService.generate_campaign_evidence`:
- Generates a deterministic key-sorted JSON manifest (`sort_keys=True`) of campaign metadata and all `ATTESTED` (and `EXEMPTED`) records, writes it to `EVIDENCE_STORAGE_ROOT/org_{organization_id}/`, computes `sha256_hash`, and inserts a Phase 3 `EvidenceItem` bound to the policy's primary mapped `OrganizationControl`.
- **Strict Phase 3 Boundary Invariant**: The created `EvidenceItem` is **always** initialized with `status = EvidenceStatusEnum.UPLOADED`. Policy services **never** set `EvidenceStatusEnum.ACCEPTED` or bypass Phase 3 `EvidenceReview` workflows.

---

## 23. CONTROL, FRAMEWORK, RISK & EXCEPTION INTEGRATION

1. **Controls & Frameworks (Phase 2)**:
   - `PolicyControlMapping` links `Policy` to `FrameworkSubcategory` and resolves to `OrganizationControl` for evidence lineage.
2. **Security Exceptions (Phase 5)**:
   - `SecurityException.linked_policy_id` links policy exceptions (`ExceptionTypeEnum.POLICY_EXCEPTION`) to a `Policy`.
   - New in Batch 4: `PolicyService.exempt_user_attestation` allows a user's `UserAttestationRecord` (`PENDING` or `OVERDUE`) in an `ACTIVE` campaign to be transitioned to `EXEMPTED` when linked to an active, non-expired `SecurityException` in the same organization with `linked_policy_id == campaign.policy_id`.
   - Enforces Four-Eyes SoD: `record.user_id != current_user_id` (approver cannot exempt themselves).

---

## 24. EXECUTIVE & CONTINUOUS COMPLIANCE TELEMETRY INTEGRATION

Batch 4 adds `PolicyService.get_policy_telemetry(db, organization_id)` exposed at `GET /api/v1/policies/telemetry`:
- `total_policies`: count of all policies in organization
- `published_policies`: count of policies with `status == PUBLISHED`
- `draft_policies`: count of policies with `status == DRAFT`
- `under_review_policies`: count of policies with `status == UNDER_REVIEW`
- `archived_policies`: count of policies with `status == ARCHIVED`
- `policies_due_for_review_count`: count of non-archived policies where `review_date <= now_utc`
- `mapped_controls_count`: count of `PolicyControlMapping` rows in organization
- `unmapped_policies_count`: count of non-archived policies with 0 mapped controls
- `total_campaigns`: count of all `PolicyAttestationCampaign` rows in organization
- `active_campaigns`: count of `ACTIVE` campaigns
- `completed_campaigns`: count of `COMPLETED` campaigns
- `total_targeted_attestations`: sum of `total_targeted_count` across `ACTIVE` and `COMPLETED` campaigns
- `total_completed_attestations`: sum of `completed_count` across `ACTIVE` and `COMPLETED` campaigns
- `overall_attestation_completion_rate`: `round(total_completed_attestations / total_targeted_attestations * 100.0, 2)` (or `0.0` if `0`)
- `overdue_attestations_count`: count of `UserAttestationRecord` rows in `OVERDUE` status (after running live deadline evaluation)
- `exempted_attestations_count`: count of `UserAttestationRecord` rows in `EXEMPTED` status
- `active_policy_exceptions_count`: count of Phase 5 `SecurityException` rows for the tenant where `linked_policy_id IS NOT NULL` and `status in (APPROVED, ACTIVE)` and `expiry_date >= today`.

---

## 25. API ENDPOINT SPECIFICATION

All endpoints are mounted under `/api/v1/policies` (`backend/app/api/v1/endpoints/policies.py`). Static paths (`/telemetry`, `/my-pending-attestations`, `/campaigns/*`) are registered **before** parametric `/{policy_id}` routes to prevent path shadowing.

| # | Method & Path | Permission | Classification | Description |
|---|---|---|---|---|
| 1 | `GET /api/v1/policies` | `policy:read` | Existing | List organization policies with filters (`status`, `policy_type`, `owner_id`, `search`). |
| 2 | `POST /api/v1/policies` | `policy:manage` | Existing | Create a new policy with initial v1 draft and SHA-256 hash. |
| 3 | `GET /api/v1/policies/telemetry` | `policy:read` | **NEW (Batch 4)** | Retrieve organization-wide policy governance & attestation telemetry. |
| 4 | `GET /api/v1/policies/my-pending-attestations` | `policy:attest` | **HARDENED** | List caller's `PENDING` and `OVERDUE` attestations with `policy_version_hash` and `policy_content`. |
| 5 | `GET /api/v1/policies/campaigns` | `policy:read` | **HARDENED** | List attestation campaigns (includes `overdue_count`). |
| 6 | `POST /api/v1/policies/campaigns` | `policy:campaign_manage` | **HARDENED** | Create campaign in `DRAFT` (validates `assessment_id` org ownership & `target_role`). |
| 7 | `GET /api/v1/policies/campaigns/{campaign_id}` | `policy:read` | **HARDENED** | Retrieve campaign details and telemetry (`overdue_count`, `completion_rate`). |
| 8 | `PATCH /api/v1/policies/campaigns/{campaign_id}` | `policy:campaign_manage` | **HARDENED** | Update `DRAFT` campaign metadata (validates `assessment_id` org ownership). |
| 9 | `POST /api/v1/policies/campaigns/{campaign_id}/launch` | `policy:campaign_manage` | **HARDENED** | Launch `DRAFT` campaign (blocks 0-user audience). |
| 10 | `POST /api/v1/policies/campaigns/{campaign_id}/close` | `policy:approve` | **HARDENED** | Close `ACTIVE` campaign (`HTTP 400` if not `ACTIVE`). |
| 11 | `POST /api/v1/policies/campaigns/{campaign_id}/cancel` | `policy:approve` | **NEW (Batch 4)** | Cancel `DRAFT` or `ACTIVE` campaign with reason. |
| 12 | `GET /api/v1/policies/campaigns/{campaign_id}/records` | `policy:read` | **NEW (Batch 4)** | List per-user attestation records for a campaign (filterable by `status`). |
| 13 | `POST /api/v1/policies/campaigns/{campaign_id}/evaluate-overdue` | `policy:campaign_manage` | **NEW (Batch 4)** | Evaluate and mark past-due `PENDING` records (past `due_date + grace_period_days`) as `OVERDUE`. |
| 14 | `POST /api/v1/policies/campaigns/{campaign_id}/records/{record_id}/exempt` | `policy:approve` | **NEW (Batch 4)** | Exempt a user attestation record backed by an active `SecurityException` (Four-Eyes SoD enforced). |
| 15 | `POST /api/v1/policies/campaigns/{campaign_id}/attest` | `policy:attest` | **HARDENED** | Submit personal attestation (allows `PENDING` or `OVERDUE` records in `ACTIVE` campaign). |
| 16 | `POST /api/v1/policies/campaigns/{campaign_id}/evidence` | `policy:campaign_manage` | Existing | Generate tamper-evident campaign evidence manifest (`UPLOADED` `EvidenceItem`). |
| 17 | `GET /api/v1/policies/{policy_id}` | `policy:read` | Existing | Get policy details, versions, review workflows, and mapped controls. |
| 18 | `PATCH /api/v1/policies/{policy_id}` | `policy:manage` | Existing | Update policy metadata. |
| 19 | `POST /api/v1/policies/{policy_id}/status` | `policy:manage` | Existing | Transition policy lifecycle status. |
| 20 | `GET /api/v1/policies/{policy_id}/versions` | `policy:read` | Existing | List all versions for a policy. |
| 21 | `POST /api/v1/policies/{policy_id}/versions` | `policy:manage` | **HARDENED** | Create new incremented `DRAFT` version (blocked if policy is `ARCHIVED`). |
| 22 | `GET /api/v1/policies/{policy_id}/versions/{version_id}` | `policy:read` | Existing | Get single policy version details. |
| 23 | `PATCH /api/v1/policies/{policy_id}/versions/{version_id}` | `policy:manage` | Existing | Update `DRAFT` policy version content/summary. |
| 24 | `GET /api/v1/policies/{policy_id}/versions/{version_id}/reviews` | `policy:read` | **NEW (Batch 4)** | List review workflows for a specific policy version. |
| 25 | `POST /api/v1/policies/{policy_id}/versions/{version_id}/submit-review` | `policy:manage` | **HARDENED** | Submit `DRAFT` version for review (blocks duplicate `PENDING` workflow). |
| 26 | `POST /api/v1/policies/{policy_id}/versions/{version_id}/review/{workflow_id}` | `policy:approve` | **HARDENED** | Approve/reject/request-changes on `PENDING` workflow (enforces dual Four-Eyes SoD & replay guard). |
| 27 | `POST /api/v1/policies/{policy_id}/versions/{version_id}/publish` | `policy:manage` | **HARDENED** | Publish `APPROVED` version and supersede prior `PUBLISHED` versions. |
| 28 | `DELETE /api/v1/policies/{policy_id}/versions/{version_id}` | `policy:manage` | **HARDENED** | Delete `DRAFT` version (blocked if non-`DRAFT`, sole version, or referenced by any campaign). |
| 29 | `POST /api/v1/policies/{policy_id}/mappings` | `policy:manage` | Existing | Add `PolicyControlMapping` to `FrameworkSubcategory`. |
| 30 | `DELETE /api/v1/policies/{policy_id}/mappings/{subcategory_id}` | `policy:manage` | Existing | Remove `PolicyControlMapping`. |

---

## 26. REQUEST / RESPONSE SCHEMA SPECIFICATION

New and enhanced Pydantic v2 schemas in `backend/app/schemas/policy.py`:

1. **`PolicyCampaignCancelRequest`**:
   - `model_config = ConfigDict(extra="forbid")`
   - `reason: Optional[str] = Field(None, max_length=1000)`
2. **`PolicyAttestationExemptionCreate`**:
   - `model_config = ConfigDict(extra="forbid")`
   - `security_exception_id: int = Field(..., description="ID of active SecurityException linked to this policy")`
   - `exemption_reason: str = Field(..., min_length=5, max_length=2000)`
3. **`UserAttestationRecordResponse` (Extended Backward-Compatibly)**:
   - Existing fields preserved: `id`, `organization_id`, `campaign_id`, `policy_id`, `version_id`, `user_id`, `status`, `attested_at`, `ip_address`, `user_agent`, `acknowledgement_text`, `comprehension_passed`, `attestation_receipt_hash`, `evidence_item_id`, `created_at`, `policy_title`, `policy_version_number`, `campaign_title`, `due_date`.
   - Additive fields: `record_id: Optional[int] = None`, `campaign_code: Optional[str] = None`, `version_number: Optional[int] = None`, `policy_version_hash: Optional[str] = None`, `policy_content: Optional[str] = None`, `assessment_id: Optional[int] = None`, `exemption_exception_id: Optional[int] = None`, `exemption_reason: Optional[str] = None`, `exempted_by_id: Optional[int] = None`, `exempted_at: Optional[datetime] = None`, `user_email: Optional[str] = None`, `user_full_name: Optional[str] = None`.
4. **`PolicyAttestationCampaignResponse` (Extended Backward-Compatibly)**:
   - Additive field: `overdue_count: int = 0`.
5. **`PolicyTelemetryResponse`**:
   - `total_policies: int`
   - `published_policies: int`
   - `draft_policies: int`
   - `under_review_policies: int`
   - `archived_policies: int`
   - `policies_due_for_review_count: int`
   - `mapped_controls_count: int`
   - `unmapped_policies_count: int`
   - `total_campaigns: int`
   - `active_campaigns: int`
   - `completed_campaigns: int`
   - `total_targeted_attestations: int`
   - `total_completed_attestations: int`
   - `overall_attestation_completion_rate: float`
   - `overdue_attestations_count: int`
   - `exempted_attestations_count: int`
   - `active_policy_exceptions_count: int`

---

## 27. RBAC PERMISSION MATRIX

| Operation | Endpoint | Required Permission | Allowed Roles | Four-Eyes SoD |
|---|---|---|---|---|
| Read Policies / Versions / Reviews / Campaigns / Records / Telemetry | `GET /api/v1/policies/*` | `policy:read` | All 6 Roles | N/A |
| View My Pending Attestations | `GET /api/v1/policies/my-pending-attestations` | `policy:attest` | All 6 Roles | Scoped to `current_user.id` |
| Submit Personal Attestation | `POST /api/v1/policies/campaigns/{id}/attest` | `policy:attest` | All 6 Roles | Scoped to `current_user.id` |
| Create / Update Policy & Draft Versions | `POST/PATCH /api/v1/policies*` | `policy:manage` | `ADMIN`, `MANAGER`, `GRC_ANALYST` | N/A |
| Submit Version for Review | `POST .../submit-review` | `policy:manage` | `ADMIN`, `MANAGER`, `GRC_ANALYST` | Records `wf.created_by_id = current_user.id` |
| Review & Approve/Reject Version | `POST .../review/{workflow_id}` | `policy:approve` | `ADMIN`, `MANAGER` | `current_user.id != ver.created_by_id` AND `current_user.id != wf.created_by_id` |
| Publish Approved Version | `POST .../publish` | `policy:manage` | `ADMIN`, `MANAGER`, `GRC_ANALYST` | Requires `ver.status == APPROVED` |
| Create / Update / Launch Campaign / Evaluate Overdue / Generate Evidence | `POST/PATCH /api/v1/policies/campaigns*` | `policy:campaign_manage` | `ADMIN`, `MANAGER`, `GRC_ANALYST` | N/A |
| Close / Cancel Campaign | `POST .../close`, `POST .../cancel` | `policy:approve` | `ADMIN`, `MANAGER` | N/A |
| Exempt User Attestation Record | `POST .../records/{record_id}/exempt` | `policy:approve` | `ADMIN`, `MANAGER` | `current_user.id != record.user_id` |

---

## 28. MULTI-TENANT ISOLATION INVARIANTS

1. Every query on `Policy`, `PolicyVersion`, `PolicyReviewWorkflow`, `PolicyAttestationCampaign`, `UserAttestationRecord`, and `PolicyControlMapping` filters by `organization_id == current_user.organization_id`.
2. Cross-tenant resource lookups (`policy_id`, `version_id`, `workflow_id`, `campaign_id`, `record_id`) return `HTTP 404 Not Found` (preventing cross-tenant ID enumeration).
3. Cross-entity foreign keys supplied in request payloads (`owner_id`, `assigned_reviewer_id`, `assessment_id`, `security_exception_id`) are explicitly verified against `organization_id == current_user.organization_id` before persistence (`HTTP 400` on cross-tenant foreign key injection).

---

## 29. CONCURRENCY, RACE CONDITION & IDEMPOTENCY DESIGN

1. **Duplicate Attestation Prevention**:
   - Database constraint `UniqueConstraint("organization_id", "campaign_id", "user_id", name="uq_camp_user_attestation")` prevents duplicate `UserAttestationRecord` rows at campaign launch.
   - `submit_user_attestation` checks `if record.status in (AttestationRecordStatusEnum.ATTESTED, AttestationRecordStatusEnum.EXEMPTED)` and raises `HTTP 409 Conflict` (`Duplicate attestation`).
2. **Duplicate Pending Review Prevention**:
   - `submit_version_for_review` checks both `ver.status == DRAFT` and that no `PENDING` `PolicyReviewWorkflow` exists for `version_id`, preventing concurrent duplicate review workflows.
3. **Review Decision Replay Prevention**:
   - `review_policy_version_workflow` checks `wf.status == PENDING` and `ver.status == UNDER_REVIEW`, rejecting any replay with `HTTP 400`.
4. **Control Mapping Idempotency**:
   - `add_control_mapping` checks for an existing `(organization_id, policy_id, subcategory_id)` row and returns it idempotently (`uq_org_policy_subcategory`).

---

## 30. MIGRATION ARCHITECTURE

**Alembic Migration File**: `backend/alembic/versions/0025_policy_lifecycle_governance_hardening.py`  
- `revision = "0025"`  
- `down_revision = "0024"`  
- Uses `op.batch_alter_table` for full SQLite and PostgreSQL compatibility:
  1. `user_attestation_records`:
     - Add `exemption_exception_id` (`sa.Integer()`, `sa.ForeignKey("security_exceptions.id", ondelete="SET NULL")`, `nullable=True`)
     - Add `exemption_reason` (`sa.Text()`, `nullable=True`)
     - Add `exempted_by_id` (`sa.Integer()`, `sa.ForeignKey("users.id", ondelete="SET NULL")`, `nullable=True`)
     - Add `exempted_at` (`sa.DateTime(timezone=True)`, `nullable=True`)
     - Create index `ix_user_att_org_camp_status` on `["organization_id", "campaign_id", "status"]`
  2. `policy_attestation_campaigns`:
     - Add `overdue_count` (`sa.Integer()`, `server_default="0"`, `nullable=False`)
     - Create index `ix_pol_camp_org_pol_status` on `["organization_id", "policy_id", "status"]`
  3. `policy_review_workflows`:
     - Add `updated_at` (`sa.DateTime(timezone=True)`, `server_default=sa.func.now()`, `nullable=True`)
     - Create index `ix_pol_rev_wf_org_ver_status` on `["organization_id", "version_id", "status"]`

---

## 31. FRONTEND ARCHITECTURE & UX WORKFLOWS

1. **`frontend/src/pages/PoliciesPage.tsx`**:
   - Add **Policy Governance Telemetry Summary Cards** at the top of the page fetched from `GET /api/v1/policies/telemetry` (Published Policies, Policies Due for Review, Overall Attestation Rate, Overdue Attestations, Active Policy Exceptions).
   - In the Campaigns table, add:
     - **Inspect Roster** button opening a modal displaying `GET /api/v1/policies/campaigns/{campaign_id}/records` (user name/email, status badge `PENDING`/`ATTESTED`/`OVERDUE`/`EXEMPTED`, receipt hash, and an **Exempt** action for `ADMIN`/`MANAGER`).
     - **Evaluate Overdue** button (`POST /api/v1/policies/campaigns/{campaign_id}/evaluate-overdue`) and **Cancel Campaign** button (`POST /api/v1/policies/campaigns/{campaign_id}/cancel`).
2. **`frontend/src/pages/PolicyDetailPage.tsx`**:
   - Display version `effective_date` and block version delete button in UI when version status is not `DRAFT` or `total_versions <= 1`.
3. **`frontend/src/types/index.ts`**:
   - Add `PolicyTelemetry` interface and extend `UserAttestationRecord` with exemption fields (`exemption_exception_id`, `exemption_reason`, `exempted_by_id`, `exempted_at`, `user_email`, `user_full_name`).

---

## 32. ADVERSARIAL THREAT MODEL (MINIMUM 45 ATTACK VECTORS)

| # | Vector ID | Threat Category | Attack Description | Expected Defense & HTTP Status |
|---|---|---|---|---|
| 1 | `ADV-B4-01` | Tenant Isolation | Tenant B reads Tenant A policy (`GET /policies/{id}`) | `404 Not Found` |
| 2 | `ADV-B4-02` | Tenant Isolation | Tenant B updates Tenant A policy (`PATCH /policies/{id}`) | `404 Not Found` |
| 3 | `ADV-B4-03` | Tenant Isolation | Tenant B lists/reads Tenant A policy versions (`GET /policies/{id}/versions`) | `404 Not Found` |
| 4 | `ADV-B4-04` | Tenant Isolation | Tenant B reads Tenant A review workflows (`GET /policies/{id}/versions/{vid}/reviews`) | `404 Not Found` |
| 5 | `ADV-B4-05` | Tenant Isolation | Tenant B approves Tenant A review workflow (`POST .../review/{wf_id}`) | `404 Not Found` |
| 6 | `ADV-B4-06` | Tenant Isolation | Tenant B reads Tenant A campaign (`GET /policies/campaigns/{id}`) | `404 Not Found` |
| 7 | `ADV-B4-07` | Tenant Isolation | Tenant B reads Tenant A campaign roster (`GET /policies/campaigns/{id}/records`) | `404 Not Found` |
| 8 | `ADV-B4-08` | Tenant Isolation | Tenant B attests to Tenant A campaign (`POST /policies/campaigns/{id}/attest`) | `404 Not Found` |
| 9 | `ADV-B4-09` | Tenant Isolation | Tenant B cancels or closes Tenant A campaign | `404 Not Found` |
| 10 | `ADV-B4-10` | Tenant Isolation | Tenant B exempts record in Tenant A campaign | `404 Not Found` |
| 11 | `ADV-B4-11` | Cross-Tenant FK Injection | Create policy with `owner_id` belonging to Tenant B | `400 Bad Request` |
| 12 | `ADV-B4-12` | Cross-Tenant FK Injection | Submit version for review with `assigned_reviewer_id` belonging to Tenant B | `400 Bad Request` |
| 13 | `ADV-B4-13` | Cross-Tenant FK Injection | Create campaign with `assessment_id` belonging to Tenant B | `400 Bad Request` |
| 14 | `ADV-B4-14` | Cross-Tenant FK Injection | Exempt attestation record using `security_exception_id` belonging to Tenant B | `400 Bad Request` |
| 15 | `ADV-B4-15` | Four-Eyes SoD | Version author (`created_by_id`) attempts to approve own version | `400 Bad Request` (`Four-Eyes Violation`) |
| 16 | `ADV-B4-16` | Four-Eyes SoD | Review workflow submitter (`wf.created_by_id` != `ver.created_by_id`) attempts to approve own review submission | `400 Bad Request` (`Four-Eyes Violation`) |
| 17 | `ADV-B4-17` | Four-Eyes SoD | Assigned reviewer constraint: unassigned non-admin manager attempts to decide workflow assigned to another reviewer | `400 Bad Request` |
| 18 | `ADV-B4-18` | Four-Eyes SoD | Manager attempts to grant an attestation exemption to their own `UserAttestationRecord` | `400 Bad Request` (`Four-Eyes Violation`) |
| 19 | `ADV-B4-19` | Workflow Replay | Approver attempts to re-approve or reject an already `APPROVED` review workflow | `400 Bad Request` |
| 20 | `ADV-B4-20` | Workflow Replay | Approver attempts to approve an already `REJECTED` or `CHANGES_REQUESTED` review workflow | `400 Bad Request` |
| 21 | `ADV-B4-21` | Duplicate Review Queue | Submitter attempts to call `submit-review` on a version already in `UNDER_REVIEW` | `400 Bad Request` |
| 22 | `ADV-B4-22` | Version Immutability | Attempt to `PATCH` content of an `UNDER_REVIEW`, `APPROVED`, `PUBLISHED`, or `SUPERSEDED` version | `400 Bad Request` |
| 23 | `ADV-B4-23` | Version Deletion Guard | Attempt to `DELETE` an `APPROVED`, `PUBLISHED`, or `SUPERSEDED` policy version | `400 Bad Request` |
| 24 | `ADV-B4-24` | Version Deletion Guard | Attempt to `DELETE` a policy version bound to a `DRAFT` or `COMPLETED` campaign | `400 Bad Request` |
| 25 | `ADV-B4-25` | Version Deletion Guard | Attempt to `DELETE` the sole remaining version (`v1`) of a policy | `400 Bad Request` |
| 26 | `ADV-B4-26` | Unapproved Publish | Attempt to publish a `DRAFT`, `UNDER_REVIEW`, or `ARCHIVED` version | `400 Bad Request` |
| 27 | `ADV-B4-27` | Supersession Integrity | Publishing `v2` automatically transitions previously `PUBLISHED` `v1` to `SUPERSEDED` | Verified `v1.status == SUPERSEDED` |
| 28 | `ADV-B4-28` | Archived Policy Lock | Attempt to create a new version, map controls, or create a campaign on an `ARCHIVED` policy | `400 Bad Request` |
| 29 | `ADV-B4-29` | Campaign State Machine | Attempt to `close` a `DRAFT`, `COMPLETED`, or `CANCELLED` campaign | `400 Bad Request` |
| 30 | `ADV-B4-30` | Campaign State Machine | Attempt to `cancel` an already `COMPLETED` or `CANCELLED` campaign | `400 Bad Request` |
| 31 | `ADV-B4-31` | Campaign State Machine | Attempt to `launch` an already `ACTIVE`, `COMPLETED`, or `CANCELLED` campaign | `400 Bad Request` |
| 32 | `ADV-B4-32` | Campaign Audience Guard | Attempt to `launch` a `ROLE_BASED` campaign targeting a role with 0 active users in the org | `400 Bad Request` |
| 33 | `ADV-B4-33` | Invalid Target Role | Attempt to create a `ROLE_BASED` campaign with an invalid or missing `target_role` | `400 Bad Request` |
| 34 | `ADV-B4-34` | Cryptographic Hash Verification | Submit attestation with tampered or mismatched `policy_version_hash` | `400 Bad Request` |
| 35 | `ADV-B4-35` | Duplicate Attestation Replay | Submit second attestation for an already `ATTESTED` or `EXEMPTED` record | `409 Conflict` |
| 36 | `ADV-B4-36` | Unassigned User Attestation | User not in campaign roster attempts to submit attestation | `404 Not Found` |
| 37 | `ADV-B4-37` | Closed/Cancelled Campaign Attestation | Assigned user attempts to attest after campaign is `COMPLETED` or `CANCELLED` | `400 Bad Request` |
| 38 | `ADV-B4-38` | Assessment Gate Enforcement | User attempts to attest when linked `Assessment` is not `COMPLETED` + `EFFECTIVE` | `400 Bad Request` |
| 39 | `ADV-B4-39` | Exception Exemption Validation | Attempt to exempt user attestation with an expired, rejected, or unlinked `SecurityException` | `400 Bad Request` |
| 40 | `ADV-B4-40` | Overdue Deadline Sweep | `evaluate-overdue` transitions past-due `PENDING` records (respecting `grace_period_days`) to `OVERDUE` without affecting `ATTESTED` or `EXEMPTED` records | Verified `status == OVERDUE` & `overdue_count` |
| 41 | `ADV-B4-41` | Late Attestation Recovery | User with `OVERDUE` record attests while campaign is still `ACTIVE`; status transitions `OVERDUE -> ATTESTED` and `overdue_count` decrements | Verified `status == ATTESTED` |
| 42 | `ADV-B4-42` | Phase 3 Evidence Boundary | Generated campaign evidence manifest always enters `EvidenceStatusEnum.UPLOADED` and fails cleanly (`400`) if policy has no mapped `OrganizationControl` | Verified `status == UPLOADED` |
| 43 | `ADV-B4-43` | RBAC Enforcement | `GRC_ANALYST`, `SECURITY_ANALYST`, `AUDITOR`, and `VIEWER` are blocked (`403`) from approving reviews, closing/cancelling campaigns, or granting exemptions | `403 Forbidden` |
| 44 | `ADV-B4-44` | Mass Assignment / Extra Fields | Extra fields on new Batch 4 schemas (`PolicyAttestationExemptionCreate`, `PolicyCampaignCancelRequest`) are rejected with `422`, while legacy endpoints ignore injected `organization_id`/`user_id`/`status` | `422` / Server-authoritative override |
| 45 | `ADV-B4-45` | IDOR on `/my-pending-attestations` | Query parameter `?user_id=...` cannot leak another user's pending attestations; payload includes authoritative `policy_version_hash` and `policy_content` | `200 OK` (caller records only) |

---

## 33. TEST STRATEGY & REQUIRED COVERAGE MATRIX

1. **Preserve 100% of Existing Tests**:
   - `backend/tests/test_policies.py` (7 tests)
   - `backend/tests/test_phase24_api.py` (2 tests)
   - `backend/tests/test_phase24_adversarial_security.py` (38 tests)
2. **Add New Batch 4 Comprehensive Test Suite (`backend/tests/test_batch4_policy_lifecycle_governance.py`)**:
   - Minimum 25 new integration and adversarial tests covering:
     - Review workflow replay rejection (`PENDING -> APPROVED` replay blocked, `PENDING -> REJECTED` replay blocked)
     - Submitter Four-Eyes SoD (`wf.created_by_id == current_user_id` blocked on `APPROVE`)
     - Assigned reviewer enforcement (`wf.assigned_reviewer_id` check)
     - Version deletion immutability (`APPROVED`, `PUBLISHED`, `SUPERSEDED`, sole version, and `DRAFT`/`COMPLETED`-campaign linked versions blocked from deletion)
     - Cross-tenant `assessment_id` rejection on campaign creation and update
     - Invalid `target_role` rejection on `ROLE_BASED` campaign creation and 0-user launch rejection
     - Campaign close state guard (`DRAFT` / `CANCELLED` close blocked) and campaign cancellation (`DRAFT -> CANCELLED`, `ACTIVE -> CANCELLED`)
     - Campaign roster listing (`GET /api/v1/policies/campaigns/{id}/records`)
     - Overdue attestation evaluation (`evaluate-overdue` respecting `grace_period_days`, updating `overdue_count`, and late attestation transitioning `OVERDUE -> ATTESTED`)
     - Policy exception-backed workforce exemption (`POST .../records/{record_id}/exempt`), including Four-Eyes self-exemption block, wrong-policy exception block, expired/unapproved exception block, and automatic campaign completion when `ATTESTED + EXEMPTED == total_targeted_count`
     - Enriched `/api/v1/policies/my-pending-attestations` contract verification (`policy_version_hash`, `policy_content`, `campaign_code`, `version_number`, `record_id`)
     - Organization-wide `GET /api/v1/policies/telemetry` accuracy and tenant isolation.

---

## 34. EXPLICIT NON-GOALS & DEFERRED SCOPE

1. **No Parallel Quiz Engine**: Batch 4 will not create custom quiz question/answer tables; comprehension testing remains governed by Phase 4 `Assessment` (`assessment_id`).
2. **No Automatic Evidence Acceptance**: Batch 4 will never transition `EvidenceItem` directly to `ACCEPTED`; Phase 3 `EvidenceReview` retains sole authority over evidence acceptance.
3. **No External Email/SMTP Dispatcher**: Workforce attestation notifications remain in-app via `/api/v1/policies/my-pending-attestations` and `AuditLog`.
4. **No Destructive Schema Changes**: Existing Phase 2 and Phase 24 tables, columns, and route paths are preserved without breaking changes.

---

## 35. IMPLEMENTATION FILE MANIFEST

When Batch 4 proceeds to implementation (after the Hardening Gate), only the following files will be created or modified:

| File Path | Action | Purpose |
|---|---|---|
| `backend/alembic/versions/0025_policy_lifecycle_governance_hardening.py` | **CREATE** | Additive columns (`exemption_*`, `overdue_count`, `updated_at`) and composite indexes on policy tables. |
| `backend/app/models/policy.py` | **MODIFY** | Add `EXEMPTED` to `AttestationRecordStatusEnum`, additive columns on `UserAttestationRecord`, `PolicyAttestationCampaign`, and `PolicyReviewWorkflow`. |
| `backend/app/schemas/policy.py` | **MODIFY** | Add `PolicyCampaignCancelRequest`, `PolicyAttestationExemptionCreate`, `PolicyTelemetryResponse`, and enrich `UserAttestationRecordResponse` & `PolicyAttestationCampaignResponse`. |
| `backend/app/services/policy_service.py` | **MODIFY** | Harden review workflow state machine & SoD, version deletion immutability, campaign validation/cancel/close/overdue/roster/exemption logic, `/my-pending-attestations` payload, and `get_policy_telemetry`. |
| `backend/app/api/v1/endpoints/policies.py` | **MODIFY** | Add `/telemetry`, `/campaigns/{id}/cancel`, `/campaigns/{id}/records`, `/campaigns/{id}/evaluate-overdue`, `/campaigns/{id}/records/{rid}/exempt`, and `/{id}/versions/{vid}/reviews` endpoints with full `AuditService.log` coverage. |
| `frontend/src/types/index.ts` | **MODIFY** | Add `PolicyTelemetry` interface and exemption fields on `UserAttestationRecord`. |
| `frontend/src/pages/PoliciesPage.tsx` | **MODIFY** | Add Policy Governance Telemetry banner, Campaign Roster & Exemption modal, Cancel Campaign button, and Evaluate Overdue button. |
| `frontend/src/pages/PolicyDetailPage.tsx` | **MODIFY** | Surface version effective date and version deletion guard in UI. |
| `backend/tests/test_batch4_policy_lifecycle_governance.py` | **CREATE** | Comprehensive integration & adversarial security test suite for Batch 4. |

---

## 36. HARDENING GATE CHECKLIST & GO/NO-GO VERDICT

| Gate Criterion | Verification Status |
|---|---|
| Frozen baseline (`9c34411f5cc4f7f5b849e457d2304ea1e9fc00bd`, Alembic head `0024`) verified | **PASS** |
| Existing Phase 2 (`0002`) & Phase 24 (`0021`) policy tables, services, endpoints, and tests inventoried | **PASS** |
| Existing 47 policy tests (`test_policies.py`, `test_phase24_api.py`, `test_phase24_adversarial_security.py`) analyzed for zero-regression compatibility | **PASS** |
| Domain authority boundaries with Phase 2 Controls, Phase 3 Evidence, Phase 4 Assessments, and Phase 5 Security Exceptions defined | **PASS** |
| Four-Eyes SoD, review replay protection, version immutability, overdue calculation, and exception-backed exemption architecture specified | **PASS** |
| 45 adversarial attack vectors cataloged with explicit HTTP status expectations | **PASS** |
| Zero application code modified during discovery | **PASS** |

BATCH 4 ARCHITECTURE DISCOVERY COMPLETE — GO TO HARDENING.
