import { api } from './api';
import type {
  ConcentrationRiskReportResponse,
  Vendor,
  VendorAssessment,
  VendorAssessmentCreate,
  VendorAssessmentItem,
  VendorAssessmentItemEscalateRequest,
  VendorAssessmentItemUpdate,
  VendorAssessmentReview,
  VendorContract,
  VendorContractCreate,
  VendorCreate,
  VendorEngagement,
  VendorEngagementCreate,
  VendorEngagementUpdate,
  VendorEvidenceLink,
  VendorEvidenceLinkCreate,
  VendorOffboardingCreate,
  VendorOffboardingItem,
  VendorOffboardingRecord,
  VendorOverviewResponse,
  VendorRiskBand,
  VendorRiskPostureResponse,
  VendorSlaBreach,
  VendorSlaBreachCreate,
  VendorSlaObligation,
  VendorSlaObligationCreate,
  VendorStatus,
  VendorSubprocessor,
  VendorSubprocessorCreate,
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

  getConcentrationRisk: async (): Promise<ConcentrationRiskReportResponse> => {
    const response = await api.get<ConcentrationRiskReportResponse>('/vendors/concentration-risk');
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

  // ─── 3. Assessments & Closed-Loop Escalation ─────────────────────────────

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

  escalateAssessmentItem: async (
    assessmentId: number,
    itemId: number,
    data: VendorAssessmentItemEscalateRequest
  ): Promise<VendorAssessmentItem> => {
    const response = await api.post<VendorAssessmentItem>(
      `/vendors/assessments/${assessmentId}/items/${itemId}/escalate`,
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

  // ─── 6. Contracts (MSA / DPA / SLA Addendum / DORA ICT) ──────────────────

  listContracts: async (vendorId: number): Promise<VendorContract[]> => {
    const response = await api.get<VendorContract[]>(`/vendors/${vendorId}/contracts`);
    return response.data;
  },

  createContract: async (
    vendorId: number,
    data: VendorContractCreate
  ): Promise<VendorContract> => {
    const response = await api.post<VendorContract>(`/vendors/${vendorId}/contracts`, data);
    return response.data;
  },

  submitContract: async (contractId: number): Promise<VendorContract> => {
    const response = await api.post<VendorContract>(`/vendors/contracts/${contractId}/submit`);
    return response.data;
  },

  approveContract: async (
    contractId: number,
    review_notes?: string
  ): Promise<VendorContract> => {
    const response = await api.post<VendorContract>(
      `/vendors/contracts/${contractId}/approve`,
      { review_notes }
    );
    return response.data;
  },

  rejectContract: async (
    contractId: number,
    rejection_reason: string
  ): Promise<VendorContract> => {
    const response = await api.post<VendorContract>(
      `/vendors/contracts/${contractId}/reject`,
      { rejection_reason }
    );
    return response.data;
  },

  // ─── 7. Fourth-Party Subprocessors ───────────────────────────────────────

  listSubprocessors: async (vendorId: number): Promise<VendorSubprocessor[]> => {
    const response = await api.get<VendorSubprocessor[]>(`/vendors/${vendorId}/subprocessors`);
    return response.data;
  },

  createSubprocessor: async (
    vendorId: number,
    data: VendorSubprocessorCreate
  ): Promise<VendorSubprocessor> => {
    const response = await api.post<VendorSubprocessor>(
      `/vendors/${vendorId}/subprocessors`,
      data
    );
    return response.data;
  },

  approveSubprocessor: async (
    subprocessorId: number,
    review_notes?: string
  ): Promise<VendorSubprocessor> => {
    const response = await api.post<VendorSubprocessor>(
      `/vendors/subprocessors/${subprocessorId}/approve`,
      { review_notes }
    );
    return response.data;
  },

  rejectSubprocessor: async (
    subprocessorId: number,
    rejection_reason: string
  ): Promise<VendorSubprocessor> => {
    const response = await api.post<VendorSubprocessor>(
      `/vendors/subprocessors/${subprocessorId}/reject`,
      { rejection_reason }
    );
    return response.data;
  },

  suspendSubprocessor: async (
    subprocessorId: number,
    reason?: string
  ): Promise<VendorSubprocessor> => {
    const response = await api.post<VendorSubprocessor>(
      `/vendors/subprocessors/${subprocessorId}/suspend`,
      { review_notes: reason }
    );
    return response.data;
  },

  terminateSubprocessor: async (
    subprocessorId: number,
    reason?: string
  ): Promise<VendorSubprocessor> => {
    const response = await api.post<VendorSubprocessor>(
      `/vendors/subprocessors/${subprocessorId}/terminate`,
      { review_notes: reason }
    );
    return response.data;
  },

  // ─── 8. SLA Obligations & Breaches ───────────────────────────────────────

  listSlaObligations: async (vendorId: number): Promise<VendorSlaObligation[]> => {
    const response = await api.get<VendorSlaObligation[]>(
      `/vendors/${vendorId}/sla-obligations`
    );
    return response.data;
  },

  createSlaObligation: async (
    vendorId: number,
    data: VendorSlaObligationCreate
  ): Promise<VendorSlaObligation> => {
    const response = await api.post<VendorSlaObligation>(
      `/vendors/${vendorId}/sla-obligations`,
      data
    );
    return response.data;
  },

  listSlaBreaches: async (vendorId: number): Promise<VendorSlaBreach[]> => {
    const response = await api.get<VendorSlaBreach[]>(`/vendors/${vendorId}/sla-breaches`);
    return response.data;
  },

  recordSlaBreach: async (
    obligationId: number,
    data: VendorSlaBreachCreate
  ): Promise<VendorSlaBreach> => {
    const response = await api.post<VendorSlaBreach>(
      `/vendors/sla-obligations/${obligationId}/breaches`,
      data
    );
    return response.data;
  },

  escalateSlaBreach: async (
    breachId: number,
    data: {
      create_remediation_plan?: boolean;
      remediation_plan_title?: string;
      owner_id?: number;
      due_date?: string;
      escalation_notes?: string;
    }
  ): Promise<VendorSlaBreach> => {
    const response = await api.post<VendorSlaBreach>(
      `/vendors/sla-breaches/${breachId}/escalate`,
      data
    );
    return response.data;
  },

  waiveSlaBreach: async (
    breachId: number,
    data: { exception_id: number; justification: string }
  ): Promise<VendorSlaBreach> => {
    const response = await api.post<VendorSlaBreach>(
      `/vendors/sla-breaches/${breachId}/waive`,
      data
    );
    return response.data;
  },

  resolveSlaBreach: async (
    breachId: number,
    data: { resolution_evidence_id: number; resolution_notes?: string }
  ): Promise<VendorSlaBreach> => {
    const response = await api.post<VendorSlaBreach>(
      `/vendors/sla-breaches/${breachId}/resolve`,
      data
    );
    return response.data;
  },

  verifyCloseSlaBreach: async (
    breachId: number,
    data: { closure_notes?: string }
  ): Promise<VendorSlaBreach> => {
    const response = await api.post<VendorSlaBreach>(
      `/vendors/sla-breaches/${breachId}/verify-close`,
      data
    );
    return response.data;
  },

  // ─── 9. Governed Vendor Offboarding ──────────────────────────────────────

  listOffboardingRecords: async (vendorId: number): Promise<VendorOffboardingRecord[]> => {
    const response = await api.get<VendorOffboardingRecord[]>(
      `/vendors/${vendorId}/offboarding`
    );
    return response.data;
  },

  initiateOffboarding: async (
    vendorId: number,
    data: VendorOffboardingCreate
  ): Promise<VendorOffboardingRecord> => {
    const response = await api.post<VendorOffboardingRecord>(
      `/vendors/${vendorId}/offboarding`,
      data
    );
    return response.data;
  },

  attestOffboardingItem: async (
    offboardingId: number,
    itemId: number,
    data: { evidence_id: number; attestation_notes?: string }
  ): Promise<VendorOffboardingItem> => {
    const response = await api.post<VendorOffboardingItem>(
      `/vendors/offboarding/${offboardingId}/items/${itemId}/attest`,
      data
    );
    return response.data;
  },

  waiveOffboardingItem: async (
    offboardingId: number,
    itemId: number,
    data: { waiver_exception_id: number; waiver_justification: string }
  ): Promise<VendorOffboardingItem> => {
    const response = await api.post<VendorOffboardingItem>(
      `/vendors/offboarding/${offboardingId}/items/${itemId}/waive`,
      data
    );
    return response.data;
  },

  submitOffboarding: async (offboardingId: number): Promise<VendorOffboardingRecord> => {
    const response = await api.post<VendorOffboardingRecord>(
      `/vendors/offboarding/${offboardingId}/submit`
    );
    return response.data;
  },

  approveOffboarding: async (
    offboardingId: number,
    closure_certificate_summary: string
  ): Promise<VendorOffboardingRecord> => {
    const response = await api.post<VendorOffboardingRecord>(
      `/vendors/offboarding/${offboardingId}/approve`,
      { closure_certificate_summary }
    );
    return response.data;
  },

  rejectOffboarding: async (
    offboardingId: number,
    rejection_reason: string
  ): Promise<VendorOffboardingRecord> => {
    const response = await api.post<VendorOffboardingRecord>(
      `/vendors/offboarding/${offboardingId}/reject`,
      { rejection_reason }
    );
    return response.data;
  },

  cancelOffboarding: async (
    offboardingId: number,
    reason?: string
  ): Promise<VendorOffboardingRecord> => {
    const response = await api.post<VendorOffboardingRecord>(
      `/vendors/offboarding/${offboardingId}/cancel`,
      { rejection_reason: reason }
    );
    return response.data;
  },
};
