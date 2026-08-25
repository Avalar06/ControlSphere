import { api } from './api';
import type {
  ControlEvidenceSummary,
  EvidenceItem,
  EvidenceRequirement,
  EvidenceStatus,
  EvidenceType,
  OrganizationEvidenceStats,
  ReviewDecision,
} from '../types';


export const evidenceService = {
  // Requirements
  async getRequirements(params?: {
    organization_control_id?: number;
    is_required?: boolean;
    evidence_type?: EvidenceType;
    search?: string;
  }): Promise<EvidenceRequirement[]> {
    const res = await api.get<EvidenceRequirement[]>('/api/v1/evidence/requirements', { params });
    return res.data;
  },

  async getRequirementById(id: number): Promise<EvidenceRequirement> {
    const res = await api.get<EvidenceRequirement>(`/api/v1/evidence/requirements/${id}`);
    return res.data;
  },

  async createRequirement(data: {
    organization_control_id: number;
    title: string;
    description?: string;
    evidence_type?: EvidenceType;
    is_required?: boolean;
    guidance?: string;
  }): Promise<EvidenceRequirement> {
    const res = await api.post<EvidenceRequirement>('/api/v1/evidence/requirements', data);
    return res.data;
  },

  async updateRequirement(
    id: number,
    data: {
      title?: string;
      description?: string;
      evidence_type?: EvidenceType;
      is_required?: boolean;
      guidance?: string;
    }
  ): Promise<EvidenceRequirement> {
    const res = await api.patch<EvidenceRequirement>(`/api/v1/evidence/requirements/${id}`, data);
    return res.data;
  },

  async deleteRequirement(id: number): Promise<void> {
    await api.delete(`/api/v1/evidence/requirements/${id}`);
  },

  // Evidence Items
  async getEvidenceItems(params?: {
    organization_control_id?: number;
    evidence_requirement_id?: number;
    status?: EvidenceStatus;
    uploaded_by_id?: number;
    search?: string;
  }): Promise<EvidenceItem[]> {
    const res = await api.get<EvidenceItem[]>('/api/v1/evidence', { params });
    return res.data;
  },

  async getEvidenceById(id: number): Promise<EvidenceItem> {
    const res = await api.get<EvidenceItem>(`/api/v1/evidence/${id}`);
    return res.data;
  },

  async uploadEvidence(formData: FormData): Promise<EvidenceItem> {
    const res = await api.post<EvidenceItem>('/api/v1/evidence/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return res.data;
  },

  async updateEvidenceMetadata(
    id: number,
    data: { title?: string; description?: string }
  ): Promise<EvidenceItem> {
    const res = await api.patch<EvidenceItem>(`/api/v1/evidence/${id}`, data);
    return res.data;
  },

  async submitForReview(id: number): Promise<EvidenceItem> {
    const res = await api.post<EvidenceItem>(`/api/v1/evidence/${id}/submit-review`);
    return res.data;
  },

  async reviewEvidence(
    id: number,
    data: {
      decision: ReviewDecision;
      review_notes?: string;
      rejection_reason?: string;
    }
  ): Promise<EvidenceItem> {
    const res = await api.post<EvidenceItem>(`/api/v1/evidence/${id}/review`, data);
    return res.data;
  },

  async supersedeEvidence(id: number, newEvidenceId: number): Promise<EvidenceItem> {
    const res = await api.post<EvidenceItem>(`/api/v1/evidence/${id}/supersede`, null, {
      params: { new_evidence_id: newEvidenceId },
    });
    return res.data;
  },

  async downloadEvidence(id: number, filename: string): Promise<void> {
    const res = await api.get(`/api/v1/evidence/${id}/download`, {
      responseType: 'blob',
    });
    const url = window.URL.createObjectURL(new Blob([res.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },

  // Assurance & Stats
  async getControlEvidenceAssurance(controlId: number): Promise<ControlEvidenceSummary> {
    const res = await api.get<ControlEvidenceSummary>(`/api/v1/evidence/controls/${controlId}/assurance`);
    return res.data;
  },

  async getEvidenceStats(): Promise<OrganizationEvidenceStats> {
    const res = await api.get<OrganizationEvidenceStats>('/api/v1/evidence/stats');
    return res.data;
  },
};