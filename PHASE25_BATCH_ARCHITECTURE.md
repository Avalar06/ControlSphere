# Batch 1 Architecture Blueprint: Enterprise Audit Fieldwork Governance

**Batch Code**: `BATCH-1-AUDIT-FIELDWORK`
**Batch Title**: Enterprise Audit Fieldwork, PBC Requests, Statistical Sampling & Workpaper Governance
**Consolidated Architectural Capabilities**:
- Capability A: Audit Fieldwork & Workpaper Execution
- Capability B: PBC (Provided By Client) Evidence Request Governance
- Capability C: Statistical, Systematic & Stratified Audit Sampling Engine (AU-C 530 / PCAOB AS 2315)
- Capability D: Audit Sample Exception $\rightarrow$ Finding Escalation Bridge
- Capability E: Multi-Tier Workpaper Review & Four-Eyes Signoff (`prepared_by_id != reviewed_by_id`)
- Capability F: Enhanced Audit Readiness & PBC Telemetry

**Vertical Stack Status**: ARCHITECTURE BLUEPRINT COMPLETE — GATE PASS
**Git Baseline**: `8b8b482d98e8d74a4807f490c0219b9b9eefa564` (main, clean, pushed)
**Alembic Head**: `0021 (head)`
**Target Migration**: `0022_audit_fieldwork_and_sampling.py`
**Current Test Baseline**: 965 / 965 passing tests (100% pass rate)

---

## 1. Current Audit Architecture Ground Truth

### 1.1 Existing Phase 6 Database Models (`backend/app/models/audit_engagement.py`)
ControlSphere currently models audit engagements through:
1. `Audit`: Top-level engagement entity with metadata, dates, lead auditor, and status (`PLANNED`, `INITIATED`, `FIELDWORK`, `REVIEW`, `REPORTING`, `COMPLETED`, `CLOSED`).
2. `AuditScopeControl`: Links an `OrganizationControl` into the audit scope.
3. `AuditProcedure`: Represents an individual audit test step linked to an optional `OrganizationControl` with `test_steps`, `expected_result`, `actual_result`, `tester_id`, and `result` (`NOT_STARTED`, `IN_PROGRESS`, `PASSED`, `PARTIALLY_PASSED`, `FAILED`, `NOT_APPLICABLE`).
4. `AuditProcedureEvidence`: Many-to-many junction linking an `EvidenceItem` to an `AuditProcedure`.
5. `AuditFindingLink`: Many-to-many junction linking a `Finding` to an `Audit` and optional `AuditProcedure`.

### 1.2 Existing Service & Endpoints (`AuditEngagementService` & `/api/v1/audits`)
- Engagement CRUD, scope management, procedure management, evidence linking, and finding linking.
- Human-authoritative opinion issuance (`UNQUALIFIED`, `QUALIFIED`, `ADVERSE`, `DISCLAIMER`) with lead auditor SoD.
- Deterministic Audit Readiness score calculation (`procedures_completion * 40% + evidence_coverage * 30% - findings_penalty * 30%`).

### 1.3 Operational Deficiencies in Current State
While the engagement shell exists, **actual audit fieldwork execution cannot currently take place in ControlSphere**:
- **No Document Request Mechanism (PBC)**: Auditors cannot issue formal requests with deadlines to control owners; control owners have no submission portal.
- **No Population Sampling Engine**: Testing recurring control populations (thousands of user access grants, change tickets, background checks) requires manual ad-hoc evidence inspection without documented sampling seeds or methodologies.
- **No Four-Eyes Workpaper Signoff**: Audit procedures lack independent review signoff (`preparer_id != reviewer_id`).
- **No Automated Deficiency Escalation**: Sample testing failures cannot be escalated directly into formal findings.

---

## 2. Existing Authority Matrix

| Domain Engine | Existing Authority Model | Authority Owner | Interaction with Batch 1 | Anti-Duplication Boundary |
| :--- | :--- | :--- | :--- | :--- |
| **Audit Engagements** | `Audit`, `AuditProcedure` | `AuditEngagementService` | Extended with PBC, Sampling & Workpapers | Bounded to single audit domain |
| **Controls** | `OrganizationControl` | `ControlService` | Anchor for PBC requests and sample tests | Reused via foreign keys |
| **Evidence Management**| `EvidenceItem` | `EvidenceService` | PBC fulfillment creates `EvidenceItem` | **Sole evidence storage authority** |
| **Findings** | `Finding` | `FindingService` | Sample exceptions escalate into `Finding` | **Sole finding authority** |
| **Qualitative Risk** | `Risk` | `RiskService` | Findings inform residual risk | No duplicate risk engine |
| **Remediation** | `RemediationPlan` | `RemediationService` | Findings trigger remediation plans | No duplicate CAPA engine |
| **Audit Logging** | `AuditLog` | `AuditService` | Logs all PBC and Workpaper actions | Immutable event logging |

---

## 3. Capability Dependency Map

```
                               ┌────────────────────────────────────────────────────────┐
                               │                    AUDIT ENGAGEMENT                    │
                               │                        (Audit)                         │
                               └───────────────────────────┬────────────────────────────┘
                                                           │
                                ┌──────────────────────────┴──────────────────────────┐
                                ▼                                                     ▼
                  ┌───────────────────────────┐                         ┌───────────────────────────┐
                  │    AuditScopeControl      │                         │      AuditProcedure       │
                  │ (in-scope controls/tests) │                         │   (testing procedures)    │
                  └─────────────┬─────────────┘                         └─────────────┬─────────────┘
                                │                                                     │
               ┌────────────────┴────────────────┐                   ┌────────────────┴────────────────┐
               ▼                                 ▼                   ▼                                 ▼
┌─────────────────────────────┐   ┌─────────────────────────────┐   ┌─────────────────────────────┐   ┌─────────────────────────────┐
│       AuditPBCRequest       │   │    AuditSamplePopulation    │   │       AuditWorkpaper        │   │    AuditReadinessService    │
│  (Cap B: Evidence Request)  │   │   (Cap C: Sampling Engine)  │   │   (Cap A/E: Four-Eyes Sign) │   │   (Cap F: Readiness Score)  │
└──────────────┬──────────────┘   └──────────────┬──────────────┘   └──────────────┬──────────────┘   └─────────────────────────────┘
               │ fulfills                        │ samples                         │ reviews
               ▼                                 ▼                                 ▼
┌─────────────────────────────┐   ┌─────────────────────────────┐   ┌─────────────────────────────┐
│        EvidenceItem         │   │       AuditSampleItem       │   │     AuditProcedureReview    │
│     (Phase 3 Authority)     │   │     (Individual Tests)      │   │  (preparer_id!=reviewer_id) │
└─────────────────────────────┘   └──────────────┬──────────────┘   └─────────────────────────────┘
                                                 │ fails (Cap D)
                                                 ▼
                                  ┌─────────────────────────────┐
                                  │           Finding           │
                                  │     (Phase 4 Authority)     │
                                  └─────────────────────────────┘
```

---

## 4. Evidence Authority Boundary

### 4.1 Strict Invariant: No "AuditEvidence" Duplicate Engine
ControlSphere strictly maintains **one authoritative Evidence engine**: Phase 3 [`EvidenceItem`](file:///E:/PROJECT%20WORKSPACE%202/ControlSphere/backend/app/models/evidence.py).

### 4.2 PBC Fulfillment Lineage Trace
1. Auditor creates an `AuditPBCRequest` specifying required documentation, `organization_control_id`, `procedure_id`, `assigned_to_id`, and `due_date`.
2. Auditee uploads requested documentation via `POST /api/v1/audits/{audit_id}/pbc-requests/{pbc_id}/fulfill`.
3. The fulfillment handler creates an authoritative `EvidenceItem`:
   - `organization_id = current_user.organization_id`
   - `organization_control_id = pbc_request.organization_control_id`
   - `uploaded_by_id = current_user.id`
   - `sha256_hash = canonical_file_hash`
   - `status = EvidenceStatusEnum.UPLOADED` (strict invariant: never auto-accepted)
   - `original_filename`, `storage_key`, `file_size`
4. The PBC request stores `fulfilled_evidence_id = evidence_item.id`.
5. An `AuditProcedureEvidence` record is automatically linked.
6. The auditor reviews the PBC request:
   - `ACCEPTED`: Status becomes `ACCEPTED`, records `reviewed_by_id` and `reviewed_at`.
   - `REJECTED`: Status becomes `REJECTED`, records `auditor_feedback`, allowing auditee re-submission.

---

## 5. Finding Authority Boundary

### 5.1 Strict Invariant: No "AuditFinding" Duplicate Engine
ControlSphere strictly maintains **one authoritative Finding engine**: Phase 4 [`Finding`](file:///E:/PROJECT%20WORKSPACE%202/ControlSphere/backend/app/models/finding.py).

### 5.2 Audit Observation $\rightarrow$ Finding Escalation Trace
1. When an auditor evaluates an `AuditSampleItem` or executes an `AuditProcedure`, an exception or failure is detected (`SampleItemResultEnum.FAIL` or `ProcedureResultEnum.FAILED`).
2. The auditor initiates deficiency escalation via `POST /api/v1/audits/{audit_id}/procedures/{proc_id}/samples/{sample_id}/escalate-finding`.
3. The handler invokes `FindingService.create_finding()`:
   - `organization_id = current_user.organization_id`
   - `organization_control_id = procedure.organization_control_id`
   - `title = f"Audit Deficiency: {procedure.title} - Sample {sample_item.item_identifier}"`
   - `description = f"Sample item {sample_item.item_identifier} failed testing attributes. {sample_item.testing_notes}"`
   - `finding_type = FindingTypeEnum.CONTROL_GAP`
   - `severity = requested_severity` (validated)
   - `status = FindingStatusEnum.OPEN`
4. Automatically creates an `AuditFindingLink(audit_id=audit_id, finding_id=finding.id, source_procedure_id=procedure.id)`.
5. Links `sample_item.deficiency_finding_id = finding.id`.

---

## 6. Sampling Architecture (AICPA AU-C 530 / PCAOB AS 2315)

### 6.1 Deterministic & Auditable Engine
Audit sampling must be 100% reproducible by independent third-party regulators. The sampling algorithm is implemented entirely on the backend and uses a recorded cryptographic seed:

```python
seed_string = f"{audit_id}:{procedure_id}:{population_id}:{total_count}:{sample_size}:{created_at.isoformat()}"
seed_hash = hashlib.sha256(seed_string.encode("utf-8")).hexdigest()
# Integer seed derived deterministically from hex prefix
prng_seed = int(seed_hash[:16], 16)
rng = random.Random(prng_seed)
```

### 6.2 Supported Methodologies
1. **`RANDOM` (Simple Random Sampling)**:
   - Uses `rng.sample(range(1, total_count + 1), sample_size)`.
   - Every item in the population has an equal selection probability.
2. **`SYSTEMATIC` (Interval Sampling)**:
   - Sampling interval $k = \lfloor N / n \rfloor$.
   - Random start point $r \in [1, k]$ chosen via `rng.randint(1, k)`.
   - Sequence: $r, r+k, r+2k, \dots, r+(n-1)k$.
3. **`STRATIFIED` (Stratified Random Sampling)**:
   - Population is divided into distinct non-overlapping strata (e.g., Tier 1 Critical vs Tier 2 Standard).
   - Random sampling is performed proportionally within each stratum.

### 6.3 Sample Item Testing Attributes
- Each generated sample receives a record: `AuditSampleItem`.
- Attributes: `item_identifier` (e.g. `EMP-1082`, `PR-5541`), `item_index` (1 to $n$), `item_attributes` (JSON), `test_result` (`PENDING`, `PASS`, `FAIL`, `EXCEPTION`, `NOT_APPLICABLE`), `testing_notes`, `evidence_item_id`.
- Sample summary telemetry: `total_samples`, `tested_count`, `pass_count`, `fail_count`, `exception_rate = round(fail_count / tested_count * 100, 2)`.

---

## 7. Workpaper Architecture & Four-Eyes Governance

### 7.1 Lifecycle State Machine
```
[DRAFT] ──(preparer submits)──► [SUBMITTED_FOR_REVIEW] ──(reviewer approves)──► [REVIEWED_APPROVED]
                                        │
                               (reviewer rejects)
                                        │
                                        ▼
                              [CHANGES_REQUESTED]
                                        │
                              (preparer updates)
                                        │
                                        ▼
                             [SUBMITTED_FOR_REVIEW]
```

### 7.2 Strict Four-Eyes Separation of Duties
- **Preparer (`prepared_by_id`)**: The staff/senior auditor who documented the testing steps, evaluated sample items, and formulated the preliminary conclusion.
- **Reviewer (`reviewed_by_id`)**: The lead auditor or audit manager who independently inspects the workpaper.
- **Strict Invariant**:
  ```python
  if workpaper.prepared_by_id == current_user_id:
      raise ValueError("Four-Eyes SoD Violation: Workpaper preparer cannot review or approve their own workpaper.")
  ```
- **Permission Boundary**: Preparation requires `AUDIT_EXECUTE`; Review requires `AUDIT_APPROVE` (restricted to `ADMIN`, `AUDITOR` Lead, and `MANAGER`).

### 7.3 Tamper-Evident Workpaper Hash
Upon moving to `REVIEWED_APPROVED`, the system computes a SHA-256 digest over:
`canonical_json({audit_id, procedure_id, preparer_id, prepared_at, reviewer_id, reviewed_at, conclusion, sample_summary})`.
Stored in `workpaper.workpaper_hash_sha256`. Once approved, the workpaper and its linked sample items become strictly immutable.

---

## 8. PBC (Provided By Client) Architecture

### 8.1 PBC Lifecycle States
```
[REQUESTED] ──(auditee uploads)──► [SUBMITTED] ──(auditor accepts)──► [ACCEPTED]
     │                                    │
(cancelled)                       (auditor rejects)
     │                                    │
     ▼                                    ▼
[CANCELLED]                          [REJECTED]
                                          │
                                  (auditee re-uploads)
                                          │
                                          ▼
                                     [SUBMITTED]
```

### 8.2 Operational Safeguards
- **Tenant Boundary**: Auditees can only view and fulfill PBC requests belonging to their authenticated `organization_id`.
- **Auditor Independence**: An auditee cannot accept their own PBC request (`assigned_to_id != reviewed_by_id`).
- **Deadline Monitoring**: Automatically detects overdue requests (`due_date < current_date` while status is not `ACCEPTED` or `CANCELLED`).

---

## 9. Audit Readiness Architecture Enhancements

The existing `AuditEngagementService.get_audit_readiness()` is extended with Batch 1 metrics without creating a duplicate engine:

```python
# Extended Readiness Breakdown
readiness_metrics = {
    # 1. Existing procedure completion (30%)
    "procedure_score": proc_completed / proc_total * 100,
    # 2. Existing evidence coverage (20%)
    "evidence_coverage_score": controls_with_evidence / controls_in_scope * 100,
    # 3. Batch 1: PBC Fulfillment Rate (25%)
    "pbc_score": pbc_accepted / pbc_total * 100 if pbc_total > 0 else 100.0,
    # 4. Batch 1: Workpaper Signoff Rate (25%)
    "workpaper_score": workpapers_approved / workpapers_total * 100 if workpapers_total > 0 else 100.0,
    # Penalties
    "findings_penalty": (critical_high * 5.0) + (findings_open * 2.0),
    "pbc_overdue_penalty": pbc_overdue_count * 3.0,
    "sample_exception_penalty": total_sample_exceptions * 4.0,
}
```

---

## 10. Batch Boundary Analysis

### Option 1: One Integrated Batch (`BATCH 1 — AUDIT FIELDWORK GOVERNANCE`)
- **Architectural Coupling**: Extremely high. Capabilities A through F share the exact same domain entities (`audits`, `audit_procedures`), foreign keys, and execution workflow.
- **Migration Coupling**: Single clean migration (`0022_audit_fieldwork_and_sampling.py`).
- **Security Coupling**: Unified Four-Eyes security model across workpapers and PBC reviews.
- **Test Coupling**: Tests form a complete audit story: Create Audit $\rightarrow$ Issue PBC $\rightarrow$ Fulfill with Evidence $\rightarrow$ Generate Samples $\rightarrow$ Test Samples $\rightarrow$ Sign Off Workpaper $\rightarrow$ Check Readiness.
- **Frontend Coupling**: Single update to `AuditDetailPage.tsx` providing tabs for Scope, Procedures, PBC Requests, Sampling Lab, and Workpaper Signoff.
- **Productivity Benefit**: Maximum. Delivers the entire audit execution stack in one coherent block, avoiding fragmented context switches.

### Option 2: Two Related Batches (Batch 1A: PBC; Batch 1B: Sampling & Workpapers)
- **Architectural Coupling**: Artificial split. Auditors issue PBC requests specifically to populate sample populations and test procedures.
- **Migration Coupling**: Requires two migrations (`0022` and `0023`), altering `audit_procedures` twice.
- **Frontend Coupling**: Incomplete UI in Batch 1A, forcing rework of `AuditDetailPage.tsx` in Batch 1B.
- **Productivity Impact**: Unnecessary overhead; duplicates review gates and verification cycles.

### Option 3: Three or More Batches
- **Architectural Coupling**: Severe fragmentation of a single operational domain.
- **Rollback Complexity**: High migration dependency chain.
- **Productivity Impact**: Lowest efficiency.

### Verdict on Boundary: **OPTION 1 IS STRONGLY RECOMMENDED**.

---

## 11. Recommended Batch: `BATCH 1 — AUDIT FIELDWORK GOVERNANCE`

### 11.1 Included Capabilities
- **Phase 25A**: PBC Request Management (Issuance, Auditee Fulfillment, Document Attachment, Review Workflow).
- **Phase 25B**: Audit Sampling Engine (Random, Systematic, Stratified, Deterministic Seed, Sample Item Testing).
- **Phase 25C**: Workpaper Execution & Four-Eyes Signoff (Preparer / Reviewer SoD, Cryptographic Workpaper Digest).
- **Phase 25D**: Audit Sample Exception $\rightarrow$ Finding Escalation Bridge.
- **Phase 25E**: Enhanced Audit Readiness Telemetry (PBC, Sample, and Workpaper Progress).

### 11.2 Explicitly Excluded Capabilities (Reserved for Future Batches)
- Continuous Control Monitoring rules (Already authoritative in Phase 7).
- Key Risk Indicators & Risk Appetite (Reserved for Batch 2).
- Third-Party Vendor Audits (Already authoritative in Phase 9).
- Automated AI Audit Procedures (Reserved for future AI tooling).

### 11.3 Migration Plan
- **Migration File**: `backend/alembic/versions/0022_audit_fieldwork_and_sampling.py`
- **Revises**: `0021`
- **Tables Created**:
  1. `audit_pbc_requests`
  2. `audit_sample_populations`
  3. `audit_sample_items`
  4. `audit_workpaper_reviews`
- **Table Alterations**:
  - `audit_procedures`: Add `has_sampling: Boolean = False`, `workpaper_status: String = "DRAFT"`.

---

## 12. Security & Permission Model

### 12.1 Permissions
- `AUDIT_FIELDWORK_MANAGE`: Create/edit PBC requests, configure sample populations (`ADMIN`, `AUDITOR`, `MANAGER`).
- `AUDIT_PBC_RESPOND`: Fulfill PBC requests with evidence uploads (`ADMIN`, `MANAGER`, `GRC_ANALYST`, `SECURITY_ANALYST`, `VIEWER` assigned).
- `AUDIT_SAMPLE_TEST`: Evaluate sample items, record pass/fail (`ADMIN`, `AUDITOR`).
- `AUDIT_WORKPAPER_PREPARE`: Submit workpapers for review (`ADMIN`, `AUDITOR`).
- `AUDIT_WORKPAPER_APPROVE`: Approve/sign off workpapers (`ADMIN`, `AUDITOR` Lead, `MANAGER`).

### 12.2 Four-Eyes Separation
`prepared_by_id != reviewed_by_id` enforced in service layer with HTTP 400 rejection.

---

## 13. Test Architecture Plan

Anticipated Test Matrix: **~42 tests**:
1. **Multi-Tenant Isolation & IDOR** (8 tests)
2. **PBC Request Lifecycle & Fulfillment** (8 tests)
3. **Deterministic Sampling Engine & Seeds** (8 tests)
4. **Sample Item Evaluation & Status Transitions** (6 tests)
5. **Workpaper Four-Eyes Signoff & SoD** (6 tests)
6. **Deficiency $\rightarrow$ Finding Escalation Bridge** (4 tests)
7. **Audit Readiness Calculation** (2 tests)

---

## 14. Future Batch Roadmap

| Batch | Code Name | Capabilities Included | Authoritative Anchor |
| :--- | :--- | :--- | :--- |
| **Batch 1** | **`AUDIT-FIELDWORK-GRC`** | PBC Requests, Statistical Sampling, Workpaper Signoffs, Deficiency Escalation | Phase 6 (`Audit`) & Phase 3 (`Evidence`) |
| **Batch 2** | **`KRI-APPETITE-GRC`** | Key Risk Indicators, Metric Telemetry, Risk Appetite Thresholds, Breach Alerts | Phase 5 (`Risk`) & Phase 12 (`QuantRisk`) |
| **Batch 3** | **`DATA-GOVERNANCE-GRC`** | Data Asset Catalog, Classification Schemas, Sensitivity Lineage, Jurisdiction Rules | Phase 16 (`Privacy`) & Phase 18 (`CloudSec`) |
| **Batch 4** | **`OBLIGATION-TRUST-GRC`** | Contractual Commitments, Customer Security Addendums (CSAs), BAA/DPA Tracking | Phase 21 (`Regulatory`) & Phase 9 (`Vendor`) |
| **Batch 5** | **`ADVANCED-ASSURANCE-GRC`** | Automated Drift Auto-Remediation, Closed-Loop Evidence Scheduling | Phase 22 (`Integration`) & Phase 23 (`Continuous`) |

---

## 15. Architecture Gate Verdict

# **GO — BATCH READY FOR HARDENING**
