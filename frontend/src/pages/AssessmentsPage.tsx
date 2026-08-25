import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  FileCheck2,
  Plus,
  Search,
  Filter,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  ChevronRight,
  FileText,
  User as UserIcon,
} from 'lucide-react';
import { assessmentService } from '../lib/assessmentService';
import { api } from '../lib/api';
import { useAuth } from '../context/AuthContext';
import type {
  AssessmentConclusion,
  AssessmentMethod,
  AssessmentStatus,
  OrganizationControl,
} from '../types';

export const AssessmentsPage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { hasRole } = useAuth();
  const canAssess = hasRole('ADMIN', 'GRC_ANALYST', 'SECURITY_ANALYST');

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [conclusionFilter, setConclusionFilter] = useState<string>('ALL');
  const [methodFilter, setMethodFilter] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState<string>('');

  // Modal
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newControlId, setNewControlId] = useState<number | ''>('');
  const [newMethod, setNewMethod] = useState<AssessmentMethod>('EXAMINATION');
  const [newScope, setNewScope] = useState('');
  const [newSummary, setNewSummary] = useState('');
  const [newLimitations, setNewLimitations] = useState('');
  const [formError, setFormError] = useState<string | null>(null);

  // Queries
  const { data: stats } = useQuery({
    queryKey: ['assessmentStats'],
    queryFn: () => assessmentService.getAssessmentStats(),
  });

  const { data: assessments = [], isLoading } = useQuery({
    queryKey: ['assessments', statusFilter, conclusionFilter, methodFilter],
    queryFn: () =>
      assessmentService.getAssessments({
        status: statusFilter !== 'ALL' ? (statusFilter as AssessmentStatus) : undefined,
        conclusion: conclusionFilter !== 'ALL' ? (conclusionFilter as AssessmentConclusion) : undefined,
      }),
  });

  const { data: controls = [] } = useQuery({
    queryKey: ['controlsList'],
    queryFn: async () => {
      const res = await api.get<OrganizationControl[]>('/api/v1/controls');
      return res.data;
    },
  });

  // Create Mutation
  const createMutation = useMutation({
    mutationFn: assessmentService.createAssessment,
    onSuccess: (newAss) => {
      queryClient.invalidateQueries({ queryKey: ['assessments'] });
      queryClient.invalidateQueries({ queryKey: ['assessmentStats'] });
      setShowCreateModal(false);
      resetForm();
      navigate(`/assessments/${newAss.id}`);
    },
    onError: (err: any) => {
      setFormError(err.response?.data?.detail || 'Failed to create assessment.');
    },
  });

  const resetForm = () => {
    setNewControlId('');
    setNewMethod('EXAMINATION');
    setNewScope('');
    setNewSummary('');
    setNewLimitations('');
    setFormError(null);
  };

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newControlId) {
      setFormError('Please select a control to assess.');
      return;
    }
    createMutation.mutate({
      organization_control_id: Number(newControlId),
      assessment_method: newMethod,
      assessment_scope: newScope || undefined,
      summary: newSummary || undefined,
      limitations: newLimitations || undefined,
    });
  };

  const filteredAssessments = assessments.filter((a) => {
    if (methodFilter !== 'ALL' && a.assessment_method !== methodFilter) return false;
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      const matchCtrl = a.control_identifier?.toLowerCase().includes(term);
      const matchTitle = a.control_title?.toLowerCase().includes(term);
      const matchSummary = a.summary?.toLowerCase().includes(term);
      if (!matchCtrl && !matchTitle && !matchSummary) return false;
    }
    return true;
  });

  const renderConclusionBadge = (conclusion: AssessmentConclusion) => {
    switch (conclusion) {
      case 'EFFECTIVE':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-950/80 text-emerald-300 border border-emerald-800/80">
            <CheckCircle2 className="w-3.5 h-3.5" /> Effective
          </span>
        );
      case 'PARTIALLY_EFFECTIVE':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-950/80 text-amber-300 border border-amber-800/80">
            <AlertTriangle className="w-3.5 h-3.5" /> Partially Effective
          </span>
        );
      case 'INEFFECTIVE':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-950/80 text-rose-300 border border-rose-800/80">
            <XCircle className="w-3.5 h-3.5" /> Ineffective
          </span>
        );
      case 'NOT_ASSESSED':
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-800 text-slate-400 border border-slate-700">
            <Clock className="w-3.5 h-3.5" /> Not Assessed
          </span>
        );
    }
  };

  const renderStatusBadge = (status: AssessmentStatus) => {
    switch (status) {
      case 'DRAFT':
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-800 text-slate-300 border border-slate-700">
            DRAFT
          </span>
        );
      case 'IN_PROGRESS':
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-blue-950 text-blue-300 border border-blue-800 animate-pulse">
            IN PROGRESS
          </span>
        );
      case 'COMPLETED':
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-950 text-emerald-300 border border-emerald-800">
            COMPLETED
          </span>
        );
      case 'SUPERSEDED':
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-900 text-slate-500 border border-slate-800 line-through">
            SUPERSEDED
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-indigo-400 mb-1">
            <FileCheck2 className="w-4 h-4" /> Phase 4 &bull; Assurance Workflow
          </div>
          <h1 className="text-2xl font-bold text-slate-100">Control Assessments</h1>
          <p className="text-sm text-slate-400">
            Authoritative human-in-the-loop control effectiveness evaluations linked to verified evidence.
          </p>
        </div>
        {canAssess && (
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors shadow-xs"
          >
            <Plus className="w-4 h-4" /> New Assessment
          </button>
        )}
      </div>

      {/* Metrics Banner */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
          <div className="bg-slate-900/90 border border-slate-800 p-3 rounded-lg">
            <div className="text-xs text-slate-400 font-medium">Total</div>
            <div className="text-xl font-bold text-slate-100 mt-0.5">{stats.total_assessments}</div>
          </div>
          <div className="bg-slate-900/90 border border-slate-800 p-3 rounded-lg">
            <div className="text-xs text-slate-400 font-medium">Draft</div>
            <div className="text-xl font-bold text-slate-300 mt-0.5">{stats.draft_count}</div>
          </div>
          <div className="bg-slate-900/90 border border-slate-800 p-3 rounded-lg">
            <div className="text-xs text-blue-400 font-medium">In Progress</div>
            <div className="text-xl font-bold text-blue-300 mt-0.5">{stats.in_progress_count}</div>
          </div>
          <div className="bg-slate-900/90 border border-slate-800 p-3 rounded-lg">
            <div className="text-xs text-emerald-400 font-medium">Completed</div>
            <div className="text-xl font-bold text-emerald-300 mt-0.5">{stats.completed_count}</div>
          </div>
          <div className="bg-slate-900/90 border border-slate-800 p-3 rounded-lg">
            <div className="text-xs text-emerald-400 font-medium">Effective</div>
            <div className="text-xl font-bold text-emerald-400 mt-0.5">{stats.effective_count}</div>
          </div>
          <div className="bg-slate-900/90 border border-slate-800 p-3 rounded-lg">
            <div className="text-xs text-amber-400 font-medium">Partial</div>
            <div className="text-xl font-bold text-amber-400 mt-0.5">{stats.partially_effective_count}</div>
          </div>
          <div className="bg-slate-900/90 border border-slate-800 p-3 rounded-lg">
            <div className="text-xs text-rose-400 font-medium">Ineffective</div>
            <div className="text-xl font-bold text-rose-400 mt-0.5">{stats.ineffective_count}</div>
          </div>
          <div className="bg-slate-900/90 border border-slate-800 p-3 rounded-lg">
            <div className="text-xs text-slate-500 font-medium">Superseded</div>
            <div className="text-xl font-bold text-slate-500 mt-0.5">{stats.superseded_count}</div>
          </div>
        </div>
      )}

      {/* Filter Bar */}
      <div className="flex flex-col md:flex-row gap-3 items-center justify-between bg-slate-900/60 p-4 rounded-xl border border-slate-800">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search control identifier, title..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
          />
        </div>

        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <span className="text-xs text-slate-400 font-medium">Filters:</span>
          </div>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 text-slate-300 text-xs rounded-lg px-3 py-2 focus:outline-hidden focus:border-indigo-500"
          >
            <option value="ALL">All Statuses</option>
            <option value="DRAFT">Draft</option>
            <option value="IN_PROGRESS">In Progress</option>
            <option value="COMPLETED">Completed</option>
            <option value="SUPERSEDED">Superseded</option>
          </select>

          <select
            value={conclusionFilter}
            onChange={(e) => setConclusionFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 text-slate-300 text-xs rounded-lg px-3 py-2 focus:outline-hidden focus:border-indigo-500"
          >
            <option value="ALL">All Conclusions</option>
            <option value="EFFECTIVE">Effective</option>
            <option value="PARTIALLY_EFFECTIVE">Partially Effective</option>
            <option value="INEFFECTIVE">Ineffective</option>
            <option value="NOT_ASSESSED">Not Assessed</option>
          </select>

          <select
            value={methodFilter}
            onChange={(e) => setMethodFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 text-slate-300 text-xs rounded-lg px-3 py-2 focus:outline-hidden focus:border-indigo-500"
          >
            <option value="ALL">All Methods</option>
            <option value="EXAMINATION">Examination</option>
            <option value="INTERVIEW">Interview</option>
            <option value="TESTING">Testing</option>
            <option value="AUTOMATED_VERIFICATION">Automated</option>
            <option value="COMBINED">Combined</option>
          </select>
        </div>
      </div>

      {/* Assessments Catalog */}
      {isLoading ? (
        <div className="text-center py-16 text-slate-400">Loading assessments...</div>
      ) : filteredAssessments.length === 0 ? (
        <div className="text-center py-16 bg-slate-900/30 rounded-xl border border-dashed border-slate-800">
          <FileCheck2 className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-300">No assessments found</h3>
          <p className="text-sm text-slate-500 mt-1 max-w-sm mx-auto">
            Create an assessment evaluation for an organization control to begin validating implementation effectiveness.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3">
          {filteredAssessments.map((ass) => (
            <div
              key={ass.id}
              onClick={() => navigate(`/assessments/${ass.id}`)}
              className="group bg-slate-900/80 hover:bg-slate-800/80 border border-slate-800 hover:border-slate-700 p-4 rounded-xl transition-all cursor-pointer flex flex-col md:flex-row md:items-center justify-between gap-4"
            >
              <div className="space-y-1.5 flex-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs font-bold text-indigo-400 bg-indigo-950/70 border border-indigo-800/60 px-2 py-0.5 rounded">
                    {ass.control_identifier || `Control #${ass.organization_control_id}`}
                  </span>
                  {renderStatusBadge(ass.status)}
                  {renderConclusionBadge(ass.conclusion)}
                  <span className="text-xs text-slate-400 font-mono bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                    {ass.assessment_method}
                  </span>
                </div>

                <h3 className="text-sm font-semibold text-slate-200 truncate group-hover:text-indigo-300 transition-colors">
                  {ass.control_title || 'Control Assessment'}
                </h3>

                {ass.summary && (
                  <p className="text-xs text-slate-400 line-clamp-1">
                    {ass.summary}
                  </p>
                )}

                <div className="flex items-center gap-4 text-xs text-slate-400 pt-1">
                  <span className="flex items-center gap-1">
                    <UserIcon className="w-3.5 h-3.5" />
                    {ass.assessor?.full_name || 'Unassigned'}
                  </span>
                  <span className="flex items-center gap-1">
                    <FileText className="w-3.5 h-3.5" />
                    {ass.evidence_count} evidence linked
                  </span>
                  <span className="flex items-center gap-1 text-rose-400/80">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    {ass.findings_count} findings
                  </span>
                  <span>Date: {ass.assessment_date}</span>
                </div>
              </div>

              <div className="flex items-center gap-2 self-end md:self-center shrink-0">
                <span className="text-xs text-indigo-400 font-medium group-hover:translate-x-1 transition-transform inline-flex items-center gap-1">
                  View Detail <ChevronRight className="w-4 h-4" />
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* New Assessment Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-xs">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                <Plus className="w-5 h-5 text-indigo-400" /> New Control Assessment
              </h3>
              <button
                onClick={() => {
                  setShowCreateModal(false);
                  resetForm();
                }}
                className="text-slate-400 hover:text-slate-200"
              >
                &times;
              </button>
            </div>

            {formError && (
              <div className="p-3 bg-rose-950/80 border border-rose-800 text-rose-200 text-xs rounded-lg">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreate} className="space-y-4 text-sm">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Select Control <span className="text-rose-400">*</span>
                </label>
                <select
                  value={newControlId}
                  onChange={(e) => setNewControlId(Number(e.target.value))}
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 text-sm focus:outline-hidden focus:border-indigo-500"
                >
                  <option value="">-- Select an organization control --</option>
                  {controls.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.subcategory?.identifier}: {c.subcategory?.title} ({c.status})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Assessment Method
                  </label>
                  <select
                    value={newMethod}
                    onChange={(e) => setNewMethod(e.target.value as AssessmentMethod)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 text-sm focus:outline-hidden focus:border-indigo-500"
                  >
                    <option value="EXAMINATION">Examination (Artifact inspection)</option>
                    <option value="INTERVIEW">Interview (Personnel interrogation)</option>
                    <option value="TESTING">Testing (Active technical tests)</option>
                    <option value="AUTOMATED_VERIFICATION">Automated Verification</option>
                    <option value="COMBINED">Combined Methodology</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Assessment Scope
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. AWS Production Workloads"
                    value={newScope}
                    onChange={(e) => setNewScope(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 text-sm focus:outline-hidden focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Initial Summary / Assessment Plan
                </label>
                <textarea
                  rows={3}
                  placeholder="Describe the assessment objectives and procedures to execute..."
                  value={newSummary}
                  onChange={(e) => setNewSummary(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-slate-200 text-sm focus:outline-hidden focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Known Limitations
                </label>
                <input
                  type="text"
                  placeholder="e.g. Excludes legacy staging infrastructure"
                  value={newLimitations}
                  onChange={(e) => setNewLimitations(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 text-sm focus:outline-hidden focus:border-indigo-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateModal(false);
                    resetForm();
                  }}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
                >
                  {createMutation.isPending ? 'Creating...' : 'Create Assessment (DRAFT)'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
export default AssessmentsPage;
