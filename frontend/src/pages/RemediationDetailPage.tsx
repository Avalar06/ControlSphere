import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Activity,
  AlertCircle,
  AlertOctagon,
  AlertTriangle,
  ArrowLeft,
  Calendar,
  CheckCircle2,
  FileCheck2,
  Link as LinkIcon,
  Lock,
  Plus,
  RefreshCw,
  ShieldCheck,
  Trash2,
  UserCheck,
  UserX,
  XCircle,
  Zap,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { remediationService } from '../lib/remediationService';
import { api } from '../lib/api';
import type {
  EvidenceItem,
  RemediationEvidenceLinkCreate,
  RemediationPlanDetailRead,
  RemediationReTestCreate,
  RemediationStatus,
  RemediationTaskCreate,
  ReTestResult,
  User,
} from '../types';

export const RemediationDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const planId = Number(id);
  const navigate = useNavigate();
  const { user: currentUser, hasRole } = useAuth();

  const [loading, setLoading] = useState(true);
  const [plan, setPlan] = useState<RemediationPlanDetailRead | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [availableEvidence, setAvailableEvidence] = useState<EvidenceItem[]>([]);
  const [activeTab, setActiveTab] = useState<'overview' | 'tasks' | 'evidence' | 'retests' | 'governance'>('overview');

  // Governance action states & modals
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Modal controls
  const [showApproveModal, setShowApproveModal] = useState(false);
  const [approveNotes, setApproveNotes] = useState('');
  const [approveCustomDeadline, setApproveCustomDeadline] = useState('');

  const [showCancelModal, setShowCancelModal] = useState(false);
  const [cancelNotes, setCancelNotes] = useState('');

  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectNotes, setRejectNotes] = useState('');

  const [showVerifyModal, setShowVerifyModal] = useState(false);
  const [verifyNotes, setVerifyNotes] = useState('');

  const [showAddTaskModal, setShowAddTaskModal] = useState(false);
  const [taskForm, setTaskForm] = useState<RemediationTaskCreate>({
    task_seq: 1,
    title: '',
    description: '',
    assignee_id: undefined,
    due_date: undefined,
  });

  const [showLinkEvidenceModal, setShowLinkEvidenceModal] = useState(false);
  const [selectedTaskIdForEvidence, setSelectedTaskIdForEvidence] = useState<number | null>(null);
  const [evidenceLinkForm, setEvidenceLinkForm] = useState<RemediationEvidenceLinkCreate>({
    evidence_id: 0,
    notes: '',
  });

  const [showRetestModal, setShowRetestModal] = useState(false);
  const [retestForm, setRetestForm] = useState<RemediationReTestCreate>({
    test_executed_at: new Date().toISOString().slice(0, 16),
    test_result: 'PASS',
    metric_observed_value: undefined,
    evidence_id: undefined,
    validation_narrative: '',
  });

  const fetchPlanData = async () => {
    if (!planId) return;
    setLoading(true);
    try {
      const [planData, usersData, evidenceData] = await Promise.all([
        remediationService.getPlan(planId),
        api.get<User[]>('/users').then((r) => r.data).catch(() => []),
        api.get<EvidenceItem[]>('/evidence').then((r) => r.data).catch(() => []),
      ]);
      setPlan(planData);
      setUsers(usersData);
      setAvailableEvidence(evidenceData.filter((e) => e.status === 'ACCEPTED'));

      // Set next task sequence
      if (planData.tasks && planData.tasks.length > 0) {
        const maxSeq = Math.max(...planData.tasks.map((t) => t.task_seq));
        setTaskForm((prev) => ({ ...prev, task_seq: maxSeq + 1 }));
      }
    } catch (err: any) {
      console.error('Failed to load remediation plan', err);
      setActionError(err.response?.data?.detail || 'Failed to load remediation plan.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPlanData();
  }, [planId]);

  if (loading || !plan) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-3">
        <RefreshCw className="w-8 h-8 animate-spin text-indigo-400" />
        <p className="text-sm text-slate-400 font-mono">Loading ROC-V Remediation Plan #{planId}...</p>
      </div>
    );
  }

  // Permission checks
  const isAdminOrManager = hasRole('ADMIN', 'MANAGER');
  const isAuditor = hasRole('AUDITOR', 'ADMIN', 'MANAGER');
  const canExecute = hasRole('ADMIN', 'MANAGER', 'GRC_ANALYST', 'SECURITY_ANALYST');
  const canManage = hasRole('ADMIN', 'MANAGER', 'GRC_ANALYST', 'SECURITY_ANALYST');

  // Four-Eyes Separation Evaluation
  const isPlanOwner = currentUser?.id === plan.plan_owner_id;
  const isTaskAssignee = plan.tasks?.some((t) => t.assignee_id === currentUser?.id);
  const hasPassRetest = plan.retest_records?.some((r) => r.test_result === 'PASS');
  const allTasksCompleted =
    plan.tasks &&
    plan.tasks.length > 0 &&
    plan.tasks.every((t) => t.status === 'COMPLETED' || t.status === 'CANCELLED');

  // Lifecycle Actions
  const handleApprove = async () => {
    setActionLoading(true);
    setActionError(null);
    try {
      await remediationService.approvePlan(plan.id, {
        notes: approveNotes.trim() || undefined,
        target_completion_at: approveCustomDeadline
          ? new Date(approveCustomDeadline).toISOString()
          : undefined,
      });
      setShowApproveModal(false);
      fetchPlanData();
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Approval failed.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleStart = async () => {
    setActionLoading(true);
    setActionError(null);
    try {
      await remediationService.startPlan(plan.id);
      fetchPlanData();
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Failed to start plan execution.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleSubmitValidation = async () => {
    setActionLoading(true);
    setActionError(null);
    try {
      await remediationService.submitForValidation(plan.id);
      fetchPlanData();
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Validation submission failed.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRejectValidation = async () => {
    if (rejectNotes.trim().length < 15) {
      setActionError('Mandatory rejection notes must be at least 15 characters.');
      return;
    }
    setActionLoading(true);
    setActionError(null);
    try {
      await remediationService.rejectValidation(plan.id, { rejection_notes: rejectNotes.trim() });
      setShowRejectModal(false);
      fetchPlanData();
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Rejection failed.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleVerifyClose = async () => {
    if (verifyNotes.trim().length < 15) {
      setActionError('Verification notes must be at least 15 characters.');
      return;
    }
    setActionLoading(true);
    setActionError(null);
    try {
      await remediationService.verifyClose(plan.id, { verification_notes: verifyNotes.trim() });
      setShowVerifyModal(false);
      fetchPlanData();
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Verification closure failed.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancelPlan = async () => {
    if (!cancelNotes.trim()) {
      setActionError('Cancellation notes are mandatory.');
      return;
    }
    setActionLoading(true);
    setActionError(null);
    try {
      await remediationService.cancelPlan(plan.id, { cancellation_notes: cancelNotes.trim() });
      setShowCancelModal(false);
      fetchPlanData();
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Cancellation failed.');
    } finally {
      setActionLoading(false);
    }
  };

  // Task Actions
  const handleAddTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!taskForm.title.trim() || !taskForm.description.trim()) {
      setActionError('Task title and description are required.');
      return;
    }
    setActionLoading(true);
    setActionError(null);
    try {
      await remediationService.createTask(plan.id, {
        task_seq: Number(taskForm.task_seq),
        title: taskForm.title.trim(),
        description: taskForm.description.trim(),
        assignee_id: taskForm.assignee_id ? Number(taskForm.assignee_id) : undefined,
        due_date: taskForm.due_date ? new Date(taskForm.due_date).toISOString() : undefined,
      });
      setShowAddTaskModal(false);
      setTaskForm({
        task_seq: plan.tasks.length + 2,
        title: '',
        description: '',
        assignee_id: undefined,
        due_date: undefined,
      });
      fetchPlanData();
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Failed to add task.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleStartTask = async (taskId: number) => {
    setActionLoading(true);
    try {
      await remediationService.startTask(taskId);
      fetchPlanData();
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Failed to start task.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCompleteTask = async (taskId: number) => {
    setActionLoading(true);
    try {
      await remediationService.completeTask(taskId);
      fetchPlanData();
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Failed to complete task.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancelTask = async (taskId: number) => {
    setActionLoading(true);
    try {
      await remediationService.cancelTask(taskId);
      fetchPlanData();
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Failed to cancel task.');
    } finally {
      setActionLoading(false);
    }
  };

  // Evidence Link Actions
  const handleLinkEvidence = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTaskIdForEvidence || !evidenceLinkForm.evidence_id) {
      setActionError('Please select a valid task and evidence item.');
      return;
    }
    setActionLoading(true);
    setActionError(null);
    try {
      await remediationService.linkEvidence(selectedTaskIdForEvidence, {
        evidence_id: Number(evidenceLinkForm.evidence_id),
        notes: evidenceLinkForm.notes?.trim() || undefined,
      });
      setShowLinkEvidenceModal(false);
      setEvidenceLinkForm({ evidence_id: 0, notes: '' });
      fetchPlanData();
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Failed to link evidence.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleUnlinkEvidence = async (taskId: number, linkId: number) => {
    if (!window.confirm('Are you sure you want to unlink this evidence item?')) return;
    setActionLoading(true);
    try {
      await remediationService.unlinkEvidence(taskId, linkId);
      fetchPlanData();
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Failed to unlink evidence.');
    } finally {
      setActionLoading(false);
    }
  };

  // Re-Test Actions
  const handleRecordRetest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!retestForm.validation_narrative.trim() || retestForm.validation_narrative.trim().length < 10) {
      setActionError('Validation narrative must be at least 10 characters.');
      return;
    }
    if (retestForm.test_result === 'PASS' && !retestForm.evidence_id) {
      setActionError('Empirical PASS re-test strictly requires selecting an accepted evidence item.');
      return;
    }
    setActionLoading(true);
    setActionError(null);
    try {
      await remediationService.recordRetest(plan.id, {
        test_executed_at: new Date(retestForm.test_executed_at).toISOString(),
        test_result: retestForm.test_result,
        metric_observed_value: retestForm.metric_observed_value
          ? Number(retestForm.metric_observed_value)
          : undefined,
        evidence_id: retestForm.evidence_id ? Number(retestForm.evidence_id) : undefined,
        validation_narrative: retestForm.validation_narrative.trim(),
      });
      setShowRetestModal(false);
      setRetestForm({
        test_executed_at: new Date().toISOString().slice(0, 16),
        test_result: 'PASS',
        metric_observed_value: undefined,
        evidence_id: undefined,
        validation_narrative: '',
      });
      fetchPlanData();
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Failed to record re-test.');
    } finally {
      setActionLoading(false);
    }
  };

  const getUserName = (userId?: number) => {
    if (!userId) return 'Unassigned';
    const u = users.find((x) => x.id === userId);
    return u ? u.full_name : `User #${userId}`;
  };

  // Stepper Visualizer
  const lifecycleSteps: RemediationStatus[] = [
    'DRAFT',
    'APPROVED',
    'IN_EXECUTION',
    'PENDING_VALIDATION',
    'VERIFIED_CLOSED',
  ];

  const getStepIndex = (st: RemediationStatus) => {
    if (st === 'CANCELLED') return -1;
    return lifecycleSteps.indexOf(st);
  };

  const currentStepIdx = getStepIndex(plan.status);

  return (
    <div className="space-y-6 pb-16">
      {/* Top Breadcrumb & Return */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/remediations')}
          className="flex items-center gap-2 text-xs text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Remediation Portfolio
        </button>

        <div className="flex items-center gap-2">
          {plan.is_immutable && (
            <span className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono bg-emerald-950/80 text-emerald-300 border border-emerald-800 rounded-lg">
              <Lock className="w-3.5 h-3.5 text-emerald-400" />
              IMMUTABLE RECORD
            </span>
          )}
          <span className="text-xs text-slate-500 font-mono">
            UPDATED: {new Date(plan.updated_at).toLocaleString()}
          </span>
        </div>
      </div>

      {/* Global Error Banner */}
      {actionError && (
        <div className="p-4 bg-red-950/60 border border-red-800 rounded-xl text-xs text-red-300 flex items-start gap-3 shadow-lg">
          <AlertOctagon className="w-5 h-5 mt-0.5 shrink-0 text-red-400" />
          <div className="space-y-1">
            <span className="font-semibold text-red-200">Governance Error</span>
            <p>{actionError}</p>
          </div>
          <button
            onClick={() => setActionError(null)}
            className="ml-auto text-red-400 hover:text-white text-base font-mono"
          >
            ✕
          </button>
        </div>
      )}

      {/* Header Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2.5">
              <span className="px-2.5 py-0.5 font-mono text-sm font-bold bg-indigo-950 text-indigo-300 border border-indigo-800 rounded-md">
                {plan.plan_code}
              </span>
              <span
                className={`px-2.5 py-0.5 text-xs font-medium border rounded-full ${
                  plan.status === 'VERIFIED_CLOSED'
                    ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                    : plan.status === 'PENDING_VALIDATION'
                    ? 'bg-amber-950 text-amber-300 border-amber-800'
                    : plan.status === 'IN_EXECUTION'
                    ? 'bg-indigo-950 text-indigo-300 border-indigo-800 animate-pulse'
                    : plan.status === 'CANCELLED'
                    ? 'bg-rose-950 text-rose-300 border-rose-800'
                    : 'bg-slate-800 text-slate-300 border-slate-700'
                }`}
              >
                {plan.status.replace('_', ' ')}
              </span>
              <span
                className={`px-2 py-0.5 text-xs border rounded ${
                  plan.severity === 'CRITICAL'
                    ? 'bg-red-950/80 text-red-300 border-red-800'
                    : plan.severity === 'HIGH'
                    ? 'bg-orange-950/80 text-orange-300 border-orange-800'
                    : plan.severity === 'MEDIUM'
                    ? 'bg-amber-950/80 text-amber-300 border-amber-800'
                    : 'bg-blue-950/80 text-blue-300 border-blue-800'
                }`}
              >
                {plan.severity}
              </span>
              <span className="px-2 py-0.5 text-xs font-mono bg-purple-950/60 text-purple-300 border border-purple-800/60 rounded">
                SOURCE: {plan.source_type}
              </span>
            </div>

            <h1 className="text-xl md:text-2xl font-bold text-white tracking-tight">{plan.title}</h1>
            <p className="text-xs text-slate-400 max-w-4xl">{plan.problem_statement}</p>
          </div>

          {/* Governance Action Bar */}
          <div className="flex flex-wrap items-center gap-2 pt-2 lg:pt-0">
            {/* DRAFT Actions */}
            {plan.status === 'DRAFT' && (
              <>
                {isAdminOrManager && (
                  <button
                    onClick={() => {
                      setActionError(null);
                      setShowApproveModal(true);
                    }}
                    disabled={actionLoading || plan.tasks.length === 0}
                    className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg shadow transition-colors disabled:opacity-50"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    Approve Plan
                  </button>
                )}
                {canManage && (
                  <button
                    onClick={() => {
                      setActionError(null);
                      setShowCancelModal(true);
                    }}
                    disabled={actionLoading}
                    className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-rose-300 bg-rose-950/40 hover:bg-rose-900/60 border border-rose-800/60 rounded-lg transition-colors"
                  >
                    <XCircle className="w-4 h-4" />
                    Cancel Plan
                  </button>
                )}
              </>
            )}

            {/* APPROVED Actions */}
            {plan.status === 'APPROVED' && (
              <>
                {canExecute && (
                  <button
                    onClick={handleStart}
                    disabled={actionLoading}
                    className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg shadow transition-colors"
                  >
                    <Zap className="w-4 h-4" />
                    Start Execution
                  </button>
                )}
                {canManage && (
                  <button
                    onClick={() => {
                      setActionError(null);
                      setShowCancelModal(true);
                    }}
                    disabled={actionLoading}
                    className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-rose-300 bg-rose-950/40 hover:bg-rose-900/60 border border-rose-800/60 rounded-lg transition-colors"
                  >
                    <XCircle className="w-4 h-4" />
                    Cancel Plan
                  </button>
                )}
              </>
            )}

            {/* IN_EXECUTION Actions */}
            {plan.status === 'IN_EXECUTION' && (
              <>
                {canExecute && (
                  <button
                    onClick={handleSubmitValidation}
                    disabled={actionLoading || !allTasksCompleted}
                    className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-amber-600 hover:bg-amber-500 rounded-lg shadow transition-colors disabled:opacity-50"
                  >
                    <FileCheck2 className="w-4 h-4" />
                    Submit for Validation
                  </button>
                )}
              </>
            )}

            {/* PENDING_VALIDATION Actions */}
            {plan.status === 'PENDING_VALIDATION' && (
              <>
                {isAuditor && (
                  <>
                    <button
                      onClick={() => {
                        setActionError(null);
                        setShowRetestModal(true);
                      }}
                      disabled={actionLoading}
                      className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium text-indigo-300 bg-indigo-950 hover:bg-indigo-900 border border-indigo-800 rounded-lg transition-colors"
                    >
                      <Activity className="w-4 h-4" />
                      Log Re-Test
                    </button>

                    <button
                      onClick={() => {
                        setActionError(null);
                        setShowRejectModal(true);
                      }}
                      disabled={actionLoading}
                      className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-amber-300 bg-amber-950/60 hover:bg-amber-900/60 border border-amber-800 rounded-lg transition-colors"
                    >
                      <AlertTriangle className="w-4 h-4" />
                      Reject (Rework)
                    </button>

                    <button
                      onClick={() => {
                        setActionError(null);
                        setShowVerifyModal(true);
                      }}
                      disabled={actionLoading || !hasPassRetest}
                      className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg shadow-lg shadow-emerald-900/30 transition-colors disabled:opacity-50"
                    >
                      <ShieldCheck className="w-4 h-4" />
                      Verify & Close Plan
                    </button>
                  </>
                )}
              </>
            )}
          </div>
        </div>

        {/* Telemetry Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 pt-3 border-t border-slate-800/80 text-xs">
          <div>
            <span className="text-[10px] text-slate-500 uppercase font-mono">Plan Owner</span>
            <div className="text-white font-medium mt-0.5 flex items-center gap-1.5">
              <UserCheck className="w-3.5 h-3.5 text-indigo-400" />
              {getUserName(plan.plan_owner_id)}
            </div>
          </div>

          <div>
            <span className="text-[10px] text-slate-500 uppercase font-mono">Target Deadline</span>
            <div className="text-white font-medium mt-0.5 flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-blue-400" />
              {plan.target_completion_at
                ? new Date(plan.target_completion_at).toLocaleDateString()
                : 'Not Set'}
            </div>
          </div>

          <div>
            <span className="text-[10px] text-slate-500 uppercase font-mono">SLA Telemetry</span>
            <div className="text-white font-medium mt-0.5">
              <span
                className={`px-2 py-0.5 rounded text-[10px] font-mono border ${
                  plan.sla_status === 'BREACHED'
                    ? 'bg-rose-950 text-rose-200 border-rose-700'
                    : plan.sla_status === 'AT_RISK'
                    ? 'bg-amber-950 text-amber-200 border-amber-700'
                    : 'bg-emerald-950 text-emerald-200 border-emerald-800'
                }`}
              >
                {plan.sla_status ? plan.sla_status.replace('_', ' ') : 'NOT STARTED'}
              </span>
            </div>
          </div>

          <div>
            <span className="text-[10px] text-slate-500 uppercase font-mono">Effectiveness Index</span>
            <div className="text-white font-mono font-bold mt-0.5 flex items-center gap-1">
              {plan.rei_score !== undefined && plan.rei_score !== null ? (
                <span className="text-emerald-400">{plan.rei_score.toFixed(1)} / 100</span>
              ) : (
                <span className="text-slate-500">Calculated on Close</span>
              )}
            </div>
          </div>

          <div>
            <span className="text-[10px] text-slate-500 uppercase font-mono">Time to Remediate</span>
            <div className="text-white font-mono font-bold mt-0.5">
              {plan.ttr_hours !== undefined && plan.ttr_hours !== null ? (
                <span className="text-cyan-400">{plan.ttr_hours} Hours</span>
              ) : (
                <span className="text-slate-500">Available on Close</span>
              )}
            </div>
          </div>

          <div>
            <span className="text-[10px] text-slate-500 uppercase font-mono">Validation Attempts</span>
            <div className="text-white font-mono font-bold mt-0.5">
              {plan.validation_attempts_count} Attempt(s)
            </div>
          </div>
        </div>
      </div>

      {/* Interactive Lifecycle Flow Stepper */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
        <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-3">
          ROC-V Governed Lifecycle Progression
        </span>
        <div className="grid grid-cols-5 gap-2">
          {lifecycleSteps.map((st, idx) => {
            const isCurrent = plan.status === st;
            const isPast = currentStepIdx > idx && currentStepIdx !== -1;
            return (
              <div
                key={st}
                className={`p-3 rounded-lg border text-center transition-all ${
                  isCurrent
                    ? 'bg-indigo-950/80 border-indigo-500 shadow-md shadow-indigo-900/30'
                    : isPast
                    ? 'bg-slate-950/80 border-emerald-800/60 text-slate-400'
                    : 'bg-slate-950/40 border-slate-800/60 text-slate-600'
                }`}
              >
                <div className="text-[10px] font-mono text-slate-500">Step 0{idx + 1}</div>
                <div
                  className={`text-xs font-bold mt-0.5 ${
                    isCurrent ? 'text-indigo-200' : isPast ? 'text-emerald-300' : 'text-slate-500'
                  }`}
                >
                  {st.replace('_', ' ')}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Tabs Header */}
      <div className="flex border-b border-slate-800 gap-2">
        <button
          onClick={() => setActiveTab('overview')}
          className={`px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === 'overview'
              ? 'text-indigo-400 border-indigo-500'
              : 'text-slate-400 border-transparent hover:text-slate-200'
          }`}
        >
          Overview & Telemetry
        </button>

        <button
          onClick={() => setActiveTab('tasks')}
          className={`px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors flex items-center gap-1.5 ${
            activeTab === 'tasks'
              ? 'text-indigo-400 border-indigo-500'
              : 'text-slate-400 border-transparent hover:text-slate-200'
          }`}
        >
          Remediation Tasks ({plan.tasks?.length ?? 0})
        </button>

        <button
          onClick={() => setActiveTab('evidence')}
          className={`px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors flex items-center gap-1.5 ${
            activeTab === 'evidence'
              ? 'text-indigo-400 border-indigo-500'
              : 'text-slate-400 border-transparent hover:text-slate-200'
          }`}
        >
          Evidence Bindings
        </button>

        <button
          onClick={() => setActiveTab('retests')}
          className={`px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors flex items-center gap-1.5 ${
            activeTab === 'retests'
              ? 'text-indigo-400 border-indigo-500'
              : 'text-slate-400 border-transparent hover:text-slate-200'
          }`}
        >
          Independent Re-Tests ({plan.retest_records?.length ?? 0})
        </button>

        <button
          onClick={() => setActiveTab('governance')}
          className={`px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === 'governance'
              ? 'text-indigo-400 border-indigo-500'
              : 'text-slate-400 border-transparent hover:text-slate-200'
          }`}
        >
          Governance & Traceability
        </button>
      </div>

      {/* Tab 1: Overview & Telemetry */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            {/* Problem Statement & Root Cause */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
              <h3 className="text-sm font-semibold text-white">Root Cause & Problem Statement</h3>
              <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg text-xs space-y-2">
                <div>
                  <span className="text-slate-500 font-mono uppercase text-[10px]">Classification:</span>
                  <span className="text-indigo-300 font-medium ml-2">{plan.root_cause_classification}</span>
                </div>
                <p className="text-slate-300 leading-relaxed">{plan.problem_statement}</p>
              </div>
            </div>

            {/* Validation Readiness Checklist */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
              <h3 className="text-sm font-semibold text-white">Validation & Closure Readiness Checklist</h3>
              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between p-2.5 bg-slate-950 border border-slate-800 rounded-lg">
                  <div className="flex items-center gap-2">
                    {allTasksCompleted ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    ) : (
                      <AlertCircle className="w-4 h-4 text-slate-500" />
                    )}
                    <span className="text-slate-200">100% Active Remediation Tasks Completed</span>
                  </div>
                  <span className="font-mono text-[11px] text-slate-400">
                    {plan.tasks?.filter((t) => t.status === 'COMPLETED').length} / {plan.tasks?.length} Tasks
                  </span>
                </div>

                <div className="flex items-center justify-between p-2.5 bg-slate-950 border border-slate-800 rounded-lg">
                  <div className="flex items-center gap-2">
                    {hasPassRetest ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    ) : (
                      <AlertCircle className="w-4 h-4 text-amber-500" />
                    )}
                    <span className="text-slate-200">At Least 1 Empirical 'PASS' Re-Test Recorded</span>
                  </div>
                  <span className="font-mono text-[11px] text-slate-400">
                    {plan.retest_records?.filter((r) => r.test_result === 'PASS').length} Pass Record(s)
                  </span>
                </div>

                <div className="flex items-center justify-between p-2.5 bg-slate-950 border border-slate-800 rounded-lg">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-indigo-400" />
                    <span className="text-slate-200">Four-Eyes Separation of Duties Enforced</span>
                  </div>
                  <span className="font-mono text-[10px] text-indigo-300">
                    Verifier ≠ Owner & Verifier ≠ Assignees
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Telemetry & Upstream Source Card */}
          <div className="space-y-6">
            {/* Authoritative Source Card */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                Upstream Source Traceability
              </span>
              <div className="p-3.5 bg-slate-950 border border-slate-800 rounded-lg text-xs space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-white">{plan.source_type}</span>
                  <span className="px-2 py-0.5 text-[10px] font-mono bg-indigo-950 text-indigo-300 border border-indigo-800 rounded">
                    ID #{plan.finding_id || plan.compliance_drift_alert_id || plan.security_incident_id || plan.vendor_assessment_id || plan.audit_id}
                  </span>
                </div>

                {plan.finding && (
                  <div className="text-slate-400 text-[11px] pt-1">
                    Finding: <span className="text-slate-200">{plan.finding.title}</span> (Severity: {plan.finding.severity}, Status: {plan.finding.status})
                  </div>
                )}
                {plan.compliance_drift_alert && (
                  <div className="text-slate-400 text-[11px] pt-1">
                    CCM Drift: <span className="text-slate-200">{plan.compliance_drift_alert.title}</span> ({plan.compliance_drift_alert.status})
                  </div>
                )}
                {plan.security_incident && (
                  <div className="text-slate-400 text-[11px] pt-1">
                    Security Incident: <span className="text-slate-200">{plan.security_incident.title}</span> ({plan.security_incident.incident_code})
                  </div>
                )}

                <div className="pt-2 border-t border-slate-800/80 text-[11px] text-slate-500">
                  {plan.status === 'VERIFIED_CLOSED' ? (
                    <span className="text-emerald-400 flex items-center gap-1 font-mono">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Upstream resolution completed atomically.
                    </span>
                  ) : (
                    <span>Will trigger auto-resolution upon verified closure.</span>
                  )}
                </div>
              </div>
            </div>

            {/* SLA Telemetry Breakdown */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-2 text-xs">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                SLA Engine Rules
              </span>
              <ul className="space-y-1 text-slate-400 text-[11px] list-disc list-inside">
                <li>CRITICAL: 7 Days (168h)</li>
                <li>HIGH: 30 Days (720h)</li>
                <li>MEDIUM: 60 Days (1,440h)</li>
                <li>LOW: 90 Days (2,160h)</li>
                <li>AT_RISK triggers when ≤ 20% duration remains</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Tasks */}
      {activeTab === 'tasks' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">Atomic Remediation Tasks</h3>
            {!plan.is_immutable && plan.status !== 'CANCELLED' && canManage && (
              <button
                onClick={() => {
                  setActionError(null);
                  setShowAddTaskModal(true);
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors"
              >
                <Plus className="w-3.5 h-3.5" />
                Add Task
              </button>
            )}
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-950/80 border-b border-slate-800 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  <th className="py-3 px-4">Seq</th>
                  <th className="py-3 px-4">Title & Description</th>
                  <th className="py-3 px-4">Assignee</th>
                  <th className="py-3 px-4">Due Date</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Completed At</th>
                  <th className="py-3 px-4">Evidence</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {plan.tasks?.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-slate-500">
                      No tasks created yet. Click "Add Task" to define remediation steps.
                    </td>
                  </tr>
                ) : (
                  plan.tasks?.map((task) => (
                    <tr key={task.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-3 px-4 font-mono font-bold text-indigo-300">#{task.task_seq}</td>
                      <td className="py-3 px-4 max-w-sm">
                        <div className="font-semibold text-white">{task.title}</div>
                        <div className="text-[11px] text-slate-400">{task.description}</div>
                      </td>
                      <td className="py-3 px-4 text-slate-300">{getUserName(task.assignee_id)}</td>
                      <td className="py-3 px-4 text-slate-400 font-mono text-[11px]">
                        {task.due_date ? new Date(task.due_date).toLocaleDateString() : '—'}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2 py-0.5 text-[10px] font-medium border rounded-full ${
                            task.status === 'COMPLETED'
                              ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                              : task.status === 'IN_PROGRESS'
                              ? 'bg-indigo-950 text-indigo-300 border-indigo-800'
                              : task.status === 'CANCELLED'
                              ? 'bg-rose-950 text-rose-300 border-rose-800'
                              : 'bg-slate-800 text-slate-400 border-slate-700'
                          }`}
                        >
                          {task.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-400 font-mono text-[11px]">
                        {task.completed_at ? new Date(task.completed_at).toLocaleString() : '—'}
                      </td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 text-[10px] font-mono bg-slate-950 text-slate-300 border border-slate-800 rounded">
                          {task.evidence_links?.length ?? 0} linked
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        {!plan.is_immutable && plan.status !== 'CANCELLED' && (
                          <div className="flex items-center justify-end gap-1.5">
                            {task.status === 'PENDING' && canExecute && (
                              <button
                                onClick={() => handleStartTask(task.id)}
                                className="px-2 py-1 text-[10px] bg-slate-800 hover:bg-slate-700 text-slate-200 rounded"
                              >
                                Start
                              </button>
                            )}
                            {task.status === 'IN_PROGRESS' && canExecute && (
                              <button
                                onClick={() => handleCompleteTask(task.id)}
                                className="px-2 py-1 text-[10px] bg-emerald-950 hover:bg-emerald-900 text-emerald-300 border border-emerald-800 rounded"
                              >
                                Complete
                              </button>
                            )}
                            {canExecute && (
                              <button
                                onClick={() => {
                                  setSelectedTaskIdForEvidence(task.id);
                                  setShowLinkEvidenceModal(true);
                                }}
                                className="p-1 bg-indigo-950 hover:bg-indigo-900 text-indigo-300 border border-indigo-800 rounded"
                                title="Link Evidence"
                              >
                                <LinkIcon className="w-3.5 h-3.5" />
                              </button>
                            )}
                            {task.status !== 'CANCELLED' && task.status !== 'COMPLETED' && canManage && (
                              <button
                                onClick={() => handleCancelTask(task.id)}
                                className="p-1 bg-rose-950 hover:bg-rose-900 text-rose-300 border border-rose-800 rounded"
                                title="Cancel Task"
                              >
                                <XCircle className="w-3.5 h-3.5" />
                              </button>
                            )}
                          </div>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 3: Evidence Bindings */}
      {activeTab === 'evidence' && (
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-white">Attached Phase 3 Evidence Bindings</h3>
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-950/80 border-b border-slate-800 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  <th className="py-3 px-4">Task #</th>
                  <th className="py-3 px-4">Evidence Item Title</th>
                  <th className="py-3 px-4">Verification Status</th>
                  <th className="py-3 px-4">Notes</th>
                  <th className="py-3 px-4">Linked At</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {plan.tasks?.flatMap((t) => (t.evidence_links || []).map((link) => ({ ...link, taskSeq: t.task_seq, taskId: t.id }))).length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-slate-500">
                      No evidence items bound to tasks yet.
                    </td>
                  </tr>
                ) : (
                  plan.tasks?.flatMap((t) =>
                    (t.evidence_links || []).map((link) => (
                      <tr key={link.id} className="hover:bg-slate-800/30 transition-colors">
                        <td className="py-3 px-4 font-mono font-bold text-indigo-300">Task #{t.task_seq}</td>
                        <td className="py-3 px-4">
                          <div className="font-semibold text-white">{link.evidence?.title || `Evidence Item #${link.evidence_id}`}</div>
                          <div className="text-[10px] text-slate-500 font-mono">{link.evidence?.original_filename}</div>
                        </td>
                        <td className="py-3 px-4">
                          <span className="px-2 py-0.5 text-[10px] font-mono bg-emerald-950 text-emerald-300 border border-emerald-800 rounded">
                            {link.verification_status}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-slate-400">{link.notes || '—'}</td>
                        <td className="py-3 px-4 font-mono text-slate-500 text-[11px]">
                          {new Date(link.created_at).toLocaleString()}
                        </td>
                        <td className="py-3 px-4 text-right">
                          {!plan.is_immutable && plan.status !== 'CANCELLED' && canExecute && (
                            <button
                              onClick={() => handleUnlinkEvidence(t.id, link.id)}
                              className="p-1 text-rose-400 hover:text-rose-300 hover:bg-rose-950 rounded transition-colors"
                              title="Unlink"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </td>
                      </tr>
                    ))
                  )
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 4: Re-Tests */}
      {activeTab === 'retests' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">Independent Re-Test History</h3>
            {!plan.is_immutable && plan.status === 'PENDING_VALIDATION' && isAuditor && (
              <button
                onClick={() => {
                  setActionError(null);
                  setShowRetestModal(true);
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors"
              >
                <Plus className="w-3.5 h-3.5" />
                Log Empirical Re-Test
              </button>
            )}
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-950/80 border-b border-slate-800 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  <th className="py-3 px-4">Execution Time</th>
                  <th className="py-3 px-4">Tester</th>
                  <th className="py-3 px-4">Result</th>
                  <th className="py-3 px-4">Metric Value</th>
                  <th className="py-3 px-4">Evidence</th>
                  <th className="py-3 px-4">Validation Narrative</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {plan.retest_records?.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-slate-500">
                      No re-test records logged. During PENDING_VALIDATION, an auditor can record empirical results.
                    </td>
                  </tr>
                ) : (
                  plan.retest_records?.map((record) => (
                    <tr key={record.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-3 px-4 font-mono text-slate-300">
                        {new Date(record.test_executed_at).toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-slate-200">{getUserName(record.tester_id)}</td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2.5 py-0.5 text-[10px] font-bold font-mono border rounded ${
                            record.test_result === 'PASS'
                              ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                              : record.test_result === 'FAIL'
                              ? 'bg-rose-950 text-rose-300 border-rose-800'
                              : 'bg-amber-950 text-amber-300 border-amber-800'
                          }`}
                        >
                          {record.test_result}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-400">
                        {record.metric_observed_value !== undefined && record.metric_observed_value !== null
                          ? record.metric_observed_value
                          : '—'}
                      </td>
                      <td className="py-3 px-4 text-indigo-300 font-mono text-[11px]">
                        {record.evidence_id ? `Evidence #${record.evidence_id}` : '—'}
                      </td>
                      <td className="py-3 px-4 text-slate-300 max-w-md">{record.validation_narrative}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 5: Governance / Audit Traceability */}
      {activeTab === 'governance' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <h3 className="text-sm font-semibold text-white">Governance Audit Trail & Traceability</h3>
          <div className="space-y-3 text-xs">
            <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg flex items-center justify-between">
              <span className="text-slate-400">Created:</span>
              <span className="font-mono text-slate-200">{new Date(plan.created_at).toLocaleString()} by {getUserName(plan.plan_owner_id)}</span>
            </div>
            {plan.approved_at && (
              <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg flex items-center justify-between">
                <span className="text-slate-400">Approved:</span>
                <span className="font-mono text-slate-200">{new Date(plan.approved_at).toLocaleString()} by {getUserName(plan.approved_by_id)}</span>
              </div>
            )}
            {plan.started_at && (
              <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg flex items-center justify-between">
                <span className="text-slate-400">Execution Started:</span>
                <span className="font-mono text-slate-200">{new Date(plan.started_at).toLocaleString()}</span>
              </div>
            )}
            {plan.verified_at && (
              <div className="p-3 bg-emerald-950/40 border border-emerald-800/60 rounded-lg flex items-center justify-between">
                <span className="text-emerald-300 font-semibold">Verified & Closed:</span>
                <span className="font-mono text-emerald-200">{new Date(plan.verified_at).toLocaleString()} by {getUserName(plan.verified_by_id)}</span>
              </div>
            )}
            {plan.verification_notes && (
              <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg space-y-1">
                <span className="text-slate-500 font-mono uppercase text-[10px]">Verification Notes:</span>
                <p className="text-slate-300">{plan.verification_notes}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ─── MODALS ──────────────────────────────────────────────────────── */}

      {/* Approve Modal */}
      {showApproveModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-white">Approve Remediation Plan</h3>
            <p className="text-xs text-slate-400">
              Four-eyes governance rule: Approver must be distinct from Plan Owner ({getUserName(plan.plan_owner_id)}).
            </p>
            {isPlanOwner && (
              <div className="p-3 bg-red-950/60 border border-red-800 rounded-lg text-xs text-red-300 flex items-center gap-2">
                <UserX className="w-4 h-4 shrink-0 text-red-400" />
                <span>Separation violation: You are the Plan Owner and cannot approve your own plan.</span>
              </div>
            )}
            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Custom Target Completion Date (Optional)</label>
                <input
                  type="date"
                  value={approveCustomDeadline}
                  onChange={(e) => setApproveCustomDeadline(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white font-mono"
                />
              </div>
              <div>
                <label className="block text-slate-300 font-medium mb-1">Approval Notes</label>
                <textarea
                  rows={2}
                  value={approveNotes}
                  onChange={(e) => setApproveNotes(e.target.value)}
                  placeholder="Governance justification notes..."
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                onClick={() => setShowApproveModal(false)}
                className="px-3 py-1.5 text-xs text-slate-400 hover:text-white bg-slate-800 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleApprove}
                disabled={actionLoading || isPlanOwner}
                className="px-4 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg disabled:opacity-50"
              >
                {actionLoading ? 'Approving...' : 'Confirm Approval'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Verify & Close Modal */}
      {showVerifyModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-white">Four-Eyes Verification & Permanent Closure</h3>
            <p className="text-xs text-slate-400">
              Verifying this CAPA permanently locks the record as immutable, calculates final REI/TTR metrics, and auto-resolves the upstream source.
            </p>
            {isPlanOwner && (
              <div className="p-3 bg-red-950/60 border border-red-800 rounded-lg text-xs text-red-300">
                Separation violation: Plan Owner cannot execute final verification.
              </div>
            )}
            {isTaskAssignee && (
              <div className="p-3 bg-red-950/60 border border-red-800 rounded-lg text-xs text-red-300">
                Separation violation: Task implementers cannot execute final verification.
              </div>
            )}
            <div>
              <label className="block text-slate-300 font-medium mb-1 text-xs">
                Mandatory Verification Notes * (Min 15 Characters)
              </label>
              <textarea
                rows={3}
                value={verifyNotes}
                onChange={(e) => setVerifyNotes(e.target.value)}
                placeholder="Document independent verification evidence, control validation results, and sign-off justification..."
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white text-xs"
                required
              />
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                onClick={() => setShowVerifyModal(false)}
                className="px-3 py-1.5 text-xs text-slate-400 hover:text-white bg-slate-800 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleVerifyClose}
                disabled={actionLoading || isPlanOwner || isTaskAssignee || verifyNotes.trim().length < 15}
                className="px-4 py-1.5 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg shadow disabled:opacity-50"
              >
                {actionLoading ? 'Verifying...' : 'Verify & Close Record'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reject Validation Modal */}
      {showRejectModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-white">Reject Validation (Return for Rework)</h3>
            <p className="text-xs text-slate-400">
              Returns the plan from PENDING_VALIDATION back to IN_EXECUTION for engineering rework.
            </p>
            <div>
              <label className="block text-slate-300 font-medium mb-1 text-xs">
                Mandatory Rejection Notes * (Min 15 Characters)
              </label>
              <textarea
                rows={3}
                value={rejectNotes}
                onChange={(e) => setRejectNotes(e.target.value)}
                placeholder="Explain deficiency, missing evidence, or failed testing requirements..."
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white text-xs"
                required
              />
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                onClick={() => setShowRejectModal(false)}
                className="px-3 py-1.5 text-xs text-slate-400 hover:text-white bg-slate-800 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleRejectValidation}
                disabled={actionLoading || rejectNotes.trim().length < 15}
                className="px-4 py-1.5 text-xs font-semibold text-white bg-amber-600 hover:bg-amber-500 rounded-lg disabled:opacity-50"
              >
                {actionLoading ? 'Rejecting...' : 'Reject Validation'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Cancel Plan Modal */}
      {showCancelModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-white">Cancel Remediation Plan</h3>
            <p className="text-xs text-slate-400">
              Cancelling permanently closes this plan as CANCELLED without resolving upstream sources.
            </p>
            <div>
              <label className="block text-slate-300 font-medium mb-1 text-xs">Cancellation Justification *</label>
              <textarea
                rows={3}
                value={cancelNotes}
                onChange={(e) => setCancelNotes(e.target.value)}
                placeholder="Business justification for cancellation (e.g. Risk Accepted, system decommissioned)..."
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white text-xs"
                required
              />
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                onClick={() => setShowCancelModal(false)}
                className="px-3 py-1.5 text-xs text-slate-400 hover:text-white bg-slate-800 rounded-lg"
              >
                Back
              </button>
              <button
                onClick={handleCancelPlan}
                disabled={actionLoading || !cancelNotes.trim()}
                className="px-4 py-1.5 text-xs font-semibold text-white bg-rose-600 hover:bg-rose-500 rounded-lg disabled:opacity-50"
              >
                {actionLoading ? 'Cancelling...' : 'Confirm Cancellation'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Task Modal */}
      {showAddTaskModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <h3 className="text-base font-bold text-white">Add Remediation Task</h3>
              <button onClick={() => setShowAddTaskModal(false)} className="text-slate-400 text-lg">✕</button>
            </div>
            <form onSubmit={handleAddTask} className="space-y-3 text-xs">
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Seq *</label>
                  <input
                    type="number"
                    min={1}
                    value={taskForm.task_seq}
                    onChange={(e) => setTaskForm({ ...taskForm, task_seq: Number(e.target.value) })}
                    className="w-full px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-white font-mono"
                    required
                  />
                </div>
                <div className="col-span-2">
                  <label className="block text-slate-300 font-medium mb-1">Assignee</label>
                  <select
                    value={taskForm.assignee_id || ''}
                    onChange={(e) => setTaskForm({ ...taskForm, assignee_id: Number(e.target.value) || undefined })}
                    className="w-full px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-white"
                  >
                    <option value="">-- Unassigned --</option>
                    {users.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.full_name} ({u.role})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Title *</label>
                <input
                  type="text"
                  placeholder="Task title..."
                  value={taskForm.title}
                  onChange={(e) => setTaskForm({ ...taskForm, title: e.target.value })}
                  className="w-full px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-white"
                  required
                />
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Description *</label>
                <textarea
                  rows={3}
                  placeholder="Detailed task description..."
                  value={taskForm.description}
                  onChange={(e) => setTaskForm({ ...taskForm, description: e.target.value })}
                  className="w-full px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-white"
                  required
                />
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Due Date</label>
                <input
                  type="date"
                  value={taskForm.due_date ? taskForm.due_date.slice(0, 10) : ''}
                  onChange={(e) => setTaskForm({ ...taskForm, due_date: e.target.value })}
                  className="w-full px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-white font-mono"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowAddTaskModal(false)}
                  className="px-3 py-1.5 text-xs text-slate-400 bg-slate-800 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg"
                >
                  {actionLoading ? 'Adding...' : 'Add Task'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Link Evidence Modal */}
      {showLinkEvidenceModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <h3 className="text-base font-bold text-white">Link Phase 3 Evidence Item</h3>
              <button onClick={() => setShowLinkEvidenceModal(false)} className="text-slate-400 text-lg">✕</button>
            </div>
            <form onSubmit={handleLinkEvidence} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Select Accepted Evidence *</label>
                <select
                  value={evidenceLinkForm.evidence_id || ''}
                  onChange={(e) => setEvidenceLinkForm({ ...evidenceLinkForm, evidence_id: Number(e.target.value) })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white"
                  required
                >
                  <option value="">-- Choose Accepted Evidence Item --</option>
                  {availableEvidence.map((ev) => (
                    <option key={ev.id} value={ev.id}>
                      [ID #{ev.id}] {ev.title} ({ev.original_filename})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Linkage Notes</label>
                <textarea
                  rows={2}
                  placeholder="How this evidence satisfies the task requirement..."
                  value={evidenceLinkForm.notes || ''}
                  onChange={(e) => setEvidenceLinkForm({ ...evidenceLinkForm, notes: e.target.value })}
                  className="w-full px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-white"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowLinkEvidenceModal(false)}
                  className="px-3 py-1.5 text-xs text-slate-400 bg-slate-800 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading || !evidenceLinkForm.evidence_id}
                  className="px-4 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg disabled:opacity-50"
                >
                  {actionLoading ? 'Linking...' : 'Link Evidence'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Log Re-Test Modal */}
      {showRetestModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <h3 className="text-base font-bold text-white">Record Empirical Re-Test</h3>
              <button onClick={() => setShowRetestModal(false)} className="text-slate-400 text-lg">✕</button>
            </div>
            <form onSubmit={handleRecordRetest} className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Test Result *</label>
                  <select
                    value={retestForm.test_result}
                    onChange={(e) =>
                      setRetestForm({ ...retestForm, test_result: e.target.value as ReTestResult })
                    }
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white font-semibold"
                  >
                    <option value="PASS">PASS (Validation Satisfied)</option>
                    <option value="FAIL">FAIL (Auto-Revert to Execution)</option>
                    <option value="INCONCLUSIVE">INCONCLUSIVE</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-300 font-medium mb-1">Observed Metric Value</label>
                  <input
                    type="number"
                    step="0.1"
                    placeholder="e.g. 100.0"
                    value={retestForm.metric_observed_value || ''}
                    onChange={(e) =>
                      setRetestForm({ ...retestForm, metric_observed_value: Number(e.target.value) || undefined })
                    }
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">
                  Associated Accepted Evidence Item {retestForm.test_result === 'PASS' && '*'}
                </label>
                <select
                  value={retestForm.evidence_id || ''}
                  onChange={(e) =>
                    setRetestForm({ ...retestForm, evidence_id: Number(e.target.value) || undefined })
                  }
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white"
                  required={retestForm.test_result === 'PASS'}
                >
                  <option value="">-- Choose Supporting Evidence Item --</option>
                  {availableEvidence.map((ev) => (
                    <option key={ev.id} value={ev.id}>
                      [ID #{ev.id}] {ev.title} ({ev.original_filename})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">
                  Validation Narrative * (Min 10 Characters)
                </label>
                <textarea
                  rows={3}
                  placeholder="Detailed testing methodology, commands run, output verified, and empirical observations..."
                  value={retestForm.validation_narrative}
                  onChange={(e) => setRetestForm({ ...retestForm, validation_narrative: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white text-xs"
                  required
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowRetestModal(false)}
                  className="px-3 py-1.5 text-xs text-slate-400 bg-slate-800 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg"
                >
                  {actionLoading ? 'Recording...' : 'Record Test Result'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
