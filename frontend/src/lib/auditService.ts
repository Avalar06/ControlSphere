import { api } from './api';
import type {
  Audit,
  AuditFindingLink,
  AuditOpinion,
  AuditProcedure,
  AuditProcedureEvidence,
  AuditReadiness,
  AuditScopeControl,
  AuditStats,
  AuditStatus,
  AuditType,
  ProcedureResult,
} from '../types';

export interface AuditFilterParams {
  status?: AuditStatus;
  audit_type?: AuditType;
  lead_auditor_id?: number;
  search?: string;
  skip?: number;
  limit?: number;
}

export interface AuditCreatePayload {
  title: string;
  objective: string;
  audit_type?: AuditType;
  audit_reference?: string;
  scope_description?: string;
  methodology?: string;
  limitations?: string;
  framework_id?: number;
  lead_auditor_id?: number;
  audit_team_notes?: string;
  planned_start_date?: string;
  planned_end_date?: string;
}

export interface AuditUpdatePayload {
  title?: string;
  objective?: string;
  audit_type?: AuditType;
  audit_reference?: string;
  scope_description?: string;
  methodology?: string;
  limitations?: string;
  summary?: string;
  framework_id?: number;
  lead_auditor_id?: number;
  audit_team_notes?: string;
  planned_start_date?: string;
  planned_end_date?: string;
  actual_start_date?: string;
  actual_end_date?: string;
}

export interface AuditProcedureCreatePayload {
  title: string;
  objective?: string;
  test_steps?: string;
  expected_result?: string;
  actual_result?: string;
  assessment_method?: string;
  result?: ProcedureResult;
  execution_notes?: string;
  limitations?: string;
  organization_control_id?: number;
  tester_id?: number;
  execution_date?: string;
}

export interface AuditProcedureUpdatePayload {
  title?: string;
  objective?: string;
  test_steps?: string;
  expected_result?: string;
  actual_result?: string;
  assessment_method?: string;
  result?: ProcedureResult;
  execution_notes?: string;
  limitations?: string;
  organization_control_id?: number;
  tester_id?: number;
  execution_date?: string;
}

export const auditService = {
  listAudits: async (params?: AuditFilterParams): Promise<Audit[]> => {
    const res = await api.get<Audit[]>('/api/v1/audits', { params });
    return res.data;
  },

  getAudit: async (id: number): Promise<Audit> => {
    const res = await api.get<Audit>(`/api/v1/audits/${id}`);
    return res.data;
  },

  getStats: async (): Promise<AuditStats> => {
    const res = await api.get<AuditStats>('/api/v1/audits/stats');
    return res.data;
  },

  createAudit: async (payload: AuditCreatePayload): Promise<Audit> => {
    const res = await api.post<Audit>('/api/v1/audits', payload);
    return res.data;
  },

  updateAudit: async (id: number, payload: AuditUpdatePayload): Promise<Audit> => {
    const res = await api.patch<Audit>(`/api/v1/audits/${id}`, payload);
    return res.data;
  },

  updateStatus: async (
    id: number,
    status: AuditStatus,
    notes?: string
  ): Promise<Audit> => {
    const res = await api.post<Audit>(`/api/v1/audits/${id}/status`, { status, notes });
    return res.data;
  },

  // Scope
  listScope: async (auditId: number): Promise<AuditScopeControl[]> => {
    const res = await api.get<AuditScopeControl[]>(`/api/v1/audits/${auditId}/scope`);
    return res.data;
  },

  addScopeControl: async (
    auditId: number,
    organizationControlId: number,
    scopeNotes?: string
  ): Promise<AuditScopeControl> => {
    const res = await api.post<AuditScopeControl>(`/api/v1/audits/${auditId}/scope`, {
      organization_control_id: organizationControlId,
      scope_notes: scopeNotes,
    });
    return res.data;
  },

  removeScopeControl: async (
    auditId: number,
    controlId: number
  ): Promise<void> => {
    await api.delete(`/api/v1/audits/${auditId}/scope/${controlId}`);
  },

  // Procedures
  listProcedures: async (auditId: number): Promise<AuditProcedure[]> => {
    const res = await api.get<AuditProcedure[]>(`/api/v1/audits/${auditId}/procedures`);
    return res.data;
  },

  createProcedure: async (
    auditId: number,
    payload: AuditProcedureCreatePayload
  ): Promise<AuditProcedure> => {
    const res = await api.post<AuditProcedure>(
      `/api/v1/audits/${auditId}/procedures`,
      payload
    );
    return res.data;
  },

  updateProcedure: async (
    auditId: number,
    procedureId: number,
    payload: AuditProcedureUpdatePayload
  ): Promise<AuditProcedure> => {
    const res = await api.patch<AuditProcedure>(
      `/api/v1/audits/${auditId}/procedures/${procedureId}`,
      payload
    );
    return res.data;
  },

  // Procedure Evidence Linkage
  linkEvidence: async (
    auditId: number,
    procedureId: number,
    evidenceId: number,
    linkNotes?: string
  ): Promise<AuditProcedureEvidence> => {
    const res = await api.post<AuditProcedureEvidence>(
      `/api/v1/audits/${auditId}/procedures/${procedureId}/evidence`,
      {
        evidence_id: evidenceId,
        link_notes: linkNotes,
      }
    );
    return res.data;
  },

  unlinkEvidence: async (
    auditId: number,
    procedureId: number,
    evidenceId: number
  ): Promise<void> => {
    await api.delete(
      `/api/v1/audits/${auditId}/procedures/${procedureId}/evidence/${evidenceId}`
    );
  },

  // Finding Linkage
  listFindings: async (auditId: number): Promise<AuditFindingLink[]> => {
    const res = await api.get<AuditFindingLink[]>(`/api/v1/audits/${auditId}/findings`);
    return res.data;
  },

  linkFinding: async (
    auditId: number,
    findingId: number,
    sourceProcedureId?: number,
    linkNotes?: string
  ): Promise<AuditFindingLink> => {
    const res = await api.post<AuditFindingLink>(
      `/api/v1/audits/${auditId}/findings`,
      {
        finding_id: findingId,
        source_procedure_id: sourceProcedureId,
        link_notes: linkNotes,
      }
    );
    return res.data;
  },

  unlinkFinding: async (
    auditId: number,
    findingId: number
  ): Promise<void> => {
    await api.delete(`/api/v1/audits/${auditId}/findings/${findingId}`);
  },

  // Readiness Metrics
  getReadiness: async (auditId: number): Promise<AuditReadiness> => {
    const res = await api.get<AuditReadiness>(`/api/v1/audits/${auditId}/readiness`);
    return res.data;
  },

  // Opinion Issuance
  issueOpinion: async (
    auditId: number,
    opinion: AuditOpinion,
    opinionNotes?: string
  ): Promise<Audit> => {
    const res = await api.post<Audit>(`/api/v1/audits/${auditId}/opinion`, {
      opinion,
      opinion_notes: opinionNotes,
    });
    return res.data;
  },

  // Audit Closure
  closeAudit: async (
    auditId: number,
    closureNotes: string
  ): Promise<Audit> => {
    const res = await api.post<Audit>(`/api/v1/audits/${auditId}/close`, {
      closure_notes: closureNotes,
    });
    return res.data;
  },
};
