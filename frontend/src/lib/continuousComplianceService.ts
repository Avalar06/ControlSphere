import { api } from './api';
import type {
  ContinuousComplianceProfile,
  ContinuousComplianceProfileUpdate,
  ComplianceDriftRecord,
  UnifiedAssurancePosture,
  ContinuousAssuranceSnapshot,
  ContinuousAssuranceSnapshotCreate,
} from '../types';

export const continuousComplianceService = {
  // Profile
  getProfile: async (): Promise<ContinuousComplianceProfile> => {
    const res = await api.get<ContinuousComplianceProfile>('/continuous-compliance/profile');
    return res.data;
  },

  updateProfile: async (data: ContinuousComplianceProfileUpdate): Promise<ContinuousComplianceProfile> => {
    const res = await api.put<ContinuousComplianceProfile>('/continuous-compliance/profile', data);
    return res.data;
  },

  // Live Posture & Drift
  getPosture: async (): Promise<UnifiedAssurancePosture> => {
    const res = await api.get<UnifiedAssurancePosture>('/continuous-compliance/posture');
    return res.data;
  },

  evaluateCompliance: async (): Promise<UnifiedAssurancePosture> => {
    const res = await api.post<UnifiedAssurancePosture>('/continuous-compliance/evaluate');
    return res.data;
  },

  listDrifts: async (status?: string, vector?: string): Promise<ComplianceDriftRecord[]> => {
    const res = await api.get<ComplianceDriftRecord[]>('/continuous-compliance/drift', {
      params: { ...(status ? { status } : {}), ...(vector ? { vector } : {}) },
    });
    return res.data;
  },

  triggerRemediation: async (driftId: number): Promise<ComplianceDriftRecord> => {
    const res = await api.post<ComplianceDriftRecord>(`/continuous-compliance/drift/${driftId}/trigger-remediation`);
    return res.data;
  },

  // Snapshots
  listSnapshots: async (): Promise<ContinuousAssuranceSnapshot[]> => {
    const res = await api.get<ContinuousAssuranceSnapshot[]>('/continuous-compliance/snapshots');
    return res.data;
  },

  captureSnapshot: async (data: ContinuousAssuranceSnapshotCreate): Promise<ContinuousAssuranceSnapshot> => {
    const res = await api.post<ContinuousAssuranceSnapshot>('/continuous-compliance/snapshots', data);
    return res.data;
  },
};
