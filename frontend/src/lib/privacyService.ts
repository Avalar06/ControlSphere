import { api } from './api';
import type {
  DataAsset,
  DataAssetCreate,
  DataAssetUpdate,
  DataSensitivityLevel,
  DataTransferAssessment,
  DataTransferCalculatePreviewRequest,
  DataTransferCalculatePreviewResponse,
  DataTransferCreate,
  DataTransferReviewRequest,
  DPIAAssessment,
  DPIACalculatePreviewRequest,
  DPIACalculatePreviewResponse,
  DPIACreate,
  DPIAReviewRequest,
  DPIARiskBand,
  DPIAUpdate,
  JurisdictionRiskTier,
  PrivacyApprovalStatus,
  PrivacyPostureSummaryResponse,
  ProcessingActivity,
  ProcessingActivityCreate,
  ProcessingActivityStatusUpdate,
  ProcessingActivityUpdate,
  ProcessingLegalBasis,
  ProcessingLifecycleState,
} from '../types';

export const privacyService = {
  // ─── 1. Data Assets Catalog ─────────────────────────────────────────────────

  createDataAsset: async (data: DataAssetCreate): Promise<DataAsset> => {
    const res = await api.post<DataAsset>('/privacy/data-assets', data);
    return res.data;
  },

  listDataAssets: async (params?: {
    sensitivity?: DataSensitivityLevel;
    skip?: number;
    limit?: number;
  }): Promise<DataAsset[]> => {
    const res = await api.get<DataAsset[]>('/privacy/data-assets', { params });
    return res.data;
  },

  getDataAsset: async (id: number): Promise<DataAsset> => {
    const res = await api.get<DataAsset>(`/privacy/data-assets/${id}`);
    return res.data;
  },

  updateDataAsset: async (id: number, data: DataAssetUpdate): Promise<DataAsset> => {
    const res = await api.put<DataAsset>(`/privacy/data-assets/${id}`, data);
    return res.data;
  },

  deleteDataAsset: async (id: number): Promise<void> => {
    await api.delete(`/privacy/data-assets/${id}`);
  },

  // ─── 2. Processing Activities (RoPA) ────────────────────────────────────────

  createProcessingActivity: async (data: ProcessingActivityCreate): Promise<ProcessingActivity> => {
    const res = await api.post<ProcessingActivity>('/privacy/activities', data);
    return res.data;
  },

  listProcessingActivities: async (params?: {
    lifecycle_state?: ProcessingLifecycleState;
    legal_basis?: ProcessingLegalBasis;
    skip?: number;
    limit?: number;
  }): Promise<ProcessingActivity[]> => {
    const res = await api.get<ProcessingActivity[]>('/privacy/activities', { params });
    return res.data;
  },

  getProcessingActivity: async (id: number): Promise<ProcessingActivity> => {
    const res = await api.get<ProcessingActivity>(`/privacy/activities/${id}`);
    return res.data;
  },

  updateProcessingActivity: async (
    id: number,
    data: ProcessingActivityUpdate
  ): Promise<ProcessingActivity> => {
    const res = await api.put<ProcessingActivity>(`/privacy/activities/${id}`, data);
    return res.data;
  },

  updateProcessingActivityStatus: async (
    id: number,
    data: ProcessingActivityStatusUpdate
  ): Promise<ProcessingActivity> => {
    const res = await api.patch<ProcessingActivity>(`/privacy/activities/${id}/status`, data);
    return res.data;
  },

  deleteProcessingActivity: async (id: number): Promise<void> => {
    await api.delete(`/privacy/activities/${id}`);
  },

  // ─── 3. DPIA Assessments ───────────────────────────────────────────────────

  createDPIA: async (data: DPIACreate): Promise<DPIAAssessment> => {
    const res = await api.post<DPIAAssessment>('/privacy/dpia', data);
    return res.data;
  },

  listDPIAs: async (params?: {
    activity_id?: number;
    risk_band?: DPIARiskBand;
    status_filter?: PrivacyApprovalStatus;
    skip?: number;
    limit?: number;
  }): Promise<DPIAAssessment[]> => {
    const res = await api.get<DPIAAssessment[]>('/privacy/dpia', { params });
    return res.data;
  },

  getDPIA: async (id: number): Promise<DPIAAssessment> => {
    const res = await api.get<DPIAAssessment>(`/privacy/dpia/${id}`);
    return res.data;
  },

  updateDPIA: async (id: number, data: DPIAUpdate): Promise<DPIAAssessment> => {
    const res = await api.put<DPIAAssessment>(`/privacy/dpia/${id}`, data);
    return res.data;
  },

  reviewDPIA: async (id: number, data: DPIAReviewRequest): Promise<DPIAAssessment> => {
    const res = await api.post<DPIAAssessment>(`/privacy/dpia/${id}/review`, data);
    return res.data;
  },

  calculateDPIAPreview: async (
    data: DPIACalculatePreviewRequest
  ): Promise<DPIACalculatePreviewResponse> => {
    const res = await api.post<DPIACalculatePreviewResponse>('/privacy/dpia/calculate-preview', data);
    return res.data;
  },

  // ─── 4. Data Transfer Assessments (TIA) ─────────────────────────────────────

  createDataTransfer: async (data: DataTransferCreate): Promise<DataTransferAssessment> => {
    const res = await api.post<DataTransferAssessment>('/privacy/transfers', data);
    return res.data;
  },

  listDataTransfers: async (params?: {
    activity_id?: number;
    tier?: JurisdictionRiskTier;
    skip?: number;
    limit?: number;
  }): Promise<DataTransferAssessment[]> => {
    const res = await api.get<DataTransferAssessment[]>('/privacy/transfers', { params });
    return res.data;
  },

  getDataTransfer: async (id: number): Promise<DataTransferAssessment> => {
    const res = await api.get<DataTransferAssessment>(`/privacy/transfers/${id}`);
    return res.data;
  },

  reviewDataTransfer: async (
    id: number,
    data: DataTransferReviewRequest
  ): Promise<DataTransferAssessment> => {
    const res = await api.post<DataTransferAssessment>(`/privacy/transfers/${id}/review`, data);
    return res.data;
  },

  calculateTransferPreview: async (
    data: DataTransferCalculatePreviewRequest
  ): Promise<DataTransferCalculatePreviewResponse> => {
    const res = await api.post<DataTransferCalculatePreviewResponse>(
      '/privacy/transfers/calculate-preview',
      data
    );
    return res.data;
  },

  // ─── 5. Executive Posture & Telemetry ───────────────────────────────────────

  getPostureSummary: async (): Promise<PrivacyPostureSummaryResponse> => {
    const res = await api.get<PrivacyPostureSummaryResponse>('/privacy/summary/posture');
    return res.data;
  },
};
