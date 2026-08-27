import { api } from './api';
import type {
  RemediationEvidenceLink,
  RemediationEvidenceLinkCreate,
  RemediationOverviewResponse,
  RemediationPlan,
  RemediationPlanApproveRequest,
  RemediationPlanCancelRequest,
  RemediationPlanCreate,
  RemediationPlanDetailRead,
  RemediationPlanRejectValidationRequest,
  RemediationPlanUpdate,
  RemediationPlanVerifyCloseRequest,
  RemediationReTestCreate,
  RemediationReTestRecord,
  RemediationSeverity,
  RemediationSourceType,
  RemediationStatus,
  RemediationTask,
  RemediationTaskCreate,
  RemediationTaskUpdate,
} from '../types';

export const remediationService = {
  // ─── 1. Overview & Enterprise Telemetry ───────────────────────────────────

  getOverview: async (): Promise<RemediationOverviewResponse> => {
    const response = await api.get<RemediationOverviewResponse>('/remediations/overview');
    return response.data;
  },

  // ─── 2. Remediation Plan Portfolio ────────────────────────────────────────

  listPlans: async (params?: {
    status?: RemediationStatus;
    severity?: RemediationSeverity;
    source_type?: RemediationSourceType;
    search?: string;
    skip?: number;
    limit?: number;
  }): Promise<RemediationPlan[]> => {
    const response = await api.get<RemediationPlan[]>('/remediations', { params });
    return response.data;
  },

  getPlan: async (id: number): Promise<RemediationPlanDetailRead> => {
    const response = await api.get<RemediationPlanDetailRead>(`/remediations/${id}`);
    return response.data;
  },

  createPlan: async (data: RemediationPlanCreate): Promise<RemediationPlan> => {
    const response = await api.post<RemediationPlan>('/remediations', data);
    return response.data;
  },

  updatePlan: async (id: number, data: RemediationPlanUpdate): Promise<RemediationPlan> => {
    const response = await api.patch<RemediationPlan>(`/remediations/${id}`, data);
    return response.data;
  },

  // ─── 3. Governance Lifecycle Actions ──────────────────────────────────────

  approvePlan: async (
    id: number,
    data: RemediationPlanApproveRequest
  ): Promise<RemediationPlan> => {
    const response = await api.post<RemediationPlan>(`/remediations/${id}/approve`, data);
    return response.data;
  },

  startPlan: async (id: number): Promise<RemediationPlan> => {
    const response = await api.post<RemediationPlan>(`/remediations/${id}/start`);
    return response.data;
  },

  submitForValidation: async (id: number): Promise<RemediationPlan> => {
    const response = await api.post<RemediationPlan>(`/remediations/${id}/submit-validation`);
    return response.data;
  },

  rejectValidation: async (
    id: number,
    data: RemediationPlanRejectValidationRequest
  ): Promise<RemediationPlan> => {
    const response = await api.post<RemediationPlan>(`/remediations/${id}/reject-validation`, data);
    return response.data;
  },

  verifyClose: async (
    id: number,
    data: RemediationPlanVerifyCloseRequest
  ): Promise<RemediationPlan> => {
    const response = await api.post<RemediationPlan>(`/remediations/${id}/verify-close`, data);
    return response.data;
  },

  cancelPlan: async (
    id: number,
    data: RemediationPlanCancelRequest
  ): Promise<RemediationPlan> => {
    const response = await api.post<RemediationPlan>(`/remediations/${id}/cancel`, data);
    return response.data;
  },

  // ─── 4. Task Management ───────────────────────────────────────────────────

  listTasks: async (planId: number): Promise<RemediationTask[]> => {
    const response = await api.get<RemediationTask[]>(`/remediations/${planId}/tasks`);
    return response.data;
  },

  createTask: async (planId: number, data: RemediationTaskCreate): Promise<RemediationTask> => {
    const response = await api.post<RemediationTask>(`/remediations/${planId}/tasks`, data);
    return response.data;
  },

  updateTask: async (
    taskId: number,
    data: RemediationTaskUpdate
  ): Promise<RemediationTask> => {
    const response = await api.patch<RemediationTask>(`/remediations/tasks/${taskId}`, data);
    return response.data;
  },

  startTask: async (taskId: number): Promise<RemediationTask> => {
    const response = await api.post<RemediationTask>(`/remediations/tasks/${taskId}/start`);
    return response.data;
  },

  completeTask: async (taskId: number): Promise<RemediationTask> => {
    const response = await api.post<RemediationTask>(`/remediations/tasks/${taskId}/complete`);
    return response.data;
  },

  cancelTask: async (taskId: number): Promise<RemediationTask> => {
    const response = await api.post<RemediationTask>(`/remediations/tasks/${taskId}/cancel`);
    return response.data;
  },

  // ─── 5. Evidence Links ────────────────────────────────────────────────────

  listEvidence: async (taskId: number): Promise<RemediationEvidenceLink[]> => {
    const response = await api.get<RemediationEvidenceLink[]>(
      `/remediations/tasks/${taskId}/evidence`
    );
    return response.data;
  },

  linkEvidence: async (
    taskId: number,
    data: RemediationEvidenceLinkCreate
  ): Promise<RemediationEvidenceLink> => {
    const response = await api.post<RemediationEvidenceLink>(
      `/remediations/tasks/${taskId}/evidence`,
      data
    );
    return response.data;
  },

  unlinkEvidence: async (taskId: number, linkId: number): Promise<void> => {
    await api.delete(`/remediations/tasks/${taskId}/evidence/${linkId}`);
  },

  // ─── 6. Re-Test Records ───────────────────────────────────────────────────

  listRetests: async (planId: number): Promise<RemediationReTestRecord[]> => {
    const response = await api.get<RemediationReTestRecord[]>(
      `/remediations/${planId}/retests`
    );
    return response.data;
  },

  recordRetest: async (
    planId: number,
    data: RemediationReTestCreate
  ): Promise<RemediationReTestRecord> => {
    const response = await api.post<RemediationReTestRecord>(
      `/remediations/${planId}/retests`,
      data
    );
    return response.data;
  },
};
