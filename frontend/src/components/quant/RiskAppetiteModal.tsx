import React, { useState } from 'react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { quantRiskService } from '../../lib/quantRiskService';
import type { FinancialRiskAppetiteCreate } from '../../types';
import { AlertTriangle, ShieldAlert, Sparkles } from 'lucide-react';

interface RiskAppetiteModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const RiskAppetiteModal: React.FC<RiskAppetiteModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [aleLimit, setAleLimit] = useState<number>(500000);
  const [var95Limit, setVar95Limit] = useState<number>(1500000);
  const [notes, setNotes] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (aleLimit < 0 || var95Limit < 0) {
      setErrorMsg('Financial appetite limits must be non-negative.');
      return;
    }
    if (var95Limit < aleLimit) {
      setErrorMsg('Tail loss limit (95% VaR) should typically be greater than or equal to Annual Expected Loss (ALE).');
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);

    try {
      const payload: FinancialRiskAppetiteCreate = {
        ale_limit: Number(aleLimit),
        var_95_limit: Number(var95Limit),
        notes: notes.trim() || undefined,
      };
      await quantRiskService.createRiskAppetite(payload);
      onSuccess();
      onClose();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setErrorMsg(typeof detail === 'string' ? detail : 'Failed to create risk appetite draft.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Draft New Financial Risk Appetite Policy"
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="flex items-start gap-3 p-3.5 bg-indigo-950/40 border border-indigo-800/60 rounded-lg text-xs text-indigo-200">
          <ShieldAlert className="h-4 w-4 text-indigo-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold text-indigo-100">Board Governance & Four-Eyes Approval:</span> Proposed risk appetite thresholds are created in <strong>DRAFT</strong> status.
            In accordance with four-eyes segregation of duties, the draft must be formally approved by an independent manager before superseding the active threshold.
          </div>
        </div>

        {errorMsg && (
          <div className="flex items-center gap-2 p-3 bg-rose-950/50 border border-rose-800 rounded-lg text-xs text-rose-300">
            <AlertTriangle className="h-4 w-4 shrink-0 text-rose-400" />
            <span>{errorMsg}</span>
          </div>
        )}

        <div>
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
            Maximum Annual Expected Loss Threshold (ALE Limit USD) *
          </label>
          <input
            type="number"
            required
            min={0}
            step={10000}
            value={aleLimit}
            onChange={(e) => setAleLimit(parseFloat(e.target.value) || 0)}
            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3.5 py-2 text-sm text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
          />
          <span className="text-[11px] text-slate-500 mt-1 block">
            Annual aggregate portfolio loss limit approved by the Risk Committee.
          </span>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
            Maximum 95% Value-at-Risk Tail Loss Threshold (95% VaR Limit USD) *
          </label>
          <input
            type="number"
            required
            min={0}
            step={25000}
            value={var95Limit}
            onChange={(e) => setVar95Limit(parseFloat(e.target.value) || 0)}
            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3.5 py-2 text-sm text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
          />
          <span className="text-[11px] text-slate-500 mt-1 block">
            Maximum acceptable 95th percentile catastrophic tail loss threshold.
          </span>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
            Policy Rational & Governance Notes (Optional)
          </label>
          <textarea
            rows={3}
            placeholder="e.g. Approved in Q3 Board Risk Oversight Committee meeting ref ROC-2026-Q3."
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3.5 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
          <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={isSubmitting}>
            <Sparkles className="h-4 w-4 mr-1.5" />
            {isSubmitting ? 'Submitting Draft...' : 'Propose Appetite Version'}
          </Button>
        </div>
      </form>
    </Modal>
  );
};