import React, { useEffect, useState } from 'react';
import {
  Activity,
  AlertOctagon,
  AlertTriangle,
  Bell,
  CheckCircle2,
  FileCheck,
  Filter,
  History,
  Layers,
  Play,
  RefreshCw,
  Search,
  Shield,
  ShieldCheck,
  Sliders,
  XCircle,
} from 'lucide-react';
import { monitoringService } from '../lib/monitoringService';
import type {
  ComplianceDriftAlert,
  ControlHealthSnapshot,
  ControlHealthStatus,
  ControlHealthSummary,
  DriftAlertSeverity,
  EvaluationRunResult,
  MonitoringConfig,
  MonitoringOverview,
} from '../types';

export const ContinuousMonitoringPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'registry' | 'alerts' | 'config'>('registry');
  const [overview, setOverview] = useState<MonitoringOverview | null>(null);
  const [controls, setControls] = useState<ControlHealthSummary[]>([]);
  const [alerts, setAlerts] = useState<ComplianceDriftAlert[]>([]);
  const [config, setConfig] = useState<MonitoringConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState(false);
  const [evalResult, setEvalResult] = useState<EvaluationRunResult | null>(null);

  // Filters
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');

  // History modal
  const [selectedControlHistory, setSelectedControlHistory] = useState<{
    code: string;
    snapshots: ControlHealthSnapshot[];
  } | null>(null);

  // Alert Action Modals
  const [resolveModalAlert, setResolveModalAlert] = useState<ComplianceDriftAlert | null>(null);
  const [resolutionNotes, setResolutionNotes] = useState('');
  const [dismissModalAlert, setDismissModalAlert] = useState<ComplianceDriftAlert | null>(null);
  const [dismissJustification, setDismissJustification] = useState('');

  // Config form state
  const [configForm, setConfigForm] = useState<Partial<MonitoringConfig>>({});
  const [configSaving, setConfigSaving] = useState(false);
  const [configSavedSuccess, setConfigSavedSuccess] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [overviewData, controlsData, alertsData, configData] = await Promise.all([
        monitoringService.getOverview(),
        monitoringService.listControlHealth(),
        monitoringService.listAlerts(),
        monitoringService.getConfig(),
      ]);
      setOverview(overviewData);
      setControls(controlsData);
      setAlerts(alertsData);
      setConfig(configData);
      setConfigForm(configData);
    } catch (err) {
      console.error('Failed to load continuous monitoring telemetry:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleRunEvaluation = async () => {
    setEvaluating(true);
    try {
      const result = await monitoringService.triggerEvaluation();
      setEvalResult(result);
      await fetchData();
    } catch (err) {
      console.error('Evaluation run failed:', err);
    } finally {
      setEvaluating(false);
    }
  };

  const handleAcknowledgeAlert = async (alertId: number) => {
    try {
      await monitoringService.acknowledgeAlert(alertId);
      await fetchData();
    } catch (err) {
      console.error('Failed to acknowledge alert:', err);
    }
  };

  const handleResolveAlert = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resolveModalAlert || !resolutionNotes.trim()) return;
    try {
      await monitoringService.resolveAlert(resolveModalAlert.id, resolutionNotes);
      setResolveModalAlert(null);
      setResolutionNotes('');
      await fetchData();
    } catch (err) {
      console.error('Failed to resolve alert:', err);
    }
  };

  const handleDismissAlert = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!dismissModalAlert || !dismissJustification.trim()) return;
    try {
      await monitoringService.dismissAlert(dismissModalAlert.id, dismissJustification);
      setDismissModalAlert(null);
      setDismissJustification('');
      await fetchData();
    } catch (err) {
      console.error('Failed to dismiss alert:', err);
    }
  };

  const handleSaveConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    setConfigSaving(true);
    setConfigSavedSuccess(false);
    try {
      const updated = await monitoringService.updateConfig(configForm);
      setConfig(updated);
      setConfigSavedSuccess(true);
      setTimeout(() => setConfigSavedSuccess(false), 3000);
    } catch (err) {
      console.error('Failed to save monitoring config:', err);
    } finally {
      setConfigSaving(false);
    }
  };

  const viewHistory = async (ctrl: ControlHealthSummary) => {
    try {
      const history = await monitoringService.getControlHistory(ctrl.organization_control_id);
      setSelectedControlHistory({
        code: ctrl.control_code || `Control #${ctrl.organization_control_id}`,
        snapshots: history,
      });
    } catch (err) {
      console.error('Failed to fetch history:', err);
    }
  };

  const getStatusBadge = (status: ControlHealthStatus) => {
    switch (status) {
      case 'HEALTHY':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950/60 text-emerald-400 border border-emerald-800/60">
            <ShieldCheck className="w-3.5 h-3.5 mr-1" /> HEALTHY
          </span>
        );
      case 'DEGRADED':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-950/60 text-amber-400 border border-amber-800/60">
            <AlertTriangle className="w-3.5 h-3.5 mr-1" /> DEGRADED
          </span>
        );
      case 'AT_RISK':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-orange-950/60 text-orange-400 border border-orange-800/60">
            <AlertOctagon className="w-3.5 h-3.5 mr-1" /> AT RISK
          </span>
        );
      case 'FAILING':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-950/60 text-rose-400 border border-rose-800/60">
            <XCircle className="w-3.5 h-3.5 mr-1" /> FAILING
          </span>
        );
      default:
        return null;
    }
  };

  const getSeverityBadge = (severity: DriftAlertSeverity) => {
    switch (severity) {
      case 'CRITICAL':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-rose-950 text-rose-300 border border-rose-800">
            CRITICAL
          </span>
        );
      case 'HIGH':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-orange-950 text-orange-300 border border-orange-800">
            HIGH
          </span>
        );
      case 'MEDIUM':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-amber-950 text-amber-300 border border-amber-800">
            MEDIUM
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-800 text-slate-300 border border-slate-700">
            {severity}
          </span>
        );
    }
  };

  const filteredControls = controls.filter((ctrl) => {
    const matchesSearch =
      !search ||
      (ctrl.control_code && ctrl.control_code.toLowerCase().includes(search.toLowerCase())) ||
      (ctrl.control_title && ctrl.control_title.toLowerCase().includes(search.toLowerCase()));
    const matchesStatus = statusFilter === 'ALL' || ctrl.health_status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const filteredAlerts = alerts.filter((alert) => {
    const matchesSeverity = severityFilter === 'ALL' || alert.severity === severityFilter;
    return matchesSeverity;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-slate-900/80 p-6 rounded-xl border border-slate-800 shadow-xl backdrop-blur-sm">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-blue-500/10 border border-blue-500/30 rounded-lg text-blue-400">
              <Activity className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold text-slate-100">Continuous Control Monitoring</h1>
                <span className="px-2 py-0.5 text-xs font-semibold rounded bg-blue-900/60 text-blue-300 border border-blue-700/60">
                  Phase 7 Telemetry
                </span>
              </div>
              <p className="text-sm text-slate-400 mt-0.5">
                Automated health signals, deterministic telemetry, and real-time compliance drift detection.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchData}
            disabled={loading}
            className="px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-sm font-medium transition flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>
          <button
            onClick={handleRunEvaluation}
            disabled={evaluating}
            className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold shadow-lg shadow-blue-900/40 transition flex items-center gap-2"
          >
            <Play className={`w-4 h-4 ${evaluating ? 'animate-spin' : ''}`} />
            {evaluating ? 'Evaluating Telemetry...' : 'Run Evaluation Engine'}
          </button>
        </div>
      </div>

      {/* Evaluation Result Toast Banner */}
      {evalResult && (
        <div className="p-4 rounded-xl bg-blue-950/60 border border-blue-800 text-blue-200 flex items-center justify-between animate-fadeIn">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-blue-400" />
            <span className="text-sm">
              Evaluation Run Complete: Evaluated <strong>{evalResult.evaluated_controls_count}</strong> controls. Generated <strong>{evalResult.alerts_generated_count}</strong> drift alerts. Organization Health Average: <strong>{evalResult.average_health_score}%</strong>.
            </span>
          </div>
          <button
            onClick={() => setEvalResult(null)}
            className="text-xs text-blue-400 hover:text-blue-200 uppercase font-semibold tracking-wider"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* KPI Overview Cards */}
      {overview && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-slate-900/60 p-5 rounded-xl border border-slate-800/80 shadow-md">
            <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
              <span>Overall Health Score</span>
              <Activity className="w-4 h-4 text-blue-400" />
            </div>
            <div className="mt-3 flex items-baseline gap-3">
              <span className="text-3xl font-extrabold text-slate-100">
                {overview.average_health_score}%
              </span>
              {getStatusBadge(overview.overall_health_status)}
            </div>
            <div className="mt-2 text-xs text-slate-400">
              Across {overview.total_monitored_controls} controls
            </div>
          </div>

          <div className="bg-slate-900/60 p-5 rounded-xl border border-slate-800/80 shadow-md">
            <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
              <span>Control Distribution</span>
              <Layers className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="mt-3 grid grid-cols-4 gap-2 text-center">
              <div className="bg-emerald-950/40 border border-emerald-900/60 p-1.5 rounded">
                <div className="text-xs text-emerald-400 font-bold">{overview.healthy_controls_count}</div>
                <div className="text-[10px] text-emerald-500">Healthy</div>
              </div>
              <div className="bg-amber-950/40 border border-amber-900/60 p-1.5 rounded">
                <div className="text-xs text-amber-400 font-bold">{overview.degraded_controls_count}</div>
                <div className="text-[10px] text-amber-500">Degraded</div>
              </div>
              <div className="bg-orange-950/40 border border-orange-900/60 p-1.5 rounded">
                <div className="text-xs text-orange-400 font-bold">{overview.at_risk_controls_count}</div>
                <div className="text-[10px] text-orange-500">At Risk</div>
              </div>
              <div className="bg-rose-950/40 border border-rose-900/60 p-1.5 rounded">
                <div className="text-xs text-rose-400 font-bold">{overview.failing_controls_count}</div>
                <div className="text-[10px] text-rose-500">Failing</div>
              </div>
            </div>
          </div>

          <div className="bg-slate-900/60 p-5 rounded-xl border border-slate-800/80 shadow-md">
            <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
              <span>Active Drift Alerts</span>
              <Bell className="w-4 h-4 text-rose-400" />
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-3xl font-extrabold text-rose-400">
                {overview.active_drift_alerts_count}
              </span>
              <span className="text-xs text-rose-300/80">
                ({overview.critical_drift_alerts_count} Critical, {overview.high_drift_alerts_count} High)
              </span>
            </div>
            <div className="mt-2 text-xs text-slate-400">Requires action or resolution</div>
          </div>

          <div className="bg-slate-900/60 p-5 rounded-xl border border-slate-800/80 shadow-md">
            <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
              <span>Telemetry Freshness</span>
              <FileCheck className="w-4 h-4 text-indigo-400" />
            </div>
            <div className="mt-3 space-y-1.5">
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">Evidence Freshness:</span>
                <span className="text-indigo-300 font-semibold">{overview.evidence_freshness_aggregate_pct}%</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">Assessment Currency:</span>
                <span className="text-indigo-300 font-semibold">{overview.controls_assessed_currency_pct}%</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab('registry')}
          className={`px-4 py-2 rounded-lg text-sm font-semibold transition flex items-center gap-2 ${
            activeTab === 'registry'
              ? 'bg-blue-600 text-white shadow-md'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <Shield className="w-4 h-4" /> Control Health Registry ({controls.length})
        </button>
        <button
          onClick={() => setActiveTab('alerts')}
          className={`px-4 py-2 rounded-lg text-sm font-semibold transition flex items-center gap-2 ${
            activeTab === 'alerts'
              ? 'bg-blue-600 text-white shadow-md'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <AlertOctagon className="w-4 h-4" /> Compliance Drift Alerts ({alerts.length})
        </button>
        <button
          onClick={() => setActiveTab('config')}
          className={`px-4 py-2 rounded-lg text-sm font-semibold transition flex items-center gap-2 ${
            activeTab === 'config'
              ? 'bg-blue-600 text-white shadow-md'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <Sliders className="w-4 h-4" /> Monitoring Settings
        </button>
      </div>

      {/* TAB 1: CONTROL HEALTH REGISTRY */}
      {activeTab === 'registry' && (
        <div className="space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 bg-slate-900/60 p-4 rounded-xl border border-slate-800">
            <div className="relative flex-1 max-w-md">
              <Search className="w-4 h-4 absolute left-3 top-3 text-slate-500" />
              <input
                type="text"
                placeholder="Search control code or title..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-9 pr-4 py-2 rounded-lg bg-slate-800/80 border border-slate-700 text-slate-200 text-sm focus:outline-none focus:border-blue-500"
              />
            </div>
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-slate-400" />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 text-sm focus:outline-none focus:border-blue-500"
              >
                <option value="ALL">All Health States</option>
                <option value="HEALTHY">Healthy</option>
                <option value="DEGRADED">Degraded</option>
                <option value="AT_RISK">At Risk</option>
                <option value="FAILING">Failing</option>
              </select>
            </div>
          </div>

          <div className="bg-slate-900/80 rounded-xl border border-slate-800 overflow-hidden shadow-xl">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="bg-slate-950/60 text-slate-400 text-xs font-semibold uppercase tracking-wider border-b border-slate-800">
                  <tr>
                    <th className="px-5 py-3.5">Control</th>
                    <th className="px-5 py-3.5">Health Score</th>
                    <th className="px-5 py-3.5">Freshness</th>
                    <th className="px-5 py-3.5">Currency</th>
                    <th className="px-5 py-3.5">Findings / Exceptions</th>
                    <th className="px-5 py-3.5">Active Alerts</th>
                    <th className="px-5 py-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {filteredControls.map((ctrl) => (
                    <tr key={ctrl.organization_control_id} className="hover:bg-slate-800/40 transition">
                      <td className="px-5 py-4">
                        <div className="font-semibold text-slate-100">{ctrl.control_code}</div>
                        <div className="text-xs text-slate-400 line-clamp-1 max-w-sm">{ctrl.control_title}</div>
                      </td>
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-slate-200">{ctrl.health_score}%</span>
                          {getStatusBadge(ctrl.health_status)}
                        </div>
                      </td>
                      <td className="px-5 py-4">
                        <div className="text-xs font-medium text-slate-300">{ctrl.evidence_freshness_score}%</div>
                        <div className="text-[11px] text-slate-500">
                          {ctrl.days_since_last_evidence !== null && ctrl.days_since_last_evidence !== undefined
                            ? `${ctrl.days_since_last_evidence}d ago`
                            : 'No evidence'}
                        </div>
                      </td>
                      <td className="px-5 py-4">
                        <div className="text-xs font-medium text-slate-300">{ctrl.assessment_currency_score}%</div>
                        <div className="text-[11px] text-slate-500">
                          {ctrl.implementation_status}
                        </div>
                      </td>
                      <td className="px-5 py-4">
                        <div className="text-xs text-slate-300">
                          Findings: <strong>{ctrl.active_findings_count}</strong> ({ctrl.critical_high_findings_count} Crit/High)
                        </div>
                        <div className="text-[11px] text-slate-500">
                          Exceptions: {ctrl.active_exceptions_count}
                        </div>
                      </td>
                      <td className="px-5 py-4">
                        {ctrl.active_drift_alerts_count > 0 ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-rose-950/80 text-rose-300 border border-rose-800/60">
                            {ctrl.active_drift_alerts_count} Active
                          </span>
                        ) : (
                          <span className="text-xs text-emerald-400 flex items-center gap-1">
                            <CheckCircle2 className="w-3.5 h-3.5" /> Normal
                          </span>
                        )}
                      </td>
                      <td className="px-5 py-4 text-right">
                        <button
                          onClick={() => viewHistory(ctrl)}
                          className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
                          title="View Telemetry History"
                        >
                          <History className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                  {filteredControls.length === 0 && (
                    <tr>
                      <td colSpan={7} className="px-5 py-8 text-center text-slate-500">
                        No controls match the specified criteria.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: COMPLIANCE DRIFT ALERTS */}
      {activeTab === 'alerts' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between bg-slate-900/60 p-4 rounded-xl border border-slate-800">
            <div className="text-sm text-slate-400">
              Active & historical compliance drift notifications generated by continuous monitoring.
            </div>
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-slate-400" />
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 text-sm focus:outline-none focus:border-blue-500"
              >
                <option value="ALL">All Severities</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>
            </div>
          </div>

          <div className="bg-slate-900/80 rounded-xl border border-slate-800 overflow-hidden shadow-xl">
            <div className="divide-y divide-slate-800/60">
              {filteredAlerts.map((alert) => (
                <div key={alert.id} className="p-5 hover:bg-slate-800/40 transition">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                    <div className="space-y-1.5">
                      <div className="flex items-center gap-2.5">
                        {getSeverityBadge(alert.severity)}
                        <span className="font-semibold text-slate-100">{alert.title}</span>
                        <span
                          className={`text-xs px-2 py-0.5 rounded font-mono ${
                            alert.status === 'ACTIVE'
                              ? 'bg-rose-950 text-rose-300'
                              : alert.status === 'ACKNOWLEDGED'
                              ? 'bg-amber-950 text-amber-300'
                              : alert.status === 'RESOLVED'
                              ? 'bg-emerald-950 text-emerald-300'
                              : 'bg-slate-800 text-slate-400'
                          }`}
                        >
                          {alert.status}
                        </span>
                      </div>
                      <p className="text-sm text-slate-400">{alert.description}</p>
                      {alert.remediation_guidance && (
                        <div className="text-xs text-blue-300/90 bg-blue-950/30 p-2 rounded border border-blue-900/40">
                          <strong>Remediation:</strong> {alert.remediation_guidance}
                        </div>
                      )}
                      {alert.resolution_notes && (
                        <div className="text-xs text-emerald-300/90 bg-emerald-950/30 p-2 rounded border border-emerald-900/40">
                          <strong>Resolution:</strong> {alert.resolution_notes}
                        </div>
                      )}
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      {alert.status === 'ACTIVE' && (
                        <button
                          onClick={() => handleAcknowledgeAlert(alert.id)}
                          className="px-3 py-1.5 rounded-lg bg-amber-900/60 hover:bg-amber-800 text-amber-200 border border-amber-700/60 text-xs font-semibold transition"
                        >
                          Acknowledge
                        </button>
                      )}
                      {(alert.status === 'ACTIVE' || alert.status === 'ACKNOWLEDGED') && (
                        <>
                          <button
                            onClick={() => setResolveModalAlert(alert)}
                            className="px-3 py-1.5 rounded-lg bg-emerald-700 hover:bg-emerald-600 text-white text-xs font-semibold transition"
                          >
                            Resolve Alert
                          </button>
                          <button
                            onClick={() => setDismissModalAlert(alert)}
                            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs font-semibold transition"
                          >
                            Dismiss
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              {filteredAlerts.length === 0 && (
                <div className="p-8 text-center text-slate-500">No compliance drift alerts found.</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: MONITORING CONFIGURATION */}
      {activeTab === 'config' && config && (
        <div className="bg-slate-900/80 p-6 rounded-xl border border-slate-800 shadow-xl max-w-2xl">
          <h2 className="text-lg font-bold text-slate-100 mb-4 flex items-center gap-2">
            <Sliders className="w-5 h-5 text-blue-400" /> Continuous Telemetry Evaluation Policies
          </h2>
          <form onSubmit={handleSaveConfig} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">
                  Evidence Freshness Threshold (Days)
                </label>
                <input
                  type="number"
                  min={7}
                  max={365}
                  value={configForm.evidence_max_age_days ?? 90}
                  onChange={(e) =>
                    setConfigForm({ ...configForm, evidence_max_age_days: parseInt(e.target.value) || 90 })
                  }
                  className="w-full px-3.5 py-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 text-sm focus:outline-none focus:border-blue-500"
                />
                <span className="text-[11px] text-slate-500">Evidence older than this decays freshness score.</span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">
                  Assessment Currency Window (Days)
                </label>
                <input
                  type="number"
                  min={30}
                  max={730}
                  value={configForm.assessment_max_age_days ?? 180}
                  onChange={(e) =>
                    setConfigForm({ ...configForm, assessment_max_age_days: parseInt(e.target.value) || 180 })
                  }
                  className="w-full px-3.5 py-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 text-sm focus:outline-none focus:border-blue-500"
                />
                <span className="text-[11px] text-slate-500">Controls unassessed beyond this are flagged.</span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">
                  Critical Finding Remediation SLA (Days)
                </label>
                <input
                  type="number"
                  min={1}
                  max={90}
                  value={configForm.finding_sla_critical_days ?? 15}
                  onChange={(e) =>
                    setConfigForm({ ...configForm, finding_sla_critical_days: parseInt(e.target.value) || 15 })
                  }
                  className="w-full px-3.5 py-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 text-sm focus:outline-none focus:border-blue-500"
                />
                <span className="text-[11px] text-slate-500">SLA breach triggers critical drift alert.</span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">
                  High Finding Remediation SLA (Days)
                </label>
                <input
                  type="number"
                  min={1}
                  max={180}
                  value={configForm.finding_sla_high_days ?? 30}
                  onChange={(e) =>
                    setConfigForm({ ...configForm, finding_sla_high_days: parseInt(e.target.value) || 30 })
                  }
                  className="w-full px-3.5 py-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 text-sm focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">
                  Exception Expiration Warning (Days)
                </label>
                <input
                  type="number"
                  min={1}
                  max={60}
                  value={configForm.exception_warning_window_days ?? 14}
                  onChange={(e) =>
                    setConfigForm({ ...configForm, exception_warning_window_days: parseInt(e.target.value) || 14 })
                  }
                  className="w-full px-3.5 py-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 text-sm focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">
                  Automated Frequency (Hours)
                </label>
                <input
                  type="number"
                  min={1}
                  max={168}
                  value={configForm.frequency_hours ?? 24}
                  onChange={(e) =>
                    setConfigForm({ ...configForm, frequency_hours: parseInt(e.target.value) || 24 })
                  }
                  className="w-full px-3.5 py-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 text-sm focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>

            <div className="pt-4 flex items-center justify-between border-t border-slate-800">
              {configSavedSuccess && (
                <span className="text-xs text-emerald-400 font-semibold flex items-center gap-1">
                  <CheckCircle2 className="w-4 h-4" /> Settings updated successfully
                </span>
              )}
              <button
                type="submit"
                disabled={configSaving}
                className="ml-auto px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold shadow-md transition"
              >
                {configSaving ? 'Saving...' : 'Save Configuration'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* RESOLVE ALERT MODAL */}
      {resolveModalAlert && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" /> Formally Resolve Compliance Alert
            </h3>
            <p className="text-xs text-slate-400">
              Alert: <strong>{resolveModalAlert.title}</strong>
            </p>
            <form onSubmit={handleResolveAlert} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Mandatory Resolution Notes
                </label>
                <textarea
                  rows={4}
                  required
                  placeholder="Detail the corrective actions taken, artifacts verified, or justification..."
                  value={resolutionNotes}
                  onChange={(e) => setResolutionNotes(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 text-sm focus:outline-none focus:border-emerald-500"
                />
              </div>
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setResolveModalAlert(null)}
                  className="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 text-sm font-medium hover:bg-slate-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!resolutionNotes.trim()}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold shadow-md"
                >
                  Confirm Resolution
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* DISMISS ALERT MODAL */}
      {dismissModalAlert && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              <XCircle className="w-5 h-5 text-rose-400" /> Dismiss Compliance Drift Alert
            </h3>
            <p className="text-xs text-slate-400">
              Alert: <strong>{dismissModalAlert.title}</strong>
            </p>
            <form onSubmit={handleDismissAlert} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Mandatory Dismissal Justification
                </label>
                <textarea
                  rows={4}
                  required
                  placeholder="State reason for dismissal (e.g. false positive, maintenance window, decommissioned asset)..."
                  value={dismissJustification}
                  onChange={(e) => setDismissJustification(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 text-sm focus:outline-none focus:border-rose-500"
                />
              </div>
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setDismissModalAlert(null)}
                  className="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 text-sm font-medium hover:bg-slate-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!dismissJustification.trim()}
                  className="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-sm font-semibold shadow-md"
                >
                  Confirm Dismissal
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* TELEMETRY HISTORY MODAL */}
      {selectedControlHistory && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-2xl w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                <History className="w-5 h-5 text-blue-400" /> Historical Telemetry: {selectedControlHistory.code}
              </h3>
              <button
                onClick={() => setSelectedControlHistory(null)}
                className="text-slate-400 hover:text-slate-200"
              >
                ✕
              </button>
            </div>
            <div className="max-h-80 overflow-y-auto divide-y divide-slate-800">
              {selectedControlHistory.snapshots.map((s) => (
                <div key={s.id} className="py-3 flex items-center justify-between text-xs">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-slate-200">{s.health_score}%</span>
                      {getStatusBadge(s.health_status)}
                      <span className="text-slate-500">via {s.evaluation_trigger}</span>
                    </div>
                    <div className="text-slate-400 mt-1">
                      Freshness: {s.evidence_freshness_score}% | Findings Penalty: -{s.finding_penalty_score}
                    </div>
                  </div>
                  <div className="text-slate-500 font-mono">
                    {new Date(s.evaluated_at).toLocaleString()}
                  </div>
                </div>
              ))}
              {selectedControlHistory.snapshots.length === 0 && (
                <div className="py-6 text-center text-slate-500 text-xs">No historical snapshots recorded yet.</div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
