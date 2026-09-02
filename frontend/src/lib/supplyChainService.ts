import { api } from './api';
import type {
  BusinessCriticality,
  ComponentCalculatePreviewRequest,
  ComponentCalculatePreviewResponse,
  ComponentVulnerabilityLink,
  ComponentVulnerabilityLinkCreate,
  LicenseCompliancePolicy,
  LicenseCompliancePolicyCreate,
  ProductCalculatePreviewRequest,
  ProductCalculatePreviewResponse,
  ProductLifecycleState,
  SBOMDocument,
  SBOMDocumentCreate,
  SoftwareComponent,
  SoftwareComponentCreate,
  SoftwareProduct,
  SoftwareProductCreate,
  SoftwareProductStatusUpdate,
  SoftwareProductUpdate,
  SupplyChainApprovalStatus,
  SupplyChainExemption,
  SupplyChainExemptionCreate,
  SupplyChainExemptionReview,
  SupplyChainPostureSummaryResponse,
} from '../types';

export const supplyChainService = {
  // ─── 1. Software Products ───────────────────────────────────────────────────

  createProduct: async (data: SoftwareProductCreate): Promise<SoftwareProduct> => {
    const res = await api.post<SoftwareProduct>('/supply-chain/products', data);
    return res.data;
  },

  listProducts: async (params?: {
    lifecycle_state?: ProductLifecycleState;
    criticality_tier?: BusinessCriticality;
    skip?: number;
    limit?: number;
  }): Promise<SoftwareProduct[]> => {
    const res = await api.get<SoftwareProduct[]>('/supply-chain/products', { params });
    return res.data;
  },

  getProduct: async (id: number): Promise<SoftwareProduct> => {
    const res = await api.get<SoftwareProduct>(`/supply-chain/products/${id}`);
    return res.data;
  },

  updateProduct: async (id: number, data: SoftwareProductUpdate): Promise<SoftwareProduct> => {
    const res = await api.put<SoftwareProduct>(`/supply-chain/products/${id}`, data);
    return res.data;
  },

  updateProductStatus: async (
    id: number,
    data: SoftwareProductStatusUpdate
  ): Promise<SoftwareProduct> => {
    const res = await api.patch<SoftwareProduct>(`/supply-chain/products/${id}/status`, data);
    return res.data;
  },

  deleteProduct: async (id: number): Promise<void> => {
    await api.delete(`/supply-chain/products/${id}`);
  },

  // ─── 2. SBOM Documents ──────────────────────────────────────────────────────

  ingestSBOM: async (productId: number, data: SBOMDocumentCreate): Promise<SBOMDocument> => {
    const res = await api.post<SBOMDocument>(`/supply-chain/products/${productId}/sboms`, data);
    return res.data;
  },

  listProductSBOMs: async (productId: number): Promise<SBOMDocument[]> => {
    const res = await api.get<SBOMDocument[]>(`/supply-chain/products/${productId}/sboms`);
    return res.data;
  },

  getSBOM: async (id: number): Promise<SBOMDocument> => {
    const res = await api.get<SBOMDocument>(`/supply-chain/sboms/${id}`);
    return res.data;
  },

  // ─── 3. Software Components ─────────────────────────────────────────────────

  addComponent: async (
    sbomId: number,
    data: SoftwareComponentCreate
  ): Promise<SoftwareComponent> => {
    const res = await api.post<SoftwareComponent>(`/supply-chain/sboms/${sbomId}/components`, data);
    return res.data;
  },

  listSBOMComponents: async (sbomId: number): Promise<SoftwareComponent[]> => {
    const res = await api.get<SoftwareComponent[]>(`/supply-chain/sboms/${sbomId}/components`);
    return res.data;
  },

  getComponent: async (id: number): Promise<SoftwareComponent> => {
    const res = await api.get<SoftwareComponent>(`/supply-chain/components/${id}`);
    return res.data;
  },

  linkVulnerability: async (
    componentId: number,
    data: ComponentVulnerabilityLinkCreate
  ): Promise<ComponentVulnerabilityLink> => {
    const res = await api.post<ComponentVulnerabilityLink>(
      `/supply-chain/components/${componentId}/vulnerabilities`,
      data
    );
    return res.data;
  },

  // ─── 4. Preview Calculations ────────────────────────────────────────────────

  calculateComponentPreview: async (
    data: ComponentCalculatePreviewRequest
  ): Promise<ComponentCalculatePreviewResponse> => {
    const res = await api.post<ComponentCalculatePreviewResponse>(
      '/supply-chain/components/calculate-preview',
      data
    );
    return res.data;
  },

  calculateProductPreview: async (
    data: ProductCalculatePreviewRequest
  ): Promise<ProductCalculatePreviewResponse> => {
    const res = await api.post<ProductCalculatePreviewResponse>(
      '/supply-chain/products/calculate-preview',
      data
    );
    return res.data;
  },

  // ─── 5. License Policies & Exemptions ───────────────────────────────────────

  createPolicy: async (
    data: LicenseCompliancePolicyCreate
  ): Promise<LicenseCompliancePolicy> => {
    const res = await api.post<LicenseCompliancePolicy>('/supply-chain/policies', data);
    return res.data;
  },

  listPolicies: async (): Promise<LicenseCompliancePolicy[]> => {
    const res = await api.get<LicenseCompliancePolicy[]>('/supply-chain/policies');
    return res.data;
  },

  createExemption: async (
    data: SupplyChainExemptionCreate
  ): Promise<SupplyChainExemption> => {
    const res = await api.post<SupplyChainExemption>('/supply-chain/exemptions', data);
    return res.data;
  },

  listExemptions: async (params?: {
    approval_status?: SupplyChainApprovalStatus;
    product_id?: number;
    skip?: number;
    limit?: number;
  }): Promise<SupplyChainExemption[]> => {
    const res = await api.get<SupplyChainExemption[]>('/supply-chain/exemptions', { params });
    return res.data;
  },

  getExemption: async (id: number): Promise<SupplyChainExemption> => {
    const res = await api.get<SupplyChainExemption>(`/supply-chain/exemptions/${id}`);
    return res.data;
  },

  reviewExemption: async (
    id: number,
    data: SupplyChainExemptionReview
  ): Promise<SupplyChainExemption> => {
    const res = await api.post<SupplyChainExemption>(`/supply-chain/exemptions/${id}/review`, data);
    return res.data;
  },

  // ─── 6. Posture Telemetry ───────────────────────────────────────────────────

  getPostureSummary: async (): Promise<SupplyChainPostureSummaryResponse> => {
    const res = await api.get<SupplyChainPostureSummaryResponse>('/supply-chain/summary/posture');
    return res.data;
  },
};
