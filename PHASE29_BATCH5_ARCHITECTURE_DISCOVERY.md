# PHASE 29 — BATCH 5 ARCHITECTURE DISCOVERY REPORT
**Document ID**: `PHASE29_BATCH5_ARCHITECTURE_DISCOVERY.md`
**Repository**: `E:\PROJECT WORKSPACE 2\ControlSphere` (`https://github.com/Avalar06/ControlSphere.git`)
**Branch**: `main`
**Frozen Baseline Commit**: `812a18342ff6cec90b31264f1828a60a18bdc57b` (`feat(batch4): implement policy lifecycle and workforce attestation governance`)
**Frozen Alembic Head**: `0025 (head)` (`0025_policy_lifecycle_governance_hardening.py`)
**Recommended Batch 5 Capability**: **Operational Resilience Continuity Planning, DR Exercise Testing & Empirical RTO/RPO Assurance (`RESILIENCE-CONTINUITY-GRC`)**
**Status**: **ARCHITECTURE DISCOVERY COMPLETE — GO TO HARDENING**

---

## 1. Executive Summary

- **REPOSITORY FACT**: ControlSphere at commit `812a18342ff6cec90b31264f1828a60a18bdc57b` (Alembic revision `0025`) is a multi-tenant enterprise Governance, Risk, and Compliance (GRC) platform comprising 27 SQLAlchemy model modules (`backend/app/models/`), 29 domain service modules (`backend/app/services/`), 36 API endpoint routers (`backend/app/api/v1/api.py`), 25 sequential Alembic migrations (`0001`–`0025`), 45 React TypeScript pages (`frontend/src/pages/`), and 1,139 passing automated backend tests.
- **REPOSITORY FACT**: Batches 1 through 4 systematically hardened and expanded four foundational GRC domains that previously had shallow or incomplete operational lifecycles:
  - **Batch 1 (`a3e9b4ab6926789479399e0e56df7138a7640c40`, migration `0022`)**: Hardened Phase 6 Audits with Enterprise Audit Fieldwork, Sampling & PBC Collaboration (`AUDIT-FIELDWORK-GRC`).
  - **Batch 2 (`7b5c7954c33f6aca44b7a193ad91d1b384188456`, migration `0023`)**: Hardened Phase 5 Risks with Dynamic Key Risk Indicators & Risk Appetite Governance (`KRI-APPETITE-GRC`).
  - **Batch 3 (`9c34411f5cc4f7f5b849e457d2304ea1e9fc00bd`, migration `0024`)**: Hardened Phase 16 Privacy/Data Assets with Enterprise Data Governance, Classification & Lineage (`DATA-GOVERNANCE-GRC`).
  - **Batch 4 (`812a18342ff6cec90b31264f1828a60a18bdc57b`, migration `0025`)**: Hardened Phase 2/24 Policies with Multi-Stage Review Workflows, Version Diffing, Role-Scoped Campaigns & Structured Attestations (`POLICY-LIFECYCLE-GRC`).
- **REPOSITORY FACT**: A comprehensive audit of all 27 model modules and 45 frontend pages reveals that **Phase 13 Operational Resilience (`RESILIENCE-GRC`)** (`backend/app/models/resilience.py`, 235 lines; `backend/app/services/resilience_service.py`, 619 lines; `backend/app/api/v1/endpoints/resilience.py`, 276 lines) is currently one of the thinnest domain modules in the platform. It contains only 3 tables (`business_processes`, `business_impact_analyses`, `process_dependencies`) and stops at theoretical recovery targets (`rto_hours`, `rpo_hours`, `mtd_hours`) and a linear cost formula (`calculate_projected_outage_loss`). It has **zero** Business Continuity Plans (BCP) or Disaster Recovery (DR) runbooks, **zero** recovery exercise or tabletop/failover test execution records, **zero** empirical RTO/RPO achievement vs. target variance evaluation, **zero** evidence binding (`EvidenceItem`), **zero** closed-loop escalation to Findings (`Finding`) or CAPA (`RemediationPlan`), and **zero** contribution of BIA/resilience posture to `ExecutiveService.calculate_live_telemetry` (which claims `business_impact_analyses` in `source_tables` at line 403 of `executive_service.py` while computing `resilience_score` solely from `SecurityIncident` counts). Furthermore, several Phase 13 endpoints (`delete_business_process`, `update_draft_bia`, `get_active_bia`, `list_process_dependencies`) bypass `ResilienceService`, omit `AuditLog` entries, or fail to validate parent `BusinessProcess` tenant existence before querying child records.
- **ARCHITECTURAL DECISION**: Select **Operational Resilience Continuity Planning, DR Exercise Testing & Empirical RTO/RPO Assurance (`RESILIENCE-CONTINUITY-GRC`)** as **Batch 5**, extending Phase 13 (`resilience.py`) at Alembic revision `0026` with governed Continuity Plans (`ContinuityPlan`, `ContinuityRecoveryStep`), empirical Recovery Exercises (`ResilienceExercise`), Evidence bindings (`ResilienceEvidenceLink`), expanded cross-domain dependency lineage (`CLOUD_ASSET`, `DATA_ASSET` in addition to `VENDOR`, `CONTROL`), deterministic RTO/RPO variance and resilience readiness scoring, and closed-loop remediation/finding escalation.

---

## 2. Baseline Verification

- **REPOSITORY FACT**: Mandatory baseline verification commands were executed against `E:\PROJECT WORKSPACE 2\ControlSphere` prior to analysis:
  - `git status`: `On branch main`, `Your branch is up to date with 'origin/main'`, `nothing to commit, working tree clean`.
  - `git rev-parse HEAD`: `812a18342ff6cec90b31264f1828a60a18bdc57b`.
  - `git log -1 --oneline`: `812a183 feat(batch4): implement policy lifecycle and workforce attestation governance`.
  - `git branch --show-current`: `main`.
  - `git remote -v`: `origin https://github.com/Avalar06/ControlSphere.git (fetch / push)`.
  - `python -m alembic -c backend/alembic.ini heads`: `0025 (head)`.
- **REPOSITORY FACT**: All frozen batch commits are verified in the Git commit graph:
  - Batch 1: `a3e9b4ab6926789479399e0e56df7138a7640c40` (`feat(batch1): implement audit fieldwork governance`)
  - Batch 2: `7b5c7954c33f6aca44b7a193ad91d1b384188456` (`feat(batch2): implement kri appetite governance`)
  - Batch 3: `9c34411f5cc4f7f5b849e457d2304ea1e9fc00bd` (`feat(batch3): implement data governance and lineage`)
  - Batch 4: `812a18342ff6cec90b31264f1828a60a18bdc57b` (`feat(batch4): implement policy lifecycle and workforce attestation governance`, parent `9c34411f5cc4f7f5b849e457d2304ea1e9fc00bd`).

---

## 3. Current Platform Architecture

- **REPOSITORY FACT**: ControlSphere is structured as a monolithic, multi-tenant FastAPI + SQLAlchemy 2.x backend (`backend/app/`) paired with a React 19 + TypeScript + Vite + TailwindCSS + TanStack Query frontend (`frontend/src/`).
- **REPOSITORY FACT**: Multi-tenancy is enforced via `organization_id` foreign keys (`ForeignKey("organizations.id", ondelete="CASCADE")`) on every domain table, extracted exclusively from the authenticated user's JWT session (`current_user.organization_id` in `backend/app/api/deps.py`).
- **REPOSITORY FACT**: Authorization is enforced via a deterministic 6-role RBAC model (`RoleEnum`: `ADMIN`, `MANAGER`, `GRC_ANALYST`, `SECURITY_ANALYST`, `AUDITOR`, `VIEWER` in `backend/app/core/permissions.py`) mapped to granular `Permission` enum members via `ROLE_PERMISSIONS` and checked via `require_permission(...)` route dependencies.
- **REPOSITORY FACT**: Immutable audit logging is centralized in `AuditService.log(...)` (`backend/app/services/audit_service.py`), persisting `AuditLog` rows (`backend/app/models/audit_log.py`) within the same database session.
- **REPOSITORY FACT**: Cross-domain posture aggregation is governed by two higher-order orchestrators:
  1. `ExecutiveService.calculate_live_telemetry` (`backend/app/services/executive_service.py`), which computes a 10-domain weighted composite `overall_posture` score (`[0.0, 100.0]`), canonical SHA-256 source manifests, top risks, critical findings, and immutable `ExecutiveSnapshot` records.
  2. `ContinuousComplianceService.calculate_unified_assurance` and `evaluate_continuous_compliance` (`backend/app/services/continuous_compliance_service.py`), which compute a 6-pillar unified assurance score, detect multi-vector `ComplianceDriftRecord` entries, and trigger Phase 11 `RemediationPlan` (CAPA) records.

---

## 4. Historical Roadmap Reconciliation

- **REPOSITORY FACT**: The historical discovery artifact `PHASE_NEXT_ARCHITECTURE_DISCOVERY.md` (Section 8, lines 152–173) proposed 5 expansion candidates after Phase 23 (`0020_continuous_compliance_and_assurance.py`). Reconciling those 5 historical candidates against the live repository at `0025 (head)` establishes:

| Historical Candidate (`PHASE_NEXT_ARCHITECTURE_DISCOVERY.md`) | Historical Scope Summary | Live Repository Status at `812a183` (`0025`) | Reconciliation Verdict |
| :--- | :--- | :--- | :--- |
| **Candidate 1: `POLICY-ATTESTATION-GRC`** | Policy Lifecycle, Versioning, Exception Waivers & Workforce Attestation Campaigns | Implemented in Phase 24 (`0021_policy_attestation_and_lifecycle.py`) and comprehensively hardened in **Batch 4** (`812a18342ff6cec90b31264f1828a60a18bdc57b`, migration `0025_policy_lifecycle_governance_hardening.py`). | **COMPLETE & FROZEN (Batch 4)** |
| **Candidate 2: `AUDIT-OPS-GRC`** | Internal Audit Workpapers, Sampling Methodology & PBC Request Collaboration | Implemented and frozen in **Batch 1** (`a3e9b4ab6926789479399e0e56df7138a7640c40`, migration `0022_audit_fieldwork_and_sampling.py`). | **COMPLETE & FROZEN (Batch 1)** |
| **Candidate 3: `KRI-METRICS-GRC`** | Dynamic Key Risk Indicators (KRIs), Threshold Telemetry & Risk Appetite Monitoring | Implemented and frozen in **Batch 2** (`7b5c7954c33f6aca44b7a193ad91d1b384188456`, migration `0023_kri_and_risk_appetite_governance.py`). | **COMPLETE & FROZEN (Batch 2)** |
| **Candidate 4: `DATA-ASSET-GRC`** | Enterprise Data Asset Inventory, Classification & Lineage Governance | Implemented and frozen in **Batch 3** (`9c34411f5cc4f7f5b849e457d2304ea1e9fc00bd`, migration `0024_data_governance_and_lineage.py`). | **COMPLETE & FROZEN (Batch 3)** |
| **Candidate 5: `AI-ANALYST-GRC`** | Governed AI GRC Copilot & Natural Language Reasoning Oversight | Route `/ai-analyst` in `frontend/src/App.tsx` (lines 195–209) still renders `PlaceholderModulePage`. No backend models, services, or endpoints exist for `/ai-analyst` (distinct from Phase 15 `ai_governance.py` which governs AI systems/models). | **UNIMPLEMENTED CANDIDATE** (Evaluated in Section 7 alongside deeper core GRC operational gaps) |

---

## 5. Existing Authority Inventory

- **REPOSITORY FACT**: The table below inventories every authoritative domain module in `backend/app/models/`, its service, API prefix, deterministic metric engine, state machine, latest migration, test suite, and frontend pages:

| # | Domain / Phase / Batch | Model File (`backend/app/models/`) | Service File (`backend/app/services/`) | API Prefix (`api.py`) | Deterministic Metric / Engine | Key State Machines | Migrations | Frontend Surface (`frontend/src/pages/`) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | Phase 1: Core Auth, Tenants, Users & Audit Logs | `organization.py`, `user.py`, `audit_log.py` | `user_service.py`, `organization_service.py`, `audit_service.py` | `/auth`, `/users`, `/organizations`, `/audit-logs` | RBAC permission matrix (`ROLE_PERMISSIONS`) | `User.is_active` | `0001` | `LoginPage.tsx`, `UsersPage.tsx`, `AuditLogsPage.tsx` |
| 2 | Phase 2: Frameworks & Controls | `framework.py`, `control.py` | `framework_service.py`, `control_service.py` | `/frameworks`, `/controls` | Control implementation ratio | `ImplementationStatusEnum` | `0002` | `FrameworksPage.tsx`, `ControlsPage.tsx` |
| 3 | Phase 2 / 24 / **Batch 4**: Policy Lifecycle & Attestation | `policy.py` | `policy_service.py` | `/policies` | Campaign attestation completion %, overdue rate, version diff engine | `PolicyStatusEnum`, `PolicyVersionStatusEnum`, `PolicyReviewStatusEnum`, `CampaignStatusEnum`, `AttestationRecordStatusEnum` | `0002`, `0021`, `0025` | `PoliciesPage.tsx`, `PolicyDetailPage.tsx` |
| 4 | Phase 3: Evidence Management | `evidence.py` | `evidence_service.py` | `/evidence` | SHA-256 file integrity, freshness window | `EvidenceStatusEnum`, `ReviewDecisionEnum` | `0003` | `EvidencePage.tsx`, `EvidenceRequirementsPage.tsx` |
| 5 | Phase 4: Assessments & Findings | `assessment.py`, `finding.py` | `assessment_service.py`, `finding_service.py` | `/assessments`, `/findings` | Assessment pass rate, finding SLA tracking | `AssessmentStatusEnum`, `FindingStatusEnum` | `0004` | `AssessmentsPage.tsx`, `AssessmentDetailPage.tsx`, `FindingsPage.tsx`, `FindingDetailPage.tsx` |
| 6 | Phase 5: Risk Register & Exceptions | `risk.py`, `exception.py` | `risk_service.py`, `exception_service.py` | `/risks`, `/exceptions` | Inherent $L \times I$ & residual risk score, exception expiration | `RiskStatusEnum`, `ExceptionStatusEnum` | `0005` | `RisksPage.tsx`, `RiskDetailPage.tsx`, `ExceptionsPage.tsx`, `ExceptionDetailPage.tsx` |
| 7 | Phase 6 / **Batch 1**: Audits & Fieldwork Governance | `audit_engagement.py` | `audit_engagement_service.py`, `audit_fieldwork_service.py` | `/audits` | Deterministic SHA-256 sampling seed, sample deviation rate, readiness index | `AuditStatusEnum`, `PBCStatusEnum`, `WorkpaperStatusEnum` | `0006`, `0022` | `AuditsPage.tsx`, `AuditDetailPage.tsx` |
| 8 | Phase 7: Continuous Control Monitoring (CCM) | `monitoring.py` | `monitoring_service.py` | `/monitoring` | Control health score `[0, 100]`, drift alert generation | `ControlHealthStatusEnum`, `DriftAlertStatusEnum` | `0007` | `ContinuousMonitoringPage.tsx` |
| 9 | Phase 8: Multi-Framework Harmonization | `harmonization.py` | `harmonization_service.py` | `/harmonization` | Crosswalk inheritance & framework compliance snapshot % | `RationalizationStatusEnum` | `0008` | `HarmonizationPage.tsx`, `FrameworkPosturePage.tsx`, `CommonControlDetailPage.tsx` |
| 10 | Phase 9: Third-Party & Vendor Risk (TPRM) | `tprm.py` | `tprm_service.py` | `/vendors` | Engagement inherent risk, vendor tiering, weighted questionnaire residual score | `VendorStatusEnum`, `EngagementStatusEnum`, `VendorAssessmentStatusEnum` | `0009` | `VendorsPage.tsx`, `VendorDetailPage.tsx`, `VendorAssessmentDetailPage.tsx` |
| 11 | Phase 10: Security Incident & Breach Governance | `incident.py` | `incident_service.py` | `/incidents` | Statutory disclosure deadline clock (72h/96h/36h) | `IncidentStatusEnum`, `DisclosureStatusEnum` | `0010` | `IncidentsPage.tsx`, `IncidentDetailPage.tsx` |
| 12 | Phase 11: Governed Remediation (CAPA / ROC-V) | `remediation.py` | `remediation_service.py` | `/remediations` | Remediation Effectiveness Index (`rei_score`), `ttr_hours`, `SlaStatusEnum` | `RemediationStatusEnum`, `TaskStatusEnum`, `EvidenceVerificationStatusEnum` | `0011` | `RemediationsPage.tsx`, `RemediationDetailPage.tsx` |
| 13 | Phase 12: Cyber Risk Quantification (FAIR / ROSI) | `quant_risk.py` | `quant_risk_service.py` | `/quant-risk` | Deterministic PERT/Monte Carlo ALE, VaR95, PML99, ROSI % | `ScenarioStatusEnum`, `AppetiteStatusEnum` | `0012` | `QuantRiskPage.tsx`, `QuantScenarioDetailPage.tsx` |
| 14 | **Phase 13: Operational Resilience & BIA** | `resilience.py` | `resilience_service.py` | `/resilience` | **Only linear `calculate_projected_outage_loss` (`fixed + hourly * H`)** | **Only `BiaStatusEnum` (`DRAFT`, `ACTIVE`, `SUPERSEDED`, `ARCHIVED`)** | `0013` | `ResiliencePage.tsx`, `BusinessProcessDetailPage.tsx` |
| 15 | Phase 14: Threat Exposure & Vulnerability (CVE) | `exposure.py` | `exposure_service.py` | `/exposures` | Composite `exposure_index` (CVSS + EPSS + KEV + criticality) | `ExposureStatusEnum`, `ExceptionApprovalStatusEnum` | `0014` | `ExposurePage.tsx`, `ExposureDetailPage.tsx` |
| 16 | Phase 15: AI Governance (AI-GRC) | `ai_governance.py` | `ai_governance_service.py` | `/ai-governance` | `algorithmic_risk_index`, `eu_compliance_score` | `AILifecycleStateEnum`, `AIApprovalStatusEnum` | `0015` | `AIGovernancePage.tsx`, `AISystemDetailPage.tsx` |
| 17 | Phase 16: Privacy Governance (PRIVACY-GRC) | `privacy.py` | `privacy_service.py` | `/privacy` | RoPA & DPIA risk scoring, cross-border transfer risk | `ProcessingLifecycleState`, `PrivacyApprovalStatus` | `0016` | `PrivacyGovernancePage.tsx`, `PrivacyProcessingDetailPage.tsx`, `PrivacyAssetDetailPage.tsx` |
| 18 | Phase 17: Software Supply Chain & SBOM | `supply_chain.py` | `supply_chain_service.py` | `/supply-chain` | SBOM component vulnerability roll-up, license compliance | `ProductLifecycleStateEnum`, `SBOMStatusEnum`, `ExemptionApprovalStatusEnum` | `0017` | `SupplyChainGovernancePage.tsx`, `SoftwareProductDetailPage.tsx`, `SBOMDetailPage.tsx` |
| 19 | Phase 18: Cloud Security Posture (CSPM) | `cloudsec.py` | `cloudsec_service.py` | `/cloud-security` | Benchmark rule evaluation, IAM blast radius, asset posture score | `CloudPostureStatusEnum`, `DriftStatusEnum` | `0018` | `CloudSecurityPage.tsx`, `CloudAssetDetailPage.tsx` |
| 20 | Phase 19: Identity Governance (IGA) | `identity_governance.py` | `identity_governance_service.py` | `/identity-governance` | Zero Trust score, SoD violation detection, access certification | `CampaignStatusEnum`, `JITApprovalStatusEnum`, `SoDViolationStatusEnum` | `0019` | `IdentityGovernancePage.tsx`, `IdentityDetailPage.tsx`, `CertificationCampaignDetailPage.tsx` |
| 21 | Phase 20: Executive & Board Telemetry | `executive.py` | `executive_service.py` | `/executive` | 10-domain weighted posture, canonical SHA-256 manifest, dossier/briefing | `DossierStatusEnum`, `BriefingStatusEnum` | `0020` (part 1 / `0019b`) | `ExecutiveDashboardPage.tsx`, `RegulatoryDossiersPage.tsx`, `ExecutiveBriefingsPage.tsx`, `ExecutiveSnapshotsPage.tsx` |
| 22 | Phase 21: Regulatory Intelligence | `regulatory.py` | `regulatory_service.py` | `/regulatory` | Mandate compliance ratio, SHA-256 change deduplication | `RegulatoryMandateStatusEnum`, `RegulatoryChangeStatusEnum`, `RegulatoryImpactStatusEnum` | `0020` / `0021` | `RegulatoryIntelligencePage.tsx` |
| 23 | Phase 22: Automated Evidence Integrations | `integration.py` | `integration_service.py` | `/integrations` | SHA-256 payload hashing, automated evidence collection runs | `IntegrationConnectionStatusEnum`, `CollectionRunStatusEnum` | `0020` | `IntegrationCenterPage.tsx`, `EvidenceCollectionJobsPage.tsx` |
| 24 | Phase 23: Continuous Compliance & Assurance | `continuous_compliance.py` | `continuous_compliance_service.py` | `/continuous-compliance` | 6-pillar composite assurance score, 5-vector drift detection, auto-CAPA | `ComplianceDriftStatusEnum` | `0020_continuous_compliance_and_assurance.py` | `ContinuousComplianceDashboardPage.tsx` |
| 25 | **Batch 2**: KRI & Risk Appetite Governance | `kri.py` | `kri_service.py` | `/kri` | Directional 3-tier threshold evaluation, breach lifecycle, appetite sync | `AppetiteStatementStatusEnum`, `KriStatusEnum`, `BreachStatusEnum` | `0023` | `KriPage.tsx`, `RisksPage.tsx` |
| 26 | **Batch 3**: Enterprise Data Governance & Lineage | `data_governance.py` | `data_governance_service.py` | `/data-governance` | BFS cycle detection, upward sensitivity propagation, retention/disposal | `DataAssetLifecycleEnum`, `DataClassificationApprovalStatusEnum`, `DataOwnerTransferStatusEnum` | `0024` | `DataGovernancePage.tsx`, `PrivacyAssetDetailPage.tsx` |

---

## 6. Remaining Capability Gaps

- **REPOSITORY FACT**: Based on code inspection across all 27 model files, 29 service files, and 45 frontend pages, four concrete capability gaps remain in ControlSphere:

### Gap 1: Phase 13 Operational Resilience Stops at BIA Targets — Lacks Continuity Plans (BCP/DR), Recovery Exercises, Empirical RTO/RPO Validation & Closed-Loop Remediation
- **REPOSITORY FACT**: `backend/app/models/resilience.py` (235 lines) defines only `BusinessProcess`, `BusinessImpactAnalysis`, and `ProcessDependency`.
- **REPOSITORY FACT**: While a `BusinessImpactAnalysis` sets target `rto_hours`, `rpo_hours`, and `mtd_hours`, there is **no model, service, or API** for:
  1. **Business Continuity & Disaster Recovery Plans (`ContinuityPlan` & `ContinuityRecoveryStep`)**: Organizations cannot author, version, review, or approve actionable BCP/DR recovery plans or ordered recovery runbook steps for a `BusinessProcess`.
  2. **Resilience Recovery Exercises & Failover Testing (`ResilienceExercise`)**: Organizations cannot schedule, execute, or record tabletop exercises, functional failover drills, or full disaster recovery simulations against a `BusinessProcess` and its active `BusinessImpactAnalysis` / `ContinuityPlan`.
  3. **Empirical RTO / RPO / MTD Validation**: There is no server-authoritative calculation comparing actual `observed_rto_hours` and `observed_rpo_hours` measured during an exercise against the active BIA baseline's `rto_hours`, `rpo_hours`, and `mtd_hours`, nor deterministic classification of exercise outcomes (`PASSED`, `PASSED_WITH_OBSERVATIONS`, `FAILED_RTO_BREACH`, `FAILED_RPO_BREACH`, `FAILED_MTD_BREACH`).
  4. **Four-Eyes Exercise Sign-Off & Evidence Binding**: Exercises cannot bind `EvidenceItem` artifacts (e.g., failover logs, tabletop sign-off reports) or enforce Four-Eyes separation between the exercise executor (`executed_by_id`) and independent reviewer/approver (`reviewed_by_id`).
  5. **Closed-Loop Deficiency Escalation**: Failed exercises or RTO/RPO breaches cannot spawn or link authoritative Phase 4 `Finding` records, Phase 11 `RemediationPlan` (CAPA) records, or Phase 5 `Risk` records.
  6. **Infrastructure & Data Dependency Lineage**: `DependencyTypeEnum` (`backend/app/models/resilience.py`, lines 38–40) only supports `VENDOR` and `CONTROL`. It cannot map critical dependencies on `CLOUD_ASSET` (`CloudAsset` from Phase 18) or `DATA_ASSET` (`DataAsset` from Phase 16/Batch 3), nor compute Single-Point-of-Failure (SPOF) or degraded dependency impact on process resilience readiness.
  7. **Executive & Continuous Assurance Disconnect**: `ExecutiveService.calculate_live_telemetry` (`backend/app/services/executive_service.py`, lines 386–408) declares `"source_tables": ["security_incidents", "business_impact_analyses"]` under `incidents_resilience`, yet **never queries** `BusinessImpactAnalysis` or `BusinessProcess`!
  8. **Existing Phase 13 Route Hygiene Defects**: In `backend/app/api/v1/endpoints/resilience.py`, `delete_business_process` (lines 88–100) and `update_draft_bia` (lines 141–167) mutate the database directly inside the FastAPI route without calling `ResilienceService` or recording `AuditLog` entries, and `get_active_bia` (lines 196–213) and `list_process_dependencies` (lines 230–246) do not verify that `process_id` belongs to `current_user.organization_id` (returning `null`/`[]` instead of `404 Not Found` on cross-tenant `process_id` probes).

### Gap 2: Third-Party Extended Lifecycle — Fourth-Party Subprocessors, SLA Tracking & Governed Offboarding (`TPRM-EXTENDED-GRC`)
- **REPOSITORY FACT**: `backend/app/models/tprm.py` (411 lines) implements `Vendor`, `VendorEngagement`, `VendorAssessment`, `VendorAssessmentItem`, and `VendorEvidenceLink`. While `VendorStatusEnum` includes `OFFBOARDED` and `TERMINATED`, there is no governed offboarding workflow checklist (access revocation verification, data destruction attestation, Four-Eyes offboarding approval), no fourth-party (`VendorSubprocessor`) registry, and no contractual SLA breach tracking.

### Gap 3: Governed AI GRC Analyst Workspace (`AI-ANALYST-GRC`)
- **REPOSITORY FACT**: Route `/ai-analyst` in `frontend/src/App.tsx` (lines 195–209) renders `PlaceholderModulePage` ("AI GRC Analyst — Phase 9"). No backend tables or endpoints exist for assistive AI reasoning sessions. However, `backend/app/core/config.py` has no external LLM provider configuration, meaning an implementation would either be a deterministic rule-based template advisor or require external network/API dependencies.

### Gap 4: Tenant Platform Settings (`TENANT-SETTINGS-GRC`)
- **REPOSITORY FACT**: Route `/settings` in `frontend/src/App.tsx` (lines 211–226) renders `PlaceholderModulePage` ("Platform Settings — Phase 1"). `Organization` (`backend/app/models/organization.py`) stores only `id`, `name`, `slug`, `is_active`, `created_at`, `updated_at`.

---

## 7. Candidate Batch Analysis

- **ARCHITECTURAL DECISION**: We compare four concrete Batch 5 candidates factually across repository gap, enterprise GRC importance, architectural fit, cross-module integration value, security/governance complexity, migration complexity, testability, and duplication risk:

| Evaluation Dimension | Candidate A: Operational Resilience Continuity Planning, DR Exercise Testing & Empirical RTO/RPO Assurance (`RESILIENCE-CONTINUITY-GRC`) | Candidate B: Third-Party Subprocessors, SLA Governance & Vendor Offboarding (`TPRM-EXTENDED-GRC`) | Candidate C: Governed AI GRC Analyst Copilot (`AI-ANALYST-GRC`) | Candidate D: Tenant Platform Security & Governance Settings (`TENANT-SETTINGS-GRC`) |
| :--- | :--- | :--- | :--- | :--- |
| **Current Repository Gap** | Phase 13 (`resilience.py`) has only 3 tables (`BusinessProcess`, `BusinessImpactAnalysis`, `ProcessDependency`), zero BCP/DR plans, zero recovery exercises, zero empirical RTO/RPO testing, unlogged route mutations, and is omitted from `ExecutiveService` calculations despite being listed in `source_tables`. | Phase 9 (`tprm.py`) has 5 tables and full assessment/tiering lifecycles, but lacks fourth-party subprocessors, SLA breach tracking, and structured offboarding checklists. | `/ai-analyst` in `App.tsx` is a `PlaceholderModulePage` with no backend implementation. | `/settings` in `App.tsx` is a `PlaceholderModulePage`; `Organization` has only 6 columns. |
| **Enterprise GRC Importance** | Essential for ISO 22301, DORA (EU Digital Operational Resilience Act Articles 24–27), NIS2, SOC 2 Availability (A1.2/A1.3), and NIST CSF 2.0 (`RC.RP`, `ID.BE`). Regulators require empirical proof that RTO/RPO targets in BIAs are actually achievable via tested BCP/DR plans. | High importance for supply chain concentration risk and GDPR Article 28 subprocessor tracking, plus SOC 2 vendor termination evidence. | Assistive productivity feature; not a statutory or audit-mandated system of record (and Phase 15 `AI-GRC` already governs AI systems/models). | Administrative hygiene; useful for tenant preferences but not a core GRC assurance domain. |
| **Architectural Fit with Existing Modules** | Directly follows the Batch 1–4 pattern of transforming a thin existing module (Phase 13) into a full-lifecycle, Four-Eyes governed, deterministic assurance engine. | Fits cleanly into `tprm.py` / `tprm_service.py`, though Phase 9 is already relatively mature (5 tables, 411 lines in model, 3 frontend pages). | Requires either mocked/rule-based heuristics (which can feel synthetic) or external LLM API calls (which violate deterministic offline testability). | Simple CRUD over a tenant configuration table; lacks multi-stage state machines or deterministic posture math. |
| **Cross-Module Integration Value** | Connects Phase 13 `BusinessProcess` & `BusinessImpactAnalysis` with Phase 2 `OrganizationControl`, Phase 9 `Vendor`, Phase 18 `CloudAsset`, Phase 16/Batch 3 `DataAsset`, Phase 3 `EvidenceItem`, Phase 4 `Finding`, Phase 11 `RemediationPlan` (CAPA), Phase 5 `Risk`, Phase 20 `ExecutiveService`, and Phase 23 `ContinuousComplianceService`. | Connects Phase 9 `Vendor` with Phase 16 `ProcessingActivity`, Phase 11 `RemediationPlan`, and Phase 3 `EvidenceItem`. | Read-only consumer of controls, evidence, and findings; cannot be an authoritative source of posture scores. | Affects session/password/storage metadata; minimal integration with GRC domain engines. |
| **Security & Governance Complexity** | High and well-defined: Four-Eyes approval on Continuity Plans (`created_by_id != approved_by_id`), Four-Eyes sign-off on Resilience Exercises (`executed_by_id != reviewed_by_id`), immutable approved plans/completed exercises, BOLA checks across 6 linked domains, RBAC separation (`RESILIENCE_EXECUTE` vs `RESILIENCE_APPROVE`). | Moderate: Four-Eyes on vendor offboarding sign-off and subprocessor risk acceptance. | Prompt-injection/output-sanitization concerns if external LLM used; RBAC data-leakage filtering across all queried tables. | Privilege escalation prevention (`ADMIN`-only mutations). |
| **Migration Complexity** | Clean additive Alembic revision `0026`: adds new resilience tables (`continuity_plans`, `continuity_recovery_steps`, `resilience_exercises`, `resilience_evidence_links`) and extends `process_dependencies` (`CLOUD_ASSET`, `DATA_ASSET`, `criticality_impact`, `is_single_point_of_failure`). | Clean additive Alembic revision `0026`: adds `vendor_subprocessors`, `vendor_sla_obligations`, `vendor_offboarding_records`. | Additive tables for copilot sessions/recommendations. | Single table `organization_settings` or columns on `organizations`. |
| **Testability** | 100% deterministic math (RTO/RPO variance, breach flags, process resilience readiness score, SPOF dependency degradation) and strict state machines; ideal for 50+ adversarial pytest tests. | High deterministic testability for SLA breach and offboarding state machines. | Lower determinism if natural language generation is involved. | Basic CRUD and RBAC tests. |
| **Risk of Duplicating Existing Modules** | Zero duplication when scoped to **continuity planning and empirical recovery exercise testing** (explicitly delegating incidents to Phase 10 `SecurityIncident`, financial Monte Carlo to Phase 12 `QuantitativeRiskScenario`, and CAPA execution to Phase 11 `RemediationPlan`). | Low, provided fourth-party tracking does not duplicate Phase 17 `SoftwareComponent` SBOM trees. | Risk of overlapping with Phase 15 `AI-GRC` terminology if not carefully separated. | Zero duplication. |

---

## 8. Candidate Dependency Analysis

- **REPOSITORY FACT**: Analyzing upstream and downstream dependencies across the candidates:
  - **Candidate A (`RESILIENCE-CONTINUITY-GRC`)** depends on:
    - Phase 13 `BusinessProcess`, `BusinessImpactAnalysis`, `ProcessDependency` (already implemented in `0013`).
    - Phase 2 `OrganizationControl`, Phase 9 `Vendor`, Phase 18 `CloudAsset`, and Phase 16/Batch 3 `DataAsset` (all frozen and complete as of Batch 3 `0024`), enabling `ProcessDependency` to link infrastructure (`CLOUD_ASSET`) and data (`DATA_ASSET`) alongside `VENDOR` and `CONTROL`.
    - Phase 3 `EvidenceItem` (frozen in `0003`), enabling cryptographic evidence attachment to Continuity Plans and Recovery Exercises.
    - Phase 4 `Finding`, Phase 5 `Risk`, and Phase 11 `RemediationPlan` (frozen in `0004`, `0005`, `0011`), enabling failed recovery exercises or RTO/RPO breaches to escalate into governed findings and CAPA plans.
    - Phase 20 `ExecutiveService` and Phase 23 `ContinuousComplianceService`, both of which already have hooks expecting operational resilience telemetry.
  - Because Batch 3 (`DataAsset` governance) and Batch 4 (`Policy` governance) are now frozen, **all upstream dependencies required for full-spectrum Operational Resilience Continuity & Exercise Governance are in place**.

---

## 9. Recommended Batch 5 Capability

- **ARCHITECTURAL DECISION**: **Recommend Candidate A — Operational Resilience Continuity Planning, DR Exercise Testing & Empirical RTO/RPO Assurance (`RESILIENCE-CONTINUITY-GRC`)** for Batch 5.
- **Why It Is the Strongest Next Batch**:
  1. **Closes the Largest Core Domain Depth Gap**: Phase 13 (`resilience.py`) currently has only 3 tables and 235 lines of model code, with no BCP/DR continuity plans and no recovery exercise testing. Every major resilience standard (DORA, ISO 22301, NIS2, SOC 2 Availability) mandates that BIA recovery objectives (`RTO`, `RPO`, `MTD`) be backed by approved Continuity Plans and empirically validated through periodic recovery exercises.
  2. **Fixes Existing Repository Hygiene & Telemetry Gaps in Phase 13**: Hardens the existing Phase 13 endpoints that currently mutate state directly in the router without `AuditLog` entries (`delete_business_process`, `update_draft_bia`) or fail to verify tenant ownership of `process_id` (`get_active_bia`, `list_process_dependencies`), and connects real BIA + Continuity + Exercise readiness telemetry into `ExecutiveService.calculate_live_telemetry` (which already lists `"business_impact_analyses"` in `source_tables` at line 403 of `executive_service.py`).
  3. **Leverages Batch 3 (`DataAsset`) & Phase 18 (`CloudAsset`)**: Expands `ProcessDependency` so business processes can map dependencies not only to `VENDOR` and `CONTROL`, but also to `CLOUD_ASSET` and `DATA_ASSET`, with Single-Point-of-Failure (`is_single_point_of_failure`) and dependency health degradation analysis.
  4. **100% Deterministic, Self-Contained & Adversarially Testable**: Requires zero external services or LLM APIs, features strict multi-stage state machines, dual Four-Eyes Separation of Duties gates, deterministic RTO/RPO variance and readiness formulas, and closed-loop CAPA/Finding integration.
- **Why the Other Candidates Should Wait**:
  - **Candidate B (`TPRM-EXTENDED-GRC`)**: Phase 9 TPRM already has 5 tables, a full assessment questionnaire engine, tiering overrides, evidence verification, and 3 dedicated frontend pages. Extending it is valuable for Batch 6+, whereas Phase 13 lacks the entire second half of operational resilience (BCP/DR plans and recovery testing).
  - **Candidate C (`AI-ANALYST-GRC`)**: Assistive copilot features are non-authoritative by definition and should wait until all authoritative GRC systems of record are complete.
  - **Candidate D (`TENANT-SETTINGS-GRC`)**: Administrative configuration CRUD lacks the multi-stage assurance workflows, Four-Eyes governance, and cross-domain posture integration expected of a core GRC batch.
- **Exact Scope Included in Batch 5**:
  1. **Governed Continuity & Disaster Recovery Plans (`ContinuityPlan` & `ContinuityRecoveryStep`)**: Versioned per `BusinessProcess`, with lifecycle `DRAFT -> UNDER_REVIEW -> APPROVED -> SUPERSEDED -> ARCHIVED`, mandatory Four-Eyes approval (`created_by_id != approved_by_id`), immutable approved versions, and ordered recovery runbook steps (`step_order`, `title`, `description`, `responsible_role`, `estimated_duration_minutes`, `verification_criteria`).
  2. **Empirical Resilience Recovery Exercises & Failover Testing (`ResilienceExercise`)**: Scheduled and executed against a `BusinessProcess`, its active `BusinessImpactAnalysis`, and optionally an `APPROVED` `ContinuityPlan`. Supports exercise types (`TABLETOP`, `FUNCTIONAL_FAILOVER`, `FULL_DR_SIMULATION`, `CHAOS_ENGINEERING`), lifecycle (`PLANNED -> IN_PROGRESS -> COMPLETED_PENDING_REVIEW -> REVIEWED_CLOSED -> CANCELLED`), server-authoritative empirical RTO/RPO evaluation (`observed_rto_hours` vs `target_rto_hours`, `observed_rpo_hours` vs `target_rpo_hours`, `rto_variance_hours`, `rpo_variance_hours`, `is_rto_breached`, `is_rpo_breached`, `is_mtd_breached`, deterministic `exercise_outcome`), and mandatory Four-Eyes review sign-off (`executed_by_id != reviewed_by_id`).
  3. **Expanded Cross-Domain Process Dependencies & SPOF Analysis (`ProcessDependency` Hardening)**: Extends `DependencyTypeEnum` with `CLOUD_ASSET` (`CloudAsset`) and `DATA_ASSET` (`DataAsset`) alongside `VENDOR` and `CONTROL`, adds `is_single_point_of_failure` (`bool`) and `criticality_impact` (`CriticalityTierEnum`), validates cross-tenant BOLA on all 4 target tables, and evaluates live dependency health (e.g., non-compliant `CloudAsset`, high/critical risk `Vendor`, non-implemented `OrganizationControl`, retired/unclassified `DataAsset`).
  4. **Cryptographic Evidence Binding (`ResilienceEvidenceLink`)**: Links Phase 3 `EvidenceItem` records to `ContinuityPlan` or `ResilienceExercise` records with tenant isolation and duplicate prevention.
  5. **Closed-Loop Deficiency Escalation**: Allows failed or breached exercises (`is_rto_breached == True`, `is_rpo_breached == True`, or `exercise_outcome` in failure states) to link or spawn authoritative Phase 4 `Finding` and Phase 11 `RemediationPlan` (CAPA) records (`remediation_plan_id`, `finding_id`, `risk_id`).
  6. **Deterministic Process & Tenant Resilience Readiness Scoring**: Server-authoritative calculation of per-process and tenant-wide Resilience Readiness Score `[0.0, 100.0]` combining BIA coverage (25%), Approved Continuity Plan coverage (25%), Empirical Exercise validation & RTO/RPO achievement (30%), and Dependency/SPOF health (20%), integrated into `ExecutiveService` and `ContinuousComplianceService`.
  7. **Phase 13 Endpoint & Audit Hygiene Hardening**: Routes `delete_business_process`, `update_draft_bia`, `get_active_bia`, and `list_process_dependencies` through `ResilienceService` with strict parent-process tenant checks (`404 Not Found`) and complete `AuditLog` coverage.
- **Exact Scope Excluded from Batch 5**:
  - Live automated cloud infrastructure chaos injection or network packet disruption agents (ControlSphere is the governance, assurance, and empirical telemetry system of record, not an infrastructure chaos daemon).
  - Duplicating Phase 10 `SecurityIncident` crisis response timelines or statutory breach disclosure clocks.
  - Duplicating Phase 12 `QuantitativeRiskScenario` Monte Carlo simulations (Phase 13 retains deterministic outage loss and empirical RTO/RPO variance math).

---

## 10. Authority Matrix

- **ARCHITECTURAL DECISION**: To preserve single-source-of-truth invariants across ControlSphere, Batch 5 enforces the following Authority Matrix:

| Domain Concept | Authoritative System of Record | Batch 5 Role (`RESILIENCE-CONTINUITY-GRC`) | Forbidden Duplication |
| :--- | :--- | :--- | :--- |
| Business Process Catalog & BIA Baselines (`RTO`, `RPO`, `MTD`, Outage Costs) | Phase 13 `BusinessProcess`, `BusinessImpactAnalysis` (`backend/app/models/resilience.py`) | **Primary Authority** (retained and hardened) | Must not create parallel process or BIA tables. |
| Business Continuity Plans (BCP / DR Runbooks) & Ordered Recovery Steps | **Batch 5** `ContinuityPlan`, `ContinuityRecoveryStep` (`backend/app/models/resilience.py`) | **Primary Authority** | Must not store BCP plans as generic `Policy` records in `policy.py`. |
| Empirical Recovery Exercises, Failover Tests & RTO/RPO Achievement | **Batch 5** `ResilienceExercise` (`backend/app/models/resilience.py`) | **Primary Authority** | Must not store DR exercises as Phase 4 control `Assessment` or Phase 6 `AuditProcedure` rows. |
| Cross-Module Process Dependencies (`VENDOR`, `CONTROL`, `CLOUD_ASSET`, `DATA_ASSET`) | Phase 13 / **Batch 5** `ProcessDependency` (`backend/app/models/resilience.py`) | **Primary Authority** for process-to-asset dependency mapping & SPOF flags | Must not duplicate `Vendor`, `OrganizationControl`, `CloudAsset`, or `DataAsset` attributes; references them by ID + tenant check. |
| Evidence Artifacts & SHA-256 File Integrity | Phase 3 `EvidenceItem` (`backend/app/models/evidence.py`) | **Consumer / Linker** via `ResilienceEvidenceLink` | Must not create a separate file upload or blob storage table. |
| Deficiencies / Findings | Phase 4 `Finding` (`backend/app/models/finding.py`) | **Consumer / Trigger** (`ResilienceExercise.finding_id` FK to `findings.id`) | Must not create a parallel resilience findings table. |
| Corrective Action Plans (CAPA) | Phase 11 `RemediationPlan` (`backend/app/models/remediation.py`) | **Consumer / Trigger** (`ResilienceExercise.remediation_plan_id` FK to `remediation_plans.id`) | Must not create a parallel CAPA task tracker for failed exercises. |
| Enterprise Risk Register | Phase 5 `Risk` (`backend/app/models/risk.py`) | **Consumer / Linker** (`ResilienceExercise.risk_id` FK to `risks.id`) | Must not create a parallel risk register. |
| Real-World Security Incidents | Phase 10 `SecurityIncident` (`backend/app/models/incident.py`) | **Distinct Peer Domain** (Incidents = unplanned real-world breaches; Resilience Exercises = governed continuity testing) | Must not duplicate incident timeline or regulatory breach disclosure tables. |

---

## 11. Data Model Analysis

- **REPOSITORY FACT**: Currently, `backend/app/models/resilience.py` defines 3 enums (`BiaStatusEnum`, `CriticalityTierEnum`, `DependencyTypeEnum`) and 3 models (`BusinessProcess`, `BusinessImpactAnalysis`, `ProcessDependency`).
- **ARCHITECTURAL DECISION**: Batch 5 extends `backend/app/models/resilience.py` (and Alembic migration `0026`) with the following enums, columns, tables, constraints, and indexes:

### 11.1 New & Extended Enums in `backend/app/models/resilience.py`
1. **Extend `DependencyTypeEnum`**:
   - Existing: `VENDOR = "VENDOR"`, `CONTROL = "CONTROL"`
   - Add: `CLOUD_ASSET = "CLOUD_ASSET"`, `DATA_ASSET = "DATA_ASSET"`
2. **`ContinuityPlanTypeEnum(str, enum.Enum)`**:
   - `BUSINESS_CONTINUITY_PLAN = "BUSINESS_CONTINUITY_PLAN"`
   - `DISASTER_RECOVERY_RUNBOOK = "DISASTER_RECOVERY_RUNBOOK"`
   - `CRISIS_COMMUNICATION_PLAN = "CRISIS_COMMUNICATION_PLAN"`
   - `VENDOR_CONTINGENCY_PLAN = "VENDOR_CONTINGENCY_PLAN"`
3. **`ContinuityPlanStatusEnum(str, enum.Enum)`**:
   - `DRAFT = "DRAFT"`
   - `UNDER_REVIEW = "UNDER_REVIEW"`
   - `APPROVED = "APPROVED"`
   - `SUPERSEDED = "SUPERSEDED"`
   - `ARCHIVED = "ARCHIVED"`
4. **`ResilienceExerciseTypeEnum(str, enum.Enum)`**:
   - `TABLETOP = "TABLETOP"`
   - `FUNCTIONAL_FAILOVER = "FUNCTIONAL_FAILOVER"`
   - `FULL_DR_SIMULATION = "FULL_DR_SIMULATION"`
   - `CHAOS_ENGINEERING = "CHAOS_ENGINEERING"`
5. **`ResilienceExerciseStatusEnum(str, enum.Enum)`**:
   - `PLANNED = "PLANNED"`
   - `IN_PROGRESS = "IN_PROGRESS"`
   - `COMPLETED_PENDING_REVIEW = "COMPLETED_PENDING_REVIEW"`
   - `REVIEWED_CLOSED = "REVIEWED_CLOSED"`
   - `CANCELLED = "CANCELLED"`
6. **`ResilienceExerciseOutcomeEnum(str, enum.Enum)`**:
   - `PENDING = "PENDING"`
   - `PASSED = "PASSED"`
   - `PASSED_WITH_OBSERVATIONS = "PASSED_WITH_OBSERVATIONS"`
   - `FAILED_RTO_BREACH = "FAILED_RTO_BREACH"`
   - `FAILED_RPO_BREACH = "FAILED_RPO_BREACH"`
   - `FAILED_MTD_BREACH = "FAILED_MTD_BREACH"`
   - `FAILED_EXECUTION = "FAILED_EXECUTION"`
7. **`ResilienceEvidenceTargetTypeEnum(str, enum.Enum)`**:
   - `CONTINUITY_PLAN = "CONTINUITY_PLAN"`
   - `RESILIENCE_EXERCISE = "RESILIENCE_EXERCISE"`

### 11.2 Extended Columns on Existing `ProcessDependency` (`process_dependencies`)
- `is_single_point_of_failure = Column(Boolean, nullable=False, default=False)`
- `criticality_impact = Column(Enum(CriticalityTierEnum), nullable=False, default=CriticalityTierEnum.TIER_2)`
- `updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))`

### 11.3 New Model 1: `ContinuityPlan` (`continuity_plans`)
- **Purpose**: Governed, versioned Business Continuity Plan (BCP) or Disaster Recovery (DR) Runbook linked to a `BusinessProcess` and optionally its active `BusinessImpactAnalysis`.
- **Columns**:
  - `id`: `Integer`, PK, indexed.
  - `organization_id`: `Integer`, `ForeignKey("organizations.id", ondelete="CASCADE")`, `nullable=False`, indexed.
  - `process_id`: `Integer`, `ForeignKey("business_processes.id", ondelete="CASCADE")`, `nullable=False`, indexed.
  - `bia_id`: `Integer`, `ForeignKey("business_impact_analyses.id", ondelete="SET NULL")`, `nullable=True`, indexed.
  - `plan_code`: `String(64)`, `nullable=False`, indexed.
  - `title`: `String(255)`, `nullable=False`.
  - `plan_type`: `Enum(ContinuityPlanTypeEnum)`, `nullable=False`, default `BUSINESS_CONTINUITY_PLAN`, indexed.
  - `status`: `Enum(ContinuityPlanStatusEnum)`, `nullable=False`, default `DRAFT`, indexed.
  - `version`: `Integer`, `nullable=False`, default `1`.
  - `activation_triggers`: `Text`, `nullable=False` (conditions that trigger BCP/DR invocation).
  - `recovery_strategy_summary`: `Text`, `nullable=False` (failover architecture, alternate site/region, manual workaround).
  - `communication_protocol`: `Text`, `nullable=True` (stakeholder & escalation communication plan).
  - `estimated_recovery_hours`: `Float`, `nullable=False`, default `4.0` (estimated total recovery duration across steps).
  - `review_frequency_days`: `Integer`, `nullable=False`, default `365`.
  - `next_review_due_at`: `DateTime(timezone=True)`, `nullable=True`.
  - `created_by_id`: `Integer`, `ForeignKey("users.id", ondelete="RESTRICT")`, `nullable=False`, indexed.
  - `submitted_at`: `DateTime(timezone=True)`, `nullable=True`.
  - `approved_by_id`: `Integer`, `ForeignKey("users.id", ondelete="SET NULL")`, `nullable=True`, indexed.
  - `approved_at`: `DateTime(timezone=True)`, `nullable=True`.
  - `approval_notes`: `Text`, `nullable=True`.
  - `created_at`: `DateTime(timezone=True)`, `nullable=False`.
  - `updated_at`: `DateTime(timezone=True)`, `nullable=False`.
- **Constraints**:
  - `UniqueConstraint("organization_id", "plan_code", name="uq_continuity_plan_org_code")`
  - `UniqueConstraint("process_id", "plan_type", "version", name="uq_continuity_plan_proc_type_ver")`
  - `CheckConstraint("version >= 1", name="chk_continuity_plan_version_pos")`
  - `CheckConstraint("estimated_recovery_hours >= 0.0", name="chk_continuity_plan_est_hours_nonneg")`
  - `CheckConstraint("review_frequency_days >= 1 AND review_frequency_days <= 1825", name="chk_continuity_plan_rev_freq_bounds")`
  - `CheckConstraint("approved_by_id IS NULL OR created_by_id != approved_by_id", name="chk_continuity_plan_sod")`

### 11.4 New Model 2: `ContinuityRecoveryStep` (`continuity_recovery_steps`)
- **Purpose**: Ordered, actionable recovery runbook procedure step inside a `ContinuityPlan`.
- **Columns**:
  - `id`: `Integer`, PK, indexed.
  - `organization_id`: `Integer`, `ForeignKey("organizations.id", ondelete="CASCADE")`, `nullable=False`, indexed.
  - `continuity_plan_id`: `Integer`, `ForeignKey("continuity_plans.id", ondelete="CASCADE")`, `nullable=False`, indexed.
  - `step_order`: `Integer`, `nullable=False`.
  - `title`: `String(255)`, `nullable=False`.
  - `description`: `Text`, `nullable=False`.
  - `responsible_role`: `String(100)`, `nullable=False`, default `"SECURITY_ANALYST"`.
  - `estimated_duration_minutes`: `Integer`, `nullable=False`, default `30`.
  - `verification_criteria`: `Text`, `nullable=False`.
  - `is_automated`: `Boolean`, `nullable=False`, default `False`.
  - `created_at`: `DateTime(timezone=True)`, `nullable=False`.
  - `updated_at`: `DateTime(timezone=True)`, `nullable=False`.
- **Constraints**:
  - `UniqueConstraint("continuity_plan_id", "step_order", name="uq_continuity_step_plan_order")`
  - `CheckConstraint("step_order >= 1", name="chk_continuity_step_order_pos")`
  - `CheckConstraint("estimated_duration_minutes >= 1", name="chk_continuity_step_duration_pos")`

### 11.5 New Model 3: `ResilienceExercise` (`resilience_exercises`)
- **Purpose**: Empirical operational resilience exercise / DR failover test record that validates whether a `BusinessProcess` and its `ContinuityPlan` achieve the active `BusinessImpactAnalysis` `RTO`, `RPO`, and `MTD` targets.
- **Columns**:
  - `id`: `Integer`, PK, indexed.
  - `organization_id`: `Integer`, `ForeignKey("organizations.id", ondelete="CASCADE")`, `nullable=False`, indexed.
  - `process_id`: `Integer`, `ForeignKey("business_processes.id", ondelete="CASCADE")`, `nullable=False`, indexed.
  - `bia_id`: `Integer`, `ForeignKey("business_impact_analyses.id", ondelete="RESTRICT")`, `nullable=False`, indexed.
  - `continuity_plan_id`: `Integer`, `ForeignKey("continuity_plans.id", ondelete="SET NULL")`, `nullable=True`, indexed.
  - `exercise_code`: `String(64)`, `nullable=False`, indexed.
  - `title`: `String(255)`, `nullable=False`.
  - `exercise_type`: `Enum(ResilienceExerciseTypeEnum)`, `nullable=False`, default `TABLETOP`, indexed.
  - `status`: `Enum(ResilienceExerciseStatusEnum)`, `nullable=False`, default `PLANNED`, indexed.
  - `scenario_description`: `Text`, `nullable=False`.
  - `scheduled_at`: `DateTime(timezone=True)`, `nullable=False`.
  - `started_at`: `DateTime(timezone=True)`, `nullable=True`.
  - `completed_at`: `DateTime(timezone=True)`, `nullable=True`.
  - **Snapshot of Target Thresholds from Active BIA at Exercise Binding (Server-Authoritative)**:
    - `target_rto_hours`: `Float`, `nullable=False`.
    - `target_rpo_hours`: `Float`, `nullable=False`.
    - `target_mtd_hours`: `Float`, `nullable=False`.
  - **Empirical Observed Telemetry & Deterministic Variance (Server-Calculated on Completion)**:
    - `observed_rto_hours`: `Float`, `nullable=True`.
    - `observed_rpo_hours`: `Float`, `nullable=True`.
    - `rto_variance_hours`: `Float`, `nullable=True` (`round(observed_rto_hours - target_rto_hours, 2)`).
    - `rpo_variance_hours`: `Float`, `nullable=True` (`round(observed_rpo_hours - target_rpo_hours, 2)`).
    - `is_rto_breached`: `Boolean`, `nullable=False`, default `False` (`observed_rto_hours > target_rto_hours`).
    - `is_rpo_breached`: `Boolean`, `nullable=False`, default `False` (`observed_rpo_hours > target_rpo_hours`).
    - `is_mtd_breached`: `Boolean`, `nullable=False`, default `False` (`observed_rto_hours > target_mtd_hours`).
    - `exercise_score`: `Float`, `nullable=True` (`[0.0, 100.0]` deterministic achievement score).
    - `exercise_outcome`: `Enum(ResilienceExerciseOutcomeEnum)`, `nullable=False`, default `PENDING`, indexed.
  - **Observations, Lessons Learned & Closed-Loop Governance Links**:
    - `execution_summary`: `Text`, `nullable=True`.
    - `lessons_learned`: `Text`, `nullable=True`.
    - `finding_id`: `Integer`, `ForeignKey("findings.id", ondelete="SET NULL")`, `nullable=True`, indexed.
    - `remediation_plan_id`: `Integer`, `ForeignKey("remediation_plans.id", ondelete="SET NULL")`, `nullable=True`, indexed.
    - `risk_id`: `Integer`, `ForeignKey("risks.id", ondelete="SET NULL")`, `nullable=True`, indexed.
  - **Actors & Four-Eyes Separation of Duties**:
    - `planned_by_id`: `Integer`, `ForeignKey("users.id", ondelete="RESTRICT")`, `nullable=False`, indexed.
    - `executed_by_id`: `Integer`, `ForeignKey("users.id", ondelete="SET NULL")`, `nullable=True`, indexed.
    - `reviewed_by_id`: `Integer`, `ForeignKey("users.id", ondelete="SET NULL")`, `nullable=True`, indexed.
    - `reviewed_at`: `DateTime(timezone=True)`, `nullable=True`.
    - `review_notes`: `Text`, `nullable=True`.
    - `created_at`: `DateTime(timezone=True)`, `nullable=False`.
    - `updated_at`: `DateTime(timezone=True)`, `nullable=False`.
- **Constraints**:
  - `UniqueConstraint("organization_id", "exercise_code", name="uq_resilience_exercise_org_code")`
  - `CheckConstraint("target_rto_hours >= 0.0 AND target_rpo_hours >= 0.0 AND target_mtd_hours >= 0.0", name="chk_exercise_targets_nonneg")`
  - `CheckConstraint("observed_rto_hours IS NULL OR observed_rto_hours >= 0.0", name="chk_exercise_obs_rto_nonneg")`
  - `CheckConstraint("observed_rpo_hours IS NULL OR observed_rpo_hours >= 0.0", name="chk_exercise_obs_rpo_nonneg")`
  - `CheckConstraint("exercise_score IS NULL OR (exercise_score >= 0.0 AND exercise_score <= 100.0)", name="chk_exercise_score_bounds")`
  - `CheckConstraint("reviewed_by_id IS NULL OR executed_by_id IS NULL OR executed_by_id != reviewed_by_id", name="chk_exercise_review_sod")`

### 11.6 New Model 4: `ResilienceEvidenceLink` (`resilience_evidence_links`)
- **Purpose**: Binds Phase 3 `EvidenceItem` records to either a `ContinuityPlan` or a `ResilienceExercise` with strict single-target invariant and tenant isolation.
- **Columns**:
  - `id`: `Integer`, PK, indexed.
  - `organization_id`: `Integer`, `ForeignKey("organizations.id", ondelete="CASCADE")`, `nullable=False`, indexed.
  - `target_type`: `Enum(ResilienceEvidenceTargetTypeEnum)`, `nullable=False`, indexed.
  - `continuity_plan_id`: `Integer`, `ForeignKey("continuity_plans.id", ondelete="CASCADE")`, `nullable=True`, indexed.
  - `exercise_id`: `Integer`, `ForeignKey("resilience_exercises.id", ondelete="CASCADE")`, `nullable=True`, indexed.
  - `evidence_id`: `Integer`, `ForeignKey("evidence_items.id", ondelete="RESTRICT")`, `nullable=False`, indexed.
  - `linked_by_id`: `Integer`, `ForeignKey("users.id", ondelete="SET NULL")`, `nullable=True`, indexed.
  - `notes`: `String(500)`, `nullable=True`.
  - `created_at`: `DateTime(timezone=True)`, `nullable=False`.
- **Constraints**:
  - `CheckConstraint("((CASE WHEN continuity_plan_id IS NOT NULL THEN 1 ELSE 0 END) + (CASE WHEN exercise_id IS NOT NULL THEN 1 ELSE 0 END)) = 1", name="chk_resilience_evidence_single_target")`
  - `UniqueConstraint("continuity_plan_id", "evidence_id", name="uq_continuity_plan_evidence")`
  - `UniqueConstraint("exercise_id", "evidence_id", name="uq_resilience_exercise_evidence")`

---

## 12. State Machine Analysis

- **ARCHITECTURAL DECISION**: Batch 5 governs three interconnected state machines in `ResilienceService`:

### 12.1 Business Impact Analysis (`BiaStatusEnum` — Existing + Hardened)
```
DRAFT ──(approve_bia: Four-Eyes requested_by_id != user_id)──> ACTIVE ──(new BIA approved for same process)──> SUPERSEDED
  │
  └──(archive_draft_bia)──> ARCHIVED
```
- **Invariants**:
  - Only `DRAFT` BIAs can be updated (`update_draft_bia`) or archived (`archive_draft_bia`).
  - `ACTIVE`, `SUPERSEDED`, and `ARCHIVED` BIAs are strictly immutable (`409 Conflict` on edit/archive).
  - Approving a `DRAFT` BIA atomically transitions any prior `ACTIVE` BIA for that `process_id` to `SUPERSEDED`.

### 12.2 Continuity Plan (`ContinuityPlanStatusEnum` — New in Batch 5)
```
DRAFT ──(submit_continuity_plan: requires >= 1 ContinuityRecoveryStep)──> UNDER_REVIEW
  ▲                                                                            │
  │                                                                            ├──(reject_continuity_plan)──> DRAFT
  │                                                                            │
  │                                      (approve_continuity_plan: Four-Eyes created_by_id != approved_by_id)
  │                                                                            ▼
  └──(archive_continuity_plan)──> ARCHIVED <──(manual archive)────────── APPROVED ──(newer version approved for same process_id + plan_type)──> SUPERSEDED
```
- **Invariants**:
  - `ContinuityRecoveryStep` additions, updates, or deletions are permitted **only** while `ContinuityPlan.status == DRAFT`. Attempting to mutate steps in `UNDER_REVIEW`, `APPROVED`, `SUPERSEDED`, or `ARCHIVED` raises `409 Conflict`.
  - Submitting a `DRAFT` plan to `UNDER_REVIEW` requires at least 1 `ContinuityRecoveryStep` (`422 Unprocessable Entity` if 0 steps exist).
  - Approving a plan in `UNDER_REVIEW` enforces Four-Eyes (`created_by_id != current_user.id` -> `403 Forbidden`), sets `status = APPROVED`, `approved_by_id`, `approved_at`, `next_review_due_at = approved_at + timedelta(days=review_frequency_days)`, and atomically transitions any previously `APPROVED` plan for the same `(process_id, plan_type)` to `SUPERSEDED`.
  - `SUPERSEDED` and `ARCHIVED` plans are terminal and immutable (`409 Conflict`).

### 12.3 Resilience Exercise (`ResilienceExerciseStatusEnum` — New in Batch 5)
```
PLANNED ──(start_exercise)──> IN_PROGRESS ──(complete_exercise: computes RTO/RPO variance & outcome)──> COMPLETED_PENDING_REVIEW
   │                               │                                                                           │
   └──(cancel_exercise)────────────┴──────────────────────> CANCELLED                                          ├──(review_exercise: Four-Eyes executed_by_id != reviewed_by_id)──> REVIEWED_CLOSED
                                                                                                               │
                                                                                                               └──(reopen_exercise: review rejected)──> IN_PROGRESS
```
- **Invariants**:
  - Creating an exercise (`PLANNED`) requires an `ACTIVE` `BusinessImpactAnalysis` on the target `BusinessProcess` (or explicitly bound `bia_id` belonging to that process in `ACTIVE` status) and snapshots `target_rto_hours = bia.rto_hours`, `target_rpo_hours = bia.rpo_hours`, `target_mtd_hours = bia.mtd_hours` server-side (client cannot spoof target thresholds). If `continuity_plan_id` is provided, it must belong to the same `process_id` and be in `APPROVED` status (`409 Conflict` if `DRAFT`/`ARCHIVED`).
  - `start_exercise`: transitions `PLANNED -> IN_PROGRESS`, sets `started_at = now_utc`, `executed_by_id = current_user.id`.
  - `complete_exercise`: transitions `IN_PROGRESS -> COMPLETED_PENDING_REVIEW`, requires `observed_rto_hours >= 0.0`, `observed_rpo_hours >= 0.0`, and `execution_summary`. Deterministically computes:
    - `rto_variance_hours = round(observed_rto_hours - target_rto_hours, 2)`
    - `rpo_variance_hours = round(observed_rpo_hours - target_rpo_hours, 2)`
    - `is_rto_breached = observed_rto_hours > target_rto_hours`
    - `is_rpo_breached = observed_rpo_hours > target_rpo_hours`
    - `is_mtd_breached = observed_rto_hours > target_mtd_hours`
    - Deterministic `exercise_outcome`:
      - If `has_execution_failure == True`: `FAILED_EXECUTION`
      - Else if `is_mtd_breached`: `FAILED_MTD_BREACH`
      - Else if `is_rto_breached`: `FAILED_RTO_BREACH`
      - Else if `is_rpo_breached`: `FAILED_RPO_BREACH`
      - Else if `has_observations == True`: `PASSED_WITH_OBSERVATIONS`
      - Else: `PASSED`
    - Deterministic `exercise_score` (`[0.0, 100.0]`):
      - Base `100.0`; minus `50.0` if `is_mtd_breached`; minus `30.0` if `is_rto_breached`; minus `25.0` if `is_rpo_breached`; minus `40.0` if `FAILED_EXECUTION`; minus `10.0` if `PASSED_WITH_OBSERVATIONS`; clamped to `[0.0, 100.0]`.
  - `review_exercise`: transitions `COMPLETED_PENDING_REVIEW -> REVIEWED_CLOSED` (if approved) or `IN_PROGRESS` (if rejected for re-execution). Enforces Four-Eyes (`executed_by_id != current_user.id` and `planned_by_id != current_user.id` when `executed_by_id == planned_by_id` -> `403 Forbidden`). If the exercise outcome is a failure/breach (`FAILED_MTD_BREACH`, `FAILED_RTO_BREACH`, `FAILED_RPO_BREACH`, `FAILED_EXECUTION`), closing (`REVIEWED_CLOSED`) requires either an existing linked `finding_id` / `remediation_plan_id` or `auto_create_finding=True` so no failed recovery exercise can be silently closed without remediation tracking!
  - `REVIEWED_CLOSED` and `CANCELLED` exercises are strictly immutable (`409 Conflict` on any mutation).

---

## 13. Four-Eyes / SoD

- **ARCHITECTURAL DECISION**: Batch 5 enforces three layers of Separation of Duties (SoD) across service logic and SQLAlchemy `CheckConstraint` declarations:
  1. **BIA Baseline Approval SoD (Existing, Preserved)**:
     - `BusinessImpactAnalysis.requested_by_id != current_user.id` enforced in `ResilienceService.approve_bia` (`403 Forbidden`).
  2. **Continuity Plan Approval SoD (New)**:
     - Service check in `ResilienceService.approve_continuity_plan`: if `plan.created_by_id == current_user.id`, raise `HTTPException(status_code=403, detail="Four-eyes governance violation: The plan author cannot approve their own Continuity Plan.")`.
     - Database constraint on `continuity_plans`: `CheckConstraint("approved_by_id IS NULL OR created_by_id != approved_by_id", name="chk_continuity_plan_sod")`.
  3. **Resilience Exercise Review & Sign-Off SoD (New)**:
     - Service check in `ResilienceService.review_exercise`: if `exercise.executed_by_id == current_user.id` (or `exercise.executed_by_id is None and exercise.planned_by_id == current_user.id`), raise `HTTPException(status_code=403, detail="Four-eyes governance violation: The exercise executor cannot review and sign off their own Resilience Exercise.")`.
     - Database constraint on `resilience_exercises`: `CheckConstraint("reviewed_by_id IS NULL OR executed_by_id IS NULL OR executed_by_id != reviewed_by_id", name="chk_exercise_review_sod")`.

---

## 14. RBAC Matrix

- **REPOSITORY FACT**: `backend/app/core/permissions.py` currently defines 3 resilience permissions (`RESILIENCE_READ`, `RESILIENCE_MANAGE`, `RESILIENCE_APPROVE`). Notably, `SECURITY_ANALYST` currently has only `RESILIENCE_READ`, even though security analysts participate in executing DR failover exercises and runbook drills.
- **ARCHITECTURAL DECISION**: Add `Permission.RESILIENCE_EXECUTE = "resilience:execute"` to `Permission` in `backend/app/core/permissions.py` and grant it to `ADMIN`, `MANAGER`, `GRC_ANALYST`, and `SECURITY_ANALYST`. The complete RBAC matrix across all 6 platform roles is:

| Permission | Action Scope in `RESILIENCE-CONTINUITY-GRC` | `ADMIN` | `MANAGER` | `GRC_ANALYST` | `SECURITY_ANALYST` | `AUDITOR` | `VIEWER` |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `RESILIENCE_READ` | View processes, BIAs, continuity plans, recovery steps, exercises, dependencies, evidence links, outage loss & readiness posture | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW |
| `RESILIENCE_MANAGE` | Create/update/delete business processes, draft/archive BIAs, create/edit/submit/archive continuity plans & recovery steps, schedule/cancel exercises, manage process dependencies | ALLOW | ALLOW | ALLOW | DENY (`403`) | DENY (`403`) | DENY (`403`) |
| `RESILIENCE_EXECUTE` | Start (`PLANNED -> IN_PROGRESS`) and complete (`IN_PROGRESS -> COMPLETED_PENDING_REVIEW`) resilience exercises, bind evidence items (`ResilienceEvidenceLink`), escalate failed exercises to Findings/CAPA | ALLOW | ALLOW | ALLOW | ALLOW | DENY (`403`) | DENY (`403`) |
| `RESILIENCE_APPROVE` | Four-Eyes approve BIA baselines, Four-Eyes approve/reject Continuity Plans (`UNDER_REVIEW -> APPROVED`), Four-Eyes review/close Resilience Exercises (`COMPLETED_PENDING_REVIEW -> REVIEWED_CLOSED`) | ALLOW | ALLOW | DENY (`403`) | DENY (`403`) | DENY (`403`) | DENY (`403`) |

---

## 15. Tenant Isolation

- **ARCHITECTURAL DECISION**: Every table in Batch 5 (`continuity_plans`, `continuity_recovery_steps`, `resilience_exercises`, `resilience_evidence_links`, as well as existing `business_processes`, `business_impact_analyses`, `process_dependencies`) carries `organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)`.
- **ARCHITECTURAL DECISION**: `organization_id` is **never** accepted from request payloads or query parameters; it is always injected from `current_user.organization_id`. Every `SELECT`, `UPDATE`, and `DELETE` query in `ResilienceService` filters by `Model.organization_id == organization_id`.

---

## 16. BOLA / IDOR

- **ARCHITECTURAL DECISION**: Cross-tenant or non-existent object references must always return `404 Not Found` (`status.HTTP_404_NOT_FOUND`) before any state validation or mutation occurs, preventing tenant enumeration.
- **ARCHITECTURAL DECISION**: All cross-entity and cross-module foreign keys supplied in payloads are explicitly verified against `organization_id == current_user.organization_id`:
  1. `process_id` -> `BusinessProcess(id=process_id, organization_id=organization_id)` (`404` if missing; also fixed on `get_active_bia` and `list_process_dependencies`).
  2. `bia_id` -> `BusinessImpactAnalysis(id=bia_id, organization_id=organization_id, process_id=process_id)` (`404` if missing or belongs to a different process).
  3. `continuity_plan_id` -> `ContinuityPlan(id=continuity_plan_id, organization_id=organization_id, process_id=process_id)` (`404` if missing or belongs to a different process).
  4. `dependency_id` in `ProcessDependency`:
     - `VENDOR` -> `Vendor(id=dependency_id, organization_id=organization_id)` (`404` if missing)
     - `CONTROL` -> `OrganizationControl(id=dependency_id, organization_id=organization_id)` (`404` if missing)
     - `CLOUD_ASSET` -> `CloudAsset(id=dependency_id, organization_id=organization_id)` (`404` if missing)
     - `DATA_ASSET` -> `DataAsset(id=dependency_id, organization_id=organization_id)` (`404` if missing)
  5. `evidence_id` in `ResilienceEvidenceLink` -> `EvidenceItem(id=evidence_id, organization_id=organization_id)` (`404` if missing).
  6. `finding_id`, `remediation_plan_id`, `risk_id` on `ResilienceExercise` -> verified against `Finding`, `RemediationPlan`, and `Risk` in the same `organization_id` (`404` if missing).

---

## 17. Evidence Integration

- **REPOSITORY FACT**: Phase 3 (`backend/app/models/evidence.py`) governs `EvidenceItem` (`status` in `EvidenceStatusEnum`: `SUBMITTED`, `UNDER_REVIEW`, `ACCEPTED`, `REJECTED`, `EXPIRED`).
- **ARCHITECTURAL DECISION**: `ResilienceEvidenceLink` binds `EvidenceItem` records to either a `ContinuityPlan` (e.g., architecture failover diagrams, call-tree documentation) or a `ResilienceExercise` (e.g., DR failover execution logs, database restoration timing logs).
- **ARCHITECTURAL DECISION**: `ResilienceService.link_evidence` rejects `EvidenceItem` records whose status is `REJECTED` or `EXPIRED` (`409 Conflict`), ensuring only active/valid evidence artifacts substantiate continuity plans and exercises.

---

## 18. Control Integration

- **REPOSITORY FACT**: Phase 2 (`OrganizationControl`, `ImplementationStatusEnum`) and Phase 7 (`ControlHealthSnapshot`) track control implementation and health.
- **ARCHITECTURAL DECISION**: `ProcessDependency` links `BusinessProcess` to `OrganizationControl` (`DependencyTypeEnum.CONTROL`). In Batch 5's deterministic readiness engine (`ResilienceService.calculate_process_resilience_readiness`), any linked `OrganizationControl` that is not `IMPLEMENTED` (or whose latest `ControlHealthSnapshot` is `FAILING`/`DEGRADED`) degrades the process's Dependency Health sub-score, and if marked `is_single_point_of_failure=True`, flags an active SPOF risk on the process.

---

## 19. Risk Integration

- **REPOSITORY FACT**: Phase 5 (`backend/app/models/risk.py`) governs enterprise `Risk` records (`RiskCategoryEnum`, `RiskSourceEnum`, `RiskStatusEnum`).
- **ARCHITECTURAL DECISION**: `ResilienceExercise` includes an optional `risk_id` (`ForeignKey("risks.id", ondelete="SET NULL")`). When a `ResilienceExercise` results in an RTO, RPO, or MTD breach (`is_rto_breached`, `is_rpo_breached`, or `is_mtd_breached`), analysts can link an existing `Risk` or invoke `ResilienceService.escalate_exercise_deficiency` to link/update operational risk posture in the same tenant.

---

## 20. Remediation Integration

- **REPOSITORY FACT**: Phase 11 (`backend/app/models/remediation.py`, lines 25–30 & 184–192) enforces a strict `CheckConstraint` (`chk_remediation_single_source`) requiring every `RemediationPlan` to have `source_type` in `RemediationSourceTypeEnum` (`FINDING`, `CCM_DRIFT`, `SECURITY_INCIDENT`, `TPRM_ASSESSMENT`, `AUDIT`) and exactly one corresponding FK (`finding_id`, `compliance_drift_alert_id`, `security_incident_id`, `vendor_assessment_id`, `audit_id`) non-null.
- **ARCHITECTURAL DECISION**: To integrate cleanly with Phase 11 `RemediationPlan` **without** breaking `chk_remediation_single_source` on existing migrations, `ResilienceService.escalate_exercise_deficiency` creates (or links) an authoritative Phase 4 `Finding` (`FindingTypeEnum.CONTROL_DEFICIENCY`, severity derived from `is_mtd_breached` -> `CRITICAL`, `is_rto_breached` -> `HIGH`, `is_rpo_breached` -> `MEDIUM`) and then creates a Phase 11 `RemediationPlan` with `source_type = RemediationSourceTypeEnum.FINDING` and `finding_id = finding.id`! Both `finding_id` and `remediation_plan_id` are stored on `ResilienceExercise`, satisfying both Phase 11's single-source check constraint and Batch 5's closed-loop remediation requirement.

---

## 21. Regulatory Integration

- **REPOSITORY FACT**: Phase 21 (`backend/app/models/regulatory.py`) governs `RegulatoryMandate` and `RegulatoryObligation` mapped to `OrganizationControl`.
- **ARCHITECTURAL DECISION**: Continuity plans and recovery exercises provide empirical assurance for operational resilience mandates (such as DORA, ISO 22301, and NIS2) via shared `OrganizationControl` dependencies (`ProcessDependency.dependency_type == CONTROL` <-> `RegulatoryObligation.organization_control_id`).

---

## 22. Executive Integration

- **REPOSITORY FACT**: In `backend/app/services/executive_service.py` (lines 386–408), Domain 10 (`incidents_resilience`, weight `0.05`) currently computes `resilience_score` solely from `SecurityIncident` counts (`100.0 - (open_critical_incidents * 25.0 + open_high_incidents * 10.0)`) and never queries `BusinessProcess` or `BusinessImpactAnalysis` even though line 403 states `"source_tables": ["security_incidents", "business_impact_analyses"]`.
- **ARCHITECTURAL DECISION**: Update `ExecutiveService.calculate_live_telemetry` (`incidents_resilience` domain) so that:
  - When a tenant has zero `BusinessProcess` records (the default in legacy unit tests that only seed `SecurityIncident` records), `resilience_score` continues to evaluate to `round(max(0.0, min(100.0, 100.0 - incidents_penalty)), 2)` (**100% backward-compatible with all existing Phase 20 tests**).
  - When a tenant has one or more `BusinessProcess` records, `incidents_resilience` incorporates the authoritative tenant resilience readiness score from `ResilienceService.calculate_tenant_resilience_posture(db, org_id)` blended with `incidents_score` (`0.60 * incident_score + 0.40 * process_resilience_readiness_score`, with `continuity_plans` and `resilience_exercises` included in `source_tables`).

---

## 23. Continuous Assurance Integration

- **REPOSITORY FACT**: `ContinuousComplianceService` (`backend/app/services/continuous_compliance_service.py`) aggregates enterprise assurance pillars and detects multi-vector drift.
- **ARCHITECTURAL DECISION**: Expose `ResilienceService.calculate_tenant_resilience_posture(db, organization_id)` so continuous assurance and resilience dashboards have a single authoritative calculation of:
  - `bia_coverage_pct`
  - `approved_continuity_plan_coverage_pct`
  - `tested_process_coverage_pct`
  - `exercise_pass_rate_pct`
  - `rto_rpo_breach_count`
  - `spof_dependency_count`
  - `overall_resilience_readiness_score` (`[0.0, 100.0]`).

---

## 24. Notification Integration

- **REPOSITORY FACT**: ControlSphere does not use an external SMTP/webhook notification daemon; all operational alerts and governance events are surfaced via database-backed status queues, dashboard posture banners, and `AuditLog` entries.
- **ARCHITECTURAL DECISION**: `ResilienceService.calculate_tenant_resilience_posture` surfaces actionable governance alerts (overdue continuity plan reviews where `next_review_due_at < now_utc`, unassessed Tier 1 processes lacking an `ACTIVE` BIA or `APPROVED` Continuity Plan, exercises in `COMPLETED_PENDING_REVIEW`, and unmitigated exercise RTO/RPO breaches).

---

## 25. Audit Logging

- **ARCHITECTURAL DECISION**: Every state-changing operation in `ResilienceService` must write a structured `AuditLog` entry via `AuditService.log`:
  - **Existing Phase 13 Actions (Preserved + Fixed)**:
    - `BUSINESS_PROCESS_CREATED`, `BUSINESS_PROCESS_UPDATED`, `BUSINESS_PROCESS_DELETED` (newly added to fix unlogged delete in route)
    - `BIA_DRAFTED`, `BIA_UPDATED` (newly added to fix unlogged update in route), `BIA_APPROVED`, `BIA_ARCHIVED`
    - `PROCESS_DEPENDENCY_ADDED`, `PROCESS_DEPENDENCY_REMOVED`
  - **New Batch 5 Actions**:
    - `CONTINUITY_PLAN_CREATED`, `CONTINUITY_PLAN_UPDATED`, `CONTINUITY_PLAN_SUBMITTED`, `CONTINUITY_PLAN_APPROVED`, `CONTINUITY_PLAN_REJECTED`, `CONTINUITY_PLAN_ARCHIVED`
    - `CONTINUITY_STEP_ADDED`, `CONTINUITY_STEP_UPDATED`, `CONTINUITY_STEP_DELETED`
    - `RESILIENCE_EXERCISE_PLANNED`, `RESILIENCE_EXERCISE_STARTED`, `RESILIENCE_EXERCISE_COMPLETED`, `RESILIENCE_EXERCISE_REVIEWED`, `RESILIENCE_EXERCISE_REOPENED`, `RESILIENCE_EXERCISE_CANCELLED`
    - `RESILIENCE_EXERCISE_ESCALATED`
    - `RESILIENCE_EVIDENCE_LINKED`, `RESILIENCE_EVIDENCE_UNLINKED`

---

## 26. API Boundary

- **REPOSITORY FACT**: Phase 13 is mounted at `/api/v1/resilience` (`backend/app/api/v1/api.py`, line 62) and defined in `backend/app/api/v1/endpoints/resilience.py`.
- **ARCHITECTURAL DECISION**: Preserve all 14 existing endpoints in `backend/app/api/v1/endpoints/resilience.py` with 100% route and schema backward compatibility, while adding the following governed endpoints under `/api/v1/resilience`:

| Method & Path | Permission Required | Service Method | Purpose |
| :--- | :--- | :--- | :--- |
| `GET /api/v1/resilience/posture` | `RESILIENCE_READ` | `ResilienceService.calculate_tenant_resilience_posture` | Tenant-wide operational resilience readiness score, BIA/BCP/exercise coverage, RTO/RPO breach counts, and SPOF telemetry |
| `GET /api/v1/resilience/processes/{process_id}/readiness` | `RESILIENCE_READ` | `ResilienceService.calculate_process_resilience_readiness` | Per-process deterministic readiness score `[0, 100]`, dependency health, active BIA/BCP status, and latest exercise telemetry |
| `POST /api/v1/resilience/plans` | `RESILIENCE_MANAGE` | `ResilienceService.create_continuity_plan` | Create a `DRAFT` Continuity Plan (auto-increments version per `process_id` + `plan_type`) |
| `GET /api/v1/resilience/plans` | `RESILIENCE_READ` | `ResilienceService.list_continuity_plans` | List tenant Continuity Plans (filterable by `process_id`, `plan_type`, `status`) |
| `GET /api/v1/resilience/plans/{plan_id}` | `RESILIENCE_READ` | `ResilienceService.get_continuity_plan` | Retrieve Continuity Plan with ordered `recovery_steps` and `evidence_links` |
| `PUT /api/v1/resilience/plans/{plan_id}` | `RESILIENCE_MANAGE` | `ResilienceService.update_continuity_plan` | Update a `DRAFT` Continuity Plan (`409` if not `DRAFT`) |
| `POST /api/v1/resilience/plans/{plan_id}/steps` | `RESILIENCE_MANAGE` | `ResilienceService.add_recovery_step` | Add an ordered `ContinuityRecoveryStep` to a `DRAFT` plan (`409` if not `DRAFT`) |
| `PUT /api/v1/resilience/plans/{plan_id}/steps/{step_id}` | `RESILIENCE_MANAGE` | `ResilienceService.update_recovery_step` | Update a recovery step on a `DRAFT` plan (`409` if not `DRAFT`) |
| `DELETE /api/v1/resilience/plans/{plan_id}/steps/{step_id}` | `RESILIENCE_MANAGE` | `ResilienceService.delete_recovery_step` | Delete a recovery step from a `DRAFT` plan (`409` if not `DRAFT`) |
| `POST /api/v1/resilience/plans/{plan_id}/submit` | `RESILIENCE_MANAGE` | `ResilienceService.submit_continuity_plan` | Transition `DRAFT -> UNDER_REVIEW` (requires $\ge 1$ recovery step) |
| `POST /api/v1/resilience/plans/{plan_id}/approve` | `RESILIENCE_APPROVE` | `ResilienceService.approve_continuity_plan` | Four-Eyes approve `UNDER_REVIEW -> APPROVED` (`created_by_id != user_id`; supersedes prior `APPROVED` version) |
| `POST /api/v1/resilience/plans/{plan_id}/reject` | `RESILIENCE_APPROVE` | `ResilienceService.reject_continuity_plan` | Reject `UNDER_REVIEW -> DRAFT` with mandatory review notes |
| `POST /api/v1/resilience/plans/{plan_id}/archive` | `RESILIENCE_MANAGE` | `ResilienceService.archive_continuity_plan` | Archive `DRAFT` or `APPROVED` plan (`-> ARCHIVED`) |
| `POST /api/v1/resilience/exercises` | `RESILIENCE_MANAGE` | `ResilienceService.create_exercise` | Schedule a `PLANNED` Resilience Exercise bound to an `ACTIVE` BIA and optional `APPROVED` Continuity Plan |
| `GET /api/v1/resilience/exercises` | `RESILIENCE_READ` | `ResilienceService.list_exercises` | List tenant Resilience Exercises (filterable by `process_id`, `status`, `exercise_type`, `outcome`) |
| `GET /api/v1/resilience/exercises/{exercise_id}` | `RESILIENCE_READ` | `ResilienceService.get_exercise` | Retrieve Resilience Exercise with empirical RTO/RPO variance and linked Finding/CAPA/Evidence |
| `POST /api/v1/resilience/exercises/{exercise_id}/start` | `RESILIENCE_EXECUTE` | `ResilienceService.start_exercise` | Transition `PLANNED -> IN_PROGRESS`, recording `started_at` and `executed_by_id` |
| `POST /api/v1/resilience/exercises/{exercise_id}/complete` | `RESILIENCE_EXECUTE` | `ResilienceService.complete_exercise` | Transition `IN_PROGRESS -> COMPLETED_PENDING_REVIEW`, computing RTO/RPO variance, breach flags, score, and outcome |
| `POST /api/v1/resilience/exercises/{exercise_id}/review` | `RESILIENCE_APPROVE` | `ResilienceService.review_exercise` | Four-Eyes sign-off (`executed_by_id != reviewed_by_id`): `COMPLETED_PENDING_REVIEW -> REVIEWED_CLOSED` (or `IN_PROGRESS` on rejection) |
| `POST /api/v1/resilience/exercises/{exercise_id}/cancel` | `RESILIENCE_MANAGE` | `ResilienceService.cancel_exercise` | Cancel `PLANNED` or `IN_PROGRESS` exercise (`-> CANCELLED`) |
| `POST /api/v1/resilience/exercises/{exercise_id}/escalate` | `RESILIENCE_EXECUTE` | `ResilienceService.escalate_exercise_deficiency` | Spawn or link Phase 4 `Finding`, Phase 11 `RemediationPlan` (CAPA), and/or Phase 5 `Risk` for a breached/failed exercise |
| `POST /api/v1/resilience/evidence-links` | `RESILIENCE_EXECUTE` | `ResilienceService.link_evidence` | Link Phase 3 `EvidenceItem` to a `ContinuityPlan` or `ResilienceExercise` |
| `GET /api/v1/resilience/evidence-links` | `RESILIENCE_READ` | `ResilienceService.list_evidence_links` | List evidence links for a `continuity_plan_id` or `exercise_id` |
| `DELETE /api/v1/resilience/evidence-links/{link_id}` | `RESILIENCE_MANAGE` | `ResilienceService.unlink_evidence` | Remove a resilience evidence link |

---

## 27. Frontend Boundary

- **REPOSITORY FACT**: The frontend currently has `frontend/src/pages/ResiliencePage.tsx`, `frontend/src/pages/BusinessProcessDetailPage.tsx`, `frontend/src/lib/resilienceService.ts`, and components under `frontend/src/components/resilience/`.
- **ARCHITECTURAL DECISION**: Extend `frontend/src/lib/resilienceService.ts`, `frontend/src/types/index.ts`, `ResiliencePage.tsx`, and `BusinessProcessDetailPage.tsx` (without adding broken routes or removing existing tabs):
  - **`ResiliencePage.tsx`**:
    - Enhance the Executive Posture Overview tab with live server-authoritative readiness telemetry from `GET /api/v1/resilience/posture` (Overall Resilience Readiness Score, Approved BCP Coverage %, Empirical Exercise Pass Rate %, Active RTO/RPO Breaches, and SPOF Dependency Count).
    - Add tabs for **Continuity & DR Plans (`ContinuityPlan` catalog)** and **Recovery Exercises & DR Testing (`ResilienceExercise` register)** alongside the existing Business Process Register and Governance Lineage tabs.
  - **`BusinessProcessDetailPage.tsx`**:
    - Display the per-process Resilience Readiness score and SPOF alerts from `GET /api/v1/resilience/processes/{id}/readiness`.
    - Add interactive sections/modals for managing **Continuity Plans & Ordered Recovery Steps** (Create Draft, Add Step, Submit for Review, Four-Eyes Approve/Reject), **Resilience Exercises** (Schedule, Start, Complete with Empirical RTO/RPO inputs, Escalate Deficiency to Finding/CAPA, Four-Eyes Review & Close), and **Expanded Dependencies** (`VENDOR`, `CONTROL`, `CLOUD_ASSET`, `DATA_ASSET` with `is_single_point_of_failure` toggle).

---

## 28. Migration Strategy

- **REPOSITORY FACT**: The current Alembic head is `0025` (`backend/alembic/versions/0025_policy_lifecycle_governance_hardening.py`).
- **ARCHITECTURAL DECISION**: Create migration `backend/alembic/versions/0026_operational_resilience_continuity_and_testing.py` with `revision = "0026"` and `down_revision = "0025"`:
  1. Safely extend `dependencytypeenum` in PostgreSQL (`ALTER TYPE dependencytypeenum ADD VALUE IF NOT EXISTS 'CLOUD_ASSET'` and `'DATA_ASSET'`) with SQLite dialect compatibility.
  2. Add `is_single_point_of_failure` (`Boolean`, `server_default='false'`, `nullable=False`), `criticality_impact` (`Enum(CriticalityTierEnum)`, `server_default='TIER_2'`, `nullable=False`), and `updated_at` (`DateTime(timezone=True)`, `nullable=True` or server_default `now()`) to `process_dependencies`.
  3. Create `continuity_plans` with all FK, unique, and check constraints (`uq_continuity_plan_org_code`, `uq_continuity_plan_proc_type_ver`, `chk_continuity_plan_sod`, etc.).
  4. Create `continuity_recovery_steps` with `uq_continuity_step_plan_order` and positive check constraints.
  5. Create `resilience_exercises` with all FK, unique, and check constraints (`uq_resilience_exercise_org_code`, `chk_exercise_review_sod`, `chk_exercise_score_bounds`, etc.).
  6. Create `resilience_evidence_links` with `chk_resilience_evidence_single_target`, `uq_continuity_plan_evidence`, and `uq_resilience_exercise_evidence`.
  7. Provide a complete, deterministic `downgrade()` function that drops the 4 new tables and the 3 new columns on `process_dependencies`.

---

## 29. Anti-Duplication Gate

- **ARCHITECTURAL DECISION**: Every entity in Batch 5 has been verified against all 27 existing model modules:
  1. `ContinuityPlan` & `ContinuityRecoveryStep`: No other table in `backend/app/models/` stores business continuity plans or disaster recovery runbooks (`policy.py` stores corporate governance policies and workforce attestations; `remediation.py` stores post-deficiency CAPA plans).
  2. `ResilienceExercise`: No other table stores empirical BCP/DR failover exercises or RTO/RPO variance tests (`assessment.py` tests control design/operating effectiveness; `audit_engagement.py` conducts internal/external audit engagements; `quant_risk.py` runs financial FAIR Monte Carlo simulations).
  3. `ResilienceEvidenceLink`: Follows the exact link-table pattern established in `VendorEvidenceLink` (`tprm.py`), `RemediationEvidenceLink` (`remediation.py`), and `DataAssetEvidenceLink` (`data_governance.py`), referencing `EvidenceItem` (`evidence.py`) without duplicating file metadata.
  4. `Escalation to Finding & CAPA`: Reuses Phase 4 `Finding` (`finding.py`) and Phase 11 `RemediationPlan` (`remediation.py`) via foreign keys rather than inventing a resilience-specific remediation tracker.

---

## 30. Security Threat Model

- **ARCHITECTURAL DECISION**: At least 45 concrete adversarial security and governance vectors (`SEC-B5-01` through `SEC-B5-45`) are modeled and mitigated by design:

| Vector ID | Threat Category | Adversarial Attack Scenario | Authoritative Mitigation in Batch 5 |
| :--- | :--- | :--- | :--- |
| `SEC-B5-01` | Tenant Isolation | User in Tenant A queries `GET /api/v1/resilience/plans` or `/exercises` hoping to see Tenant B records. | Every query filters by `organization_id == current_user.organization_id`. |
| `SEC-B5-02` | BOLA / IDOR | User in Tenant A calls `GET /api/v1/resilience/plans/{plan_id}` with a `plan_id` belonging to Tenant B. | Returns `404 Not Found` before inspecting plan state. |
| `SEC-B5-03` | BOLA / IDOR | User in Tenant A creates a `ContinuityPlan` referencing Tenant B's `process_id`. | `ResilienceService` verifies `BusinessProcess(id=process_id, organization_id=org_id)` first; raises `404 Not Found`. |
| `SEC-B5-04` | BOLA / IDOR | User in Tenant A creates a `ContinuityPlan` with a `bia_id` belonging to Tenant B or to a different `process_id` in Tenant A. | `ResilienceService` verifies `bia.organization_id == org_id` AND `bia.process_id == process_id` (`404` / `422`). |
| `SEC-B5-05` | BOLA / IDOR | User in Tenant A adds a `ProcessDependency` (`CLOUD_ASSET`) referencing Tenant B's `CloudAsset.id`. | `ResilienceService.add_process_dependency` queries `CloudAsset(id=dep_id, organization_id=org_id)`; raises `404 Not Found`. |
| `SEC-B5-06` | BOLA / IDOR | User in Tenant A adds a `ProcessDependency` (`DATA_ASSET`) referencing Tenant B's `DataAsset.id`. | `ResilienceService.add_process_dependency` queries `DataAsset(id=dep_id, organization_id=org_id)`; raises `404 Not Found`. |
| `SEC-B5-07` | BOLA / IDOR | User in Tenant A calls `GET /api/v1/resilience/processes/{process_id}/bia/active` or `/dependencies` with Tenant B's `process_id`. | Fixed in Batch 5: both endpoints validate `BusinessProcess` existence in `current_user.organization_id` and return `404 Not Found`. |
| `SEC-B5-08` | BOLA / IDOR | User in Tenant A links Tenant B's `EvidenceItem` (`evidence_id`) to a Tenant A `ResilienceExercise`. | `ResilienceService.link_evidence` verifies `EvidenceItem(id=evidence_id, organization_id=org_id)`; raises `404 Not Found`. |
| `SEC-B5-09` | BOLA / IDOR | User in Tenant A escalates or links a `ResilienceExercise` to Tenant B's `finding_id`, `remediation_plan_id`, or `risk_id`. | Service validates all linked IDs against `organization_id == current_user.organization_id` (`404 Not Found`). |
| `SEC-B5-10` | BOLA / IDOR | User in Tenant A attempts to update or delete a `ContinuityRecoveryStep` (`step_id`) belonging to Plan Y via `/plans/{plan_x_id}/steps/{step_id}`. | Service filters `ContinuityRecoveryStep` by `id == step_id`, `continuity_plan_id == plan_x_id`, and `organization_id == org_id` (`404 Not Found`). |
| `SEC-B5-11` | Four-Eyes / SoD | `MANAGER` or `ADMIN` creates a `ContinuityPlan` (`created_by_id = U1`) and calls `POST /plans/{id}/approve` as `U1`. | Blocked in service (`403 Forbidden`) and by DB constraint `chk_continuity_plan_sod`. |
| `SEC-B5-12` | Four-Eyes / SoD | `MANAGER` or `ADMIN` executes a `ResilienceExercise` (`executed_by_id = U1`) and calls `POST /exercises/{id}/review` as `U1`. | Blocked in service (`403 Forbidden`) and by DB constraint `chk_exercise_review_sod`. |
| `SEC-B5-13` | Four-Eyes / SoD | User `U1` plans an exercise (`planned_by_id = U1`), another user starts it, `U1` completes it (`executed_by_id = U1`), and `U1` tries to review it. | `complete_exercise` records `executed_by_id`; `review_exercise` blocks if `current_user.id == executed_by_id` (`403 Forbidden`). |
| `SEC-B5-14` | Four-Eyes / SoD | Creator `U1` updates a `DRAFT` Continuity Plan via another user `U2` and then `U1` tries to approve it as original creator. | `created_by_id` is immutable on `ContinuityPlan`; `U1` remains blocked from approving (`403 Forbidden`). |
| `SEC-B5-15` | RBAC Enforcement | `VIEWER` attempts to create a `ContinuityPlan`, schedule an exercise, or add a dependency. | Blocked by `require_permission(Permission.RESILIENCE_MANAGE)` (`403 Forbidden`). |
| `SEC-B5-16` | RBAC Enforcement | `AUDITOR` attempts to create, edit, execute, or approve any BIA, Continuity Plan, or Exercise. | Blocked by `require_permission` (`403 Forbidden`); `AUDITOR` has `RESILIENCE_READ` only. |
| `SEC-B5-17` | RBAC Enforcement | `SECURITY_ANALYST` attempts to create a `ContinuityPlan` (`RESILIENCE_MANAGE`) or approve a plan/exercise (`RESILIENCE_APPROVE`). | Blocked (`403 Forbidden`); `SECURITY_ANALYST` has `RESILIENCE_READ` and `RESILIENCE_EXECUTE` only. |
| `SEC-B5-18` | RBAC Enforcement | `GRC_ANALYST` attempts to approve a `ContinuityPlan` (`/plans/{id}/approve`) or review/close a `ResilienceExercise` (`/exercises/{id}/review`). | Blocked by `require_permission(Permission.RESILIENCE_APPROVE)` (`403 Forbidden`). |
| `SEC-B5-19` | State Machine Integrity | User attempts to approve a `ContinuityPlan` directly from `DRAFT` without submitting to `UNDER_REVIEW`. | Raises `409 Conflict` (must transition `DRAFT -> UNDER_REVIEW -> APPROVED`). |
| `SEC-B5-20` | State Machine Integrity | User attempts to submit a `ContinuityPlan` (`DRAFT -> UNDER_REVIEW`) that has 0 `ContinuityRecoveryStep` rows. | Raises `422 Unprocessable Entity` ("Continuity plan must contain at least one recovery step before submission"). |
| `SEC-B5-21` | State Machine Integrity | User attempts to modify a `ContinuityPlan` or add/edit/delete a `ContinuityRecoveryStep` when the plan is in `UNDER_REVIEW`, `APPROVED`, `SUPERSEDED`, or `ARCHIVED`. | Raises `409 Conflict` (immutability of non-draft plans). |
| `SEC-B5-22` | State Machine Integrity | User approves version 2 of a `BUSINESS_CONTINUITY_PLAN` for Process X while version 1 is `APPROVED`. | Version 1 is atomically transitioned to `SUPERSEDED` in the same DB transaction; at most one `APPROVED` plan per `(process_id, plan_type)` exists. |
| `SEC-B5-23` | State Machine Integrity | User attempts to schedule a `ResilienceExercise` for a `BusinessProcess` that has no `ACTIVE` `BusinessImpactAnalysis` (or passes a `DRAFT` `bia_id`). | Raises `409 Conflict` ("Resilience exercises require an ACTIVE approved BIA baseline"). |
| `SEC-B5-24` | State Machine Integrity | User attempts to schedule a `ResilienceExercise` linked to a `ContinuityPlan` that is still in `DRAFT` or `ARCHIVED` status. | Raises `409 Conflict` ("Linked continuity plan must be in APPROVED status"). |
| `SEC-B5-25` | State Machine Integrity | User attempts to call `complete_exercise` on a `PLANNED` exercise without calling `start_exercise` (`IN_PROGRESS`). | Raises `409 Conflict`. |
| `SEC-B5-26` | State Machine Integrity | User attempts to call `review_exercise` on an `IN_PROGRESS` or `PLANNED` exercise before `complete_exercise`. | Raises `409 Conflict`. |
| `SEC-B5-27` | State Machine Integrity | User attempts to mutate, re-complete, or cancel a `REVIEWED_CLOSED` or `CANCELLED` exercise. | Raises `409 Conflict` (terminal state immutability). |
| `SEC-B5-28` | Metric Integrity | Client payload attempts to inject fabricated `target_rto_hours`, `rto_variance_hours`, `is_rto_breached`, `exercise_score`, or `exercise_outcome`. | Pydantic create/complete schemas exclude server-authoritative fields; `ResilienceService` computes all targets from the active BIA and all variance/breach/outcome metrics server-side. |
| `SEC-B5-29` | Metric Integrity | Exercise reports `observed_rto_hours = 6.5` against `target_rto_hours = 4.0`, `target_mtd_hours = 24.0`, and client claims exercise passed. | Server deterministically sets `rto_variance_hours = +2.5`, `is_rto_breached = True`, `exercise_outcome = FAILED_RTO_BREACH`. |
| `SEC-B5-30` | Metric Integrity | Exercise reports `observed_rto_hours = 30.0` exceeding `target_mtd_hours = 24.0`. | Server deterministically sets `is_rto_breached = True`, `is_mtd_breached = True`, `exercise_outcome = FAILED_MTD_BREACH`. |
| `SEC-B5-31` | Metric Integrity | Exercise reports negative `observed_rto_hours` or `observed_rpo_hours` (`-1.0`). | Blocked by Pydantic `ge=0.0`, service validation, and DB `CheckConstraint`. |
| `SEC-B5-32` | Governance Gate | Reviewer attempts to close (`REVIEWED_CLOSED`) a failed/breached exercise (`FAILED_RTO_BREACH`, `FAILED_RPO_BREACH`, `FAILED_MTD_BREACH`, `FAILED_EXECUTION`) without a linked `finding_id`/`remediation_plan_id` and with `auto_create_finding=False`. | Raises `422 Unprocessable Entity` ("Failed or breached resilience exercises require a linked Finding/CAPA or auto_create_finding=True before closure"). |
| `SEC-B5-33` | Evidence Integrity | User attempts to link an `EvidenceItem` with status `REJECTED` or `EXPIRED` to a `ContinuityPlan` or `ResilienceExercise`. | Raises `409 Conflict` ("Cannot link REJECTED or EXPIRED evidence item"). |
| `SEC-B5-34` | Evidence Integrity | User attempts to link the same `EvidenceItem` twice to the same `ContinuityPlan` or `ResilienceExercise`. | Raises `409 Conflict` (enforced in service and by `uq_continuity_plan_evidence` / `uq_resilience_exercise_evidence`). |
| `SEC-B5-35` | Evidence Integrity | Payload attempts to create a `ResilienceEvidenceLink` with both `continuity_plan_id` and `exercise_id` set (or neither set). | Blocked by Pydantic validator, service check (`422`), and DB constraint `chk_resilience_evidence_single_target`. |
| `SEC-B5-36` | Duplicate Prevention | User attempts to create two `ContinuityPlan` records with the same `plan_code` in the same tenant, or duplicate `step_order` in the same plan. | Raises `409 Conflict` (enforced in service and by `uq_continuity_plan_org_code` / `uq_continuity_step_plan_order`). |
| `SEC-B5-37` | Duplicate Prevention | User attempts to create two `ResilienceExercise` records with the same `exercise_code` in the same tenant. | Raises `409 Conflict` (`uq_resilience_exercise_org_code`). |
| `SEC-B5-38` | Duplicate Prevention | User attempts to add a duplicate `(process_id, dependency_type, dependency_id)` row in `process_dependencies`. | Raises `409 Conflict` (`uq_process_dependency`). |
| `SEC-B5-39` | Referential Integrity | User attempts to delete an `ACTIVE` `BusinessImpactAnalysis` that is referenced by a `ResilienceExercise`. | Protected by `ForeignKey("business_impact_analyses.id", ondelete="RESTRICT")` and service immutability rules. |
| `SEC-B5-40` | Escalation Idempotency | User calls `POST /exercises/{id}/escalate` multiple times on the same breached exercise to spam duplicate Findings and CAPA plans. | `ResilienceService.escalate_exercise_deficiency` checks if `exercise.remediation_plan_id` / `exercise.finding_id` is already populated and raises `409 Conflict` (or returns existing linked entities idempotently). |
| `SEC-B5-41` | Escalation Gate | User calls `POST /exercises/{id}/escalate` on a `PLANNED` exercise or a `PASSED` exercise with zero breaches. | Raises `409 Conflict` ("Only completed exercises with breaches, observations, or failures can be escalated to Finding/CAPA"). |
| `SEC-B5-42` | Audit Trail Completeness | User deletes a `BusinessProcess` or updates a `DRAFT` BIA via `DELETE /processes/{id}` or `PUT /bia/{id}`. | Fixed in Batch 5: routed through `ResilienceService` and writes `BUSINESS_PROCESS_DELETED` and `BIA_UPDATED` `AuditLog` entries. |
| `SEC-B5-43` | Cross-Tenant Spoofing | Payload includes `organization_id: 999`, `created_by_id: 999`, or `approved_by_id: 999` in JSON body. | Ignored/rejected by Pydantic schemas; actor and tenant IDs are bound exclusively from `current_user`. |
| `SEC-B5-44` | Dependency Health Spoofing | Client attempts to override calculated `process_resilience_readiness_score` or `dependency_health_score`. | Readiness scores are computed dynamically on the server from live `BusinessImpactAnalysis`, `ContinuityPlan`, `ResilienceExercise`, and target dependency tables. |
| `SEC-B5-45` | Executive Telemetry Regression | Existing Phase 20 executive telemetry tests run with zero `BusinessProcess` rows. | `ExecutiveService` preserves exact `incidents_resilience` score formula when `process_count == 0`, preventing any regression in existing tests while blending resilience readiness when `process_count > 0`. |

---

## 31. Adversarial Test Matrix

- **ARCHITECTURAL DECISION**: Batch 5 will be verified by a dedicated test suite `backend/tests/test_batch5_resilience_continuity_governance.py` containing at least 50 tests mapped directly to `SEC-B5-01`..`SEC-B5-45`, plus full regression across the existing 1,139 backend tests:
  1. **Continuity Plan & Recovery Step Lifecycle Tests (12 tests)**:
     - Create `DRAFT` plan, version auto-increment per `(process_id, plan_type)`, add/update/delete `ContinuityRecoveryStep`, duplicate `plan_code` (`409`), duplicate `step_order` (`409`), block submission with 0 steps (`422`), submit `DRAFT -> UNDER_REVIEW`, reject `UNDER_REVIEW -> DRAFT`, Four-Eyes self-approval blocked (`403`), independent `MANAGER` approval (`UNDER_REVIEW -> APPROVED`), automatic superseding of prior `APPROVED` plan (`-> SUPERSEDED`), immutability of `APPROVED`/`SUPERSEDED`/`ARCHIVED` plans and their steps (`409`).
  2. **Resilience Exercise Lifecycle & Deterministic RTO/RPO Math Tests (14 tests)**:
     - Block exercise creation without `ACTIVE` BIA (`409`) or with `DRAFT` Continuity Plan (`409`); verify server-side snapshot of `target_rto_hours`, `target_rpo_hours`, `target_mtd_hours`; start exercise (`PLANNED -> IN_PROGRESS`); complete with `PASSED`, `PASSED_WITH_OBSERVATIONS`, `FAILED_RTO_BREACH`, `FAILED_RPO_BREACH`, `FAILED_MTD_BREACH`, `FAILED_EXECUTION`; verify exact `rto_variance_hours`, `rpo_variance_hours`, `exercise_score`, and breach booleans; Four-Eyes self-review blocked (`403`); block closure of failed exercise without Finding/CAPA (`422`); independent review with `auto_create_finding=True` (`-> REVIEWED_CLOSED`); reopen rejected exercise (`-> IN_PROGRESS`); terminal immutability of `REVIEWED_CLOSED` and `CANCELLED` (`409`).
  3. **Closed-Loop Escalation & Evidence Integration Tests (8 tests)**:
     - Escalate breached exercise to Phase 4 `Finding` + Phase 11 `RemediationPlan` (CAPA) (`source_type=FINDING`); block duplicate escalation (`409`); block escalation on `PASSED`/`PLANNED` exercise (`409`); link `ACCEPTED` `EvidenceItem` to `ContinuityPlan` and `ResilienceExercise`; block `REJECTED`/`EXPIRED` evidence (`409`); block duplicate evidence link (`409`).
  4. **Expanded Cross-Domain Process Dependencies & Readiness Posture Tests (8 tests)**:
     - Add `VENDOR`, `CONTROL`, `CLOUD_ASSET`, and `DATA_ASSET` dependencies with `is_single_point_of_failure=True`; verify live dependency health degradation when a linked `CloudAsset` is `NON_COMPLIANT`, `OrganizationControl` is `NOT_STARTED`, `Vendor` is `CRITICAL` risk band, or `DataAsset` is unapproved; verify deterministic `calculate_process_resilience_readiness` and `calculate_tenant_resilience_posture`; verify `ExecutiveService.calculate_live_telemetry` integration.
  5. **BOLA / IDOR, RBAC Across All 6 Roles & Phase 13 Hygiene Fix Tests (10 tests)**:
     - Cross-tenant BOLA checks returning `404` on plans, steps, exercises, dependencies (`CLOUD_ASSET`, `DATA_ASSET`), evidence links, `get_active_bia`, and `list_process_dependencies`; RBAC matrix verification across `ADMIN`, `MANAGER`, `GRC_ANALYST`, `SECURITY_ANALYST`, `AUDITOR`, and `VIEWER`; audit log verification for `BUSINESS_PROCESS_DELETED`, `BIA_UPDATED`, and all new Batch 5 actions.

---

## 32. Implementation File Inventory

- **ARCHITECTURAL DECISION**: During the subsequent Batch 5 Implementation phase, only the following files will be created or modified:

| File Path | Action | Scope of Changes |
| :--- | :--- | :--- |
| `backend/alembic/versions/0026_operational_resilience_continuity_and_testing.py` | **CREATE** | Alembic migration `0026` (down_revision `0025`) adding `continuity_plans`, `continuity_recovery_steps`, `resilience_exercises`, `resilience_evidence_links`, and extending `process_dependencies`. |
| `backend/app/models/resilience.py` | **MODIFY** | Add new enums (`ContinuityPlanTypeEnum`, `ContinuityPlanStatusEnum`, `ResilienceExerciseTypeEnum`, `ResilienceExerciseStatusEnum`, `ResilienceExerciseOutcomeEnum`, `ResilienceEvidenceTargetTypeEnum`), extend `DependencyTypeEnum` (`CLOUD_ASSET`, `DATA_ASSET`) and `ProcessDependency`, and add `ContinuityPlan`, `ContinuityRecoveryStep`, `ResilienceExercise`, `ResilienceEvidenceLink`. |
| `backend/app/models/__init__.py` | **MODIFY** | Export the new resilience models and enums. |
| `backend/app/core/permissions.py` | **MODIFY** | Add `Permission.RESILIENCE_EXECUTE = "resilience:execute"` and grant to `ADMIN`, `MANAGER`, `GRC_ANALYST`, `SECURITY_ANALYST`. |
| `backend/app/schemas/resilience.py` | **MODIFY** | Add Pydantic v2 schemas for Continuity Plans, Recovery Steps, Resilience Exercises, Escalation requests, Evidence Links, Process Readiness, and Tenant Resilience Posture. |
| `backend/app/services/resilience_service.py` | **MODIFY** | Implement Continuity Plan lifecycle, Recovery Step management, Exercise lifecycle & deterministic RTO/RPO variance math, Closed-Loop Finding/CAPA escalation, Evidence linking, extended `CLOUD_ASSET`/`DATA_ASSET` dependency validation, readiness scoring, and audit logging on `delete_business_process` and `update_draft_bia`. |
| `backend/app/api/v1/endpoints/resilience.py` | **MODIFY** | Route existing delete/update/active-bia/dependencies handlers through `ResilienceService` with tenant validation and add the 24 Batch 5 endpoints. |
| `backend/app/services/executive_service.py` | **MODIFY** | Connect `ResilienceService.calculate_tenant_resilience_posture` into `incidents_resilience` when `BusinessProcess` records exist while preserving 100% backward compatibility when `process_count == 0`. |
| `frontend/src/types/index.ts` | **MODIFY** | Add TypeScript interfaces for `ContinuityPlan`, `ContinuityRecoveryStep`, `ResilienceExercise`, `ResilienceEvidenceLink`, `ProcessResilienceReadiness`, and `TenantResiliencePosture`. |
| `frontend/src/lib/resilienceService.ts` | **MODIFY** | Add typed API client methods for all new `/api/v1/resilience` endpoints. |
| `frontend/src/pages/ResiliencePage.tsx` | **MODIFY** | Add Continuity & DR Plans tab, Recovery Exercises & DR Testing tab, and live Resilience Readiness & SPOF posture KPIs. |
| `frontend/src/pages/BusinessProcessDetailPage.tsx` | **MODIFY** | Add Continuity Plan & Recovery Steps management, Exercise scheduling/execution/review/escalation workflows, Evidence binding, and `CLOUD_ASSET`/`DATA_ASSET` SPOF dependency controls. |
| `backend/tests/test_batch5_resilience_continuity_governance.py` | **CREATE** | Comprehensive adversarial test suite (50+ tests covering `SEC-B5-01`..`SEC-B5-45`). |

---

## 33. Dependency Impact

- **REPOSITORY FACT**: Batch 5 requires **zero** new Python packages in `backend/requirements.txt` and **zero** new npm packages in `frontend/package.json`. All calculations use Python's standard library (`datetime`, `math`, `enum`) and SQLAlchemy 2.x.

---

## 34. Backward Compatibility

- **ARCHITECTURAL DECISION**:
  1. All existing columns, relationships, and constraints on `business_processes`, `business_impact_analyses`, and `process_dependencies` are preserved.
  2. All 14 existing endpoints under `/api/v1/resilience` preserve their URL paths, HTTP methods, request schemas, and response schemas.
  3. New columns on `process_dependencies` (`is_single_point_of_failure`, `criticality_impact`, `updated_at`) have sensible server and Pydantic defaults (`False`, `TIER_2`, `now_utc`) so existing callers of `POST /api/v1/resilience/dependencies` continue to work without modification.
  4. `ExecutiveService.calculate_live_telemetry` preserves exact output values when `BusinessProcess` count is 0, ensuring zero regressions in existing Phase 20 executive test suites.

---

## 35. Batch Boundary

- **ARCHITECTURAL DECISION**: Batch 5 begins at frozen commit `812a18342ff6cec90b31264f1828a60a18bdc57b` (Alembic head `0025`) and will conclude with a single atomic commit advancing Alembic head to `0026`, implementing `RESILIENCE-CONTINUITY-GRC` end-to-end across database migration, SQLAlchemy models, permissions, Pydantic schemas, service layer, FastAPI endpoints, React TypeScript UI, and adversarial pytest suite.

---

## 36. Open Questions

- **OPEN QUESTION**: None. All architectural boundaries, state transitions, Four-Eyes rules, RBAC permissions, cross-module foreign keys, and deterministic formulas are fully resolved from repository facts.

---

## 37. Final Recommendation

- **ARCHITECTURAL DECISION**: Proceed immediately to **Batch 5 Hardening & Implementation** for **Operational Resilience Continuity Planning, DR Exercise Testing & Empirical RTO/RPO Assurance (`RESILIENCE-CONTINUITY-GRC`)** on top of frozen baseline `812a18342ff6cec90b31264f1828a60a18bdc57b` (Alembic revision `0025` -> `0026`).

**BATCH 5 ARCHITECTURE DISCOVERY COMPLETE — GO TO HARDENING.**
