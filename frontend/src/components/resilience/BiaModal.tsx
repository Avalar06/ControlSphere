import React, { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { resilienceService } from '../../lib/resilienceService';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import type { BusinessImpactAnalysis } from '../../types';
import { AlertCircle, AlertTriangle } from 'lucide-react';

interface BiaModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  processId: number;
  initialBia?: BusinessImpactAnalysis | null;
}

export const BiaModal: React.FC<BiaModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  processId,
  initialBia,
}) => {
  const queryClient = useQueryClient();
  const isEditing = !!initialBia && initialBia.status === 'DRAFT';

  const [rtoHours, setRtoHours] = useState<number>(4.0);
  const [rpoHours, setRpoHours] = useState<number>(1.0);
  const [mtdHours, setMtdHours] = useState<number>(24.0);
  const [hourlyDowntimeCost, setHourlyDowntimeCost] = useState<number>(10000.0);
  const [fixedOutageCost, setFixedOutageCost] = useState<number>(5000.0);
  const [notes, setNotes] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (initialBia) {
      setRtoHours(initialBia.rto_hours);
      setRpoHours(initialBia.rpo_hours);
      setMtdHours(initialBia.mtd_hours);
      setHourlyDowntimeCost(initialBia.hourly_downtime_cost);
      setFixedOutageCost(initialBia.fixed_outage_cost);
      setNotes(initialBia.notes || '');
    } else {
      setRtoHours(4.0);
      setRpoHours(1.0);
      setMtdHours(24.0);
      setHourlyDowntimeCost(10000.0);
      setFixedOutageCost(5000.0);
      setNotes('');
    }
    setErrorMessage(null);
  }, [initialBia, isOpen]);

  // Client-side validation preview check
  const isRtoValid = rtoHours <= mtdHours;
  const areNumbersValid =
    rtoHours >= 0 &&
    rpoHours >= 0 &&
    mtdHours >= 0 &&
    hourlyDowntimeCost >= 0 &&
    fixedOutageCost >= 0;

  const mutation = useMutation({
    mutationFn: async () => {
      const payload = {
        process_id: processId,
        rto_hours: Number(rtoHours),
        rpo_hours: Number(rpoHours),
        mtd_hours: Number(mtdHours),
        hourly_downtime_cost: Number(hourlyDowntimeCost),
        fixed_outage_cost: Number(fixedOutageCost),
        notes: notes.trim() || null,
      };

      if (isEditing && initialBia) {
        return resilienceService.updateDraftBia(initialBia.id, payload);
      } else {
        return resilienceService.draftBia(payload);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resilience-process', processId] });
      queryClient.invalidateQueries({ queryKey: ['resilience-process-bias', processId] });
      queryClient.invalidateQueries({ queryKey: ['resilience-processes'] });
      onSuccess();
      onClose();
    },
    onError: (error: any) => {
      const detail = error.response?.data?.detail;
      setErrorMessage(typeof detail === 'string' ? detail : 'Failed to record Business Impact Analysis.');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!isRtoValid) {
      setErrorMessage(`Recovery Time Objective (${rtoHours}h) cannot exceed Maximum Tolerable Downtime (${mtdHours}h).`);
      return;
    }
    if (!areNumbersValid) {
      setErrorMessage('All recovery thresholds and disruption costs must be non-negative (>= 0).');
      return;
    }
    setErrorMessage(null);
    mutation.mutate();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEditing ? `Edit Draft BIA (v${initialBia.version})` : 'Draft Business Impact Analysis (BIA)'}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {errorMessage && (
          <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg flex items-center gap-2 text-xs text-rose-400">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        <div className="p-3 bg-indigo-950/30 border border-indigo-800/50 rounded-lg text-xs text-indigo-300">
          <span className="font-semibold block mb-1">Server-Authoritative Lifecycle:</span>
          Drafting a BIA creates a <span className="font-mono font-bold text-amber-400">DRAFT</span> baseline.
          Formal four-eyes approval by a secondary Manager or Administrator is required to promote this record to an <span className="font-mono font-bold text-emerald-400">ACTIVE</span> baseline.
        </div>

        {/* Downtime Objectives */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
              RTO (Hours) <span className="text-rose-400">*</span>
            </label>
            <input
              type="number"
              step="0.1"
              min="0"
              required
              value={rtoHours}
              onChange={(e) => setRtoHours(parseFloat(e.target.value) || 0)}
              className={`w-full px-3 py-2 bg-slate-900 border rounded-lg text-sm text-slate-100 focus:outline-none ${
                !isRtoValid ? 'border-rose-500' : 'border-slate-700 focus:border-indigo-500'
              }`}
            />
            <span className="text-[10px] text-slate-400 mt-0.5 block">Recovery Time Target</span>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
              RPO (Hours) <span className="text-rose-400">*</span>
            </label>
            <input
              type="number"
              step="0.1"
              min="0"
              required
              value={rpoHours}
              onChange={(e) => setRpoHours(parseFloat(e.target.value) || 0)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
            />
            <span className="text-[10px] text-slate-400 mt-0.5 block">Max Data Loss Window</span>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
              MTD (Hours) <span className="text-rose-400">*</span>
            </label>
            <input
              type="number"
              step="0.1"
              min="0"
              required
              value={mtdHours}
              onChange={(e) => setMtdHours(parseFloat(e.target.value) || 0)}
              className={`w-full px-3 py-2 bg-slate-900 border rounded-lg text-sm text-slate-100 focus:outline-none ${
                !isRtoValid ? 'border-rose-500' : 'border-slate-700 focus:border-indigo-500'
              }`}
            />
            <span className="text-[10px] text-slate-400 mt-0.5 block">Max Tolerable Downtime</span>
          </div>
        </div>

        {!isRtoValid && (
          <div className="p-2.5 bg-rose-500/10 border border-rose-500/30 rounded text-xs text-rose-400 flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>Invalid threshold: RTO ({rtoHours}h) cannot exceed MTD ({mtdHours}h).</span>
          </div>
        )}

        {/* Financial Disruption Telemetry */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 border-t border-slate-800">
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
              Hourly Downtime Cost ($) <span className="text-rose-400">*</span>
            </label>
            <input
              type="number"
              step="100"
              min="0"
              required
              value={hourlyDowntimeCost}
              onChange={(e) => setHourlyDowntimeCost(parseFloat(e.target.value) || 0)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
            />
            <span className="text-[10px] text-slate-400 mt-0.5 block">Hourly variable disruption loss</span>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
              Fixed Outage Cost ($)
            </label>
            <input
              type="number"
              step="100"
              min="0"
              value={fixedOutageCost}
              onChange={(e) => setFixedOutageCost(parseFloat(e.target.value) || 0)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
            />
            <span className="text-[10px] text-slate-400 mt-0.5 block">Initial disruption incident cost</span>
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
            Impact Analysis &amp; Justification Notes
          </label>
          <textarea
            rows={3}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Operational dependencies, critical data feeds, customer SLA obligations..."
            className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
          <Button type="button" variant="secondary" onClick={onClose} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button
            type="submit"
            disabled={mutation.isPending || !isRtoValid || !areNumbersValid}
            className="bg-indigo-600 hover:bg-indigo-500"
          >
            {mutation.isPending ? 'Saving...' : isEditing ? 'Update Draft BIA' : 'Save Draft BIA'}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
