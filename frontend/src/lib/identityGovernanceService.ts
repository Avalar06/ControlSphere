import { api } from './api';
import type {
  AccessCertificationCampaign,
  AccessCertificationCampaignCreate,
  AccessCertificationItem,
  AccessCertificationItemReview,
  CampaignStatus,
  CertificationDecision,
  EmploymentStatus,
  EntitlementAssignment,
  EntitlementAssignmentCreate,
  GovernedIdentity,
  GovernedIdentityCreate,
  GovernedIdentityUpdate,
  IdentityEntitlement,
  IdentityEntitlementCreate,
  IdentityPostureSummaryResponse,
  IdentityRiskBand,
  IdentityType,
  JITAccessRequest,
  JITAccessRequestCreate,
  JITAccessReviewRequest,
  JITApprovalStatus,
  SoDConflictPolicy,
  SoDConflictPolicyCreate,
  SoDConflictViolation,
  SoDViolationStatus,
  SystemType,
  ZeroTrustAssessment,
  ZeroTrustAssessmentCreate,
  ZeroTrustPreviewRequest,
  ZeroTrustPreviewResponse,
} from '../types';

export const identityGovernanceService = {
  // ─── 1. Governed Identities ─────────────────────────────────────────────────

  createIdentity: async (data: GovernedIdentityCreate): Promise<GovernedIdentity> => {
    const res = await api.post<GovernedIdentity>('/identity-governance/identities', data);
    return res.data;
  },

  listIdentities: async (params?: {
    identity_type?: IdentityType;
    employment_status?: EmploymentStatus;
    risk_band?: IdentityRiskBand;
  }): Promise<GovernedIdentity[]> => {
    const res = await api.get<GovernedIdentity[]>('/identity-governance/identities', { params });
    return res.data;
  },

  getIdentity: async (id: number): Promise<GovernedIdentity> => {
    const res = await api.get<GovernedIdentity>(`/identity-governance/identities/${id}`);
    return res.data;
  },

  updateIdentity: async (id: number, data: GovernedIdentityUpdate): Promise<GovernedIdentity> => {
    const res = await api.patch<GovernedIdentity>(`/identity-governance/identities/${id}`, data);
    return res.data;
  },

  deleteIdentity: async (id: number): Promise<void> => {
    await api.delete(`/identity-governance/identities/${id}`);
  },

  // ─── 2. Entitlements & Assignments ──────────────────────────────────────────

  createEntitlement: async (data: IdentityEntitlementCreate): Promise<IdentityEntitlement> => {
    const res = await api.post<IdentityEntitlement>('/identity-governance/entitlements', data);
    return res.data;
  },

  listEntitlements: async (params?: {
    system_type?: SystemType;
    is_privileged?: boolean;
  }): Promise<IdentityEntitlement[]> => {
    const res = await api.get<IdentityEntitlement[]>('/identity-governance/entitlements', { params });
    return res.data;
  },

  assignEntitlement: async (
    identityId: number,
    data: EntitlementAssignmentCreate
  ): Promise<EntitlementAssignment> => {
    const res = await api.post<EntitlementAssignment>(
      `/identity-governance/identities/${identityId}/assignments`,
      data
    );
    return res.data;
  },

  listIdentityAssignments: async (identityId: number): Promise<EntitlementAssignment[]> => {
    const res = await api.get<EntitlementAssignment[]>(
      `/identity-governance/identities/${identityId}/assignments`
    );
    return res.data;
  },

  // ─── 3. Access Certification Campaigns (Four-Eyes SoD) ──────────────────────

  createCampaign: async (data: AccessCertificationCampaignCreate): Promise<AccessCertificationCampaign> => {
    const res = await api.post<AccessCertificationCampaign>('/identity-governance/campaigns', data);
    return res.data;
  },

  listCampaigns: async (params?: { status?: CampaignStatus }): Promise<AccessCertificationCampaign[]> => {
    const res = await api.get<AccessCertificationCampaign[]>('/identity-governance/campaigns', { params });
    return res.data;
  },

  getCampaign: async (id: number): Promise<AccessCertificationCampaign> => {
    const res = await api.get<AccessCertificationCampaign>(`/identity-governance/campaigns/${id}`);
    return res.data;
  },

  listCampaignItems: async (
    campaignId: number,
    params?: { decision?: CertificationDecision }
  ): Promise<AccessCertificationItem[]> => {
    const res = await api.get<AccessCertificationItem[]>(
      `/identity-governance/campaigns/${campaignId}/items`,
      { params }
    );
    return res.data;
  },

  reviewCertificationItem: async (
    itemId: number,
    data: AccessCertificationItemReview
  ): Promise<AccessCertificationItem> => {
    const res = await api.post<AccessCertificationItem>(
      `/identity-governance/certifications/${itemId}/review`,
      data
    );
    return res.data;
  },

  finalizeCampaign: async (campaignId: number): Promise<AccessCertificationCampaign> => {
    const res = await api.post<AccessCertificationCampaign>(
      `/identity-governance/campaigns/${campaignId}/finalize`
    );
    return res.data;
  },

  // ─── 4. JIT Access Requests (Four-Eyes SoD) ──────────────────────────────────

  createJITRequest: async (data: JITAccessRequestCreate): Promise<JITAccessRequest> => {
    const res = await api.post<JITAccessRequest>('/identity-governance/jit-requests', data);
    return res.data;
  },

  listJITRequests: async (params?: { status?: JITApprovalStatus }): Promise<JITAccessRequest[]> => {
    const res = await api.get<JITAccessRequest[]>('/identity-governance/jit-requests', { params });
    return res.data;
  },

  reviewJITRequest: async (
    requestId: number,
    data: JITAccessReviewRequest
  ): Promise<JITAccessRequest> => {
    const res = await api.post<JITAccessRequest>(
      `/identity-governance/jit-requests/${requestId}/review`,
      data
    );
    return res.data;
  },

  // ─── 5. Zero Trust Assurance ────────────────────────────────────────────────

  assessZeroTrust: async (
    identityId: number,
    data: ZeroTrustAssessmentCreate
  ): Promise<ZeroTrustAssessment> => {
    const res = await api.post<ZeroTrustAssessment>(
      `/identity-governance/identities/${identityId}/zero-trust`,
      data
    );
    return res.data;
  },

  previewZeroTrust: async (data: ZeroTrustPreviewRequest): Promise<ZeroTrustPreviewResponse> => {
    const res = await api.post<ZeroTrustPreviewResponse>('/identity-governance/zero-trust/preview', data);
    return res.data;
  },

  // ─── 6. SoD Policies & Violations ───────────────────────────────────────────

  createSoDPolicy: async (data: SoDConflictPolicyCreate): Promise<SoDConflictPolicy> => {
    const res = await api.post<SoDConflictPolicy>('/identity-governance/sod-policies', data);
    return res.data;
  },

  listSoDPolicies: async (): Promise<SoDConflictPolicy[]> => {
    const res = await api.get<SoDConflictPolicy[]>('/identity-governance/sod-policies');
    return res.data;
  },

  listSoDViolations: async (params?: {
    identity_id?: number;
    status?: SoDViolationStatus;
  }): Promise<SoDConflictViolation[]> => {
    const res = await api.get<SoDConflictViolation[]>('/identity-governance/sod-violations', { params });
    return res.data;
  },

  // ─── 7. Posture Summary ─────────────────────────────────────────────────────

  getPostureSummary: async (): Promise<IdentityPostureSummaryResponse> => {
    const res = await api.get<IdentityPostureSummaryResponse>('/identity-governance/posture/summary');
    return res.data;
  },
};
