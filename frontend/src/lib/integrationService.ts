import { api } from './api';
import type {
  IntegrationProvider,
  IntegrationConnection,
  IntegrationConnectionCreate,
  IntegrationCredentialCreate,
  IntegrationCredentialResponse,
  EvidenceCollectionJob,
  EvidenceCollectionJobCreate,
  EvidenceCollectionRun,
} from '../types';

export const integrationService = {
  // Providers
  listProviders: async (): Promise<IntegrationProvider[]> => {
    const res = await api.get<IntegrationProvider[]>('/integrations/providers');
    return res.data;
  },

  // Connections
  listConnections: async (): Promise<IntegrationConnection[]> => {
    const res = await api.get<IntegrationConnection[]>('/integrations/connections');
    return res.data;
  },

  getConnection: async (id: number): Promise<IntegrationConnection> => {
    const res = await api.get<IntegrationConnection>(`/integrations/connections/${id}`);
    return res.data;
  },

  createConnection: async (data: IntegrationConnectionCreate): Promise<IntegrationConnection> => {
    const res = await api.post<IntegrationConnection>('/integrations/connections', data);
    return res.data;
  },

  setCredentials: async (id: number, data: IntegrationCredentialCreate): Promise<IntegrationCredentialResponse> => {
    const res = await api.post<IntegrationCredentialResponse>(`/integrations/connections/${id}/credentials`, data);
    return res.data;
  },

  testConnection: async (id: number): Promise<{ connection_id: number; status: string; is_authenticated: boolean; tested_at: string }> => {
    const res = await api.post(`/integrations/connections/${id}/test`);
    return res.data;
  },

  // Jobs
  listJobs: async (): Promise<EvidenceCollectionJob[]> => {
    const res = await api.get<EvidenceCollectionJob[]>('/integrations/jobs');
    return res.data;
  },

  createJob: async (data: EvidenceCollectionJobCreate): Promise<EvidenceCollectionJob> => {
    const res = await api.post<EvidenceCollectionJob>('/integrations/jobs', data);
    return res.data;
  },

  triggerJobRun: async (id: number): Promise<EvidenceCollectionRun> => {
    const res = await api.post<EvidenceCollectionRun>(`/integrations/jobs/${id}/run`);
    return res.data;
  },

  // Runs
  listRuns: async (jobId?: number): Promise<EvidenceCollectionRun[]> => {
    const res = await api.get<EvidenceCollectionRun[]>('/integrations/runs', {
      params: jobId ? { job_id: jobId } : undefined,
    });
    return res.data;
  },
};
