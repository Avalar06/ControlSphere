import { api } from './api';
import type {
  ExceptionCompensatingControl,
  ExceptionStats,
  ExceptionStatus,
  ExceptionType,
  SecurityException,
} from '../types';

export interface ExceptionFilterParams {
  status?: ExceptionStatus;
  exception_type?: ExceptionType;
  owner_id?: number;
  reviewer_id?: number;
  active_only?: boolean;
  expired_only?: boolean;
  search?: string;
  skip?: number;
  limit?: number;
}

export interface ExceptionCreatePayload {
  title: string;
  description: string;
  justification: string;
  exception_type: ExceptionType;
  expiry_date: string;
  effective_date?: string;
  review_date?: string;
  residual_risk_level?: string;
  owner_id?: number;
  reviewer_id?: number;
  linked_organization_control_id?: number;
  linked_policy_id?: number;
  linked_finding_id?: number;
}

export interface ExceptionUpdatePayload {
  title?: string;
  description?: string;
  justification?: string;
  exception_type?: ExceptionType;
  expiry_date?: string;
  effective_date?: string;
  review_date?: string;
  residual_risk_level?: string;
  owner_id?: number;
  reviewer_id?: number;
  linked_organization_control_id?: number;
  linked_policy_id?: number;
  linked_finding_id?: number;
}

export const exceptionService = {
  listExceptions: async (
    params?: ExceptionFilterParams
  ): Promise<SecurityException[]> => {
    const res = await api.get<SecurityException[]>('/api/v1/exceptions', { params });
    return res.data;
  },

  getException: async (id: number): Promise<SecurityException> => {
    const res = await api.get<SecurityException>(`/api/v1/exceptions/${id}`);
    return res.data;
  },

  getStats: async (): Promise<ExceptionStats> => {
    const res = await api.get<ExceptionStats>('/api/v1/exceptions/stats');
    return res.data;
  },

  createException: async (
    payload: ExceptionCreatePayload
  ): Promise<SecurityException> => {
    const res = await api.post<SecurityException>('/api/v1/exceptions', payload);
    return res.data;
  },

  updateException: async (
    id: number,
    payload: ExceptionUpdatePayload
  ): Promise<SecurityException> => {
    const res = await api.patch<SecurityException>(`/api/v1/exceptions/${id}`, payload);
    return res.data;
  },

  submitForReview: async (id: number): Promise<SecurityException> => {
    const res = await api.post<SecurityException>(`/api/v1/exceptions/${id}/submit-review`);
    return res.data;
  },

  approveException: async (
    id: number,
    approvalNotes?: string
  ): Promise<SecurityException> => {
    const res = await api.post<SecurityException>(`/api/v1/exceptions/${id}/approve`, {
      approval_notes: approvalNotes,
    });
    return res.data;
  },

  rejectException: async (
    id: number,
    rejectionReason: string
  ): Promise<SecurityException> => {
    const res = await api.post<SecurityException>(`/api/v1/exceptions/${id}/reject`, {
      rejection_reason: rejectionReason,
    });
    return res.data;
  },

  closeException: async (
    id: number,
    closureNotes: string
  ): Promise<SecurityException> => {
    const res = await api.post<SecurityException>(`/api/v1/exceptions/${id}/close`, {
      closure_notes: closureNotes,
    });
    return res.data;
  },

  linkCompensatingControl: async (
    exceptionId: number,
    controlId: number,
    notes?: string
  ): Promise<ExceptionCompensatingControl> => {
    const res = await api.post<ExceptionCompensatingControl>(
      `/api/v1/exceptions/${exceptionId}/compensating-controls`,
      {
        organization_control_id: controlId,
        implementation_notes: notes,
      }
    );
    return res.data;
  },

  unlinkCompensatingControl: async (
    exceptionId: number,
    controlId: number
  ): Promise<void> => {
    await api.delete(`/api/v1/exceptions/${exceptionId}/compensating-controls/${controlId}`);
  },
};
