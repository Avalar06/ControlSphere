# ControlSphere — Master Architectural & Engineering Specification

## 1. Core Engineering Philosophy

ControlSphere is built on five architectural pillars:
1. **Traceability**: Direct, unbroken lineage from Compliance Frameworks down to Control Evidence, Findings, Risks, and Remediation.
2. **Deterministic Computations**: Authoritative risk scores, readiness percentages, and compliance statuses are computed strictly by deterministic backend business logic.
3. **AI Assistance (Never Authority)**: AI provides recommendations, summaries, and gap explanations with transparent reasoning. AI never silently mutates authoritative compliance or risk state.
4. **Strict Multi-Tenancy**: Organization boundaries are enforced at the database query and service layer. Cross-tenant access is structurally prevented.
5. **Non-Repudiation & Auditability**: All security-sensitive actions generate immutable audit log records.

---

## 2. Authentication & Session Architecture

- **Password Cryptography**: Native salted `bcrypt` password hashing (`bcrypt.gensalt()`, `bcrypt.hashpw()`, `bcrypt.checkpw()`).
- **Token Format**: Standard JSON Web Tokens (JWT) signed with HMAC-SHA256 (`HS256`).
- **Token Claims**:
  - `sub`: User ID
  - `org_id`: Tenant Organization ID (bound at token issuance)
  - `role`: User Role Enum
  - `iat`: Issued At timestamp
  - `exp`: Expiration timestamp
- **Security Boundary**: The token payload is verified on every request. If the user's current database state indicates an inactive account or organization mismatch, access is immediately revoked.

---

## 3. Role-Based Access Control (RBAC) Model

ControlSphere implements granular permission matrices enforced via FastAPI dependency injection:

### Defined Roles:
- **`ADMIN`**: Complete administrative oversight over the tenant organization, user provisioning, and role assignment.
- **`GRC_ANALYST`**: Full operational capability across frameworks, controls, evidence, gap findings, risks, remediation plans, and policies.
- **`SECURITY_ANALYST`**: Technical focus on controls, evidence collection, deficiency identification, and technical remediation actions.
- **`AUDITOR`**: Independent assurance role with read-only access across compliance assets, evidence review capability, and audit log inspection.
- **`MANAGER`**: Management oversight over risk posture, remediation timelines, and compliance progress.
- **`VIEWER`**: Read-only stakeholder access to permitted organizational reports and dashboards.

### Enforcement Mechanism:
Permissions are verified server-side using `require_permission(...)` and `require_roles(...)` dependencies. When an unauthorized action is attempted:
1. An immutable audit record is logged with action `auth.forbidden` and status `UNAUTHORIZED`.
2. A `403 Forbidden` response is returned to the client.

---

## 4. Multi-Tenancy & Organization Isolation

Organization isolation is a first-class security boundary:
1. **Global Catalog vs Tenant Data**: Compliance framework taxonomies (e.g. NIST CSF 2.0) are shared read-only definitions. Implementation states (`organization_controls`), policies (`policies`, `policy_versions`), and mappings (`policy_control_mappings`) are strictly tenant-scoped (`organization_id`).
2. **Query Scoping**: Every data-access query for tenant-owned resources explicitly filters by `current_user.organization_id`.
3. **IDOR Defense**: Accessing an object by ID from another tenant yields `404 Not Found`, eliminating information leakage and horizontal privilege escalation.
4. **Client Isolation**: Client-supplied tenant IDs in request bodies are ignored or validated against the authenticated JWT context.

---

## 5. Compliance Framework & Control Management (Phase 2)

### Authoritative Taxonomy — NIST CSF 2.0
The platform models the official NIST Cybersecurity Framework 2.0 hierarchy:
- **Framework**: NIST Cybersecurity Framework 2.0
- **Functions (6)**:
  1. `GV` — Govern
  2. `ID` — Identify
  3. `PR` — Protect
  4. `DE` — Detect
  5. `RS` — Respond
  6. `RC` — Recover
- **Categories (22)**: Complete NIST categories (`GV.OC`, `GV.RM`, `GV.RR`, `GV.PO`, `GV.OV`, `GV.SC`, `ID.AM`, `ID.RA`, `ID.IM`, `PR.AA`, `PR.AT`, `PR.DS`, `PR.PS`, `PR.IR`, `DE.CM`, `DE.AE`, `RS.MA`, `RS.AN`, `RS.CO`, `RS.MI`, `RC.RP`, `RC.CO`).
- **Subcategories (69 Outcomes)**: Authoritative NIST outcome statements.

### Deterministic Implementation State
Organization controls have verified implementation states:
`NOT_STARTED`, `IN_PROGRESS`, `PARTIALLY_IMPLEMENTED`, `IMPLEMENTED`, `NOT_APPLICABLE`, `NEEDS_REVIEW`.

### Compliance Scoring Formula
```
compliance_score_pct = ((implemented * 1.0) + (partially_implemented * 0.5)) / (total_controls - not_applicable) * 100
```
All scoring calculations are computed exclusively on the backend by `ControlService.calculate_framework_progress`.

### Information Security Policy Lifecycle & Versioning
- **Lifecycle States**: `DRAFT` -> `UNDER_REVIEW` -> `APPROVED` -> `PUBLISHED` -> `ARCHIVED` (state machine validated).
- **Immutable Version History**: Published and draft policy iterations are versioned with revision summaries in `policy_versions`.
- **Policy-to-Control Mapping**: Direct traceability linkages between security policies and NIST CSF 2.0 subcategories via `policy_control_mappings`.

---

## 6. Immutable Audit Logging Architecture

The `audit_logs` table provides a tamper-resistant event log for forensic compliance:
- **Captured Attributes**: `timestamp`, `organization_id`, `actor_id`, `actor_email`, `action`, `resource_type`, `resource_id`, `status`, `ip_address`, `user_agent`, `details`.
- **Phase 2 Audit Actions**: `control.update`, `control.status.change`, `policy.create`, `policy.update`, `policy.version.create`, `policy.submit_review`, `policy.approve`, `policy.publish`, `policy.archive`, `policy.mapping.create`, `policy.mapping.delete`.
- **Immutability**: No mutation or deletion API endpoints exist for audit logs.

---

## 7. Implementation Roadmap

- [x] **Phase 0 — Architecture & Scaffolding**: Domain model design, workspace initialization, Docker Compose configuration.
- [x] **Phase 1 — Foundation**: Authentication, RBAC, Multi-tenancy, Database Models & Migrations, Audit Logging, React Enterprise Shell, Automated Tests.
- [x] **Phase 2 — Frameworks, Controls & Policy Management**: NIST CSF 2.0 hierarchy, Organization Controls, Deterministic Compliance Scoring, Versioned Policies, Policy-to-Control Traceability, Automated Tests.
- [ ] **Phase 3 — Evidence Management**: Secure file upload, MIME validation, storage abstraction, evidence review workflows.
- [ ] **Phase 4 — Assessments & Findings**: Control assessments, gap analysis, deficiency findings (Low, Medium, High, Critical).
- [ ] **Phase 5 — Deterministic Risk Engine**: Likelihood x Impact scoring, inherent risk vs residual risk calculations, risk heatmap.
- [ ] **Phase 6 — Remediation Workflows**: Action plans, ownership, verification workflows before closure.
- [ ] **Phase 7 — Audit Workspace & Readiness**: Explainable audit readiness score (e.g. 72%), "What is preventing 90%?" blocker breakdown.
- [ ] **Phase 8 — Executive & Analyst Dashboards**: Real-time compliance metrics calculated from backend data.
- [ ] **Phase 9 — AI GRC Analyst**: Assistive AI reasoning with human-in-the-loop governance.
- [ ] **Phase 10 — Cross-Framework Mappings**: NIST ↔ ISO 27001 ↔ SOC 2 ↔ CIS mappings.
- [ ] **Phase 11 — Hardening & Final Validation**: Rate limiting, security scans, CI/CD pipeline, production deployment packaging.