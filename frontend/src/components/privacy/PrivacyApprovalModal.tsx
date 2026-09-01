import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useAuth } from '../../context/AuthContext';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { privacyService } from '../../lib/privacyService';
import type { PrivacyApprovalStatus } from '../../types';
import {
  AlertCircle,
  AlertOctagon,
  CheckCircle2,
  Lock,
  RefreshCw,
  XCircle,
} from 'lucide-react';

interface PrivacyApprovalModalProps {
  isOpen: boolean;
  onClose: () => void;
  targetType: 'DPIA' | 'TRANSFER';
  targetId: number;
  targetCode: string;
  creatorOrRequesterId: number;
  currentStatus: PrivacyApprovalStatus;
  onSuccess: () => void;
}

export const PrivacyApprovalModal: React.FC<PrivacyApprovalModalProps> = ({
  isOpen,
  onClose,
  targetType,
  targetId,
  targetCode,
  creatorOrRequesterId,
  currentStatus,
  onSuccess,
}) => {
  const { user, hasRole } = useAuth();
  const [decision, setDecision] = useState<PrivacyApprovalStatus>('APPROVED');
  const [notes, setNotes] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const isCreatorOrRequester = user ? user.id === creatorOrRequesterId : false;
  const isFinalized = currentStatus !== 'PENDING';
  const canApproveRole = hasRole('ADMIN', 'MANAGER');

  const mutation = useMutation({
    mutationFn: async () => {
      if (notes.trim().length < 5) {
        throw new Error('Review notes must be at least 5 characters long');
      }

      if (targetType === 'DPIA') {
        return privacyService.reviewDPIA(targetId, {
          decision,
          recommendation_notes: notes.trim(),
        });
      } else {
        return privacyService.reviewDataTransfer(targetId, {
          decision,
          reviewer_notes: notes.trim(),
        });
      }
    },
    onSuccess: () => {
      setErrorMsg(null);
      setNotes('');
      onSuccess();
      onClose();
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || err.message || 'Failed to submit review decision';
      setErrorMsg(msg);
    },
  });

  const title =
    targetType === 'DPIA'
      ? `DPO Consultation Review: ${targetCode}`
      : `Transfer Governance Review: ${targetCode}`;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title}>
      <div className="space-y-4">
        {/* Status Header */}
        <div className="p-3.5 rounded-lg bg-slate-950/70 border border-slate-800 flex items-center justify-between">
          <div>
            <div className="text-[11px] text-slate-400 font-medium">ASSESSMENT IDENTIFIER</div>
            <div className="text-sm font-semibold text-slate-200 mt-0.5">{targetCode}</div>
          </div>
          <Badge
            variant={
              currentStatus === 'APPROVED'
                ? 'success'
                : currentStatus === 'REJECTED'
                ? 'danger'
                : 'warning'
            }
          >
            {currentStatus}
          </Badge>
        </div>

        {/* Four-Eyes SoD Violation Warning */}
        {isCreatorOrRequester && (
          <div className="p-3 rounded-lg bg-amber-950/40 border border-amber-800/60 flex items-start gap-2.5">
            <AlertOctagon size={18} className="text-amber-400 shrink-0 mt-0.5" />
            <div className="text-xs text-amber-200">
              <strong>Segregation of Duties (Four-Eyes Principle) Enforced:</strong> You created or requested this assessment (User #{creatorOrRequesterId}). Privacy governance policy strictly prohibits self-review. An independent DPO or Compliance Manager must conduct this review.
            </div>
          </div>
        )}

        {/* Finalized Record Warning */}
        {isFinalized && (
          <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex items-start gap-2.5">
            <Lock size={16} className="text-slate-400 shrink-0 mt-0.5" />
            <div className="text-xs text-slate-400">
              This assessment has already reached finalized status (<strong>{currentStatus}</strong>). Replaying review decisions on finalized assessments is blocked by the backend.
            </div>
          </div>
        )}

        {/* Review Form */}
        {!isCreatorOrRequester && !isFinalized && canApproveRole && (
          <>
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Governance Decision
              </label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setDecision('APPROVED')}
                  className={`p-2.5 rounded-lg border text-xs font-medium flex items-center justify-center gap-2 cursor-pointer transition-all ${
                    decision === 'APPROVED'
                      ? 'bg-emerald-950/50 border-emerald-500 text-emerald-300 ring-1 ring-emerald-500'
                      : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                  }`}
                >
                  <CheckCircle2 size={16} />
                  <span>APPROVE</span>
                </button>
                <button
                  type="button"
                  onClick={() => setDecision('REJECTED')}
                  className={`p-2.5 rounded-lg border text-xs font-medium flex items-center justify-center gap-2 cursor-pointer transition-all ${
                    decision === 'REJECTED'
                      ? 'bg-rose-950/50 border-rose-500 text-rose-300 ring-1 ring-rose-500'
                      : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                  }`}
                >
                  <XCircle size={16} />
                  <span>REJECT</span>
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Reviewer Commentary &amp; Safeguard Recommendations{' '}
                <span className="text-rose-400">*</span>
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
                placeholder="Enter mandatory audit commentary (minimum 5 characters)..."
                className="w-full bg-slate-950 border border-slate-800 rounded-md p-2.5 text-xs text-slate-200 focus:outline-hidden focus:border-indigo-500 placeholder:text-slate-600"
              />
              <div className="text-[10px] text-slate-500 mt-1">
                Commentary is cryptographically associated with your authenticated identity in the audit log.
              </div>
            </div>
          </>
        )}

        {/* Error message */}
        {errorMsg && (
          <div className="p-3 rounded-lg bg-rose-950/50 border border-rose-800/80 flex items-start gap-2 text-xs text-rose-300">
            <AlertCircle size={15} className="shrink-0 mt-0.5" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
          <Button variant="ghost" onClick={onClose} disabled={mutation.isPending}>
            Close
          </Button>
          {!isCreatorOrRequester && !isFinalized && canApproveRole && (
            <Button
              variant={decision === 'APPROVED' ? 'primary' : 'danger'}
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending || notes.trim().length < 5}
              className="flex items-center gap-1.5"
            >
              {mutation.isPending && <RefreshCw size={14} className="animate-spin" />}
              <span>Submit Review</span>
            </Button>
          )}
        </div>
      </div>
    </Modal>
  );
};
