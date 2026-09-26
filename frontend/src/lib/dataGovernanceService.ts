import { api } from './api';
import type {
  DataAssetCloudLink,
  DataAssetCloudLinkCreate,
  DataAssetControlLink,
  DataAssetControlLinkCreate,
  DataAssetDeprecateRequest,
  DataAssetEvidenceLink,
  DataAssetEvidenceLinkCreate,
  DataAssetProcessingLink,
  DataAssetProcessingLinkCreate,
  DataAssetRegisterRequest,
  DataAssetRestoreRequest,
  DataAssetRetireRequest,
  DataClassificationLevel,
  DataClassificationLevelCreate,
  DataClassificationRecord,
  DataClassificationRejectRequest,
  DataClassificationRequestCreate,
  DataClassificationScheme,
  DataClassificationSchemeCreate,
  DataGovernanceSummary,
  DataLineageEdge,
  DataLineageEdgeCreate,
  DataLineageEdgeRevokeRequest,
  DataOwnershipUpdateRequest,
  GovernedDataAsset,
  GovernedDataAssetCreate,
  GovernedDataAssetDossier,
  GovernedDataAssetUpdate,
} from '../types/dataGovernance';

export const dataGovernanceService = {
  // Posture Summary
  getSummary: async (): Promise<DataGovernanceSummary> => {
    const res = await api.get('/data-governance/summary');
    return res.data;
  },

  // Classification Schemes & Levels
  createScheme: async (
    payload: DataClassificationSchemeCreate
  ): Promise<DataClassificationScheme> => {
    const res = await api.post('/data-governance/schemes', payload);
    return res.data;
  },

  listSchemes: async (status?: string): Promise<DataClassificationScheme[]> => {
    const res = await api.get('/data-governance/schemes', {
      params: status ? { status } : undefined,
    });
    return res.data;
  },

  getScheme: async (schemeId: number): Promise<DataClassificationScheme> => {
    const res = await api.get(`/data-governance/schemes/${schemeId}`);
    return res.data;
  },

  addLevelToScheme: async (
    schemeId: number,
    payload: DataClassificationLevelCreate
  ): Promise<DataClassificationLevel> => {
    const res = await api.post(
      `/data-governance/schemes/${schemeId}/levels`,
      payload
    );
    return res.data;
  },

  submitScheme: async (schemeId: number): Promise<DataClassificationScheme> => {
    const res = await api.post(`/data-governance/schemes/${schemeId}/submit`);
    return res.data;
  },

  approveScheme: async (
    schemeId: number
  ): Promise<DataClassificationScheme> => {
    const res = await api.post(`/data-governance/schemes/${schemeId}/approve`);
    return res.data;
  },

  // Governed Data Assets
  createAsset: async (
    payload: GovernedDataAssetCreate
  ): Promise<GovernedDataAsset> => {
    const res = await api.post('/data-governance/assets', payload);
    return res.data;
  },

  listAssets: async (params?: {
    lifecycle_state?: string;
    sensitivity_level?: string;
    classification_status?: string;
    owner_id?: number;
  }): Promise<GovernedDataAsset[]> => {
    const res = await api.get('/data-governance/assets', { params });
    return res.data;
  },

  getAssetDossier: async (
    assetId: number
  ): Promise<GovernedDataAssetDossier> => {
    const res = await api.get(`/data-governance/assets/${assetId}`);
    return res.data;
  },

  updateAsset: async (
    assetId: number,
    payload: GovernedDataAssetUpdate
  ): Promise<GovernedDataAsset> => {
    const res = await api.put(`/data-governance/assets/${assetId}`, payload);
    return res.data;
  },

  // Classification Workflow
  requestClassification: async (
    assetId: number,
    payload: DataClassificationRequestCreate
  ): Promise<DataClassificationRecord> => {
    const res = await api.post(
      `/data-governance/assets/${assetId}/classifications`,
      payload
    );
    return res.data;
  },

  listClassificationHistory: async (
    assetId: number
  ): Promise<DataClassificationRecord[]> => {
    const res = await api.get(
      `/data-governance/assets/${assetId}/classifications`
    );
    return res.data;
  },

  approveClassification: async (
    recordId: number
  ): Promise<DataClassificationRecord> => {
    const res = await api.post(
      `/data-governance/classifications/${recordId}/approve`
    );
    return res.data;
  },

  rejectClassification: async (
    recordId: number,
    payload: DataClassificationRejectRequest
  ): Promise<DataClassificationRecord> => {
    const res = await api.post(
      `/data-governance/classifications/${recordId}/reject`,
      payload
    );
    return res.data;
  },

  // Ownership, Lifecycle & Retirement
  registerDiscoveredAsset: async (
    assetId: number,
    payload: DataAssetRegisterRequest
  ): Promise<GovernedDataAsset> => {
    const res = await api.post(
      `/data-governance/assets/${assetId}/register`,
      payload
    );
    return res.data;
  },

  activateAsset: async (assetId: number): Promise<GovernedDataAsset> => {
    const res = await api.post(`/data-governance/assets/${assetId}/activate`);
    return res.data;
  },

  updateOwnership: async (
    assetId: number,
    payload: DataOwnershipUpdateRequest
  ): Promise<GovernedDataAsset> => {
    const res = await api.post(
      `/data-governance/assets/${assetId}/ownership`,
      payload
    );
    return res.data;
  },

  approveOwnershipTransfer: async (
    assetId: number
  ): Promise<GovernedDataAsset> => {
    const res = await api.post(
      `/data-governance/assets/${assetId}/ownership/approve`
    );
    return res.data;
  },

  deprecateAsset: async (
    assetId: number,
    payload: DataAssetDeprecateRequest
  ): Promise<GovernedDataAsset> => {
    const res = await api.post(
      `/data-governance/assets/${assetId}/deprecate`,
      payload
    );
    return res.data;
  },

  requestRetirement: async (
    assetId: number,
    payload: DataAssetRetireRequest
  ): Promise<GovernedDataAsset> => {
    const res = await api.post(
      `/data-governance/assets/${assetId}/retire-request`,
      payload
    );
    return res.data;
  },

  finalizeRetirement: async (
    assetId: number,
    payload: DataAssetRetireRequest
  ): Promise<GovernedDataAsset> => {
    const res = await api.post(
      `/data-governance/assets/${assetId}/retire`,
      payload
    );
    return res.data;
  },

  restoreAsset: async (
    assetId: number,
    payload: DataAssetRestoreRequest
  ): Promise<GovernedDataAsset> => {
    const res = await api.post(
      `/data-governance/assets/${assetId}/restore`,
      payload
    );
    return res.data;
  },

  // Data Lineage
  createLineageEdge: async (
    payload: DataLineageEdgeCreate
  ): Promise<DataLineageEdge> => {
    const res = await api.post('/data-governance/lineage-edges', payload);
    return res.data;
  },

  listLineageEdges: async (params?: {
    status?: string;
    asset_id?: number;
  }): Promise<DataLineageEdge[]> => {
    const res = await api.get('/data-governance/lineage-edges', { params });
    return res.data;
  },

  getLineageEdge: async (edgeId: number): Promise<DataLineageEdge> => {
    const res = await api.get(`/data-governance/lineage-edges/${edgeId}`);
    return res.data;
  },

  approveLineageEdge: async (edgeId: number): Promise<DataLineageEdge> => {
    const res = await api.post(
      `/data-governance/lineage-edges/${edgeId}/approve`
    );
    return res.data;
  },

  revokeLineageEdge: async (
    edgeId: number,
    payload: DataLineageEdgeRevokeRequest
  ): Promise<DataLineageEdge> => {
    const res = await api.post(
      `/data-governance/lineage-edges/${edgeId}/revoke`,
      payload
    );
    return res.data;
  },

  // Cross-Domain Links
  linkCloudAsset: async (
    assetId: number,
    payload: DataAssetCloudLinkCreate
  ): Promise<DataAssetCloudLink> => {
    const res = await api.post(
      `/data-governance/assets/${assetId}/cloud-links`,
      payload
    );
    return res.data;
  },

  linkProcessingActivity: async (
    assetId: number,
    payload: DataAssetProcessingLinkCreate
  ): Promise<DataAssetProcessingLink> => {
    const res = await api.post(
      `/data-governance/assets/${assetId}/processing-links`,
      payload
    );
    return res.data;
  },

  linkControl: async (
    assetId: number,
    payload: DataAssetControlLinkCreate
  ): Promise<DataAssetControlLink> => {
    const res = await api.post(
      `/data-governance/assets/${assetId}/control-links`,
      payload
    );
    return res.data;
  },

  linkEvidence: async (
    assetId: number,
    payload: DataAssetEvidenceLinkCreate
  ): Promise<DataAssetEvidenceLink> => {
    const res = await api.post(
      `/data-governance/assets/${assetId}/evidence-links`,
      payload
    );
    return res.data;
  },
};
