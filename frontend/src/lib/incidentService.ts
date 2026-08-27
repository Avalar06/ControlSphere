import { api } from './api';
import type {
  IncidentCategory,
  IncidentCloseRequest,
  IncidentControlLink,
  IncidentControlLinkCreate,
  IncidentCreate,
  IncidentDetailRead,
  IncidentMaterialityUpdate,
  IncidentOverviewResponse,
  IncidentRegulatoryDisclosure,
  IncidentRegulatoryDisclosureCreate,
  IncidentRegulatoryExemptionRequest,
  IncidentRegulatoryNotificationRequest,
  IncidentSeverity,
  IncidentStatus,
  IncidentStatusTransition,
  IncidentTimelineEvent,
  IncidentTimelineEventCreate,
  IncidentUpdate,
  IncidentVendorLink,
  IncidentVendorLinkCreate,
  SecurityIncident,
} from '../types';

export const incidentService = {
  // ─── 1. Incident Overview & Telemetry ─────────────────────────────────────

  getOverview: async (): Promise<IncidentOverviewResponse> => {
    const response = await api.get<IncidentOverviewResponse>('/incidents/overview');
    return response.data;
  },

  // ─── 2. Incident List & Search ────────────────────────────────────────────

  listIncidents: async (params?: {
    status?: IncidentStatus;
    severity?: IncidentSeverity;
    category?: IncidentCategory;
    is_material?: boolean;
    search?: string;
    limit?: number;
    offset?: number;
  }): Promise<SecurityIncident[]> => {
    const response = await api.get<SecurityIncident[]>('/incidents', { params });
    return response.data;
  },

  // ─── 3. Incident Detail ───────────────────────────────────────────────────

  getIncidentDetail: async (id: number): Promise<IncidentDetailRead> => {
    const response = await api.get<IncidentDetailRead>(`/incidents/${id}`);
    return response.data;
  },

  // ─── 4. Incident Creation ─────────────────────────────────────────────────

  createIncident: async (data: IncidentCreate): Promise<SecurityIncident> => {
    const response = await api.post<SecurityIncident>('/incidents', data);
    return response.data;
  },

  // ─── 5. Incident Metadata Update ──────────────────────────────────────────

  updateIncident: async (id: number, data: IncidentUpdate): Promise<SecurityIncident> => {
    const response = await api.patch<SecurityIncident>(`/incidents/${id}`, data);
    return response.data;
  },

  // ─── 6. Lifecycle Transition ──────────────────────────────────────────────

  transitionLifecycle: async (
    id: number,
    data: IncidentStatusTransition
  ): Promise<SecurityIncident> => {
    const response = await api.post<SecurityIncident>(`/incidents/${id}/transition`, data);
    return response.data;
  },

  // ─── 7. Four-Eyes Incident Closure ────────────────────────────────────────

  closeIncident: async (id: number, data: IncidentCloseRequest): Promise<SecurityIncident> => {
    const response = await api.post<SecurityIncident>(`/incidents/${id}/close`, data);
    return response.data;
  },

  // ─── 8. SEC Materiality Determination ─────────────────────────────────────

  setMateriality: async (
    id: number,
    data: IncidentMaterialityUpdate
  ): Promise<SecurityIncident> => {
    const response = await api.post<SecurityIncident>(`/incidents/${id}/materiality`, data);
    return response.data;
  },

  // ─── 9. Timeline Management (Append-Only) ─────────────────────────────────

  getTimeline: async (id: number): Promise<IncidentTimelineEvent[]> => {
    const response = await api.get<IncidentTimelineEvent[]>(`/incidents/${id}/timeline`);
    return response.data;
  },

  appendTimelineEvent: async (
    id: number,
    data: IncidentTimelineEventCreate
  ): Promise<IncidentTimelineEvent> => {
    const response = await api.post<IncidentTimelineEvent>(`/incidents/${id}/timeline`, data);
    return response.data;
  },

  // ─── 10. Control Linkages ─────────────────────────────────────────────────

  linkControl: async (
    id: number,
    data: IncidentControlLinkCreate
  ): Promise<IncidentControlLink> => {
    const response = await api.post<IncidentControlLink>(`/incidents/${id}/controls`, data);
    return response.data;
  },

  unlinkControl: async (id: number, linkId: number): Promise<void> => {
    await api.delete(`/incidents/${id}/controls/${linkId}`);
  },

  // ─── 11. Vendor Linkages ──────────────────────────────────────────────────

  linkVendor: async (
    id: number,
    data: IncidentVendorLinkCreate
  ): Promise<IncidentVendorLink> => {
    const response = await api.post<IncidentVendorLink>(`/incidents/${id}/vendors`, data);
    return response.data;
  },

  unlinkVendor: async (id: number, linkId: number): Promise<void> => {
    await api.delete(`/incidents/${id}/vendors/${linkId}`);
  },

  // ─── 12. Regulatory Disclosures ───────────────────────────────────────────

  listDisclosures: async (id: number): Promise<IncidentRegulatoryDisclosure[]> => {
    const response = await api.get<IncidentRegulatoryDisclosure[]>(`/incidents/${id}/disclosures`);
    return response.data;
  },

  evaluateDisclosure: async (
    id: number,
    data: IncidentRegulatoryDisclosureCreate
  ): Promise<IncidentRegulatoryDisclosure> => {
    const response = await api.post<IncidentRegulatoryDisclosure>(
      `/incidents/${id}/disclosures`,
      data
    );
    return response.data;
  },

  notifyDisclosure: async (
    disclosureId: number,
    data: IncidentRegulatoryNotificationRequest
  ): Promise<IncidentRegulatoryDisclosure> => {
    const response = await api.post<IncidentRegulatoryDisclosure>(
      `/incidents/disclosures/${disclosureId}/notify`,
      data
    );
    return response.data;
  },

  exemptDisclosure: async (
    disclosureId: number,
    data: IncidentRegulatoryExemptionRequest
  ): Promise<IncidentRegulatoryDisclosure> => {
    const response = await api.post<IncidentRegulatoryDisclosure>(
      `/incidents/disclosures/${disclosureId}/exempt`,
      data
    );
    return response.data;
  },
};
