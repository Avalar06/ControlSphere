# ControlSphere Phase 27 — Batch 3 Implementation Report: Data Governance, Classification & Lineage (`DATA-GOVERNANCE-GRC`)

**Module**: `DATA-GOVERNANCE-GRC`
**Batch**: `BATCH-3-DATA-GOVERNANCE-GRC`
**Authoritative Base Commit**: `7b5c7954f6c4ae29a9f89e4b90497b3cc04fc7ca` (`feat(batch2): implement kri appetite governance`)
**Target Migration**: `0024_data_governance_and_lineage.py` (Revises: `0023_kri_and_risk_appetite_governance`)
**Architecture Discovery**: `PHASE27_BATCH3_ARCHITECTURE_DISCOVERY.md`
**Hardened Architecture**: `PHASE27_BATCH3_ARCHITECTURE_HARDENED.md`
**Status**: COMPLETE — ALL ADVERSARIAL GATES, MIGRATION REVERSIBILITY & REGRESSION VERIFIED

---

## 1. Executive Summary & Batch Identification
Batch 3 (`DATA-GOVERNANCE-GRC`) implements the enterprise Data Governance, Classification & Lineage vertical slice for ControlSphere. In strict accordance with the hardened architectural contract (`PHASE27_BATCH3_ARCHITECTURE_HARDENED.md`), Batch 3 extends the canonical Phase 16 `DataAsset` (`data_assets`) model in-place—preserving zero-duplication authority across Privacy (`PRIVACY-GRC`) and Cloud Security (`CLOUDSEC-GRC`)—while introducing governed classification schemes, monotonic sensitivity levels, append-only classification audit ledgers, directed acyclic graph (DAG) data lineage with cryptographic SHA-256 provenance digests, Four-Eyes Segregation of Duties (SoD) workflows, and cross-domain traceability across Cloud Assets, Processing Activities (RoPA), Organization Controls, Evidence Items, and Regulatory Obligations.

---

## 2. Authoritative Base Commit & Lineage
- **Frozen Base Commit**: `7b5c7954f6c4ae29a9f89e4b90497b3cc04fc7ca` (`7b5c795`) — `feat(batch2): implement kri appetite governance`
- **Preceding Migration Head**: `0023_kri_and_risk_appetite_governance.py`
- **Target Migration Head**: `0024_data_governance_and_lineage.py`
- **Branch**: `main`
- **Lineage Integrity**: Strict linear Alembic migration history (`0022 -> 0023 -> 0024`) with zero fork heads.

---

## 3. Alembic Migration Ledger State & Schema Delta
- **Migration Script**: `backend/alembic/versions/0024_data_governance_and_lineage.py`
- **Revision ID**: `0024`
- **Revises**: `0023`
- **In-Place Extension of `data_assets` (`op.batch_alter_table`)**:
  - Added 22 governance columns to `data_assets` with safe `server_default` values for backward compatibility with Phase 16 records: `asset_type` (`DATABASE_TABLE`), `lifecycle_state` (`ACTIVE`), `steward_id`, `cloud_asset_id`, `classification_scheme_id`, `classification_level_id`, `classification_status` (`APPROVED`), `classified_by_id`, `classification_approved_by_id`, `classification_approved_at`, `last_reviewed_at`, `owner_transfer_status` (`NONE`), `pending_owner_id`, `owner_transfer_requested_by_id`, `owner_transfer_justification`, `deprecation_notes`, `disposal_method`, `retirement_requested_by_id`, `retired_by_id`, `retired_at`, `retirement_notes`, and `retirement_evidence_id`.
- **New Governance & Bridge Tables Created (8 Tables)**:
  1. `data_classification_schemes`: Versioned tenant classification taxonomies with Four-Eyes approval lifecycle (`DRAFT`, `PENDING_APPROVAL`, `ACTIVE`, `ARCHIVED`).
  2. `data_classification_levels`: Monotonic classification tiers (`ordinal_rank` $1 \dots 10$) mapped to `DataSensitivityLevel` with mandatory encryption, Four-Eyes approval, retention, and disposal policy flags.
  3. `data_classification_records`: Immutable, append-only ledger of asset classification proposals, upgrades, downgrades, revalidations, Four-Eyes approvals, and rejections.
  4. `data_lineage_edges`: Directed dataset-to-dataset lineage edges with BFS cycle prevention, sensitivity flow gating, canonical SHA-256 `provenance_hash`, and Four-Eyes approval/revocation tracking.
  5. `data_asset_cloud_links`: Many-to-many bridge linking `DataAsset` to Phase 18 `CloudAsset` with hosting role (`PRIMARY_STORE`, `REPLICA_STORE`, `BACKUP_ARCHIVE`, `PROCESSING_COMPUTE`, `ENCRYPTION_KEY_VAULT`).
  6. `data_asset_processing_links`: Many-to-many bridge linking `DataAsset` to Phase 16 `ProcessingActivity` (RoPA) with usage role (`PRIMARY_SOURCE`, `DERIVED_OUTPUT`, `ANALYTICS_INPUT`, `ARCHIVE_RETENTION`, `VENDOR_TRANSFER`).
  7. `data_asset_control_links`: Many-to-many bridge linking `DataAsset` to Phase 2 `OrganizationControl` with control objective (`ENCRYPTION_AT_REST`, `ENCRYPTION_IN_TRANSIT`, `ACCESS_CONTROL`, `DATA_MASKING_PSEUDONYMIZATION`, `RETENTION_DISPOSAL`, `BACKUP_INTEGRITY`, `DLP_MONITORING`).
  8. `data_asset_evidence_links`: Many-to-many bridge linking `DataAsset` to Phase 3 `EvidenceItem` with evidence purpose (`CLASSIFICATION_JUSTIFICATION`, `ENCRYPTION_ATTESTATION`, `LINEAGE_VERIFICATION`, `OWNERSHIP_STEWARDSHIP_ATTESTATION`, `RETENTION_DISPOSAL_CERTIFICATE`).

---

## 4. Canonical DataAsset Authority & Cross-Phase Boundaries
1. **Single Canonical `DataAsset` Table (`data_assets`)**:
   - No duplicate `DataGovernanceAsset` or `CatalogAsset` table was created. `DataAsset` in `backend/app/models/privacy.py` is extended in-place.
   - Phase 16 `/api/v1/privacy/data-assets` endpoints remain 100% operational and enforced against Batch 3 governance locks (blocking direct sensitivity downgrades on governed assets with `HTTP 422` and blocking mutations/deletions of `RETIRED` assets with `HTTP 409`).
2. **Phase 18 Cloud Security (`CLOUDSEC-GRC`) Boundary**:
   - `CloudAsset` remains the sole authority for infrastructure posture (`encryption_enabled`, `is_internet_facing`, `posture_status`).
   - `DataGovernanceService.evaluate_asset_cloud_alignment` evaluates alignment between `DataAsset` classification requirements and linked `CloudAsset` telemetry without overwriting human-governed `DataAsset` classifications.
3. **Phase 21 Regulatory Intelligence (`REGULATORY-GRC`) Traceability**:
   - Regulatory obligations applicable to a `DataAsset` are derived dynamically by joining `DataAssetControlLink.organization_control_id == RegulatoryObligation.organization_control_id` within the same `organization_id`.

---

## 5. Zero Role Inflation & RBAC Permission Matrix
ControlSphere's exact 6 platform roles (`ADMIN`, `MANAGER`, `GRC_ANALYST`, `SECURITY_ANALYST`, `AUDITOR`, `VIEWER`) were preserved with zero role inflation. Six granular permissions were registered in `backend/app/core/permissions.py`:

| Permission | `ADMIN` | `MANAGER` | `GRC_ANALYST` | `SECURITY_ANALYST` | `AUDITOR` | `VIEWER` |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| `DATA_GOV_READ` (`data_gov:read`) | YES | YES | YES | YES | YES | YES |
| `DATA_GOV_MANAGE` (`data_gov:manage`) | YES | YES | YES | NO | NO | NO |
| `DATA_GOV_CLASSIFY` (`data_gov:classify`) | YES | YES | YES | YES | NO | NO |
| `DATA_GOV_APPROVE` (`data_gov:approve`) | YES | YES | NO | NO | NO | NO |
| `DATA_GOV_LINEAGE_MANAGE` (`data_gov:lineage_manage`) | YES | YES | YES | YES | NO | NO |
| `DATA_GOV_OWNER_MANAGE` (`data_gov:owner_manage`) | YES | YES | YES | NO | NO | NO |

---

## 6. Classification Governance, Monotonicity & Downgrade Defense
- **Monotonic Ordinal Rank Invariant**:
  - Within any `DataClassificationScheme`, for any two levels $L_i, L_j$, if `ordinal_rank(L_i) < ordinal_rank(L_j)`, then `SENSITIVITY_RANK(L_i.mapped_sensitivity_level) <= SENSITIVITY_RANK(L_j.mapped_sensitivity_level)`. Contradictory rank mappings are rejected with `HTTP 422`.
- **Downgrade Attack Defense**:
  - Whenever a classification request lowers `SENSITIVITY_RANK` or `ordinal_rank`, `change_type` is forced to `DOWNGRADE` and `status` is set to `PENDING_APPROVAL`.
  - Crucially, `DataAsset.data_sensitivity_level` and `DataAsset.classification_level_id` remain locked at their prior higher values until a different user (`approver_id != requested_by_id`) with `DATA_GOV_APPROVE` approves the record.
- **Immutable Append-Only Ledger**:
  - `DataClassificationRecord` rows are never mutated in-place or deleted; `PUT` and `DELETE` on `/classifications/{id}` return `HTTP 405 Method Not Allowed`.

---

## 7. Directed Lineage Engine, DAG Cycle Prevention & Sensitivity Flow Gate
- **Graph Cycle Prevention (BFS)**:
  - Self-loops (`source_data_asset_id == target_data_asset_id`) are rejected via both Pydantic/service validation (`HTTP 422`) and SQL `CheckConstraint`.
  - Before persisting or versioning any lineage edge $S \to T$, `DataGovernanceService._validate_no_lineage_cycle` performs a Breadth-First Search over all `ACTIVE` and `PENDING_APPROVAL` edges in the tenant's graph starting at $T$. If $S$ is reachable from $T$, the edge is rejected with `HTTP 422`.
- **Sensitivity Flow Gate**:
  - Unmasked flows from `RESTRICTED_PII` or `SPECIAL_CATEGORY_SENSITIVE_PHI` into `PUBLIC` targets (`is_masked_or_anonymized == False`) are strictly prohibited (`HTTP 422`).
  - Flows into lower-sensitivity targets require a non-empty `transformation_summary` (`HTTP 422` if omitted) and automatically enter `PENDING_APPROVAL` requiring Four-Eyes approval (`approver_id != created_by_id`).
- **Cryptographic Provenance Digest**:
  - Every `DataLineageEdge` computes a deterministic SHA-256 `provenance_hash` over canonical JSON (`sort_keys=True`, compact separators) of its lineage attributes.

---

## 8. Lifecycle State Machine & Governed Retirement Prerequisites
- **Governed Asset Lifecycle**:
  - `DISCOVERED -> REGISTERED -> CLASSIFIED -> ACTIVE -> DEPRECATED -> RETIRED` (plus governed restoration `RETIRED -> ACTIVE / REGISTERED` with Four-Eyes SoD).
  - Assets in `DISCOVERED` state cannot skip directly to `CLASSIFIED` or `ACTIVE` (`HTTP 422`).
  - Assets in `REGISTERED` state cannot transition to `ACTIVE` until `classification_status == APPROVED` (`HTTP 422`).
- **Retirement Gates**:
  - Retiring any asset requires `disposal_method != NONE` and non-empty `retirement_notes`.
  - Retiring `CONFIDENTIAL`, `RESTRICTED_PII`, or `SPECIAL_CATEGORY_SENSITIVE_PHI` assets requires `retirement_evidence_id` referencing an active (`status not in {REJECTED, SUPERSEDED}`) same-tenant `EvidenceItem` (`HTTP 422`).
  - Finalizing retirement enforces Four-Eyes SoD (`retired_by_id != retirement_requested_by_id`, `HTTP 403`) and automatically revokes active/pending lineage edges connected to the retired asset.
  - Once `RETIRED`, all metadata mutations, classifications, ownership transfers, and new lineage/bridge links are blocked (`HTTP 409 Conflict`).

---

## 9. Adversarial Attack Vector Verification (`SEC-B3-01` through `SEC-B3-45`)
All 45 adversarial security scenarios from the hardened specification were verified via automated tests:
- **Authentication & RBAC (`SEC-B3-01` to `SEC-B3-04`)**: Unauthenticated requests return `401`; `VIEWER`/`AUDITOR` mutations return `403`; `SECURITY_ANALYST` blocked from scheme/asset creation and ownership/retirement (`403`); `GRC_ANALYST`/`SECURITY_ANALYST` blocked from approval endpoints (`403`).
- **Multi-Tenant Isolation (`SEC-B3-05` to `SEC-B3-10`)**: Cross-tenant reads, updates, lineage edges, RoPA/Control/Evidence/Cloud links, owner/steward assignments, and scheme/level references return `HTTP 404 Not Found` (zero cross-tenant enumeration leakage).
- **Mass Assignment & Input Validation (`SEC-B3-11` to `SEC-B3-15`)**: `ConfigDict(extra="forbid")` rejects injected `organization_id`, `status`, `approved_by_id`, `provenance_hash`, or unknown fields (`422`); legacy Phase 16 `PUT /api/v1/privacy/data-assets/{id}` blocks direct sensitivity downgrades (`422`).
- **Scheme & Classification Four-Eyes (`SEC-B3-16` to `SEC-B3-25`)**: Non-monotonic ranks (`422`), scheme self-approval (`403`), mutating `ACTIVE` schemes (`409`), classifying against `ARCHIVED` schemes (`422`), classification self-approval (`403`), empty rejection/justification (`422`), pending downgrade sensitivity lock, and concurrent pending classifications (`409`).
- **Lineage DAG & Sensitivity Flow (`SEC-B3-26` to `SEC-B3-31`)**: Self-loops (`422`), 2-hop/3-hop/multi-hop cycles (`422`), unmasked PII-to-Public flow (`422`), high-to-low flow without transformation summary (`422`), and lineage self-approval (`403`).
- **Ownership, Lifecycle & Retirement (`SEC-B3-32` to `SEC-B3-41`, `SEC-B3-45`)**: Inactive owner/steward rejection (`422`), ownership transfer self-approval (`403`), concurrent pending transfer (`409`), retired asset lock (`409`), premature activation (`422`), missing/rejected retirement evidence (`422`), retirement self-approval (`403`), self-restoration (`403`), and legacy Phase 16 mutation/deletion of retired assets (`409`).
- **Immutability & Idempotency (`SEC-B3-42` to `SEC-B3-44`)**: `PUT`/`DELETE` on `/classifications/{id}` and `/lineage-edges/{id}` return `405 Method Not Allowed`; duplicate codes/links and double-approvals return `409 Conflict`.

---

## 10. Test Execution, Migration Reversibility & Full Regression Audit
- **Batch 3 Domain Tests**: `10 / 10 passed` (`backend/tests/test_data_governance_domain.py`)
- **Batch 3 API, Adversarial Security & Migration Tests**: `36 / 36 passed` (`backend/tests/test_data_governance_api.py`)
- **Total Batch 3 Tests**: `46 / 46 passed` (`100%` pass rate)
- **Alembic Reversibility Verification**: Automated test `test_alembic_migration_0024_upgrade_downgrade_reversibility` verified full `0024 -> 0023 -> 0024 -> 0023 -> 0024` cycle on an isolated SQLite database.
- **Full Repository Regression Suite**: `1,084` total tests (`1,038` baseline + `46` Batch 3), `0` failures (`100%` pass rate).

---

## 11. Frontend Implementation & Production Build Verification
- **Created**:
  - `frontend/src/types/dataGovernance.ts`
  - `frontend/src/lib/dataGovernanceService.ts`
  - `frontend/src/pages/DataGovernancePage.tsx`
- **Modified**:
  - `frontend/src/App.tsx`: Registered `/data-governance` route.
  - `frontend/src/components/layout/Sidebar.tsx`: Added `Data Governance & Lineage` navigation entry (`tag: 'Batch 3'`) under `Privacy & Data Protection`.
- **Frontend Production Build**:
  - Command: `npm run build` (`tsc -b && vite build`)
  - Result: Exit code `0`, `2075 modules transformed`, `0` TypeScript or bundler errors.
