import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../context/AuthContext';
import { aiGovernanceService } from '../lib/aiGovernanceService';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { AISystemModal } from '../components/ai-governance/AISystemModal';
import { AIModelCardModal } from '../components/ai-governance/AIModelCardModal';
import { DeploymentApprovalModal } from '../components/ai-governance/DeploymentApprovalModal';
import { DeploymentReviewModal } from '../components/ai-governance/DeploymentReviewModal';
import { ARIExposureCard } from '../components/ai-governance/ARIExposureCard';
import { AIComplianceCard } from '../components/ai-governance/AIComplianceCard';
import { AIGovernanceLineageCard } from '../components/ai-governance/AIGovernanceLineageCard';
import { Modal } from '../components/ui/Modal';
import type {
  AIDeploymentApproval,
  AIDeploymentApprovalCreate,
  AIDeploymentApprovalReviewRequest,
  AILifecycleState,
  AIModelCardCreate,
  AISystemStatusUpdate,
  AISystemUpdate,
} from '../types';
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  BookOpen,
  Bot,
  Cpu,
  Edit2,
  Layers,
  Lock,
  Plus,
  RefreshCw,
  Rocket,
  ShieldAlert,
  ShieldCheck,
} from 'lucide-react';

type TabKey = 'telemetry' | 'model-cards' | 'approvals' | 'lineage';

export const AISystemDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const systemId = Number(id);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { hasRole, user } = useAuth();

  const canManage = hasRole('ADMIN', 'MANAGER', 'GRC_ANALYST');
  const canAssess = hasRole('ADMIN', 'MANAGER', 'GRC_ANALYST', 'SECURITY_ANALYST');
  const canApprove = hasRole('ADMIN', 'MANAGER');

  const [activeTab, setActiveTab] = useState<TabKey>('telemetry');

  // Modals state
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isModelCardModalOpen, setIsModelCardModalOpen] = useState(false);
  const [isDeploymentModalOpen, setIsDeploymentModalOpen] = useState(false);
  const [reviewingApproval, setReviewingApproval] = useState<AIDeploymentApproval | null>(null);
  const [isLifecycleModalOpen, setIsLifecycleModalOpen] = useState(false);
  const [targetLifecycleState, setTargetLifecycleState] = useState<AILifecycleState>('VALIDATION');
  const [lifecycleNotes, setLifecycleNotes] = useState('');
  const [lifecycleError, setLifecycleError] = useState<string | null>(null);

  // Query: System Detail
  const {
    data: system,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ['ai-system-detail', systemId],
    queryFn: () => aiGovernanceService.getSystem(systemId),
    enabled: !isNaN(systemId),
  });

  // Mutations
  const updateSystemMutation = useMutation({
    mutationFn: (data: AISystemUpdate) => aiGovernanceService.updateSystem(systemId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-system-detail', systemId] });
      queryClient.invalidateQueries({ queryKey: ['ai-systems-list'] });
      setIsEditModalOpen(false);
    },
  });

  const createModelCardMutation = useMutation({
    mutationFn: (data: AIModelCardCreate) =>
      aiGovernanceService.createModelCard(systemId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-system-detail', systemId] });
      queryClient.invalidateQueries({ queryKey: ['ai-systems-list'] });
      setIsModelCardModalOpen(false);
    },
  });

  const requestDeploymentMutation = useMutation({
    mutationFn: (data: AIDeploymentApprovalCreate) =>
      aiGovernanceService.requestDeploymentApproval(systemId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-system-detail', systemId] });
      queryClient.invalidateQueries({ queryKey: ['ai-systems-list'] });
      setIsDeploymentModalOpen(false);
    },
  });

  const reviewDeploymentMutation = useMutation({
    mutationFn: ({
      approvalId,
      data,
    }: {
      approvalId: number;
      data: AIDeploymentApprovalReviewRequest;
    }) => aiGovernanceService.reviewDeploymentApproval(approvalId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-system-detail', systemId] });
      queryClient.invalidateQueries({ queryKey: ['ai-systems-list'] });
      setReviewingApproval(null);
    },
  });

  const updateLifecycleMutation = useMutation({
    mutationFn: (data: AISystemStatusUpdate) =>
      aiGovernanceService.updateLifecycle(systemId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-system-detail', systemId] });
      queryClient.invalidateQueries({ queryKey: ['ai-systems-list'] });
      setIsLifecycleModalOpen(false);
      setLifecycleNotes('');
      setLifecycleError(null);
    },
    onError: (err: any) => {
      setLifecycleError(
        err.response?.data?.detail ||
          err.message ||
          'Failed to update lifecycle state. Verify state prerequisites.'
      );
    },
  });

  if (isLoading) {
    return (
      <div className="p-16 flex flex-col items-center justify-center gap-3">
        <LoadingSpinner />
        <span className="text-xs text-slate-400 font-medium">Loading AI System dossier...</span>
      </div>
    );
  }

  if (isError || !system) {
    return (
      <div className="p-8 text-center space-y-3">
        <AlertTriangle size={32} className="mx-auto text-rose-400" />
        <h3 className="text-sm font-semibold text-slate-200">AI System Not Found</h3>
        <p className="text-xs text-slate-400">
          The requested system may not exist or belongs to another organization context.
        </p>
        <Button variant="outline" size="sm" onClick={() => navigate('/ai-governance')}>
          Back to AI Register
        </Button>
      </div>
    );
  }

  const isDecommissioned = system.lifecycle_state === 'DECOMMISSIONED';
  const isProhibited = system.regulatory_tier === 'PROHIBITED' || system.is_prohibited_practice;

  // Lifecycle state options based on legal state machine
  const getLegalNextStates = (current: AILifecycleState): AILifecycleState[] => {
    switch (current) {
      case 'DEVELOPMENT':
        return ['VALIDATION', 'REJECTED', 'DECOMMISSIONED'];
      case 'VALIDATION':
        return ['ETHICAL_REVIEW', 'DEVELOPMENT', 'REJECTED', 'DECOMMISSIONED'];
      case 'ETHICAL_REVIEW':
        return ['APPROVED_STAGING', 'VALIDATION', 'REJECTED', 'DECOMMISSIONED'];
      case 'APPROVED_STAGING':
        return ['PRODUCTION', 'VALIDATION', 'DECOMMISSIONED'];
      case 'PRODUCTION':
        return ['ETHICAL_REVIEW', 'DECOMMISSIONED'];
      case 'REJECTED':
        return ['DEVELOPMENT', 'DECOMMISSIONED'];
      case 'DECOMMISSIONED':
        return [];
    }
  };

  const legalNextStates = getLegalNextStates(system.lifecycle_state);

  return (
    <div className="space-y-6">
      {/* Header & Back Navigation */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div className="space-y-2">
          <button
            onClick={() => navigate('/ai-governance')}
            className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
          >
            <ArrowLeft size={14} />
            <span>Back to AI Systems Register</span>
          </button>

          <div className="flex flex-wrap items-center gap-3">
            <div className="p-2 bg-indigo-950/80 border border-indigo-700/60 rounded-lg text-indigo-400">
              <Bot size={22} />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-sm font-bold text-indigo-400">
                  {system.system_code}
                </span>
                <span className="text-slate-600 font-bold">•</span>
                <h1 className="text-lg font-bold text-slate-100">{system.name}</h1>
                <Badge
                  variant={
                    system.lifecycle_state === 'PRODUCTION'
                      ? 'success'
                      : system.lifecycle_state === 'APPROVED_STAGING'
                      ? 'info'
                      : system.lifecycle_state === 'DECOMMISSIONED' || system.lifecycle_state === 'REJECTED'
                      ? 'danger'
                      : 'warning'
                  }
                  className="text-[10px]"
                >
                  {system.lifecycle_state.replace(/_/g, ' ')}
                </Badge>
              </div>

              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-400 mt-1">
                <span>
                  Type: <strong className="text-slate-300">{system.system_type.replace(/_/g, ' ')}</strong>
                </span>
                <span>
                  Hosting: <strong className="text-slate-300">{system.hosting_type.replace(/_/g, ' ')}</strong>
                </span>
                <span>
                  Owner ID: <strong className="text-slate-300">#{system.owner_id}</strong>
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Global System Actions */}
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            className="flex items-center gap-1.5 text-xs text-slate-300"
          >
            <RefreshCw size={14} />
            <span>Refresh</span>
          </Button>

          {canAssess && !isDecommissioned && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsModelCardModalOpen(true)}
              className="flex items-center gap-1.5 text-xs text-indigo-300 border-indigo-700/50 hover:bg-indigo-950/40"
            >
              <BookOpen size={14} />
              <span>Publish Model Card</span>
            </Button>
          )}

          {canManage && !isDecommissioned && (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  if (legalNextStates.length > 0) {
                    setTargetLifecycleState(legalNextStates[0]);
                    setIsLifecycleModalOpen(true);
                  }
                }}
                disabled={legalNextStates.length === 0}
                className="flex items-center gap-1.5 text-xs text-sky-300 border-sky-700/50 hover:bg-sky-950/40"
              >
                <Layers size={14} />
                <span>Lifecycle State</span>
              </Button>

              <Button
                variant="primary"
                size="sm"
                onClick={() => setIsDeploymentModalOpen(true)}
                className="flex items-center gap-1.5 text-xs shadow-xs"
              >
                <Rocket size={14} />
                <span>Request Deployment</span>
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsEditModalOpen(true)}
                className="flex items-center gap-1.5 text-xs text-slate-300"
              >
                <Edit2 size={13} />
                <span>Edit</span>
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Prohibited Alert Callout */}
      {isProhibited && (
        <div className="p-4 bg-rose-950/90 border border-rose-800 rounded-xl flex items-start gap-3 text-xs text-rose-200">
          <ShieldAlert size={20} className="text-rose-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <span className="font-bold text-sm block text-rose-100">
              EU AI Act Article 5 Prohibited Practice Classification
            </span>
            <p className="text-rose-300/90 leading-relaxed">
              This system is categorized under prohibited AI practices (e.g. subliminal manipulation, social scoring, biometric categorization). The platform blocks staging/production promotion.
            </p>
          </div>
        </div>
      )}

      {/* Decommissioned Lock Callout */}
      {isDecommissioned && (
        <div className="p-3.5 bg-slate-950 border border-slate-800 rounded-xl flex items-center gap-3 text-xs text-slate-400">
          <Lock size={16} className="text-rose-400 shrink-0" />
          <span>
            <strong>System Decommissioned:</strong> This AI system is permanently immutable for compliance audit trails. Modifications and deployment approvals are blocked.
          </span>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab('telemetry')}
          className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all cursor-pointer flex items-center gap-1.5 ${
            activeTab === 'telemetry'
              ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Activity size={14} />
          <span>Risk Telemetry &amp; EU Conformity</span>
        </button>

        <button
          onClick={() => setActiveTab('model-cards')}
          className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all cursor-pointer flex items-center gap-1.5 ${
            activeTab === 'model-cards'
              ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <BookOpen size={14} />
          <span>Model Cards ({system.model_cards?.length || 0})</span>
        </button>

        <button
          onClick={() => setActiveTab('approvals')}
          className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all cursor-pointer flex items-center gap-1.5 ${
            activeTab === 'approvals'
              ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Rocket size={14} />
          <span>Deployment Gates ({system.deployment_approvals?.length || 0})</span>
        </button>

        <button
          onClick={() => setActiveTab('lineage')}
          className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all cursor-pointer flex items-center gap-1.5 ${
            activeTab === 'lineage'
              ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Layers size={14} />
          <span>Cross-Module Lineage</span>
        </button>
      </div>

      {/* TAB 1: Risk Telemetry & EU Conformity */}
      {activeTab === 'telemetry' && (
        <div className="space-y-6">
          <ARIExposureCard system={system} />
          <AIComplianceCard system={system} />

          {/* Technical Specifications Dossier Card */}
          <Card className="border-slate-800 bg-slate-900/90 shadow-xl p-5 space-y-4">
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
              <Cpu size={16} className="text-indigo-400" />
              Technical Telemetry &amp; Architecture Specs
            </h3>

            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 text-xs">
              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                <span className="text-[10px] text-slate-500 uppercase block">Foundation Model</span>
                <span className="font-semibold text-slate-200 truncate block">
                  {system.foundation_model_name || 'Custom Architecture'}
                </span>
              </div>

              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                <span className="text-[10px] text-slate-500 uppercase block">Model Version</span>
                <span className="font-semibold text-slate-200 font-mono block">
                  {system.model_version || '1.0.0'}
                </span>
              </div>

              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                <span className="text-[10px] text-slate-500 uppercase block">Data Cutoff</span>
                <span className="font-semibold text-slate-200 font-mono block">
                  {system.training_data_cutoff || 'N/A'}
                </span>
              </div>

              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                <span className="text-[10px] text-slate-500 uppercase block">Parameters</span>
                <span className="font-semibold text-slate-200 font-mono block">
                  {system.parameters_billion ? `${system.parameters_billion}B` : '—'}
                </span>
              </div>

              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                <span className="text-[10px] text-slate-500 uppercase block">Context Window</span>
                <span className="font-semibold text-slate-200 font-mono block">
                  {system.context_window_tokens ? `${system.context_window_tokens.toLocaleString()} tokens` : '—'}
                </span>
              </div>

              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                <span className="text-[10px] text-slate-500 uppercase block">Compute FLOPs</span>
                <span className="font-semibold text-slate-200 font-mono block">
                  {system.compute_flops_exponent ? `10^${system.compute_flops_exponent}` : '—'}
                </span>
              </div>
            </div>

            {system.description && (
              <div className="pt-2 border-t border-slate-800">
                <span className="text-[10px] text-slate-500 uppercase block mb-1">Operational Description</span>
                <p className="text-xs text-slate-300 leading-relaxed bg-slate-950 p-3 rounded-lg border border-slate-800">
                  {system.description}
                </p>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* TAB 2: Model Cards & Benchmarks */}
      {activeTab === 'model-cards' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
              Registered Model Cards &amp; Safety Benchmarks
            </h3>
            {canAssess && !isDecommissioned && (
              <Button
                size="sm"
                variant="primary"
                onClick={() => setIsModelCardModalOpen(true)}
                className="flex items-center gap-1.5 text-xs"
              >
                <Plus size={13} />
                <span>Publish New Card Version</span>
              </Button>
            )}
          </div>

          {!system.model_cards || system.model_cards.length === 0 ? (
            <Card className="p-8 text-center space-y-2 border-slate-800 bg-slate-900/90">
              <BookOpen size={32} className="mx-auto text-slate-600" />
              <h4 className="text-sm font-semibold text-slate-300">No Model Cards Published</h4>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Publish a model card with safety and accuracy telemetry (hallucination rate, prompt injection resistance) to verify EU AI Act conformity.
              </p>
            </Card>
          ) : (
            <div className="space-y-4">
              {system.model_cards.map((card) => (
                <Card key={card.id} className="border-slate-800 bg-slate-900/90 p-5 space-y-4 shadow-md">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                    <div className="flex items-center gap-2">
                      <Badge variant="purple" className="text-xs font-mono">
                        Version {card.version}
                      </Badge>
                      <span className="text-[11px] text-slate-400">
                        Published: {new Date(card.created_at).toLocaleString()}
                      </span>
                    </div>

                    {card.benchmark_eval_dataset && (
                      <span className="text-xs text-slate-300 bg-slate-950 px-2.5 py-1 rounded border border-slate-800">
                        Eval: <strong className="text-indigo-400">{card.benchmark_eval_dataset}</strong>
                        {card.benchmark_score && (
                          <span className="ml-1 font-mono text-slate-200">({Number(card.benchmark_score).toFixed(1)}%)</span>
                        )}
                      </span>
                    )}
                  </div>

                  {/* Safety & Accuracy Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                    <div className="p-2.5 bg-slate-950 rounded border border-slate-800">
                      <span className="text-[10px] text-slate-500 uppercase block">Hallucination Rate</span>
                      <span className="font-bold text-slate-200 font-mono">
                        {Number(card.hallucination_rate_percent).toFixed(2)}%
                      </span>
                    </div>

                    <div className="p-2.5 bg-slate-950 rounded border border-slate-800">
                      <span className="text-[10px] text-slate-500 uppercase block">Injection Resistance</span>
                      <span className="font-bold text-emerald-400 font-mono">
                        {Number(card.prompt_injection_resistance_score).toFixed(2)}%
                      </span>
                    </div>

                    <div className="p-2.5 bg-slate-950 rounded border border-slate-800">
                      <span className="text-[10px] text-slate-500 uppercase block">Toxicity Filter Efficiency</span>
                      <span className="font-bold text-sky-400 font-mono">
                        {Number(card.toxicity_filter_efficiency_score).toFixed(2)}%
                      </span>
                    </div>

                    <div className="p-2.5 bg-slate-950 rounded border border-slate-800">
                      <span className="text-[10px] text-slate-500 uppercase block">Synthetic Data</span>
                      <span className="font-bold text-slate-200 font-mono">
                        {Number(card.synthetic_data_percentage).toFixed(2)}%
                      </span>
                    </div>
                  </div>

                  {/* Intended Use & Mitigations */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                    <div className="p-3 bg-slate-950/70 rounded-lg border border-slate-800/80">
                      <span className="text-[10px] text-slate-400 font-semibold uppercase block mb-1">
                        Intended Operating Scope
                      </span>
                      <p className="text-slate-300 leading-relaxed">{card.intended_use}</p>
                    </div>

                    {card.bias_mitigation_notes && (
                      <div className="p-3 bg-slate-950/70 rounded-lg border border-slate-800/80">
                        <span className="text-[10px] text-slate-400 font-semibold uppercase block mb-1">
                          Bias &amp; Fairness Mitigations
                        </span>
                        <p className="text-slate-300 leading-relaxed">{card.bias_mitigation_notes}</p>
                      </div>
                    )}
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: Four-Eyes Deployment Approvals */}
      {activeTab === 'approvals' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
              Four-Eyes Deployment Approval History
            </h3>
            {canManage && !isDecommissioned && (
              <Button
                size="sm"
                variant="primary"
                onClick={() => setIsDeploymentModalOpen(true)}
                className="flex items-center gap-1.5 text-xs"
              >
                <Plus size={13} />
                <span>Request Deployment</span>
              </Button>
            )}
          </div>

          {!system.deployment_approvals || system.deployment_approvals.length === 0 ? (
            <Card className="p-8 text-center space-y-2 border-slate-800 bg-slate-900/90">
              <Rocket size={32} className="mx-auto text-slate-600" />
              <h4 className="text-sm font-semibold text-slate-300">No Deployment Approvals Requested</h4>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Promoting AI systems to Staging or Production requires independent Four-Eyes approval gatekeeping.
              </p>
            </Card>
          ) : (
            <div className="space-y-3">
              {system.deployment_approvals.map((approval) => {
                const isRequester = !!(user && user.id === approval.requested_by_id);
                const isPending = approval.approval_status === 'PENDING';

                return (
                  <Card key={approval.id} className="border-slate-800 bg-slate-900/90 p-5 space-y-3 shadow-md">
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-slate-100 font-mono">
                          Target: {approval.target_environment}
                        </span>
                        <Badge
                          variant={
                            approval.approval_status === 'APPROVED'
                              ? 'success'
                              : approval.approval_status === 'REJECTED'
                              ? 'danger'
                              : 'warning'
                          }
                          className="text-[10px]"
                        >
                          {approval.approval_status}
                        </Badge>
                      </div>

                      <span className="text-[11px] text-slate-400 font-mono">
                        Requested: {new Date(approval.created_at).toLocaleString()}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                      <div className="p-3 bg-slate-950 rounded-lg border border-slate-800/80">
                        <span className="text-[10px] text-slate-500 uppercase block mb-1">
                          Risk Acceptance Justification
                        </span>
                        <p className="text-slate-300 italic">"{approval.risk_acceptance_justification}"</p>
                      </div>

                      <div className="p-3 bg-slate-950 rounded-lg border border-slate-800/80">
                        <span className="text-[10px] text-slate-500 uppercase block mb-1">
                          Human Oversight Controls (HITL)
                        </span>
                        <p className="text-slate-300 italic">"{approval.human_oversight_measures}"</p>
                      </div>
                    </div>

                    {approval.reviewer_notes && (
                      <div className="p-3 bg-slate-950/80 rounded-lg border border-slate-800/80 text-xs">
                        <span className="text-[10px] text-slate-500 uppercase block mb-1">
                          Reviewer Audit Rationale (by User #{approval.reviewed_by_id})
                        </span>
                        <p className="text-slate-200 font-medium">{approval.reviewer_notes}</p>
                      </div>
                    )}

                    {/* Action Bar for Pending Approvals */}
                    {isPending && (
                      <div className="flex items-center justify-between pt-2 border-t border-slate-800">
                        {isRequester ? (
                          <span className="text-[11px] text-amber-400 font-semibold flex items-center gap-1.5">
                            <ShieldAlert size={14} />
                            Segregation of Duties: You requested this release and cannot approve it.
                          </span>
                        ) : (
                          <span className="text-[11px] text-slate-400">
                            Requested by User #{approval.requested_by_id}. Requires independent review.
                          </span>
                        )}

                        {canApprove && (
                          <Button
                            size="sm"
                            variant="primary"
                            disabled={isRequester}
                            onClick={() => setReviewingApproval(approval)}
                            className="text-xs"
                          >
                            Review Deployment Gate
                          </Button>
                        )}
                      </div>
                    )}
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 4: Cross-Module Lineage */}
      {activeTab === 'lineage' && <AIGovernanceLineageCard system={system} />}

      {/* Modal: Edit AI System */}
      <AISystemModal
        isOpen={isEditModalOpen}
        initialData={system}
        onClose={() => setIsEditModalOpen(false)}
        onSubmit={async (data) => {
          await updateSystemMutation.mutateAsync(data as AISystemUpdate);
        }}
        isSubmitting={updateSystemMutation.isPending}
      />

      {/* Modal: Publish Model Card */}
      <AIModelCardModal
        isOpen={isModelCardModalOpen}
        systemId={system.id}
        systemCode={system.system_code}
        onClose={() => setIsModelCardModalOpen(false)}
        onSubmit={async (data) => {
          await createModelCardMutation.mutateAsync(data);
        }}
        isSubmitting={createModelCardMutation.isPending}
      />

      {/* Modal: Request Deployment Approval */}
      <DeploymentApprovalModal
        isOpen={isDeploymentModalOpen}
        system={system}
        onClose={() => setIsDeploymentModalOpen(false)}
        onSubmit={async (data) => {
          await requestDeploymentMutation.mutateAsync(data);
        }}
        isSubmitting={requestDeploymentMutation.isPending}
      />

      {/* Modal: Four-Eyes Review Decision */}
      <DeploymentReviewModal
        isOpen={!!reviewingApproval}
        approval={reviewingApproval}
        systemCode={system.system_code}
        onClose={() => setReviewingApproval(null)}
        onSubmit={async (approvalId, data) => {
          await reviewDeploymentMutation.mutateAsync({ approvalId, data });
        }}
        isSubmitting={reviewDeploymentMutation.isPending}
      />

      {/* Modal: Governed Lifecycle State Machine Transition */}
      <Modal
        isOpen={isLifecycleModalOpen}
        onClose={() => {
          setIsLifecycleModalOpen(false);
          setLifecycleError(null);
        }}
        title={`Transition Lifecycle State: ${system.system_code}`}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            updateLifecycleMutation.mutate({
              lifecycle_state: targetLifecycleState,
              notes: lifecycleNotes.trim() || undefined,
            });
          }}
          className="space-y-4"
        >
          {lifecycleError && (
            <div className="p-3 bg-rose-950/80 border border-rose-800 rounded-md flex items-start gap-2.5 text-xs text-rose-200">
              <AlertTriangle size={16} className="text-rose-400 shrink-0 mt-0.5" />
              <span>{lifecycleError}</span>
            </div>
          )}

          <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-xs space-y-1">
            <span className="text-slate-400">Current State:</span>
            <div className="font-bold text-slate-100 font-mono">
              {system.lifecycle_state.replace(/_/g, ' ')}
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Target Lifecycle State <span className="text-rose-400">*</span>
            </label>
            <select
              value={targetLifecycleState}
              onChange={(e) => setTargetLifecycleState(e.target.value as AILifecycleState)}
              className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-xs text-slate-100 focus:outline-hidden focus:border-indigo-500"
            >
              {legalNextStates.map((st) => (
                <option key={st} value={st}>
                  {st.replace(/_/g, ' ')}
                </option>
              ))}
            </select>
          </div>

          {(targetLifecycleState === 'APPROVED_STAGING' || targetLifecycleState === 'PRODUCTION') && (
            <div className="p-3 bg-indigo-950/50 border border-indigo-800/80 rounded-md text-xs text-indigo-200 flex items-start gap-2">
              <ShieldCheck size={16} className="text-indigo-400 shrink-0 mt-0.5" />
              <span>
                <strong>Prerequisite:</strong> Promoting to {targetLifecycleState} requires an approved Four-Eyes deployment record for environment '{targetLifecycleState === 'PRODUCTION' ? 'PRODUCTION' : 'STAGING'}'.
              </span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Audit Notes &amp; Transition Justification
            </label>
            <textarea
              rows={3}
              value={lifecycleNotes}
              onChange={(e) => setLifecycleNotes(e.target.value)}
              placeholder="Record reason for state transition, validation findings..."
              className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setIsLifecycleModalOpen(false);
                setLifecycleError(null);
              }}
              disabled={updateLifecycleMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              isLoading={updateLifecycleMutation.isPending}
            >
              Confirm State Transition
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
