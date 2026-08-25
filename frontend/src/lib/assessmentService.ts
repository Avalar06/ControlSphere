import { api } from './api';
import type {
  Assessment,
  AssessmentConclusion,
  AssessmentEvidence,
  AssessmentMethod,
  AssessmentStats,
  AssessmentStatus,
} from '../types';

export const assessmentService = {
  async getAssessments(params?: {
    organization_control_id?: number;
    assessor_id?: number;
    status?: AssessmentStatus;
    conclusion?: AssessmentConclusion;
    start_date?: string;
    end_date?: string;
    skip?: number;
    limit?: number;
  }): Promise<Assessment[]> {
    const res = await api.get<Assessment[]>('/api/v1/assessments', { params });
    return res.data;
  },

  async getAssessmentById(id: number): Promise<Assessment> {
    const res = await api.get<Assessment>(`/api/v1/assessments/${id}`);
    return res.data;
  },

  async getAssessmentStats(): Promise<AssessmentStats> {
    const res = await api.get<AssessmentStats>('/api/v1/assessments/stats');
    return res.data;
  },

  async createAssessment(data: {
    organization_control_id: number;
    assessment_method?: AssessmentMethod;
    assessment_scope?: string;
    assessment_date?: string;
    summary?: string;
    limitations?: string;
    assessor_id?: number;
  }): Promise<Assessment> {
    const res = await api.post<Assessment>('/api/v1/assessments', data);
    return res.data;
  },

  async updateAssessment(
    id: number,
    data: {
      assessment_method?: AssessmentMethod;
      assessment_scope?: string;
      assessment_date?: string;
      summary?: string;
      limitations?: string;
      assessor_id?: number;
    }
  ): Promise<Assessment> {
    const res = await api.patch<Assessment>(`/api/v1/assessments/${id}`, data);
    return res.data;
  },

  async startAssessment(id: number): Promise<Assessment> {
    const res = await api.post<Assessment>(`/api/v1/assessments/${id}/start`);
    return res.data;
  },

  async completeAssessment(
    id: number,
    data: {
      conclusion: AssessmentConclusion;
      summary: string;
      limitations?: string;
    }
  ): Promise<Assessment> {
    const res = await api.post<Assessment>(`/api/v1/assessments/${id}/complete`, data);
    return res.data;
  },

  async supersedeAssessment(id: number): Promise<Assessment> {
    const res = await api.post<Assessment>(`/api/v1/assessments/${id}/supersede`);
    return res.data;
  },

  async linkEvidence(assessmentId: number, evidenceId: number): Promise<AssessmentEvidence> {
    const res = await api.post<AssessmentEvidence>(`/api/v1/assessments/${assessmentId}/evidence`, {
      evidence_id: evidenceId,
    });
    return res.data;
  },

  async unlinkEvidence(assessmentId: number, evidenceId: number): Promise<void> {
    await api.delete(`/api/v1/assessments/${assessmentId}/evidence/${evidenceId}`);
  },
};
