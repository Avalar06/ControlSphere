# ControlSphere — Batch 1 Architecture Hardening Specification

**Document Identifier**: `PHASE25_BATCH_ARCHITECTURE_HARDENED.md`
**Batch Identifier**: `BATCH-1-AUDIT-FIELDWORK`
**Module Name**: `AUDIT-FIELDWORK-GRC`
**Target Migration**: `0022_audit_fieldwork_and_sampling.py`
**Alembic Head Baseline**: `0021 (head)`
**Git Baseline**: Commit `8b8b482d98e8d74a4807f490c0219b9b9eefa564` (main, clean, pushed)
**Security Model**: Production Enterprise RBAC (Exact 6 Platform Roles, Zero Role Inflation)
**Four-Eyes Model**: Hard Enforcement (`actor_a != actor_b` via server-authoritative token context)
**Cryptographic Integrity**: SHA-256 Digest over Canonical JSON Serialization
**Compliance Standards**: AICPA AU-C Section 530 (*Audit Sampling*), PCAOB AS 2315 (*Audit Sampling*), IIA Standard 2300 (*Performing the Engagement*)
**Architecture Gate Status**: **GO — BATCH READY FOR IMPLEMENTATION**

---

## 1. Executive Summary

Batch 1 (`AUDIT-FIELDWORK-GRC`) bridges the critical operational gap between the engagement shell created in Phase 6 (`Audit`, `AuditProcedure`, `AuditScopeControl`) and real-world audit fieldwork execution. In enterprise GRC environments, an audit engagement cannot proceed merely by logging descriptive test steps and manually issuing high-level opinions. Fieldwork requires:
1. **Governed Document Request Workflows (PBC)**: Formal issuance, auditee fulfillment, and auditor acceptance/rejection of audit artifacts.
2. **Deterministic & Auditable Population Sampling**: Strict adherence to AICPA AU-C 530 and PCAOB AS 2315 via server-controlled cryptographic seeds, deterministic pseudo-random generators, immutable population snapshots, and canonical ordering.
3. **Four-Eyes Workpaper Signoff**: Strict segregation of duties (`prepared_by_id != reviewed_by_id`) with immutable SHA-256 workpaper digests.
4. **Automated Deficiency Escalation**: Direct conversion of sample exceptions into authoritative Phase 4 `Finding` records without intermediate data silos.
5. **Dynamic Audit Readiness Telemetry**: Live metric derivation measuring PBC turnaround, workpaper signoffs, and sample failure penalties.

This hardened architecture document provides the definitive, mathematically sound, tamper-resistant blueprint for Batch 1. It enforces strict multi-tenant boundaries, non-repudiation logging, and zero duplicate domain engines.

---

## 2. Repository Ground Truth & Verified Baseline

All specifications in this document are derived directly from the authoritative repository state as inspected on the local file system and remote tracking branch:

| Attribute | Verified Ground Truth | Evidence Source |
| :--- | :--- | :--- |
| **Repository Remote** | `https://github.com/Avalar06/ControlSphere.git` | `git remote -v` |
| **Active Branch** | `main` (synchronized with `origin/main`) | `git status` |
| **Git HEAD Commit** | `8b8b482d98e8d74a4807f490c0219b9b9eefa564` | `git rev-parse HEAD` |
| **Commit Message** | `feat(phase24): implement policy lifecycle and workforce attestation governance` | `git log -1 --oneline` |
| **Working Tree** | Clean (Zero uncommitted code changes, zero unstaged code modifications) | `git status --short` |
| **Alembic Revision Head** | `0021` (`0021_policy_lifecycle_and_attestation.py`) | `backend/alembic/versions/` |
| **Backend Test Baseline** | **965 / 965 Passing Tests (100% Pass Rate)** | `pytest` suite execution |
| **Platform Roles** | Exactly 6: `ADMIN`, `MANAGER`, `GRC_ANALYST`, `SECURITY_ANALYST`, `AUDITOR`, `VIEWER` | `backend/app/models/user.py` |
| **Next Target Migration** | `0022_audit_fieldwork_and_sampling.py` (Revises: `0021`) | Alembic migration sequence |

---

## 3. Batch Boundary Decision

### Decision: **KEEP AS ONE INTEGRATED BATCH (`BATCH 1 — AUDIT FIELDWORK GOVERNANCE`)**

A rigorous coupling analysis of the ControlSphere repository confirms that splitting the fieldwork scope into separate sub-batches (e.g., Batch 1A: PBC, Batch 1B: Sampling, Batch 1C: Workpapers) introduces artificial boundaries, database schema churn, and broken intermediate user experiences:

```
                            ┌─────────────────────────────────────────────────────────┐
                            │               AUDIT ENGAGEMENT (Phase 6)                │
                            │                      Table: audits                      │
                            └────────────────────────────┬────────────────────────────┘
                                                         │
                                  ┌──────────────────────┴──────────────────────┐
                                  ▼                                             ▼
                   ┌───────────────────────────────┐             ┌───────────────────────────────┐
                   │       AuditScopeControl       │             │        AuditProcedure         │
                   │ table: audit_scope_controls   │             │   table: audit_procedures     │
                   └──────────────┬────────────────┘             └──────────────┬────────────────┘
                                  │                                             │
               ┌──────────────────┴──────────────────┐          ┌───────────────┴───────────────┐
               ▼                                     ▼          ▼                               ▼
┌───────────────────────────────┐     ┌─────────────────────────────────┐     ┌─────────────────────────────────┐
│        AuditPBCRequest        │     │      AuditSamplePopulation      │     │         AuditWorkpaper          │
│  table: audit_pbc_requests    │     │ table: audit_sample_populations │     │  table: audit_workpaper_reviews │
└──────────────┬────────────────┘     └─────────────────┬───────────────┘     └─────────────────┬───────────────┘
               │ fulfills                               │ generates                             │ reviews & signs
               ▼                                        ▼                                       ▼
┌───────────────────────────────┐     ┌─────────────────────────────────┐     ┌─────────────────────────────────┐
│         EvidenceItem          │     │         AuditSampleItem         │     │     SHA-256 Workpaper Hash      │
│     (Phase 3 Authority)       │     │    table: audit_sample_items    │     │   (Tamper-Evident Digest)       │
└───────────────────────────────┘     └─────────────────┬───────────────┘     └─────────────────────────────────┘
                                                        │ fails & escalates
                                                        ▼
                                      ┌─────────────────────────────────┐
                                      │             Finding             │
                                      │       (Phase 4 Authority)       │
                                      └─────────────────────────────────┘
```

#### Factual Reasons for Keeping One Integrated Batch:
1. **Shared Database Foreign Key Graph**: `AuditPBCRequest`, `AuditSamplePopulation`, and `AuditWorkpaperReview` all share identical foreign keys pointing to `(audit_id, organization_id)` and `(procedure_id, organization_id)`. Splitting into sub-batches would require modifying `audit_procedures` in migration `0022`, then modifying it again in `0023`, creating unnecessary schema churn.
2. **Operational Workflow Atomicity**: An auditor cannot test a control procedure without sample items; sample items cannot be tested without PBC evidence requests; testing cannot conclude without four-eyes workpaper signoff; and readiness cannot be reported without sample exception metrics. Splitting them breaks the single end-to-end fieldwork lifecycle.
3. **Frontend Cohesion (`AuditDetailPage.tsx`)**: In `AuditDetailPage.tsx`, tabs for Scope, Procedures, PBC Requests, Sampling Lab, and Workpapers form a unified analyst workspace. Delivering them piecemeal would result in a fragmented UI with dead-end user flows.
4. **Single Deterministic Migration**: A single clean migration (`0022_audit_fieldwork_and_sampling.py`) creates the 4 fieldwork tables and adds 2 metadata columns to `audit_procedures`, ensuring an atomic, fully reversible schema change.

---

## 4. Current Phase 6 Gap Analysis

While Phase 6 introduced the core audit entities, fieldwork execution is currently blocked by four critical operational deficiencies:

| Functional Area | Current State (Phase 6) | Operational Defect | Batch 1 Hardened Solution |
| :--- | :--- | :--- | :--- |
| **Evidence Request (PBC)** | None. Ad-hoc evidence linking via `AuditProcedureEvidence`. | Auditors cannot issue formal requests with due dates; auditees have no submission queue; evidence status is unmanaged. | `AuditPBCRequest` with lifecycle (`REQUESTED` $\rightarrow$ `SUBMITTED` $\rightarrow$ `ACCEPTED`/`REJECTED`), auditee fulfillment, and auto-linking to `EvidenceItem`. |
| **Population Sampling** | None. Ad-hoc procedure testing notes. | Cannot test recurring controls (e.g. 5,000 access grants or 200 change tickets) with auditable statistical validity; zero reproducibility. | Deterministic `AuditSamplePopulation` and `AuditSampleItem` engine adhering to AU-C 530 / PCAOB AS 2315 with SHA-256 seeds and frozen populations. |
| **Workpaper Signoff** | `AuditProcedure.tester_id` recorded without independent review. | Violates IIA Standard 2300 and Sarbanes-Oxley; no segregation of duties between the auditor executing the test and the reviewer approving it. | `AuditWorkpaperReview` with strict Four-Eyes SoD (`prepared_by_id != reviewed_by_id`) and tamper-evident SHA-256 workpaper hash. |
| **Deficiency Escalation** | Manual `AuditFindingLink` linking existing findings. | Failed sample items require manual duplicate data entry in the Findings module with broken traceability to the originating sample item. | Direct escalation from `AuditSampleItem` (`FAIL`) into Phase 4 `Finding` (`CONTROL_GAP`) with bidirectional foreign key traceability. |
| **Readiness Telemetry** | Simple ratio: `proc_score * 0.4 + evidence_score * 0.3 - finding_penalty`. | Ignores overdue PBC requests, un-reviewed workpapers, and sample exception rates. | Live enhanced formula in `AuditEngagementService.get_readiness()` incorporating PBC fulfillment (25%) and workpaper approvals (25%). |

---

## 5. Authoritative Domain Engine Matrix

ControlSphere adheres strictly to single-domain authority. Batch 1 introduces **zero duplicate engines**:

| Domain Capability | Authoritative Engine / Model | Owner Service | Interaction with Batch 1 | Prohibited Duplicate Pattern |
| :--- | :--- | :--- | :--- | :--- |
| **Audit Engagement** | `Audit`, `AuditProcedure` | `AuditEngagementService` | Extended with PBC, Sampling, and Workpaper child tables. | Prohibited: Creating `Audit2` or an external fieldwork micro-service. |
| **Evidence Management** | `EvidenceItem`, `EvidenceReview` | `EvidenceService` | Auditee fulfills PBC requests by creating standard `EvidenceItem` records. | Prohibited: Creating `AuditEvidence` or duplicate file storage tables. |
| **Findings & Deficiencies** | `Finding`, `FindingEvidence` | `FindingService` | Sample failures invoke `FindingService.create_finding()` to instantiate formal findings. | Prohibited: Creating `AuditDeficiency` or `AuditFinding` duplicate tables. |
| **Control Authority** | `OrganizationControl` | `ControlService` | Controls anchor PBC requests, sample populations, and procedure scopes. | Prohibited: Storing ad-hoc control text detached from `OrganizationControl`. |
| **Audit Logging** | `AuditLog` | `AuditService` | All fieldwork actions (freeze, sample, fulfill, approve) record structured events. | Prohibited: Creating a separate `FieldworkLog` table. |

---

## 6. Concrete Domain Model & Schema Specifications

The schema additions for Batch 1 are encapsulated in `backend/alembic/versions/0022_audit_fieldwork_and_sampling.py`:

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                            AuditPBCRequest                                             │
├────────────────────────────┬────────────────────────────┬───────────┬──────────────────────────────────┤
│ Column                     │ Type                       │ Nullable  │ Constraints / Indexes            │
├────────────────────────────┼────────────────────────────┼───────────┼──────────────────────────────────┤
│ id                         │ Integer                    │ False     │ PK, autoincrement                │
│ organization_id            │ Integer                    │ False     │ FK(organizations.id, CASCADE), IX│
│ audit_id                   │ Integer                    │ False     │ FK(audits.id, CASCADE), IX       │
│ procedure_id               │ Integer                    │ True      │ FK(audit_procedures.id, SET NULL)│
│ organization_control_id    │ Integer                    │ False     │ FK(organization_controls.id), IX │
│ request_identifier         │ String(50)                 │ False     │ IX (e.g., "PBC-2026-001")        │
│ title                      │ String(255)                │ False     │                                  │
│ description                │ Text                       │ False     │ Required request instructions    │
│ status                     │ Enum(PBCStatusEnum)        │ False     │ IX, default: REQUESTED           │
│ priority                   │ Enum(PBCPriorityEnum)      │ False     │ default: MEDIUM                  │
│ assigned_to_id             │ Integer                    │ True      │ FK(users.id, SET NULL), IX       │
│ due_date                   │ Date                       │ False     │ IX                               │
│ fulfilled_evidence_id      │ Integer                    │ True      │ FK(evidence_items.id, SET NULL)  │
│ submission_notes           │ Text                       │ True      │ Auditee notes upon submission    │
│ submitted_at               │ DateTime(timezone=True)    │ True      │ Recorded on submission           │
│ reviewed_by_id             │ Integer                    │ True      │ FK(users.id, SET NULL)           │
│ reviewed_at                │ DateTime(timezone=True)    │ True      │ Recorded on accept/reject        │
│ rejection_reason           │ Text                       │ True      │ Auditor feedback on rejection    │
│ created_by_id              │ Integer                    │ True      │ FK(users.id, SET NULL)           │
│ created_at                 │ DateTime(timezone=True)    │ False     │ default: utcnow                  │
│ updated_at                 │ DateTime(timezone=True)    │ False     │ default: utcnow, onupdate        │
└────────────────────────────┴────────────────────────────┴───────────┴──────────────────────────────────┘
Unique Constraint: uq_pbc_org_identifier ("organization_id", "request_identifier")
```

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                         AuditSamplePopulation                                          │
├────────────────────────────┬────────────────────────────┬───────────┬──────────────────────────────────┤
│ Column                     │ Type                       │ Nullable  │ Constraints / Indexes            │
├────────────────────────────┼────────────────────────────┼───────────┼──────────────────────────────────┤
│ id                         │ Integer                    │ False     │ PK, autoincrement                │
│ organization_id            │ Integer                    │ False     │ FK(organizations.id, CASCADE), IX│
│ audit_id                   │ Integer                    │ False     │ FK(audits.id, CASCADE), IX       │
│ procedure_id               │ Integer                    │ False     │ FK(audit_procedures.id, CASCADE) │
│ population_name            │ String(255)                │ False     │ Descriptive label                │
│ description                │ Text                       │ True      │ Population source criteria       │
│ population_source          │ String(255)                │ False     │ e.g. "Okta Audit Logs Q1"        │
│ total_count                │ Integer                    │ False     │ Must be >= 1                     │
│ version_number             │ Integer                    │ False     │ default: 1                       │
│ is_frozen                  │ Boolean                    │ False     │ default: False, IX               │
│ frozen_at                  │ DateTime(timezone=True)    │ True      │ Timestamp when frozen            │
│ frozen_by_id               │ Integer                    │ True      │ FK(users.id, SET NULL)           │
│ population_digest_sha256   │ String(64)                 │ True      │ SHA-256 of canonical items data  │
│ sampling_method            │ Enum(SamplingMethodEnum)   │ False     │ RANDOM, SYSTEMATIC, STRATIFIED   │
│ sampling_seed              │ String(64)                 │ True      │ Server-generated PRNG seed       │
│ sample_size                │ Integer                    │ False     │ Calculated sample count (1..N)   │
│ sample_parameters_json     │ Text                       │ True      │ Methodology parameters (JSON)    │
│ samples_generated          │ Boolean                    │ False     │ default: False                   │
│ generated_at               │ DateTime(timezone=True)    │ True      │ Timestamp of sample extraction   │
│ created_by_id              │ Integer                    │ True      │ FK(users.id, SET NULL)           │
│ created_at                 │ DateTime(timezone=True)    │ False     │ default: utcnow                  │
│ updated_at                 │ DateTime(timezone=True)    │ False     │ default: utcnow, onupdate        │
└────────────────────────────┴────────────────────────────┴───────────┴──────────────────────────────────┘
Unique Constraint: uq_population_proc_version ("procedure_id", "version_number")
```

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                            AuditSampleItem                                             │
├────────────────────────────┬────────────────────────────┬───────────┬──────────────────────────────────┤
│ Column                     │ Type                       │ Nullable  │ Constraints / Indexes            │
├────────────────────────────┼────────────────────────────┼───────────┼──────────────────────────────────┤
│ id                         │ Integer                    │ False     │ PK, autoincrement                │
│ organization_id            │ Integer                    │ False     │ FK(organizations.id, CASCADE), IX│
│ population_id              │ Integer                    │ False     │ FK(audit_sample_populations.id)  │
│ item_index                 │ Integer                    │ False     │ 1-indexed position in sample     │
│ source_record_id           │ String(255)                │ False     │ External business key / ID       │
│ item_attributes_json       │ Text                       │ False     │ Canonical JSON record attributes │
│ test_result                │ Enum(SampleResultEnum)     │ False     │ IX, default: PENDING             │
│ testing_notes              │ Text                       │ True      │ Fieldwork evaluation notes       │
│ tested_by_id               │ Integer                    │ True      │ FK(users.id, SET NULL)           │
│ tested_at                  │ DateTime(timezone=True)    │ True      │ Timestamp of testing             │
│ evidence_item_id           │ Integer                    │ True      │ FK(evidence_items.id, SET NULL)  │
│ deficiency_finding_id      │ Integer                    │ True      │ FK(findings.id, SET NULL), IX    │
│ created_at                 │ DateTime(timezone=True)    │ False     │ default: utcnow                  │
│ updated_at                 │ DateTime(timezone=True)    │ False     │ default: utcnow, onupdate        │
└────────────────────────────┴────────────────────────────┴───────────┴──────────────────────────────────┘
Unique Constraint: uq_sample_pop_item ("population_id", "item_index")
```

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                         AuditWorkpaperReview                                           │
├────────────────────────────┬────────────────────────────┬───────────┬──────────────────────────────────┤
│ Column                     │ Type                       │ Nullable  │ Constraints / Indexes            │
├────────────────────────────┼────────────────────────────┼───────────┼──────────────────────────────────┤
│ id                         │ Integer                    │ False     │ PK, autoincrement                │
│ organization_id            │ Integer                    │ False     │ FK(organizations.id, CASCADE), IX│
│ audit_id                   │ Integer                    │ False     │ FK(audits.id, CASCADE), IX       │
│ procedure_id               │ Integer                    │ False     │ FK(audit_procedures.id, CASCADE) │
│ version_number             │ Integer                    │ False     │ default: 1                       │
│ status                     │ Enum(WorkpaperStatusEnum)  │ False     │ IX, default: DRAFT               │
│ testing_summary            │ Text                       │ False     │ Summary of fieldwork performed   │
│ conclusion                 │ Text                       │ False     │ Auditor evaluation & conclusion  │
│ prepared_by_id             │ Integer                    │ False     │ FK(users.id, RESTRICT), IX       │
│ prepared_at                │ DateTime(timezone=True)    │ False     │ Timestamp submitted for review   │
│ reviewed_by_id             │ Integer                    │ True      │ FK(users.id, RESTRICT), IX       │
│ reviewed_at                │ DateTime(timezone=True)    │ True      │ Timestamp reviewed               │
│ review_notes               │ Text                       │ True      │ Reviewer comments / feedback     │
│ rejection_reason           │ Text                       │ True      │ Populated if changes requested   │
│ workpaper_hash_sha256      │ String(64)                 │ True      │ SHA-256 digest upon approval     │
│ created_at                 │ DateTime(timezone=True)    │ False     │ default: utcnow                  │
│ updated_at                 │ DateTime(timezone=True)    │ False     │ default: utcnow, onupdate        │
└────────────────────────────┴────────────────────────────┴───────────┴──────────────────────────────────┘
Unique Constraint: uq_workpaper_proc_version ("procedure_id", "version_number")
```

#### Alterations to Existing Table `audit_procedures`:
- `has_sampling`: `Boolean`, `nullable=False`, `server_default=sa.text('false')`
- `workpaper_status`: `String(50)`, `nullable=False`, `server_default='DRAFT'`

---

## 7. State Machines & Lifecycle Transitions

### 7.1 PBC Request State Machine
```
   ┌───────────┐
   │ REQUESTED │ ◄─────────────────────────────────────────────┐
   └─────┬─────┘                                               │
         │ (auditee fulfills with EvidenceItem)                │ (auditor rejects,
         ▼                                                     │  requests rework)
   ┌───────────┐                                               │
   │ SUBMITTED │ ──────────────────────────────────────────────┘
   └─────┬─────┘
         │ (auditor accepts)
         ▼
   ┌───────────┐
   │ ACCEPTED  │  (Immutable Terminal State)
   └───────────┘
```
- **REQUESTED $\rightarrow$ SUBMITTED**: Actor must be `assigned_to_id`, `MANAGER`, or `ADMIN`. Attaches `fulfilled_evidence_id` pointing to an authoritative `EvidenceItem` in `UPLOADED` status.
- **SUBMITTED $\rightarrow$ ACCEPTED**: Actor must possess `AUDIT_FIELDWORK_MANAGE` (`AUDITOR`, `MANAGER`, `ADMIN`). **Four-Eyes Invariant**: `reviewer_id != assigned_to_id` (Auditee cannot approve their own submitted evidence).
- **SUBMITTED $\rightarrow$ REQUESTED (Reject / Request Changes)**: Auditor provides mandatory `rejection_reason`. Returns PBC to `REQUESTED` for rework.

### 7.2 Workpaper Four-Eyes State Machine
```
   ┌───────────┐
   │   DRAFT   │ ◄─────────────────────────────────────────────┐
   └─────┬─────┘                                               │
         │ (preparer submits)                                  │ (reviewer requests
         ▼                                                     │  changes)
   ┌────────────────────┐                                      │
   │ SUBMITTED_FOR_     │ ─────────────────────────────────────┘
   │      REVIEW        │
   └─────┬──────────────┘
         │ (reviewer approves)
         ▼
   ┌────────────────────┐
   │ REVIEWED_APPROVED  │  (Immutable Sealed State with SHA-256 Digest)
   └────────────────────┘
```
- **DRAFT $\rightarrow$ SUBMITTED_FOR_REVIEW**: Actor must possess `AUDIT_WORKPAPER_PREPARE`. Sets `prepared_by_id = current_user.id`, `prepared_at = utcnow()`.
- **SUBMITTED_FOR_REVIEW $\rightarrow$ REVIEWED_APPROVED**: Actor must possess `AUDIT_WORKPAPER_APPROVE` (`AUDITOR`, `MANAGER`, `ADMIN`). **Strict Four-Eyes Rule**:
  $$\text{current\_user.id} \neq \text{workpaper.prepared\_by\_id}$$
  Computes and persists `workpaper_hash_sha256`. Workpaper and linked samples become strictly immutable.
- **SUBMITTED_FOR_REVIEW $\rightarrow$ CHANGES_REQUESTED**: Reviewer provides mandatory `rejection_reason`. State returns to `DRAFT` allowing the preparer to remediate testing notes.

---

## 8. Sampling Reproducibility Contract (AICPA AU-C 530 / PCAOB AS 2315)

In accordance with international auditing standards, any sample selected by an auditor must be **100% reproducible by an independent regulatory inspector or peer reviewer** given the recorded population and parameters.

### 8.1 Reproducibility Invariant
A reproduction procedure must yield the exact identical sequence of sample items:
$$\text{Sample}(P, M, \text{Seed}, n) \equiv \text{Sample}(P, M, \text{Seed}, n) \quad \forall \text{ executions}$$

### 8.2 Canonical Ordering Protocol
Before applying any sampling algorithm, the population records must be sorted deterministically. **Database query ordering is strictly prohibited as an ordering authority.**
1. Each population item MUST possess a unique business key (`source_record_id`).
2. Canonical sort order:
   $$\text{Order by: } (\text{source\_record\_id ASC})$$
3. In case of tie, secondary sort:
   $$\text{Order by: } (\text{source\_record\_id ASC}, \text{item\_digest ASC})$$

### 8.3 Cryptographic Seed Construction
The PRNG seed is **server-authoritative**. The client is strictly forbidden from providing or modifying the seed.
$$\text{Seed String} = \text{org\_id} : \text{audit\_id} : \text{procedure\_id} : \text{pop\_id} : \text{total\_count} : \text{sample\_size} : \text{created\_at\_iso}$$
$$\text{sampling\_seed} = \text{SHA-256}(\text{Seed String})$$
The integer PRNG seed is derived from the first 16 hexadecimal characters of the digest:
$$\text{prng\_seed} = \text{int}(\text{sampling\_seed}[0:16], 16)$$

### 8.4 Mathematical Sampling Algorithms (Python Standard Library `random.Random`)
All algorithms utilize an isolated `random.Random(prng_seed)` instance. Global `random` state is never touched.

#### Algorithm 1: `RANDOM` (Simple Random Sampling Without Replacement)
```python
def sample_random(canonical_items: List[dict], sample_size: int, prng_seed: int) -> List[dict]:
    rng = random.Random(prng_seed)
    # Selected indices between 0 and N-1 without replacement
    selected_indices = sorted(rng.sample(range(len(canonical_items)), sample_size))
    return [canonical_items[i] for i in selected_indices]
```

#### Algorithm 2: `SYSTEMATIC` (Fixed Interval Sampling with Random Start)
Given population size $N$ and sample size $n$:
1. Sampling interval $k = \lfloor N / n \rfloor$.
2. Random starting point $r \in [0, k - 1]$ selected via `rng.randint(0, k - 1)`.
3. Sequence of indices:
   $$i_j = r + (j \times k) \quad \text{for } j \in [0, n - 1]$$
```python
def sample_systematic(canonical_items: List[dict], sample_size: int, prng_seed: int) -> List[dict]:
    N = len(canonical_items)
    k = N // sample_size
    rng = random.Random(prng_seed)
    start_r = rng.randint(0, k - 1)
    selected_indices = [start_r + (j * k) for j in range(sample_size)]
    return [canonical_items[i] for i in selected_indices]
```

#### Algorithm 3: `STRATIFIED` (Proportional Stratified Random Sampling)
Given strata $S_1, S_2, \dots, S_m$ where $\sum |S_h| = N$:
1. For each stratum $h$, sample allocation:
   $$n_h = \max\left(1, \operatorname{round}\left(n \times \frac{|S_h|}{N}\right)\right)$$
2. Normalize $\sum n_h = n$ by adjusting the largest stratum.
3. Within each stratum, sort items by `source_record_id ASC`.
4. Derive stratum sub-seed:
   $$\text{sub\_seed}_h = \text{int}(\text{SHA-256}(f"\text{sampling\_seed}:stratum\_\{h\}")[0:16], 16)$$
5. Sample $n_h$ items using `random.Random(sub_seed_h).sample()`.

---

## 9. Population Snapshot & Mutability Contract

To prevent silent invalidation of audit evidence, populations are governed by an **Immutability Contract**:

```
                  ┌────────────────────┐
                  │    DRAFT / OPEN    │
                  └─────────┬──────────┘
                            │ (auditor freezes population)
                            ▼
                  ┌────────────────────┐
                  │       FROZEN       │ ────► Generates Samples (AuditSampleItem)
                  └─────────┬──────────┘
                            │ (population change detected after testing)
                            ▼
                  ┌────────────────────┐
                  │  REGENERATION REQ  │
                  └─────────┬──────────┘
                            │ (creates new version, e.g. v2)
                            ▼
                  ┌────────────────────┐
                  │   POPULATION V2    │ (Prior v1 & samples preserved for audit trail)
                  └────────────────────┘
```

### Invariants:
1. **Freeze Requirement**: Samples CANNOT be generated until the population is formally frozen (`is_frozen = True`, `population_digest_sha256` computed).
2. **Canonical Digest Formula**:
   $$\text{Canonical Items String} = \text{canonical\_json}(\text{sorted}([(\text{item.id}, \text{item.source\_record\_id}, \text{item.digest})]))$$
   $$\text{population\_digest\_sha256} = \text{SHA-256}(\text{Canonical Items String})$$
3. **Zero Silent Invalidation**: If the source data changes after sampling, the existing population snapshot and its tested sample items are **NEVER overwritten or updated in place**.
4. **Regeneration Protocol**: Re-sampling creates a new `AuditSamplePopulation` record with `version_number = previous.version_number + 1`. The prior version is marked historical, retaining complete lineage for external regulators.

---

## 10. PBC $\rightarrow$ Evidence Authority Contract

ControlSphere maintains **one authoritative Evidence engine**: Phase 3 [`EvidenceItem`](file:///E:/PROJECT%20WORKSPACE%202/ControlSphere/backend/app/models/evidence.py).

### Lineage Trace:
```
1. Auditor creates AuditPBCRequest
   ├── organization_control_id = 14
   ├── procedure_id = 8
   └── assigned_to_id = 5 (Auditee)

2. Auditee fulfills via POST /api/v1/audits/{audit_id}/pbc-requests/{pbc_id}/fulfill
   ├── Creates EvidenceItem (Phase 3 Authority)
   │   ├── organization_id = current_user.organization_id
   │   ├── organization_control_id = pbc_request.organization_control_id
   │   ├── status = EvidenceStatusEnum.UPLOADED (Strict: Never auto-accepted)
   │   ├── sha256_hash = canonical_file_hash
   │   └── storage_key = secure_tenant_path
   ├── Updates AuditPBCRequest
   │   ├── fulfilled_evidence_id = EvidenceItem.id
   │   ├── status = PBCStatusEnum.SUBMITTED
   │   └── submitted_at = utcnow()
   └── Creates AuditProcedureEvidence (Junction)
       ├── procedure_id = pbc_request.procedure_id
       └── evidence_id = EvidenceItem.id

3. Auditor reviews PBC via POST /api/v1/audits/{audit_id}/pbc-requests/{pbc_id}/review
   ├── Enforces Four-Eyes: reviewer_id != assigned_to_id
   ├── If ACCEPTED:
   │   ├── AuditPBCRequest.status = ACCEPTED
   │   └── Creates EvidenceReview(decision=ACCEPT, reviewer_id=current_user.id)
   └── If REJECTED:
       ├── AuditPBCRequest.status = REQUESTED (re-opens for auditee)
       ├── AuditPBCRequest.rejection_reason = "Document missing 2026 signatures"
       └── Creates EvidenceReview(decision=REJECT, rejection_reason=...)
```

#### Operational Safeguards:
- **Tenant Boundary**: Auditees can only view and fulfill PBC requests belonging to their authenticated `organization_id`.
- **Replacement / Resubmission**: If rejected, resubmission creates a new `EvidenceItem` and sets `superseded_by_id` on the previous item, preserving the complete rejection history.
- **Concurrent Upload Protection**: Enforced via row-level locking (`with_for_update()`) on the `AuditPBCRequest` record during fulfillment.

---

## 11. Sample Exception $\rightarrow$ Finding Authority Contract

ControlSphere maintains **one authoritative Finding engine**: Phase 4 [`Finding`](file:///E:/PROJECT%20WORKSPACE%202/ControlSphere/backend/app/models/finding.py).

### Escalation Trace:
```
1. Auditor tests AuditSampleItem
   ├── Sets test_result = SampleResultEnum.FAIL
   └── Records testing_notes = "Access grant lacked manager signoff ticket."

2. Auditor escalates via POST /api/v1/audits/{audit_id}/procedures/{proc_id}/samples/{sample_id}/escalate-finding
   ├── Validates procedure is linked to an organization_control_id
   ├── Invokes FindingService.create_finding():
   │   ├── organization_id = current_user.organization_id
   │   ├── organization_control_id = procedure.organization_control_id
   │   ├── title = f"Audit Sample Exception: {procedure.title} [Item {sample.source_record_id}]"
   │   ├── description = f"Audit testing failure on sample item {sample.source_record_id}. {sample.testing_notes}"
   │   ├── finding_type = FindingTypeEnum.CONTROL_GAP
   │   ├── severity = FindingSeverityEnum.HIGH (validated)
   │   ├── status = FindingStatusEnum.OPEN
   │   └── identified_by_id = current_user.id
   ├── Creates AuditFindingLink:
   │   ├── audit_id = audit_id
   │   ├── finding_id = finding.id
   │   └── source_procedure_id = procedure.id
   └── Updates AuditSampleItem:
       └── deficiency_finding_id = finding.id
```

#### Invariants:
- **Idempotency**: If `sample_item.deficiency_finding_id` is already populated, the escalation endpoint returns HTTP 409 Conflict, preventing duplicate findings for the same sample failure.
- **Control Lineage**: Because `Finding.organization_control_id` is non-nullable (`nullable=False`), escalation requires that the procedure or sample population be linked to an in-scope control.

---

## 12. Workpaper Four-Eyes Signoff Contract

In accordance with IIA Standard 2300 and regulatory independence mandates, no auditor may review or approve their own audit testing.

### 12.1 Segregation of Duties (SoD) Invariant
$$\text{workpaper.prepared\_by\_id} \neq \text{current\_user.id}$$

### 12.2 Verification Rule (Enforced in Service Layer)
```python
if workpaper.prepared_by_id == current_user.id:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Four-Eyes Governance Violation: The auditor who prepared this workpaper cannot review or approve it."
    )
```

### 12.3 Role Separation
- **Preparation (`AUDIT_WORKPAPER_PREPARE`)**: Available to `ADMIN`, `AUDITOR`, `MANAGER`.
- **Review & Approval (`AUDIT_WORKPAPER_APPROVE`)**: Restricted to `ADMIN`, `MANAGER`, and Lead `AUDITOR`.

---

## 13. Cryptographic Workpaper Digest Contract

Upon transition of an `AuditWorkpaperReview` to `REVIEWED_APPROVED`, the backend calculates and seals an immutable SHA-256 digest over the canonical JSON representation of the fieldwork execution:

### 13.1 Exact Digest Input Payload
```json
{
  "organization_id": 1,
  "audit_id": 4,
  "procedure_id": 12,
  "version_number": 1,
  "prepared_by_id": 7,
  "prepared_at": "2026-09-20T14:30:00Z",
  "reviewed_by_id": 3,
  "reviewed_at": "2026-09-20T16:45:00Z",
  "testing_summary": "Tested 25 randomly sampled access grants across Q1.",
  "conclusion": "Operating effectively with 0 exceptions noted.",
  "sample_summary": {
    "total_samples": 25,
    "pass_count": 25,
    "fail_count": 0,
    "exception_rate": 0.0
  }
}
```

### 13.2 Canonical Serialization Formula
```python
canonical_bytes = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
workpaper_hash_sha256 = hashlib.sha256(canonical_bytes).hexdigest()
```
Once generated, `workpaper.workpaper_hash_sha256` is written to the database. Any subsequent modification of the workpaper or its linked sample items invalidates the digest, failing tamper-evidence verification.

---

## 14. RBAC & Permission Model (Exact 6 Platform Roles)

ControlSphere strictly maintains its **6 authoritative platform roles**. No new roles are created.

### 14.1 New Permissions in `app/core/permissions.py`
- `AUDIT_PBC_MANAGE = "audit:pbc_manage"`
- `AUDIT_PBC_RESPOND = "audit:pbc_respond"`
- `AUDIT_SAMPLE_MANAGE = "audit:sample_manage"`
- `AUDIT_SAMPLE_TEST = "audit:sample_test"`
- `AUDIT_WORKPAPER_PREPARE = "audit:workpaper_prepare"`
- `AUDIT_WORKPAPER_APPROVE = "audit:workpaper_approve"`

### 14.2 Role-to-Permission Mapping Matrix

| Permission | ADMIN | AUDITOR | MANAGER | GRC_ANALYST | SECURITY_ANALYST | VIEWER |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `audit:read` | Yes | Yes | Yes | Yes | Yes | Yes |
| `audit:manage` | Yes | Yes | Yes | No | No | No |
| `audit:execute` | Yes | Yes | Yes | No | No | No |
| `audit:pbc_manage` | Yes | Yes | Yes | No | No | No |
| `audit:pbc_respond` | Yes | Yes | Yes | Yes | Yes | Conditional* |
| `audit:sample_manage` | Yes | Yes | Yes | No | No | No |
| `audit:sample_test` | Yes | Yes | Yes | No | No | No |
| `audit:workpaper_prepare` | Yes | Yes | Yes | No | No | No |
| `audit:workpaper_approve` | Yes | Yes (Lead) | Yes | No | No | No |

*\*VIEWER is only permitted to fulfill PBC requests explicitly assigned to their `user_id`.*

---

## 15. Tenant Isolation & Anti-IDOR Model

Multi-tenancy is enforced at the database and query layers:

1. **Mandatory `organization_id` on All Tables**:
   `AuditPBCRequest`, `AuditSamplePopulation`, `AuditSampleItem`, and `AuditWorkpaperReview` each declare:
   ```python
   organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
   ```
2. **Server-Derived Context**:
   The client CANNOT pass or override `organization_id`. It is derived exclusively from the authenticated JWT token via `current_user.organization_id`.
3. **Anti-IDOR Query Boundary**:
   Every database query includes `organization_id == current_user.organization_id`:
   ```python
   pbc = db.query(AuditPBCRequest).filter(
       AuditPBCRequest.id == pbc_id,
       AuditPBCRequest.organization_id == current_user.organization_id
   ).first()
   if not pbc:
       raise HTTPException(status_code=404, detail="PBC request not found")
   ```
   *Strict Invariant: Cross-tenant probes return HTTP 404 Not Found to prevent tenant enumeration.*

---

## 16. Authoritative API Contracts

All endpoints are mounted under `/api/v1/audits/{audit_id}/`:

### 16.1 PBC Request Endpoints
- `GET /api/v1/audits/{audit_id}/pbc-requests`: List PBC requests for the engagement.
- `POST /api/v1/audits/{audit_id}/pbc-requests`: Create a new PBC request.
- `GET /api/v1/audits/{audit_id}/pbc-requests/{pbc_id}`: Get PBC request details and evidence links.
- `POST /api/v1/audits/{audit_id}/pbc-requests/{pbc_id}/fulfill`: Upload and attach evidence artifact (`EvidenceItem`).
- `POST /api/v1/audits/{audit_id}/pbc-requests/{pbc_id}/review`: Auditor decision (`ACCEPT` / `REJECT` with reason).

### 16.2 Sampling Lab Endpoints
- `POST /api/v1/audits/{audit_id}/procedures/{proc_id}/population`: Define/upload population records.
- `POST /api/v1/audits/{audit_id}/procedures/{proc_id}/population/freeze`: Seal population snapshot and compute digest.
- `POST /api/v1/audits/{audit_id}/procedures/{proc_id}/sample/generate`: Execute deterministic sampling algorithm.
- `GET /api/v1/audits/{audit_id}/procedures/{proc_id}/samples`: List generated sample items.
- `PUT /api/v1/audits/{audit_id}/procedures/{proc_id}/samples/{sample_id}`: Record test result (`PASS`/`FAIL`) and testing notes.
- `POST /api/v1/audits/{audit_id}/procedures/{proc_id}/samples/{sample_id}/escalate-finding`: Escalate sample failure to Phase 4 `Finding`.

### 16.3 Workpaper Governance Endpoints
- `GET /api/v1/audits/{audit_id}/procedures/{proc_id}/workpaper`: Get active workpaper review state.
- `POST /api/v1/audits/{audit_id}/procedures/{proc_id}/workpaper/submit`: Submit workpaper for Four-Eyes review.
- `POST /api/v1/audits/{audit_id}/procedures/{proc_id}/workpaper/approve`: Approve workpaper and seal SHA-256 digest.
- `POST /api/v1/audits/{audit_id}/procedures/{proc_id}/workpaper/request-changes`: Return workpaper to preparer with feedback.

---

## 17. Frontend Contract (`AuditDetailPage.tsx`)

The existing frontend architecture in `frontend/src/pages/AuditDetailPage.tsx` will be cleanly extended:

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│  AuditDetailPage.tsx                                                                     │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│  Tabs:                                                                                   │
│  [ Overview ]  [ Scope ]  [ Procedures ]  [ PBC Requests ]  [ Findings ]  [ Readiness ]  │
│                                                                                          │
│  Tab 1: Overview       — Engagement details, lead auditor, lifecycle transitions        │
│  Tab 2: Scope          — In-scope controls, rationalized frameworks                      │
│  Tab 3: Procedures     — Procedure list, Sampling Lab Drawer, Workpaper Signoff Drawer   │
│  Tab 4: PBC Requests   — Request queue, auditee fulfillment modal, auditor review modal  │
│  Tab 5: Findings       — Linked findings and sample exception escalations                │
│  Tab 6: Readiness      — Live readiness telemetry, radar breakdown, blocker alerts       │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

### Strict Client Boundaries:
1. **Zero Sampling Math on Client**: The browser never generates seeds, random numbers, or sample item slices. It issues `generate` commands and renders server results.
2. **Zero Readiness Calculation on Client**: Readiness score and bands are computed entirely on the backend in `AuditEngagementService.get_readiness()`.
3. **Cache Invalidation Discipline**: Any mutation invalidates `['audit', auditId]` and `['auditReadiness', auditId]`.

---

## 18. Audit Logging & Non-Repudiation Contract

All sensitive fieldwork operations invoke `AuditService.log_action()` to create immutable `AuditLog` records:

| Action Identifier | Entity Type | Target Entity | Context Logged |
| :--- | :--- | :--- | :--- |
| `AUDIT_PBC_CREATED` | `AuditPBCRequest` | PBC ID | `organization_control_id`, `due_date`, `assigned_to_id` |
| `AUDIT_PBC_SUBMITTED` | `AuditPBCRequest` | PBC ID | `fulfilled_evidence_id`, `submitted_at` |
| `AUDIT_PBC_ACCEPTED` | `AuditPBCRequest` | PBC ID | `reviewed_by_id`, `reviewed_at` |
| `AUDIT_PBC_REJECTED` | `AuditPBCRequest` | PBC ID | `reviewed_by_id`, `rejection_reason` |
| `AUDIT_POPULATION_FROZEN`| `AuditSamplePopulation`| Pop ID | `total_count`, `population_digest_sha256` |
| `AUDIT_SAMPLE_GENERATED`| `AuditSamplePopulation`| Pop ID | `sample_size`, `sampling_method`, `sampling_seed` |
| `AUDIT_SAMPLE_TESTED` | `AuditSampleItem` | Item ID | `test_result`, `tested_by_id` |
| `AUDIT_FINDING_ESCALATED`| `Finding` | Finding ID | `source_sample_item_id`, `procedure_id` |
| `AUDIT_WORKPAPER_SUBMIT` | `AuditWorkpaperReview` | Workpaper ID| `prepared_by_id`, `prepared_at` |
| `AUDIT_WORKPAPER_APPROVED`| `AuditWorkpaperReview`| Workpaper ID| `reviewed_by_id`, `workpaper_hash_sha256` |

---

## 19. Concurrency & Idempotency Controls

To prevent race conditions during high-volume fieldwork execution:

1. **PBC Double-Fulfillment Race**: Prevented via row-level locking:
   `db.query(AuditPBCRequest).filter(...).with_for_update().first()`
2. **Sample Generation Idempotency**: `AuditSamplePopulation.samples_generated` acts as a guard. Attempting to re-sample a generated population raises HTTP 409 Conflict unless a new version is created.
3. **Concurrent Workpaper Approval**:
   ```sql
   UPDATE audit_workpaper_reviews
   SET status = 'REVIEWED_APPROVED', reviewed_by_id = :user_id, ...
   WHERE id = :id AND status = 'SUBMITTED_FOR_REVIEW';
   ```
   If 0 rows are affected, returns HTTP 409 (Workpaper already approved or state changed).
4. **Duplicate Finding Escalation**: `uq_sample_pop_item` and checking `sample_item.deficiency_finding_id IS NOT NULL` guarantees one finding per failed sample.

---

## 20. Migration Design: `0022_audit_fieldwork_and_sampling.py`

### 20.1 Forward Migration (`upgrade()`)
1. Create table `audit_pbc_requests` with all foreign keys and `uq_pbc_org_identifier`.
2. Create table `audit_sample_populations` with `uq_population_proc_version`.
3. Create table `audit_sample_items` with `uq_sample_pop_item`.
4. Create table `audit_workpaper_reviews` with `uq_workpaper_proc_version`.
5. Alter table `audit_procedures`:
   - Add column `has_sampling: Boolean`, `server_default=sa.text('false')`, `nullable=False`.
   - Add column `workpaper_status: String(50)`, `server_default='DRAFT'`, `nullable=False`.

### 20.2 Reverse Migration (`downgrade()`)
1. Drop column `workpaper_status` from `audit_procedures`.
2. Drop column `has_sampling` from `audit_procedures`.
3. Drop table `audit_workpaper_reviews`.
4. Drop table `audit_sample_items`.
5. Drop table `audit_sample_populations`.
6. Drop table `audit_pbc_requests`.

---

## 21. Adversarial Security Test Matrix

The following 22 adversarial security tests are mandated for implementation verification:

| Test ID | Adversarial Attack Scenario | Injected Vector | Expected Security Enforcement |
| :--- | :--- | :--- | :--- |
| `SEC-B1-01` | Cross-Tenant PBC Access | Org B user queries `/audits/1/pbc-requests/1` (Org A) | HTTP 404 Not Found (Zero tenant leakage) |
| `SEC-B1-02` | Cross-Tenant Population Injection | Org B user attempts to attach population to Org A procedure | HTTP 404 Not Found |
| `SEC-B1-03` | Self-Review Workpaper Approval | Workpaper preparer attempts to approve own workpaper | HTTP 400 Bad Request ("Four-Eyes Violation") |
| `SEC-B1-04` | Auditee Self-Acceptance of PBC | Assigned auditee attempts to accept their own submitted PBC | HTTP 403 Forbidden / HTTP 400 SoD Violation |
| `SEC-B1-05` | Post-Approval Workpaper Tampering | Client attempts PUT on workpaper in `REVIEWED_APPROVED` | HTTP 400 Bad Request ("Workpaper is sealed") |
| `SEC-B1-06` | Post-Approval Sample Tampering | Client attempts to alter sample test result after workpaper approval | HTTP 400 Bad Request ("Sample items frozen") |
| `SEC-B1-07` | Client Seed Forgery | Client supplies arbitrary PRNG seed in sample generate request | Server ignores client seed; generates cryptographic seed |
| `SEC-B1-08` | Client Sample Size Tampering | Client supplies sample size exceeding total population count | HTTP 422 Unprocessable Entity ($n \le N$) |
| `SEC-B1-09` | Client `organization_id` Injection | Client injects foreign `organization_id` in JSON body | Server overrides with authenticated token org |
| `SEC-B1-10` | Forged Reviewer Identity | Client passes `reviewed_by_id` of lead auditor in body | Server ignores body; uses `current_user.id` |
| `SEC-B1-11` | Forged Audit Timestamps | Client passes backdated `reviewed_at` or `prepared_at` | Server uses `datetime.now(timezone.utc)` |
| `SEC-B1-12` | Unfrozen Population Sampling | Client requests sample generation on an unfrozen population | HTTP 400 Bad Request ("Population must be frozen") |
| `SEC-B1-13` | Population Mutability After Freeze | Client attempts to add/remove records to a frozen population | HTTP 400 Bad Request ("Population snapshot immutable") |
| `SEC-B1-14` | Duplicate PBC Fulfillment Race | Two concurrent threads submit evidence to same PBC | DB row lock: Thread 1 succeeds, Thread 2 rejected |
| `SEC-B1-15` | Duplicate Finding Escalation Race | Two concurrent requests escalate the same sample item | DB unique constraint: Exactly one finding created |
| `SEC-B1-16` | Unauthorized Fieldwork Access | User with `VIEWER` role attempts to freeze population | HTTP 403 Forbidden (`AUDIT_SAMPLE_MANAGE` required) |
| `SEC-B1-17` | Illegal Workpaper State Jump | Client attempts jump from `DRAFT` directly to `APPROVED` | HTTP 400 Bad Request (Invalid state transition) |
| `SEC-B1-18` | Evidence Storage Bypass | PBC fulfillment without valid binary or SHA-256 hash | HTTP 422 Unprocessable Entity |
| `SEC-B1-19` | Finding Engine Duplication Probe | Escalation endpoint attempts to write to unmapped table | Strict foreign key verification against `findings` table |
| `SEC-B1-20` | Workpaper Digest Invalidation | Attacker modifies testing notes directly in database | Digest re-verification fails: hash mismatch detected |
| `SEC-B1-21` | Systematic Sampling Edge Case | Systematic sample requested with $n = 0$ or $k = 0$ | HTTP 422 Validation Error |
| `SEC-B1-22` | Stratified Sampling Empty Stratum | Stratum contains 0 records | HTTP 422 Validation Error |

---

## 22. Comprehensive Test Plan

Implementation of Batch 1 will deliver a dedicated test suite in `backend/tests/test_audit_fieldwork.py`:

```
Test Suite Structure (Estimated ~45 targeted tests):
├── TestTenantIsolationAndIDOR
│   ├── test_cross_tenant_pbc_request_blocked (404)
│   ├── test_cross_tenant_population_blocked (404)
│   └── test_cross_tenant_workpaper_blocked (404)
├── TestPBCRequestLifecycle
│   ├── test_create_and_assign_pbc_request
│   ├── test_fulfill_pbc_with_authoritative_evidence_item
│   ├── test_auditor_accept_pbc_request
│   ├── test_auditor_reject_pbc_request_with_reason
│   └── test_auditee_self_approval_blocked
├── TestSamplingReproducibility
│   ├── test_deterministic_random_sampling_with_seed
│   ├── test_deterministic_systematic_sampling_with_seed
│   ├── test_deterministic_stratified_sampling_with_seed
│   ├── test_canonical_ordering_independence_from_db
│   └── test_population_freeze_and_digest_generation
├── TestWorkpaperFourEyesGovernance
│   ├── test_preparer_cannot_approve_own_workpaper
│   ├── test_authorized_reviewer_can_approve_workpaper
│   ├── test_workpaper_hash_sha256_generated_on_approval
│   └── test_tamper_evidence_detects_post_approval_modifications
├── TestDeficiencyEscalationBridge
│   ├── test_sample_fail_escalates_to_authoritative_finding
│   ├── test_duplicate_escalation_blocked
│   └── test_finding_links_to_source_audit_and_procedure
└── TestAuditReadinessIntegration
    ├── test_pbc_fulfillment_improves_readiness_score
    └── test_sample_exceptions_penalize_readiness_score
```
*Full regression mandate: 965 existing tests + all new Batch 1 tests must pass (100% pass rate).*

---

## 23. Concrete Implementation Sequence

The implementation phase for Batch 1 will proceed in an 8-stage vertical execution sequence:

```
Step 1: Alembic Migration & Database Models
        ├── Create backend/alembic/versions/0022_audit_fieldwork_and_sampling.py
        ├── Extend backend/app/models/audit_engagement.py with 4 new entities
        └── Execute alembic upgrade head and verify schema

Step 2: RBAC & Permission Additions
        └── Update backend/app/core/permissions.py with 6 new fieldwork permissions

Step 3: Pydantic Schemas & DTOs
        └── Create backend/app/schemas/audit_fieldwork.py

Step 4: Fieldwork & Sampling Domain Services
        ├── Create backend/app/services/audit_fieldwork_service.py (PBC & Workpaper)
        ├── Create backend/app/services/audit_sampling_service.py (AU-C 530 Sampling Engine)
        └── Enhance AuditEngagementService.get_readiness() with fieldwork metrics

Step 5: FastAPI REST API Endpoints
        ├── Create backend/app/api/v1/endpoints/audit_fieldwork.py
        └── Register router in backend/app/api/v1/api.py

Step 6: Comprehensive Security & Functional Tests
        ├── Author backend/tests/test_audit_fieldwork.py
        └── Execute pytest and verify 100% pass rate

Step 7: Frontend Fieldwork Integration
        ├── Update frontend/src/lib/auditService.ts
        ├── Update frontend/src/types/index.ts
        ├── Enhance frontend/src/pages/AuditDetailPage.tsx with PBC & Sampling Labs
        └── Verify frontend production build (npm run build)

Step 8: Final Regression & Pre-Commit Verification
        ├── Run full 965+ test suite
        ├── Verify git status, git diff --check
        └── Perform Git checkpoint
```

---

## 24. Productivity & Batch Boundary Justification

Implementing Capabilities A through F as a single coordinated batch delivers measurable productivity advantages over fragmented single-phase development:

1. **Zero Context Switching**: The engineering team works within a single cohesive bounded context (`Audit` $\leftrightarrow$ `AuditProcedure` $\leftrightarrow$ `Fieldwork`), eliminating overhead from repeated context re-orientation.
2. **Schema Stability**: A single migration `0022` eliminates the hazards of incremental table alterations, orphaned migrations, or conflicting revision heads.
3. **Integrated Regression Cycle**: The entire audit lifecycle is verified in a single end-to-end integration pass rather than requiring multiple partial regression gates.
4. **No Artificial Mocking**: Testing PBC requests directly feeds into Evidence linking; testing samples directly feeds into Finding escalation. There is zero need to create throwaway mock test fixtures between phases.

---

## 25. Risks & Architectural Mitigations

| Risk Identified | Severity | Architectural Mitigation Strategy |
| :--- | :---: | :--- |
| **Large Population Memory Pressure** | Medium | Populations exceeding 10,000 items stream records via server-side cursors; sampling uses item index arrays rather than loading full JSON objects into memory. |
| **Auditee Evidence Confusion** | Low | PBC requests display explicit guidance, accepted file types, and control context directly in the auditee submission portal. |
| **Non-Deterministic PRNG implementations** | High | Bounded strictly to Python standard library `random.Random` with integer seed derived from SHA-256; zero reliance on platform-specific C extensions. |
| **Silent Audit Invalidation** | Critical | Population snapshots are permanently frozen with SHA-256 digests; any modification requires creating an explicitly incremented population version ($v2$). |

---

## 26. Final Architecture Gate & Authoritative Verdict

### Architecture Verification Summary:
- **Repository Ground Truth Confirmed**: Yes (Clean Git baseline `8b8b482d`, Alembic head `0021`, 965/965 passing tests).
- **Single Batch Boundary Justified**: Yes (High entity coupling, atomic fieldwork lifecycle, shared UI surface).
- **Sampling Reproducibility Mathematically Guaranteed**: Yes (Server-controlled SHA-256 seed, canonical ordering, isolated `random.Random` instance, frozen snapshots).
- **Authority Boundaries Strictly Preserved**: Yes (Zero duplicate evidence or finding engines).
- **Four-Eyes Segregation of Duties Enforced**: Yes (Server-derived `prepared_by_id != reviewed_by_id`).
- **Cryptographic Workpaper Digest Formulated**: Yes (SHA-256 over canonical JSON).
- **Exact 6 Platform Roles Preserved**: Yes (Zero role inflation).
- **Tenant Isolation & Anti-IDOR Guaranteed**: Yes (Mandatory `organization_id`, HTTP 404 semantics).
- **Adversarial Test Matrix Specified**: Yes (22 explicit attack vectors).

---

# **GO — BATCH READY FOR IMPLEMENTATION**
