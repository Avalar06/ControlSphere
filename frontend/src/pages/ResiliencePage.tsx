import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { resilienceService } from '../lib/resilienceService';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Table, TableBody, TableCell, TableHead, TableHeaderCell, TableRow } from '../components/ui/Table';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { ProcessModal } from '../components/resilience/ProcessModal';
import { ResilienceLineageCard } from '../components/resilience/ResilienceLineageCard';
import type { BusinessProcess, CriticalityTier } from '../types';
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  CheckCircle2,
  DollarSign,
  Edit,
  Layers,
  Link2,
  Lock,
  Plus,
  Search,
  ShieldAlert,
  ShieldCheck,
  Trash2,
} from 'lucide-react';

type TabKey = 'overview' | 'processes' | 'lineage';

export const ResiliencePage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { hasRole } = useAuth();

  const canManage = hasRole('ADMIN', 'MANAGER', 'GRC_ANALYST');
  const [activeTab, setActiveTab] = useState<TabKey>('overview');

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [tierFilter, setTierFilter] = useState<CriticalityTier | 'ALL'>('ALL');

  // Modals state
  const [isProcessModalOpen, setIsProcessModalOpen] = useState(false);
  const [editingProcess, setEditingProcess] = useState<BusinessProcess | null>(null);

  // Queries
  const {
    data: processes = [],
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ['resilience-processes', tierFilter, searchQuery],
    queryFn: () =>
      resilienceService.listProcesses({
        criticality_tier: tierFilter === 'ALL' ? undefined : tierFilter,
        search: searchQuery || undefined,
      }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => resilienceService.deleteProcess(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resilience-processes'] });
    },
  });

  // Calculate executive posture metrics from process catalog
  const totalProcesses = processes.length;
  const tier1Count = processes.filter((p) => p.criticality_tier === 'TIER_1').length;
  const tier2Count = processes.filter((p) => p.criticality_tier === 'TIER_2').length;
  const activeBiaCount = processes.filter((p) => p.active_bia && p.active_bia.status === 'ACTIVE').length;
  const unassessedCount = totalProcesses - activeBiaCount;
  const coveragePercentage = totalProcesses > 0 ? Math.round((activeBiaCount / totalProcesses) * 100) : 0;

  // Cumulative hourly disruption exposure from active baselines
  const cumulativeHourlyLoss = processes.reduce((acc, p) => {
    return acc + (p.active_bia?.status === 'ACTIVE' ? p.active_bia.hourly_downtime_cost : 0);
  }, 0);

  const getTierBadge = (tier: CriticalityTier) => {
    switch (tier) {
      case 'TIER_1':
        return <Badge variant="danger">TIER 1 (CRITICAL)</Badge>;
      case 'TIER_2':
        return <Badge variant="warning">TIER 2 (HIGH)</Badge>;
      case 'TIER_3':
        return <Badge variant="info">TIER 3 (MODERATE)</Badge>;
      case 'TIER_4':
        return <Badge variant="default">TIER 4 (LOW)</Badge>;
      default:
        return <Badge variant="default">{tier}</Badge>;
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold tracking-tight text-slate-100">
              Operational Resilience &amp; BIA
            </h1>
            <span className="px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
              Phase 13
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Enterprise business process catalog, four-eyes Business Impact Analysis baselines, and deterministic outage disruption modeling.
          </p>
        </div>

        {canManage && (
          <Button
            onClick={() => {
              setEditingProcess(null);
              setIsProcessModalOpen(true);
            }}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white self-start sm:self-auto shadow-lg shadow-indigo-950/50"
          >
            <Plus size={16} />
            <span>New Business Process</span>
          </Button>
        )}
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-800 space-x-1">
        <button
          onClick={() => setActiveTab('overview')}
          className={`px-4 py-2.5 text-xs font-semibold rounded-t-lg transition-all flex items-center gap-2 ${
            activeTab === 'overview'
              ? 'bg-slate-900 text-indigo-400 border-t-2 border-indigo-500 border-x border-slate-800'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
          }`}
        >
          <Activity size={15} />
          <span>Executive Posture Overview</span>
        </button>

        <button
          onClick={() => setActiveTab('processes')}
          className={`px-4 py-2.5 text-xs font-semibold rounded-t-lg transition-all flex items-center gap-2 ${
            activeTab === 'processes'
              ? 'bg-slate-900 text-indigo-400 border-t-2 border-indigo-500 border-x border-slate-800'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
          }`}
        >
          <Layers size={15} />
          <span>Business Process Register ({processes.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('lineage')}
          className={`px-4 py-2.5 text-xs font-semibold rounded-t-lg transition-all flex items-center gap-2 ${
            activeTab === 'lineage'
              ? 'bg-slate-900 text-indigo-400 border-t-2 border-indigo-500 border-x border-slate-800'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
          }`}
        >
          <ShieldCheck size={15} />
          <span>Governance Lineage</span>
        </button>
      </div>

      {/* Tab Content */}
      {isLoading ? (
        <div className="py-16 flex justify-center">
          <LoadingSpinner text="Loading operational resilience telemetry..." />
        </div>
      ) : isError ? (
        <div className="p-6 bg-rose-500/10 border border-rose-500/30 rounded-xl text-center">
          <AlertTriangle className="h-8 w-8 text-rose-400 mx-auto mb-2" />
          <p className="text-sm font-semibold text-rose-300">Failed to load operational resilience data.</p>
          <Button variant="secondary" onClick={() => refetch()} className="mt-3 text-xs">
            Retry Loading
          </Button>
        </div>
      ) : (
        <>
          {/* TAB 1: EXECUTIVE OVERVIEW */}
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* Executive KPI Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <Card className="border-slate-800 bg-slate-900/80">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      Total Business Processes
                    </span>
                    <Layers className="h-4 w-4 text-indigo-400" />
                  </div>
                  <div className="mt-3 flex items-baseline gap-2">
                    <span className="text-3xl font-bold font-mono text-slate-100">{totalProcesses}</span>
                    <span className="text-xs text-slate-400 font-medium">cataloged</span>
                  </div>
                  <div className="mt-2 text-xs text-slate-400">
                    <span className="text-rose-400 font-semibold">{tier1Count} Tier 1</span>, <span className="text-amber-400 font-semibold">{tier2Count} Tier 2</span> critical
                  </div>
                </Card>

                <Card className="border-slate-800 bg-slate-900/80">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      BIA Baseline Coverage
                    </span>
                    <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  </div>
                  <div className="mt-3 flex items-baseline gap-2">
                    <span className="text-3xl font-bold font-mono text-emerald-400">{coveragePercentage}%</span>
                    <span className="text-xs text-slate-400 font-medium">approved</span>
                  </div>
                  <div className="mt-2 text-xs text-slate-400">
                    <span className="text-emerald-400 font-semibold">{activeBiaCount}</span> of {totalProcesses} active baselines
                  </div>
                </Card>

                <Card className="border-slate-800 bg-slate-900/80">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      Unassessed Processes
                    </span>
                    <AlertTriangle className="h-4 w-4 text-amber-400" />
                  </div>
                  <div className="mt-3 flex items-baseline gap-2">
                    <span className="text-3xl font-bold font-mono text-amber-400">{unassessedCount}</span>
                    <span className="text-xs text-slate-400 font-medium">lacking BIA</span>
                  </div>
                  <div className="mt-2 text-xs text-slate-400">
                    Require four-eyes BIA baseline
                  </div>
                </Card>

                <Card className="border-slate-800 bg-slate-900/80">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      Hourly Outage Exposure
                    </span>
                    <DollarSign className="h-4 w-4 text-purple-400" />
                  </div>
                  <div className="mt-3 flex items-baseline gap-1">
                    <span className="text-2xl font-bold font-mono text-slate-100">
                      ${cumulativeHourlyLoss.toLocaleString()}
                    </span>
                    <span className="text-xs text-slate-400 font-mono">/hr</span>
                  </div>
                  <div className="mt-2 text-xs text-slate-400">
                    Cumulative portfolio disruption rate
                  </div>
                </Card>
              </div>

              {/* Critical Process Exposure Summary */}
              <Card className="border-slate-800 bg-slate-900/90 space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <div className="flex items-center gap-2">
                    <ShieldAlert className="h-5 w-5 text-rose-400" />
                    <div>
                      <h3 className="text-sm font-semibold text-slate-100">
                        Mission Critical (Tier 1) Processes &amp; Active Baselines
                      </h3>
                      <p className="text-xs text-slate-400 mt-0.5">
                        High-priority services requiring strict RTO/RPO enforcement and continuous supplier resilience.
                      </p>
                    </div>
                  </div>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => {
                      setTierFilter('TIER_1');
                      setActiveTab('processes');
                    }}
                    className="text-xs"
                  >
                    View All Critical
                  </Button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
                  {processes
                    .filter((p) => p.criticality_tier === 'TIER_1')
                    .slice(0, 6)
                    .map((p) => (
                      <div
                        key={p.id}
                        onClick={() => navigate(`/resilience/processes/${p.id}`)}
                        className="p-3.5 bg-slate-950/80 border border-slate-800 hover:border-indigo-500/50 rounded-xl transition-all cursor-pointer group flex flex-col justify-between"
                      >
                        <div>
                          <div className="flex items-start justify-between gap-2 mb-2">
                            <span className="text-xs font-bold text-slate-200 group-hover:text-indigo-400 transition-colors">
                              {p.name}
                            </span>
                            <Badge variant="danger">TIER 1</Badge>
                          </div>
                          <p className="text-xs text-slate-400 line-clamp-2 mb-3">
                            {p.description || 'No description recorded.'}
                          </p>
                        </div>

                        <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs font-mono">
                          {p.active_bia ? (
                            <div className="text-emerald-400 text-[11px] font-semibold flex items-center gap-1">
                              <CheckCircle2 size={12} />
                              <span>RTO: {p.active_bia.rto_hours}h | MTD: {p.active_bia.mtd_hours}h</span>
                            </div>
                          ) : (
                            <span className="text-amber-400 text-[11px]">No Active BIA</span>
                          )}
                          <ArrowUpRight size={14} className="text-slate-500 group-hover:text-indigo-400 transition-colors" />
                        </div>
                      </div>
                    ))}
                  {tier1Count === 0 && (
                    <div className="col-span-full p-8 text-center bg-slate-950/40 rounded-xl border border-slate-800 text-xs text-slate-400">
                      No Tier 1 processes registered yet.
                    </div>
                  )}
                </div>
              </Card>

              {/* Lineage Overview Card */}
              <ResilienceLineageCard />
            </div>
          )}

          {/* TAB 2: PROCESS REGISTER */}
          {activeTab === 'processes' && (
            <Card className="border-slate-800 bg-slate-900/90 space-y-4">
              {/* Filter Bar */}
              <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
                <div className="relative w-full sm:w-80">
                  <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search processes..."
                    className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div className="flex items-center gap-2 w-full sm:w-auto">
                  <span className="text-xs text-slate-400 font-medium">Criticality:</span>
                  <select
                    value={tierFilter}
                    onChange={(e) => setTierFilter(e.target.value as CriticalityTier | 'ALL')}
                    className="px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="ALL">All Criticality Tiers</option>
                    <option value="TIER_1">TIER 1 (Critical)</option>
                    <option value="TIER_2">TIER 2 (High)</option>
                    <option value="TIER_3">TIER 3 (Moderate)</option>
                    <option value="TIER_4">TIER 4 (Low)</option>
                  </select>
                </div>
              </div>

              {/* Table */}
              {processes.length === 0 ? (
                <div className="p-12 text-center bg-slate-950/40 rounded-xl border border-slate-800 space-y-3">
                  <Layers className="h-10 w-10 text-slate-600 mx-auto" />
                  <p className="text-sm font-semibold text-slate-300">No Business Processes Found</p>
                  <p className="text-xs text-slate-500 max-w-sm mx-auto">
                    {searchQuery || tierFilter !== 'ALL'
                      ? 'No processes match your filter criteria.'
                      : 'Get started by creating your first organizational business process.'}
                  </p>
                  {canManage && (
                    <Button
                      size="sm"
                      onClick={() => {
                        setEditingProcess(null);
                        setIsProcessModalOpen(true);
                      }}
                      className="bg-indigo-600 hover:bg-indigo-500 text-xs"
                    >
                      <Plus size={14} className="mr-1" /> Add Process
                    </Button>
                  )}
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableHeaderCell>Business Process</TableHeaderCell>
                        <TableHeaderCell>Criticality Tier</TableHeaderCell>
                        <TableHeaderCell>Active BIA Baseline</TableHeaderCell>
                        <TableHeaderCell>Disruption Rate</TableHeaderCell>
                        <TableHeaderCell>Dependencies</TableHeaderCell>
                        <TableHeaderCell>Owner</TableHeaderCell>
                        <TableHeaderCell className="text-right">Actions</TableHeaderCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {processes.map((proc) => {
                        const activeBia = proc.active_bia;
                        const depCount = proc.dependencies?.length || 0;

                        return (
                          <TableRow
                            key={proc.id}
                            className="hover:bg-slate-800/40 cursor-pointer"
                            onClick={() => navigate(`/resilience/processes/${proc.id}`)}
                          >
                            <TableCell>
                              <div className="font-semibold text-slate-200 hover:text-indigo-400 transition-colors">
                                {proc.name}
                              </div>
                              <div className="text-[11px] text-slate-400 line-clamp-1 max-w-xs">
                                {proc.description || 'No scope notes.'}
                              </div>
                            </TableCell>

                            <TableCell>{getTierBadge(proc.criticality_tier)}</TableCell>

                            <TableCell>
                              {activeBia ? (
                                <div className="space-y-0.5">
                                  <div className="flex items-center gap-1.5">
                                    <Badge variant="success">ACTIVE (v{activeBia.version})</Badge>
                                    <Lock size={12} className="text-slate-400" />
                                  </div>
                                  <div className="text-[11px] text-slate-400 font-mono">
                                    RTO: <span className="text-slate-200">{activeBia.rto_hours}h</span> | MTD: {activeBia.mtd_hours}h
                                  </div>
                                </div>
                              ) : (
                                <Badge variant="warning">NO ACTIVE BIA</Badge>
                              )}
                            </TableCell>

                            <TableCell className="font-mono text-xs">
                              {activeBia ? (
                                <span className="text-purple-300 font-semibold">
                                  ${activeBia.hourly_downtime_cost.toLocaleString()}/hr
                                </span>
                              ) : (
                                <span className="text-slate-500">—</span>
                              )}
                            </TableCell>

                            <TableCell>
                              <div className="flex items-center gap-1 text-xs text-slate-300 font-mono">
                                <Link2 size={13} className="text-indigo-400" />
                                <span>{depCount} linked</span>
                              </div>
                            </TableCell>

                            <TableCell className="text-xs text-slate-400">
                              {proc.owner?.full_name || `User #${proc.owner_id}`}
                            </TableCell>

                            <TableCell className="text-right">
                              <div className="flex items-center justify-end gap-1.5" onClick={(e: React.MouseEvent) => e.stopPropagation()}>
                                <Button
                                  variant="secondary"
                                  size="sm"
                                  onClick={() => navigate(`/resilience/processes/${proc.id}`)}
                                  className="text-xs py-1 px-2.5"
                                >
                                  View Detail
                                </Button>

                                {canManage && (
                                  <>
                                    <Button
                                      variant="secondary"
                                      size="sm"
                                      onClick={() => {
                                        setEditingProcess(proc);
                                        setIsProcessModalOpen(true);
                                      }}
                                      className="text-xs py-1 px-2"
                                    >
                                      <Edit size={13} />
                                    </Button>

                                    <Button
                                      variant="danger"
                                      size="sm"
                                      onClick={() => {
                                        if (window.confirm(`Delete business process "${proc.name}"?`)) {
                                          deleteMutation.mutate(proc.id);
                                        }
                                      }}
                                      disabled={deleteMutation.isPending}
                                      className="text-xs py-1 px-2"
                                    >
                                      <Trash2 size={13} />
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
              )}
            </Card>
          )}

          {/* TAB 3: LINEAGE */}
          {activeTab === 'lineage' && <ResilienceLineageCard />}
        </>
      )}

      {/* Process Create/Edit Modal */}
      <ProcessModal
        isOpen={isProcessModalOpen}
        onClose={() => {
          setIsProcessModalOpen(false);
          setEditingProcess(null);
        }}
        onSuccess={() => refetch()}
        initialProcess={editingProcess}
      />
    </div>
  );
};
