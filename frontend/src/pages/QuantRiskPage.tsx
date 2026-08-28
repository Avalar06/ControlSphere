import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { quantRiskService } from '../lib/quantRiskService';
import { Card, CardHeader } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Table, TableBody, TableCell, TableHead, TableHeaderCell, TableRow } from '../components/ui/Table';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { QuantScenarioModal } from '../components/quant/QuantScenarioModal';
import { RiskAppetiteModal } from '../components/quant/RiskAppetiteModal';
import { SimulationRunModal } from '../components/quant/SimulationRunModal';
import { QuantLineageCard } from '../components/quant/QuantLineageCard';
import type {
  AppetiteBreachState,
  QuantitativeRiskScenario,
  ScenarioStatus,
  ThreatActorCategory,
} from '../types';
import {
  AlertTriangle,
  ArrowUpRight,
  Calculator,
  CheckCircle2,
  Clock,
  DollarSign,
  Layers,
  Lock,
  Play,
  Plus,
  RotateCw,
  Search,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
  UserCheck,
} from 'lucide-react';

type TabKey = 'overview' | 'scenarios' | 'appetites';

export const QuantRiskPage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user, hasRole } = useAuth();

  const canManage = hasRole('ADMIN', 'MANAGER', 'GRC_ANALYST', 'SECURITY_ANALYST');
  const canExecute = hasRole('ADMIN', 'MANAGER', 'GRC_ANALYST', 'SECURITY_ANALYST');
  const canApprove = hasRole('ADMIN', 'MANAGER');

  const [activeTab, setActiveTab] = useState<TabKey>('overview');

  // Filters for Scenario Register
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<ScenarioStatus | 'ALL'>('ALL');
  const [threatFilter, setThreatFilter] = useState<ThreatActorCategory | 'ALL'>('ALL');

  // Modals state
  const [isScenarioModalOpen, setIsScenarioModalOpen] = useState(false);
  const [editingScenario, setEditingScenario] = useState<QuantitativeRiskScenario | null>(null);
  const [isAppetiteModalOpen, setIsAppetiteModalOpen] = useState(false);
  const [simulatingScenario, setSimulatingScenario] = useState<QuantitativeRiskScenario | null>(null);

  // Queries
  const {
    data: overview,
    isLoading: isOverviewLoading,
    isError: isOverviewError,
    refetch: refetchOverview,
  } = useQuery({
    queryKey: ['quant-overview'],
    queryFn: quantRiskService.getOverview,
  });

  const {
    data: scenarios = [],
    isLoading: isScenariosLoading,
    isError: isScenariosError,
  } = useQuery({
    queryKey: ['quant-scenarios', statusFilter, threatFilter, searchQuery],
    queryFn: () =>
      quantRiskService.listScenarios({
        status: statusFilter === 'ALL' ? undefined : statusFilter,
        threat_category: threatFilter === 'ALL' ? undefined : threatFilter,
        search: searchQuery || undefined,
      }),
  });

  const {
    data: currentAppetite,
    isLoading: isCurrentAppetiteLoading,
  } = useQuery({
    queryKey: ['quant-appetite-current'],
    queryFn: quantRiskService.getCurrentAppetite,
  });

  const {
    data: allAppetites = [],
    isLoading: isAppetitesLoading,
  } = useQuery({
    queryKey: ['quant-appetites-list'],
    queryFn: () => quantRiskService.listRiskAppetites(),
  });

  // Lifecycle Mutations
  const activateMutation = useMutation({
    mutationFn: (id: number) => quantRiskService.activateScenario(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quant-scenarios'] });
      queryClient.invalidateQueries({ queryKey: ['quant-overview'] });
    },
  });

  const freezeMutation = useMutation({
    mutationFn: (id: number) => quantRiskService.freezeScenario(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quant-scenarios'] });
      queryClient.invalidateQueries({ queryKey: ['quant-overview'] });
    },
  });

  const approveAppetiteMutation = useMutation({
    mutationFn: (id: number) => quantRiskService.approveRiskAppetite(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quant-appetites-list'] });
      queryClient.invalidateQueries({ queryKey: ['quant-appetite-current'] });
      queryClient.invalidateQueries({ queryKey: ['quant-overview'] });
    },
  });

  const getBreachBadge = (state?: AppetiteBreachState) => {
    switch (state) {
      case 'WITHIN_APPETITE':
        return <Badge variant="success">Within Board Appetite</Badge>;
      case 'EXCEEDS_ALE':
        return <Badge variant="warning">Exceeds ALE Limit</Badge>;
      case 'EXCEEDS_VAR':
        return <Badge variant="warning">Exceeds 95% VaR Limit</Badge>;
      case 'EXCEEDS_BOTH':
        return <Badge variant="danger">Critical Breach (ALE & VaR)</Badge>;
      default:
        return <Badge variant="default">Appetite Uncalibrated</Badge>;
    }
  };

  const getStatusBadge = (status: ScenarioStatus) => {
    switch (status) {
      case 'DRAFT':
        return <Badge variant="default">Draft</Badge>;
      case 'ACTIVE':
        return <Badge variant="info">Active</Badge>;
      case 'FROZEN':
        return <Badge variant="success">Frozen Baseline</Badge>;
      case 'ARCHIVED':
        return <Badge variant="default">Archived</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="h-9 w-9 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
              <Calculator className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-slate-100 tracking-tight">
                  Cyber Risk Quantification & Loss Modeling
                </h1>
                <Badge variant="info">QUANTUM-GRC</Badge>
                <span className="text-[10px] font-mono text-slate-500 uppercase px-1.5 py-0.5 bg-slate-900 border border-slate-800 rounded">
                  Phase 12
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Deterministic FAIR decomposition, empirical Monte Carlo loss modeling, and Board Risk Appetite governance.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {canManage && (
            <Button
              variant="primary"
              onClick={() => {
                setEditingScenario(null);
                setIsScenarioModalOpen(true);
              }}
            >
              <Plus className="h-4 w-4 mr-1.5" />
              New Risk Scenario
            </Button>
          )}
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-800 gap-1">
        <button
          onClick={() => setActiveTab('overview')}
          className={`px-4 py-2.5 text-xs font-semibold tracking-wide transition-all border-b-2 flex items-center gap-2 ${
            activeTab === 'overview'
              ? 'border-indigo-500 text-indigo-400 bg-indigo-950/20'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
          }`}
        >
          <TrendingUp className="h-4 w-4" />
          Executive Overview
        </button>
        <button
          onClick={() => setActiveTab('scenarios')}
          className={`px-4 py-2.5 text-xs font-semibold tracking-wide transition-all border-b-2 flex items-center gap-2 ${
            activeTab === 'scenarios'
              ? 'border-indigo-500 text-indigo-400 bg-indigo-950/20'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
          }`}
        >
          <Layers className="h-4 w-4" />
          Scenario Register
          {scenarios.length > 0 && (
            <span className="ml-1.5 px-1.5 py-0.2 bg-slate-800 text-slate-300 rounded-full text-[10px] font-mono">
              {scenarios.length}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab('appetites')}
          className={`px-4 py-2.5 text-xs font-semibold tracking-wide transition-all border-b-2 flex items-center gap-2 ${
            activeTab === 'appetites'
              ? 'border-indigo-500 text-indigo-400 bg-indigo-950/20'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
          }`}
        >
          <ShieldCheck className="h-4 w-4" />
          Financial Risk Appetite
        </button>
      </div>

      {/* TAB 1: EXECUTIVE OVERVIEW */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {isOverviewLoading ? (
            <div className="flex justify-center p-12">
              <LoadingSpinner />
            </div>
          ) : isOverviewError ? (
            <Card className="border-rose-900 bg-rose-950/20 p-6 text-center">
              <AlertTriangle className="h-8 w-8 text-rose-400 mx-auto mb-2" />
              <h3 className="text-sm font-semibold text-rose-200">Failed to load quantitative portfolio telemetry</h3>
              <Button variant="outline" className="mt-3" onClick={() => refetchOverview()}>
                <RotateCw className="h-3.5 w-3.5 mr-1" /> Retry
              </Button>
            </Card>
          ) : overview ? (
            <>
              {/* Executive Metric KPI Grid */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card className="p-4 bg-slate-900/90 border-slate-800">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-400 font-medium">Portfolio Expected Loss (ALE)</span>
                    <DollarSign className="h-4 w-4 text-indigo-400" />
                  </div>
                  <div className="text-2xl font-bold text-slate-100 font-mono mt-2">
                    ${overview.portfolio_ale.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </div>
                  <span className="text-[11px] text-slate-500 mt-1 block">
                    Aggregated annual expected financial loss across active models
                  </span>
                </Card>

                <Card className="p-4 bg-slate-900/90 border-slate-800">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-400 font-medium">Portfolio 95% VaR (Tail)</span>
                    <TrendingDown className="h-4 w-4 text-cyan-400" />
                  </div>
                  <div className="text-2xl font-bold text-cyan-400 font-mono mt-2">
                    ${overview.portfolio_var_95.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </div>
                  <span className="text-[11px] text-slate-500 mt-1 block">
                    95th percentile aggregate catastrophic annual tail exposure
                  </span>
                </Card>

                <Card className="p-4 bg-slate-900/90 border-slate-800">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-400 font-medium">Scenario Portfolio Status</span>
                    <Layers className="h-4 w-4 text-emerald-400" />
                  </div>
                  <div className="text-2xl font-bold text-slate-100 font-mono mt-2">
                    {overview.active_scenarios + overview.frozen_scenarios}
                    <span className="text-xs text-slate-400 font-normal ml-2 font-sans">
                      / {overview.total_scenarios} Total
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-500 mt-1 block">
                    {overview.frozen_scenarios} frozen baseline records locked
                  </span>
                </Card>

                <Card className="p-4 bg-slate-900/90 border-slate-800 flex flex-col justify-between">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-400 font-medium">Board Appetite Posture</span>
                    <ShieldCheck className="h-4 w-4 text-purple-400" />
                  </div>
                  <div className="mt-2">{getBreachBadge(overview.appetite_status)}</div>
                  <div className="text-[11px] text-slate-500 mt-2 font-mono flex justify-between">
                    <span>ALE Limit: ${overview.ale_limit ? overview.ale_limit.toLocaleString() : 'N/A'}</span>
                    <span>VaR Limit: ${overview.var_95_limit ? overview.var_95_limit.toLocaleString() : 'N/A'}</span>
                  </div>
                </Card>
              </div>

              {/* Threat Actor Distribution & Top Loss Scenarios */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <Card className="p-5 bg-slate-900/90 border-slate-800">
                  <CardHeader title="Threat Actor Distribution" subtitle="Distribution of modeled risk scenarios by adversary type" />
                  <div className="space-y-3">
                    {Object.entries(overview.threat_category_distribution).map(([cat, count]) => (
                      <div key={cat} className="space-y-1">
                        <div className="flex justify-between text-xs">
                          <span className="text-slate-300 font-medium">{cat.replace('_', ' ')}</span>
                          <span className="text-slate-400 font-mono">{count} scenarios</span>
                        </div>
                        <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800">
                          <div
                            className="bg-indigo-500 h-full rounded-full"
                            style={{
                              width: `${overview.total_scenarios > 0 ? (count / overview.total_scenarios) * 100 : 0}%`,
                            }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>

                <Card className="md:col-span-2 p-5 bg-slate-900/90 border-slate-800">
                  <CardHeader
                    title="Top Financial Exposure Scenarios"
                    subtitle="Ranked by Annualized Loss Expectancy (ALE)"
                    action={
                      <Button variant="ghost" size="sm" onClick={() => setActiveTab('scenarios')}>
                        View Register <ArrowUpRight className="h-3.5 w-3.5 ml-1" />
                      </Button>
                    }
                  />
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHead>
                        <TableRow>
                          <TableHeaderCell>Code</TableHeaderCell>
                          <TableHeaderCell>Scenario Title</TableHeaderCell>
                          <TableHeaderCell>Threat Category</TableHeaderCell>
                          <TableHeaderCell className="text-right">Control (CS)</TableHeaderCell>
                          <TableHeaderCell className="text-right">ALE ($/yr)</TableHeaderCell>
                          <TableHeaderCell className="text-right">95% VaR</TableHeaderCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {overview.top_risk_scenarios && overview.top_risk_scenarios.length > 0 ? (
                          overview.top_risk_scenarios.map((sc) => (
                            <TableRow
                              key={sc.id}
                              className="cursor-pointer hover:bg-slate-800/60"
                              onClick={() => navigate(`/quant-risk/scenarios/${sc.id}`)}
                            >
                              <TableCell className="font-mono text-xs font-bold text-indigo-400">
                                {sc.scenario_code}
                              </TableCell>
                              <TableCell className="text-xs font-medium text-slate-200">{sc.title}</TableCell>
                              <TableCell className="text-xs text-slate-400">{sc.threat_actor_category}</TableCell>
                              <TableCell className="text-right font-mono text-xs text-emerald-400">
                                {(sc.control_strength * 100).toFixed(0)}%
                              </TableCell>
                              <TableCell className="text-right font-mono text-xs font-bold text-slate-100">
                                ${sc.annualized_loss_expectancy.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                              </TableCell>
                              <TableCell className="text-right font-mono text-xs text-cyan-400">
                                ${sc.var_95_empirical ? sc.var_95_empirical.toLocaleString('en-US', { maximumFractionDigits: 0 }) : sc.var_95_parametric ? sc.var_95_parametric.toLocaleString('en-US', { maximumFractionDigits: 0 }) : 'N/A'}
                              </TableCell>
                            </TableRow>
                          ))
                        ) : (
                          <TableRow>
                            <TableCell colSpan={6} className="text-center py-6 text-slate-500 text-xs">
                              No quantitative scenarios created yet.
                            </TableCell>
                          </TableRow>
                        )}
                      </TableBody>
                    </Table>
                  </div>
                </Card>
              </div>

              {/* Cross-Module Data Lineage */}
              <QuantLineageCard />
            </>
          ) : null}
        </div>
      )}

      {/* TAB 2: SCENARIO REGISTER */}
      {activeTab === 'scenarios' && (
        <div className="space-y-4">
          <div className="flex flex-col md:flex-row gap-3 items-center justify-between p-4 bg-slate-900/90 border border-slate-800 rounded-lg">
            <div className="flex flex-1 items-center gap-3 w-full">
              <div className="relative flex-1">
                <Search className="h-4 w-4 text-slate-500 absolute left-3 top-2.5" />
                <input
                  type="text"
                  placeholder="Search scenarios by code, title, or description..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg pl-9 pr-3.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as any)}
                className="bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
              >
                <option value="ALL">All Statuses</option>
                <option value="DRAFT">Draft</option>
                <option value="ACTIVE">Active</option>
                <option value="FROZEN">Frozen Baseline</option>
                <option value="ARCHIVED">Archived</option>
              </select>

              <select
                value={threatFilter}
                onChange={(e) => setThreatFilter(e.target.value as any)}
                className="bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
              >
                <option value="ALL">All Threat Categories</option>
                <option value="CYBERCRIMINAL">Cybercriminal</option>
                <option value="NATION_STATE">Nation-State</option>
                <option value="INSIDER">Insider</option>
                <option value="HACKTIVIST">Hacktivist</option>
                <option value="ACCIDENTAL">Accidental</option>
              </select>
            </div>
          </div>

          <Card className="p-0 overflow-hidden bg-slate-900/90 border-slate-800">
            {isScenariosLoading ? (
              <div className="flex justify-center p-12">
                <LoadingSpinner />
              </div>
            ) : isScenariosError ? (
              <div className="p-8 text-center text-rose-300 text-xs">Failed to load risk scenarios.</div>
            ) : scenarios.length === 0 ? (
              <div className="p-12 text-center text-slate-500 text-xs">
                No quantitative risk scenarios matching current filters.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableHeaderCell>Code</TableHeaderCell>
                      <TableHeaderCell>Scenario Title</TableHeaderCell>
                      <TableHeaderCell>Status</TableHeaderCell>
                      <TableHeaderCell>Threat Actor</TableHeaderCell>
                      <TableHeaderCell className="text-right">Control (CS)</TableHeaderCell>
                      <TableHeaderCell className="text-right">Loss Freq (LEF)</TableHeaderCell>
                      <TableHeaderCell className="text-right">Single Loss (SLE)</TableHeaderCell>
                      <TableHeaderCell className="text-right">Annual Loss (ALE)</TableHeaderCell>
                      <TableHeaderCell className="text-right">95% VaR (Tail)</TableHeaderCell>
                      <TableHeaderCell className="text-center">Flags</TableHeaderCell>
                      <TableHeaderCell className="text-right">Actions</TableHeaderCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {scenarios.map((sc) => (
                      <TableRow key={sc.id} className="hover:bg-slate-800/50 transition-colors">
                        <TableCell>
                          <button
                            onClick={() => navigate(`/quant-risk/scenarios/${sc.id}`)}
                            className="font-mono text-xs font-bold text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
                          >
                            {sc.scenario_code}
                            <ArrowUpRight className="h-3 w-3 opacity-60" />
                          </button>
                        </TableCell>
                        <TableCell className="text-xs font-medium text-slate-200 max-w-xs truncate">
                          {sc.title}
                        </TableCell>
                        <TableCell>{getStatusBadge(sc.status)}</TableCell>
                        <TableCell className="text-xs text-slate-400">{sc.threat_actor_category}</TableCell>
                        <TableCell className="text-right font-mono text-xs text-emerald-400">
                          {(sc.control_strength * 100).toFixed(0)}%
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs text-slate-300">
                          {sc.loss_event_frequency.toFixed(2)}/yr
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs text-slate-300">
                          ${sc.single_loss_expectancy.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs font-bold text-slate-100">
                          ${sc.annualized_loss_expectancy.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs text-cyan-400">
                          ${sc.var_95_empirical ? sc.var_95_empirical.toLocaleString('en-US', { maximumFractionDigits: 0 }) : sc.var_95_parametric ? sc.var_95_parametric.toLocaleString('en-US', { maximumFractionDigits: 0 }) : 'N/A'}
                        </TableCell>
                        <TableCell className="text-center">
                          <div className="flex items-center justify-center gap-1.5">
                            {sc.is_immutable && (
                              <span title="Frozen Baseline (Immutable)">
                                <Lock className="h-3.5 w-3.5 text-emerald-400" />
                              </span>
                            )}
                            {sc.is_ccm_stale && (
                              <span title="Stale Phase 7 CCM Telemetry (>30 days)">
                                <Clock className="h-3.5 w-3.5 text-amber-400" />
                              </span>
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            {canExecute && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setSimulatingScenario(sc)}
                                title="Run Monte Carlo Simulation"
                              >
                                <Play className="h-3.5 w-3.5 text-indigo-400" />
                              </Button>
                            )}

                            {canManage && !sc.is_immutable && (
                              <>
                                {sc.status === 'DRAFT' && (
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => activateMutation.mutate(sc.id)}
                                    title="Activate Scenario"
                                  >
                                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                                  </Button>
                                )}
                                {sc.status === 'ACTIVE' && (
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => freezeMutation.mutate(sc.id)}
                                    title="Freeze Scenario Baseline"
                                  >
                                    <Lock className="h-3.5 w-3.5 text-amber-400" />
                                  </Button>
                                )}
                              </>
                            )}

                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => navigate(`/quant-risk/scenarios/${sc.id}`)}
                            >
                              Details
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* TAB 3: FINANCIAL RISK APPETITE & GOVERNANCE */}
      {activeTab === 'appetites' && (
        <div className="space-y-6">
          <Card className="p-6 bg-slate-900/90 border-slate-800">
            <CardHeader
              title="Active Board Financial Risk Appetite"
              subtitle="Governing loss limits formally approved by the Board Risk Committee"
              action={
                canManage && (
                  <Button variant="outline" size="sm" onClick={() => setIsAppetiteModalOpen(true)}>
                    <Plus className="h-3.5 w-3.5 mr-1" />
                    Propose New Version
                  </Button>
                )
              }
            />

            {isCurrentAppetiteLoading ? (
              <LoadingSpinner />
            ) : currentAppetite ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="p-4 bg-slate-950 border border-slate-800 rounded-lg">
                  <span className="text-xs text-slate-400 uppercase tracking-wider block mb-1">
                    Annual Expected Loss Limit (ALE Limit)
                  </span>
                  <span className="text-2xl font-bold text-slate-100 font-mono mt-1">
                    ${currentAppetite.ale_limit.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                </div>

                <div className="p-4 bg-slate-950 border border-slate-800 rounded-lg">
                  <span className="text-xs text-slate-400 uppercase tracking-wider block mb-1">
                    Maximum 95% Tail Loss Limit (95% VaR Limit)
                  </span>
                  <span className="text-2xl font-bold text-cyan-400 font-mono mt-1">
                    ${currentAppetite.var_95_limit.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                </div>

                <div className="p-4 bg-slate-950 border border-slate-800 rounded-lg flex flex-col justify-between">
                  <div>
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-xs text-slate-400 uppercase tracking-wider">Version & Governance</span>
                      <Badge variant="success">Version {currentAppetite.version} Active</Badge>
                    </div>
                    <span className="text-xs text-slate-300 block">
                      Approved by User #{currentAppetite.approved_by_id} on{' '}
                      {new Date(currentAppetite.approved_at || '').toLocaleDateString()}
                    </span>
                  </div>
                  {currentAppetite.notes && (
                    <span className="text-[11px] text-slate-500 italic mt-2 block">"{currentAppetite.notes}"</span>
                  )}
                </div>
              </div>
            ) : (
              <div className="p-8 text-center text-slate-500 text-xs">
                No active approved risk appetite policy found.
              </div>
            )}
          </Card>

          <Card className="p-5 bg-slate-900/90 border-slate-800">
            <CardHeader
              title="Risk Appetite Governance & Version History"
              subtitle="Four-eyes review queue and historical superseded versions"
            />
            {isAppetitesLoading ? (
              <LoadingSpinner />
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableHeaderCell>Version</TableHeaderCell>
                      <TableHeaderCell>Status</TableHeaderCell>
                      <TableHeaderCell className="text-right">ALE Limit ($)</TableHeaderCell>
                      <TableHeaderCell className="text-right">95% VaR Limit ($)</TableHeaderCell>
                      <TableHeaderCell>Requester</TableHeaderCell>
                      <TableHeaderCell>Approver</TableHeaderCell>
                      <TableHeaderCell>Governance Notes</TableHeaderCell>
                      <TableHeaderCell className="text-right">Actions</TableHeaderCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {allAppetites.map((app) => {
                      const isRequester = user?.id === app.requested_by_id;
                      return (
                        <TableRow key={app.id}>
                          <TableCell className="font-mono text-xs font-bold text-slate-100">
                            v{app.version}
                          </TableCell>
                          <TableCell>
                            {app.status === 'APPROVED' ? (
                              <Badge variant="success">Approved</Badge>
                            ) : app.status === 'DRAFT' ? (
                              <Badge variant="warning">Draft (Pending Review)</Badge>
                            ) : (
                              <Badge variant="default">Superseded</Badge>
                            )}
                          </TableCell>
                          <TableCell className="text-right font-mono text-xs text-slate-200">
                            ${app.ale_limit.toLocaleString()}
                          </TableCell>
                          <TableCell className="text-right font-mono text-xs text-cyan-400">
                            ${app.var_95_limit.toLocaleString()}
                          </TableCell>
                          <TableCell className="text-xs text-slate-400">User #{app.requested_by_id}</TableCell>
                          <TableCell className="text-xs text-slate-400">
                            {app.approved_by_id ? `User #${app.approved_by_id}` : '—'}
                          </TableCell>
                          <TableCell className="text-xs text-slate-400 max-w-xs truncate">
                            {app.notes || '—'}
                          </TableCell>
                          <TableCell className="text-right">
                            {app.status === 'DRAFT' && (
                              canApprove ? (
                                isRequester ? (
                                  <div
                                    title="Four-Eyes Governance: Requester cannot approve their own proposed risk appetite."
                                    className="text-[11px] text-amber-400/90 font-medium italic"
                                  >
                                    Separation of Duties (Self-approval locked)
                                  </div>
                                ) : (
                                  <Button
                                    variant="primary"
                                    size="sm"
                                    onClick={() => approveAppetiteMutation.mutate(app.id)}
                                  >
                                    <UserCheck className="h-3.5 w-3.5 mr-1" />
                                    Approve Version
                                  </Button>
                                )
                              ) : (
                                <span className="text-[11px] text-slate-500">Manager approval required</span>
                              )
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Modals */}
      {isScenarioModalOpen && (
        <QuantScenarioModal
          isOpen={isScenarioModalOpen}
          onClose={() => {
            setIsScenarioModalOpen(false);
            setEditingScenario(null);
          }}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ['quant-scenarios'] });
            queryClient.invalidateQueries({ queryKey: ['quant-overview'] });
          }}
          scenario={editingScenario}
        />
      )}

      {isAppetiteModalOpen && (
        <RiskAppetiteModal
          isOpen={isAppetiteModalOpen}
          onClose={() => setIsAppetiteModalOpen(false)}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ['quant-appetites-list'] });
            queryClient.invalidateQueries({ queryKey: ['quant-appetite-current'] });
            queryClient.invalidateQueries({ queryKey: ['quant-overview'] });
          }}
        />
      )}

      {simulatingScenario && (
        <SimulationRunModal
          isOpen={!!simulatingScenario}
          onClose={() => setSimulatingScenario(null)}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ['quant-scenarios'] });
            queryClient.invalidateQueries({ queryKey: ['quant-overview'] });
          }}
          scenarioId={simulatingScenario.id}
          scenarioCode={simulatingScenario.scenario_code}
        />
      )}

    </div>
  );
};
export default QuantRiskPage;
