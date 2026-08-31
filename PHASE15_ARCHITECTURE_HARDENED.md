# PHASE 15 ARCHITECTURE SPECIFICATION (HARDENED)
## AI-GRC — Artificial Intelligence Governance, Algorithmic Risk Management & Model Compliance
### Enterprise GRC Architecture, Domain Foundation, Mathematical Authority & Adversarial Security

---

## 1. Executive Summary

As enterprise adoption of generative AI, autonomous agentic workflows, machine learning models, and foundation LLMs surges, organizations face unprecedented regulatory and operational risks. Global frameworks—most notably the **European Union Artificial Intelligence Act (EU AI Act, Regulation 2024/1689)**, the **NIST AI Risk Management Framework (NIST AI RMF 1.0)**, **ISO/IEC 42001:2023 (Artificial Intelligence Management System)**, and **US Executive Order 14110**—mandate formal model inventories, algorithmic risk classification, data provenance tracking, bias/drift monitoring, and strict Human-in-the-Loop (HITL) deployment governance.

**Phase 15: AI-GRC** establishes ControlSphere as an enterprise-grade AI Governance, Risk, and Compliance System of Record. It enables organizations to catalog AI systems and models, classify them into regulatory risk tiers (Prohibited, High-Risk, General-Purpose AI / GPAI, Limited, Minimal), quantify algorithmic risk indices, enforce four-eyes ethical deployment approvals, and trace end-to-end lineage across Third-Party AI Vendors (Phase 9), Threat Exposures (Phase 14), Business Processes (Phase 13), Financial Loss Scenarios (Phase 12), and Corrective Action Plans (Phase 11).

---

## 2. Current Repository Baseline

The ControlSphere platform has completed and verified Phases 1 through 14:

| Phase | Domain | Status | Key Artifacts & Capabilities |
|---|---|---|---|
| **Phase 1** | Foundation & Multi-Tenancy | Complete | Multi-tenant DB schema, User & Org models, JWT auth, Role-based access control, Tamper-evident Audit Logs (`audit_logs`) with SHA-256 integrity. |
| **Phase 2** | Frameworks, Controls & Policies | Complete | NIST CSF, ISO 27001, SOC 2, HIPAA, CIS controls; OrganizationControl; Policy lifecycle management. |
| **Phase 3** | Evidence Management | Complete | Cryptographic SHA-256 evidence chain of custody, multi-control evidence linking, freshness and expiration tracking. |
| **Phase 4** | Assessments & Findings | Complete | Control assessments, effectiveness scoring, finding lifecycle, root cause analysis. |
| **Phase 5** | Qualitative Risk & Exceptions | Complete | 5×5 Qualitative Risk Register, Inherent vs Residual scoring, Exception workflows with Four-Eyes approvals. |
| **Phase 6** | Audit Engagements & Workpapers | Complete | Fieldwork management, workpaper reviews, PBC requests, immutable audit engagement lockouts. |
| **Phase 7** | Continuous Control Monitoring | Complete | Automated health scoring, metric telemetry collection, automated degraded/failing alert generation. |
| **Phase 8** | Multi-Framework Harmonization | Complete | Many-to-many cross-framework mapping, confidence scoring, redundancy reduction. |
| **Phase 9** | Third-Party & Vendor Risk | Complete | TPRM vendor catalog, tiering (Tier 1-4), security questionnaires, vendor evidence linking. |
| **Phase 10** | Security Incidents & Disclosure | Complete | Incident triage, regulatory disclosure countdowns (SEC 4-Day, GDPR 72-Hr, NYDFS), materiality governance. |
| **Phase 11** | Remediation Orchestration | Complete | CAPA orchestration, multi-task workflows, IV&V independent verification sign-off. |
| **Phase 12** | QUANTUM-GRC Cyber Risk | Complete | Monte Carlo financial loss simulation (Loss Event Frequency × Loss Magnitude), 95th/99th VaR, ROSI optimization. |
| **Phase 13** | RESILIENCE-GRC Resilience | Complete | Business Process catalog, BIA (RTO/RPO/MTD), Tier 1-4 criticality, dependency mapping, outage loss estimation. |
| **Phase 14** | EXPOSURE-GRC Threat Exposure | Complete | Continuous threat exposure, CVE/CWE catalog, CVSS + EPSS + CISA KEV scoring, process blast radius scaling ($1.00\times - 1.25\times$), Four-Eyes SLA deferral governance. |

- **Current Git Baseline**: Commit `6bc9e8ec1b600049eaa5042f30b086c8b1099b81` (`feat(phase14): implement exposure grc governance workspace`).
- **Alembic Head**: `0014` (`0014_threat_exposure_governance.py`).
- **Backend Test Baseline**: 594/594 passing (0 failures).
- **Frontend Production Build**: 1,992 modules transformed (0 errors).

---

## 3. Phase 1–14 Capability Map & Integration Anchors

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      ControlSphere Enterprise GRC Map                       │
└─────────────────────────────────────────────────────────────────────────────┘
  Phase 2: Organization Controls  ◄──────►  Phase 8: Multi-Framework Crosswalk
             │                                       │
  Phase 3: Cryptographic Evidence ◄──────►  Phase 7: Continuous Monitoring
             │                                       │
  Phase 4: Assessments & Findings ◄──────►  Phase 6: Audit Workpapers
             │                                       │
  Phase 9: TPRM & AI SaaS Vendors ◄──────►  Phase 5: Qualitative Risk
             │                                       │
  Phase 14: Threat Exposure (CVE) ◄──────►  Phase 10: Security Incidents
             │                                       │
  Phase 13: Operational Resilience◄──────►  Phase 12: QUANTUM-GRC Financial Loss
             │                                       │
             └───────────────────┬───────────────────┘
                                 ▼
                     Phase 11: CAPA Remediation
                                 ▲
                                 │
           ┌─────────────────────┴─────────────────────┐
           │   PHASE 15: AI-GRC (MODEL GOVERNANCE)     │
           │  • AI System & Model Inventory            │
           │  • EU AI Act & NIST AI RMF Risk Tiering   │
           │  • Algorithmic Risk Index (ARI) Engine    │
           │  • Four-Eyes Ethical Deployment Gate      │
           │  • Cross-Module Lineage (P9,11,12,13,14)  │
           └───────────────────────────────────────────┘
```

---

## 4. Enterprise Gap Analysis

| Enterprise GRC Dimension | Current Capability | Identified Gap | Severity / Urgency |
|---|---|---|---|
| **1. AI & Algorithmic Governance** | Placeholder `/ai-analyst` route | No AI system inventory, no EU AI Act classification, no model card tracking, no bias/drift telemetry. | **CRITICAL** |
| **2. Identity & Access Governance** | RBAC on platform users | No external identity store sync, no periodic access certification campaigns, no toxic SoD combination engine. | Medium |
| **3. Privacy & Data Protection** | Breach timers (Phase 10) | No Article 30 RoPA catalog, no DPIA workflow, no DSAR SLA tracker. | High |
| **4. Enterprise Risk Aggregation** | 5×5 Qualitative (P5) + Monte Carlo (P12) | No global KRI threshold alerting engine aggregating telemetry across all 14 phases. | Medium |
| **5. Threat Intelligence (CTI)** | CVE, EPSS, CISA KEV (P14) | No MITRE ATT&CK enterprise matrix mapping, no threat actor profiling. | Low |

---

## 5. Candidate Capability Evaluation & Ranking

### Candidate Scoring Matrix (10-Point Scale):

| Evaluation Criteria (Weight) | Candidate 1: AI-GRC (EU AI Act / NIST AI RMF) | Candidate 2: IDENTITY-GRC (IGA / Access Cert) | Candidate 3: PRIVACY-GRC (RoPA / DPIA / DSAR) | Candidate 4: ENTERPRISE-KRI (ERM Aggregator) |
|---|:---:|:---:|:---:|:---:|
| **Enterprise Value (15%)** | 10.0 | 9.0 | 9.0 | 8.0 |
| **Cross-Module Synergy (15%)** | 10.0 | 8.0 | 8.5 | 9.0 |
| **Regulatory Urgency (15%)** | 10.0 | 8.5 | 9.0 | 7.5 |
| **Security Impact (15%)** | 9.5 | 9.5 | 8.0 | 8.0 |
| **Market Differentiation (10%)** | 10.0 | 7.5 | 8.0 | 7.0 |
| **Implementation Feasibility (10%)** | 9.0 | 8.5 | 9.0 | 9.0 |
| **Data Integrity & Governance (10%)** | 10.0 | 9.0 | 9.0 | 8.5 |
| **Adversarial Test Depth (10%)** | 10.0 | 9.5 | 8.0 | 8.0 |
| **WEIGHTED SCORE (100%)** | **9.80** | **8.68** | **8.68** | **8.23** |

### Decision:
**Candidate 1: AI-GRC (Artificial Intelligence Governance, Algorithmic Risk Management & Model Compliance)** is decisively selected as the Phase 15 domain.

---

## 6. Phase 15: AI-GRC Domain Specification

### 6.1 Official Naming & Scope
- **Phase Name**: Phase 15: AI-GRC
- **Module Title**: Artificial Intelligence Governance, Algorithmic Risk Management & Model Compliance
- **Regulatory Frameworks Covered**:
  - **EU AI Act (Regulation 2024/1689)**: Prohibited AI (Art 5), High-Risk AI (Art 6 & Annex III), General-Purpose AI / GPAI with Systemic Risk (Art 51-55), Transparency & Minimal Risk.
  - **NIST AI RMF 1.0**: GOVERN, MAP, MEASURE, MANAGE functions.
  - **ISO/IEC 42001:2023**: AI Management System (AIMS) controls.
  - **US Executive Order 14110**: Safety evaluations, red-teaming benchmarks, and compute reporting ($> 10^{26}$ integer ops).

### 6.2 Key Personas & RBAC Mapping
- **`ADMIN` / `MANAGER`**: Full operational authority, policy overrides, Four-Eyes Deployment Approvals (`AI_APPROVE`), Risk Acceptance.
- **`SECURITY_ANALYST` / `GRC_ANALYST`**: AI System registration, model card telemetry ingestion, assessment execution, exception requesting, CAPA spawning.
- **`AUDITOR` / `VIEWER`**: Read-only oversight, model registry inspection, compliance export.

---

## 7. Data Models & Database Schema (`0015_ai_governance.py`)

### 7.1 Table: `ai_systems`
Represents an enterprise AI application, autonomous agent pipeline, or machine learning workflow.

```sql
CREATE TABLE ai_systems (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    system_code VARCHAR(64) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    system_type VARCHAR(32) NOT NULL, -- LLM_APPLICATION, AGENTIC_WORKFLOW, EMBEDDED_ML, COMPUTER_VISION, RECOMMENDER, PREDICTIVE_ANALYTICS
    lifecycle_state VARCHAR(32) NOT NULL DEFAULT 'DEVELOPMENT', -- DEVELOPMENT, VALIDATION, ETHICAL_REVIEW, APPROVED_STAGING, PRODUCTION, DECOMMISSIONED, REJECTED
    regulatory_tier VARCHAR(32) NOT NULL, -- PROHIBITED, HIGH_RISK, GPAI_SYSTEMIC_RISK, LIMITED_RISK, MINIMAL_RISK
    autonomy_level VARCHAR(32) NOT NULL DEFAULT 'HUMAN_IN_THE_LOOP', -- NO_AUTONOMY, HUMAN_IN_THE_LOOP, HUMAN_ON_THE_LOOP, FULL_AUTONOMY
    data_sensitivity VARCHAR(32) NOT NULL DEFAULT 'INTERNAL', -- PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED_PII_PHI
    hosting_type VARCHAR(32) NOT NULL, -- CLOUD_THIRD_PARTY, ON_PREMISE_SELF_HOSTED, HYBRID_VPC, EDGE_DEVICE
    
    -- Technical Telemetry
    foundation_model_name VARCHAR(255), -- e.g. "gpt-4o", "claude-3-7-sonnet", "llama-3.3-70b"
    model_version VARCHAR(64),
    training_data_cutoff VARCHAR(32),
    parameters_billion NUMERIC(8, 2), -- e.g. 70.00
    context_window_tokens INTEGER, -- e.g. 128000
    compute_flops_exponent NUMERIC(5, 2), -- e.g. 25.5 (meaning 10^25.5 FLOPs)
    
    -- Authoritative Governance Scores
    algorithmic_risk_index NUMERIC(5, 2) NOT NULL DEFAULT 0.00, -- 0.00 to 100.00
    eu_compliance_score NUMERIC(5, 2) NOT NULL DEFAULT 0.00, -- 0.00 to 100.00%
    is_prohibited_practice BOOLEAN NOT NULL DEFAULT FALSE,
    requires_conformity_assessment BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Cross-Module Anchor Foreign Keys
    business_process_id INTEGER REFERENCES business_processes(id) ON DELETE SET NULL, -- Phase 13 Link
    vendor_id INTEGER REFERENCES vendors(id) ON DELETE SET NULL, -- Phase 9 Link
    remediation_plan_id INTEGER REFERENCES remediation_plans(id) ON DELETE SET NULL, -- Phase 11 Link
    
    -- Ownership & Auditing
    owner_id INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_at TIMESTAMPTZ,
    approved_by_id INTEGER REFERENCES users(id),
    
    CONSTRAINT uq_ai_system_org_code UNIQUE (organization_id, system_code)
);
```

### 7.2 Table: `ai_model_cards`
Stores model metadata, safety benchmarks, transparency documentation, and prompt evaluation metrics.

```sql
CREATE TABLE ai_model_cards (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    ai_system_id INTEGER NOT NULL REFERENCES ai_systems(id) ON DELETE CASCADE,
    version VARCHAR(32) NOT NULL,
    intended_use TEXT NOT NULL,
    out_of_scope_uses TEXT,
    bias_mitigation_notes TEXT,
    training_data_provenance TEXT,
    synthetic_data_percentage NUMERIC(5, 2) DEFAULT 0.00,
    
    -- Safety & Accuracy Telemetry
    hallucination_rate_percent NUMERIC(5, 2) DEFAULT 0.00, -- 0.00% - 100.00%
    prompt_injection_resistance_score NUMERIC(5, 2) DEFAULT 100.00, -- 0.00 - 100.00
    toxicity_filter_efficiency_score NUMERIC(5, 2) DEFAULT 100.00,
    benchmark_eval_dataset VARCHAR(255), -- e.g. "MMLU / GSM8K / HELM / RedTeam-v2"
    benchmark_score NUMERIC(5, 2), -- 0.00 - 100.00%
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_model_card_system_version UNIQUE (ai_system_id, version)
);
```

### 7.3 Table: `ai_deployment_approvals`
Enforces Four-Eyes Ethical & Compliance Gate before production promotion.

```sql
CREATE TABLE ai_deployment_approvals (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    ai_system_id INTEGER NOT NULL REFERENCES ai_systems(id) ON DELETE CASCADE,
    requested_by_id INTEGER NOT NULL REFERENCES users(id),
    reviewed_by_id INTEGER REFERENCES users(id),
    
    target_environment VARCHAR(32) NOT NULL, -- STAGING, PRODUCTION
    approval_status VARCHAR(32) NOT NULL DEFAULT 'PENDING', -- PENDING, APPROVED, REJECTED, WITHDRAWN
    risk_acceptance_justification TEXT NOT NULL,
    human_oversight_measures TEXT NOT NULL,
    reviewer_notes TEXT,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ,
    
    CONSTRAINT chk_ai_approval_sod CHECK (
        reviewed_by_id IS NULL OR requested_by_id != reviewed_by_id
    )
);
```

---

## 8. Server-Authoritative Mathematical Model

### 8.1 Algorithmic Risk Index (ARI) Formula
The Algorithmic Risk Index (0.00 to 100.00) quantifies the composite enterprise risk posed by an AI system. It is calculated exclusively on the backend:

$$\text{ARI} = \min\left(100.00, \, \left(\text{BaseRisk} \times \text{AutonomyMultiplier} \times \text{ProcessTierMultiplier}\right) + \text{SafetyPenalty}\right)$$

#### 1. Base Regulatory Risk ($\text{BaseRisk}$):
- `PROHIBITED`: $100.00$
- `HIGH_RISK`: $65.00$
- `GPAI_SYSTEMIC_RISK`: $50.00$
- `LIMITED_RISK`: $25.00$
- `MINIMAL_RISK`: $5.00$

#### 2. Autonomy Multiplier ($\text{AutonomyMultiplier}$):
- `FULL_AUTONOMY` (No human in loop): $1.40\times$
- `HUMAN_ON_THE_LOOP` (Human can veto after execution): $1.20\times$
- `HUMAN_IN_THE_LOOP` (Human must approve every action): $1.00\times$
- `NO_AUTONOMY` (Advisory/Passive read-only): $0.80\times$

#### 3. Operational Resilience Multiplier ($\text{ProcessTierMultiplier}$ - Linked Phase 13 Process):
- Linked to `TIER_1` Critical Process: $1.25\times$
- Linked to `TIER_2` High Process: $1.15\times$
- Linked to `TIER_3` Moderate Process: $1.05\times$
- `TIER_4` / Unlinked: $1.00\times$

#### 4. Safety & Telemetry Penalty ($\text{SafetyPenalty}$):
$$\text{SafetyPenalty} = (\text{HallucinationRate} \times 0.20) + ((100 - \text{InjectionResistance}) \times 0.15) + \text{DataSensitivityAddon}$$
Where $\text{DataSensitivityAddon}$:
- `RESTRICTED_PII_PHI`: $+15.0$
- `CONFIDENTIAL`: $+8.0$
- `INTERNAL`: $+2.0$
- `PUBLIC`: $+0.0$

---

## 9. Four-Eyes Ethical Deployment Governance

1. **Deployment Promotion Gate**: An AI system cannot transition from `ETHICAL_REVIEW` to `APPROVED_STAGING` or `PRODUCTION` without an independent `ai_deployment_approvals` record in `APPROVED` status.
2. **Segregation of Duties Enforcement**:
   - The database constraint `chk_ai_approval_sod` guarantees `requested_by_id != reviewed_by_id`.
   - The backend service rejects self-review attempts with HTTP 403 Forbidden (*"Segregation of Duties: Model requester cannot review their own deployment request"*).
   - Only users with `RoleEnum.ADMIN` or `RoleEnum.MANAGER` holding `Permission.AI_APPROVE` can approve.

---

## 10. Lifecycle State Machine

```
   [ DEVELOPMENT ] ──────► [ VALIDATION ]
                                │
                                ▼
                       [ ETHICAL_REVIEW ] ◄────────┐
                                │                  │ (Re-review)
                                ▼                  │
         ┌──────────── [ Four-Eyes Gate ] ─────────┤
         │                      │                  │
 (Reject)│                      ▼ (Approve)        │
         ▼            [ APPROVED_STAGING ]         │
    [ REJECTED ]                │                  │
                                ▼                  │
                         [ PRODUCTION ] ───────────┘
                                │       (Model Drift / Vulnerability)
                                ▼
                       [ DECOMMISSIONED ] (Immutable)
```

- **`DECOMMISSIONED` / `REJECTED` Immutability**: Once decommissioned or rejected, the record cannot be modified or reactivated without administrative audit justification.

---

## 11. Cross-Module Lineage Integration

| Source Phase | Integration Type | Phase 15 Function | Downstream Effect |
|---|---|---|---|
| **Phase 9 (TPRM)** | `vendor_id` ForeignKey | Traces Foundation Model / AI SaaS provider risk | Links OpenAI/Anthropic/Bedrock risk tiering to enterprise AI applications. |
| **Phase 13 (Resilience)** | `business_process_id` ForeignKey | Connects AI model to Tier 1-4 Business Processes | Determines `ProcessTierMultiplier` ($1.00\times - 1.25\times$) for ARI calculation. |
| **Phase 14 (Exposure)** | Asset Link (`APPLICATION` / `CLOUD_SERVICE`) | Maps CVEs in ML packages (PyTorch, LangChain, transformers) | Elevates AI risk when underlying dependencies contain CISA KEV or high EPSS vulnerabilities. |
| **Phase 11 (Remediation)** | `remediation_plan_id` ForeignKey | Spawns CAPA when AI model breaches safety/bias thresholds | Automates model retraining, guardrail patching, or prompt engineering corrective actions. |
| **Phase 12 (QUANTUM-GRC)** | Scenario Financial Mapping | Evaluates financial loss exposure from AI failure or EU AI Act fines | Feeds AI liability scenarios into Monte Carlo loss simulations. |
| **Phase 2 & 8 (Controls)** | NIST AI RMF / ISO 42001 | Maps controls directly to AI system guardrails | Harmonizes AI risk controls into the centralized compliance registry. |

---

## 12. Dedicated Adversarial Security Suite (`ADV-P15`)

Phase 15 will implement **25 dedicated adversarial test vectors** verifying absolute tenant isolation, authorization bounds, calculation determinism, and four-eyes segregation:

1. `ADV-P15-01`: Cross-tenant IDOR — Tenant B cannot view Tenant A's AI systems via `GET /api/v1/ai/systems/:id`.
2. `ADV-P15-02`: Cross-tenant IDOR — Tenant B cannot update Tenant A's AI system via `PUT /api/v1/ai/systems/:id`.
3. `ADV-P15-03`: Cross-tenant IDOR — Tenant B cannot delete Tenant A's AI system via `DELETE /api/v1/ai/systems/:id`.
4. `ADV-P15-04`: Cross-tenant Model Card IDOR — Tenant B cannot attach model cards to Tenant A's AI systems.
5. `ADV-P15-05`: Horizontal Tenant Approval IDOR — Tenant B cannot approve an AI deployment request belonging to Tenant A.
6. `ADV-P15-06`: Tenant ID Injection Spoofing — Injecting `organization_id` in request body is ignored; server binds strictly to authenticated JWT.
7. `ADV-P15-07`: Four-Eyes Segregation of Duties — Model requester cannot approve their own deployment request (`403 Forbidden`).
8. `ADV-P15-08`: Analyst Approval Escalation — `GRC_ANALYST` / `SECURITY_ANALYST` cannot approve deployment requests (`403 Forbidden`).
9. `ADV-P15-09`: Viewer/Auditor Mutation Block — Read-only roles cannot create, update, transition, or delete AI systems (`403 Forbidden`).
10. `ADV-P15-10`: Unauthenticated Access Block — Requests without valid JWT are rejected (`401 Unauthorized`).
11. `ADV-P15-11`: Client ARI Calculation Tampering — Client cannot inject pre-computed `algorithmic_risk_index`; server recalculates authoritatively.
12. `ADV-P15-12`: Client EU Compliance Score Tampering — Client cannot override `eu_compliance_score` in create/update payloads.
13. `ADV-P15-13`: Illegal State Machine Transition — Direct transition from `DEVELOPMENT` to `PRODUCTION` without `ETHICAL_REVIEW` is blocked (`409 Conflict`).
14. `ADV-P15-14`: Unapproved Production Promotion — Promoting to `PRODUCTION` without an `APPROVED` deployment approval is rejected (`409 Conflict`).
15. `ADV-P15-15`: Decommissioned Record Immutability — Modifying telemetry on a `DECOMMISSIONED` AI system is rejected (`409 Conflict`).
16. `ADV-P15-16`: Prohibited Practice Guardrail — Creating an AI system with `is_prohibited_practice: true` enforces ARI of $100.00$ and blocks `PRODUCTION` promotion.
17. `ADV-P15-17`: Cross-Module Process IDOR — Linking a `business_process_id` belonging to Tenant B is rejected (`404/403`).
18. `ADV-P15-18`: Cross-Module Vendor IDOR — Linking a `vendor_id` belonging to Tenant B is rejected (`404/403`).
19. `ADV-P15-19`: Cross-Module Remediation IDOR — Spawning CAPA for Tenant B's finding is rejected.
20. `ADV-P15-20`: Duplicate System Code Collision — Registering duplicate `system_code` within the same organization triggers HTTP 409.
21. `ADV-P15-21`: Invalid Autonomy / Regulatory Tier Enums — Injecting unmapped enum values triggers HTTP 422 Unprocessable Entity.
22. `ADV-P15-22`: Negative / Out-of-Bounds Score Injection — Supplying negative hallucination rates or $>100\%$ synthetic data is rejected (`422`).
23. `ADV-P15-23`: Replay Deployment Approval — Attempting to re-approve an already `APPROVED` or `REJECTED` request is rejected (`409 Conflict`).
24. `ADV-P15-24`: Audit Trail Tampering Prevention — AI governance state mutations produce immutable `audit_logs` entries with SHA-256 hash chains.
25. `ADV-P15-25`: SQL / JSON Injection in Model Cards — Escaping strings or injecting malicious payloads in dataset provenance is safely sanitized.

---

## 13. Staged Implementation Plan

### Stage 1: Database + Domain Foundation
- Migration: `backend/alembic/versions/0015_ai_governance.py`
- Permissions: Add `AI_READ`, `AI_MANAGE`, `AI_ASSESS`, `AI_APPROVE` in `backend/app/core/permissions.py`
- Models: `backend/app/models/ai_governance.py` (`AISystem`, `AIModelCard`, `AIDeploymentApproval`)
- Schemas: `backend/app/schemas/ai_governance.py`
- Domain Service: `backend/app/services/ai_governance_service.py`
- Domain Tests: `backend/tests/test_ai_governance_domain.py` (Verify calculations, bounds, four-eyes logic, state transitions)

### Stage 2: REST API + Cross-Module Integration + Adversarial Security
- API Router: `backend/app/api/v1/endpoints/ai_governance.py` (15+ endpoints)
- Register Router: `backend/app/api/v1/api.py` under `/ai`
- API Tests: `backend/tests/test_ai_governance_api.py`
- Security Tests: `backend/tests/test_phase15_adversarial_security.py` (25/25 `ADV-P15` vectors)

### Stage 3: Frontend Governance Workspace
- Types: Add AI-GRC domain types to `frontend/src/types/index.ts`
- API Service: `frontend/src/lib/aiGovernanceService.ts`
- Pages:
  - `frontend/src/pages/AIGovernancePage.tsx` (Executive AI Risk Dashboard, Searchable Model Register, EU AI Act Breakdown)
  - `frontend/src/pages/AISystemDetailPage.tsx` (Model Telemetry, ARI Breakdown, Safety Metrics, Four-Eyes Deployment Gate, Lineage)
- Components:
  - `frontend/src/components/ai/AISystemModal.tsx`
  - `frontend/src/components/ai/AIModelCardModal.tsx`
  - `frontend/src/components/ai/AIDeploymentApprovalModal.tsx`
  - `frontend/src/components/ai/AIStatusModal.tsx`
  - `frontend/src/components/ai/AILineageCard.tsx`
- Navigation: Replace placeholder `/ai-analyst` in `App.tsx` and `Sidebar.tsx` with `/ai-governance`.

---

## 14. Exact Preliminary File Plan

### Backend:
1. `backend/alembic/versions/0015_ai_governance.py` [NEW]
2. `backend/app/core/permissions.py` [MODIFY]
3. `backend/app/models/ai_governance.py` [NEW]
4. `backend/app/models/__init__.py` [MODIFY]
5. `backend/app/schemas/ai_governance.py` [NEW]
6. `backend/app/services/ai_governance_service.py` [NEW]
7. `backend/app/api/v1/endpoints/ai_governance.py` [NEW]
8. `backend/app/api/v1/api.py` [MODIFY]
9. `backend/tests/test_ai_governance_domain.py` [NEW]
10. `backend/tests/test_ai_governance_api.py` [NEW]
11. `backend/tests/test_phase15_adversarial_security.py` [NEW]

### Frontend:
12. `frontend/src/types/index.ts` [MODIFY]
13. `frontend/src/lib/aiGovernanceService.ts` [NEW]
14. `frontend/src/pages/AIGovernancePage.tsx` [NEW]
15. `frontend/src/pages/AISystemDetailPage.tsx` [NEW]
16. `frontend/src/components/ai/AISystemModal.tsx` [NEW]
17. `frontend/src/components/ai/AIModelCardModal.tsx` [NEW]
18. `frontend/src/components/ai/AIDeploymentApprovalModal.tsx` [NEW]
19. `frontend/src/components/ai/AIStatusModal.tsx` [NEW]
20. `frontend/src/components/ai/AILineageCard.tsx` [NEW]
21. `frontend/src/App.tsx` [MODIFY]
22. `frontend/src/components/layout/Sidebar.tsx` [MODIFY]

---

## 15. Verification Gates & Release Criteria

- **Alembic Single-Head**: Head must cleanly advance from `0014` to `0015`.
- **Backend Regression Suite**: Maintain 594/594 existing passing tests + 100% passing on all new Phase 15 domain, API, and `ADV-P15` test vectors.
- **Frontend Production Build**: `npm run build` with 0 TypeScript/Vite compilation errors.
- **Dependency Audit**: **Zero** new npm or Python packages.
- **Git State**: Clean working tree with exact file staging at each checkpoint.

---

*PHASE 15 STAGE 0 ARCHITECTURAL SPECIFICATION COMPLETE. PRE-IMPLEMENTATION DISCOVERY AND SPECIFICATION ONLY. NO CODE MODIFICATIONS COMMENCED.*
