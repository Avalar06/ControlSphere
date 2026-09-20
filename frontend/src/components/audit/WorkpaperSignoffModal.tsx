import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Clock,
  Send,
  X,
  Lock,
  AlertTriangle,
  UserCheck,
} from 'lucide-react';
import { auditService } from '../../lib/auditService';
import type { AuditWorkpaperReview, WorkpaperStatus } from '../../types';

interface WorkpaperSignoffModalProps {
  auditId: number;
  procedure: any;
  isOpen: boolean;
  onClose: () => void;
  isClosed: boolean;
}

export const WorkpaperSignoffModal: React.FC<WorkpaperSignoffModalProps> = ({
  auditId,
  procedure,
  isOpen,
  onClose,
  isClosed,
}) => {
  const queryClient = useQueryClient();
  const procedureId = procedure.id;

  const [testingSummary, setTestingSummary] = useState('');
  const [conclusion, setConclusion] = useState('');
  const [reviewNotes, setReviewNotes] = useState('');
  const [rejectionReason, setRejectionReason] = useState('');
  const [isRejecting, setIsRejecting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Query active workpaper
  const { data: workpaper, isLoading } = useQuery<AuditWorkpaperReview | null>({
    queryKey: ['auditWorkpaper', auditId, procedureId],
    queryFn: () => auditService.getWorkpaper(auditId, procedureId),
    enabled: isOpen && !isNaN(procedureId),
  });

  // Mutations
  const submitMutation = useMutation({
    mutationFn: (payload: any) => auditService.submitWorkpaper(auditId, procedureId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auditWorkpaper', auditId, procedureId] });
      queryClient.invalidateQueries({ queryKey: ['audit', auditId] });
      queryClient.invalidateQueries({ queryKey: ['auditReadiness', auditId] });
      setActionError(null);
    },
    onError: (err: any) => {
      setActionError(err.response?.data?.detail || err.message || 'Failed to submit workpaper');
    },
  });

  const approveMutation = useMutation({
    mutationFn: (payload: any) => auditService.approveWorkpaper(auditId, procedureId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auditWorkpaper', auditId, procedureId] });
      queryClient.invalidateQueries({ queryKey: ['audit', auditId] });
      queryClient.invalidateQueries({ queryKey: ['auditReadiness', auditId] });
      setActionError(null);
    },
    onError: (err: any) => {
      setActionError(err.response?.data?.detail || err.message || 'Failed to approve workpaper');
    },
  });

  const requestChangesMutation = useMutation({
    mutationFn: (payload: any) =>
      auditService.requestChangesWorkpaper(auditId, procedureId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auditWorkpaper', auditId, procedureId] });
      queryClient.invalidateQueries({ queryKey: ['audit', auditId] });
      queryClient.invalidateQueries({ queryKey: ['auditReadiness', auditId] });
      setIsRejecting(false);
      setActionError(null);
    },
    onError: (err: any) => {
      setActionError(err.response?.data?.detail || err.message || 'Failed to request changes');
    },
  });

  if (!isOpen) return null;

  const getStatusBadge = (status?: WorkpaperStatus) => {
    switch (status) {
      case 'REVIEWED_APPROVED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-semibold bg-emerald-950 text-emerald-300 border border-emerald-800">
            <Lock size={12} /> Approved & Sealed
          </span>
        );
      case 'SUBMITTED_FOR_REVIEW':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-semibold bg-amber-950 text-amber-300 border border-amber-800">
            <Clock size={12} /> Under Review (Four-Eyes)
          </span>
        );
      case 'CHANGES_REQUESTED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-semibold bg-rose-950 text-rose-300 border border-rose-800">
            <XCircle size={12} /> Changes Requested
          </span>
        );
      case 'DRAFT':
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-700">
            Draft
          </span>
        );
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-xs p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex justify-between items-center px-6 py-4 border-b border-slate-800 bg-slate-950">
          <div>
            <div className="flex items-center gap-2">
              <ShieldCheck size={18} className="text-indigo-400" />
              <h3 className="text-sm font-bold text-slate-100">Four-Eyes Workpaper Signoff</h3>
              {getStatusBadge(workpaper?.status)}
            </div>
            <p className="text-xs text-slate-400 mt-0.5">Procedure: {procedure.title}</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-200">
            <X size={18} />
          </button>
        </div>

        {actionError && (
          <div className="mx-6 mt-4 p-3 bg-rose-950/60 border border-rose-800 rounded-xl text-xs text-rose-300 flex items-center justify-between">
            <span>{actionError}</span>
            <button onClick={() => setActionError(null)} className="text-rose-400 hover:text-rose-200">
              <X size={14} />
            </button>
          </div>
        )}

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-4 text-xs">
          {isLoading ? (
            <div className="p-8 text-center text-slate-500">Loading workpaper signoff data...</div>
          ) : (
            <>
              {/* If SEALED & APPROVED */}
              {workpaper?.status === 'REVIEWED_APPROVED' && (
                <div className="bg-slate-950 p-5 rounded-xl border border-emerald-800/60 space-y-4">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-xl bg-emerald-950/80 border border-emerald-700 flex items-center justify-center text-emerald-300">
                      <Lock size={20} />
                    </div>
                    <div>
                      <div className="text-sm font-bold text-slate-100">
                        Cryptographically Sealed Workpaper (Version {workpaper.version_number})
                      </div>
                      <div className="text-slate-400 text-[11px]">
                        Fieldwork testing approved under strict Segregation of Duties.
                      </div>
                    </div>
                  </div>

                  <div className="p-3 bg-slate-900/80 rounded-lg border border-slate-800 font-mono text-[11px] space-y-1">
                    <div className="text-slate-400 text-[10px] uppercase tracking-wider font-semibold">
                      Tamper-Evident SHA-256 Digest
                    </div>
                    <div className="text-emerald-400 break-all select-all font-bold">
                      {workpaper.workpaper_hash_sha256}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4 text-xs pt-2 border-t border-slate-800">
                    <div>
                      <span className="text-slate-500 block">Prepared By:</span>
                      <span className="text-slate-200 font-semibold">{workpaper.prepared_by_name || `User #${workpaper.prepared_by_id}`}</span>
                      <span className="text-[11px] text-slate-400 block mt-0.5 font-mono">{workpaper.prepared_at ? new Date(workpaper.prepared_at).toLocaleString() : '—'}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Reviewed & Approved By:</span>
                      <span className="text-slate-200 font-semibold">{workpaper.reviewed_by_name || `User #${workpaper.reviewed_by_id}`}</span>
                      <span className="text-[11px] text-slate-400 block mt-0.5 font-mono">{workpaper.reviewed_at ? new Date(workpaper.reviewed_at).toLocaleString() : '—'}</span>
                    </div>
                  </div>

                  <div className="space-y-2 pt-2 border-t border-slate-800">
                    <div>
                      <span className="text-slate-400 font-semibold block mb-1">Testing Summary:</span>
                      <div className="p-2.5 bg-slate-900 rounded-lg text-slate-300 text-xs">
                        {workpaper.testing_summary}
                      </div>
                    </div>
                    <div>
                      <span className="text-slate-400 font-semibold block mb-1">Auditor Conclusion:</span>
                      <div className="p-2.5 bg-slate-900 rounded-lg text-slate-300 text-xs">
                        {workpaper.conclusion}
                      </div>
                    </div>
                    {workpaper.review_notes && (
                      <div>
                        <span className="text-slate-400 font-semibold block mb-1">Review Notes:</span>
                        <div className="p-2.5 bg-slate-900 rounded-lg text-slate-400 text-xs">
                          {workpaper.review_notes}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* If UNDER REVIEW (Four-Eyes Approval Phase) */}
              {workpaper?.status === 'SUBMITTED_FOR_REVIEW' && (
                <div className="space-y-4">
                  <div className="bg-slate-950 p-4 rounded-xl border border-amber-800/60 space-y-3">
                    <div className="flex items-center gap-2 text-amber-300 font-semibold">
                      <UserCheck size={16} /> Four-Eyes Verification In Progress
                    </div>
                    <p className="text-slate-400 text-xs">
                      Submitted by <span className="text-slate-200 font-semibold">{workpaper.prepared_by_name || `User #${workpaper.prepared_by_id}`}</span>.
                      Per IIA Standard 2300, the preparer cannot approve their own workpaper.
                    </p>

                    <div className="space-y-2 pt-2 border-t border-slate-800 text-xs">
                      <div>
                        <span className="text-slate-400 font-semibold">Testing Summary:</span>
                        <div className="p-2.5 bg-slate-900 rounded-lg text-slate-200 mt-1">
                          {workpaper.testing_summary}
                        </div>
                      </div>
                      <div>
                        <span className="text-slate-400 font-semibold">Auditor Conclusion:</span>
                        <div className="p-2.5 bg-slate-900 rounded-lg text-slate-200 mt-1">
                          {workpaper.conclusion}
                        </div>
                      </div>
                    </div>
                  </div>

                  {!isClosed && (
                    <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3">
                      <h4 className="font-bold text-slate-200">Reviewer Decision</h4>

                      {isRejecting ? (
                        <div className="space-y-3">
                          <div>
                            <label className="block text-rose-300 font-semibold mb-1">
                              Rejection Reason / Required Changes *
                            </label>
                            <textarea
                              rows={3}
                              value={rejectionReason}
                              onChange={(e) => setRejectionReason(e.target.value)}
                              placeholder="Describe what additional testing or documentation is required before signoff..."
                              className="w-full bg-slate-900 border border-rose-800 rounded-lg p-2.5 text-slate-200 focus:outline-hidden focus:border-rose-500"
                            />
                          </div>
                          <div className="flex justify-end gap-2">
                            <button
                              onClick={() => setIsRejecting(false)}
                              className="px-3 py-1.5 rounded border border-slate-700 text-slate-300"
                            >
                              Cancel
                            </button>
                            <button
                              onClick={() =>
                                requestChangesMutation.mutate({
                                  rejection_reason: rejectionReason,
                                })
                              }
                              disabled={requestChangesMutation.isPending}
                              className="px-3 py-1.5 rounded bg-rose-600 hover:bg-rose-500 text-white font-medium disabled:opacity-50"
                            >
                              {requestChangesMutation.isPending ? 'Submitting...' : 'Confirm Request Changes'}
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="space-y-3">
                          <div>
                            <label className="block text-slate-300 font-semibold mb-1">
                              Review Notes (Optional)
                            </label>
                            <textarea
                              rows={2}
                              value={reviewNotes}
                              onChange={(e) => setReviewNotes(e.target.value)}
                              placeholder="Feedback on fieldwork execution..."
                              className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2.5 text-slate-200 focus:outline-hidden focus:border-indigo-500"
                            />
                          </div>

                          <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
                            <button
                              onClick={() => setIsRejecting(true)}
                              className="px-3 py-1.5 rounded-lg border border-rose-800 text-rose-300 hover:bg-rose-950/40 font-medium transition-colors cursor-pointer"
                            >
                              Request Changes
                            </button>
                            <button
                              onClick={() =>
                                approveMutation.mutate({
                                  review_notes: reviewNotes,
                                })
                              }
                              disabled={approveMutation.isPending}
                              className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50"
                            >
                              <CheckCircle2 size={14} />
                              {approveMutation.isPending ? 'Sealing...' : 'Approve & Seal Digest'}
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* If DRAFT or CHANGES_REQUESTED (Preparation Phase) */}
              {(!workpaper || workpaper.status === 'DRAFT' || workpaper.status === 'CHANGES_REQUESTED') && (
                <div className="space-y-4">
                  {workpaper?.status === 'CHANGES_REQUESTED' && (
                    <div className="p-3 bg-rose-950/40 border border-rose-800 rounded-xl text-rose-300 space-y-1">
                      <div className="font-semibold flex items-center gap-1">
                        <AlertTriangle size={14} /> Reviewer Feedback on Version {workpaper.version_number}:
                      </div>
                      <div className="text-[11px]">{workpaper.rejection_reason}</div>
                    </div>
                  )}

                  <div className="bg-slate-950 p-5 rounded-xl border border-slate-800 space-y-4">
                    <div>
                      <h4 className="font-bold text-slate-200">Prepare Workpaper Submission</h4>
                      <p className="text-slate-400">
                        Record testing fieldwork summary and audit conclusion before submitting for Four-Eyes review.
                      </p>
                    </div>

                    <div>
                      <label className="block text-slate-300 font-semibold mb-1">
                        Testing Summary * (Methodology, Scope, Observations)
                      </label>
                      <textarea
                        required
                        rows={4}
                        defaultValue={workpaper?.testing_summary || testingSummary}
                        onChange={(e) => setTestingSummary(e.target.value)}
                        placeholder="Detail sample extraction, testing procedures conducted, and outcomes..."
                        className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2.5 text-slate-200 focus:outline-hidden focus:border-indigo-500"
                      />
                    </div>

                    <div>
                      <label className="block text-slate-300 font-semibold mb-1">
                        Auditor Conclusion * (Effectiveness Verdict)
                      </label>
                      <textarea
                        required
                        rows={3}
                        defaultValue={workpaper?.conclusion || conclusion}
                        onChange={(e) => setConclusion(e.target.value)}
                        placeholder="State definitive conclusion on operational effectiveness of the control..."
                        className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2.5 text-slate-200 focus:outline-hidden focus:border-indigo-500"
                      />
                    </div>

                    {!isClosed && (
                      <div className="flex justify-end pt-2 border-t border-slate-800">
                        <button
                          onClick={() => {
                            const summaryText = testingSummary || workpaper?.testing_summary || '';
                            const conclusionText = conclusion || workpaper?.conclusion || '';
                            if (!summaryText.trim() || !conclusionText.trim()) {
                              setActionError('Both testing summary and conclusion are required.');
                              return;
                            }
                            submitMutation.mutate({
                              testing_summary: summaryText,
                              conclusion: conclusionText,
                            });
                          }}
                          disabled={submitMutation.isPending}
                          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-medium flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50"
                        >
                          <Send size={14} />
                          {submitMutation.isPending ? 'Submitting...' : 'Submit for Four-Eyes Review'}
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};
