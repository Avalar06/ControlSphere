import React, { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { resilienceService } from '../../lib/resilienceService';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import type { BusinessProcess, CriticalityTier } from '../../types';
import { AlertTriangle } from 'lucide-react';

interface ProcessModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  initialProcess?: BusinessProcess | null;
}

export const ProcessModal: React.FC<ProcessModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  initialProcess,
}) => {
  const queryClient = useQueryClient();
  const isEditing = !!initialProcess;

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [criticalityTier, setCriticalityTier] = useState<CriticalityTier>('TIER_3');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (initialProcess) {
      setName(initialProcess.name);
      setDescription(initialProcess.description || '');
      setCriticalityTier(initialProcess.criticality_tier);
    } else {
      setName('');
      setDescription('');
      setCriticalityTier('TIER_3');
    }
    setErrorMessage(null);
  }, [initialProcess, isOpen]);

  const mutation = useMutation({
    mutationFn: async () => {
      if (isEditing && initialProcess) {
        return resilienceService.updateProcess(initialProcess.id, {
          name: name.trim(),
          description: description.trim() || null,
          criticality_tier: criticalityTier,
        });
      } else {
        return resilienceService.createProcess({
          name: name.trim(),
          description: description.trim() || null,
          criticality_tier: criticalityTier,
        });
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resilience-processes'] });
      if (isEditing && initialProcess) {
        queryClient.invalidateQueries({ queryKey: ['resilience-process', initialProcess.id] });
      }
      onSuccess();
      onClose();
    },
    onError: (error: any) => {
      const detail = error.response?.data?.detail;
      setErrorMessage(typeof detail === 'string' ? detail : 'Failed to save business process.');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || name.trim().length < 2) {
      setErrorMessage('Process name must be at least 2 characters.');
      return;
    }
    setErrorMessage(null);
    mutation.mutate();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEditing ? 'Edit Business Process' : 'New Business Process'}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {errorMessage && (
          <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg flex items-center gap-2 text-xs text-rose-400">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        <div>
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
            Process Name <span className="text-rose-400">*</span>
          </label>
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Core Banking Settlement Engine"
            className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
            Criticality Tier <span className="text-rose-400">*</span>
          </label>
          <select
            value={criticalityTier}
            onChange={(e) => setCriticalityTier(e.target.value as CriticalityTier)}
            className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
          >
            <option value="TIER_1">TIER 1 — Mission Critical (Core Revenue / Life-Safety)</option>
            <option value="TIER_2">TIER 2 — Business Operational (High Impact)</option>
            <option value="TIER_3">TIER 3 — Moderate Operational (Standard Business Function)</option>
            <option value="TIER_4">TIER 4 — Low Impact / Non-Critical</option>
          </select>
          <p className="text-[11px] text-slate-400 mt-1">
            Determines executive prioritization and recovery escalation SLAs during disruptive incidents.
          </p>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
            Description &amp; Operational Scope
          </label>
          <textarea
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Detailed function, primary services delivered, and system boundaries..."
            className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
          <Button type="button" variant="secondary" onClick={onClose} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button type="submit" disabled={mutation.isPending} className="bg-indigo-600 hover:bg-indigo-500">
            {mutation.isPending ? 'Saving...' : isEditing ? 'Update Process' : 'Create Process'}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
