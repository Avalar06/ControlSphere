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
