import { api } from './api';
import type {
  KeyRiskIndicator,
  KeyRiskIndicatorCreate,
  KriBreachAcknowledgePayload,
  KriBreachClosePayload,
  KriBreachEscalateFindingPayload,
  KriBreachRecord,
  KriObservation,
  KriObservationCreate,
  KriRiskLink,
  KriRiskLinkCreate,
  KriTelemetryOverview,
  KriThreshold,
  KriThresholdCreate,
  RiskAppetiteApprovePayload,
  RiskAppetiteStatement,
  RiskAppetiteStatementCreate,
} from '../types/kri';

export const kriService = {
  // Telemetry Dashboard
  getTelemetryOverview: async (): Promise<KriTelemetryOverview> => {
    const res = await api.get('/kri/telemetry-overview');
    return res.data;
  },

  // Risk Appetite Statements
  createAppetiteStatement: async (
    data: RiskAppetiteStatementCreate
  ): Promise<RiskAppetiteStatement> => {
    const res = await api.post('/kri/appetite-statements', data);
    return res.data;
  },

  listAppetiteStatements: async (): Promise<RiskAppetiteStatement[]> => {
    const res = await api.get('/kri/appetite-statements');
    return res.data;
  },

  getLatestApprovedAppetite: async (): Promise<RiskAppetiteStatement> => {
    const res = await api.get('/kri/appetite-statements/latest');
    return res.data;
  },

  getAppetiteStatement: async (id: number): Promise<RiskAppetiteStatement> => {
    const res = await api.get(`/kri/appetite-statements/${id}`);
    return res.data;
  },

  approveAppetiteStatement: async (
    id: number,
    data: RiskAppetiteApprovePayload
  ): Promise<RiskAppetiteStatement> => {
    const res = await api.post(`/kri/appetite-statements/${id}/approve`, data);
    return res.data;
  },

  // Key Risk Indicators
  createKri: async (data: KeyRiskIndicatorCreate): Promise<KeyRiskIndicator> => {
    const res = await api.post('/kri/indicators', data);
    return res.data;
  },

  listKris: async (params?: {
    risk_category?: string;
    status?: string;
    search?: string;
  }): Promise<KeyRiskIndicator[]> => {
    const res = await api.get('/kri/indicators', { params });
    return res.data;
  },

  getKri: async (id: number): Promise<KeyRiskIndicator> => {
    const res = await api.get(`/kri/indicators/${id}`);
    return res.data;
  },

  updateKri: async (
    id: number,
    data: Partial<KeyRiskIndicatorCreate>
  ): Promise<KeyRiskIndicator> => {
    const res = await api.put(`/kri/indicators/${id}`, data);
    return res.data;
  },

  // Thresholds
  createThreshold: async (
    kriId: number,
    data: KriThresholdCreate
  ): Promise<KriThreshold> => {
    const res = await api.post(`/kri/indicators/${kriId}/thresholds`, data);
    return res.data;
  },

  listThresholds: async (kriId: number): Promise<KriThreshold[]> => {
    const res = await api.get(`/kri/indicators/${kriId}/thresholds`);
    return res.data;
  },

  // Observations
  ingestObservation: async (
    kriId: number,
    data: KriObservationCreate
  ): Promise<KriObservation> => {
    const res = await api.post(`/kri/indicators/${kriId}/observations`, data);
    return res.data;
  },

  listObservations: async (
    kriId: number,
    limit = 50
  ): Promise<KriObservation[]> => {
    const res = await api.get(`/kri/indicators/${kriId}/observations`, {
      params: { limit },
    });
    return res.data;
  },

  // Risk Linkage
  linkRisk: async (
    kriId: number,
    data: KriRiskLinkCreate
  ): Promise<KriRiskLink> => {
    const res = await api.post(`/kri/indicators/${kriId}/link-risk`, data);
    return res.data;
  },

  listLinkedRisks: async (kriId: number): Promise<KriRiskLink[]> => {
    const res = await api.get(`/kri/indicators/${kriId}/risks`);
    return res.data;
  },

  // Breaches
  listBreaches: async (params?: {
    kri_id?: number;
    status?: string;
  }): Promise<KriBreachRecord[]> => {
    const res = await api.get('/kri/breaches', { params });
    return res.data;
  },

  getBreach: async (id: number): Promise<KriBreachRecord> => {
    const res = await api.get(`/kri/breaches/${id}`);
    return res.data;
  },

  acknowledgeBreach: async (
    id: number,
    data: KriBreachAcknowledgePayload
  ): Promise<KriBreachRecord> => {
    const res = await api.post(`/kri/breaches/${id}/acknowledge`, data);
    return res.data;
  },

  escalateBreachToFinding: async (
    id: number,
    data: KriBreachEscalateFindingPayload
  ): Promise<KriBreachRecord> => {
    const res = await api.post(`/kri/breaches/${id}/escalate-finding`, data);
    return res.data;
  },

  closeBreach: async (
    id: number,
    data: KriBreachClosePayload
  ): Promise<KriBreachRecord> => {
    const res = await api.post(`/kri/breaches/${id}/close`, data);
    return res.data;
  },
};
