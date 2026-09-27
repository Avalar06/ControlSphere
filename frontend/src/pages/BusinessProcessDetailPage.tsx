import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../context/AuthContext';
import { resilienceService } from '../lib/resilienceService';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Table, TableBody, TableCell, TableHead, TableHeaderCell, TableRow } from '../components/ui/Table';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { ProcessModal } from '../components/resilience/ProcessModal';
import { BiaModal } from '../components/resilience/BiaModal';
import { BiaApprovalModal } from '../components/resilience/BiaApprovalModal';
import { DependencyModal } from '../components/resilience/DependencyModal';
import { OutageImpactCard } from '../components/resilience/OutageImpactCard';
import { BiaHistoryCard } from '../components/resilience/BiaHistoryCard';
import type {
  BusinessImpactAnalysis,
  CriticalityTier,
  DependencyType,
  ExerciseOutcome,
} from '../types';
import {
  AlertTriangle,
  ArrowLeft,
  Building2,
  CheckCircle2,
  ClipboardCheck,
  Clock,
  Cloud,
  Database,
  Edit2,
  FileCheck2,
  Layers,
  Link2,
  Lock,
  Plus,
  Shield,
  ShieldCheck,
  Trash2,
} from 'lucide-react';

export const BusinessProcessDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const processId = parseInt(id || '0', 10);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { hasRole } = useAuth();

  const canManage = hasRole('ADMIN', 'MANAGER', 'GRC_ANALYST');
  const canApprove = hasRole('ADMIN', 'MANAGER');

  // Modals state
  const [isProcessModalOpen, setIsProcessModalOpen] = useState(false);
  const [isBiaModalOpen, setIsBiaModalOpen] = useState(false);
  const [editingBia, setEditingBia] = useState<BusinessImpactAnalysis | null>(null);
  const [isApprovalModalOpen, setIsApprovalModalOpen] = useState(false);
  const [approvingBia, setApprovingBia] = useState<BusinessImpactAnalysis | null>(null);
  const [isDependencyModalOpen, setIsDependencyModalOpen] = useState(false);

  // Queries
  const {
    data: process,
    isLoading: isProcessLoading,
    isError: isProcessError,
    refetch: refetchProcess,
  } = useQuery({
    queryKey: ['resilience-process', processId],
    queryFn: () => resilienceService.getProcess(processId),
    enabled: processId > 0,
  });

  const { data: bias = [] } = useQuery({
    queryKey: ['resilience-process-bias', processId],
    queryFn: () => resilienceService.listProcessBias(processId),
    enabled: processId > 0,
  });

  const { data: dependencies = [] } = useQuery({
    queryKey: ['resilience-dependencies', processId],
    queryFn: () => resilienceService.listDependencies(processId),
    enabled: processId > 0,
  });

  const { data: depHealth } = useQuery({
    queryKey: ['resilience-dep-health', processId],
    queryFn: () => resilienceService.getDependencyHealth(processId),
    enabled: processId > 0,
  });

  const { data: continuityPlans = [] } = useQuery({
    queryKey: ['resilience-continuity-plans', processId],
    queryFn: () => resilienceService.listContinuityPlans(processId),
    enabled: processId > 0,
  });

  const { data: exercises = [] } = useQuery({
    queryKey: ['resilience-process-exercises', processId],
    queryFn: () => resilienceService.listExercises({ process_id: processId }),
    enabled: processId > 0,
  });

  const removeDepMutation = useMutation({
    mutationFn: (depId: number) => resilienceService.removeDependency(depId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resilience-process', processId] });
      queryClient.invalidateQueries({ queryKey: ['resilience-dependencies', processId] });
      queryClient.invalidateQueries({ queryKey: ['resilience-dep-health', processId] });
    },
  });

  const submitPlanMutation = useMutation({
    mutationFn: (planId: number) => resilienceService.submitContinuityPlan(planId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resilience-continuity-plans', processId] });
      queryClient.invalidateQueries({ queryKey: ['resilience-dep-health', processId] });
    },
  });

  const approvePlanMutation = useMutation({
    mutationFn: (planId: number) => resilienceService.approveContinuityPlan(planId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resilience-continuity-plans', processId] });
      queryClient.invalidateQueries({ queryKey: ['resilience-dep-health', processId] });
      queryClient.invalidateQueries({ queryKey: ['resilience-dashboard'] });
    },
  });

  if (isProcessLoading) {
    return (
      <div className="py-20 flex justify-center">
        <LoadingSpinner text="Loading business process telemetry..." />
      </div>
    );
  }

  if (isProcessError || !process) {
    return (
      <div className="p-8 bg-rose-500/10 border border-rose-500/30 rounded-xl text-center space-y-3">
        <AlertTriangle className="h-10 w-10 text-rose-400 mx-auto" />
        <h2 className="text-base font-bold text-slate-100">Business Process Not Found</h2>
        <p className="text-xs text-slate-400">
          The requested business process does not exist or is not authorized under the current tenant organization.
        </p>
        <Button variant="secondary" onClick={() => navigate('/resilience')} className="text-xs">
          Return to Process Register
        </Button>
      </div>
    );
  }

  const activeBia = process.active_bia;

  const getTierBadge = (tier: CriticalityTier) => {
    switch (tier) {
      case 'TIER_1':
        return <Badge variant="danger">TIER 1 — MISSION CRITICAL</Badge>;
      case 'TIER_2':
        return <Badge variant="warning">TIER 2 — HIGH IMPACT</Badge>;
      case 'TIER_3':
        return <Badge variant="info">TIER 3 — MODERATE</Badge>;
      case 'TIER_4':
        return <Badge variant="default">TIER 4 — LOW IMPACT</Badge>;
      default:
        return <Badge variant="default">{tier}</Badge>;
    }
  };

  const renderDependencyTypeBadge = (type: DependencyType) => {
    switch (type) {
      case 'VENDOR':
        return (
          <div className="flex items-center gap-1.5 text-purple-300 text-xs font-semibold">
            <Building2 size={14} />
            <span>Third-Party Vendor</span>
          </div>
        );
      case 'CONTROL':
        return (
          <div className="flex items-center gap-1.5 text-emerald-300 text-xs font-semibold">
            <Shield size={14} />
            <span>Internal Control</span>
          </div>
        );
      case 'CLOUD_ASSET':
        return (
          <div className="flex items-center gap-1.5 text-cyan-300 text-xs font-semibold">
            <Cloud size={14} />
            <span>Cloud Infrastructure</span>
          </div>
        );
      case 'DATA_ASSET':
        return (
          <div className="flex items-center gap-1.5 text-amber-300 text-xs font-semibold">
            <Database size={14} />
            <span>Governed Data Asset</span>
          </div>
        );
      case 'PROCESS':
        return (
          <div className="flex items-center gap-1.5 text-indigo-300 text-xs font-semibold">
            <Layers size={14} />
            <span>Upstream Process</span>
          </div>
        );
      default:
        return <span className="text-xs text-slate-300">{type}</span>;
    }
  };

  const getOutcomeBadge = (outcome?: ExerciseOutcome | null) => {
    if (!outcome) return <Badge variant="default">PENDING</Badge>;
    switch (outcome) {
      case 'PASS':
        return <Badge variant="success">PASS</Badge>;
      case 'PASS_WITH_MINOR_EXCEPTIONS':
        return <Badge variant="info">PASS (MINOR EXC)</Badge>;
      case 'FAIL_MTD_BREACH':
        return <Badge variant="danger">FAIL — MTD BREACH</Badge>;
      case 'FAIL_RTO_BREACH':
        return <Badge variant="danger">FAIL — RTO BREACH</Badge>;
      case 'FAIL_RPO_BREACH':
        return <Badge variant="warning">FAIL — RPO BREACH</Badge>;
      case 'FAIL_CONTROL_DEFICIENCY':
        return <Badge variant="warning">FAIL — CTRL DEFICIENCY</Badge>;
      default:
        return <Badge variant="default">{outcome}</Badge>;
    }
  };

  return (
    <div className="space-y-6 pb-16">
      {/* Navigation Breadcrumb & Back */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/resilience')}
          className="flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-slate-200 transition-colors"
        >
          <ArrowLeft size={16} />
          <span>Back to Process Register</span>
        </button>

        <div className="flex items-center gap-2">
          {getTierBadge(process.criticality_tier)}
          <span className="text-xs font-mono text-slate-500">ID #{process.id}</span>
        </div>
      </div>

      {/* Process Header & Overview Card */}
      <Card className="border-slate-800 bg-slate-900/90 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold text-slate-100">{process.name}</h1>
            </div>
            <p className="text-xs text-slate-400 mt-1 max-w-3xl">
              {process.description || 'No detailed scope or service boundary description provided.'}
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {canManage && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setIsProcessModalOpen(true)}
                className="text-xs flex items-center gap-1.5"
              >
                <Edit2 size={13} />
                <span>Edit Process</span>
              </Button>
            )}

            {canManage && (
              <Button
                size="sm"
                onClick={() => {
                  setEditingBia(null);
                  setIsBiaModalOpen(true);
                }}
                className="text-xs flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-500 text-white"
              >
                <Plus size={14} />
                <span>Draft New BIA</span>
              </Button>
            )}
          </div>
        </div>

        {/* Process Metadata Details */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
          <div>
            <span className="text-slate-500 block text-[10px] uppercase font-semibold">Process Owner</span>
            <span className="text-slate-200">{process.owner?.full_name || `User #${process.owner_id}`}</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px] uppercase font-semibold">Criticality Tier</span>
            <span className="text-slate-200">{process.criticality_tier}</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px] uppercase font-semibold">Dependency Health</span>
            <span className="text-emerald-400 font-bold">
              {depHealth ? `${depHealth.dependency_health_score}%` : '100%'}
            </span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px] uppercase font-semibold">Unmitigated SPOFs</span>
            <span
              className={
                (depHealth?.unmitigated_spof_count ?? 0) > 0
                  ? 'text-rose-400 font-bold'
                  : 'text-slate-200'
              }
            >
              {depHealth?.unmitigated_spof_count ?? 0}
            </span>
          </div>
        </div>
      </Card>

      {/* Active Baseline Card */}
      {activeBia ? (
        <Card className="border-emerald-950/60 bg-slate-900/90 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2.5">
              <ShieldCheck className="h-5 w-5 text-emerald-400" />
              <div>
                <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
                  Active Approved BIA Baseline (Version {activeBia.version})
                  <Badge variant="success">ACTIVE BASELINE</Badge>
                  <Lock size={13} className="text-slate-400" />
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Governed operational recovery thresholds &amp; financial disruption metrics approved under four-eyes separation.
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3.5">
            <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800">
              <span className="text-[10px] font-semibold text-slate-400 uppercase font-mono">Recovery Time (RTO)</span>
              <div className="text-xl font-bold font-mono text-emerald-400 mt-1">{activeBia.rto_hours}h</div>
              <span className="text-[10px] text-slate-500 mt-1 block">Target recovery window</span>
            </div>

            <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800">
              <span className="text-[10px] font-semibold text-slate-400 uppercase font-mono">Recovery Point (RPO)</span>
              <div className="text-xl font-bold font-mono text-slate-200 mt-1">{activeBia.rpo_hours}h</div>
              <span className="text-[10px] text-slate-500 mt-1 block">Maximum data loss</span>
            </div>

            <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800">
              <span className="text-[10px] font-semibold text-slate-400 uppercase font-mono">Max Downtime (MTD)</span>
              <div className="text-xl font-bold font-mono text-amber-400 mt-1">{activeBia.mtd_hours}h</div>
              <span className="text-[10px] text-slate-500 mt-1 block">Disruption tolerance ceiling</span>
            </div>

            <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800">
              <span className="text-[10px] font-semibold text-slate-400 uppercase font-mono">Hourly Disruption</span>
              <div className="text-xl font-bold font-mono text-indigo-300 mt-1">
                ${activeBia.hourly_downtime_cost.toLocaleString()}
              </div>
              <span className="text-[10px] text-slate-500 mt-1 block">Loss per downtime hour</span>
            </div>

            <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800">
              <span className="text-[10px] font-semibold text-slate-400 uppercase font-mono">Fixed Outage Cost</span>
              <div className="text-xl font-bold font-mono text-slate-200 mt-1">
                ${activeBia.fixed_outage_cost.toLocaleString()}
              </div>
              <span className="text-[10px] text-slate-500 mt-1 block">Initial mobilization loss</span>
            </div>
          </div>

          <div className="p-3 bg-slate-950/40 rounded-lg border border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between text-xs text-slate-400 gap-2">
            <div>
              <span className="font-semibold text-slate-300">Four-Eyes Governance Trail:</span>{' '}
              Drafted by <span className="font-mono text-slate-200">{activeBia.requested_by?.full_name || `User #${activeBia.requested_by_id}`}</span> |{' '}
              Approved by <span className="font-mono text-emerald-400 font-semibold">{activeBia.approved_by?.full_name || `User #${activeBia.approved_by_id}`}</span> on{' '}
              <span className="font-mono text-slate-200">{activeBia.approved_at ? new Date(activeBia.approved_at).toLocaleDateString() : 'N/A'}</span>
            </div>
          </div>
        </Card>
      ) : (
        <Card className="border-amber-900/40 bg-amber-950/10 p-6 text-center space-y-3">
          <Clock className="h-8 w-8 text-amber-400 mx-auto" />
          <h3 className="text-sm font-bold text-slate-100">No Active BIA Baseline Established</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            This business process has no formally approved BIA baseline. Create a draft BIA and submit it for secondary managerial review.
          </p>
          {canManage && (
            <Button
              onClick={() => {
                setEditingBia(null);
                setIsBiaModalOpen(true);
              }}
              className="bg-indigo-600 hover:bg-indigo-500 text-xs"
            >
              <Plus size={14} className="mr-1" /> Draft Initial BIA
            </Button>
          )}
        </Card>
      )}

      {/* Outage Loss Simulation Engine (Rendered when active BIA exists) */}
      {activeBia && <OutageImpactCard bia={activeBia} />}

      {/* Cross-Module Dependencies Section (Extended Batch 5 Lineage) */}
      <Card className="border-slate-800 bg-slate-900/90 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <Link2 className="h-5 w-5 text-indigo-400" />
            <div>
              <h3 className="text-sm font-semibold text-slate-100">
                Upstream Process Dependencies &amp; SPOF Lineage ({dependencies.length})
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Links to Vendors (TPRM), Controls, Cloud Assets (CloudSec), Data Assets (Privacy), and Upstream Processes.
              </p>
            </div>
          </div>

          {canManage && (
            <Button
              size="sm"
              onClick={() => setIsDependencyModalOpen(true)}
              className="text-xs flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-500 text-white"
            >
              <Plus size={14} />
              <span>Link Dependency</span>
            </Button>
          )}
        </div>

        {dependencies.length === 0 ? (
          <div className="p-8 text-center bg-slate-950/60 rounded-xl border border-slate-800">
            <Link2 className="h-8 w-8 text-slate-600 mx-auto mb-2" />
            <p className="text-xs text-slate-400 font-medium">
              No vendor, control, cloud asset, data asset, or process dependencies linked yet.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHead>
                <TableRow>
                  <TableHeaderCell>Priority</TableHeaderCell>
                  <TableHeaderCell>Dependency Type</TableHeaderCell>
                  <TableHeaderCell>Target Reference</TableHeaderCell>
                  <TableHeaderCell>SPOF &amp; Weight</TableHeaderCell>
                  <TableHeaderCell>Context Notes</TableHeaderCell>
                  <TableHeaderCell className="text-right">Actions</TableHeaderCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {dependencies.map((dep) => (
                  <TableRow key={dep.id}>
                    <TableCell className="font-mono text-xs text-slate-300">
                      #{dep.recovery_priority_order ?? 1}
                    </TableCell>
                    <TableCell>{renderDependencyTypeBadge(dep.dependency_type)}</TableCell>

                    <TableCell className="font-mono text-xs text-slate-200">
                      {dep.dependency_type} #{dep.dependency_id}
                    </TableCell>

                    <TableCell className="text-xs font-mono">
                      {dep.is_single_point_of_failure ? (
                        <Badge variant="danger">SPOF (w=1.0)</Badge>
                      ) : (
                        <span className="text-slate-400">w={dep.failure_propagation_weight ?? 1.0}</span>
                      )}
                    </TableCell>

                    <TableCell className="text-xs text-slate-400">
                      {dep.notes || dep.criticality_notes || (
                        <span className="italic text-slate-600">No notes</span>
                      )}
                    </TableCell>

                    <TableCell className="text-right">
                      {canManage && (
                        <Button
                          variant="danger"
                          size="sm"
                          onClick={() => removeDepMutation.mutate(dep.id)}
                          disabled={removeDepMutation.isPending}
                          className="text-xs py-1 px-2"
                        >
                          <Trash2 size={12} />
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </Card>

      {/* Batch 5: Continuity & Recovery Plans Section */}
      <Card className="border-slate-800 bg-slate-900/90 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <FileCheck2 className="h-5 w-5 text-emerald-400" />
            <div>
              <h3 className="text-sm font-semibold text-slate-100">
                Business Continuity &amp; Recovery Plans ({continuityPlans.length})
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Versioned continuity strategies, ordered recovery step durations, four-eyes approval, and SHA-256 tamper-evident sealing.
              </p>
            </div>
          </div>
        </div>

        {continuityPlans.length === 0 ? (
          <div className="p-8 text-center bg-slate-950/60 rounded-xl border border-slate-800">
            <FileCheck2 className="h-8 w-8 text-slate-600 mx-auto mb-2" />
            <p className="text-xs text-slate-400 font-medium">
              No Continuity Plans registered for this business process yet.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHead>
                <TableRow>
                  <TableHeaderCell>Plan Code &amp; Version</TableHeaderCell>
                  <TableHeaderCell>Title &amp; Strategy</TableHeaderCell>
                  <TableHeaderCell>Status</TableHeaderCell>
                  <TableHeaderCell>Est. Recovery / RPO</TableHeaderCell>
                  <TableHeaderCell>SHA-256 Seal</TableHeaderCell>
                  <TableHeaderCell className="text-right">Governance Actions</TableHeaderCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {continuityPlans.map((plan) => (
                  <TableRow key={plan.id}>
                    <TableCell className="font-mono text-xs">
                      <div className="font-bold text-indigo-400">{plan.plan_code}</div>
                      <div className="text-slate-400">v{plan.version_label}</div>
                    </TableCell>
                    <TableCell>
                      <div className="text-xs font-semibold text-slate-200">{plan.title}</div>
                      <div className="text-[11px] font-mono text-slate-400">{plan.strategy_type}</div>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          plan.status === 'APPROVED'
                            ? 'success'
                            : plan.status === 'PENDING_APPROVAL'
                            ? 'warning'
                            : 'default'
                        }
                      >
                        {plan.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-slate-300">
                      RTO: {plan.estimated_recovery_hours}h | RPO: {plan.estimated_rpo_hours}h
                    </TableCell>
                    <TableCell className="font-mono text-[11px] text-slate-400">
                      {plan.plan_hash_sha256 ? `${plan.plan_hash_sha256.slice(0, 12)}…` : '—'}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        {canManage && plan.status === 'DRAFT' && (
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => submitPlanMutation.mutate(plan.id)}
                            disabled={submitPlanMutation.isPending}
                            className="text-xs py-1 px-2.5"
                          >
                            Submit
                          </Button>
                        )}
                        {canApprove && plan.status === 'PENDING_APPROVAL' && (
                          <Button
                            size="sm"
                            onClick={() => approvePlanMutation.mutate(plan.id)}
                            disabled={approvePlanMutation.isPending}
                            className="text-xs py-1 px-2.5 bg-emerald-600 hover:bg-emerald-500 text-white"
                          >
                            <CheckCircle2 size={12} className="mr-1" /> Approve
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </Card>

      {/* Batch 5: Empirical Resilience Exercises Section */}
      <Card className="border-slate-800 bg-slate-900/90 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <ClipboardCheck className="h-5 w-5 text-cyan-400" />
            <div>
              <h3 className="text-sm font-semibold text-slate-100">
                Empirical DR &amp; Continuity Exercises ({exercises.length})
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Measured actual RTO/RPO recovery times vs. BIA snapshot targets and closed-loop CAPA/Risk escalations.
              </p>
            </div>
          </div>
        </div>

        {exercises.length === 0 ? (
          <div className="p-8 text-center bg-slate-950/60 rounded-xl border border-slate-800">
            <ClipboardCheck className="h-8 w-8 text-slate-600 mx-auto mb-2" />
            <p className="text-xs text-slate-400 font-medium">
              No resilience or failover exercises executed for this business process yet.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHead>
                <TableRow>
                  <TableHeaderCell>Exercise Code</TableHeaderCell>
                  <TableHeaderCell>Type &amp; Status</TableHeaderCell>
                  <TableHeaderCell>Target vs Actual RTO</TableHeaderCell>
                  <TableHeaderCell>Target vs Actual RPO</TableHeaderCell>
                  <TableHeaderCell>Outcome</TableHeaderCell>
                  <TableHeaderCell>CAPA / Risk Escalation</TableHeaderCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {exercises.map((ex) => (
                  <TableRow key={ex.id}>
                    <TableCell>
                      <div className="font-mono text-xs font-bold text-indigo-400">{ex.exercise_code}</div>
                      <div className="text-xs text-slate-200">{ex.title}</div>
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      <div className="text-slate-300">{ex.exercise_type}</div>
                      <div className="text-[11px] text-slate-500">{ex.status}</div>
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      T: {ex.target_rto_hours_snapshot}h /{' '}
                      {ex.actual_rto_hours !== null ? (
                        <span className={ex.rto_breached ? 'text-rose-400 font-bold' : 'text-emerald-400 font-bold'}>
                          A: {ex.actual_rto_hours}h
                        </span>
                      ) : (
                        '—'
                      )}
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      T: {ex.target_rpo_hours_snapshot}h /{' '}
                      {ex.actual_rpo_hours !== null ? (
                        <span className={ex.rpo_breached ? 'text-rose-400 font-bold' : 'text-emerald-400 font-bold'}>
                          A: {ex.actual_rpo_hours}h
                        </span>
                      ) : (
                        '—'
                      )}
                    </TableCell>
                    <TableCell>{getOutcomeBadge(ex.outcome)}</TableCell>
                    <TableCell className="font-mono text-xs text-slate-400">
                      {ex.finding_id || ex.remediation_plan_id || ex.risk_id ? (
                        <div className="flex flex-wrap gap-1">
                          {ex.finding_id && <Badge variant="warning">Finding #{ex.finding_id}</Badge>}
                          {ex.remediation_plan_id && <Badge variant="info">CAPA #{ex.remediation_plan_id}</Badge>}
                          {ex.risk_id && <Badge variant="danger">Risk #{ex.risk_id}</Badge>}
                        </div>
                      ) : (
                        '—'
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </Card>

      {/* BIA Version History & Audit Trail */}
      <BiaHistoryCard
        processId={processId}
        bias={bias}
        onApproveClick={(b) => {
          setApprovingBia(b);
          setIsApprovalModalOpen(true);
        }}
        onEditClick={(b) => {
          setEditingBia(b);
          setIsBiaModalOpen(true);
        }}
        canManage={canManage}
        canApprove={canApprove}
      />

      {/* Modals */}
      <ProcessModal
        isOpen={isProcessModalOpen}
        onClose={() => setIsProcessModalOpen(false)}
        onSuccess={() => refetchProcess()}
        initialProcess={process}
      />

      <BiaModal
        isOpen={isBiaModalOpen}
        onClose={() => {
          setIsBiaModalOpen(false);
          setEditingBia(null);
        }}
        onSuccess={() => {
          refetchProcess();
          queryClient.invalidateQueries({ queryKey: ['resilience-process-bias', processId] });
        }}
        processId={processId}
        initialBia={editingBia}
      />

      {approvingBia && (
        <BiaApprovalModal
          isOpen={isApprovalModalOpen}
          onClose={() => {
            setIsApprovalModalOpen(false);
            setApprovingBia(null);
          }}
          onSuccess={() => {
            refetchProcess();
            queryClient.invalidateQueries({ queryKey: ['resilience-process-bias', processId] });
          }}
          bia={approvingBia}
        />
      )}

      <DependencyModal
        isOpen={isDependencyModalOpen}
        onClose={() => setIsDependencyModalOpen(false)}
        onSuccess={() => {
          refetchProcess();
          queryClient.invalidateQueries({ queryKey: ['resilience-dependencies', processId] });
          queryClient.invalidateQueries({ queryKey: ['resilience-dep-health', processId] });
        }}
        processId={processId}
      />
    </div>
  );
};
