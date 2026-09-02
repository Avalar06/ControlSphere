import { api } from './api';
import type {
  CloudAsset,
  CloudAssetCreate,
  CloudAssetStatusUpdate,
  CloudAssetUpdate,
  CloudBenchmarkRule,
  CloudBenchmarkRuleCreate,
  CloudConfigurationDrift,
  CloudConfigurationDriftCreate,
  CloudEnvironment,
  CloudIAMBlastRadius,
  CloudIAMBlastRadiusCreate,
  CloudIAMBlastRadiusPreviewRequest,
  CloudIAMBlastRadiusPreviewResponse,
  CloudLifecycleState,
  CloudPostureStatus,
  CloudPostureSummaryResponse,
  CloudProvider,
  CloudSecurityBenchmark,
  CloudSecurityBenchmarkCreate,
  CloudSecurityFinding,
  CloudSecurityFindingCreate,
  DriftStatus,
  EvaluationStatus,
  RuleSeverity,
} from '../types';

export const cloudSecService = {
  // ─── 1. Cloud Assets ────────────────────────────────────────────────────────

  createAsset: async (data: CloudAssetCreate): Promise<CloudAsset> => {
    const res = await api.post<CloudAsset>('/cloud-security/assets', data);
    return res.data;
  },

  listAssets: async (params?: {
    provider?: CloudProvider;
    environment?: CloudEnvironment;
    posture_status?: CloudPostureStatus;
    lifecycle_state?: CloudLifecycleState;
  }): Promise<CloudAsset[]> => {
    const res = await api.get<CloudAsset[]>('/cloud-security/assets', { params });
    return res.data;
  },

  getAsset: async (id: number): Promise<CloudAsset> => {
    const res = await api.get<CloudAsset>(`/cloud-security/assets/${id}`);
    return res.data;
  },

  updateAsset: async (id: number, data: CloudAssetUpdate): Promise<CloudAsset> => {
    const res = await api.patch<CloudAsset>(`/cloud-security/assets/${id}`, data);
    return res.data;
  },

  updateAssetStatus: async (id: number, data: CloudAssetStatusUpdate): Promise<CloudAsset> => {
    const res = await api.post<CloudAsset>(`/cloud-security/assets/${id}/status`, data);
    return res.data;
  },

  deleteAsset: async (id: number): Promise<void> => {
    await api.delete(`/cloud-security/assets/${id}`);
  },

  // ─── 2. Benchmarks & Rules ──────────────────────────────────────────────────

  createBenchmark: async (data: CloudSecurityBenchmarkCreate): Promise<CloudSecurityBenchmark> => {
    const res = await api.post<CloudSecurityBenchmark>('/cloud-security/benchmarks', data);
    return res.data;
  },

  listBenchmarks: async (params?: { provider?: CloudProvider }): Promise<CloudSecurityBenchmark[]> => {
    const res = await api.get<CloudSecurityBenchmark[]>('/cloud-security/benchmarks', { params });
    return res.data;
  },

  createRule: async (data: CloudBenchmarkRuleCreate): Promise<CloudBenchmarkRule> => {
    const res = await api.post<CloudBenchmarkRule>('/cloud-security/rules', data);
    return res.data;
  },

  listRules: async (params?: { benchmark_id?: number }): Promise<CloudBenchmarkRule[]> => {
    const res = await api.get<CloudBenchmarkRule[]>('/cloud-security/rules', { params });
    return res.data;
  },

  // ─── 3. Findings & Evaluations ──────────────────────────────────────────────

  recordFinding: async (data: CloudSecurityFindingCreate): Promise<CloudSecurityFinding> => {
    const res = await api.post<CloudSecurityFinding>('/cloud-security/findings', data);
    return res.data;
  },

  listFindings: async (params?: {
    asset_id?: number;
    evaluation_status?: EvaluationStatus;
    severity?: RuleSeverity;
  }): Promise<CloudSecurityFinding[]> => {
    const res = await api.get<CloudSecurityFinding[]>('/cloud-security/findings', { params });
    return res.data;
  },

  // ─── 4. Configuration Drift ─────────────────────────────────────────────────

  recordDrift: async (data: CloudConfigurationDriftCreate): Promise<CloudConfigurationDrift> => {
    const res = await api.post<CloudConfigurationDrift>('/cloud-security/drifts', data);
    return res.data;
  },

  listDrifts: async (params?: {
    asset_id?: number;
    drift_status?: DriftStatus;
  }): Promise<CloudConfigurationDrift[]> => {
    const res = await api.get<CloudConfigurationDrift[]>('/cloud-security/drifts', { params });
    return res.data;
  },

  // ─── 5. IAM Blast Radius ────────────────────────────────────────────────────

  analyzeBlastRadius: async (data: CloudIAMBlastRadiusCreate): Promise<CloudIAMBlastRadius> => {
    const res = await api.post<CloudIAMBlastRadius>('/cloud-security/blast-radius', data);
    return res.data;
  },

  previewBlastRadius: async (
    data: CloudIAMBlastRadiusPreviewRequest
  ): Promise<CloudIAMBlastRadiusPreviewResponse> => {
    const res = await api.post<CloudIAMBlastRadiusPreviewResponse>('/cloud-security/blast-radius/preview', data);
    return res.data;
  },

  // ─── 6. Posture Summary ─────────────────────────────────────────────────────

  getPostureSummary: async (): Promise<CloudPostureSummaryResponse> => {
    const res = await api.get<CloudPostureSummaryResponse>('/cloud-security/posture/summary');
    return res.data;
  },
};
