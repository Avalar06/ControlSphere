import { api } from './api';
import type {
  BusinessImpactAnalysis,
  BusinessImpactAnalysisApproveRequest,
  BusinessImpactAnalysisCreate,
  BusinessProcess,
  BusinessProcessCreate,
  BusinessProcessUpdate,
  ContinuityPlan,
  ContinuityPlanCreate,
  ContinuityPlanDetail,
  ContinuityPlanStatus,
  ContinuityRecoveryStep,
  ContinuityRecoveryStepCreate,
  CriticalityTier,
  DependencyType,
  ExerciseEscalationRequest,
  ExerciseOutcome,
  ExerciseStatus,
  OutageCostCalculationRequest,
  OutageCostCalculationResult,
  ProcessDependency,
  ProcessDependencyCreate,
  ProcessDependencyHealth,
  ResilienceDashboard,
  ResilienceEvidenceLink,
  ResilienceEvidenceLinkCreate,
  ResilienceExercise,
  ResilienceExerciseCompleteRequest,
  ResilienceExerciseCreate,
  ResilienceExerciseDetail,
} from '../types';

export interface ProcessImpactSummary {
  process_id: number;
  process_name: string;
  criticality_tier: CriticalityTier;
  has_active_bia: boolean;
  active_bia_id?: number | null;
  rto_hours?: number | null;
  rpo_hours?: number | null;
  mtd_hours?: number | null;
  projected_24h_loss: number;
  total_dependencies: number;
  spof_count: number;
  unmitigated_spof_count: number;
  dependency_health_score: number;
  active_continuity_plan_id?: number | null;
  active_continuity_plan_version?: string | null;
  latest_exercise_id?: number | null;
  latest_exercise_outcome?: string | null;
  latest_actual_rto_hours?: number | null;
  latest_actual_rpo_hours?: number | null;
}

export interface OutageSimulationRequest {
  failing_node_type: DependencyType;
  failing_node_id: number;
  outage_duration_hours: number;
}

export interface OutageSimulationResponse {
  failing_node_type: DependencyType;
  failing_node_id: number;
  outage_duration_hours: number;
  affected_process_count: number;
  tier_1_affected_count: number;
  rto_breach_count: number;
  mtd_breach_count: number;
  total_projected_financial_loss: number;
  affected_processes: Array<{
    process_id: number;
    process_name: string;
    criticality_tier: CriticalityTier;
    hop_distance: number;
    effective_propagation_weight: number;
    projected_financial_loss: number;
    rto_breached: boolean;
    mtd_breached: boolean;
  }>;
}

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

  // ─── 3. Process Dependencies & Live Health ────────────────────────────────

  addDependency: async (data: ProcessDependencyCreate): Promise<ProcessDependency> => {
    const response = await api.post<ProcessDependency>('/resilience/dependencies', data);
    return response.data;
  },

  addProcessDependency: async (
    processId: number,
    data: ProcessDependencyCreate
  ): Promise<ProcessDependency> => {
    const response = await api.post<ProcessDependency>(
      `/resilience/processes/${processId}/dependencies`,
      data
    );
    return response.data;
  },

  listDependencies: async (processId: number): Promise<ProcessDependency[]> => {
    const response = await api.get<ProcessDependency[]>(`/resilience/processes/${processId}/dependencies`);
    return response.data;
  },

  removeDependency: async (dependencyId: number): Promise<void> => {
    await api.delete(`/resilience/dependencies/${dependencyId}`);
  },

  getDependencyHealth: async (processId: number): Promise<ProcessDependencyHealth> => {
    const response = await api.get<ProcessDependencyHealth>(
      `/resilience/processes/${processId}/dependency-health`
    );
    return response.data;
  },

  // ─── 4. Outage Loss, Blast-Radius Simulation & Dashboard Telemetry ────────

  calculateOutageLoss: async (
    data: OutageCostCalculationRequest
  ): Promise<OutageCostCalculationResult> => {
    const response = await api.post<OutageCostCalculationResult>('/resilience/outage-loss', data);
    return response.data;
  },

  simulateOutage: async (data: OutageSimulationRequest): Promise<OutageSimulationResponse> => {
    const response = await api.post<OutageSimulationResponse>('/resilience/simulate-outage', data);
    return response.data;
  },

  getProcessImpactSummary: async (processId: number): Promise<ProcessImpactSummary> => {
    const response = await api.get<ProcessImpactSummary>(
      `/resilience/processes/${processId}/impact-summary`
    );
    return response.data;
  },

  getDashboard: async (): Promise<ResilienceDashboard> => {
    const response = await api.get<ResilienceDashboard>('/resilience/dashboard');
    return response.data;
  },

  // ─── 5. Continuity Plans & Ordered Recovery Steps (Batch 5) ───────────────

  listContinuityPlans: async (
    processId: number,
    status?: ContinuityPlanStatus
  ): Promise<ContinuityPlan[]> => {
    const response = await api.get<ContinuityPlan[]>(
      `/resilience/processes/${processId}/continuity-plans`,
      { params: status ? { status } : undefined }
    );
    return response.data;
  },

  createContinuityPlan: async (
    processId: number,
    data: ContinuityPlanCreate
  ): Promise<ContinuityPlan> => {
    const response = await api.post<ContinuityPlan>(
      `/resilience/processes/${processId}/continuity-plans`,
      data
    );
    return response.data;
  },

  getContinuityPlanDetail: async (planId: number): Promise<ContinuityPlanDetail> => {
    const response = await api.get<ContinuityPlanDetail>(`/resilience/continuity-plans/${planId}`);
    return response.data;
  },

  updateContinuityPlan: async (
    planId: number,
    data: Partial<ContinuityPlanCreate>
  ): Promise<ContinuityPlan> => {
    const response = await api.patch<ContinuityPlan>(
      `/resilience/continuity-plans/${planId}`,
      data
    );
    return response.data;
  },

  listRecoverySteps: async (planId: number): Promise<ContinuityRecoveryStep[]> => {
    const response = await api.get<ContinuityRecoveryStep[]>(
      `/resilience/continuity-plans/${planId}/steps`
    );
    return response.data;
  },

  createRecoveryStep: async (
    planId: number,
    data: ContinuityRecoveryStepCreate
  ): Promise<ContinuityRecoveryStep> => {
    const response = await api.post<ContinuityRecoveryStep>(
      `/resilience/continuity-plans/${planId}/steps`,
      data
    );
    return response.data;
  },

  updateRecoveryStep: async (
    planId: number,
    stepId: number,
    data: Partial<ContinuityRecoveryStepCreate>
  ): Promise<ContinuityRecoveryStep> => {
    const response = await api.patch<ContinuityRecoveryStep>(
      `/resilience/continuity-plans/${planId}/steps/${stepId}`,
      data
    );
    return response.data;
  },

  deleteRecoveryStep: async (planId: number, stepId: number): Promise<void> => {
    await api.delete(`/resilience/continuity-plans/${planId}/steps/${stepId}`);
  },

  submitContinuityPlan: async (planId: number): Promise<ContinuityPlan> => {
    const response = await api.post<ContinuityPlan>(
      `/resilience/continuity-plans/${planId}/submit`
    );
    return response.data;
  },

  approveContinuityPlan: async (planId: number): Promise<ContinuityPlan> => {
    const response = await api.post<ContinuityPlan>(
      `/resilience/continuity-plans/${planId}/approve`
    );
    return response.data;
  },

  rejectContinuityPlan: async (planId: number, reason: string): Promise<ContinuityPlan> => {
    const response = await api.post<ContinuityPlan>(
      `/resilience/continuity-plans/${planId}/reject`,
      { reason }
    );
    return response.data;
  },

  archiveContinuityPlan: async (planId: number): Promise<ContinuityPlan> => {
    const response = await api.post<ContinuityPlan>(
      `/resilience/continuity-plans/${planId}/archive`
    );
    return response.data;
  },

  listPlanEvidence: async (planId: number): Promise<ResilienceEvidenceLink[]> => {
    const response = await api.get<ResilienceEvidenceLink[]>(
      `/resilience/continuity-plans/${planId}/evidence`
    );
    return response.data;
  },

  linkEvidenceToPlan: async (
    planId: number,
    data: ResilienceEvidenceLinkCreate
  ): Promise<ResilienceEvidenceLink> => {
    const response = await api.post<ResilienceEvidenceLink>(
      `/resilience/continuity-plans/${planId}/evidence`,
      data
    );
    return response.data;
  },

  // ─── 6. Resilience Exercises & Closed-Loop Escalation (Batch 5) ───────────

  listExercises: async (params?: {
    process_id?: number;
    continuity_plan_id?: number;
    status?: ExerciseStatus;
    outcome?: ExerciseOutcome;
    skip?: number;
    limit?: number;
  }): Promise<ResilienceExercise[]> => {
    const response = await api.get<ResilienceExercise[]>('/resilience/exercises', { params });
    return response.data;
  },

  createExercise: async (data: ResilienceExerciseCreate): Promise<ResilienceExercise> => {
    const response = await api.post<ResilienceExercise>('/resilience/exercises', data);
    return response.data;
  },

  getExerciseDetail: async (exerciseId: number): Promise<ResilienceExerciseDetail> => {
    const response = await api.get<ResilienceExerciseDetail>(`/resilience/exercises/${exerciseId}`);
    return response.data;
  },

  startExercise: async (
    exerciseId: number,
    started_at?: string
  ): Promise<ResilienceExercise> => {
    const response = await api.post<ResilienceExercise>(
      `/resilience/exercises/${exerciseId}/start`,
      started_at ? { started_at } : {}
    );
    return response.data;
  },

  completeExercise: async (
    exerciseId: number,
    data: ResilienceExerciseCompleteRequest
  ): Promise<ResilienceExercise> => {
    const response = await api.post<ResilienceExercise>(
      `/resilience/exercises/${exerciseId}/complete`,
      data
    );
    return response.data;
  },

  reviewExercise: async (
    exerciseId: number,
    review_notes?: string
  ): Promise<ResilienceExercise> => {
    const response = await api.post<ResilienceExercise>(
      `/resilience/exercises/${exerciseId}/review`,
      review_notes ? { review_notes } : {}
    );
    return response.data;
  },

  cancelExercise: async (
    exerciseId: number,
    reason?: string
  ): Promise<ResilienceExercise> => {
    const response = await api.post<ResilienceExercise>(
      `/resilience/exercises/${exerciseId}/cancel`,
      reason ? { reason } : {}
    );
    return response.data;
  },

  listExerciseEvidence: async (exerciseId: number): Promise<ResilienceEvidenceLink[]> => {
    const response = await api.get<ResilienceEvidenceLink[]>(
      `/resilience/exercises/${exerciseId}/evidence`
    );
    return response.data;
  },

  linkEvidenceToExercise: async (
    exerciseId: number,
    data: ResilienceEvidenceLinkCreate
  ): Promise<ResilienceEvidenceLink> => {
    const response = await api.post<ResilienceEvidenceLink>(
      `/resilience/exercises/${exerciseId}/evidence`,
      data
    );
    return response.data;
  },

  escalateExercise: async (
    exerciseId: number,
    data: ExerciseEscalationRequest
  ): Promise<ResilienceExercise> => {
    const response = await api.post<ResilienceExercise>(
      `/resilience/exercises/${exerciseId}/escalate`,
      data
    );
    return response.data;
  },
};
