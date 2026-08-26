import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  CalendarCheck,
  Plus,
  Search,
  ArrowRight,
  ShieldCheck,
  Clock,
  FileCheck,
  AlertCircle,
  Award,
  CheckCircle2,
  Lock,
} from 'lucide-react';
import { auditService } from '../lib/auditService';
import type { AuditCreatePayload } from '../lib/auditService';
import type { AuditStatus, AuditType, AuditOpinion } from '../types';

export const AuditsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<AuditStatus | ''>('');
  const [typeFilter, setTypeFilter] = useState<AuditType | ''>('');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  // Form State
  const [formData, setFormData] = useState<AuditCreatePayload>({
    title: '',
    objective: '',
    audit_type: 'INTERNAL',
    audit_reference: '',
    scope_description: '',
    methodology: '',
    limitations: '',
    planned_start_date: '',
    planned_end_date: '',
  });
  const [formError, setFormError] = useState<string | null>(null);

  const { data: stats, isLoading: isStatsLoading } = useQuery({
    queryKey: ['auditStats'],
    queryFn: auditService.getStats,
  });

  const { data: audits = [], isLoading: isAuditsLoading } = useQuery({
    queryKey: ['audits', statusFilter, typeFilter, search],
    queryFn: () =>
      auditService.listAudits({
        status: statusFilter || undefined,
        audit_type: typeFilter || undefined,
        search: search || undefined,
      }),
  });

  const createMutation = useMutation({
    mutationFn: auditService.createAudit,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['audits'] });
      queryClient.invalidateQueries({ queryKey: ['auditStats'] });
      setIsCreateModalOpen(false);
      setFormError(null);
      setFormData({
        title: '',
        objective: '',
        audit_type: 'INTERNAL',
        audit_reference: '',
        scope_description: '',
        methodology: '',
        limitations: '',
        planned_start_date: '',
        planned_end_date: '',
      });
    },
    onError: (err: any) => {
      setFormError(
        err.response?.data?.detail || err.message || 'Failed to create audit engagement'
      );
    },
  });

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    if (!formData.title.trim()) {
      setFormError('Audit Title is required (minimum 3 characters).');
      return;
    }
    if (!formData.objective.trim() || formData.objective.trim().length < 10) {
      setFormError('Objective must be at least 10 characters long.');
      return;
    }
    createMutation.mutate({
      ...formData,
      planned_start_date: formData.planned_start_date || undefined,
      planned_end_date: formData.planned_end_date || undefined,
    });
  };

  const getStatusBadge = (status: AuditStatus) => {
    switch (status) {
      case 'PLANNED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-700">
            <Clock size={12} /> Planned
          </span>
        );
      case 'INITIATED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-950/80 text-blue-300 border border-blue-800/80">
            <FileCheck size={12} /> Initiated
          </span>
        );
      case 'FIELDWORK':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-950/80 text-indigo-300 border border-indigo-800/80">
            <ShieldCheck size={12} /> Fieldwork
          </span>
        );
      case 'REVIEW':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-950/80 text-amber-300 border border-amber-800/80">
            <AlertCircle size={12} /> Review
          </span>
        );
      case 'REPORTING':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-950/80 text-purple-300 border border-purple-800/80">
            <Award size={12} /> Reporting
          </span>
        );
      case 'COMPLETED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950/80 text-emerald-300 border border-emerald-800/80">
            <CheckCircle2 size={12} /> Completed
          </span>
        );
      case 'CLOSED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-900 text-slate-400 border border-slate-800">
            <Lock size={12} /> Closed
          </span>
        );
    }
  };

  const getOpinionBadge = (opinion: AuditOpinion) => {
    switch (opinion) {
      case 'UNQUALIFIED':
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-950 text-emerald-300 border border-emerald-800">
            Unqualified (Clean)
          </span>
        );
      case 'QUALIFIED':
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-950 text-amber-300 border border-amber-800">
            Qualified
          </span>
        );
      case 'ADVERSE':
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-rose-950 text-rose-300 border border-rose-800">
            Adverse
          </span>
        );
      case 'DISCLAIMER':
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-red-950 text-red-300 border border-red-800">
            Disclaimer
          </span>
        );
      case 'UNISSUED':
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-900 text-slate-500 border border-slate-800">
            Unissued
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100 flex items-center gap-2.5">
            <CalendarCheck className="text-indigo-400" size={28} />
            Audit Management & Assurance
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Plan, execute, and govern formal internal & external compliance audit engagements.
          </p>
        </div>
        <button
          onClick={() => setIsCreateModalOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg shadow-sm transition-colors cursor-pointer"
        >
          <Plus size={16} />
          New Audit Engagement
        </button>
      </div>

      {/* KPI Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 shadow-xs">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Audits</div>
          <div className="text-2xl font-bold text-slate-100 mt-1">
            {isStatsLoading ? '...' : stats?.total_audits ?? 0}
          </div>
        </div>
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 shadow-xs">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Planned</div>
          <div className="text-2xl font-bold text-slate-300 mt-1">
            {isStatsLoading ? '...' : stats?.planned_count ?? 0}
          </div>
        </div>
        <div className="p-4 rounded-xl bg-slate-900/80 border border-indigo-900/40 shadow-xs">
          <div className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">In Progress</div>
          <div className="text-2xl font-bold text-indigo-300 mt-1">
            {isStatsLoading ? '...' : stats?.in_progress_count ?? 0}
          </div>
        </div>
        <div className="p-4 rounded-xl bg-slate-900/80 border border-emerald-900/40 shadow-xs">
          <div className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">Completed</div>
          <div className="text-2xl font-bold text-emerald-300 mt-1">
            {isStatsLoading ? '...' : stats?.completed_count ?? 0}
          </div>
        </div>
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 shadow-xs">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Closed</div>
          <div className="text-2xl font-bold text-slate-400 mt-1">
            {isStatsLoading ? '...' : stats?.closed_count ?? 0}
          </div>
        </div>
        <div className="p-4 rounded-xl bg-slate-900/80 border border-amber-900/40 shadow-xs">
          <div className="text-xs font-semibold text-amber-400 uppercase tracking-wider">Open Findings</div>
          <div className="text-2xl font-bold text-amber-400 mt-1">
            {isStatsLoading ? '...' : stats?.open_findings_across_audits ?? 0}
          </div>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="flex flex-col sm:flex-row gap-3 bg-slate-900/60 p-3 rounded-xl border border-slate-800">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 text-slate-500" size={16} />
          <input
            type="text"
            placeholder="Search audits by title, reference or objective..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
          />
        </div>
        <div className="flex gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as AuditStatus | '')}
            className="bg-slate-950 border border-slate-800 text-slate-300 text-sm rounded-lg px-3 py-1.5 focus:outline-hidden focus:border-indigo-500"
          >
            <option value="">All Statuses</option>
            <option value="PLANNED">Planned</option>
            <option value="INITIATED">Initiated</option>
            <option value="FIELDWORK">Fieldwork</option>
            <option value="REVIEW">Review</option>
            <option value="REPORTING">Reporting</option>
            <option value="COMPLETED">Completed</option>
            <option value="CLOSED">Closed</option>
          </select>

          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value as AuditType | '')}
            className="bg-slate-950 border border-slate-800 text-slate-300 text-sm rounded-lg px-3 py-1.5 focus:outline-hidden focus:border-indigo-500"
          >
            <option value="">All Types</option>
            <option value="INTERNAL">Internal</option>
            <option value="EXTERNAL">External</option>
            <option value="REGULATORY">Regulatory</option>
            <option value="COMPLIANCE">Compliance</option>
            <option value="OPERATIONAL">Operational</option>
            <option value="TECHNICAL">Technical</option>
            <option value="THIRD_PARTY">Third Party</option>
          </select>
        </div>
      </div>

      {/* Audit List Table */}
      <div className="bg-slate-900/80 rounded-xl border border-slate-800 overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-950/80 text-xs uppercase font-semibold text-slate-400 border-b border-slate-800">
              <tr>
                <th className="px-6 py-3.5">Audit Title & Reference</th>
                <th className="px-6 py-3.5">Type</th>
                <th className="px-6 py-3.5">Lifecycle Status</th>
                <th className="px-6 py-3.5">Opinion</th>
                <th className="px-6 py-3.5 text-center">Scope / Procedures / Findings</th>
                <th className="px-6 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {isAuditsLoading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-slate-500">
                    Loading audit engagements...
                  </td>
                </tr>
              ) : audits.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-slate-500">
                    <CalendarCheck className="mx-auto mb-2 text-slate-600" size={32} />
                    No audit engagements found. Click "New Audit Engagement" to create one.
                  </td>
                </tr>
              ) : (
                audits.map((audit) => (
                  <tr key={audit.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="px-6 py-4">
                      <div className="font-medium text-slate-100">{audit.title}</div>
                      <div className="text-xs text-slate-400 font-mono mt-0.5">
                        {audit.audit_reference || `AUD-${audit.id.toString().padStart(4, '0')}`}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="px-2 py-0.5 rounded text-xs font-mono bg-slate-800 text-slate-300">
                        {audit.audit_type}
                      </span>
                    </td>
                    <td className="px-6 py-4">{getStatusBadge(audit.status)}</td>
                    <td className="px-6 py-4">{getOpinionBadge(audit.opinion)}</td>
                    <td className="px-6 py-4 text-center">
                      <div className="inline-flex items-center gap-2 text-xs font-mono">
                        <span className="text-indigo-400" title="Scope Controls">
                          {audit.scope_controls_count} controls
                        </span>
                        <span className="text-slate-600">•</span>
                        <span className="text-emerald-400" title="Procedures">
                          {audit.procedures_count} procs
                        </span>
                        <span className="text-slate-600">•</span>
                        <span
                          className={
                            audit.findings_count > 0 ? 'text-amber-400' : 'text-slate-500'
                          }
                          title="Findings"
                        >
                          {audit.findings_count} findings
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Link
                        to={`/audits/${audit.id}`}
                        className="inline-flex items-center gap-1 text-xs font-medium text-indigo-400 hover:text-indigo-300 transition-colors"
                      >
                        Open Workspace <ArrowRight size={14} />
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create Audit Modal */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-xs">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-6 max-h-[90vh] overflow-y-auto">
            <div>
              <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                <CalendarCheck className="text-indigo-400" size={24} />
                Create New Audit Engagement
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                Initialize an audit engagement. Lifecycle begins in PLANNED status.
              </p>
            </div>

            {formError && (
              <div className="p-3 bg-rose-950/50 border border-rose-800/80 rounded-lg text-xs text-rose-300">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreateSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Audit Title <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Q3 2026 NIST CSF 2.0 Compliance Audit"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-hidden focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Audit Type <span className="text-rose-400">*</span>
                  </label>
                  <select
                    value={formData.audit_type}
                    onChange={(e) =>
                      setFormData({ ...formData, audit_type: e.target.value as AuditType })
                    }
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-hidden focus:border-indigo-500"
                  >
                    <option value="INTERNAL">Internal</option>
                    <option value="EXTERNAL">External</option>
                    <option value="REGULATORY">Regulatory</option>
                    <option value="COMPLIANCE">Compliance</option>
                    <option value="OPERATIONAL">Operational</option>
                    <option value="TECHNICAL">Technical</option>
                    <option value="THIRD_PARTY">Third Party</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Audit Reference Code
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. AUD-2026-NIST-01"
                    value={formData.audit_reference}
                    onChange={(e) => setFormData({ ...formData, audit_reference: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-hidden focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Objective & Goals <span className="text-rose-400">* (min 10 chars)</span>
                </label>
                <textarea
                  required
                  rows={3}
                  placeholder="Define the primary objective and governance goals of this audit engagement..."
                  value={formData.objective}
                  onChange={(e) => setFormData({ ...formData, objective: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-hidden focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Planned Start Date
                  </label>
                  <input
                    type="date"
                    value={formData.planned_start_date}
                    onChange={(e) =>
                      setFormData({ ...formData, planned_start_date: e.target.value })
                    }
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-hidden focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Planned End Date
                  </label>
                  <input
                    type="date"
                    value={formData.planned_end_date}
                    onChange={(e) =>
                      setFormData({ ...formData, planned_end_date: e.target.value })
                    }
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-hidden focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Scope Summary / Boundary Notes
                </label>
                <textarea
                  rows={2}
                  placeholder="Optional scope boundaries, business units, systems or cloud regions in scope..."
                  value={formData.scope_description}
                  onChange={(e) =>
                    setFormData({ ...formData, scope_description: e.target.value })
                  }
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-hidden focus:border-indigo-500"
                />
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium rounded-lg transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors cursor-pointer"
                >
                  {createMutation.isPending ? 'Creating...' : 'Create Engagement'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
