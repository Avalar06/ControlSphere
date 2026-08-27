import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertOctagon,
  AlertTriangle,
  Clock,
  ExternalLink,
  Flame,
  Plus,
  RefreshCw,
  Search,
  ShieldAlert,
  ShieldCheck,
  Zap,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { incidentService } from '../lib/incidentService';
import { api } from '../lib/api';
import type {
  ComplianceDriftAlert,
  IncidentCategory,
  IncidentCreate,
  IncidentOverviewResponse,
  IncidentSeverity,
  IncidentStatus,
  SecurityIncident,
  User,
} from '../types';

export const IncidentsPage: React.FC = () => {
  const navigate = useNavigate();
  const { hasRole } = useAuth();
  const canManage = hasRole('ADMIN', 'GRC_ANALYST', 'SECURITY_ANALYST', 'MANAGER');

  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState<IncidentOverviewResponse | null>(null);
  const [incidents, setIncidents] = useState<SecurityIncident[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [driftAlerts, setDriftAlerts] = useState<ComplianceDriftAlert[]>([]);

  // Filters
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [categoryFilter, setCategoryFilter] = useState<string>('ALL');
  const [materialFilter, setMaterialFilter] = useState<string>('ALL');

  // Declare Incident Modal
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createForm, setCreateForm] = useState<IncidentCreate>({
    incident_code: '',
    title: '',
    description: '',
    severity: 'MEDIUM',
    category: 'DATA_BREACH',
    detected_at: new Date().toISOString().slice(0, 16),
    affected_record_count: 0,
    financial_impact_estimate: 0,
    business_owner_id: undefined,
    compliance_drift_alert_id: undefined,
  });
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [overviewData, incidentsData, usersData, alertsData] = await Promise.all([
        incidentService.getOverview().catch(() => null),
        incidentService.listIncidents().catch(() => []),
        api.get<User[]>('/users').then((r) => r.data).catch(() => []),
        api.get<ComplianceDriftAlert[]>('/monitoring/alerts').then((r) => r.data).catch(() => []),
      ]);
      setOverview(overviewData);
      setIncidents(incidentsData);
      setUsers(usersData);
      setDriftAlerts(alertsData);
    } catch (err) {
      console.error('Failed to load incident management data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreateIncident = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createForm.incident_code.trim() || !createForm.title.trim() || !createForm.description.trim()) {
      setCreateError('Incident code, title, and description are required.');
      return;
    }

    setCreateLoading(true);
    setCreateError(null);
    try {
      const detectedIso = new Date(createForm.detected_at).toISOString();
      const newInc = await incidentService.createIncident({
        incident_code: createForm.incident_code.trim().toUpperCase(),
        title: createForm.title.trim(),
        description: createForm.description.trim(),
        severity: createForm.severity,
        category: createForm.category,
        detected_at: detectedIso,
        affected_record_count: Number(createForm.affected_record_count) || 0,
        financial_impact_estimate: Number(createForm.financial_impact_estimate) || 0,
        business_owner_id: createForm.business_owner_id || undefined,
        compliance_drift_alert_id: createForm.compliance_drift_alert_id || undefined,
      });
      setShowCreateModal(false);
      setCreateForm({
        incident_code: '',
        title: '',
        description: '',
        severity: 'MEDIUM',
        category: 'DATA_BREACH',
        detected_at: new Date().toISOString().slice(0, 16),
        affected_record_count: 0,
        financial_impact_estimate: 0,
        business_owner_id: undefined,
        compliance_drift_alert_id: undefined,
      });
      await fetchData();
      navigate(`/incidents/${newInc.id}`);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setCreateError(typeof detail === 'string' ? detail : 'Failed to declare incident.');
    } finally {
      setCreateLoading(false);
    }
  };

  // Filtered incidents
  const filteredIncidents = incidents.filter((inc) => {
    if (statusFilter !== 'ALL' && inc.status !== statusFilter) return false;
    if (severityFilter !== 'ALL' && inc.severity !== severityFilter) return false;
    if (categoryFilter !== 'ALL' && inc.category !== categoryFilter) return false;
    if (materialFilter === 'MATERIAL_ONLY' && !inc.is_material) return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      return (
        inc.incident_code.toLowerCase().includes(q) ||
        inc.title.toLowerCase().includes(q) ||
        inc.description.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const getSeverityBadge = (severity: IncidentSeverity) => {
    switch (severity) {
      case 'CRITICAL':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300">CRITICAL</span>;
      case 'HIGH':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-orange-100 text-orange-800 dark:bg-orange-950 dark:text-orange-300">HIGH</span>;
      case 'MEDIUM':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-yellow-100 text-yellow-800 dark:bg-yellow-950 dark:text-yellow-300">MEDIUM</span>;
      case 'LOW':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300">LOW</span>;
      default:
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-800">{severity}</span>;
    }
  };

  const getStatusBadge = (status: IncidentStatus) => {
    switch (status) {
      case 'DECLARED':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300">DECLARED</span>;
      case 'TRIAGED':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300">TRIAGED</span>;
      case 'CONTAINED':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-yellow-100 text-yellow-800 dark:bg-yellow-950 dark:text-yellow-300">CONTAINED</span>;
      case 'ERADICATED':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-800 dark:bg-indigo-950 dark:text-indigo-300">ERADICATED</span>;
      case 'RECOVERED':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-cyan-100 text-cyan-800 dark:bg-cyan-950 dark:text-cyan-300">RECOVERED</span>;
      case 'POST_MORTEM':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300">POST_MORTEM</span>;
      case 'CLOSED':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">CLOSED</span>;
      default:
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-800">{status}</span>;
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              Security Incident Response & Breach Governance
            </h1>
            <span className="px-2.5 py-0.5 text-xs font-bold bg-red-600 text-white rounded-full">
              Phase 10
            </span>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Reactive incident command, four-eyes forensic closure, and statutory regulatory disclosure tracking.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchData}
            disabled={loading}
            className="inline-flex items-center px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 transition"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          {canManage && (
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-lg shadow-sm transition"
            >
              <Plus className="w-4 h-4 mr-2" />
              Declare Security Incident
            </button>
          )}
        </div>
      </div>

      {/* Executive KPI Cards */}
      {overview && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                Total Incidents
              </span>
              <ShieldAlert className="w-4 h-4 text-gray-400" />
            </div>
            <div className="text-2xl font-bold text-gray-900 dark:text-white mt-2">
              {overview.total_incidents}
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {overview.open_incidents} active response
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-red-200 dark:border-red-900/50 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-red-600 dark:text-red-400 uppercase font-semibold">
                Critical / High
              </span>
              <Flame className="w-4 h-4 text-red-500" />
            </div>
            <div className="text-2xl font-bold text-red-600 dark:text-red-400 mt-2">
              {overview.critical_or_high_incidents}
            </div>
            <div className="text-xs text-red-500 mt-1">High priority containment</div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-purple-200 dark:border-purple-900/50 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-purple-600 dark:text-purple-400 uppercase font-semibold">
                SEC Material
              </span>
              <AlertOctagon className="w-4 h-4 text-purple-500" />
            </div>
            <div className="text-2xl font-bold text-purple-600 dark:text-purple-400 mt-2">
              {overview.material_incidents}
            </div>
            <div className="text-xs text-purple-500 mt-1">Item 1.05 Form 8-K</div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-amber-200 dark:border-amber-900/50 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-amber-600 dark:text-amber-400 uppercase font-semibold">
                Overdue Disclosures
              </span>
              <AlertTriangle className="w-4 h-4 text-amber-500" />
            </div>
            <div className="text-2xl font-bold text-amber-600 dark:text-amber-400 mt-2">
              {overview.overdue_disclosures}
            </div>
            <div className="text-xs text-amber-500 mt-1">Statutory breach alert</div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                Avg TTC (Hours)
              </span>
              <Clock className="w-4 h-4 text-blue-500" />
            </div>
            <div className="text-2xl font-bold text-gray-900 dark:text-white mt-2">
              {overview.average_ttc_hours !== null && overview.average_ttc_hours !== undefined
                ? `${overview.average_ttc_hours}h`
                : '—'}
            </div>
            <div className="text-xs text-gray-500 mt-1">Time to Containment</div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                Avg MTTR (Hours)
              </span>
              <Zap className="w-4 h-4 text-emerald-500" />
            </div>
            <div className="text-2xl font-bold text-gray-900 dark:text-white mt-2">
              {overview.average_mttr_hours !== null && overview.average_mttr_hours !== undefined
                ? `${overview.average_mttr_hours}h`
                : '—'}
            </div>
            <div className="text-xs text-gray-500 mt-1">Mean Time to Recover</div>
          </div>
        </div>
      )}

      {/* Filter & Search Bar */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700 shadow-sm space-y-3">
        <div className="flex flex-col md:flex-row items-center gap-3">
          <div className="relative flex-1 w-full">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search by incident code, title, or narrative..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-red-500 focus:border-transparent transition"
            />
          </div>
          <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-xs font-medium bg-white dark:bg-gray-750 text-gray-800 dark:text-gray-200"
            >
              <option value="ALL">All Lifecycle Statuses</option>
              <option value="DECLARED">DECLARED</option>
              <option value="TRIAGED">TRIAGED</option>
              <option value="CONTAINED">CONTAINED</option>
              <option value="ERADICATED">ERADICATED</option>
              <option value="RECOVERED">RECOVERED</option>
              <option value="POST_MORTEM">POST_MORTEM</option>
              <option value="CLOSED">CLOSED</option>
            </select>

            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-xs font-medium bg-white dark:bg-gray-750 text-gray-800 dark:text-gray-200"
            >
              <option value="ALL">All Severities</option>
              <option value="CRITICAL">CRITICAL</option>
              <option value="HIGH">HIGH</option>
              <option value="MEDIUM">MEDIUM</option>
              <option value="LOW">LOW</option>
            </select>

            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-xs font-medium bg-white dark:bg-gray-750 text-gray-800 dark:text-gray-200"
            >
              <option value="ALL">All Categories</option>
              <option value="DATA_BREACH">DATA_BREACH</option>
              <option value="RANSOMWARE">RANSOMWARE</option>
              <option value="SUPPLY_CHAIN_COMPROMISE">SUPPLY_CHAIN</option>
              <option value="UNAUTHORIZED_ACCESS">UNAUTHORIZED_ACCESS</option>
              <option value="DENIAL_OF_SERVICE">DENIAL_OF_SERVICE</option>
              <option value="INSIDER_THREAT">INSIDER_THREAT</option>
              <option value="OTHER">OTHER</option>
            </select>

            <select
              value={materialFilter}
              onChange={(e) => setMaterialFilter(e.target.value)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-xs font-medium bg-white dark:bg-gray-750 text-gray-800 dark:text-gray-200"
            >
              <option value="ALL">All Materiality</option>
              <option value="MATERIAL_ONLY">SEC Material Only</option>
            </select>
          </div>
        </div>
      </div>

      {/* Incident Portfolio Table */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-gray-600 dark:text-gray-300">
            <thead className="bg-gray-50 dark:bg-gray-900/60 text-xs uppercase font-semibold text-gray-700 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
              <tr>
                <th className="px-6 py-4">Incident Code & Title</th>
                <th className="px-6 py-4">Severity</th>
                <th className="px-6 py-4">Category</th>
                <th className="px-6 py-4">Lifecycle Status</th>
                <th className="px-6 py-4">Materiality</th>
                <th className="px-6 py-4">Affected Records</th>
                <th className="px-6 py-4">Declared At</th>
                <th className="px-6 py-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {loading ? (
                <tr>
                  <td colSpan={8} className="px-6 py-12 text-center text-gray-400">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
                    Loading security incident records...
                  </td>
                </tr>
              ) : filteredIncidents.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-6 py-12 text-center text-gray-400">
                    <ShieldCheck className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
                    No security incidents match the selected filters.
                  </td>
                </tr>
              ) : (
                filteredIncidents.map((inc) => (
                  <tr
                    key={inc.id}
                    onClick={() => navigate(`/incidents/${inc.id}`)}
                    className="hover:bg-gray-50 dark:hover:bg-gray-750/50 cursor-pointer transition"
                  >
                    <td className="px-6 py-4 font-medium text-gray-900 dark:text-white">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs text-red-600 dark:text-red-400 font-bold">
                          {inc.incident_code}
                        </span>
                        <span className="truncate max-w-xs">{inc.title}</span>
                      </div>
                      <p className="text-xs text-gray-400 truncate max-w-xs mt-0.5">
                        {inc.description}
                      </p>
                    </td>
                    <td className="px-6 py-4">{getSeverityBadge(inc.severity)}</td>
                    <td className="px-6 py-4 text-xs font-mono text-gray-500 dark:text-gray-400">
                      {inc.category}
                    </td>
                    <td className="px-6 py-4">{getStatusBadge(inc.status)}</td>
                    <td className="px-6 py-4">
                      {inc.is_material ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300">
                          SEC 8-K
                        </span>
                      ) : (
                        <span className="text-xs text-gray-400">Non-Material</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-xs font-mono">
                      {inc.affected_record_count.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 text-xs text-gray-500">
                      {new Date(inc.declared_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/incidents/${inc.id}`);
                        }}
                        className="inline-flex items-center text-xs font-semibold text-red-600 dark:text-red-400 hover:underline"
                      >
                        Command <ExternalLink className="w-3 h-3 ml-1" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Declare Incident Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="bg-white dark:bg-gray-800 rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-gray-200 dark:border-gray-700 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-4 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-2">
                <Flame className="w-5 h-5 text-red-600" />
                <h3 className="text-lg font-bold text-gray-900 dark:text-white">
                  Declare New Security Incident
                </h3>
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
              >
                ✕
              </button>
            </div>

            {createError && (
              <div className="mt-4 p-3 bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-700 dark:text-red-300">
                {createError}
              </div>
            )}

            <form onSubmit={handleCreateIncident} className="mt-4 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                    Incident Code *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. INC-2026-001"
                    value={createForm.incident_code}
                    onChange={(e) =>
                      setCreateForm({ ...createForm, incident_code: e.target.value.toUpperCase() })
                    }
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white font-mono"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                    Severity *
                  </label>
                  <select
                    value={createForm.severity}
                    onChange={(e) =>
                      setCreateForm({ ...createForm, severity: e.target.value as IncidentSeverity })
                    }
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white"
                  >
                    <option value="CRITICAL">CRITICAL</option>
                    <option value="HIGH">HIGH</option>
                    <option value="MEDIUM">MEDIUM</option>
                    <option value="LOW">LOW</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                  Incident Title *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Production Database Unauthorized Exfiltration Attempt"
                  value={createForm.title}
                  onChange={(e) => setCreateForm({ ...createForm, title: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                    Category *
                  </label>
                  <select
                    value={createForm.category}
                    onChange={(e) =>
                      setCreateForm({ ...createForm, category: e.target.value as IncidentCategory })
                    }
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white"
                  >
                    <option value="DATA_BREACH">DATA_BREACH</option>
                    <option value="RANSOMWARE">RANSOMWARE</option>
                    <option value="SUPPLY_CHAIN_COMPROMISE">SUPPLY_CHAIN_COMPROMISE</option>
                    <option value="UNAUTHORIZED_ACCESS">UNAUTHORIZED_ACCESS</option>
                    <option value="DENIAL_OF_SERVICE">DENIAL_OF_SERVICE</option>
                    <option value="INSIDER_THREAT">INSIDER_THREAT</option>
                    <option value="OTHER">OTHER</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                    Detected Timestamp *
                  </label>
                  <input
                    type="datetime-local"
                    required
                    value={createForm.detected_at}
                    onChange={(e) => setCreateForm({ ...createForm, detected_at: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                  Incident Narrative / Description *
                </label>
                <textarea
                  rows={3}
                  required
                  placeholder="Provide technical synopsis of detection vector, affected telemetry, and initial triage indicators..."
                  value={createForm.description}
                  onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                    Affected Records Count
                  </label>
                  <input
                    type="number"
                    min={0}
                    value={createForm.affected_record_count}
                    onChange={(e) =>
                      setCreateForm({
                        ...createForm,
                        affected_record_count: Math.max(0, parseInt(e.target.value, 10) || 0),
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                    Financial Impact Estimate ($)
                  </label>
                  <input
                    type="number"
                    min={0}
                    step={0.01}
                    value={createForm.financial_impact_estimate}
                    onChange={(e) =>
                      setCreateForm({
                        ...createForm,
                        financial_impact_estimate: Math.max(0, parseFloat(e.target.value) || 0),
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                    Business Owner
                  </label>
                  <select
                    value={createForm.business_owner_id || ''}
                    onChange={(e) =>
                      setCreateForm({
                        ...createForm,
                        business_owner_id: e.target.value ? parseInt(e.target.value, 10) : undefined,
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white"
                  >
                    <option value="">None / Unassigned</option>
                    {users.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.full_name || u.email} ({u.role})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold uppercase text-gray-700 dark:text-gray-300 mb-1">
                    Link CCM Drift Alert (Optional)
                  </label>
                  <select
                    value={createForm.compliance_drift_alert_id || ''}
                    onChange={(e) =>
                      setCreateForm({
                        ...createForm,
                        compliance_drift_alert_id: e.target.value
                          ? parseInt(e.target.value, 10)
                          : undefined,
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-750 text-gray-900 dark:text-white"
                  >
                    <option value="">None / Independent Detection</option>
                    {driftAlerts.map((a) => (
                      <option key={a.id} value={a.id}>
                        #{a.id} - {a.title} ({a.severity})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-700 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createLoading}
                  className="px-5 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium shadow-sm transition disabled:opacity-50"
                >
                  {createLoading ? 'Declaring...' : 'Declare Incident'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
