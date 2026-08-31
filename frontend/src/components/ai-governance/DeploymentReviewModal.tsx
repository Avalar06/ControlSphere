import React, { useState, useEffect } from 'react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { useAuth } from '../../context/AuthContext';
import type {
  AIDeploymentApproval,
  AIDeploymentApprovalReviewRequest,
} from '../../types';
import { AlertTriangle, CheckCircle2, ShieldAlert, XCircle } from 'lucide-react';

interface DeploymentReviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  approval: AIDeploymentApproval | null;
  systemCode?: string;
  onSubmit: (
    approvalId: number,
    data: AIDeploymentApprovalReviewRequest
  ) => Promise<void>;
  isSubmitting?: boolean;
}

export const DeploymentReviewModal: React.FC<DeploymentReviewModalProps> = ({
  isOpen,
  onClose,
  approval,
  systemCode,
  onSubmit,
  isSubmitting = false,
}) => {
  const { user } = useAuth();

  const [decision, setDecision] = useState<'APPROVED' | 'REJECTED'>('APPROVED');
  const [reviewerNotes, setReviewerNotes] = useState('');
  const [error, setError] = useState<string | null>(null);

  // Four-Eyes SoD check
  const isRequester = !!(user && approval && user.id === approval.requested_by_id);

  useEffect(() => {
    if (isOpen) {
      setDecision('APPROVED');
      setReviewerNotes('');
      setError(null);
    }
  }, [isOpen, approval]);

  if (!approval) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (isRequester) {
      setError(
        'Segregation of Duties Violation: You cannot review or approve a deployment you requested.'
      );
      return;
    }

    try {
      await onSubmit(approval.id, {
        decision,
        reviewer_notes: reviewerNotes.trim() || null,
      });
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          'Failed to record review decision.'
      );
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Review Deployment Gate: ${systemCode || ''} (${approval.target_environment})`}
    >
      <form onSubmit={handleSubmit} className="space-y-4 max-h-[75vh] overflow-y-auto pr-1">
        {error && (
          <div className="p-3 bg-rose-950/80 border border-rose-800 rounded-md flex items-start gap-2.5 text-xs text-rose-200">
            <AlertTriangle size={16} className="text-rose-400 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {isRequester && (
          <div className="p-3 bg-amber-950/90 border border-amber-800 rounded-md flex items-start gap-2.5 text-xs text-amber-200">
            <ShieldAlert size={16} className="text-amber-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold block">Segregation of Duties Enforcement</span>
              You submitted this deployment request. Enterprise Four-Eyes governance requires an independent authorized reviewer to evaluate and approve this release gate.
            </div>
          </div>
        )}

        {/* Request Context Summary */}
        <div className="p-3 bg-slate-950 border border-slate-800 rounded-md space-y-2 text-xs">
          <div className="flex items-center justify-between text-slate-400">
            <span>Target Environment:</span>
            <span className="font-bold text-slate-200 font-mono">
              {approval.target_environment}
            </span>
          </div>
          <div className="flex items-center justify-between text-slate-400">
            <span>Requested By:</span>
            <span className="text-slate-200">
              {approval.requested_by?.email || `User #${approval.requested_by_id}`}
            </span>
          </div>
          <div className="flex items-center justify-between text-slate-400">
            <span>Requested At:</span>
            <span className="text-slate-200 font-mono">
              {new Date(approval.created_at).toLocaleString()}
            </span>
          </div>

          <div className="pt-2 border-t border-slate-800/80">
            <span className="text-slate-400 block font-semibold mb-0.5">
              Risk Acceptance Justification:
            </span>
            <p className="text-slate-300 italic bg-slate-900 p-2 rounded text-[11px]">
              "{approval.risk_acceptance_justification}"
            </p>
          </div>

          <div className="pt-1">
            <span className="text-slate-400 block font-semibold mb-0.5">
              Human Oversight Measures (HITL):
            </span>
            <p className="text-slate-300 italic bg-slate-900 p-2 rounded text-[11px]">
              "{approval.human_oversight_measures}"
            </p>
          </div>
        </div>

        {/* Decision Selection */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-2">
            Governance Decision <span className="text-rose-400">*</span>
          </label>
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              disabled={isRequester}
              onClick={() => setDecision('APPROVED')}
              className={`p-3 rounded-lg border text-xs font-semibold flex items-center justify-center gap-2 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${
                decision === 'APPROVED'
                  ? 'bg-emerald-950/70 border-emerald-500 text-emerald-300 shadow-xs'
                  : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
              }`}
            >
              <CheckCircle2 size={16} className="text-emerald-400" />
              <span>APPROVE Deployment</span>
            </button>

            <button
              type="button"
              disabled={isRequester}
              onClick={() => setDecision('REJECTED')}
              className={`p-3 rounded-lg border text-xs font-semibold flex items-center justify-center gap-2 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${
                decision === 'REJECTED'
                  ? 'bg-rose-950/70 border-rose-500 text-rose-300 shadow-xs'
                  : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
              }`}
            >
              <XCircle size={16} className="text-rose-400" />
              <span>REJECT Request</span>
            </button>
          </div>
        </div>

        {/* Reviewer Notes */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1">
            Reviewer Audit Notes &amp; Rationale
          </label>
          <textarea
            rows={3}
            disabled={isRequester}
            value={reviewerNotes}
            onChange={(e) => setReviewerNotes(e.target.value)}
            placeholder="Record evaluation findings, conditions of release, or reason for rejection..."
            className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500 disabled:opacity-50"
          />
        </div>

        {/* Modal Actions */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
          <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant={decision === 'APPROVED' ? 'primary' : 'danger'}
            isLoading={isSubmitting}
            disabled={isRequester}
          >
            {decision === 'APPROVED' ? 'Confirm Approval' : 'Confirm Rejection'}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
