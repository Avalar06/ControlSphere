import React, { useState } from 'react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import type { ExposureStatus, VulnerabilityExposure } from '../../types';
import { AlertTriangle, Lock } from 'lucide-react';

interface ExposureStatusModalProps {
  isOpen: boolean;
  onClose: () => void;
  exposure: VulnerabilityExposure | null;
  onSubmit: (status: ExposureStatus, notes?: string) => Promise<void>;
  isSubmitting?: boolean;
}

export const ExposureStatusModal: React.FC<ExposureStatusModalProps> = ({
  isOpen,
  onClose,
  exposure,
  onSubmit,
  isSubmitting = false,
}) => {
  const currentStatus = exposure?.status || 'OPEN';
  const [selectedStatus, setSelectedStatus] = useState<ExposureStatus>('UNDER_INVESTIGATION');
  const [notes, setNotes] = useState('');
  const [error, setError] = useState<string | null>(null);

  // Legal transitions based on current status
  const getAvailableStatuses = (): ExposureStatus[] => {
    switch (currentStatus) {
      case 'OPEN':
        return ['UNDER_INVESTIGATION', 'REMEDIATING', 'RESOLVED'];
      case 'UNDER_INVESTIGATION':
        return ['REMEDIATING', 'RESOLVED'];
      case 'REMEDIATING':
        return ['RESOLVED'];
      case 'EXCEPTION_APPROVED':
      case 'EXCEPTION_REJECTED':
        return ['UNDER_INVESTIGATION', 'REMEDIATING', 'RESOLVED'];
      default:
        return [];
    }
  };

  const availableStatuses = getAvailableStatuses();

  React.useEffect(() => {
    if (availableStatuses.length > 0) {
      setSelectedStatus(availableStatuses[0]);
    }
    setNotes('');
    setError(null);
  }, [exposure, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await onSubmit(selectedStatus, notes.trim() || undefined);
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to update status.');
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Transition Status: ${exposure?.cve_id}`}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg flex items-center gap-2 text-xs text-rose-400">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">
            Current Status
          </label>
          <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono font-bold text-indigo-400">
            {currentStatus}
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">
            Target Status <span className="text-rose-400">*</span>
          </label>
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value as ExposureStatus)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
          >
            {availableStatuses.map((st) => (
              <option key={st} value={st}>
                {st}
              </option>
            ))}
          </select>
        </div>

        {selectedStatus === 'RESOLVED' && (
          <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg flex items-start gap-2.5 text-xs text-amber-300">
            <Lock className="h-4 w-4 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Permanent Immutability Warning</p>
              <p className="text-[11px] text-amber-300/80 mt-0.5">
                Transitioning to RESOLVED is final. Resolved records are permanently locked against modifications, deletions, asset links, and status reversals.
              </p>
            </div>
          </div>
        )}

        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">
            Transition Rationale / Audit Notes
          </label>
          <textarea
            rows={3}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Document verification steps, patch testing evidence, or rationale..."
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 resize-none"
          />
        </div>

        <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
          <Button variant="outline" type="button" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button variant="primary" type="submit" disabled={isSubmitting || availableStatuses.length === 0}>
            {isSubmitting ? 'Updating...' : 'Confirm Transition'}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
