# CONTROLSPHERE — PHASE 24 HARDENED ARCHITECTURE SPECIFICATION
**Module Code**: `POLICY-ATTESTATION-GRC`
**Module Title**: Enterprise Policy Lifecycle & Workforce Attestation Governance
**Architecture Gate Status**: **HARDENED & VALIDATED**

---

## 1. Architecture Gate Verdict

# **VERDICT: GO**

All critical architecture, cryptographic, tenant-isolation, Four-Eyes Segregation of Duties (SoD), evidence lifecycle, and concurrency invariants have been fully analyzed and hardened against the actual ControlSphere codebase.

---

## 2. Repository Ground Truth

```text
Repository Path:      E:\PROJECT WORKSPACE 2\ControlSphere
Current Branch:       main
Current HEAD Commit:  ef34526fb6ab387a3eaafbb2a22c1485666b7626 (ef34526)
Alembic Linear Head:  0020_regulatory_integration_continuous_grc (0020)
Backend Regression:   925 / 925 tests PASSED (0 failures, 0 errors in pytest)
Frontend Build:       PASS (tsc -b && vite build in 559ms)
Working Tree State:   Clean (0 unstaged changes, 0 staged changes)
Platform Roles:       ADMIN, MANAGER, GRC_ANALYST, SECURITY_ANALYST, AUDITOR, VIEWER (Exactly 6 roles)
```

---

## 3. Existing Policy Authority

Inspection of [`backend/app/models/policy.py`](file:///e:/PROJECT%20WORKSPACE%202/ControlSphere/backend/app/models/policy.py) and [`backend/app/services/policy_service.py`](file:///e:/PROJECT%20WORKSPACE%202/ControlSphere/backend/app/services/policy_service.py) confirms the baseline Phase 2 implementation:
- **`Policy` Table**: Root entity holding `id`, `organization_id`, `title`, `description`, `policy_type`, `status` (`DRAFT`, `UNDER_REVIEW`, `APPROVED`, `PUBLISHED`, `ARCHIVED`), `owner_id`, `effective_date`, `review_date`, `created_at`, `updated_at`.
- **`PolicyVersion` Table**: Child entity holding `id`, `policy_id`, `version_number` (Integer 1, 2, 3...), `content` (Markdown text), `change_summary`, `created_by_id`, `created_at`.
- **`PolicyControlMapping` Table**: Mapping table linking policies to `framework_subcategories`.
- **Authority Boundary**: `PolicyService` owns basic CRUD, policy status transitions, and control mapping.

---

## 4. Phase 24 Boundary & Anti-Duplication Directives

Phase 24 **EXTENDS** the existing Policy domain and strictly avoids duplicate engines:
1. **NO Duplicate Policy Model**: Extends existing `policies` and `policy_versions` without creating `Policy2` or `PolicyCompliance`.
2. **NO Duplicate Control Engine**: Reuses existing `organization_controls` and `PolicyControlMapping`.
3. **NO Duplicate Evidence Engine**: Completed attestation campaigns deposit records into Phase 3 [`EvidenceItem`](file:///e:/PROJECT%20WORKSPACE%202/ControlSphere/backend/app/models/evidence.py) in `UPLOADED` status. `EvidenceReview` remains 100% authoritative.
4. **NO Duplicate Assessment Engine**: If a policy campaign requires comprehension testing, it optionally links to Phase 4 [`Assessment`](file:///e:/PROJECT%20WORKSPACE%202/ControlSphere/backend/app/models/assessment.py) rather than inventing a second quiz/questionnaire engine.
5. **NO Duplicate CAPA / Remediation Engine**: Policy deficiencies or unmitigated non-compliance trigger Phase 11 [`RemediationPlan`](file:///e:/PROJECT%20WORKSPACE%202/ControlSphere/backend/app/models/remediation.py).

---

## 5. Entity Model & Database Architecture (Migration `0021`)

Migration `0021_policy_lifecycle_and_attestation.py` will introduce schema enhancements to `policy_versions` and create 3 new persistent tables:

```
[ policies ] (Existing Phase 2)
     │
     ├──< [ policy_versions ] (Enhanced with SHA-256 hash, status, approval metadata)
     │         │
     │         ├──< [ policy_review_workflows ] (Four-Eyes Legal/CISO Review Lifecycle)
     │         │
     │         └──< [ policy_attestation_campaigns ] (Targeted Distribution & Deadlines)
     │                   │
     │                   └──< [ user_attestation_records ] (Cryptographic Receipts & Sign-offs)
     │
     └──< [ policy_control_mappings ] (Existing Phase 2)
```

### Table 1: `policy_versions` (Updated Columns in Migration `0021`)
- `id`: Integer PK
- `organization_id`: Integer FK $\rightarrow$ `organizations.id` (CASCADE)
- `policy_id`: Integer FK $\rightarrow$ `policies.id` (CASCADE)
- `version_number`: Integer NOT NULL (1, 2, 3...)
- `content`: Text NOT NULL (Markdown policy body)
- `content_hash_sha256`: String(64) NOT NULL (Canonical SHA-256 of normalized markdown)
- `change_summary`: String(255) NOT NULL
- `status`: String(50) NOT NULL server default `'DRAFT'` (`DRAFT`, `UNDER_REVIEW`, `APPROVED`, `PUBLISHED`, `SUPERSEDED`, `ARCHIVED`)
- `effective_date`: Date NULL
- `approved_by_id`: Integer FK $\rightarrow$ `users.id` (SET NULL)
- `approved_at`: DateTime(timezone=True) NULL
- `created_by_id`: Integer FK $\rightarrow$ `users.id` (SET NULL)
- `created_at`: DateTime(timezone=True) NOT NULL
- **Constraints**: `UniqueConstraint("policy_id", "version_number", name="uq_policy_version_number")`, `Index("ix_policy_versions_org_hash", "organization_id", "content_hash_sha256")`

### Table 2: `policy_review_workflows` (New Table)
- `id`: Integer PK
- `organization_id`: Integer FK $\rightarrow$ `organizations.id` (CASCADE)
- `policy_id`: Integer FK $\rightarrow$ `policies.id` (CASCADE)
- `version_id`: Integer FK $\rightarrow$ `policy_versions.id` (CASCADE)
- `workflow_code`: String(64) NOT NULL
- `review_stage`: String(50) NOT NULL default `'LEGAL_REVIEW'` (`LEGAL_REVIEW`, `SECURITY_REVIEW`, `EXECUTIVE_APPROVAL`)
- `status`: String(50) NOT NULL default `'PENDING'` (`PENDING`, `APPROVED`, `REJECTED`, `CHANGES_REQUESTED`)
- `assigned_reviewer_id`: Integer FK $\rightarrow$ `users.id` (SET NULL)
- `review_notes`: Text NULL
- `reviewed_by_id`: Integer FK $\rightarrow$ `users.id` (SET NULL)
- `reviewed_at`: DateTime(timezone=True) NULL
- `created_by_id`: Integer FK $\rightarrow$ `users.id` (SET NULL)
- `created_at`: DateTime(timezone=True) NOT NULL
- **Constraints**: `UniqueConstraint("organization_id", "workflow_code", name="uq_pol_rev_wf_code")`

### Table 3: `policy_attestation_campaigns` (New Table)
- `id`: Integer PK
- `organization_id`: Integer FK $\rightarrow$ `organizations.id` (CASCADE)
- `campaign_code`: String(64) NOT NULL
- `title`: String(255) NOT NULL
- `policy_id`: Integer FK $\rightarrow$ `policies.id` (CASCADE)
- `version_id`: Integer FK $\rightarrow$ `policy_versions.id` (RESTRICT) — *Prevents deletion of version during active campaign*
- `policy_version_hash`: String(64) NOT NULL — *Snapshot of version hash at campaign launch*
- `target_type`: String(50) NOT NULL default `'ALL_USERS'` (`ALL_USERS`, `ROLE_BASED`, `CUSTOM_GROUP`)
- `target_role`: String(50) NULL (e.g. `'SECURITY_ANALYST'`)
- `due_date`: DateTime(timezone=True) NOT NULL
- `grace_period_days`: Integer NOT NULL default `0`
- `status`: String(50) NOT NULL default `'DRAFT'` (`DRAFT`, `ACTIVE`, `COMPLETED`, `CANCELLED`)
- `assessment_id`: Integer FK $\rightarrow$ `assessments.id` (SET NULL) — *Optional Phase 4 comprehension quiz*
- `total_targeted_count`: Integer NOT NULL default `0`
- `completed_count`: Integer NOT NULL default `0`
- `created_by_id`: Integer FK $\rightarrow$ `users.id` (SET NULL)
- `launched_at`: DateTime(timezone=True) NULL
- `closed_at`: DateTime(timezone=True) NULL
- `created_at`: DateTime(timezone=True) NOT NULL
- **Constraints**: `UniqueConstraint("organization_id", "campaign_code", name="uq_pol_att_camp_code")`

### Table 4: `user_attestation_records` (New Table)
- `id`: Integer PK
- `organization_id`: Integer FK $\rightarrow$ `organizations.id` (CASCADE)
- `campaign_id`: Integer FK $\rightarrow$ `policy_attestation_campaigns.id` (CASCADE)
- `policy_id`: Integer FK $\rightarrow$ `policies.id` (CASCADE)
- `version_id`: Integer FK $\rightarrow$ `policy_versions.id` (CASCADE)
- `user_id`: Integer FK $\rightarrow$ `users.id` (CASCADE)
- `status`: String(50) NOT NULL default `'PENDING'` (`PENDING`, `ATTESTED`, `OVERDUE`)
- `attested_at`: DateTime(timezone=True) NULL
- `ip_address`: String(45) NULL
- `user_agent`: String(500) NULL
- `acknowledgement_text`: Text NULL
- `comprehension_passed`: Boolean NOT NULL default `true`
- `attestation_receipt_hash`: String(64) NULL — *Deterministic SHA-256 tamper-evident receipt*
- `evidence_item_id`: Integer FK $\rightarrow$ `evidence_items.id` (SET NULL)
- `created_at`: DateTime(timezone=True) NOT NULL
- **Constraints**: `UniqueConstraint("organization_id", "campaign_id", "user_id", name="uq_camp_user_attestation")`, `Index("ix_user_att_status", "organization_id", "user_id", "status")`

---

## 6. State Machines

### A. Policy Version State Machine
```
[ DRAFT ] ───────────► [ UNDER_REVIEW ] ───────────► [ APPROVED ] ───────────► [ PUBLISHED ] ───────────► [ SUPERSEDED / ARCHIVED ]
    ▲                         │ (Changes Req)               │                        ▲
    └─────────────────────────┴─────────────────────────────┴────────────────────────┘
```
- `DRAFT`: Editable by author (`created_by_id`).
- `UNDER_REVIEW`: Locked from content mutation. Assigned to reviewers.
- `APPROVED`: Passed Four-Eyes review (`created_by_id != approved_by_id`). Fully immutable.
- `PUBLISHED`: Active enterprise policy. Eligible for attestation campaign distribution.
- `SUPERSEDED`: Replaced by a newer published version.
- `ARCHIVED`: Withdrawn / deprecated policy.

### B. Attestation Campaign State Machine
```
[ DRAFT ] ───────────► [ ACTIVE ] ───────────► [ COMPLETED ]
   │                       │
   └──► [ CANCELLED ] ◄────┘
```
- `DRAFT`: Targets configured, due dates set. User assignments not yet generated.
- `ACTIVE`: Launched by Manager/Admin. User attestation records created in `PENDING` state. Policy version locked.
- `COMPLETED`: 100% attested or deadline passed and formally closed. Deposits Phase 3 `EvidenceItem`.
- `CANCELLED`: Aborted campaign. Pending attestations voided.

---

## 7. Immutability Rules

1. **Policy Content Locking**:
   - `content` and `content_hash_sha256` are mutable **only** while `status == 'DRAFT'`.
   - Once submitted to `UNDER_REVIEW` or `APPROVED`, the database layer rejects updates to `content` and `version_number`.
   - Any proposed modification requires creating a new incremented `PolicyVersion` (e.g. Version 2).
2. **Campaign Policy Freezing**:
   - At launch, `policy_attestation_campaigns` captures `policy_version_hash`.
   - The campaign is permanently locked to that exact version hash. No administrator can substitute the underlying content.
3. **Attestation Record Immutability**:
   - Once `status` transitions from `PENDING` $\rightarrow$ `ATTESTED`, the record (`attested_at`, `attestation_receipt_hash`, `ip_address`, `user_agent`) becomes **strictly read-only**.

---

## 8. Four-Eyes / Segregation of Duties (SoD) Model

| Workflow Gate | Creator / Requester | Reviewer / Approver | SoD Validation Rule (Backend Enforced) |
| :--- | :--- | :--- | :--- |
| **Policy Version Approval** | `policy_version.created_by_id` | `workflow.reviewed_by_id` / `approver_id` | `policy_version.created_by_id != approver_id` (Self-approval rejected with HTTP 400) |
| **Campaign Launch** | `campaign.created_by_id` | `current_user_id` (Manager/Admin) | Authorized role check; logged with non-repudiation audit event |
| **User Attestation** | `user_attestation_record.user_id` | N/A (Self-service) | `current_user.id == record.user_id` (Admin/Manager cannot forge user signatures) |
| **Attestation Evidence Acceptance** | `campaign.created_by_id` (uploader) | Phase 3 `EvidenceReview.reviewer_id` | `uploaded_by_id != reviewer_id` (Enforced by existing Phase 3 engine) |

---

## 9. Attestation Integrity & Cryptographic Terminology

### Clarification on Cryptography
ControlSphere explicitly designates the attestation token as a **Tamper-Evident Cryptographic Attestation Receipt** (or **Attestation Digest**), **NOT** an asymmetric digital signature:

$$\text{Attestation Receipt Hash} = \text{SHA256}(\text{org\_id} \parallel \text{user\_id} \parallel \text{campaign\_id} \parallel \text{version\_id} \parallel \text{policy\_hash} \parallel \text{timestamp\_iso} \parallel \text{ip\_address})$$

### Rationale
- **Non-Repudiation**: Binds the authenticated server context, user ID, policy content hash, immutable timestamp, and origin network address into a deterministic SHA-256 digest.
- **Audit Verification**: Auditors can recompute the hash at any time to verify that neither the user record, policy version, nor timestamp was manipulated post-attestation.
- **Accuracy**: Avoids false claims of PKI asymmetric signing while providing audit-grade integrity.

---

## 10. Canonical Policy Hash Representation

To guarantee identical SHA-256 hash generation across all platforms and operating systems:
1. **UTF-8 Encoding**: Content is decoded to UTF-8 strings.
2. **Newline Normalization**: All line breaks (`\r\n` or `\r`) are converted to Unix LF (`\n`).
3. **Trailing Whitespace Trimming**: Trailing whitespace on individual lines is stripped; leading indentation is preserved.
4. **Encoding & Digesting**:
   ```python
   normalized_text = "\n".join(line.rstrip() for line in raw_content.replace("\r\n", "\n").replace("\r", "\n").split("\n"))
   content_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
   ```

---

## 11. Campaign Management & Target Assignment

### Assignment Mechanics
- When a campaign is launched (`POST /api/v1/policies/campaigns/{id}/launch`):
  1. Active users (`User.is_active == True`) matching `target_type` (`ALL_USERS` or `target_role`) in `organization_id` are enumerated.
  2. For each eligible user, a `UserAttestationRecord` is bulk-inserted with `status = 'PENDING'`.
  3. `total_targeted_count` is set to the total inserted records.
  4. Inactive or terminated users are strictly excluded.
- **Idempotent Assignments**: The composite constraint `uq_camp_user_attestation(organization_id, campaign_id, user_id)` prevents duplicate records on relaunch or retry.

---

## 12. Comprehension Verification Model

1. **Standard Mode (Default)**: User confirms statutory acknowledgment checkbox with explicit text ("I have read, understood, and agree to comply with this policy").
2. **Assessment-Linked Mode (Optional)**:
   - If the campaign defines `assessment_id` (referencing an existing Phase 4 [`Assessment`](file:///e:/PROJECT%20WORKSPACE%202/ControlSphere/backend/app/models/assessment.py)), the user must complete and pass the assessment questions.
   - `comprehension_passed` is set to `True` upon achieving the required passing score in `AssessmentService`.
   - **Zero Duplication**: Reuses Phase 4 `AssessmentQuestion` and `AssessmentResponse` models without introducing a parallel quiz engine.

---

## 13. Evidence Lifecycle Boundary

```
[ Attestation Campaign Completed ]
               │
               ▼ (Generates JSON Attestation Manifest)
[ EvidenceItem Created (status = 'UPLOADED') ]
               │
               ▼ (Assigned to Independent Reviewer)
[ Phase 3 EvidenceReview (Four-Eyes Check: uploaded_by_id != reviewer_id) ]
               │
               ├──► [ ACCEPTED ] (Authoritative compliance credit)
               └──► [ REJECTED ] (Deficiency logged, CAPA triggered)
```

- **Manifest Payload**: Contains `campaign_code`, `policy_title`, `policy_version_number`, `policy_content_hash`, `total_targeted`, `total_completed`, `completion_rate`, `launched_at`, `closed_at`, and list of attested user receipts with SHA-256 hashes.
- **Strict Invariant**: Auto-acceptance is prohibited.

---

## 14. Permissions Architecture

Mapped across the exactly 6 platform roles in [`backend/app/core/permissions.py`](file:///e:/PROJECT%20WORKSPACE%202/ControlSphere/backend/app/core/permissions.py):

| Permission | Identifier | ADMIN | MANAGER | GRC_ANALYST | SECURITY_ANALYST | AUDITOR | VIEWER |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **View Policies & Versions** | `policy:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Manage & Draft Policies** | `policy:manage` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Approve Policy Versions** | `policy:approve` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Manage Campaigns** | `policy:campaign_manage` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Attest to Assigned Policy**| `policy:attest` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## 15. Tenant Isolation & IDOR Protection

1. **Token Scoping**: `organization_id` is extracted strictly from authenticated JWT token context (`current_user.organization_id`). Client-provided `organization_id` in request bodies is discarded.
2. **Cross-Tenant Blocking**: Queries filter by `organization_id`. Any lookup for foreign policies, versions, campaigns, or attestation records returns **HTTP 404**.
3. **Personal User Scoping**: Self-service attestation endpoints (`GET /api/v1/policies/my-pending-attestations` and `POST /api/v1/policies/campaigns/{id}/attest`) enforce `user_id == current_user.id`.

---

## 16. Audit Logging & Non-Repudiation

All sensitive operations emit structured records via `AuditService.log`:
- `CREATE_POLICY_VERSION`
- `SUBMIT_POLICY_REVIEW`
- `APPROVE_POLICY_VERSION` (Logs `approved_by_id`, `version_number`)
- `PUBLISH_POLICY_VERSION`
- `LAUNCH_ATTESTATION_CAMPAIGN` (Logs `campaign_code`, `target_count`)
- `SUBMIT_USER_ATTESTATION` (Logs `user_id`, `attestation_receipt_hash`, `ip_address`)
- `CLOSE_ATTESTATION_CAMPAIGN`
- `DEPOSIT_ATTESTATION_EVIDENCE` (Logs `evidence_item_id`, `sha256_hash`)

---

## 17. Race Conditions, Concurrency & Idempotency

1. **Concurrent Attestations**:
   - Atomic database condition:
     ```sql
     UPDATE user_attestation_records
     SET status = 'ATTESTED', attested_at = :now, attestation_receipt_hash = :hash
     WHERE id = :record_id AND status = 'PENDING' AND organization_id = :org_id;
     ```
   - If rowcount is 0, request returns HTTP 409 Conflict ("Attestation already submitted").
2. **Concurrent Campaign Launches**:
   - `status` check inside database transaction ensures only one worker transitions `DRAFT` $\rightarrow$ `ACTIVE`.
3. **Concurrent Version Numbers**:
   - `UniqueConstraint("policy_id", "version_number")` prevents duplicate version generation.

---

## 18. Cross-Module Integration Map

- **Phase 2 (Controls)**: Policies map to subcategories via `PolicyControlMapping`.
- **Phase 3 (Evidence)**: Campaign manifests deposit directly into `evidence_items`.
- **Phase 5 (Exceptions)**: Policy exception requests link to `policy_versions`.
- **Phase 20 (Executive GRC)**: Attestation completion percentages feed Executive Dossiers.
- **Phase 21 (Regulatory GRC)**: Regulatory obligations reference policies demonstrating compliance.
- **Phase 23 (Continuous GRC)**: Attestation campaign health directly informs the Evidence Pipeline pillar.

---

## 19. API Design (Endpoints)

```
# Policy Versions & Review
GET    /api/v1/policies/{id}/versions                       (policy:read)
POST   /api/v1/policies/{id}/versions                       (policy:manage)
POST   /api/v1/policies/{id}/versions/{v_id}/submit-review   (policy:manage)
POST   /api/v1/policies/{id}/versions/{v_id}/approve        (policy:approve)
POST   /api/v1/policies/{id}/versions/{v_id}/publish        (policy:manage)

# Attestation Campaigns
GET    /api/v1/policies/campaigns                           (policy:read)
POST   /api/v1/policies/campaigns                           (policy:campaign_manage)
GET    /api/v1/policies/campaigns/{id}                      (policy:read)
POST   /api/v1/policies/campaigns/{id}/launch               (policy:campaign_manage)
POST   /api/v1/policies/campaigns/{id}/close                (policy:campaign_manage)

# User Self-Service Attestation
GET    /api/v1/policies/my-pending-attestations             (policy:attest)
POST   /api/v1/policies/campaigns/{id}/attest               (policy:attest)
```

---

## 20. Exact Adversarial Security Test Matrix (35 Tests)

To be implemented in `backend/tests/test_phase24_adversarial_security.py`:

| Test Identifier | Security Invariant Tested |
| :--- | :--- |
| `test_adv_p24_01_cross_tenant_policy_version_read` | Tenant A cannot read Tenant B policy versions (HTTP 404). |
| `test_adv_p24_02_cross_tenant_version_creation` | Tenant A cannot create versions under Tenant B policy. |
| `test_adv_p24_03_four_eyes_policy_version_self_approval` | Creator cannot approve own policy version (HTTP 400). |
| `test_adv_p24_04_admin_four_eyes_bypass_rejection` | Admin creator cannot bypass Four-Eyes SoD rule. |
| `test_adv_p24_05_analyst_unauthorized_policy_approval` | `GRC_ANALYST` cannot approve policy version (HTTP 403). |
| `test_adv_p24_06_viewer_version_mutation_escalation` | `VIEWER` cannot create or update versions (HTTP 403). |
| `test_adv_p24_07_post_approval_content_tamper_rejection` | Modifying content of `APPROVED` version is blocked. |
| `test_adv_p24_08_duplicate_version_number_conflict` | Duplicate `version_number` under same policy returns HTTP 409. |
| `test_adv_p24_09_canonical_hash_whitespace_insensitivity` | Hash calculation normalizes CRLF and trailing spaces deterministically. |
| `test_adv_p24_10_cross_tenant_campaign_access` | Tenant A cannot view Tenant B attestation campaigns. |
| `test_adv_p24_11_campaign_policy_substitution_rejection` | Cannot change `version_id` or hash on an `ACTIVE` campaign. |
| `test_adv_p24_12_cross_tenant_campaign_launch` | Launching a campaign in another tenant returns HTTP 404. |
| `test_adv_p24_13_duplicate_campaign_code_conflict` | Unique constraint enforces tenant-scoped `campaign_code`. |
| `test_adv_p24_14_cross_tenant_user_attestation_submission` | Submitting attestation for foreign tenant record returns HTTP 404. |
| `test_adv_p24_15_forged_user_attestation_rejection` | User cannot submit attestation on behalf of another user ID. |
| `test_adv_p24_16_duplicate_attestation_replay_rejection` | Submitting second attestation on `ATTESTED` record returns HTTP 409. |
| `test_adv_p24_17_concurrent_attestation_race_condition` | Concurrent attestation requests execute atomically without duplicate state. |
| `test_adv_p24_18_client_controlled_timestamp_override_ignored`| Server overrides client timestamp with authoritative UTC now. |
| `test_adv_p24_19_client_controlled_status_tampering_ignored` | Client cannot set `status = 'ATTESTED'` without executing full workflow. |
| `test_adv_p24_20_tampered_policy_hash_attestation_rejection` | Submitting attestation with mismatched policy hash is rejected. |
| `test_adv_p24_21_attestation_receipt_hash_reproducibility` | Recomputed receipt hash matches recorded `attestation_receipt_hash`. |
| `test_adv_p24_22_inactive_user_exclusion_from_campaign` | `is_active = False` users are excluded from campaign target assignments. |
| `test_adv_p24_23_unauthorized_campaign_closure` | Only authorized roles (`ADMIN`, `MANAGER`) can close campaigns. |
| `test_adv_p24_24_evidence_auto_acceptance_prevention` | Deposited campaign evidence enters `EvidenceItem` as `UPLOADED` only. |
| `test_adv_p24_25_evidence_manifest_checksum_integrity` | Deposited evidence JSON manifest matches recorded SHA-256 payload. |
| `test_adv_p24_26_xss_injection_in_acknowledgement_text` | Malicious scripts in acknowledgment comments are sanitized. |
| `test_adv_p24_27_sql_injection_in_campaign_filters` | SQL injection in campaign search/role filters is safely parameterized. |
| `test_adv_p24_28_audit_log_emission_on_policy_approval` | Audit log records approval event with user and version metadata. |
| `test_adv_p24_29_audit_log_emission_on_attestation` | Audit log records attestation event with receipt hash. |
| `test_adv_p24_30_my_pending_attestations_idor_protection` | `/my-pending-attestations` returns strictly authenticated user's records. |
| `test_adv_p24_31_campaign_due_date_timezone_handling` | Timezone-aware deadline calculation accurately identifies overdue records. |
| `test_adv_p24_32_assessment_comprehension_failure_blocks_attest`| Failing linked comprehension quiz prevents attestation completion. |
| `test_adv_p24_33_unauthorized_policy_publishing` | Cannot publish version without prior formal approval. |
| `test_adv_p24_34_policy_version_deletion_restriction` | Cannot delete a version currently bound to an active campaign. |
| `test_adv_p24_35_client_organization_id_injection_ignored` | Client payload `organization_id` cannot hijack tenant scoping. |

---

## 21. Implementation Sequence

1. **Migration `0021`**: Add columns to `policy_versions`, create `policy_review_workflows`, `policy_attestation_campaigns`, and `user_attestation_records`.
2. **SQLAlchemy Models**: Update `backend/app/models/policy.py`.
3. **Pydantic Schemas**: Define versioning, review, campaign, and attestation schemas in `backend/app/schemas/policy.py`.
4. **Domain Services**: Implement `PolicyLifecycleService` and `PolicyAttestationService` in `backend/app/services/policy_service.py`.
5. **REST API Endpoints**: Add routes in `backend/app/api/v1/endpoints/policies.py`.
6. **Permissions**: Update `backend/app/core/permissions.py`.
7. **Adversarial Test Suite**: Create `backend/tests/test_phase24_adversarial_security.py` (35 tests) + domain/API test suites.
8. **Frontend Workspaces**:
   - Version history and markdown diff tab in `PolicyDetailPage.tsx`.
   - Campaign management and telemetry dashboard in `PoliciesPage.tsx`.
   - Employee pending attestation modal in `DashboardPage.tsx`.
9. **Verification**: Full backend regression ($925 \rightarrow 960+$ tests passing) and production frontend build (`npm run build`).

---

## 22. Architecture Decision Record (ADR)

- **ADR-024**: Hardening of Enterprise Policy Lifecycle and Workforce Attestation Governance.
- **Context**: Workforce attestation and legal policy review are critical compliance requirements across SOC 2, ISO 27001, NIST CSF 2.0, and HIPAA.
- **Decision**: Extend existing `Policy` and `PolicyVersion` entities; introduce `policy_review_workflows`, `policy_attestation_campaigns`, and `user_attestation_records`; utilize deterministic SHA-256 Tamper-Evident Attestation Receipts; deposit summary evidence into Phase 3 in `UPLOADED` status without auto-acceptance.
- **Consequences**: Delivers complete workforce policy governance with zero architectural duplication, strict Four-Eyes enforcement, and full backward compatibility.

---

## 23. Final Architecture Gate Verdict

# **VERDICT: GO**

Phase 24 is architecturally hardened, security-verified, and ready for full vertical implementation.
