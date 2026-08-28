import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../context/AuthContext';
import { quantRiskService } from '../lib/quantRiskService';
import { Card, CardHeader } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Table, TableBody, TableCell, TableHead, TableHeaderCell, TableRow } from '../components/ui/Table';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { QuantScenarioModal } from '../components/quant/QuantScenarioModal';
import { SimulationRunModal } from '../components/quant/SimulationRunModal';
import { RosiCalculatorModal } from '../components/quant/RosiCalculatorModal';
import type { ScenarioStatus } from '../types';
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Clock,
  DollarSign,
  Edit,
  Flame,
  Lock,
  Play,
  ShieldCheck,
  Target,
  TrendingDown,
} from 'lucide-react';

export const QuantScenarioDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const scenarioId = parseInt(id || '0', 10);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { hasRole } = useAuth();

  const canManage = hasRole('ADMIN', 'MANAGER', 'GRC_ANALYST', 'SECURITY_ANALYST');
  const canExecute = hasRole('ADMIN', 'MANAGER', 'GRC_ANALYST', 'SECURITY_ANALYST');

  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isSimModalOpen, setIsSimModalOpen] = useState(false);
  const [isRosiModalOpen, setIsRosiModalOpen] = useState(false);

  // Queries
  const {
    data: scenario,
    isLoading: isScenarioLoading,
    isError: isScenarioError,
  } = useQuery({
    queryKey: ['quant-scenario-detail', scenarioId],
    queryFn: () => quantRiskService.getScenario(scenarioId),
    enabled: scenarioId > 0,
  });

  const {
    data: simulations = [],
    isLoading: isSimulationsLoading,
  } = useQuery({
    queryKey: ['quant-scenario-simulations', scenarioId],
    queryFn: () => quantRiskService.listScenarioSimulations(scenarioId),
    enabled: scenarioId > 0,
  });

  const {
    data: rosiList = [],
    isLoading: isRosiLoading,
  } = useQuery({
    queryKey: ['quant-scenario-rosi', scenarioId],
    queryFn: () => quantRiskService.listScenarioRosi(scenarioId),
    enabled: scenarioId > 0,
  });

  // Lifecycle Mutations
  const activateMutation = useMutation({
    mutationFn: () => quantRiskService.activateScenario(scenarioId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quant-scenario-detail', scenarioId] });
      queryClient.invalidateQueries({ queryKey: ['quant-scenarios'] });
    },
  });

  const freezeMutation = useMutation({
    mutationFn: () => quantRiskService.freezeScenario(scenarioId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quant-scenario-detail', scenarioId] });
      queryClient.invalidateQueries({ queryKey: ['quant-scenarios'] });
    },
  });

  const archiveMutation = useMutation({
    mutationFn: () => quantRiskService.archiveScenario(scenarioId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quant-scenario-detail', scenarioId] });
      queryClient.invalidateQueries({ queryKey: ['quant-scenarios'] });
    },
  });

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

  if (isScenarioLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <LoadingSpinner />
      </div>
    );
  }

  if (isScenarioError || !scenario) {
    return (
      <Card className="border-rose-900 bg-rose-950/20 p-8 text-center">
        <AlertTriangle className="h-8 w-8 text-rose-400 mx-auto mb-2" />
        <h3 className="text-sm font-semibold text-rose-200">Scenario not found or access denied</h3>
        <Button variant="outline" className="mt-4" onClick={() => navigate('/quant-risk')}>
          <ArrowLeft className="h-4 w-4 mr-1.5" /> Back to Register
        </Button>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb & Lifecycle Action Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/quant-risk')}>
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono font-bold text-sm text-indigo-400">
                {scenario.scenario_code}
              </span>
              {getStatusBadge(scenario.status)}
              {scenario.is_immutable && (
                <Badge variant="success">
                  <Lock className="h-3 w-3 mr-1" /> Immutable Record
                </Badge>
              )}
              {scenario.is_ccm_stale && (
                <Badge variant="warning">
                  <Clock className="h-3 w-3 mr-1" /> CCM Stale (&gt;30d)
                </Badge>
              )}
            </div>
            <h1 className="text-xl font-bold text-slate-100 mt-1">{scenario.title}</h1>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          {canExecute && (
            <>
              <Button variant="primary" onClick={() => setIsSimModalOpen(true)}>
                <Play className="h-4 w-4 mr-1.5" />
                Monte Carlo Simulation
              </Button>
              <Button variant="outline" onClick={() => setIsRosiModalOpen(true)}>
                <Target className="h-4 w-4 mr-1.5" />
                Evaluate ROSI
              </Button>
            </>
          )}

          {canManage && !scenario.is_immutable && (
            <>
              <Button variant="outline" onClick={() => setIsEditModalOpen(true)}>
                <Edit className="h-4 w-4 mr-1.5" />
                Edit Assumptions
              </Button>
              {scenario.status === 'DRAFT' && (
                <Button variant="outline" onClick={() => activateMutation.mutate()}>
                  <CheckCircle2 className="h-4 w-4 mr-1.5 text-emerald-400" />
                  Activate
                </Button>
              )}
              {scenario.status === 'ACTIVE' && (
                <Button variant="outline" onClick={() => freezeMutation.mutate()}>
                  <Lock className="h-4 w-4 mr-1.5 text-amber-400" />
                  Freeze Baseline
                </Button>
              )}
              {scenario.status !== 'ARCHIVED' && (
                <Button variant="outline" onClick={() => archiveMutation.mutate()}>
                  Archive
                </Button>
              )}
            </>
          )}
        </div>
      </div>

      {/* Key Financial Telemetry KPI Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4 bg-slate-900/90 border-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium">Annual Loss Expectancy (ALE)</span>
            <DollarSign className="h-4 w-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100 font-mono mt-2">
            ${scenario.annualized_loss_expectancy.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <span className="text-[11px] text-slate-500 mt-1 block">
            Expected annual monetary financial loss: LEF * SLE
          </span>
        </Card>

        <Card className="p-4 bg-slate-900/90 border-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium">Empirical 95% VaR (Tail)</span>
            <TrendingDown className="h-4 w-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-cyan-400 font-mono mt-2">
            ${scenario.var_95_empirical ? scenario.var_95_empirical.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : scenario.var_95_parametric ? scenario.var_95_parametric.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : 'N/A'}
          </div>
          <span className="text-[11px] text-slate-500 mt-1 block">
            95th percentile worst-case simulated annual loss
          </span>
        </Card>

        <Card className="p-4 bg-slate-900/90 border-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium">Single Loss Expectancy (SLE)</span>
            <Flame className="h-4 w-4 text-rose-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100 font-mono mt-2">
            ${scenario.single_loss_expectancy.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <span className="text-[11px] text-slate-500 mt-1 block">
            PL(mean) + (SL(mean) * SLoP)
          </span>
        </Card>

        <Card className="p-4 bg-slate-900/90 border-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium">Control Strength (CS)</span>
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400 font-mono mt-2">
            {(scenario.control_strength * 100).toFixed(1)}%
          </div>
          <span className="text-[11px] text-slate-500 mt-1 block">
            Vulnerability factor: {(scenario.vulnerability_factor * 100).toFixed(1)}%
          </span>
        </Card>
      </div>

      {/* FAIR Decomposition Pipeline Explanation */}
      <Card className="p-5 bg-slate-900/90 border-slate-800">
        <CardHeader
          title="FAIR Mathematical Decomposition & Telemetry Pipeline"
          subtitle="Deterministic server-authoritative calculations derived from three-point assumptions and CCM telemetry"
        />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 bg-slate-950 border border-slate-800 rounded-lg">
            <span className="text-xs font-bold text-indigo-400 uppercase tracking-wider block mb-1">
              Step 1: Loss Event Frequency (LEF)
            </span>
            <div className="text-sm font-mono text-slate-200 mt-2">
              TEF(mean) * VULN = LEF
            </div>
            <div className="text-xs text-slate-400 mt-2 space-y-1 font-mono">
              <div>TEF(mean): {((scenario.tef_min + 4 * scenario.tef_mode + scenario.tef_max) / 6).toFixed(2)} events/yr</div>
              <div>VULN: {(scenario.vulnerability_factor * 100).toFixed(1)}% (TCAP * (1 - CS))</div>
              <div className="text-slate-100 font-bold">=&gt; LEF: {scenario.loss_event_frequency.toFixed(2)} events/yr</div>
            </div>
          </div>

          <div className="p-4 bg-slate-950 border border-slate-800 rounded-lg">
            <span className="text-xs font-bold text-indigo-400 uppercase tracking-wider block mb-1">
              Step 2: Single Loss Expectancy (SLE)
            </span>
            <div className="text-sm font-mono text-slate-200 mt-2">
              PL(mean) + (SL(mean) * SLoP) = SLE
            </div>
            <div className="text-xs text-slate-400 mt-2 space-y-1 font-mono">
              <div>PL(mean): ${((scenario.pl_min + 4 * scenario.pl_mode + scenario.pl_max) / 6).toLocaleString('en-US', { maximumFractionDigits: 0 })}</div>
              <div>Expected SL: ${(((scenario.sl_min + 4 * scenario.sl_mode + scenario.sl_max) / 6) * scenario.slop).toLocaleString('en-US', { maximumFractionDigits: 0 })} (SLoP: {(scenario.slop * 100).toFixed(0)}%)</div>
              <div className="text-slate-100 font-bold">=&gt; SLE: ${scenario.single_loss_expectancy.toLocaleString('en-US', { maximumFractionDigits: 0 })}</div>
            </div>
          </div>

          <div className="p-4 bg-indigo-950/30 border border-indigo-800/80 rounded-lg">
            <span className="text-xs font-bold text-indigo-300 uppercase tracking-wider block mb-1">
              Step 3: Annualized Loss Expectancy (ALE)
            </span>
            <div className="text-sm font-mono text-indigo-200 mt-2">
              LEF * SLE = ALE
            </div>
            <div className="text-xs text-indigo-300 mt-2 space-y-1 font-mono">
              <div>LEF: {scenario.loss_event_frequency.toFixed(2)} / yr</div>
              <div>SLE: ${scenario.single_loss_expectancy.toLocaleString('en-US', { maximumFractionDigits: 0 })} / event</div>
              <div className="text-indigo-100 font-bold text-sm">
                =&gt; ALE: ${scenario.annualized_loss_expectancy.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} / yr
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* Assumptions & Upstream Lineage Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Three-Point PERT Inputs */}
        <Card className="p-5 bg-slate-900/90 border-slate-800">
          <CardHeader title="Three-Point PERT Parameters" subtitle="Estimates supplied by security analysts & threat intel" />
          <div className="space-y-4 text-xs font-mono">
            <div className="p-3 bg-slate-950 border border-slate-800 rounded">
              <span className="text-slate-400 block mb-1 font-sans font-semibold">Threat Frequency & Capability:</span>
              <div className="flex justify-between text-slate-200">
                <span>Min: {scenario.tef_min}/yr</span>
                <span>Mode: {scenario.tef_mode}/yr</span>
                <span>Max: {scenario.tef_max}/yr</span>
                <span className="text-indigo-400 font-bold">TCAP: {(scenario.tcap * 100).toFixed(0)}%</span>
              </div>
            </div>

            <div className="p-3 bg-slate-950 border border-slate-800 rounded">
              <span className="text-slate-400 block mb-1 font-sans font-semibold">Primary Financial Loss:</span>
              <div className="flex justify-between text-slate-200">
                <span>Min: ${scenario.pl_min.toLocaleString()}</span>
                <span>Mode: ${scenario.pl_mode.toLocaleString()}</span>
                <span>Max: ${scenario.pl_max.toLocaleString()}</span>
              </div>
            </div>

            <div className="p-3 bg-slate-950 border border-slate-800 rounded">
              <span className="text-slate-400 block mb-1 font-sans font-semibold">Secondary Financial Loss & Prob:</span>
              <div className="flex justify-between text-slate-200">
                <span>Min: ${scenario.sl_min.toLocaleString()}</span>
                <span>Mode: ${scenario.sl_mode.toLocaleString()}</span>
                <span>Max: ${scenario.sl_max.toLocaleString()}</span>
                <span className="text-amber-400 font-bold">SLoP: {(scenario.slop * 100).toFixed(0)}%</span>
              </div>
            </div>
          </div>
        </Card>

        {/* Upstream Governance Lineage & Metadata */}
        <Card className="p-5 bg-slate-900/90 border-slate-800">
          <CardHeader title="Governance Attribution & Lineage" subtitle="Upstream entity bindings and cryptographic audit metadata" />
          <div className="space-y-3 text-xs">
            <div className="flex justify-between py-2 border-b border-slate-800">
              <span className="text-slate-400">Threat Actor Category</span>
              <span className="text-slate-200 font-medium">{scenario.threat_actor_category}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-slate-800">
              <span className="text-slate-400">Phase 2 Organization Control Link</span>
              <span className="text-slate-200 font-mono">{scenario.organization_control_id ? `Control #${scenario.organization_control_id}` : 'None'}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-slate-800">
              <span className="text-slate-400">Phase 5 Qualitative Risk Link</span>
              <span className="text-slate-200 font-mono">{scenario.risk_id ? `Risk #${scenario.risk_id}` : 'None'}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-slate-800">
              <span className="text-slate-400">Phase 9 Vendor Link</span>
              <span className="text-slate-200 font-mono">{scenario.vendor_id ? `Vendor #${scenario.vendor_id}` : 'None'}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-slate-800">
              <span className="text-slate-400">Calculation Engine Version</span>
              <span className="text-slate-200 font-mono">{scenario.calculation_version}</span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-slate-400">Input Snapshot Hash</span>
              <span className="text-slate-400 font-mono text-[11px] truncate max-w-xs" title={scenario.input_snapshot_hash || ''}>
                {scenario.input_snapshot_hash || '—'}
              </span>
            </div>
          </div>
        </Card>
      </div>

      {/* Historical Monte Carlo Simulation Runs */}
      <Card className="p-5 bg-slate-900/90 border-slate-800">
        <div className="flex justify-between items-center pb-4 mb-4 border-b border-slate-800">
          <div>
            <h3 className="text-sm font-semibold text-slate-100">Historical Simulation Runs</h3>
            <p className="text-xs text-slate-400 mt-0.5">Immutable record of past Monte Carlo stochastic evaluations</p>
          </div>
          {canExecute && (
            <Button variant="outline" size="sm" onClick={() => setIsSimModalOpen(true)}>
              <Play className="h-3.5 w-3.5 mr-1" />
              New Run
            </Button>
          )}
        </div>

        {isSimulationsLoading ? (
          <LoadingSpinner />
        ) : simulations.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-xs">
            No Monte Carlo simulations executed yet for this scenario.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHead>
                <TableRow>
                  <TableHeaderCell>Run ID</TableHeaderCell>
                  <TableHeaderCell>Trials</TableHeaderCell>
                  <TableHeaderCell>Seed</TableHeaderCell>
                  <TableHeaderCell className="text-right">Mean Loss ($)</TableHeaderCell>
                  <TableHeaderCell className="text-right">Std Dev ($)</TableHeaderCell>
                  <TableHeaderCell className="text-right">P50 (Median)</TableHeaderCell>
                  <TableHeaderCell className="text-right">P95 (Tail VaR)</TableHeaderCell>
                  <TableHeaderCell className="text-right">P99 (Extreme)</TableHeaderCell>
                  <TableHeaderCell>Executed At</TableHeaderCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {simulations.map((sim) => (
                  <TableRow key={sim.id}>
                    <TableCell className="font-mono text-xs font-bold text-indigo-400">#{sim.id}</TableCell>
                    <TableCell className="font-mono text-xs text-slate-200">{sim.trial_count.toLocaleString()}</TableCell>
                    <TableCell className="font-mono text-xs text-slate-400">{sim.simulation_seed}</TableCell>
                    <TableCell className="text-right font-mono text-xs text-slate-100">
                      ${sim.mean_loss.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs text-slate-400">
                      ${sim.std_dev_loss.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs text-slate-300">
                      ${sim.percentile_50.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs font-bold text-indigo-300">
                      ${sim.percentile_95.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs font-bold text-rose-400">
                      ${sim.percentile_99.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                    </TableCell>
                    <TableCell className="text-xs text-slate-400">
                      {new Date(sim.simulated_at).toLocaleString()}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </Card>

      {/* Historical ROSI Analyses */}
      <Card className="p-5 bg-slate-900/90 border-slate-800">
        <div className="flex justify-between items-center pb-4 mb-4 border-b border-slate-800">
          <div>
            <h3 className="text-sm font-semibold text-slate-100">Return on Security Investment (ROSI) Appraisals</h3>
            <p className="text-xs text-slate-400 mt-0.5">Financial appraisal history linked to Phase 11 Remediation Plans</p>
          </div>
          {canExecute && (
            <Button variant="outline" size="sm" onClick={() => setIsRosiModalOpen(true)}>
              <Target className="h-3.5 w-3.5 mr-1" />
              New ROSI Evaluation
            </Button>
          )}
        </div>

        {isRosiLoading ? (
          <LoadingSpinner />
        ) : rosiList.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-xs">
            No ROSI analyses recorded for this scenario yet.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHead>
                <TableRow>
                  <TableHeaderCell>Record ID</TableHeaderCell>
                  <TableHeaderCell>Plan ID</TableHeaderCell>
                  <TableHeaderCell className="text-right">Remediation Cost</TableHeaderCell>
                  <TableHeaderCell className="text-right">Current ALE</TableHeaderCell>
                  <TableHeaderCell className="text-right">Projected ALE</TableHeaderCell>
                  <TableHeaderCell className="text-right">Risk Reduction (Delta ALE)</TableHeaderCell>
                  <TableHeaderCell className="text-right">Net Economic Benefit</TableHeaderCell>
                  <TableHeaderCell className="text-right">ROSI %</TableHeaderCell>
                  <TableHeaderCell>Appraised At</TableHeaderCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {rosiList.map((rosi) => (
                  <TableRow key={rosi.id}>
                    <TableCell className="font-mono text-xs font-bold text-indigo-400">#{rosi.id}</TableCell>
                    <TableCell className="font-mono text-xs text-slate-200">Plan #{rosi.remediation_plan_id}</TableCell>
                    <TableCell className="text-right font-mono text-xs text-slate-300">
                      ${rosi.remediation_cost.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs text-slate-400">
                      ${rosi.current_ale.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs text-slate-400">
                      ${rosi.projected_ale.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs font-bold text-emerald-400">
                      +${rosi.risk_reduction_ale.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                    </TableCell>
                    <TableCell
                      className={`text-right font-mono text-xs font-bold ${
                        rosi.net_economic_benefit >= 0 ? 'text-emerald-400' : 'text-rose-400'
                      }`}
                    >
                      {rosi.net_economic_benefit >= 0 ? '+' : ''}$
                      {rosi.net_economic_benefit.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                    </TableCell>
                    <TableCell className="text-right">
                      <span
                        className={`font-mono text-xs font-bold px-2 py-0.5 rounded ${
                          rosi.rosi_percentage >= 0
                            ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                            : 'bg-rose-950 text-rose-300 border border-rose-800'
                        }`}
                      >
                        {rosi.rosi_percentage >= 0 ? '+' : ''}
                        {rosi.rosi_percentage.toFixed(1)}%
                      </span>
                    </TableCell>
                    <TableCell className="text-xs text-slate-400">
                      {new Date(rosi.created_at).toLocaleString()}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </Card>

      {/* Modals */}
      {isEditModalOpen && (
        <QuantScenarioModal
          isOpen={isEditModalOpen}
          onClose={() => setIsEditModalOpen(false)}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ['quant-scenario-detail', scenarioId] });
            queryClient.invalidateQueries({ queryKey: ['quant-scenarios'] });
          }}
          scenario={scenario}
        />
      )}

      {isSimModalOpen && (
        <SimulationRunModal
          isOpen={isSimModalOpen}
          onClose={() => setIsSimModalOpen(false)}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ['quant-scenario-detail', scenarioId] });
            queryClient.invalidateQueries({ queryKey: ['quant-scenario-simulations', scenarioId] });
            queryClient.invalidateQueries({ queryKey: ['quant-scenarios'] });
          }}
          scenarioId={scenario.id}
          scenarioCode={scenario.scenario_code}
        />
      )}

      {isRosiModalOpen && (
        <RosiCalculatorModal
          isOpen={isRosiModalOpen}
          onClose={() => setIsRosiModalOpen(false)}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ['quant-scenario-rosi', scenarioId] });
          }}
          scenarioId={scenario.id}
          scenarioCode={scenario.scenario_code}
          currentAle={scenario.annualized_loss_expectancy}
        />
      )}

    </div>
  );
};
export default QuantScenarioDetailPage;
