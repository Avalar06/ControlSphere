import { api } from './api';
import type {
  DossierStatus,
  DossierType,
  BriefingStatus,
  ExportFormat,
  ExecutiveTelemetryResponse,
  ExecutiveTrendsResponse,
  ExecutiveSnapshot,
  ExecutiveSnapshotCreate,
  ExecutiveDossier,
  ExecutiveDossierCreate,
  ExecutiveDossierUpdate,
  ExecutiveBriefing,
  ExecutiveBriefingCreate,
  ExecutiveBriefingReview,
  ExecutiveExportArtifact,
} from '../types';

export const executiveService = {
  // ─── 1. Executive Telemetry & Trends ────────────────────────────────────────

  getLiveTelemetry: async (): Promise<ExecutiveTelemetryResponse> => {
    const res = await api.get<ExecutiveTelemetryResponse>('/executive/telemetry/live');
    return res.data;
  },

  getHistoricalTrends: async (windowDays: number = 90): Promise<ExecutiveTrendsResponse> => {
    const res = await api.get<ExecutiveTrendsResponse>('/executive/telemetry/trends', {
      params: { window_days: windowDays },
    });
    return res.data;
  },

  getDomainMatrix: async (): Promise<{
    overall_posture_score: number;
    domains: Record<string, { name: string; score: number; weight: number }>;
    calculated_at: string;
  }> => {
    const res = await api.get('/executive/telemetry/domain-matrix');
    return res.data;
  },

  // ─── 2. Executive Snapshots ──────────────────────────────────────────────────

  captureSnapshot: async (data: ExecutiveSnapshotCreate): Promise<ExecutiveSnapshot> => {
    const res = await api.post<ExecutiveSnapshot>('/executive/snapshots', data);
    return res.data;
  },

  listSnapshots: async (): Promise<ExecutiveSnapshot[]> => {
    const res = await api.get<ExecutiveSnapshot[]>('/executive/snapshots');
    return res.data;
  },

  getSnapshot: async (id: number): Promise<ExecutiveSnapshot> => {
    const res = await api.get<ExecutiveSnapshot>(`/executive/snapshots/${id}`);
    return res.data;
  },

  // ─── 3. Regulatory Compliance Dossiers ──────────────────────────────────────

  createDossier: async (data: ExecutiveDossierCreate): Promise<ExecutiveDossier> => {
    const res = await api.post<ExecutiveDossier>('/executive/dossiers', data);
    return res.data;
  },

  listDossiers: async (params?: {
    status?: DossierStatus;
    dossier_type?: DossierType;
  }): Promise<ExecutiveDossier[]> => {
    const res = await api.get<ExecutiveDossier[]>('/executive/dossiers', { params });
    return res.data;
  },

  getDossier: async (id: number): Promise<ExecutiveDossier> => {
    const res = await api.get<ExecutiveDossier>(`/executive/dossiers/${id}`);
    return res.data;
  },

  updateDossier: async (id: number, data: ExecutiveDossierUpdate): Promise<ExecutiveDossier> => {
    const res = await api.patch<ExecutiveDossier>(`/executive/dossiers/${id}`, data);
    return res.data;
  },

  compileDossier: async (id: number): Promise<ExecutiveDossier> => {
    const res = await api.post<ExecutiveDossier>(`/executive/dossiers/${id}/compile`);
    return res.data;
  },

  finalizeDossier: async (id: number): Promise<ExecutiveDossier> => {
    const res = await api.post<ExecutiveDossier>(`/executive/dossiers/${id}/finalize`);
    return res.data;
  },

  // ─── 4. Executive & Board Briefings ──────────────────────────────────────────

  generateBriefing: async (data: ExecutiveBriefingCreate): Promise<ExecutiveBriefing> => {
    const res = await api.post<ExecutiveBriefing>('/executive/briefings', data);
    return res.data;
  },

  listBriefings: async (params?: { status?: BriefingStatus }): Promise<ExecutiveBriefing[]> => {
    const res = await api.get<ExecutiveBriefing[]>('/executive/briefings', { params });
    return res.data;
  },

  getBriefing: async (id: number): Promise<ExecutiveBriefing> => {
    const res = await api.get<ExecutiveBriefing>(`/executive/briefings/${id}`);
    return res.data;
  },

  submitBriefing: async (id: number): Promise<ExecutiveBriefing> => {
    const res = await api.post<ExecutiveBriefing>(`/executive/briefings/${id}/submit`);
    return res.data;
  },

  reviewBriefing: async (id: number, review: ExecutiveBriefingReview): Promise<ExecutiveBriefing> => {
    const res = await api.post<ExecutiveBriefing>(`/executive/briefings/${id}/review`, review);
    return res.data;
  },

  // ─── 5. Forensic Exports (PDF / JSON) ────────────────────────────────────────

  exportSnapshot: async (id: number, format: ExportFormat = 'PDF'): Promise<ExecutiveExportArtifact> => {
    const res = await api.post<ExecutiveExportArtifact>(`/executive/exports/snapshot/${id}`, null, {
      params: { format },
    });
    return res.data;
  },

  exportDossier: async (id: number, format: ExportFormat = 'PDF'): Promise<ExecutiveExportArtifact> => {
    const res = await api.post<ExecutiveExportArtifact>(`/executive/exports/dossier/${id}`, null, {
      params: { format },
    });
    return res.data;
  },

  exportBriefing: async (id: number, format: ExportFormat = 'PDF'): Promise<ExecutiveExportArtifact> => {
    const res = await api.post<ExecutiveExportArtifact>(`/executive/exports/briefing/${id}`, null, {
      params: { format },
    });
    return res.data;
  },

  listExports: async (): Promise<ExecutiveExportArtifact[]> => {
    const res = await api.get<ExecutiveExportArtifact[]>('/executive/exports');
    return res.data;
  },

  downloadExport: async (exportId: number, filename: string): Promise<void> => {
    const response = await api.get(`/executive/exports/${exportId}/download`, {
      responseType: 'blob',
    });
    const blob = new Blob([response.data], {
      type: (response.headers as any)['content-type'] || 'application/octet-stream',
    });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },
};
