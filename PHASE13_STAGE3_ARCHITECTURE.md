# ControlSphere — Phase 13 Stage 3 Architecture Specification
## Frontend Operational Resilience & Business Impact Analysis (RESILIENCE-GRC) Governance Workspace

---

## 1. Executive Architecture Summary

Phase 13 establishes **Operational Resilience & Business Impact Analysis (RESILIENCE-GRC)** within the ControlSphere GRC ecosystem. Following the verified deployment and cryptographic verification of the Stage 1 Database & Domain Foundation and Stage 2 REST API, Cross-Module Integration, and 25-vector Adversarial Security (`ADV-P13-01` through `ADV-P13-25`), Stage 3 delivers the enterprise frontend governance workspace.

### Core Architecture Philosophy
1. **Server Authority**: The frontend is exclusively a presentation, workflow orchestration, interactive visualization, and client-side validation UX layer. The backend remains strictly authoritative for all calculations (e.g., deterministic outage loss), status transitions (`DRAFT -> ACTIVE -> SUPERSEDED`, `DRAFT -> ARCHIVED`), version numbering, tenant scoping, actor attribution, and four-eyes enforcement.
2. **Deterministic Financial Disruption Modeling**: Outage loss modeling is strictly deterministic:
   $$\text{Total Projected Outage Loss}(H) = \text{Fixed Outage Cost} + (\text{Hourly Downtime Cost} \times H)$$
   The frontend renders parametric curves and scenario projections based directly on server-authoritative formulas and telemetry without introducing stochastic simulations (FAIR/Monte Carlo are retained in Phase 12).
3. **Four-Eyes Governance & Immutability UX**: Separation of duties is prominently displayed in the UX: a user who drafted a BIA cannot approve it. Active and superseded BIAs are rendered as immutable, tamper-evident baselines with explicit visual locks and immutable historical telemetry.
4. **Cross-Module Dependency Graphing**: Business processes directly reference Phase 9 Vendors (`Vendor` model) and Phase 2 Internal Controls (`OrganizationControl` model) without duplicating catalog stores or creating parallel data repositories.

---

## 2. Existing Frontend Patterns Discovered

During our audit of the ControlSphere frontend repository (`frontend/src/`), the following conventions and architectural patterns were identified:

| Architectural Dimension | Existing ControlSphere Standard | Stage 3 Alignment Strategy |
|---|---|---|
| **Routing & App Shell** | `react-router-dom` v6 nested routes inside `<AppLayout />` with `<BrowserRouter>` and `<Routes>` in `App.tsx`. | Register `/resilience` and `/resilience/processes/:id` within `<AppLayout />`. |
| **Navigation & Sidebar** | `Sidebar.tsx` with categorized `navGroups` (`Core`, `Compliance & Controls`, `Risk & Remediation`, etc.) with `LucideIcon` and badges. | Add `Operational Resilience` (`Building2` / `Layers` / `Activity` icon) under `Risk & Remediation` tagged as `'Phase 13'`. |
| **Data Fetching & State** | `@tanstack/react-query` using `useQuery` and `useMutation` with query key invalidation patterns (`queryClient.invalidateQueries`). | Adopt React Query for all process catalog, BIA lifecycle, dependency, and calculation endpoints. |
| **API Client** | Centralized Axios instance in `frontend/src/lib/api.ts` attaching JWT via request interceptors and handling 401 redirection. | Create `frontend/src/lib/resilienceService.ts` wrapping Axios endpoints directly matching backend routes. |
| **UI Primitives** | Custom atomic Tailwind components in `frontend/src/components/ui/` (`Card`, `Badge`, `Button`, `Table`, `Modal`, `LoadingSpinner`). | Reuse 100% existing UI primitives; zero external UI framework or chart library dependencies. |
| **Visualizations & Charts** | Native Tailwind and accessible mathematical SVGs (e.g. parametric cost curves, tier distribution meters, RTO/RPO/MTD gauges). | Render SVG-based downtime recovery timelines and linear outage cost curves without npm chart libraries. |
| **RBAC Enforcement** | `useAuth()` hook providing `user` object and `hasRole(...roles)` helper. | Restrict management mutations to `ADMIN`, `MANAGER`, `GRC_ANALYST`, approvals to `ADMIN`, `MANAGER`, and render read-only UX for `SECURITY_ANALYST`, `AUDITOR`, `VIEWER`. |

---

## 3. Route Architecture

```
/ (Protected App Shell via AppLayout)
 ├── /dashboard
 ├── /quant-risk (Phase 12)
 ├── /remediations (Phase 11)
 ├── /incidents (Phase 10)
 ├── /vendors (Phase 9)
 ├── /resilience                                 <-- [NEW: Phase 13 Executive Dashboard & Process Register]
 │    ├── Tab: "Overview" (Executive Posture & Outage Telemetry)
 │    ├── Tab: "Processes" (Process Catalog & BIA Status Table)
 │    └── Tab: "Lineage" (Cross-Module Governance Map)
 └── /resilience/processes/:id                   <-- [NEW: Phase 13 Business Process & BIA Detail]
      ├── Section: Process Metadata & Ownership
      ├── Section: Active BIA Baseline & Downtime Thresholds (RTO, RPO, MTD)
      ├── Section: Deterministic Outage Loss Cost Curve Engine
      ├── Section: Cross-Module Dependencies (Vendors & Controls)
      └── Section: BIA Version History & Four-Eyes Governance Audit Trail
```

---

## 4. Page & Component Architecture

### Component Hierarchy Tree
```
frontend/src/
 ├── pages/
 │    ├── ResiliencePage.tsx                     (Main workspace: Overview, Register, Lineage)
 │    └── BusinessProcessDetailPage.tsx          (Deep-dive process, active BIA, cost curve, dependencies)
 ├── components/resilience/
 │    ├── ProcessModal.tsx                       (Create & edit business process dialog)
 │    ├── BiaModal.tsx                           (Draft new BIA version with client-side RTO <= MTD check)
 │    ├── BiaApprovalModal.tsx                   (Four-eyes approval dialog with SoD verification)
 │    ├── DependencyModal.tsx                    (Attach Phase 9 Vendor or Phase 2 Control to process)
 │    ├── OutageImpactCard.tsx                   (Interactive outage loss slider & deterministic curve)
 │    ├── BiaHistoryCard.tsx                     (Version table with immutable lock badges & audit logs)
 │    └── ResilienceLineageCard.tsx              (Multi-phase dependency & resilience data flow graph)
```

---

## 5. TypeScript Contracts (`frontend/src/types/index.ts`)

```typescript
// ─── Phase 13: Operational Resilience & Business Impact Analysis (RESILIENCE-GRC)

export type CriticalityTier = 'TIER_1' | 'TIER_2' | 'TIER_3' | 'TIER_4';

export type BiaStatus = 'DRAFT' | 'ACTIVE' | 'SUPERSEDED' | 'ARCHIVED';

export type DependencyType = 'VENDOR' | 'CONTROL';

export interface BusinessProcessBase {
  name: string;
  description?: string | null;
  criticality_tier: CriticalityTier;
}

export interface BusinessProcessCreate extends BusinessProcessBase {}

export interface BusinessProcessUpdate {
  name?: string;
  description?: string | null;
  criticality_tier?: CriticalityTier;
}

export interface ProcessDependency {
  id: number;
  organization_id: number;
  process_id: number;
  dependency_type: DependencyType;
  dependency_id: number;
  notes?: string | null;
  created_at: string;
}

export interface ProcessDependencyCreate {
  process_id: number;
  dependency_type: DependencyType;
  dependency_id: number;
  notes?: string | null;
}

export interface BusinessImpactAnalysisBase {
  rto_hours: number;
  rpo_hours: number;
  mtd_hours: number;
  hourly_downtime_cost: number;
  fixed_outage_cost: number;
  notes?: string | null;
}

export interface BusinessImpactAnalysisCreate extends BusinessImpactAnalysisBase {
  process_id: number;
}

export interface BusinessImpactAnalysisApproveRequest {
  notes?: string | null;
}

export interface BusinessImpactAnalysis extends BusinessImpactAnalysisBase {
  id: number;
  organization_id: number;
  process_id: number;
  status: BiaStatus;
  version: number;
  requested_by_id: number;
  approved_by_id?: number | null;
  approved_at?: string | null;
  created_at: string;
  updated_at: string;
  requested_by?: User;
  approved_by?: User;
}

export interface BusinessProcess extends BusinessProcessBase {
  id: number;
  organization_id: number;
  owner_id: number;
  created_at: string;
  updated_at: string;
  owner?: User;
  active_bia?: BusinessImpactAnalysis | null;
  dependencies?: ProcessDependency[];
}

export interface OutageCostCalculationRequest {
  duration_hours: number;
  hourly_downtime_cost: number;
  fixed_outage_cost?: number;
}

export interface OutageCostCalculationResult {
  duration_hours: number;
  fixed_outage_cost: number;
  hourly_downtime_cost: number;
  variable_outage_cost: number;
  total_projected_loss: number;
}
```

---

## 6. API Service Method Plan (`frontend/src/lib/resilienceService.ts`)

```typescript
import { api } from './api';
import type {
  BusinessImpactAnalysis,
  BusinessImpactAnalysisApproveRequest,
  BusinessImpactAnalysisCreate,
  BusinessProcess,
  BusinessProcessCreate,
  BusinessProcessUpdate,
  CriticalityTier,
  OutageCostCalculationRequest,
  OutageCostCalculationResult,
  ProcessDependency,
  ProcessDependencyCreate,
} from '../types';

export const resilienceService = {
  // ─── 1. Business Process Catalog ──────────────────────────────────────────
  createProcess: async (data: BusinessProcessCreate): Promise<BusinessProcess> => {
    const response = await api.post<BusinessProcess>('/resilience/processes', data);
    return response.data;
  },

  listProcesses: async (params?: {
    criticality_tier?: CriticalityTier;
    search?: string;
    skip?: number;
    limit?: number;
  }): Promise<BusinessProcess[]> => {
    const response = await api.get<BusinessProcess[]>('/resilience/processes', { params });
    return response.data;
  },

  getProcess: async (id: number): Promise<BusinessProcess> => {
    const response = await api.get<BusinessProcess>(`/resilience/processes/${id}`);
    return response.data;
  },

  updateProcess: async (id: number, data: BusinessProcessUpdate): Promise<BusinessProcess> => {
    const response = await api.put<BusinessProcess>(`/resilience/processes/${id}`, data);
    return response.data;
  },

  deleteProcess: async (id: number): Promise<void> => {
    await api.delete(`/resilience/processes/${id}`);
  },

  // ─── 2. Business Impact Analysis (BIA) ────────────────────────────────────
  draftBia: async (data: BusinessImpactAnalysisCreate): Promise<BusinessImpactAnalysis> => {
    const response = await api.post<BusinessImpactAnalysis>('/resilience/bia', data);
    return response.data;
  },

  listProcessBias: async (processId: number): Promise<BusinessImpactAnalysis[]> => {
    const response = await api.get<BusinessImpactAnalysis[]>(`/resilience/processes/${processId}/bia`);
    return response.data;
  },

  getBia: async (biaId: number): Promise<BusinessImpactAnalysis> => {
    const response = await api.get<BusinessImpactAnalysis>(`/resilience/bia/${biaId}`);
    return response.data;
  },

  updateDraftBia: async (
    biaId: number,
    data: BusinessImpactAnalysisCreate
  ): Promise<BusinessImpactAnalysis> => {
    const response = await api.put<BusinessImpactAnalysis>(`/resilience/bia/${biaId}`, data);
    return response.data;
  },

  approveBia: async (
    biaId: number,
    data?: BusinessImpactAnalysisApproveRequest
  ): Promise<BusinessImpactAnalysis> => {
    const response = await api.post<BusinessImpactAnalysis>(`/resilience/bia/${biaId}/approve`, data || {});
    return response.data;
  },

  archiveDraftBia: async (biaId: number): Promise<BusinessImpactAnalysis> => {
    const response = await api.post<BusinessImpactAnalysis>(`/resilience/bia/${biaId}/archive`);
    return response.data;
  },

  getActiveBia: async (processId: number): Promise<BusinessImpactAnalysis | null> => {
    const response = await api.get<BusinessImpactAnalysis | null>(`/resilience/processes/${processId}/bia/active`);
    return response.data;
  },

  // ─── 3. Process Dependencies ──────────────────────────────────────────────
  addDependency: async (data: ProcessDependencyCreate): Promise<ProcessDependency> => {
    const response = await api.post<ProcessDependency>('/resilience/dependencies', data);
    return response.data;
  },

  listDependencies: async (processId: number): Promise<ProcessDependency[]> => {
    const response = await api.get<ProcessDependency[]>(`/resilience/processes/${processId}/dependencies`);
    return response.data;
  },

  removeDependency: async (dependencyId: number): Promise<void> => {
    await api.delete(`/resilience/dependencies/${dependencyId}`);
  },

  // ─── 4. Deterministic Outage Loss Engine ──────────────────────────────────
  calculateOutageLoss: async (
    data: OutageCostCalculationRequest
  ): Promise<OutageCostCalculationResult> => {
    const response = await api.post<OutageCostCalculationResult>('/resilience/outage-loss', data);
    return response.data;
  },
};
```

---

## 7. RBAC UX Strategy

The frontend will reflect the exact server-side permission matrix via `useAuth()`:

```typescript
const canManage = hasRole('ADMIN', 'MANAGER', 'GRC_ANALYST');
const canApprove = hasRole('ADMIN', 'MANAGER');
const isReadOnly = hasRole('SECURITY_ANALYST', 'AUDITOR', 'VIEWER');
```

| Action / UI Element | ADMIN | MANAGER | GRC_ANALYST | SECURITY_ANALYST | AUDITOR | VIEWER | UX Treatment for Unauthorized Roles |
|---|---|---|---|---|---|---|---|
| **Create Process Button** | Visible | Visible | Visible | Hidden | Hidden | Hidden | Hidden from header |
| **Edit Process Metadata** | Enabled | Enabled | Enabled | Disabled | Disabled | Disabled | Button omitted or rendered as view-only badge |
| **Draft New BIA** | Enabled | Enabled | Enabled | Disabled | Disabled | Disabled | Action button omitted |
| **Approve BIA Action** | Enabled* | Enabled* | Disabled | Disabled | Disabled | Disabled | Disabled with tooltip: *"Requires Manager/Admin role"* |
| **Add / Delete Dependencies** | Enabled | Enabled | Enabled | Disabled | Disabled | Disabled | Delete buttons & "Link Dependency" omitted |
| **Outage Impact Simulator** | Interactive | Interactive | Interactive | Interactive | Interactive | Interactive | Read-only calculation available to all roles |

*\*Subject to four-eyes segregation-of-duties check.*

---

## 8. Four-Eyes Approval UX Strategy

The Four-Eyes Principle is enforced in the UI before API submission:

1. **Self-Approval Prohibition Check**:
   ```typescript
   const isRequester = currentBia.requested_by_id === currentUser.id;
   const canApproveBia = canApprove && !isRequester;
   ```
2. **Visual Warning & Segregation of Duties Banner**:
   - If `isRequester === true`, the "Approve BIA" button is disabled.
   - An informative alert is displayed:
     > ⚠️ **Segregation of Duties (Four-Eyes Principle)**: You cannot approve this BIA because you drafted it (`requested_by_id: #${user.id}`). A secondary qualified Manager or Administrator must review and approve this baseline.
3. **Server Attribution Safety**:
   - The approval dialog sends only optional `notes`.
   - `approved_by_id` and `approved_at` are NEVER passed from the client; they are derived server-side from the authenticated JWT session.

---

## 9. Immutability Strategy

In accordance with Phase 13 domain rules, once a BIA is `ACTIVE` or `SUPERSEDED`, it represents an authoritative baseline and cannot be mutated:

| Status | Visual Indicator | Edit Controls | Archival Controls | Immutability Banner |
|---|---|---|---|---|
| **`DRAFT`** | `bg-amber-500/10 text-amber-400 border-amber-500/30` | Enabled (if authorized) | Enabled | None (Editable draft) |
| **`ACTIVE`** | `bg-emerald-500/10 text-emerald-400 border-emerald-500/30` | **Disabled & Locked** | **Disabled** | 🔒 *"Approved Active Baseline — Immutable. To alter recovery thresholds, draft a new BIA version."* |
| **`SUPERSEDED`** | `bg-slate-800 text-slate-400 border-slate-700` | **Disabled & Locked** | **Disabled** | 🔒 *"Historical Superseded Baseline — Immutable audit record."* |
| **`ARCHIVED`** | `bg-rose-500/10 text-rose-400 border-rose-500/30` | **Disabled & Locked** | **Disabled** | 🚫 *"Archived Draft — Terminal status."* |

---

## 10. Dependency Management Strategy

The dependency management interface allows linking upstream enterprise entities:

1. **Vendor Dependencies (`VENDOR`)**:
   - Fetches active vendors from Phase 9 TPRM service (`tprmService.listVendors()`).
   - Displays vendor legal name, vendor tier (`TIER_1_CRITICAL`, `TIER_2_SIGNIFICANT`, etc.), and vendor status.
2. **Control Dependencies (`CONTROL`)**:
   - Fetches implemented controls from Phase 2 Control service.
   - Displays control subcategory identifier (e.g., `PR.DS-01`), title, and implementation status.
3. **Multi-Tenant Safety**:
   - The dependency modal selects ONLY from the authenticated tenant's entities.
   - Submissions pass `dependency_id` and `dependency_type`; the backend performs strict tenant verification (`HTTP 404` on cross-tenant attempts).

---

## 11. Outage Impact Visualization Strategy

An interactive deterministic loss calculator is rendered inside the Business Process Detail page:

```
+-----------------------------------------------------------------------------------+
|  Deterministic Outage Loss Simulator                                            |
|  Formula: Total Loss(H) = Fixed Outage Cost + (Hourly Downtime Cost x H)          |
|                                                                                   |
|  Downtime Duration (Hours): [  8.0 hrs  ]  <---------[ Slider: 0 to 72 hrs ]---->  |
|                                                                                   |
|  Fixed Disruption Cost:    $10,000.00                                            |
|  Variable Loss (8h @ $20k): $160,000.00                                           |
|  ======================================                                           |
|  Total Projected Outage Loss:  $170,000.00                                        |
|                                                                                   |
|  [ SVG Parametric Cost Curve & RTO/MTD Threshold Markers ]                        |
|   Loss ($)                                                                        |
|      ^                                                                            |
|      |                                                / (Total Projected Loss)    |
|      |                                   / (MTD: 24h)|                            |
|      |                      / (RTO: 4h) |            |                            |
|      |            ________/             |            |                            |
|      |  Fixed Cost                                                                |
|      +------------------------------------------------------------> Hours         |
+-----------------------------------------------------------------------------------+
```

- Uses accessible SVG with SVG paths, dashed threshold marker lines for `RTO` and `MTD`, and dynamic gradient fills.
- Zero external charting libraries (no chart.js, recharts, or d3).

---

## 12. Cross-Module Lineage Design

A dedicated component (`ResilienceLineageCard.tsx`) clarifies ControlSphere's multi-phase architecture:

```
[Phase 13 Business Process] (Catalog & Criticality Tiers 1-4)
             │
             ▼
[Phase 13 BIA Baseline] (RTO, RPO, MTD, Hourly & Fixed Losses)
             │
             ├──▶ [Phase 9 TPRM Vendors] (Third-Party Dependency SLA & Supply Chain Risk)
             └──▶ [Phase 2 Controls & Phase 7 CCM] (Internal Safeguards & Continuous Health)
             │
             ▼
[Phase 12 QUANTUM-GRC & Phase 10 Incidents] (Financial Loss Calibration & Incident Response)
```

---

## 13. Accessibility Considerations

- All interactive controls (buttons, tabs, sliders, modals) include standard `aria-label`, `aria-expanded`, and keyboard focus rings (`focus:ring-2 focus:ring-indigo-500`).
- Color badges pair color with text indicators (e.g., status badges include text and icons).
- Tables include explicit `<TableHead>`, `<TableHeaderCell>`, and scope attributes.
- SVG diagrams include `<title>` and `<desc>` elements for screen readers.

---

## 14. Responsive Behavior

- **Desktop (>= 1280px)**: 3-column metric cards, full data tables, side-by-side lineage and cost curve layout.
- **Tablet (768px - 1279px)**: 2-column grid, responsive horizontally scrollable tables.
- **Mobile (< 768px)**: 1-column stacked layout, full-width modal sheets with touch-friendly targets (minimum 44px hit areas).

---

## 15. Error, Loading, and Empty States

- **Loading States**: Centered `<LoadingSpinner message="Loading operational resilience telemetry..." />` on query fetch.
- **Error States**: Card-level error alerts with retry button (`refetch()`).
- **Empty States**:
  - Process Register: *"No business processes defined yet. Click 'New Business Process' to initialize the catalog."*
  - Dependencies: *"No third-party vendors or internal controls linked to this process."*
  - BIA History: *"No historical BIA versions found."*

---

## 16. Exact Files to Create

1. [`frontend/src/lib/resilienceService.ts`](file:///e:/PROJECT%20WORKSPACE%202/ControlSphere/frontend/src/lib/resilienceService.ts) — Full typed Axios API client for Phase 13 endpoints.
2. [`frontend/src/pages/ResiliencePage.tsx`](file:///e:/PROJECT%20WORKSPACE%202/ControlSphere/frontend/src/pages/ResiliencePage.tsx) — Main executive dashboard and business process catalog.
3. [`frontend/src/pages/BusinessProcessDetailPage.tsx`](file:///e:/PROJECT%20WORKSPACE%202/ControlSphere/frontend/src/pages/BusinessProcessDetailPage.tsx) — Deep-dive process detail, active baseline, dependencies, and outage curve.
4. [`frontend/src/components/resilience/ProcessModal.tsx`](file:///e:/PROJECT%20WORKSPACE%202/ControlSphere/frontend/src/components/resilience/ProcessModal.tsx) — Modal for creating/editing business processes.
5. [`frontend/src/components/resilience/BiaModal.tsx`](file:///e:/PROJECT%20WORKSPACE%202/ControlSphere/frontend/src/components/resilience/BiaModal.tsx) — Modal for drafting new BIA baselines.
6. [`frontend/src/components/resilience/BiaApprovalModal.tsx`](file:///e:/PROJECT%20WORKSPACE%202/ControlSphere/frontend/src/components/resilience/BiaApprovalModal.tsx) — Modal for four-eyes BIA approval.
7. [`frontend/src/components/resilience/DependencyModal.tsx`](file:///e:/PROJECT%20WORKSPACE%202/ControlSphere/frontend/src/components/resilience/DependencyModal.tsx) — Modal for attaching Phase 9 Vendors and Phase 2 Controls.
8. [`frontend/src/components/resilience/OutageImpactCard.tsx`](file:///e:/PROJECT%20WORKSPACE%202/ControlSphere/frontend/src/components/resilience/OutageImpactCard.tsx) — Interactive deterministic outage loss calculation card.
9. [`frontend/src/components/resilience/BiaHistoryCard.tsx`](file:///e:/PROJECT%20WORKSPACE%202/ControlSphere/frontend/src/components/resilience/BiaHistoryCard.tsx) — Version history table with lock badges and SoD audit details.
10. [`frontend/src/components/resilience/ResilienceLineageCard.tsx`](file:///e:/PROJECT%20WORKSPACE%202/ControlSphere/frontend/src/components/resilience/ResilienceLineageCard.tsx) — Multi-phase governance lineage card.

---

## 17. Exact Files to Modify

1. [`frontend/src/types/index.ts`](file:///e:/PROJECT%20WORKSPACE%202/ControlSphere/frontend/src/types/index.ts) — Append Phase 13 resilience TypeScript definitions.
2. [`frontend/src/App.tsx`](file:///e:/PROJECT%20WORKSPACE%202/ControlSphere/frontend/src/App.tsx) — Register `/resilience` and `/resilience/processes/:id` routes.
3. [`frontend/src/components/layout/Sidebar.tsx`](file:///e:/PROJECT%20WORKSPACE%202/ControlSphere/frontend/src/components/layout/Sidebar.tsx) — Add "Operational Resilience" navigation item under "Risk & Remediation" with `tag: 'Phase 13'`.

---

## 18. Dependency Analysis

- **NPM Dependencies Added**: `0` (Zero new dependencies required; leveraging React 19, TypeScript 5.9, React Query 5, Lucide React, and Tailwind CSS).
- **Python Backend Dependencies Added**: `0`.

---

## 19. Stage 3 Implementation Sequence

```
Step 1: TypeScript Contract Definition (frontend/src/types/index.ts)
Step 2: API Client Service Implementation (frontend/src/lib/resilienceService.ts)
Step 3: Component Development (frontend/src/components/resilience/*)
Step 4: Page Assembly (ResiliencePage.tsx & BusinessProcessDetailPage.tsx)
Step 5: Router & Navigation Integration (App.tsx & Sidebar.tsx)
Step 6: Production Build & TypeScript Verification (npm run build)
```

---

## 20. Security Invariants

1. **Zero Client Authority**: The frontend never assigns IDs, versions, statuses, timestamps, or actor attribution.
2. **Tenant Scoping**: All API requests rely on the backend JWT session; the client never injects or attempts to switch `organization_id`.
3. **Four-Eyes Enforcement**: UI prohibits self-approval by the creator while relying strictly on backend `HTTP 403` rejection as the authoritative barrier.
4. **Immutability Protection**: `ACTIVE` and `SUPERSEDED` records are read-only in the UI; mutations are blocked server-side with `HTTP 409`.
5. **Deterministic Formulas**: Outage loss projections use pure linear mathematics matching the server specification without stochastic randomness.
