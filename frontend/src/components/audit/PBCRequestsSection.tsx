import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  FileText,
  Plus,
  CheckCircle2,
  AlertCircle,
  Clock,
  Send,
  XCircle,
  X,
  FileCheck,
} from 'lucide-react';
import { auditService } from '../../lib/auditService';
import { evidenceService } from '../../lib/evidenceService';
import type { AuditPBCRequest, PBCStatus, PBCPriority } from '../../types';

interface PBCRequestsSectionProps {
  auditId: number;
  isClosed: boolean;
  scopeControls?: any[];
  allUsers?: any[];
}

export const PBCRequestsSection: React.FC<PBCRequestsSectionProps> = ({
  auditId,
  isClosed,
  scopeControls = [],
  allUsers = [],
}) => {
  const queryClient = useQueryClient();
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [selectedPbcForFulfill, setSelectedPbcForFulfill] = useState<AuditPBCRequest | null>(null);
  const [selectedPbcForReview, setSelectedPbcForReview] = useState<AuditPBCRequest | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  // Form states
  const [createForm, setCreateForm] = useState({
    title: '',
    description: '',
    organization_control_id: '' as number | '',
    procedure_id: '' as number | '',
    assigned_to_id: '' as number | '',
    due_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    priority: 'MEDIUM' as PBCPriority,
  });

  const [fulfillForm, setFulfillForm] = useState({
    evidence_id: '' as number | '',
    submission_notes: '',
  });

  const [reviewForm, setReviewForm] = useState({
    decision: 'ACCEPT' as 'ACCEPT' | 'REJECT',
    review_notes: '',
    rejection_reason: '',
  });

  // Queries
  const { data: pbcRequests = [], isLoading } = useQuery<AuditPBCRequest[]>({
    queryKey: ['auditPBCRequests', auditId],
    queryFn: () => auditService.listPBCRequests(auditId),
    enabled: !isNaN(auditId),
  });

  const { data: evidenceItems = [] } = useQuery({
    queryKey: ['evidence'],
    queryFn: () => evidenceService.getEvidenceItems(),
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: (payload: any) => auditService.createPBCRequest(auditId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auditPBCRequests', auditId] });
      queryClient.invalidateQueries({ queryKey: ['auditReadiness', auditId] });
      setIsCreateModalOpen(false);
      setCreateForm({
        title: '',
        description: '',
        organization_control_id: '',
        procedure_id: '',
        assigned_to_id: '',
        due_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        priority: 'MEDIUM',
      });
      setActionError(null);
    },
    onError: (err: any) => {
      setActionError(err.response?.data?.detail || err.message || 'Failed to create PBC request');
    },
  });

  const fulfillMutation = useMutation({
    mutationFn: ({ pbcId, payload }: { pbcId: number; payload: any }) =>
      auditService.fulfillPBCRequest(auditId, pbcId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auditPBCRequests', auditId] });
      queryClient.invalidateQueries({ queryKey: ['audit', auditId] });
      queryClient.invalidateQueries({ queryKey: ['auditReadiness', auditId] });
      setSelectedPbcForFulfill(null);
      setFulfillForm({ evidence_id: '', submission_notes: '' });
      setActionError(null);
    },
    onError: (err: any) => {
      setActionError(err.response?.data?.detail || err.message || 'Failed to fulfill PBC request');
    },
  });

  const reviewMutation = useMutation({
    mutationFn: ({ pbcId, payload }: { pbcId: number; payload: any }) =>
      auditService.reviewPBCRequest(auditId, pbcId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auditPBCRequests', auditId] });
      queryClient.invalidateQueries({ queryKey: ['audit', auditId] });
      queryClient.invalidateQueries({ queryKey: ['auditReadiness', auditId] });
      setSelectedPbcForReview(null);
      setReviewForm({ decision: 'ACCEPT', review_notes: '', rejection_reason: '' });
      setActionError(null);
    },
    onError: (err: any) => {
      setActionError(err.response?.data?.detail || err.message || 'Failed to review PBC request');
    },
  });

  const getStatusBadge = (status: PBCStatus) => {
    switch (status) {
      case 'ACCEPTED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-950 text-emerald-300 border border-emerald-800">
            <CheckCircle2 size={11} /> Accepted
          </span>
        );
      case 'SUBMITTED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-950 text-amber-300 border border-amber-800">
            <Clock size={11} /> Under Review
          </span>
        );
      case 'REJECTED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-950 text-rose-300 border border-rose-800">
            <XCircle size={11} /> Changes Requested
          </span>
        );
      case 'REQUESTED':
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-indigo-950 text-indigo-300 border border-indigo-800">
            <Send size={11} /> Requested
          </span>
        );
    }
  };

  const getPriorityBadge = (priority: PBCPriority) => {
    const colors: Record<PBCPriority, string> = {
      CRITICAL: 'bg-rose-950/80 text-rose-300 border-rose-800',
      HIGH: 'bg-amber-950/80 text-amber-300 border-amber-800',
      MEDIUM: 'bg-slate-800 text-slate-300 border-slate-700',
      LOW: 'bg-slate-900 text-slate-400 border-slate-800',
    };
    return (
      <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono border ${colors[priority]}`}>
        {priority}
      </span>
    );
  };

  return (
    <div className="space-y-4">
      {actionError && (
        <div className="p-3 bg-rose-950/60 border border-rose-800 rounded-xl text-xs text-rose-300 flex items-center justify-between">
          <span>{actionError}</span>
          <button onClick={() => setActionError(null)} className="text-rose-400 hover:text-rose-200">
            <X size={14} />
          </button>
        </div>
      )}

      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
            <FileText size={16} className="text-indigo-400" />
            PBC (Provided By Client) Requests
          </h3>
          <p className="text-xs text-slate-400">
            Formal audit evidence requests with four-eyes signoff and authoritative evidence binding.
          </p>
        </div>
        {!isClosed && (
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <Plus size={14} /> New PBC Request
          </button>
        )}
      </div>

      {/* Table */}
      <div className="bg-slate-900/80 rounded-xl border border-slate-800 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-xs text-slate-500">Loading PBC requests...</div>
        ) : pbcRequests.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500">
            No PBC requests logged for this engagement. Click "New PBC Request" to issue a formal request to control owners.
          </div>
        ) : (
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950 text-slate-400 font-semibold uppercase border-b border-slate-800">
              <tr>
                <th className="px-4 py-3">Identifier & Title</th>
                <th className="px-4 py-3">Control</th>
                <th className="px-4 py-3">Priority</th>
                <th className="px-4 py-3">Assigned To</th>
                <th className="px-4 py-3">Due Date</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Evidence</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {pbcRequests.map((pbc) => (
                <tr key={pbc.id} className="hover:bg-slate-800/40">
                  <td className="px-4 py-3">
                    <div className="font-mono text-[11px] text-indigo-400 font-semibold">
                      {pbc.request_identifier}
                    </div>
                    <div className="font-medium text-slate-200 text-xs">{pbc.title}</div>
                    {pbc.rejection_reason && (
                      <div className="text-[11px] text-rose-400 mt-1 flex items-start gap-1">
                        <AlertCircle size={12} className="shrink-0 mt-0.5" />
                        <span>Rejection note: {pbc.rejection_reason}</span>
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className="font-mono text-[11px] text-slate-300 bg-slate-800 px-1.5 py-0.5 rounded">
                      {pbc.control_code || `Control #${pbc.organization_control_id}`}
                    </span>
                  </td>
                  <td className="px-4 py-3">{getPriorityBadge(pbc.priority)}</td>
                  <td className="px-4 py-3 text-slate-300">
                    {pbc.assigned_to_name || 'Unassigned'}
                  </td>
                  <td className="px-4 py-3 text-slate-400 font-mono text-[11px]">
                    {pbc.due_date}
                  </td>
                  <td className="px-4 py-3">{getStatusBadge(pbc.status)}</td>
                  <td className="px-4 py-3 text-slate-300">
                    {pbc.fulfilled_evidence_id ? (
                      <span className="inline-flex items-center gap-1 text-[11px] text-emerald-400 font-medium">
                        <FileCheck size={12} />
                        {pbc.evidence_filename || `Evidence #${pbc.fulfilled_evidence_id}`}
                      </span>
                    ) : (
                      <span className="text-slate-500 italic text-[11px]">None</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right space-x-2">
                    {!isClosed && (pbc.status === 'REQUESTED' || pbc.status === 'REJECTED') && (
                      <button
                        onClick={() => setSelectedPbcForFulfill(pbc)}
                        className="px-2 py-1 bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-300 text-[11px] font-medium rounded transition-colors"
                      >
                        Fulfill
                      </button>
                    )}
                    {!isClosed && pbc.status === 'SUBMITTED' && (
                      <button
                        onClick={() => setSelectedPbcForReview(pbc)}
                        className="px-2 py-1 bg-purple-600/30 hover:bg-purple-600/50 text-purple-300 text-[11px] font-medium rounded transition-colors"
                      >
                        Review
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* MODAL: CREATE PBC REQUEST */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl">
            <div className="flex justify-between items-center px-5 py-4 border-b border-slate-800 bg-slate-950">
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <Plus size={16} className="text-indigo-400" /> Issue New PBC Request
              </h3>
              <button
                onClick={() => setIsCreateModalOpen(false)}
                className="text-slate-400 hover:text-slate-200"
              >
                <X size={16} />
              </button>
            </div>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (!createForm.organization_control_id) {
                  setActionError('Must select an organization control.');
                  return;
                }
                createMutation.mutate({
                  title: createForm.title,
                  description: createForm.description,
                  organization_control_id: Number(createForm.organization_control_id),
                  procedure_id: createForm.procedure_id ? Number(createForm.procedure_id) : undefined,
                  assigned_to_id: createForm.assigned_to_id ? Number(createForm.assigned_to_id) : undefined,
                  due_date: createForm.due_date,
                  priority: createForm.priority,
                });
              }}
              className="p-5 space-y-4 text-xs"
            >
              <div>
                <label className="block text-slate-300 font-semibold mb-1">Request Title *</label>
                <input
                  type="text"
                  required
                  value={createForm.title}
                  onChange={(e) => setCreateForm({ ...createForm, title: e.target.value })}
                  placeholder="e.g. Q1 Okta MFA Configuration Screenshot"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200 focus:outline-hidden focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Description / Request Criteria *</label>
                <textarea
                  required
                  rows={3}
                  value={createForm.description}
                  onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                  placeholder="Provide explicit instructions for the auditee on what evidence is expected..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200 focus:outline-hidden focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">In-Scope Control *</label>
                  <select
                    required
                    value={createForm.organization_control_id}
                    onChange={(e) =>
                      setCreateForm({
                        ...createForm,
                        organization_control_id: e.target.value ? Number(e.target.value) : '',
                      })
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200 focus:outline-hidden focus:border-indigo-500"
                  >
                    <option value="">Select Control</option>
                    {scopeControls.map((sc) => (
                      <option key={sc.id} value={sc.organization_control_id}>
                        {sc.organization_control?.subcategory?.identifier || `Control #${sc.organization_control_id}`} -{' '}
                        {sc.organization_control?.subcategory?.title || 'Scope Control'}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Priority</label>
                  <select
                    value={createForm.priority}
                    onChange={(e) => setCreateForm({ ...createForm, priority: e.target.value as PBCPriority })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200 focus:outline-hidden focus:border-indigo-500"
                  >
                    <option value="LOW">LOW</option>
                    <option value="MEDIUM">MEDIUM</option>
                    <option value="HIGH">HIGH</option>
                    <option value="CRITICAL">CRITICAL</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Assigned Auditee</label>
                  <select
                    value={createForm.assigned_to_id}
                    onChange={(e) =>
                      setCreateForm({
                        ...createForm,
                        assigned_to_id: e.target.value ? Number(e.target.value) : '',
                      })
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200 focus:outline-hidden focus:border-indigo-500"
                  >
                    <option value="">Unassigned</option>
                    {allUsers.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.full_name || u.email} ({u.role})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Due Date *</label>
                  <input
                    type="date"
                    required
                    value={createForm.due_date}
                    onChange={(e) => setCreateForm({ ...createForm, due_date: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200 focus:outline-hidden focus:border-indigo-500"
                  >
                  </input>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                  className="px-3 py-1.5 rounded-lg border border-slate-700 text-slate-300 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium disabled:opacity-50"
                >
                  {createMutation.isPending ? 'Issuing...' : 'Issue PBC Request'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: FULFILL PBC REQUEST */}
      {selectedPbcForFulfill && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl">
            <div className="flex justify-between items-center px-5 py-4 border-b border-slate-800 bg-slate-950">
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <Send size={16} className="text-indigo-400" /> Fulfill PBC Request: {selectedPbcForFulfill.request_identifier}
              </h3>
              <button
                onClick={() => setSelectedPbcForFulfill(null)}
                className="text-slate-400 hover:text-slate-200"
              >
                <X size={16} />
              </button>
            </div>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (!fulfillForm.evidence_id) {
                  setActionError('Must select an authoritative evidence item.');
                  return;
                }
                fulfillMutation.mutate({
                  pbcId: selectedPbcForFulfill.id,
                  payload: {
                    evidence_id: Number(fulfillForm.evidence_id),
                    submission_notes: fulfillForm.submission_notes,
                  },
                });
              }}
              className="p-5 space-y-4 text-xs"
            >
              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-slate-400 space-y-1">
                <div className="text-slate-200 font-semibold">{selectedPbcForFulfill.title}</div>
                <div>{selectedPbcForFulfill.description}</div>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Select Evidence Artifact *</label>
                <select
                  required
                  value={fulfillForm.evidence_id}
                  onChange={(e) =>
                    setFulfillForm({
                      ...fulfillForm,
                      evidence_id: e.target.value ? Number(e.target.value) : '',
                    })
                  }
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200 focus:outline-hidden focus:border-indigo-500"
                >
                  <option value="">Select Authoritative Evidence</option>
                  {evidenceItems.map((ev: any) => (
                    <option key={ev.id} value={ev.id}>
                      #{ev.id} - {ev.title || ev.original_filename} ({ev.status})
                    </option>
                  ))}
                </select>
                <p className="text-[11px] text-slate-500 mt-1">
                  Binds to Phase 3 authoritative EvidenceItem record.
                </p>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Submission Notes</label>
                <textarea
                  rows={3}
                  value={fulfillForm.submission_notes}
                  onChange={(e) => setFulfillForm({ ...fulfillForm, submission_notes: e.target.value })}
                  placeholder="Notes explaining how this evidence satisfies the auditor's request..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200 focus:outline-hidden focus:border-indigo-500"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setSelectedPbcForFulfill(null)}
                  className="px-3 py-1.5 rounded-lg border border-slate-700 text-slate-300 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={fulfillMutation.isPending}
                  className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium disabled:opacity-50"
                >
                  {fulfillMutation.isPending ? 'Submitting...' : 'Submit Evidence'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: REVIEW PBC REQUEST */}
      {selectedPbcForReview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl">
            <div className="flex justify-between items-center px-5 py-4 border-b border-slate-800 bg-slate-950">
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <FileCheck size={16} className="text-purple-400" /> Auditor Review: {selectedPbcForReview.request_identifier}
              </h3>
              <button
                onClick={() => setSelectedPbcForReview(null)}
                className="text-slate-400 hover:text-slate-200"
              >
                <X size={16} />
              </button>
            </div>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (reviewForm.decision === 'REJECT' && (!reviewForm.rejection_reason || reviewForm.rejection_reason.trim().length < 5)) {
                  setActionError('A detailed rejection reason (minimum 5 characters) is required when rejecting.');
                  return;
                }
                reviewMutation.mutate({
                  pbcId: selectedPbcForReview.id,
                  payload: {
                    decision: reviewForm.decision,
                    review_notes: reviewForm.review_notes,
                    rejection_reason: reviewForm.rejection_reason,
                  },
                });
              }}
              className="p-5 space-y-4 text-xs"
            >
              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-1">
                <div className="text-slate-200 font-semibold">{selectedPbcForReview.title}</div>
                <div className="text-slate-400 text-[11px]">{selectedPbcForReview.submission_notes || 'No submission notes provided.'}</div>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Review Decision *</label>
                <div className="grid grid-cols-2 gap-3">
                  <label
                    className={`flex items-center gap-2 p-2.5 rounded-lg border cursor-pointer transition-colors ${
                      reviewForm.decision === 'ACCEPT'
                        ? 'bg-emerald-950/40 border-emerald-500 text-emerald-300'
                        : 'bg-slate-950 border-slate-800 text-slate-400'
                    }`}
                  >
                    <input
                      type="radio"
                      name="decision"
                      value="ACCEPT"
                      checked={reviewForm.decision === 'ACCEPT'}
                      onChange={() => setReviewForm({ ...reviewForm, decision: 'ACCEPT' })}
                      className="hidden"
                    />
                    <CheckCircle2 size={16} /> Accept Evidence
                  </label>
                  <label
                    className={`flex items-center gap-2 p-2.5 rounded-lg border cursor-pointer transition-colors ${
                      reviewForm.decision === 'REJECT'
                        ? 'bg-rose-950/40 border-rose-500 text-rose-300'
                        : 'bg-slate-950 border-slate-800 text-slate-400'
                    }`}
                  >
                    <input
                      type="radio"
                      name="decision"
                      value="REJECT"
                      checked={reviewForm.decision === 'REJECT'}
                      onChange={() => setReviewForm({ ...reviewForm, decision: 'REJECT' })}
                      className="hidden"
                    />
                    <XCircle size={16} /> Request Changes
                  </label>
                </div>
              </div>

              {reviewForm.decision === 'REJECT' && (
                <div>
                  <label className="block text-rose-300 font-semibold mb-1">Rejection Reason *</label>
                  <textarea
                    required
                    rows={3}
                    value={reviewForm.rejection_reason}
                    onChange={(e) => setReviewForm({ ...reviewForm, rejection_reason: e.target.value })}
                    placeholder="Describe why the evidence does not satisfy the request..."
                    className="w-full bg-slate-950 border border-rose-800/80 rounded-lg p-2.5 text-slate-200 focus:outline-hidden focus:border-rose-500"
                  />
                </div>
              )}

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Review Notes</label>
                <textarea
                  rows={2}
                  value={reviewForm.review_notes}
                  onChange={(e) => setReviewForm({ ...reviewForm, review_notes: e.target.value })}
                  placeholder="Internal notes regarding evidence verification..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200 focus:outline-hidden focus:border-indigo-500"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setSelectedPbcForReview(null)}
                  className="px-3 py-1.5 rounded-lg border border-slate-700 text-slate-300 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={reviewMutation.isPending}
                  className="px-4 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-medium disabled:opacity-50"
                >
                  {reviewMutation.isPending ? 'Submitting...' : 'Complete Review'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
