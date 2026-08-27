import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertOctagon,
  ArrowRight,
  CheckCircle2,
  Plus,
  RefreshCw,
  Search,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { remediationService } from '../lib/remediationService';
import { api } from '../lib/api';
import type {
  ComplianceDriftAlert,
  Finding,
  RemediationOverviewResponse,
  RemediationPlan,
  RemediationPlanCreate,
  RemediationRootCauseClassification,
  RemediationSeverity,
  RemediationSourceType,
  RemediationStatus,
  SecurityIncident,
  SlaStatus,
  User,
} from '../types';

export const RemediationsPage: React.FC = () => {
  const navigate = useNavigate();
  const { hasRole } = useAuth();
  const canManage = hasRole('ADMIN', 'GRC_ANALYST', 'SECURITY_ANALYST', 'MANAGER');

  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState<RemediationOverviewResponse | null>(null);
  const [plans, setPlans] = useState<RemediationPlan[]>([]);
  const [users, setUsers] = useState<User[]>([]);

  // Source options for creation modal
  const [findings, setFindings] = useState<Finding[]>([]);
  const [driftAlerts, setDriftAlerts] = useState<ComplianceDriftAlert[]>([]);
  const [incidents, setIncidents] = useState<SecurityIncident[]>([]);

  // Filters
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [sourceTypeFilter, setSourceTypeFilter] = useState<string>('ALL');
  const [slaStatusFilter, setSlaStatusFilter] = useState<string>('ALL');

  // Create Plan Modal
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createForm, setCreateForm] = useState<RemediationPlanCreate>({
    plan_code: '',
    title: '',
    problem_statement: '',
    root_cause_classification: 'CONTROL_DEFICIENCY',
    source_type: 'FINDING',
    severity: 'HIGH',
    finding_id: undefined,
    compliance_drift_alert_id: undefined,
    security_incident_id: undefined,
    vendor_assessment_id: undefined,
    audit_id: undefined,
    target_completion_at: undefined,
  });
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [overviewData, plansData, usersData, findingsData, alertsData, incidentsData] =
        await Promise.all([
          remediationService.getOverview().catch(() => null),
          remediationService.listPlans().catch(() => []),
          api.get<User[]>('/users').then((r) => r.data).catch(() => []),
          api.get<Finding[]>('/findings').then((r) => r.data).catch(() => []),
          api.get<ComplianceDriftAlert[]>('/monitoring/alerts').then((r) => r.data).catch(() => []),
          api.get<SecurityIncident[]>('/incidents').then((r) => r.data).catch(() => []),
        ]);
      setOverview(overviewData);
      setPlans(plansData);
      setUsers(usersData);
      setFindings(findingsData);
      setDriftAlerts(alertsData);
      setIncidents(incidentsData);
    } catch (err) {
      console.error('Failed to load remediation plans portfolio', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreatePlan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createForm.plan_code.trim() || !createForm.title.trim() || !createForm.problem_statement.trim()) {
      setCreateError('Plan code, title, and problem statement are mandatory.');
      return;
    }

    // Ensure selected source foreign key is populated
    if (createForm.source_type === 'FINDING' && !createForm.finding_id) {
      setCreateError('Please select a valid source Finding.');
      return;
    }
    if (createForm.source_type === 'CCM_DRIFT' && !createForm.compliance_drift_alert_id) {
      setCreateError('Please select a valid source CCM Drift Alert.');
      return;
    }
    if (createForm.source_type === 'SECURITY_INCIDENT' && !createForm.security_incident_id) {
      setCreateError('Please select a valid source Security Incident.');
      return;
    }

    setCreateLoading(true);
    setCreateError(null);
    try {
      const payload: RemediationPlanCreate = {
        plan_code: createForm.plan_code.trim(),
        title: createForm.title.trim(),
        problem_statement: createForm.problem_statement.trim(),
        root_cause_classification: createForm.root_cause_classification,
        source_type: createForm.source_type,
        severity: createForm.severity,
        finding_id: createForm.source_type === 'FINDING' ? Number(createForm.finding_id) : undefined,
        compliance_drift_alert_id:
          createForm.source_type === 'CCM_DRIFT' ? Number(createForm.compliance_drift_alert_id) : undefined,
        security_incident_id:
          createForm.source_type === 'SECURITY_INCIDENT' ? Number(createForm.security_incident_id) : undefined,
        vendor_assessment_id:
          createForm.source_type === 'TPRM_ASSESSMENT' ? Number(createForm.vendor_assessment_id) : undefined,
        audit_id: createForm.source_type === 'AUDIT' ? Number(createForm.audit_id) : undefined,
        target_completion_at: createForm.target_completion_at
          ? new Date(createForm.target_completion_at).toISOString()
          : undefined,
      };

      const newPlan = await remediationService.createPlan(payload);
      setShowCreateModal(false);
      navigate(`/remediations/${newPlan.id}`);
    } catch (err: any) {
      setCreateError(err.response?.data?.detail || 'Failed to create remediation plan.');
    } finally {
      setCreateLoading(false);
    }
  };

  const filteredPlans = plans.filter((p) => {
    if (statusFilter !== 'ALL' && p.status !== statusFilter) return false;
    if (severityFilter !== 'ALL' && p.severity !== severityFilter) return false;
    if (sourceTypeFilter !== 'ALL' && p.source_type !== sourceTypeFilter) return false;
    if (slaStatusFilter !== 'ALL' && p.sla_status !== slaStatusFilter) return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      const matchCode = p.plan_code.toLowerCase().includes(q);
      const matchTitle = p.title.toLowerCase().includes(q);
      const matchStatement = p.problem_statement.toLowerCase().includes(q);
      if (!matchCode && !matchTitle && !matchStatement) return false;
    }
    return true;
  });

  const getStatusBadge = (status: RemediationStatus) => {
    switch (status) {
      case 'DRAFT':
        return 'bg-slate-800 text-slate-300 border-slate-700';
      case 'APPROVED':
        return 'bg-blue-950/70 text-blue-300 border-blue-800/80';
      case 'IN_EXECUTION':
        return 'bg-indigo-950/70 text-indigo-300 border-indigo-800/80 animate-pulse';
      case 'PENDING_VALIDATION':
        return 'bg-amber-950/70 text-amber-300 border-amber-800/80';
      case 'VERIFIED_CLOSED':
        return 'bg-emerald-950/70 text-emerald-300 border-emerald-800/80';
      case 'CANCELLED':
        return 'bg-rose-950/70 text-rose-300 border-rose-800/80';
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700';
    }
  };

  const getSeverityBadge = (sev: RemediationSeverity) => {
    switch (sev) {
      case 'CRITICAL':
        return 'bg-red-950/80 text-red-300 border-red-800 font-semibold';
      case 'HIGH':
        return 'bg-orange-950/80 text-orange-300 border-orange-800';
      case 'MEDIUM':
        return 'bg-amber-950/80 text-amber-300 border-amber-800';
      case 'LOW':
        return 'bg-blue-950/80 text-blue-300 border-blue-800';
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700';
    }
  };

  const getSlaBadge = (sla?: SlaStatus) => {
    switch (sla) {
      case 'NOT_STARTED':
        return 'bg-slate-800 text-slate-400 border-slate-700';
      case 'ON_TRACK':
        return 'bg-emerald-950/60 text-emerald-300 border-emerald-800/60';
      case 'AT_RISK':
        return 'bg-amber-950/80 text-amber-300 border-amber-700 animate-pulse';
      case 'BREACHED':
        return 'bg-rose-950/90 text-rose-200 border-rose-700 font-bold';
      case 'COMPLETED_ON_TIME':
        return 'bg-emerald-900/60 text-emerald-200 border-emerald-700';
      case 'COMPLETED_LATE':
        return 'bg-orange-950/80 text-orange-200 border-orange-700';
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700';
    }
  };

  const getSourceTypeBadge = (source: RemediationSourceType) => {
    switch (source) {
      case 'FINDING':
        return 'bg-purple-950/60 text-purple-300 border-purple-800/60';
      case 'CCM_DRIFT':
        return 'bg-cyan-950/60 text-cyan-300 border-cyan-800/60';
      case 'SECURITY_INCIDENT':
        return 'bg-rose-950/60 text-rose-300 border-rose-800/60';
      case 'TPRM_ASSESSMENT':
        return 'bg-amber-950/60 text-amber-300 border-amber-800/60';
      case 'AUDIT':
        return 'bg-indigo-950/60 text-indigo-300 border-indigo-800/60';
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700';
    }
  };

  const getUserName = (userId?: number) => {
    if (!userId) return 'Unassigned';
    const u = users.find((x) => x.id === userId);
    return u ? u.full_name : `User #${userId}`;
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider bg-indigo-950 text-indigo-300 border border-indigo-800 rounded">
              Phase 11 — ROC-V
            </span>
            <span className="text-xs text-slate-500 font-mono">CLOSED-LOOP ASSURANCE</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-bold text-white tracking-tight mt-1">
            Governed Remediation & Corrective Actions (CAPA)
          </h1>
          <p className="text-sm text-slate-400 mt-1 max-w-3xl">
            Deterministic remediation orchestration with four-eyes verification, independent re-testing,
            and automated upstream resolution for CCM drift, findings, incidents, TPRM, and audits.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchData}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>

          {canManage && (
            <button
              onClick={() => {
                setCreateError(null);
                setShowCreateModal(true);
              }}
              className="flex items-center gap-2 px-4 py-2 text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg shadow-lg shadow-indigo-900/30 transition-colors"
            >
              <Plus className="w-4 h-4" />
              New Remediation Plan
            </button>
          )}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 flex flex-col justify-between">
          <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Total Plans</span>
          <span className="text-2xl font-bold text-white mt-2">{overview?.total_plans ?? 0}</span>
          <span className="text-[10px] text-slate-500 mt-1 font-mono">ROC-V Portfolio</span>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 flex flex-col justify-between">
          <span className="text-[11px] font-medium text-blue-400 uppercase tracking-wider">Active Plans</span>
          <span className="text-2xl font-bold text-blue-400 mt-2">{overview?.open_plans ?? 0}</span>
          <span className="text-[10px] text-slate-500 mt-1 font-mono">In Progress</span>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 flex flex-col justify-between">
          <span className="text-[11px] font-medium text-amber-400 uppercase tracking-wider">Pending Validation</span>
          <span className="text-2xl font-bold text-amber-400 mt-2">{overview?.pending_validation_plans ?? 0}</span>
          <span className="text-[10px] text-slate-500 mt-1 font-mono">Ready for Re-Test</span>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 flex flex-col justify-between">
          <span className="text-[11px] font-medium text-rose-400 uppercase tracking-wider">SLA Breached</span>
          <span className="text-2xl font-bold text-rose-400 mt-2">{overview?.sla_breached_plans ?? 0}</span>
          <span className="text-[10px] text-slate-500 mt-1 font-mono">Past Target Date</span>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 flex flex-col justify-between">
          <span className="text-[11px] font-medium text-orange-400 uppercase tracking-wider">Crit / High</span>
          <span className="text-2xl font-bold text-orange-400 mt-2">{overview?.critical_or_high_plans ?? 0}</span>
          <span className="text-[10px] text-slate-500 mt-1 font-mono">High Priority</span>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 flex flex-col justify-between">
          <span className="text-[11px] font-medium text-emerald-400 uppercase tracking-wider">Avg REI Score</span>
          <span className="text-2xl font-bold text-emerald-400 mt-2">
            {overview?.average_rei_score !== undefined && overview?.average_rei_score !== null
              ? `${overview.average_rei_score}`
              : 'N/A'}
          </span>
          <span className="text-[10px] text-slate-500 mt-1 font-mono">Effectiveness / 100</span>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 flex flex-col justify-between">
          <span className="text-[11px] font-medium text-cyan-400 uppercase tracking-wider">Avg TTR</span>
          <span className="text-2xl font-bold text-cyan-400 mt-2">
            {overview?.average_ttr_hours !== undefined && overview?.average_ttr_hours !== null
              ? `${overview.average_ttr_hours}h`
              : 'N/A'}
          </span>
          <span className="text-[10px] text-slate-500 mt-1 font-mono">Time to Remediate</span>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 flex flex-col justify-between">
          <span className="text-[11px] font-medium text-purple-400 uppercase tracking-wider">Verified Closed</span>
          <span className="text-2xl font-bold text-purple-400 mt-2">
            {overview?.status_distribution?.VERIFIED_CLOSED ?? 0}
          </span>
          <span className="text-[10px] text-slate-500 mt-1 font-mono">Immutable</span>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {/* Search */}
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search plan code, title..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs text-white bg-slate-950 border border-slate-800 rounded-lg focus:outline-none focus:border-indigo-500"
            />
          </div>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 text-xs text-white bg-slate-950 border border-slate-800 rounded-lg focus:outline-none focus:border-indigo-500"
          >
            <option value="ALL">All Lifecycle Statuses</option>
            <option value="DRAFT">DRAFT</option>
            <option value="APPROVED">APPROVED</option>
            <option value="IN_EXECUTION">IN EXECUTION</option>
            <option value="PENDING_VALIDATION">PENDING VALIDATION</option>
            <option value="VERIFIED_CLOSED">VERIFIED CLOSED</option>
            <option value="CANCELLED">CANCELLED</option>
          </select>

          {/* Severity Filter */}
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="px-3 py-1.5 text-xs text-white bg-slate-950 border border-slate-800 rounded-lg focus:outline-none focus:border-indigo-500"
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">CRITICAL (7 Days SLA)</option>
            <option value="HIGH">HIGH (30 Days SLA)</option>
            <option value="MEDIUM">MEDIUM (60 Days SLA)</option>
            <option value="LOW">LOW (90 Days SLA)</option>
          </select>

          {/* Source Type Filter */}
          <select
            value={sourceTypeFilter}
            onChange={(e) => setSourceTypeFilter(e.target.value)}
            className="px-3 py-1.5 text-xs text-white bg-slate-950 border border-slate-800 rounded-lg focus:outline-none focus:border-indigo-500"
          >
            <option value="ALL">All Authoritative Sources</option>
            <option value="FINDING">Finding (Phase 4)</option>
            <option value="CCM_DRIFT">CCM Drift Alert (Phase 7)</option>
            <option value="SECURITY_INCIDENT">Security Incident (Phase 10)</option>
            <option value="TPRM_ASSESSMENT">TPRM Assessment (Phase 9)</option>
            <option value="AUDIT">Audit Deficiency (Phase 6)</option>
          </select>

          {/* SLA Status Filter */}
          <select
            value={slaStatusFilter}
            onChange={(e) => setSlaStatusFilter(e.target.value)}
            className="px-3 py-1.5 text-xs text-white bg-slate-950 border border-slate-800 rounded-lg focus:outline-none focus:border-indigo-500"
          >
            <option value="ALL">All SLA States</option>
            <option value="NOT_STARTED">Not Started</option>
            <option value="ON_TRACK">On Track</option>
            <option value="AT_RISK">At Risk (≤20% Remaining)</option>
            <option value="BREACHED">Breached (Overdue)</option>
            <option value="COMPLETED_ON_TIME">Completed On Time</option>
            <option value="COMPLETED_LATE">Completed Late</option>
          </select>
        </div>
      </div>

      {/* Plans Portfolio Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-950/80 border-b border-slate-800 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                <th className="py-3 px-4">Plan Code</th>
                <th className="py-3 px-4">Title & Problem Statement</th>
                <th className="py-3 px-4">Source</th>
                <th className="py-3 px-4">Severity</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">SLA Telemetry</th>
                <th className="py-3 px-4 text-center">REI</th>
                <th className="py-3 px-4 text-center">TTR</th>
                <th className="py-3 px-4">Owner</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-xs">
              {loading ? (
                <tr>
                  <td colSpan={10} className="py-12 text-center text-slate-500">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-400" />
                    Loading remediation plans...
                  </td>
                </tr>
              ) : filteredPlans.length === 0 ? (
                <tr>
                  <td colSpan={10} className="py-12 text-center text-slate-500">
                    <CheckCircle2 className="w-8 h-8 mx-auto mb-2 text-slate-600" />
                    No remediation plans found matching the criteria.
                  </td>
                </tr>
              ) : (
                filteredPlans.map((plan) => (
                  <tr
                    key={plan.id}
                    onClick={() => navigate(`/remediations/${plan.id}`)}
                    className="hover:bg-slate-800/40 cursor-pointer transition-colors"
                  >
                    <td className="py-3.5 px-4 font-mono font-bold text-indigo-300">
                      {plan.plan_code}
                    </td>

                    <td className="py-3.5 px-4 max-w-xs">
                      <div className="font-semibold text-white truncate">{plan.title}</div>
                      <div className="text-[11px] text-slate-400 truncate">{plan.problem_statement}</div>
                    </td>

                    <td className="py-3.5 px-4">
                      <span
                        className={`inline-block px-2 py-0.5 text-[10px] font-mono border rounded ${getSourceTypeBadge(
                          plan.source_type
                        )}`}
                      >
                        {plan.source_type}
                      </span>
                    </td>

                    <td className="py-3.5 px-4">
                      <span
                        className={`inline-block px-2 py-0.5 text-[10px] border rounded ${getSeverityBadge(
                          plan.severity
                        )}`}
                      >
                        {plan.severity}
                      </span>
                    </td>

                    <td className="py-3.5 px-4">
                      <span
                        className={`inline-block px-2.5 py-0.5 text-[11px] font-medium border rounded-full ${getStatusBadge(
                          plan.status
                        )}`}
                      >
                        {plan.status.replace('_', ' ')}
                      </span>
                    </td>

                    <td className="py-3.5 px-4">
                      <div className="flex flex-col gap-0.5">
                        <span
                          className={`inline-block px-2 py-0.5 text-[10px] border rounded w-fit ${getSlaBadge(
                            plan.sla_status
                          )}`}
                        >
                          {plan.sla_status ? plan.sla_status.replace('_', ' ') : 'NOT STARTED'}
                        </span>
                        {plan.remaining_hours !== undefined && plan.remaining_hours !== null && (
                          <span className="text-[10px] text-slate-500 font-mono">
                            {plan.remaining_hours > 0
                              ? `${plan.remaining_hours.toFixed(0)}h remaining`
                              : `${Math.abs(plan.remaining_hours).toFixed(0)}h overdue`}
                          </span>
                        )}
                      </div>
                    </td>

                    <td className="py-3.5 px-4 text-center font-mono">
                      {plan.rei_score !== undefined && plan.rei_score !== null ? (
                        <span
                          className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                            plan.rei_score >= 85
                              ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                              : plan.rei_score >= 60
                              ? 'bg-amber-950 text-amber-300 border border-amber-800'
                              : 'bg-rose-950 text-rose-300 border border-rose-800'
                          }`}
                        >
                          {plan.rei_score.toFixed(1)}
                        </span>
                      ) : (
                        <span className="text-slate-600">—</span>
                      )}
                    </td>

                    <td className="py-3.5 px-4 text-center font-mono text-slate-300">
                      {plan.ttr_hours !== undefined && plan.ttr_hours !== null ? (
                        `${plan.ttr_hours}h`
                      ) : (
                        <span className="text-slate-600">—</span>
                      )}
                    </td>

                    <td className="py-3.5 px-4 text-slate-300">{getUserName(plan.plan_owner_id)}</td>

                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/remediations/${plan.id}`);
                        }}
                        className="p-1 text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 rounded transition-colors"
                      >
                        <ArrowRight className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create Remediation Plan Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-lg font-bold text-white">Create Governed Remediation Plan</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Authoritative single-source CAPA initialization with automated SLA boundaries.
                </p>
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-white text-lg font-mono p-1"
              >
                ✕
              </button>
            </div>

            {createError && (
              <div className="p-3 bg-red-950/50 border border-red-800 rounded-lg text-xs text-red-300 flex items-start gap-2">
                <AlertOctagon className="w-4 h-4 mt-0.5 shrink-0" />
                <span>{createError}</span>
              </div>
            )}

            <form onSubmit={handleCreatePlan} className="space-y-4 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Plan Code *</label>
                  <input
                    type="text"
                    placeholder="e.g. CAPA-2026-001"
                    value={createForm.plan_code}
                    onChange={(e) => setCreateForm({ ...createForm, plan_code: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white font-mono focus:outline-none focus:border-indigo-500"
                    required
                  />
                </div>

                <div>
                  <label className="block text-slate-300 font-medium mb-1">Severity *</label>
                  <select
                    value={createForm.severity}
                    onChange={(e) =>
                      setCreateForm({ ...createForm, severity: e.target.value as RemediationSeverity })
                    }
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="CRITICAL">CRITICAL (7 Days SLA)</option>
                    <option value="HIGH">HIGH (30 Days SLA)</option>
                    <option value="MEDIUM">MEDIUM (60 Days SLA)</option>
                    <option value="LOW">LOW (90 Days SLA)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Plan Title *</label>
                <input
                  type="text"
                  placeholder="e.g. Enforce Default TLS 1.3 on API Gateways"
                  value={createForm.title}
                  onChange={(e) => setCreateForm({ ...createForm, title: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white focus:outline-none focus:border-indigo-500"
                  required
                />
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Problem Statement *</label>
                <textarea
                  rows={3}
                  placeholder="Detailed description of the deficiency, root cause, and scope of remediation required..."
                  value={createForm.problem_statement}
                  onChange={(e) => setCreateForm({ ...createForm, problem_statement: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white focus:outline-none focus:border-indigo-500"
                  required
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    Root Cause Classification *
                  </label>
                  <select
                    value={createForm.root_cause_classification}
                    onChange={(e) =>
                      setCreateForm({
                        ...createForm,
                        root_cause_classification: e.target.value as RemediationRootCauseClassification,
                      })
                    }
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="CONTROL_DEFICIENCY">Control Deficiency</option>
                    <option value="CONFIGURATION_DRIFT">Configuration Drift</option>
                    <option value="HUMAN_ERROR">Human Error</option>
                    <option value="VENDOR_DEFAULT">Vendor Default</option>
                    <option value="ARCHITECTURAL_GAP">Architectural Gap</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    Authoritative Source Type *
                  </label>
                  <select
                    value={createForm.source_type}
                    onChange={(e) =>
                      setCreateForm({
                        ...createForm,
                        source_type: e.target.value as RemediationSourceType,
                        finding_id: undefined,
                        compliance_drift_alert_id: undefined,
                        security_incident_id: undefined,
                        vendor_assessment_id: undefined,
                        audit_id: undefined,
                      })
                    }
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="FINDING">Assessment Finding (Phase 4)</option>
                    <option value="CCM_DRIFT">Continuous Monitoring Drift (Phase 7)</option>
                    <option value="SECURITY_INCIDENT">Security Incident (Phase 10)</option>
                    <option value="TPRM_ASSESSMENT">Vendor Assessment (Phase 9)</option>
                    <option value="AUDIT">Audit Engagement Deficiency (Phase 6)</option>
                  </select>
                </div>
              </div>

              {/* Dedicated Source Selector */}
              <div className="bg-slate-950 p-3.5 border border-slate-800 rounded-xl space-y-2">
                <label className="block text-indigo-300 font-semibold text-xs">
                  Select Specific {createForm.source_type} Entity *
                </label>

                {createForm.source_type === 'FINDING' && (
                  <select
                    value={createForm.finding_id || ''}
                    onChange={(e) =>
                      setCreateForm({ ...createForm, finding_id: Number(e.target.value) || undefined })
                    }
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-indigo-500 text-xs"
                    required
                  >
                    <option value="">-- Select Upstream Finding --</option>
                    {findings.map((f) => (
                      <option key={f.id} value={f.id}>
                        [ID #{f.id}] [{f.severity}] {f.title} ({f.status})
                      </option>
                    ))}
                  </select>
                )}

                {createForm.source_type === 'CCM_DRIFT' && (
                  <select
                    value={createForm.compliance_drift_alert_id || ''}
                    onChange={(e) =>
                      setCreateForm({
                        ...createForm,
                        compliance_drift_alert_id: Number(e.target.value) || undefined,
                      })
                    }
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-indigo-500 text-xs"
                    required
                  >
                    <option value="">-- Select Upstream CCM Drift Alert --</option>
                    {driftAlerts.map((a) => (
                      <option key={a.id} value={a.id}>
                        [ID #{a.id}] [{a.severity}] {a.title} ({a.status})
                      </option>
                    ))}
                  </select>
                )}

                {createForm.source_type === 'SECURITY_INCIDENT' && (
                  <select
                    value={createForm.security_incident_id || ''}
                    onChange={(e) =>
                      setCreateForm({
                        ...createForm,
                        security_incident_id: Number(e.target.value) || undefined,
                      })
                    }
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-indigo-500 text-xs"
                    required
                  >
                    <option value="">-- Select Upstream Security Incident --</option>
                    {incidents.map((inc) => (
                      <option key={inc.id} value={inc.id}>
                        [{inc.incident_code}] [{inc.severity}] {inc.title} ({inc.status})
                      </option>
                    ))}
                  </select>
                )}

                {(createForm.source_type === 'TPRM_ASSESSMENT' || createForm.source_type === 'AUDIT') && (
                  <div>
                    <input
                      type="number"
                      placeholder={`Enter ${createForm.source_type} Record ID`}
                      value={
                        createForm.source_type === 'TPRM_ASSESSMENT'
                          ? createForm.vendor_assessment_id || ''
                          : createForm.audit_id || ''
                      }
                      onChange={(e) => {
                        const val = Number(e.target.value) || undefined;
                        if (createForm.source_type === 'TPRM_ASSESSMENT') {
                          setCreateForm({ ...createForm, vendor_assessment_id: val });
                        } else {
                          setCreateForm({ ...createForm, audit_id: val });
                        }
                      }}
                      className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-indigo-500 text-xs font-mono"
                      required
                    />
                  </div>
                )}
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 text-xs text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createLoading}
                  className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg shadow-lg shadow-indigo-900/30 transition-colors disabled:opacity-50"
                >
                  {createLoading ? 'Creating Plan...' : 'Create Remediation Plan'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
