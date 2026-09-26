# PHASE 28 — BATCH 4 ARCHITECTURE HARDENED SPECIFICATION: ENTERPRISE POLICY LIFECYCLE & WORKFORCE ATTESTATION GOVERNANCE (`POLICY-LIFECYCLE-GRC`)

**Repository**: `E:\PROJECT WORKSPACE 2\ControlSphere` (`https://github.com/Avalar06/ControlSphere.git`)  
**Branch**: `main`  
**Frozen Baseline Commit**: `9c34411f5cc4f7f5b849e457d2304ea1e9fc00bd` (`feat(batch3): implement data governance and lineage`)  
**Parent Commit (Batch 2)**: `7b5c7954c33f6aca44b7a193ad91d1b384188456` (`feat(batch2): implement kri appetite governance`)  
**Current Alembic Head**: `0024` (`0024_data_governance_and_lineage.py`)  
**Target Migration**: `0025_policy_lifecycle_governance_hardening.py`  
**Task Classification**: Architecture Hardening & Validation Specification Only (Zero Application Code Changes)

---

## 1. Executive Summary

This document provides the hardened, repository-verified architecture specification for **Batch 4 — Enterprise Policy Lifecycle & Workforce Attestation Governance (`POLICY-LIFECYCLE-GRC`)**.

Independent verification of the repository confirms that historical Phase 2 (`0002_frameworks_controls_policies.py`) and Phase 24 (`0021_policy_lifecycle_and_attestation.py`, commit `8b8b482`) already established the authoritative 6-table relational model (`Policy`, `PolicyVersion`, `PolicyReviewWorkflow`, `PolicyAttestationCampaign`, `UserAttestationRecord`, `PolicyControlMapping`), service (`PolicyService` in `backend/app/services/policy_service.py`), router (`backend/app/api/v1/endpoints/policies.py`), RBAC permissions (`backend/app/core/permissions.py`), frontend pages (`PoliciesPage.tsx`, `PolicyDetailPage.tsx`, `DashboardPage.tsx`), and 47 existing tests (`test_policies.py`, `test_phase24_api.py`, `test_phase24_adversarial_security.py`).

Critical code-level inspection during hardening confirmed all discovery claims and uncovered **three additional concrete defects** in the existing Phase 24 code that were not fully detailed in the discovery summary:
1. **`PolicyResponse` and `PolicyVersionResponse` Schema Stripping Defect (`backend/app/schemas/policy.py` lines 32–50, 65–85, 226–236)**:
   - **REPOSITORY FACT**: `PolicyService.get_policy_by_id` (`policy_service.py` line 168) returns `"versions": pol.versions`, and `PolicyDetailPage.tsx` (lines 253, 261, 426, 551, 574) reads `policy.versions`, `currentDisplayVersion.reviews`, and `wf.created_by.full_name`. However, `PolicyResponse` omits `versions`, `PolicyVersionResponse` omits `reviews`, and `PolicyReviewWorkflowResponse` omits `created_by`. As a result, FastAPI strips version history and review audit trails from `GET /api/v1/policies/{policy_id}` responses!
2. **`REQUEST_CHANGES` vs `CHANGES_REQUESTED` Enum Mismatch (`PolicyDetailPage.tsx` line 60 vs `policy_service.py` line 502)**:
   - **REPOSITORY FACT**: `PolicyDetailPage.tsx` sends `decision: "REQUEST_CHANGES"`, whereas `PolicyService.review_policy_version_workflow` only accepts `"CHANGES_REQUESTED"`, causing UI review change-requests to fail with `HTTP 400`.
3. **Cross-Tenant `assigned_reviewer_id` Injection in `submit_version_for_review` (`policy_service.py` lines 401–438)**:
   - **REPOSITORY FACT**: `submit_version_for_review` stores `review_in.assigned_reviewer_id` directly on `PolicyReviewWorkflow` without verifying that the user exists, is active, and belongs to `organization_id`.
4. **Exemption Four-Eyes SoD Strengthening**:
   - **ARCHITECTURAL DECISION**: Checking only `record.user_id != current_user_id` is insufficient for Four-Eyes governance on attestation exemptions. When exempting a `UserAttestationRecord` via a Phase 5 `SecurityException`, `PolicyService.exempt_user_attestation` must enforce **all three** SoD invariants:
     1. `current_user_id != record.user_id` (approver cannot exempt their own attestation requirement),
     2. `current_user_id != exc.requested_by_id` (approver of the campaign exemption cannot be the requester of the `SecurityException`), and
     3. `exc.reviewer_id is not None and exc.reviewer_id != exc.requested_by_id` (the underlying `SecurityException` must have been approved under Phase 5 Four-Eyes).

All Batch 4 requirements can be safely, cleanly, and transactionally delivered in **one cohesive implementation batch** extending the existing Phase 24 architecture in place with zero duplicate engines and zero regressions against the 1,084 existing backend tests.

---

## 2. Baseline Verification

Executed directly against `E:\PROJECT WORKSPACE 2\ControlSphere`:

```text
$ git status
On branch main
Your branch is up to date with 'origin/main'.
Untracked files:
	PHASE28_BATCH4_ARCHITECTURE_DISCOVERY.md

$ git rev-parse HEAD
9c34411f5cc4f7f5b849e457d2304ea1e9fc00bd

$ git log -1 --oneline
9c34411 feat(batch3): implement data governance and lineage

$ git branch --show-current
main

$ git remote -v
origin	https://github.com/Avalar06/ControlSphere.git (fetch)
origin	https://github.com/Avalar06/ControlSphere.git (push)

$ python -m alembic -c backend/alembic.ini heads
0024 (head)
```

- **REPOSITORY FACT**: `HEAD` is `9c34411f5cc4f7f5b849e457d2304ea1e9fc00bd`, parent is `7b5c7954c33f6aca44b7a193ad91d1b384188456`, Alembic head is `0024`, and working tree is clean aside from architecture markdown artifacts.

---

## 3. Discovery Reconciliation

Every claim in `PHASE28_BATCH4_ARCHITECTURE_DISCOVERY.md` was audited against the actual codebase:

| Discovery Claim | Classification | Source Code Verification & Hardening Reconciliation |
|---|---|---|
| Historical Phase 24 (`0021`) created `PolicyReviewWorkflow`, `PolicyAttestationCampaign`, `UserAttestationRecord`, and enhanced `PolicyVersion`. | **REPOSITORY FACT** | Verified in `backend/alembic/versions/0021_policy_lifecycle_and_attestation.py` (lines 18–266) and `backend/app/models/policy.py` (lines 118–245). |
| `review_policy_version_workflow` lacks `wf.status == PENDING` and `ver.status == UNDER_REVIEW` guards. | **REPOSITORY FACT** | Verified in `backend/app/services/policy_service.py` (lines 441–518). Currently an `APPROVED` or `REJECTED` workflow can be re-reviewed. |
| `submit_version_for_review` validates `assigned_reviewer_id` belongs to `organization_id`. | **CORRECTION TO DISCOVERY** | **REPOSITORY FACT**: `submit_version_for_review` (`policy_service.py` lines 401–438) does **NOT** currently validate `assigned_reviewer_id`! Hardening adds explicit tenant + `is_active` validation on `assigned_reviewer_id` (`HTTP 400` if invalid/cross-tenant). |
| `delete_policy_version` only blocks deletion if bound to an `ACTIVE` campaign. | **REPOSITORY FACT** | Verified in `policy_service.py` (lines 563–588). Currently allows deleting `APPROVED`, `PUBLISHED`, `SUPERSEDED`, sole versions, or versions bound to `DRAFT`/`COMPLETED`/`CANCELLED` campaigns. |
| `create_campaign` does not validate `assessment_id` tenant ownership or `target_role` validity. | **REPOSITORY FACT** | Verified in `policy_service.py` (lines 637–689). |
| `close_campaign` does not verify `campaign.status == ACTIVE`. | **REPOSITORY FACT** | Verified in `policy_service.py` (lines 766–780). |
| `/my-pending-attestations` omits `policy_version_hash`, `policy_content`, `campaign_code`, `version_number`, and `record_id` expected by `DashboardPage.tsx`. | **REPOSITORY FACT** | Verified in `policy_service.py` (lines 785–826) vs `DashboardPage.tsx` (lines 161–164, 701–715) and `frontend/src/types/index.ts` (`PendingAttestationItem`, lines 286–300). |
| `PolicyResponse` and `PolicyVersionResponse` serialize `versions` and `reviews` for `PolicyDetailPage.tsx`. | **ADDITIONAL DEFECT FOUND** | **REPOSITORY FACT**: `PolicyResponse` (`schemas/policy.py` lines 226–236) omits `versions: Optional[List[PolicyVersionResponse]] = None`, `PolicyVersionResponse` (lines 32–50) omits `reviews: List[PolicyReviewWorkflowResponse] = []`, and `PolicyReviewWorkflowResponse` (lines 65–85) omits `created_by: Optional[UserResponse] = None`. Hardening adds these fields so `PolicyDetailPage.tsx` receives full version & review history. |
| `PolicyDetailPage.tsx` sends `decision: "REQUEST_CHANGES"` while `policy_service.py` checks `decision == "CHANGES_REQUESTED"`. | **ADDITIONAL DEFECT FOUND** | **REPOSITORY FACT**: Verified in `PolicyDetailPage.tsx` line 60 vs `policy_service.py` line 502. Hardening normalizes `"REQUEST_CHANGES"` -> `"CHANGES_REQUESTED"` in `review_policy_version_workflow`. |
| Exemption Four-Eyes requires `record.user_id != current_user_id`. | **HARDENED DECISION** | **ARCHITECTURAL DECISION**: `record.user_id != current_user_id` alone is insufficient. Hardening enforces `current_user_id != record.user_id` AND `current_user_id != exc.requested_by_id` AND `exc.reviewer_id != exc.requested_by_id`. |
| Standalone `Notification` table exists in repository. | **REPOSITORY FACT** | Verified via repository-wide search: **no** standalone `Notification` table/service exists. Workforce attestation inbox notifications are delivered via `UserAttestationRecord` (`GET /api/v1/policies/my-pending-attestations`) and `AuditService.log`. |

---

## 4. Current Policy Authority

- **Authoritative Models (`backend/app/models/policy.py`)**:
  - `Policy` (`policies`, lines 92–116)
  - `PolicyVersion` (`policy_versions`, lines 118–145)
  - `PolicyReviewWorkflow` (`policy_review_workflows`, lines 147–177)
  - `PolicyAttestationCampaign` (`policy_attestation_campaigns`, lines 179–214)
  - `UserAttestationRecord` (`user_attestation_records`, lines 216–245)
  - `PolicyControlMapping` (`policy_control_mappings`, lines 247–261)
- **Authoritative Service (`backend/app/services/policy_service.py`)**:
  - `PolicyService` (lines 43–1094)
- **Authoritative API Router (`backend/app/api/v1/endpoints/policies.py`)**:
  - Mounted at `/api/v1/policies` in `backend/app/api/v1/api.py` (line 41).

---

## 5. Historical Phase 24 Reconciliation

Every existing Phase 2 / Phase 24 component is classified below with direct source evidence:

| Component | Classification | Source Evidence & Rationale |
|---|---|---|
| `Policy` model & CRUD (`list_policies`, `create_policy`, `update_policy`, `update_policy_status`) | **B. Complete but requiring hardening** | `models/policy.py` lines 92–116; `policy_service.py` lines 60–282. Needs `get_policy_by_id` to eager-load `PolicyVersion.reviews` and `PolicyVersion.approved_by`, and `PolicyResponse` to include `versions`. |
| `PolicyVersion` model & hashing (`compute_canonical_hash`, `create_policy_version`, `update_policy_version`) | **B. Complete but requiring hardening** | `models/policy.py` lines 118–145; `policy_service.py` lines 45–56, 286–399. Hashing and `DRAFT`-only edit guard are complete; `delete_policy_version` (lines 563–588) requires immutability hardening. |
| `PolicyReviewWorkflow` (`submit_version_for_review`, `review_policy_version_workflow`) | **C. Partially complete and extendable** | `models/policy.py` lines 147–177; `policy_service.py` lines 401–519. Missing `assigned_reviewer_id` tenant check, duplicate `PENDING` workflow guard, `PENDING` replay guard, submitter Four-Eyes SoD, `"REQUEST_CHANGES"` alias support, and `GET .../reviews` endpoint. |
| `publish_policy_version` | **A. Complete and reusable** | `policy_service.py` lines 521–560. Enforces `ver.status == APPROVED`, supersedes old `PUBLISHED` versions, updates `pol.status = PUBLISHED` and `pol.effective_date`. |
| `PolicyAttestationCampaign` (`create_campaign`, `update_campaign`, `launch_campaign`, `close_campaign`) | **C. Partially complete and extendable** | `models/policy.py` lines 179–214; `policy_service.py` lines 592–781. Needs `assessment_id` tenant check, `target_role` enum check, 0-user launch prevention, `ACTIVE`-only close check, `cancel_campaign`, `list_campaign_records`, and `evaluate_campaign_overdue`. |
| `UserAttestationRecord` (`get_user_pending_attestations`, `submit_user_attestation`) | **C. Partially complete and extendable** | `models/policy.py` lines 216–245; `policy_service.py` lines 785–906. Needs `EXEMPTED` status, `exempt_user_attestation` linked to Phase 5 `SecurityException`, overdue recovery (`OVERDUE -> ATTESTED`), and enriched `/my-pending-attestations` fields. |
| `generate_campaign_evidence` | **A. Complete and reusable** | `policy_service.py` lines 911–1014. Deterministically builds key-sorted JSON manifest, computes SHA-256, resolves mapped `OrganizationControl`, creates `EvidenceItem` in `UPLOADED` status. |
| `PolicyControlMapping` (`add_control_mapping`, `remove_control_mapping`) | **A. Complete and reusable** | `models/policy.py` lines 247–261; `policy_service.py` lines 1019–1094. Enforces tenant isolation, archival lock, and idempotent uniqueness. |

---

## 6. Authority Matrix

| Entity | Authoritative Table | Authoritative Service | Authoritative API | Lifecycle States | Cryptographic Authority | Mathematical Authority | Owning Module | Batch 4 May Extend? | Batch 4 Must Not Duplicate? |
|---|---|---|---|---|---|---|---|---|---|
| `Policy` | `policies` | `PolicyService` | `/api/v1/policies` | `DRAFT`, `UNDER_REVIEW`, `APPROVED`, `PUBLISHED`, `ARCHIVED` | N/A | Version counter | `POLICY-LIFECYCLE-GRC` | **YES** | **MUST NOT DUPLICATE** |
| `PolicyVersion` | `policy_versions` | `PolicyService` | `/api/v1/policies/{id}/versions` | `DRAFT`, `UNDER_REVIEW`, `APPROVED`, `PUBLISHED`, `SUPERSEDED`, `ARCHIVED` | `content_hash_sha256` (SHA-256 digest) | Sequential `version_number` | `POLICY-LIFECYCLE-GRC` | **YES** | **MUST NOT DUPLICATE** |
| `PolicyReviewWorkflow` | `policy_review_workflows` | `PolicyService` | `/api/v1/policies/{id}/versions/{vid}/review*` | `PENDING`, `APPROVED`, `REJECTED`, `CHANGES_REQUESTED` | N/A | Four-Eyes SoD | `POLICY-LIFECYCLE-GRC` | **YES** | **MUST NOT DUPLICATE** |
| `PolicyControlMapping` | `policy_control_mappings` | `PolicyService` | `/api/v1/policies/{id}/mappings` | Active / Deleted | N/A | Control linkage count | `POLICY-LIFECYCLE-GRC` | **YES** | **MUST NOT DUPLICATE** |
| `Assessment` | `assessments` | `AssessmentService` | `/api/v1/assessments` | `DRAFT`, `IN_PROGRESS`, `COMPLETED`, `SUPERSEDED` | N/A | `conclusion == EFFECTIVE` | Phase 4 Assessments | **NO (Read-only)** | **MUST NOT DUPLICATE** |
| `EvidenceItem` | `evidence_items` | `EvidenceService` / `PolicyService.generate_campaign_evidence` | `/api/v1/evidence` | `UPLOADED`, `UNDER_REVIEW`, `ACCEPTED`, `REJECTED`, `SUPERSEDED` | `sha256_hash` of stored file bytes | File byte length & checksum | Phase 3 Evidence | **Create in `UPLOADED` only** | **MUST NOT DUPLICATE** |
| `EvidenceReview` | `evidence_reviews` | `EvidenceService` | `/api/v1/evidence/{id}/reviews` | `ACCEPT`, `REJECT` | N/A | Reviewer decision | Phase 3 Evidence | **NO** | **MUST NOT DUPLICATE** |
| `PolicyAttestationCampaign` | `policy_attestation_campaigns` | `PolicyService` | `/api/v1/policies/campaigns` | `DRAFT`, `ACTIVE`, `COMPLETED`, `CANCELLED` | `policy_version_hash` snapshot | `total_targeted_count`, `completed_count`, `overdue_count`, `completion_rate` | `POLICY-LIFECYCLE-GRC` | **YES** | **MUST NOT DUPLICATE** |
| `UserAttestationRecord` | `user_attestation_records` | `PolicyService` | `/api/v1/policies/campaigns/{id}/attest`, `/records` | `PENDING`, `OVERDUE`, `ATTESTED`, `EXEMPTED` | `attestation_receipt_hash` (SHA-256 receipt digest) | Per-user completion & overdue state | `POLICY-LIFECYCLE-GRC` | **YES** | **MUST NOT DUPLICATE** |
| `Notification` (In-App Inbox) | `user_attestation_records` + `audit_logs` | `PolicyService` + `AuditService` | `/api/v1/policies/my-pending-attestations` | Derived from `PENDING` / `OVERDUE` in `ACTIVE` campaigns | N/A | Pending count | `POLICY-LIFECYCLE-GRC` | **YES (via `/my-pending-attestations`)** | **MUST NOT CREATE `notifications` TABLE** |
| `SecurityException` | `security_exceptions` | `ExceptionService` | `/api/v1/exceptions` | `REQUESTED`, `UNDER_REVIEW`, `APPROVED`, `ACTIVE`, `EXPIRED`, `REJECTED`, `CLOSED` | N/A | `calculate_exception_effective_status` | Phase 5 Exceptions | **NO (Read-only validation & FK link)** | **MUST NOT DUPLICATE** |
| `ExecutiveSnapshot` | `executive_snapshots` | `ExecutiveService` | `/api/v1/executive/snapshots` | Immutable upon creation | `data_hash_sha256` | 10-domain weighted posture | Phase 20 Executive | **NO** | **MUST NOT DUPLICATE** |
| `ContinuousAssuranceSnapshot` | `continuous_assurance_snapshots` | `ContinuousComplianceService` | `/api/v1/continuous-compliance/snapshots` | Immutable upon creation | `data_hash_sha256` | 6-pillar weighted assurance | Phase 23 Continuous | **NO** | **MUST NOT DUPLICATE** |
| `AuditLog` | `audit_logs` | `AuditService` | `/api/v1/audit-logs` | Immutable append-only | N/A | Monotonic event ledger | Phase 1 Audit | **Append via `AuditService.log`** | **MUST NOT DUPLICATE** |

---

## 7. Policy Version State Machine

### 7.1 States (`PolicyVersionStatusEnum` in `backend/app/models/policy.py`)
- `DRAFT`: Initial state when authored (`create_policy`, `create_policy_version`) or returned for revision (`CHANGES_REQUESTED`). Mutable via `PATCH /api/v1/policies/{policy_id}/versions/{version_id}`.
- `UNDER_REVIEW`: Locked state entered via `submit_version_for_review`. Content and hash are frozen.
- `APPROVED`: Entered via `review_policy_version_workflow` with `decision == "APPROVE"`. Records `approved_by_id` and `approved_at`. Immutable.
- `PUBLISHED`: Entered via `publish_policy_version` from `APPROVED`. Becomes the active organizational policy version; any previously `PUBLISHED` version for the same `policy_id` transitions atomically to `SUPERSEDED`. Immutable.
- `SUPERSEDED`: Entered automatically when a newer `APPROVED` version of the same policy is published. Immutable.
- `ARCHIVED`: Entered when a version under review is rejected (`decision == "REJECT"`). Immutable. *(Note: No separate `RETIRED` state is invented because `SUPERSEDED` and `ARCHIVED` already exist in `PolicyVersionStatusEnum`).*

### 7.2 Hardened Modification: `delete_policy_version`
- **CURRENT**: `PolicyService.delete_policy_version` (`policy_service.py` lines 563–588) only checks whether an `ACTIVE` campaign references `version.id`. It allows deleting `UNDER_REVIEW`, `APPROVED`, `PUBLISHED`, `SUPERSEDED`, or `ARCHIVED` versions, sole versions of a policy, or versions referenced by `DRAFT`, `COMPLETED`, or `CANCELLED` campaigns.
- **CHANGE**:
  1. Block deletion if `version.status != PolicyVersionStatusEnum.DRAFT` (`raise ValueError(f"Cannot delete policy version in '{version.status.value}' status. Only unsubmitted DRAFT versions may be deleted.")` -> `HTTP 400`).
  2. Block deletion if `any_campaign` (in `DRAFT`, `ACTIVE`, `COMPLETED`, or `CANCELLED` status) references `version.id` (`raise ValueError(...)` -> `HTTP 400`).
  3. Block deletion if `any_attestation_record` references `version.id` (`raise ValueError(...)` -> `HTTP 400`).
  4. Block deletion if `any_review_workflow` with status in `{APPROVED, REJECTED}` exists on `version.id` (`raise ValueError(...)` -> `HTTP 400`).
  5. Block deletion if the policy has only 1 version (`version_count <= 1`: `raise ValueError("Cannot delete the sole version of a policy.")` -> `HTTP 400`).
- **REASON**: Prevents destruction of approved/published governance history, campaign bindings (`RESTRICT` FK protection), and audit lineage.
- **AUTHORITY**: `PolicyService.delete_policy_version`.
- **SECURITY IMPACT**: Eliminates post-approval history erasure (`ADV-B4-23`, `ADV-B4-24`, `ADV-B4-25`).
- **MIGRATION IMPACT**: None.
- **TEST REQUIREMENT**: Test deleting `APPROVED`, `PUBLISHED`, `SUPERSEDED`, sole `v1`, and `DRAFT`/`COMPLETED`-campaign-bound versions (`HTTP 400`), while verifying an unreferenced `DRAFT` `v2` can still be deleted (`HTTP 204`).

---

## 8. Review Workflow State Machine

### 8.1 States (`PolicyReviewStatusEnum` in `backend/app/models/policy.py`)
- `PENDING`: Initial state created by `submit_version_for_review`.
- `APPROVED` (Terminal): Version transitions `UNDER_REVIEW -> APPROVED`; policy transitions to `APPROVED`.
- `REJECTED` (Terminal): Version transitions `UNDER_REVIEW -> ARCHIVED`.
- `CHANGES_REQUESTED` (Terminal for this workflow instance): Version transitions `UNDER_REVIEW -> DRAFT`, allowing the author to edit the draft and submit a new review workflow when ready.

### 8.2 Hardened Modifications: `submit_version_for_review` & `review_policy_version_workflow`
- **CURRENT**:
  - `submit_version_for_review` (`policy_service.py` lines 401–438) does not validate `assigned_reviewer_id` against `organization_id` and does not check for an existing `PENDING` workflow on `version_id`.
  - `review_policy_version_workflow` (`policy_service.py` lines 441–519) does not check `workflow.status == PolicyReviewStatusEnum.PENDING` or `version.status == PolicyVersionStatusEnum.UNDER_REVIEW`, does not check `workflow.created_by_id == current_user_id`, does not check `workflow.assigned_reviewer_id`, and rejects `"REQUEST_CHANGES"`.
- **CHANGE**:
  1. In `submit_version_for_review`:
     - If `review_in.assigned_reviewer_id is not None`, query `User` where `User.id == review_in.assigned_reviewer_id`, `User.organization_id == organization_id`, `User.is_active.is_(True)`. If not found, raise `ValueError("Assigned reviewer not found or inactive in your organization")` (`HTTP 400`).
     - Verify no existing `PolicyReviewWorkflow` with `version_id == version.id` and `status == PolicyReviewStatusEnum.PENDING` exists; if found, raise `ValueError("A pending review workflow already exists for this policy version")` (`HTTP 400`).
     - Ensure `version.content_hash_sha256 = PolicyService.compute_canonical_hash(version.content)` is frozen upon submission.
  2. In `review_policy_version_workflow`:
     - Verify `workflow.status == PolicyReviewStatusEnum.PENDING`. If not, raise `ValueError(f"Review workflow is already finalized in '{workflow.status.value}' status and cannot be replayed or modified.")` (`HTTP 400`).
     - Verify `version.status == PolicyVersionStatusEnum.UNDER_REVIEW`. If not, raise `ValueError(f"Policy version is in '{version.status.value}' status and is not open for review.")` (`HTTP 400`).
     - Normalize `decision = action_in.decision.strip().upper()`; map `"REQUEST_CHANGES"` -> `"CHANGES_REQUESTED"`.
     - If `workflow.assigned_reviewer_id is not None` and `workflow.assigned_reviewer_id != current_user_id`: check if caller is `RoleEnum.ADMIN`; if not, raise `ValueError("Only the assigned reviewer or an organization administrator may record a decision on this review workflow.")` (`HTTP 400`).
     - On `APPROVE`: enforce `version.created_by_id != current_user_id` AND `workflow.created_by_id != current_user_id` (`Four-Eyes Violation` -> `HTTP 400`).
     - Set `workflow.updated_at = now`.
  3. Add `PolicyService.list_version_reviews(db, policy_id, version_id, organization_id)` and `GET /api/v1/policies/{policy_id}/versions/{version_id}/reviews`.
- **REASON**: Eliminates workflow replay, cross-tenant reviewer injection, and self-approval by review submitter.
- **AUTHORITY**: `PolicyService`.
- **SECURITY IMPACT**: Blocks `ADV-B4-12`, `ADV-B4-15`, `ADV-B4-16`, `ADV-B4-17`, `ADV-B4-19`, `ADV-B4-20`, `ADV-B4-21`.
- **MIGRATION IMPACT**: Adds `updated_at` and `ix_pol_rev_wf_org_ver_status` on `policy_review_workflows` in `0025`.
- **TEST REQUIREMENT**: Test replay on `APPROVED`/`REJECTED`/`CHANGES_REQUESTED` workflows (`HTTP 400`), submitter self-approval (`HTTP 400`), wrong assigned reviewer (`HTTP 400`), cross-tenant `assigned_reviewer_id` (`HTTP 400`), `"REQUEST_CHANGES"` alias (`HTTP 200`), and `GET .../reviews` (`HTTP 200`).

---

## 9. Four-Eyes / Segregation of Duties (SoD)

 Batch 4 enforces server-side Four-Eyes SoD across all governance approval boundaries:

1. **Policy Version Approval (`review_policy_version_workflow`)**:
   - Requires `Permission.POLICY_APPROVE` (`ADMIN` or `MANAGER`).
   - `current_user.id != version.created_by_id` (author cannot approve own version).
   - `current_user.id != workflow.created_by_id` (submitter cannot approve own review request).
2. **Workforce Attestation Exemption (`exempt_user_attestation`)**:
   - Requires `Permission.POLICY_APPROVE` (`ADMIN` or `MANAGER`).
   - Requires a valid, same-tenant `SecurityException` (`exc.linked_policy_id == campaign.policy_id`, `exc.status in (APPROVED, ACTIVE)`, `exc.expiry_date >= today`).
   - **Triple Four-Eyes Check**:
     - `current_user.id != record.user_id` (cannot exempt oneself from attesting),
     - `current_user.id != exc.requested_by_id` (the requester of the `SecurityException` cannot approve the campaign attestation exemption), AND
     - `exc.reviewer_id is not None and exc.reviewer_id != exc.requested_by_id` (the underlying `SecurityException` must itself carry a valid Four-Eyes approval).

---

## 10. Attestation Authority

- **REPOSITORY FACT**: `submit_user_attestation` (`policy_service.py` lines 829–906) derives `organization_id = current_user.organization_id` and `current_user_id = current_user.id` strictly from the JWT-authenticated `User` dependency (`get_current_user`).
- **Identity Binding Invariants**:
  - Client payload (`UserAttestationSubmit`) contains only `policy_version_hash` and `acknowledgement_text`.
  - Any extra fields injected by a malicious client (`user_id`, `organization_id`, `campaign_id`, `attested_at`, `status`, `attestation_receipt_hash`) are ignored by Pydantic and never read by `PolicyService.submit_user_attestation` (verified by `test_adv_p24_04`, `05`, `07`, `22`).
  - Database constraint `UniqueConstraint("organization_id", "campaign_id", "user_id", name="uq_camp_user_attestation")` guarantees at the storage engine level that a user can never have more than one `UserAttestationRecord` per campaign.
  - Once `record.status` is `ATTESTED` or `EXEMPTED`, it is **terminal and non-revocable**. Subsequent calls to `/attest` raise `ValueError("Duplicate attestation...")` -> `HTTP 409 Conflict`.
  - If `record.status == AttestationRecordStatusEnum.OVERDUE` and `campaign.status == CampaignStatusEnum.ACTIVE`, calling `/attest` transitions `OVERDUE -> ATTESTED`, decrements `campaign.overdue_count`, increments `campaign.completed_count`, and records the actual server UTC `attested_at` timestamp.

---

## 11. Cryptographic Receipt Model

- **Terminology Precision**:
  - Both `PolicyVersion.content_hash_sha256` and `UserAttestationRecord.attestation_receipt_hash` are **deterministic SHA-256 cryptographic digests (tamper-evident hashes)**, **NOT** asymmetric digital signatures or keyed HMACs.
- **Canonical Content Digest (`PolicyService.compute_canonical_hash`)**:
  ```python
  lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
  normalized = "\n".join(line.rstrip() for line in lines)
  return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
  ```
- **Canonical Attestation Receipt Digest (`PolicyService.submit_user_attestation`, lines 885–889)**:
  ```python
  canonical_str = (
      f"{organization_id}|{current_user_id}|{campaign.id}|{campaign.version_id}|"
      f"{campaign.policy_version_hash}|{now_iso}|{client_ip or 'unknown'}"
  )
  receipt_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
  ```
  - `organization_id`, `current_user_id`, `campaign.id`, `campaign.version_id`, `campaign.policy_version_hash`, and `now_iso` (`datetime.now(timezone.utc).isoformat()`) are 100% server-authoritative.
  - `client_ip` and `client_ua` are captured as non-repudiation audit metadata (`record.ip_address`, `record.user_agent`) and are never used as authentication identity.

---

## 12. Comprehension / Assessment Authority

- **REPOSITORY FACT**: `PolicyAttestationCampaign.assessment_id` (`ForeignKey("assessments.id", ondelete="SET NULL")`) links a campaign to the authoritative Phase 4 `Assessment` model (`backend/app/models/assessment.py`).
- **Hardened Rules**:
  1. **No Parallel Quiz Engine**: Batch 4 does not create any `PolicyQuiz` or `Assessment2` table.
  2. **Tenant Validation on Link**: In `PolicyService.create_campaign` and `PolicyService.update_campaign`, whenever `assessment_id is not None`, `PolicyService` queries `Assessment` filtering by `Assessment.id == assessment_id` and `Assessment.organization_id == organization_id`. If not found, raises `ValueError("Linked comprehension assessment not found in your organization")` (`HTTP 400`).
  3. **Comprehension Gating**:
     - When `campaign.assessment_id is None`: `UserAttestationRecord.comprehension_passed` defaults to `True`.
     - When `campaign.assessment_id is not None`: `UserAttestationRecord.comprehension_passed` initializes to `False` at campaign launch (`test_adv_p24_38`), and `submit_user_attestation` blocks attestation (`HTTP 400`) unless `assessment.status == AssessmentStatusEnum.COMPLETED` and `assessment.conclusion == AssessmentConclusionEnum.EFFECTIVE` (`test_adv_p24_32`, `test_adv_p24_37`).

---

## 13. Evidence Authority

- **REPOSITORY FACT**: Phase 3 `EvidenceItem` and `EvidenceReview` (`backend/app/models/evidence.py`, `backend/app/services/evidence_service.py`) are the sole authoritative evidence engine.
- **Lineage Chain**:
  `Policy` -> `PolicyVersion` (`content_hash_sha256`) -> `PolicyAttestationCampaign` (`policy_version_hash`) -> `UserAttestationRecord` (`attestation_receipt_hash`) -> `PolicyService.generate_campaign_evidence` -> `EvidenceItem` (`sha256_hash`, `organization_control_id` resolved via `PolicyControlMapping`, `status = EvidenceStatusEnum.UPLOADED`) -> Phase 3 `EvidenceReview` (`ACCEPT` / `REJECT`).
- **Strict Boundary Invariant**: `generate_campaign_evidence` **always** creates `EvidenceItem` with `status = EvidenceStatusEnum.UPLOADED` (`policy_service.py` line 1002) and includes both `ATTESTED` receipts and `EXEMPTED` exception references in the deterministic JSON manifest. It **never** bypasses `EvidenceReview`.

---

## 14. Campaign State Machine

### 14.1 Authoritative States (`CampaignStatusEnum` in `backend/app/models/policy.py`)
- `DRAFT`: Campaign created, bound to immutable `(policy_id, version_id, policy_version_hash)`. Metadata (`title`, `description`, `due_date`, `grace_period_days`, `assessment_id`) is editable.
- `ACTIVE`: Entered via `launch_campaign`. Target population is snapshotted into `user_attestation_records`. Metadata and bindings are frozen.
- `COMPLETED` (Terminal): Entered automatically when `completed_count >= total_targeted_count` (with `total_targeted_count > 0`) or explicitly via `close_campaign` (`Permission.POLICY_APPROVE`).
- `CANCELLED` (Terminal): Entered explicitly via `cancel_campaign` (`Permission.POLICY_APPROVE`) from `DRAFT` or `ACTIVE`.

*(Note: No `SCHEDULED`, `PAUSED`, or `EXPIRED` database enum states are added to `CampaignStatusEnum` because `DRAFT`, `ACTIVE`, `COMPLETED`, and `CANCELLED` are the exact 4 states in `backend/app/models/policy.py` lines 59–63).*

### 14.2 Hardened Campaign Transitions
- **`create_campaign`**:
  - Reject if `pol.status == PolicyStatusEnum.ARCHIVED` or `version.status in (PolicyVersionStatusEnum.ARCHIVED, PolicyVersionStatusEnum.SUPERSEDED)` (`HTTP 400`).
  - If `target_type == CampaignTargetTypeEnum.ROLE_BASED`: verify `target_role` is non-empty and in `{r.value for r in RoleEnum}` (`HTTP 400` if invalid).
  - If `assessment_id is not None`: verify `Assessment` belongs to `organization_id` (`HTTP 400` if not found).
- **`launch_campaign`**:
  - Require `campaign.status == CampaignStatusEnum.DRAFT` (`HTTP 400` otherwise).
  - Resolve active users in `organization_id` matching `target_type` / `target_role`. If `len(target_users) == 0`, raise `ValueError("Cannot launch campaign: target audience resolved to 0 active users in your organization.")` (`HTTP 400`).
- **`close_campaign`**:
  - Require `campaign.status == CampaignStatusEnum.ACTIVE` (`raise ValueError(f"Cannot close campaign in status '{campaign.status.value}'. Only ACTIVE campaigns can be closed.")` -> `HTTP 400`).
- **`cancel_campaign` (NEW)**:
  - Require `campaign.status in (CampaignStatusEnum.DRAFT, CampaignStatusEnum.ACTIVE)` (`raise ValueError(...)` -> `HTTP 400`).
  - Set `campaign.status = CampaignStatusEnum.CANCELLED` and `campaign.closed_at = datetime.now(timezone.utc)`.

---

## 15. Campaign Target Snapshot & User / Role Change Semantics

- **REPOSITORY FACT**: `PolicyService.launch_campaign` (`policy_service.py` lines 732–760) materializes one `UserAttestationRecord` row per targeted user at the moment of activation and sets `campaign.total_targeted_count = len(records)`.
- **Authoritative Snapshot Semantics**:
  1. **User joins organization after activation**: Not added to already-launched campaign; `total_targeted_count` and existing `user_attestation_records` remain frozen.
  2. **User changes role after activation**: Existing `UserAttestationRecord` remains in the campaign roster; denominator does not shrink or expand mid-campaign.
  3. **User becomes inactive (`is_active = False`) after activation**: Their `UserAttestationRecord` remains in the snapshot so the denominator (`total_targeted_count`) cannot be manipulated by deactivating non-compliant users. If the user is on leave or terminated, a manager/admin can either close the campaign or grant a governed `EXEMPTED` status backed by a `SecurityException`.

---

## 16. Campaign Telemetry & Overdue Evaluation

### 16.1 Authoritative Formulas
For any campaign $C$:
- $\text{total\_targeted\_count} = \text{COUNT}(\text{UserAttestationRecord where campaign\_id} = C.\text{id})$
- $\text{attested\_count} = \text{COUNT}(\text{status} == \text{ATTESTED})$
- $\text{exempted\_count} = \text{COUNT}(\text{status} == \text{EXEMPTED})$
- $\text{completed\_count} = \text{attested\_count} + \text{exempted\_count}$
- $\text{overdue\_count} = \text{COUNT}(\text{status} == \text{OVERDUE})$
- $\text{completion\_rate} = \begin{cases} \min\left(100.0, \text{round}\left(\frac{\text{completed\_count}}{\text{total\_targeted\_count}} \times 100.0, 2\right)\right) & \text{if } \text{total\_targeted\_count} > 0 \\ 0.0 & \text{otherwise} \end{cases}$

### 16.2 Overdue Evaluation (`evaluate_campaign_overdue`)
- **Deadline Formula**:
  $$\text{effective\_deadline} = C.\text{due\_date} + \text{timedelta}(\text{days}=C.\text{grace\_period\_days})$$
- When `now_utc > effective_deadline` and $C.\text{status} == \text{ACTIVE}$:
  - All `UserAttestationRecord` rows for $C$ with `status == AttestationRecordStatusEnum.PENDING` transition deterministically to `AttestationRecordStatusEnum.OVERDUE`.
  - Records in `ATTESTED` or `EXEMPTED` status are untouched.
  - `C.overdue_count` is synchronized with the exact database count of `OVERDUE` rows for $C$.
- **Idempotency**: Running `POST /api/v1/policies/campaigns/{campaign_id}/evaluate-overdue` repeatedly when no additional records have crossed the deadline is a strict idempotent no-op returning the same `overdue_count`.
- **Automatic Reconciliation**: `reconcile_campaign_counters(db, campaign)` recalculates `total_targeted_count`, `completed_count`, and `overdue_count` directly from `UserAttestationRecord` aggregate queries within the transaction so denormalized counters never drift under concurrent requests.

---

## 17. User / Role Change Semantics

See Section 15: Campaign target population is snapshotted into `user_attestation_records` at `launch_campaign` time. Role changes, new hires, or user deactivations after `launched_at` do not silently alter `total_targeted_count` or retroactively delete `UserAttestationRecord` rows.

---

## 18. SecurityException Integration & Exemption Four-Eyes

### 18.1 Phase 5 `SecurityException` Authority (`backend/app/models/exception.py`, `backend/app/services/exception_service.py`)
- **REPOSITORY FACT**: `SecurityException` (`security_exceptions` table) already contains:
  - `linked_policy_id = Column(Integer, ForeignKey("policies.id", ondelete="SET NULL"), nullable=True, index=True)` (`models/exception.py` line 71)
  - `exception_type` (`ExceptionTypeEnum.POLICY_EXCEPTION`)
  - `status` (`ExceptionStatusEnum`: `REQUESTED`, `UNDER_REVIEW`, `APPROVED`, `ACTIVE`, `EXPIRED`, `REJECTED`, `CLOSED`)
  - `requested_by_id`, `owner_id`, `reviewer_id`, `effective_date`, `expiry_date`.
- **REPOSITORY FACT**: `ExceptionService.approve_exception` (`exception_service.py` lines 444–446) enforces Phase 5 Four-Eyes: `if reviewer_id and exc.requested_by_id and reviewer_id == exc.requested_by_id: raise ValueError("Self-approval prohibited...")`.

### 18.2 Hardened Batch 4 Attestation Exemption Flow (`PolicyService.exempt_user_attestation`)
- **Endpoint**: `POST /api/v1/policies/campaigns/{campaign_id}/records/{record_id}/exempt`
- **Required Permission**: `Permission.POLICY_APPROVE` (`ADMIN` or `MANAGER`).
- **Authoritative Validation Steps**:
  1. Fetch `campaign` in `organization_id`; verify `campaign.status == CampaignStatusEnum.ACTIVE` (`HTTP 400` if not `ACTIVE`).
  2. Fetch `record` (`UserAttestationRecord`) where `id == record_id`, `campaign_id == campaign_id`, `organization_id == organization_id` (`HTTP 404` if not found).
  3. Verify `record.status in (AttestationRecordStatusEnum.PENDING, AttestationRecordStatusEnum.OVERDUE)`. If already `ATTESTED` or `EXEMPTED`, raise `HTTP 409 Conflict` (`Record is already finalized in status '...'`).
  4. Fetch `exc` (`SecurityException`) where `id == exemption_in.security_exception_id` and `organization_id == organization_id` (`HTTP 400` if not found in organization).
  5. Verify `exc.linked_policy_id == campaign.policy_id` (`HTTP 400` if exception is not linked to the campaign's policy).
  6. Verify `exc` is currently active and non-expired using `calculate_exception_effective_status(exc.status.value, exc.expiry_date, exc.effective_date, date.today()) == "ACTIVE"` (or `exc.status in (ExceptionStatusEnum.APPROVED, ExceptionStatusEnum.ACTIVE)` and `exc.expiry_date >= date.today()`) (`HTTP 400` if unapproved, rejected, closed, or expired).
  7. **Triple Four-Eyes SoD Verification**:
     - `if record.user_id == current_user_id`: raise `ValueError("Four-Eyes Violation: You cannot exempt your own attestation record.")` (`HTTP 400`).
     - `if exc.requested_by_id is not None and exc.requested_by_id == current_user_id`: raise `ValueError("Four-Eyes Violation: The requester of the security exception cannot approve an attestation exemption using that exception.")` (`HTTP 400`).
     - `if exc.reviewer_id is not None and exc.requested_by_id is not None and exc.reviewer_id == exc.requested_by_id`: raise `ValueError("Four-Eyes Violation: Underlying security exception violates Four-Eyes approval rules.")` (`HTTP 400`).
  8. Transition `record`:
     - `record.status = AttestationRecordStatusEnum.EXEMPTED`
     - `record.exemption_exception_id = exc.id`
     - `record.exemption_reason = exemption_in.exemption_reason.strip()`
     - `record.exempted_by_id = current_user_id`
     - `record.exempted_at = datetime.now(timezone.utc)`
  9. Reconcile campaign counters (`completed_count`, `overdue_count`); if `completed_count >= total_targeted_count` and `total_targeted_count > 0`, transition `campaign.status = CampaignStatusEnum.COMPLETED` and `campaign.closed_at = now`.

---

## 19. Executive Integration (Phase 20)

- **REPOSITORY FACT**: `ExecutiveService.calculate_live_telemetry` (`backend/app/services/executive_service.py` lines 142–591) computes a 10-domain weighted posture score (`sum(weights) == 1.00`) and `audit_readiness_index` from `EvidenceItem` (`evidence_items`).
- **ARCHITECTURAL DECISION**:
  - Do **not** alter `ExecutiveSnapshot` schema or the 10-domain weights in `ExecutiveService`, preserving 100% compatibility with `test_executive_domain.py`, `test_executive_api.py`, and `test_phase20_adversarial_security.py`.
  - Campaign evidence manifests generated via `PolicyService.generate_campaign_evidence` already populate `evidence_items` and flow into `ExecutiveService` audit readiness once reviewed/accepted via Phase 3 `EvidenceReview`.
  - Organization-wide policy lifecycle and workforce attestation metrics are exposed via the dedicated `GET /api/v1/policies/telemetry` endpoint (`PolicyService.get_policy_telemetry`).

---

## 20. Continuous Assurance Integration (Phase 23)

- **REPOSITORY FACT**: `ContinuousComplianceService.calculate_unified_assurance` (`backend/app/services/continuous_compliance_service.py` lines 134–273) computes 6 fixed assurance pillars (`controls_assurance`, `evidence_pipeline`, `regulatory_compliance`, `remediation_sla`, `cloud_identity_posture`, `harmonized_frameworks`).
- **ARCHITECTURAL DECISION**:
  - Pillar 2 (`evidence_pipeline`, lines 154–173) automatically consumes `EvidenceItem` rows created by `PolicyService.generate_campaign_evidence`.
  - Do **not** invent a 7th pillar or alter the 6-pillar weights in `ContinuousComplianceService`, preserving 100% compatibility with `test_phase23_adversarial_security.py`.

---

## 21. Notification Integration

- **REPOSITORY FACT**: Verified via repository-wide search that ControlSphere has **no** standalone `Notification` model or service.
- **Authoritative Pattern**:
  - Workforce attestation notifications are served via `GET /api/v1/policies/my-pending-attestations` (`PolicyService.get_user_pending_attestations`), which queries `UserAttestationRecord` rows in `PENDING` or `OVERDUE` status for `ACTIVE` campaigns in `current_user.organization_id`.
  - Because this query reads directly from `UserAttestationRecord` (which is constrained by `uq_camp_user_attestation`), it is strictly idempotent and can never emit duplicate pending notifications.

---

## 22. RBAC Matrix

No new roles or permissions are created; the existing 6 roles and 5 policy permissions in `backend/app/core/permissions.py` (lines 48–52, 182–523) are authoritative:

| Endpoint / Action | Required Permission | `ADMIN` | `MANAGER` | `GRC_ANALYST` | `SECURITY_ANALYST` | `AUDITOR` | `VIEWER` |
|---|---|---:|---:|---:|---:|---:|---:|
| `GET /api/v1/policies*` (Policies, Versions, Reviews, Campaigns, Records, Telemetry) | `policy:read` | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW |
| `GET /api/v1/policies/my-pending-attestations` | `policy:attest` | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW |
| `POST /api/v1/policies/campaigns/{id}/attest` | `policy:attest` | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW |
| `POST / PATCH /api/v1/policies` & `/status` & `/mappings` | `policy:manage` | ALLOW | ALLOW | ALLOW | DENY (403) | DENY (403) | DENY (403) |
| `POST / PATCH / DELETE /api/v1/policies/{id}/versions*` & `/submit-review` & `/publish` | `policy:manage` | ALLOW | ALLOW | ALLOW | DENY (403) | DENY (403) | DENY (403) |
| `POST /api/v1/policies/{id}/versions/{vid}/review/{wf_id}` | `policy:approve` | ALLOW* | ALLOW* | DENY (403) | DENY (403) | DENY (403) | DENY (403) |
| `POST / PATCH /api/v1/policies/campaigns` & `/launch` & `/evaluate-overdue` & `/evidence` | `policy:campaign_manage` | ALLOW | ALLOW | ALLOW | DENY (403) | DENY (403) | DENY (403) |
| `POST /api/v1/policies/campaigns/{id}/close` & `/cancel` | `policy:approve` | ALLOW | ALLOW | DENY (403) | DENY (403) | DENY (403) | DENY (403) |
| `POST /api/v1/policies/campaigns/{id}/records/{rid}/exempt` | `policy:approve` | ALLOW* | ALLOW* | DENY (403) | DENY (403) | DENY (403) | DENY (403) |

*\*Subject to strict server-side Four-Eyes SoD checks (`HTTP 400` on violation).*

---

## 23. Tenant Isolation & 24. BOLA / IDOR Defenses

| Parameter / Foreign Key | Defense Mechanism | Failure Status |
|---|---|---|
| `policy_id` (Path) | Queried with `Policy.id == policy_id` AND `Policy.organization_id == current_user.organization_id`. | `404 Not Found` |
| `version_id` (Path) | Queried with `PolicyVersion.id == version_id`, `PolicyVersion.policy_id == policy_id`, AND `Policy.organization_id == current_user.organization_id`. | `404 Not Found` |
| `workflow_id` (Path) | Queried with `PolicyReviewWorkflow.id == workflow_id`, `PolicyReviewWorkflow.version_id == version_id`, AND `PolicyReviewWorkflow.organization_id == current_user.organization_id`. | `404 Not Found` |
| `campaign_id` (Path) | Queried with `PolicyAttestationCampaign.id == campaign_id` AND `PolicyAttestationCampaign.organization_id == current_user.organization_id`. | `404 Not Found` |
| `record_id` (Path) | Queried with `UserAttestationRecord.id == record_id`, `UserAttestationRecord.campaign_id == campaign_id`, AND `UserAttestationRecord.organization_id == current_user.organization_id`. | `404 Not Found` |
| `owner_id` (Body) | Validated via `UserService.get_by_id(db, user_id=owner_id, organization_id=current_user.organization_id)`. | `400 Bad Request` |
| `assigned_reviewer_id` (Body) | Validated via `User` query filtering `id == assigned_reviewer_id`, `organization_id == organization_id`, `is_active == True`. | `400 Bad Request` |
| `assessment_id` (Body) | Validated via `Assessment` query filtering `id == assessment_id`, `organization_id == organization_id`. | `400 Bad Request` |
| `security_exception_id` (Body) | Validated via `SecurityException` query filtering `id == security_exception_id`, `organization_id == organization_id`, `linked_policy_id == campaign.policy_id`. | `400 Bad Request` |

---

## 25. Immutability Invariants

| Record Type | Immutable Condition | Protected Fields | Enforcement |
|---|---|---|---|
| `Policy` | `status == ARCHIVED` | All metadata, versions, mappings, campaigns | `HTTP 400` on update, version create, mapping add/remove, campaign create |
| `PolicyVersion` | `status != DRAFT` | `content`, `change_summary`, `effective_date`, `content_hash_sha256`, row deletion | `HTTP 400` on `PATCH` or `DELETE` |
| `PolicyReviewWorkflow` | `status != PENDING` | `status`, `review_notes`, `reviewed_by_id`, `approved_by_id`, `reviewed_at`, `approved_at` | `HTTP 400` on `POST .../review/{workflow_id}` |
| `PolicyAttestationCampaign` | `status != DRAFT` | `title`, `description`, `due_date`, `grace_period_days`, `assessment_id`, `policy_id`, `version_id`, `policy_version_hash` | `HTTP 400` on `PATCH` or `POST .../launch` |
| `PolicyAttestationCampaign` | `status in (COMPLETED, CANCELLED)` | Campaign status,attestation submissions, exemptions | `HTTP 400` on `/close`, `/cancel`, `/attest`, `/exempt` |
| `UserAttestationRecord` | `status in (ATTESTED, EXEMPTED)` | All record fields, receipt hash, timestamp, exemption link | `HTTP 409 Conflict` on `/attest` or `/exempt` |

---

## 26. Concurrency / Idempotency

1. **Database Unique Constraints**:
   - `uq_policy_version_number`: `("policy_id", "version_number")` on `policy_versions`
   - `uq_pol_rev_wf_code`: `("organization_id", "workflow_code")` on `policy_review_workflows`
   - `uq_pol_att_camp_code`: `("organization_id", "campaign_code")` on `policy_attestation_campaigns`
   - `uq_camp_user_attestation`: `("organization_id", "campaign_id", "user_id")` on `user_attestation_records`
   - `uq_org_policy_control_mapping`: `("organization_id", "policy_id", "subcategory_id")` on `policy_control_mappings`
2. **Counter Reconciliation (`reconcile_campaign_counters`)**:
   - Whenever an attestation is submitted (`submit_user_attestation`), an exemption is granted (`exempt_user_attestation`), or overdue evaluation runs (`evaluate_campaign_overdue`), `completed_count` and `overdue_count` are recomputed from `db.query(func.count(UserAttestationRecord.id))` rather than relying solely on `+= 1` in-memory increments, preventing lost updates or >100% completion rates.

---

## 27. Migration Strategy

**File**: `backend/alembic/versions/0025_policy_lifecycle_governance_hardening.py`  
**Revision**: `"0025"`  
**Down Revision**: `"0024"`

### Exact Upgrade Operations:
1. `with op.batch_alter_table("user_attestation_records") as batch_op:`
   - `batch_op.add_column(sa.Column("exemption_exception_id", sa.Integer(), sa.ForeignKey("security_exceptions.id", ondelete="SET NULL"), nullable=True))`
   - `batch_op.add_column(sa.Column("exemption_reason", sa.Text(), nullable=True))`
   - `batch_op.add_column(sa.Column("exempted_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))`
   - `batch_op.add_column(sa.Column("exempted_at", sa.DateTime(timezone=True), nullable=True))`
   - `batch_op.create_index("ix_user_att_org_camp_status", ["organization_id", "campaign_id", "status"])`
2. `with op.batch_alter_table("policy_attestation_campaigns") as batch_op:`
   - `batch_op.add_column(sa.Column("overdue_count", sa.Integer(), server_default="0", nullable=False))`
   - `batch_op.create_index("ix_pol_camp_org_pol_status", ["organization_id", "policy_id", "status"])`
3. `with op.batch_alter_table("policy_review_workflows") as batch_op:`
   - `batch_op.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True))`
   - `batch_op.create_index("ix_pol_rev_wf_org_ver_status", ["organization_id", "version_id", "status"])`

### Exact Downgrade Operations:
- Drops the 3 composite indexes and the 6 additive columns using `op.batch_alter_table`.
- 100% non-destructive, compatible with both PostgreSQL and SQLite test databases.

---

## 28. API Boundary & Modification Specifications

### Detailed Modification Matrix (`CURRENT` / `CHANGE` / `REASON` / `AUTHORITY` / `SECURITY IMPACT` / `MIGRATION IMPACT` / `TEST REQUIREMENT`)

#### Modification 1: `GET /api/v1/policies/telemetry`
- **CURRENT**: Does not exist.
- **CHANGE**: Add `GET /api/v1/policies/telemetry` (`Permission.POLICY_READ`, response model `PolicyTelemetryResponse`) calling `PolicyService.get_policy_telemetry(db, current_user.organization_id)`.
- **REASON**: Provides server-authoritative organization-wide policy lifecycle, review cadence, campaign progress, overdue, and exception metrics.
- **AUTHORITY**: `PolicyService.get_policy_telemetry`.
- **SECURITY IMPACT**: Tenant-scoped (`organization_id == current_user.organization_id`); eliminates client-side metric fabrication.
- **MIGRATION IMPACT**: Uses `overdue_count` and `status` indexes from `0025`.
- **TEST REQUIREMENT**: Verify exact telemetry counts and cross-tenant isolation.

#### Modification 2: `GET /api/v1/policies/my-pending-attestations`
- **CURRENT**: Returns `PENDING` records without `record_id`, `campaign_code`, `version_number`, `policy_version_hash`, `policy_content`, or `assessment_id`, and excludes `OVERDUE` records in `ACTIVE` campaigns.
- **CHANGE**: Filter `UserAttestationRecord.status.in_([PENDING, OVERDUE])` joined with `PolicyAttestationCampaign.status == ACTIVE`, and include `record_id`, `campaign_code`, `version_number`, `policy_version_hash`, `policy_content`, and `assessment_id` in both `PolicyService.get_user_pending_attestations` and `UserAttestationRecordResponse`.
- **REASON**: Aligns backend response with `DashboardPage.tsx` (`PendingAttestationItem`) and allows overdue users in active campaigns to complete their attestation.
- **AUTHORITY**: `PolicyService.get_user_pending_attestations`.
- **SECURITY IMPACT**: Preserves caller-scoped IDOR protection (`user_id == current_user.id`) while providing the authoritative `policy_version_hash` needed for cryptographic verification.
- **MIGRATION IMPACT**: None.
- **TEST REQUIREMENT**: Verify response contains `policy_version_hash`, `policy_content`, `campaign_code`, `version_number`, and `record_id`.

#### Modification 3: `POST /api/v1/policies/campaigns/{campaign_id}/cancel`
- **CURRENT**: Does not exist (`CampaignStatusEnum.CANCELLED` exists in model but has no endpoint).
- **CHANGE**: Add `POST /api/v1/policies/campaigns/{campaign_id}/cancel` (`Permission.POLICY_APPROVE`, request schema `PolicyCampaignCancelRequest`), transitioning `DRAFT` or `ACTIVE` campaigns to `CANCELLED` and logging `policy.campaign.cancel`.
- **REASON**: Enables governed cancellation of erroneous or superseded campaigns.
- **AUTHORITY**: `PolicyService.cancel_campaign`.
- **SECURITY IMPACT**: Restricted to `ADMIN`/`MANAGER`; blocks attestation on cancelled campaigns (`HTTP 400`).
- **MIGRATION IMPACT**: None.
- **TEST REQUIREMENT**: Test `DRAFT -> CANCELLED`, `ACTIVE -> CANCELLED`, `COMPLETED -> CANCELLED` (`400`), RBAC (`403` for analyst/viewer), and post-cancel attestation block (`400`).

#### Modification 4: `GET /api/v1/policies/campaigns/{campaign_id}/records`
- **CURRENT**: Does not exist.
- **CHANGE**: Add `GET /api/v1/policies/campaigns/{campaign_id}/records` (`Permission.POLICY_READ`, optional `?status=` filter) returning `List[UserAttestationRecordResponse]` with user details, receipt hashes, and exemption metadata.
- **REASON**: Enables campaign managers and auditors to inspect the frozen target population roster and individual attestation receipts/exemptions.
- **AUTHORITY**: `PolicyService.list_campaign_records`.
- **SECURITY IMPACT**: Tenant-isolated (`404` on cross-tenant `campaign_id`).
- **MIGRATION IMPACT**: Uses `ix_user_att_org_camp_status` from `0025`.
- **TEST REQUIREMENT**: Test roster listing, status filtering, and cross-tenant `404`.

#### Modification 5: `POST /api/v1/policies/campaigns/{campaign_id}/evaluate-overdue`
- **CURRENT**: Does not exist (`AttestationRecordStatusEnum.OVERDUE` is never set).
- **CHANGE**: Add `POST /api/v1/policies/campaigns/{campaign_id}/evaluate-overdue` (`Permission.POLICY_CAMPAIGN_MANAGE`) calling `PolicyService.evaluate_campaign_overdue`, transitioning `PENDING` records past `due_date + timedelta(days=grace_period_days)` to `OVERDUE` and updating `campaign.overdue_count`.
- **REASON**: Activates the `OVERDUE` record state and `overdue_count` telemetry deterministically using server UTC time.
- **AUTHORITY**: `PolicyService.evaluate_campaign_overdue`.
- **SECURITY IMPACT**: Server UTC time authority; idempotent on repeated execution.
- **MIGRATION IMPACT**: Updates `policy_attestation_campaigns.overdue_count` added in `0025`.
- **TEST REQUIREMENT**: Test past-due transition to `OVERDUE`, grace period protection, idempotency, and late attestation recovery (`OVERDUE -> ATTESTED`).

#### Modification 6: `POST /api/v1/policies/campaigns/{campaign_id}/records/{record_id}/exempt`
- **CURRENT**: Does not exist.
- **CHANGE**: Add `POST /api/v1/policies/campaigns/{campaign_id}/records/{record_id}/exempt` (`Permission.POLICY_APPROVE`, request schema `PolicyAttestationExemptionCreate`) calling `PolicyService.exempt_user_attestation`.
- **REASON**: Connects Phase 5 `SecurityException` (`POLICY_EXCEPTION`) to workforce attestation records with strict Four-Eyes SoD.
- **AUTHORITY**: `PolicyService.exempt_user_attestation` + Phase 5 `SecurityException`.
- **SECURITY IMPACT**: Enforces triple Four-Eyes SoD (`current_user.id != record.user_id`, `current_user.id != exc.requested_by_id`, `exc.reviewer_id != exc.requested_by_id`), same-policy binding, and active non-expired exception status.
- **MIGRATION IMPACT**: Populates `exemption_exception_id`, `exemption_reason`, `exempted_by_id`, `exempted_at` on `user_attestation_records` from `0025`.
- **TEST REQUIREMENT**: Test valid exemption, self-exemption block (`400`), exception-requester self-approval block (`400`), unapproved/expired/wrong-policy exception block (`400`), cross-tenant exception block (`400`), and duplicate exemption block (`409`).

#### Modification 7: `GET /api/v1/policies/{policy_id}/versions/{version_id}/reviews`
- **CURRENT**: Does not exist as a standalone endpoint, and `PolicyVersionResponse` omitted `reviews`.
- **CHANGE**: Add `GET /api/v1/policies/{policy_id}/versions/{version_id}/reviews` (`Permission.POLICY_READ`, response `List[PolicyReviewWorkflowResponse]`) AND add `reviews: List[PolicyReviewWorkflowResponse] = []` to `PolicyVersionResponse` and `versions: List[PolicyVersionResponse] = []` to `PolicyResponse`.
- **REASON**: Provides direct review workflow inspection and fixes `PolicyDetailPage.tsx` version/review rendering.
- **AUTHORITY**: `PolicyService.list_version_reviews`.
- **SECURITY IMPACT**: Tenant-isolated (`404` on cross-tenant policy/version).
- **MIGRATION IMPACT**: Uses `ix_pol_rev_wf_org_ver_status` from `0025`.
- **TEST REQUIREMENT**: Test listing version reviews and verify `GET /api/v1/policies/{id}` includes `versions` and `reviews`.

---

## 29. Frontend Architecture

1. **`frontend/src/types/index.ts`**:
   - Add `PolicyTelemetry` interface matching `PolicyTelemetryResponse`.
   - Extend `UserAttestationRecord` with `exemption_exception_id?: number`, `exemption_reason?: string`, `exempted_by_id?: number`, `exempted_at?: string`, `user_email?: string`, `user_full_name?: string`.
2. **`frontend/src/pages/PoliciesPage.tsx`**:
   - Fetch `GET /api/v1/policies/telemetry` and display a 5-card **Policy Governance Telemetry** bar (Published Policies, Due for Review, Attestation Completion Rate, Overdue Attestations, Active Policy Exceptions).
   - In the Campaigns tab, add:
     - **Roster** button (`GET /api/v1/policies/campaigns/{id}/records`) opening a Campaign Roster & Exemption modal showing each targeted user's status (`PENDING`, `ATTESTED`, `OVERDUE`, `EXEMPTED`), receipt hash, and an **Exempt** form (`security_exception_id`, `exemption_reason`) for `policy:approve` users.
     - **Sweep Overdue** button (`POST /api/v1/policies/campaigns/{id}/evaluate-overdue`) on `ACTIVE` campaigns.
     - **Cancel** button (`POST /api/v1/policies/campaigns/{id}/cancel`) on `DRAFT` and `ACTIVE` campaigns for `policy:approve` users.
3. **`frontend/src/pages/PolicyDetailPage.tsx`**:
   - With `PolicyResponse.versions` and `PolicyVersionResponse.reviews` now serialized by the backend and `"REQUEST_CHANGES"` accepted by `review_policy_version_workflow`, the existing version selector, side-by-side diff viewer, Four-Eyes review modal, and Review Audit Trail card work seamlessly.
4. **`frontend/src/pages/DashboardPage.tsx`**:
   - No code changes required in `DashboardPage.tsx`; enriching `GET /api/v1/policies/my-pending-attestations` with `policy_version_hash`, `policy_content`, `campaign_code`, `version_number`, and `record_id` resolves the contract mismatch directly at the authoritative backend layer.

---

## 30. Audit Logging

All mutations emit structured events via `AuditService.log` (`backend/app/services/audit_service.py`) into `audit_logs`:

| Event Action | Resource Type | Non-Repudiation Details Captured |
|---|---|---|
| `policy.create` | `POLICY` | `title`, `type`, `ip_address`, `user_agent` |
| `policy.update` | `POLICY` | `updated_fields`, `ip_address`, `user_agent` |
| `policy.approve` / `publish` / `archive` / `submit_review` / `draft` | `POLICY` | `new_status`, `reason`, `ip_address`, `user_agent` |
| `policy.version.create` | `POLICY_VERSION` | `policy_id`, `version_number`, `content_hash`, `ip_address`, `user_agent` |
| `policy.version.update` | `POLICY_VERSION` | `version_number`, `content_hash`, `ip_address`, `user_agent` |
| `policy.version.delete` | `POLICY_VERSION` | `policy_id`, `version_id`, `ip_address`, `user_agent` |
| `policy.version.submit_review` | `POLICY_REVIEW_WORKFLOW` | `version_id`, `workflow_code`, `stage`, `assigned_reviewer_id`, `ip_address`, `user_agent` |
| `policy.version.approve` / `reject` / `changes_requested` | `POLICY_REVIEW_WORKFLOW` | `version_id`, `decision`, `approved_by_id`, `ip_address`, `user_agent` |
| `policy.version.publish` | `POLICY_VERSION` | `policy_id`, `version_number`, `content_hash`, `ip_address`, `user_agent` |
| `policy.campaign.create` | `POLICY_CAMPAIGN` | `campaign_code`, `policy_id`, `version_id`, `ip_address`, `user_agent` |
| `policy.campaign.update` | `POLICY_CAMPAIGN` | `updated_fields`, `ip_address`, `user_agent` |
| `policy.campaign.launch` | `POLICY_CAMPAIGN` | `campaign_code`, `total_targeted`, `ip_address`, `user_agent` |
| `policy.campaign.close` | `POLICY_CAMPAIGN` | `campaign_code`, `completed_count`, `ip_address`, `user_agent` |
| `policy.campaign.cancel` **(NEW)** | `POLICY_CAMPAIGN` | `campaign_code`, `reason`, `ip_address`, `user_agent` |
| `policy.campaign.evaluate_overdue` **(NEW)** | `POLICY_CAMPAIGN` | `campaign_code`, `overdue_count`, `ip_address`, `user_agent` |
| `policy.attestation.submit` | `USER_ATTESTATION` | `campaign_id`, `receipt_hash`, `ip_address`, `user_agent` |
| `policy.attestation.exempt` **(NEW)** | `USER_ATTESTATION` | `campaign_id`, `record_id`, `user_id`, `security_exception_id`, `ip_address`, `user_agent` |
| `policy.evidence.generate` | `EVIDENCE_ITEM` | `campaign_id`, `manifest_sha256`, `ip_address`, `user_agent` |
| `policy.mapping.create` / `delete` | `POLICY_MAPPING` | `policy_id`, `subcategory_id`, `ip_address`, `user_agent` |

---

## 31. Anti-Duplication Gate

| System / Engine | Authoritative Location | Batch 4 Duplication Check |
|---|---|---|
| Policy & PolicyVersion | `backend/app/models/policy.py` | **PASS** — Extended in place; no `Policy2` or `PolicyVersion2`. |
| PolicyReviewWorkflow | `backend/app/models/policy.py` | **PASS** — Extended in place; no `Review2`. |
| Assessment / Comprehension | `backend/app/models/assessment.py` | **PASS** — Reused via `assessment_id` FK; no `PolicyQuiz` or `Assessment2`. |
| Evidence & EvidenceReview | `backend/app/models/evidence.py` | **PASS** — Creates `EvidenceItem` in `UPLOADED` status; no `Evidence2` or review bypass. |
| Notification Inbox | `UserAttestationRecord` + `/my-pending-attestations` | **PASS** — Reused in place; no `notifications` table invented. |
| SecurityException | `backend/app/models/exception.py` | **PASS** — Linked via `exemption_exception_id` FK; no `PolicyException2` table. |
| Executive Metrics | `backend/app/services/executive_service.py` | **PASS** — Unmodified; policy telemetry exposed at `/api/v1/policies/telemetry`. |
| Continuous Assurance | `backend/app/services/continuous_compliance_service.py` | **PASS** — Unmodified; consumes `EvidenceItem` automatically. |
| AuditLog | `backend/app/services/audit_service.py` | **PASS** — Reuses `AuditService.log`. |
| RBAC Roles | `backend/app/core/permissions.py` | **PASS** — Uses exact 6 roles and 5 existing policy permissions. |

---

## 32. Security Threat Model & 33. Adversarial Test Matrix (50 Attack Vectors)

All 38 existing tests in `backend/tests/test_phase24_adversarial_security.py` are preserved, and 50 total vectors (including 45+ in the new `backend/tests/test_batch4_policy_lifecycle_governance.py` + existing suite) are enforced:

| Vector ID | Attack Description | Server-Side Defense | Expected HTTP Status | Test Location |
|---|---|---|---|---|
| `VEC-01` | Cross-tenant read policy / versions (`Org B -> Org A`) | `organization_id` filter on `Policy` | `404 Not Found` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-02` | Cross-tenant read version review workflows (`Org B -> Org A`) | `organization_id` filter on `PolicyService.list_version_reviews` | `404 Not Found` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-03` | Cross-tenant approve/reject review workflow (`Org B -> Org A`) | `organization_id` filter on `review_policy_version_workflow` | `404 Not Found` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-04` | Cross-tenant read campaign or campaign records (`Org B -> Org A`) | `organization_id` filter on `get_campaign` / `list_campaign_records` | `404 Not Found` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-05` | Cross-tenant cancel, close, or evaluate-overdue on campaign (`Org B -> Org A`) | `organization_id` filter on campaign mutations | `404 Not Found` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-06` | Cross-tenant exempt attestation record (`Org B -> Org A`) | `organization_id` filter on `exempt_user_attestation` | `404 Not Found` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-07` | Cross-tenant `owner_id` injection on policy create/update | `UserService.get_by_id` scoped to `organization_id` | `400 Bad Request` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-08` | Cross-tenant `assigned_reviewer_id` injection on `submit-review` | `User` lookup scoped to `organization_id` and `is_active` | `400 Bad Request` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-09` | Cross-tenant `assessment_id` injection on campaign create/update | `Assessment` lookup scoped to `organization_id` | `400 Bad Request` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-10` | Cross-tenant `security_exception_id` injection on record exemption | `SecurityException` lookup scoped to `organization_id` | `400 Bad Request` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-11` | Spoofed `organization_id` in policy or campaign create body | Ignored; server binds `current_user.organization_id` | `201 Created` (bound to caller org) | `test_phase24_adversarial_security.py` (`05, 35`) |
| `VEC-12` | Spoofed `user_id` in `/attest` body (User A attempting to attest for User B) | Ignored; server binds `current_user.id` | `200 OK` (bound to caller user) | `test_phase24_adversarial_security.py` (`04`) |
| `VEC-13` | Admin attempting to attest on behalf of an employee when Admin is not in role-targeted campaign | `UserAttestationRecord` lookup for `current_user.id` fails | `404 Not Found` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-14` | IDOR query param `?user_id=...` on `/my-pending-attestations` | Server ignores query param and filters `user_id == current_user.id` | `200 OK` (caller rows only) | `test_phase24_adversarial_security.py` (`30`) |
| `VEC-15` | Four-Eyes violation: Version creator (`ver.created_by_id`) attempts to approve own version | `version.created_by_id == current_user_id` check | `400 Bad Request` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-16` | Four-Eyes violation: Review submitter (`wf.created_by_id` != author) attempts to approve own submission | `workflow.created_by_id == current_user_id` check | `400 Bad Request` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-17` | Assigned reviewer bypass: Non-admin manager attempts to decide workflow assigned to another reviewer | `workflow.assigned_reviewer_id != current_user_id` check | `400 Bad Request` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-18` | Review decision replay: Approver attempts to re-approve or reject an already `APPROVED` workflow | `workflow.status != PENDING` check | `400 Bad Request` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-19` | Review decision replay: Approver attempts to approve an already `REJECTED` or `CHANGES_REQUESTED` workflow | `workflow.status != PENDING` check | `400 Bad Request` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-20` | Duplicate `submit-review` call on a version already in `UNDER_REVIEW` | `version.status == DRAFT` & no `PENDING` workflow check | `400 Bad Request` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-21` | Mutating content of `UNDER_REVIEW`, `APPROVED`, `PUBLISHED`, or `SUPERSEDED` version via `PATCH` | `version.status != DRAFT` check | `400 Bad Request` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-22` | Deleting an `UNDER_REVIEW`, `APPROVED`, `PUBLISHED`, or `SUPERSEDED` version via `DELETE` | `version.status != DRAFT` check in `delete_policy_version` | `400 Bad Request` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-23` | Deleting a `DRAFT` version bound to a `DRAFT`, `ACTIVE`, `COMPLETED`, or `CANCELLED` campaign | Any-campaign reference check in `delete_policy_version` | `400 Bad Request` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-24` | Deleting the sole remaining version (`v1`) of a policy | `version_count <= 1` check in `delete_policy_version` | `400 Bad Request` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-25` | Publishing an unapproved (`DRAFT`, `UNDER_REVIEW`, `ARCHIVED`) version | `version.status != APPROVED` check | `400 Bad Request` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-26` | Creating campaign on an `ARCHIVED` policy or `SUPERSEDED`/`ARCHIVED` version | Policy & version status guard in `create_campaign` | `400 Bad Request` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-27` | Creating `ROLE_BASED` campaign with invalid or missing `target_role` | `RoleEnum` validation in `create_campaign` | `400 Bad Request` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-28` | Launching campaign when target audience resolves to 0 active users | `len(target_users) == 0` guard in `launch_campaign` | `400 Bad Request` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-29` | Launching an already `ACTIVE`, `COMPLETED`, or `CANCELLED` campaign | `campaign.status != DRAFT` guard | `400 Bad Request` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-30` | Modifying campaign metadata or `assessment_id` after launch (`ACTIVE`/`COMPLETED`/`CANCELLED`) | `campaign.status != DRAFT` guard in `update_campaign` | `400 Bad Request` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-31` | Closing a `DRAFT`, `COMPLETED`, or `CANCELLED` campaign | `campaign.status != ACTIVE` guard in `close_campaign` | `400 Bad Request` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-32` | Cancelling an already `COMPLETED` or `CANCELLED` campaign | `campaign.status not in (DRAFT, ACTIVE)` guard in `cancel_campaign` | `400 Bad Request` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-33` | Attesting to a `DRAFT`, `COMPLETED`, or `CANCELLED` campaign | `campaign.status != ACTIVE` guard in `submit_user_attestation` | `400 Bad Request` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-34` | Attesting with a tampered or mismatched `policy_version_hash` | Exact hash equality check against `campaign.policy_version_hash` | `400 Bad Request` | `test_phase24_adversarial_security.py` (`06, 13`) |
| `VEC-35` | Duplicate / replayed attestation on an already `ATTESTED` record | `record.status in (ATTESTED, EXEMPTED)` check | `409 Conflict` | `test_phase24_adversarial_security.py` (`15, 16`) |
| `VEC-36` | Attesting to an already `EXEMPTED` record | `record.status in (ATTESTED, EXEMPTED)` check | `409 Conflict` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-37` | Attesting when linked `Assessment` is `DRAFT`, `IN_PROGRESS`, or `INEFFECTIVE` | `Assessment` `COMPLETED` + `EFFECTIVE` gate | `400 Bad Request` | `test_phase24_adversarial_security.py` (`32, 37`) |
| `VEC-38` | Exemption Four-Eyes violation: Manager attempts to exempt their own `UserAttestationRecord` | `record.user_id == current_user_id` check | `400 Bad Request` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-39` | Exemption Four-Eyes violation: Manager who requested the `SecurityException` attempts to approve the attestation exemption | `exc.requested_by_id == current_user_id` check | `400 Bad Request` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-40` | Exempting a record with a `SecurityException` linked to a different `policy_id` | `exc.linked_policy_id == campaign.policy_id` check | `400 Bad Request` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-41` | Exempting a record with an unapproved (`REQUESTED`, `UNDER_REVIEW`, `REJECTED`, `CLOSED`) or expired `SecurityException` | Effective status == `ACTIVE` check | `400 Bad Request` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-42` | Replaying exemption on an already `EXEMPTED` or `ATTESTED` record | `record.status not in (PENDING, OVERDUE)` check | `409 Conflict` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-43` | Overdue evaluation idempotency and grace period enforcement | `due_date + timedelta(days=grace_period_days)` check; idempotent repeat | `200 OK` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-44` | Late attestation recovery (`OVERDUE -> ATTESTED`) updates `overdue_count` and `completed_count` accurately | Counter reconciliation in `submit_user_attestation` | `200 OK` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-45` | Campaign target snapshot stability when user changes role or is deactivated after launch | Frozen `user_attestation_records` snapshot; denominator unchanged | Verified in DB | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-46` | Evidence manifest generation blocked (`400`) if policy has no mapped `OrganizationControl` and always enters `UPLOADED` status when mapped | Control resolution & `EvidenceStatusEnum.UPLOADED` | `400` / `200 (UPLOADED)` | `test_phase24_adversarial_security.py` (`23, 24, 36`) |
| `VEC-47` | Mass-assignment extra field injection on `PolicyAttestationExemptionCreate` and `PolicyCampaignCancelRequest` | `ConfigDict(extra="forbid")` | `422 Unprocessable Entity` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-48` | RBAC enforcement across all 6 roles (`VIEWER`, `AUDITOR`, `SECURITY_ANALYST`, `GRC_ANALYST` blocked from `policy:approve` endpoints) | `require_permission(Permission.POLICY_APPROVE)` | `403 Forbidden` | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-49` | Canonical SHA-256 content hash normalization (`\r\n` vs `\n` and trailing line spaces produce identical hash) | `PolicyService.compute_canonical_hash` | Identical 64-char hex digest | `test_batch4_policy_lifecycle_governance.py` |
| `VEC-50` | Client timestamp / IP spoofing in attestation payload cannot forge server UTC `attested_at` or receipt identity | Server `datetime.now(timezone.utc)` & JWT `current_user.id` | `200 OK` (server UTC recorded) | `test_phase24_adversarial_security.py` (`07`) |

---

## 34. Implementation File Inventory

Only the following 9 files will be created or modified during Batch 4 implementation:

1. `backend/alembic/versions/0025_policy_lifecycle_governance_hardening.py` **(CREATE)**
2. `backend/app/models/policy.py` **(MODIFY)**
3. `backend/app/schemas/policy.py` **(MODIFY)**
4. `backend/app/services/policy_service.py` **(MODIFY)**
5. `backend/app/api/v1/endpoints/policies.py` **(MODIFY)**
6. `frontend/src/types/index.ts` **(MODIFY)**
7. `frontend/src/pages/PoliciesPage.tsx` **(MODIFY)**
8. `frontend/src/pages/PolicyDetailPage.tsx` **(MODIFY)**
9. `backend/tests/test_batch4_policy_lifecycle_governance.py` **(CREATE)**

---

## 35. Dependency Impact

- **Upstream Dependencies (Read-Only)**:
  - Phase 1: `User`, `Organization`, `AuditService`, `Permission`, `RoleEnum`
  - Phase 2: `FrameworkSubcategory`, `OrganizationControl`
  - Phase 3: `EvidenceItem`, `EvidenceStatusEnum`
  - Phase 4: `Assessment`, `AssessmentStatusEnum`, `AssessmentConclusionEnum`
  - Phase 5: `SecurityException`, `ExceptionStatusEnum`, `calculate_exception_effective_status`
- **No external Python or npm package additions are required.**

---

## 36. Backward Compatibility

- All 19 existing endpoints in `backend/app/api/v1/endpoints/policies.py` retain their exact URL paths, HTTP methods, status codes, and response fields.
- Existing schemas (`PolicyCreate`, `PolicyAttestationCampaignCreate`, `UserAttestationSubmit`) retain `extra="ignore"` so `test_adv_p24_04`, `05`, `07`, `22`, and `35` pass without modification.
- `create_campaign` continues to allow `DRAFT`, `APPROVED`, and `PUBLISHED` versions (blocking only `ARCHIVED` and `SUPERSEDED`) so `test_phase24_api.py` and `test_phase24_adversarial_security.py` (which create campaigns on `v1` in `DRAFT` status) pass 100%.

---

## 37. Batch Boundary

All Batch 4 (`POLICY-LIFECYCLE-GRC`) scope items share the same SQLAlchemy model module (`backend/app/models/policy.py`), service (`backend/app/services/policy_service.py`), API router (`backend/app/api/v1/endpoints/policies.py`), migration (`0025`), and React workspace (`PoliciesPage.tsx`, `PolicyDetailPage.tsx`). Splitting them would create artificial partial migrations and intermediate states. Therefore, **Batch 4 remains a single cohesive implementation batch**.

---

## 38. Resolution of Critical Hardening Questions (A–Z) & Open Questions

| ID | Question | Authoritative Resolution |
|---|---|---|
| **A** | Is `PolicyVersion` already sufficiently authoritative? | **YES.** Contains `version_number`, `content`, `content_hash_sha256`, `status`, `created_by_id`, `approved_by_id`, `approved_at`, `effective_date`. |
| **B** | Is `PolicyReviewWorkflow` sufficient or does it require extension? | **Requires 1 additive column (`updated_at`), composite index, `created_by` relationship in schema, and service-layer replay/SoD hardening.** |
| **C** | Does campaign membership already have a frozen snapshot? | **YES.** `launch_campaign` materializes `UserAttestationRecord` rows and freezes `total_targeted_count`. |
| **D** | Can target population disappear and incorrectly improve compliance? | **NO.** Deactivating a user or changing their role after launch does not delete their `UserAttestationRecord` or reduce `total_targeted_count`. |
| **E** | Is `EXEMPTED` actually compatible with `SecurityException` authority? | **YES.** `UserAttestationRecord.exemption_exception_id` links directly to `security_exceptions.id` (`linked_policy_id == campaign.policy_id`). |
| **F** | Does `SecurityException` already provide the required Four-Eyes? | **Phase 5 enforces `exc.reviewer_id != exc.requested_by_id`, and Batch 4 adds `current_user_id != record.user_id` AND `current_user_id != exc.requested_by_id` at exemption grant time.** |
| **G** | Does current attestation identity derive exclusively from authenticated user? | **YES.** `submit_user_attestation` uses `current_user.id` and `current_user.organization_id` from JWT dependency. |
| **H** | Is the current cryptographic receipt deterministic and tamper evident? | **YES.** SHA-256 over pipe-delimited `org_id|user_id|campaign_id|version_id|policy_version_hash|now_iso|client_ip`. |
| **I** | Can approved/published policy content be mutated? | **NO.** `update_policy_version` blocks any version where `status != DRAFT`. |
| **J** | Can policy versions be deleted in ways that destroy lineage? | **Hardened in Batch 4:** `delete_policy_version` will block deleting any non-`DRAFT` version, sole version, or campaign/review-referenced version. |
| **K** | Can review decisions be replayed? | **Hardened in Batch 4:** `review_policy_version_workflow` will enforce `workflow.status == PENDING` and `version.status == UNDER_REVIEW`. |
| **L** | Can campaign activation race? | **Protected:** `campaign.status == DRAFT` check + `UniqueConstraint("organization_id", "campaign_id", "user_id")`. |
| **M** | Can duplicate attestations race? | **Protected:** `uq_camp_user_attestation` + `record.status in (ATTESTED, EXEMPTED)` check returning `HTTP 409`. |
| **N** | Can assessment completion be substituted? | **Hardened in Batch 4:** `create_campaign` and `update_campaign` validate `Assessment.organization_id == organization_id`, and `submit_user_attestation` checks the campaign's bound `assessment_id`. |
| **O** | Can `EvidenceReview` be bypassed? | **NO.** `generate_campaign_evidence` always sets `status = EvidenceStatusEnum.UPLOADED`. |
| **P** | Can cross-tenant evidence or assessment relationships be injected? | **NO.** All foreign keys (`owner_id`, `assigned_reviewer_id`, `assessment_id`, `security_exception_id`) are verified against `organization_id`. |
| **Q** | Are telemetry counters authoritative? | **YES.** Reconciled via database aggregate queries over `UserAttestationRecord`. |
| **R** | Can role changes alter campaign denominator unexpectedly? | **NO.** Target roster is snapshotted at `launch_campaign`. |
| **S** | Can cancelled campaigns still be attested? | **NO.** `submit_user_attestation` enforces `campaign.status == CampaignStatusEnum.ACTIVE`. |
| **T** | Can superseded versions be used for new campaigns? | **Hardened in Batch 4:** `create_campaign` blocks `SUPERSEDED` and `ARCHIVED` versions (`HTTP 400`). |
| **U** | Can expired campaigns be treated as completed? | **NO.** Past-due records transition to `OVERDUE` (`evaluate_campaign_overdue`), not `COMPLETED`. |
| **V** | Can exemption be used to artificially inflate compliance? | **NO.** Exemptions require `Permission.POLICY_APPROVE`, an active non-expired Phase 5 `SecurityException` linked to the same policy, triple Four-Eyes SoD, and an audit log entry. |
| **W** | Does the frontend currently expect fields that backend does not return? | **YES.** Fixed in Batch 4 by adding `versions` to `PolicyResponse`, `reviews` to `PolicyVersionResponse`, `created_by` to `PolicyReviewWorkflowResponse`, and `policy_version_hash`/`policy_content`/`campaign_code`/`version_number`/`record_id` to `UserAttestationRecordResponse`. |
| **X** | Does executive integration already have a policy governance extension point? | **YES.** `EvidenceItem` flows into `ExecutiveService` audit readiness, and `/api/v1/policies/telemetry` provides dedicated policy governance telemetry. |
| **Y** | Does continuous assurance already have a policy governance metric extension point? | **YES.** Pillar 2 (`evidence_pipeline`) in `ContinuousComplianceService` automatically consumes campaign `EvidenceItem` rows. |
| **Z** | Is migration `0025` sufficient and safe? | **YES.** Additive nullable/defaulted columns and indexes via `op.batch_alter_table`, preserving all existing data. |

**Open Questions**: **NONE.** All architectural, schema, state-machine, RBAC, Four-Eyes, and cross-module boundary questions are fully resolved from repository ground truth.

---

## 39. Final GO / NO-GO

| Security & Architecture Gate | Verdict |
|---|---|
| Baseline Verification (`9c34411f5cc4f7f5b849e457d2304ea1e9fc00bd`, Alembic head `0024`) | **PASS** |
| Phase 24 Reconciliation & Anti-Duplication Gate | **PASS** |
| Tenant Isolation & BOLA/IDOR Defenses | **PASS** |
| RBAC & Triple Four-Eyes SoD Governance | **PASS** |
| Immutability & Cryptographic Digest Integrity | **PASS** |
| Phase 3 Evidence, Phase 4 Assessment & Phase 5 SecurityException Authority | **PASS** |
| Migration `0025` Non-Destructive Safety | **PASS** |
| Frontend/Backend Contract Alignment | **PASS** |

BATCH 4 ARCHITECTURE HARDENING COMPLETE — GO FOR IMPLEMENTATION.
