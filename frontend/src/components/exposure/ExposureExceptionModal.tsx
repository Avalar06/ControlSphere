import React, { useState, useEffect } from 'react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import type {
  ExposureException,
  ExposureExceptionCreate,
  ExposureExceptionReviewRequest,
  VulnerabilityExposure,
} from '../../types';
import { AlertTriangle, CheckCircle2, ShieldAlert, XCircle } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

interface ExposureExceptionModalProps {
  isOpen: boolean;
  onClose: () => void;
  exposure: VulnerabilityExposure | null;
  mode: 'request' | 'review';
  exceptionToReview?: ExposureException | null;
  onRequestSubmit?: (data: ExposureExceptionCreate) => Promise<void>;
  onReviewSubmit?: (exceptionId: number, data: ExposureExceptionReviewRequest) => Promise<void>;
  isSubmitting?: boolean;
}

export const ExposureExceptionModal: React.FC<ExposureExceptionModalProps> = ({
  isOpen,
  onClose,
  exposure,
  mode,
  exceptionToReview,
  onRequestSubmit,
  onReviewSubmit,
  isSubmitting = false,
}) => {
  const { user } = useAuth();

  // Request form state
  const [requestedSlaDate, setRequestedSlaDate] = useState('');
  const [justification, setJustification] = useState('');
  const [compensatingControls, setCompensatingControls] = useState('');

  // Review form state
  const [decision, setDecision] = useState<'APPROVED' | 'REJECTED'>('APPROVED');
  const [reviewNotes, setReviewNotes] = useState('');
  const [error, setError] = useState<string | null>(null);

  // Check Four-Eyes violation
  const isRequester = !!(
    user &&
    exceptionToReview &&
    exceptionToReview.requested_by_id === user.id
  );

  useEffect(() => {
    if (mode === 'request' && exposure?.remediation_sla_due) {
      // Default to current SLA + 30 days formatted as YYYY-MM-DD
      const current = new Date(exposure.remediation_sla_due);
      current.setDate(current.getDate() + 30);
      setRequestedSlaDate(current.toISOString().split('T')[0]);
      setJustification('');
      setCompensatingControls('');
    } else if (mode === 'review') {
      setDecision('APPROVED');
      setReviewNotes('');
    }
    setError(null);
  }, [exposure, exceptionToReview, mode, isOpen]);

  const handleRequestSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!requestedSlaDate) {
      setError('Please select a valid requested SLA extension date.');
      return;
    }
    if (!justification.trim() || justification.trim().length < 5) {
      setError('Business justification must be at least 5 characters.');
      return;
    }

    try {
      if (onRequestSubmit) {
        await onRequestSubmit({
          requested_sla_due: new Date(`${requestedSlaDate}T23:59:59Z`).toISOString(),
          justification: justification.trim(),
          compensating_controls: compensatingControls.trim() || null,
        });
      }
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to submit exception request.');
    }
  };

  const handleReviewSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (isRequester) {
      setError('Segregation of duties violation: Requesters cannot approve their own SLA exceptions.');
      return;
    }

    if (!exceptionToReview) return;

    try {
      if (onReviewSubmit) {
        await onReviewSubmit(exceptionToReview.id, {
          decision,
          review_notes: reviewNotes.trim() || null,
        });
      }
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to review exception.');
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        mode === 'request'
          ? `Request SLA Extension: ${exposure?.cve_id}`
          : `Review Exception Request #${exceptionToReview?.id}`
      }
    >
      {mode === 'request' ? (
        <form onSubmit={handleRequestSubmit} className="space-y-4">
          {error && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg flex items-center gap-2 text-xs text-rose-400">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-1 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Current Authoritative SLA:</span>
              <span className="font-mono font-bold text-rose-400">
                {exposure?.remediation_sla_due
                  ? new Date(exposure.remediation_sla_due).toLocaleDateString()
                  : 'N/A'}
              </span>
            </div>
            <p className="text-[11px] text-slate-500">
              Four-eyes governance rule: Extension requests must be independently approved by a Manager or Administrator.
            </p>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Requested Extension SLA Date <span className="text-rose-400">*</span>
            </label>
            <input
              type="date"
              required
              value={requestedSlaDate}
              onChange={(e) => setRequestedSlaDate(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500 font-mono"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Business Justification & Root Cause <span className="text-rose-400">*</span>
            </label>
            <textarea
              rows={3}
              required
              value={justification}
              onChange={(e) => setJustification(e.target.value)}
              placeholder="Explain why standard remediation SLA cannot be met (e.g. vendor patch timeline, scheduled maintenance window)..."
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 resize-none"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Compensating Controls & Mitigating Factors
            </label>
            <textarea
              rows={2}
              value={compensatingControls}
              onChange={(e) => setCompensatingControls(e.target.value)}
              placeholder="WAF rules, network segment isolation, rate limiting, or heightened monitoring..."
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 resize-none"
            />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
            <Button variant="outline" type="button" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Submitting...' : 'Submit Request'}
            </Button>
          </div>
        </form>
      ) : (
        <form onSubmit={handleReviewSubmit} className="space-y-4">
          {error && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg flex items-center gap-2 text-xs text-rose-400">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {isRequester && (
            <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg flex items-start gap-2.5 text-xs text-amber-300">
              <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Segregation of Duties Enforced</p>
                <p className="text-[11px] text-amber-300/80 mt-0.5">
                  You are the author of this SLA extension request. In accordance with four-eyes governance, you cannot approve your own exception. Another Manager or Admin must review.
                </p>
              </div>
            </div>
          )}

          <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-slate-400">Original SLA:</span>
              <span className="text-slate-200">
                {exceptionToReview?.original_sla_due
                  ? new Date(exceptionToReview.original_sla_due).toLocaleDateString()
                  : 'N/A'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Requested Extended SLA:</span>
              <span className="font-bold text-indigo-400">
                {exceptionToReview?.requested_sla_due
                  ? new Date(exceptionToReview.requested_sla_due).toLocaleDateString()
                  : 'N/A'}
              </span>
            </div>
            <div className="border-t border-slate-900 pt-2 space-y-1">
              <span className="text-slate-400">Justification:</span>
              <p className="text-slate-300 italic">{exceptionToReview?.justification}</p>
            </div>
            {exceptionToReview?.compensating_controls && (
              <div className="border-t border-slate-900 pt-2 space-y-1">
                <span className="text-slate-400">Compensating Controls:</span>
                <p className="text-emerald-400">{exceptionToReview.compensating_controls}</p>
              </div>
            )}
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Review Decision <span className="text-rose-400">*</span>
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setDecision('APPROVED')}
                className={`flex items-center justify-center gap-2 p-3 rounded-lg border text-xs font-bold transition-all ${
                  decision === 'APPROVED'
                    ? 'bg-emerald-950/40 border-emerald-500/60 text-emerald-400'
                    : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                }`}
              >
                <CheckCircle2 className="h-4 w-4" />
                Approve Deferral
              </button>
              <button
                type="button"
                onClick={() => setDecision('REJECTED')}
                className={`flex items-center justify-center gap-2 p-3 rounded-lg border text-xs font-bold transition-all ${
                  decision === 'REJECTED'
                    ? 'bg-rose-950/40 border-rose-500/60 text-rose-400'
                    : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                }`}
              >
                <XCircle className="h-4 w-4" />
                Reject Deferral
              </button>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Review Notes & Evaluation
            </label>
            <textarea
              rows={3}
              value={reviewNotes}
              onChange={(e) => setReviewNotes(e.target.value)}
              placeholder="Document review findings, risk committee notes, or mitigation validation..."
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 resize-none"
            />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
            <Button variant="outline" type="button" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button
              variant={decision === 'APPROVED' ? 'primary' : 'danger'}
              type="submit"
              disabled={isSubmitting || isRequester}
            >
              {isSubmitting ? 'Recording Decision...' : `Confirm ${decision}`}
            </Button>
          </div>
        </form>
      )}
    </Modal>
  );
};
