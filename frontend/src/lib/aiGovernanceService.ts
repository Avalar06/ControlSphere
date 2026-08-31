import { api } from './api';
import type {
  AIApprovalStatus,
  AIDeploymentApproval,
  AIDeploymentApprovalCreate,
  AIDeploymentApprovalReviewRequest,
  AIHostingType,
  AIIndexCalculateRequest,
  AIIndexCalculateResponse,
  AILifecycleState,
  AIModelCard,
  AIModelCardCreate,
  AIPostureSummaryResponse,
  AIRegulatoryTier,
  AISystem,
  AISystemCreate,
  AISystemStatusUpdate,
  AISystemType,
  AISystemUpdate,
} from '../types';

export const aiGovernanceService = {
  // ─── 1. AI System Registry & Governance ───────────────────────────────────

  createSystem: async (data: AISystemCreate): Promise<AISystem> => {
    const res = await api.post<AISystem>('/ai-governance/systems', data);
    return res.data;
  },

  listSystems: async (params?: {
    system_type?: AISystemType;
    regulatory_tier?: AIRegulatoryTier;
    lifecycle_state?: AILifecycleState;
    hosting_type?: AIHostingType;
    search?: string;
    skip?: number;
    limit?: number;
  }): Promise<AISystem[]> => {
    const res = await api.get<AISystem[]>('/ai-governance/systems', { params });
    return res.data;
  },

  getSystem: async (id: number): Promise<AISystem> => {
    const res = await api.get<AISystem>(`/ai-governance/systems/${id}`);
    return res.data;
  },

  updateSystem: async (id: number, data: AISystemUpdate): Promise<AISystem> => {
    const res = await api.put<AISystem>(`/ai-governance/systems/${id}`, data);
    return res.data;
  },

  deleteSystem: async (id: number): Promise<void> => {
    await api.delete(`/ai-governance/systems/${id}`);
  },

  updateLifecycle: async (
    id: number,
    data: AISystemStatusUpdate
  ): Promise<AISystem> => {
    const res = await api.post<AISystem>(`/ai-governance/systems/${id}/lifecycle`, data);
    return res.data;
  },

  // ─── 2. Model Cards & Algorithmic Safety ──────────────────────────────────

  createModelCard: async (
    systemId: number,
    data: AIModelCardCreate
  ): Promise<AIModelCard> => {
    const res = await api.post<AIModelCard>(
      `/ai-governance/systems/${systemId}/model-cards`,
      data
    );
    return res.data;
  },

  listModelCards: async (systemId: number): Promise<AIModelCard[]> => {
    const res = await api.get<AIModelCard[]>(
      `/ai-governance/systems/${systemId}/model-cards`
    );
    return res.data;
  },

  getModelCard: async (id: number): Promise<AIModelCard> => {
    const res = await api.get<AIModelCard>(`/ai-governance/model-cards/${id}`);
    return res.data;
  },

  // ─── 3. Four-Eyes Deployment Approvals ───────────────────────────────────

  requestDeploymentApproval: async (
    systemId: number,
    data: AIDeploymentApprovalCreate
  ): Promise<AIDeploymentApproval> => {
    const res = await api.post<AIDeploymentApproval>(
      `/ai-governance/systems/${systemId}/approvals`,
      data
    );
    return res.data;
  },

  listDeploymentApprovals: async (params?: {
    approval_status?: AIApprovalStatus;
    target_environment?: string;
  }): Promise<AIDeploymentApproval[]> => {
    const res = await api.get<AIDeploymentApproval[]>('/ai-governance/approvals', {
      params,
    });
    return res.data;
  },

  getDeploymentApproval: async (id: number): Promise<AIDeploymentApproval> => {
    const res = await api.get<AIDeploymentApproval>(
      `/ai-governance/approvals/${id}`
    );
    return res.data;
  },

  reviewDeploymentApproval: async (
    approvalId: number,
    data: AIDeploymentApprovalReviewRequest
  ): Promise<AIDeploymentApproval> => {
    const res = await api.post<AIDeploymentApproval>(
      `/ai-governance/approvals/${approvalId}/review`,
      data
    );
    return res.data;
  },

  // ─── 4. Telemetry, Calculators & Posture ──────────────────────────────────

  calculateIndex: async (
    data: AIIndexCalculateRequest
  ): Promise<AIIndexCalculateResponse> => {
    const res = await api.post<AIIndexCalculateResponse>(
      '/ai-governance/systems/calculate-index',
      data
    );
    return res.data;
  },

  getPostureSummary: async (): Promise<AIPostureSummaryResponse> => {
    const res = await api.get<AIPostureSummaryResponse>(
      '/ai-governance/systems/summary/posture'
    );
    return res.data;
  },
};
