import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { aiGovernanceService } from '../lib/aiGovernanceService';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from '../components/ui/Table';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { AISystemModal } from '../components/ai-governance/AISystemModal';
import type {
  AIAutonomyLevel,
  AIDataSensitivity,
  AIIndexCalculateResponse,
  AILifecycleState,
  AIRegulatoryTier,
  AISystem,
  AISystemCreate,
  AISystemType,
  AISystemUpdate,
} from '../types';
import {
  Activity,
  AlertOctagon,
  ArrowRight,
  Bot,
  Building2,
  Calculator,
  Edit2,
  Eye,
  Layers,
  Plus,
  RefreshCw,
  Rocket,
  Search,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Trash2,
} from 'lucide-react';

type TabKey = 'register' | 'calculator' | 'posture';

export const AIGovernancePage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { hasRole } = useAuth();

  const canManage = hasRole('ADMIN', 'MANAGER', 'GRC_ANALYST');

  const [activeTab, setActiveTab] = useState<TabKey>('register');
  const [searchQuery, setSearchQuery] = useState('');
  const [tierFilter, setTierFilter] = useState<AIRegulatoryTier | 'ALL'>('ALL');
  const [stateFilter, setStateFilter] = useState<AILifecycleState | 'ALL'>('ALL');
  const [typeFilter, setTypeFilter] = useState<AISystemType | 'ALL'>('ALL');

  // Modals state
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [editingSystem, setEditingSystem] = useState<AISystem | null>(null);

  // Ephemeral Calculator State
  const [calcTier, setCalcTier] = useState<AIRegulatoryTier>('HIGH_RISK');
  const [calcAutonomy, setCalcAutonomy] = useState<AIAutonomyLevel>('HUMAN_IN_THE_LOOP');
  const [calcDataSensitivity, setCalcDataSensitivity] = useState<AIDataSensitivity>('INTERNAL');
  const [calcProcessTier, setCalcProcessTier] = useState<string>('TIER_2');
  const [calcHallucination, setCalcHallucination] = useState<number>(3.5);
  const [calcInjectionResistance, setCalcInjectionResistance] = useState<number>(95.0);
  const [calcResult, setCalcResult] = useState<AIIndexCalculateResponse | null>(null);
  const [isCalculating, setIsCalculating] = useState(false);

  // Queries
  const {
    data: systems = [],
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ['ai-systems-list', tierFilter, stateFilter, typeFilter, searchQuery],
    queryFn: () =>
      aiGovernanceService.listSystems({
        regulatory_tier: tierFilter === 'ALL' ? undefined : tierFilter,
        lifecycle_state: stateFilter === 'ALL' ? undefined : stateFilter,
        system_type: typeFilter === 'ALL' ? undefined : typeFilter,
        search: searchQuery.trim() || undefined,
      }),
  });

  const { data: summary } = useQuery({
    queryKey: ['ai-posture-summary'],
    queryFn: () => aiGovernanceService.getPostureSummary(),
  });

  const createMutation = useMutation({
    mutationFn: (data: AISystemCreate) => aiGovernanceService.createSystem(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-systems-list'] });
      queryClient.invalidateQueries({ queryKey: ['ai-posture-summary'] });
      setIsCreateModalOpen(false);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: AISystemUpdate }) =>
      aiGovernanceService.updateSystem(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-systems-list'] });
      queryClient.invalidateQueries({ queryKey: ['ai-posture-summary'] });
      setEditingSystem(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => aiGovernanceService.deleteSystem(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-systems-list'] });
      queryClient.invalidateQueries({ queryKey: ['ai-posture-summary'] });
    },
  });

  const handleRunCalculator = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsCalculating(true);
    try {
      const res = await aiGovernanceService.calculateIndex({
        regulatory_tier: calcTier,
        autonomy_level: calcAutonomy,
        data_sensitivity: calcDataSensitivity,
        process_tier: calcProcessTier,
        hallucination_rate_percent: calcHallucination,
        prompt_injection_resistance_score: calcInjectionResistance,
      });
      setCalcResult(res);
    } catch (err) {
      console.error('Calculation preview failed', err);
    } finally {
      setIsCalculating(false);
    }
  };

  const getAriBadgeVariant = (ari: number) => {
    if (ari >= 80.0) return 'danger';
    if (ari >= 60.0) return 'warning';
    if (ari >= 40.0) return 'warning';
    if (ari >= 20.0) return 'info';
    return 'success';
  };

  const getTierBadgeVariant = (tier: AIRegulatoryTier) => {
    switch (tier) {
      case 'PROHIBITED':
        return 'danger';
      case 'HIGH_RISK':
      case 'GPAI_SYSTEMIC_RISK':
        return 'warning';
      case 'LIMITED_RISK':
        return 'info';
      case 'MINIMAL_RISK':
        return 'success';
    }
  };

  const getStateBadgeVariant = (state: AILifecycleState) => {
    switch (state) {
      case 'PRODUCTION':
        return 'success';
      case 'APPROVED_STAGING':
        return 'info';
      case 'ETHICAL_REVIEW':
      case 'VALIDATION':
        return 'warning';
      case 'DEVELOPMENT':
        return 'default';
      case 'DECOMMISSIONED':
      case 'REJECTED':
        return 'danger';
    }
  };

  return (
    <div className="space-y-6">
      {/* Workspace Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-950/80 border border-indigo-700/60 rounded-lg text-indigo-400">
              <Bot size={24} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-slate-100 tracking-tight">
                  AI Governance &amp; Algorithmic Risk Management
                </h1>
                <Badge variant="purple" className="text-[10px]">
                  AI-GRC • PHASE 15
                </Badge>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                EU AI Act conformity, Algorithmic Risk Index (ARI) mathematical telemetry, Four-Eyes deployment gates, and cross-module lineage.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            className="flex items-center gap-1.5 text-xs text-slate-300"
          >
            <RefreshCw size={14} />
            <span>Refresh</span>
          </Button>

          {canManage && (
            <Button
              variant="primary"
              size="sm"
              onClick={() => setIsCreateModalOpen(true)}
              className="flex items-center gap-1.5 text-xs shadow-xs"
            >
              <Plus size={14} />
              <span>Register AI System</span>
            </Button>
          )}
        </div>
      </div>

      {/* Executive Telemetry Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
        <Card className="p-4 border-slate-800 bg-slate-900/90 shadow-md">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Total AI Systems
            </span>
            <Bot size={16} className="text-indigo-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-slate-100">
              {summary?.total_ai_systems ?? (isLoading ? '—' : systems.length)}
            </span>
            <span className="text-[11px] text-slate-500">cataloged</span>
          </div>
        </Card>

        <Card className="p-4 border-slate-800 bg-slate-900/90 shadow-md">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              High / Systemic Risk
            </span>
            <ShieldAlert size={16} className="text-amber-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-amber-400">
              {summary?.high_risk_systems ?? 0}
            </span>
            <span className="text-[11px] text-slate-500">Annex III</span>
          </div>
        </Card>

        <Card className="p-4 border-slate-800 bg-slate-900/90 shadow-md">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Prohibited Systems
            </span>
            <AlertOctagon size={16} className="text-rose-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-rose-400">
              {summary?.prohibited_systems ?? 0}
            </span>
            <span className="text-[11px] text-rose-400/80 font-semibold">Art. 5 Banned</span>
          </div>
        </Card>

        <Card className="p-4 border-slate-800 bg-slate-900/90 shadow-md">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Live in Production
            </span>
            <Rocket size={16} className="text-emerald-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-emerald-400">
              {summary?.production_systems ?? 0}
            </span>
            <span className="text-[11px] text-slate-500">active instances</span>
          </div>
        </Card>

        <Card className="p-4 border-slate-800 bg-slate-900/90 shadow-md">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Average ARI Score
            </span>
            <Activity size={16} className="text-sky-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-sky-400">
              {summary?.average_algorithmic_risk_index !== undefined
                ? Number(summary.average_algorithmic_risk_index).toFixed(1)
                : '0.0'}
            </span>
            <span className="text-[11px] text-slate-500">/ 100.0</span>
          </div>
        </Card>
      </div>

      {/* Workspace Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab('register')}
          className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all cursor-pointer flex items-center gap-1.5 ${
            activeTab === 'register'
              ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Bot size={14} />
          <span>AI System Register ({systems.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('calculator')}
          className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all cursor-pointer flex items-center gap-1.5 ${
            activeTab === 'calculator'
              ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Calculator size={14} />
          <span>Interactive ARI Calculator</span>
        </button>

        <button
          onClick={() => setActiveTab('posture')}
          className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all cursor-pointer flex items-center gap-1.5 ${
            activeTab === 'posture'
              ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <ShieldCheck size={14} />
          <span>Enterprise Posture Analytics</span>
        </button>
      </div>

      {/* TAB 1: AI System Register */}
      {activeTab === 'register' && (
        <div className="space-y-4">
          {/* Filters & Search */}
          <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2 flex-1 min-w-[240px]">
              <div className="relative w-full max-w-sm">
                <Search size={14} className="absolute left-3 top-2.5 text-slate-500" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search code, name, foundation model..."
                  className="w-full bg-slate-950 border border-slate-700 rounded-md pl-9 pr-3 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
                />
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <select
                value={tierFilter}
                onChange={(e) => setTierFilter(e.target.value as any)}
                className="bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-300 focus:outline-hidden focus:border-indigo-500"
              >
                <option value="ALL">All Regulatory Tiers</option>
                <option value="PROHIBITED">Prohibited (Art. 5)</option>
                <option value="HIGH_RISK">High Risk (Annex III)</option>
                <option value="GPAI_SYSTEMIC_RISK">GPAI Systemic Risk</option>
                <option value="LIMITED_RISK">Limited Risk</option>
                <option value="MINIMAL_RISK">Minimal Risk</option>
              </select>

              <select
                value={stateFilter}
                onChange={(e) => setStateFilter(e.target.value as any)}
                className="bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-300 focus:outline-hidden focus:border-indigo-500"
              >
                <option value="ALL">All Lifecycle States</option>
                <option value="DEVELOPMENT">Development</option>
                <option value="VALIDATION">Validation</option>
                <option value="ETHICAL_REVIEW">Ethical Review</option>
                <option value="APPROVED_STAGING">Approved Staging</option>
                <option value="PRODUCTION">Production</option>
                <option value="DECOMMISSIONED">Decommissioned</option>
                <option value="REJECTED">Rejected</option>
              </select>

              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value as any)}
                className="bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-300 focus:outline-hidden focus:border-indigo-500"
              >
                <option value="ALL">All System Types</option>
                <option value="LLM_APPLICATION">LLM Application</option>
                <option value="AGENTIC_WORKFLOW">Agentic Workflow</option>
                <option value="EMBEDDED_ML">Embedded ML</option>
                <option value="COMPUTER_VISION">Computer Vision</option>
                <option value="RECOMMENDER">Recommender</option>
                <option value="PREDICTIVE_ANALYTICS">Predictive Analytics</option>
              </select>
            </div>
          </div>

          {/* Registry Table */}
          <Card className="border-slate-800 bg-slate-900/90 shadow-xl overflow-hidden">
            {isLoading ? (
              <div className="p-12 flex flex-col items-center justify-center gap-3">
                <LoadingSpinner />
                <span className="text-xs text-slate-400 font-medium">
                  Loading AI systems registry...
                </span>
              </div>
            ) : isError ? (
              <div className="p-8 text-center text-xs text-rose-400">
                Failed to load AI systems registry. Verify your backend connection.
              </div>
            ) : systems.length === 0 ? (
              <div className="p-12 text-center space-y-3">
                <Bot size={36} className="mx-auto text-slate-600" />
                <h3 className="text-sm font-semibold text-slate-300">
                  No AI Systems Registered
                </h3>
                <p className="text-xs text-slate-500 max-w-sm mx-auto">
                  Catalog your algorithmic models, agentic workflows, and LLMs to enforce EU AI Act conformity and risk governance.
                </p>
                {canManage && (
                  <Button
                    size="sm"
                    variant="primary"
                    onClick={() => setIsCreateModalOpen(true)}
                    className="mt-2"
                  >
                    Register First AI System
                  </Button>
                )}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableHeaderCell>System Code &amp; Name</TableHeaderCell>
                      <TableHeaderCell>Type &amp; Hosting</TableHeaderCell>
                      <TableHeaderCell>EU Regulatory Tier</TableHeaderCell>
                      <TableHeaderCell>Autonomy</TableHeaderCell>
                      <TableHeaderCell>ARI Score</TableHeaderCell>
                      <TableHeaderCell>Lifecycle State</TableHeaderCell>
                      <TableHeaderCell>Lineage Links</TableHeaderCell>
                      <TableHeaderCell className="text-right">Actions</TableHeaderCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {systems.map((sys) => {
                      const ari = Number(sys.algorithmic_risk_index) || 0.0;
                      const isDecommissioned = sys.lifecycle_state === 'DECOMMISSIONED';
                      const isProduction = sys.lifecycle_state === 'PRODUCTION';

                      return (
                        <TableRow key={sys.id} className="hover:bg-slate-800/40">
                          <TableCell>
                            <div>
                              <Link
                                to={`/ai-governance/systems/${sys.id}`}
                                className="text-xs font-bold text-indigo-400 hover:underline font-mono flex items-center gap-1.5"
                              >
                                <span>{sys.system_code}</span>
                                <ArrowRight size={12} />
                              </Link>
                              <span className="text-xs text-slate-200 block font-semibold truncate max-w-[200px]">
                                {sys.name}
                              </span>
                              {sys.foundation_model_name && (
                                <span className="text-[10px] text-slate-400">
                                  Model: {sys.foundation_model_name}
                                </span>
                              )}
                            </div>
                          </TableCell>

                          <TableCell>
                            <span className="text-xs text-slate-300 block font-medium">
                              {sys.system_type.replace(/_/g, ' ')}
                            </span>
                            <span className="text-[10px] text-slate-400 block font-mono">
                              {sys.hosting_type.replace(/_/g, ' ')}
                            </span>
                          </TableCell>

                          <TableCell>
                            <Badge variant={getTierBadgeVariant(sys.regulatory_tier)} className="text-[10px]">
                              {sys.regulatory_tier.replace(/_/g, ' ')}
                            </Badge>
                            {sys.is_prohibited_practice && (
                              <span className="block text-[10px] text-rose-400 font-semibold mt-0.5">
                                Art. 5 Prohibited
                              </span>
                            )}
                          </TableCell>

                          <TableCell>
                            <span className="text-xs text-slate-300 font-medium block">
                              {sys.autonomy_level.replace(/_/g, ' ')}
                            </span>
                            <span className="text-[10px] text-slate-400 block">
                              Data: {sys.data_sensitivity}
                            </span>
                          </TableCell>

                          <TableCell>
                            <div className="flex items-center gap-1.5">
                              <span className="font-mono font-bold text-xs text-slate-200">
                                {ari.toFixed(2)}
                              </span>
                              <Badge variant={getAriBadgeVariant(ari)} className="text-[9px] px-1.5 py-0">
                                {ari >= 80 ? 'CRITICAL' : ari >= 60 ? 'HIGH' : ari >= 40 ? 'MOD' : 'LOW'}
                              </Badge>
                            </div>
                          </TableCell>

                          <TableCell>
                            <Badge variant={getStateBadgeVariant(sys.lifecycle_state)} className="text-[10px]">
                              {sys.lifecycle_state.replace(/_/g, ' ')}
                            </Badge>
                          </TableCell>

                          <TableCell>
                            <div className="flex items-center gap-2 text-xs">
                              {sys.business_process_id && (
                                <span title={`Linked Business Process #${sys.business_process_id}`}>
                                  <Layers size={13} className="text-sky-400" />
                                </span>
                              )}
                              {sys.vendor_id && (
                                <span title={`Linked Vendor #${sys.vendor_id}`}>
                                  <Building2 size={13} className="text-amber-400" />
                                </span>
                              )}
                              {sys.remediation_plan_id && (
                                <span title={`Linked Remediation #${sys.remediation_plan_id}`}>
                                  <Shield size={13} className="text-purple-400" />
                                </span>
                              )}
                              {!sys.business_process_id && !sys.vendor_id && !sys.remediation_plan_id && (
                                <span className="text-slate-600 text-[11px]">—</span>
                              )}
                            </div>
                          </TableCell>

                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-1.5">
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => navigate(`/ai-governance/systems/${sys.id}`)}
                                title="View System Dossier"
                                className="p-1.5 h-7 w-7 text-indigo-400 border-indigo-700/40 hover:bg-indigo-950/40"
                              >
                                <Eye size={13} />
                              </Button>

                              {canManage && (
                                <>
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    disabled={isDecommissioned}
                                    onClick={() => setEditingSystem(sys)}
                                    title={isDecommissioned ? 'Decommissioned systems are immutable' : 'Edit System'}
                                    className="p-1.5 h-7 w-7 text-slate-400 hover:text-slate-200 border-slate-700 disabled:opacity-30"
                                  >
                                    <Edit2 size={13} />
                                  </Button>

                                  <Button
                                    size="sm"
                                    variant="danger"
                                    disabled={isProduction}
                                    onClick={() => {
                                      if (
                                        window.confirm(
                                          `Are you sure you want to delete AI system ${sys.system_code}? This action cannot be undone.`
                                        )
                                      ) {
                                        deleteMutation.mutate(sys.id);
                                      }
                                    }}
                                    title={isProduction ? 'Production systems cannot be deleted' : 'Delete System'}
                                    className="p-1.5 h-7 w-7 disabled:opacity-30"
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
        </div>
      )}

      {/* TAB 2: Interactive Ephemeral ARI Calculator */}
      {activeTab === 'calculator' && (
        <Card className="border-slate-800 bg-slate-900/90 shadow-xl p-6">
          <div className="flex items-center gap-3 border-b border-slate-800 pb-4 mb-6">
            <div className="p-2 bg-indigo-950/80 border border-indigo-700/60 rounded-lg text-indigo-400">
              <Calculator size={20} />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
                Ephemeral Algorithmic Risk Index (ARI) Mathematical Simulator
              </h3>
              <p className="text-xs text-slate-400">
                Simulate server-authoritative ARI calculations without persisting state.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Input Simulation Parameters Form */}
            <form onSubmit={handleRunCalculator} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Regulatory Tier
                  </label>
                  <select
                    value={calcTier}
                    onChange={(e) => setCalcTier(e.target.value as AIRegulatoryTier)}
                    className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-xs text-slate-100 focus:outline-hidden focus:border-indigo-500"
                  >
                    <option value="PROHIBITED">PROHIBITED (Base 100.0)</option>
                    <option value="HIGH_RISK">HIGH RISK (Base 65.0)</option>
                    <option value="GPAI_SYSTEMIC_RISK">GPAI SYSTEMIC RISK (Base 50.0)</option>
                    <option value="LIMITED_RISK">LIMITED RISK (Base 25.0)</option>
                    <option value="MINIMAL_RISK">MINIMAL RISK (Base 5.0)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Autonomy Level
                  </label>
                  <select
                    value={calcAutonomy}
                    onChange={(e) => setCalcAutonomy(e.target.value as AIAutonomyLevel)}
                    className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-xs text-slate-100 focus:outline-hidden focus:border-indigo-500"
                  >
                    <option value="FULL_AUTONOMY">FULL AUTONOMY (1.40x)</option>
                    <option value="HUMAN_ON_THE_LOOP">HUMAN ON THE LOOP (1.20x)</option>
                    <option value="HUMAN_IN_THE_LOOP">HUMAN IN THE LOOP (1.00x)</option>
                    <option value="NO_AUTONOMY">NO AUTONOMY (0.80x)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Data Sensitivity
                  </label>
                  <select
                    value={calcDataSensitivity}
                    onChange={(e) => setCalcDataSensitivity(e.target.value as AIDataSensitivity)}
                    className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-xs text-slate-100 focus:outline-hidden focus:border-indigo-500"
                  >
                    <option value="RESTRICTED_PII_PHI">RESTRICTED PII/PHI (+15.0)</option>
                    <option value="CONFIDENTIAL">CONFIDENTIAL (+8.0)</option>
                    <option value="INTERNAL">INTERNAL (+2.0)</option>
                    <option value="PUBLIC">PUBLIC (+0.0)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Process Criticality Tier
                  </label>
                  <select
                    value={calcProcessTier}
                    onChange={(e) => setCalcProcessTier(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-xs text-slate-100 focus:outline-hidden focus:border-indigo-500"
                  >
                    <option value="TIER_1">TIER 1 (Mission Critical - 1.25x)</option>
                    <option value="TIER_2">TIER 2 (Core Business - 1.15x)</option>
                    <option value="TIER_3">TIER 3 (Important - 1.05x)</option>
                    <option value="TIER_4">TIER 4 (Standard - 1.00x)</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-slate-800">
                <div>
                  <label className="block text-[11px] font-medium text-slate-400 mb-1">
                    Hallucination Rate (%: 0.0 - 100.0)
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                    value={calcHallucination}
                    onChange={(e) => setCalcHallucination(parseFloat(e.target.value) || 0)}
                    className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-100 font-mono focus:outline-hidden focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-medium text-slate-400 mb-1">
                    Injection Resistance (%: 0.0 - 100.0)
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                    value={calcInjectionResistance}
                    onChange={(e) => setCalcInjectionResistance(parseFloat(e.target.value) || 0)}
                    className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-100 font-mono focus:outline-hidden focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="pt-2">
                <Button type="submit" variant="primary" isLoading={isCalculating} className="w-full">
                  Compute Server ARI Preview
                </Button>
              </div>
            </form>

            {/* Live Authoritative Results Showcase */}
            <div className="p-5 bg-slate-950 rounded-xl border border-slate-800 flex flex-col justify-between space-y-4">
              <div>
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">
                  Server Calculation Response
                </span>

                {calcResult ? (
                  <div className="space-y-4">
                    <div className="flex items-baseline justify-between p-4 bg-slate-900 rounded-xl border border-slate-800">
                      <div>
                        <span className="text-[11px] text-slate-400 block uppercase">
                          Authoritative Simulated ARI
                        </span>
                        <span className="text-3xl font-extrabold font-mono text-indigo-400">
                          {Number(calcResult.algorithmic_risk_index).toFixed(2)}
                        </span>
                        <span className="text-xs text-slate-500 font-mono ml-1">/ 100.00</span>
                      </div>
                      <Badge variant={getAriBadgeVariant(calcResult.algorithmic_risk_index)}>
                        {calcResult.algorithmic_risk_index >= 80
                          ? 'CRITICAL'
                          : calcResult.algorithmic_risk_index >= 60
                          ? 'HIGH'
                          : calcResult.algorithmic_risk_index >= 40
                          ? 'MODERATE'
                          : 'LOW'}
                      </Badge>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="p-2.5 bg-slate-900 rounded border border-slate-800/80">
                        <span className="text-[10px] text-slate-500 uppercase block">Base Risk</span>
                        <span className="font-bold text-slate-200 font-mono">
                          {calcResult.base_risk.toFixed(1)}
                        </span>
                      </div>
                      <div className="p-2.5 bg-slate-900 rounded border border-slate-800/80">
                        <span className="text-[10px] text-slate-500 uppercase block">Autonomy Multiplier</span>
                        <span className="font-bold text-slate-200 font-mono">
                          {calcResult.autonomy_multiplier.toFixed(2)}x
                        </span>
                      </div>
                      <div className="p-2.5 bg-slate-900 rounded border border-slate-800/80">
                        <span className="text-[10px] text-slate-500 uppercase block">Process Multiplier</span>
                        <span className="font-bold text-slate-200 font-mono">
                          {calcResult.process_tier_multiplier.toFixed(2)}x
                        </span>
                      </div>
                      <div className="p-2.5 bg-slate-900 rounded border border-slate-800/80">
                        <span className="text-[10px] text-slate-500 uppercase block">Safety Penalty</span>
                        <span className="font-bold text-slate-200 font-mono">
                          +{calcResult.safety_penalty.toFixed(2)}
                        </span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="p-8 text-center text-xs text-slate-500 space-y-2">
                    <Activity size={24} className="mx-auto text-slate-700" />
                    <span>Adjust parameters and submit to execute a server-side ARI mathematical simulation.</span>
                  </div>
                )}
              </div>

              <div className="p-3 bg-slate-900/80 border border-slate-800/80 rounded-lg text-[11px] text-slate-400">
                <strong className="text-slate-300">Mathematical Formula:</strong>{' '}
                <code className="text-indigo-300 font-mono">
                  ARI = min(100.0, (BaseRisk * AutonomyMult * ProcessMult) + SafetyPenalty)
                </code>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* TAB 3: Posture Analytics */}
      {activeTab === 'posture' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Regulatory Tier Distribution */}
          <Card className="border-slate-800 bg-slate-900/90 shadow-xl p-5 space-y-4">
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
              <ShieldCheck size={16} className="text-indigo-400" />
              EU AI Act Tier Distribution
            </h3>

            {summary?.tier_distribution ? (
              <div className="space-y-3">
                {Object.entries(summary.tier_distribution).map(([tier, count]) => {
                  const pct = summary.total_ai_systems > 0 ? (count / summary.total_ai_systems) * 100 : 0;
                  return (
                    <div key={tier} className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-300 font-medium">
                          {tier.replace(/_/g, ' ')}
                        </span>
                        <span className="font-mono text-slate-400">
                          {count} ({pct.toFixed(0)}%)
                        </span>
                      </div>
                      <div className="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800">
                        <div
                          className={`h-full rounded-full ${
                            tier === 'PROHIBITED'
                              ? 'bg-rose-500'
                              : tier === 'HIGH_RISK'
                              ? 'bg-amber-500'
                              : tier === 'GPAI_SYSTEMIC_RISK'
                              ? 'bg-orange-500'
                              : tier === 'LIMITED_RISK'
                              ? 'bg-sky-500'
                              : 'bg-emerald-500'
                          }`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-xs text-slate-500 py-4 text-center">No tier data available.</div>
            )}
          </Card>

          {/* Lifecycle State Distribution */}
          <Card className="border-slate-800 bg-slate-900/90 shadow-xl p-5 space-y-4">
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
              <Layers size={16} className="text-indigo-400" />
              AI Lifecycle State Distribution
            </h3>

            {summary?.lifecycle_distribution ? (
              <div className="space-y-3">
                {Object.entries(summary.lifecycle_distribution).map(([state, count]) => {
                  const pct = summary.total_ai_systems > 0 ? (count / summary.total_ai_systems) * 100 : 0;
                  return (
                    <div key={state} className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-300 font-medium">
                          {state.replace(/_/g, ' ')}
                        </span>
                        <span className="font-mono text-slate-400">
                          {count} ({pct.toFixed(0)}%)
                        </span>
                      </div>
                      <div className="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800">
                        <div
                          className={`h-full rounded-full ${
                            state === 'PRODUCTION'
                              ? 'bg-emerald-500'
                              : state === 'APPROVED_STAGING'
                              ? 'bg-sky-500'
                              : state === 'ETHICAL_REVIEW'
                              ? 'bg-purple-500'
                              : state === 'VALIDATION'
                              ? 'bg-amber-500'
                              : state === 'DECOMMISSIONED' || state === 'REJECTED'
                              ? 'bg-rose-500'
                              : 'bg-slate-500'
                          }`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-xs text-slate-500 py-4 text-center">No lifecycle data available.</div>
            )}
          </Card>
        </div>
      )}

      {/* Modal: Register New AI System */}
      <AISystemModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSubmit={async (data) => {
          await createMutation.mutateAsync(data as AISystemCreate);
        }}
        isSubmitting={createMutation.isPending}
      />

      {/* Modal: Edit AI System */}
      <AISystemModal
        isOpen={!!editingSystem}
        initialData={editingSystem}
        onClose={() => setEditingSystem(null)}
        onSubmit={async (data) => {
          if (editingSystem) {
            await updateMutation.mutateAsync({
              id: editingSystem.id,
              data: data as AISystemUpdate,
            });
          }
        }}
        isSubmitting={updateMutation.isPending}
      />
    </div>
  );
};
