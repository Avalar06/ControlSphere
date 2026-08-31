# PHASE 15 STAGE 3 — FRONTEND GOVERNANCE WORKSPACE ARCHITECTURE SPECIFICATION
## AI-GRC: Continuous Artificial Intelligence Governance & Algorithmic Risk Management

---

## 1. Executive Summary & Verified Repository Baseline

Phase 15 Stage 3 implements the enterprise Frontend Governance Workspace for the **AI-GRC (Artificial Intelligence Governance & Algorithmic Risk Management)** module in ControlSphere.

### Verified Git Baseline:
- **Baseline Commits**:
  - `50ec431`: `feat(phase15): implement ai governance domain foundation` (Stage 1)
  - `a73d0bd`: `feat(phase15): implement ai governance api and security` (Stage 2)
- **Branch**: `main` (`HEAD == origin/main`, working tree clean)
- **Alembic Head**: `0015` (`0015_ai_governance.py`)
- **Backend Test Baseline**: `662/662` tests passing (100% regression and integration)
- **Frontend Build Baseline**: `1,992` modules transformed, 0 errors

---

## 2. Verified API Contract (`/api/v1/ai-governance`)

All client communication is managed via the authenticated Axios client (`frontend/src/lib/api.ts`) against the `/ai-governance` router endpoints:

### 2.1 Endpoints Specification

| Method | Endpoint Path | Description | Required RBAC Permission | Request Body | Response Type |
|---|---|---|---|---|---|
| `POST` | `/ai-governance/systems` | Register new AI system & calculate server ARI | `Permission.AI_MANAGE` | `AISystemCreate` | `AISystemResponse` |
| `GET` | `/ai-governance/systems` | List tenant AI systems with query filtering | `Permission.AI_READ` | Query params (`system_type`, `regulatory_tier`, `lifecycle_state`, `hosting_type`, `search`, `skip`, `limit`) | `List[AISystemResponse]` |
| `GET` | `/ai-governance/systems/summary/posture` | Organization AI risk posture telemetry | `Permission.AI_READ` | None | `AIPostureSummaryResponse` |
| `POST` | `/ai-governance/systems/calculate-index` | Ephemeral ARI preview calculator (no write) | `Permission.AI_READ` | `AIIndexCalculateRequest` | `AIIndexCalculateResponse` |
| `GET` | `/ai-governance/systems/{id}` | Retrieve AI system with model cards & approvals | `Permission.AI_READ` | None | `AISystemResponse` |
| `PUT` | `/ai-governance/systems/{id}` | Update AI system metadata & recalculate ARI | `Permission.AI_MANAGE` | `AISystemUpdate` | `AISystemResponse` |
| `DELETE` | `/ai-governance/systems/{id}` | Delete non-production AI system | `Permission.AI_MANAGE` | None | `204 No Content` |
| `POST` | `/ai-governance/systems/{id}/lifecycle` | Transition system lifecycle state | `Permission.AI_MANAGE` | `AISystemStatusUpdate` | `AISystemResponse` |
| `POST` | `/ai-governance/systems/{id}/model-cards` | Publish new model card version & update ARI | `Permission.AI_ASSESS` | `AIModelCardCreate` | `AIModelCardResponse` |
| `GET` | `/ai-governance/systems/{id}/model-cards` | List model cards for an AI system | `Permission.AI_READ` | None | `List[AIModelCardResponse]` |
| `GET` | `/ai-governance/model-cards/{id}` | Get model card detail by ID | `Permission.AI_READ` | None | `AIModelCardResponse` |
| `POST` | `/ai-governance/systems/{id}/approvals` | Request Staging/Production deployment approval | `Permission.AI_MANAGE` | `AIDeploymentApprovalCreate` | `AIDeploymentApprovalResponse` |
| `GET` | `/ai-governance/approvals` | List all tenant deployment approval requests | `Permission.AI_READ` | Query params (`approval_status`, `target_environment`) | `List[AIDeploymentApprovalResponse]` |
| `GET` | `/ai-governance/approvals/{id}` | Get deployment approval by ID | `Permission.AI_READ` | None | `AIDeploymentApprovalResponse` |
| `POST` | `/ai-governance/approvals/{id}/review` | Review deployment request (Four-Eyes SoD) | `Permission.AI_APPROVE` | `AIDeploymentApprovalReviewRequest` | `AIDeploymentApprovalResponse` |

---

## 3. TypeScript Domain & Contract Mapping (`frontend/src/types/index.ts`)

```typescript
// ─── Phase 15: AI-GRC Domain Types ──────────────────────────────────────────

export type AISystemType =
  | 'LLM_APPLICATION'
  | 'AGENTIC_WORKFLOW'
  | 'EMBEDDED_ML'
  | 'COMPUTER_VISION'
  | 'RECOMMENDER'
  | 'PREDICTIVE_ANALYTICS';

export type AILifecycleState =
  | 'DEVELOPMENT'
  | 'VALIDATION'
  | 'ETHICAL_REVIEW'
  | 'APPROVED_STAGING'
  | 'PRODUCTION'
  | 'DECOMMISSIONED'
  | 'REJECTED';

export type AIRegulatoryTier =
  | 'PROHIBITED'
  | 'HIGH_RISK'
  | 'GPAI_SYSTEMIC_RISK'
  | 'LIMITED_RISK'
  | 'MINIMAL_RISK';

export type AIAutonomyLevel =
  | 'NO_AUTONOMY'
  | 'HUMAN_IN_THE_LOOP'
  | 'HUMAN_ON_THE_LOOP'
  | 'FULL_AUTONOMY';

export type AIDataSensitivity =
  | 'PUBLIC'
  | 'INTERNAL'
  | 'CONFIDENTIAL'
  | 'RESTRICTED_PII_PHI';

export type AIHostingType =
  | 'CLOUD_THIRD_PARTY'
  | 'ON_PREMISE_SELF_HOSTED'
  | 'HYBRID_VPC'
  | 'EDGE_DEVICE';

export type AIApprovalStatus =
  | 'PENDING'
  | 'APPROVED'
  | 'REJECTED'
  | 'WITHDRAWN';

export interface AIModelCardBase {
  version: string;
  intended_use: string;
  out_of_scope_uses?: string | null;
  bias_mitigation_notes?: string | null;
  training_data_provenance?: string | null;
  synthetic_data_percentage: number;
  hallucination_rate_percent: number;
  prompt_injection_resistance_score: number;
  toxicity_filter_efficiency_score: number;
  benchmark_eval_dataset?: string | null;
  benchmark_score?: number | null;
}

export interface AIModelCardCreate extends AIModelCardBase {}

export interface AIModelCard extends AIModelCardBase {
  id: number;
  organization_id: number;
  ai_system_id: number;
  created_at: string;
  updated_at: string;
}

export interface AIDeploymentApprovalCreate {
  target_environment: 'STAGING' | 'PRODUCTION';
  risk_acceptance_justification: string;
  human_oversight_measures: string;
}

export interface AIDeploymentApprovalReviewRequest {
  decision: 'APPROVED' | 'REJECTED';
  reviewer_notes?: string | null;
}

export interface AIDeploymentApproval {
  id: number;
  organization_id: number;
  ai_system_id: number;
  requested_by_id: number;
  reviewed_by_id?: number | null;
  target_environment: string;
  approval_status: AIApprovalStatus;
  risk_acceptance_justification: string;
  human_oversight_measures: string;
  reviewer_notes?: string | null;
  created_at: string;
  reviewed_at?: string | null;
  requested_by?: User | null;
  reviewed_by?: User | null;
}

export interface AISystemBase {
  system_code: string;
  name: string;
  description?: string | null;
  system_type: AISystemType;
  regulatory_tier: AIRegulatoryTier;
  autonomy_level: AIAutonomyLevel;
  data_sensitivity: AIDataSensitivity;
  hosting_type: AIHostingType;
  foundation_model_name?: string | null;
  model_version?: string | null;
  training_data_cutoff?: string | null;
  parameters_billion?: number | null;
  context_window_tokens?: number | null;
  compute_flops_exponent?: number | null;
  business_process_id?: number | null;
  vendor_id?: number | null;
  remediation_plan_id?: number | null;
}

export interface AISystemCreate extends AISystemBase {}

export interface AISystemUpdate {
  name?: string;
  description?: string | null;
  system_type?: AISystemType;
  regulatory_tier?: AIRegulatoryTier;
  autonomy_level?: AIAutonomyLevel;
  data_sensitivity?: AIDataSensitivity;
  hosting_type?: AIHostingType;
  foundation_model_name?: string | null;
  model_version?: string | null;
  training_data_cutoff?: string | null;
  parameters_billion?: number | null;
  context_window_tokens?: number | null;
  compute_flops_exponent?: number | null;
  business_process_id?: number | null;
  vendor_id?: number | null;
  remediation_plan_id?: number | null;
}

export interface AISystemStatusUpdate {
  lifecycle_state: AILifecycleState;
  notes?: string | null;
}

export interface AISystem extends AISystemBase {
  id: number;
  organization_id: number;
  lifecycle_state: AILifecycleState;
  algorithmic_risk_index: number;
  eu_compliance_score: number;
  is_prohibited_practice: boolean;
  requires_conformity_assessment: boolean;
  owner_id: number;
  approved_by_id?: number | null;
  approved_at?: string | null;
  created_at: string;
  updated_at: string;
  owner?: User | null;
  approved_by?: User | null;
  model_cards?: AIModelCard[];
  deployment_approvals?: AIDeploymentApproval[];
}

export interface AIIndexCalculateRequest {
  regulatory_tier: AIRegulatoryTier;
  autonomy_level: AIAutonomyLevel;
  data_sensitivity: AIDataSensitivity;
  process_tier?: string | null;
  hallucination_rate_percent?: number;
  prompt_injection_resistance_score?: number;
}

export interface AIIndexCalculateResponse {
  base_risk: number;
  autonomy_multiplier: number;
  process_tier_multiplier: number;
  safety_penalty: number;
  algorithmic_risk_index: number;
}

export interface AIPostureSummaryResponse {
  total_ai_systems: number;
  high_risk_systems: number;
  prohibited_systems: number;
  production_systems: number;
  pending_approvals_count: number;
  average_algorithmic_risk_index: number;
  tier_distribution: Record<string, number>;
  lifecycle_distribution: Record<string, number>;
}
```

---

## 4. Frontend Route & Navigation Architecture

### 4.1 Route Declarations (`frontend/src/App.tsx`)
```tsx
{/* Phase 15: AI Governance & Algorithmic Risk Management (AI-GRC) */}
<Route path="/ai-governance" element={<AIGovernancePage />} />
<Route path="/ai-governance/:id" element={<AISystemDetailPage />} />
```

### 4.2 Sidebar Navigation Group (`frontend/src/components/layout/Sidebar.tsx`)
Update `AI Governance` navigation group:
```tsx
{
  group: 'AI Governance',
  items: [
    { name: 'AI Systems & Risk', path: '/ai-governance', icon: Bot, tag: 'Phase 15' },
    { name: 'AI GRC Analyst', path: '/ai-analyst', icon: Sparkles, tag: 'Phase 9' },
  ],
}
```

---

## 5. Page & Component Hierarchy

```
frontend/src/
├── lib/
│   └── aiGovernanceService.ts           # Service API wrapper for all AI-GRC endpoints
├── pages/
│   ├── AIGovernancePage.tsx             # Master dashboard: posture telemetry, filters, registry table, calculator
│   └── AISystemDetailPage.tsx           # Deep dive: ARI telemetry, EU AI Act conformity, model cards, 4-Eyes approvals, lineage
└── components/
    └── ai/
        ├── AISystemModal.tsx            # Modal to Register / Edit an AI System
        ├── AILifecycleModal.tsx         # Modal to progress lifecycle state with validation
        ├── AIModelCardModal.tsx         # Modal to publish Model Card with safety benchmarks
        ├── AIDeploymentModal.tsx        # Modal to request Staging/Production deployment
        ├── AIApprovalReviewModal.tsx    # Modal for Four-Eyes deployment approval/rejection
        ├── AIRiskIndexCalculator.tsx    # Interactive ephemeral ARI calculation preview
        └── AILineageCard.tsx            # Visual cross-module lineage (TPRM, Resilience, Exposure, Remediation)
```

---

## 6. Security, Invariants & Architectural Boundaries

### 6.1 Zero Client Calculation Authority
- The frontend will **never** calculate or override Algorithmic Risk Index (ARI), Base Risk, multipliers, EU AI Act compliance scores, or conformity requirements.
- The `AIRiskIndexCalculator` component calls `POST /ai-governance/systems/calculate-index` for real-time mathematical simulation from the backend.

### 6.2 Role-Based Access Control (RBAC) UX Behavior
- **`ADMIN` / `MANAGER`**: Can create systems, edit metadata, request deployments, progress lifecycle, and review deployment approvals.
- **`GRC_ANALYST`**: Can create systems, edit metadata, progress lifecycle, and request deployment approvals (cannot review/approve deployment requests).
- **`SECURITY_ANALYST`**: Can publish model cards and benchmark safety metrics (cannot create/delete systems or approve deployments).
- **`AUDITOR` / `VIEWER`**: Read-only access to all dashboards, detail views, and calculation previews. Mutation buttons are omitted or disabled.

### 6.3 Four-Eyes Segregation of Duties (SoD) UX Guardrail
- If `currentUser.id === approval.requested_by_id`:
  - Review action buttons are disabled.
  - An amber banner is displayed: *"Segregation of Duties Enforcement: You requested this deployment and cannot approve your own request."*

### 6.4 Prohibited AI Practices Guardrail (EU AI Act Article 5)
- Systems with `regulatory_tier === 'PROHIBITED'` render a prominent red alert banner: *"PROHIBITED PRACTICE (EU AI Act Article 5) — Banned from staging or production deployment."*
- Deployment approval request actions for `PRODUCTION` or `STAGING` are disabled.

### 6.5 Decommissioned / Rejected Immutability Guardrail
- Systems in `DECOMMISSIONED` or `REJECTED` states render a locked status badge.
- Edit, Model Card attachment, Lifecycle change, and Deployment approval controls are disabled/hidden.

### 6.6 Multi-Tenant Isolation
- The frontend never submits `organization_id` in request payloads.
- Organization scoping is enforced server-side from the JWT bearer token.

---

## 7. Implementation File List

### 7.1 Files to Create (9 new files)
1. `frontend/src/lib/aiGovernanceService.ts`
2. `frontend/src/pages/AIGovernancePage.tsx`
3. `frontend/src/pages/AISystemDetailPage.tsx`
4. `frontend/src/components/ai/AISystemModal.tsx`
5. `frontend/src/components/ai/AILifecycleModal.tsx`
6. `frontend/src/components/ai/AIModelCardModal.tsx`
7. `frontend/src/components/ai/AIDeploymentModal.tsx`
8. `frontend/src/components/ai/AIApprovalReviewModal.tsx`
9. `frontend/src/components/ai/AIRiskIndexCalculator.tsx`
10. `frontend/src/components/ai/AILineageCard.tsx`

### 7.2 Files to Modify (3 existing files)
1. `frontend/src/types/index.ts` (Add AI-GRC TypeScript interfaces & enums)
2. `frontend/src/App.tsx` (Register `/ai-governance` and `/ai-governance/:id` routes)
3. `frontend/src/components/layout/Sidebar.tsx` (Add `AI Systems & Risk` navigation link with `Bot` icon)

---

## 8. Verification & Test Plan

1. **Type Checking & Production Build**:
   ```bash
   cd frontend && npm run build
   ```
   Must pass with 0 TypeScript and Vite compilation errors.
2. **Backend Regression Integrity**:
   ```bash
   cd backend && pytest tests -q
   ```
   Must maintain 662/662 passing backend tests with zero regression.
3. **Manual Flow & UX Verification**:
   - Navigation from Sidebar to `/ai-governance`.
   - Posture summary cards & ARI telemetry gauge visualization.
   - Creating an AI system with cross-module linkages.
   - Real-time ARI calculator preview.
   - Publishing Model Cards and viewing real-time safety penalty updates.
   - Four-Eyes deployment approval workflow and self-approval block.
   - Prohibited AI practice restriction badge and disabled deployment buttons.
   - Decommissioned state lock and immutability.
