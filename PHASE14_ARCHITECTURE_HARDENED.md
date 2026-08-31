# ControlSphere — Phase 14 Hardened Architecture Specification
## Continuous Threat Exposure & Vulnerability Governance (EXPOSURE-GRC)
### Enterprise Threat Intelligence, CVE/EPSS Prioritization, Exploit Governance, and Asset-to-Process Blast Radius Engine

---

## 1. Executive Summary

ControlSphere has developed through 13 rigorous, cryptographically verified, and tenant-isolated architectural phases spanning Foundation (Phases 1–4), Risk & Compliance (Phases 5–8), Supply Chain (Phase 9), Incident Response (Phase 10), Governed Remediation (Phase 11), Quantitative FAIR Loss Modeling (Phase 12), and Operational Resilience (Phase 13).

Following the successful release of **Phase 13 RESILIENCE-GRC** (commit `1aa6d51`), ControlSphere provides exhaustive governance over organizational business processes, recovery thresholds ($RTO$, $RPO$, $MTD$), deterministic financial outage modeling, and four-eyes operational baselines.

However, an enterprise-critical architectural gap exists at the intersection of **Technical Security Operations (SecOps)** and **Executive Risk Governance (GRC)**:
1. **Lack of Governed Threat Exposure Telemetry**: Security vulnerabilities (CVEs, zero-days, misconfigurations) are currently disconnected from organizational controls, remediation workflows, and business process impact.
2. **Missing Exploit Intelligence & Risk-Based Prioritization**: In real-world enterprise environments, thousands of raw vulnerabilities exist, but only a fraction are actively exploited. Without native **CISA Known Exploited Vulnerabilities (KEV)** matching, **CVSS v3/v4 scoring**, and **EPSS (Exploit Prediction Scoring System)** probability integration, security teams suffer from alert fatigue and cannot justify remediation SLAs to risk committees.
3. **Absence of Blast Radius Quantification**: When a critical vulnerability emerges in an infrastructure component or software dependency, risk leaders cannot immediately identify which **Phase 13 Business Processes** and **Phase 2 Controls** are exposed, or what the financial disruption exposure would be under Phase 12/13 parameters.

**Phase 14 establishes EXPOSURE-GRC: Continuous Threat Exposure & Vulnerability Governance**. This module delivers:
- Governed Vulnerability & Exposure Catalog (CVE/CWE taxonomy, CVSS Base/Temporal, EPSS Exploit Probability, CISA KEV active exploitation tracking).
- Asset-to-Process Exposure Graph (Mapping exposed IT/cloud assets to Phase 13 Business Processes and Phase 9 Vendors).
- Risk-Derived Exposure Index & SLA Governance (Automated SLA timers based on severity and exploit probability, with four-eyes exception/deferral approvals).
- Closed-Loop Remediation & Control Lineage (Automatic generation of Phase 11 Remediation Plans and validation against Phase 2 Controls).
- Deterministic Exposure Index Formula:
  $$\text{Exposure Score} = \min\left(100.0, \, \left(\text{CVSS Base} \times 0.4 + \text{EPSS} \times 100 \times 0.35 + \text{KEV Bonus} (25.0)\right) \times \text{Criticality Multiplier}\right)$$

---

## 2. Repository Findings

A comprehensive audit of the ControlSphere repository (`backend/` and `frontend/`) revealed the following architectural state:

| Platform Layer | Existing Implementation State | Phase 14 Integration Strategy |
|---|---|---|
| **Database & Migrations** | Alembic chain is strictly linear from `0001` to `0013` (Head: `0013_operational_resilience.py`). | Create migration `0014_threat_exposure_governance.py` maintaining linear Alembic history. |
| **ORM Models** | 20 domain models covering Users, Controls, Evidence, Risks, Incidents, Remediations, QuantRisk, Resilience, etc. | Introduce `VulnerabilityExposure`, `ExposureAsset`, `ExposureProcessLink`, `ExposureException` in `backend/app/models/exposure.py`. |
| **RBAC Matrix** | 6 standardized roles (`ADMIN`, `GRC_ANALYST`, `SECURITY_ANALYST`, `AUDITOR`, `MANAGER`, `VIEWER`) in `permissions.py`. | Add `EXPOSURE_READ`, `EXPOSURE_MANAGE`, `EXPOSURE_ASSESS`, `EXPOSURE_APPROVE` to permissions matrix. |
| **Auditing** | Append-only audit logger in `backend/app/models/audit_log.py` with actor attribution, tenant isolation, and IP logging. | Emit audit events for exposure ingestion, status changes, SLA extensions, and exception approvals. |
| **Service Layer** | Domain-driven services enforcing multi-tenant filtering, four-eyes rules, and deterministic mathematical calculations. | Implement `exposure_service.py` with deterministic prioritization algorithms and four-eyes SLA deferral workflows. |
| **Frontend Framework** | React 19, TypeScript 5.9, Vite, `@tanstack/react-query`, Tailwind CSS, Lucide React, pure SVG visualizations. | Build `ExposurePage.tsx`, `ExposureDetailPage.tsx`, and supporting modals without adding external chart libraries. |

---

## 3. Existing Capability Map (Phases 1–13)

```
[Phase 1: Multi-Tenant Foundation & RBAC]
   ├── [Phase 2: Frameworks, Controls & Policies]
   ├── [Phase 3: Evidence Management & Hash Integrity]
   ├── [Phase 4: Assessments, Findings & Remediation]
   ├── [Phase 5: Qualitative Risk Register & Exceptions]
   ├── [Phase 6: Audit Engagements & Assurance Readiness]
   ├── [Phase 7: Continuous Control Monitoring (CCM)]
   ├── [Phase 8: Multi-Framework Harmonization & Crosswalk]
   ├── [Phase 9: Third-Party & Vendor Risk Management (TPRM)]
   ├── [Phase 10: Security Incident Response & Regulatory Breach Disclosure (SEC/GDPR)]
   ├── [Phase 11: Governed Remediation Orchestration & CAPA Root Cause Analysis]
   ├── [Phase 12: QUANTUM-GRC Cyber Risk Quantification, Monte Carlo & Financial Loss Modeling]
   └── [Phase 13: RESILIENCE-GRC Operational Resilience, BIA Baselines & Deterministic Outage Modeling]
```

---

## 4. Gap Analysis

Despite the breadth of Phases 1–13, significant enterprise governance gaps remain regarding technical risk exposure:

| Governance Dimension | Current State in ControlSphere | Missing Enterprise Capability |
|---|---|---|
| **Threat Intelligence & CVE Tracking** | Non-existent. Risks (Phase 5) and Incidents (Phase 10) operate only on high-level business risk or materialized breaches. | Structured tracking of Common Vulnerabilities and Exposures (CVE), CWE identifiers, CVSS metrics, and EPSS exploit prediction probabilities. |
| **Active Exploitation Signals** | None. No awareness of in-the-wild exploitation or zero-day weaponization. | CISA KEV (Known Exploited Vulnerabilities) catalog integration and active threat actor exploit flags. |
| **Remediation SLA Governance** | Phase 11 manages general remediation tasks, but has no automated vulnerability SLA calculation based on exploitability. | Dynamic SLA countdown timers (e.g., Critical + KEV = 7 days, High = 30 days) with strict four-eyes deferral governance. |
| **Blast Radius & Business Lineage** | Phase 13 catalogs business processes, but cannot see which technical assets or vulnerabilities directly endanger them. | Bidirectional mapping between exposed infrastructure/software assets, Phase 13 Business Processes, and Phase 2 Controls. |
| **Risk Model Calibration** | Phase 12 FAIR simulations rely on manual estimates for Threat Event Frequency (TEF) and Vulnerability (VULN). | Real-time exposure scores provide empirical telemetry to calibrate Phase 12 Monte Carlo parameters. |

---

## 5. Candidate Phase 14 Capabilities

Four major candidate capabilities were evaluated for Phase 14:

1. **Candidate A: Continuous Threat Exposure & Vulnerability Governance (EXPOSURE-GRC)**
   - *Scope*: Governed CVE/EPSS vulnerability repository, asset-to-process exposure mapping, CISA KEV threat intelligence, risk-based exposure scoring, SLA governance, and four-eyes deferrals.
2. **Candidate B: Enterprise Policy Attestation & Awareness Campaign Lifecycle (ATTEST-GRC)**
   - *Scope*: Employee policy attestation campaigns, mandatory reading compliance tracking, comprehension quizzes, and employee exception requests.
3. **Candidate C: Key Risk Indicators & Executive Risk Threshold Telemetry (KRI-GRC)**
   - *Scope*: Leading/lagging KRI metrics, amber/red risk limit monitoring, and board-level risk appetite telemetry dashboards.
4. **Candidate D: AI System Risk & Algorithmic Governance (AI-GRC / ISO 42001 & NIST AI RMF)**
   - *Scope*: AI model registry, foundation model risk assessments, training data provenance, hallucination evaluation, and AI regulatory compliance.

---

## 6. Candidate Ranking & Evaluation

| Evaluation Criteria | Candidate A: EXPOSURE-GRC | Candidate B: ATTEST-GRC | Candidate C: KRI-GRC | Candidate D: AI-GRC |
|---|:---:|:---:|:---:|:---:|
| **Enterprise Business Value** | **9.8 / 10** | 7.5 / 10 | 8.2 / 10 | 8.8 / 10 |
| **Cross-Module Synergies (Phases 2, 5, 9, 10, 11, 12, 13)** | **10.0 / 10** | 6.0 / 10 | 7.8 / 10 | 7.2 / 10 |
| **Regulatory & Standard Mandates (NIST SP 800-40, DORA, PCI-DSS, FedRAMP)** | **9.9 / 10** | 8.0 / 10 | 7.5 / 10 | 8.5 / 10 |
| **Data Reuse & Telemetry Integration** | **9.7 / 10** | 5.5 / 10 | 8.0 / 10 | 6.5 / 10 |
| **Adversarial Security Test Depth** | **10.0 / 10** | 6.0 / 10 | 7.0 / 10 | 8.0 / 10 |
| **Portfolio & Production Architectural Value** | **9.9 / 10** | 7.0 / 10 | 8.0 / 10 | 8.9 / 10 |
| **Overall Rank** | **RANK 1 (Selected)** | RANK 4 | RANK 3 | RANK 2 |

---

## 7. Recommended Phase 14 Capability: EXPOSURE-GRC

**Selected**: **Continuous Threat Exposure & Vulnerability Governance (EXPOSURE-GRC)**

### Why EXPOSURE-GRC was Selected:
1. **Fills the Primary SecOps-to-GRC Void**: Connects technical vulnerability intelligence directly into ControlSphere's governance and risk workflows.
2. **Consumes and Enriches 7 Existing Modules**:
   - Consumes **Phase 13 Business Processes** to compute business blast radius.
   - Consumes **Phase 9 TPRM Vendors** to identify supply chain software vulnerabilities.
   - Consumes **Phase 2 Controls** to evaluate safeguard efficacy.
   - Generates **Phase 11 Remediation Plans** for automated corrective actions.
   - Provides empirical frequency telemetry to **Phase 12 QUANTUM-GRC** Monte Carlo models.
   - Correlates with **Phase 10 Incidents** to identify exploited zero-days.
   - Feeds evidence into **Phase 6 Audits** to prove vulnerability management compliance.
3. **Enforces Strict Governance Controls**: Incorporates Four-Eyes SLA exception/deferral approvals, immutable historical remediation records, and mathematical exposure indexing.

---

## 8. Business & Regulatory Justification

- **CISA Directive 22-01**: Mandates Federal and critical infrastructure organizations remediate KEV catalog vulnerabilities within strict timeframes (14–21 days).
- **DORA (Digital Operational Resilience Act - EU)**: Articles 9 & 10 mandate financial institutions maintain vulnerability identification, threat intelligence, and continuous patch governance.
- **PCI-DSS v4.0 Requirement 6.3**: Mandates risk-ranked vulnerability identification and remediation within 30 days for high-risk vulnerabilities.
- **SEC Cyber Disclosure Rules (Item 106)**: Requires disclosure of processes for assessing, identifying, and managing material risks from cybersecurity threats.

---

## 9. Domain Architecture

### Core Domain Entities

```
+-----------------------------------------------------------------------------------------+
|                                 VulnerabilityExposure                                   |
+-----------------------------------------------------------------------------------------+
| id: int                                                                                 |
| organization_id: int                                                                    |
| cve_id: str (e.g. "CVE-2026-1337")                                                      |
| title: str                                                                              |
| description: str                                                                        |
| cvss_score: float (0.0 to 10.0)                                                         |
| cvss_vector: str                                                                        |
| epss_score: float (0.00000 to 1.00000)                                                  |
| cisa_kev: bool (True/False)                                                             |
| severity: ExposureSeverityEnum (CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL)             |
| status: ExposureStatusEnum (OPEN, UNDER_INVESTIGATION, REMEDIATING, EXCEPTION, RESOLVED)|
| exposure_index: float (0.0 to 100.0)                                                    |
| remediation_sla_due: datetime                                                           |
| discovered_at: datetime                                                                 |
| resolved_at: datetime?                                                                  |
+-----------------------------------------------------------------------------------------+
                               | 1
                               |
                               | N
+-----------------------------------------------------------------------------------------+
|                                   ExposureAssetLink                                     |
+-----------------------------------------------------------------------------------------+
| id: int                                                                                 |
| organization_id: int                                                                    |
| exposure_id: int (FK -> VulnerabilityExposure.id)                                       |
| asset_identifier: str (e.g. "srv-db-prod-01", "auth-gateway-cluster")                   |
| asset_type: AssetTypeEnum (SERVER, DATABASE, CLOUD_SERVICE, NETWORK_DEVICE, APPLICATION)|
| environment: EnvironmentEnum (PRODUCTION, STAGING, DEVELOPMENT)                         |
| process_id: int? (FK -> BusinessProcess.id from Phase 13)                                |
| vendor_id: int? (FK -> Vendor.id from Phase 9)                                          |
| control_id: int? (FK -> OrganizationControl.id from Phase 2)                            |
+-----------------------------------------------------------------------------------------+
                               | 1
                               |
                               | N
+-----------------------------------------------------------------------------------------+
|                                   ExposureException                                     |
+-----------------------------------------------------------------------------------------+
| id: int                                                                                 |
| organization_id: int                                                                    |
| exposure_id: int (FK -> VulnerabilityExposure.id)                                       |
| requested_by_id: int (FK -> User.id)                                                    |
| approved_by_id: int? (FK -> User.id)                                                   |
| status: ExceptionApprovalStatusEnum (PENDING, APPROVED, REJECTED, EXPIRED)              |
| original_sla_due: datetime                                                              |
| requested_sla_due: datetime                                                             |
| justification: str                                                                      |
| compensating_controls: str                                                              |
| created_at: datetime                                                                    |
| reviewed_at: datetime?                                                                  |
+-----------------------------------------------------------------------------------------+
```

---

## 10. Database Architecture & Alembic Migration

### Migration Version: `0014_threat_exposure_governance.py`
- Down revision: `0013_operational_resilience`
- Dependencies: References `organizations.id`, `users.id`, `business_processes.id`, `vendors.id`, `organization_controls.id`.
- Composite Indexes:
  - `ix_exposures_org_status (organization_id, status)`
  - `ix_exposures_org_cve (organization_id, cve_id)`
  - `ix_exposure_assets_org_proc (organization_id, process_id)`
  - `ix_exposure_exceptions_org_status (organization_id, status)`

---

## 11. API Architecture

Base Prefix: `/api/v1/exposures`

| Method | Route | Permission Required | Description |
|---|---|---|---|
| `POST` | `/exposures` | `EXPOSURE_MANAGE` | Ingest/Register a new vulnerability exposure record |
| `GET` | `/exposures` | `EXPOSURE_READ` | Search & filter exposures by severity, KEV, SLA status |
| `GET` | `/exposures/{id}` | `EXPOSURE_READ` | Get exposure details with linked assets, processes, and controls |
| `PUT` | `/exposures/{id}` | `EXPOSURE_MANAGE` | Update exposure telemetry, status, or CVSS/EPSS parameters |
| `DELETE`| `/exposures/{id}` | `EXPOSURE_MANAGE` | Delete exposure record (Restricted to non-resolved/non-immutable) |
| `POST` | `/exposures/{id}/assets` | `EXPOSURE_MANAGE` | Link exposed asset, Phase 13 Process, or Phase 9 Vendor |
| `DELETE`| `/exposures/assets/{link_id}` | `EXPOSURE_MANAGE` | Remove asset link |
| `POST` | `/exposures/{id}/exceptions` | `EXPOSURE_MANAGE` | Request four-eyes SLA deferral exception |
| `POST` | `/exposures/exceptions/{id}/review`| `EXPOSURE_APPROVE` | Review & approve/reject exception (Four-Eyes SoD enforced) |
| `POST` | `/exposures/{id}/remediate` | `REMEDIATION_MANAGE` | Instantiate a Phase 11 Remediation Plan linked to exposure |
| `GET` | `/exposures/summary/posture` | `EXPOSURE_READ` | Executive posture metrics (KEV count, SLA breach rate, index) |
| `POST` | `/exposures/calculate-index` | `EXPOSURE_READ` | Server-authoritative Exposure Index calculation preview |

---

## 12. Service Architecture (`exposure_service.py`)

1. **Deterministic Priority & SLA Engine**:
   - Automatically computes SLA deadline upon ingestion:
     - `CRITICAL` + `CISA_KEV == True`: **7 Calendar Days**
     - `CRITICAL`: **14 Calendar Days**
     - `HIGH`: **30 Calendar Days**
     - `MEDIUM`: **60 Calendar Days**
     - `LOW`: **90 Calendar Days**
2. **Blast Radius Calculator**:
   - Traverses `ExposureAssetLink` to identify all connected `BusinessProcess` entities and extracts their `CriticalityTier` (`TIER_1` to `TIER_4`).
   - If any linked process is `TIER_1`, the Exposure Index applies a $1.25\times$ blast radius multiplier.
3. **Four-Eyes Exception Governance**:
   - Prohibits self-approval (`requested_by_id != approved_by_id`).
   - Requires `ADMIN` or `MANAGER` role for approval.

---

## 13. Frontend Architecture

### Routes Registered:
1. `/exposures` — Executive Exposure Dashboard, SLA Breach Radar, KEV Threat Watch, and Vulnerability Register.
2. `/exposures/:id` — Deep-Dive Exposure View: CVE Telemetry, CVSS/EPSS gauges, Asset-to-Process Blast Radius Map, Linked Phase 2 Controls, Remediation Plan Integration, and Four-Eyes Exception History.

### Components:
- `ExposureModal.tsx` — Ingestion & editing modal with client-side CVSS validation.
- `ExposureAssetLinkModal.tsx` — Asset linking dialog with Phase 13 Business Process & Phase 9 Vendor selectors.
- `ExposureExceptionModal.tsx` — Four-eyes SLA deferral request & approval dialog.
- `BlastRadiusCard.tsx` — Visual mapping showing affected business processes and disruption risk.
- `ExposureLineageCard.tsx` — Cross-module governance lineage diagram.

---

## 14. RBAC Architecture

| Action | ADMIN | MANAGER | GRC_ANALYST | SECURITY_ANALYST | AUDITOR | VIEWER |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| `EXPOSURE_READ` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `EXPOSURE_MANAGE` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `EXPOSURE_ASSESS` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `EXPOSURE_APPROVE`| ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |

---

## 15. Tenant Isolation Model

- Every query strictly applies `WHERE organization_id = :org_id`.
- Cross-tenant lookups on `BusinessProcess`, `Vendor`, or `OrganizationControl` return `HTTP 404 Not Found`.
- Cross-tenant IDOR attempts raise immediate security audit logs.

---

## 16. Audit Architecture

The module records tamper-evident events into `audit_logs`:
- `EXPOSURE_INGESTED`
- `EXPOSURE_STATUS_CHANGED`
- `EXPOSURE_ASSET_LINKED`
- `EXPOSURE_ASSET_UNLINKED`
- `EXPOSURE_EXCEPTION_REQUESTED`
- `EXPOSURE_EXCEPTION_APPROVED`
- `EXPOSURE_EXCEPTION_REJECTED`
- `EXPOSURE_REMEDIATION_SPAWNED`

---

## 17. Lifecycle & State Machine Requirements

```
[DISCOVERED / OPEN]
        │
        ├──▶ [UNDER_INVESTIGATION] ──▶ [REMEDIATING] ──▶ [RESOLVED (Immutable)]
        │                                    │
        └──▶ [EXCEPTION_REQUESTED] ──────────┘
                    │
                    ├──▶ [EXCEPTION_APPROVED (SLA Extended)]
                    └──▶ [EXCEPTION_REJECTED]
```

---

## 18. Four-Eyes Governance Requirements

- Deferrals and exceptions extending mandatory remediation SLAs require four-eyes approval:
  $$\text{Requester} \neq \text{Approver}$$
- Any attempt by the creator of an exception to approve their own request is rejected with `HTTP 403 Forbidden`.

---

## 19. Immutability Requirements

- Once an exposure is transitioned to `RESOLVED`, the historical remediation timestamp, final mitigating controls, and resolved SLA telemetry are locked as immutable records.
- Any attempt to mutate historical audit logs or approved exceptions is blocked.

---

## 20. Cross-Module Lineage

```
[Phase 14: Threat Exposure & CVE Telemetry]
                  │
                  ├──▶ [Phase 13: Business Process] (Blast Radius & Criticality Tier 1-4)
                  ├──▶ [Phase 9: TPRM Vendors] (Third-Party Software & Supply Chain Exposure)
                  ├──▶ [Phase 2 & 7: Controls & CCM] (Mitigating Safeguards & Automated Monitoring)
                  │
                  ├──▶ [Phase 11: Governed Remediation] (Auto-instantiated CAPA Plans & Verification)
                  ├──▶ [Phase 10: Security Incidents] (Zero-Day Exploitation & Material Breach Link)
                  └──▶ [Phase 12: QUANTUM-GRC] (Empirical Threat Frequency Calibration for Monte Carlo)
```

---

## 21. Mathematical & Calculation Requirements

### 1. Deterministic Exposure Index Formula:
$$\text{Base Score} = (\text{CVSS Base} \times 0.40) + (\text{EPSS Probability} \times 100 \times 0.35) + (\text{CISA KEV} \ ? \ 25.0 : 0.0)$$

$$\text{Blast Radius Multiplier} = \begin{cases}
1.25 & \text{if linked to any TIER\_1 Process} \\
1.15 & \text{if linked to any TIER\_2 Process} \\
1.05 & \text{if linked to any TIER\_3 Process} \\
1.00 & \text{otherwise}
\end{cases}$$

$$\text{Final Exposure Index} = \min(100.0, \, \text{Base Score} \times \text{Blast Radius Multiplier})$$

---

## 22. ADV-P14 Adversarial Security Threat Model

A dedicated adversarial security suite (`test_phase14_adversarial_security.py`) will test 25 attack vectors (`ADV-P14-01` through `ADV-P14-25`):
1. **ADV-P14-01**: Cross-tenant exposure lookup IDOR (`HTTP 404`).
2. **ADV-P14-02**: Cross-tenant exposure update IDOR (`HTTP 404`).
3. **ADV-P14-03**: Cross-tenant exposure deletion IDOR (`HTTP 404`).
4. **ADV-P14-04**: Cross-tenant asset linking IDOR (attempting to link Organization B's process to Organization A's exposure).
5. **ADV-P14-05**: Cross-tenant exception review IDOR (`HTTP 404`).
6. **ADV-P14-06**: Four-eyes exception self-approval bypass (`HTTP 403`).
7. **ADV-P14-07**: GRC Analyst privilege escalation (attempting approval without `EXPOSURE_APPROVE`).
8. **ADV-P14-08**: Security Analyst mutation bypass (attempting write without `EXPOSURE_MANAGE`).
9. **ADV-P14-09**: Viewer role read-only boundary enforcement.
10. **ADV-P14-10**: Unauthenticated access rejection (`HTTP 401`).
11. **ADV-P14-11**: Invalid JWT token spoofing (`HTTP 401`).
12. **ADV-P14-12**: Ingestion payload injection & XSS sanitization in description/compensating controls.
13. **ADV-P14-13**: Out-of-bounds CVSS score injection (`cvss > 10.0` or `cvss < 0.0`).
14. **ADV-P14-14**: Out-of-bounds EPSS probability injection (`epss > 1.0` or `epss < 0.0`).
15. **ADV-P14-15**: Negative SLA date injection (setting SLA date in the past).
16. **ADV-P14-16**: Mutation of resolved exposure record (`HTTP 409 Conflict`).
17. **ADV-P14-17**: Double-approval of pending exception (`HTTP 409 Conflict`).
18. **ADV-P14-18**: Exception approval after rejection terminal state.
19. **ADV-P14-19**: SQL injection in CVE search filter parameter.
20. **ADV-P14-20**: SQL injection in asset identifier parameter.
21. **ADV-P14-21**: Client-side `organization_id` tampering during ingestion.
22. **ADV-P14-22**: Client-side `exposure_index` tampering (server calculates authoritative score).
23. **ADV-P14-23**: Replay attack on approved SLA extension.
24. **ADV-P14-24**: Bulk asset linking resource exhaustion / DoS threshold test.
25. **ADV-P14-25**: Tampering with append-only audit trail.

---

## 23. Stage 1 Implementation Scope (Database & Domain Foundation)
- Migration `0014_threat_exposure_governance.py`.
- Models: `backend/app/models/exposure.py`.
- Schemas: `backend/app/schemas/exposure.py`.
- Permissions in `permissions.py`.
- Domain service: `backend/app/services/exposure_service.py`.
- Domain tests: `test_exposure_domain.py`.

## 24. Stage 2 Implementation Scope (REST API, Integration & Security)
- Endpoints: `backend/app/api/v1/endpoints/exposure.py`.
- Router registration in `api.py`.
- Cross-module integration with Phase 13, Phase 11, Phase 9, Phase 2.
- API tests: `test_exposure_api.py`.
- Adversarial Security suite: `test_phase14_adversarial_security.py` (25 ADV-P14 vectors).

## 25. Stage 3 Implementation Scope (Frontend Governance Workspace)
- TypeScript definitions in `frontend/src/types/index.ts`.
- API Service client: `frontend/src/lib/exposureService.ts`.
- Components in `frontend/src/components/exposure/`.
- Pages: `ExposurePage.tsx`, `ExposureDetailPage.tsx`.
- Routes in `App.tsx` and Navigation in `Sidebar.tsx`.

---

## 26. Verification Strategy
- **Stage 1**: Domain tests pass (100%), Alembic heads linear (`0014`).
- **Stage 2**: Full backend regression suite (`540+` tests passing), `25/25` ADV-P14 tests passing.
- **Stage 3**: `npm run build` passing with 0 errors, `git diff --check` clean.

---

## 27. Dependency Strategy
- **NPM Dependencies Added**: `0`
- **Python Dependencies Added**: `0`

---

## 28. Exact Proposed Files

### Files to Create:
1. `backend/alembic/versions/0014_threat_exposure_governance.py`
2. `backend/app/models/exposure.py`
3. `backend/app/schemas/exposure.py`
4. `backend/app/services/exposure_service.py`
5. `backend/app/api/v1/endpoints/exposure.py`
6. `backend/tests/test_exposure_domain.py`
7. `backend/tests/test_exposure_api.py`
8. `backend/tests/test_phase14_adversarial_security.py`
9. `frontend/src/lib/exposureService.ts`
10. `frontend/src/pages/ExposurePage.tsx`
11. `frontend/src/pages/ExposureDetailPage.tsx`
12. `frontend/src/components/exposure/ExposureModal.tsx`
13. `frontend/src/components/exposure/ExposureAssetLinkModal.tsx`
14. `frontend/src/components/exposure/ExposureExceptionModal.tsx`
15. `frontend/src/components/exposure/BlastRadiusCard.tsx`
16. `frontend/src/components/exposure/ExposureLineageCard.tsx`

### Files to Modify:
1. `backend/app/core/permissions.py` (Register `EXPOSURE_*` permissions)
2. `backend/app/models/__init__.py` (Export exposure models)
3. `backend/app/api/v1/api.py` (Register `/exposures` router)
4. `frontend/src/types/index.ts` (Export Phase 14 TypeScript types)
5. `frontend/src/App.tsx` (Register `/exposures` routes)
6. `frontend/src/components/layout/Sidebar.tsx` (Add navigation item)

---

## 29. Migration Strategy
- Alembic single revision step: `0013 -> 0014`.
- Upgrade & downgrade functions fully defined and tested.

---

## 30. Explicit Non-Goals
- **Non-Goal 1**: Developing an active network packet vulnerability scanner (e.g. replacing Tenable/Qualys). Phase 14 is the **governance, prioritization, SLA management, and blast radius orchestration platform** that ingests and contextualizes vulnerability telemetry.
- **Non-Goal 2**: Modifying existing Phase 1–13 database schemas or altering previous migration chains.
- **Non-Goal 3**: Introducing third-party SaaS threat intelligence API keys as hard system requirements (mock/deterministic engine provided out-of-the-box).

---

## 31. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Large vulnerability volume causing UI performance degradation | Database indexing on `(organization_id, status)`, server-side pagination, and aggregate posture caching. |
| Unauthorized SLA extensions by engineers | Strict Four-Eyes Segregation of Duties prohibiting self-approval (`requested_by_id != approved_by_id`). |
| Inaccurate manual exposure estimates | Server-authoritative Exposure Index formula combining CVSS, EPSS, KEV, and Business Criticality Tier. |

---

## 32. Definition of Done
1. Clean Alembic migration `0014` with forward and rollback validation.
2. 100% backend domain, API, and 25 ADV-P14 adversarial security tests passing.
3. Zero regression across all 523 prior tests (target: 550+ passing).
4. Frontend workspace fully responsive, accessible, with zero TypeScript/Vite errors.
5. Zero new npm or Python dependencies.
