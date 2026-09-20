# CONTROLSPHERE — PHASE 24+ ARCHITECTURE DISCOVERY & EXPANSION BLUEPRINT

---

## 1. Executive Summary

ControlSphere has successfully achieved a milestone in enterprise cybersecurity Governance, Risk, and Compliance (GRC). With **Phases 1 through 23 fully implemented, tested (925 backend regression tests passing, 0 failures), and committed**, the platform possesses foundational controls, multi-framework harmonization, evidence lifecycle, qualitative and quantitative risk modeling, operational resilience, vulnerability exposure, AI governance, privacy RoPA/DPIA, SBOM supply-chain analysis, cloud security posture (CSPM), identity governance (IGA), executive board reporting, regulatory intelligence, automated evidence collection pipelines, and continuous multi-vector assurance.

The objective of this architectural discovery is to evaluate the current ground truth of the ControlSphere codebase, map all authoritative domain engines, identify remaining enterprise capability gaps, and present a rigorous, defensible architectural blueprint for the next major vertical engineering phase (**Phase 24: Enterprise Policy Lifecycle & Workforce Attestation Governance** and its natural companions).

---

## 2. Repository Ground Truth

### Git Baseline
- **Current HEAD Commit**: `ef34526fb6ab387a3eaafbb2a22c1485666b7626` (`ef34526`)
- **Commit Message**: `feat(phases20-23): implement executive regulatory integration and continuous grc`
- **Current Branch**: `main` (`HEAD == origin/main`)
- **Working Tree State**: Clean (0 unstaged changes, 0 staged changes)

### Database & Migration Status
- **Current Alembic Head**: `0020_regulatory_integration_continuous_grc` (`0020`)
- **Migration Lineage**: Linear from `0001` through `0020` without branching or split heads
- **Total Persistent Tables**: 72 database tables across all 23 domains

### Verification Baseline
- **Backend Test Suite**: **925 tests passing, 0 failures, 0 errors** (`pytest -q`)
- **Adversarial Security Test Suites**: 23 dedicated phase security test files (including `test_phase20_adversarial_security.py`, `test_phase21_adversarial_security.py`, `test_phase22_adversarial_security.py`, `test_phase23_adversarial_security.py`)
- **Frontend Production Build**: `npm run build` (`tsc -b && vite build`) passing cleanly with 0 TypeScript errors

---

## 3. Current Architecture

ControlSphere operates on a modern, decoupled client-server architecture strictly enforcing **Server Authority**, **Multi-Tenancy**, **Granular RBAC**, and **Four-Eyes Segregation of Duties (SoD)**:

```
[ Frontend: React 19 + TypeScript + Vite + TailwindCSS ]
                           │  (HTTPS / JWT Bearer)
                           ▼
[ Backend API: FastAPI + Pydantic v2 + OAuth2 / Permissions ]
                           │
      ┌────────────────────┼────────────────────┐
      ▼                    ▼                    ▼
[ Domain Services ]  [ Security/SSRF/AES ]  [ Audit Logger ]
      │                    │                    │
      └────────────────────┼────────────────────┘
                           ▼
[ Data Layer: SQLAlchemy 2.0 ORM + Alembic Migrations + PostgreSQL / SQLite ]
```

### Core Architectural Invariants
1. **Multi-Tenant Isolation**: Every query and mutation is strictly scoped to `organization_id` derived exclusively from the authenticated JWT session context. Cross-tenant queries return HTTP 404.
2. **Exactly Six Platform Roles**: `ADMIN`, `MANAGER`, `GRC_ANALYST`, `SECURITY_ANALYST`, `AUDITOR`, `VIEWER`. No role expansion or client-side elevation.
3. **Deterministic Mathematical Authority**: All scores (CCM health, residual risk, ALE, ROSI, SCEI, CSPM posture, SoD risk, unified assurance) are computed exclusively server-side.
4. **Four-Eyes Segregation of Duties**: Requesters, creators, and uploaders cannot review, approve, verify, or close their own records (`created_by_id != approved_by_id`).
5. **No Autonomous AI Compliance Decisions**: AI assistance (Phase 15 and future copilot capabilities) is strictly advisory and human-in-the-loop.

---

## 4. Authority Matrix

| Domain / Capability | Authoritative Table(s) | Authoritative Service | State Machine / Lifecycle | Authoritative Metric / Formula | Authoritative API Router |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Frameworks** | `frameworks`, `framework_functions`, `framework_categories`, `framework_subcategories` | `FrameworkService` | Hierarchical catalog | Structure counts & versioning | `/api/v1/frameworks` |
| **Organization Controls** | `organization_controls` | `ControlService` | `NOT_STARTED` $\rightarrow$ `IN_PROGRESS` $\rightarrow$ `IMPLEMENTED` $\rightarrow$ `DEPRECATED` | Implementation & priority weighting | `/api/v1/controls` |
| **Evidence & Review** | `evidence_items`, `evidence_reviews`, `evidence_requirements` | `EvidenceService` | `UPLOADED` $\rightarrow$ `ACCEPTED` / `REJECTED` / `SUPERSEDED` | Four-Eyes human verification | `/api/v1/evidence` |
| **Assessments** | `assessments`, `assessment_questions`, `assessment_responses` | `AssessmentService` | `DRAFT` $\rightarrow$ `IN_PROGRESS` $\rightarrow$ `SUBMITTED` $\rightarrow$ `COMPLETED` | Weighted compliance score | `/api/v1/assessments` |
| **Findings** | `findings` | `FindingService` | `OPEN` $\rightarrow$ `IN_REMEDIATION` $\rightarrow$ `RESOLVED` $\rightarrow$ `CLOSED` | Severity & SLA breach tracking | `/api/v1/findings` |
| **Qualitative Risk** | `risks`, `risk_history` | `RiskService` | `IDENTIFIED` $\rightarrow$ `ASSESSED` $\rightarrow$ `TREATED` $\rightarrow$ `ACCEPTED` $\rightarrow$ `CLOSED` | $R_{\text{residual}} = I \times L \times (1 - \text{attenuation})$ | `/api/v1/risks` |
| **Exceptions** | `exception_requests` | `ExceptionService` | `REQUESTED` $\rightarrow$ `APPROVED` / `REJECTED` $\rightarrow$ `EXPIRED` | Compensating control score | `/api/v1/exceptions` |
| **Audit Management** | `audit_engagements`, `audit_procedures` | `AuditEngagementService` | `PLANNING` $\rightarrow$ `FIELDWORK` $\rightarrow$ `REVIEW` $\rightarrow$ `REPORTING` $\rightarrow$ `CLOSED` | Audit readiness index | `/api/v1/audits` |
| **Continuous Control Monitoring** | `control_health_snapshots`, `compliance_drift_alerts` | `MonitoringService` | `HEALTHY` $\rightarrow$ `WARNING` $\rightarrow$ `CRITICAL` | Metric stream health formula | `/api/v1/monitoring` |
| **Harmonization** | `rationalized_common_controls`, `framework_crosswalks` | `HarmonizationService` | Active / Archived crosswalks | Common control overlap coverage | `/api/v1/harmonization` |
| **Third-Party Risk (TPRM)** | `vendors`, `vendor_engagements`, `vendor_assessments` | `TPRMService` | `ONBOARDING` $\rightarrow$ `ACTIVE` $\rightarrow$ `UNDER_REVIEW` $\rightarrow$ `OFFBOARDED` | Inherent Tier & Residual Vendor Risk | `/api/v1/vendors` |
| **Incident Management** | `security_incidents`, `materiality_assessments` | `IncidentService` | `TRIAGE` $\rightarrow$ `CONTAINMENT` $\rightarrow$ `REMEDIATED` $\rightarrow$ `CLOSED` | SEC Materiality & SLA tracking | `/api/v1/incidents` |
| **Remediation & CAPA (ROC-V)** | `remediation_plans`, `remediation_actions`, `retest_records` | `RemediationService` | `DRAFT` $\rightarrow$ `APPROVED` $\rightarrow$ `IN_EXECUTION` $\rightarrow$ `READY_FOR_RETEST` $\rightarrow$ `CLOSED` | REI, TTR, SLA performance | `/api/v1/remediations` |
| **Quantitative Risk (QUANTUM)** | `quantitative_risk_scenarios`, `fair_simulation_runs` | `QuantumGRCService` | Monte Carlo / FAIR simulation engine | Expected Loss ($ALE$), $VaR_{95\%}$, $ROSI$ | `/api/v1/quant-risk` |
| **Operational Resilience** | `business_processes`, `business_impact_assessments` | `ResilienceService` | `DRAFT` $\rightarrow$ `ACTIVE` $\rightarrow$ `SUPERSEDED` | Outage Loss $= \text{Fixed} + (\text{Hourly} \times t)$ | `/api/v1/resilience` |
| **Threat Exposure** | `vulnerability_exposures`, `exposure_exemptions` | `ExposureService` | `ACTIVE` $\rightarrow$ `MITIGATED` $\rightarrow$ `EXEMPTED` $\rightarrow$ `REMEDIATED` | CVSS, EPSS probability, KEV multiplier | `/api/v1/exposure` |
| **AI Governance** | `ai_governance_systems`, `ai_model_cards` | `AIGovernanceService` | `ASSESSMENT` $\rightarrow$ `APPROVED` $\rightarrow$ `PRODUCTION` $\rightarrow$ `DECOMMISSIONED` | EU AI Act Risk Tiering & Model Governance | `/api/v1/ai-governance` |
| **Privacy Governance** | `privacy_assets`, `ropa_processing_activities`, `dpia_assessments` | `PrivacyService` | `DRAFT` $\rightarrow$ `DPO_REVIEWED` $\rightarrow$ `APPROVED` | Privacy Risk Index & RoPA mapping | `/api/v1/privacy` |
| **Supply Chain (SBOM)** | `software_products`, `sbom_components`, `license_policies` | `SupplyChainService` | `DEVELOPMENT` $\rightarrow$ `ACTIVE` $\rightarrow$ `DEPRECATED` $\rightarrow$ `RETIRED` | Supply Chain Exploitability Index ($SCEI$) | `/api/v1/supply-chain` |
| **Cloud Security (CSPM)** | `cloud_assets`, `benchmark_rules`, `cloud_security_findings` | `CloudSecService` | `PENDING` $\rightarrow$ `ACTIVE` $\rightarrow$ `DECOMMISSIONED` | CSPM Compliance Rate & Severity Scoring | `/api/v1/cloud-security` |
| **Identity Governance (IGA)**| `governed_identities`, `certification_campaigns`, `sod_policies` | `IdentityGovernanceService` | Certification & JIT approval lifecycles | SoD Conflict Index & Certification Progress | `/api/v1/identity-governance` |
| **Executive GRC** | `executive_snapshots`, `executive_dossiers`, `executive_briefings` | `ExecutiveService` | `DRAFT` $\rightarrow$ `COMPILED` $\rightarrow$ `FINALIZED` | Deterministic SHA-256 JSON forensic hash | `/api/v1/executive` |
| **Regulatory Intelligence** | `regulatory_sources`, `regulatory_mandates`, `regulatory_change_events` | `RegulatoryService` | `STAGED` $\rightarrow$ `REVIEWED` $\rightarrow$ `APPROVED` | Content SHA-256 deduplication & gap analysis | `/api/v1/regulatory` |
| **Integrations & Pipelines**| `integration_connections`, `integration_credentials`, `evidence_collection_jobs` | `IntegrationService` | Scheduled collection & run lifecycle | AES-128-CBC + HMAC-SHA256 & SSRF validator | `/api/v1/integrations` |
| **Continuous Assurance** | `continuous_compliance_profiles`, `compliance_drift_records`, `continuous_assurance_snapshots` | `ContinuousComplianceService` | Drift detection & CAPA triggering | 6-Pillar Composite Assurance Score ($0.25 C + 0.20 E + 0.15 R + 0.15 S + 0.15 I + 0.10 H$) | `/api/v1/continuous-compliance` |

---

## 5. Completed Phase Inventory

- **Phases 1–6 (Core GRC & Audit)**: Multi-tenant auth, NIST/ISO controls, evidence review, assessments, risks, audit engagements.
- **Phases 7–11 (Monitoring, Harmonization & CAPA)**: Continuous control monitoring, multi-framework rationalization, vendor risk (TPRM), incident response & materiality, authoritative CAPA remediation (ROC-V).
- **Phases 12–17 (Advanced Quantitative & Domain Governance)**: FAIR/Monte Carlo quantification, business resilience (BIA), vulnerability exposure (CVE/EPSS), AI governance (EU AI Act), privacy (RoPA/DPIA), supply chain SBOM.
- **Phases 18–19 (Technical Infrastructure Security)**: Cloud CSPM & IAM governance, Identity Governance & Administration (IGA/SoD).
- **Phases 20–23 (Executive, Regulatory & Continuous GRC)**: Executive board telemetry & PDF dossiers, regulatory intelligence & mandate obligations, automated collection pipelines with encrypted credentials, continuous assurance & multi-vector drift.

---

## 6. Existing Domain Dependency Map

```
                     ┌─────────────────────────────┐
                     │   Phase 20: Executive GRC   │
                     └──────────────┬──────────────┘
                                    │ (aggregates)
                     ┌──────────────▼──────────────┐
                     │ Phase 23: Continuous GRC    │
                     └──────────────┬──────────────┘
            ┌───────────────────────┼───────────────────────┐
            │                       │                       │
┌───────────▼──────────┐ ┌──────────▼──────────┐ ┌──────────▼──────────┐
│ Phase 21: Regulatory │ │ Phase 22: Pipeline  │ │  Phase 7: CCM Health │
└───────────┬──────────┘ └──────────┬──────────┘ └──────────┬──────────┘
            │                       │                       │
            │                       ▼                       │
            │            ┌─────────────────────┐            │
            │            │ Phase 3: Evidence   │            │
            │            └──────────┬──────────┘            │
            │                       │                       │
            └───────────────────────┼───────────────────────┘
                                    ▼
                     ┌─────────────────────────────┐
                     │ Phase 2: Controls & Policies│
                     └──────────────┬──────────────┘
            ┌───────────────────────┼───────────────────────┐
            ▼                       ▼                       ▼
┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
│  Phase 11: CAPA     │ │ Phase 18: CloudSec  │ │ Phase 19: Identity  │
└─────────────────────┘ └─────────────────────┘ └─────────────────────┘
```

---

## 7. Current Architectural Gaps

Despite the immense depth of ControlSphere's technical and operational modules, an architectural discovery of the actual repository reveals three distinct enterprise-grade operational gaps:

1. **Policy Lifecycle & Workforce Attestation Gap**:
   - [`backend/app/models/policy.py`](file:///e:/PROJECT%20WORKSPACE%202/ControlSphere/backend/app/models/policy.py) remains a basic Phase 2 CRUD entity.
   - It lacks formal policy drafting, multi-stakeholder legal/CISO review, version lineage diffing, target group distribution, and mandatory employee read-and-attest acknowledgments required by SOC 2 Type II, ISO 27001 (A.5), and HIPAA.
2. **Audit Sampling & Fieldwork Execution Gap**:
   - Phase 6 [`audit_engagement.py`](file:///e:/PROJECT%20WORKSPACE%202/ControlSphere/backend/app/models/audit_engagement.py) defines engagement scopes and procedures, but lacks formal Test of Design (ToD) / Test of Operating Effectiveness (ToE) workpapers, mathematical sample selection (e.g., 25/45 item populations), and an interactive PBC (Provided By Client) request tracker.
3. **Enterprise Key Risk Indicators (KRIs) & Appetite Thresholds Gap**:
   - Phase 5 `Risk` and Phase 12 `QuantumGRC` model static and Monte Carlo loss distributions, but lack real-time KRI telemetry binding with automated yellow/red threshold triggers that dynamically alter residual risk or prompt board escalations.

---

## 8. Five Next-Phase Candidates

### Candidate 1: Phase 24 — Policy Lifecycle Management & Workforce Attestation Governance (`POLICY-ATTESTATION-GRC`)
- **Objective**: Expand the policy domain into an enterprise policy lifecycle engine with multi-stage legal approval, version branching, target employee distribution campaigns, mandatory read-and-attest workflows with comprehension verification, and non-compliance escalations.
- **Value**: Directly satisfies major audit requirements for workforce policy governance and turns policy compliance into auditable Phase 3 evidence.

### Candidate 2: Phase 24 — Enterprise Audit Fieldwork, Sampling & PBC Collaboration Portal (`AUDIT-OPS-GRC`)
- **Objective**: Extend Phase 6 audit management into a fieldwork execution system: population sampling engines, ToD/ToE testing workpapers, PBC request assignment with external auditor workspaces.
- **Value**: Reduces audit fatigue and enables external auditors (`AUDITOR` role) to execute fieldwork directly within ControlSphere without out-of-band spreadsheets.

### Candidate 3: Phase 24 — Dynamic Key Risk Indicators & Risk Appetite Governance (`KRI-METRICS-GRC`)
- **Objective**: Establish organizational risk appetite bands (Green/Amber/Red) and connect automated KRI telemetry feeds from CSPM, IGA, Findings, and CCM into continuous risk threshold monitoring.
- **Value**: Provides board-level early warnings before residual risks breach corporate risk appetite.

### Candidate 4: Phase 24 — Enterprise Data Asset Inventory, Classification & Lineage Governance (`DATA-ASSET-GRC`)
- **Objective**: Unified inventory of physical, cloud, and SaaS data assets with sensitivity tiering (PII, PHI, Secret, Public), retention scheduling, and cryptographic protection tagging.
- **Value**: Unifies Phase 16 Privacy, Phase 18 CloudSec, and Phase 2 Controls into an authoritative enterprise data asset dictionary.

### Candidate 5: Phase 24 — Governed AI GRC Copilot & Natural Language Reasoning Oversight (`AI-ANALYST-GRC`)
- **Objective**: Fulfill the `/ai-analyst` navigation route with an assistive, LLM-powered compliance reasoning assistant providing control mapping suggestions, gap analysis explanations, and audit preparation guidance—operating strictly under advisory, human-in-the-loop governance.
- **Value**: Accelerates analyst productivity while strictly enforcing the platform's non-autonomous AI invariant.

---

## 9. Candidate Comparison Matrix

| Candidate | Enterprise Value | Existing Engines Reused | New DB Tables | Four-Eyes SoD Impact | Risk of Duplicating Engines | Migration Risk |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1. Policy Lifecycle & Attestation** | **CRITICAL (High)** | `Policy`, `User`, `EvidenceItem`, `Exception` | 4 tables | Mandatory (Legal Approval) | **NONE** (Extends Phase 2) | **Very Low** |
| **2. Audit Fieldwork & Sampling** | **High** | `AuditEngagement`, `EvidenceItem`, `Finding` | 5 tables | Mandatory (Workpaper Review) | Low | Low |
| **3. KRI & Risk Appetite** | Medium-High | `Risk`, `QuantScenario`, `CCM`, `CloudFinding` | 4 tables | Moderate | Low | Low |
| **4. Data Asset & Classification** | Medium | `PrivacyAsset`, `CloudAsset`, `OrganizationControl` | 4 tables | Low | Medium (Overlaps Privacy/Cloud) | Moderate |
| **5. Governed AI Copilot** | Medium | `AIGovernanceSystem`, `AuditLog` | 2 tables | N/A (Advisory only) | Low | Very Low |

---

## 10. Recommended Next Phase

### **PHASE 24: ENTERPRISE POLICY LIFECYCLE & WORKFORCE ATTESTATION GOVERNANCE (`POLICY-ATTESTATION-GRC`)**

---

## 11. Why This Phase Should Be Next

1. **Foundational Maturity Requirement**: Every major cybersecurity framework (NIST CSF 2.0 GV.PO, ISO 27001:2022 A.5.1, SOC 2 CC5.2/CC5.3, HIPAA §164.308) mandates not only that policies exist, but that they undergo **formal lifecycle governance** and **documented workforce distribution and attestation**.
2. **Zero Architecture Duplication**: Phase 2 established [`Policy`](file:///e:/PROJECT%20WORKSPACE%202/ControlSphere/backend/app/models/policy.py) as an authoritative entity. Phase 24 naturally builds upon it by adding version lineage, review/approval lifecycles, distribution campaigns, and user attestation records.
3. **Direct Feed into Phase 3 & Phase 23**: Completed attestation campaigns automatically deposit verified attestation certificates into the Phase 3 [`EvidenceItem`](file:///e:/PROJECT%20WORKSPACE%202/ControlSphere/backend/app/models/evidence.py) repository and feed into Phase 23's Evidence Pipeline pillar.
4. **Clean Scope & Minimal Complexity**: It cleanly delivers immense enterprise governance value in a single vertical implementation block without risking schema conflicts or unbounded foreign dependencies.

---

## 12. Detailed Proposed Architecture (Phase 24)

```
[ Phase 2: Policy (Authoritative) ]
                 │
                 ├── [ 1. PolicyVersion ] (Immutable SHA-256 Markdown Snapshots)
                 │
                 ├── [ 2. PolicyReviewWorkflow ] (Four-Eyes Drafting -> Legal/CISO Sign-off)
                 │
                 └── [ 3. AttestationCampaign ] (Target Group Distribution & Deadlines)
                               │
                               ▼
                     [ 4. UserAttestationRecord ] (Cryptographic Sign-off & Comprehension)
                               │
                               ▼ (Deposits automated evidence)
                     [ Phase 3: EvidenceItem (UPLOADED) ]
```

---

## 13. Entity/Table Proposal (Migration 0021)

Exactly **4 new persistent tables**:

1. `policy_versions`:
   - `id`, `organization_id`, `policy_id` (FK `policies.id`), `version_number` (e.g. "1.0", "1.1", "2.0"), `title`, `content_markdown`, `content_hash_sha256`, `change_summary`, `effective_date`, `created_by_id` (FK `users.id`), `created_at`.
   - Unique: `(organization_id, policy_id, version_number)`.
2. `policy_review_workflows`:
   - `id`, `organization_id`, `policy_id`, `version_id`, `status` (`DRAFT`, `LEGAL_REVIEW`, `SECURITY_REVIEW`, `EXECUTIVE_APPROVAL`, `APPROVED`, `REJECTED`), `assigned_reviewer_id` (FK `users.id`), `review_notes`, `approved_by_id`, `approved_at`, `created_by_id`, `created_at`.
3. `policy_attestation_campaigns`:
   - `id`, `organization_id`, `campaign_code`, `title`, `policy_id`, `version_id`, `target_role` (Optional Role filter), `due_date`, `status` (`SCHEDULED`, `ACTIVE`, `COMPLETED`, `CANCELLED`), `total_targeted_count`, `completed_count`, `created_by_id`, `created_at`.
4. `user_attestation_records`:
   - `id`, `organization_id`, `campaign_id` (FK `policy_attestation_campaigns.id`), `policy_id`, `user_id` (FK `users.id`), `status` (`PENDING`, `ATTESTED`, `OVERDUE`), `attested_at`, `ip_address`, `user_agent`, `signature_sha256`, `evidence_item_id` (FK `evidence_items.id`).
   - Unique: `(organization_id, campaign_id, user_id)`.

---

## 14. Backend Service Proposal

- `PolicyLifecycleService`:
  - `create_policy_version(db, org_id, policy_id, version_in, user_id)`
  - `submit_policy_for_review(db, org_id, policy_id, reviewer_id, user_id)`
  - `approve_policy_version(db, org_id, review_id, approve_in, approver_id)` — *Enforces Four-Eyes: `created_by_id != approver_id`*.
  - `publish_policy_version(db, org_id, policy_id, version_id, user_id)`
- `PolicyAttestationService`:
  - `create_attestation_campaign(db, org_id, campaign_in, user_id)`
  - `record_user_attestation(db, org_id, campaign_id, user_id, ip_address, user_agent)` — *Generates digital signature and deposits `EvidenceItem` in `UPLOADED` status*.
  - `get_campaign_telemetry(db, org_id, campaign_id)`

---

## 15. API Proposal

- `GET /api/v1/policies/{id}/versions`
- `POST /api/v1/policies/{id}/versions`
- `POST /api/v1/policies/{id}/reviews/{review_id}/approve`
- `POST /api/v1/policies/campaigns`
- `GET /api/v1/policies/campaigns`
- `GET /api/v1/policies/campaigns/{id}`
- `POST /api/v1/policies/campaigns/{id}/attest` (Self-service user attestation)
- `GET /api/v1/policies/my-pending-attestations` (Personal employee inbox)

---

## 16. Permission Proposal

Add to [`backend/app/core/permissions.py`](file:///e:/PROJECT%20WORKSPACE%202/ControlSphere/backend/app/core/permissions.py):
- `POLICY_REVIEW = "policy:review"`
- `POLICY_APPROVE = "policy:approve"`
- `POLICY_ATTEST = "policy:attest"` (Granted to all active roles including `VIEWER`)
- `POLICY_CAMPAIGN_MANAGE = "policy:campaign_manage"`

---

## 17. Four-Eyes / SoD Model

- **Policy Approvals**: A user who created or authored a policy version draft cannot act as the approving CISO or legal counsel (`policy_version.created_by_id != workflow.approved_by_id`).
- **Attestation Sign-off**: User attestation is strictly personal (`user_id == current_user.id`). Administrators cannot sign attestations on behalf of employees without explicit audit flagging.

---

## 18. Tenant Isolation Model

- All policy versions, workflows, campaigns, and attestation records are strictly partitioned by `organization_id`.
- Cross-tenant campaign lookups or attestation submissions return HTTP 404.

---

## 19. Audit / Non-Repudiation Model

- When an employee attests to a policy, a SHA-256 digital signature is computed from:
  $$\text{Signature} = \text{SHA256}(\text{org\_id} \parallel \text{user\_id} \parallel \text{policy\_hash} \parallel \text{timestamp} \parallel \text{ip\_address})$$
- Emits structured `AuditLog` action `USER_POLICY_ATTESTATION`.

---

## 20. Deterministic Calculation Model

- Campaign completion rate:
  $$\text{Attestation Rate} = \frac{\text{completed\_count}}{\text{total\_targeted\_count}} \times 100\%$$
- Feeds directly into Phase 23 Evidence Pipeline pillar freshness score.

---

## 21. Cross-Module Integration Map

- **Phase 2 (Controls)**: Policies link to controls via existing `organization_controls`.
- **Phase 3 (Evidence)**: Completed attestation campaigns deposit summary compliance manifests into `evidence_items` in `UPLOADED` status.
- **Phase 5 (Exceptions)**: Policy exception requests link directly to specific `policy_versions`.
- **Phase 20 (Executive)**: Policy attestation completion percentages feed executive governance dossiers.
- **Phase 23 (Continuous)**: Active policy compliance gaps influence continuous assurance posture.

---

## 22. Frontend Information Architecture

1. **Policy Detail Page (`/policies/:id`)**:
   - Version history tab with visual markdown diffing.
   - Review & approval workflow status timeline.
2. **Workforce Attestation Portal (`/policies/attestations` or `/compliance/attestations`)**:
   - Campaign management table for compliance officers.
   - Attestation completion dial, overdue employee tracking, reminder trigger.
3. **Employee Self-Service Attestation Banner (`DashboardPage.tsx`)**:
   - Interactive pop-up / action card for employees with pending policy acknowledgments.

---

## 23. Security Threat Model

- **BOLA / IDOR**: Attesting to another user's campaign record blocked by verifying `user_id == current_user.id`.
- **Policy Tampering**: Versions once approved are immutable (`content_hash_sha256` prevents silent alteration).
- **Four-Eyes Bypass**: Backend prevents self-approval of policies.

---

## 24. Test Strategy

- **Domain Tests (`test_policy_lifecycle_domain.py`)**: 12 tests (version lineage, Four-Eyes checks, signature generation, campaign metrics).
- **API Tests (`test_policy_lifecycle_api.py`)**: 10 tests (REST endpoints, approval workflows, user attestation).
- **Adversarial Security Tests (`test_phase24_adversarial_security.py`)**: 12 tests (cross-tenant attestation injection, spoofed signature, creator self-approval, unauthorized publishing).
- **Target Regression**: $925 + 34 = 959$ total tests.

---

## 25. Alembic Migration Strategy

- **File**: `backend/alembic/versions/0021_policy_lifecycle_and_attestation.py`
- **Revision**: `0021`
- **Down Revision**: `0020`
- **Tables**: Exactly 4 persistent tables with cascading deletes on tenant removal.

---

## 26. Dependency Impact

- Zero new backend or frontend dependencies required.
- Standard libraries (`hashlib`, `json`, `datetime`) suffice.

---

## 27. Backward Compatibility

- Existing `policies` table remains completely intact.
- Existing policy foreign keys across controls, exceptions, and assessments continue to resolve without schema modification.

---

## 28. Risks and Mitigations

| Risk | Mitigation |
| :--- | :--- |
| High-volume attestation load during organization-wide rollout | Lightweight indexed `user_attestation_records` with atomic counters. |
| Inadvertent deletion of approved policy versions | `ondelete="RESTRICT"` on active versions linked to campaigns. |
| Employee disputes policy acknowledgment | Cryptographic signature binding IP, timestamp, user ID, and content SHA-256. |

---

## 29. Explicit Non-Goals

- Do not implement custom Rich Text / WYSIWYG editors (markdown is standard).
- Do not bypass Phase 3 human evidence review for attestation reports.
- Do not create a parallel employee user table (uses existing `User` model).

---

## 30. Implementation Phases

1. **Migration 0021 & SQLAlchemy Models**: `policy_versions`, `policy_review_workflows`, `policy_attestation_campaigns`, `user_attestation_records`.
2. **Core Domain Services & Schemas**: `PolicyLifecycleService`, `PolicyAttestationService`, Pydantic schemas.
3. **REST API Endpoints & RBAC**: Versioning, review, and attestation routes.
4. **Test Harness**: 34 unit, API, and adversarial security tests.
5. **Frontend Workspaces**: Policy version diff viewer, campaign manager, employee attestation modal.
6. **Full Regression & Build Verification**: Alembic head check and production build.

---

## 31. Architecture Decision Record (ADR)

- **ADR-024**: Implementation of Enterprise Policy Lifecycle and Workforce Attestation Governance as Phase 24.
- **Context**: ControlSphere requires auditable policy distribution and formal legal review workflows to satisfy SOC 2, ISO 27001, and regulatory compliance.
- **Decision**: Extend existing Phase 2 `Policy` architecture with immutable versioning, Four-Eyes review workflows, and campaign-based user attestation.
- **Consequences**: Provides complete policy governance without duplicating existing domain engines.

---

## 32. Final Recommendation

# **VERDICT: GO**

The ControlSphere architecture is fully stable, verified at **925 passing tests**, and primed for the execution of **Phase 24: Enterprise Policy Lifecycle & Workforce Attestation Governance**.
