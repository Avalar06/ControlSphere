import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Gauge,
  Plus,
  Search,
  ShieldAlert,
  XCircle,
  FileText,
  TrendingUp,
} from 'lucide-react';
import { kriService } from '../lib/kriService';
import type {
  KeyRiskIndicator,
  KeyRiskIndicatorCreate,
  KriObservationCreate,
} from '../types/kri';

export const KriPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'overview' | 'indicators' | 'appetite' | 'breaches'>('overview');
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');

  // Modals
  const [isCreateKriOpen, setIsCreateKriOpen] = useState(false);
  const [isObserveOpen, setIsObserveOpen] = useState(false);
  const [selectedKri, setSelectedKri] = useState<KeyRiskIndicator | null>(null);
  const [isApproveAppetiteOpen, setIsApproveAppetiteOpen] = useState(false);
  const [selectedAppetiteId, setSelectedAppetiteId] = useState<number | null>(null);
  const [approvalJustification, setApprovalJustification] = useState('');
  const [isCloseBreachOpen, setIsCloseBreachOpen] = useState(false);
  const [selectedBreachId, setSelectedBreachId] = useState<number | null>(null);
  const [closureNotes, setClosureNotes] = useState('');

  // Form states
  const [newKri, setNewKri] = useState<KeyRiskIndicatorCreate>({
    kri_code: '',
    title: '',
    description: '',
    risk_category: 'CYBERSECURITY',
    unit_of_measure: 'COUNT',
    direction: 'LOWER_IS_BETTER',
    frequency: 'DAILY',
    source_type: 'MANUAL',
    initial_threshold: {
      target_value: 0,
      warning_threshold: 10,
      critical_threshold: 25,
      rationale: 'Initial baseline threshold',
    },
  });

  const [newObservation, setNewObservation] = useState<KriObservationCreate>({
    observed_value: 0,
    unit: 'COUNT',
    observed_at: new Date().toISOString(),
    source_type: 'MANUAL',
    source_system: 'Internal Audit Fieldwork',
  });

  // Queries
  const { data: overview, isLoading: isOverviewLoading } = useQuery({
    queryKey: ['kriOverview'],
    queryFn: kriService.getTelemetryOverview,
  });

  const { data: kris = [] } = useQuery({
    queryKey: ['kris', categoryFilter, search],
    queryFn: () =>
      kriService.listKris({
        risk_category: categoryFilter || undefined,
        search: search || undefined,
      }),
  });

  const { data: appetites = [] } = useQuery({
    queryKey: ['kriAppetites'],
    queryFn: kriService.listAppetiteStatements,
  });

  const { data: breaches = [] } = useQuery({
    queryKey: ['kriBreaches'],
    queryFn: () => kriService.listBreaches(),
  });

  // Mutations
  const createKriMutation = useMutation({
    mutationFn: kriService.createKri,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['kris'] });
      queryClient.invalidateQueries({ queryKey: ['kriOverview'] });
      setIsCreateKriOpen(false);
      setNewKri({
        kri_code: '',
        title: '',
        description: '',
        risk_category: 'CYBERSECURITY',
        unit_of_measure: 'COUNT',
        direction: 'LOWER_IS_BETTER',
        frequency: 'DAILY',
        source_type: 'MANUAL',
        initial_threshold: {
          target_value: 0,
          warning_threshold: 10,
          critical_threshold: 25,
          rationale: 'Initial baseline threshold',
        },
      });
    },
  });

  const observeMutation = useMutation({
    mutationFn: ({ kriId, data }: { kriId: number; data: KriObservationCreate }) =>
      kriService.ingestObservation(kriId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['kris'] });
      queryClient.invalidateQueries({ queryKey: ['kriOverview'] });
      queryClient.invalidateQueries({ queryKey: ['kriBreaches'] });
      setIsObserveOpen(false);
      setSelectedKri(null);
    },
  });

  const approveAppetiteMutation = useMutation({
    mutationFn: ({ id, justification }: { id: number; justification: string }) =>
      kriService.approveAppetiteStatement(id, { approval_justification: justification }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['kriAppetites'] });
      queryClient.invalidateQueries({ queryKey: ['kriOverview'] });
      setIsApproveAppetiteOpen(false);
      setApprovalJustification('');
      setSelectedAppetiteId(null);
    },
  });

  const acknowledgeBreachMutation = useMutation({
    mutationFn: (breachId: number) =>
      kriService.acknowledgeBreach(breachId, { notes: 'Formal breach acknowledgement' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['kriBreaches'] });
      queryClient.invalidateQueries({ queryKey: ['kriOverview'] });
    },
  });

  const closeBreachMutation = useMutation({
    mutationFn: ({ id, notes }: { id: number; notes: string }) =>
      kriService.closeBreach(id, { closure_notes: notes }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['kriBreaches'] });
      queryClient.invalidateQueries({ queryKey: ['kriOverview'] });
      setIsCloseBreachOpen(false);
      setClosureNotes('');
      setSelectedBreachId(null);
    },
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'WITHIN_APPETITE':
        return 'bg-emerald-950/60 text-emerald-400 border-emerald-800/80';
      case 'WARNING_BREACH':
        return 'bg-amber-950/60 text-amber-400 border-amber-800/80';
      case 'CRITICAL_BREACH':
        return 'bg-red-950/60 text-red-400 border-red-800/80';
      default:
        return 'bg-slate-900 text-slate-400 border-slate-700';
    }
  };

  const getBreachStatusBadge = (status: string) => {
    switch (status) {
      case 'DETECTED':
        return 'bg-red-950/60 text-red-400 border-red-800/80';
      case 'ACKNOWLEDGED':
        return 'bg-amber-950/60 text-amber-400 border-amber-800/80';
      case 'ESCALATED':
        return 'bg-purple-950/60 text-purple-400 border-purple-800/80';
      case 'RECOVERED':
        return 'bg-blue-950/60 text-blue-400 border-blue-800/80';
      case 'CLOSED':
        return 'bg-emerald-950/60 text-emerald-400 border-emerald-800/80';
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700';
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
            <Gauge className="w-6 h-6 text-indigo-400" />
            Key Risk Indicators (KRI) & Risk Appetite
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Deterministic directional threshold telemetry, breach lifecycle governance, and risk appetite policy alignment.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsCreateKriOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg shadow-sm transition-colors cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            New Indicator
          </button>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Active KRIs</span>
            <Activity className="w-4 h-4 text-indigo-400" />
          </div>
          <p className="text-2xl font-bold text-slate-100 mt-2">
            {isOverviewLoading ? '...' : overview?.active_kris ?? 0}
          </p>
          <p className="text-xs text-slate-400 mt-1">
            {overview?.total_kris ?? 0} registered indicators
          </p>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Within Appetite</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <p className="text-2xl font-bold text-emerald-400 mt-2">
            {isOverviewLoading ? '...' : overview?.within_appetite_count ?? 0}
          </p>
          <p className="text-xs text-slate-400 mt-1">Normal operating threshold</p>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Warning Breaches</span>
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          </div>
          <p className="text-2xl font-bold text-amber-400 mt-2">
            {isOverviewLoading ? '...' : overview?.warning_breach_count ?? 0}
          </p>
          <p className="text-xs text-slate-400 mt-1">Elevated risk posture</p>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Critical Breaches</span>
            <XCircle className="w-4 h-4 text-red-400" />
          </div>
          <p className="text-2xl font-bold text-red-400 mt-2">
            {isOverviewLoading ? '...' : overview?.critical_breach_count ?? 0}
          </p>
          <p className="text-xs text-slate-400 mt-1">Tolerance threshold exceeded</p>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Open Breaches</span>
            <ShieldAlert className="w-4 h-4 text-purple-400" />
          </div>
          <p className="text-2xl font-bold text-purple-400 mt-2">
            {isOverviewLoading ? '...' : overview?.open_breaches_count ?? 0}
          </p>
          <p className="text-xs text-slate-400 mt-1">
            {overview?.stale_kris_count ?? 0} KRIs stale
          </p>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="border-b border-slate-800 flex items-center gap-6">
        <button
          onClick={() => setActiveTab('overview')}
          className={`pb-3 text-sm font-medium border-b-2 transition-colors cursor-pointer ${
            activeTab === 'overview'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Overview & Telemetry
        </button>
        <button
          onClick={() => setActiveTab('indicators')}
          className={`pb-3 text-sm font-medium border-b-2 transition-colors cursor-pointer ${
            activeTab === 'indicators'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Indicators ({kris.length})
        </button>
        <button
          onClick={() => setActiveTab('appetite')}
          className={`pb-3 text-sm font-medium border-b-2 transition-colors cursor-pointer ${
            activeTab === 'appetite'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Risk Appetite Statements ({appetites.length})
        </button>
        <button
          onClick={() => setActiveTab('breaches')}
          className={`pb-3 text-sm font-medium border-b-2 transition-colors cursor-pointer ${
            activeTab === 'breaches'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Breach Governance ({breaches.length})
        </button>
      </div>

      {/* Tab Contents */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Latest Approved Appetite Card */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
              <FileText className="w-5 h-5 text-indigo-400" />
              Active Risk Appetite Framework
            </h2>
            {overview?.latest_appetite_statement ? (
              <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <span className="text-xs text-slate-400 uppercase tracking-wider">Statement Code & Title</span>
                  <p className="text-base font-semibold text-slate-200 mt-1">
                    {overview.latest_appetite_statement.statement_code} — {overview.latest_appetite_statement.title}
                  </p>
                  <p className="text-sm text-slate-400 mt-2">
                    {overview.latest_appetite_statement.executive_summary}
                  </p>
                </div>
                <div>
                  <span className="text-xs text-slate-400 uppercase tracking-wider">Overall Loss Tolerance</span>
                  <p className="text-xl font-bold text-emerald-400 mt-1">
                    {overview.latest_appetite_statement.overall_loss_tolerance_pct
                      ? `${overview.latest_appetite_statement.overall_loss_tolerance_pct}%`
                      : 'N/A'}
                  </p>
                  <span className="text-xs text-slate-400 uppercase tracking-wider mt-3 block">Review Cadence</span>
                  <p className="text-sm text-slate-300">
                    Every {overview.latest_appetite_statement.review_cadence_months} months
                  </p>
                </div>
                <div>
                  <span className="text-xs text-slate-400 uppercase tracking-wider">Approval Governance</span>
                  <p className="text-sm text-emerald-400 mt-1 font-medium">
                    Status: {overview.latest_appetite_statement.status}
                  </p>
                  {overview.latest_appetite_statement.approved_at && (
                    <p className="text-xs text-slate-400 mt-1">
                      Approved at {new Date(overview.latest_appetite_statement.approved_at).toLocaleDateString()}
                    </p>
                  )}
                  {overview.latest_appetite_statement.approval_justification && (
                    <p className="text-xs text-slate-400 italic mt-2 border-l-2 border-indigo-500 pl-2">
                      "{overview.latest_appetite_statement.approval_justification}"
                    </p>
                  )}
                </div>
              </div>
            ) : (
              <p className="text-sm text-slate-400 mt-3">
                No active approved risk appetite statement found. Create and approve a statement in the Risk Appetite tab.
              </p>
            )}
          </div>

          {/* Quick Indicator Posture */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-indigo-400" />
              Real-Time Indicator Feed
            </h2>
            <div className="mt-4 divide-y divide-slate-800">
              {kris.slice(0, 5).map((kri) => (
                <div key={kri.id} className="py-3 flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-semibold text-indigo-400">{kri.kri_code}</span>
                      <span className="text-sm font-medium text-slate-200">{kri.title}</span>
                    </div>
                    <p className="text-xs text-slate-400 mt-0.5">{kri.risk_category} • {kri.unit_of_measure}</p>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <span className="text-sm font-bold text-slate-100">
                        {kri.current_value !== null && kri.current_value !== undefined ? kri.current_value : '—'}
                      </span>
                      <span className="text-xs text-slate-500 ml-1">{kri.unit_of_measure}</span>
                    </div>
                    <span className={`px-2.5 py-1 text-xs font-semibold rounded-full border ${getStatusBadge(kri.current_evaluation_status)}`}>
                      {kri.current_evaluation_status.replace('_', ' ')}
                    </span>
                  </div>
                </div>
              ))}
              {kris.length === 0 && (
                <p className="text-sm text-slate-500 py-4 text-center">No indicators registered yet.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Indicators Tab */}
      {activeTab === 'indicators' && (
        <div className="space-y-4">
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex flex-wrap items-center gap-3">
            <div className="relative flex-1 min-w-[240px]">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Search KRI by code or title..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg pl-9 pr-4 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-300 focus:outline-none focus:border-indigo-500"
            >
              <option value="">All Categories</option>
              <option value="CYBERSECURITY">CYBERSECURITY</option>
              <option value="OPERATIONAL">OPERATIONAL</option>
              <option value="COMPLIANCE">COMPLIANCE</option>
              <option value="FINANCIAL">FINANCIAL</option>
              <option value="STRATEGIC">STRATEGIC</option>
            </select>
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-950/80 text-xs uppercase text-slate-400 border-b border-slate-800 font-semibold tracking-wider">
                <tr>
                  <th className="px-4 py-3">KRI Code</th>
                  <th className="px-4 py-3">Indicator Title</th>
                  <th className="px-4 py-3">Direction & Unit</th>
                  <th className="px-4 py-3">Thresholds (Warn / Crit)</th>
                  <th className="px-4 py-3">Current Value</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {kris.map((kri) => (
                  <tr key={kri.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs font-semibold text-indigo-400">
                      {kri.kri_code}
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-slate-200">{kri.title}</div>
                      <div className="text-xs text-slate-500">{kri.risk_category}</div>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400">
                      {kri.direction} ({kri.unit_of_measure})
                    </td>
                    <td className="px-4 py-3 text-xs font-mono">
                      {kri.active_threshold ? (
                        <span>
                          <span className="text-amber-400">{kri.active_threshold.warning_threshold ?? '—'}</span> /{' '}
                          <span className="text-red-400">{kri.active_threshold.critical_threshold ?? '—'}</span>
                        </span>
                      ) : (
                        <span className="text-slate-500">None</span>
                      )}
                    </td>
                    <td className="px-4 py-3 font-bold text-slate-100">
                      {kri.current_value !== null && kri.current_value !== undefined ? kri.current_value : '—'}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2.5 py-0.5 text-xs font-semibold rounded-full border ${getStatusBadge(kri.current_evaluation_status)}`}>
                        {kri.current_evaluation_status.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => {
                          setSelectedKri(kri);
                          setNewObservation({
                            observed_value: 0,
                            unit: kri.unit_of_measure,
                            observed_at: new Date().toISOString(),
                            source_type: 'MANUAL',
                            source_system: 'Web Portal',
                          });
                          setIsObserveOpen(true);
                        }}
                        className="px-2.5 py-1 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg transition-colors cursor-pointer"
                      >
                        Ingest Observation
                      </button>
                    </td>
                  </tr>
                ))}
                {kris.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-slate-500 text-sm">
                      No indicators registered.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Risk Appetite Statements Tab */}
      {activeTab === 'appetite' && (
        <div className="space-y-4">
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-950/80 text-xs uppercase text-slate-400 border-b border-slate-800 font-semibold tracking-wider">
                <tr>
                  <th className="px-4 py-3">Statement Code</th>
                  <th className="px-4 py-3">Title & Summary</th>
                  <th className="px-4 py-3">Loss Tolerance</th>
                  <th className="px-4 py-3">Effective Date</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Four-Eyes Approval</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {appetites.map((stmt) => (
                  <tr key={stmt.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs font-semibold text-indigo-400">
                      {stmt.statement_code}
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-slate-200">{stmt.title}</div>
                      <div className="text-xs text-slate-400 line-clamp-1">{stmt.executive_summary}</div>
                    </td>
                    <td className="px-4 py-3 font-semibold text-slate-100">
                      {stmt.overall_loss_tolerance_pct ? `${stmt.overall_loss_tolerance_pct}%` : '—'}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400">
                      {new Date(stmt.effective_from).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 text-xs font-semibold rounded-full border ${
                        stmt.status === 'APPROVED'
                          ? 'bg-emerald-950/60 text-emerald-400 border-emerald-800'
                          : stmt.status === 'SUPERSEDED'
                          ? 'bg-slate-800 text-slate-500 border-slate-700'
                          : 'bg-amber-950/60 text-amber-400 border-amber-800'
                      }`}>
                        {stmt.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      {stmt.status === 'DRAFT' || stmt.status === 'UNDER_REVIEW' ? (
                        <button
                          onClick={() => {
                            setSelectedAppetiteId(stmt.id);
                            setIsApproveAppetiteOpen(true);
                          }}
                          className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded-lg transition-colors cursor-pointer"
                        >
                          Approve (Four-Eyes)
                        </button>
                      ) : (
                        <span className="text-xs text-slate-500">Approved</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Breaches Tab */}
      {activeTab === 'breaches' && (
        <div className="space-y-4">
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-950/80 text-xs uppercase text-slate-400 border-b border-slate-800 font-semibold tracking-wider">
                <tr>
                  <th className="px-4 py-3">Breach Code</th>
                  <th className="px-4 py-3">Severity</th>
                  <th className="px-4 py-3">Peak Value</th>
                  <th className="px-4 py-3">Detected At</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Lifecycle Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {breaches.map((breach) => (
                  <tr key={breach.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs font-semibold text-indigo-400">
                      {breach.breach_code}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 text-xs font-semibold rounded-full border ${
                        breach.breach_severity === 'CRITICAL'
                          ? 'bg-red-950/60 text-red-400 border-red-800'
                          : 'bg-amber-950/60 text-amber-400 border-amber-800'
                      }`}>
                        {breach.breach_severity}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-bold text-slate-100">
                      {breach.peak_value}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400">
                      {new Date(breach.detected_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 text-xs font-semibold rounded-full border ${getBreachStatusBadge(breach.status)}`}>
                        {breach.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {breach.status === 'DETECTED' && (
                          <button
                            onClick={() => acknowledgeBreachMutation.mutate(breach.id)}
                            className="px-2 py-1 bg-amber-600 hover:bg-amber-500 text-white text-xs font-medium rounded-lg transition-colors cursor-pointer"
                          >
                            Acknowledge
                          </button>
                        )}
                        {(breach.status === 'ACKNOWLEDGED' || breach.status === 'RECOVERED') && (
                          <button
                            onClick={() => {
                              setSelectedBreachId(breach.id);
                              setIsCloseBreachOpen(true);
                            }}
                            className="px-2 py-1 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded-lg transition-colors cursor-pointer"
                          >
                            Close Breach
                          </button>
                        )}
                        {breach.status === 'CLOSED' && (
                          <span className="text-xs text-slate-500">Resolved & Closed</span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
                {breaches.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-slate-500 text-sm">
                      No breach records found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Observation Modal */}
      {isObserveOpen && selectedKri && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 space-y-4 shadow-xl">
            <h3 className="text-lg font-bold text-slate-100">
              Ingest Telemetry Observation
            </h3>
            <p className="text-xs text-slate-400">
              {selectedKri.kri_code} — {selectedKri.title}
            </p>
            <div>
              <label className="text-xs font-medium text-slate-400 block mb-1">Observed Value ({selectedKri.unit_of_measure})</label>
              <input
                type="number"
                step="any"
                value={newObservation.observed_value}
                onChange={(e) => setNewObservation({ ...newObservation, observed_value: parseFloat(e.target.value) || 0 })}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-400 block mb-1">Source System</label>
              <input
                type="text"
                value={newObservation.source_system || ''}
                onChange={(e) => setNewObservation({ ...newObservation, source_system: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setIsObserveOpen(false)}
                className="px-4 py-2 border border-slate-700 text-slate-300 hover:bg-slate-800 rounded-lg text-sm font-medium transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={() => observeMutation.mutate({ kriId: selectedKri.id, data: newObservation })}
                disabled={observeMutation.isPending}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors cursor-pointer disabled:opacity-50"
              >
                {observeMutation.isPending ? 'Ingesting...' : 'Ingest & Evaluate'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Four-Eyes Approval Modal */}
      {isApproveAppetiteOpen && selectedAppetiteId && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 space-y-4 shadow-xl">
            <h3 className="text-lg font-bold text-slate-100">
              Approve Risk Appetite Statement
            </h3>
            <p className="text-xs text-slate-400">
              Enforcing Four-Eyes Segregation of Duties. Approver must be different from the statement author.
            </p>
            <div>
              <label className="text-xs font-medium text-slate-400 block mb-1">Approval Justification</label>
              <textarea
                rows={3}
                value={approvalJustification}
                onChange={(e) => setApprovalJustification(e.target.value)}
                placeholder="Document executive or board justification for accepting this risk appetite profile..."
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setIsApproveAppetiteOpen(false)}
                className="px-4 py-2 border border-slate-700 text-slate-300 hover:bg-slate-800 rounded-lg text-sm font-medium transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={() => approveAppetiteMutation.mutate({ id: selectedAppetiteId, justification: approvalJustification })}
                disabled={!approvalJustification.trim() || approveAppetiteMutation.isPending}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-medium transition-colors cursor-pointer disabled:opacity-50"
              >
                {approveAppetiteMutation.isPending ? 'Approving...' : 'Authorize Appetite'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Close Breach Modal */}
      {isCloseBreachOpen && selectedBreachId && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 space-y-4 shadow-xl">
            <h3 className="text-lg font-bold text-slate-100">
              Close Breach Record
            </h3>
            <p className="text-xs text-slate-400">
              Provide formal closure rationale verifying telemetry has recovered within acceptable risk thresholds.
            </p>
            <div>
              <label className="text-xs font-medium text-slate-400 block mb-1">Closure Notes</label>
              <textarea
                rows={3}
                value={closureNotes}
                onChange={(e) => setClosureNotes(e.target.value)}
                placeholder="Describe remediation verification and evidence of recovered metric..."
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setIsCloseBreachOpen(false)}
                className="px-4 py-2 border border-slate-700 text-slate-300 hover:bg-slate-800 rounded-lg text-sm font-medium transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={() => closeBreachMutation.mutate({ id: selectedBreachId, notes: closureNotes })}
                disabled={!closureNotes.trim() || closeBreachMutation.isPending}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-medium transition-colors cursor-pointer disabled:opacity-50"
              >
                {closeBreachMutation.isPending ? 'Closing...' : 'Close Breach'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create KRI Modal */}
      {isCreateKriOpen && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 space-y-4 shadow-xl">
            <h3 className="text-lg font-bold text-slate-100">
              Register Key Risk Indicator (KRI)
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-slate-400 block mb-1">KRI Code</label>
                <input
                  type="text"
                  placeholder="KRI-CYBER-01"
                  value={newKri.kri_code}
                  onChange={(e) => setNewKri({ ...newKri, kri_code: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-400 block mb-1">Risk Category</label>
                <select
                  value={newKri.risk_category}
                  onChange={(e) => setNewKri({ ...newKri, risk_category: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-300 focus:outline-none focus:border-indigo-500"
                >
                  <option value="CYBERSECURITY">CYBERSECURITY</option>
                  <option value="OPERATIONAL">OPERATIONAL</option>
                  <option value="COMPLIANCE">COMPLIANCE</option>
                  <option value="FINANCIAL">FINANCIAL</option>
                  <option value="STRATEGIC">STRATEGIC</option>
                </select>
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-slate-400 block mb-1">Title</label>
              <input
                type="text"
                placeholder="Unpatched Critical Vulnerabilities"
                value={newKri.title}
                onChange={(e) => setNewKri({ ...newKri, title: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="text-xs font-medium text-slate-400 block mb-1">Unit</label>
                <input
                  type="text"
                  placeholder="COUNT"
                  value={newKri.unit_of_measure}
                  onChange={(e) => setNewKri({ ...newKri, unit_of_measure: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-400 block mb-1">Warning Threshold</label>
                <input
                  type="number"
                  step="any"
                  value={newKri.initial_threshold?.warning_threshold ?? 10}
                  onChange={(e) =>
                    setNewKri({
                      ...newKri,
                      initial_threshold: {
                        ...newKri.initial_threshold,
                        warning_threshold: parseFloat(e.target.value) || 0,
                      },
                    })
                  }
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-400 block mb-1">Critical Threshold</label>
                <input
                  type="number"
                  step="any"
                  value={newKri.initial_threshold?.critical_threshold ?? 25}
                  onChange={(e) =>
                    setNewKri({
                      ...newKri,
                      initial_threshold: {
                        ...newKri.initial_threshold,
                        critical_threshold: parseFloat(e.target.value) || 0,
                      },
                    })
                  }
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setIsCreateKriOpen(false)}
                className="px-4 py-2 border border-slate-700 text-slate-300 hover:bg-slate-800 rounded-lg text-sm font-medium transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={() => createKriMutation.mutate(newKri)}
                disabled={!newKri.kri_code || !newKri.title || createKriMutation.isPending}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors cursor-pointer disabled:opacity-50"
              >
                {createKriMutation.isPending ? 'Registering...' : 'Register Indicator'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
