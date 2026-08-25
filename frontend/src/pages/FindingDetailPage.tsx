import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  CheckCircle2,
  Clock,
  Shield,
  FileText,
  Paperclip,
  Trash2,
  Plus,
  Play,
  Check,
  BadgeAlert,
  FileCheck2,
} from 'lucide-react';
import { findingService } from '../lib/findingService';
import { evidenceService } from '../lib/evidenceService';
import { useAuth } from '../context/AuthContext';
import type {
  FindingStatus,
} from '../types';

export const FindingDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { hasRole } = useAuth();

  const canManageFindings = hasRole('ADMIN', 'GRC_ANALYST', 'SECURITY_ANALYST');
  const canManageRisk = hasRole('ADMIN', 'GRC_ANALYST');

  const findingId = Number(id);

  // Modals & Action drawers
  const [showStatusModal, setShowStatusModal] = useState(false);
  const [targetStatus, setTargetStatus] = useState<FindingStatus>('IN_REMEDIATION');
  const [statusNotes, setStatusNotes] = useState('');
  const [statusResolution, setStatusResolution] = useState('');

  const [showValidateModal, setShowValidateModal] = useState(false);
  const [isValidReview, setIsValidReview] = useState(true);
  const [validationNotes, setValidationNotes] = useState('');

  const [showRiskAcceptModal, setShowRiskAcceptModal] = useState(false);
  const [riskJustification, setRiskJustification] = useState('');
  const [riskExpiry, setRiskExpiry] = useState('');

  const [showLinkEvidenceModal, setShowLinkEvidenceModal] = useState(false);
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<number | ''>('');

  const [actionError, setActionError] = useState<string | null>(null);

  // Queries
  const { data: finding, isLoading, error } = useQuery({
    queryKey: ['finding', findingId],
    queryFn: () => findingService.getFindingById(findingId),
    enabled: !isNaN(findingId),
  });

  const { data: availableEvidence = [] } = useQuery({
    queryKey: ['availableEvidenceForFindingControl', finding?.organization_control_id],
    queryFn: () =>
      evidenceService.getEvidenceItems({
        organization_control_id: finding?.organization_control_id,
      }),
    enabled: !!finding?.organization_control_id,
  });

  // Mutations
  const updateStatusMutation = useMutation({
    mutationFn: (data: { status: FindingStatus; notes?: string; resolution?: string }) =>
      findingService.updateStatus(findingId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['finding', findingId] });
      queryClient.invalidateQueries({ queryKey: ['findings'] });
      queryClient.invalidateQueries({ queryKey: ['findingStats'] });
      setShowStatusModal(false);
      setStatusNotes('');
      setStatusResolution('');
    },
    onError: (err: any) => setActionError(err.response?.data?.detail || 'Failed to update status.'),
  });

  const validateMutation = useMutation({
    mutationFn: (data: { is_valid: boolean; validation_notes: string }) =>
      findingService.validateFinding(findingId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['finding', findingId] });
      queryClient.invalidateQueries({ queryKey: ['findings'] });
      queryClient.invalidateQueries({ queryKey: ['findingStats'] });
      setShowValidateModal(false);
      setValidationNotes('');
    },
    onError: (err: any) => setActionError(err.response?.data?.detail || 'Validation failed.'),
  });

  const acceptRiskMutation = useMutation({
    mutationFn: (data: { justification: string; expiry_date?: string }) =>
      findingService.acceptRisk(findingId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['finding', findingId] });
      queryClient.invalidateQueries({ queryKey: ['findings'] });
      queryClient.invalidateQueries({ queryKey: ['findingStats'] });
      setShowRiskAcceptModal(false);
      setRiskJustification('');
      setRiskExpiry('');
    },
    onError: (err: any) => setActionError(err.response?.data?.detail || 'Risk acceptance failed.'),
  });

  const linkEvidenceMutation = useMutation({
    mutationFn: (evId: number) => findingService.linkEvidence(findingId, evId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['finding', findingId] });
      setShowLinkEvidenceModal(false);
      setSelectedEvidenceId('');
    },
    onError: (err: any) => setActionError(err.response?.data?.detail || 'Failed to link evidence.'),
  });

  const unlinkEvidenceMutation = useMutation({
    mutationFn: (evId: number) => findingService.unlinkEvidence(findingId, evId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['finding', findingId] });
    },
    onError: (err: any) => setActionError(err.response?.data?.detail || 'Failed to unlink evidence.'),
  });

  if (isLoading) {
    return <div className="text-center py-20 text-slate-400">Loading finding details...</div>;
  }

  if (error || !finding) {
    return (
      <div className="p-6 bg-slate-900 border border-slate-800 rounded-xl text-center space-y-3">
        <h3 className="text-lg font-bold text-rose-400">Finding Not Found</h3>
        <p className="text-sm text-slate-400">The requested finding does not exist or you do not have permission.</p>
        <button
          onClick={() => navigate('/findings')}
          className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg"
        >
          Back to Findings
        </button>
      </div>
    );
  }

  const isClosed = finding.status === 'CLOSED';

  const renderOverdueBadge = (overdueStatus: string) => {
    switch (overdueStatus) {
      case 'OVERDUE':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-bold bg-rose-950 text-rose-300 border border-rose-700 animate-pulse">
            <BadgeAlert className="w-4 h-4 text-rose-400" /> OVERDUE
          </span>
        );
      case 'DUE_SOON':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-semibold bg-amber-950 text-amber-300 border border-amber-800">
            <Clock className="w-4 h-4 text-amber-400" /> DUE SOON (&le;7d)
          </span>
        );
      case 'ON_TRACK':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium bg-slate-900 text-emerald-400 border border-emerald-900/50">
            ON TRACK
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Navigation Breadcrumb & Back */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/findings')}
          className="inline-flex items-center gap-2 text-xs font-medium text-slate-400 hover:text-slate-200 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Findings
        </button>

        {/* Action Controls */}
        {!isClosed && canManageFindings && (
          <div className="flex flex-wrap items-center gap-2">
            {finding.status === 'OPEN' && (
              <button
                onClick={() => {
                  setTargetStatus('IN_REMEDIATION');
                  setShowStatusModal(true);
                }}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold transition-colors"
              >
                <Play className="w-3.5 h-3.5" /> Start Remediation
              </button>
            )}

            {(finding.status === 'IN_REMEDIATION' || finding.status === 'OPEN') && (
              <button
                onClick={() => {
                  setTargetStatus('PENDING_VALIDATION');
                  setStatusResolution(finding.resolution || '');
                  setShowStatusModal(true);
                }}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-xs font-semibold transition-colors"
              >
                <FileCheck2 className="w-3.5 h-3.5" /> Submit for Validation
              </button>
            )}

            {finding.status === 'PENDING_VALIDATION' && (
              <button
                onClick={() => setShowValidateModal(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold transition-colors shadow-xs"
              >
                <CheckCircle2 className="w-3.5 h-3.5" /> Authoritative Validation Review
              </button>
            )}

            {(finding.status === 'RESOLVED' || finding.status === 'ACCEPTED_RISK') && (
              <button
                onClick={() => {
                  setTargetStatus('CLOSED');
                  setShowStatusModal(true);
                }}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold transition-colors"
              >
                <Check className="w-3.5 h-3.5 text-emerald-400" /> Close Finding
              </button>
            )}

            {canManageRisk && finding.status !== 'RESOLVED' && finding.status !== 'ACCEPTED_RISK' && (
              <button
                onClick={() => setShowRiskAcceptModal(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-purple-950 hover:bg-purple-900 border border-purple-800 text-purple-300 rounded-lg text-xs font-semibold transition-colors"
              >
                <Shield className="w-3.5 h-3.5" /> Accept Risk
              </button>
            )}
          </div>
        )}
      </div>

      {actionError && (
        <div className="p-3 bg-rose-950/80 border border-rose-800 text-rose-200 text-xs rounded-lg flex items-center justify-between">
          <span>{actionError}</span>
          <button onClick={() => setActionError(null)} className="text-rose-400">&times;</button>
        </div>
      )}

      {/* Header Card */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-6 shadow-xs space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-xs font-bold text-indigo-400 bg-indigo-950 border border-indigo-800 px-2 py-0.5 rounded">
                {finding.control_identifier || `Control #${finding.organization_control_id}`}
              </span>
              <span className="text-xs px-2 py-0.5 rounded font-mono bg-slate-950 text-slate-400 border border-slate-800">
                {finding.finding_type}
              </span>
              <span className="text-xs px-2 py-0.5 rounded font-bold bg-rose-950 text-rose-300 border border-rose-800">
                {finding.severity}
              </span>
              <span className="text-xs px-2 py-0.5 rounded font-semibold bg-slate-800 text-slate-300 border border-slate-700">
                {finding.status}
              </span>
              {renderOverdueBadge(finding.overdue_status)}
            </div>

            <h1 className="text-xl font-bold text-slate-100">{finding.title}</h1>
            <p className="text-xs text-slate-400">{finding.control_title}</p>
          </div>

          {/* 5x5 Deterministic Risk Card */}
          <div className="bg-slate-950 border border-slate-800 p-3.5 rounded-xl text-center min-w-40">
            <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
              Deterministic Risk Matrix
            </div>
            <div className="text-2xl font-bold text-rose-400 mt-0.5 font-mono">
              {finding.risk_score} <span className="text-xs text-slate-500 font-sans">/ 25</span>
            </div>
            <div className="text-xs font-bold text-rose-300 uppercase tracking-wider mt-0.5">
              {finding.risk_band} BAND
            </div>
            <div className="text-[10px] text-slate-500 mt-1 font-mono">
              Impact ({finding.impact}) &times; Likelihood ({finding.likelihood})
            </div>
          </div>
        </div>

        {/* Metadata Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-slate-800/80 text-xs">
          <div>
            <span className="text-slate-500 block">Owner</span>
            <span className="text-slate-200 font-medium">{finding.owner?.full_name || 'Unassigned'}</span>
          </div>
          <div>
            <span className="text-slate-500 block">Due Date</span>
            <span className="text-slate-200 font-medium">{finding.due_date || 'None'}</span>
          </div>
          <div>
            <span className="text-slate-500 block">Created By</span>
            <span className="text-slate-200 font-medium">{finding.created_by?.full_name || 'System'}</span>
          </div>
          <div>
            <span className="text-slate-500 block">Created At</span>
            <span className="text-slate-200 font-medium">{new Date(finding.created_at).toLocaleDateString()}</span>
          </div>
        </div>

        {/* Details & Recommendation */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-slate-800/80 text-xs">
          <div className="space-y-1">
            <span className="font-semibold text-slate-400 uppercase tracking-wider text-[10px]">
              Deficiency Description
            </span>
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-slate-300 whitespace-pre-wrap">
              {finding.description}
            </div>
          </div>

          <div className="space-y-1">
            <span className="font-semibold text-slate-400 uppercase tracking-wider text-[10px]">
              Remediation Recommendation
            </span>
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-slate-300 whitespace-pre-wrap">
              {finding.recommendation}
            </div>
          </div>
        </div>

        {/* Root Cause & Remediation Plan */}
        {(finding.root_cause || finding.remediation_plan) && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-slate-800/80 text-xs">
            {finding.root_cause && (
              <div className="space-y-1">
                <span className="font-semibold text-slate-400 uppercase tracking-wider text-[10px]">
                  Root Cause Analysis
                </span>
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-slate-400 whitespace-pre-wrap">
                  {finding.root_cause}
                </div>
              </div>
            )}
            {finding.remediation_plan && (
              <div className="space-y-1">
                <span className="font-semibold text-slate-400 uppercase tracking-wider text-[10px]">
                  Remediation Action Plan
                </span>
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-slate-300 whitespace-pre-wrap">
                  {finding.remediation_plan}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Risk Acceptance Box */}
        {finding.status === 'ACCEPTED_RISK' && (
          <div className="p-4 bg-purple-950/50 border border-purple-800/80 rounded-xl space-y-2 text-xs">
            <div className="flex items-center gap-2 text-purple-300 font-bold">
              <Shield className="w-4 h-4" /> Formal Risk Acceptance Active
            </div>
            <div className="text-slate-300 whitespace-pre-wrap">
              <strong className="text-slate-400">Justification:</strong> {finding.risk_acceptance_justification}
            </div>
            <div className="flex items-center gap-4 text-purple-400 font-mono text-[11px]">
              <span>Accepted By: {finding.risk_accepted_by?.full_name || 'Authorized Lead'}</span>
              <span>Accepted At: {finding.risk_accepted_at ? new Date(finding.risk_accepted_at).toLocaleDateString() : 'N/A'}</span>
              <span>Review Expiry: {finding.risk_acceptance_expiry || 'Indefinite'}</span>
            </div>
          </div>
        )}

        {/* Resolution Box */}
        {finding.resolution && (
          <div className="p-4 bg-emerald-950/50 border border-emerald-800/80 rounded-xl space-y-2 text-xs">
            <div className="flex items-center gap-2 text-emerald-300 font-bold">
              <CheckCircle2 className="w-4 h-4" /> Documented Resolution
            </div>
            <div className="text-slate-300 whitespace-pre-wrap">{finding.resolution}</div>
            {finding.resolved_at && (
              <div className="text-[11px] text-emerald-400 font-mono">
                Validated and Resolved at {new Date(finding.resolved_at).toLocaleString()} by {finding.resolved_by?.full_name || 'Security Auditor'}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Remediation Audit Log & Notes */}
      {finding.remediation_notes && (
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 shadow-xs space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Remediation &amp; Validation Log
          </h3>
          <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 text-xs font-mono text-slate-300 whitespace-pre-wrap max-h-60 overflow-y-auto">
            {finding.remediation_notes}
          </div>
        </div>
      )}

      {/* Linked Evidence Section */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <Paperclip className="w-4 h-4 text-indigo-400" /> Linked Evidence Artifacts
            </h2>
            <p className="text-xs text-slate-400">
              Evidence proving remediation or demonstrating the vulnerability.
            </p>
          </div>
          {!isClosed && canManageFindings && (
            <button
              onClick={() => setShowLinkEvidenceModal(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-indigo-300 rounded-lg text-xs font-medium transition-colors"
            >
              <Plus className="w-3.5 h-3.5" /> Link Evidence
            </button>
          )}
        </div>

        {finding.evidence_links && finding.evidence_links.length > 0 ? (
          <div className="divide-y divide-slate-800 border border-slate-800 rounded-lg overflow-hidden">
            {finding.evidence_links.map((link) => (
              <div
                key={link.id}
                className="p-3 bg-slate-950/60 flex items-center justify-between gap-4 text-xs"
              >
                <div className="flex items-center gap-3">
                  <FileText className="w-4 h-4 text-indigo-400 shrink-0" />
                  <div>
                    <div className="font-semibold text-slate-200">
                      {link.evidence?.title || link.evidence?.original_filename}
                    </div>
                    <div className="text-slate-500 font-mono text-[11px]">
                      {link.evidence?.file_extension.toUpperCase()} &bull; {link.evidence?.status} &bull; SHA-256: {link.evidence?.sha256_hash.slice(0, 12)}...
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span className="text-[11px] text-slate-500">
                    Linked: {new Date(link.created_at).toLocaleDateString()}
                  </span>
                  {!isClosed && canManageFindings && (
                    <button
                      onClick={() => unlinkEvidenceMutation.mutate(link.evidence_id)}
                      className="p-1 text-rose-400 hover:text-rose-300 hover:bg-rose-950/50 rounded transition-colors"
                      title="Unlink evidence"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-6 bg-slate-950/40 rounded-lg border border-dashed border-slate-800 text-xs text-slate-500">
            No evidence artifacts linked to this finding yet.
          </div>
        )}
      </div>

      {/* Status Transition Modal */}
      {showStatusModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-xs">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-slate-100">
              Update Status: {targetStatus.replace('_', ' ')}
            </h3>

            <div className="space-y-3 text-sm">
              {targetStatus === 'PENDING_VALIDATION' && (
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Documented Resolution <span className="text-rose-400">*</span>
                  </label>
                  <textarea
                    rows={3}
                    required
                    placeholder="Describe how the deficiency was remediated and what configuration changes were deployed..."
                    value={statusResolution}
                    onChange={(e) => setStatusResolution(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200 text-sm focus:outline-hidden"
                  />
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Status Transition Notes
                </label>
                <textarea
                  rows={2}
                  placeholder="Optional log comments for audit trail..."
                  value={statusNotes}
                  onChange={(e) => setStatusNotes(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200 text-sm focus:outline-hidden"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setShowStatusModal(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-lg"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={
                  (targetStatus === 'PENDING_VALIDATION' && !statusResolution.trim()) ||
                  updateStatusMutation.isPending
                }
                onClick={() =>
                  updateStatusMutation.mutate({
                    status: targetStatus,
                    notes: statusNotes || undefined,
                    resolution: statusResolution || undefined,
                  })
                }
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg disabled:opacity-50"
              >
                {updateStatusMutation.isPending ? 'Updating...' : 'Confirm Status Transition'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Authoritative Validation Modal */}
      {showValidateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-xs">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" /> Authoritative Validation Review
            </h3>
            <p className="text-xs text-slate-400">
              Perform independent verification of the documented resolution. If validation fails, the finding will return to IN_REMEDIATION status.
            </p>

            <div className="space-y-3 text-sm">
              <div className="flex items-center gap-4 p-3 bg-slate-950 border border-slate-800 rounded-lg">
                <label className="flex items-center gap-2 text-xs font-semibold text-emerald-400 cursor-pointer">
                  <input
                    type="radio"
                    name="validation_decision"
                    checked={isValidReview === true}
                    onChange={() => setIsValidReview(true)}
                    className="text-emerald-500 focus:ring-emerald-500"
                  />
                  PASS (Mark Resolved)
                </label>
                <label className="flex items-center gap-2 text-xs font-semibold text-rose-400 cursor-pointer">
                  <input
                    type="radio"
                    name="validation_decision"
                    checked={isValidReview === false}
                    onChange={() => setIsValidReview(false)}
                    className="text-rose-500 focus:ring-rose-500"
                  />
                  FAIL (Return to Remediation)
                </label>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Validation Review Notes <span className="text-rose-400">*</span>
                </label>
                <textarea
                  rows={3}
                  required
                  placeholder="Document tests executed and justification for validation decision..."
                  value={validationNotes}
                  onChange={(e) => setValidationNotes(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200 text-sm focus:outline-hidden"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setShowValidateModal(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-lg"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={!validationNotes.trim() || validateMutation.isPending}
                onClick={() =>
                  validateMutation.mutate({
                    is_valid: isValidReview,
                    validation_notes: validationNotes,
                  })
                }
                className={`px-4 py-2 text-white text-xs font-semibold rounded-lg disabled:opacity-50 ${
                  isValidReview ? 'bg-emerald-600 hover:bg-emerald-500' : 'bg-rose-600 hover:bg-rose-500'
                }`}
              >
                {validateMutation.isPending ? 'Processing...' : isValidReview ? 'Confirm Resolution' : 'Reject Remediation'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Risk Acceptance Modal */}
      {showRiskAcceptModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-xs">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <Shield className="w-5 h-5 text-purple-400" /> Formal Risk Acceptance
            </h3>
            <p className="text-xs text-slate-400">
              Formally accept residual risk for this finding. Requires an authorized GRC or Security lead with documented business justification.
            </p>

            <div className="space-y-3 text-sm">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Business Justification &amp; Compensating Controls <span className="text-rose-400">*</span>
                </label>
                <textarea
                  rows={3}
                  required
                  placeholder="Document business rationale, compensating controls in place, and mitigation milestones..."
                  value={riskJustification}
                  onChange={(e) => setRiskJustification(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200 text-sm focus:outline-hidden"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Risk Acceptance Expiry / Review Date
                </label>
                <input
                  type="date"
                  value={riskExpiry}
                  onChange={(e) => setRiskExpiry(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 text-sm focus:outline-hidden"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setShowRiskAcceptModal(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-lg"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={riskJustification.trim().length < 5 || acceptRiskMutation.isPending}
                onClick={() =>
                  acceptRiskMutation.mutate({
                    justification: riskJustification,
                    expiry_date: riskExpiry || undefined,
                  })
                }
                className="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold rounded-lg disabled:opacity-50"
              >
                {acceptRiskMutation.isPending ? 'Submitting...' : 'Sign & Accept Risk'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Link Evidence Modal */}
      {showLinkEvidenceModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-xs">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <Paperclip className="w-4 h-4 text-indigo-400" /> Link Evidence Item
            </h3>
            <p className="text-xs text-slate-400">
              Select an uploaded evidence artifact belonging to this control.
            </p>

            <select
              value={selectedEvidenceId}
              onChange={(e) => setSelectedEvidenceId(Number(e.target.value))}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 text-sm focus:outline-hidden focus:border-indigo-500"
            >
              <option value="">-- Choose evidence artifact --</option>
              {availableEvidence.map((ev) => (
                <option key={ev.id} value={ev.id}>
                  {ev.title || ev.original_filename} ({ev.status})
                </option>
              ))}
            </select>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setShowLinkEvidenceModal(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-lg"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={!selectedEvidenceId || linkEvidenceMutation.isPending}
                onClick={() => linkEvidenceMutation.mutate(Number(selectedEvidenceId))}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg disabled:opacity-50"
              >
                Link Artifact
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
export default FindingDetailPage;
