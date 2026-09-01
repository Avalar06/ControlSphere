import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { privacyService } from '../../lib/privacyService';
import type { ProcessingActivity, ProcessingLifecycleState } from '../../types';
import { AlertCircle, AlertTriangle, RefreshCw } from 'lucide-react';

interface PrivacyLifecycleModalProps {
  isOpen: boolean;
  onClose: () => void;
  activity: ProcessingActivity | null;
  onSuccess: () => void;
}

export const PrivacyLifecycleModal: React.FC<PrivacyLifecycleModalProps> = ({
  isOpen,
  onClose,
  activity,
  onSuccess,
}) => {
  const [targetState, setTargetState] = useState<ProcessingLifecycleState>('DPO_REVIEW');
  const [notes, setNotes] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => {
      if (!activity) throw new Error('No activity selected');
      return privacyService.updateProcessingActivityStatus(activity.id, {
        lifecycle_state: targetState,
        notes: notes.trim() || undefined,
      });
    },
    onSuccess: () => {
      setErrorMsg(null);
      setNotes('');
      onSuccess();
      onClose();
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || err.message || 'Failed to update lifecycle state';
      setErrorMsg(msg);
    },
  });

  if (!activity) return null;

  const getPermittedTransitions = (current: ProcessingLifecycleState): ProcessingLifecycleState[] => {
    switch (current) {
      case 'DRAFT':
        return ['DPO_REVIEW', 'ARCHIVED'];
      case 'DPO_REVIEW':
        return ['ACTIVE', 'DRAFT', 'SUSPENDED'];
      case 'ACTIVE':
        return ['SUSPENDED', 'ARCHIVED', 'RETIRED'];
      case 'SUSPENDED':
        return ['DPO_REVIEW', 'ARCHIVED', 'RETIRED'];
      case 'ARCHIVED':
        return ['RETIRED'];
      case 'RETIRED':
        return [];
      default:
        return [];
    }
  };

  const permitted = getPermittedTransitions(activity.lifecycle_state);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Transition Lifecycle: ${activity.activity_code}`}
    >
      <div className="space-y-4">
        {/* Current State Display */}
        <div className="p-3.5 rounded-lg bg-slate-950/70 border border-slate-800 flex items-center justify-between">
          <div>
            <div className="text-[11px] text-slate-400 font-medium">CURRENT GOVERNANCE STATE</div>
            <div className="text-sm font-semibold text-slate-200 mt-0.5">{activity.name}</div>
          </div>
          <Badge variant="info">{activity.lifecycle_state}</Badge>
        </div>

        {/* State Machine Rules Notice */}
        {activity.lifecycle_state === 'RETIRED' ? (
          <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-800/60 flex items-start gap-2.5">
            <AlertCircle size={16} className="text-rose-400 shrink-0 mt-0.5" />
            <div className="text-xs text-rose-300">
              This processing activity is <strong>RETIRED</strong> and permanently immutable. No further state transitions are permitted under Privacy-GRC governance rules.
            </div>
          </div>
        ) : permitted.length === 0 ? (
          <div className="text-xs text-slate-400">No valid lifecycle transitions available.</div>
        ) : (
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Target Lifecycle State
            </label>
            <select
              value={targetState}
              onChange={(e) => setTargetState(e.target.value as ProcessingLifecycleState)}
              className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-hidden focus:border-indigo-500"
            >
              {permitted.map((state) => (
                <option key={state} value={state}>
                  {state}
                </option>
              ))}
            </select>
            {targetState === 'ACTIVE' && activity.dpo_approval_status !== 'APPROVED' && (
              <div className="mt-2 p-2.5 rounded bg-amber-950/30 border border-amber-800/50 flex items-start gap-2 text-[11px] text-amber-300">
                <AlertTriangle size={14} className="shrink-0 mt-0.5 text-amber-400" />
                <span>
                  Transitioning to <strong>ACTIVE</strong> requires formal prior DPO approval ({activity.dpo_approval_status}). The backend will reject if unapproved.
                </span>
              </div>
            )}
          </div>
        )}

        {/* Transition Notes */}
        {permitted.length > 0 && (
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Audit Notes &amp; Justification
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              placeholder="Provide reason for lifecycle transition..."
              className="w-full bg-slate-950 border border-slate-800 rounded-md p-2.5 text-xs text-slate-200 focus:outline-hidden focus:border-indigo-500 placeholder:text-slate-600"
            />
          </div>
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
            Cancel
          </Button>
          {permitted.length > 0 && (
            <Button
              variant="primary"
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending}
              className="flex items-center gap-1.5"
            >
              {mutation.isPending && <RefreshCw size={14} className="animate-spin" />}
              <span>Confirm Transition</span>
            </Button>
          )}
        </div>
      </div>
    </Modal>
  );
};
