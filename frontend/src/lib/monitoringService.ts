import { api } from './api';
import type {
  ComplianceDriftAlert,
  ControlHealthSnapshot,
  ControlHealthStatus,
  ControlHealthSummary,
  DriftAlertSeverity,
  DriftAlertStatus,
  DriftAlertType,
  EvaluationRunResult,
  MonitoringConfig,
  MonitoringOverview,
} from '../types';

export const monitoringService = {
  // Overview metrics
  getOverview: async (): Promise<MonitoringOverview> => {
    const response = await api.get<MonitoringOverview>('/monitoring/overview');
    return response.data;
  },

  // Control health catalog
  listControlHealth: async (params?: {
    status?: ControlHealthStatus;
    search?: string;
    skip?: number;
    limit?: number;
  }): Promise<ControlHealthSummary[]> => {
    const response = await api.get<ControlHealthSummary[]>('/monitoring/controls', {
      params,
    });
    return response.data;
  },

  // Control health snapshots history
  getControlHistory: async (
    controlId: number,
    limit: number = 30
  ): Promise<ControlHealthSnapshot[]> => {
    const response = await api.get<ControlHealthSnapshot[]>(
      `/monitoring/controls/${controlId}/history`,
      { params: { limit } }
    );
    return response.data;
  },

  // Trigger manual evaluation run
  triggerEvaluation: async (): Promise<EvaluationRunResult> => {
    const response = await api.post<EvaluationRunResult>('/monitoring/evaluate');
    return response.data;
  },

  // Alerts
  listAlerts: async (params?: {
    status?: DriftAlertStatus;
    severity?: DriftAlertSeverity;
    alert_type?: DriftAlertType;
    skip?: number;
    limit?: number;
  }): Promise<ComplianceDriftAlert[]> => {
    const response = await api.get<ComplianceDriftAlert[]>('/monitoring/alerts', {
      params,
    });
    return response.data;
  },

  acknowledgeAlert: async (alertId: number): Promise<ComplianceDriftAlert> => {
    const response = await api.post<ComplianceDriftAlert>(
      `/monitoring/alerts/${alertId}/acknowledge`
    );
    return response.data;
  },

  resolveAlert: async (
    alertId: number,
    resolutionNotes: string
  ): Promise<ComplianceDriftAlert> => {
    const response = await api.post<ComplianceDriftAlert>(
      `/monitoring/alerts/${alertId}/resolve`,
      { resolution_notes: resolutionNotes }
    );
    return response.data;
  },

  dismissAlert: async (
    alertId: number,
    justification: string
  ): Promise<ComplianceDriftAlert> => {
    const response = await api.post<ComplianceDriftAlert>(
      `/monitoring/alerts/${alertId}/dismiss`,
      { justification }
    );
    return response.data;
  },

  // Config
  getConfig: async (): Promise<MonitoringConfig> => {
    const response = await api.get<MonitoringConfig>('/monitoring/config');
    return response.data;
  },

  updateConfig: async (
    configUpdate: Partial<MonitoringConfig>
  ): Promise<MonitoringConfig> => {
    const response = await api.patch<MonitoringConfig>(
      '/monitoring/config',
      configUpdate
    );
    return response.data;
  },
};
