import { api } from './api';
import type {
  RegulatorySource,
  RegulatorySourceCreate,
  RegulatoryMandate,
  RegulatoryMandateCreate,
  RegulatoryObligation,
  RegulatoryObligationCreate,
  RegulatoryChangeEvent,
  RegulatoryChangeEventCreate,
  RegulatoryChangeReviewRequest,
  RegulatoryChangeApproveRequest,
  RegulatoryChangeDismissRequest,
} from '../types';

export const regulatoryService = {
  // Sources
  listSources: async (): Promise<RegulatorySource[]> => {
    const res = await api.get<RegulatorySource[]>('/regulatory/sources');
    return res.data;
  },

  createSource: async (data: RegulatorySourceCreate): Promise<RegulatorySource> => {
    const res = await api.post<RegulatorySource>('/regulatory/sources', data);
    return res.data;
  },

  // Mandates
  listMandates: async (status?: string): Promise<RegulatoryMandate[]> => {
    const res = await api.get<RegulatoryMandate[]>('/regulatory/mandates', {
      params: status ? { status } : undefined,
    });
    return res.data;
  },

  createMandate: async (data: RegulatoryMandateCreate): Promise<RegulatoryMandate> => {
    const res = await api.post<RegulatoryMandate>('/regulatory/mandates', data);
    return res.data;
  },

  // Obligations
  listObligations: async (mandateId?: number): Promise<RegulatoryObligation[]> => {
    const res = await api.get<RegulatoryObligation[]>('/regulatory/obligations', {
      params: mandateId ? { mandate_id: mandateId } : undefined,
    });
    return res.data;
  },

  createObligation: async (data: RegulatoryObligationCreate): Promise<RegulatoryObligation> => {
    const res = await api.post<RegulatoryObligation>('/regulatory/obligations', data);
    return res.data;
  },

  // Change Events & Workflow
  listChanges: async (status?: string, mandateId?: number): Promise<RegulatoryChangeEvent[]> => {
    const res = await api.get<RegulatoryChangeEvent[]>('/regulatory/changes', {
      params: { ...(status ? { status } : {}), ...(mandateId ? { mandate_id: mandateId } : {}) },
    });
    return res.data;
  },

  stageChange: async (data: RegulatoryChangeEventCreate): Promise<RegulatoryChangeEvent> => {
    const res = await api.post<RegulatoryChangeEvent>('/regulatory/changes', data);
    return res.data;
  },

  reviewChange: async (id: number, data: RegulatoryChangeReviewRequest): Promise<RegulatoryChangeEvent> => {
    const res = await api.post<RegulatoryChangeEvent>(`/regulatory/changes/${id}/review`, data);
    return res.data;
  },

  approveChange: async (id: number, data: RegulatoryChangeApproveRequest): Promise<RegulatoryChangeEvent> => {
    const res = await api.post<RegulatoryChangeEvent>(`/regulatory/changes/${id}/approve`, data);
    return res.data;
  },

  dismissChange: async (id: number, data: RegulatoryChangeDismissRequest): Promise<RegulatoryChangeEvent> => {
    const res = await api.post<RegulatoryChangeEvent>(`/regulatory/changes/${id}/dismiss`, data);
    return res.data;
  },
};
