import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { supplyChainService } from '../../lib/supplyChainService';
import type { SupplyChainApprovalStatus, SupplyChainExemption } from '../../types';
import { AlertCircle, CheckCircle, RefreshCw, XCircle, ShieldAlert } from 'lucide-react';

interface SupplyChainApprovalModalProps {
  isOpen: boolean;
  onClose: () => void;
  exemption: SupplyChainExemption | null;
  onSuccess: () => void;
}

export const SupplyChainApprovalModal: React.FC<SupplyChainApprovalModalProps> = ({
  isOpen,
  onClose,
  exemption,
  onSuccess,
}) => {
  const [decision, setDecision] = useState<SupplyChainApprovalStatus>('APPROVED');
  const [reviewerNotes, setReviewerNotes] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: async () => {
      if (!exemption) throw new Error('No exemption selected.');
      return supplyChainService.reviewExemption(exemption.id, {
        decision,
        reviewer_notes: reviewerNotes.trim(),
      });
    },
    onSuccess: () => {
      onSuccess();
      onClose();
    },
    onError: (err: any) => {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to submit exemption review decision.';
      setErrorMsg(typeof msg === 'string' ? msg : JSON.stringify(msg));
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!reviewerNotes.trim() || reviewerNotes.trim().length < 5) {
      setErrorMsg('Mandatory audit review commentary must be at least 5 characters.');
      return;
    }
    setErrorMsg(null);
    mutation.mutate();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Four-Eyes Exemption Review: ${exemption?.exemption_code || ''}`}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {errorMsg && (
          <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg flex items-start gap-2.5 text-xs text-rose-400">
            <AlertCircle size={16} className="shrink-0 mt-0.5" />
            <span>{errorMsg}</span>
          </div>
        )}

        <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg space-y-2 text-xs">
          <div className="flex justify-between items-center text-slate-400">
            <span>Requested By:</span>
            <span className="font-semibold text-slate-200">{exemption?.requested_by?.full_name || `User #${exemption?.requested_by_id}`}</span>
          </div>
          <div className="flex justify-between items-center text-slate-400">
            <span>Target:</span>
            <span className="font-mono text-indigo-400">
              {exemption?.component_id ? `Component #${exemption.component_id}` : `Product #${exemption?.software_product_id}`}
            </span>
          </div>
          <div className="pt-1 border-t border-slate-800 text-slate-300">
            <span className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-0.5">Reason:</span>
            <p className="italic text-slate-300 bg-slate-900/50 p-2 rounded">{exemption?.reason}</p>
          </div>
          <div className="text-slate-300">
            <span className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-0.5">Compensating Controls:</span>
            <p className="text-slate-300 bg-slate-900/50 p-2 rounded">{exemption?.compensating_controls}</p>
          </div>
        </div>

        <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg text-xs text-amber-300 flex items-start gap-2">
          <ShieldAlert size={16} className="shrink-0 mt-0.5 text-amber-400" />
          <span>
            Segregation of Duties (Four-Eyes SoD): Self-review is strictly rejected. Completed review decisions are permanently immutable.
          </span>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-300 mb-2">Review Decision</label>
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setDecision('APPROVED')}
              className={`p-2.5 rounded-lg border text-xs font-semibold flex items-center justify-center gap-2 transition-colors ${
                decision === 'APPROVED'
                  ? 'bg-emerald-500/20 border-emerald-500 text-emerald-300'
                  : 'bg-slate-900 border-slate-700 text-slate-400 hover:border-slate-600'
              }`}
            >
              <CheckCircle size={15} />
              <span>Approve Exemption</span>
            </button>

            <button
              type="button"
              onClick={() => setDecision('REJECTED')}
              className={`p-2.5 rounded-lg border text-xs font-semibold flex items-center justify-center gap-2 transition-colors ${
                decision === 'REJECTED'
                  ? 'bg-rose-500/20 border-rose-500 text-rose-300'
                  : 'bg-slate-900 border-slate-700 text-slate-400 hover:border-slate-600'
              }`}
            >
              <XCircle size={15} />
              <span>Reject Exemption</span>
            </button>
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">
            Mandatory Reviewer Audit Notes <span className="text-rose-400">*</span>
          </label>
          <textarea
            rows={3}
            placeholder="Document risk acceptance evaluation, compensatory control adequacy, or rejection grounds..."
            value={reviewerNotes}
            onChange={(e) => setReviewerNotes(e.target.value)}
            className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
          />
        </div>

        <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
          <Button type="button" variant="outline" size="sm" onClick={onClose} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button
            type="submit"
            size="sm"
            disabled={mutation.isPending}
            className={`flex items-center gap-1.5 ${
              decision === 'APPROVED' ? 'bg-emerald-600 hover:bg-emerald-500 text-white' : 'bg-rose-600 hover:bg-rose-500 text-white'
            }`}
          >
            {mutation.isPending && <RefreshCw size={14} className="animate-spin" />}
            <span>{decision === 'APPROVED' ? 'Confirm Approval' : 'Confirm Rejection'}</span>
          </Button>
        </div>
      </form>
    </Modal>
  );
};
