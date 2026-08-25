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
1. **Query Scoping**: Every data-access query for tenant-owned resources explicitly filters by `current_user.organization_id`.
2. **IDOR Defense**: Accessing an object by ID from another tenant yields `404 Not Found`, eliminating information leakage and horizontal privilege escalation.
3. **Client Isolation**: Client-supplied tenant IDs in request bodies are ignored or validated against the authenticated JWT context.

---

## 5. Immutable Audit Logging Architecture

The `audit_logs` table provides a tamper-resistant event log for forensic compliance:
- **Captured Attributes**:
  - `timestamp`: UTC event timestamp
  - `organization_id`: Organization scope
  - `actor_id`: Foreign key to `users.id` (set to `NULL` if actor is deleted to preserve history)
  - `actor_email`: Preserved identity of actor at event time
  - `action`: Categorized event (e.g. `auth.login.success`, `user.create`, `organization.update`)
  - `resource_type`: Target entity (e.g. `USER`, `ORGANIZATION`, `AUTH`)
  - `resource_id`: Affected entity identifier
  - `status`: Outcome (`SUCCESS`, `FAILURE`, `UNAUTHORIZED`)
  - `ip_address`: Client IP address
  - `user_agent`: Client browser / API agent
  - `details`: JSON payload with contextual parameters and diffs
- **Immutability**: The API provides no mutation (`PATCH`/`PUT`) or deletion (`DELETE`) endpoints for audit logs.

---

## 6. Implementation Roadmap

- [x] **Phase 0 — Architecture & Scaffolding**: Domain model design, workspace initialization, Docker Compose configuration.
- [x] **Phase 1 — Foundation**: Authentication, RBAC, Multi-tenancy, Database Models & Migrations, Audit Logging, React Enterprise Shell, Automated Tests.
- [ ] **Phase 2 — Frameworks & Controls**: NIST CSF 2.0 structured data, Control hierarchy, search, filter, and mappings.
- [ ] **Phase 3 — Evidence Management**: Secure file upload, MIME validation, storage abstraction, evidence review workflows.
- [ ] **Phase 4 — Assessments & Findings**: Control assessments, gap analysis, deficiency findings (Low, Medium, High, Critical).
- [ ] **Phase 5 — Deterministic Risk Engine**: Likelihood x Impact scoring, inherent risk vs residual risk calculations, risk heatmap.
- [ ] **Phase 6 — Remediation Workflows**: Action plans, ownership, verification workflows before closure.
- [ ] **Phase 7 — Audit Workspace & Readiness**: Explainable audit readiness score (e.g. 72%), "What is preventing 90%?" blocker breakdown.
- [ ] **Phase 8 — Executive & Analyst Dashboards**: Real-time compliance metrics calculated from backend data.
- [ ] **Phase 9 — AI GRC Analyst**: Assistive AI reasoning with human-in-the-loop governance.
- [ ] **Phase 10 — Cross-Framework Mappings**: NIST ↔ ISO 27001 ↔ SOC 2 ↔ CIS mappings.
- [ ] **Phase 11 — Hardening & Final Validation**: Rate limiting, security scans, CI/CD pipeline, production deployment packaging.