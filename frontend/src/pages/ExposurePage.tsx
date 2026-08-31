import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { exposureService } from '../lib/exposureService';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Table, TableBody, TableCell, TableHead, TableHeaderCell, TableRow } from '../components/ui/Table';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { ExposureModal } from '../components/exposure/ExposureModal';
import { ExposureStatusModal } from '../components/exposure/ExposureStatusModal';
import { ExposureLineageCard } from '../components/exposure/ExposureLineageCard';
import type {
  ExposureSeverity,
  ExposureStatus,
  VulnerabilityExposure,
  VulnerabilityExposureCreate,
  VulnerabilityExposureUpdate,
} from '../types';
import {
  Activity,
  AlertOctagon,
  AlertTriangle,
  ArrowUpRight,
  Clock,
  Crosshair,
  Edit2,
  Flame,
  Layers,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Trash2,
} from 'lucide-react';

type TabKey = 'register' | 'posture' | 'lineage';

export const ExposurePage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { hasRole } = useAuth();

  const canManage = hasRole('ADMIN', 'MANAGER', 'SECURITY_ANALYST', 'GRC_ANALYST');

  const [activeTab, setActiveTab] = useState<TabKey>('register');
  const [searchQuery, setSearchQuery] = useState('');
  const [severityFilter, setSeverityFilter] = useState<ExposureSeverity | 'ALL'>('ALL');
  const [statusFilter, setStatusFilter] = useState<ExposureStatus | 'ALL'>('ALL');
  const [cisaKevOnly, setCisaKevOnly] = useState<boolean>(false);

  // Modals state
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [editingExposure, setEditingExposure] = useState<VulnerabilityExposure | null>(null);
  const [statusTransitionExposure, setStatusTransitionExposure] = useState<VulnerabilityExposure | null>(null);

  // Queries
  const {
    data: exposures = [],
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ['exposures-list', severityFilter, statusFilter, cisaKevOnly, searchQuery],
    queryFn: () =>
      exposureService.listExposures({
        severity: severityFilter === 'ALL' ? undefined : severityFilter,
        status: statusFilter === 'ALL' ? undefined : statusFilter,
        cisa_kev: cisaKevOnly ? true : undefined,
        search: searchQuery.trim() || undefined,
      }),
  });

  const { data: summary } = useQuery({
    queryKey: ['exposure-summary'],
    queryFn: () => exposureService.getPostureSummary(),
  });

  const createMutation = useMutation({
    mutationFn: (data: VulnerabilityExposureCreate) => exposureService.createExposure(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exposures-list'] });
      queryClient.invalidateQueries({ queryKey: ['exposure-summary'] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: VulnerabilityExposureUpdate }) =>
      exposureService.updateExposure(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exposures-list'] });
      queryClient.invalidateQueries({ queryKey: ['exposure-summary'] });
    },
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, status, notes }: { id: number; status: ExposureStatus; notes?: string }) =>
      exposureService.updateStatus(id, { status, notes }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exposures-list'] });
      queryClient.invalidateQueries({ queryKey: ['exposure-summary'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => exposureService.deleteExposure(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exposures-list'] });
      queryClient.invalidateQueries({ queryKey: ['exposure-summary'] });
    },
  });

  const getSeverityBadge = (sev: ExposureSeverity) => {
    switch (sev) {
      case 'CRITICAL':
        return <Badge variant="danger">CRITICAL</Badge>;
      case 'HIGH':
        return <Badge variant="warning">HIGH</Badge>;
      case 'MEDIUM':
        return <Badge variant="info">MEDIUM</Badge>;
      case 'LOW':
        return <Badge variant="default">LOW</Badge>;
      case 'INFORMATIONAL':
        return <Badge variant="default">INFO</Badge>;
      default:
        return <Badge variant="default">{sev}</Badge>;
    }
  };

  const getStatusBadge = (st: ExposureStatus) => {
    switch (st) {
      case 'OPEN':
        return <Badge variant="default">OPEN</Badge>;
      case 'UNDER_INVESTIGATION':
        return <Badge variant="info">INVESTIGATING</Badge>;
      case 'REMEDIATING':
        return <Badge variant="warning">REMEDIATING</Badge>;
      case 'EXCEPTION_REQUESTED':
        return <Badge variant="warning">EXCEPTION PENDING</Badge>;
      case 'EXCEPTION_APPROVED':
        return <Badge variant="info">EXCEPTION APPROVED</Badge>;
      case 'EXCEPTION_REJECTED':
        return <Badge variant="danger">EXCEPTION REJECTED</Badge>;
      case 'RESOLVED':
        return <Badge variant="success">RESOLVED</Badge>;
      default:
        return <Badge variant="default">{st}</Badge>;
    }
  };

  const getSlaDisplay = (slaDateStr: string, status: ExposureStatus) => {
    if (status === 'RESOLVED') {
      return <span className="text-xs text-slate-500 font-medium">Closed</span>;
    }
    const due = new Date(slaDateStr);
    const now = new Date();
    const diffHours = (due.getTime() - now.getTime()) / (1000 * 60 * 60);

    if (diffHours < 0) {
      return (
        <span className="inline-flex items-center gap-1 text-xs font-bold text-rose-400 bg-rose-950/40 px-2 py-0.5 rounded-full border border-rose-800/60">
          <AlertOctagon className="h-3 w-3" />
          BREACHED
        </span>
      );
    } else if (diffHours <= 72) {
      const days = Math.ceil(diffHours / 24);
      return (
        <span className="inline-flex items-center gap-1 text-xs font-bold text-amber-400 bg-amber-950/40 px-2 py-0.5 rounded-full border border-amber-800/60">
          <Clock className="h-3 w-3" />
          {days}d remaining
        </span>
      );
    } else {
      const days = Math.ceil(diffHours / 24);
      return (
        <span className="inline-flex items-center gap-1 text-xs text-slate-300">
          <Clock className="h-3 w-3 text-slate-500" />
          {days}d ({due.toLocaleDateString()})
        </span>
      );
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400">
              <Crosshair className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-100 flex items-center gap-2">
                Continuous Threat Exposure & Vulnerabilities
                <Badge variant="danger" className="text-[10px]">EXPOSURE-GRC</Badge>
              </h1>
              <p className="text-xs text-slate-400">
                Continuous threat exposure governance, weaponization intelligence, blast radius modeling, and four-eyes SLA control.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            className="flex items-center gap-1.5"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </Button>
          {canManage && (
            <Button
              variant="primary"
              size="sm"
              onClick={() => setIsCreateModalOpen(true)}
              className="flex items-center gap-1.5"
            >
              <Plus className="h-4 w-4" />
              Ingest Exposure
            </Button>
          )}
        </div>
      </div>

      {/* Executive Telemetry Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <Card className="p-4 bg-slate-900/60 border-slate-800 space-y-1">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Total Catalog</span>
          <div className="text-2xl font-bold text-slate-100">{summary?.total_exposures ?? exposures.length}</div>
          <span className="text-[10px] text-slate-500">Tracked CVE Exposures</span>
        </Card>

        <Card className="p-4 bg-slate-900/60 border-slate-800 space-y-1">
          <span className="text-[11px] font-semibold text-rose-400 uppercase tracking-wider">Critical & High</span>
          <div className="text-2xl font-bold text-rose-400">
            {(summary?.critical_exposures ?? 0) + (summary?.high_exposures ?? 0)}
          </div>
          <span className="text-[10px] text-slate-500">Severe Threat Surface</span>
        </Card>

        <Card className="p-4 bg-slate-900/60 border-slate-800 space-y-1">
          <span className="text-[11px] font-semibold text-rose-300 uppercase tracking-wider flex items-center gap-1">
            <Flame className="h-3 w-3 text-rose-400" /> CISA KEV
          </span>
          <div className="text-2xl font-bold text-rose-300">{summary?.cisa_kev_count ?? 0}</div>
          <span className="text-[10px] text-slate-500">Active Weaponized Zero-Days</span>
        </Card>

        <Card className="p-4 bg-slate-900/60 border-slate-800 space-y-1">
          <span className="text-[11px] font-semibold text-amber-400 uppercase tracking-wider">Active Exceptions</span>
          <div className="text-2xl font-bold text-amber-400">{summary?.active_exceptions_count ?? 0}</div>
          <span className="text-[10px] text-slate-500">Four-Eyes SLA Deferrals</span>
        </Card>

        <Card className="p-4 bg-slate-900/60 border-slate-800 space-y-1">
          <span className="text-[11px] font-semibold text-rose-400 uppercase tracking-wider">SLA Breached</span>
          <div className="text-2xl font-bold text-rose-400">
            {summary?.sla_breached_count ?? 0}
            <span className="text-xs font-normal text-slate-400 ml-1">
              ({summary?.sla_breach_rate_percent ?? 0}%)
            </span>
          </div>
          <span className="text-[10px] text-slate-500">Remediation Delinquency</span>
        </Card>

        <Card className="p-4 bg-slate-900/60 border-slate-800 space-y-1">
          <span className="text-[11px] font-semibold text-indigo-400 uppercase tracking-wider">Avg Threat Index</span>
          <div className="text-2xl font-bold text-indigo-300">
            {summary?.average_exposure_index?.toFixed(2) ?? '0.00'}
          </div>
          <span className="text-[10px] text-slate-500">Enterprise Exposure Mean</span>
        </Card>
      </div>

      {/* Tabs Navigation */}
      <div className="flex items-center gap-2 border-b border-slate-800">
        <button
          onClick={() => setActiveTab('register')}
          className={`px-4 py-2.5 text-xs font-bold transition-colors border-b-2 flex items-center gap-1.5 ${
            activeTab === 'register'
              ? 'border-indigo-500 text-indigo-400 bg-indigo-500/5'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Crosshair className="h-4 w-4" />
          Exposure Register ({exposures.length})
        </button>

        <button
          onClick={() => setActiveTab('posture')}
          className={`px-4 py-2.5 text-xs font-bold transition-colors border-b-2 flex items-center gap-1.5 ${
            activeTab === 'posture'
              ? 'border-indigo-500 text-indigo-400 bg-indigo-500/5'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Activity className="h-4 w-4" />
          Threat Posture Breakdown
        </button>

        <button
          onClick={() => setActiveTab('lineage')}
          className={`px-4 py-2.5 text-xs font-bold transition-colors border-b-2 flex items-center gap-1.5 ${
            activeTab === 'lineage'
              ? 'border-indigo-500 text-indigo-400 bg-indigo-500/5'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Layers className="h-4 w-4" />
          Governance Lineage Map
        </button>
      </div>

      {/* Tab 1: Exposure Register */}
      {activeTab === 'register' && (
        <div className="space-y-4">
          {/* Filters Bar */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 bg-slate-900/60 rounded-xl border border-slate-800">
            <div className="flex flex-wrap items-center gap-2 flex-1">
              <div className="relative flex-1 min-w-[200px] max-w-xs">
                <Search className="h-4 w-4 absolute left-3 top-2.5 text-slate-500" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search CVE, CWE, Title..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono"
                />
              </div>

              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value as any)}
                className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
              >
                <option value="ALL">All Severities</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as any)}
                className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
              >
                <option value="ALL">All Statuses</option>
                <option value="OPEN">Open</option>
                <option value="UNDER_INVESTIGATION">Investigating</option>
                <option value="REMEDIATING">Remediating</option>
                <option value="EXCEPTION_REQUESTED">Exception Pending</option>
                <option value="RESOLVED">Resolved</option>
              </select>

              <label className="flex items-center gap-1.5 text-xs font-semibold text-rose-400 bg-rose-950/30 px-2.5 py-1.5 rounded-lg border border-rose-800/40 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={cisaKevOnly}
                  onChange={(e) => setCisaKevOnly(e.target.checked)}
                  className="rounded bg-slate-900 border-slate-700 text-rose-500 focus:ring-rose-500"
                />
                <span>CISA KEV Only</span>
              </label>
            </div>

            {(searchQuery || severityFilter !== 'ALL' || statusFilter !== 'ALL' || cisaKevOnly) && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setSearchQuery('');
                  setSeverityFilter('ALL');
                  setStatusFilter('ALL');
                  setCisaKevOnly(false);
                }}
                className="text-xs text-slate-400 hover:text-slate-200"
              >
                Reset Filters
              </Button>
            )}
          </div>

          {/* Exposures Table */}
          {isLoading ? (
            <div className="py-20 flex justify-center">
              <LoadingSpinner text="Loading threat exposure catalog..." />
            </div>
          ) : isError ? (
            <div className="p-8 bg-rose-500/10 border border-rose-500/30 rounded-xl text-center space-y-3">
              <AlertTriangle className="h-10 w-10 text-rose-400 mx-auto" />
              <h2 className="text-base font-bold text-slate-100">Failed to Load Exposures</h2>
              <p className="text-xs text-slate-400">
                An error occurred while communicating with the threat exposure telemetry service.
              </p>
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                Retry
              </Button>
            </div>
          ) : exposures.length === 0 ? (
            <Card className="p-12 text-center space-y-3 bg-slate-900/60 border-slate-800">
              <ShieldCheck className="h-12 w-12 text-emerald-400 mx-auto" />
              <h3 className="text-base font-bold text-slate-100">No Vulnerability Exposures Found</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                No threat exposures match the current filters. Ingest a new vulnerability or clear active filters.
              </p>
              {canManage && (
                <Button variant="primary" size="sm" onClick={() => setIsCreateModalOpen(true)}>
                  Ingest First Exposure
                </Button>
              )}
            </Card>
          ) : (
            <Card className="bg-slate-900/60 border-slate-800 overflow-hidden">
              <div className="overflow-x-auto">
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableHeaderCell>Vulnerability Identifier</TableHeaderCell>
                      <TableHeaderCell>Severity & Exploitability</TableHeaderCell>
                      <TableHeaderCell>Exposure Index</TableHeaderCell>
                      <TableHeaderCell>SLA Target / Status</TableHeaderCell>
                      <TableHeaderCell>Lifecycle</TableHeaderCell>
                      <TableHeaderCell className="text-right">Actions</TableHeaderCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {exposures.map((exp) => {
                      const isResolved = exp.status === 'RESOLVED';
                      return (
                        <TableRow key={exp.id} className="hover:bg-slate-800/40">
                          <TableCell>
                            <div className="space-y-0.5">
                              <div className="flex items-center gap-2">
                                <Link
                                  to={`/exposure/${exp.id}`}
                                  className="font-mono text-sm font-bold text-indigo-400 hover:text-indigo-300 hover:underline flex items-center gap-1"
                                >
                                  {exp.cve_id}
                                  <ArrowUpRight className="h-3.5 w-3.5 opacity-60" />
                                </Link>
                                {exp.cwe_id && (
                                  <span className="font-mono text-[10px] text-slate-400 bg-slate-950 px-1.5 py-0.5 rounded border border-slate-800">
                                    {exp.cwe_id}
                                  </span>
                                )}
                              </div>
                              <p className="text-xs text-slate-200 line-clamp-1 max-w-sm">{exp.title}</p>
                            </div>
                          </TableCell>

                          <TableCell>
                            <div className="space-y-1">
                              <div className="flex items-center gap-1.5">
                                {getSeverityBadge(exp.severity)}
                                {exp.cisa_kev && (
                                  <Badge variant="danger" className="text-[10px] flex items-center gap-0.5">
                                    <Flame className="h-3 w-3" /> KEV
                                  </Badge>
                                )}
                              </div>
                              <div className="flex items-center gap-2 text-[11px] text-slate-400 font-mono">
                                <span>CVSS: {exp.cvss_score.toFixed(1)}</span>
                                <span>•</span>
                                <span>EPSS: {(exp.epss_score * 100).toFixed(1)}%</span>
                              </div>
                            </div>
                          </TableCell>

                          <TableCell>
                            <div className="space-y-1">
                              <div className="flex items-center gap-2 font-mono font-bold">
                                <span
                                  className={`text-base ${
                                    exp.exposure_index >= 75
                                      ? 'text-rose-400'
                                      : exp.exposure_index >= 50
                                      ? 'text-amber-400'
                                      : exp.exposure_index >= 25
                                      ? 'text-indigo-400'
                                      : 'text-slate-300'
                                  }`}
                                >
                                  {exp.exposure_index.toFixed(2)}
                                </span>
                                <span className="text-[10px] text-slate-500 font-normal">/ 100</span>
                              </div>
                              {/* Mini progress bar */}
                              <div className="w-24 h-1.5 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
                                <div
                                  className={`h-full ${
                                    exp.exposure_index >= 75
                                      ? 'bg-rose-500'
                                      : exp.exposure_index >= 50
                                      ? 'bg-amber-500'
                                      : exp.exposure_index >= 25
                                      ? 'bg-indigo-500'
                                      : 'bg-slate-400'
                                  }`}
                                  style={{ width: `${Math.min(100, exp.exposure_index)}%` }}
                                />
                              </div>
                            </div>
                          </TableCell>

                          <TableCell>
                            {getSlaDisplay(exp.remediation_sla_due, exp.status)}
                          </TableCell>

                          <TableCell>
                            {getStatusBadge(exp.status)}
                          </TableCell>

                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-1.5">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => navigate(`/exposure/${exp.id}`)}
                                className="text-xs px-2 py-1"
                              >
                                View
                              </Button>

                              {canManage && !isResolved && (
                                <>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => setStatusTransitionExposure(exp)}
                                    className="p-1.5 h-8 text-slate-400 hover:text-indigo-300"
                                    title="Transition Status"
                                  >
                                    <Activity className="h-4 w-4" />
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => setEditingExposure(exp)}
                                    className="p-1.5 h-8 text-slate-400 hover:text-slate-200"
                                    title="Edit Telemetry"
                                  >
                                    <Edit2 className="h-4 w-4" />
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => {
                                      if (confirm(`Are you sure you want to delete exposure ${exp.cve_id}?`)) {
                                        deleteMutation.mutate(exp.id);
                                      }
                                    }}
                                    className="p-1.5 h-8 text-slate-400 hover:text-rose-400"
                                    title="Delete Exposure"
                                  >
                                    <Trash2 className="h-4 w-4" />
                                  </Button>
                                </>
                              )}
                            </div>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* Tab 2: Threat Posture Breakdown */}
      {activeTab === 'posture' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card className="p-6 bg-slate-900/60 border-slate-800 space-y-4">
            <h3 className="text-base font-bold text-slate-100">Severity Distribution</h3>
            <div className="space-y-3">
              {Object.entries(summary?.severity_distribution || {}).map(([sev, count]) => {
                const total = summary?.total_exposures || 1;
                const pct = Math.round((count / total) * 100);
                return (
                  <div key={sev} className="space-y-1">
                    <div className="flex justify-between text-xs font-medium text-slate-300">
                      <span>{sev}</span>
                      <span>{count} ({pct}%)</span>
                    </div>
                    <div className="w-full h-2 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
                      <div
                        className={`h-full ${
                          sev === 'CRITICAL'
                            ? 'bg-rose-500'
                            : sev === 'HIGH'
                            ? 'bg-amber-500'
                            : sev === 'MEDIUM'
                            ? 'bg-indigo-500'
                            : 'bg-slate-400'
                        }`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>

          <Card className="p-6 bg-slate-900/60 border-slate-800 space-y-4">
            <h3 className="text-base font-bold text-slate-100">Lifecycle Status Breakdown</h3>
            <div className="space-y-3">
              {Object.entries(summary?.status_distribution || {}).map(([st, count]) => {
                const total = summary?.total_exposures || 1;
                const pct = Math.round((count / total) * 100);
                return (
                  <div key={st} className="space-y-1">
                    <div className="flex justify-between text-xs font-medium text-slate-300">
                      <span>{st}</span>
                      <span>{count} ({pct}%)</span>
                    </div>
                    <div className="w-full h-2 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
                      <div
                        className={`h-full ${
                          st === 'RESOLVED'
                            ? 'bg-emerald-500'
                            : st === 'REMEDIATING'
                            ? 'bg-amber-500'
                            : 'bg-indigo-500'
                        }`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>
      )}

      {/* Tab 3: Lineage */}
      {activeTab === 'lineage' && <ExposureLineageCard />}

      {/* Ingestion / Edit Modal */}
      <ExposureModal
        isOpen={isCreateModalOpen || !!editingExposure}
        onClose={() => {
          setIsCreateModalOpen(false);
          setEditingExposure(null);
        }}
        initialData={editingExposure}
        onSubmit={async (payload) => {
          if (editingExposure) {
            await updateMutation.mutateAsync({ id: editingExposure.id, data: payload as VulnerabilityExposureUpdate });
          } else {
            await createMutation.mutateAsync(payload as VulnerabilityExposureCreate);
          }
        }}
        isSubmitting={createMutation.isPending || updateMutation.isPending}
      />

      {/* Status Transition Modal */}
      <ExposureStatusModal
        isOpen={!!statusTransitionExposure}
        onClose={() => setStatusTransitionExposure(null)}
        exposure={statusTransitionExposure}
        onSubmit={async (st, notes) => {
          if (statusTransitionExposure) {
            await statusMutation.mutateAsync({ id: statusTransitionExposure.id, status: st, notes });
          }
        }}
        isSubmitting={statusMutation.isPending}
      />
    </div>
  );
};
