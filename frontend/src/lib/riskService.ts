import { api } from './api';
import type {
  HeatmapCell,
  Risk,
  RiskCategory,
  RiskControlLink,
  RiskFindingLink,
  RiskSource,
  RiskStats,
  RiskStatus,
  RiskTreatmentStrategy,
} from '../types';

export interface RiskFilterParams {
  status?: RiskStatus;
  risk_category?: RiskCategory;
  risk_source?: RiskSource;
  treatment_strategy?: RiskTreatmentStrategy;
  inherent_band?: string;
  appetite_status?: string;
  owner_id?: number;
  overdue_treatment?: boolean;
  search?: string;
  skip?: number;
  limit?: number;
}

export interface RiskCreatePayload {
  title: string;
  description: string;
  risk_category?: RiskCategory;
  risk_source?: RiskSource;
  inherent_impact: number;
  inherent_likelihood: number;
  target_risk_band?: string;
  owner_id?: number;
  treatment_strategy?: RiskTreatmentStrategy;
  treatment_plan?: string;
  treatment_owner_id?: number;
  treatment_due_date?: string;
  review_date?: string;
}

export interface RiskUpdatePayload {
  title?: string;
  description?: string;
  risk_category?: RiskCategory;
  risk_source?: RiskSource;
  owner_id?: number;
  inherent_impact?: number;
  inherent_likelihood?: number;
  residual_impact?: number;
  residual_likelihood?: number;
  target_risk_band?: string;
  treatment_strategy?: RiskTreatmentStrategy;
  treatment_plan?: string;
  treatment_owner_id?: number;
  treatment_due_date?: string;
  review_date?: string;
}

export interface RiskAcceptancePayload {
  justification: string;
  expiry_date?: string;
}

export const riskService = {
  listRisks: async (params?: RiskFilterParams): Promise<Risk[]> => {
    const res = await api.get<Risk[]>('/api/v1/risks', { params });
    return res.data;
  },

  getRisk: async (id: number): Promise<Risk> => {
    const res = await api.get<Risk>(`/api/v1/risks/${id}`);
    return res.data;
  },

  getStats: async (): Promise<RiskStats> => {
    const res = await api.get<RiskStats>('/api/v1/risks/stats');
    return res.data;
  },

  getHeatmap: async (): Promise<HeatmapCell[]> => {
    const res = await api.get<HeatmapCell[]>('/api/v1/risks/heatmap');
    return res.data;
  },

  createRisk: async (payload: RiskCreatePayload): Promise<Risk> => {
    const res = await api.post<Risk>('/api/v1/risks', payload);
    return res.data;
  },

  updateRisk: async (id: number, payload: RiskUpdatePayload): Promise<Risk> => {
    const res = await api.patch<Risk>(`/api/v1/risks/${id}`, payload);
    return res.data;
  },

  updateStatus: async (
    id: number,
    status: RiskStatus,
    notes?: string
  ): Promise<Risk> => {
    const res = await api.post<Risk>(`/api/v1/risks/${id}/status`, { status, notes });
    return res.data;
  },

  acceptRisk: async (
    id: number,
    payload: RiskAcceptancePayload
  ): Promise<Risk> => {
    const res = await api.post<Risk>(`/api/v1/risks/${id}/risk-acceptance`, payload);
    return res.data;
  },

  linkControl: async (
    riskId: number,
    organizationControlId: number
  ): Promise<RiskControlLink> => {
    const res = await api.post<RiskControlLink>(`/api/v1/risks/${riskId}/controls`, {
      organization_control_id: organizationControlId,
    });
    return res.data;
  },

  unlinkControl: async (
    riskId: number,
    controlId: number
  ): Promise<void> => {
    await api.delete(`/api/v1/risks/${riskId}/controls/${controlId}`);
  },

  linkFinding: async (
    riskId: number,
    findingId: number
  ): Promise<RiskFindingLink> => {
    const res = await api.post<RiskFindingLink>(`/api/v1/risks/${riskId}/findings`, {
      finding_id: findingId,
    });
    return res.data;
  },

  unlinkFinding: async (
    riskId: number,
    findingId: number
  ): Promise<void> => {
    await api.delete(`/api/v1/risks/${riskId}/findings/${findingId}`);
  },
};
