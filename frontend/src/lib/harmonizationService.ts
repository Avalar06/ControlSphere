import { api } from './api';
import type {
  CommonControlCreate,
  CommonControlDomain,
  CommonControlMapping,
  CommonControlMappingCreate,
  CommonControlUpdate,
  CrosswalkMappingCreate,
  CrosswalkMappingUpdate,
  FrameworkComplianceSnapshot,
  FrameworkCrosswalkMapping,
  FrameworkDetailedPostureResponse,
  HarmonizationEvaluationResponse,
  MultiFrameworkPostureResponse,
  RationalizationStatus,
  RationalizedCommonControl,
} from '../types';

export const harmonizationService = {
  // ── Global Crosswalk Mappings ─────────────────────────────────────────────
  listCrosswalks: async (params?: {
    source_framework_id?: number;
    target_framework_id?: number;
  }): Promise<FrameworkCrosswalkMapping[]> => {
    const response = await api.get<FrameworkCrosswalkMapping[]>('/harmonization/crosswalks', {
      params,
    });
    return response.data;
  },

  getCrosswalk: async (id: number): Promise<FrameworkCrosswalkMapping> => {
    const response = await api.get<FrameworkCrosswalkMapping>(`/harmonization/crosswalks/${id}`);
    return response.data;
  },

  createCrosswalk: async (data: CrosswalkMappingCreate): Promise<FrameworkCrosswalkMapping> => {
    const response = await api.post<FrameworkCrosswalkMapping>('/harmonization/crosswalks', data);
    return response.data;
  },

  updateCrosswalk: async (
    id: number,
    data: CrosswalkMappingUpdate
  ): Promise<FrameworkCrosswalkMapping> => {
    const response = await api.patch<FrameworkCrosswalkMapping>(
      `/harmonization/crosswalks/${id}`,
      data
    );
    return response.data;
  },

  deleteCrosswalk: async (id: number): Promise<void> => {
    await api.delete(`/harmonization/crosswalks/${id}`);
  },

  // ── Rationalized Common Controls ──────────────────────────────────────────
  listCommonControls: async (params?: {
    domain?: CommonControlDomain;
    status?: RationalizationStatus;
  }): Promise<RationalizedCommonControl[]> => {
    const response = await api.get<RationalizedCommonControl[]>('/harmonization/common-controls', {
      params,
    });
    return response.data;
  },

  getCommonControl: async (id: number): Promise<RationalizedCommonControl> => {
    const response = await api.get<RationalizedCommonControl>(
      `/harmonization/common-controls/${id}`
    );
    return response.data;
  },

  createCommonControl: async (data: CommonControlCreate): Promise<RationalizedCommonControl> => {
    const response = await api.post<RationalizedCommonControl>(
      '/harmonization/common-controls',
      data
    );
    return response.data;
  },

  updateCommonControl: async (
    id: number,
    data: CommonControlUpdate
  ): Promise<RationalizedCommonControl> => {
    const response = await api.patch<RationalizedCommonControl>(
      `/harmonization/common-controls/${id}`,
      data
    );
    return response.data;
  },

  // ── Common Control Mappings ───────────────────────────────────────────────
  listMappings: async (commonControlId: number): Promise<CommonControlMapping[]> => {
    const response = await api.get<CommonControlMapping[]>(
      `/harmonization/common-controls/${commonControlId}/mappings`
    );
    return response.data;
  },

  addMapping: async (
    commonControlId: number,
    data: CommonControlMappingCreate
  ): Promise<CommonControlMapping> => {
    const response = await api.post<CommonControlMapping>(
      `/harmonization/common-controls/${commonControlId}/mappings`,
      data
    );
    return response.data;
  },

  removeMapping: async (
    commonControlId: number,
    organizationControlId: number
  ): Promise<void> => {
    await api.delete(
      `/harmonization/common-controls/${commonControlId}/mappings/${organizationControlId}`
    );
  },

  // ── Multi-Framework Evaluation ────────────────────────────────────────────
  evaluateAll: async (): Promise<HarmonizationEvaluationResponse> => {
    const response = await api.post<HarmonizationEvaluationResponse>('/harmonization/evaluate');
    return response.data;
  },

  evaluateFramework: async (frameworkId: number): Promise<FrameworkComplianceSnapshot> => {
    const response = await api.post<FrameworkComplianceSnapshot>(
      `/harmonization/frameworks/${frameworkId}/evaluate`
    );
    return response.data;
  },

  // ── Posture & Detailed Matrices ───────────────────────────────────────────
  getPosture: async (): Promise<MultiFrameworkPostureResponse> => {
    const response = await api.get<MultiFrameworkPostureResponse>('/harmonization/posture');
    return response.data;
  },

  getFrameworkPosture: async (frameworkId: number): Promise<FrameworkDetailedPostureResponse> => {
    const response = await api.get<FrameworkDetailedPostureResponse>(
      `/harmonization/frameworks/${frameworkId}/posture`
    );
    return response.data;
  },

  // ── Historical Compliance Snapshots ───────────────────────────────────────
  listSnapshots: async (params?: {
    framework_id?: number;
    limit?: number;
  }): Promise<FrameworkComplianceSnapshot[]> => {
    const response = await api.get<FrameworkComplianceSnapshot[]>('/harmonization/snapshots', {
      params,
    });
    return response.data;
  },

  listFrameworkSnapshots: async (
    frameworkId: number,
    limit: number = 50
  ): Promise<FrameworkComplianceSnapshot[]> => {
    const response = await api.get<FrameworkComplianceSnapshot[]>(
      `/harmonization/frameworks/${frameworkId}/snapshots`,
      { params: { limit } }
    );
    return response.data;
  },

  getSnapshot: async (snapshotId: number): Promise<FrameworkComplianceSnapshot> => {
    const response = await api.get<FrameworkComplianceSnapshot>(
      `/harmonization/snapshots/${snapshotId}`
    );
    return response.data;
  },
};
