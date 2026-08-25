import { api } from './api';
import type {
  Finding,
  FindingEvidence,
  FindingSeverity,
  FindingStats,
  FindingStatus,
  FindingType,
} from '../types';

export const findingService = {
  async getFindings(params?: {
    organization_control_id?: number;
    assessment_id?: number;
    owner_id?: number;
    status?: FindingStatus;
    severity?: FindingSeverity;
    finding_type?: FindingType;
    risk_band?: string;
    overdue_only?: boolean;
    search?: string;
    skip?: number;
    limit?: number;
  }): Promise<Finding[]> {
    const res = await api.get<Finding[]>('/api/v1/findings', { params });
    return res.data;
  },

  async getFindingById(id: number): Promise<Finding> {
    const res = await api.get<Finding>(`/api/v1/findings/${id}`);
    return res.data;
  },

  async getFindingStats(): Promise<FindingStats> {
    const res = await api.get<FindingStats>('/api/v1/findings/stats');
    return res.data;
  },

  async createFinding(data: {
    organization_control_id: number;
    assessment_id?: number;
    title: string;
    description: string;
    finding_type?: FindingType;
    severity?: FindingSeverity;
    impact: number;
    likelihood: number;
    recommendation: string;
    root_cause?: string;
    due_date?: string;
    remediation_plan?: string;
    owner_id?: number;
  }): Promise<Finding> {
    const res = await api.post<Finding>('/api/v1/findings', data);
    return res.data;
  },

  async updateFinding(
    id: number,
    data: {
      title?: string;
      description?: string;
      finding_type?: FindingType;
      severity?: FindingSeverity;
      impact?: number;
      likelihood?: number;
      recommendation?: string;
      root_cause?: string;
      due_date?: string;
      remediation_plan?: string;
      remediation_notes?: string;
      owner_id?: number;
    }
  ): Promise<Finding> {
    const res = await api.patch<Finding>(`/api/v1/findings/${id}`, data);
    return res.data;
  },

  async updateStatus(
    id: number,
    data: {
      status: FindingStatus;
      notes?: string;
      resolution?: string;
    }
  ): Promise<Finding> {
    const res = await api.post<Finding>(`/api/v1/findings/${id}/status`, data);
    return res.data;
  },

  async validateFinding(
    id: number,
    data: {
      is_valid: boolean;
      validation_notes: string;
    }
  ): Promise<Finding> {
    const res = await api.post<Finding>(`/api/v1/findings/${id}/validate`, data);
    return res.data;
  },

  async acceptRisk(
    id: number,
    data: {
      justification: string;
      expiry_date?: string;
    }
  ): Promise<Finding> {
    const res = await api.post<Finding>(`/api/v1/findings/${id}/risk-acceptance`, data);
    return res.data;
  },

  async linkEvidence(findingId: number, evidenceId: number): Promise<FindingEvidence> {
    const res = await api.post<FindingEvidence>(`/api/v1/findings/${findingId}/evidence`, {
      evidence_id: evidenceId,
    });
    return res.data;
  },

  async unlinkEvidence(findingId: number, evidenceId: number): Promise<void> {
    await api.delete(`/api/v1/findings/${findingId}/evidence/${evidenceId}`);
  },
};
