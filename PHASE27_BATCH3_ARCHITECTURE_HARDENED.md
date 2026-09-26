# ControlSphere — Phase 27 / Batch 3 Hardened Architecture & Security Contract
## Module: `DATA-GOVERNANCE-GRC` (`BATCH-3-DATA-GOVERNANCE-GRC`)

- **Repository**: `E:\PROJECT WORKSPACE 2\ControlSphere`
- **Remote**: `https://github.com/Avalar06/ControlSphere.git`
- **Branch**: `main`
- **Verified Baseline Commit (Short)**: `7b5c795` (`feat(batch2): implement kri appetite governance`)
- **Verified Baseline Commit (`git rev-parse HEAD`)**: `7b5c7954c33f6aca44b7a193ad91d1b384188456`
- **Current Alembic Head**: `0023` (`0023_kri_and_risk_appetite_governance.py`)
- **Target Migration**: `0024_data_governance_and_lineage.py` (revises `0023`)
- **Hardening Verdict**: **GO — BATCH 3 ARCHITECTURE HARDENED & READY FOR IMPLEMENTATION**

---

## 1. Baseline Verification

Direct command verification against `E:\PROJECT WORKSPACE 2\ControlSphere`:

| Check | Command | Actual Output | Verdict |
| :--- | :--- | :--- | :--- |
| **Working Tree** | `git status` | `On branch main`, `Your branch is up to date with 'origin/main'`, `0` modified tracked files (only untracked `PHASE27_BATCH3_ARCHITECTURE_DISCOVERY.md`) | **PASS** |
| **Commit Summary** | `git log -1 --oneline` | `7b5c795 feat(batch2): implement kri appetite governance` | **PASS** |
| **Exact HEAD SHA** | `git rev-parse HEAD` | `7b5c7954c33f6aca44b7a193ad91d1b384188456` (matches short commit `7b5c795`) | **PASS** |
| **Active Branch** | `git branch --show-current` | `main` | **PASS** |
| **Remote** | `git remote -v` | `origin https://github.com/Avalar06/ControlSphere.git (fetch/push)` | **PASS** |
| **Alembic Head** | `alembic -c backend/alembic.ini heads` | `0023 (head)` (`0023_kri_and_risk_appetite_governance.py`) | **PASS** |

---

## 2. Discovery Validation

Every claim in `PHASE27_BATCH3_ARCHITECTURE_DISCOVERY.md` was audited directly against the repository source code (`backend/app/models/privacy.py`, `backend/app/services/privacy_service.py`, `backend/app/models/cloudsec.py`, `backend/app/models/evidence.py`, `backend/app/models/regulatory.py`).

### 2.1 Validated Claims vs. Hardening Corrections Applied

| # | Discovery Claim | Code Inspection Finding | Hardened Architectural Resolution |
| :--- | :--- | :--- | :--- |
| 1 | Extend `DataAsset` (`data_assets`) in-place | **VALIDATED**: `DataAsset` in `app/models/privacy.py` is the canonical logical dataset table. | Extend `data_assets` in migration `0024` with safe `server_default` values for all non-null columns. |
| 2 | `DataAsset` already has `storage_type` (`String(64)`) | **REFINED**: Discovery proposed `asset_type` without explicitly contrasting it against existing `DataAsset.storage_type`. | `storage_type` (`String(64)`, default `"POSTGRES_DB"`) remains authoritative for physical storage engine string; `asset_type` (`DataAssetTypeEnum`) is added for logical data governance asset taxonomy. |
| 3 | `DPIAAssessment` and `DataTransferAssessment` have `data_asset_id` | **CORRECTED**: In `app/models/privacy.py` (lines 205, 264), `DPIAAssessment` and `DataTransferAssessment` link to `processing_activity_id` (`processing_activities.id`), **NOT** `data_asset_id`! | `DataAssetProcessingLink` (`data_asset_processing_links`) is the authoritative M:N bridge connecting `DataAsset` $\leftrightarrow$ `ProcessingActivity` $\leftrightarrow$ `DPIAAssessment` / `DataTransferAssessment`. |
| 4 | `CloudAsset` has `public_access_blocked`, `logging_enabled`, `versioning_enabled` | **CORRECTED**: In `app/models/cloudsec.py` (lines 128–229), `CloudAsset` actually has `is_internet_facing`, `encryption_enabled`, `posture_status`, `posture_score`, `blast_radius_score`, `lifecycle_state`, and `configuration_metadata`. | Cloud posture alignment checks in Batch 3 must inspect the actual `CloudAsset` columns (`encryption_enabled`, `is_internet_facing`, `posture_status`, `lifecycle_state`). |
| 5 | `DataAsset` $\rightarrow$ `CloudAsset` cardinality | **HARDENED**: A single S3 bucket/RDS instance can host multiple datasets, and a distributed dataset can span multiple cloud resources. | Provide **both** `DataAsset.cloud_asset_id` (nullable primary hosting FK) AND `DataAssetCloudLink` (`data_asset_cloud_links`) M:N bridge (`PRIMARY_STORE`, `REPLICA_STORE`, `BACKUP_ARCHIVE`, `ENCRYPTION_KEY_VAULT`). |
| 6 | `DataAssetControlLink` combined `organization_control_id` and `evidence_item_id` in one table | **HARDENED**: Mixing control linkage and evidence linkage in one row overloads semantics and prevents multiple evidence items per asset/control. | Split into two clean bridge tables: `DataAssetControlLink` (`data_asset_control_links` $\rightarrow$ `organization_controls.id`) and `DataAssetEvidenceLink` (`data_asset_evidence_links` $\rightarrow$ `evidence_items.id`). |
| 7 | Ownership transfer Four-Eyes governance | **HARDENED**: Discovery had a single immediate ownership update call without a formal Four-Eyes ownership transfer state machine when required. | Add `DataOwnershipTransferRequest` / governed transfer state machine supporting Four-Eyes approval (`requested_by_id != approved_by_id`) and inactive-owner protection. |

---

## 3. Phase 16 Authority Validation (`PRIVACY-GRC`)

Direct code inspection of `backend/app/models/privacy.py`, `backend/app/services/privacy_service.py`, and `backend/app/api/v1/endpoints/privacy.py` confirms:

1. **`DataAsset` (`data_assets`)**:
   - Currently managed by `PrivacyService.create_data_asset`, `get_data_asset`, `list_data_assets`, `update_data_asset`, `delete_data_asset`.
   - Protected by `Permission.PRIVACY_READ` and `Permission.PRIVACY_MANAGE`.
   - Logs to `AuditService.log` with `resource_type="DataAsset"` and actions `"CREATE"`, `"UPDATE"`, `"DELETE"`.
2. **`ProcessingActivity` (`processing_activities`)**:
   - Authoritative GDPR Art. 30 RoPA record with `ProcessingLifecycleState` (`DRAFT`, `DPO_REVIEW`, `ACTIVE`, `SUSPENDED`, `ARCHIVED`, `RETIRED`) and `dpo_approval_status` (`PrivacyApprovalStatus`).
   - Note: `PrivacyService.delete_processing_activity` blocks deletion only when `lifecycle_state == ACTIVE`, allowing deletion in non-active states.
3. **`DPIAAssessment` (`dpia_assessments`)**:
   - Links to `processing_activity_id` (`ondelete="CASCADE"`) and `remediation_plan_id` (`ondelete="SET NULL"`).
   - Enforces DB-level SoD: `CheckConstraint("dpo_reviewed_by_id IS NULL OR created_by_id != dpo_reviewed_by_id", name="chk_dpia_approval_sod")`.
4. **`DataTransferAssessment` (`data_transfer_assessments`)**:
   - Links to `processing_activity_id` (`ondelete="CASCADE"`).
   - Enforces DB-level SoD: `CheckConstraint("approved_by_id IS NULL OR requested_by_id != approved_by_id", name="chk_transfer_approval_sod")`.

---

## 4. Phase 18 Authority Validation (`CLOUDSEC-GRC`)

Direct code inspection of `backend/app/models/cloudsec.py` (lines 128–229) confirms:

- **Model**: `CloudAsset` (`__tablename__ = "cloud_assets"`)
- **Authoritative Fields**:
  - `id` (`Integer`, PK)
  - `organization_id` (`Integer`, FK `organizations.id`, `ondelete="CASCADE"`, NOT NULL, indexed)
  - `asset_code` (`String(64)`, NOT NULL, unique per tenant via `uq_cloud_asset_tenant_code`)
  - `provider` (`Enum(CloudProviderEnum)`: `AWS`, `AZURE`, `GCP`, `OCI`, `ALIBABA`)
  - `account_id` (`String(128)`, NOT NULL, indexed)
  - `region` (`String(64)`, NOT NULL)
  - `resource_type` (`Enum(CloudAssetTypeEnum)`: `S3_BUCKET`, `IAM_ROLE`, `EC2_INSTANCE`, `KUBERNETES_CLUSTER`, `RDS_DATABASE`, `KEY_VAULT`, `SECURITY_GROUP`, `SERVERLESS_FUNCTION`, `CONTAINER_REGISTRY`, `VIRTUAL_NETWORK`)
  - `resource_arn` (`String(512)`, NOT NULL, unique per tenant via `uq_cloud_asset_tenant_arn`)
  - `resource_name` (`String(255)`, NOT NULL)
  - `environment` (`Enum(CloudEnvironmentEnum)`: `PRODUCTION`, `STAGING`, `DEVELOPMENT`, `SANDBOX`)
  - `criticality` (`Enum(CloudCriticalityEnum)`: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`)
  - `posture_status` (`Enum(CloudPostureStatusEnum)`: `COMPLIANT`, `NON_COMPLIANT`, `DEVIATED`, `UNASSESSED`)
  - `posture_score` (`Numeric(5, 2)`, `0.00..100.00`)
  - `blast_radius_score` (`Numeric(5, 2)`, `0.00..100.00`)
  - `lifecycle_state` (`Enum(CloudLifecycleStateEnum)`: `ACTIVE`, `PROVISIONING`, `MAINTENANCE`, `DECOMMISSIONED`)
  - `is_internet_facing` (`Boolean`, default `False`)
  - `encryption_enabled` (`Boolean`, default `True`)
  - `owner_id` (`Integer`, FK `users.id`, `ondelete="RESTRICT"`, NOT NULL)

---

## 5. `DataAsset` Authority & Column Conflict Analysis

### 5.1 Existing `DataAsset` Columns (`backend/app/models/privacy.py`)

| Existing Column | SQLAlchemy Type | Nullable | Default | Semantic Authority |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `Integer` (PK) | `False` | Auto | Canonical Data Asset primary key across Privacy and Data Governance. |
| `organization_id` | `Integer` (`FK organizations.id`) | `False` | — | Multi-tenant isolation boundary (`ondelete="CASCADE"`). |
| `asset_code` | `String(64)` | `False` | — | Unique asset identifier per tenant (`uq_data_asset_org_code`). |
| `name` | `String(255)` | `False` | — | Human-readable dataset name. |
| `description` | `Text` | `True` | `None` | Narrative description of dataset contents and purpose. |
| `data_sensitivity_level` | `SAEnum(DataSensitivityLevel)` | `False` | `INTERNAL` | Canonical platform sensitivity enum (`PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED_PII`, `SPECIAL_CATEGORY_SENSITIVE_PHI`). |
| `data_volume_range` | `String(64)` | `False` | `"LOW"` | Volume tier (`LOW`, `MEDIUM`, `HIGH`). |
| `storage_type` | `String(64)` | `False` | `"POSTGRES_DB"` | **Existing Technical Storage Engine String** (e.g., `"POSTGRES_DB"`, `"SNOWFLAKE"`, `"S3_PARQUET"`). |
| `hosting_jurisdiction` | `String(64)` | `False` | `"EU_EEA"` | Primary legal/geographic hosting jurisdiction code. |
| `is_encrypted_at_rest` | `Boolean` | `False` | `True` | Attested encryption-at-rest flag on the dataset. |
| `is_encrypted_in_transit` | `Boolean` | `False` | `True` | Attested encryption-in-transit flag on the dataset. |
| `is_pseudonymized` | `Boolean` | `False` | `False` | Attested pseudonymization/tokenization flag. |
| `retention_period_months` | `Integer` | `True` | `12` | Authoritative retention schedule in months (`1..1200`). |
| `business_process_id` | `Integer` (`FK business_processes.id`) | `True` | `None` | Optional link to Phase 17 `BusinessProcess` (`ondelete="SET NULL"`). |
| `ai_system_id` | `Integer` (`FK ai_systems.id`) | `True` | `None` | Optional link to Phase 15 `AISystem` (`ondelete="SET NULL"`). |
| `vendor_id` | `Integer` (`FK vendors.id`) | `True` | `None` | Optional link to Phase 9 `Vendor` (`ondelete="SET NULL"`). |
| `owner_id` | `Integer` (`FK users.id`) | `False` | — | Authoritative accountable **Data Owner** (`users.id`). |
| `created_at` / `updated_at` | `DateTime(timezone=True)` | `False` | `utcnow` | Audit timestamps. |

### 5.2 New Columns Added to `DataAsset` in Migration `0024` (Zero Duplication)

| New Column | SQLAlchemy Type | Nullable | Server Default | Conflict / Overlap Resolution |
| :--- | :--- | :---: | :--- | :--- |
| `asset_type` | `String(64)` (`DataAssetTypeEnum`) | `False` | `'DATABASE_TABLE'` | **No conflict with `storage_type`**: `asset_type` classifies the logical structure (`DATABASE_TABLE`, `DATA_LAKE_DATASET`, `OBJECT_STORAGE_BUCKET`, `DOCUMENT_REPOSITORY`, `MESSAGE_STREAM`, `API_FEED`, `FEATURE_STORE`, `ARCHIVE_BACKUP`), whereas `storage_type` describes the underlying DB/engine (`"POSTGRES_DB"`). |
| `lifecycle_state` | `String(32)` (`DataAssetLifecycleEnum`) | `False` | `'ACTIVE'` | Does not exist on `DataAsset`. Default `'ACTIVE'` preserves 100% compatibility for existing rows and Phase 16 `POST /privacy/data-assets`. |
| `steward_id` | `Integer` (`FK users.id`, `ondelete="SET NULL"`) | `True` | `None` | Distinct from `owner_id`: `owner_id` is accountable executive/business owner; `steward_id` is operational data steward. |
| `cloud_asset_id` | `Integer` (`FK cloud_assets.id`, `ondelete="SET NULL"`) | `True` | `None` | Primary hosting `CloudAsset` pointer (complemented by M:N `DataAssetCloudLink` for multi-resource datasets). |
| `classification_scheme_id` | `Integer` (`FK data_classification_schemes.id`, `ondelete="SET NULL"`) | `True` | `None` | Points to the active `DataClassificationScheme` governing this asset. |
| `classification_level_id` | `Integer` (`FK data_classification_levels.id`, `ondelete="SET NULL"`) | `True` | `None` | Points to the currently approved `DataClassificationLevel`. |
| `classification_status` | `String(32)` (`DataClassificationApprovalStatusEnum`) | `False` | `'APPROVED'` | Tracks whether the asset's classification is `UNCLASSIFIED`, `PENDING_APPROVAL`, `APPROVED`, or `REJECTED`. |
| `classified_by_id` | `Integer` (`FK users.id`, `ondelete="SET NULL"`) | `True` | `None` | User who initiated the currently active classification. |
| `classification_approved_by_id` | `Integer` (`FK users.id`, `ondelete="SET NULL"`) | `True` | `None` | Approver (`!= classified_by_id` when Four-Eyes applies) of the active classification. |
| `classification_approved_at` | `DateTime(timezone=True)` | `True` | `None` | Timestamp of last approved classification. |
| `last_reviewed_at` | `DateTime(timezone=True)` | `True` | `None` | Timestamp of last stewardship/classification revalidation. |
| `disposal_method` | `String(64)` (`DataDisposalMethodEnum`) | `True` | `None` | Authoritative disposal method (`CRYPTOGRAPHIC_ERASURE`, `SECURE_OVERWRITE`, `PHYSICAL_DESTRUCTION`, `ANONYMIZATION`) populated upon retirement. |
| `retirement_requested_by_id` | `Integer` (`FK users.id`, `ondelete="SET NULL"`) | `True` | `None` | User who requested retirement (enables Four-Eyes retirement approval). |
| `retired_by_id` | `Integer` (`FK users.id`, `ondelete="SET NULL"`) | `True` | `None` | User who approved/finalized retirement. |
| `retired_at` | `DateTime(timezone=True)` | `True` | `None` | Authoritative retirement timestamp. |
| `retirement_notes` | `Text` | `True` | `None` | Disposal verification notes. |
| `retirement_evidence_id` | `Integer` (`FK evidence_items.id`, `ondelete="SET NULL"`) | `True` | `None` | Authoritative Phase 3 `EvidenceItem` proving data disposal/erasure. |

---

## 6. Classification Authority

### 6.1 `DataClassificationScheme` (`data_classification_schemes`)
- **Purpose**: Organization-scoped, versioned classification taxonomy (e.g., `"CS-CORP-2026"` v1).
- **Columns**:
  - `id` (`Integer`, PK)
  - `organization_id` (`Integer`, FK `organizations.id`, `ondelete="CASCADE"`, NOT NULL, indexed)
  - `scheme_code` (`String(64)`, NOT NULL, indexed)
  - `name` (`String(255)`, NOT NULL)
  - `description` (`Text`, nullable)
  - `version` (`Integer`, NOT NULL, default `1`)
  - `status` (`String(32)` / `DataClassificationSchemeStatusEnum`: `DRAFT`, `PENDING_APPROVAL`, `ACTIVE`, `ARCHIVED`, default `DRAFT`, indexed)
  - `is_default` (`Boolean`, NOT NULL, default `False`)
  - `created_by_id` (`Integer`, FK `users.id`, `ondelete="RESTRICT"`, NOT NULL)
  - `approved_by_id` (`Integer`, FK `users.id`, `ondelete="SET NULL"`, nullable)
  - `approved_at` (`DateTime(timezone=True)`, nullable)
  - `created_at`, `updated_at` (`DateTime(timezone=True)`, NOT NULL)
- **Constraints**:
  - `UniqueConstraint("organization_id", "scheme_code", "version", name="uq_class_scheme_org_code_ver")`
  - `CheckConstraint("version >= 1", name="ck_class_scheme_version_pos")`
  - `CheckConstraint("approved_by_id IS NULL OR created_by_id != approved_by_id", name="ck_class_scheme_sod")`

### 6.2 `DataClassificationLevel` (`data_classification_levels`)
- **Purpose**: Ordered classification tier within a `DataClassificationScheme`.
- **Columns**:
  - `id` (`Integer`, PK)
  - `organization_id` (`Integer`, FK `organizations.id`, `ondelete="CASCADE"`, NOT NULL, indexed)
  - `scheme_id` (`Integer`, FK `data_classification_schemes.id`, `ondelete="CASCADE"`, NOT NULL, indexed)
  - `level_code` (`String(64)`, NOT NULL)
  - `name` (`String(128)`, NOT NULL)
  - `description` (`Text`, nullable)
  - `ordinal_rank` (`Integer`, NOT NULL — `1..10`, where higher integer = higher sensitivity/restriction)
  - `mapped_sensitivity_level` (`SAEnum(DataSensitivityLevel)`, NOT NULL — maps this level deterministically to `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED_PII`, or `SPECIAL_CATEGORY_SENSITIVE_PHI`)
  - `requires_encryption_at_rest` (`Boolean`, NOT NULL, default `True`)
  - `requires_encryption_in_transit` (`Boolean`, NOT NULL, default `True`)
  - `requires_four_eyes_approval` (`Boolean`, NOT NULL, default `False`)
  - `default_retention_months` (`Integer`, nullable)
  - `required_disposal_method` (`String(64)`, nullable)
  - `created_at`, `updated_at` (`DateTime(timezone=True)`, NOT NULL)
- **Constraints**:
  - `UniqueConstraint("scheme_id", "level_code", name="uq_class_level_scheme_code")`
  - `UniqueConstraint("scheme_id", "ordinal_rank", name="uq_class_level_scheme_rank")`
  - `CheckConstraint("ordinal_rank >= 1 AND ordinal_rank <= 10", name="ck_class_level_rank_bounds")`
  - **Monotonic Rank-to-Sensitivity Rule**: Within a scheme, if `level_A.ordinal_rank < level_B.ordinal_rank`, then `SENSITIVITY_RANK_MAP[level_A.mapped_sensitivity_level] <= SENSITIVITY_RANK_MAP[level_B.mapped_sensitivity_level]`. Validated server-side when adding levels (`HTTP 422` if violated) so `ordinal_rank` and `DataSensitivityLevel` never contradict each other.

### 6.3 `DataClassificationRecord` (`data_classification_records`)
- **Purpose**: **Append-Only Versioned Immutable Ledger** of classification requests, approvals, rejections, and revalidations for each `DataAsset`.
- **Columns**:
  - `id` (`Integer`, PK)
  - `organization_id` (`Integer`, FK `organizations.id`, `ondelete="CASCADE"`, NOT NULL, indexed)
  - `data_asset_id` (`Integer`, FK `data_assets.id`, `ondelete="CASCADE"`, NOT NULL, indexed)
  - `version` (`Integer`, NOT NULL, default `1` — monotonically increasing per `data_asset_id`)
  - `scheme_id` (`Integer`, FK `data_classification_schemes.id`, `ondelete="RESTRICT"`, NOT NULL, indexed)
  - `level_id` (`Integer`, FK `data_classification_levels.id`, `ondelete="RESTRICT"`, NOT NULL, indexed)
  - `previous_level_id` (`Integer`, FK `data_classification_levels.id`, `ondelete="SET NULL"`, nullable)
  - `previous_sensitivity_level` (`SAEnum(DataSensitivityLevel)`, nullable)
  - `new_sensitivity_level` (`SAEnum(DataSensitivityLevel)`, NOT NULL)
  - `change_type` (`String(32)` / `DataClassificationChangeTypeEnum`: `INITIAL`, `UPGRADE`, `DOWNGRADE`, `REVALIDATION`, NOT NULL)
  - `status` (`String(32)` / `DataClassificationRecordStatusEnum`: `PENDING_APPROVAL`, `APPROVED`, `REJECTED`, `SUPERSEDED`, NOT NULL, indexed)
  - `justification` (`Text`, NOT NULL)
  - `requested_by_id` (`Integer`, FK `users.id`, `ondelete="RESTRICT"`, NOT NULL, indexed)
  - `approved_by_id` (`Integer`, FK `users.id`, `ondelete="SET NULL"`, nullable, indexed)
  - `approved_at` (`DateTime(timezone=True)`, nullable)
  - `rejection_reason` (`Text`, nullable)
  - `effective_from` (`DateTime(timezone=True)`, nullable)
  - `effective_to` (`DateTime(timezone=True)`, nullable)
  - `created_at` (`DateTime(timezone=True)`, NOT NULL)
- **Constraints**:
  - `UniqueConstraint("data_asset_id", "version", name="uq_class_record_asset_version")`

---

## 7. `DataSensitivityLevel` Authority & Exact Boundary

### 7.1 Authoritative Rank Ordering of `DataSensitivityLevel`
In `backend/app/models/privacy.py`, `DataSensitivityLevel` has 5 canonical values. Batch 3 establishes the authoritative numeric rank map `SENSITIVITY_RANK_MAP`:

| `DataSensitivityLevel` Enum | Numeric Rank (`SENSITIVITY_RANK_MAP`) | Phase 16 `BASE_SENSITIVITY_MAP` Weight | Default Four-Eyes Mandatory? |
| :--- | :---: | :---: | :---: |
| `PUBLIC` | `1` | `0.0` | On Downgrade to `PUBLIC` |
| `INTERNAL` | `2` | `5.0` | On Downgrade to `INTERNAL` |
| `CONFIDENTIAL` | `3` | `20.0` | On Downgrade to `CONFIDENTIAL` |
| `RESTRICTED_PII` | `4` | `40.0` | **ALWAYS** (Assign, Upgrade, or Downgrade) |
| `SPECIAL_CATEGORY_SENSITIVE_PHI` | `5` | `65.0` | **ALWAYS** (Assign, Upgrade, or Downgrade) |

### 7.2 Authority Choice (Question 4 Resolution)
- **`DataClassificationLevel`** is **Option A**: the **Authoritative Configurable Governance Classification Tier** with a mandatory deterministic mapping (`mapped_sensitivity_level`) into Phase 16 `DataSensitivityLevel`.
- **`DataAsset.data_sensitivity_level`** is the **Authoritative Canonical Sensitivity Projection** on `DataAsset`.
- **Exact Synchronization Rule**:
  1. While a `DataClassificationRecord` is in `status = PENDING_APPROVAL`, `DataAsset.classification_status` is set to `PENDING_APPROVAL`, **but `DataAsset.classification_level_id` and `DataAsset.data_sensitivity_level` retain their prior approved values**.
  2. Only when the `DataClassificationRecord` transitions to `status = APPROVED` does the server atomically update `DataAsset.classification_scheme_id = record.scheme_id`, `DataAsset.classification_level_id = record.level_id`, and `DataAsset.data_sensitivity_level = level.mapped_sensitivity_level`.
  3. Therefore, a malicious actor **cannot** request a downgrade from `RESTRICTED_PII` to `PUBLIC` and immediately run a DPIA or lineage flow using `PUBLIC` before a second authorized manager/admin approves the downgrade!

---

## 8. Ownership & Stewardship Authority

### 8.1 Semantic Distinction: `DATA OWNER` vs `DATA STEWARD`
1. **`DataAsset.owner_id` (`DATA OWNER`)**:
   - **Accountable Executive / Business Owner** (`nullable=False`, FK `users.id`).
   - Accountable for business purpose, risk acceptance, retention period, and retirement initiation.
2. **`DataAsset.steward_id` (`DATA STEWARD`)**:
   - **Operational Domain Custodian / Steward** (`nullable=True`, FK `users.id`).
   - Responsible for day-to-day metadata curation, classification proposals, lineage registration, and control/evidence linkage.
   - `owner_id` and `steward_id` may be different users (recommended) or the same user in smaller teams, but their roles and fields are never conflated.

### 8.2 Governed Ownership Transfer & Inactive User Protection
- **Active Tenant User Validation**:
  - Whenever `owner_id` or `steward_id` is assigned or transferred, the service queries `User` filtering by `User.id == target_user_id` AND `User.organization_id == organization_id`.
  - If the user does not exist or belongs to another tenant $\rightarrow$ `HTTP 404 Not Found`.
  - If `user.is_active == False` $\rightarrow$ `HTTP 422 Unprocessable Entity` (`"Cannot assign an inactive user as Data Owner or Data Steward"`).
- **Orphaned / Inactive Owner Detection**:
  - Foreign keys use `ondelete="RESTRICT"` on `owner_id` and `ondelete="SET NULL"` on `steward_id`.
  - If an existing assigned owner or steward is later deactivated (`User.is_active == False`), `DataGovernanceService.get_governance_summary()` and `get_asset_governance_dossier()` automatically flag `OWNER_INACTIVE_ORPHAN_RISK` / `STEWARD_INACTIVE` so governance posture reflects the orphaned state immediately and requires reassignment via `/ownership`.
- **Ownership Transfer Audit & Four-Eyes**:
  - Changing `owner_id` on an asset classified as `RESTRICTED_PII` or `SPECIAL_CATEGORY_SENSITIVE_PHI` (or where `lifecycle_state == ACTIVE`) records a full before/after audit log (`OWNER_TRANSFERRED`) with mandatory `justification` (`min_length=5`). If a non-approver (`GRC_ANALYST` without `DATA_GOV_APPROVE`) initiates an ownership change on a restricted asset, or if `require_approval=True`, the transfer is gated by `DATA_GOV_APPROVE` (`ADMIN`/`MANAGER`).

---

## 9. Lifecycle State Machine (`DataAssetLifecycleEnum`)

### 9.1 States
1. `DISCOVERED`: Created via automated cloud/schema discovery or initial unverified intake.
2. `REGISTERED`: `owner_id` and `steward_id` verified and active.
3. `CLASSIFIED`: Asset has an `APPROVED` `DataClassificationRecord`.
4. `ACTIVE`: Approved for production use; required controls/processing links active.
5. `DEPRECATED`: Phasing out; no new outbound lineage edges permitted.
6. `RETIRED`: Terminal disposed state; requires disposal method, retirement approval, and (for restricted/confidential assets) `retirement_evidence_id`.

### 9.2 Exact Transition Table

| From State | To State | Allowed? | Required Preconditions & Guards |
| :--- | :--- | :---: | :--- |
| `DISCOVERED` | `REGISTERED` | ✅ YES | `owner_id` and `steward_id` must be assigned and active (`User.is_active == True`). |
| `DISCOVERED` | `CLASSIFIED` | ❌ NO | Must transition through `REGISTERED` first (`owner_id` and `steward_id` verified). |
| `DISCOVERED` | `ACTIVE` | ❌ NO | **Explicitly Prohibited**: Unregistered/unclassified discovered assets cannot jump directly to `ACTIVE`. |
| `REGISTERED` | `CLASSIFIED` | ✅ YES | Triggered automatically or explicitly once an `APPROVED` `DataClassificationRecord` exists. |
| `REGISTERED` | `ACTIVE` | ✅ YES | Permitted ONLY if `classification_status == APPROVED` and `owner_id` is active. |
| `CLASSIFIED` | `ACTIVE` | ✅ YES | Requires `classification_status == APPROVED` and active `owner_id`. |
| `ACTIVE` | `DEPRECATED` | ✅ YES | Requires `deprecation_notes` (`min_length=5`). |
| `CLASSIFIED` | `DEPRECATED` | ✅ YES | Requires `deprecation_notes` (`min_length=5`). |
| `DEPRECATED` | `ACTIVE` | ✅ YES | Re-activation from `DEPRECATED` requires `classification_status == APPROVED` and `DATA_GOV_APPROVE`. |
| `DEPRECATED` | `RETIRED` | ✅ YES | Requires `disposal_method != NONE`, `retirement_notes`, Four-Eyes approval (`retirement_requested_by_id != retired_by_id`), and `retirement_evidence_id` (mandatory for `CONFIDENTIAL`, `RESTRICTED_PII`, `SPECIAL_CATEGORY_SENSITIVE_PHI`). Revokes active lineage edges. |
| `ACTIVE` | `RETIRED` | ✅ YES | Same strict retirement preconditions as `DEPRECATED -> RETIRED`. |
| `RETIRED` | `ACTIVE` | ✅ YES (Restricted) | **Governed Restoration Only**: `RETIRED` assets are read-only; mutations are rejected (`409 Conflict`). Restoration (`POST .../restore`) requires `Permission.DATA_GOV_APPROVE` (`ADMIN`/`MANAGER`), Four-Eyes (`retired_by_id != restored_by_id`), and mandatory `restoration_justification`. |

---

## 10. Classification State Machine & Downgrade Attack Prevention

### 10.1 Classification Record State Machine (`DataClassificationRecordStatusEnum`)
- `PENDING_APPROVAL` $\rightarrow$ `APPROVED` (Requires `Permission.DATA_GOV_APPROVE` and `record.requested_by_id != current_user.id`)
- `PENDING_APPROVAL` $\rightarrow$ `REJECTED` (Requires `Permission.DATA_GOV_APPROVE` and `rejection_reason`)
- `APPROVED` $\rightarrow$ `SUPERSEDED` (Automatic server transition when a newer `DataClassificationRecord` on the same `DataAsset` is `APPROVED`)
- **Immutability Rule**: Once created, a `DataClassificationRecord` row is never deleted (`DELETE` returns `405 Method Not Allowed`) and its `requested_by_id`, `scheme_id`, `level_id`, `change_type`, and `justification` can never be mutated (`PUT` returns `405 Method Not Allowed`).

### 10.2 Defending Against the Classification Downgrade Attack (Section 6)
Consider the attack chain: `SPECIAL_CATEGORY_SENSITIVE_PHI (5) -> RESTRICTED_PII (4) -> CONFIDENTIAL (3) -> INTERNAL (2) -> PUBLIC (1)`.
1. **Detection of Downgrade**:
   - A classification request is a `DOWNGRADE` if **either**:
     - `SENSITIVITY_RANK_MAP[new_level.mapped_sensitivity_level] < SENSITIVITY_RANK_MAP[asset.data_sensitivity_level]`, **OR**
     - Within the same scheme, `new_level.ordinal_rank < current_level.ordinal_rank`.
2. **Mandatory Four-Eyes Gate**:
   - Four-Eyes approval (`status = PENDING_APPROVAL`, requiring `requested_by_id != approved_by_id` by a user with `Permission.DATA_GOV_APPROVE`) is **MANDATORY** whenever:
     - `change_type == DOWNGRADE` (any downgrade, even `CONFIDENTIAL -> INTERNAL` or `INTERNAL -> PUBLIC`), **OR**
     - `new_level.mapped_sensitivity_level in (RESTRICTED_PII, SPECIAL_CATEGORY_SENSITIVE_PHI)`, **OR**
     - `asset.data_sensitivity_level in (RESTRICTED_PII, SPECIAL_CATEGORY_SENSITIVE_PHI)`, **OR**
     - `new_level.requires_four_eyes_approval == True`.
3. **Authoritative State During `PENDING_APPROVAL`**:
   - While a `DataClassificationRecord` is `PENDING_APPROVAL`:
     - Only **one** `PENDING_APPROVAL` record may exist per `DataAsset` at a time (submitting a second pending request while one is pending returns `HTTP 409 Conflict`).
     - `DataAsset.data_sensitivity_level` and `DataAsset.classification_level_id` **remain locked at their previous approved values** (`RESTRICTED_PII`, etc.).
     - All downstream consumers (Phase 16 DPIA, Lineage Sensitivity Flow Gate, Cloud Posture Alignment, Retirement Evidence Gate) evaluate the **currently active approved sensitivity**, completely neutralizing unapproved downgrade bypasses.

---

## 11. Four-Eyes / Segregation of Duties (SoD) Matrix

| Workflow | Request Endpoint | Approval Endpoint | Request State | Pending State | Approved State | Rejected State | Who Can Request | Who Can Approve | SoD Rule Enforced Server-Side |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **A. Scheme Activation** | `POST /schemes/{id}/submit` | `POST /schemes/{id}/approve` | `DRAFT` | `PENDING_APPROVAL` | `ACTIVE` | `DRAFT` | `DATA_GOV_MANAGE` | `DATA_GOV_APPROVE` (`ADMIN`, `MANAGER`) | `scheme.created_by_id != current_user.id` (`403` on self-approval; DB check `ck_class_scheme_sod`) |
| **B. Standard Classification (Low-Sensitivity Initial/Upgrade)** | `POST /assets/{id}/classifications` | `POST /classifications/{id}/approve` (if `require_approval=True`) | — | `PENDING_APPROVAL` | `APPROVED` | `REJECTED` | `DATA_GOV_CLASSIFY` | `DATA_GOV_APPROVE` (`ADMIN`, `MANAGER`) | If `PENDING_APPROVAL`: `record.requested_by_id != current_user.id` (`403`) |
| **C. Restricted Classification (`RESTRICTED_PII` / `PHI`)** | `POST /assets/{id}/classifications` | `POST /classifications/{id}/approve` | — | `PENDING_APPROVAL` (Forced) | `APPROVED` | `REJECTED` | `DATA_GOV_CLASSIFY` | `DATA_GOV_APPROVE` (`ADMIN`, `MANAGER`) | **Always `PENDING_APPROVAL`**; `record.requested_by_id != current_user.id` (`403` on self-approval) |
| **D. Classification Downgrade (Any Rank Decrease)** | `POST /assets/{id}/classifications` | `POST /classifications/{id}/approve` | — | `PENDING_APPROVAL` (Forced) | `APPROVED` | `REJECTED` | `DATA_GOV_CLASSIFY` | `DATA_GOV_APPROVE` (`ADMIN`, `MANAGER`) | **Always `PENDING_APPROVAL`**; `record.requested_by_id != current_user.id` (`403` on self-approval) |
| **E. Ownership Transfer (Restricted Asset / Governed)** | `POST /assets/{id}/ownership` | `POST /assets/{id}/ownership/approve` | `ACTIVE` | `PENDING_TRANSFER` (if restricted/requested) | `ACTIVE` (Owner Updated) | `ACTIVE` (Unchanged) | `DATA_GOV_OWNER_MANAGE` | `DATA_GOV_APPROVE` (`ADMIN`, `MANAGER`) | `transfer_requested_by_id != current_user.id` (`403` on self-approval) |
| **F. Asset Retirement** | `POST /assets/{id}/retire-request` (or `retire`) | `POST /assets/{id}/retire` | `ACTIVE` / `DEPRECATED` | `retirement_requested_by_id` set | `RETIRED` | Remains `DEPRECATED` | `DATA_GOV_MANAGE` | `DATA_GOV_APPROVE` (`ADMIN`, `MANAGER`) | For restricted/confidential assets, `retirement_requested_by_id != current_user.id` (`403` on self-approval) + valid `EvidenceItem` |
| **G. Lineage Approval (Sensitivity Downgrade Flow)** | `POST /lineage-edges` | `POST /lineage-edges/{id}/approve` | — | `PENDING_APPROVAL` (Forced) | `ACTIVE` | `REVOKED` | `DATA_GOV_LINEAGE_MANAGE` | `DATA_GOV_APPROVE` (`ADMIN`, `MANAGER`) | `edge.created_by_id != current_user.id` (`403` on self-approval) |

---

## 12. Lineage Authority (`DataLineageEdge`)

- **Table**: `data_lineage_edges`
- **Model**: `DataLineageEdge` (`backend/app/models/data_governance.py`)
- **Immutability Model**: **Versioned Append-Only Ledger**.
  - Physical `DELETE` is prohibited (`DELETE /api/v1/data-governance/lineage-edges/{id}` returns `HTTP 405 Method Not Allowed`).
  - Revising an existing active lineage edge (`edge_code`) creates a new row with `version = old_edge.version + 1`, marks the prior row `status = SUPERSEDED` (`effective_to = now()`), and computes a fresh `provenance_hash`.
  - Decommissioning an edge transitions `status = REVOKED` (`revoked_by_id`, `revoked_at`, `revocation_reason`, `effective_to = now()`).

---

## 13. Lineage DAG Security & Cycle Prevention

1. **Direct Self-Loop Check**:
   - Service check + DB `CheckConstraint("source_data_asset_id != target_data_asset_id", name="ck_lineage_no_self_loop")`. Rejects `A -> A` with `HTTP 422 Unprocessable Entity`.
2. **Authoritative Graph Reachability (BFS/DFS Cycle Detection)**:
   - Before inserting or activating any directed edge `source_id -> target_id` within `organization_id`, `DataGovernanceService._validate_no_lineage_cycle(db, organization_id, source_id, target_id)` loads all non-revoked, non-superseded edges (`status in (ACTIVE, PENDING_APPROVAL)`) for `organization_id`.
   - Performs an iterative Breadth-First Search (BFS) starting from `target_id`:
     - Queue initialized with `[target_id]`, `visited = {target_id}`.
     - While queue is non-empty, pop `curr`; if `curr == source_id`, raise `HTTP 422 Unprocessable Entity` (`"Lineage DAG violation: adding edge {source_id} -> {target_id} creates a directed cycle"`).
     - Enqueue all unvisited neighbors `next_target` where an active/pending edge `curr -> next_target` exists.
   - **Verified Against All Cycle Topologies**:
     - 2-node cycle (`A -> B`, then `B -> A`): BFS from `A` visits `B == source_id` $\rightarrow$ **Blocked (`422`)**.
     - 3-node cycle (`A -> B`, `B -> C`, then `C -> A`): BFS from `A` visits `B -> C == source_id` $\rightarrow$ **Blocked (`422`)**.
     - Multi-hop cycle (`A -> B -> C -> D -> A`): BFS from `A` visits `B -> C -> D == source_id` $\rightarrow$ **Blocked (`422`)**.

---

## 14. Sensitivity Flow Rules & Canonical Provenance Hash

### 14.1 Exact Sensitivity Flow Policy (Section 16 Resolution)
Let $R(\text{asset}) = \text{SENSITIVITY\_RANK\_MAP}[\text{asset.data\_sensitivity\_level}] \in \{1, 2, 3, 4, 5\}$.
When creating a lineage edge `source_asset -> target_asset`:

| Flow Comparison | Condition | Exact Enforcement Policy |
| :--- | :--- | :--- |
| **Equal Sensitivity** ($R(\text{source}) == R(\text{target})$) | e.g., `CONFIDENTIAL -> CONFIDENTIAL` | Permitted. Edge created as `ACTIVE` (unless `require_approval=True` requested). |
| **Sensitivity Upgrade Flow** ($R(\text{source}) < R(\text{target})$) | e.g., `INTERNAL -> RESTRICTED_PII` | Permitted (lower-sensitivity data flowing into a more restricted container is safe). Edge created as `ACTIVE`. |
| **Masked/Anonymized Downgrade Flow** ($R(\text{source}) > R(\text{target})$ AND `is_masked_or_anonymized == True`) | e.g., `RESTRICTED_PII -> INTERNAL` with transformation summary | **Requires Documented Transformation & Four-Eyes Approval**: `transformation_summary` (`min_length=10`) is mandatory (`422` if missing), and edge is forced into `status = PENDING_APPROVAL` requiring Four-Eyes approval (`created_by_id != approved_by_id`). |
| **Unmasked Restricted Downgrade to `PUBLIC`** ($R(\text{source}) \ge 4$ AND `target == PUBLIC` AND `is_masked_or_anonymized == False`) | e.g., Raw `RESTRICTED_PII` or `PHI` flowing unmasked into a `PUBLIC` dataset | **STRICTLY PROHIBITED (`HTTP 422 Unprocessable Entity`)**: Raw `RESTRICTED_PII` or `SPECIAL_CATEGORY_SENSITIVE_PHI` cannot flow unmasked into a `PUBLIC` asset under any circumstance. |
| **Other Unmasked Downgrade Flows** ($R(\text{source}) > R(\text{target})$ AND `is_masked_or_anonymized == False`) | e.g., `CONFIDENTIAL -> INTERNAL` or `RESTRICTED_PII -> CONFIDENTIAL` | Requires `transformation_summary` (`min_length=10`) explaining field filtering/subsetting (`422` if omitted) AND is forced into `status = PENDING_APPROVAL` requiring Four-Eyes approval (`created_by_id != approved_by_id`). |

### 14.2 Canonical SHA-256 `provenance_hash` Specification (Section 18 Resolution)
`DataLineageEdge.provenance_hash` is computed server-side using deterministic canonical JSON serialization (matching `ExecutiveService.compute_canonical_sha256` conventions):
- **Canonical Input Dictionary**:
  ```json
  {
    "cloud_asset_id": 12,
    "created_by_id": 5,
    "edge_code": "LIN-CUST-001",
    "effective_from": "2026-09-26T13:00:00Z",
    "is_encrypted_in_transit": true,
    "is_masked_or_anonymized": true,
    "organization_id": 1,
    "processing_activity_id": 8,
    "relationship_type": "ETL_TRANSFORMATION",
    "source_data_asset_id": 101,
    "target_data_asset_id": 102,
    "transformation_summary": "SHA-256 tokenization of email and national ID",
    "version": 1
  }
  ```
- **Exact Canonicalization Rules**:
  1. Keys sorted lexicographically (`json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=False)`).
  2. `None` values serialized as JSON `null`.
  3. Strings stripped of leading/trailing whitespace (`(val or "").strip()`).
  4. `effective_from` normalized to UTC ISO-8601 string with trailing `"Z"` (`YYYY-MM-DDTHH:MM:SSZ`, microseconds truncated to `0` for cross-DB SQLite/PostgreSQL determinism).
  5. Encoded as UTF-8 bytes and hashed with `hashlib.sha256(canonical_bytes).hexdigest().lower()` (64 lowercase hex characters).

---

## 15. Privacy Integration (`PRIVACY-GRC`)

1. **Shared `DataAsset` Authority**:
   - Phase 16 `PrivacyService` and Batch 3 `DataGovernanceService` share `app.models.privacy.DataAsset`.
   - In `PrivacyService.update_data_asset` (`PUT /api/v1/privacy/data-assets/{id}`):
     - If `asset.lifecycle_state == "RETIRED"`, raise `HTTP 409 Conflict` (`"Cannot modify a RETIRED data asset"`).
     - If `asset.classification_level_id is not None` or `asset.classification_status == "PENDING_APPROVAL"`, and `payload.data_sensitivity_level` is lower rank than `asset.data_sensitivity_level`, raise `HTTP 422 Unprocessable Entity` (`"Governed data asset sensitivity downgrades require the Data Governance classification approval workflow"`).
   - In `PrivacyService.delete_data_asset` (`DELETE /api/v1/privacy/data-assets/{id}`):
     - If `asset.lifecycle_state == "RETIRED"` or the asset has governed `DataClassificationRecord` / active `DataLineageEdge` history, raise `HTTP 409 Conflict` (`"Governed data assets with lineage or classification history must be retired via Data Governance rather than hard-deleted"`).
     - Legacy Phase 16 test assets created via `POST /api/v1/privacy/data-assets` without governed classification records or lineage edges continue to support `PUT` and `DELETE` identically to Phase 16 baseline.

---

## 16. Cloud Integration (`CLOUDSEC-GRC`) & Cloud Discovery Boundary

### 16.1 Cardinality Resolution: Primary FK + M:N `DataAssetCloudLink`
To support both simple single-container datasets and multi-cloud/distributed datasets (Section 11 of prompt):
1. **`DataAsset.cloud_asset_id`** (`ForeignKey("cloud_assets.id", ondelete="SET NULL")`, nullable): Points to the primary hosting `CloudAsset`.
2. **`DataAssetCloudLink` (`data_asset_cloud_links`)**: Authoritative M:N bridge table allowing a `DataAsset` to link to multiple `CloudAsset` resources (`PRIMARY_STORE`, `REPLICA_STORE`, `BACKUP_ARCHIVE`, `PROCESSING_COMPUTE`, `ENCRYPTION_KEY_VAULT`) and allowing one `CloudAsset` (e.g. an S3 bucket or RDS cluster) to host multiple `DataAsset` records.
   - Constraint: `UniqueConstraint("organization_id", "data_asset_id", "cloud_asset_id", name="uq_data_asset_cloud_link")`.
   - Linking a `CloudAsset` with `hosting_role == PRIMARY_STORE` automatically sets `DataAsset.cloud_asset_id = cloud_asset.id`.

### 16.2 Cloud Discovery vs. Governed Data Boundary (Section 12 Resolution)
- Cloud telemetry / CSPM discovery **NEVER** overwrites `DataAsset.data_sensitivity_level`, `classification_level_id`, or `owner_id`.
- When an asset is registered as `lifecycle_state = DISCOVERED` (e.g., from cloud storage discovery), its `classification_status` is `UNCLASSIFIED` and it **cannot** transition to `ACTIVE` until a human `owner_id` and `steward_id` are verified (`REGISTERED`) and a formal `DataClassificationRecord` is `APPROVED` (`CLASSIFIED`).
- **Posture Alignment Evaluation**:
  - Evaluates all linked `CloudAsset` records (`DataAsset.cloud_asset_id` and `DataAssetCloudLink`).
  - Flags `CLOUD_ENCRYPTION_MISMATCH` if `DataAsset.is_encrypted_at_rest == True` (or sensitivity $\ge$ `CONFIDENTIAL`) while a linked storage `CloudAsset` has `encryption_enabled == False`.
  - Flags `CLOUD_PUBLIC_EXPOSURE_MISMATCH` if sensitivity $>$ `PUBLIC` while a linked `CloudAsset` has `is_internet_facing == True`.
  - Flags `CLOUD_POSTURE_NON_COMPLIANT` if a linked `CloudAsset` has `posture_status == CloudPostureStatusEnum.NON_COMPLIANT`.
  - Flags `CLOUD_HOST_DECOMMISSIONED` if an `ACTIVE` `DataAsset` is linked to a `CloudAsset` with `lifecycle_state == CloudLifecycleStateEnum.DECOMMISSIONED`.

---

## 17. Processing Activity Integration (`DataAssetProcessingLink`)

- **Table**: `data_asset_processing_links` (`DataAssetProcessingLink`)
- **Columns**:
  - `id` (`Integer`, PK)
  - `organization_id` (`Integer`, FK `organizations.id`, `ondelete="CASCADE"`, NOT NULL, indexed)
  - `data_asset_id` (`Integer`, FK `data_assets.id`, `ondelete="CASCADE"`, NOT NULL, indexed)
  - `processing_activity_id` (`Integer`, FK `processing_activities.id`, `ondelete="CASCADE"`, NOT NULL, indexed)
  - `usage_role` (`String(32)` / `DataProcessingUsageRoleEnum`: `PRIMARY_SOURCE`, `INTERMEDIATE_STORE`, `OUTPUT_SINK`, `ARCHIVAL_STORE`, NOT NULL)
  - `notes` (`Text`, nullable)
  - `linked_by_id` (`Integer`, FK `users.id`, `ondelete="SET NULL"`, nullable)
  - `created_at` (`DateTime(timezone=True)`, NOT NULL)
- **Uniqueness**: `UniqueConstraint("organization_id", "data_asset_id", "processing_activity_id", name="uq_data_asset_processing_link")`.
- **Lifecycle Guard**: Linking a `DataAsset` to a `ProcessingActivity` in `lifecycle_state == RETIRED` is rejected with `HTTP 422 Unprocessable Entity`.

---

## 18. Control & Evidence Integration (`DataAssetControlLink` & `DataAssetEvidenceLink`)

Per Section 14 of the hardening prompt, control linkage and evidence linkage are separated into two dedicated, single-purpose bridge tables:

### 18.1 `DataAssetControlLink` (`data_asset_control_links`)
- Links `DataAsset` (`data_assets.id`) $\leftrightarrow$ Phase 2 `OrganizationControl` (`organization_controls.id`).
- **Columns**: `id`, `organization_id`, `data_asset_id`, `organization_control_id`, `control_objective` (`ENCRYPTION_AT_REST`, `ENCRYPTION_IN_TRANSIT`, `ACCESS_CONTROL`, `RETENTION_ENFORCEMENT`, `DLP_MONITORING`, `BACKUP_RECOVERY`, `DISPOSAL_VERIFICATION`), `is_mandatory` (`Boolean`, default `True`), `coverage_notes` (`Text`), `linked_by_id` (`FK users.id`), `created_at`.
- **Constraint**: `UniqueConstraint("organization_id", "data_asset_id", "organization_control_id", name="uq_data_asset_control_link")`.

### 18.2 `DataAssetEvidenceLink` (`data_asset_evidence_links`)
- Links `DataAsset` (`data_assets.id`) $\leftrightarrow$ Phase 3 `EvidenceItem` (`evidence_items.id`).
- **Columns**: `id`, `organization_id`, `data_asset_id`, `evidence_item_id`, `evidence_purpose` (`CLASSIFICATION_JUSTIFICATION`, `ENCRYPTION_ATTESTATION`, `LINEAGE_VALIDATION`, `RETENTION_DISPOSAL_CERTIFICATE`, `STEWARDSHIP_AUDIT`), `notes` (`Text`), `linked_by_id` (`FK users.id`), `created_at`.
- **Constraint**: `UniqueConstraint("organization_id", "data_asset_id", "evidence_item_id", "evidence_purpose", name="uq_data_asset_evidence_link")`.

### 18.3 Retirement / Disposal Evidence Verification (Section 10 Resolution)
- When retiring a `DataAsset` with sensitivity $\ge$ `CONFIDENTIAL` (or `requires_four_eyes_approval == True`):
  1. `retirement_evidence_id` is **mandatory** (`HTTP 422` if `None`).
  2. The referenced `EvidenceItem` must exist in `current_user.organization_id` (`HTTP 404` if cross-tenant or missing).
  3. The `EvidenceItem.status` (`EvidenceStatusEnum` in `app/models/evidence.py`) must be in `(EvidenceStatusEnum.UPLOADED, EvidenceStatusEnum.UNDER_REVIEW, EvidenceStatusEnum.ACCEPTED)` — if `EvidenceItem.status in (EvidenceStatusEnum.REJECTED, EvidenceStatusEnum.SUPERSEDED)`, retirement is rejected with `HTTP 422 Unprocessable Entity` (`"Cannot retire data asset using a REJECTED or SUPERSEDED evidence item"`).

---

## 19. Regulatory Integration (`REGULATORY-GRC`)

- Inspected `RegulatoryObligation` in `backend/app/models/regulatory.py` (lines 254–306):
  - `RegulatoryObligation` has `organization_control_id = Column(Integer, ForeignKey("organization_controls.id", ondelete="SET NULL"))` and `mandate_id = Column(Integer, ForeignKey("regulatory_mandates.id"))`.
- Through `DataAsset` $\rightarrow$ `DataAssetControlLink.organization_control_id` $\rightarrow$ `RegulatoryObligation.organization_control_id` $\rightarrow$ `RegulatoryMandate`, `DataGovernanceService.get_asset_governance_dossier()` resolves all applicable statutory obligations and mandates governing a `DataAsset` without creating any duplicate regulatory tables (`DataObligation`, `DataRegulation`, etc. are strictly prohibited).

---

## 20. Continuous Assurance Integration (`CONTINUOUS-GRC`)

- `DataGovernanceService.get_governance_summary(db, organization_id)` calculates server-authoritative Data Governance assurance telemetry:
  - `total_assets`, `active_assets`, `discovered_unregistered_assets`, `retired_assets`
  - `classified_assets_count`, `pending_classification_approvals`, `unclassified_assets_count`
  - `owner_coverage_pct`, `steward_coverage_pct`, `inactive_owner_count`
  - `active_lineage_edges_count`, `pending_lineage_approvals_count`
  - `cloud_linked_assets_count`, `cloud_posture_mismatch_count`
  - `control_linked_assets_count`, `evidence_linked_assets_count`
  - `governance_health_score` (`0.00..100.00`, deterministic weighted formula computed server-side).
- Phase 23 `ContinuousComplianceService` remains the single continuous assurance engine.

---

## 21. Executive Integration (`EXECUTIVE-GRC`)

- Phase 20 `ExecutiveService` remains the single executive snapshot and briefing engine.
- `DataGovernanceService.get_executive_telemetry(db, organization_id)` returns a canonical key-sorted dictionary compatible with `ExecutiveService.compute_canonical_sha256()` so executive snapshots and board dossiers can include Data Governance posture without a second executive engine.

---

## 22. RBAC Matrix & Indirect Privilege Escalation Prevention

### 22.1 Role & Permission Matrix (`backend/app/core/permissions.py`)

| Permission Enum | String Value | `ADMIN` | `MANAGER` | `GRC_ANALYST` | `SECURITY_ANALYST` | `AUDITOR` | `VIEWER` |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `DATA_GOV_READ` | `"data_gov:read"` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `DATA_GOV_MANAGE` | `"data_gov:manage"` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| `DATA_GOV_CLASSIFY` | `"data_gov:classify"` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `DATA_GOV_APPROVE` | `"data_gov:approve"` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `DATA_GOV_LINEAGE_MANAGE` | `"data_gov:lineage_manage"` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `DATA_GOV_OWNER_MANAGE` | `"data_gov:owner_manage"` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |

### 22.2 Indirect Privilege Escalation Defenses
1. **No Classification via Asset Update**: `PUT /api/v1/data-governance/assets/{id}` (`DATA_GOV_MANAGE`) does **not** accept `data_sensitivity_level`, `classification_scheme_id`, `classification_level_id`, or `classification_status`. Classification changes must go through `POST /api/v1/data-governance/assets/{id}/classifications` (`DATA_GOV_CLASSIFY`) and approval through `POST /api/v1/data-governance/classifications/{id}/approve` (`DATA_GOV_APPROVE`).
2. **No Ownership Transfer via Asset Update**: `PUT /api/v1/data-governance/assets/{id}` does **not** accept `owner_id` or `steward_id`. Ownership and stewardship changes must go through `/ownership` (`DATA_GOV_OWNER_MANAGE` / `DATA_GOV_APPROVE`).
3. **No Retirement via Asset Update**: `PUT /api/v1/data-governance/assets/{id}` does **not** accept `lifecycle_state`, `retired_at`, `retired_by_id`, or `retirement_evidence_id`.

---

## 23. Tenant Isolation

Every query and foreign key resolution in `DataGovernanceService` enforces `organization_id == current_user.organization_id`:

| Target Foreign Key | Validated Table | Tenant Filter Applied | Cross-Tenant Failure Status |
| :--- | :--- | :--- | :---: |
| `owner_id`, `steward_id` | `users` | `User.id == uid, User.organization_id == org_id` | `404 Not Found` |
| `cloud_asset_id` | `cloud_assets` | `CloudAsset.id == cid, CloudAsset.organization_id == org_id` | `404 Not Found` |
| `business_process_id` | `business_processes` | `BusinessProcess.id == bpid, BusinessProcess.organization_id == org_id` | `404 Not Found` |
| `ai_system_id` | `ai_systems` | `AISystem.id == aiid, AISystem.organization_id == org_id` | `404 Not Found` |
| `vendor_id` | `vendors` | `Vendor.id == vid, Vendor.organization_id == org_id` | `404 Not Found` |
| `scheme_id` | `data_classification_schemes` | `DataClassificationScheme.id == sid, DataClassificationScheme.organization_id == org_id` | `404 Not Found` |
| `level_id` | `data_classification_levels` | `DataClassificationLevel.id == lid, DataClassificationLevel.organization_id == org_id` | `404 Not Found` |
| `source_data_asset_id`, `target_data_asset_id` | `data_assets` | `DataAsset.id == aid, DataAsset.organization_id == org_id` | `404 Not Found` |
| `processing_activity_id` | `processing_activities` | `ProcessingActivity.id == pid, ProcessingActivity.organization_id == org_id` | `404 Not Found` |
| `organization_control_id` | `organization_controls` | `OrganizationControl.id == ocid, OrganizationControl.organization_id == org_id` | `404 Not Found` |
| `evidence_item_id`, `retirement_evidence_id` | `evidence_items` | `EvidenceItem.id == eid, EvidenceItem.organization_id == org_id` | `404 Not Found` |

---

## 24. Mass Assignment Protection

All Pydantic request schemas in `backend/app/schemas/data_governance.py` use `extra="forbid"` (or explicit field whitelisting) and strictly exclude all server-controlled authority columns:
- **Never accepted from client request bodies**:
  - `organization_id`
  - `created_by_id`, `requested_by_id`, `classified_by_id`, `linked_by_id`, `retired_by_id`, `revoked_by_id`
  - `approved_by_id`, `classification_approved_by_id`
  - `approved_at`, `classification_approved_at`, `retired_at`, `revoked_at`, `created_at`, `updated_at`
  - `status`, `classification_status`, `change_type`, `version`
  - `provenance_hash`
  - `previous_level_id`, `previous_sensitivity_level`, `new_sensitivity_level`

---

## 25. Concurrency Model

1. **Single Pending Classification Invariant**:
   - Before inserting a `PENDING_APPROVAL` `DataClassificationRecord` for `data_asset_id`, the service queries for any existing record with `data_asset_id == asset.id` and `status == PENDING_APPROVAL`. If found, raises `HTTP 409 Conflict` (`"Data asset already has a pending classification request"`).
2. **One-Time Approval Guard**:
   - Scheme approval (`scheme.status != PENDING_APPROVAL`), classification record approval/rejection (`record.status != PENDING_APPROVAL`), lineage approval (`edge.status != PENDING_APPROVAL`), and asset retirement (`asset.lifecycle_state == RETIRED`) check current state inside the transaction and raise `HTTP 409 Conflict` if already finalized.
3. **Database-Level Integrity Catch**:
   - All `db.commit()` calls in `DataGovernanceService` catch `sqlalchemy.exc.IntegrityError`, roll back the session (`db.rollback()`), and raise `HTTP 409 Conflict`.

---

## 26. Idempotency Model

| Relationship / Entity | Unique Constraint Name | Columns | Duplicate Request Behavior |
| :--- | :--- | :--- | :---: |
| Data Asset Code | `uq_data_asset_org_code` | `(organization_id, asset_code)` | `409 Conflict` |
| Classification Scheme | `uq_class_scheme_org_code_ver` | `(organization_id, scheme_code, version)` | `409 Conflict` |
| Classification Level Code | `uq_class_level_scheme_code` | `(scheme_id, level_code)` | `409 Conflict` |
| Classification Level Rank | `uq_class_level_scheme_rank` | `(scheme_id, ordinal_rank)` | `409 Conflict` |
| Classification Record Version | `uq_class_record_asset_version` | `(data_asset_id, version)` | `409 Conflict` |
| Lineage Edge Code + Version | `uq_lineage_edge_org_code_ver` | `(organization_id, edge_code, version)` | `409 Conflict` |
| Asset $\leftrightarrow$ Cloud Resource Link | `uq_data_asset_cloud_link` | `(organization_id, data_asset_id, cloud_asset_id)` | `409 Conflict` |
| Asset $\leftrightarrow$ Processing Activity Link | `uq_data_asset_processing_link` | `(organization_id, data_asset_id, processing_activity_id)` | `409 Conflict` |
| Asset $\leftrightarrow$ Control Link | `uq_data_asset_control_link` | `(organization_id, data_asset_id, organization_control_id)` | `409 Conflict` |
| Asset $\leftrightarrow$ Evidence Link | `uq_data_asset_evidence_link` | `(organization_id, data_asset_id, evidence_item_id, evidence_purpose)` | `409 Conflict` |

---

## 27. Audit Logging

Mapped to ControlSphere's `AuditService.log(db, organization_id, action, resource_type, actor_email, actor_id, resource_id, details)` convention:

| Event Action | `resource_type` | `details` Payload |
| :--- | :--- | :--- |
| `DATA_GOV_SCHEME_CREATED` | `data_classification_scheme` | `{scheme_code, version, is_default}` |
| `DATA_GOV_SCHEME_SUBMITTED` | `data_classification_scheme` | `{scheme_code, version, levels_count}` |
| `DATA_GOV_SCHEME_APPROVED` | `data_classification_scheme` | `{scheme_code, version, created_by_id, approved_by_id}` |
| `DATA_GOV_LEVEL_CREATED` | `data_classification_level` | `{scheme_id, level_code, ordinal_rank, mapped_sensitivity_level}` |
| `DATA_GOV_ASSET_CREATED` | `data_asset` | `{asset_code, asset_type, lifecycle_state, owner_id, steward_id}` |
| `DATA_GOV_ASSET_UPDATED` | `data_asset` | `{asset_code, updated_fields}` |
| `DATA_GOV_ASSET_REGISTERED` | `data_asset` | `{asset_code, previous_state, new_state: "REGISTERED", owner_id, steward_id}` |
| `DATA_GOV_OWNER_ASSIGNED` | `data_asset` | `{asset_code, previous_owner_id, new_owner_id, previous_steward_id, new_steward_id, justification}` |
| `DATA_GOV_OWNER_TRANSFERRED` | `data_asset` | `{asset_code, previous_owner_id, new_owner_id, approved_by_id, justification}` |
| `DATA_GOV_CLASSIFICATION_REQUESTED` | `data_classification_record` | `{data_asset_id, version, change_type, previous_sensitivity, new_sensitivity, status}` |
| `DATA_GOV_CLASSIFICATION_APPROVED` | `data_classification_record` | `{data_asset_id, record_id, change_type, requested_by_id, approved_by_id, new_sensitivity}` |
| `DATA_GOV_CLASSIFICATION_REJECTED` | `data_classification_record` | `{data_asset_id, record_id, requested_by_id, rejected_by_id, rejection_reason}` |
| `DATA_GOV_LINEAGE_CREATED` | `data_lineage_edge` | `{edge_code, version, source_data_asset_id, target_data_asset_id, status, provenance_hash}` |
| `DATA_GOV_LINEAGE_APPROVED` | `data_lineage_edge` | `{edge_code, version, created_by_id, approved_by_id, provenance_hash}` |
| `DATA_GOV_LINEAGE_REVISED` | `data_lineage_edge` | `{edge_code, old_version, new_version, provenance_hash}` |
| `DATA_GOV_LINEAGE_REVOKED` | `data_lineage_edge` | `{edge_code, version, revoked_by_id, revocation_reason}` |
| `DATA_GOV_CLOUD_LINK_CREATED` | `data_asset_cloud_link` | `{data_asset_id, cloud_asset_id, hosting_role}` |
| `DATA_GOV_PROCESSING_LINK_CREATED` | `data_asset_processing_link` | `{data_asset_id, processing_activity_id, usage_role}` |
| `DATA_GOV_CONTROL_LINK_CREATED` | `data_asset_control_link` | `{data_asset_id, organization_control_id, control_objective}` |
| `DATA_GOV_EVIDENCE_LINK_CREATED` | `data_asset_evidence_link` | `{data_asset_id, evidence_item_id, evidence_purpose}` |
| `DATA_GOV_ASSET_DEPRECATED` | `data_asset` | `{asset_code, previous_state, deprecation_notes}` |
| `DATA_GOV_ASSET_RETIRE_REQUESTED` | `data_asset` | `{asset_code, requested_by_id, disposal_method, retirement_evidence_id}` |
| `DATA_GOV_ASSET_RETIRED` | `data_asset` | `{asset_code, requested_by_id, retired_by_id, disposal_method, retirement_evidence_id}` |
| `DATA_GOV_ASSET_RESTORED` | `data_asset` | `{asset_code, restored_by_id, restoration_justification}` |

---

## 28. Migration Strategy (`0024_data_governance_and_lineage.py`)

- **File**: `backend/alembic/versions/0024_data_governance_and_lineage.py` (`revision = "0024"`, `down_revision = "0023"`)
- **Safe Backfill & SQLite/PostgreSQL Compatibility**:
  1. Uses `sa.String(length=...)` with explicit `server_default` on new non-null columns added to `data_assets` (matching `0022` and `0023` migration patterns) so neither PostgreSQL enum type DDL locks nor SQLite `ALTER TABLE ADD COLUMN` restrictions fail on existing `DataAsset` rows:
     - `asset_type`: `sa.String(length=64), server_default="DATABASE_TABLE", nullable=False`
     - `lifecycle_state`: `sa.String(length=32), server_default="ACTIVE", nullable=False`
     - `classification_status`: `sa.String(length=32), server_default="APPROVED", nullable=False`
     - `owner_transfer_status`: `sa.String(length=32), server_default="NONE", nullable=False`
  2. All new foreign key columns added to `data_assets` (`steward_id`, `cloud_asset_id`, `classification_scheme_id`, `classification_level_id`, `classified_by_id`, `classification_approved_by_id`, `pending_owner_id`, `owner_transfer_requested_by_id`, `retirement_requested_by_id`, `retired_by_id`, `retirement_evidence_id`) are `nullable=True`, requiring zero destructive backfill on existing Phase 16 rows.
  3. Uses `op.batch_alter_table("data_assets")` for adding columns, foreign keys, and indexes on `data_assets` so both SQLite and PostgreSQL execute `upgrade()` and `downgrade()` cleanly.
  4. Creates the 7 new Batch 3 tables (`data_classification_schemes`, `data_classification_levels`, `data_classification_records`, `data_lineage_edges`, `data_asset_cloud_links`, `data_asset_processing_links`, `data_asset_control_links`, `data_asset_evidence_links` — wait: 3 classification tables + 1 lineage table + 4 link tables = 8 tables total, all cleanly scoped to `organization_id`).

---

## 29. Backward Compatibility

1. **Existing Phase 16 `POST /api/v1/privacy/data-assets`**:
   - Accepts `DataAssetCreate` (`asset_code`, `name`, `description`, `data_sensitivity_level`, `data_volume_range`, `storage_type`, `hosting_jurisdiction`, `is_encrypted_at_rest`, `is_encrypted_in_transit`, `is_pseudonymized`, `retention_period_months`, `business_process_id`, `ai_system_id`, `vendor_id`).
   - ORM/DB defaults automatically populate `asset_type = "DATABASE_TABLE"`, `lifecycle_state = "ACTIVE"`, `classification_status = "APPROVED"`, `owner_transfer_status = "NONE"`.
2. **Existing Phase 16 `DataAssetResponse`**:
   - Returns all original Phase 16 fields plus optional Batch 3 governance fields with safe defaults, breaking zero existing tests or frontend consumers.

---

## 30. API Boundary (`/api/v1/data-governance`)

Mounted at `/api/v1/data-governance` in `backend/app/api/v1/api.py`:
1. `GET /summary` (`DATA_GOV_READ`)
2. `POST /schemes` (`DATA_GOV_MANAGE`)
3. `GET /schemes` (`DATA_GOV_READ`)
4. `GET /schemes/{scheme_id}` (`DATA_GOV_READ`)
5. `POST /schemes/{scheme_id}/levels` (`DATA_GOV_MANAGE`)
6. `POST /schemes/{scheme_id}/submit` (`DATA_GOV_MANAGE`)
7. `POST /schemes/{scheme_id}/approve` (`DATA_GOV_APPROVE`)
8. `POST /assets` (`DATA_GOV_MANAGE`)
9. `GET /assets` (`DATA_GOV_READ`)
10. `GET /assets/{asset_id}` (`DATA_GOV_READ` — full governance dossier)
11. `PUT /assets/{asset_id}` (`DATA_GOV_MANAGE` — metadata only; blocks sensitivity/owner/lifecycle mass assignment)
12. `POST /assets/{asset_id}/register` (`DATA_GOV_MANAGE` — `DISCOVERED -> REGISTERED`)
13. `POST /assets/{asset_id}/activate` (`DATA_GOV_MANAGE` — `REGISTERED/CLASSIFIED -> ACTIVE`)
14. `POST /assets/{asset_id}/ownership` (`DATA_GOV_OWNER_MANAGE` — assign/request transfer of owner/steward)
15. `POST /assets/{asset_id}/ownership/approve` (`DATA_GOV_APPROVE` — Four-Eyes approve pending owner transfer)
16. `POST /assets/{asset_id}/classifications` (`DATA_GOV_CLASSIFY` — submit classification record)
17. `GET /assets/{asset_id}/classifications` (`DATA_GOV_READ` — list immutable classification history)
18. `POST /classifications/{record_id}/approve` (`DATA_GOV_APPROVE` — Four-Eyes approve pending classification)
19. `POST /classifications/{record_id}/reject` (`DATA_GOV_APPROVE` — reject pending classification)
20. `DELETE /classifications/{record_id}` & `PUT /classifications/{record_id}` $\rightarrow$ `405 Method Not Allowed`
21. `POST /lineage-edges` (`DATA_GOV_LINEAGE_MANAGE` — create/version lineage edge with DAG & sensitivity gate)
22. `GET /lineage-edges` (`DATA_GOV_READ`)
23. `POST /lineage-edges/{edge_id}/approve` (`DATA_GOV_APPROVE` — Four-Eyes approve pending lineage edge)
24. `POST /lineage-edges/{edge_id}/revoke` (`DATA_GOV_LINEAGE_MANAGE` — revoke active lineage edge)
25. `DELETE /lineage-edges/{edge_id}` $\rightarrow$ `405 Method Not Allowed`
26. `POST /assets/{asset_id}/cloud-links` (`DATA_GOV_MANAGE` — link `DataAsset` to `CloudAsset`)
27. `POST /assets/{asset_id}/processing-links` (`DATA_GOV_MANAGE` — link `DataAsset` to `ProcessingActivity`)
28. `POST /assets/{asset_id}/control-links` (`DATA_GOV_MANAGE` — link `DataAsset` to `OrganizationControl`)
29. `POST /assets/{asset_id}/evidence-links` (`DATA_GOV_MANAGE` — link `DataAsset` to `EvidenceItem`)
30. `POST /assets/{asset_id}/deprecate` (`DATA_GOV_MANAGE` — transition to `DEPRECATED`)
31. `POST /assets/{asset_id}/retire` (`DATA_GOV_MANAGE` / `DATA_GOV_APPROVE` — request or Four-Eyes finalize governed retirement with `EvidenceItem`)
32. `POST /assets/{asset_id}/restore` (`DATA_GOV_APPROVE` — Four-Eyes governed restoration from `RETIRED` to `ACTIVE`)

---

## 31. Frontend Boundary

- **Types**: `frontend/src/types/dataGovernance.ts`
- **Service**: `frontend/src/lib/dataGovernanceService.ts`
- **Page**: `frontend/src/pages/DataGovernancePage.tsx` (displays server-calculated posture metrics, asset catalog & lifecycle controls, classification scheme & Four-Eyes approval queue, directed lineage graph with SHA-256 provenance digest, and cross-domain links to Cloud, RoPA, Controls, and Evidence).
- **Zero Client-Side Authority**: Frontend never computes sensitivity scores, provenance hashes, or posture compliance percentages.

---

## 32. Architectural Anti-Duplication Gate

| Potential Duplicate | Created in Batch 3? | Authoritative Engine Used Instead | Gate Verdict |
| :--- | :---: | :--- | :---: |
| `DataAsset2` / `DataInventory2` | **NO** | `DataAsset` (`data_assets` in `app/models/privacy.py`) extended in-place | **PASS** |
| `ProcessingActivity2` | **NO** | `ProcessingActivity` (`processing_activities` in `app/models/privacy.py`) | **PASS** |
| `DPIA2` | **NO** | `DPIAAssessment` (`dpia_assessments` in `app/models/privacy.py`) | **PASS** |
| `DataTransfer2` | **NO** | `DataTransferAssessment` (`data_transfer_assessments` in `app/models/privacy.py`) | **PASS** |
| `CloudAsset2` | **NO** | `CloudAsset` (`cloud_assets` in `app/models/cloudsec.py`) | **PASS** |
| `DataFinding` | **NO** | `Finding` (`findings` in `app/models/finding.py`) | **PASS** |
| `DataRisk` | **NO** | `Risk` (`risks` in `app/models/risk.py`) | **PASS** |
| `DataEvidence` / `DataRetirementEvidence` | **NO** | `EvidenceItem` (`evidence_items` in `app/models/evidence.py`) | **PASS** |
| `DataRemediation` | **NO** | `RemediationPlan` (`remediation_plans` in `app/models/remediation.py`) | **PASS** |
| `DataControl` | **NO** | `OrganizationControl` (`organization_controls` in `app/models/control.py`) | **PASS** |
| `DataObligation` / `DataRegulation` | **NO** | `RegulatoryObligation` (`regulatory_obligations` in `app/models/regulatory.py`) | **PASS** |
| Second Lineage Engine | **NO** | Single `DataLineageEdge` (`data_lineage_edges`) | **PASS** |
| Second Audit Engine | **NO** | `AuditLog` / `AuditService` (`app/services/audit_service.py`) | **PASS** |
| Second Continuous Assurance Engine | **NO** | `ContinuousComplianceService` (`app/services/continuous_compliance_service.py`) | **PASS** |
| Second Executive Metrics Engine | **NO** | `ExecutiveService` (`app/services/executive_service.py`) | **PASS** |

---

## 33. Threat Model (45 Adversarial Vectors)

| Vector ID | Threat Description | Server-Side Defense & Mitigation | Expected HTTP Status |
| :--- | :--- | :--- | :---: |
| `SEC-B3-01` | Cross-tenant asset read (`GET /data-governance/assets/{other_org_asset_id}`) | Query scoped by `DataAsset.organization_id == current_user.organization_id` | `404 Not Found` |
| `SEC-B3-02` | Cross-tenant asset mutation (`PUT /data-governance/assets/{other_org_asset_id}`) | Query scoped by `DataAsset.organization_id == current_user.organization_id` | `404 Not Found` |
| `SEC-B3-03` | `organization_id` tampering in request body | `organization_id` omitted from all Pydantic create/update schemas (`extra="forbid"`); derived from JWT | `422` / Ignored |
| `SEC-B3-04` | Classification privilege escalation by user without `DATA_GOV_CLASSIFY` | `require_permission(Permission.DATA_GOV_CLASSIFY)` on `/classifications` | `403 Forbidden` |
| `SEC-B3-05` | `VIEWER` attempting any write, classify, lineage, or approval mutation | `VIEWER` has only `DATA_GOV_READ` | `403 Forbidden` |
| `SEC-B3-06` | `AUDITOR` attempting any write, classify, lineage, or approval mutation | `AUDITOR` has only `DATA_GOV_READ` | `403 Forbidden` |
| `SEC-B3-07` | Classification self-approval (`requested_by_id == current_user.id`) | Explicit server check `if record.requested_by_id == current_user.id` raises `403` | `403 Forbidden` |
| `SEC-B3-08` | Owner transfer self-approval (`owner_transfer_requested_by_id == current_user.id`) | Explicit server check `if asset.owner_transfer_requested_by_id == current_user.id` raises `403` | `403 Forbidden` |
| `SEC-B3-09` | Lineage cross-tenant injection (`source` or `target` asset in another tenant) | Both `source_data_asset_id` and `target_data_asset_id` verified in `current_user.organization_id` | `404 Not Found` |
| `SEC-B3-10` | Lineage self-loop (`source_data_asset_id == target_data_asset_id`) | Service validation + DB `ck_lineage_no_self_loop` | `422 Unprocessable Entity` |
| `SEC-B3-11` | Lineage 3-node cycle (`A -> B -> C -> A`) | BFS reachability check from `target` to `source` detects `A` reachable from `A` | `422 Unprocessable Entity` |
| `SEC-B3-12` | Lineage multi-hop cycle (`A -> B -> C -> D -> A` and `A -> B -> A`) | Full transitive BFS across active/pending tenant edges blocks cycle | `422 Unprocessable Entity` |
| `SEC-B3-13` | Duplicate lineage replay (`same edge_code + version`) | `uq_lineage_edge_org_code_ver` + pre-check raises `409 Conflict` | `409 Conflict` |
| `SEC-B3-14` | Historical lineage tampering (`DELETE /lineage-edges/{id}`) | Explicit `DELETE` route handler returns `405 Method Not Allowed` | `405 Method Not Allowed` |
| `SEC-B3-15` | Classification downgrade bypass via `PUT /data-governance/assets/{id}` or `PUT /privacy/data-assets/{id}` | `data_sensitivity_level` excluded from `GovernedDataAssetUpdate`; legacy `PrivacyService.update_data_asset` blocks sensitivity downgrade on governed assets | `422 Unprocessable Entity` |
| `SEC-B3-16` | Restricted classification (`RESTRICTED_PII` / `SPECIAL_CATEGORY_SENSITIVE_PHI`) immediate activation without Four-Eyes | Forced into `status = PENDING_APPROVAL`; active sensitivity unchanged until second user approves | `201 Created` (`PENDING_APPROVAL`) |
| `SEC-B3-17` | Stale / retired asset resurrection without Four-Eyes approval | `RETIRED -> ACTIVE` blocked on standard endpoints; `/restore` requires `DATA_GOV_APPROVE` + Four-Eyes (`retired_by_id != current_user.id`) | `403 Forbidden` / `409 Conflict` |
| `SEC-B3-18` | Retired asset mutation (`PUT`, `classify`, `lineage`, `ownership` on `RETIRED` asset) | All mutating methods check `if asset.lifecycle_state == RETIRED` and reject | `409 Conflict` |
| `SEC-B3-19` | Cloud resource cross-tenant linking (`cloud_asset_id` from Org B) | `CloudAsset` queried with `organization_id == current_user.organization_id` | `404 Not Found` |
| `SEC-B3-20` | Foreign classification scheme / level linking (`scheme_id` or `level_id` from Org B) | `DataClassificationScheme` and `DataClassificationLevel` queried with `organization_id == current_user.organization_id` | `404 Not Found` |
| `SEC-B3-21` | Foreign processing activity linking (`processing_activity_id` from Org B) | `ProcessingActivity` queried with `organization_id == current_user.organization_id` | `404 Not Found` |
| `SEC-B3-22` | Foreign control linking (`organization_control_id` from Org B) | `OrganizationControl` queried with `organization_id == current_user.organization_id` | `404 Not Found` |
| `SEC-B3-23` | Foreign evidence linking (`evidence_item_id` or `retirement_evidence_id` from Org B) | `EvidenceItem` queried with `organization_id == current_user.organization_id` | `404 Not Found` |
| `SEC-B3-24` | Linking `DataAsset` to a `RETIRED` `ProcessingActivity` | Checked in `link_processing_activity`: rejects if `activity.lifecycle_state == RETIRED` | `422 Unprocessable Entity` |
| `SEC-B3-25` | Linking `DataAsset` to a `REJECTED` or `SUPERSEDED` `EvidenceItem` | Checked in `link_evidence_item` and `retire_data_asset`: rejects invalid evidence status | `422 Unprocessable Entity` |
| `SEC-B3-26` | Duplicate pending classification request or duplicate pending ownership transfer | Rejects concurrent pending request with `409 Conflict` | `409 Conflict` |
| `SEC-B3-27` | Unauthorized ownership transfer by `SECURITY_ANALYST` | `SECURITY_ANALYST` lacks `DATA_GOV_OWNER_MANAGE` | `403 Forbidden` |
| `SEC-B3-28` | Assigning an inactive user (`User.is_active == False`) as `owner_id` or `steward_id` | Explicit check `if not user.is_active` raises `422` | `422 Unprocessable Entity` |
| `SEC-B3-29` | Race-condition / replay double approval of classification record | Checks `if record.status != PENDING_APPROVAL` $\rightarrow$ `409 Conflict` | `409 Conflict` |
| `SEC-B3-30` | Race-condition / replay double retirement of data asset | Checks `if asset.lifecycle_state == RETIRED` $\rightarrow$ `409 Conflict` | `409 Conflict` |
| `SEC-B3-31` | Audit-log omission on governance state change | Every mutating service method writes `AuditLog` via `AuditService.log` | Verified in `audit_logs` |
| `SEC-B3-32` | Client-side authority manipulation (supplying `approved_by_id`, `classification_status`, `lifecycle_state`) | Stripped/rejected by Pydantic schemas; set exclusively by server logic | `422` / Server-Derived |
| `SEC-B3-33` | API mass assignment via unexpected JSON properties | `model_config = ConfigDict(extra="forbid")` on request schemas | `422 Unprocessable Entity` |
| `SEC-B3-34` | Hidden privilege escalation: `GRC_ANALYST` attempting scheme/classification/lineage/retirement approval | `GRC_ANALYST` lacks `DATA_GOV_APPROVE` (`ADMIN` and `MANAGER` only) | `403 Forbidden` |
| `SEC-B3-35` | Classification history mutation (`DELETE` or `PUT` on `/classifications/{record_id}`) | Explicit `405 Method Not Allowed` endpoints | `405 Method Not Allowed` |
| `SEC-B3-36` | Provenance hash forgery in `POST /lineage-edges` | `provenance_hash` not accepted in request schema; computed server-side via canonical SHA-256 | `422` / Server-Computed |
| `SEC-B3-37` | Cloud auto-discovery classification overwrite (`DISCOVERED` asset skipping to `ACTIVE`) | `DISCOVERED -> ACTIVE` blocked (`422`); cloud linkage never mutates `data_sensitivity_level` | `422 Unprocessable Entity` |
| `SEC-B3-38` | Cross-tenant `owner_id` or `steward_id` assignment | User lookup scoped by `organization_id == current_user.organization_id` | `404 Not Found` |
| `SEC-B3-39` | Retiring a `RESTRICTED_PII` or `SPECIAL_CATEGORY_SENSITIVE_PHI` asset without `retirement_evidence_id` | Mandatory check raises `422 Unprocessable Entity` | `422 Unprocessable Entity` |
| `SEC-B3-40` | Lineage sensitivity downgrade bypass (unmasked `RESTRICTED_PII -> PUBLIC` or unapproved `RESTRICTED_PII -> INTERNAL`) | Unmasked `RESTRICTED_PII/PHI -> PUBLIC` blocked (`422`); other downgrades require `transformation_summary` and force `PENDING_APPROVAL` | `422` / `PENDING_APPROVAL` |
| `SEC-B3-41` | Scheme self-approval (`scheme.created_by_id == current_user.id`) | Server check + DB `ck_class_scheme_sod` raises `403 Forbidden` | `403 Forbidden` |
| `SEC-B3-42` | Lineage self-approval (`edge.created_by_id == current_user.id`) | Server check raises `403 Forbidden` | `403 Forbidden` |
| `SEC-B3-43` | Contradictory `ordinal_rank` vs `mapped_sensitivity_level` in `DataClassificationLevel` | Validated on level creation: higher `ordinal_rank` cannot map to a lower `DataSensitivityLevel` rank than a lower `ordinal_rank` | `422 Unprocessable Entity` |
| `SEC-B3-44` | Activating a `DataClassificationScheme` with $< 2$ levels | Checked on `/submit` and `/approve`: requires $\ge 2$ levels | `422 Unprocessable Entity` |
| `SEC-B3-45` | Deleting a governed `DataAsset` with classification/lineage history via legacy `DELETE /api/v1/privacy/data-assets/{id}` | Blocked in `PrivacyService.delete_data_asset` (`409 Conflict`), enforcing governed retirement | `409 Conflict` |

---

## 34. Adversarial Test Matrix

1. **`backend/tests/test_data_governance_domain.py`** (Minimum 18 domain/service tests):
   - Scheme & level creation, monotonic rank-to-sensitivity validation, $<2$ level submission rejection, Four-Eyes scheme activation.
   - `DataAsset` lifecycle transitions (`DISCOVERED -> REGISTERED -> CLASSIFIED -> ACTIVE -> DEPRECATED -> RETIRED -> RESTORED`), blocking `DISCOVERED -> ACTIVE`.
   - Classification upgrade, downgrade (`PENDING_APPROVAL` lock preserving current sensitivity), restricted sensitivity gate, Four-Eyes approval & rejection, immutable history superseding.
   - Ownership & stewardship assignment, inactive user rejection (`422`), restricted ownership transfer Four-Eyes approval, inactive owner orphan detection in summary.
   - Lineage DAG cycle prevention (`A -> A`, `A -> B -> A`, `A -> B -> C -> A`, `A -> B -> C -> D -> A`), canonical SHA-256 `provenance_hash` determinism, sensitivity flow gating (`RESTRICTED_PII -> PUBLIC` blocked, masked downgrade `PENDING_APPROVAL`), versioned superseding and revocation.
   - Cloud M:N linkage (`DataAssetCloudLink`), encryption/exposure/decommissioned posture mismatch detection without overwriting classification.
   - Control, Evidence, and Processing Activity linkage, regulatory obligation resolution, and retirement evidence verification (blocking `REJECTED`/`SUPERSEDED` evidence).
2. **`backend/tests/test_data_governance_api.py`** (Minimum 22 API/security tests):
   - Full 6-role RBAC matrix (`ADMIN`, `MANAGER`, `GRC_ANALYST`, `SECURITY_ANALYST`, `AUDITOR`, `VIEWER`).
   - All cross-tenant isolation probes (`SEC-B3-01`, `SEC-B3-02`, `SEC-B3-09`, `SEC-B3-19` through `SEC-B3-23`, `SEC-B3-38`) returning `404`.
   - Four-Eyes self-approval blocks (`SEC-B3-07`, `SEC-B3-08`, `SEC-B3-41`, `SEC-B3-42`) returning `403`.
   - Mass assignment & `extra="forbid"` checks (`SEC-B3-03`, `SEC-B3-32`, `SEC-B3-33`, `SEC-B3-36`).
   - Ledger immutability `405 Method Not Allowed` checks (`SEC-B3-14`, `SEC-B3-35`).
   - Replay & duplicate constraint `409 Conflict` checks (`SEC-B3-13`, `SEC-B3-18`, `SEC-B3-26`, `SEC-B3-29`, `SEC-B3-30`, `SEC-B3-45`).

---

## 35. Implementation File Inventory

| Path | Action | Purpose | Authority | Security Impact | Test Impact |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `backend/alembic/versions/0024_data_governance_and_lineage.py` | **CREATE** | Alembic migration `0024` (revises `0023`) extending `data_assets` and creating Batch 3 governance tables. | Schema Migration | Enforces DB uniqueness, FKs, and SoD check constraints. | Verified via migration head & schema tests. |
| `backend/app/models/privacy.py` | **MODIFY** | Extend existing `DataAsset` in-place with Batch 3 lifecycle, steward, cloud, classification, ownership transfer, and retirement columns. | `DataAsset` Authority | Preserves single `DataAsset` table with safe defaults. | Tested in `test_privacy_*` and `test_data_governance_*`. |
| `backend/app/models/data_governance.py` | **CREATE** | Define Batch 3 enums and models (`DataClassificationScheme`, `DataClassificationLevel`, `DataClassificationRecord`, `DataLineageEdge`, `DataAssetCloudLink`, `DataAssetProcessingLink`, `DataAssetControlLink`, `DataAssetEvidenceLink`). | Batch 3 Governance Authority | Enforces immutable history & tenant-scoped FKs. | Tested in `test_data_governance_domain.py`. |
| `backend/app/models/__init__.py` | **MODIFY** | Export Batch 3 models and enums. | Model Registry | Ensures Alembic/SQLAlchemy metadata registration. | Imported across all test suites. |
| `backend/app/core/permissions.py` | **MODIFY** | Add `DATA_GOV_READ`, `DATA_GOV_MANAGE`, `DATA_GOV_CLASSIFY`, `DATA_GOV_APPROVE`, `DATA_GOV_LINEAGE_MANAGE`, `DATA_GOV_OWNER_MANAGE` to the 6 existing roles. | RBAC Authority | Zero new roles; strict least-privilege mapping. | Verified in `test_data_governance_api.py`. |
| `backend/app/schemas/data_governance.py` | **CREATE** | Pydantic v2 request/response schemas with `ConfigDict(extra="forbid")`. | API Validation Boundary | Prevents mass assignment & `organization_id` spoofing. | Verified in `test_data_governance_api.py`. |
| `backend/app/services/data_governance_service.py` | **CREATE** | Authoritative `DataGovernanceService` (schemes, classification state machine, Four-Eyes, DAG lineage, SHA-256 provenance, cloud alignment, retirement). | Service Authority | Enforces all tenant, SoD, lifecycle, and DAG invariants. | Verified in domain and API test suites. |
| `backend/app/services/privacy_service.py` | **MODIFY** | Add guard in `update_data_asset` and `delete_data_asset` to prevent bypassing governed `RETIRED` or `PENDING_APPROVAL` classification states via legacy routes. | Phase 16 Compatibility & Security Guard | Closes `SEC-B3-15` and `SEC-B3-45` bypass vectors while keeping Phase 16 tests 100% green. | Verified in `test_privacy_api.py` and `test_data_governance_api.py`. |
| `backend/app/api/v1/endpoints/data_governance.py` | **CREATE** | FastAPI router under `/api/v1/data-governance` (all governance endpoints + `405` immutability handlers). | HTTP API Boundary | Enforces `require_permission` on every route. | Verified in `test_data_governance_api.py`. |
| `backend/app/api/v1/api.py` | **MODIFY** | Mount `data_governance.router` at `/data-governance`. | API Router | Exposes `/api/v1/data-governance/*`. | Verified in `test_data_governance_api.py`. |
| `backend/tests/test_data_governance_domain.py` | **CREATE** | Domain, state machine, DAG cycle, provenance hash, and posture alignment tests. | Test Suite | Validates all domain invariants. | New Batch 3 test file. |
| `backend/tests/test_data_governance_api.py` | **CREATE** | End-to-end API, RBAC, Four-Eyes SoD, cross-tenant `404`, `405`, and `409` adversarial tests. | Security Test Suite | Validates all 45 threat vectors. | New Batch 3 test file. |
| `frontend/src/types/dataGovernance.ts` | **CREATE** | TypeScript interfaces for Data Governance & Lineage. | Frontend Types | Type safety for server-calculated responses. | Verified by `tsc -b`. |
| `frontend/src/lib/dataGovernanceService.ts` | **CREATE** | Typed Axios client for `/api/v1/data-governance`. | Frontend API Client | Uses authenticated bearer client. | Verified by `npm run build`. |
| `frontend/src/pages/DataGovernancePage.tsx` | **CREATE** | Enterprise Data Governance & Lineage UI workspace. | Frontend UI | Displays server-authoritative posture & workflows. | Verified by `npm run build`. |
| `frontend/src/App.tsx` & `frontend/src/components/layout/Sidebar.tsx` | **MODIFY** | Add `/data-governance` route and navigation item. | Frontend Navigation | Integrates workspace into ControlSphere shell. | Verified by `npm run build`. |

---

## 36. Batch Boundary Decision

- **Evaluation of Capabilities A–H** (Data Asset Catalog, Classification, Ownership/Stewardship, Lineage, Privacy Integration, Cloud Integration, Control/Evidence Integration, Executive/Continuous Assurance Integration):
  - Because `DataLineageEdge` sensitivity flow gating directly depends on `DataClassificationLevel` / `DataAsset.data_sensitivity_level`, and `DataAsset` retirement directly depends on Phase 3 `EvidenceItem` and active `DataLineageEdge` revocation, these capabilities share a single cohesive security boundary centered on `DataAsset`.
- **Decision**: **ONE COHESIVE BATCH (`BATCH-3-DATA-GOVERNANCE-GRC`)** implemented in a single atomic migration (`0024_data_governance_and_lineage.py`).

---

## 37. Security Gates

1. **Role Count Invariant**: Exactly 6 roles in `UserRole` (`ADMIN`, `MANAGER`, `GRC_ANALYST`, `SECURITY_ANALYST`, `AUDITOR`, `VIEWER`).
2. **Tenant Isolation Gate**: 100% of cross-tenant foreign-key references and ID lookups return `HTTP 404 Not Found`.
3. **Four-Eyes SoD Gate**: Self-approval of schemes, classification downgrades/restricted levels, ownership transfers, retirements, and restricted lineage edges returns `HTTP 403 Forbidden`.
4. **Mass Assignment Gate**: `extra="forbid"` rejects unexpected fields (`422`) and prevents client control of authority fields.
5. **DAG & Provenance Gate**: All 2-node, 3-node, and multi-hop lineage cycles return `422`, and `provenance_hash` is deterministic 64-char lowercase SHA-256 hex.
6. **Immutability Gate**: `DELETE`/`PUT` on classification records and `DELETE` on lineage edges return `405 Method Not Allowed`.

---

## 38. Regression Gates

1. **Phase 16 Privacy Suite**: `pytest backend/tests/test_privacy_domain.py backend/tests/test_privacy_api.py` passes `100%`.
2. **Phase 18 CloudSec Suite**: `pytest backend/tests/test_cloudsec_domain.py backend/tests/test_cloudsec_api.py` passes `100%`.
3. **Full Backend Regression**: All `1,038` baseline tests + all new Batch 3 tests pass (`0` failures).
4. **Frontend Build**: `npm run build` (`tsc -b && vite build`) passes with exit code `0`.

---

## 39. Open Questions

- **None**. Every authority conflict, column overlap, cardinality requirement, state machine transition, and security vector has been resolved against the actual codebase.

---

## 40. Final GO / NO-GO

- **Final Verdict**: **GO — BATCH 3 READY FOR IMPLEMENTATION**
