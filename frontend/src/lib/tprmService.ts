import { api } from './api';
import type {
  Vendor,
  VendorAssessment,
  VendorAssessmentCreate,
  VendorAssessmentItemUpdate,
  VendorAssessmentReview,
  VendorCreate,
  VendorEngagement,
  VendorEngagementCreate,
  VendorEngagementUpdate,
  VendorEvidenceLink,
  VendorEvidenceLinkCreate,
  VendorOverviewResponse,
  VendorRiskBand,
  VendorRiskPostureResponse,
  VendorStatus,
  VendorTier,
  VendorTierOverride,
  VendorUpdate,
} from '../types';

export const tprmService = {
  // ─── 1. Overview & Vendor Management ─────────────────────────────────────

  getOverview: async (): Promise<VendorOverviewResponse> => {
    const response = await api.get<VendorOverviewResponse>('/vendors/overview');
    return response.data;
  },

  listVendors: async (params?: {
    vendor_status?: VendorStatus;
    tier?: VendorTier;
    risk_band?: VendorRiskBand;
    search?: string;
    limit?: number;
    offset?: number;
  }): Promise<Vendor[]> => {
    const response = await api.get<Vendor[]>('/vendors', { params });
    return response.data;
  },

  getVendor: async (id: number): Promise<Vendor> => {
    const response = await api.get<Vendor>(`/vendors/${id}`);
    return response.data;
  },

  createVendor: async (data: VendorCreate): Promise<Vendor> => {
    const response = await api.post<Vendor>('/vendors', data);
    return response.data;
  },

  updateVendor: async (id: number, data: VendorUpdate): Promise<Vendor> => {
    const response = await api.patch<Vendor>(`/vendors/${id}`, data);
    return response.data;
  },

  overrideTier: async (id: number, data: VendorTierOverride): Promise<Vendor> => {
    const response = await api.post<Vendor>(`/vendors/${id}/override-tier`, data);
    return response.data;
  },

  // ─── 2. Engagements ──────────────────────────────────────────────────────

  createEngagement: async (
    vendorId: number,
    data: VendorEngagementCreate
  ): Promise<VendorEngagement> => {
    const response = await api.post<VendorEngagement>(`/vendors/${vendorId}/engagements`, data);
    return response.data;
  },

  updateEngagement: async (
    engagementId: number,
    data: VendorEngagementUpdate
  ): Promise<VendorEngagement> => {
    const response = await api.patch<VendorEngagement>(
      `/vendors/engagements/${engagementId}`,
      data
    );
    return response.data;
  },

  // ─── 3. Assessments ──────────────────────────────────────────────────────

  listVendorAssessments: async (vendorId: number): Promise<VendorAssessment[]> => {
    const response = await api.get<VendorAssessment[]>(`/vendors/${vendorId}/assessments`);
    return response.data;
  },

  createVendorAssessment: async (
    vendorId: number,
    data: VendorAssessmentCreate
  ): Promise<VendorAssessment> => {
    const response = await api.post<VendorAssessment>(`/vendors/${vendorId}/assessments`, data);
    return response.data;
  },

  getVendorAssessment: async (assessmentId: number): Promise<VendorAssessment> => {
    const response = await api.get<VendorAssessment>(`/vendors/assessments/${assessmentId}`);
    return response.data;
  },

  updateAssessmentItems: async (
    assessmentId: number,
    payload: Record<number, VendorAssessmentItemUpdate>
  ): Promise<VendorAssessment> => {
    const response = await api.patch<VendorAssessment>(
      `/vendors/assessments/${assessmentId}/items`,
      payload
    );
    return response.data;
  },

  submitAssessment: async (assessmentId: number): Promise<VendorAssessment> => {
    const response = await api.post<VendorAssessment>(
      `/vendors/assessments/${assessmentId}/submit`
    );
    return response.data;
  },

  startAssessmentReview: async (assessmentId: number): Promise<VendorAssessment> => {
    const response = await api.post<VendorAssessment>(
      `/vendors/assessments/${assessmentId}/start-review`
    );
    return response.data;
  },

  approveAssessment: async (
    assessmentId: number,
    data: VendorAssessmentReview
  ): Promise<VendorAssessment> => {
    const response = await api.post<VendorAssessment>(
      `/vendors/assessments/${assessmentId}/approve`,
      data
    );
    return response.data;
  },

  rejectAssessment: async (
    assessmentId: number,
    data: VendorAssessmentReview
  ): Promise<VendorAssessment> => {
    const response = await api.post<VendorAssessment>(
      `/vendors/assessments/${assessmentId}/reject`,
      data
    );
    return response.data;
  },

  // ─── 4. Evidence Linkage ─────────────────────────────────────────────────

  linkVendorEvidence: async (
    vendorId: number,
    data: VendorEvidenceLinkCreate
  ): Promise<VendorEvidenceLink> => {
    const response = await api.post<VendorEvidenceLink>(`/vendors/${vendorId}/evidence`, data);
    return response.data;
  },

  unlinkVendorEvidence: async (vendorId: number, linkId: number): Promise<void> => {
    await api.delete(`/vendors/${vendorId}/evidence/${linkId}`);
  },

  // ─── 5. Risk Posture Telemetry ───────────────────────────────────────────

  getVendorRiskPosture: async (vendorId: number): Promise<VendorRiskPostureResponse> => {
    const response = await api.get<VendorRiskPostureResponse>(
      `/vendors/${vendorId}/risk-posture`
    );
    return response.data;
  },
};
