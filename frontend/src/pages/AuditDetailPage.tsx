import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Award,
  Lock,
  Plus,
  Trash2,
  Link as LinkIcon,
  Unlink,
  X,
  Layers,
  FileText,
  Activity,
  AlertCircle,
} from 'lucide-react';
import { auditService } from '../lib/auditService';
import { api } from '../lib/api';
import { findingService } from '../lib/findingService';
import { evidenceService } from '../lib/evidenceService';
import type {
  AuditStatus,
  AuditOpinion,
  ProcedureResult,
} from '../types';

export const AuditDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const auditId = Number(id);

  const [activeTab, setActiveTab] = useState<
    'overview' | 'scope' | 'procedures' | 'findings' | 'readiness' | 'governance'
  >('overview');

  // Modal states
  const [isAddScopeModalOpen, setIsAddScopeModalOpen] = useState(false);
  const [isCreateProcedureModalOpen, setIsCreateProcedureModalOpen] = useState(false);
  const [isLinkFindingModalOpen, setIsLinkFindingModalOpen] = useState(false);
  const [isLinkEvidenceModalOpen, setIsLinkEvidenceModalOpen] = useState(false);
  const [selectedProcedureId, setSelectedProcedureId] = useState<number | null>(null);
  const [isIssueOpinionModalOpen, setIsIssueOpinionModalOpen] = useState(false);
  const [isCloseAuditModalOpen, setIsCloseAuditModalOpen] = useState(false);
  const [isEditProcedureModalOpen, setIsEditProcedureModalOpen] = useState(false);
  const [editingProcedure, setEditingProcedure] = useState<any>(null);

  // Form states
  const [selectedControlId, setSelectedControlId] = useState<number | ''>('');
  const [scopeNotes, setScopeNotes] = useState('');
  const [newProcData, setNewProcData] = useState({
    title: '',
    objective: '',
    test_steps: '',
    expected_result: '',
    assessment_method: 'Inspection',
    result: 'NOT_STARTED' as ProcedureResult,
    organization_control_id: undefined as number | undefined,
  });
  const [selectedFindingId, setSelectedFindingId] = useState<number | ''>('');
  const [findingSourceProcId, setFindingSourceProcId] = useState<number | ''>('');
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<number | ''>('');
  const [opinionData, setOpinionData] = useState<{
    opinion: AuditOpinion;
    opinion_notes: string;
  }>({
    opinion: 'UNQUALIFIED',
    opinion_notes: '',
  });
  const [closureNotes, setClosureNotes] = useState('');
  const [actionError, setActionError] = useState<string | null>(null);

  // Queries
  const { data: audit, isLoading: isAuditLoading } = useQuery({
    queryKey: ['audit', auditId],
    queryFn: () => auditService.getAudit(auditId),
    enabled: !isNaN(auditId),
  });

  const { data: readiness } = useQuery({
    queryKey: ['auditReadiness', auditId],
    queryFn: () => auditService.getReadiness(auditId),
    enabled: !isNaN(auditId),
  });

  const { data: allControls = [] } = useQuery({
    queryKey: ['controls'],
    queryFn: async () => {
      const res = await api.get<any[]>('/api/v1/controls');
      return res.data;
    },
  });

  const { data: allFindings = [] } = useQuery({
    queryKey: ['findings'],
    queryFn: () => findingService.getFindings(),
  });

  const { data: allEvidence = [] } = useQuery({
    queryKey: ['evidence'],
    queryFn: () => evidenceService.getEvidenceItems(),
  });

  // Mutations
  const statusMutation = useMutation({
    mutationFn: (newStatus: AuditStatus) =>
      auditService.updateStatus(auditId, newStatus),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['audit', auditId] });
      queryClient.invalidateQueries({ queryKey: ['auditReadiness', auditId] });
      setActionError(null);
    },
    onError: (err: any) => {
      setActionError(err.response?.data?.detail || err.message || 'Status change failed');
    },
  });

  const addScopeMutation = useMutation({
    mutationFn: () =>
      auditService.addScopeControl(auditId, Number(selectedControlId), scopeNotes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['audit', auditId] });
      queryClient.invalidateQueries({ queryKey: ['auditReadiness', auditId] });
      setIsAddScopeModalOpen(false);
      setSelectedControlId('');
      setScopeNotes('');
      setActionError(null);
    },
    onError: (err: any) => {
      setActionError(err.response?.data?.detail || err.message || 'Failed to add control');
    },
  });

  const removeScopeMutation = useMutation({
    mutationFn: (controlId: number) =>
      auditService.removeScopeControl(auditId, controlId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['audit', auditId] });
      queryClient.invalidateQueries({ queryKey: ['auditReadiness', auditId] });
      setActionError(null);
    },
    onError: (err: any) => {
      setActionError(err.response?.data?.detail || err.message || 'Failed to remove control');
    },
  });

  const createProcMutation = useMutation({
    mutationFn: () =>
      auditService.createProcedure(auditId, {
        ...newProcData,
        organization_control_id: newProcData.organization_control_id || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['audit', auditId] });
      queryClient.invalidateQueries({ queryKey: ['auditReadiness', auditId] });
      setIsCreateProcedureModalOpen(false);
      setNewProcData({
        title: '',
        objective: '',
        test_steps: '',
        expected_result: '',
        assessment_method: 'Inspection',
        result: 'NOT_STARTED',
        organization_control_id: undefined,
      });
      setActionError(null);
    },
    onError: (err: any) => {
      setActionError(err.response?.data?.detail || err.message || 'Failed to create procedure');
    },
  });

  const updateProcMutation = useMutation({
    mutationFn: () =>
      auditService.updateProcedure(auditId, editingProcedure.id, {
        result: editingProcedure.result,
        actual_result: editingProcedure.actual_result,
        execution_notes: editingProcedure.execution_notes,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['audit', auditId] });
      queryClient.invalidateQueries({ queryKey: ['auditReadiness', auditId] });
      setIsEditProcedureModalOpen(false);
      setEditingProcedure(null);
      setActionError(null);
    },
    onError: (err: any) => {
      setActionError(err.response?.data?.detail || err.message || 'Failed to update procedure');
    },
  });

  const linkEvidenceMutation = useMutation({
    mutationFn: () =>
      auditService.linkEvidence(
        auditId,
        selectedProcedureId!,
        Number(selectedEvidenceId)
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['audit', auditId] });
      queryClient.invalidateQueries({ queryKey: ['auditReadiness', auditId] });
      setIsLinkEvidenceModalOpen(false);
      setSelectedEvidenceId('');
      setSelectedProcedureId(null);
      setActionError(null);
    },
    onError: (err: any) => {
      setActionError(err.response?.data?.detail || err.message || 'Failed to link evidence');
    },
  });

  const unlinkEvidenceMutation = useMutation({
    mutationFn: ({ procId, evId }: { procId: number; evId: number }) =>
      auditService.unlinkEvidence(auditId, procId, evId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['audit', auditId] });
      queryClient.invalidateQueries({ queryKey: ['auditReadiness', auditId] });
      setActionError(null);
    },
    onError: (err: any) => {
      setActionError(err.response?.data?.detail || err.message || 'Failed to unlink evidence');
    },
  });

  const linkFindingMutation = useMutation({
    mutationFn: () =>
      auditService.linkFinding(
        auditId,
        Number(selectedFindingId),
        findingSourceProcId ? Number(findingSourceProcId) : undefined
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['audit', auditId] });
      queryClient.invalidateQueries({ queryKey: ['auditReadiness', auditId] });
      setIsLinkFindingModalOpen(false);
      setSelectedFindingId('');
      setFindingSourceProcId('');
      setActionError(null);
    },
    onError: (err: any) => {
      setActionError(err.response?.data?.detail || err.message || 'Failed to link finding');
    },
  });

  const unlinkFindingMutation = useMutation({
    mutationFn: (findingId: number) =>
      auditService.unlinkFinding(auditId, findingId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['audit', auditId] });
      queryClient.invalidateQueries({ queryKey: ['auditReadiness', auditId] });
      setActionError(null);
    },
    onError: (err: any) => {
      setActionError(err.response?.data?.detail || err.message || 'Failed to unlink finding');
    },
  });

  const issueOpinionMutation = useMutation({
    mutationFn: () =>
      auditService.issueOpinion(
        auditId,
        opinionData.opinion,
        opinionData.opinion_notes
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['audit', auditId] });
      setIsIssueOpinionModalOpen(false);
      setActionError(null);
    },
    onError: (err: any) => {
      setActionError(err.response?.data?.detail || err.message || 'Failed to issue opinion');
    },
  });

  const closeAuditMutation = useMutation({
    mutationFn: () => auditService.closeAudit(auditId, closureNotes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['audit', auditId] });
      setIsCloseAuditModalOpen(false);
      setActionError(null);
    },
    onError: (err: any) => {
      setActionError(err.response?.data?.detail || err.message || 'Failed to close audit');
    },
  });

  if (isAuditLoading) {
    return (
      <div className="p-12 text-center text-slate-500">
        Loading audit workspace...
      </div>
    );
  }

  if (!audit) {
    return (
      <div className="p-12 text-center text-slate-500 space-y-4">
        <div>Audit engagement not found or you lack permission to view it.</div>
        <Link
          to="/audits"
          className="inline-flex items-center gap-1 text-sm text-indigo-400 hover:underline"
        >
          <ArrowLeft size={16} /> Return to Audit Catalog
        </Link>
      </div>
    );
  }

  const isClosed = audit.status === 'CLOSED';

  const getNextStatuses = (current: AuditStatus): AuditStatus[] => {
    switch (current) {
      case 'PLANNED':
        return ['INITIATED'];
      case 'INITIATED':
        return ['FIELDWORK', 'PLANNED'];
      case 'FIELDWORK':
        return ['REVIEW', 'INITIATED'];
      case 'REVIEW':
        return ['REPORTING', 'FIELDWORK'];
      case 'REPORTING':
        return ['COMPLETED', 'REVIEW'];
      case 'COMPLETED':
        return [];
      case 'CLOSED':
      default:
        return [];
    }
  };

  const nextStatuses = getNextStatuses(audit.status);

  return (
    <div className="space-y-6">
      {/* Top Bar Navigation & Header */}
      <div className="flex flex-col gap-4">
        <Link
          to="/audits"
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors w-fit"
        >
          <ArrowLeft size={14} /> Back to Audits
        </Link>

        {actionError && (
          <div className="p-3 bg-rose-950/60 border border-rose-800 rounded-xl text-xs text-rose-300 flex items-center justify-between">
            <span>{actionError}</span>
            <button
              onClick={() => setActionError(null)}
              className="text-rose-400 hover:text-rose-200"
            >
              <X size={14} />
            </button>
          </div>
        )}

        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 bg-slate-900/90 p-5 rounded-2xl border border-slate-800">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-indigo-950 text-indigo-300 border border-indigo-800">
                {audit.audit_reference || `AUD-${audit.id.toString().padStart(4, '0')}`}
              </span>
              <span className="px-2 py-0.5 rounded text-xs font-semibold bg-slate-800 text-slate-300">
                {audit.audit_type}
              </span>
              {isClosed && (
                <span className="px-2 py-0.5 rounded text-xs font-semibold bg-slate-950 text-slate-400 border border-slate-800 flex items-center gap-1">
                  <Lock size={12} /> Closed
                </span>
              )}
            </div>
            <h1 className="text-xl font-bold text-slate-100">{audit.title}</h1>
            <p className="text-xs text-slate-400 max-w-3xl">{audit.objective}</p>
          </div>

          {/* Lifecycle & Actions Bar */}
          <div className="flex flex-wrap items-center gap-2">
            {!isClosed && nextStatuses.length > 0 && (
              <div className="flex items-center gap-1.5 bg-slate-950 p-1 rounded-lg border border-slate-800">
                <span className="text-[11px] font-semibold text-slate-500 uppercase px-2">
                  Transition:
                </span>
                {nextStatuses.map((s) => (
                  <button
                    key={s}
                    disabled={statusMutation.isPending}
                    onClick={() => statusMutation.mutate(s)}
                    className="px-2.5 py-1 bg-indigo-600/20 hover:bg-indigo-600/40 text-indigo-300 text-xs font-medium rounded transition-colors cursor-pointer disabled:opacity-50"
                  >
                    → {s}
                  </button>
                ))}
              </div>
            )}

            {/* Opinion Button */}
            {!isClosed &&
              ['REVIEW', 'REPORTING', 'COMPLETED'].includes(audit.status) && (
                <button
                  onClick={() => setIsIssueOpinionModalOpen(true)}
                  className="px-3 py-1.5 bg-purple-600 hover:bg-purple-500 text-white text-xs font-medium rounded-lg shadow-xs transition-colors flex items-center gap-1.5 cursor-pointer"
                >
                  <Award size={14} />
                  {audit.opinion === 'UNISSUED' ? 'Issue Opinion' : 'Update Opinion'}
                </button>
              )}

            {/* Close Audit Button */}
            {!isClosed && audit.status === 'COMPLETED' && (
              <button
                onClick={() => setIsCloseAuditModalOpen(true)}
                className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded-lg shadow-xs transition-colors flex items-center gap-1.5 cursor-pointer"
              >
                <Lock size={14} />
                Close Audit
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Readiness Banner Widget */}
      {readiness && (
        <div className="bg-gradient-to-r from-slate-900 via-indigo-950/30 to-slate-900 p-4 rounded-xl border border-indigo-900/40 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="h-12 w-12 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center font-bold text-lg text-indigo-300 font-mono">
              {Math.round(readiness.readiness_score)}%
            </div>
            <div>
              <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Deterministic Audit Readiness
              </div>
              <div className="text-sm font-bold text-slate-200 flex items-center gap-2 mt-0.5">
                <span>Band: {readiness.readiness_band.replace(/_/g, ' ')}</span>
                <span className="text-slate-600">•</span>
                <span className="text-xs text-slate-400 font-normal">
                  {readiness.procedures_passed} of {readiness.procedures_total} procs passed
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3 text-xs">
            <div className="text-slate-400">
              <span className="font-semibold text-slate-200">
                {readiness.controls_with_evidence}/{readiness.controls_in_scope}
              </span>{' '}
              Controls with Evidence
            </div>
            <span className="text-slate-700">|</span>
            <div className="text-slate-400">
              <span className="font-semibold text-rose-400">
                {readiness.findings_critical + readiness.findings_high}
              </span>{' '}
              Critical/High Gaps
            </div>
            <button
              onClick={() => setActiveTab('readiness')}
              className="px-2.5 py-1 bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-300 rounded font-medium transition-colors cursor-pointer"
            >
              View Gap Analysis
            </button>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-slate-800 space-x-2">
        {[
          { id: 'overview', label: 'Overview', icon: FileText },
          {
            id: 'scope',
            label: `Scope Controls (${audit.scope_controls?.length ?? 0})`,
            icon: Layers,
          },
          {
            id: 'procedures',
            label: `Procedures & Tests (${audit.procedures?.length ?? 0})`,
            icon: Activity,
          },
          {
            id: 'findings',
            label: `Findings (${audit.finding_links?.length ?? 0})`,
            icon: AlertTriangle,
          },
          { id: 'readiness', label: 'Assurance Readiness', icon: ShieldCheck },
          { id: 'governance', label: 'Opinion & Closure', icon: Award },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-4 py-3 text-xs font-semibold border-b-2 transition-colors cursor-pointer ${
                isActive
                  ? 'border-indigo-500 text-indigo-400 bg-slate-900/40'
                  : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
              }`}
            >
              <Icon size={14} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      <div className="space-y-6">
        {/* TAB 1: OVERVIEW */}
        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-slate-900/80 p-5 rounded-xl border border-slate-800 space-y-4">
              <h3 className="text-sm font-semibold text-slate-200 border-b border-slate-800 pb-2">
                Audit Information
              </h3>
              <dl className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <dt className="text-slate-500">Audit Reference</dt>
                  <dd className="text-slate-300 font-mono font-medium mt-0.5">
                    {audit.audit_reference || 'N/A'}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Audit Type</dt>
                  <dd className="text-slate-300 font-medium mt-0.5">{audit.audit_type}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Lifecycle Status</dt>
                  <dd className="text-slate-300 font-medium mt-0.5">{audit.status}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Formal Opinion</dt>
                  <dd className="text-slate-300 font-medium mt-0.5">{audit.opinion}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Planned Dates</dt>
                  <dd className="text-slate-300 mt-0.5 font-mono">
                    {audit.planned_start_date || '—'} to {audit.planned_end_date || '—'}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Actual Dates</dt>
                  <dd className="text-slate-300 mt-0.5 font-mono">
                    {audit.actual_start_date || '—'} to {audit.actual_end_date || '—'}
                  </dd>
                </div>
              </dl>
            </div>

            <div className="bg-slate-900/80 p-5 rounded-xl border border-slate-800 space-y-4">
              <h3 className="text-sm font-semibold text-slate-200 border-b border-slate-800 pb-2">
                Scope & Methodology
              </h3>
              <div className="space-y-3 text-xs">
                <div>
                  <div className="text-slate-500 font-medium mb-1">Scope Description:</div>
                  <div className="p-2.5 rounded bg-slate-950 border border-slate-800 text-slate-300">
                    {audit.scope_description || 'No specific scope description provided.'}
                  </div>
                </div>
                <div>
                  <div className="text-slate-500 font-medium mb-1">Methodology:</div>
                  <div className="p-2.5 rounded bg-slate-950 border border-slate-800 text-slate-300">
                    {audit.methodology || 'Inspection, testing, and evidence verification.'}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: SCOPE CONTROLS */}
        {activeTab === 'scope' && (
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <div>
                <h3 className="text-sm font-bold text-slate-200">Organization Controls in Scope</h3>
                <p className="text-xs text-slate-400">
                  Controls subject to verification and procedure testing under this audit.
                </p>
              </div>
              {!isClosed && (
                <button
                  onClick={() => setIsAddScopeModalOpen(true)}
                  className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg flex items-center gap-1.5 transition-colors cursor-pointer"
                >
                  <Plus size={14} /> Add Control to Scope
                </button>
              )}
            </div>

            <div className="bg-slate-900/80 rounded-xl border border-slate-800 overflow-hidden">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-950 text-slate-400 font-semibold uppercase border-b border-slate-800">
                  <tr>
                    <th className="px-4 py-3">Control ID</th>
                    <th className="px-4 py-3">Scope Notes</th>
                    <th className="px-4 py-3">Date Added</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {audit.scope_controls?.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="px-4 py-8 text-center text-slate-500">
                        No controls added to audit scope yet.
                      </td>
                    </tr>
                  ) : (
                    audit.scope_controls?.map((sc: any) => (
                      <tr key={sc.id} className="hover:bg-slate-800/40">
                        <td className="px-4 py-3 font-mono font-medium text-slate-200">
                          Control #{sc.organization_control_id}
                        </td>
                        <td className="px-4 py-3 text-slate-400">
                          {sc.scope_notes || '—'}
                        </td>
                        <td className="px-4 py-3 font-mono text-slate-500">
                          {sc.created_at ? new Date(sc.created_at).toLocaleDateString() : '—'}
                        </td>
                        <td className="px-4 py-3 text-right">
                          {!isClosed && (
                            <button
                              onClick={() =>
                                removeScopeMutation.mutate(sc.organization_control_id)
                              }
                              className="text-rose-400 hover:text-rose-300 transition-colors p-1"
                              title="Remove from Scope"
                            >
                              <Trash2 size={14} />
                            </button>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 3: PROCEDURES */}
        {activeTab === 'procedures' && (
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <div>
                <h3 className="text-sm font-bold text-slate-200">Audit Procedures & Test Steps</h3>
                <p className="text-xs text-slate-400">
                  Formal audit testing procedures executed to verify control design and operating effectiveness.
                </p>
              </div>
              {!isClosed && (
                <button
                  onClick={() => setIsCreateProcedureModalOpen(true)}
                  className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg flex items-center gap-1.5 transition-colors cursor-pointer"
                >
                  <Plus size={14} /> Create Procedure
                </button>
              )}
            </div>

            <div className="space-y-3">
              {audit.procedures?.length === 0 ? (
                <div className="p-8 text-center bg-slate-900/60 rounded-xl border border-slate-800 text-slate-500 text-xs">
                  No procedures created for this audit engagement.
                </div>
              ) : (
                audit.procedures?.map((proc: any) => (
                  <div
                    key={proc.id}
                    className="p-4 bg-slate-900/80 rounded-xl border border-slate-800 space-y-3"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div className="flex items-center gap-2.5">
                        <span className="font-mono text-xs font-bold text-slate-400">
                          PROC-{proc.id}
                        </span>
                        <h4 className="text-sm font-semibold text-slate-100">{proc.title}</h4>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                            proc.result === 'PASSED'
                              ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                              : proc.result === 'FAILED'
                              ? 'bg-rose-950 text-rose-300 border border-rose-800'
                              : proc.result === 'PARTIALLY_PASSED'
                              ? 'bg-amber-950 text-amber-300 border border-amber-800'
                              : 'bg-slate-800 text-slate-400'
                          }`}
                        >
                          {proc.result.replace(/_/g, ' ')}
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        {!isClosed && (
                          <>
                            <button
                              onClick={() => {
                                setEditingProcedure(proc);
                                setIsEditProcedureModalOpen(true);
                              }}
                              className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs rounded transition-colors"
                            >
                              Record Results
                            </button>
                            <button
                              onClick={() => {
                                setSelectedProcedureId(proc.id);
                                setIsLinkEvidenceModalOpen(true);
                              }}
                              className="px-2 py-1 bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-300 text-xs rounded flex items-center gap-1 transition-colors"
                            >
                              <LinkIcon size={12} /> Link Evidence
                            </button>
                          </>
                        )}
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                      <div>
                        <div className="text-slate-500 font-medium">Test Steps:</div>
                        <div className="text-slate-300 mt-0.5">{proc.test_steps || '—'}</div>
                      </div>
                      <div>
                        <div className="text-slate-500 font-medium">Expected Result:</div>
                        <div className="text-slate-300 mt-0.5">{proc.expected_result || '—'}</div>
                      </div>
                    </div>

                    {proc.actual_result && (
                      <div className="p-2.5 bg-slate-950 rounded border border-slate-800 text-xs">
                        <span className="text-slate-500 font-medium">Actual Result: </span>
                        <span className="text-slate-200">{proc.actual_result}</span>
                      </div>
                    )}

                    {/* Linked Evidence */}
                    <div className="pt-2 border-t border-slate-800/80 space-y-1.5">
                      <div className="flex items-center gap-2 text-xs text-slate-400">
                        <FileText size={12} className="text-indigo-400" />
                        <span>{proc.evidence_links?.length ?? proc.evidence_count ?? 0} Evidence Item(s) Linked</span>
                      </div>
                      {proc.evidence_links && proc.evidence_links.length > 0 && (
                        <div className="flex flex-wrap gap-2 pt-1">
                          {proc.evidence_links.map((el: any) => (
                            <span
                              key={el.id}
                              className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] bg-slate-950 border border-slate-800 text-slate-300"
                            >
                              <span>{el.evidence?.title || `Evidence #${el.evidence_id}`}</span>
                              {!isClosed && (
                                <button
                                  onClick={() =>
                                    unlinkEvidenceMutation.mutate({
                                      procId: proc.id,
                                      evId: el.evidence_id,
                                    })
                                  }
                                  className="text-slate-500 hover:text-rose-400"
                                >
                                  <X size={12} />
                                </button>
                              )}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* TAB 4: FINDINGS */}
        {activeTab === 'findings' && (
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <div>
                <h3 className="text-sm font-bold text-slate-200">Audit Findings</h3>
                <p className="text-xs text-slate-400">
                  Gaps, deficiencies, and non-conformities identified during this engagement.
                </p>
              </div>
              {!isClosed && (
                <button
                  onClick={() => setIsLinkFindingModalOpen(true)}
                  className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg flex items-center gap-1.5 transition-colors cursor-pointer"
                >
                  <Plus size={14} /> Link Existing Finding
                </button>
              )}
            </div>

            <div className="bg-slate-900/80 rounded-xl border border-slate-800 overflow-hidden">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-950 text-slate-400 font-semibold uppercase border-b border-slate-800">
                  <tr>
                    <th className="px-4 py-3">Finding Title</th>
                    <th className="px-4 py-3">Severity</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Link Notes</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {audit.finding_links?.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-4 py-8 text-center text-slate-500">
                        No findings linked to this audit engagement.
                      </td>
                    </tr>
                  ) : (
                    audit.finding_links?.map((fl: any) => (
                      <tr key={fl.id} className="hover:bg-slate-800/40">
                        <td className="px-4 py-3 font-medium text-slate-200">
                          {fl.finding?.title || `Finding #${fl.finding_id}`}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              fl.finding?.severity === 'CRITICAL'
                                ? 'bg-rose-950 text-rose-300'
                                : fl.finding?.severity === 'HIGH'
                                ? 'bg-amber-950 text-amber-300'
                                : 'bg-slate-800 text-slate-300'
                            }`}
                          >
                            {fl.finding?.severity || 'HIGH'}
                          </span>
                        </td>
                        <td className="px-4 py-3">{fl.finding?.status || 'OPEN'}</td>
                        <td className="px-4 py-3 text-slate-400">{fl.link_notes || '—'}</td>
                        <td className="px-4 py-3 text-right">
                          {!isClosed && (
                            <button
                              onClick={() => unlinkFindingMutation.mutate(fl.finding_id)}
                              className="text-rose-400 hover:text-rose-300 transition-colors p-1"
                              title="Unlink Finding"
                            >
                              <Unlink size={14} />
                            </button>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 5: READINESS */}
        {activeTab === 'readiness' && readiness && (
          <div className="space-y-6">
            <div className="bg-slate-900/80 p-6 rounded-2xl border border-slate-800 space-y-6">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-800 pb-4">
                <div>
                  <h3 className="text-base font-bold text-slate-100">
                    Deterministic Readiness Breakdown
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Server-calculated assurance score based on procedure completion, evidence coverage, and open finding penalties.
                  </p>
                </div>
                <div className="px-4 py-2 bg-indigo-950/80 border border-indigo-800/80 rounded-xl text-center">
                  <div className="text-[10px] uppercase font-semibold text-indigo-400">Score</div>
                  <div className="text-2xl font-black text-indigo-200 font-mono">
                    {readiness.readiness_score}%
                  </div>
                </div>
              </div>

              {/* Explainable Blockers */}
              <div className="space-y-2">
                <div className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                  <AlertCircle className="text-amber-400" size={14} />
                  Active Readiness Blockers ({readiness.readiness_blockers.length})
                </div>
                {readiness.readiness_blockers.length === 0 ? (
                  <div className="p-3 bg-emerald-950/40 border border-emerald-800/80 rounded-lg text-xs text-emerald-300 flex items-center gap-2">
                    <CheckCircle2 size={16} /> All readiness criteria satisfied! Engagement is ready for formal opinion and closure.
                  </div>
                ) : (
                  <div className="space-y-1.5">
                    {readiness.readiness_blockers.map((b: string, i: number) => (
                      <div
                        key={i}
                        className="p-2.5 bg-amber-950/30 border border-amber-800/50 rounded-lg text-xs text-amber-300 flex items-center gap-2"
                      >
                        <AlertTriangle size={14} className="shrink-0" />
                        <span>{b}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* TAB 6: GOVERNANCE, OPINION & CLOSURE */}
        {activeTab === 'governance' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-slate-900/80 p-5 rounded-xl border border-slate-800 space-y-4">
              <h3 className="text-sm font-semibold text-slate-200 border-b border-slate-800 pb-2 flex items-center gap-2">
                <Award className="text-purple-400" size={16} />
                Formal Audit Opinion
              </h3>
              <dl className="space-y-3 text-xs">
                <div>
                  <dt className="text-slate-500">Authoritative Opinion</dt>
                  <dd className="text-sm font-bold text-slate-100 mt-0.5">
                    {audit.opinion}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Issued By User ID</dt>
                  <dd className="text-slate-300 font-mono mt-0.5">
                    {audit.opinion_issued_by_id || 'Not yet issued'}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Issued Timestamp</dt>
                  <dd className="text-slate-300 font-mono mt-0.5">
                    {audit.opinion_issued_at
                      ? new Date(audit.opinion_issued_at).toLocaleString()
                      : '—'}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Opinion Notes & Rationale</dt>
                  <dd className="p-2.5 rounded bg-slate-950 border border-slate-800 text-slate-300 mt-1">
                    {audit.opinion_notes || 'No opinion notes recorded.'}
                  </dd>
                </div>
              </dl>
            </div>

            <div className="bg-slate-900/80 p-5 rounded-xl border border-slate-800 space-y-4">
              <h3 className="text-sm font-semibold text-slate-200 border-b border-slate-800 pb-2 flex items-center gap-2">
                <Lock className="text-emerald-400" size={16} />
                Engagement Closure Record
              </h3>
              <dl className="space-y-3 text-xs">
                <div>
                  <dt className="text-slate-500">Closed Status</dt>
                  <dd className="text-sm font-bold text-slate-100 mt-0.5">
                    {isClosed ? 'CLOSED (Immutable)' : 'ACTIVE (In Progress)'}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Closed By User ID</dt>
                  <dd className="text-slate-300 font-mono mt-0.5">
                    {audit.closed_by_id || '—'}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Closed Timestamp</dt>
                  <dd className="text-slate-300 font-mono mt-0.5">
                    {audit.closed_at
                      ? new Date(audit.closed_at).toLocaleString()
                      : '—'}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Closure Notes</dt>
                  <dd className="p-2.5 rounded bg-slate-950 border border-slate-800 text-slate-300 mt-1">
                    {audit.closure_notes || 'No closure notes.'}
                  </dd>
                </div>
              </dl>
            </div>
          </div>
        )}
      </div>

      {/* Modal: Add Scope Control */}
      {isAddScopeModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-xs">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-slate-100">Add Control to Audit Scope</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Select Control <span className="text-rose-400">*</span>
                </label>
                <select
                  value={selectedControlId}
                  onChange={(e) => setSelectedControlId(Number(e.target.value))}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200"
                >
                  <option value="">Choose a control...</option>
                  {allControls.map((c: any) => (
                    <option key={c.id} value={c.id}>
                      Control #{c.id} — Status: {c.status}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Scope Justification Notes
                </label>
                <textarea
                  rows={2}
                  value={scopeNotes}
                  onChange={(e) => setScopeNotes(e.target.value)}
                  placeholder="Optional scope notes..."
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setIsAddScopeModalOpen(false)}
                className="px-3 py-1.5 bg-slate-800 text-slate-300 text-xs rounded-lg"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={!selectedControlId || addScopeMutation.isPending}
                onClick={() => addScopeMutation.mutate()}
                className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-medium rounded-lg"
              >
                {addScopeMutation.isPending ? 'Adding...' : 'Add to Scope'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Create Procedure */}
      {isCreateProcedureModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-xs">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-slate-100">Create Audit Procedure</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Procedure Title <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Verify MFA Enforcement on Root Accounts"
                  value={newProcData.title}
                  onChange={(e) => setNewProcData({ ...newProcData, title: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Test Steps
                </label>
                <textarea
                  rows={2}
                  placeholder="Step-by-step test procedure..."
                  value={newProcData.test_steps}
                  onChange={(e) =>
                    setNewProcData({ ...newProcData, test_steps: e.target.value })
                  }
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Expected Result
                </label>
                <input
                  type="text"
                  placeholder="e.g. All root logins require FIDO2 MFA token"
                  value={newProcData.expected_result}
                  onChange={(e) =>
                    setNewProcData({ ...newProcData, expected_result: e.target.value })
                  }
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setIsCreateProcedureModalOpen(false)}
                className="px-3 py-1.5 bg-slate-800 text-slate-300 text-xs rounded-lg"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={!newProcData.title.trim() || createProcMutation.isPending}
                onClick={() => createProcMutation.mutate()}
                className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-medium rounded-lg"
              >
                {createProcMutation.isPending ? 'Creating...' : 'Create Procedure'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Edit Procedure Result */}
      {isEditProcedureModalOpen && editingProcedure && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-xs">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-slate-100">
              Record Results — {editingProcedure.title}
            </h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Test Result <span className="text-rose-400">*</span>
                </label>
                <select
                  value={editingProcedure.result}
                  onChange={(e) =>
                    setEditingProcedure({
                      ...editingProcedure,
                      result: e.target.value as ProcedureResult,
                    })
                  }
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200"
                >
                  <option value="NOT_STARTED">Not Started</option>
                  <option value="IN_PROGRESS">In Progress</option>
                  <option value="PASSED">Passed</option>
                  <option value="PARTIALLY_PASSED">Partially Passed</option>
                  <option value="FAILED">Failed</option>
                  <option value="NOT_APPLICABLE">Not Applicable</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Actual Result Observed
                </label>
                <textarea
                  rows={3}
                  value={editingProcedure.actual_result || ''}
                  onChange={(e) =>
                    setEditingProcedure({
                      ...editingProcedure,
                      actual_result: e.target.value,
                    })
                  }
                  placeholder="Record actual test evidence and observations..."
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setIsEditProcedureModalOpen(false)}
                className="px-3 py-1.5 bg-slate-800 text-slate-300 text-xs rounded-lg"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={updateProcMutation.isPending}
                onClick={() => updateProcMutation.mutate()}
                className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-medium rounded-lg"
              >
                {updateProcMutation.isPending ? 'Saving...' : 'Save Results'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Link Evidence */}
      {isLinkEvidenceModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-xs">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-slate-100">Link Existing Evidence</h3>
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Select Evidence Item <span className="text-rose-400">*</span>
              </label>
              <select
                value={selectedEvidenceId}
                onChange={(e) => setSelectedEvidenceId(Number(e.target.value))}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200"
              >
                <option value="">Choose an evidence item...</option>
                {allEvidence.map((ev: any) => (
                  <option key={ev.id} value={ev.id}>
                    #{ev.id} — {ev.title} ({ev.original_filename})
                  </option>
                ))}
              </select>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setIsLinkEvidenceModalOpen(false)}
                className="px-3 py-1.5 bg-slate-800 text-slate-300 text-xs rounded-lg"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={!selectedEvidenceId || linkEvidenceMutation.isPending}
                onClick={() => linkEvidenceMutation.mutate()}
                className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-medium rounded-lg"
              >
                {linkEvidenceMutation.isPending ? 'Linking...' : 'Link Evidence'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Link Finding */}
      {isLinkFindingModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-xs">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-slate-100">Link Finding to Audit</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Select Finding <span className="text-rose-400">*</span>
                </label>
                <select
                  value={selectedFindingId}
                  onChange={(e) => setSelectedFindingId(Number(e.target.value))}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200"
                >
                  <option value="">Choose a finding...</option>
                  {allFindings.map((f: any) => (
                    <option key={f.id} value={f.id}>
                      #{f.id} — {f.title} ({f.severity})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Source Procedure (Optional)
                </label>
                <select
                  value={findingSourceProcId}
                  onChange={(e) => setFindingSourceProcId(Number(e.target.value))}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200"
                >
                  <option value="">No specific procedure</option>
                  {audit.procedures?.map((p: any) => (
                    <option key={p.id} value={p.id}>
                      PROC-{p.id}: {p.title}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setIsLinkFindingModalOpen(false)}
                className="px-3 py-1.5 bg-slate-800 text-slate-300 text-xs rounded-lg"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={!selectedFindingId || linkFindingMutation.isPending}
                onClick={() => linkFindingMutation.mutate()}
                className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-medium rounded-lg"
              >
                {linkFindingMutation.isPending ? 'Linking...' : 'Link Finding'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Issue Opinion */}
      {isIssueOpinionModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-xs">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <Award className="text-purple-400" size={20} />
              Issue Authoritative Audit Opinion
            </h3>
            <p className="text-xs text-slate-400">
              Audit opinions are human-authorized and require separation of duties (the lead auditor cannot approve their own engagement).
            </p>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Opinion Type <span className="text-rose-400">*</span>
                </label>
                <select
                  value={opinionData.opinion}
                  onChange={(e) =>
                    setOpinionData({
                      ...opinionData,
                      opinion: e.target.value as AuditOpinion,
                    })
                  }
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200"
                >
                  <option value="UNQUALIFIED">Unqualified (Clean / Full Assurance)</option>
                  <option value="QUALIFIED">Qualified (Material Exception)</option>
                  <option value="ADVERSE">Adverse (Non-Compliant)</option>
                  <option value="DISCLAIMER">Disclaimer (Insufficient Evidence)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Opinion Notes & Governance Justification (min 10 chars)
                </label>
                <textarea
                  rows={3}
                  value={opinionData.opinion_notes}
                  onChange={(e) =>
                    setOpinionData({
                      ...opinionData,
                      opinion_notes: e.target.value,
                    })
                  }
                  placeholder="Detail the rationale, evidence basis, and scope limitations for this opinion..."
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setIsIssueOpinionModalOpen(false)}
                className="px-3 py-1.5 bg-slate-800 text-slate-300 text-xs rounded-lg"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={issueOpinionMutation.isPending}
                onClick={() => issueOpinionMutation.mutate()}
                className="px-3 py-1.5 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white text-xs font-medium rounded-lg"
              >
                {issueOpinionMutation.isPending ? 'Issuing...' : 'Issue Formal Opinion'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Close Audit */}
      {isCloseAuditModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-xs">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <Lock className="text-emerald-400" size={20} />
              Formally Close Audit Engagement
            </h3>
            <p className="text-xs text-slate-400">
              Closing an audit makes the record completely immutable. No further modifications, scope changes, or procedure edits will be permitted.
            </p>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Closure Notes & Executive Summary <span className="text-rose-400">* (min 5 chars)</span>
              </label>
              <textarea
                rows={3}
                required
                value={closureNotes}
                onChange={(e) => setClosureNotes(e.target.value)}
                placeholder="Final summary confirming completion and executive sign-off..."
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setIsCloseAuditModalOpen(false)}
                className="px-3 py-1.5 bg-slate-800 text-slate-300 text-xs rounded-lg"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={closureNotes.trim().length < 5 || closeAuditMutation.isPending}
                onClick={() => closeAuditMutation.mutate()}
                className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-medium rounded-lg"
              >
                {closeAuditMutation.isPending ? 'Closing...' : 'Confirm Closure'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
