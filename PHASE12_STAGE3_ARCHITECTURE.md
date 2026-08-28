# CONTROLSPHERE — PHASE 12 STAGE 3 ARCHITECTURAL SPECIFICATION
## FRONTEND QUANTUM-GRC GOVERNANCE WORKSPACE

---

## 1. EXECUTIVE BASELINE & GOVERNING PRINCIPLES

### Current Verified Checkpoint
- **Phases 1–11**: Fully implemented, released, and verified.
- **Phase 12 Stage 1 (Database & Domain Foundation)**: Complete (Alembic `0012`).
- **Phase 12 Stage 2 (REST API & Adversarial Security)**: Complete (Commit `3874f70`).
- **Backend Test Baseline**: **467/467 tests passing** (441 baseline + 20 ADV-P12 + 6 API integration).
- **Frontend Production Build**: **0 errors** (`tsc -b && vite build` clean).
- **External Dependencies**: **0 new Python packages, 0 new Node packages**.
- **Mathematical Specification**: Mathematically frozen in `PHASE12_ARCHITECTURE_HARDENED.md`.

---

### Core Architectural Axiom: Zero Client Calculation Authority

> [!IMPORTANT]
> The frontend is strictly a **presentation, orchestration, and visualization tier**. It **NEVER calculates or dictates authoritative risk metrics**.
> All of the following telemetry values are **server-authoritative** and calculated exclusively by the backend domain engine:
> - Base & Final Control Strength ($\text{CS}_{\text{base}}, \text{CS}$)
> - Severity-Weighted Finding Penalties ($\text{Penalty}_{\text{total}}$)
> - Vulnerability Factor ($\text{VULN}$)
> - Loss Event Frequency ($\text{LEF}$)
> - Single Loss Expectancy ($\text{SLE}$) & Mean Loss Magnitude ($\text{MLM}$)
> - Annualized Loss Expectancy ($\text{ALE}$)
> - Empirical Monte Carlo Percentiles ($P_{10}, P_{50}, P_{90}, P_{95}, P_{99}$)
> - Authoritative Empirical $\text{VaR}_{95\%}^{\text{sim}}$ and $\text{VaR}_{99\%}^{\text{sim}}$
> - Analytical Parametric Comparison $\text{VaR}_{95\%}^{\text{param}}$
> - Return on Security Investment ($\text{ROSI}$) and $\Delta\text{ALE}$
> - Financial Risk Appetite Breach State (`WITHIN_APPETITE`, `EXCEEDS_ALE`, `EXCEEDS_VAR`, `EXCEEDS_BOTH`)
> - Calculation & Rule Versions (`2026.12.1`, `SIM_PERT_V1`, `PENALTY_RULE_2026_1`)
> - Cryptographic Input Snapshot Hash (`input_snapshot_hash`)
> - Telemetry Staleness Flags (`is_ccm_stale`)

---

## 2. FRONTEND ARCHITECTURAL LANDSCAPE

### Technology Stack
- **Framework**: React 19 + TypeScript (Strict Mode)
- **Bundler & Build Tooling**: Vite + Rolldown
- **State Management & Caching**: `@tanstack/react-query` (Query invalidation on mutations, optimistic state isolation)
- **Routing**: `react-router-dom` v6
- **Styling & Design System**: Tailwind CSS + `clsx` / `tailwind-merge`
- **Iconography**: `lucide-react`
- **HTTP Client**: Axios instance configured with JWT interceptors (`frontend/src/lib/api.ts`)

---

### Existing Reusable UI Components
The Stage 3 frontend implementation will directly reuse the existing design system components located in `frontend/src/components/ui/`:
1. `Card`, `CardHeader` — Standard container with dark slate border and headers.
2. `Badge` — Status/severity pill indicators with semantic color variants (`success`, `warning`, `danger`, `info`, `neutral`).
3. `Button` — Action triggers with variant styling (`primary`, `secondary`, `danger`, `outline`, `ghost`) and loading spinner states.
4. `Modal` — Accessible overlay dialog for create/edit forms, simulation triggers, and confirmation dialogs.
5. `Table` — Multi-column data grid with hover states, sorting headers, and responsive overflow wrappers.
6. `LoadingSpinner` — Centered asynchronous loading indicator.
7. `Sidebar` — Multi-group enterprise sidebar navigation with active path matching and role-based link filtering.
8. `Header` — Top navbar displaying active tenant, breadcrumbs, user profile, and notification triggers.

---

## 3. TYPESCRIPT DATA MODEL & SCHEMAS

All TypeScript interfaces in `frontend/src/types/index.ts` will strictly reflect the backend Pydantic models from `backend/app/schemas/quant_risk.py`:

```typescript
// ─── Enums ──────────────────────────────────────────────────────────────────

export type ScenarioStatus = 'DRAFT' | 'ACTIVE' | 'FROZEN' | 'ARCHIVED';

export type ThreatActorCategory =
  | 'CYBERCRIMINAL'
  | 'NATION_STATE'
  | 'INSIDER'
  | 'HACKTIVIST'
  | 'ACCIDENTAL';

export type AppetiteStatus = 'DRAFT' | 'APPROVED' | 'SUPERSEDED';

export type AppetiteBreachState =
  | 'WITHIN_APPETITE'
  | 'EXCEEDS_ALE'
  | 'EXCEEDS_VAR'
  | 'EXCEEDS_BOTH';

// ─── 1. Quantitative Risk Scenarios ─────────────────────────────────────────

export interface QuantitativeRiskScenario {
  id: number;
  organization_id: number;
  scenario_code: string;
  title: string;
  description: string;
  status: ScenarioStatus;
  threat_actor_category: ThreatActorCategory;

  // Upstream Linkages
  risk_id?: number;
  organization_control_id?: number;
  vendor_id?: number;

  // Three-Point Estimation Parameters
  tef_min: number;
  tef_mode: number;
  tef_max: number;
  tcap: number;

  pl_min: number;
  pl_mode: number;
  pl_max: number;

  sl_min: number;
  sl_mode: number;
  sl_max: number;
  slop: number;

  // Server-Authoritative Telemetry
  control_strength: number;
  vulnerability_factor: number;
  loss_event_frequency: number;
  single_loss_expectancy: number;
  annualized_loss_expectancy: number;
  var_95_parametric?: number;
  var_99_parametric?: number;
  var_95_empirical?: number;
  var_99_empirical?: number;

  // Governance & Immutability
  is_immutable: boolean;
  is_ccm_stale: boolean;
  calculation_version: string;
  input_snapshot_hash?: string;
  calculated_at?: string;

  created_by_id: number;
  created_at: string;
  updated_at: string;
  created_by?: User;
}

export interface QuantitativeRiskScenarioCreate {
  scenario_code: string;
  title: string;
  description: string;
  threat_actor_category?: ThreatActorCategory;
  risk_id?: number;
  organization_control_id?: number;
  vendor_id?: number;
  tef_min?: number;
  tef_mode?: number;
  tef_max?: number;
  tcap?: number;
  pl_min?: number;
  pl_mode?: number;
  pl_max?: number;
  sl_min?: number;
  sl_mode?: number;
  sl_max?: number;
  slop?: number;
}

export interface QuantitativeRiskScenarioUpdate {
  title?: string;
  description?: string;
  threat_actor_category?: ThreatActorCategory;
  risk_id?: number;
  organization_control_id?: number;
  vendor_id?: number;
  tef_min?: number;
  tef_mode?: number;
  tef_max?: number;
  tcap?: number;
  pl_min?: number;
  pl_mode?: number;
  pl_max?: number;
  sl_min?: number;
  sl_mode?: number;
  sl_max?: number;
  slop?: number;
}

// ─── 2. Empirical Monte Carlo Simulations ───────────────────────────────────

export interface QuantitativeSimulationRequest {
  trial_count?: number; // Bounds: 100 <= N <= 50,000, default: 10,000
  simulation_seed?: number;
}

export interface QuantitativeSimulationRun {
  id: number;
  organization_id: number;
  scenario_id: number;
  trial_count: number;
  simulation_seed: number;
  algorithm_version: string;

  mean_loss: number;
  variance_loss: number;
  std_dev_loss: number;

  percentile_10: number;
  percentile_50: number;
  percentile_90: number;
  percentile_95: number;
  percentile_99: number;

  simulated_by_id: number;
  simulated_at: string;
  simulated_by?: User;
}

// ─── 3. Return on Security Investment (ROSI) ─────────────────────────────────

export interface RosiAnalysisCreate {
  remediation_plan_id: number;
  remediation_cost: number; // Must be > 0
  projected_control_strength_delta?: number;
}

export interface RosiAnalysis {
  id: number;
  organization_id: number;
  scenario_id: number;
  remediation_plan_id: number;

  remediation_cost: number;
  current_ale: number;
  projected_ale: number;
  risk_reduction_ale: number;
  net_economic_benefit: number;
  rosi_percentage: number;

  created_by_id: number;
  created_at: string;
  created_by?: User;
}

// ─── 4. Financial Risk Appetite ─────────────────────────────────────────────

export interface FinancialRiskAppetiteCreate {
  ale_limit: number;
  var_95_limit: number;
  notes?: string;
}

export interface FinancialRiskAppetiteApproveRequest {
  notes?: string;
}

export interface FinancialRiskAppetite {
  id: number;
  organization_id: number;
  version: number;
  ale_limit: number;
  var_95_limit: number;
  status: AppetiteStatus;
  notes?: string;

  requested_by_id: number;
  approved_by_id?: number;
  created_at: string;
  approved_at?: string;

  requested_by?: User;
  approved_by?: User;
}

// ─── 5. Portfolio Telemetry Overview ────────────────────────────────────────

export interface QuantOverviewResponse {
  total_scenarios: number;
  active_scenarios: number;
  frozen_scenarios: number;
  portfolio_ale: number;
  portfolio_var_95: number;
  appetite_status: AppetiteBreachState;
  ale_limit?: number;
  var_95_limit?: number;
  threat_category_distribution: Record<string, number>;
  top_risk_scenarios: QuantitativeRiskScenario[];
}
```

---

## 4. API SERVICE CLIENT CONTRACT (`quantRiskService.ts`)

A dedicated API client service will be implemented in `frontend/src/lib/quantRiskService.ts` mapping directly to the 19 Phase 12 REST endpoints:

```typescript
import { api } from './api';
import type {
  FinancialRiskAppetite,
  FinancialRiskAppetiteApproveRequest,
  FinancialRiskAppetiteCreate,
  QuantOverviewResponse,
  QuantitativeRiskScenario,
  QuantitativeRiskScenarioCreate,
  QuantitativeRiskScenarioUpdate,
  QuantitativeSimulationRequest,
  QuantitativeSimulationRun,
  RosiAnalysis,
  RosiAnalysisCreate,
  ScenarioStatus,
  ThreatActorCategory,
} from '../types';

export const quantRiskService = {
  // ─── 0. Portfolio Overview ────────────────────────────────────────────────
  getOverview: async (): Promise<QuantOverviewResponse> => {
    const res = await api.get<QuantOverviewResponse>('/quant-risk/overview');
    return res.data;
  },

  // ─── 1. Scenarios ─────────────────────────────────────────────────────────
  createScenario: async (data: QuantitativeRiskScenarioCreate): Promise<QuantitativeRiskScenario> => {
    const res = await api.post<QuantitativeRiskScenario>('/quant-risk/scenarios', data);
    return res.data;
  },

  listScenarios: async (params?: {
    status?: ScenarioStatus;
    threat_category?: ThreatActorCategory;
    search?: string;
    skip?: number;
    limit?: number;
  }): Promise<QuantitativeRiskScenario[]> => {
    const res = await api.get<QuantitativeRiskScenario[]>('/quant-risk/scenarios', { params });
    return res.data;
  },

  getScenario: async (id: number): Promise<QuantitativeRiskScenario> => {
    const res = await api.get<QuantitativeRiskScenario>(`/quant-risk/scenarios/${id}`);
    return res.data;
  },

  updateScenario: async (id: number, data: QuantitativeRiskScenarioUpdate): Promise<QuantitativeRiskScenario> => {
    const res = await api.put<QuantitativeRiskScenario>(`/quant-risk/scenarios/${id}`, data);
    return res.data;
  },

  activateScenario: async (id: number): Promise<QuantitativeRiskScenario> => {
    const res = await api.post<QuantitativeRiskScenario>(`/quant-risk/scenarios/${id}/activate`);
    return res.data;
  },

  freezeScenario: async (id: number): Promise<QuantitativeRiskScenario> => {
    const res = await api.post<QuantitativeRiskScenario>(`/quant-risk/scenarios/${id}/freeze`);
    return res.data;
  },

  archiveScenario: async (id: number): Promise<QuantitativeRiskScenario> => {
    const res = await api.post<QuantitativeRiskScenario>(`/quant-risk/scenarios/${id}/archive`);
    return res.data;
  },

  // ─── 2. Monte Carlo Simulation ────────────────────────────────────────────
  executeSimulation: async (scenarioId: number, data?: QuantitativeSimulationRequest): Promise<QuantitativeSimulationRun> => {
    const res = await api.post<QuantitativeSimulationRun>(`/quant-risk/scenarios/${scenarioId}/simulate`, data || {});
    return res.data;
  },

  listScenarioSimulations: async (scenarioId: number, params?: { skip?: number; limit?: number }): Promise<QuantitativeSimulationRun[]> => {
    const res = await api.get<QuantitativeSimulationRun[]>(`/quant-risk/scenarios/${scenarioId}/simulations`, { params });
    return res.data;
  },

  getSimulation: async (runId: number): Promise<QuantitativeSimulationRun> => {
    const res = await api.get<QuantitativeSimulationRun>(`/quant-risk/simulations/${runId}`);
    return res.data;
  },

  // ─── 3. ROSI ──────────────────────────────────────────────────────────────
  calculateRosi: async (scenarioId: number, data: RosiAnalysisCreate): Promise<RosiAnalysis> => {
    const res = await api.post<RosiAnalysis>(`/quant-risk/scenarios/${scenarioId}/rosi`, data);
    return res.data;
  },

  listScenarioRosi: async (scenarioId: number, params?: { skip?: number; limit?: number }): Promise<RosiAnalysis[]> => {
    const res = await api.get<RosiAnalysis[]>(`/quant-risk/scenarios/${scenarioId}/rosi`, { params });
    return res.data;
  },

  getRosiAnalysis: async (analysisId: number): Promise<RosiAnalysis> => {
    const res = await api.get<RosiAnalysis>(`/quant-risk/rosi/${analysisId}`);
    return res.data;
  },

  // ─── 4. Financial Risk Appetite & Governance ──────────────────────────────
  createRiskAppetite: async (data: FinancialRiskAppetiteCreate): Promise<FinancialRiskAppetite> => {
    const res = await api.post<FinancialRiskAppetite>('/quant-risk/appetites', data);
    return res.data;
  },

  listRiskAppetites: async (params?: { skip?: number; limit?: number }): Promise<FinancialRiskAppetite[]> => {
    const res = await api.get<FinancialRiskAppetite[]>('/quant-risk/appetites', { params });
    return res.data;
  },

  getCurrentAppetite: async (): Promise<FinancialRiskAppetite | null> => {
    const res = await api.get<FinancialRiskAppetite | null>('/quant-risk/appetites/current');
    return res.data;
  },

  getRiskAppetite: async (id: number): Promise<FinancialRiskAppetite> => {
    const res = await api.get<FinancialRiskAppetite>(`/quant-risk/appetites/${id}`);
    return res.data;
  },

  approveRiskAppetite: async (id: number, data?: FinancialRiskAppetiteApproveRequest): Promise<FinancialRiskAppetite> => {
    const res = await api.post<FinancialRiskAppetite>(`/quant-risk/appetites/${id}/approve`, data || {});
    return res.data;
  },
};
```

---

## 5. PROPOSED ROUTES & NAVIGATION ARCHITECTURE

### Application Shell Routing (`App.tsx`)
New Phase 12 routes will be added under the authenticated `AppLayout`:

| Route Path | Page Component | Description |
|:---|:---|:---|
| `/quant-risk` | `QuantRiskPage.tsx` | Main Executive Hub with tabs for Overview, Scenario Register, ROSI Portfolio, and Board Risk Appetite. |
| `/quant-risk/scenarios/:id` | `QuantScenarioDetailPage.tsx` | Comprehensive Scenario workspace: PERT assumptions, live decomposition, simulation engine, ROSI analyzer, and audit history. |

### Sidebar Navigation Integration (`Sidebar.tsx`)
Add a new navigation item under the **Risk & Remediation** or **Executive Assurance** nav group:
```typescript
{
  name: 'Cyber Risk Quantification (QUANTUM)',
  path: '/quant-risk',
  icon: Calculator, // or TrendingUp / DollarSign
  tag: 'Phase 12'
}
```

---

## 6. WORKSPACE & COMPONENT SPECIFICATIONS

### Workspace 1: Quantum-GRC Executive Dashboard
- **Executive Metric Cards**:
  - **Portfolio ALE**: Total expected annual financial loss across active/frozen scenarios (formatted in USD currency, e.g. `$1,240,500.00 / yr`).
  - **Portfolio $\text{VaR}_{95\%}$ Tail Exposure**: 95th percentile aggregate catastrophic loss.
  - **Active vs Frozen Scenarios**: Operational baseline breakdown.
  - **Board Risk Appetite Status Badge**:
    - `WITHIN_APPETITE`: Green badge ("Exposure within board-approved limits").
    - `EXCEEDS_ALE`: Amber badge ("Annual expected loss exceeds ALE threshold").
    - `EXCEEDS_VAR`: Amber badge ("Tail loss exceeds 95% VaR threshold").
    - `EXCEEDS_BOTH`: Red badge ("Critical: Exceeds both ALE and VaR thresholds").
- **Visual Distributions**:
  - CSS-based Threat Actor Distribution bars (`CYBERCRIMINAL`, `NATION_STATE`, `INSIDER`, `HACKTIVIST`, `ACCIDENTAL`).
  - Top 5 Financial Loss Scenarios ranking table with direct link to scenario deep-dive.

---

### Workspace 2: Risk Scenario Register & Workflow
- **Scenario Table**:
  - Code, Title, Threat Actor, Status badge (`DRAFT`, `ACTIVE`, `FROZEN`, `ARCHIVED`), Control Strength ($\text{CS}$), Vulnerability ($\text{VULN}$), Loss Frequency ($\text{LEF}$), Single Loss Expectancy ($\text{SLE}$), Annualized Loss Expectancy ($\text{ALE}$), Empirical $\text{VaR}_{95\%}$.
  - Visual indicator for `is_ccm_stale` (Amber warning clock icon: "CCM health telemetry is > 30 days old").
  - Visual indicator for `is_immutable` (Lock icon: "Frozen Baseline").
- **Filtering & Search**:
  - Search by scenario code, title, or description.
  - Filter by lifecycle status (`DRAFT`, `ACTIVE`, `FROZEN`, `ARCHIVED`) and threat actor category.
- **Scenario Creation / Edit Modal**:
  - Two-column input layout separating **Threat Frequency Inputs** ($\text{TEF}_{\min}, \text{TEF}_{\text{mode}}, \text{TEF}_{\max}, \text{TCAP}$) and **Loss Magnitude Inputs** ($\text{PL}_{\min}, \text{PL}_{\text{mode}}, \text{PL}_{\max}, \text{SL}_{\min}, \text{SL}_{\text{mode}}, \text{SL}_{\max}, \text{SLoP}$).
  - Linkage selectors to Phase 5 `Risk`, Phase 2 `OrganizationControl`, and Phase 9 `Vendor`.
  - Client-side validation enforcing $a \le m \le b$ before submit (with informative error tooltips).
  - Explicit notification that metrics ($\text{ALE}, \text{VaR}$) will be derived server-side upon save.

---

### Workspace 3: Scenario Detail & Risk Quantification Workspace
- **Scenario Header**:
  - Code, Title, Status badge, Immutability badge, Input Snapshot Hash tooltip.
  - Lifecycle action buttons: `Activate`, `Freeze Baseline`, `Archive`, `Edit Assumptions` (disabled if frozen).
- **FAIR Decomposition Flowchart (Visual Telemetry Pipeline)**:
  - Visual step-by-step pipeline cards displaying exact authoritative values:
    $$\text{TEF}_{\text{mean}} \times \text{VULN} \implies \text{LEF}$$
    $$\text{PL}_{\text{mean}} + (\text{SL}_{\text{mean}} \times \text{SLoP}) \implies \text{SLE}$$
    $$\text{LEF} \times \text{SLE} \implies \text{ALE}$$
- **Telemetry Breakdown Cards**:
  - **Control Strength Card**: Shows $\text{CS}_{\text{base}}$, active finding deductions ($w_i$), penalty cap, and final $\text{CS}$.
  - **Vulnerability Card**: Shows $\text{TCAP}$ vs $\text{CS}$ mitigating effect.
  - **Staleness Notice Banner**: Displayed if `is_ccm_stale == true`, explaining the 30-day cutoff and fallback baseline score.

---

### Workspace 4: Empirical Monte Carlo Simulation Workspace
- **Interactive Simulation Launcher**:
  - Trial Count Selector ($1,000$, $5,000$, $10,000$ [Default], $25,000$, $50,000$).
  - Optional Simulation Seed input for audit reproducibility.
  - `Run Simulation` button (requires `quantrisk:execute`, disabled with tooltip for Viewers/Auditors).
- **Empirical Results Presentation**:
  - Summary metrics: Mean Simulated Annual Loss ($\mu$), Standard Deviation ($\sigma$), Variance.
  - Percentile Loss Curve Table: $P_{10}$, $P_{50}$ (Median), $P_{90}$, $P_{95}$ (Authoritative Tail Loss), $P_{99}$ (Extreme Tail Loss).
  - Comparison Callout: Empirical $\text{VaR}_{95\%}$ vs Analytical Parametric $\text{VaR}_{95\%}$ (explaining distribution skewness and tail fatness).
- **Historical Simulation Run Archive**:
  - Immutable timeline list of past simulation runs with trial counts, seeds, execution timestamps, and user attribution.

---

### Workspace 5: Return on Security Investment (ROSI) Workspace
- **ROSI Evaluation Engine**:
  - Link candidate Phase 11 `RemediationPlan` via dropdown.
  - Remediation Cost input field in USD ($> \$0.00$).
  - Optional Projected Control Strength Delta override slider ($0.0 \dots 1.0$) or automatic derivation from Phase 11 $\text{REI}$ score.
  - `Calculate & Record ROSI` button.
- **Financial Return Metrics Display**:
  - Current $\text{ALE}$ vs Projected $\text{ALE}$.
  - Annual Risk Reduction ($\Delta\text{ALE}$).
  - Net Economic Benefit ($\Delta\text{ALE} - \text{Cost}$).
  - **$\text{ROSI}\%$ Pill Indicator**:
    - Positive ROSI: Green highlight ($+166.7\%$ — Investment yields positive economic return).
    - Negative ROSI: Amber/Red highlight ($-40.0\%$ — Remediation cost exceeds risk reduction).
- **Historical ROSI Analyses Table**:
  - Table of all recorded ROSI calculations for the scenario with plan codes, costs, and economic benefits.

---

### Workspace 6: Financial Risk Appetite & Four-Eyes Governance Workspace
- **Board Risk Appetite Configuration**:
  - Active Appetite Card: Version number, $\text{ALE}_{\text{limit}}$, $\text{VaR}_{95\%\text{limit}}$, Status (`APPROVED`), Request Date, Approved Date, Approver user attribution.
  - New Appetite Version Drafter: Form to propose adjusted limits and policy notes (sets status to `DRAFT`).
- **Four-Eyes Governance Review Panel**:
  - Draft Appetites list awaiting formal sign-off.
  - `Approve Appetite` Action Button:
    - Enabled only for `ADMIN` and `MANAGER` roles with `quantrisk:approve`.
    - **Self-Approval Guard**: If current logged-in user is `requested_by_id`, button is disabled with alert badge: *"Four-Eyes Governance: You are the requester and cannot approve your own risk appetite proposal. An independent manager must approve."*
- **Historical Version Audit Log**:
  - Audit trail of superseded appetite versions with previous thresholds and approval notes.

---

### Workspace 7: Cross-Module Risk Lineage & Mathematical Explainability
- **End-to-End Governance Lineage Diagram**:
  ```
  Phase 5 Qualitative Risk (Ordinal 1-25)
             ↓
  Phase 7 CCM Health Snapshots (30-day Freshness)
             ↓
  Phase 4 Active Findings Deductions (w_i Severity Weights)
             ↓
  Phase 9 TPRM Vendor Criticality (Threat Modifier)
             ↓
  Phase 12 FAIR Parameter Decomposition (TEF / TCAP / PL / SL / SLoP)
             ↓
  Phase 12 Deterministic Engine (CS → VULN → LEF → SLE → ALE)
             ↓
  Empirical Monte Carlo Simulation (P10 ... P99 Tail Loss VaR)
             ↓
  Phase 11 Remediation Plan Linkage → ROSI Analysis
             ↓
  Board Financial Risk Appetite → Portfolio Breach Posture
  ```
- **Formula Glossary Modal / Drawer**:
  - Clean markdown/KaTeX explanations of all authoritative formulas for auditor review.

---

## 7. RBAC PERMISSION MATRIX & UI BEHAVIOR

| User Role | `quantrisk:read` | `quantrisk:manage` | `quantrisk:execute` | `quantrisk:approve` | UI Behavioral Constraints |
|:---|:---:|:---:|:---:|:---:|:---|
| **ADMIN** | Yes | Yes | Yes | Yes | Full access to create/edit scenarios, trigger simulations, calculate ROSI, and approve appetites (with four-eyes separation). |
| **MANAGER** | Yes | Yes | Yes | Yes | Full access to create/edit scenarios, trigger simulations, calculate ROSI, and approve appetites (with four-eyes separation). |
| **GRC_ANALYST** | Yes | Yes | Yes | No | Can create/edit scenarios, execute simulations, and calculate ROSI. Appetite approval button disabled with "Manager approval required" tooltip. |
| **SECURITY_ANALYST** | Yes | Yes | Yes | No | Can create/edit scenarios, execute simulations, and calculate ROSI. Appetite approval button disabled. |
| **AUDITOR** | Yes | No | No | No | Read-only inspection of all workspaces. All action buttons (`Create`, `Edit`, `Simulate`, `ROSI`, `Approve`) hidden or disabled. |
| **VIEWER** | Yes | No | No | No | Read-only dashboard observation. Action controls hidden. |

---

## 8. FINANCIAL VISUALIZATION & TAIL LOSS STRATEGY

### Zero-External-Dependency Visualization Architecture
To strictly honor the **Zero New Dependencies** rule, financial loss curves and distributions will be rendered using pure Tailwind CSS and accessible SVG primitives:

1. **Tail Loss Percentile Bar Graphic (SVG)**:
   - Dynamic SVG horizontal box-and-whisker / multi-segment bar representing $P_{10} \to P_{50} \to P_{90} \to P_{95} \to P_{99}$.
   - Vertical marker indicating board $\text{VaR}_{95\%\text{limit}}$ threshold to visually highlight tail exposure breaches.
2. **ALE Loss Decomposition Sankey/Waterfall (CSS Flexbox)**:
   - Primary Loss vs Secondary Loss vs Control Mitigation bars demonstrating how $\text{CS}$ reduces loss exposure.
3. **ROSI Benefit Comparison Bar**:
   - Visual comparison between $\text{RemediationCost}$ and $\text{AnnualRiskReduction}$ ($\Delta\text{ALE}$).

---

## 9. EXACT IMPLEMENTATION FILE PLAN

### Files to Create in Stage 3:
1. `frontend/src/lib/quantRiskService.ts` — API service methods for all 19 Phase 12 endpoints.
2. `frontend/src/pages/QuantRiskPage.tsx` — Main Hub containing Executive Overview, Scenario Register, ROSI Portfolio, and Risk Appetite workspaces.
3. `frontend/src/pages/QuantScenarioDetailPage.tsx` — Detailed scenario quantification workspace, FAIR decomposition, Monte Carlo launcher, and ROSI evaluator.
4. `frontend/src/components/quant/QuantScenarioModal.tsx` — Modal dialog for scenario creation and editing with PERT interval validation.
5. `frontend/src/components/quant/SimulationRunModal.tsx` — Modal dialog for launching Monte Carlo trials with custom seeds.
6. `frontend/src/components/quant/RosiCalculatorModal.tsx` — Modal dialog for evaluating remediation plan ROSI.
7. `frontend/src/components/quant/RiskAppetiteModal.tsx` — Modal dialog for drafting new board risk appetite thresholds.
8. `frontend/src/components/quant/QuantLineageCard.tsx` — Visual lineage card showing Phase 5 $\to$ 7 $\to$ 9 $\to$ 10 $\to$ 11 $\to$ 12 integration.

### Files to Modify in Stage 3:
1. `frontend/src/types/index.ts` — Append Phase 12 TypeScript models and enums.
2. `frontend/src/App.tsx` — Register `/quant-risk` and `/quant-risk/scenarios/:id` routes.
3. `frontend/src/components/layout/Sidebar.tsx` — Add `Cyber Risk Quantification` navigation entry.

---

## 10. BACKEND & DEPENDENCY EVALUATION

- **Backend Changes Required**: **0** (Backend Stage 2 REST API and services completely fulfill all frontend requirements).
- **New npm Dependencies Required**: **0** (Standard library React, Lucide icons, Tailwind CSS, and TanStack Query fulfill all UI/UX requirements).

---

## 11. ACCEPTANCE CRITERIA FOR STAGE 3

1. **Zero Mathematical Authority on Client**: The UI displays authoritative backend values for CS, VULN, LEF, SLE, ALE, VaR, ROSI, and Appetite Breach State without client-side recalculation.
2. **Full Scenario Lifecycle**: Users can create, list, filter, view details, edit (when mutable), activate, freeze, and archive scenarios.
3. **Immutability Enforcement**: Frozen scenarios display lock badges and disable modification controls.
4. **Monte Carlo Simulation UX**: Users can launch simulations ($100 \le N \le 50,000$) with deterministic seeds and inspect empirical $P_{10} \dots P_{99}$ percentiles.
5. **ROSI Evaluation UX**: Users can link Phase 11 Remediation Plans and inspect positive/negative ROSI percentages and net benefits.
6. **Four-Eyes Appetite Governance UX**: Requester cannot approve their own appetite; approval transitions draft versions to active and marks previous versions as superseded.
7. **Clean Production Build**: `tsc -b && vite build` succeeds with **0 errors**.
8. **Preserved Test Baseline**: All **467 backend tests** continue to pass.

---

*PHASE 12 STAGE 3 ARCHITECTURAL REVIEW COMPLETE.*
*Awaiting explicit user authorization to begin Stage 3 implementation.*