# Phase 25 Architecture Discovery: Enterprise Audit Fieldwork, PBC Requests & Statistical Sampling Governance

**Module Code**: `AUDIT-FIELDWORK-GRC`
**Module Title**: Enterprise Audit Fieldwork, PBC Requests & Statistical Sampling Governance
**Vertical Stack Status**: ARCHITECTURE DISCOVERY COMPLETE — GATE PASS
**Date**: September 20, 2026
**Git Baseline**: `8b8b482d98e8d74a4807f490c0219b9b9eefa564` (main, clean, pushed)
**Alembic Head**: `0021 (head)`
**Current Test Baseline**: 965 passing tests (100% pass rate)

---

## 1. Repository Ground Truth

### 1.1 Git & Working Tree State
- **Branch**: `main`
- **Current HEAD**: `8b8b482d98e8d74a4807f490c0219b9b9eefa564`
- **Remote `origin/main`**: `8b8b482d98e8d74a4807f490c0219b9b9eefa564` (fully synchronized)
- **Working Tree**: Completely clean (0 modified, 0 untracked, 0 staged changes)
- **Previous Phase**: Phase 24 (`POLICY-ATTESTATION-GRC`) complete, verified, committed, and pushed.

### 1.2 Alembic Migration Lineage
The database schema consists of **21 applied migrations** (`0001` through `0021`):
- `0001`: Initial foundation schema (Organizations, Users, Roles, AuditLog)
- `0002`: Frameworks, Controls, Policies (`Policy`, `Framework`, `OrganizationControl`, `PolicyControlMapping`)
- `0003`: Evidence Management (`EvidenceItem`, Review Workflow, SHA-256 Hashing, Storage)
- `0004`: Assessments, Findings, Remediation (`Assessment`, `Finding`, `RemediationPlan`)
- `0005`: Risks, Exceptions Governance (`Risk`, `SecurityException`)
- `0006`: Audit Management (`Audit`, `AuditScopeControl`, `AuditProcedure`, `AuditProcedureEvidence`, `AuditFindingLink`)
- `0007`: Continuous Control Monitoring (`MonitoringRule`, `MonitoringAlert`)
- `0008`: Multi-Framework Harmonization (`CommonControl`, `ControlCrosswalk`)
- `0009`: TPRM / Vendor Risk (`Vendor`, `VendorAssessment`, `VendorContract`)
- `0010`: Incident Management & Regulatory Disclosure (`SecurityIncident`, `IncidentTimelineEvent`, `RegulatoryDisclosure`)
- `0011`: Remediation Orchestration (`RemediationMilestone`, `CompensatingControl`)
- `0012`: Quantum GRC / FAIR Risk Quantification (`QuantitativeRiskScenario`, `MonteCarloSimulation`)
- `0013`: Operational Resilience & BIA (`BusinessProcess`, `ResilienceScenario`)
- `0014`: Threat Exposure & Vulnerability Governance (`VulnerabilityExposure`, `AssetExposure`)
- `0015`: AI-GRC / Algorithmic Risk (`AISystem`, `AIEthicsEvaluation`)
- `0016`: PRIVACY-GRC / RoPA & DPIA (`ProcessingActivity`, `DPIAAssessment`, `DataAsset`)
- `0017`: SUPPLYCHAIN-GRC / SBOM (`SoftwareProduct`, `SBOMDocument`, `SoftwareComponent`)
- `0018`: CLOUDSEC-GRC & IDENTITY-GRC (`CloudAsset`, `CloudPostureCheck`, `GovernedIdentity`, `AccessCertificationCampaign`, `SoDPolicy`)
- `0019`: EXECUTIVE-GRC (`ExecutiveSnapshot`, `BoardDeck`)
- `0020`: REGULATORY-GRC, INTEGRATION-GRC & CONTINUOUS-GRC (`RegulatoryMandate`, `IntegrationConnector`, `UnifiedCompliancePosture`)
- `0021`: POLICY-ATTESTATION-GRC (`PolicyVersion`, `PolicyReviewWorkflow`, `PolicyAttestationCampaign`, `UserAttestationRecord`)

**Current Alembic Head**: `0021 (head)`
**Next Required Migration**: `0022_audit_fieldwork_and_sampling.py`

### 1.3 Test Baseline
- **Total Passing Tests**: **965 / 965 PASS** (0 failures, 517 warnings captured)
- **Targeted Phase 24 Suite**: **40 / 40 PASS** in 65.15s
- **Frontend Production Build**: **PASS** (`tsc -b && vite build` in 577ms, 0 errors)

### 1.4 Authoritative Platform Roles
ControlSphere enforces exactly **six immutable platform roles** across all modules:
1. `ADMIN`: Full platform administrative, configuration, and emergency governance authority.
2. `MANAGER`: Domain managerial control, assignment, campaign management, and secondary approval authority.
3. `GRC_ANALYST`: Risk, framework, control, policy analysis, and remediation execution.
4. `SECURITY_ANALYST`: Technical security, vulnerability, CSPM, incident, and telemetry operations.
5. `AUDITOR`: Independent audit planning, fieldwork execution, testing, and assessment review.
6. `VIEWER`: Read-only tenant telemetry, personal attestation, and reporting access.

---

## 2. Current Authority Matrix

| Domain / Engine | Authoritative Model | Authoritative Service | Lifecycle States | Evidence Authority | Risk Authority | Audit Authority | Tenant Boundary | Existing APIs | Duplicate Risk |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Frameworks** | `Framework`, `FrameworkSubcategory` | `FrameworkService` | Static Catalog | Maps to Controls | Informs Inherent Risk | Audit Framework Reference | Global / System-level | `/api/v1/frameworks` | Reused directly |
| **Controls** | `OrganizationControl` | `ControlService` | `NOT_IMPLEMENTED`, `PLANNED`, `PARTIALLY_IMPLEMENTED`, `IMPLEMENTED` | Primary recipient of Evidence | Mitigates Risk | In Scope for Audits | `organization_id` FK | `/api/v1/controls` | Primary anchor |
| **Policies** | `Policy`, `PolicyVersion` | `PolicyService` | `DRAFT`, `UNDER_REVIEW`, `APPROVED`, `PUBLISHED`, `ARCHIVED` | Attestation manifests produce Evidence | Mitigates Governance Risk | Policy Audit Scope | `organization_id` FK | `/api/v1/policies` | Single policy authority |
| **Evidence** | `EvidenceItem` | `EvidenceService` | `UPLOADED`, `UNDER_REVIEW`, `ACCEPTED`, `REJECTED`, `SUPERSEDED` | **Sole Evidence Authority** | Evidences Control Effectiveness | `AuditProcedureEvidence` links | `organization_id` FK | `/api/v1/evidence` | DO NOT DUPLICATE |
| **Assessments** | `Assessment` | `AssessmentService` | `DRAFT`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED` | Evidenced by `EvidenceItem` | Generates Findings | Informs Audit Planning | `organization_id` FK | `/api/v1/assessments` | DO NOT DUPLICATE |
| **Findings** | `Finding` | `FindingService` | `OPEN`, `IN_REMEDIATION`, `PENDING_VALIDATION`, `RESOLVED`, `ACCEPTED_RISK`, `CLOSED` | Evidenced by `EvidenceItem` | Contributes to Inherent/Residual Risk | `AuditFindingLink` links | `organization_id` FK | `/api/v1/findings` | Sole finding authority |
| **Risks** | `Risk` | `RiskService` | `IDENTIFIED`, `ASSESSED`, `TREATMENT_PLANNED`, `MITIGATING`, `MONITORING`, `ACCEPTED`, `CLOSED` | Supported by Evidence | **Sole Qualitative Risk Authority** | Informs Risk-based Audits | `organization_id` FK | `/api/v1/risks` | Sole risk authority |
| **Remediation** | `RemediationPlan`, `RemediationMilestone` | `RemediationService` | `DRAFT`, `APPROVED`, `IN_PROGRESS`, `VALIDATING`, `COMPLETED`, `CANCELLED` | Completion verified by Evidence | Reduces Residual Risk | Audit remediation tracking | `organization_id` FK | `/api/v1/remediations` | Sole CAPA authority |
| **Audits (Shell)**| `Audit`, `AuditProcedure` | `AuditEngagementService` | `PLANNED`, `INITIATED`, `FIELDWORK`, `REVIEW`, `REPORTING`, `COMPLETED`, `CLOSED` | Links `EvidenceItem` | Links `Finding` | **Sole Audit Engagement Authority** | `organization_id` FK | `/api/v1/audits` | Anchor for Phase 25 |
| **Workforce Attestation** | `PolicyAttestationCampaign`, `UserAttestationRecord` | `PolicyService` | `DRAFT`, `ACTIVE`, `COMPLETED`, `CANCELLED` | Generates SHA-256 Manifest Evidence | Validates Policy Comprehension | Audit workforce compliance | `organization_id` FK | `/api/v1/policies/campaigns` | Phase 24 Authority |

---

## 3. Architectural Gap Analysis

### 3.1 The Audit Fieldwork Execution Disconnect
ControlSphere Phase 6 implemented the high-level **Audit Engagement Shell** (`Audit`, `AuditScopeControl`, `AuditProcedure`, `AuditProcedureEvidence`, `AuditFindingLink`). However, examining actual enterprise audit practices (SOC 2, ISO 27001, FedRAMP, SOX, and Internal Audit) reveals critical architectural operational voids:

1. **Lack of PBC (Provided By Client) Request Management**:
   - In real-world audits, auditors spend over 60% of their operational engagement time requesting, tracking, and reviewing documentation provided by control owners.
   - Currently, an auditor must manually search for existing `EvidenceItem` records. There is **no mechanism for an auditor to issue a formal request list (PBC)** with requirements, instructions, assignees, and deadlines.
   - Auditees have no dedicated inbox or workflow to submit evidence directly against audit requests.
   - Auditors cannot accept, reject, or request revisions on submitted PBC items with feedback loops.

2. **Absence of Audit Sampling Engine (AICPA AU-C 530 / PCAOB AS 2315)**:
   - Auditing controls (e.g., periodic access reviews, change tickets, onboarding background checks, firewall changes) cannot inspect 100% of populations consisting of thousands of transactions.
   - Auditors require a formal, reproducible **Audit Sampling Engine**:
     - Population registration with row counts, time horizons, and source definitions.
     - Deterministic pseudo-random or stratified sample selection with a recorded cryptographic seed (`sampling_seed`).
     - Individual sample item test records evaluating specific control test attributes (Pass / Fail / Exception).
     - Automated sample error rate calculation and population error projection.

3. **Missing Workpaper Review & Signoff Lifecycle (Preparer / Reviewer SoD)**:
   - In regulated audit engagements, independent workpapers must follow a strict **Two-Tier Signoff** (Four-Eyes SoD):
     - **Preparer (Staff / Senior Auditor)**: Executes testing, documents observations, attaches evidence/samples, and signs off.
     - **Reviewer (Lead Auditor / Audit Manager)**: Independently inspects workpapers, validates conclusions, and signs off.
     - The preparer and reviewer **cannot be the same individual** (`prepared_by_id != reviewed_by_id`).
   - Current Phase 6 `AuditProcedure` has simple `tester_id` and `result` columns with zero review signoff workflow.

4. **Missing Audit Deficiency $\rightarrow$ Finding Escalation Bridge**:
   - When sample items fail or a procedure yields a non-compliant result, an audit observation/deficiency is born.
   - Currently, there is no automated bridge between an audit procedure failure and the authoritative Phase 4 `Finding` engine.

---

## 4. Candidate Phase 25 Modules

### Candidate 1: `AUDIT-FIELDWORK-GRC` — Enterprise Audit Fieldwork, PBC Requests & Statistical Sampling Governance
- **Business Purpose**: Extend Phase 6 `Audit` engagement management into a complete, institutional audit fieldwork execution engine with PBC document request lists, statistical sampling, multi-tier workpaper signoffs (Preparer/Reviewer SoD), and automated deficiency-to-finding escalation.
- **New Entities**: `AuditPBCRequest`, `AuditSamplePopulation`, `AuditSampleItem`, `AuditWorkpaperReview`.
- **Existing Entities Reused**: `Audit`, `AuditProcedure`, `AuditScopeControl`, `OrganizationControl`, `EvidenceItem`, `Finding`, `User`, `Organization`.
- **Migration Impact**: Migration `0022`; clean addition of 4 tables and non-breaking enhancement of `audit_procedures`.
- **API Impact**: Dedicated `/api/v1/audits/{audit_id}/pbc-requests`, `/samples`, `/workpapers`.
- **Frontend Impact**: Enhanced `AuditDetailPage.tsx` with PBC Tracker, Sampling Lab, and Workpaper Signoff panels.
- **Permission Impact**: `AUDIT_FIELDWORK_MANAGE`, `AUDIT_PBC_RESPOND`, `AUDIT_WORKPAPER_APPROVE`.
- **Anti-Duplication**: Reuses Phase 3 `EvidenceItem` (PBC fulfillment uploads an `EvidenceItem` in `UPLOADED` status), reuses Phase 4 `Finding` (deficiencies escalate into `Finding` with `FindingTypeEnum.CONTROL_GAP`).
- **Dependencies**: Seamlessly binds Phase 6 (`Audit`), Phase 3 (`EvidenceItem`), Phase 4 (`Finding`), and Phase 24 (`PolicyAttestationCampaign`).

### Candidate 2: `KRI-APPETITE-GRC` — Key Risk Indicators, Dynamic Appetite Governance & Threshold Telemetry
- **Business Purpose**: Implement continuous quantitative risk telemetry with Key Risk Indicators (KRIs), metric collectors, dynamic Green/Amber/Red threshold breach detection, and automated risk scoring recalculation.
- **New Entities**: `KeyRiskIndicator`, `KRIMetricSample`, `RiskAppetiteThreshold`, `KRIBreachEvent`.
- **Existing Entities Reused**: `Risk`, `QuantitativeRiskScenario`, `MonitoringRule`, `MonitoringAlert`.
- **Trade-offs**: Strong mathematical alignment with Phase 12 (Quantum GRC), but does not solve the critical audit execution gap.

### Candidate 3: `COMPLIANCE-OBLIGATION-GRC` — Contractual Commitments, Customer Security Addendums & Trust Assurance
- **Business Purpose**: Centralize external customer and contractual security obligations (CSAs, DPAs, SLAs), mapping them to internal controls and proving adherence.
- **New Entities**: `ComplianceObligation`, `ObligationContractLink`, `ObligationFulfillmentRecord`.
- **Existing Entities Reused**: `RegulatoryMandate`, `Framework`, `OrganizationControl`, `EvidenceItem`.
- **Trade-offs**: Overlaps partially with Phase 21 (`RegulatoryMandate`) and Phase 9 (`VendorContract`).

### Candidate 4: `DATA-ASSET-LINEAGE-GRC` — Enterprise Data Classification, Lineage & Cross-Border Governance
- **Business Purpose**: Expand Phase 16 `DataAsset` and `ProcessingActivity` with automated classification schemas, cross-border data transfer lineage, and sensitivity tagging.
- **New Entities**: `DataClassificationSchema`, `DataFlowLineage`, `DataJurisdictionPolicy`.
- **Existing Entities Reused**: `DataAsset`, `ProcessingActivity`, `CloudAsset`, `SoftwareProduct`.
- **Trade-offs**: Niche privacy expansion; does not provide core cross-functional GRC lifecycle closure.

---

## 5. Recommended Phase 25 Module

### Selection: `AUDIT-FIELDWORK-GRC` (Enterprise Audit Fieldwork, PBC Requests & Statistical Sampling Governance)

### Architectural Justification: Why Phase 25 Follows Naturally from Phase 24
1. **The Operational GRC Lifecycle Closure**:
   - In Phases 1–23, ControlSphere established controls, evidence storage, monitoring rules, continuous assurance, and automated integrations.
   - In Phase 24, ControlSphere closed the loop on workforce governance with policy attestation campaigns and tamper-evident manifests.
   - **The very next operational event in an enterprise is the examination of these artifacts by Internal and External Auditors.**
   - Without PBC request tracking, statistical sampling, and workpaper review, ControlSphere cannot support an actual end-to-end SOC 2, ISO 27001, or SOX audit engagement.
2. **Zero Engine Duplication**:
   - `AUDIT-FIELDWORK-GRC` does **not** create a new audit engine; it directly extends the Phase 6 `Audit` and `AuditProcedure` models.
   - When auditees fulfill PBC requests, it creates standard Phase 3 `EvidenceItem` records in `UPLOADED` status.
   - When sample tests fail, it escalates directly into standard Phase 4 `Finding` records.
3. **Rigorous Four-Eyes Governance**:
   - Introduces audit workpaper signoff with mandatory Preparer/Reviewer separation (`prepared_by_id != reviewed_by_id`), fulfilling regulatory independence requirements (AICPA / IIA Standards).

---

## 6. Anti-Duplication Analysis

```
                       ┌──────────────────────────────────────────────┐
                       │               AUDIT ENGAGEMENT               │
                       │             (Phase 6: audits)                │
                       └──────────────────────┬───────────────────────┘
                                              │
                    ┌─────────────────────────┴─────────────────────────┐
                    ▼                                                   ▼
       ┌────────────────────────┐                          ┌────────────────────────┐
       │   AuditScopeControl    │                          │     AuditProcedure     │
       │  (OrganizationControl) │                          │     (Test Execution)   │
       └────────────────────────┘                          └────────────┬───────────┘
                                                                        │
                        ┌───────────────────────────────────────────────┴───────────────────┐
                        ▼                                                                   ▼
       ┌─────────────────────────────────┐                                 ┌─────────────────────────────────┐
       │        AuditPBCRequest          │                                 │     AuditSamplePopulation       │
       │    (PBC Document Request)       │                                 │     (Testing Population)        │
       └────────────────┬────────────────┘                                 └────────────────┬────────────────┘
                        │ fulfills                                                          │ generates
                        ▼                                                                   ▼
       ┌─────────────────────────────────┐                                 ┌─────────────────────────────────┐
       │          EvidenceItem           │◄────────────────────────────────┤         AuditSampleItem         │
       │       (Phase 3 Authority)       │      links sample evidence      │         (Pass / Fail / N/A)     │
       └─────────────────────────────────┘                                 └────────────────┬────────────────┘
                                                                                            │ fails
                                                                                            ▼
                                                                           ┌─────────────────────────────────┐
                                                                           │             Finding             │
                                                                           │       (Phase 4 Authority)       │
                                                                           └─────────────────────────────────┘
```

- **NO Duplicate Evidence Engine**: Every uploaded document enters `evidence_items` with canonical SHA-256 hash and `EvidenceStatusEnum.UPLOADED`.
- **NO Duplicate Finding Engine**: Sample test failures and audit deficiencies create standard `Finding` rows linked via `audit_finding_links`.
- **NO Duplicate Control Engine**: Scope controls and PBC requests link directly to `organization_controls`.
- **NO Duplicate Audit Shell**: Enhances existing `audits` and `audit_procedures`.

---

## 7. Proposed Data Model for Phase 25

### 7.1 Enums
```python
class PBCRequestStatusEnum(str, enum.Enum):
    REQUESTED = "REQUESTED"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

class PBCPriorityEnum(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class SamplingMethodEnum(str, enum.Enum):
    RANDOM = "RANDOM"
    SYSTEMATIC = "SYSTEMATIC"
    STRATIFIED = "STRATIFIED"
    HAZARD_JUDGEMENTAL = "HAZARD_JUDGEMENTAL"
    CENSUS_100_PERCENT = "CENSUS_100_PERCENT"

class SampleItemResultEnum(str, enum.Enum):
    PENDING = "PENDING"
    PASS = "PASS"
    FAIL = "FAIL"
    EXCEPTION = "EXCEPTION"
    NOT_APPLICABLE = "NOT_APPLICABLE"

class WorkpaperStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED_FOR_REVIEW = "SUBMITTED_FOR_REVIEW"
    REVIEWED_APPROVED = "REVIEWED_APPROVED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
```

### 7.2 Entities

#### Entity 1: `AuditPBCRequest` (`audit_pbc_requests`)
- `id`: Integer, PK
- `organization_id`: Integer, FK(`organizations.id`), NOT NULL, Index
- `audit_id`: Integer, FK(`audits.id`), NOT NULL, Index
- `request_code`: String(64), NOT NULL (e.g. `PBC-AUD01-001`)
- `title`: String(255), NOT NULL
- `description`: Text, NOT NULL
- `organization_control_id`: Integer, FK(`organization_controls.id`), Nullable, Index
- `procedure_id`: Integer, FK(`audit_procedures.id`), Nullable, Index
- `assigned_to_id`: Integer, FK(`users.id`), Nullable, Index (Auditee / Control Owner)
- `priority`: Enum(`PBCPriorityEnum`), default `MEDIUM`, NOT NULL
- `status`: Enum(`PBCRequestStatusEnum`), default `REQUESTED`, NOT NULL, Index
- `due_date`: Date, NOT NULL, Index
- `fulfilled_evidence_id`: Integer, FK(`evidence_items.id`), Nullable, Index
- `auditor_feedback`: Text, Nullable
- `submitted_at`: DateTime(UTC), Nullable
- `reviewed_at`: DateTime(UTC), Nullable
- `reviewed_by_id`: Integer, FK(`users.id`), Nullable
- `created_by_id`: Integer, FK(`users.id`), Nullable
- `created_at`: DateTime(UTC), NOT NULL
- `updated_at`: DateTime(UTC), NOT NULL
- **Constraint**: `UniqueConstraint("organization_id", "request_code", name="uq_audit_pbc_request_code")`

#### Entity 2: `AuditSamplePopulation` (`audit_sample_populations`)
- `id`: Integer, PK
- `organization_id`: Integer, FK(`organizations.id`), NOT NULL, Index
- `audit_id`: Integer, FK(`audits.id`), NOT NULL, Index
- `procedure_id`: Integer, FK(`audit_procedures.id`), NOT NULL, Index
- `population_name`: String(255), NOT NULL
- `description`: Text, Nullable
- `sampling_method`: Enum(`SamplingMethodEnum`), default `RANDOM`, NOT NULL
- `total_population_count`: Integer, NOT NULL (e.g. 5,000)
- `sample_size`: Integer, NOT NULL (e.g. 25 or 45)
- `sampling_seed`: String(64), NOT NULL (Cryptographic seed ensuring reproducible sample selection)
- `source_evidence_id`: Integer, FK(`evidence_items.id`), Nullable (Population source export)
- `stratification_criteria`: JSON/Text, Nullable
- `created_by_id`: Integer, FK(`users.id`), Nullable
- `created_at`: DateTime(UTC), NOT NULL

#### Entity 3: `AuditSampleItem` (`audit_sample_items`)
- `id`: Integer, PK
- `organization_id`: Integer, FK(`organizations.id`), NOT NULL, Index
- `population_id`: Integer, FK(`audit_sample_populations.id`), NOT NULL, Index
- `item_identifier`: String(100), NOT NULL (e.g. `USR-EMP-4019` or `PR-10492`)
- `item_index`: Integer, NOT NULL (Sequence index in sample: 1 to N)
- `item_attributes`: Text, Nullable (JSON details of the item sampled)
- `testing_notes`: Text, Nullable
- `test_result`: Enum(`SampleItemResultEnum`), default `PENDING`, NOT NULL, Index
- `evidence_item_id`: Integer, FK(`evidence_items.id`), Nullable (Specific sample corroborating evidence)
- `tested_by_id`: Integer, FK(`users.id`), Nullable
- `tested_at`: DateTime(UTC), Nullable
- `deficiency_finding_id`: Integer, FK(`findings.id`), Nullable (Escalated finding if failed)
- **Constraint**: `UniqueConstraint("population_id", "item_index", name="uq_audit_sample_item_idx")`

#### Entity 4: `AuditWorkpaperReview` (`audit_workpaper_reviews`)
- `id`: Integer, PK
- `organization_id`: Integer, FK(`organizations.id`), NOT NULL, Index
- `audit_id`: Integer, FK(`audits.id`), NOT NULL, Index
- `procedure_id`: Integer, FK(`audit_procedures.id`), NOT NULL, Index
- `status`: Enum(`WorkpaperStatusEnum`), default `DRAFT`, NOT NULL, Index
- `prepared_by_id`: Integer, FK(`users.id`), Nullable, Index (Auditor Preparer)
- `prepared_at`: DateTime(UTC), Nullable
- `preparer_conclusion`: Text, Nullable
- `reviewed_by_id`: Integer, FK(`users.id`), Nullable, Index (Lead Auditor / Reviewer)
- `reviewed_at`: DateTime(UTC), Nullable
- `reviewer_notes`: Text, Nullable
- `workpaper_hash_sha256`: String(64), Nullable (Tamper-evident snapshot digest of test steps, samples, and results)
- `created_at`: DateTime(UTC), NOT NULL
- **Constraint**: `UniqueConstraint("audit_id", "procedure_id", name="uq_audit_proc_workpaper")`

---

## 8. Security Architecture

### 8.1 RBAC & Role Mapping
| Platform Role | PBC Requests | Sample Populations & Items | Workpaper Preparation | Workpaper Review & Signoff |
| :--- | :--- | :--- | :--- | :--- |
| `ADMIN` | Manage / Delete | Manage / Generate | Full execution | Full Review authority |
| `AUDITOR` | Create / Review / Accept | Generate / Test Samples | Prepare & Sign Off | Review & Sign Off (Four-Eyes) |
| `MANAGER` | View / Reassign / Respond | View-only | Read-only | Prohibited (Auditor independence) |
| `GRC_ANALYST` | View / Respond to PBC | View-only | Read-only | Prohibited |
| `SECURITY_ANALYST` | View / Respond to PBC | View-only | Read-only | Prohibited |
| `VIEWER` | View assigned PBC | Read-only | Read-only | Prohibited |

### 8.2 Four-Eyes Separation of Duties (SoD)
1. **Workpaper Signoff SoD**:
   `prepared_by_id != reviewed_by_id`
   The auditor who prepared and tested the sample workpaper cannot sign off as the reviewer.
2. **PBC Acceptance Independence**:
   The user fulfilling the PBC request cannot accept the PBC request (`assigned_to_id != reviewed_by_id`).
3. **Auditor Independence**:
   `AUDITOR` role cannot remediate or close `Finding` rows; findings can only be resolved by `GRC_ANALYST` or `MANAGER`, maintaining operational independence.

### 8.3 Multi-Tenant Isolation & IDOR Protection
- All queries strictly enforce `filter(Model.organization_id == current_user.organization_id)`.
- PBC responses verify that the upload matches the caller's organization boundary.
- Cross-tenant crosswalks, sample generation, or workpaper signoffs return HTTP 404.

---

## 9. Migration Strategy

- **Next Migration**: `backend/alembic/versions/0022_audit_fieldwork_and_sampling.py`
- **Revises**: `0021`
- **Down Revision**: `0021`
- **Table Alterations**:
  - `audit_procedures`: Add optional `has_sampling: Boolean = False` and `workpaper_status: String = "DRAFT"`
- **New Tables**:
  - `audit_pbc_requests`
  - `audit_sample_populations`
  - `audit_sample_items`
  - `audit_workpaper_reviews`
- **Backfill Requirements**: None. Existing `audit_procedures` default `has_sampling = False`.
- **Downgrade Safety**: Clean table drops and index removal in reverse order of creation.

---

## 10. API / Frontend Impact

### 10.1 REST API Endpoints
- `GET /api/v1/audits/{audit_id}/pbc-requests` (List PBC requests with status/assignee filters)
- `POST /api/v1/audits/{audit_id}/pbc-requests` (Auditor creates PBC item)
- `POST /api/v1/audits/{audit_id}/pbc-requests/{pbc_id}/fulfill` (Auditee submits evidence file)
- `POST /api/v1/audits/{audit_id}/pbc-requests/{pbc_id}/review` (Auditor accepts/rejects with feedback)
- `POST /api/v1/audits/{audit_id}/procedures/{proc_id}/sampling/generate` (Generate deterministic samples)
- `PATCH /api/v1/audits/{audit_id}/procedures/{proc_id}/samples/{item_id}` (Record sample item test results)
- `POST /api/v1/audits/{audit_id}/procedures/{proc_id}/samples/{item_id}/escalate-finding` (Escalate failed sample to Finding)
- `POST /api/v1/audits/{audit_id}/procedures/{proc_id}/workpaper/submit` (Preparer submits workpaper)
- `POST /api/v1/audits/{audit_id}/procedures/{proc_id}/workpaper/signoff` (Reviewer approves workpaper with Four-Eyes check)

### 10.2 Frontend Views
- **`AuditDetailPage.tsx` Extensions**:
  - Tab 1: Audit Scope Controls
  - Tab 2: Audit Procedures
  - Tab 3: **PBC Document Request Tracker** (Auditor & Auditee views, drag-and-drop evidence upload, review modals)
  - Tab 4: **Audit Sampling Lab** (Sampling methodology selector, seed reproducibility badge, sample testing checklist)
  - Tab 5: **Workpaper Signoff Matrix** (Preparer / Reviewer dual signoff badges with SHA-256 workpaper digest)
- **`DashboardPage.tsx`**: Add "My Pending PBC Requests" action widget for control owners.

---

## 11. Test Architecture

Anticipated Test Matrix for Phase 25: **~40 tests**:
1. **Tenant Isolation & IDOR** (8 tests): Cross-tenant PBC request, sample, and workpaper manipulation blocked.
2. **Four-Eyes Workpaper Signoff** (6 tests): Self-review rejection, unprivileged signoff rejection, immutable post-signoff checks.
3. **Deterministic Sampling Engine** (6 tests): Identical seed generates identical sample selection; random/stratified boundary validation.
4. **PBC Request Lifecycle** (8 tests): Request $\rightarrow$ Fulfill $\rightarrow$ Reject $\rightarrow$ Re-submit $\rightarrow$ Accept with Phase 3 Evidence linking.
5. **Deficiency Escalation Bridge** (4 tests): Sample failure creates Phase 4 `Finding` in `OPEN` status linked to control and audit.
6. **Audit Trail & Immutability** (4 tests): Audit events emitted for workpaper approval, sample generation, and PBC review.
7. **End-to-End API Integration** (4 tests): Full lifecycle API testing.

---

## 12. Phase 25 Architecture Gate

| Gate Criterion | Verification Result |
| :--- | :--- |
| **Ground Truth Verified** | Clean working tree; HEAD = `8b8b482`; Alembic = `0021` |
| **No Duplicate Engines** | Reuses `EvidenceItem`, `Finding`, `OrganizationControl`, and `Audit` |
| **Exact 6 Roles Preserved** | `AUDITOR` executes/reviews, `GRC_ANALYST`/`MANAGER` fulfill PBCs |
| **Four-Eyes Principle Enforced** | Workpaper preparer cannot be reviewer (`prepared_by_id != reviewed_by_id`) |
| **Deterministic Evidence Lineage** | PBC fulfillment directly creates Phase 3 `EvidenceItem` in `UPLOADED` status |
| **Clear Scope Boundaries** | Bounded to 4 new tables, 1 migration (`0022`), and targeted frontend tabs |

---

## 13. Final Verdict

# **GO — PROCEED TO PHASE 25 ARCHITECTURE HARDENING GATE**
