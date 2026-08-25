import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  Plus,
  Search,
  Filter,
  ChevronRight,
  Clock,
  CheckCircle2,
  Calendar,
  User as UserIcon,
  Flame,
  FileText,
  BadgeAlert,
} from 'lucide-react';
import { findingService } from '../lib/findingService';
import { api } from '../lib/api';
import { useAuth } from '../context/AuthContext';
import type {
  FindingSeverity,
  FindingStatus,
  FindingType,
  OrganizationControl,
} from '../types';

export const FindingsPage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { hasRole } = useAuth();
  const canManageFindings = hasRole('ADMIN', 'GRC_ANALYST', 'SECURITY_ANALYST');

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [riskBandFilter, setRiskBandFilter] = useState<string>('ALL');
  const [findingTypeFilter, setFindingTypeFilter] = useState<string>('ALL');
  const [overdueOnly, setOverdueOnly] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  // Modal
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newControlId, setNewControlId] = useState<number | ''>('');
  const [newTitle, setNewTitle] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newType, setNewType] = useState<FindingType>('CONTROL_GAP');
  const [newSeverity, setNewSeverity] = useState<FindingSeverity>('MEDIUM');
  const [newImpact, setNewImpact] = useState(3);
  const [newLikelihood, setNewLikelihood] = useState(3);
  const [newRecommendation, setNewRecommendation] = useState('');
  const [newRootCause, setNewRootCause] = useState('');
  const [newDueDate, setNewDueDate] = useState('');
  const [newPlan, setNewPlan] = useState('');
  const [formError, setFormError] = useState<string | null>(null);

  // Queries
  const { data: stats } = useQuery({
    queryKey: ['findingStats'],
    queryFn: () => findingService.getFindingStats(),
  });

  const { data: findings = [], isLoading } = useQuery({
    queryKey: ['findings', statusFilter, severityFilter, riskBandFilter, findingTypeFilter, overdueOnly],
    queryFn: () =>
      findingService.getFindings({
        status: statusFilter !== 'ALL' ? (statusFilter as FindingStatus) : undefined,
        severity: severityFilter !== 'ALL' ? (severityFilter as FindingSeverity) : undefined,
        risk_band: riskBandFilter !== 'ALL' ? riskBandFilter : undefined,
        finding_type: findingTypeFilter !== 'ALL' ? (findingTypeFilter as FindingType) : undefined,
        overdue_only: overdueOnly,
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
    mutationFn: findingService.createFinding,
    onSuccess: (newFinding) => {
      queryClient.invalidateQueries({ queryKey: ['findings'] });
      queryClient.invalidateQueries({ queryKey: ['findingStats'] });
      setShowCreateModal(false);
      resetForm();
      navigate(`/findings/${newFinding.id}`);
    },
    onError: (err: any) => {
      setFormError(err.response?.data?.detail || 'Failed to create finding.');
    },
  });

  const resetForm = () => {
    setNewControlId('');
    setNewTitle('');
    setNewDesc('');
    setNewType('CONTROL_GAP');
    setNewSeverity('MEDIUM');
    setNewImpact(3);
    setNewLikelihood(3);
    setNewRecommendation('');
    setNewRootCause('');
    setNewDueDate('');
    setNewPlan('');
    setFormError(null);
  };

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newControlId) {
      setFormError('Please select an organization control.');
      return;
    }
    createMutation.mutate({
      organization_control_id: Number(newControlId),
      title: newTitle,
      description: newDesc,
      finding_type: newType,
      severity: newSeverity,
      impact: newImpact,
      likelihood: newLikelihood,
      recommendation: newRecommendation,
      root_cause: newRootCause || undefined,
      due_date: newDueDate || undefined,
      remediation_plan: newPlan || undefined,
    });
  };

  const filteredFindings = findings.filter((f) => {
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      const matchTitle = f.title.toLowerCase().includes(term);
      const matchDesc = f.description.toLowerCase().includes(term);
      const matchCtrl = f.control_identifier?.toLowerCase().includes(term);
      if (!matchTitle && !matchDesc && !matchCtrl) return false;
    }
    return true;
  });

  const renderSeverityBadge = (severity: FindingSeverity) => {
    switch (severity) {
      case 'CRITICAL':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-rose-950 text-rose-300 border border-rose-800">
            <Flame className="w-3 h-3 text-rose-400" /> CRITICAL
          </span>
        );
      case 'HIGH':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-amber-950 text-amber-300 border border-amber-800">
            <AlertTriangle className="w-3 h-3 text-amber-400" /> HIGH
          </span>
        );
      case 'MEDIUM':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-yellow-950/80 text-yellow-300 border border-yellow-800">
            MEDIUM
          </span>
        );
      case 'LOW':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-slate-800 text-slate-300 border border-slate-700">
            LOW
          </span>
        );
      case 'INFORMATIONAL':
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-blue-950/80 text-blue-300 border border-blue-800">
            INFO
          </span>
        );
    }
  };

  const renderRiskScoreBadge = (score: number, band: string) => {
    let colorClasses = 'bg-slate-800 text-slate-300 border-slate-700';
    if (band === 'CRITICAL') colorClasses = 'bg-rose-950/90 text-rose-300 border-rose-800';
    else if (band === 'HIGH') colorClasses = 'bg-amber-950/90 text-amber-300 border-amber-800';
    else if (band === 'MODERATE') colorClasses = 'bg-yellow-950/80 text-yellow-300 border-yellow-800';
    else if (band === 'LOW') colorClasses = 'bg-emerald-950/80 text-emerald-300 border-emerald-800';

    return (
      <span className={`inline-flex items-center gap-1 font-mono text-[11px] font-bold px-2 py-0.5 rounded border ${colorClasses}`}>
        {score} / 25 &bull; {band}
      </span>
    );
  };

  const renderOverdueBadge = (overdueStatus: string) => {
    switch (overdueStatus) {
      case 'OVERDUE':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-rose-950 text-rose-300 border border-rose-700 animate-pulse">
            <BadgeAlert className="w-3 h-3 text-rose-400" /> OVERDUE
          </span>
        );
      case 'DUE_SOON':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-950 text-amber-300 border border-amber-800">
            <Clock className="w-3 h-3 text-amber-400" /> DUE SOON (&le;7d)
          </span>
        );
      case 'ON_TRACK':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium bg-slate-900 text-emerald-400 border border-emerald-900/50">
            ON TRACK
          </span>
        );
      case 'COMPLETED':
      default:
        return null;
    }
  };

  const renderStatusPill = (status: FindingStatus) => {
    switch (status) {
      case 'OPEN':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-950 text-rose-300 border border-rose-800">OPEN</span>;
      case 'IN_REMEDIATION':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-950 text-blue-300 border border-blue-800">IN REMEDIATION</span>;
      case 'PENDING_VALIDATION':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-950 text-amber-300 border border-amber-800 animate-pulse">PENDING VALIDATION</span>;
      case 'RESOLVED':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-300 border border-emerald-800">RESOLVED</span>;
      case 'ACCEPTED_RISK':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-950 text-purple-300 border border-purple-800">RISK ACCEPTED</span>;
      case 'CLOSED':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-900 text-slate-500 border border-slate-800">CLOSED</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-rose-400 mb-1">
            <AlertTriangle className="w-4 h-4" /> Phase 4 &bull; Risk &amp; Remediation Register
          </div>
          <h1 className="text-2xl font-bold text-slate-100">Findings &amp; Remediation</h1>
          <p className="text-sm text-slate-400">
            Enterprise vulnerability &amp; compliance gap management with deterministic risk scoring and validation workflows.
          </p>
        </div>
        {canManageFindings && (
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-sm font-medium transition-colors shadow-xs"
          >
            <Plus className="w-4 h-4" /> Create Finding
          </button>
        )}
      </div>

      {/* Metrics Banner */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
          <div className="bg-slate-900/90 border border-slate-800 p-3 rounded-lg">
            <div className="text-xs text-slate-400 font-medium">Total Findings</div>
            <div className="text-xl font-bold text-slate-100 mt-0.5">{stats.total_findings}</div>
          </div>
          <div className="bg-slate-900/90 border border-slate-800 p-3 rounded-lg">
            <div className="text-xs text-rose-400 font-medium">Open</div>
            <div className="text-xl font-bold text-rose-400 mt-0.5">{stats.open_count}</div>
          </div>
          <div className="bg-slate-900/90 border border-slate-800 p-3 rounded-lg">
            <div className="text-xs text-blue-400 font-medium">In Remediation</div>
            <div className="text-xl font-bold text-blue-400 mt-0.5">{stats.in_remediation_count}</div>
          </div>
          <div className="bg-slate-900/90 border border-slate-800 p-3 rounded-lg">
            <div className="text-xs text-amber-400 font-medium">Pending Validation</div>
            <div className="text-xl font-bold text-amber-400 mt-0.5">{stats.pending_validation_count}</div>
          </div>
          <div className="bg-slate-900/90 border border-slate-800 p-3 rounded-lg">
            <div className="text-xs text-rose-500 font-medium">Critical / High</div>
            <div className="text-xl font-bold text-rose-400 mt-0.5">
              {stats.critical_count + stats.high_count}
            </div>
          </div>
          <div className="bg-slate-900/90 border border-slate-800 p-3 rounded-lg">
            <div className="text-xs text-rose-400 font-medium">Overdue</div>
            <div className={`text-xl font-bold mt-0.5 ${stats.overdue_count > 0 ? 'text-rose-400 animate-pulse' : 'text-slate-400'}`}>
              {stats.overdue_count}
            </div>
          </div>
          <div className="bg-slate-900/90 border border-slate-800 p-3 rounded-lg">
            <div className="text-xs text-purple-400 font-medium">Risk Accepted</div>
            <div className="text-xl font-bold text-purple-400 mt-0.5">{stats.accepted_risk_count}</div>
          </div>
          <div className="bg-slate-900/90 border border-slate-800 p-3 rounded-lg">
            <div className="text-xs text-emerald-400 font-medium">Resolved</div>
            <div className="text-xl font-bold text-emerald-400 mt-0.5">{stats.resolved_count}</div>
          </div>
        </div>
      )}

      {/* Filter Bar */}
      <div className="flex flex-col md:flex-row gap-3 items-center justify-between bg-slate-900/60 p-4 rounded-xl border border-slate-800">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search finding title, control, desc..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-hidden focus:border-rose-500"
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
            className="bg-slate-950 border border-slate-800 text-slate-300 text-xs rounded-lg px-3 py-2 focus:outline-hidden"
          >
            <option value="ALL">All Statuses</option>
            <option value="OPEN">Open</option>
            <option value="IN_REMEDIATION">In Remediation</option>
            <option value="PENDING_VALIDATION">Pending Validation</option>
            <option value="RESOLVED">Resolved</option>
            <option value="ACCEPTED_RISK">Risk Accepted</option>
            <option value="CLOSED">Closed</option>
          </select>

          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 text-slate-300 text-xs rounded-lg px-3 py-2 focus:outline-hidden"
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
            <option value="INFORMATIONAL">Informational</option>
          </select>

          <select
            value={riskBandFilter}
            onChange={(e) => setRiskBandFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 text-slate-300 text-xs rounded-lg px-3 py-2 focus:outline-hidden"
          >
            <option value="ALL">All Risk Bands</option>
            <option value="CRITICAL">Critical Band (17-25)</option>
            <option value="HIGH">High Band (10-16)</option>
            <option value="MODERATE">Moderate Band (5-9)</option>
            <option value="LOW">Low Band (1-4)</option>
          </select>

          <select
            value={findingTypeFilter}
            onChange={(e) => setFindingTypeFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 text-slate-300 text-xs rounded-lg px-3 py-2 focus:outline-hidden"
          >
            <option value="ALL">All Types</option>
            <option value="CONTROL_GAP">Control Gap</option>
            <option value="EVIDENCE_GAP">Evidence Gap</option>
            <option value="POLICY_GAP">Policy Gap</option>
            <option value="PROCESS_GAP">Process Gap</option>
            <option value="TECHNICAL_GAP">Technical Gap</option>
            <option value="OTHER">Other</option>
          </select>

          <label className="flex items-center gap-2 cursor-pointer text-xs text-rose-300 font-semibold px-2 py-1 bg-rose-950/40 border border-rose-900/60 rounded-lg">
            <input
              type="checkbox"
              checked={overdueOnly}
              onChange={(e) => setOverdueOnly(e.target.checked)}
              className="rounded bg-slate-900 border-slate-700 text-rose-600 focus:ring-rose-500"
            />
            Overdue Only
          </label>
        </div>
      </div>

      {/* Findings Catalog */}
      {isLoading ? (
        <div className="text-center py-16 text-slate-400">Loading findings...</div>
      ) : filteredFindings.length === 0 ? (
        <div className="text-center py-16 bg-slate-900/30 rounded-xl border border-dashed border-slate-800">
          <CheckCircle2 className="w-12 h-12 text-emerald-500/80 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-300">No deficiency findings match your filters</h3>
          <p className="text-sm text-slate-500 mt-1 max-w-sm mx-auto">
            All controls are operating within acceptable risk thresholds.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3">
          {filteredFindings.map((finding) => (
            <div
              key={finding.id}
              onClick={() => navigate(`/findings/${finding.id}`)}
              className="group bg-slate-900/80 hover:bg-slate-800/80 border border-slate-800 hover:border-slate-700 p-4 rounded-xl transition-all cursor-pointer flex flex-col md:flex-row md:items-center justify-between gap-4"
            >
              <div className="space-y-1.5 flex-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs font-bold text-indigo-400 bg-indigo-950/70 border border-indigo-800/60 px-2 py-0.5 rounded">
                    {finding.control_identifier || `Control #${finding.organization_control_id}`}
                  </span>
                  {renderSeverityBadge(finding.severity)}
                  {renderRiskScoreBadge(finding.risk_score, finding.risk_band)}
                  {renderStatusPill(finding.status)}
                  {renderOverdueBadge(finding.overdue_status)}
                </div>

                <h3 className="text-sm font-semibold text-slate-200 truncate group-hover:text-rose-300 transition-colors">
                  {finding.title}
                </h3>

                <p className="text-xs text-slate-400 line-clamp-1">
                  {finding.recommendation}
                </p>

                <div className="flex items-center gap-4 text-xs text-slate-500 pt-1">
                  <span className="flex items-center gap-1">
                    <UserIcon className="w-3.5 h-3.5 text-slate-400" />
                    {finding.owner?.full_name || 'Unassigned'}
                  </span>
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5 text-slate-400" />
                    Due: {finding.due_date || 'None'}
                  </span>
                  <span className="flex items-center gap-1">
                    <FileText className="w-3.5 h-3.5 text-slate-400" />
                    {finding.evidence_count} evidence
                  </span>
                  <span className="font-mono text-[11px]">
                    Type: {finding.finding_type}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2 self-end md:self-center shrink-0">
                <span className="text-xs text-rose-400 font-medium group-hover:translate-x-1 transition-transform inline-flex items-center gap-1">
                  View Remediation <ChevronRight className="w-4 h-4" />
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Finding Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-xs">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-xl p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                <Plus className="w-5 h-5 text-rose-400" /> Create Deficiency Finding
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
                  Organization Control <span className="text-rose-400">*</span>
                </label>
                <select
                  value={newControlId}
                  onChange={(e) => setNewControlId(Number(e.target.value))}
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 text-sm focus:outline-hidden focus:border-rose-500"
                >
                  <option value="">-- Select an organization control --</option>
                  {controls.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.subcategory?.identifier}: {c.subcategory?.title}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Finding Title <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Unauthenticated access to database backup files"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 text-sm focus:outline-hidden focus:border-rose-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Finding Type</label>
                  <select
                    value={newType}
                    onChange={(e) => setNewType(e.target.value as FindingType)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 text-sm focus:outline-hidden"
                  >
                    <option value="CONTROL_GAP">Control Gap</option>
                    <option value="EVIDENCE_GAP">Evidence Gap</option>
                    <option value="POLICY_GAP">Policy Gap</option>
                    <option value="PROCESS_GAP">Process Gap</option>
                    <option value="TECHNICAL_GAP">Technical Gap</option>
                    <option value="OTHER">Other</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Severity</label>
                  <select
                    value={newSeverity}
                    onChange={(e) => setNewSeverity(e.target.value as FindingSeverity)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 text-sm focus:outline-hidden"
                  >
                    <option value="CRITICAL">Critical</option>
                    <option value="HIGH">High</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="LOW">Low</option>
                    <option value="INFORMATIONAL">Informational</option>
                  </select>
                </div>
              </div>

              {/* 5x5 Deterministic Risk Scoring Preview */}
              <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl space-y-2">
                <div className="text-xs font-semibold text-slate-300">Deterministic Risk Scoring (5x5 Matrix)</div>
                <div className="grid grid-cols-3 gap-3 items-center">
                  <div>
                    <label className="block text-[10px] text-slate-400 font-medium">Impact (1-5)</label>
                    <input
                      type="number"
                      min={1}
                      max={5}
                      value={newImpact}
                      onChange={(e) => setNewImpact(Number(e.target.value))}
                      className="w-full bg-slate-900 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] text-slate-400 font-medium">Likelihood (1-5)</label>
                    <input
                      type="number"
                      min={1}
                      max={5}
                      value={newLikelihood}
                      onChange={(e) => setNewLikelihood(Number(e.target.value))}
                      className="w-full bg-slate-900 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 text-sm"
                    />
                  </div>
                  <div className="text-right">
                    <div className="text-[10px] text-slate-500">Calculated Score</div>
                    <div className="text-base font-bold text-rose-400 font-mono">
                      {newImpact * newLikelihood} / 25
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Description <span className="text-rose-400">*</span>
                </label>
                <textarea
                  rows={2}
                  required
                  placeholder="Detailed breakdown of how the gap was identified..."
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200 text-sm focus:outline-hidden"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Remediation Recommendation <span className="text-rose-400">*</span>
                </label>
                <textarea
                  rows={2}
                  required
                  placeholder="Specific actions required to close this deficiency..."
                  value={newRecommendation}
                  onChange={(e) => setNewRecommendation(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200 text-sm focus:outline-hidden"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Root Cause</label>
                  <input
                    type="text"
                    placeholder="e.g. Terraform pipeline drift"
                    value={newRootCause}
                    onChange={(e) => setNewRootCause(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 text-sm focus:outline-hidden"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Remediation Due Date</label>
                  <input
                    type="date"
                    value={newDueDate}
                    onChange={(e) => setNewDueDate(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 text-sm focus:outline-hidden"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateModal(false);
                    resetForm();
                  }}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold rounded-lg disabled:opacity-50"
                >
                  {createMutation.isPending ? 'Saving...' : 'Create Finding (OPEN)'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
export default FindingsPage;
