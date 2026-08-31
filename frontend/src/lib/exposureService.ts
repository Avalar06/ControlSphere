import { api } from './api';
import type {
  ExposureAssetLink,
  ExposureAssetLinkCreate,
  ExposureException,
  ExposureExceptionCreate,
  ExposureExceptionReviewRequest,
  ExposureIndexCalculateRequest,
  ExposureIndexCalculateResponse,
  ExposureSeverity,
  ExposureStatus,
  ExposureSummaryResponse,
  RemediationPlan,
  VulnerabilityExposure,
  VulnerabilityExposureCreate,
  VulnerabilityExposureStatusUpdate,
  VulnerabilityExposureUpdate,
} from '../types';

export const exposureService = {
  // ─── 1. Exposure Catalog ──────────────────────────────────────────────────

  createExposure: async (data: VulnerabilityExposureCreate): Promise<VulnerabilityExposure> => {
    const res = await api.post<VulnerabilityExposure>('/exposures', data);
    return res.data;
  },

  listExposures: async (params?: {
    severity?: ExposureSeverity;
    status?: ExposureStatus;
    cisa_kev?: boolean;
    search?: string;
    skip?: number;
    limit?: number;
  }): Promise<VulnerabilityExposure[]> => {
    const res = await api.get<VulnerabilityExposure[]>('/exposures', { params });
    return res.data;
  },

  getExposure: async (id: number): Promise<VulnerabilityExposure> => {
    const res = await api.get<VulnerabilityExposure>(`/exposures/${id}`);
    return res.data;
  },

  updateExposure: async (
    id: number,
    data: VulnerabilityExposureUpdate
  ): Promise<VulnerabilityExposure> => {
    const res = await api.put<VulnerabilityExposure>(`/exposures/${id}`, data);
    return res.data;
  },

  deleteExposure: async (id: number): Promise<void> => {
    await api.delete(`/exposures/${id}`);
  },

  updateStatus: async (
    id: number,
    data: VulnerabilityExposureStatusUpdate
  ): Promise<VulnerabilityExposure> => {
    const res = await api.put<VulnerabilityExposure>(`/exposures/${id}/status`, data);
    return res.data;
  },

  // ─── 2. Asset & Blast Radius Linkage ──────────────────────────────────────

  linkAsset: async (
    exposureId: number,
    data: ExposureAssetLinkCreate
  ): Promise<ExposureAssetLink> => {
    const res = await api.post<ExposureAssetLink>(`/exposures/${exposureId}/assets`, data);
    return res.data;
  },

  listAssetLinks: async (exposureId: number): Promise<ExposureAssetLink[]> => {
    const res = await api.get<ExposureAssetLink[]>(`/exposures/${exposureId}/assets`);
    return res.data;
  },

  unlinkAsset: async (linkId: number): Promise<void> => {
    await api.delete(`/exposures/assets/${linkId}`);
  },

  // ─── 3. Four-Eyes Exception Governance ────────────────────────────────────

  requestException: async (
    exposureId: number,
    data: ExposureExceptionCreate
  ): Promise<ExposureException> => {
    const res = await api.post<ExposureException>(`/exposures/${exposureId}/exceptions`, data);
    return res.data;
  },

  reviewException: async (
    exceptionId: number,
    data: ExposureExceptionReviewRequest
  ): Promise<ExposureException> => {
    const res = await api.post<ExposureException>(`/exposures/exceptions/${exceptionId}/review`, data);
    return res.data;
  },

  listExceptions: async (params?: {
    exposure_id?: number;
    status?: string;
  }): Promise<ExposureException[]> => {
    const res = await api.get<ExposureException[]>('/exposures/exceptions', { params });
    return res.data;
  },

  // ─── 4. Cross-Module Remediation Spawning (Phase 11) ──────────────────────

  spawnRemediation: async (
    exposureId: number,
    params?: { title?: string; finding_id?: number }
  ): Promise<RemediationPlan> => {
    const res = await api.post<RemediationPlan>(`/exposures/${exposureId}/remediate`, null, { params });
    return res.data;
  },

  // ─── 5. Executive Posture & Calculation Preview ───────────────────────────

  getPostureSummary: async (): Promise<ExposureSummaryResponse> => {
    const res = await api.get<ExposureSummaryResponse>('/exposures/summary/posture');
    return res.data;
  },

  calculateIndexPreview: async (
    data: ExposureIndexCalculateRequest
  ): Promise<ExposureIndexCalculateResponse> => {
    const res = await api.post<ExposureIndexCalculateResponse>('/exposures/calculate-index', data);
    return res.data;
  },
};
