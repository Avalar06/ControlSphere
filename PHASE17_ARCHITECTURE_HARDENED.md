# PHASE 17 ARCHITECTURE SPECIFICATION (HARDENED)
## SUPPLYCHAIN-GRC — Software Supply Chain Governance, Software Bill of Materials (SBOM) Inventory, Component Risk Quantification & Open-Source License Compliance
### Enterprise GRC Architecture, Domain Foundation, Mathematical Authority & Adversarial Security

---

## 1. Executive Summary

### 1.1 Phase 17 Title
**PHASE 17: SUPPLYCHAIN-GRC — Software Supply Chain Risk Management, Software Bill of Materials (SBOM) Governance, Open Source Dependency Risk Quantification & Prohibited License Compliance**

### 1.2 Purpose & Business Objective
Modern enterprise IT and digital infrastructure depend heavily on thousands of third-party, commercial, and open-source software (OSS) packages. Recent systemic supply chain compromises (e.g., Log4j, SolarWinds, XZ Utils, Codecov) and global regulatory directives have transformed Software Supply Chain Risk Management (SSCRM) into a mandatory board-level governance pillar:
- **US Executive Order 14028 (Improving the Nation's Cybersecurity)** & **NIST SP 800-218 (Secure Software Development Framework - SSDF)**: Mandate verifiable Software Bill of Materials (SBOM), component provenance, and vulnerability tracking for critical software.
- **European Union Cyber Resilience Act (EU CRA / Regulation 2024/2847)**: Mandates automated SBOM generation, end-to-end vulnerability lifecycle handling, and strict supply chain due diligence for digital products with elements.
- **NTIA / CISA SBOM Minimum Elements Framework**: Establishes standard data formats (SPDX / CycloneDX), component naming conventions (Package URL / PURL), versioning, and cryptographic integrity verification.
- **Open Source License Governance & Intellectual Property (IP) Protection**: Mandates continuous scanning and governance against restrictive copyleft (e.g., GNU GPLv3, AGPLv3) and commercial conflict licenses embedded in proprietary enterprise applications.

**Phase 17: SUPPLYCHAIN-GRC** establishes ControlSphere as an enterprise-grade Software Supply Chain System of Record. It enables organizations to catalog Software Products, ingest and maintain Software Bill of Materials (SBOM) documents, index transitive software components, quantify Component Risk Indices (CRI) and Product Supply Chain Exposure Indices (SCEI) via server-authoritative mathematical formulas, detect prohibited OSS licenses, enforce Four-Eyes component risk exemptions, and trace end-to-end lineage across Threat Exposures & CVEs (Phase 14), AI Model Dependencies (Phase 15), Third-Party Software Vendors (Phase 9), Operational Business Processes (Phase 13), and CAPA Remediation Plans (Phase 11).

### 1.3 Why Phase 17 Follows Phase 16 (PRIVACY-GRC)
ControlSphere's architectural progression transitions from foundational enterprise governance to specialized risk domains:
1. **Phases 1–11**: Core GRC Foundation, NIST CSF Controls, Cryptographic Evidence, Audit Workpapers, Continuous Monitoring, TPRM, Incidents, and Remediation Orchestration.
2. **Phase 12 (QUANTUM-GRC)**: Financial Cyber Risk Quantification (Monte Carlo FAIR).
3. **Phase 13 (RESILIENCE-GRC)**: Operational Business Processes, BIA, RTO/RPO, Interdependency Graphing.
4. **Phase 14 (EXPOSURE-GRC)**: Continuous Threat Exposure Management (CTEM), Vulnerability Prioritization (CVSS + EPSS + CISA KEV).
5. **Phase 15 (AI-GRC)**: Artificial Intelligence Governance, EU AI Act Classification, Model Cards, Algorithmic Risk (ARI).
6. **Phase 16 (PRIVACY-GRC)**: Data Processing Inventory (RoPA), DPIA Risk (IRS/RRS), Cross-Border Transfers (TIA).
7. **Phase 17 (SUPPLYCHAIN-GRC)**: Bridges software engineering artifacts, open-source dependencies, and external software components with vulnerability intelligence (Phase 14), vendor risk (Phase 9), operational resilience (Phase 13), and AI model libraries (Phase 15).

---

## 2. Scope & Boundaries

### 2.1 In Scope
1. **Software Product Catalog**: Multi-tenant register of internal applications, microservices, third-party off-the-shelf (COTS) software, and firmware.
2. **Software Bill of Materials (SBOM) Ingestion & Versioning**: Structured SBOM manifest tracking supporting CycloneDX and SPDX metadata standards, component counts, specification versions, and cryptographic SHA-256 integrity digests.
3. **Software Component Inventory**: Hierarchical component registry (Direct vs Transitive dependencies, Package URL / PURL, package ecosystems: npm, PyPI, Maven, Go, Cargo, NuGet, Docker).
4. **Component Vulnerability Linking**: Associating components with Phase 14 Threat Exposures (CVEs), tracking exploitability, fix availability, and reachability.
5. **Open Source License Classification & Policy Engine**: Evaluating license categories (Permissive, Weak Copyleft, Strong Copyleft/AGPL, Prohibited, Commercial Conflict) and policy violation triggers.
6. **Mathematical Risk Engine**: Server-authoritative calculation of Component Risk Index (CRI) and Product Supply Chain Exposure Index (SCEI) incorporating vulnerability severity, exploitability (EPSS/KEV), dependency depth penalties, and license risk weights.
7. **Four-Eyes Supply Chain Exemption Workflow**: Segregation-of-Duties approval workflow for accepting high-risk dependencies or copyleft licenses.
8. **Cross-Module GRC Traceability**: Lineage links to Phase 14 (Exposures), Phase 15 (AI Systems), Phase 9 (Vendors), Phase 13 (Business Processes), and Phase 11 (Remediation).

### 2.2 Out of Scope
1. Direct binary unpacking or proprietary decompilation engines (SBOMs are ingested as structured manifests).
2. Live runtime kernel packet sniffing (governed by continuous monitoring in Phase 7).
3. Automated source code rewriting or package pull request auto-merging (governed by CAPA remediation workflows in Phase 11).

---

## 3. Domain Model & Entities

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Phase 17: SUPPLYCHAIN-GRC                             │
└─────────────────────────────────────────────────────────────────────────────┘
  SoftwareProduct (1) ────────── (N) SBOMDocument
         │                               │
         │ (1)                           │ (1)
         │                               │
         ▼ (N)                           ▼ (N)
  SupplyChainExemption            SoftwareComponent (1) ── (N) ComponentVulnLink
         │                               │                         │
         │ (Links to)                    │ (Classifies)            │ (References)
         ▼                               ▼                         ▼
  Phase 11 (CAPA)               LicensePolicy             Phase 14 (Threat Exposure)
  Phase 9  (TPRM)               Phase 15 (AI-GRC)
  Phase 13 (Resilience)
```

### 3.1 Entity Definitions

#### 1. `SoftwareProduct`
- **Purpose**: Represents a governed software application, service, or digital product.
- **Primary Key**: `id` (Integer, autoincrement).
- **Tenant Scope**: `organization_id` (Integer, FK -> `organizations.id`, indexed).
- **Core Fields**:
  - `product_code` (String(64), unique per tenant, e.g., `PROD-CORE-001`).
  - `name` (String(255)).
  - `description` (Text, nullable).
  - `product_type` (Enum: `INTERNAL_APPLICATION`, `MICROSERVICE`, `COMMERCIAL_COTS`, `FIRMWARE_IOT`, `AI_MODEL_PIPELINE`, `OPEN_SOURCE_LIBRARY`).
  - `criticality_tier` (Enum: `TIER_1_CRITICAL`, `TIER_2_MAJOR`, `TIER_3_MODERATE`, `TIER_4_LOW`).
  - `business_process_id` (Integer, nullable, FK -> `business_processes.id`).
  - `ai_system_id` (Integer, nullable, FK -> `ai_systems.id`).
  - `vendor_id` (Integer, nullable, FK -> `vendors.id`).
  - `lifecycle_state` (Enum: `DRAFT`, `ACTIVE`, `DEPRECATED`, `RETIRED`).
  - `owner_id` (Integer, FK -> `users.id`).
  - `supply_chain_exposure_index` (Float, server-calculated, default `0.0`).
  - `total_components_count` (Integer, server-calculated, default `0`).
  - `vulnerable_components_count` (Integer, server-calculated, default `0`).
  - `policy_violations_count` (Integer, server-calculated, default `0`).
  - `created_at`, `updated_at` (DateTime, UTC).

#### 2. `SBOMDocument`
- **Purpose**: Represents an immutable or versioned Software Bill of Materials manifest.
- **Primary Key**: `id` (Integer, autoincrement).
- **Tenant Scope**: `organization_id` (Integer, FK -> `organizations.id`, indexed).
- **Core Fields**:
  - `software_product_id` (Integer, FK -> `software_products.id`, indexed).
  - `sbom_code` (String(64), unique per tenant, e.g., `SBOM-CORE-2026.1`).
  - `version` (String(32), e.g., `1.4.2`).
  - `format_standard` (Enum: `CYCLONEDX_JSON`, `CYCLONEDX_XML`, `SPDX_JSON`, `SPDX_TAG_VALUE`, `CUSTOM_JSON`).
  - `spec_version` (String(16), e.g., `1.5`, `2.3`).
  - `sha256_hash` (String(64), immutable cryptographic digest).
  - `author_name` (String(255), nullable).
  - `tool_name` (String(255), nullable, e.g., `Syft v1.2`, `Trivy v0.50`).
  - `status` (Enum: `ACTIVE`, `SUPERSEDED`, `ARCHIVED`).
  - `component_count` (Integer, default `0`).
  - `created_by_id` (Integer, FK -> `users.id`).
  - `created_at`, `updated_at` (DateTime, UTC).

#### 3. `SoftwareComponent`
- **Purpose**: Represents an individual direct or transitive software package within an SBOM.
- **Primary Key**: `id` (Integer, autoincrement).
- **Tenant Scope**: `organization_id` (Integer, FK -> `organizations.id`, indexed).
- **Core Fields**:
  - `sbom_document_id` (Integer, FK -> `sbom_documents.id`, indexed).
  - `component_name` (String(255), e.g., `axios`, `cryptography`, `log4j-core`).
  - `version` (String(64), e.g., `1.6.8`, `2.14.1`).
  - `purl` (String(512), Package URL format, e.g., `pkg:npm/axios@1.6.8`, `pkg:pypi/cryptography@42.0.5`).
  - `ecosystem` (Enum: `NPM`, `PYPI`, `MAVEN`, `GO`, `CARGO`, `NUGET`, `DOCKER`, `COMPOSER`, `GENERIC`).
  - `dependency_depth` (Integer, `1` = Direct, `2+` = Transitive).
  - `supplier_name` (String(255), nullable).
  - `declared_license` (String(128), e.g., `MIT`, `Apache-2.0`, `GPL-3.0-only`, `AGPL-3.0-or-later`, `UNKNOWN`).
  - `license_category` (Enum: `PERMISSIVE`, `WEAK_COPYLEFT`, `STRONG_COPYLEFT`, `PROHIBITED`, `UNCLASSIFIED`).
  - `is_license_prohibited` (Boolean, default `False`).
  - `component_risk_index` (Float, server-calculated, scale 0-100).
  - `max_vulnerability_score` (Float, server-calculated, scale 0-100).
  - `vulnerabilities_count` (Integer, default `0`).
  - `is_exempted` (Boolean, default `False`).
  - `created_at`, `updated_at` (DateTime, UTC).

#### 4. `ComponentVulnerabilityLink`
- **Purpose**: Maps a software component to an authoritative Phase 14 Threat Exposure / CVE.
- **Primary Key**: `id` (Integer, autoincrement).
- **Tenant Scope**: `organization_id` (Integer, FK -> `organizations.id`, indexed).
- **Core Fields**:
  - `component_id` (Integer, FK -> `software_components.id`, indexed).
  - `vulnerability_id` (Integer, nullable, FK -> `threat_exposures.id`, indexed).
  - `cve_identifier` (String(64), e.g., `CVE-2021-44228`).
  - `severity_score` (Float, CVSS v3.1 base score, 0.0 - 10.0).
  - `is_exploitable` (Boolean, default `False`).
  - `is_reachable` (Boolean, default `True`).
  - `fix_version` (String(64), nullable).
  - `remediation_plan_id` (Integer, nullable, FK -> `remediation_plans.id`).
  - `created_at` (DateTime, UTC).

#### 5. `LicenseCompliancePolicy`
- **Purpose**: Configures organizational license governance rules and prohibited license categories.
- **Primary Key**: `id` (Integer, autoincrement).
- **Tenant Scope**: `organization_id` (Integer, FK -> `organizations.id`, indexed).
- **Core Fields**:
  - `license_identifier` (String(64), unique per tenant, e.g., `GPL-3.0-only`, `AGPL-3.0-or-later`).
  - `name` (String(255)).
  - `category` (Enum: `PERMISSIVE`, `WEAK_COPYLEFT`, `STRONG_COPYLEFT`, `PROHIBITED`).
  - `is_prohibited` (Boolean, default `False`).
  - `risk_penalty_points` (Float, 0.0 - 30.0).
  - `description` (Text, nullable).
  - `created_at`, `updated_at` (DateTime, UTC).

#### 6. `SupplyChainExemption`
- **Purpose**: Four-Eyes governed exception mechanism for approving high-risk components or copyleft licenses.
- **Primary Key**: `id` (Integer, autoincrement).
- **Tenant Scope**: `organization_id` (Integer, FK -> `organizations.id`, indexed).
- **Core Fields**:
  - `exemption_code` (String(64), unique per tenant, e.g., `SC-EX-2026-001`).
  - `software_product_id` (Integer, FK -> `software_products.id`, indexed).
  - `component_id` (Integer, FK -> `software_components.id`, indexed).
  - `reason` (Text, minimum 10 chars).
  - `compensating_controls` (Text).
  - `requested_by_id` (Integer, FK -> `users.id`).
  - `reviewed_by_id` (Integer, nullable, FK -> `users.id`).
  - `approval_status` (Enum: `PENDING`, `APPROVED`, `REJECTED`, `REVOKED`, `EXPIRED`).
  - `reviewer_notes` (Text, nullable).
  - `valid_until` (DateTime, nullable).
  - `reviewed_at` (DateTime, nullable).
  - `created_at`, `updated_at` (DateTime, UTC).

---

## 4. Database Architecture & Alembic Migration

### 4.1 Migration File
`backend/alembic/versions/0017_supply_chain_governance.py`
`down_revision = "0016"`

### 4.2 Tables & Constraints
1. **`software_products`**:
   - Primary key: `id`
   - Unique: `(organization_id, product_code)`
   - Indexes: `ix_software_products_org_id`, `ix_software_products_lifecycle_state`
2. **`sbom_documents`**:
   - Primary key: `id`
   - Unique: `(organization_id, sbom_code)`
   - Indexes: `ix_sbom_documents_product_id`, `ix_sbom_documents_org_id`
3. **`software_components`**:
   - Primary key: `id`
   - Indexes: `ix_software_components_sbom_id`, `ix_software_components_org_id`, `ix_software_components_purl`
4. **`component_vulnerability_links`**:
   - Primary key: `id`
   - Indexes: `ix_comp_vuln_component_id`, `ix_comp_vuln_vulnerability_id`
5. **`license_compliance_policies`**:
   - Primary key: `id`
   - Unique: `(organization_id, license_identifier)`
   - Indexes: `ix_license_policies_org_id`
6. **`supply_chain_exemptions`**:
   - Primary key: `id`
   - Unique: `(organization_id, exemption_code)`
   - Indexes: `ix_sc_exemptions_product_id`, `ix_sc_exemptions_component_id`, `ix_sc_exemptions_status`

---

## 5. Mathematical & Risk Engine

All calculations are **strictly deterministic, server-authoritative, and executed exclusively on the backend**.

### 5.1 Component Inherent Vulnerability Score ($V_{score}$)
Given component vulnerability links $v \in \text{Vulns}(c)$:
$$V_{score} = \begin{cases} 0.0 & \text{if } |\text{Vulns}(c)| = 0 \\ \min\left(100.0, \max_{v} \left(\text{CVSS}_v \times 10.0 \times E_v\right) + \sum_{v \neq \max} \left(\text{CVSS}_v \times 1.5\right)\right) & \text{if } |\text{Vulns}(c)| > 0 \end{cases}$$
Where $E_v = 1.25$ if actively exploitable (CISA KEV / EPSS $> 0.20$), otherwise $1.00$.

### 5.2 Dependency Depth Penalty Multiplier ($\delta_d$)
Transitive dependencies carry higher operational opacity and remediation difficulty:
$$\delta_d = \begin{cases} 1.00 & \text{if } \text{depth} = 1 \text{ (Direct)} \\ 1.00 + \min\left(0.30, 0.10 \times (\text{depth} - 1)\right) & \text{if } \text{depth} \ge 2 \text{ (Transitive)} \end{cases}$$

### 5.3 License Risk Points ($L_{risk}$)
$$L_{risk} = \begin{cases} 0.0 & \text{for PERMISSIVE (MIT, Apache-2.0, BSD)} \\ 10.0 & \text{for WEAK\_COPYLEFT (LGPL, MPL)} \\ 25.0 & \text{for STRONG\_COPYLEFT (GPLv2, GPLv3, AGPLv3)} \\ 30.0 & \text{for PROHIBITED / COMMERCIAL\_CONFLICT} \end{cases}$$

### 5.4 Composite Component Risk Index ($CRI \in [0.0, 100.0]$)
If the component has an active `APPROVED` exemption, a $0.50\times$ mitigation factor applies:
$$CRI = \min\left(100.0, \left(V_{score} + L_{risk}\right) \times \delta_d \times (\text{if exempted } 0.50 \text{ else } 1.00)\right)$$

### 5.5 Product Supply Chain Exposure Index ($SCEI \in [0.0, 100.0]$)
For software product $P$ containing components $C$:
$$SCEI = \begin{cases} 0.0 & \text{if } |C| = 0 \\ \min\left(100.0, \max_{c \in C}(CRI_c) \times 0.60 + \left(\frac{1}{|C|}\sum_{c \in C} CRI_c\right) \times 0.40\right) & \text{if } |C| > 0 \end{cases}$$

### 5.6 Severity Risk Bands
- **`LOW`**: $0.0 \le \text{Score} < 25.0$
- **`MODERATE`**: $25.0 \le \text{Score} < 50.0$
- **`HIGH`**: $50.0 \le \text{Score} < 75.0$
- **`VERY_HIGH`**: $75.0 \le \text{Score} < 90.0$
- **`CRITICAL`**: $90.0 \le \text{Score} \le 100.0$

---

## 6. Lifecycle State Machines

### 6.1 `SoftwareProduct` Lifecycle
- **States**: `DRAFT` $\to$ `ACTIVE` $\to$ `DEPRECATED` $\to$ `RETIRED`.
- **Transitions**:
  - `DRAFT` $\to$ `ACTIVE`, `DEPRECATED`
  - `ACTIVE` $\to$ `DEPRECATED`, `RETIRED`
  - `DEPRECATED` $\to$ `ACTIVE`, `RETIRED`
  - `RETIRED` $\to$ **Terminal State (Permanent Immutability Lock)**.
- **Rule**: Deleting an `ACTIVE` product is prohibited (must deprecate/retire first).

### 6.2 `SupplyChainExemption` Lifecycle (Four-Eyes Gate)
- **States**: `PENDING` $\to$ `APPROVED` / `REJECTED` $\to$ `REVOKED` / `EXPIRED`.
- **Rule**: Replaying decisions on finalized exemptions is rejected with `409 Conflict`.

---

## 7. RBAC & Four-Eyes Segregation of Duties

### 7.1 Permissions
- `SUPPLYCHAIN_READ`: All authenticated roles.
- `SUPPLYCHAIN_MANAGE`: `ADMIN`, `MANAGER`, `GRC_ANALYST`.
- `SUPPLYCHAIN_ASSESS`: `ADMIN`, `MANAGER`, `GRC_ANALYST`, `SECURITY_ANALYST`.
- `SUPPLYCHAIN_APPROVE`: `ADMIN`, `MANAGER`.

### 7.2 Four-Eyes Segregation of Duties Rule
If `current_user.id == exemption.requested_by_id`, review submission is blocked with `403 Forbidden / 422 Unprocessable Entity` ("Segregation of Duties: Creator cannot approve their own supply chain exemption").

---

## 8. Multi-Tenant Security & Tenant Isolation

1. **JWT-Bound Isolation**: `current_user.organization_id` strictly scopes all CRUD operations.
2. **No Client `organization_id`**: Request bodies cannot inject or alter tenant scope.
3. **IDOR Defense**: Accessing another tenant's product, SBOM, component, or exemption returns `404 Not Found`.

---

## 9. Audit Logging & Non-Repudiation

All state-altering actions emit tamper-evident audit records in `audit_logs`:
- `supplychain.product.create`, `supplychain.product.update`, `supplychain.product.status_change`, `supplychain.product.delete`
- `supplychain.sbom.ingest`, `supplychain.sbom.supersede`, `supplychain.sbom.delete`
- `supplychain.component.create`, `supplychain.component.license_override`
- `supplychain.exemption.request`, `supplychain.exemption.review`, `supplychain.exemption.revoke`

---

## 10. Cross-Module Lineage Architecture

| Module / Phase | Target Entity | Purpose |
|---|---|---|
| **Phase 14 (EXPOSURE-GRC)** | `threat_exposures` | Links component vulnerabilities to global CVE catalog, EPSS scores, and KEV exploit tracking. |
| **Phase 15 (AI-GRC)** | `ai_systems` | Links software products to AI pipeline dependencies, foundational models, and tokenizer libraries. |
| **Phase 13 (RESILIENCE-GRC)** | `business_processes` | Maps critical business processes to underlying software applications to assess operational blast radius. |
| **Phase 9 (TPRM)** | `vendors` | Connects commercial/third-party software products to vendor risk assessments and SLA terms. |
| **Phase 11 (CAPA)** | `remediation_plans` | Orchestrates corrective action workflows for upgrading or replacing vulnerable dependencies. |

---

## 11. REST API Contract

### Endpoints
1. `POST /api/v1/supply-chain/products` — Create Software Product.
2. `GET /api/v1/supply-chain/products` — List Software Products (filtering by state, criticality).
3. `GET /api/v1/supply-chain/products/{id}` — Get Product Detail.
4. `PUT /api/v1/supply-chain/products/{id}` — Update Product.
5. `PATCH /api/v1/supply-chain/products/{id}/status` — Transition Product Lifecycle.
6. `DELETE /api/v1/supply-chain/products/{id}` — Delete Product.
7. `POST /api/v1/supply-chain/products/{id}/sboms` — Ingest / Register SBOM.
8. `GET /api/v1/supply-chain/products/{id}/sboms` — List Product SBOMs.
9. `GET /api/v1/supply-chain/sboms/{id}` — Get SBOM Details.
10. `POST /api/v1/supply-chain/sboms/{id}/components` — Add Component to SBOM.
11. `GET /api/v1/supply-chain/sboms/{id}/components` — List Components in SBOM.
12. `POST /api/v1/supply-chain/components/calculate-preview` — Live Component Risk Index preview calculation.
13. `POST /api/v1/supply-chain/products/calculate-preview` — Live Product SCEI preview calculation.
14. `POST /api/v1/supply-chain/exemptions` — Request Supply Chain Exemption.
15. `GET /api/v1/supply-chain/exemptions` — List Exemptions.
16. `POST /api/v1/supply-chain/exemptions/{id}/review` — Four-Eyes Review of Exemption.
17. `GET /api/v1/supply-chain/summary/posture` — Executive Supply Chain Posture Telemetry.

---

## 12. 25-Vector Adversarial Security Threat Model

| Vector ID | Attack Name | Target Boundary | Expected Result |
|---|---|---|---|
| `ADV-P17-01` | Cross-Tenant Product Read | `GET /products/{id}` | `404 Not Found` |
| `ADV-P17-02` | Cross-Tenant Product Update | `PUT /products/{id}` | `404 Not Found` |
| `ADV-P17-03` | Cross-Tenant Product Deletion | `DELETE /products/{id}` | `404 Not Found` |
| `ADV-P17-04` | Cross-Tenant SBOM Ingestion | `POST /products/{id}/sboms` | `404 Not Found` |
| `ADV-P17-05` | Cross-Tenant Component Access | `GET /sboms/{id}/components` | `404 Not Found` |
| `ADV-P17-06` | Client Org ID Injection | `POST /products` | Server ignores client org ID, binds JWT org |
| `ADV-P17-07` | Unauthorized Product Creation | `POST /products` (VIEWER/AUDITOR) | `403 Forbidden` |
| `ADV-P17-08` | Unauthorized SBOM Ingestion | `POST /products/{id}/sboms` (VIEWER) | `403 Forbidden` |
| `ADV-P17-09` | Four-Eyes Exemption Self-Review | `POST /exemptions/{id}/review` (Requester ID == User ID) | `403 Forbidden / 422 Unprocessable Entity` |
| `ADV-P17-10` | Spoofed Reviewer Identity Injection | `POST /exemptions/{id}/review` (Body includes reviewer_id) | Body field ignored, derives from JWT |
| `ADV-P17-11` | Finalized Exemption Replay Attack | `POST /exemptions/{id}/review` on `APPROVED` record | `409 Conflict / 400 Bad Request` |
| `ADV-P17-12` | Retired Product Mutation Lockout | `PUT /products/{id}` on `RETIRED` product | `409 Conflict / 400 Bad Request` |
| `ADV-P17-13` | Illegal State Machine Transition | `DRAFT` $\to$ `RETIRED` without deprecation | `422 Unprocessable Entity` |
| `ADV-P17-14` | Active Product Direct Deletion | `DELETE /products/{id}` on `ACTIVE` product | `400 Bad Request` |
| `ADV-P17-15` | Cross-Tenant Foreign Key Escape | `POST /products` with cross-tenant `business_process_id` | `404 Not Found / 422 Unprocessable Entity` |
| `ADV-P17-16` | Cross-Tenant AI System Linkage | `POST /products` with cross-tenant `ai_system_id` | `404 Not Found / 422 Unprocessable Entity` |
| `ADV-P17-17` | Cross-Tenant Vendor Escape | `POST /products` with cross-tenant `vendor_id` | `404 Not Found / 422 Unprocessable Entity` |
| `ADV-P17-18` | Negative Score Parameter Injection | `calculate-preview` with CVSS $< 0.0$ or $> 10.0$ | `422 Unprocessable Entity` |
| `ADV-P17-19` | Out-of-Range Dependency Depth | Component creation with depth $< 1$ | `422 Unprocessable Entity` |
| `ADV-P17-20` | Duplicate Product Code Collision | `POST /products` with duplicate code in same org | `409 Conflict` |
| `ADV-P17-21` | Duplicate SBOM Code Collision | `POST /products/{id}/sboms` with duplicate sbom_code | `409 Conflict` |
| `ADV-P17-22` | Tampered Cryptographic Hash Length | `POST /products/{id}/sboms` with invalid SHA-256 string | `422 Unprocessable Entity` |
| `ADV-P17-23` | Prohibited License Policy Bypass | Unapproved component with prohibited license | Server flags `is_license_prohibited = True` |
| `ADV-P17-24` | Short Audit Justification Submission | `POST /exemptions/{id}/review` with notes $< 5$ chars | `422 Unprocessable Entity` |
| `ADV-P17-25` | Unauthenticated Endpoint Infiltration | `GET /api/v1/supply-chain/summary/posture` without Bearer token | `401 Unauthorized` |

---

## 13. Test Architecture

- **Domain Tests** (`backend/tests/test_supply_chain_domain.py`): Models, calculations, depth multipliers, license rules, state transitions.
- **API Tests** (`backend/tests/test_supply_chain_api.py`): REST routes, DTO validations, preview calculation endpoints.
- **Adversarial Security Suite** (`backend/tests/test_phase17_adversarial_security.py`): Complete 25-vector security suite.

---

## 14. Frontend Architecture & Zero Client Mathematical Authority

- **Principle**: Zero client calculation authority. The frontend strictly consumes server-returned metrics or live calculation preview endpoints.
- **Pages**:
  - `SupplyChainGovernancePage.tsx`: Executive posture cards, products tab, SBOM manifests tab, components tab, exemptions tab.
  - `SoftwareProductDetailPage.tsx`: Deep-dive product inventory, SBOM history, component tree, risk distribution, lineage card.
  - `SBOMDetailPage.tsx`: Detailed component breakdown, dependency depth, license classifications.
- **Modals**:
  - `SoftwareProductModal.tsx`
  - `SBOMUploadModal.tsx`
  - `SoftwareComponentModal.tsx`
  - `SupplyChainExemptionModal.tsx`
  - `SupplyChainApprovalModal.tsx`
- **Telemetry**:
  - `SupplyChainRiskCard.tsx`
  - `SupplyChainLineageCard.tsx`

---

## 15. File Plan (Stage 1 to Stage 3)

### Files to Create:
1. `backend/alembic/versions/0017_supply_chain_governance.py` (Stage 1)
2. `backend/app/models/supply_chain.py` (Stage 1)
3. `backend/app/schemas/supply_chain.py` (Stage 1)
4. `backend/app/services/supply_chain_service.py` (Stage 1)
5. `backend/tests/test_supply_chain_domain.py` (Stage 1)
6. `backend/app/api/v1/endpoints/supply_chain.py` (Stage 2)
7. `backend/tests/test_supply_chain_api.py` (Stage 2)
8. `backend/tests/test_phase17_adversarial_security.py` (Stage 2)
9. `frontend/src/lib/supplyChainService.ts` (Stage 3)
10. `frontend/src/pages/SupplyChainGovernancePage.tsx` (Stage 3)
11. `frontend/src/pages/SoftwareProductDetailPage.tsx` (Stage 3)
12. `frontend/src/pages/SBOMDetailPage.tsx` (Stage 3)
13. `frontend/src/components/supply_chain/SoftwareProductModal.tsx` (Stage 3)
14. `frontend/src/components/supply_chain/SBOMUploadModal.tsx` (Stage 3)
15. `frontend/src/components/supply_chain/SoftwareComponentModal.tsx` (Stage 3)
16. `frontend/src/components/supply_chain/SupplyChainExemptionModal.tsx` (Stage 3)
17. `frontend/src/components/supply_chain/SupplyChainApprovalModal.tsx` (Stage 3)
18. `frontend/src/components/supply_chain/SupplyChainRiskCard.tsx` (Stage 3)
19. `frontend/src/components/supply_chain/SupplyChainLineageCard.tsx` (Stage 3)

### Files to Modify:
1. `backend/app/core/permissions.py` (Stage 1)
2. `backend/app/models/__init__.py` (Stage 1)
3. `backend/app/api/v1/api.py` (Stage 2)
4. `frontend/src/types/index.ts` (Stage 3)
5. `frontend/src/App.tsx` (Stage 3)
6. `frontend/src/components/layout/Sidebar.tsx` (Stage 3)

---

## 16. Dependency Policy
- **Target**: Exactly **0** new Python packages, **0** new npm packages.

---

## 17. Verification Gates

1. **Stage 1 Gate**: `pytest tests/test_supply_chain_domain.py` + full backend regression ($\ge 719$ tests).
2. **Stage 2 Gate**: `pytest tests/test_supply_chain_api.py` + `pytest tests/test_phase17_adversarial_security.py` (25/25 vectors) + full backend regression.
3. **Stage 3 Gate**: `npm run build` (0 TypeScript / Vite errors) + full backend regression + `git diff --check`.

---

## 18. Git Checkpoint Strategy

- Stage 1: `feat(phase17): implement supply chain governance domain foundation`
- Stage 2: `feat(phase17): implement supply chain governance api and security`
- Stage 3: `feat(phase17): implement supply chain governance workspace`

---

## 19. Explicit Stop Conditions

1. Any unexpected file created or modified.
2. Any regression or failure in the 719 baseline backend tests.
3. Any failure in frontend production build.
4. Any attempt to modify completed migrations `0001` through `0016`.
5. Any client-side mathematical calculation implemented.
