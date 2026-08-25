import React, { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  CheckCircle2,
  XCircle,
  Plus,
  Trash2,
  ShieldCheck,
  FileText,
  UserCheck,
  Calendar,
  AlertTriangle,
} from 'lucide-react';
import { api } from '../lib/api';
import { exceptionService } from '../lib/exceptionService';
import type { OrganizationControl } from '../types';

export const ExceptionDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const exceptionId = parseInt(id || '0', 10);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [isApproveModalOpen, setIsApproveModalOpen] = useState(false);
  const [approvalNotes, setApprovalNotes] = useState('');

  const [isRejectModalOpen, setIsRejectModalOpen] = useState(false);
  const [rejectionReason, setRejectionReason] = useState('');

  const [isCloseModalOpen, setIsCloseModalOpen] = useState(false);
  const [closureNotes, setClosureNotes] = useState('');

  const [isLinkControlOpen, setIsLinkControlOpen] = useState(false);
  const [selectedControlId, setSelectedControlId] = useState<number | ''>('');
  const [compControlNotes, setCompControlNotes] = useState('');

  const { data: exception, isLoading } = useQuery({
    queryKey: ['exception', exceptionId],
    queryFn: () => exceptionService.getException(exceptionId),
    enabled: !!exceptionId,
  });

  const { data: controls = [] } = useQuery({
    queryKey: ['controls'],
    queryFn: async () => {
      const res = await api.get<OrganizationControl[]>('/api/v1/controls');
      return res.data;
    },
  });

  const submitReviewMutation = useMutation({
    mutationFn: () => exceptionService.submitForReview(exceptionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exception', exceptionId] });
      queryClient.invalidateQueries({ queryKey: ['exceptions'] });
      queryClient.invalidateQueries({ queryKey: ['exceptionStats'] });
    },
  });

  const approveMutation = useMutation({
    mutationFn: () => exceptionService.approveException(exceptionId, approvalNotes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exception', exceptionId] });
      queryClient.invalidateQueries({ queryKey: ['exceptions'] });
      queryClient.invalidateQueries({ queryKey: ['exceptionStats'] });
      setIsApproveModalOpen(false);
    },
  });

  const rejectMutation = useMutation({
    mutationFn: () => exceptionService.rejectException(exceptionId, rejectionReason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exception', exceptionId] });
      queryClient.invalidateQueries({ queryKey: ['exceptions'] });
      queryClient.invalidateQueries({ queryKey: ['exceptionStats'] });
      setIsRejectModalOpen(false);
    },
  });

  const closeMutation = useMutation({
    mutationFn: () => exceptionService.closeException(exceptionId, closureNotes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exception', exceptionId] });
      queryClient.invalidateQueries({ queryKey: ['exceptions'] });
      queryClient.invalidateQueries({ queryKey: ['exceptionStats'] });
      setIsCloseModalOpen(false);
    },
  });

  const linkControlMutation = useMutation({
    mutationFn: () =>
      exceptionService.linkCompensatingControl(
        exceptionId,
        selectedControlId as number,
        compControlNotes
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exception', exceptionId] });
      setIsLinkControlOpen(false);
      setSelectedControlId('');
      setCompControlNotes('');
    },
  });

  const unlinkControlMutation = useMutation({
    mutationFn: (controlId: number) =>
      exceptionService.unlinkCompensatingControl(exceptionId, controlId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exception', exceptionId] });
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-500">
        Loading security exception details...
      </div>
    );
  }

  if (!exception) {
    return (
      <div className="text-center py-16">
        <h2 className="text-xl font-bold text-slate-200">Exception Not Found</h2>
        <button
          onClick={() => navigate('/exceptions')}
          className="mt-4 px-4 py-2 bg-amber-600 text-white rounded-lg"
        >
          Back to Exceptions
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link
            to="/exceptions"
            className="p-2 bg-slate-900 border border-slate-800 rounded-lg text-slate-400 hover:text-slate-200 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-amber-400">EXC-{exception.id}</span>
              <span className="text-slate-500">•</span>
              <span className="text-xs text-slate-400">
                {exception.exception_type.replace('_', ' ')}
              </span>
            </div>
            <h1 className="text-2xl font-bold text-slate-100 mt-1">{exception.title}</h1>
          </div>
        </div>

        {/* Workflow Action Bar */}
        <div className="flex flex-wrap items-center gap-2">
          {exception.status === 'REQUESTED' && (
            <button
              onClick={() => submitReviewMutation.mutate()}
              disabled={submitReviewMutation.isPending}
              className="px-3 py-1.5 bg-yellow-600 hover:bg-yellow-500 text-white text-xs font-medium rounded-lg transition-colors cursor-pointer"
            >
              Submit for Review
            </button>
          )}

          {(exception.status === 'REQUESTED' || exception.status === 'UNDER_REVIEW') && (
            <>
              <button
                onClick={() => setIsApproveModalOpen(true)}
                className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded-lg transition-colors cursor-pointer"
              >
                Approve Exception
              </button>
              <button
                onClick={() => setIsRejectModalOpen(true)}
                className="px-3 py-1.5 bg-red-600 hover:bg-red-500 text-white text-xs font-medium rounded-lg transition-colors cursor-pointer"
              >
                Reject Exception
              </button>
            </>
          )}

          {exception.status !== 'CLOSED' && exception.status !== 'REJECTED' && (
            <button
              onClick={() => setIsCloseModalOpen(true)}
              className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 text-xs font-medium rounded-lg transition-colors cursor-pointer"
            >
              Close Exception
            </button>
          )}
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Details & Compensating Controls */}
        <div className="lg:col-span-2 space-y-6">
          {/* Description & Justification */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-4">
            <div>
              <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2 mb-2">
                <FileText className="w-4 h-4 text-amber-400" />
                Scope &amp; Description
              </h2>
              <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">
                {exception.description}
              </p>
            </div>

            <div className="pt-3 border-t border-slate-800">
              <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2 mb-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                Business &amp; Technical Justification
              </h2>
              <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap p-3 bg-slate-950 rounded-lg border border-slate-800/80">
                {exception.justification}
              </p>
            </div>
          </div>

          {/* Compensating Controls Section */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-slate-100 flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                Compensating Controls ({exception.compensating_controls?.length ?? 0})
              </h2>
              {exception.status !== 'CLOSED' && exception.status !== 'REJECTED' && (
                <button
                  onClick={() => setIsLinkControlOpen(true)}
                  className="flex items-center gap-1 text-xs text-amber-400 hover:text-amber-300 transition-colors cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Add Compensating Control
                </button>
              )}
            </div>

            {(!exception.compensating_controls ||
              exception.compensating_controls.length === 0) ? (
              <p className="text-xs text-slate-500 italic py-2">
                No compensating controls linked to this deviation. Adding compensating controls reduces residual risk.
              </p>
            ) : (
              <div className="divide-y divide-slate-800/60">
                {exception.compensating_controls.map((comp) => (
                  <div key={comp.id} className="py-3 space-y-1 text-xs">
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="font-mono text-indigo-400 font-medium mr-2">
                          {comp.organization_control?.subcategory?.identifier}
                        </span>
                        <span className="text-slate-200 font-medium">
                          {comp.organization_control?.subcategory?.title}
                        </span>
                      </div>
                      {exception.status !== 'CLOSED' && (
                        <button
                          onClick={() =>
                            unlinkControlMutation.mutate(comp.organization_control_id)
                          }
                          className="text-slate-500 hover:text-red-400 transition-colors p-1"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                    {comp.implementation_notes && (
                      <p className="text-slate-400 text-[11px] pl-2 border-l-2 border-slate-700">
                        {comp.implementation_notes}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Review & Decision Notes */}
          {(exception.approval_notes || exception.rejection_reason || exception.closure_notes) && (
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-3">
              <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                <UserCheck className="w-4 h-4 text-indigo-400" />
                Review &amp; Lifecycle Notes
              </h2>

              {exception.approval_notes && (
                <div className="p-3 bg-emerald-950/20 border border-emerald-800/40 rounded-lg text-xs space-y-1">
                  <span className="font-semibold text-emerald-400 block">Approval Notes:</span>
                  <p className="text-emerald-200">{exception.approval_notes}</p>
                </div>
              )}

              {exception.rejection_reason && (
                <div className="p-3 bg-red-950/20 border border-red-800/40 rounded-lg text-xs space-y-1">
                  <span className="font-semibold text-red-400 block">Rejection Reason:</span>
                  <p className="text-red-200">{exception.rejection_reason}</p>
                </div>
              )}

              {exception.closure_notes && (
                <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg text-xs space-y-1">
                  <span className="font-semibold text-slate-300 block">Closure Notes:</span>
                  <p className="text-slate-400">{exception.closure_notes}</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right 1 Col: Metadata & Governance Window */}
        <div className="space-y-6">
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-4">
            <h2 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
              <Calendar className="w-4 h-4 text-amber-400" />
              Governance &amp; Timeline
            </h2>

            <div className="space-y-3 text-xs">
              <div className="flex justify-between py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400">Effective Status</span>
                <span className="font-bold text-emerald-400">{exception.effective_status}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400">Workflow Status</span>
                <span className="font-semibold text-slate-200">{exception.status}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400">Residual Risk Level</span>
                <span className="font-semibold text-amber-400">{exception.residual_risk_level}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400">Effective Date</span>
                <span className="text-slate-200">{exception.effective_date || '--'}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400">Expiration Date</span>
                <span className="font-bold text-red-400">{exception.expiry_date}</span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-slate-400">Requested By</span>
                <span className="text-slate-200">{exception.requested_by?.full_name || '--'}</span>
              </div>
              {exception.reviewer && (
                <div className="flex justify-between py-1.5">
                  <span className="text-slate-400">Approved By</span>
                  <span className="text-slate-200">{exception.reviewer.full_name}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Approval Modal */}
      {isApproveModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <h2 className="text-lg font-bold text-emerald-400 flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5" />
              Approve Security Exception
            </h2>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                approveMutation.mutate();
              }}
              className="space-y-4"
            >
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Approval Notes / Required Conditions (Optional)
                </label>
                <textarea
                  rows={3}
                  value={approvalNotes}
                  onChange={(e) => setApprovalNotes(e.target.value)}
                  placeholder="e.g. Approved contingent on biometric 2FA for emergency access console."
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsApproveModalOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium rounded-lg transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={approveMutation.isPending}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded-lg transition-colors cursor-pointer disabled:opacity-50"
                >
                  {approveMutation.isPending ? 'Approving...' : 'Confirm Approval'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Reject Modal */}
      {isRejectModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <h2 className="text-lg font-bold text-red-400 flex items-center gap-2">
              <XCircle className="w-5 h-5" />
              Reject Security Exception
            </h2>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                rejectMutation.mutate();
              }}
              className="space-y-4"
            >
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Reason for Rejection *
                </label>
                <textarea
                  required
                  rows={3}
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  placeholder="Detail why this deviation cannot be approved..."
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-red-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsRejectModalOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium rounded-lg transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={rejectMutation.isPending || !rejectionReason}
                  className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white text-sm font-medium rounded-lg transition-colors cursor-pointer disabled:opacity-50"
                >
                  {rejectMutation.isPending ? 'Rejecting...' : 'Confirm Rejection'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Close Modal */}
      {isCloseModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <h2 className="text-lg font-bold text-slate-200 flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-indigo-400" />
              Close Exception
            </h2>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                closeMutation.mutate();
              }}
              className="space-y-4"
            >
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Closure Summary / Resolution *
                </label>
                <textarea
                  required
                  rows={3}
                  value={closureNotes}
                  onChange={(e) => setClosureNotes(e.target.value)}
                  placeholder="e.g. Server permanently decommissioned, exception no longer required."
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-slate-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsCloseModalOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium rounded-lg transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={closeMutation.isPending || !closureNotes}
                  className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white text-sm font-medium rounded-lg transition-colors cursor-pointer disabled:opacity-50"
                >
                  {closeMutation.isPending ? 'Closing...' : 'Close Exception'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Compensating Control Modal */}
      {isLinkControlOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-emerald-400" />
              Add Compensating Control
            </h2>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (selectedControlId) {
                  linkControlMutation.mutate();
                }
              }}
              className="space-y-4"
            >
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Select Control *
                </label>
                <select
                  required
                  value={selectedControlId}
                  onChange={(e) => setSelectedControlId(parseInt(e.target.value, 10))}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-amber-500"
                >
                  <option value="">Choose a control...</option>
                  {controls.map((ctrl: OrganizationControl) => (
                    <option key={ctrl.id} value={ctrl.id}>
                      {ctrl.subcategory?.identifier} - {ctrl.subcategory?.title}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Implementation Notes
                </label>
                <textarea
                  rows={2}
                  value={compControlNotes}
                  onChange={(e) => setCompControlNotes(e.target.value)}
                  placeholder="How this compensating control mitigates deviation risk..."
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-amber-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsLinkControlOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium rounded-lg transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!selectedControlId || linkControlMutation.isPending}
                  className="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white text-sm font-medium rounded-lg transition-colors cursor-pointer disabled:opacity-50"
                >
                  {linkControlMutation.isPending ? 'Linking...' : 'Link Control'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
