import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { resilienceService } from '../../lib/resilienceService';
import { useAuth } from '../../context/AuthContext';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import type { BusinessImpactAnalysis } from '../../types';
import { AlertTriangle, CheckCircle2, ShieldCheck, XCircle } from 'lucide-react';

interface BiaApprovalModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  bia: BusinessImpactAnalysis;
}

export const BiaApprovalModal: React.FC<BiaApprovalModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  bia,
}) => {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [notes, setNotes] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Four-Eyes Principle: Requester cannot approve their own BIA
  const isRequester = user ? user.id === bia.requested_by_id : false;

  const mutation = useMutation({
    mutationFn: async () => {
      return resilienceService.approveBia(bia.id, {
        notes: notes.trim() || undefined,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resilience-process', bia.process_id] });
      queryClient.invalidateQueries({ queryKey: ['resilience-process-bias', bia.process_id] });
      queryClient.invalidateQueries({ queryKey: ['resilience-processes'] });
      onSuccess();
      onClose();
    },
    onError: (error: any) => {
      const detail = error.response?.data?.detail;
      setErrorMessage(typeof detail === 'string' ? detail : 'Approval failed. Segregation of duties violation or invalid state.');
    },
  });

  const handleApprove = (e: React.FormEvent) => {
    e.preventDefault();
    if (isRequester) {
      setErrorMessage('Four-eyes governance violation: The requester cannot approve their own BIA.');
      return;
    }
    setErrorMessage(null);
    mutation.mutate();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Approve BIA Baseline — Version ${bia.version}`}
    >
      <form onSubmit={handleApprove} className="space-y-4">
        {errorMessage && (
          <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg flex items-center gap-2 text-xs text-rose-400">
            <XCircle className="h-4 w-4 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Four-Eyes Warning Banner if current user is requester */}
        {isRequester ? (
          <div className="p-3.5 bg-rose-500/10 border border-rose-500/40 rounded-lg flex items-start gap-3 text-xs text-rose-300">
            <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold text-rose-300 block mb-1">
                Segregation of Duties Enforcement (Four-Eyes Principle)
              </span>
              You drafted this BIA record (Requester ID: #{bia.requested_by_id}). Platform governance requires an independent, secondary Manager or Administrator to review and approve operational resilience baselines.
            </div>
          </div>
        ) : (
          <div className="p-3.5 bg-emerald-500/10 border border-emerald-500/30 rounded-lg flex items-start gap-3 text-xs text-emerald-300">
            <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold text-emerald-300 block mb-1">
                Four-Eyes Governance Verification
              </span>
              Requester: <span className="font-mono text-emerald-200">{bia.requested_by?.full_name || `User #${bia.requested_by_id}`}</span>.
              Approver: <span className="font-mono text-emerald-200">{user?.full_name || 'Authenticated Manager'}</span>.
              Approving will promote this version to <span className="font-bold">ACTIVE</span> and atomically supersede any existing active baseline.
            </div>
          </div>
        )}

        {/* BIA Baseline Summary Card */}
        <div className="p-3.5 bg-slate-900/90 border border-slate-800 rounded-lg space-y-2 text-xs">
          <div className="flex justify-between border-b border-slate-800 pb-2">
            <span className="text-slate-400 font-medium">BIA Record Version:</span>
            <span className="font-mono font-bold text-slate-200">v{bia.version}</span>
          </div>
          <div className="flex justify-between border-b border-slate-800 pb-2">
            <span className="text-slate-400 font-medium">Recovery Targets:</span>
            <span className="font-mono text-slate-200">RTO: {bia.rto_hours}h | RPO: {bia.rpo_hours}h | MTD: {bia.mtd_hours}h</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400 font-medium">Financial Disruption Exposure:</span>
            <span className="font-mono text-emerald-400 font-semibold">
              ${bia.hourly_downtime_cost.toLocaleString()}/hr (Fixed: ${bia.fixed_outage_cost.toLocaleString()})
            </span>
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
            Formal Approval Review Notes
          </label>
          <textarea
            rows={3}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Document executive review rationale, risk committee quorum, or governance justification..."
            className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
          <Button type="button" variant="secondary" onClick={onClose} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button
            type="submit"
            disabled={mutation.isPending || isRequester}
            className={`flex items-center gap-2 ${
              isRequester
                ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
                : 'bg-emerald-600 hover:bg-emerald-500 text-white'
            }`}
          >
            <ShieldCheck size={16} />
            {mutation.isPending ? 'Approving...' : 'Formally Approve Baseline'}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
