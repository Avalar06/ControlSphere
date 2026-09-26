# ControlSphere — Phase 27 / Batch 3 Architecture Discovery & Implementation Boundary Contract
## Module: `DATA-GOVERNANCE-GRC` (`BATCH-3-DATA-GOVERNANCE-GRC`)

- **Repository**: `E:\PROJECT WORKSPACE 2\ControlSphere`
- **Remote**: `https://github.com/Avalar06/ControlSphere.git`
- **Branch**: `main`
- **Verified Frozen Baseline Commit**: `7b5c795` (`7b5c7954f6c4ae29a9f89e4b90497b3cc04fc7ca`) — `feat(batch2): implement kri appetite governance`
- **Current Alembic Migration Head**: `0023` (`0023_kri_and_risk_appetite_governance.py`)
- **Target Migration for Batch 3**: `0024_data_governance_and_lineage.py` (revises `0023`)
- **Discovery Verdict**: **GO — BATCH 3 READY FOR HARDENING (`BATCH-3-DATA-GOVERNANCE-GRC`)**

---

## 1. Baseline Verification

| Verification Check | Command Executed | Actual Result | Status |
| :--- | :--- | :--- | :--- |
| **Git Status** | `git status` | `On branch main`, `Your branch is up to date with 'origin/main'`, `nothing to commit, working tree clean` | **PASS** |
| **Latest Commit** | `git log -1 --oneline` | `7b5c795 feat(batch2): implement kri appetite governance` | **PASS** |
| **Remote Configuration** | `git remote -v` | `origin https://github.com/Avalar06/ControlSphere.git (fetch/push)` | **PASS** |
| **Alembic Head** | `alembic -c backend/alembic.ini heads` | `0023 (head)` (`0023_kri_and_risk_appetite_governance.py`) | **PASS** |
| **Backend Regression Baseline** | Verified at Batch 2 checkpoint (`7b5c795`) | `1,038 / 1,038 passed` (`0` failures) | **PASS** |
| **Frontend Build Baseline** | Verified at Batch 2 checkpoint (`7b5c795`) | `tsc -b && vite build` exit code `0` | **PASS** |

---

## 2. Existing Phase 16 Privacy Authority (`PRIVACY-GRC`)

Phase 16 (`PRIVACY-GRC`, migration `0013_privacy_governance_and_dpia.py`) introduced the foundational privacy governance models in `backend/app/models/privacy.py`, managed by `PrivacyService` (`backend/app/services/privacy_service.py`) and exposed under `/api/v1/privacy` (`backend/app/api/v1/endpoints/privacy.py`).

### 2.1 Detailed Audit of `backend/app/models/privacy.py`

1. **`DataAsset` (`__tablename__ = "data_assets"`)**:
   - **Existing Columns**:
     - `id` (`Integer`, PK)
     - `organization_id` (`Integer`, FK `organizations.id`, indexed, NOT NULL)
     - `asset_code` (`String(64)`, indexed, NOT NULL, unique per organization via `uq_data_asset_org_code`)
     - `name` (`String(255)`, NOT NULL)
     - `description` (`Text`, nullable)
     - `data_sensitivity_level` (`Enum(DataSensitivityLevel)`: `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED_PII`, `SPECIAL_CATEGORY_SENSITIVE_PHI`, default `INTERNAL`, indexed)
     - `data_volume_range` (`Enum(DataVolumeRange)`: `LOW`, `MEDIUM`, `HIGH`, default `LOW`)
     - `storage_type` (`String(64)`, nullable)
     - `hosting_jurisdiction` (`String(64)`, nullable)
     - `is_encrypted_at_rest` (`Boolean`, default `True`)
     - `is_encrypted_in_transit` (`Boolean`, default `True`)
     - `is_pseudonymized` (`Boolean`, default `False`)
     - `retention_period_months` (`Integer`, nullable)
     - `business_process_id` (`Integer`, FK `business_processes.id`, nullable, indexed)
     - `ai_system_id` (`Integer`, FK `ai_systems.id`, nullable, indexed)
     - `vendor_id` (`Integer`, FK `vendors.id`, nullable, indexed)
     - `owner_id` (`Integer`, FK `users.id`, NOT NULL, indexed)
     - `created_at`, `updated_at` (`DateTime(timezone=True)`)
   - **Architectural Assessment**: `DataAsset` (`data_assets`) **ALREADY EXISTS** as the canonical platform table for logical data assets. However, it was built as a basic inventory record for Phase 16 privacy assessments and lacks:
     - **Stewardship separation**: Has `owner_id` (Data Owner), but no `steward_id` (Data Steward) or ownership transfer governance.
     - **Lifecycle state machine**: Has no `lifecycle_state` column (`DISCOVERED`, `REGISTERED`, `CLASSIFIED`, `ACTIVE`, `DEPRECATED`, `RETIRED`) and currently exposes a destructive `DELETE /api/v1/privacy/data-assets/{id}` endpoint without retirement governance or disposal evidence.
     - **Cloud infrastructure link**: Has no `cloud_asset_id` foreign key linking logical datasets to Phase 18 `CloudAsset` (`cloud_assets.id`).
     - **Configurable Classification Scheme & Four-Eyes History**: `data_sensitivity_level` is a static 5-value enum mutated directly via `PUT /api/v1/privacy/data-assets/{id}` with no organization-configurable classification schemes (`DataClassificationScheme` / `DataClassificationLevel`), no Four-Eyes approval workflow for downgrades or restricted classifications, and no immutable classification history ledger (`DataClassificationRecord`).
     - **Directed Asset-to-Asset Lineage**: Has no `DataLineageEdge` graph. Currently, `frontend/src/components/privacy/PrivacyLineageCard.tsx` and `PrivacyAssetDetailPage.tsx` only display single-hop foreign keys (`business_process_id`, `ai_system_id`, `vendor_id`) and infer `ProcessingActivity` links by checking if a `ProcessingActivity` happens to share the same `business_process_id`, `ai_system_id`, or `vendor_id`.
     - **Explicit M:N Processing, Control, and Evidence Traceability**: Has no explicit link table to `ProcessingActivity` (`data_asset_processing_links`) or `OrganizationControl` / `EvidenceItem` (`data_asset_control_links`).

2. **`ProcessingActivity` (`__tablename__ = "processing_activities"`)**:
   - Authoritative GDPR Art. 30 Record of Processing Activities (RoPA) model with `activity_code`, `purpose`, `legal_basis` (`ProcessingLegalBasis`), `primary_data_subject_category` (`DataSubjectCategory`), `lifecycle_state` (`ProcessingLifecycleState`: `DRAFT`, `DPO_REVIEW`, `ACTIVE`, `SUSPENDED`, `ARCHIVED`, `RETIRED`), `dpo_approved_by_id`, `dpo_approved_at`, `retention_period_months`, and foreign keys to `business_process_id`, `ai_system_id`, `vendor_id`, `owner_id`.

3. **`DPIAAssessment` (`__tablename__ = "dpia_assessments"`)**:
   - Authoritative Data Protection Impact Assessment engine with deterministic inherent/residual risk scoring (`inherent_risk_score`, `residual_risk_score`, `risk_band` [`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`]), Four-Eyes DPO approval (`created_by_id != dpo_reviewed_by_id`), and links to `processing_activity_id`, `data_asset_id`, and `remediation_plan_id`.

4. **`DataTransferAssessment` (`__tablename__ = "data_transfer_assessments"`)**:
   - Authoritative cross-border Transfer Impact Assessment (TIA) engine with `source_jurisdiction`, `destination_jurisdiction`, `transfer_mechanism` (`TransferMechanism`), `transfer_risk_index`, `approval_status`, and Four-Eyes approval (`requested_by_id != approved_by_id`).

### 2.2 Mandatory Phase 16 Privacy Authority Matrix

| CONCEPT | EXISTING AUTHORITY | TABLE/MODEL | SERVICE | API | CAN EXTEND? | MUST NOT DUPLICATE? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Logical Data Asset Inventory** | Phase 16 `PRIVACY-GRC` | `data_assets` / `DataAsset` (`app/models/privacy.py`) | `PrivacyService` (`Extended by DataGovernanceService`) | `/api/v1/privacy/data-assets` + `/api/v1/data-governance/assets` | **YES** (Extend `DataAsset` in-place via migration `0024`) | **YES** (Never create `DataAsset2` or `governed_data_assets`) |
| **Static Sensitivity Baseline** | Phase 16 `PRIVACY-GRC` | `DataSensitivityLevel` (`app/models/privacy.py`) | `PrivacyService` | `/api/v1/privacy/data-assets` | **YES** (Map configurable `DataClassificationLevel` to `DataSensitivityLevel`) | **YES** (Do not break DPIA / RoPA consumers of `data_sensitivity_level`) |
| **Record of Processing Activities (RoPA)** | Phase 16 `PRIVACY-GRC` | `processing_activities` / `ProcessingActivity` | `PrivacyService` | `/api/v1/privacy/processing-activities` | **YES** (Link via `DataAssetProcessingLink` & `DataLineageEdge.processing_activity_id`) | **YES** (Never create `ProcessingActivity2` or `DataProcessingRegistry`) |
| **Privacy Impact Assessment (DPIA)** | Phase 16 `PRIVACY-GRC` | `dpia_assessments` / `DPIAAssessment` | `PrivacyService` | `/api/v1/privacy/dpias` | **NO** (Consume via `DPIAAssessment.data_asset_id`) | **YES** (Never create `DataRiskAssessment` or `DPIA2`) |
| **Cross-Border Data Transfers (TIA)** | Phase 16 `PRIVACY-GRC` | `data_transfer_assessments` / `DataTransferAssessment` | `PrivacyService` | `/api/v1/privacy/transfers` | **NO** (Consume via `DataTransferAssessment.data_asset_id`) | **YES** (Never create `CrossBorderFlow2`) |

---

## 3. Existing Phase 18 CloudSec Authority (`CLOUDSEC-GRC`)

Phase 18 (`CLOUDSEC-GRC`, migration `0015_cloudsec_and_posture_governance.py`) established the authoritative cloud infrastructure and posture engine in `backend/app/models/cloudsec.py` and `backend/app/services/cloudsec_service.py`.

### 3.1 Detailed Audit of `backend/app/models/cloudsec.py`
- **`CloudAsset` (`__tablename__ = "cloud_assets"`)**:
  - Represents physical/cloud infrastructure containers and compute/storage resources across `AWS`, `AZURE`, `GCP`, `OCI`, `HYBRID`, `ON_PREM`.
  - `resource_type` (`CloudResourceTypeEnum`): `S3_BUCKET`, `RDS_DATABASE`, `KEY_VAULT`, `EC2_INSTANCE`, `KUBERNETES_CLUSTER`, `IAM_ROLE`, `SECURITY_GROUP`, `SERVERLESS_FUNCTION`, `CONTAINER_REGISTRY`, `VIRTUAL_NETWORK`.
  - Tracks infrastructure posture & exposure: `resource_arn`, `region`, `environment`, `criticality`, `posture_status` (`COMPLIANT`, `DRIFTED`, `NON_COMPLIANT`, `EXEMPTED`), `posture_score` (`0..100`), `blast_radius_score` (`0..100`), `lifecycle_state` (`PROVISIONING`, `ACTIVE`, `MAINTENANCE`, `DECOMMISSIONED`), `is_internet_facing`, `encryption_enabled`, `public_access_blocked`, `logging_enabled`, `versioning_enabled`, `mfa_delete_enabled`.
- **`CloudMisconfigurationRule` (`cloud_misconfiguration_rules`)** & **`CloudSecurityFinding` (`cloud_security_findings`)**:
  - Evaluate infrastructure security rules against `CloudAsset` records and escalate to canonical `Finding` (`findings.id`) and `RemediationPlan` (`remediation_plans.id`).

### 3.2 Architectural Boundary: `CLOUD RESOURCE AUTHORITY` vs `DATA ASSET AUTHORITY`

| Dimension | `CLOUD RESOURCE AUTHORITY` (`CloudAsset` — Phase 18) | `DATA ASSET AUTHORITY` (`DataAsset` — Phase 16 + Batch 3) |
| :--- | :--- | :--- |
| **Canonical Table / Model** | `cloud_assets` / `CloudAsset` (`app/models/cloudsec.py`) | `data_assets` / `DataAsset` (`app/models/privacy.py`) |
| **Abstraction Layer** | **Infrastructure / Storage / Compute Resource** (Physical or virtual cloud container identified by `resource_arn`, e.g., AWS S3 Bucket `arn:aws:s3:::prod-eu-datalake`, RDS instance `prod-billing-db`). | **Logical Information / Dataset / Data Element Collection** (Governed information asset identified by `asset_code`, e.g., `DA-CUST-PII-01` Customer Master Dataset, `DA-FIN-GL-02` General Ledger Transactions). |
| **Cardinality & Linkage** | One `CloudAsset` (`RDS_DATABASE`, `S3_BUCKET`, etc.) can host `0..N` logical `DataAsset` datasets. | Each `DataAsset` optionally references its hosting infrastructure container via `DataAsset.cloud_asset_id` (`ForeignKey("cloud_assets.id", ondelete="SET NULL")`). |
| **Governance Responsibility** | Cloud Security Engineer / DevSecOps (`SECURITY_ANALYST`, `MANAGER`): manages encryption flags, public access blocks, IAM posture, network exposure. | Data Owner / Data Steward / DPO / GRC Analyst (`GRC_ANALYST`, `MANAGER`): manages data classification scheme, sensitivity level, data lineage, retention schedule, legal processing links, and disposal governance. |
| **Posture Interaction Invariant** | Cloud telemetry (`CloudAsset.encryption_enabled`, `is_internet_facing`, `posture_status`) provides **infrastructure posture context** to hosted `DataAsset` records (e.g., flagging a control gap if a `RESTRICTED_PII` `DataAsset` is hosted on an unencrypted or internet-facing `CloudAsset`). | Cloud telemetry **MUST NEVER** automatically overwrite or downgrade a `DataAsset`'s governed classification (`classification_level_id` / `data_sensitivity_level`). |

---

## 4. Existing Data Governance Concepts Across Repository

A full-repository search across `backend/app/models/` and `backend/app/services/` identified all existing classification, sensitivity, retention, and lineage constructs:

1. **Phase 16 `DataSensitivityLevel` (`backend/app/models/privacy.py`)**:
   - Values: `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED_PII`, `SPECIAL_CATEGORY_SENSITIVE_PHI`.
   - Used by `DataAsset.data_sensitivity_level` and consumed by `PrivacyService._calculate_dpia_scores()` (`SENSITIVITY_WEIGHTS`) and `PrivacyService._calculate_transfer_risk()`.
   - **Rule**: Must be preserved intact on `DataAsset` so Phase 16 DPIA and Transfer Risk calculations remain 100% deterministic and backward-compatible.
2. **Phase 9 TPRM `DataClassificationEnum` (`backend/app/models/tprm.py`)**:
   - Values: `RESTRICTED`, `CONFIDENTIAL`, `INTERNAL`, `PUBLIC`.
   - Scoped specifically to third-party vendor profile engagements (`Vendor.data_classification`).
3. **Phase 15 AI Governance `AIDataSensitivityEnum` (`backend/app/models/ai_governance.py`)**:
   - Values: `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `PII`, `PHI`, `PCI`, `BIOMETRIC`.
   - Scoped to `AISystem.training_data_sensitivity`. Note that `DataAsset` already links to `AISystem` via `DataAsset.ai_system_id`.
4. **Retention Fields**:
   - `DataAsset.retention_period_months` (`Integer`, nullable) and `ProcessingActivity.retention_period_months` (`Integer`, default `36`) already exist on `data_assets` and `processing_activities`.
5. **Frontend Lineage Placeholder (`frontend/src/components/privacy/PrivacyLineageCard.tsx`)**:
   - Renders visual badges for `DataAsset.business_process_id`, `ai_system_id`, `vendor_id`, and inferred `ProcessingActivity` records, but has **no asset-to-asset lineage graph (`source_data_asset_id -> target_data_asset_id`)**.

---

## 5. Complete Authority Matrix

Every mandatory domain concept from Section 6 of the specification is mapped below to its authoritative source in ControlSphere:

| # | Concept | Authoritative Status | Existing Authority (Phase / Module) | Table / Model | Batch 3 Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | **Data Asset** | **EXTEND EXISTING** | Phase 16 `PRIVACY-GRC` | `data_assets` / `DataAsset` (`app/models/privacy.py`) | Extend `DataAsset` in-place via migration `0024` with lifecycle, steward, cloud link, classification scheme/level FKs, and retirement metadata. |
| 2 | **Data Element / Field** | **EMBED IN EXISTING** | Phase 16 + Batch 3 | `DataAsset` + `DataClassificationRecord` | Represent governed schema elements/fields via structured metadata and classification records on `DataAsset` without exploding table count. |
| 3 | **Data Classification** | **NEW (EXTENDS PHASE 16)** | Batch 3 `DATA-GOVERNANCE-GRC` | `data_classification_schemes`, `data_classification_levels`, `data_classification_records` | Introduce configurable classification schemes, ordinal levels (mapped to `DataSensitivityLevel`), and Four-Eyes approval history. |
| 4 | **Data Sensitivity** | **REUSE EXISTING** | Phase 16 `PRIVACY-GRC` | `DataSensitivityLevel` on `DataAsset` | Keep `DataAsset.data_sensitivity_level` synchronized with approved `DataClassificationLevel.mapped_sensitivity_level`. |
| 5 | **Data Owner** | **REUSE + EXTEND** | Phase 16 `PRIVACY-GRC` | `DataAsset.owner_id` (`FK users.id`) | Reuse `DataAsset.owner_id`; add governed ownership assignment/transfer workflow with audit logging. |
| 6 | **Data Steward** | **EXTEND EXISTING** | Batch 3 `DATA-GOVERNANCE-GRC` | `DataAsset.steward_id` (`FK users.id`) | Add `steward_id` column on `DataAsset` to separate operational stewardship from accountable ownership. |
| 7 | **Data Custodian** | **REUSE VIA CLOUD/OWNER** | Phase 18 `CLOUDSEC-GRC` | `CloudAsset.owner_id` via `DataAsset.cloud_asset_id` | Derive infrastructure custodian from linked `CloudAsset.owner_id` (or optional custodian reference) without creating a duplicate identity table. |
| 8 | **Data Lineage** | **NEW AUTHORITY** | Batch 3 `DATA-GOVERNANCE-GRC` | `data_lineage_edges` / `DataLineageEdge` | Create append-only/versioned directed graph (`source_data_asset_id -> target_data_asset_id`) with cycle detection and SHA-256 provenance digest. |
| 9 | **Data Flow** | **INTEGRATED** | Batch 3 + Phase 16 | `DataLineageEdge` + `DataTransferAssessment` | Asset-to-asset internal/external data flows are modeled as `DataLineageEdge`; cross-border legal transfers remain in `DataTransferAssessment`. |
| 10 | **Data Retention** | **EXTEND EXISTING** | Phase 16 `PRIVACY-GRC` | `DataAsset.retention_period_months` + `DataClassificationLevel.default_retention_months` | Reuse `DataAsset.retention_period_months` and add `disposal_method`, `retired_at`, `retirement_evidence_id` on `DataAsset`. |
| 11 | **Data Disposal / Retirement** | **EXTEND EXISTING** | Batch 3 `DATA-GOVERNANCE-GRC` | `DataAsset` (`lifecycle_state = RETIRED`, `disposal_method`, `retirement_evidence_id`) | Enforce non-destructive governed retirement requiring `EvidenceItem` (`retirement_evidence_id`) for `RESTRICTED_PII` / `SPECIAL_CATEGORY_SENSITIVE_PHI` assets. |
| 12 | **Processing Activity** | **REUSE EXISTING** | Phase 16 `PRIVACY-GRC` | `processing_activities` / `ProcessingActivity` | Link `DataAsset` to `ProcessingActivity` via new M:N bridge `data_asset_processing_links` (`DataAssetProcessingLink`). Never duplicate `ProcessingActivity`. |
| 13 | **DPIA** | **REUSE EXISTING** | Phase 16 `PRIVACY-GRC` | `dpia_assessments` / `DPIAAssessment` | Reuse `DPIAAssessment.data_asset_id` directly. Never duplicate DPIA. |
| 14 | **Cross-Border Transfer** | **REUSE EXISTING** | Phase 16 `PRIVACY-GRC` | `data_transfer_assessments` / `DataTransferAssessment` | Reuse `DataTransferAssessment.data_asset_id` directly. Never duplicate TIA. |
| 15 | **Cloud Resource** | **REUSE EXISTING** | Phase 18 `CLOUDSEC-GRC` | `cloud_assets` / `CloudAsset` | Link via `DataAsset.cloud_asset_id` and `DataLineageEdge.cloud_asset_id`. Never duplicate `CloudAsset`. |
| 16 | **Control Mapping** | **NEW BRIDGE TO EXISTING** | Phase 2 `OrganizationControl` | `data_asset_control_links` / `DataAssetControlLink` | Map `DataAsset` to authoritative `OrganizationControl` (`organization_controls.id`). Never create `DataControl`. |
| 17 | **Evidence Mapping** | **REUSE VIA BRIDGE** | Phase 3 `EvidenceItem` | `DataAssetControlLink.evidence_item_id` + `DataAsset.retirement_evidence_id` | Link `DataAsset` controls and retirement records to authoritative `EvidenceItem` (`evidence_items.id`). Never create `DataEvidence`. |
| 18 | **Finding** | **REUSE EXISTING** | Phase 4 `Finding` | `findings` / `Finding` (`app/models/finding.py`) | Escalate governance/posture violations to canonical `Finding` (`source_type` / audit trail). Never create `DataFinding`. |
| 19 | **Risk** | **REUSE EXISTING** | Phase 5 `Risk` | `risks` / `Risk` (`app/models/risk.py`) | Link data governance exposures to canonical `Risk` (`risks.id`). Never create `DataRisk`. |
| 20 | **Remediation** | **REUSE EXISTING** | Phase 11 `RemediationPlan` | `remediation_plans` / `RemediationPlan` | Track corrective actions via canonical `RemediationPlan` (`remediation_plans.id`). Never create `DataRemediation`. |
| 21 | **Regulatory Obligation** | **REUSE EXISTING** | Phase 21 `REGULATORY-GRC` | `regulatory_obligations` / `RegulatoryObligation` | Trace `DataAsset` $\rightarrow$ `DataAssetControlLink` $\rightarrow$ `OrganizationControl` $\rightarrow$ `RegulatoryObligation.organization_control_id`. |

---

## 6. Proposed Domain Architecture

In accordance with Section 7 of the specification, every candidate entity was evaluated before inclusion. Only **5 new focused governance tables** (plus **in-place extension of `DataAsset`**) are justified:

### 6.1 Entity Evaluation Matrix

| Candidate Entity | Table Name | Classification | Why Existing Models Cannot Represent It Alone | Authoritative Lifecycle & Cardinality |
| :--- | :--- | :--- | :--- | :--- |
| **1. `DataAsset` (Extended In-Place)** | `data_assets` (existing table extended in `0024`) | **Core Domain Model (Extended)** | `DataAsset` already exists in `app/models/privacy.py`, so creating a second asset table is forbidden. Extending `data_assets` in-place adds lifecycle state (`DISCOVERED` $\rightarrow$ `RETIRED`), `steward_id`, `cloud_asset_id`, classification scheme/level FKs, Four-Eyes classification approval metadata, and retirement/disposal governance while keeping 100% backward compatibility with Phase 16. | `DISCOVERED` $\rightarrow$ `REGISTERED` $\rightarrow$ `CLASSIFIED` $\rightarrow$ `ACTIVE` $\rightarrow$ `DEPRECATED` $\rightarrow$ `RETIRED` (`1:N` with classification records, lineage edges, processing links, control links). |
| **2. `DataClassificationScheme`** | `data_classification_schemes` | **Core Domain Model** | Phase 16 only has a hardcoded Python enum (`DataSensitivityLevel`). Enterprise Data Governance requires organization-configurable classification taxonomies (e.g., ISO 27001 Corporate Taxonomy, GDPR/HIPAA Regulated Taxonomy, Defense/CUI Taxonomy) with versioning and Four-Eyes activation approval. | `DRAFT` $\rightarrow$ `PENDING_APPROVAL` $\rightarrow$ `ACTIVE` $\rightarrow$ `ARCHIVED` (`1:N` with `DataClassificationLevel`). |
| **3. `DataClassificationLevel`** | `data_classification_levels` | **Core Domain Model** | Defines the ordered levels within a `DataClassificationScheme` (`ordinal_rank` 1..10, `level_code`, `mapped_sensitivity_level` $\rightarrow$ `DataSensitivityLevel`, mandatory control flags `requires_encryption_at_rest`, `requires_encryption_in_transit`, `requires_four_eyes_approval`, `default_retention_months`, `required_disposal_method`). | Child of `DataClassificationScheme` (`uq_class_level_scheme_code`, `uq_class_level_scheme_rank`). |
| **4. `DataClassificationRecord`** | `data_classification_records` | **Core Domain Model (Immutable History / Approval Ledger)** | Mutating `DataAsset.data_sensitivity_level` in-place loses history and bypasses Four-Eyes approval on downgrades or restricted data classifications. `DataClassificationRecord` provides an append-only versioned audit & approval workflow (`INITIAL`, `UPGRADE`, `DOWNGRADE`, `REVALIDATION`) with `requested_by_id != approved_by_id` enforcement. | `PENDING_APPROVAL` $\rightarrow$ `APPROVED` / `REJECTED` $\rightarrow$ `SUPERSEDED` (`N:1` to `DataAsset`). |
| **5. `DataLineageEdge`** | `data_lineage_edges` | **Core Domain Model** | No model in the repository represents directed asset-to-asset data flows (`source_data_asset_id` $\rightarrow$ `target_data_asset_id`), transformation metadata, cycle validation, or cryptographic lineage provenance (`provenance_hash`). | `PENDING_APPROVAL` $\rightarrow$ `ACTIVE` $\rightarrow$ `SUPERSEDED` / `REVOKED` (`N:1` to source `DataAsset` and target `DataAsset`). |
| **6. `DataAssetProcessingLink`** | `data_asset_processing_links` | **Link / Join Model** | Currently `DataAsset` and `ProcessingActivity` have no M:N relationship (only `DPIAAssessment` links one activity and one asset during a DPIA). Explicit M:N linkage (`PRIMARY_SOURCE`, `INTERMEDIATE_STORE`, `OUTPUT_SINK`, `ARCHIVAL_STORE`) is required for GDPR Art. 30 RoPA completeness. | Active association record (`uq_data_asset_processing_link`). |
| **7. `DataAssetControlLink`** | `data_asset_control_links` | **Link / Join Model** | Links a `DataAsset` directly to authoritative `OrganizationControl` (`organization_controls.id`) and optional `EvidenceItem` (`evidence_items.id`) to verify that classification-mandated controls (encryption, access control, backup/retention) are implemented and evidenced. | Active association record (`uq_data_asset_control_link`). |

---

## 7. Data Asset Lifecycle

### 7.1 Authoritative Lifecycle States (`DataAssetLifecycleEnum`)
- `DISCOVERED`: Asset ingested or registered in initial discovery; owner assigned, steward/classification may still be pending.
- `REGISTERED`: Asset metadata, `owner_id`, and `steward_id` formally assigned.
- `CLASSIFIED`: Asset has an approved `DataClassificationRecord` (`classification_status = APPROVED`).
- `ACTIVE`: Asset is approved for production processing and linked to required controls/processing activities.
- `DEPRECATED`: Asset is scheduled for decommissioning/migration; new downstream lineage edges (`source_data_asset_id = this_asset`) are blocked unless explicitly overridden by `ADMIN`/`MANAGER`.
- `RETIRED`: Terminal governed state. Data has been disposed of or archived according to `disposal_method`; asset is read-only and immutable.

### 7.2 Allowed State Transitions & Guards
1. `DISCOVERED` $\rightarrow$ `REGISTERED` (Requires `owner_id` and `steward_id` to be set).
2. `DISCOVERED` / `REGISTERED` $\rightarrow$ `CLASSIFIED` (Requires `classification_status == APPROVED`).
3. `CLASSIFIED` / `REGISTERED` $\rightarrow$ `ACTIVE` (Requires `classification_status == APPROVED`; if `DataClassificationLevel.requires_encryption_at_rest == True`, validates encryption posture or logs governance warning).
4. `ACTIVE` / `CLASSIFIED` $\rightarrow$ `DEPRECATED` (Requires deprecation justification).
5. `DEPRECATED` / `ACTIVE` $\rightarrow$ `RETIRED` (**Non-Destructive Retirement Gate**:
   - Requires `disposal_method` (`CRYPTOGRAPHIC_ERASURE`, `SECURE_OVERWRITE`, `PHYSICAL_DESTRUCTION`, `ANONYMIZATION`) and `retirement_notes`.
   - For high-sensitivity assets (`RESTRICTED_PII`, `SPECIAL_CATEGORY_SENSITIVE_PHI`, or `DataClassificationLevel.requires_four_eyes_approval == True`), requires `retirement_evidence_id` referencing a valid same-tenant `EvidenceItem` AND Four-Eyes approval (`retired_by_id != retirement_approved_by_id`).
   - Automatically marks active outbound `DataLineageEdge` records where this asset is source/target as `REVOKED` or requires lineage revocation prior to retirement).
6. **Backward Compatibility Guarantee for Phase 16**:
   - Existing `POST /api/v1/privacy/data-assets` creates `DataAsset` records with default `lifecycle_state = DataAssetLifecycleEnum.ACTIVE` and `classification_status = DataClassificationApprovalStatusEnum.APPROVED` so all existing Phase 16 tests and workflows continue to pass without modification.
   - `DELETE /api/v1/privacy/data-assets/{id}` remains functional for legacy Phase 16 callers when no governed lineage/classification lock exists, while `/api/v1/data-governance/assets/{id}/retire` provides the authoritative non-destructive retirement workflow.

---

## 8. Classification Architecture

### 8.1 Configurable Schemes & Ordinal Levels
- **`DataClassificationScheme` (`data_classification_schemes`)**:
  - Allows each organization to define one or more classification schemes (with at most one `is_default = True` active scheme per organization).
  - Status lifecycle: `DRAFT` $\rightarrow$ `PENDING_APPROVAL` $\rightarrow$ `ACTIVE` $\rightarrow$ `ARCHIVED`.
  - Activating a scheme requires Four-Eyes approval (`created_by_id != approved_by_id`).
- **`DataClassificationLevel` (`data_classification_levels`)**:
  - Defines ordered classification tiers within a scheme:
    - `level_code` (e.g., `L1_PUBLIC`, `L2_INTERNAL`, `L3_CONFIDENTIAL`, `L4_RESTRICTED_PII`, `L5_CRITICAL_REGULATED`)
    - `ordinal_rank` (`Integer`, `1..10`, where higher rank = higher sensitivity/restriction)
    - `mapped_sensitivity_level` (`Enum(DataSensitivityLevel)` — maps every custom level deterministically to Phase 16 `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED_PII`, or `SPECIAL_CATEGORY_SENSITIVE_PHI`)
    - `requires_encryption_at_rest` (`Boolean`)
    - `requires_encryption_in_transit` (`Boolean`)
    - `requires_four_eyes_approval` (`Boolean`)
    - `default_retention_months` (`Integer`, nullable)
    - `required_disposal_method` (`Enum(DataDisposalMethodEnum)`, nullable)

### 8.2 Governed Classification Workflow & Four-Eyes Enforcement
- When a user classifies or reclassifies a `DataAsset` via `POST /api/v1/data-governance/assets/{id}/classifications`:
  1. System determines `change_type`:
     - `INITIAL`: First formal classification record on the asset.
     - `UPGRADE`: New level has higher `ordinal_rank` (or higher sensitivity weight) than the current level.
     - `DOWNGRADE`: New level has lower `ordinal_rank` (or lower sensitivity weight) than the current level.
     - `REVALIDATION`: Periodic review confirming the same level.
  2. **Four-Eyes Approval Requirement**:
     - If `change_type == DOWNGRADE` **OR** `target_level.requires_four_eyes_approval == True` **OR** `target_level.mapped_sensitivity_level in (RESTRICTED_PII, SPECIAL_CATEGORY_SENSITIVE_PHI)`:
       - Record is created in `status = PENDING_APPROVAL` with `requested_by_id = current_user.id`.
       - `DataAsset.classification_status` becomes `PENDING_APPROVAL` (the currently active `data_sensitivity_level` and `classification_level_id` on `DataAsset` are **NOT** mutated until approved, preventing unapproved downgrades from weakening DPIA scores).
       - Approval via `POST /api/v1/data-governance/classifications/{record_id}/approve` enforces `record.requested_by_id != current_user.id` (`HTTP 403 Forbidden` on self-approval).
       - Upon approval, previous `APPROVED` record on the asset transitions to `SUPERSEDED`, the new record becomes `APPROVED`, and `DataAsset` updates `classification_scheme_id`, `classification_level_id`, `data_sensitivity_level = level.mapped_sensitivity_level`, `classification_status = APPROVED`, `classified_by_id = record.requested_by_id`, `classification_approved_by_id = current_user.id`, `classification_approved_at = now()`.
     - If `change_type in (INITIAL, UPGRADE, REVALIDATION)` AND `not target_level.requires_four_eyes_approval` AND `target_level.mapped_sensitivity_level not in (RESTRICTED_PII, SPECIAL_CATEGORY_SENSITIVE_PHI)`:
       - Can be immediately marked `APPROVED` (or optionally submitted for approval if `require_approval=True` is requested), while still writing an immutable `DataClassificationRecord`.

---

## 9. Ownership & Stewardship Architecture

1. **Accountable Data Owner (`DataAsset.owner_id`)**:
   - Mandatory (`nullable=False`, FK `users.id`). Represents the executive/business owner accountable for the dataset's risk, legal compliance, and classification.
2. **Operational Data Steward (`DataAsset.steward_id`)**:
   - Added on `DataAsset` (`nullable=True`, FK `users.id`). Represents the domain specialist responsible for day-to-day metadata curation, lineage maintenance, control mapping, and quality/retention monitoring.
3. **Tenant Membership Validation**:
   - Both `owner_id` and `steward_id` MUST belong to the exact same `organization_id` as the `DataAsset` (`User.organization_id == organization_id` and `User.is_active == True`). Assigning a cross-tenant user ID is rejected with `HTTP 404 Not Found` (anti-enumeration).
4. **Governed Ownership / Stewardship Assignment & Transfer**:
   - `POST /api/v1/data-governance/assets/{id}/ownership` updates `owner_id` and/or `steward_id`, validates tenant membership, updates `last_reviewed_at`, and records a tamper-evident `AuditLog` entry capturing `previous_owner_id`, `new_owner_id`, `previous_steward_id`, `new_steward_id`, and `justification`.

---

## 10. Lineage Architecture (`DataLineageEdge`)

### 10.1 Directed Asset-to-Asset Graph Model
- Table: `data_lineage_edges` (`DataLineageEdge`):
  - `id` (`Integer`, PK)
  - `organization_id` (`Integer`, FK `organizations.id`, NOT NULL, indexed)
  - `edge_code` (`String(64)`, NOT NULL, unique per organization `uq_lineage_edge_org_code`)
  - `source_data_asset_id` (`Integer`, FK `data_assets.id`, NOT NULL, indexed)
  - `target_data_asset_id` (`Integer`, FK `data_assets.id`, NOT NULL, indexed)
  - `relationship_type` (`Enum(DataLineageRelationshipTypeEnum)`: `INGESTION`, `ETL_TRANSFORMATION`, `REPLICATION`, `AGGREGATION`, `EXPORT_SHARE`, `AI_TRAINING_FEED`, `ARCHIVE_FEED`)
  - `transformation_summary` (`Text`, nullable — describes filtering, aggregation, masking, or pseudonymization applied in transit)
  - `field_mapping_manifest` (`JSON`, nullable — optional structured list of `{source_field, target_field, transformation_type}`)
  - `is_encrypted_in_transit` (`Boolean`, default `True`)
  - `is_masked_or_anonymized` (`Boolean`, default `False`)
  - `processing_activity_id` (`Integer`, FK `processing_activities.id`, nullable, indexed)
  - `cloud_asset_id` (`Integer`, FK `cloud_assets.id`, nullable, indexed — target or transit infrastructure resource)
  - `version` (`Integer`, default `1`, NOT NULL)
  - `status` (`Enum(DataLineageStatusEnum)`: `PENDING_APPROVAL`, `ACTIVE`, `SUPERSEDED`, `REVOKED`, default `ACTIVE`)
  - `provenance_hash` (`String(64)`, NOT NULL — deterministic SHA-256 hex digest of canonical JSON `{organization_id, edge_code, version, source_data_asset_id, target_data_asset_id, relationship_type, transformation_summary, processing_activity_id, cloud_asset_id}`)
  - `created_by_id` (`Integer`, FK `users.id`, nullable)
  - `approved_by_id` (`Integer`, FK `users.id`, nullable)
  - `approved_at` (`DateTime(timezone=True)`, nullable)
  - `revoked_by_id` (`Integer`, FK `users.id`, nullable)
  - `revoked_at` (`DateTime(timezone=True)`, nullable)
  - `revocation_reason` (`Text`, nullable)
  - `effective_from` (`DateTime(timezone=True)`, default `now()`)
  - `effective_to` (`DateTime(timezone=True)`, nullable)

### 10.2 Lineage Graph Integrity & Security Invariants
1. **Self-Loop Prohibition**: `source_data_asset_id == target_data_asset_id` is rejected at both service layer (`HTTP 422`) and DB `CheckConstraint("source_data_asset_id != target_data_asset_id")`.
2. **Cycle Prevention (DAG Invariant)**: Before inserting or activating an edge `u -> v`, the service traverses active outbound edges starting from `v` within `organization_id` (BFS/DFS bounded traversal). If `u` is reachable from `v`, the edge would create a cycle in active lineage and is rejected with `HTTP 422 Unprocessable Entity` (`"Lineage cycle detected"`).
3. **Sensitivity Propagation Guard**: If `source_asset` has higher sensitivity than `target_asset` (e.g. `RESTRICTED_PII` flowing into a `PUBLIC` or `INTERNAL` asset) AND `is_masked_or_anonymized == False`, the lineage edge **cannot** become `ACTIVE` automatically — it is forced into `status = PENDING_APPROVAL` and requires Four-Eyes approval (`created_by_id != approved_by_id`) or target asset reclassification.
4. **Append-Only / Versioned Immutability**: Active lineage edges cannot be overwritten in-place to point to different assets; updating transformation details creates `version = previous.version + 1`, marks the prior version `SUPERSEDED` (`effective_to = now()`), and computes a new deterministic `provenance_hash`.

---

## 11. Privacy Integration (Phase 16 `PRIVACY-GRC`)

Batch 3 integrates natively with Phase 16 without duplicating a single privacy model or breaking any existing `/api/v1/privacy` endpoint:

1. **Shared `DataAsset` Table (`data_assets`)**:
   - `PrivacyService` (`app/services/privacy_service.py`) and `DataGovernanceService` (`app/services/data_governance_service.py`) operate on the exact same `DataAsset` SQLAlchemy model.
   - When `DataGovernanceService` approves a `DataClassificationRecord`, it updates `DataAsset.data_sensitivity_level` to `level.mapped_sensitivity_level`. Consequently, `PrivacyService.create_dpia()` and `PrivacyService.create_transfer_assessment()` automatically consume the governed sensitivity level when computing `inherent_risk_score` and `transfer_risk_index`.
2. **Explicit M:N RoPA Bridge (`DataAssetProcessingLink`)**:
   - Table `data_asset_processing_links` connects `DataAsset.id` and `ProcessingActivity.id` with `usage_role` (`PRIMARY_SOURCE`, `INTERMEDIATE_STORE`, `OUTPUT_SINK`, `ARCHIVAL_STORE`), `data_element_categories` (JSON), and `linked_by_id`.
   - Solves the Phase 16 limitation where `DataAsset` and `ProcessingActivity` could only be correlated indirectly via `business_process_id`.
3. **Lineage-to-RoPA & DPIA Traceability**:
   - `DataLineageEdge.processing_activity_id` optionally links a specific data flow edge to the authorizing GDPR Art. 30 `ProcessingActivity`.
   - `DataGovernanceService.get_asset_governance_dossier(asset_id)` aggregates the asset's classification history, upstream/downstream lineage graph, linked `ProcessingActivity` records, Phase 16 `DPIAAssessment` records, and Phase 16 `DataTransferAssessment` records in a single unified view.

---

## 12. Cloud Integration (Phase 18 `CLOUDSEC-GRC`)

Batch 3 connects logical data governance (`DataAsset`) to physical/cloud infrastructure posture (`CloudAsset`) cleanly:

1. **Hosting Linkage (`DataAsset.cloud_asset_id`)**:
   - `DataAsset.cloud_asset_id` (`ForeignKey("cloud_assets.id", ondelete="SET NULL")`) links a logical dataset to its hosting `CloudAsset` (`S3_BUCKET`, `RDS_DATABASE`, `KEY_VAULT`, etc.).
   - Validated for same-tenant ownership (`CloudAsset.organization_id == organization_id`).
2. **Posture Alignment & Drift Detection (Without Overwriting Classification)**:
   - `DataGovernanceService` inspects the linked `CloudAsset` posture whenever evaluating a `DataAsset`:
     - **Encryption Mismatch**: If `DataAsset` is classified at a level where `requires_encryption_at_rest == True` (or `DataAsset.data_sensitivity_level in (CONFIDENTIAL, RESTRICTED_PII, SPECIAL_CATEGORY_SENSITIVE_PHI)`), but `CloudAsset.encryption_enabled == False`, the asset posture evaluation flags `CLOUD_ENCRYPTION_MISMATCH`.
     - **Public Exposure Mismatch**: If a non-`PUBLIC` `DataAsset` is linked to a `CloudAsset` where `is_internet_facing == True` or `public_access_blocked == False`, the asset posture evaluation flags `CLOUD_PUBLIC_EXPOSURE_MISMATCH`.
     - **Decommissioned Host Mismatch**: If an `ACTIVE` `DataAsset` is linked to a `CloudAsset` with `lifecycle_state == DECOMMISSIONED`, flags `CLOUD_HOST_DECOMMISSIONED`.
   - **Strict Non-Overwrite Invariant**: Cloud posture evaluation never mutates `DataAsset.classification_level_id` or `DataAsset.data_sensitivity_level`. Instead, mismatches surface in the Data Governance posture summary and can optionally generate a canonical Phase 4 `Finding` (`findings`) or link to an existing `CloudSecurityFinding`.

---

## 13. Control & Evidence Integration (Phases 2, 3, 4, 5, 11)

1. **Authoritative Control Mapping (`DataAssetControlLink`)**:
   - Table `data_asset_control_links` links `data_asset_id` (`FK data_assets.id`) to `organization_control_id` (`FK organization_controls.id`) and optional `evidence_item_id` (`FK evidence_items.id`), with `control_objective` (`ENCRYPTION_AT_REST`, `ENCRYPTION_IN_TRANSIT`, `ACCESS_CONTROL`, `RETENTION_ENFORCEMENT`, `DLP_MONITORING`, `BACKUP_RECOVERY`, `DISPOSAL_VERIFICATION`) and `coverage_notes`.
   - Enforces same-tenant validation on `DataAsset`, `OrganizationControl`, and `EvidenceItem`.
2. **Retirement Evidence (`DataAsset.retirement_evidence_id`)**:
   - Links `DataAsset.retirement_evidence_id` directly to `evidence_items.id` (`EvidenceItem`), ensuring data disposal certificates / cryptographic erasure logs are stored in the platform's single authoritative Evidence Repository.
3. **Reuse of Canonical `Finding`, `Risk`, and `RemediationPlan`**:
   - No `DataFinding`, `DataRisk`, or `DataRemediation` tables are created. Governance exceptions (e.g., unclassified active high-volume assets, cloud encryption mismatches, overdue retention reviews) reference or create standard `Finding`, `Risk`, and `RemediationPlan` records.

---

## 14. Regulatory Integration (Phase 21 `REGULATORY-GRC`)

- Phase 21 `RegulatoryObligation` (`backend/app/models/regulatory.py`) maps regulatory mandates (e.g., GDPR Art. 5/30/32, HIPAA Security Rule, CCPA, DORA, PCI-DSS Req 3) to `organization_control_id` (`ForeignKey("organization_controls.id")`).
- Through `DataAssetControlLink` (`DataAsset` $\rightarrow$ `OrganizationControl`) and `RegulatoryObligation` (`OrganizationControl` $\rightarrow$ `RegulatoryObligation` $\rightarrow$ `RegulatorySource`), `DataGovernanceService` provides full end-to-end regulatory traceability for every `DataAsset` without adding any duplicate regulatory tables.

---

## 15. Continuous Assurance Integration (Phase 23 `CONTINUOUS-GRC`)

- Phase 23 `ContinuousComplianceService` (`backend/app/services/continuous_compliance_service.py`) computes enterprise assurance scores and stores `pillar_breakdown` JSON on `ContinuousAssuranceSnapshot`.
- `DataGovernanceService.get_governance_summary(db, organization_id)` exposes deterministic metrics (`total_assets`, `classified_ratio`, `owner_assigned_ratio`, `steward_assigned_ratio`, `lineage_coverage_ratio`, `control_mapped_ratio`, `cloud_posture_aligned_ratio`, `pending_approvals_count`, `governance_health_score` `0..100`) that can be consumed directly by `ContinuousComplianceService` and executive reporting without altering Phase 23 table schemas.

---

## 16. Executive GRC Integration (Phase 20 `EXECUTIVE-GRC`)

- Phase 20 `ExecutiveService` (`backend/app/services/executive_service.py`) aggregates domain telemetry into `ExecutiveSnapshot.domain_posture_breakdown` (JSON) and `source_manifest` (JSON) using deterministic canonical JSON hashing (`compute_canonical_sha256`).
- Batch 3 provides a deterministic `DataGovernanceService.get_executive_telemetry(db, organization_id)` helper returning canonical key-sorted metrics (`total_data_assets`, `restricted_assets_count`, `unclassified_assets_count`, `lineage_edges_active`, `cloud_alignment_rate`, `data_governance_score`) ready for inclusion in executive posture snapshots without modifying `ExecutiveSnapshot` schema columns.

---

## 17. RBAC Matrix

### 17.1 Strict Role Preservation
The platform's exact 6 canonical roles in `UserRole` (`backend/app/models/user.py` and `backend/app/core/permissions.py`) are strictly preserved:
- `ADMIN`
- `MANAGER`
- `GRC_ANALYST`
- `SECURITY_ANALYST`
- `AUDITOR`
- `VIEWER`

**Zero new roles** (`DATA_OWNER`, `DATA_STEWARD`, `CHIEF_DATA_OFFICER`, `PRIVACY_OFFICER`, etc.) are added. Data Owner and Data Steward are per-asset user assignments (`DataAsset.owner_id`, `DataAsset.steward_id`) governed by the permission matrix below.

### 17.2 Minimum New Permissions (`backend/app/core/permissions.py`)

| Permission Enum | Permission Value | `ADMIN` | `MANAGER` | `GRC_ANALYST` | `SECURITY_ANALYST` | `AUDITOR` | `VIEWER` |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `DATA_GOV_READ` | `"data_gov:read"` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `DATA_GOV_MANAGE` | `"data_gov:manage"` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| `DATA_GOV_CLASSIFY` | `"data_gov:classify"` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `DATA_GOV_APPROVE` | `"data_gov:approve"` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `DATA_GOV_LINEAGE_MANAGE` | `"data_gov:lineage_manage"` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `DATA_GOV_OWNER_MANAGE` | `"data_gov:owner_manage"` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |

### 17.3 Endpoint-Level Authorization Summary
- **Read Inventory, Schemes, Levels, Classifications, Lineage, Summary (`GET`)**: Requires `Permission.DATA_GOV_READ` (All 6 roles; `AUDITOR` and `VIEWER` are strictly read-only).
- **Create/Update Classification Scheme & Levels, Register/Update Data Asset, Link Processing Activity or Control (`POST`/`PUT`)**: Requires `Permission.DATA_GOV_MANAGE` (`ADMIN`, `MANAGER`, `GRC_ANALYST`).
- **Submit Asset Classification / Reclassification (`POST .../classifications`)**: Requires `Permission.DATA_GOV_CLASSIFY` (`ADMIN`, `MANAGER`, `GRC_ANALYST`, `SECURITY_ANALYST`).
- **Create / Supersede / Revoke Lineage Edge (`POST .../lineage-edges`, `POST .../revoke`)**: Requires `Permission.DATA_GOV_LINEAGE_MANAGE` (`ADMIN`, `MANAGER`, `GRC_ANALYST`, `SECURITY_ANALYST`).
- **Assign / Transfer Asset Owner or Steward (`POST .../ownership`)**: Requires `Permission.DATA_GOV_OWNER_MANAGE` (`ADMIN`, `MANAGER`, `GRC_ANALYST`).
- **Approve Classification Scheme, Approve Classification Record (Downgrade / Restricted), Approve Lineage Edge, or Approve/Execute Governed Asset Retirement (`POST .../approve`, `POST .../retire`)**: Requires `Permission.DATA_GOV_APPROVE` (`ADMIN`, `MANAGER` ONLY, plus Four-Eyes `requester_id != approver_id`).

---

## 18. Four-Eyes / Segregation of Duties (SoD) Matrix

| Governance Action | Initiator Field | Approver Field | Required Approver Permission | Four-Eyes Invariant (`Initiator != Approver`) | Self-Approval Response |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Activate Classification Scheme** | `scheme.created_by_id` | `scheme.approved_by_id` | `Permission.DATA_GOV_APPROVE` (`ADMIN`, `MANAGER`) | `scheme.created_by_id != current_user.id` | `HTTP 403 Forbidden` (`"Segregation of Duties violation: scheme creator cannot approve activation"`) |
| **2. Approve Classification Downgrade or Restricted Classification** | `record.requested_by_id` | `record.approved_by_id` | `Permission.DATA_GOV_APPROVE` (`ADMIN`, `MANAGER`) | `record.requested_by_id != current_user.id` | `HTTP 403 Forbidden` (`"Segregation of Duties violation: requester cannot self-approve classification"` ) |
| **3. Approve Sensitivity-Downgrading Lineage Edge** | `edge.created_by_id` | `edge.approved_by_id` | `Permission.DATA_GOV_APPROVE` (`ADMIN`, `MANAGER`) | `edge.created_by_id != current_user.id` | `HTTP 403 Forbidden` (`"Segregation of Duties violation: lineage creator cannot self-approve restricted flow"`) |
| **4. Retire Restricted / High-Sensitivity Data Asset** | `asset.retirement_requested_by_id` (or `owner_id` / initiator) | `asset.retired_by_id` | `Permission.DATA_GOV_APPROVE` (`ADMIN`, `MANAGER`) | For `PENDING_RETIREMENT` or restricted assets with prior classification/request initiator, `initiator_id != current_user.id` (and requires `retirement_evidence_id`) | `HTTP 403 Forbidden` / `HTTP 422 Unprocessable Entity` if `retirement_evidence_id` missing |

---

## 19. Tenant Isolation Model

1. **Zero Client-Supplied `organization_id` Trust**:
   - Every Pydantic request schema (`DataClassificationSchemeCreate`, `DataClassificationLevelCreate`, `DataAssetGovernanceCreate`, `DataClassificationRecordCreate`, `DataLineageEdgeCreate`, `DataAssetProcessingLinkCreate`, `DataAssetControlLinkCreate`) **omits** `organization_id`.
   - `organization_id` is always extracted exclusively from the authenticated `current_user.organization_id` JWT context.
2. **Cross-Tenant Foreign Key Validation with Anti-Enumeration (`HTTP 404`)**:
   - Every referenced foreign key (`owner_id`, `steward_id`, `cloud_asset_id`, `business_process_id`, `ai_system_id`, `vendor_id`, `classification_scheme_id`, `classification_level_id`, `source_data_asset_id`, `target_data_asset_id`, `processing_activity_id`, `organization_control_id`, `evidence_item_id`) is queried with `.filter(Model.id == target_id, Model.organization_id == organization_id)`.
   - If a referenced entity does not exist or belongs to another organization, the service raises `HTTP 404 Not Found` (never `403`), preventing cross-tenant ID enumeration.

---

## 20. Concurrency & Idempotency Model

1. **Database Uniqueness Constraints**:
   - `uq_data_asset_org_code`: `UniqueConstraint("organization_id", "asset_code")` on `data_assets` (existing).
   - `uq_class_scheme_org_code_ver`: `UniqueConstraint("organization_id", "scheme_code", "version")` on `data_classification_schemes`.
   - `uq_class_level_scheme_code`: `UniqueConstraint("scheme_id", "level_code")` on `data_classification_levels`.
   - `uq_class_level_scheme_rank`: `UniqueConstraint("scheme_id", "ordinal_rank")` on `data_classification_levels`.
   - `uq_lineage_edge_org_code_ver`: `UniqueConstraint("organization_id", "edge_code", "version")` on `data_lineage_edges`.
   - `uq_data_asset_processing_link`: `UniqueConstraint("organization_id", "data_asset_id", "processing_activity_id")` on `data_asset_processing_links`.
   - `uq_data_asset_control_link`: `UniqueConstraint("organization_id", "data_asset_id", "organization_control_id")` on `data_asset_control_links`.
2. **Idempotent / Conflict-Safe State Transitions**:
   - Submitting duplicate `scheme_code + version`, `edge_code + version`, or duplicate M:N links catches `IntegrityError` (or pre-checks within the transaction) and returns `HTTP 409 Conflict`.
   - Re-approving an already `APPROVED`, `REJECTED`, `SUPERSEDED`, or `REVOKED` classification record or lineage edge returns `HTTP 409 Conflict` (`"Record is already in terminal/approved state"`).
   - Retiring an already `RETIRED` asset returns `HTTP 409 Conflict`.

---

## 21. Audit Logging Model

All state-changing operations in `DataGovernanceService` invoke `AuditService.log()` (`backend/app/services/audit_service.py`) within the transaction, recording `organization_id`, `actor_id`, `actor_email`, `action`, `resource_type`, `resource_id`, and structured `details`:

| Action Constant | Resource Type | Triggering Operation | Details Captured |
| :--- | :--- | :--- | :--- |
| `DATA_GOV_SCHEME_CREATED` | `data_classification_scheme` | Create classification scheme | `scheme_code`, `version`, `is_default` |
| `DATA_GOV_SCHEME_SUBMITTED` | `data_classification_scheme` | Submit scheme for approval | `scheme_code`, `status` |
| `DATA_GOV_SCHEME_APPROVED` | `data_classification_scheme` | Four-Eyes approve scheme | `scheme_code`, `created_by_id`, `approved_by_id` |
| `DATA_GOV_LEVEL_CREATED` | `data_classification_level` | Add level to scheme | `scheme_id`, `level_code`, `ordinal_rank`, `mapped_sensitivity_level` |
| `DATA_GOV_ASSET_REGISTERED` | `data_asset` | Register/create governed asset | `asset_code`, `lifecycle_state`, `owner_id`, `steward_id`, `cloud_asset_id` |
| `DATA_GOV_ASSET_OWNERSHIP_UPDATED` | `data_asset` | Assign/transfer owner or steward | `previous_owner_id`, `new_owner_id`, `previous_steward_id`, `new_steward_id`, `justification` |
| `DATA_GOV_CLASSIFICATION_REQUESTED` | `data_classification_record` | Submit asset classification | `data_asset_id`, `change_type`, `previous_sensitivity`, `new_sensitivity`, `status` |
| `DATA_GOV_CLASSIFICATION_APPROVED` | `data_classification_record` | Four-Eyes approve classification | `data_asset_id`, `record_id`, `requested_by_id`, `approved_by_id`, `new_sensitivity` |
| `DATA_GOV_CLASSIFICATION_REJECTED` | `data_classification_record` | Reject pending classification | `data_asset_id`, `record_id`, `rejected_by_id`, `rejection_reason` |
| `DATA_GOV_LINEAGE_CREATED` | `data_lineage_edge` | Create/version lineage edge | `edge_code`, `version`, `source_data_asset_id`, `target_data_asset_id`, `provenance_hash`, `status` |
| `DATA_GOV_LINEAGE_APPROVED` | `data_lineage_edge` | Approve pending lineage edge | `edge_code`, `created_by_id`, `approved_by_id`, `provenance_hash` |
| `DATA_GOV_LINEAGE_REVOKED` | `data_lineage_edge` | Revoke active lineage edge | `edge_code`, `revoked_by_id`, `revocation_reason` |
| `DATA_GOV_PROCESSING_LINKED` | `data_asset_processing_link` | Link asset to `ProcessingActivity` | `data_asset_id`, `processing_activity_id`, `usage_role` |
| `DATA_GOV_CONTROL_LINKED` | `data_asset_control_link` | Link asset to `OrganizationControl` | `data_asset_id`, `organization_control_id`, `evidence_item_id`, `control_objective` |
| `DATA_GOV_ASSET_DEPRECATED` | `data_asset` | Transition asset to `DEPRECATED` | `asset_code`, `previous_state`, `deprecation_notes` |
| `DATA_GOV_ASSET_RETIRED` | `data_asset` | Governed asset retirement | `asset_code`, `disposal_method`, `retirement_evidence_id`, `retired_by_id` |

---

## 22. Database & Migration Plan (`0024_data_governance_and_lineage.py`)

- **Migration File**: `backend/alembic/versions/0024_data_governance_and_lineage.py`
- **Revision ID**: `"0024"`
- **Down Revision**: `"0023"` (`0023_kri_and_risk_appetite_governance.py`)
- **Operations**:
  1. **Create `data_classification_schemes`**:
     - `id`, `organization_id` (FK `organizations.id`), `scheme_code` (`String(64)`), `name` (`String(255)`), `description` (`Text`), `version` (`Integer`, default `1`), `status` (`DataClassificationSchemeStatusEnum`: `DRAFT`, `PENDING_APPROVAL`, `ACTIVE`, `ARCHIVED`), `is_default` (`Boolean`, default `False`), `created_by_id` (FK `users.id`), `approved_by_id` (FK `users.id`), `approved_at` (`DateTime`), `created_at`, `updated_at`.
     - Constraints: `uq_class_scheme_org_code_ver` (`organization_id`, `scheme_code`, `version`), `ck_class_scheme_version_positive` (`version >= 1`).
  2. **Create `data_classification_levels`**:
     - `id`, `organization_id` (FK `organizations.id`), `scheme_id` (FK `data_classification_schemes.id`, `ondelete="CASCADE"`), `level_code` (`String(64)`), `name` (`String(128)`), `description` (`Text`), `ordinal_rank` (`Integer`), `mapped_sensitivity_level` (`Enum(DataSensitivityLevel)`), `color_hex` (`String(16)`), `requires_encryption_at_rest` (`Boolean`, default `True`), `requires_encryption_in_transit` (`Boolean`, default `True`), `requires_four_eyes_approval` (`Boolean`, default `False`), `default_retention_months` (`Integer`, nullable), `required_disposal_method` (`DataDisposalMethodEnum`, nullable), `created_at`, `updated_at`.
     - Constraints: `uq_class_level_scheme_code` (`scheme_id`, `level_code`), `uq_class_level_scheme_rank` (`scheme_id`, `ordinal_rank`), `ck_class_level_rank_bounds` (`ordinal_rank >= 1 AND ordinal_rank <= 10`).
  3. **Extend `data_assets` (In-Place via `op.add_column` / batch mode where needed)**:
     - `asset_type` (`DataAssetTypeEnum`: `DATABASE_TABLE`, `DATA_LAKE_DATASET`, `OBJECT_STORAGE_BUCKET`, `DOCUMENT_REPOSITORY`, `MESSAGE_STREAM`, `API_FEED`, `FEATURE_STORE`, `ARCHIVE_BACKUP`, server_default=`'DATABASE_TABLE'`, nullable=False)
     - `lifecycle_state` (`DataAssetLifecycleEnum`: `DISCOVERED`, `REGISTERED`, `CLASSIFIED`, `ACTIVE`, `DEPRECATED`, `RETIRED`, server_default=`'ACTIVE'`, nullable=False)
     - `steward_id` (`Integer`, FK `users.id`, nullable=True, indexed)
     - `cloud_asset_id` (`Integer`, FK `cloud_assets.id`, nullable=True, indexed)
     - `classification_scheme_id` (`Integer`, FK `data_classification_schemes.id`, nullable=True, indexed)
     - `classification_level_id` (`Integer`, FK `data_classification_levels.id`, nullable=True, indexed)
     - `classification_status` (`DataClassificationApprovalStatusEnum`: `UNCLASSIFIED`, `PENDING_APPROVAL`, `APPROVED`, `REJECTED`, server_default=`'APPROVED'`, nullable=False)
     - `classified_by_id` (`Integer`, FK `users.id`, nullable=True)
     - `classification_approved_by_id` (`Integer`, FK `users.id`, nullable=True)
     - `classification_approved_at` (`DateTime(timezone=True)`, nullable=True)
     - `disposal_method` (`DataDisposalMethodEnum`: `CRYPTOGRAPHIC_ERASURE`, `SECURE_OVERWRITE`, `PHYSICAL_DESTRUCTION`, `ANONYMIZATION`, `NONE`, nullable=True)
     - `last_reviewed_at` (`DateTime(timezone=True)`, nullable=True)
     - `retired_at` (`DateTime(timezone=True)`, nullable=True)
     - `retired_by_id` (`Integer`, FK `users.id`, nullable=True)
     - `retirement_notes` (`Text`, nullable=True)
     - `retirement_evidence_id` (`Integer`, FK `evidence_items.id`, nullable=True)
  4. **Create `data_classification_records`**:
     - `id`, `organization_id` (FK `organizations.id`), `data_asset_id` (FK `data_assets.id`, `ondelete="CASCADE"`), `scheme_id` (FK `data_classification_schemes.id`), `level_id` (FK `data_classification_levels.id`), `previous_sensitivity_level` (`Enum(DataSensitivityLevel)`, nullable), `new_sensitivity_level` (`Enum(DataSensitivityLevel)`, NOT NULL), `change_type` (`DataClassificationChangeTypeEnum`: `INITIAL`, `UPGRADE`, `DOWNGRADE`, `REVALIDATION`), `status` (`DataClassificationRecordStatusEnum`: `PENDING_APPROVAL`, `APPROVED`, `REJECTED`, `SUPERSEDED`), `justification` (`Text`, NOT NULL), `requested_by_id` (FK `users.id`, NOT NULL), `approved_by_id` (FK `users.id`, nullable), `approved_at` (`DateTime(timezone=True)`, nullable), `rejection_reason` (`Text`, nullable), `created_at`, `updated_at`.
  5. **Create `data_lineage_edges`**:
     - `id`, `organization_id` (FK `organizations.id`), `edge_code` (`String(64)`), `version` (`Integer`, default `1`), `source_data_asset_id` (FK `data_assets.id`, `ondelete="RESTRICT"`), `target_data_asset_id` (FK `data_assets.id`, `ondelete="RESTRICT"`), `relationship_type` (`DataLineageRelationshipTypeEnum`), `transformation_summary` (`Text`), `field_mapping_manifest` (`JSON`), `is_encrypted_in_transit` (`Boolean`, default `True`), `is_masked_or_anonymized` (`Boolean`, default `False`), `processing_activity_id` (FK `processing_activities.id`, nullable), `cloud_asset_id` (FK `cloud_assets.id`, nullable), `status` (`DataLineageStatusEnum`), `provenance_hash` (`String(64)`), `created_by_id` (FK `users.id`), `approved_by_id` (FK `users.id`), `approved_at` (`DateTime`), `revoked_by_id` (FK `users.id`), `revoked_at` (`DateTime`), `revocation_reason` (`Text`), `effective_from` (`DateTime`), `effective_to` (`DateTime`), `created_at`, `updated_at`.
     - Constraints: `uq_lineage_edge_org_code_ver` (`organization_id`, `edge_code`, `version`), `ck_lineage_no_self_loop` (`source_data_asset_id != target_data_asset_id`), `ck_lineage_version_positive` (`version >= 1`).
  6. **Create `data_asset_processing_links`**:
     - `id`, `organization_id` (FK `organizations.id`), `data_asset_id` (FK `data_assets.id`, `ondelete="CASCADE"`), `processing_activity_id` (FK `processing_activities.id`, `ondelete="CASCADE"`), `usage_role` (`DataProcessingUsageRoleEnum`: `PRIMARY_SOURCE`, `INTERMEDIATE_STORE`, `OUTPUT_SINK`, `ARCHIVAL_STORE`), `notes` (`Text`), `linked_by_id` (FK `users.id`), `created_at`.
     - Constraint: `uq_data_asset_processing_link` (`organization_id`, `data_asset_id`, `processing_activity_id`).
  7. **Create `data_asset_control_links`**:
     - `id`, `organization_id` (FK `organizations.id`), `data_asset_id` (FK `data_assets.id`, `ondelete="CASCADE"`), `organization_control_id` (FK `organization_controls.id`, `ondelete="CASCADE"`), `evidence_item_id` (FK `evidence_items.id`, nullable, `ondelete="SET NULL"`), `control_objective` (`DataControlObjectiveEnum`), `coverage_notes` (`Text`), `linked_by_id` (FK `users.id`), `created_at`.
     - Constraint: `uq_data_asset_control_link` (`organization_id`, `data_asset_id`, `organization_control_id`).

---

## 23. API Plan (`/api/v1/data-governance`)

All new endpoints are mounted under `/api/v1/data-governance` (`backend/app/api/v1/endpoints/data_governance.py`) and registered in `backend/app/api/v1/api.py`. Existing `/api/v1/privacy/data-assets` routes remain 100% intact for Phase 16 compatibility.

| # | Method | Path | Permission Required | Purpose |
| :--- | :---: | :--- | :--- | :--- |
| 1 | `GET` | `/api/v1/data-governance/summary` | `DATA_GOV_READ` | Executive & operational Data Governance summary (classification coverage, ownership/stewardship coverage, lineage integrity, cloud posture alignment, pending approvals). |
| 2 | `POST` | `/api/v1/data-governance/schemes` | `DATA_GOV_MANAGE` | Create a new `DataClassificationScheme` (`DRAFT`). |
| 3 | `GET` | `/api/v1/data-governance/schemes` | `DATA_GOV_READ` | List organization `DataClassificationScheme` records (with nested levels). |
| 4 | `GET` | `/api/v1/data-governance/schemes/{scheme_id}` | `DATA_GOV_READ` | Retrieve a specific classification scheme and its ordered levels. |
| 5 | `POST` | `/api/v1/data-governance/schemes/{scheme_id}/levels` | `DATA_GOV_MANAGE` | Add an ordered `DataClassificationLevel` to a scheme. |
| 6 | `POST` | `/api/v1/data-governance/schemes/{scheme_id}/submit` | `DATA_GOV_MANAGE` | Submit a `DRAFT` scheme (must have $\ge 2$ levels) to `PENDING_APPROVAL`. |
| 7 | `POST` | `/api/v1/data-governance/schemes/{scheme_id}/approve` | `DATA_GOV_APPROVE` | Four-Eyes approve a `PENDING_APPROVAL` scheme (`created_by_id != current_user.id`) $\rightarrow$ `ACTIVE`. |
| 8 | `POST` | `/api/v1/data-governance/assets` | `DATA_GOV_MANAGE` | Register a governed `DataAsset` (supports `steward_id`, `cloud_asset_id`, `asset_type`, `lifecycle_state`). |
| 9 | `GET` | `/api/v1/data-governance/assets` | `DATA_GOV_READ` | List governed `DataAsset` records with optional filters (`lifecycle_state`, `sensitivity_level`, `cloud_asset_id`, `owner_id`, `steward_id`, `classification_status`). |
| 10 | `GET` | `/api/v1/data-governance/assets/{asset_id}` | `DATA_GOV_READ` | Retrieve full governance dossier for a `DataAsset` (asset metadata, cloud posture alignment check, classification history, upstream/downstream lineage, linked processing activities, linked controls & regulatory obligations). |
| 11 | `PUT` | `/api/v1/data-governance/assets/{asset_id}` | `DATA_GOV_MANAGE` | Update mutable governance metadata on a non-retired `DataAsset` (blocks direct unapproved sensitivity downgrades). |
| 12 | `POST` | `/api/v1/data-governance/assets/{asset_id}/ownership` | `DATA_GOV_OWNER_MANAGE` | Assign or transfer `owner_id` and/or `steward_id` with tenant validation and audit trail. |
| 13 | `POST` | `/api/v1/data-governance/assets/{asset_id}/classifications` | `DATA_GOV_CLASSIFY` | Submit a governed classification/reclassification (`DataClassificationRecord`). Enforces `PENDING_APPROVAL` on downgrades and restricted levels. |
| 14 | `GET` | `/api/v1/data-governance/assets/{asset_id}/classifications` | `DATA_GOV_READ` | List immutable `DataClassificationRecord` history for a `DataAsset`. |
| 15 | `POST` | `/api/v1/data-governance/classifications/{record_id}/approve` | `DATA_GOV_APPROVE` | Four-Eyes approve a pending `DataClassificationRecord` (`requested_by_id != current_user.id`). |
| 16 | `POST` | `/api/v1/data-governance/classifications/{record_id}/reject` | `DATA_GOV_APPROVE` | Reject a pending `DataClassificationRecord` with mandatory reason. |
| 17 | `POST` | `/api/v1/data-governance/lineage-edges` | `DATA_GOV_LINEAGE_MANAGE` | Create or version a directed `DataLineageEdge` with cycle detection, SHA-256 provenance digest, and sensitivity flow guard. |
| 18 | `GET` | `/api/v1/data-governance/lineage-edges` | `DATA_GOV_READ` | List `DataLineageEdge` records (filterable by `data_asset_id`, `status`, `relationship_type`). |
| 19 | `POST` | `/api/v1/data-governance/lineage-edges/{edge_id}/approve` | `DATA_GOV_APPROVE` | Four-Eyes approve a `PENDING_APPROVAL` lineage edge (`created_by_id != current_user.id`). |
| 20 | `POST` | `/api/v1/data-governance/lineage-edges/{edge_id}/revoke` | `DATA_GOV_LINEAGE_MANAGE` | Revoke an active lineage edge (`status = REVOKED`, `effective_to = now()`). |
| 21 | `POST` | `/api/v1/data-governance/assets/{asset_id}/processing-links` | `DATA_GOV_MANAGE` | Link `DataAsset` to an authoritative Phase 16 `ProcessingActivity`. |
| 22 | `POST` | `/api/v1/data-governance/assets/{asset_id}/control-links` | `DATA_GOV_MANAGE` | Link `DataAsset` to an authoritative Phase 2 `OrganizationControl` and optional Phase 3 `EvidenceItem`. |
| 23 | `POST` | `/api/v1/data-governance/assets/{asset_id}/deprecate` | `DATA_GOV_MANAGE` | Transition `DataAsset` to `DEPRECATED`. |
| 24 | `POST` | `/api/v1/data-governance/assets/{asset_id}/retire` | `DATA_GOV_APPROVE` | Governed non-destructive retirement (`lifecycle_state = RETIRED`) requiring `disposal_method`, `retirement_notes`, and `retirement_evidence_id` (for restricted assets). |

**Immutable Endpoint Enforcement (`HTTP 405 Method Not Allowed`)**:
- Explicit `DELETE` and `PUT` handlers on `/api/v1/data-governance/classifications/{record_id}` and `DELETE` on `/api/v1/data-governance/lineage-edges/{edge_id}` return `HTTP 405 Method Not Allowed` to guarantee ledger immutability.

---

## 24. Frontend Plan

1. **TypeScript Definitions (`frontend/src/types/dataGovernance.ts`)**:
   - Strongly typed interfaces for `DataClassificationScheme`, `DataClassificationLevel`, `GovernedDataAsset`, `DataClassificationRecord`, `DataLineageEdge`, `DataAssetProcessingLink`, `DataAssetControlLink`, `DataGovernanceSummary`, and `DataAssetDossier`.
2. **API Client (`frontend/src/lib/dataGovernanceService.ts`)**:
   - Typed Axios service methods covering all `/api/v1/data-governance/*` endpoints.
3. **Enterprise Workspace Page (`frontend/src/pages/DataGovernancePage.tsx`)**:
   - Integrated 4-tab enterprise command center:
     1. **Asset Catalog & Lifecycle**: Governed `DataAsset` inventory with lifecycle state badges (`DISCOVERED` $\rightarrow$ `RETIRED`), owner/steward assignment modal, cloud host posture alignment badge (`CloudAsset` encryption/exposure status), and retirement workflow modal.
     2. **Classification Schemes & Approvals**: Scheme & ordinal level builder, pending classification approval queue with Four-Eyes enforcement indicators, and immutable classification audit history.
     3. **Data Lineage Graph & Provenance**: Directed asset-to-asset lineage explorer (`source -> target`), SHA-256 provenance hash badge, transformation/masking indicators, and lineage creation/approval/revocation controls.
     4. **Cross-Domain Traceability (RoPA, Controls & Regulations)**: M:N mapping manager connecting `DataAsset` records to Phase 16 `ProcessingActivity`, Phase 2 `OrganizationControl`, Phase 3 `EvidenceItem`, and Phase 21 `RegulatoryObligation`.
4. **Navigation Integration (`frontend/src/App.tsx` & `frontend/src/components/layout/Sidebar.tsx`)**:
   - Route `/data-governance` added to `App.tsx` and linked in `Sidebar.tsx`.

---

## 25. Anti-Duplication Decisions

| Prohibited Duplicate Authority | Why It Would Be Wrong | Authoritative Batch 3 Decision |
| :--- | :--- | :--- |
| `DataAsset2` / `governed_data_assets` | Splits data asset inventory across two tables and breaks Phase 16 `DPIAAssessment` / `DataTransferAssessment` foreign keys. | **EXTEND** existing `DataAsset` (`data_assets`) in `app/models/privacy.py` via migration `0024`. |
| `ProcessingActivity2` / `DataProcessingRegistry` | Duplicates Phase 16 GDPR Art. 30 `ProcessingActivity` (`processing_activities`). | **REUSE** `ProcessingActivity` via M:N bridge `DataAssetProcessingLink`. |
| `DPIA2` / `DataRiskAssessment` | Duplicates Phase 16 `DPIAAssessment` (`dpia_assessments`). | **REUSE** `DPIAAssessment` (which already has `data_asset_id`). |
| `DataTransfer2` / `CrossBorderFlow` | Duplicates Phase 16 `DataTransferAssessment` (`data_transfer_assessments`). | **REUSE** `DataTransferAssessment` (which already has `data_asset_id`). |
| `CloudAsset2` / `DataStorageResource` | Duplicates Phase 18 `CloudAsset` (`cloud_assets`). | **REUSE** `CloudAsset` via `DataAsset.cloud_asset_id` and `DataLineageEdge.cloud_asset_id`. |
| `DataControl` / `DataEvidence` | Duplicates Phase 2 `OrganizationControl` and Phase 3 `EvidenceItem`. | **REUSE** `OrganizationControl` and `EvidenceItem` via `DataAssetControlLink` and `DataAsset.retirement_evidence_id`. |
| `DataFinding` / `DataRisk` / `DataRemediation` | Fragments platform risk, finding, and CAPA tracking. | **REUSE** Phase 4 `Finding`, Phase 5 `Risk`, and Phase 11 `RemediationPlan`. |
| Custom RBAC Roles (`DATA_OWNER`, `DATA_STEWARD`, `DPO`) | Violates the platform's 6-role RBAC invariant. | **PRESERVE** exact 6 roles (`ADMIN`, `MANAGER`, `GRC_ANALYST`, `SECURITY_ANALYST`, `AUDITOR`, `VIEWER`). |

---

## 26. Threat Model (35 Security & Governance Vectors)

| Threat ID | Category | Attack / Failure Vector | Architectural Mitigation in Batch 3 | Expected HTTP Status |
| :--- | :--- | :--- | :--- | :---: |
| `SEC-B3-01` | Tenant Isolation | Spoofing `organization_id` in scheme, asset, classification, or lineage payload | Omit `organization_id` from all request schemas; bind strictly from `current_user.organization_id` | Ignored / Bound to Caller Org |
| `SEC-B3-02` | Tenant Isolation | Reading another tenant's `DataClassificationScheme` or `DataAsset` dossier by ID | Scope all queries by `organization_id == current_user.organization_id` | `404 Not Found` |
| `SEC-B3-03` | Tenant Isolation | Assigning cross-tenant `owner_id` or `steward_id` to a `DataAsset` | Verify `User.id == target_id` AND `User.organization_id == current_user.organization_id` | `404 Not Found` |
| `SEC-B3-04` | Tenant Isolation | Linking a `DataAsset` to a cross-tenant `CloudAsset` (`cloud_asset_id`) | Verify `CloudAsset.organization_id == current_user.organization_id` | `404 Not Found` |
| `SEC-B3-05` | Tenant Isolation | Creating a `DataLineageEdge` where `source_data_asset_id` or `target_data_asset_id` belongs to another tenant | Verify both endpoints belong to `current_user.organization_id` | `404 Not Found` |
| `SEC-B3-06` | Tenant Isolation | Linking a `DataAsset` to a cross-tenant `ProcessingActivity` | Verify `ProcessingActivity.organization_id == current_user.organization_id` | `404 Not Found` |
| `SEC-B3-07` | Tenant Isolation | Linking a `DataAsset` to a cross-tenant `OrganizationControl` or `EvidenceItem` | Verify both `OrganizationControl` and `EvidenceItem` belong to `current_user.organization_id` | `404 Not Found` |
| `SEC-B3-08` | Tenant Isolation | Supplying a cross-tenant `retirement_evidence_id` during asset retirement | Verify `EvidenceItem.organization_id == current_user.organization_id` | `404 Not Found` |
| `SEC-B3-09` | RBAC | `VIEWER` attempting to create a scheme, register an asset, classify data, or create lineage | Enforce `require_permission` on all mutating endpoints | `403 Forbidden` |
| `SEC-B3-10` | RBAC | `AUDITOR` attempting any write, classification, lineage, or approval action | `AUDITOR` granted only `DATA_GOV_READ` | `403 Forbidden` |
| `SEC-B3-11` | RBAC | `SECURITY_ANALYST` attempting to create a classification scheme or approve a classification downgrade | `SECURITY_ANALYST` lacks `DATA_GOV_MANAGE` and `DATA_GOV_APPROVE` | `403 Forbidden` |
| `SEC-B3-12` | RBAC | `GRC_ANALYST` attempting to approve a classification scheme, classification downgrade, or asset retirement | `GRC_ANALYST` lacks `DATA_GOV_APPROVE` (`ADMIN` and `MANAGER` only) | `403 Forbidden` |
| `SEC-B3-13` | Four-Eyes / SoD | Scheme creator (`ADMIN` or `MANAGER`) attempting to self-approve their own `DataClassificationScheme` | Enforce `scheme.created_by_id != current_user.id` | `403 Forbidden` |
| `SEC-B3-14` | Four-Eyes / SoD | Requester (`ADMIN` or `MANAGER`) attempting to self-approve their own classification downgrade or restricted classification (`DataClassificationRecord`) | Enforce `record.requested_by_id != current_user.id` | `403 Forbidden` |
| `SEC-B3-15` | Four-Eyes / SoD | Creator (`ADMIN` or `MANAGER`) attempting to self-approve a sensitivity-downgrading `DataLineageEdge` | Enforce `edge.created_by_id != current_user.id` | `403 Forbidden` |
| `SEC-B3-16` | Classification Bypass | Attempting to silently downgrade `DataAsset.data_sensitivity_level` via `PUT /api/v1/data-governance/assets/{id}` without a `DataClassificationRecord` | Block sensitivity downgrades on `PUT /data-governance/assets/{id}` (`HTTP 422`); require `/classifications` workflow | `422 Unprocessable Entity` |
| `SEC-B3-17` | Classification Integrity | Submitting a classification record referencing a `level_id` that does not belong to `scheme_id` | Validate `level.scheme_id == scheme.id` and `scheme.status == ACTIVE` | `422 Unprocessable Entity` |
| `SEC-B3-18` | Classification Integrity | Attempting to activate a `DataClassificationScheme` that has fewer than 2 levels | Require $\ge 2$ ordered levels before `submit`/`approve` | `422 Unprocessable Entity` |
| `SEC-B3-19` | Lineage Integrity | Creating a self-loop lineage edge (`source_data_asset_id == target_data_asset_id`) | Reject at service layer + DB `ck_lineage_no_self_loop` | `422 Unprocessable Entity` |
| `SEC-B3-20` | Lineage Integrity | Creating a multi-hop cycle (`A -> B -> C -> A`) in active lineage edges | Graph reachability check (BFS/DFS from `target` to `source`) rejects cycle creation | `422 Unprocessable Entity` |
| `SEC-B3-21` | Lineage Security | Unmasked data flow from `RESTRICTED_PII` source asset to `PUBLIC` target asset (`is_masked_or_anonymized=False`) | Automatically force edge into `PENDING_APPROVAL` requiring Four-Eyes approval | `201 Created` (`status=PENDING_APPROVAL`) |
| `SEC-B3-22` | Lineage Immutability | Attempting `DELETE /api/v1/data-governance/lineage-edges/{id}` | Explicit `405 Method Not Allowed` route handler; lineage must be revoked via `/revoke` | `405 Method Not Allowed` |
| `SEC-B3-23` | Classification Immutability | Attempting `DELETE` or `PUT` on `/api/v1/data-governance/classifications/{record_id}` | Explicit `405 Method Not Allowed` route handlers | `405 Method Not Allowed` |
| `SEC-B3-24` | Lifecycle Integrity | Attempting to create new outbound lineage from a `RETIRED` or `DEPRECATED` `DataAsset` | Reject lineage creation if `source` or `target` is `RETIRED` (or `source` is `DEPRECATED`) | `422 Unprocessable Entity` |
| `SEC-B3-25` | Lifecycle Integrity | Attempting to modify metadata or reclassify a `RETIRED` `DataAsset` | Reject all mutations on `RETIRED` assets (`HTTP 409 Conflict` / `422`) | `409 Conflict` |
| `SEC-B3-26` | Disposal Governance | Attempting to retire a `RESTRICTED_PII` or `SPECIAL_CATEGORY_SENSITIVE_PHI` `DataAsset` without `retirement_evidence_id` or `disposal_method == NONE` | Enforce mandatory `retirement_evidence_id` and valid destructive/anonymizing `disposal_method` | `422 Unprocessable Entity` |
| `SEC-B3-27` | Concurrency / Replay | Re-approving an already `APPROVED` or `REJECTED` `DataClassificationRecord` | Reject state transition on non-`PENDING_APPROVAL` record | `409 Conflict` |
| `SEC-B3-28` | Concurrency / Replay | Duplicate `scheme_code + version` or duplicate `edge_code + version` within same organization | Unique constraints + conflict check return `409 Conflict` | `409 Conflict` |
| `SEC-B3-29` | Concurrency / Replay | Duplicate `DataAssetProcessingLink` or `DataAssetControlLink` for same asset and target | Unique constraints + conflict check return `409 Conflict` | `409 Conflict` |
| `SEC-B3-30` | Cloud Alignment | Linking a `RESTRICTED_PII` `DataAsset` to an unencrypted or internet-facing `CloudAsset` | Surface deterministic `cloud_posture_aligned = False` and mismatch flags in dossier & summary without overwriting classification | `200 OK` (Flags Mismatch) |
| `SEC-B3-31` | Input Validation | Out-of-bounds `ordinal_rank` (`< 1` or `> 10`) on `DataClassificationLevel` | Pydantic `Field(ge=1, le=10)` + DB `ck_class_level_rank_bounds` | `422 Unprocessable Entity` |
| `SEC-B3-32` | Input Validation | Blank or whitespace-only `justification` on classification downgrade or ownership transfer | Pydantic `min_length=5` after stripping whitespace | `422 Unprocessable Entity` |
| `SEC-B3-33` | Provenance Integrity | Tampering or non-deterministic ordering in `DataLineageEdge.provenance_hash` | Compute SHA-256 over canonical key-sorted JSON (`sort_keys=True, separators=(",", ":")`) | Deterministic 64-char hex digest |
| `SEC-B3-34` | Unauthenticated Access | Calling any `/api/v1/data-governance/*` endpoint without bearer token | FastAPI `get_current_active_user` dependency rejects request | `401 Unauthorized` |
| `SEC-B3-35` | Audit Trail Completeness | Performing classification, lineage, ownership, or retirement mutation without `AuditLog` record | Every mutating method calls `AuditService.log()` before returning | Verified in DB `audit_logs` |

---

## 27. Adversarial Test Matrix

Batch 3 implementation will include two dedicated test suites (`backend/tests/test_data_governance_domain.py` and `backend/tests/test_data_governance_api.py`) covering:
1. **Domain & Service Tests (`test_data_governance_domain.py`)**:
   - Classification scheme creation, ordinal level validation (`1..10`), and Four-Eyes scheme activation.
   - Governed `DataAsset` registration, `owner_id` & `steward_id` separation, and backward compatibility with Phase 16 `PrivacyService`.
   - Classification upgrade vs downgrade detection, mandatory `PENDING_APPROVAL` on downgrades and `RESTRICTED_PII`/`SPECIAL_CATEGORY_SENSITIVE_PHI`, Four-Eyes self-approval rejection, and synchronization with `DataAsset.data_sensitivity_level`.
   - Directed `DataLineageEdge` creation, deterministic SHA-256 `provenance_hash`, self-loop rejection (`A -> A`), multi-hop cycle rejection (`A -> B -> C -> A`), sensitivity downgrade flow gating, and append-only versioned superseding.
   - Cloud posture alignment checks (`CloudAsset.encryption_enabled == False` or `is_internet_facing == True` with `RESTRICTED_PII` `DataAsset`).
   - Governed `DataAsset` retirement requiring `retirement_evidence_id` for restricted assets and blocking subsequent mutations.
2. **API, RBAC, SoD & Cross-Tenant Security Tests (`test_data_governance_api.py`)**:
   - Full end-to-end HTTP lifecycle test across all 24 endpoints.
   - Complete 6-role RBAC matrix (`ADMIN`, `MANAGER`, `GRC_ANALYST`, `SECURITY_ANALYST`, `AUDITOR`, `VIEWER`).
   - Cross-tenant isolation tests (`404 Not Found` on cross-tenant `scheme_id`, `asset_id`, `owner_id`, `steward_id`, `cloud_asset_id`, `source_data_asset_id`, `target_data_asset_id`, `processing_activity_id`, `organization_control_id`, `evidence_item_id`).
   - Four-Eyes SoD enforcement tests (`403 Forbidden` on self-approving schemes, classification downgrades, and restricted lineage edges).
   - `405 Method Not Allowed` immutability tests on classification records and lineage edges.
   - `409 Conflict` duplicate code / replay transition tests.

---

## 28. Batch Boundary Analysis

Per Section 27 of the specification, we evaluated whether `DATA-GOVERNANCE-GRC` should be executed as a single cohesive batch (`BATCH-3-DATA-GOVERNANCE-GRC`) or split into sub-batches (`3A` / `3B`):

- **Evaluation**:
  - `DataAsset` already exists in `app/models/privacy.py` (Phase 16), and `CloudAsset`, `ProcessingActivity`, `OrganizationControl`, `EvidenceItem`, and `RegulatoryObligation` already exist across Phases 2–21.
  - Consequently, Batch 3 only requires **1 migration (`0024`)** adding **5 focused governance tables** (`data_classification_schemes`, `data_classification_levels`, `data_classification_records`, `data_lineage_edges`, and the two M:N link tables `data_asset_processing_links` / `data_asset_control_links`) plus extending `data_assets` in-place.
  - Splitting classification and lineage into separate migrations (`3A` and `3B`) would artificially split the sensitivity-aware lineage flow gate (which depends on `DataClassificationLevel` and `DataAsset` sensitivity) and require two migrations touching the same domain.
- **Recommendation**: **Execute as a SINGLE COHESIVE BATCH (`BATCH-3-DATA-GOVERNANCE-GRC`)** with migration `0024_data_governance_and_lineage.py`.

---

## 29. Implementation File Inventory (Planned for Implementation Phase)

| Layer | File Path | Action | Description |
| :--- | :--- | :--- | :--- |
| **Migration** | `backend/alembic/versions/0024_data_governance_and_lineage.py` | **CREATE** | Migration `0024` (revises `0023`): extends `data_assets` in-place and creates the 5 Data Governance tables. |
| **Models** | `backend/app/models/privacy.py` | **EXTEND** | Extend `DataAsset` with Batch 3 governance columns (`asset_type`, `lifecycle_state`, `steward_id`, `cloud_asset_id`, classification FKs, retirement fields) with backward-compatible defaults. |
| **Models** | `backend/app/models/data_governance.py` | **CREATE** | Define enums and models: `DataClassificationScheme`, `DataClassificationLevel`, `DataClassificationRecord`, `DataLineageEdge`, `DataAssetProcessingLink`, `DataAssetControlLink`. |
| **Models Init** | `backend/app/models/__init__.py` | **UPDATE** | Export Batch 3 models and enums. |
| **Permissions** | `backend/app/core/permissions.py` | **UPDATE** | Add `DATA_GOV_READ`, `DATA_GOV_MANAGE`, `DATA_GOV_CLASSIFY`, `DATA_GOV_APPROVE`, `DATA_GOV_LINEAGE_MANAGE`, `DATA_GOV_OWNER_MANAGE` across the 6 existing roles. |
| **Schemas** | `backend/app/schemas/data_governance.py` | **CREATE** | Pydantic v2 request/response schemas with strict bounds, whitespace validation, and zero `organization_id` client trust. |
| **Service** | `backend/app/services/data_governance_service.py` | **CREATE** | Authoritative `DataGovernanceService` implementing classification schemes, Four-Eyes classification records, DAG lineage with SHA-256 provenance, cloud posture alignment, RoPA/control linking, and governed retirement. |
| **API Endpoints** | `backend/app/api/v1/endpoints/data_governance.py` | **CREATE** | FastAPI router under `/api/v1/data-governance` (24 endpoints + explicit `405` immutability handlers). |
| **API Router** | `backend/app/api/v1/api.py` | **UPDATE** | Register `data_governance.router` under `/data-governance`. |
| **Backend Tests** | `backend/tests/test_data_governance_domain.py` | **CREATE** | Domain, lifecycle, DAG cycle detection, provenance hash, cloud alignment, and retirement unit/integration tests. |
| **Backend Tests** | `backend/tests/test_data_governance_api.py` | **CREATE** | End-to-end API, 6-role RBAC, Four-Eyes SoD, cross-tenant `404`, `405` immutability, and `409` idempotency tests. |
| **Frontend Types** | `frontend/src/types/dataGovernance.ts` | **CREATE** | TypeScript interfaces for Data Governance & Lineage. |
| **Frontend Service** | `frontend/src/lib/dataGovernanceService.ts` | **CREATE** | Axios API client for `/api/v1/data-governance`. |
| **Frontend Page** | `frontend/src/pages/DataGovernancePage.tsx` | **CREATE** | 4-tab Enterprise Data Governance & Lineage UI. |
| **Frontend Routing** | `frontend/src/App.tsx` & `frontend/src/components/layout/Sidebar.tsx` | **UPDATE** | Wire `/data-governance` route and sidebar navigation link. |

---

## 30. Security Gates

Before Batch 3 can be marked complete during implementation, all of the following security gates must pass:
1. **Zero Role Inflation Gate**: `len(UserRole) == 6` (`ADMIN`, `MANAGER`, `GRC_ANALYST`, `SECURITY_ANALYST`, `AUDITOR`, `VIEWER`).
2. **Tenant Isolation Gate**: 100% of cross-tenant foreign-key and resource ID probes return `HTTP 404 Not Found` (`0` data leaks, `0` cross-tenant `403` enumeration leaks).
3. **Four-Eyes SoD Gate**: Self-approval of classification schemes, classification downgrades/restricted classifications, and restricted lineage flows returns `HTTP 403 Forbidden`.
4. **Ledger Immutability Gate**: `DELETE`/`PUT` on classification records and `DELETE` on lineage edges return `HTTP 405 Method Not Allowed`.
5. **DAG Lineage Gate**: Self-loops (`A -> A`) and multi-hop cycles (`A -> B -> C -> A`) return `HTTP 422 Unprocessable Entity`.

---

## 31. Regression Gates

1. **Phase 16 Privacy Compatibility**: All existing Phase 16 tests (`backend/tests/test_privacy_domain.py` and `backend/tests/test_privacy_api.py`) must pass `100%` without modification.
2. **Phase 18 CloudSec Compatibility**: All existing Phase 18 tests (`backend/tests/test_cloudsec_domain.py` and `backend/tests/test_cloudsec_api.py`) must pass `100%`.
3. **Full Backend Regression**: All `1,038` existing backend tests plus all new Batch 3 tests must pass (`0` failures, `0` errors).
4. **Frontend Production Build**: `npm run build` (`tsc -b && vite build`) must exit with code `0`.

---

## 32. Open Architectural Questions

- **None**. All architectural boundaries between Phase 16 (`PRIVACY-GRC`), Phase 18 (`CLOUDSEC-GRC`), Phase 2/3 (`OrganizationControl` / `EvidenceItem`), Phase 21 (`REGULATORY-GRC`), and Batch 3 (`DATA-GOVERNANCE-GRC`) have been verified directly against the repository source code.

---

## 33. Final GO / NO-GO Decision

- **Verdict**: **GO**
- **Recommended Scope**: Single cohesive batch **`BATCH-3-DATA-GOVERNANCE-GRC`** targeting migration `0024_data_governance_and_lineage.py`.
- **Readiness**: Ready to proceed immediately to the **Batch 3 Architecture Hardening Gate**.
