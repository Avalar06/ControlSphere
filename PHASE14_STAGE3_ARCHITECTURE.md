# PHASE 14 STAGE 3 ARCHITECTURE SPECIFICATION
## Continuous Threat Exposure & Vulnerability Governance (EXPOSURE-GRC)
### Frontend Governance Workspace & Cross-Module Intelligence

---

## 1. Architecture Summary & Philosophy

Phase 14 Stage 3 establishes the **EXPOSURE-GRC Frontend Governance Workspace** for ControlSphere. It translates backend threat exposure telemetry, EPSS exploit intelligence, CISA KEV tracking, Phase 13 business process criticality multipliers, four-eyes SLA exception deferrals, and Phase 11 corrective remediation orchestration into an enterprise-grade user interface.

### Key Architectural Pillars:
1. **Zero Client Calculation Authority**: All scores (Base Score, Blast Radius Multiplier, Exposure Index), SLA deadlines, breach statuses, exception states, and aggregated executive telemetry are server-authoritative and rendered directly from backend API responses.
2. **Four-Eyes Segregation of Duties UX**: The UI prevents self-approval of SLA extension requests when `current_user.id === exception.requested_by_id`, providing clear visual feedback and delegating enforcement to the server.
3. **Immutable Resolved Records**: Records in `RESOLVED` status display prominent immutability banners, disabling all mutation controls (status transitions, field edits, deletions, asset linkages, exception requests).
4. **Deep Cross-Module Lineage**: Seamless bi-directional navigation between Phase 14 Exposures, Phase 13 Business Processes, Phase 9 Vendors, Phase 2 Controls, Phase 11 Remediation Plans, and Phase 12 Quant Scenarios.
5. **Zero External Dependencies**: Built entirely using existing React 19, TypeScript, Tailwind CSS, Lucide React, and React Query stack without adding new npm packages.

---

## 2. Existing Patterns Reused

The implementation directly adheres to established ControlSphere frontend patterns:
- **State Management & Data Fetching**: `@tanstack/react-query` with declarative `useQuery` and `useMutation` hooks, automatic cache invalidation (`queryClient.invalidateQueries`), and `refetchOnWindowFocus: false`.
- **API Client**: Centralized Axios instance (`frontend/src/lib/api.ts`) managing JWT bearer token injection and standard error handling.
- **Role-Based Access Control**: `useAuth()` hook providing `hasRole(...)` and `user` context.
- **Design System & UI Primitives**: Standardized dark-slate components from `frontend/src/components/ui/`: `Card`, `Badge`, `Button`, `Table`, `Modal`, `LoadingSpinner`.
- **Navigation Shell**: Layout integration via `frontend/src/components/layout/AppLayout.tsx` and `Sidebar.tsx`.

---

## 3. Routes & Navigation

### Route Definitions
| Route | Page Component | Access Control | Purpose |
|---|---|---|---|
| `/exposure` | `ExposurePage` | All Authenticated Roles | Primary EXPOSURE-GRC Workspace: Executive Posture KPI Banner, Filterable Threat Exposure Register, Lineage Overview |
| `/exposure/:id` | `ExposureDetailPage` | All Authenticated Roles | Detailed Vulnerability Workspace: Technical Telemetry, Blast Radius Assessment, Asset Links, SLA Governance, Four-Eyes Exceptions, Cross-Module Links |

### Sidebar Navigation Integration
In `frontend/src/components/layout/Sidebar.tsx`, add under the **Threat & Exposure Governance** group:
```tsx
{
  group: 'Threat & Exposure Governance',
  items: [
    { name: 'Threat Exposure (CVE)', path: '/exposure', icon: Crosshair, tag: 'Phase 14' },
    { name: 'Incident Response', path: '/incidents', icon: Flame, tag: 'Phase 10' },
  ],
}
```

---

## 4. Executive Exposure Dashboard (`ExposurePage.tsx`)

The main workspace presents an executive command center combining real-time threat telemetry with operational workflows.

### 4.1 Executive Telemetry KPI Grid
Powered by `GET /api/v1/exposures/summary/posture`:
- **Total Vulnerability Exposures**: Total active catalog count.
- **Critical & High Exposures**: Count of severe exposures requiring immediate triage.
- **CISA KEV Exploited In-The-Wild**: Count of actively weaponized vulnerabilities.
- **Active SLA Exceptions**: Count of pending or approved deferrals.
- **SLA Breach Telemetry**: Breached count and breach percentage (`sla_breach_rate_percent%`) with color-coded severity indicator.
- **Average Exposure Index**: Mean organization threat index (0.0 to 100.0).

### 4.2 Tabbed Workspace Architecture
- **Tab 1: Exposure Register**: Searchable, multi-filtered catalog table.
- **Tab 2: Threat Posture & Distribution**: Visual breakdowns of severity, status, and KEV exposure distributions.
- **Tab 3: Governance Lineage**: Enterprise cross-module lineage map connecting Controls $\to$ Vendors $\to$ Processes $\to$ Exposures $\to$ Remediation.

---

## 5. Filterable Exposure Register

Supports comprehensive filtering and server-backed search:
- **Text Search**: Debounced search query matched against CVE ID, CWE ID, Title, and Description.
- **Severity Filter**: Dropdown for `ALL`, `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFORMATIONAL`.
- **Status Filter**: Dropdown for `ALL`, `OPEN`, `UNDER_INVESTIGATION`, `REMEDIATING`, `EXCEPTION_REQUESTED`, `EXCEPTION_APPROVED`, `EXCEPTION_REJECTED`, `RESOLVED`.
- **CISA KEV Toggle**: Boolean switch to isolate actively exploited CVEs.

### Columns:
1. **CVE Identifier**: Formatted badge (e.g., `CVE-2026-1001`), CWE tag, and title.
2. **Severity & Telemetry**: Severity badge (`danger`, `warning`, `info`, `default`), CVSS score, EPSS probability %, and KEV indicator badge.
3. **Exposure Index**: Server-authoritative index meter (0.00 to 100.00) with color gradients:
   - $\ge 75.0$: Rose / Critical
   - $50.0 - 74.9$: Amber / High
   - $25.0 - 49.9$: Blue / Medium
   - $< 25.0$: Slate / Low
4. **SLA Due Date & Urgency**: Server-calculated target date with countdown pill (e.g., `5 days remaining` or `BREACHED`).
5. **Lifecycle Status**: State machine badge (`OPEN`, `UNDER_INVESTIGATION`, `REMEDIATING`, `EXCEPTION_REQUESTED`, `RESOLVED`).
6. **Actions**: Detail view, Status Transition, Edit (if non-resolved), Delete (if non-resolved), Spawn CAPA.

---

## 6. Exposure Detail Workspace (`ExposureDetailPage.tsx`)

The detail page provides a complete single-pane-of-glass workspace for a specific CVE.

### Layout Structure:
1. **Header Bar**:
   - Back button to `/exposure`
   - CVE ID, Title, Status badge, Severity badge, KEV tag
   - Action buttons based on RBAC & status: `Transition Status`, `Edit Telemetry`, `Spawn CAPA`, `Delete`
2. **Telemetry & Scoring Banner**:
   - 6-metric card row displaying CVSS Base Score, EPSS Probability, CISA KEV Status, Calculated Base Score, Blast Radius Multiplier ($1.00\times - 1.25\times$), and Final Exposure Index.
3. **SLA & Exception Governance Card**:
   - SLA deadline display, relative time countdown, KEV escalation rule explanation.
   - `Request SLA Exception` button (disabled on `RESOLVED` records).
4. **Blast Radius & Asset Linkage Card (`BlastRadiusCard.tsx`)**:
   - Lists all linked technical assets (Servers, DBs, Cloud Services, Apps, Network Devices).
   - Shows associated Phase 13 Business Processes and highlights the highest criticality tier determining the multiplier.
   - Shows associated Phase 9 Vendors and Phase 2 Controls.
   - `+ Link Technical Asset` button.
5. **Four-Eyes SLA Deferral History Card**:
   - Table of all exception requests for this exposure.
   - Displays requested SLA date, justification, compensating controls, requester, approver, decision notes.
   - `Review Request` button for Managers/Admins with active segregation of duties enforcement.
6. **Cross-Module Lineage Card (`ExposureLineageCard.tsx`)**:
   - Visual map of related GRC entities.

---

## 7. Blast Radius Visualization Component (`BlastRadiusCard.tsx`)

Visualizes how technical vulnerabilities impact business operations:
- **Highest Criticality Tier Highlight**:
  - `TIER_1` Process $\to$ $1.25\times$ multiplier badge (Critical Business Process)
  - `TIER_2` Process $\to$ $1.15\times$ multiplier badge (High Business Process)
  - `TIER_3` Process $\to$ $1.05\times$ multiplier badge (Moderate Business Process)
  - `TIER_4` / None $\to$ $1.00\times$ multiplier badge (Standard Technical Asset)
- **Asset Table**:
  - Asset Identifier (hostname, IP, cluster)
  - Asset Type & Environment (`PRODUCTION`, `STAGING`, `DEVELOPMENT`)
  - Linked Process (clickable link to `/resilience/processes/:id`)
  - Linked Vendor (clickable link to `/vendors/:id`)
  - Linked Control (clickable link to `/controls`)
  - Action: Unlink button (recalculates blast radius on backend)

---

## 8. SLA Governance & Urgency Presentation

### Server-Authoritative SLA Matrix:
- `CRITICAL` + `CISA_KEV == true`: **7 calendar days**
- `CRITICAL`: **14 calendar days**
- `HIGH`: **30 calendar days**
- `MEDIUM`: **60 calendar days**
- `LOW` / `INFORMATIONAL`: **90 calendar days**

### Visual Indicators:
- **Healthy**: $> 72$ hours remaining (Slate / Green).
- **Approaching Breach**: $\le 72$ hours remaining (Amber warning badge).
- **Breached**: Current time $> \text{remediation\_sla\_due}$ (Rose glowing badge with alert icon).
- Countdown derived purely for display from server timestamp vs `Date.now()`.

---

## 9. Four-Eyes Exception & Deferral Governance UX

### Exception Request Modal (`ExposureExceptionModal.tsx`):
- **Requested SLA Extension Date**: Date picker validated to ensure date is later than current SLA deadline.
- **Business Justification**: Required text area (min 5 characters) documenting the delay rationale.
- **Compensating Controls**: Optional text area specifying WAF rules, network isolation, or temporary mitigations.

### Exception Review Modal:
- Shows full request details and requester name.
- **Decision Selector**: `APPROVED` or `REJECTED`.
- **Review Notes**: Reviewer rationale.
- **Segregation of Duties Enforcement**:
  - If `current_user.id === exception.requested_by_id`, the review action is disabled with an explanatory callout:
    > **Segregation of Duties Enforced**: You are the requester of this SLA exception. Policy requires an independent manager or administrator to review and approve this request.

---

## 10. Exposure Lifecycle State Machine UX

### Lifecycle Transitions (`ExposureStatusModal.tsx`):
Controls enforce legal status transitions:
- `OPEN` $\to$ `UNDER_INVESTIGATION`, `REMEDIATING`, `RESOLVED`
- `UNDER_INVESTIGATION` $\to$ `REMEDIATING`, `RESOLVED`
- `REMEDIATING` $\to$ `RESOLVED`
- Exception states (`EXCEPTION_REQUESTED`, `EXCEPTION_APPROVED`, `EXCEPTION_REJECTED`) are driven through the Four-Eyes Exception workflow.

### Permanent Immutability for `RESOLVED` Records:
- When `status === 'RESOLVED'`, a prominent banner displays:
  > **RECORD RESOLVED & ARCHIVED (IMMUTABLE)**: This vulnerability exposure has been verified as resolved. In accordance with enterprise audit standards, field telemetry, asset linkages, exceptions, and lifecycle states are permanently locked.
- Action buttons for Edit, Delete, Link Asset, Request Exception, and Status Change are completely hidden or disabled.

---

## 11. Asset Linkage Modal (`ExposureAssetLinkModal.tsx`)

Enables multi-entity association with server-side validation:
- **Asset Identifier**: String input (FQDN, IP, instance ID, ARN).
- **Asset Type**: Dropdown (`SERVER`, `DATABASE`, `CLOUD_SERVICE`, `NETWORK_DEVICE`, `APPLICATION`).
- **Environment**: Dropdown (`PRODUCTION`, `STAGING`, `DEVELOPMENT`).
- **Business Process**: Dropdown fetched via `resilienceService.listProcesses()` (shows Name + Criticality Tier).
- **Vendor**: Dropdown fetched via `tprmService.listVendors()` (shows Legal Name + Vendor Code).
- **Organization Control**: Dropdown fetched via `controlService.listControls()`.
- **Notes**: Optional context.

---

## 12. Remediation Orchestration Integration (Phase 11)

- **Spawn CAPA Action**:
  - In Exposure Detail Header, click **"Spawn Remediation Plan"**.
  - Invokes `POST /api/v1/exposures/:id/remediate`.
  - Creates a linked Phase 11 `RemediationPlan` (`plan_code: CAPA-EXP-CVE-...`) with target date mapped to exposure SLA.
  - Automatically transitions exposure to `REMEDIATING`.
- **Remediation Link Display**:
  - Displays linked CAPA code with clickable navigation link to `/remediations/:id`.

---

## 13. RBAC UX Matrix

| Action / Component | ADMIN | MANAGER | GRC_ANALYST | SECURITY_ANALYST | AUDITOR | VIEWER |
|---|---|---|---|---|---|---|
| View Exposures, Register & Posture | Yes | Yes | Yes | Yes | Yes | Yes |
| View Exposure Details & Blast Radius | Yes | Yes | Yes | Yes | Yes | Yes |
| Create / Ingest Exposure | Yes | Yes | Yes | Yes | No | No |
| Update Telemetry (CVSS/EPSS) | Yes | Yes | Yes | Yes | No | No |
| Delete Exposure | Yes | Yes | Yes | Yes | No | No |
| Change Status | Yes | Yes | Yes | Yes | No | No |
| Link / Unlink Technical Assets | Yes | Yes | Yes | Yes | No | No |
| Request SLA Exception | Yes | Yes | Yes | Yes | No | No |
| **Review / Approve Exception (Four-Eyes)** | **Yes** | **Yes** | **No** | **No** | **No** | **No** |
| Spawn Phase 11 CAPA Remediation | Yes | Yes | Yes | Yes | No | No |

---

## 14. API Service Layer Plan (`frontend/src/lib/exposureService.ts`)

```typescript
import { api } from './api';
import type {
  ExposureAssetLink,
  ExposureAssetLinkCreate,
  ExposureException,
  ExposureExceptionCreate,
  ExposureExceptionReviewRequest,
  ExposureIndexCalculateRequest,
  ExposureIndexCalculateResponse,
  ExposureSeverity,
  ExposureStatus,
  ExposureSummaryResponse,
  RemediationPlan,
  VulnerabilityExposure,
  VulnerabilityExposureCreate,
  VulnerabilityExposureStatusUpdate,
  VulnerabilityExposureUpdate,
} from '../types';

export const exposureService = {
  // Exposure Catalog
  createExposure: async (data: VulnerabilityExposureCreate): Promise<VulnerabilityExposure> => {
    const res = await api.post<VulnerabilityExposure>('/exposures', data);
    return res.data;
  },

  listExposures: async (params?: {
    severity?: ExposureSeverity;
    status?: ExposureStatus;
    cisa_kev?: boolean;
    search?: string;
    skip?: number;
    limit?: number;
  }): Promise<VulnerabilityExposure[]> => {
    const res = await api.get<VulnerabilityExposure[]>('/exposures', { params });
    return res.data;
  },

  getExposure: async (id: number): Promise<VulnerabilityExposure> => {
    const res = await api.get<VulnerabilityExposure>(`/exposures/${id}`);
    return res.data;
  },

  updateExposure: async (id: number, data: VulnerabilityExposureUpdate): Promise<VulnerabilityExposure> => {
    const res = await api.put<VulnerabilityExposure>(`/exposures/${id}`, data);
    return res.data;
  },

  deleteExposure: async (id: number): Promise<void> => {
    await api.delete(`/exposures/${id}`);
  },

  updateStatus: async (id: number, data: VulnerabilityExposureStatusUpdate): Promise<VulnerabilityExposure> => {
    const res = await api.put<VulnerabilityExposure>(`/exposures/${id}/status`, data);
    return res.data;
  },

  // Asset & Blast Radius Linkage
  linkAsset: async (exposureId: number, data: ExposureAssetLinkCreate): Promise<ExposureAssetLink> => {
    const res = await api.post<ExposureAssetLink>(`/exposures/${exposureId}/assets`, data);
    return res.data;
  },

  listAssetLinks: async (exposureId: number): Promise<ExposureAssetLink[]> => {
    const res = await api.get<ExposureAssetLink[]>(`/exposures/${exposureId}/assets`);
    return res.data;
  },

  unlinkAsset: async (linkId: number): Promise<void> => {
    await api.delete(`/exposures/assets/${linkId}`);
  },

  // Four-Eyes Exception Governance
  requestException: async (exposureId: number, data: ExposureExceptionCreate): Promise<ExposureException> => {
    const res = await api.post<ExposureException>(`/exposures/${exposureId}/exceptions`, data);
    return res.data;
  },

  reviewException: async (exceptionId: number, data: ExposureExceptionReviewRequest): Promise<ExposureException> => {
    const res = await api.post<ExposureException>(`/exposures/exceptions/${exceptionId}/review`, data);
    return res.data;
  },

  listExceptions: async (params?: {
    exposure_id?: number;
    status?: string;
  }): Promise<ExposureException[]> => {
    const res = await api.get<ExposureException[]>('/exposures/exceptions', { params });
    return res.data;
  },

  // Remediation Spawning
  spawnRemediation: async (exposureId: number, params?: { title?: string; finding_id?: number }): Promise<RemediationPlan> => {
    const res = await api.post<RemediationPlan>(`/exposures/${exposureId}/remediate`, null, { params });
    return res.data;
  },

  // Executive Posture & Calculation Preview
  getPostureSummary: async (): Promise<ExposureSummaryResponse> => {
    const res = await api.get<ExposureSummaryResponse>('/exposures/summary/posture');
    return res.data;
  },

  calculateIndexPreview: async (data: ExposureIndexCalculateRequest): Promise<ExposureIndexCalculateResponse> => {
    const res = await api.post<ExposureIndexCalculateResponse>('/exposures/calculate-index', data);
    return res.data;
  },
};
```

---

## 15. TypeScript Domain Contracts (`frontend/src/types/index.ts`)

```typescript
// ─── Phase 14: EXPOSURE-GRC Types ─────────────────────────────────────────────

export type ExposureSeverity =
  | 'CRITICAL'
  | 'HIGH'
  | 'MEDIUM'
  | 'LOW'
  | 'INFORMATIONAL';

export type ExposureStatus =
  | 'OPEN'
  | 'UNDER_INVESTIGATION'
  | 'REMEDIATING'
  | 'EXCEPTION_REQUESTED'
  | 'EXCEPTION_APPROVED'
  | 'EXCEPTION_REJECTED'
  | 'RESOLVED';

export type AssetType =
  | 'SERVER'
  | 'DATABASE'
  | 'CLOUD_SERVICE'
  | 'NETWORK_DEVICE'
  | 'APPLICATION';

export type Environment = 'PRODUCTION' | 'STAGING' | 'DEVELOPMENT';

export type ExceptionApprovalStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED';

export interface ExposureAssetLinkBase {
  asset_identifier: string;
  asset_type: AssetType;
  environment: Environment;
  process_id?: number | null;
  vendor_id?: number | null;
  control_id?: number | null;
  notes?: string | null;
}

export interface ExposureAssetLinkCreate extends ExposureAssetLinkBase {}

export interface ExposureAssetLink extends ExposureAssetLinkBase {
  id: number;
  organization_id: number;
  exposure_id: number;
  created_at: string;
  process_name?: string | null;
  process_tier?: CriticalityTier | null;
  vendor_name?: string | null;
  control_title?: string | null;
}

export interface ExposureExceptionBase {
  requested_sla_due: string;
  justification: string;
  compensating_controls?: string | null;
}

export interface ExposureExceptionCreate extends ExposureExceptionBase {}

export interface ExposureExceptionReviewRequest {
  decision: 'APPROVED' | 'REJECTED';
  review_notes?: string | null;
}

export interface ExposureException extends ExposureExceptionBase {
  id: number;
  organization_id: number;
  exposure_id: number;
  requested_by_id: number;
  approved_by_id?: number | null;
  status: ExceptionApprovalStatus;
  original_sla_due: string;
  requested_sla_due: string;
  justification: string;
  compensating_controls?: string | null;
  review_notes?: string | null;
  created_at: string;
  reviewed_at?: string | null;
  requested_by?: User | null;
  approved_by?: User | null;
}

export interface VulnerabilityExposureBase {
  cve_id: string;
  cwe_id?: string | null;
  title: string;
  description?: string | null;
  cvss_score: number;
  cvss_vector?: string | null;
  epss_score: number;
  cisa_kev: boolean;
  severity: ExposureSeverity;
}

export interface VulnerabilityExposureCreate extends VulnerabilityExposureBase {
  discovered_at?: string | null;
  remediation_sla_due?: string | null;
}

export interface VulnerabilityExposureUpdate {
  title?: string;
  description?: string | null;
  cwe_id?: string | null;
  cvss_score?: number;
  cvss_vector?: string | null;
  epss_score?: number;
  cisa_kev?: boolean;
  severity?: ExposureSeverity;
}

export interface VulnerabilityExposureStatusUpdate {
  status: ExposureStatus;
  notes?: string | null;
}

export interface VulnerabilityExposure extends VulnerabilityExposureBase {
  id: number;
  organization_id: number;
  status: ExposureStatus;
  exposure_index: number;
  remediation_sla_due: string;
  remediation_plan_id?: number | null;
  discovered_at: string;
  resolved_at?: string | null;
  created_at: string;
  updated_at: string;
  asset_links?: ExposureAssetLink[];
  exceptions?: ExposureException[];
}

export interface ExposureIndexCalculateRequest {
  cvss_score: number;
  epss_score: number;
  cisa_kev: boolean;
  highest_process_tier?: CriticalityTier | null;
}

export interface ExposureIndexCalculateResponse {
  cvss_score: number;
  epss_score: number;
  cisa_kev: boolean;
  base_score: number;
  blast_radius_multiplier: number;
  exposure_index: number;
}

export interface ExposureSummaryResponse {
  total_exposures: number;
  critical_exposures: number;
  high_exposures: number;
  cisa_kev_count: number;
  active_exceptions_count: number;
  sla_breached_count: number;
  sla_breach_rate_percent: number;
  average_exposure_index: number;
  severity_distribution: Record<string, number>;
  status_distribution: Record<string, number>;
}
```

---

## 16. Component Architecture & File Plan

### Files to Create in Stage 3:
1. `frontend/src/lib/exposureService.ts` — API client service.
2. `frontend/src/pages/ExposurePage.tsx` — Executive Posture Banner, Filterable CVE Register, and Overview Tabs.
3. `frontend/src/pages/ExposureDetailPage.tsx` — CVE Detail Workspace, Scoring Breakdown, SLA Tracker, Actions.
4. `frontend/src/components/exposure/ExposureModal.tsx` — Ingestion and telemetry edit modal.
5. `frontend/src/components/exposure/ExposureStatusModal.tsx` — Governed lifecycle transition modal.
6. `frontend/src/components/exposure/ExposureAssetLinkModal.tsx` — Asset and cross-module linkage modal.
7. `frontend/src/components/exposure/ExposureExceptionModal.tsx` — SLA deferral request and four-eyes review modal.
8. `frontend/src/components/exposure/BlastRadiusCard.tsx` — Technical asset list & Business Process multiplier card.
9. `frontend/src/components/exposure/ExposureLineageCard.tsx` — Multi-module GRC governance lineage map.

### Files to Modify in Stage 3:
1. `frontend/src/App.tsx` — Add `/exposure` and `/exposure/:id` routes.
2. `frontend/src/components/layout/Sidebar.tsx` — Add navigation link for Phase 14 Threat Exposure.
3. `frontend/src/types/index.ts` — Add Phase 14 TypeScript types and enums.

---

## 17. Cross-Module Governance Lineage

The workspace connects seamlessly with existing ControlSphere phases:
```
Phase 2: Organization Controls
        │
Phase 7: Continuous Control Monitoring (CCM)
        │
Phase 9: Third-Party & Vendor Risk (TPRM)
        │
Phase 13: Operational Resilience & Business Processes (Tier 1-4)
        │
Phase 14: Continuous Threat Exposure & Vulnerabilities (EXPOSURE-GRC)
        │
Phase 11: Governed Corrective Action Plans (CAPA Remediation)
        │
Phase 12: QUANTUM-GRC Cyber Risk Quantification (Loss Scenarios)
        │
Phase 10: Security Incident & Regulatory Breach Governance
```

---

## 18. Security Invariants & Client Boundaries

1. **No Client Math Authority**: The frontend never computes Base Score, Multipliers, Final Exposure Index, or SLA due dates.
2. **No Tenant Spoofing**: `organization_id` is omitted from all form payloads.
3. **Four-Eyes Segregation of Duties**: Requesters are blocked from self-approval with explicit UX messaging.
4. **Permanent Immutability**: `RESOLVED` records cannot be edited, transitioned, deleted, or linked to new assets.
5. **No Blind Trust of UI State**: All actions require authenticated JWT tokens and server-validated permissions.

---

## 19. Dependency Review
- **New npm packages**: **0**
- **New Python packages**: **0**
- Utilizes existing React 19, Tailwind CSS, Lucide React, and `@tanstack/react-query`.

---

## 20. Verification Plan

Upon authorization to implement Stage 3:
1. **Frontend Production Build**: `npm run build` in `frontend/` (must transform ~1,985+ modules with 0 TypeScript/Vite errors).
2. **Backend Regression Test Suite**: `pytest tests -q` in `backend/` (must pass 594/594 tests).
3. **Code Formatting & Git Quality**: `git diff --check` (must be clean with no whitespace errors).
4. **Route & Component Verification**: Verify `/exposure` and `/exposure/:id` render correctly in the browser shell.
5. **RBAC UX Verification**: Verify role-based button states across Admin, Manager, Analyst, and Viewer.

---

*PHASE 14 STAGE 3 ARCHITECTURAL BLUEPRINT COMPLETE. PRE-IMPLEMENTATION REVIEW ONLY. NO CODE IMPLEMENTATION COMMENCED.*
