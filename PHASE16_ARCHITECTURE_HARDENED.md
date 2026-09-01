# PHASE 16 ARCHITECTURE SPECIFICATION (HARDENED)
## PRIVACY-GRC — Continuous Privacy Governance, Data Processing Inventory (RoPA), DPIA Risk Quantification & Cross-Border Data Transfer Management
### Enterprise GRC Architecture, Domain Foundation, Mathematical Authority & Adversarial Security

---

## 1. Executive Summary

Enterprise data environments across finance, healthcare, technology, and critical infrastructure face an unprecedented matrix of global privacy and data protection mandates. Frameworks such as the **General Data Protection Regulation (GDPR / Regulation (EU) 2016/679)**, the **California Consumer Privacy Act as amended by the CPRA (CCPA/CPRA)**, **ISO/IEC 27701:2019 (Privacy Information Management System)**, **NIST Privacy Framework 1.0**, **HIPAA Privacy & Security Rules**, and **EU AI Act Article 27 (Fundamental Rights Impact Assessments)** mandate formal data inventorying, records of processing activities (RoPA), data protection impact assessments (DPIAs), cross-border data transfer impact assessments (TIAs), and stringent Data Protection Officer (DPO) oversight.

**Phase 16: PRIVACY-GRC** establishes ControlSphere as an enterprise-grade Privacy & Data Protection System of Record. It enables organizations to catalog Data Assets, maintain Article 30 Records of Processing Activities (RoPA), quantify DPIA Inherent and Residual Risk Scores via server-authoritative mathematical formulas, govern Cross-Border Data Transfer Impact Assessments (TIA) across international jurisdiction tiers, enforce Four-Eyes DPO review gates, and trace end-to-end lineage across Business Processes (Phase 13), AI Systems & Models (Phase 15), Third-Party Processors/Vendors (Phase 9), Threat Exposures (Phase 14), Security Incidents (Phase 10), and CAPA Remediation Plans (Phase 11).

---

## 2. Repository Findings & Verified Current Baseline

The ControlSphere codebase has completed and verified Phases 1 through 15:

| Phase | Module / Domain | Status | Key Artifacts & Capabilities |
|---|---|---|---|
| **Phase 1** | Foundation & Multi-Tenancy | Complete | Multi-tenant schema, Organization & User models, JWT auth, RBAC permissions engine, SHA-256 tamper-evident audit logging. |
| **Phase 2** | Frameworks, Controls & Policies | Complete | NIST CSF 2.0, ISO 27001, SOC 2, HIPAA, CIS controls; OrganizationControl; Policy lifecycle management. |
| **Phase 3** | Evidence Management | Complete | Cryptographic SHA-256 evidence chain of custody, multi-control evidence linking, freshness and expiration tracking. |
| **Phase 4** | Assessments & Findings | Complete | Control assessments, effectiveness scoring, finding lifecycle, root cause analysis. |
| **Phase 5** | Qualitative Risk & Exceptions | Complete | 5×5 Qualitative Risk Register, Inherent vs Residual scoring, Exception workflows with Four-Eyes approvals. |
| **Phase 6** | Audit Engagements & Workpapers | Complete | Fieldwork management, workpaper reviews, PBC requests, immutable audit engagement lockouts. |
| **Phase 7** | Continuous Control Monitoring | Complete | Automated health scoring, metric telemetry collection, automated degraded/failing alert generation. |
| **Phase 8** | Multi-Framework Harmonization | Complete | Many-to-many cross-framework mapping, confidence scoring, redundancy reduction. |
| **Phase 9** | Third-Party & Vendor Risk (TPRM) | Complete | TPRM vendor catalog, tiering (Tier 1-4), security questionnaires, vendor evidence linking. |
| **Phase 10** | Security Incidents & Disclosure | Complete | Incident triage, regulatory disclosure countdowns (SEC 4-Day, GDPR 72-Hr, NYDFS), materiality governance. |
| **Phase 11** | Remediation Orchestration (CAPA) | Complete | CAPA orchestration, multi-task workflows, IV&V independent verification sign-off. |
| **Phase 12** | QUANTUM-GRC Cyber Risk | Complete | Monte Carlo financial loss simulation (Loss Event Frequency × Loss Magnitude), 95th/99th VaR, ROSI optimization. |
| **Phase 13** | RESILIENCE-GRC Operational Resilience | Complete | Business Process catalog, BIA (RTO/RPO/MTD), Tier 1-4 criticality, dependency mapping, outage loss estimation. |
| **Phase 14** | EXPOSURE-GRC Threat Exposure | Complete | Continuous threat exposure, CVE/CWE catalog, CVSS + EPSS + CISA KEV scoring, process blast radius scaling ($1.00\times - 1.25\times$), Four-Eyes SLA deferral governance. |
| **Phase 15** | AI-GRC AI & Model Governance | Complete | AI system register, model cards, Algorithmic Risk Index (ARI), EU AI Act classification, Four-Eyes deployment gates, cross-module lineage. |

- **Current Git Baseline**: Commit `b5883bf` (`chore: add one-click ControlSphere startup launcher`).
- **Alembic Linear Head**: `0015` (`0015_ai_governance.py`).
- **Backend Test Baseline**: 662/662 passing (0 failures).
- **Frontend Production Build**: 2,002 modules transformed (0 errors).
- **Working Tree**: Clean.

---

## 3. Verified Current Architecture

The platform architecture follows strict multi-tenant isolation and domain layering:

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
  Phase 9: TPRM & Cloud Vendors   ◄──────►  Phase 5: Qualitative Risk
             │                                       │
  Phase 14: Threat Exposure (CVE) ◄──────►  Phase 10: Security Incidents
             │                                       │
  Phase 13: Operational Resilience◄──────►  Phase 12: QUANTUM-GRC Financial Loss
             │                                       │
  Phase 15: AI System & Models   ◄──────►  Phase 11: CAPA Remediation
             │                                       │
             └───────────────────┬───────────────────┘
                                 ▼
           ┌───────────────────────────────────────────┐
           │   PHASE 16: PRIVACY-GRC (DATA PROTECTION) │
           │  • Data Asset & Personal Data Inventory   │
           │  • GDPR Art. 30 RoPA Activity Register    │
           │  • Server-Authoritative DPIA Risk Engine  │
           │  • Cross-Border Transfer Impact (TIA)     │
           │  • Four-Eyes DPO Approval Gatekeeping     │
           │  • Privacy Lineage (P9,10,11,13,14,15)    │
           └───────────────────────────────────────────┘
```

---

## 4. Enterprise Gap Analysis

| Enterprise GRC Dimension | Current Platform Capability | Identified Gap | Severity / Urgency |
|---|---|---|---|
| **1. Privacy & Data Protection Governance** | Personal data sensitivity flags in P15 and breach countdowns in P10 | No Article 30 Records of Processing Activities (RoPA), no DPIA assessment engine, no cross-border transfer impact assessments, no DPO sign-off gate. | **CRITICAL** |
| **2. Identity & Access Governance (IGA)** | RBAC permissions on platform users | No external IAM sync, no toxic entitlement matrix, no periodic access certification campaigns. | Medium |
| **3. Regulatory Change Management** | Framework crosswalk (Phase 8) | No live statutory regulatory change feed, no legislative delta analysis. | Medium |
| **4. Enterprise Risk Appetite & KRIs** | 5×5 Qualitative (P5) + Monte Carlo (P12) | No global KRI threshold alerting engine aggregating telemetry across all 15 phases. | Low |
| **5. Policy Attestation Campaigns** | Policy publishing & lifecycle (P2) | No employee acknowledgment campaigns, no quiz/awareness verification tracking. | Low |

---

## 5. Candidate Capability Evaluation & Selection

### Candidate Scoring Matrix (10-Point Scale):

| Evaluation Criteria (Weight) | Candidate 1: PRIVACY-GRC (RoPA / DPIA / TIA) | Candidate 2: IGA-GRC (Access Certification) | Candidate 3: REGCHANGE-GRC (Reg Change Tracking) | Candidate 4: ERM-KRI (Risk Appetite Aggregator) |
|---|:---:|:---:|:---:|:---:|
| **Enterprise Value (15%)** | 9.8 | 8.8 | 8.5 | 8.9 |
| **Cross-Module Synergy (15%)** | 10.0 | 8.0 | 8.8 | 9.2 |
| **Regulatory / Standards Relevance (15%)** | 10.0 | 8.5 | 9.2 | 8.0 |
| **Technical Depth (15%)** | 9.5 | 8.8 | 8.0 | 8.5 |
| **Security / Adversarial Test Depth (15%)** | 9.8 | 9.2 | 7.8 | 8.0 |
| **Architectural Novelty (10%)** | 9.5 | 8.0 | 8.0 | 7.8 |
| **Reuse of Existing Infrastructure (15%)** | 9.8 | 8.5 | 8.8 | 9.0 |
| **Weighted Total Score (100%)** | **9.77** | **8.54** | **8.44** | **8.49** |

### Selection Decision:
**Candidate 1: PRIVACY-GRC** is selected as the single official capability for **Phase 16**.

### Selection Rationale:
1. **Direct Regulatory Mandate**: GDPR Article 30 (RoPA) and Article 35 (DPIA), CCPA/CPRA, ISO 27701, and EU AI Act Article 27 mandate that high-risk AI workflows (Phase 15) and business processes (Phase 13) must have documented personal data processing registers and verified DPIAs.
2. **Deep Cross-Module Synergy**: Privacy governance directly binds Business Processes (Phase 13), AI Systems & Foundation Models (Phase 15), Third-Party Processors/Vendors (Phase 9), Threat Exposures (Phase 14), Security Incidents (Phase 10), and CAPA Remediation Plans (Phase 11).
3. **Four-Eyes DPO Authority**: Establishes formal Segregation of Duties where Data Protection Officers (DPO) independently evaluate and approve high-risk data processing activities and cross-border transfers.

---

## 6. Official Phase 16 Design

- **Official Name**: `PRIVACY-GRC — Continuous Privacy Governance, Data Processing Inventory (RoPA), DPIA Risk Quantification & Cross-Border Data Transfer Management`
- **Short Product / Module Name**: `PRIVACY-GRC`
- **Business Purpose**: Provide an enterprise System of Record for privacy compliance, automating Article 30 Records of Processing Activities (RoPA), Data Protection Impact Assessments (DPIA), Transfer Impact Assessments (TIA), and end-to-end data lineage tracking.

---

## 7. Domain Boundaries & Core Entities

### 7.1 Entities

1. **`DataAsset` (`data_assets` table)**:
   - Represents a data store, database, file repository, or SaaS data repository containing personal data.
   - Fields: `id`, `organization_id`, `asset_code`, `name`, `description`, `data_sensitivity_level`, `data_volume_range`, `storage_type`, `hosting_jurisdiction`, `is_encrypted_at_rest`, `is_encrypted_in_transit`, `retention_period_months`, `business_process_id` (FK $\to$ `business_processes`), `ai_system_id` (FK $\to$ `ai_systems`), `vendor_id` (FK $\to$ `vendors`), `owner_id` (FK $\to$ `users`), timestamps.

2. **`ProcessingActivity` (`processing_activities` table)**:
   - Represents a formal GDPR Article 30 Record of Processing Activities (RoPA).
   - Fields: `id`, `organization_id`, `activity_code`, `name`, `purpose_description`, `legal_basis`, `data_subject_categories` (JSON), `personal_data_categories` (JSON), `is_special_category_data`, `is_automated_decision_making`, `is_cross_border_transfer`, `transfer_mechanism`, `destination_country`, `security_measures_summary`, `dpo_approval_status`, `lifecycle_state`, `business_process_id` (FK $\to$ `business_processes`), `ai_system_id` (FK $\to$ `ai_systems`), `vendor_id` (FK $\to$ `vendors`), `data_controller_name`, `owner_id` (FK $\to$ `users`), `approved_by_dpo_id` (FK $\to$ `users`), `approved_at`, timestamps.

3. **`DPIAAssessment` (`dpia_assessments` table)**:
   - Represents a Data Protection Impact Assessment (GDPR Art. 35 / EU AI Act Art. 27).
   - Fields: `id`, `organization_id`, `assessment_code`, `processing_activity_id` (FK $\to$ `processing_activities`), `necessity_proportionality_score`, `data_subject_rights_score`, `safeguards_mitigation_score`, `inherent_risk_score`, `residual_risk_score`, `risk_band`, `automated_decision_making_risk`, `large_scale_monitoring_risk`, `vulnerable_subjects_risk`, `dpo_consultation_status`, `dpo_recommendation_notes`, `dpo_reviewed_by_id` (FK $\to$ `users`), `dpo_reviewed_at`, `prior_consultation_required`, `remediation_plan_id` (FK $\to$ `remediation_plans`), timestamps.

4. **`DataTransferAssessment` (`data_transfer_assessments` table)**:
   - Represents a Cross-Border Transfer Impact Assessment (TIA / Schrems II).
   - Fields: `id`, `organization_id`, `transfer_code`, `processing_activity_id` (FK $\to$ `processing_activities`), `source_country`, `destination_country`, `destination_jurisdiction_tier`, `transfer_mechanism`, `supplementary_safeguards_description`, `government_access_risk_score`, `legal_remedies_score`, `transfer_risk_index`, `approval_status`, `approved_by_id` (FK $\to$ `users`), `approved_at`, `audit_notes`, timestamps.

---

## 8. Core Enums

```python
class DataSensitivityLevel(str, enum.Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED_PII = "RESTRICTED_PII"
    SPECIAL_CATEGORY_SENSITIVE_PHI = "SPECIAL_CATEGORY_SENSITIVE_PHI"

class ProcessingLegalBasis(str, enum.Enum):
    CONSENT = "CONSENT"
    CONTRACT_PERFORMANCE = "CONTRACT_PERFORMANCE"
    LEGAL_OBLIGATION = "LEGAL_OBLIGATION"
    VITAL_INTERESTS = "VITAL_INTERESTS"
    PUBLIC_TASK = "PUBLIC_TASK"
    LEGITIMATE_INTERESTS = "LEGITIMATE_INTERESTS"

class DataSubjectCategory(str, enum.Enum):
    EMPLOYEES = "EMPLOYEES"
    CUSTOMERS = "CUSTOMERS"
    PATIENTS = "PATIENTS"
    STUDENTS = "STUDENTS"
    PROSPECTS = "PROSPECTS"
    VULNERABLE_INDIVIDUALS = "VULNERABLE_INDIVIDUALS"
    CHILDREN = "CHILDREN"
    SUPPLIERS = "SUPPLIERS"

class ProcessingLifecycleState(str, enum.Enum):
    DRAFT = "DRAFT"
    DPO_REVIEW = "DPO_REVIEW"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    ARCHIVED = "ARCHIVED"
    RETIRED = "RETIRED"

class TransferMechanism(str, enum.Enum):
    ADEQUACY_DECISION = "ADEQUACY_DECISION"
    STANDARD_CONTRACTUAL_CLAUSES_SCC = "STANDARD_CONTRACTUAL_CLAUSES_SCC"
    BINDING_CORPORATE_RULES_BCR = "BINDING_CORPORATE_RULES_BCR"
    DEROGATION_EXPLICIT_CONSENT = "DEROGATION_EXPLICIT_CONSENT"
    NONE_INTRA_EEA = "NONE_INTRA_EEA"

class JurisdictionRiskTier(str, enum.Enum):
    ADEQUATE_LOW_RISK = "ADEQUATE_LOW_RISK"
    MODERATE_SAFEGUARDS_REQUIRED = "MODERATE_SAFEGUARDS_REQUIRED"
    HIGH_RISK_SURVEILLANCE = "HIGH_RISK_SURVEILLANCE"
    PROHIBITED_TRANSFERS = "PROHIBITED_TRANSFERS"

class DPIARiskBand(str, enum.Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"
    CRITICAL = "CRITICAL"

class PrivacyApprovalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"
```

---

## 9. Server-Authoritative Mathematical Risk Engines

The frontend perform **zero authoritative risk calculations**. The backend domain engine calculates all indices deterministically:

### 9.1 DPIA Inherent Risk Score (IRS)
$$\text{IRS} = \min\left(100.0, (\text{BaseSensitivity} \times \text{VolumeMultiplier} \times \text{SpecialCategoryMultiplier}) + \text{TriggerPenalty}\right)$$

Where:
- **$\text{BaseSensitivity}$**:
  - `SPECIAL_CATEGORY_SENSITIVE_PHI` = $65.0$
  - `RESTRICTED_PII` = $40.0$
  - `CONFIDENTIAL` = $20.0$
  - `INTERNAL` = $5.0$
  - `PUBLIC` = $0.0$
- **$\text{VolumeMultiplier}$**:
  - $> 1,000,000$ data subjects: $1.30\times$
  - $10,000 - 1,000,000$ data subjects: $1.15\times$
  - $< 10,000$ data subjects: $1.00\times$
- **$\text{SpecialCategoryMultiplier}$**:
  - $1.25\times$ if special category, children, or patient data is processed; otherwise $1.00\times$.
- **$\text{TriggerPenalty}$**:
  - $+10.0$ for Automated Decision Making / AI profiling.
  - $+10.0$ for Large Scale Monitoring / Tracking.
  - $+10.0$ for Vulnerable Subjects (Children, Patients, Employees).
  - Maximum trigger penalty capped at $+30.0$.

### 9.2 DPIA Residual Risk Score (RRS)
$$\text{RRS} = \max\left(0.0, \min\left(100.0, \text{IRS} \times (1.0 - \text{SafeguardsMitigationRate}) + \text{ThreatExposurePenalty}\right)\right)$$

Where:
- **$\text{SafeguardsMitigationRate}$** $\in [0.0, 0.70]$ based on verified technical controls (Encryption at Rest: $+0.15$, Encryption in Transit: $+0.10$, Pseudonymization/Anonymization: $+0.20$, Granular Access Control: $+0.15$, Strict Retention Enforcement: $+0.10$).
- **$\text{ThreatExposurePenalty}$**: $+15.0$ if linked data assets have unresolved Critical/High Threat Exposures (Phase 14).

### 9.3 Transfer Risk Index (TRI)
$$\text{TRI} = \min\left(100.0, \max\left(0.0, (\text{JurisdictionBase} \times \text{MechanismMultiplier}) - \text{SupplementaryMeasures}\right)\right)$$

- **$\text{JurisdictionBase}$**:
  - `PROHIBITED_TRANSFERS` = $100.0$
  - `HIGH_RISK_SURVEILLANCE` = $75.0$
  - `MODERATE_SAFEGUARDS_REQUIRED` = $40.0$
  - `ADEQUATE_LOW_RISK` = $10.0$
- **$\text{MechanismMultiplier}$**:
  - `NONE_INTRA_EEA` = $0.00\times$
  - `ADEQUACY_DECISION` = $0.50\times$
  - `BINDING_CORPORATE_RULES_BCR` = $0.80\times$
  - `STANDARD_CONTRACTUAL_CLAUSES_SCC` = $1.00\times$
  - `DEROGATION_EXPLICIT_CONSENT` = $1.20\times$
- **$\text{SupplementaryMeasures}$**: $+0.0$ to $+30.0$ for end-to-end encryption with EU key custody and contractual transparency clauses.

---

## 10. Lifecycle State Machines & Governed Transitions

### 10.1 Processing Activity (RoPA) State Machine
```
[DRAFT] ──────► [DPO_REVIEW] ──────► [ACTIVE] ──────► [ARCHIVED] / [RETIRED]
  ▲                  │
  │                  ▼
  └──────────── [SUSPENDED]
```
- **Legal Transitions**:
  - `DRAFT` $\to$ `DPO_REVIEW`, `ARCHIVED`
  - `DPO_REVIEW` $\to$ `ACTIVE` (Requires DPO Approval), `DRAFT`, `SUSPENDED`
  - `ACTIVE` $\to$ `SUSPENDED`, `ARCHIVED`, `RETIRED`
  - `SUSPENDED` $\to$ `DPO_REVIEW`, `ARCHIVED`, `RETIRED`
  - `ARCHIVED` $\to$ `RETIRED`
  - `RETIRED` $\to$ (Immutable terminal state)

---

## 11. RBAC & Four-Eyes Segregation of Duties (SoD)

### 11.1 Permissions
- `privacy:read` — View data assets, RoPA records, DPIAs, and transfer assessments.
- `privacy:manage` — Create and edit data assets, processing activities, and DPIA drafts.
- `privacy:assess` — Perform and submit DPIA risk assessments and transfer impact reviews.
- `privacy:approve` — Execute authoritative DPO approval on high-risk DPIAs and cross-border transfers.

### 11.2 Role-to-Permission Mapping:
- `ADMIN`: Full access & approval authority.
- `MANAGER`: Full operational management & approval authority.
- `GRC_ANALYST`: Manage, catalog, and submit assessments (no approval).
- `SECURITY_ANALYST`: Assess technical safeguards & view data assets (no approval).
- `AUDITOR` / `VIEWER`: Strict read-only presentation across all privacy records.

### 11.3 Four-Eyes Segregation of Duties (SoD) Invariant:
If `user.id == dpia.created_by_id`, the user **cannot** approve the DPIA. The system returns `HTTP 403 Forbidden` with:
`"Segregation of Duties Violation: The creator of a DPIA assessment cannot serve as the approving Data Protection Officer (DPO)."`

---

## 12. Tenant Isolation & Immutability Models

1. **Strict Tenant Isolation**: All queries filter by `organization_id = current_user.organization_id`.
2. **Cross-Tenant Foreign-Key Validation**: Before binding `business_process_id`, `ai_system_id`, `vendor_id`, or `remediation_plan_id`, the backend validates that the referenced entity belongs strictly to the authenticated tenant.
3. **Immutable Audit Trail**: All status changes, DPO approvals, and RoPA state transitions emit tamper-evident SHA-256 logs to `audit_logs`.
4. **Retired Record Protection**: Records in `RETIRED` state are permanently locked against modifications.

---

## 13. Cross-Module Integration Architecture

| Integration Anchor | Target Phase | Architecture & Foreign-Key Linkage | Enterprise Business Value |
|---|---|---|---|
| **Business Resilience** | **Phase 13** | `DataAsset.business_process_id` & `ProcessingActivity.business_process_id` | Maps RoPA activities and data stores directly to critical business processes. |
| **AI Governance** | **Phase 15** | `DataAsset.ai_system_id` & `ProcessingActivity.ai_system_id` | Satisfies EU AI Act Article 27 & GDPR Article 35 mandates for High-Risk AI systems. |
| **Vendor Risk (TPRM)** | **Phase 9** | `DataAsset.vendor_id` & `ProcessingActivity.vendor_id` | Tracks third-party data processors, sub-processors, and DPA compliance. |
| **Threat Exposure** | **Phase 14** | `DataAsset` $\leftrightarrow$ `ThreatExposure` correlation | Injects exposure penalties into DPIA residual risk scores when data assets have unpatched CVEs. |
| **Incident Management** | **Phase 10** | `ProcessingActivity` $\leftrightarrow$ `Incident` breach linkage | Evaluates data subject harm and personal data categories during breach disclosure countdowns. |
| **CAPA Remediation** | **Phase 11** | `DPIAAssessment.remediation_plan_id` | Automatically links high-risk DPIA mitigation tasks to audited CAPA remediation workflows. |
| **Organization Controls** | **Phase 2** | Cross-referenced ISO 27701 & NIST Privacy controls | Maps privacy obligations to existing organizational controls and policies. |

---

## 14. Regulatory & Standards Mapping

- **GDPR (Regulation (EU) 2016/679)**:
  - Article 30: Records of Processing Activities (RoPA)
  - Article 35: Data Protection Impact Assessment (DPIA)
  - Article 36: Prior Consultation with Supervisory Authorities
  - Chapter V (Articles 44–49): Transfers of Personal Data to Third Countries
- **EU Artificial Intelligence Act (Regulation 2024/1689)**:
  - Article 27: Fundamental Rights Impact Assessment for High-Risk AI Systems
- **CCPA / CPRA (Cal. Civ. Code § 1798.100 et seq.)**:
  - Data inventories, sensitive personal information (SPI) governance, and cybersecurity audit requirements.
- **ISO/IEC 27701:2019**:
  - Privacy Information Management System (PIMS) controls for Controllers and Processors.
- **NIST Privacy Framework Version 1.0**:
  - Identify-P, Govern-P, Control-P, Communicate-P, and Protect-P categories.

---

## 15. Dedicated Adversarial Security Matrix (25 Vectors)

| ID | Attack Vector / Security Invariant | Expected Status | Mitigation / Assertion |
|---|---|:---:|---|
| **ADV-P16-01** | Cross-tenant RoPA processing activity access (IDOR) | `404 Not Found` | Strict tenant filtering on `ProcessingActivity` query. |
| **ADV-P16-02** | Cross-tenant Data Asset read/mutation attempt | `404 Not Found` | Strict tenant filtering on `DataAsset` queries. |
| **ADV-P16-03** | Cross-tenant DPIA assessment access or update | `404 Not Found` | Strict tenant filtering on `DPIAAssessment` queries. |
| **ADV-P16-04** | Cross-tenant Data Transfer assessment tampering | `404 Not Found` | Strict tenant filtering on `DataTransferAssessment` queries. |
| **ADV-P16-05** | Unauthorized RoPA creation by `VIEWER` / `AUDITOR` | `403 Forbidden` | `Permission.PRIVACY_MANAGE` enforced via dependency. |
| **ADV-P16-06** | Unauthorized DPIA assessment submission by unprivileged user | `403 Forbidden` | `Permission.PRIVACY_ASSESS` enforced via dependency. |
| **ADV-P16-07** | Privilege escalation attempt to self-assign DPO approval authority | `403 Forbidden` | `Permission.PRIVACY_APPROVE` enforced on DPO endpoints. |
| **ADV-P16-08** | Four-Eyes DPO self-approval bypass (creator approving own DPIA) | `403 Forbidden` | Server checks `user.id == dpia.created_by_id`. |
| **ADV-P16-09** | Four-Eyes cross-border transfer self-approval bypass | `403 Forbidden` | Server checks `user.id == transfer.requested_by_id`. |
| **ADV-P16-10** | Approval replay attack on already approved/rejected DPIA | `409 Conflict` | Server rejects re-review of finalized approvals. |
| **ADV-P16-11** | Client risk score injection bypass (falsified low IRS/RRS in payload) | `Ignored/Overwritten` | Server recalculates IRS and RRS authoritatively. |
| **ADV-P16-12** | Client Transfer Risk Index (TRI) override attempt | `Ignored/Overwritten` | Server recalculates TRI authoritatively from jurisdiction tier. |
| **ADV-P16-13** | Mathematical boundary attack (negative scores, volume $> 10^9$) | `422 Unprocessable` | Pydantic validators enforce strictly bounded ranges. |
| **ADV-P16-14** | Illegal lifecycle state jump (e.g. `DRAFT` $\to$ `RETIRED`) | `400 Bad Request` | State machine validates legal transition matrix. |
| **ADV-P16-15** | Mutation attempt on `RETIRED` processing activity | `400 Bad Request` | Immutability guard rejects mutations on retired activities. |
| **ADV-P16-16** | Malicious foreign-key reference to cross-tenant `BusinessProcess` (P13) | `404 / 422` | Cross-tenant foreign key existence validator. |
| **ADV-P16-17** | Malicious foreign-key reference to cross-tenant `AISystem` (P15) | `404 / 422` | Cross-tenant foreign key existence validator. |
| **ADV-P16-18** | Malicious foreign-key reference to cross-tenant `Vendor` (P9) | `404 / 422` | Cross-tenant foreign key existence validator. |
| **ADV-P16-19** | Malicious foreign-key reference to cross-tenant `RemediationPlan` (P11) | `404 / 422` | Cross-tenant foreign key existence validator. |
| **ADV-P16-20** | Unauthenticated API access across Phase 16 endpoints | `401 Unauthorized` | JWT bearer authentication dependency enforced. |
| **ADV-P16-21** | Expired or forged JWT token access | `401 Unauthorized` | Cryptographic signature & expiration validation. |
| **ADV-P16-22** | SQL injection payloads in search, category, and filter queries | `Sanitized/Escaped` | SQLAlchemy parameterized statements protect all queries. |
| **ADV-P16-23** | Mass assignment attack injecting `dpo_approval_status` in create/update | `Ignored` | Pydantic input schemas exclude approval status fields. |
| **ADV-P16-24** | Audit log generation and event emission verification | `Verified` | All lifecycle and DPO actions emit SHA-256 audit logs. |
| **ADV-P16-25** | Deletion block for Active RoPA activities with linked active DPIAs | `400 Bad Request` | Relational integrity guard blocks destructive cascades. |

---

## 16. Staged Implementation Plan

### Stage 1: Database & Domain Foundation
- **Objective**: Create database migration `0016_privacy_governance.py`, SQLAlchemy models, Pydantic schemas, server-authoritative mathematical engine, domain service layer, permissions, and domain unit tests.
- **Verification Gate**:
  - Alembic linear migration head: `0016`.
  - All domain tests passing.
  - Zero regression failures across Phase 1–15 tests.

### Stage 2: REST API + Cross-Module Integration + Adversarial Security
- **Objective**: Implement FastAPI router under `/api/v1/privacy`, wire endpoints into main API router, implement cross-module validators (P9, P11, P13, P14, P15), write API tests and all 25 adversarial security tests (`ADV-P16-01` through `ADV-P16-25`).
- **Verification Gate**:
  - Full backend test suite passing ($\ge 690$ tests).
  - 25/25 adversarial security vectors verified.

### Stage 3: Frontend Governance Workspace
- **Objective**: Implement TypeScript types in `frontend/src/types/index.ts`, create `frontend/src/lib/privacyService.ts`, build pages (`PrivacyPage.tsx`, `ProcessingActivityDetailPage.tsx`, `DPIADetailPage.tsx`), build component suite (`DataAssetModal.tsx`, `ProcessingActivityModal.tsx`, `DPIAModal.tsx`, `DPIARiskCard.tsx`, `DataTransferCard.tsx`, `PrivacyLineageCard.tsx`), wire routes in `App.tsx`, and add navigation in `Sidebar.tsx`.
- **Verification Gate**:
  - `npm run build` succeeds with 0 TypeScript/Vite errors.
  - Full backend regression passing.

---

## 17. Exact File Plan

### 17.1 Files to Create (Stage 1 to 3)

#### Backend:
1. `backend/alembic/versions/0016_privacy_governance.py`
2. `backend/app/models/privacy.py`
3. `backend/app/schemas/privacy.py`
4. `backend/app/services/privacy_service.py`
5. `backend/app/api/v1/endpoints/privacy.py`
6. `backend/tests/test_privacy_domain.py`
7. `backend/tests/test_privacy_api.py`
8. `backend/tests/test_phase16_adversarial_security.py`

#### Frontend:
9. `frontend/src/lib/privacyService.ts`
10. `frontend/src/pages/PrivacyPage.tsx`
11. `frontend/src/pages/ProcessingActivityDetailPage.tsx`
12. `frontend/src/pages/DPIADetailPage.tsx`
13. `frontend/src/components/privacy/DataAssetModal.tsx`
14. `frontend/src/components/privacy/ProcessingActivityModal.tsx`
15. `frontend/src/components/privacy/DPIAModal.tsx`
16. `frontend/src/components/privacy/DPIARiskCard.tsx`
17. `frontend/src/components/privacy/DataTransferCard.tsx`
18. `frontend/src/components/privacy/PrivacyLineageCard.tsx`

### 17.2 Files to Modify

1. `backend/app/core/permissions.py` — Add `PRIVACY_READ`, `PRIVACY_MANAGE`, `PRIVACY_ASSESS`, `PRIVACY_APPROVE`.
2. `backend/app/models/__init__.py` — Export Phase 16 privacy models.
3. `backend/app/api/v1/api.py` — Register `privacy.router`.
4. `frontend/src/types/index.ts` — Add Phase 16 TypeScript interfaces and enums.
5. `frontend/src/App.tsx` — Add `/privacy`, `/privacy/activities/:id`, `/privacy/dpia/:id` routes.
6. `frontend/src/components/layout/Sidebar.tsx` — Add `Privacy & Data Protection` navigation link.

---

## 18. Architectural Invariants & Scope Boundaries

1. **Zero External NPM / Python Dependencies**: Utilize standard Python mathematical libraries and pure Tailwind/SVG components.
2. **Authoritative Calculation Lock**: All risk formulas (IRS, RRS, TRI, PEI) must be calculated exclusively server-side.
3. **Four-Eyes Segregation of Duties**: DPO review is strictly enforced server-side.
4. **Tenant Isolation**: Every database interaction filters by `organization_id`.
5. **Phase 16 Specification Freeze**: No implementation shall begin until Stage 0 is approved.

---
