import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { resilienceService } from '../../lib/resilienceService';
import { tprmService } from '../../lib/tprmService';
import { api } from '../../lib/api';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import type { DependencyType, OrganizationControl } from '../../types';
import { AlertTriangle, Building2, Link2, Shield } from 'lucide-react';

interface DependencyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  processId: number;
}

export const DependencyModal: React.FC<DependencyModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  processId,
}) => {
  const queryClient = useQueryClient();

  const [dependencyType, setDependencyType] = useState<DependencyType>('VENDOR');
  const [selectedEntityId, setSelectedEntityId] = useState<string>('');
  const [notes, setNotes] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Fetch tenant vendors from Phase 9 TPRM
  const { data: vendors = [], isLoading: isVendorsLoading } = useQuery({
    queryKey: ['resilience-dep-vendors'],
    queryFn: () => tprmService.listVendors(),
    enabled: isOpen && dependencyType === 'VENDOR',
  });

  // Fetch tenant controls from Phase 2 Controls
  const { data: controls = [], isLoading: isControlsLoading } = useQuery({
    queryKey: ['resilience-dep-controls'],
    queryFn: async () => {
      const response = await api.get<OrganizationControl[]>('/controls');
      return response.data;
    },
    enabled: isOpen && dependencyType === 'CONTROL',
  });

  const mutation = useMutation({
    mutationFn: async () => {
      const id = parseInt(selectedEntityId, 10);
      if (!id || isNaN(id)) {
        throw new Error('Please select a valid target entity.');
      }
      return resilienceService.addDependency({
        process_id: processId,
        dependency_type: dependencyType,
        dependency_id: id,
        notes: notes.trim() || null,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resilience-process', processId] });
      queryClient.invalidateQueries({ queryKey: ['resilience-dependencies', processId] });
      queryClient.invalidateQueries({ queryKey: ['resilience-processes'] });
      onSuccess();
      onClose();
      setSelectedEntityId('');
      setNotes('');
    },
    onError: (error: any) => {
      const detail = error.response?.data?.detail || error.message;
      setErrorMessage(typeof detail === 'string' ? detail : 'Failed to link dependency.');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedEntityId) {
      setErrorMessage('Please select a target entity from the catalog.');
      return;
    }
    setErrorMessage(null);
    mutation.mutate();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Link Upstream Process Dependency"
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
            Dependency Category <span className="text-rose-400">*</span>
          </label>
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => {
                setDependencyType('VENDOR');
                setSelectedEntityId('');
              }}
              className={`p-3 rounded-lg border text-left flex items-center gap-3 transition-all ${
                dependencyType === 'VENDOR'
                  ? 'bg-indigo-600/20 border-indigo-500/50 text-slate-100'
                  : 'bg-slate-900 border-slate-800 text-slate-400 hover:bg-slate-800/60'
              }`}
            >
              <Building2 className={`h-5 w-5 ${dependencyType === 'VENDOR' ? 'text-indigo-400' : 'text-slate-500'}`} />
              <div>
                <div className="text-xs font-semibold">Third-Party Vendor</div>
                <div className="text-[10px] text-slate-400">Phase 9 TPRM Catalog</div>
              </div>
            </button>

            <button
              type="button"
              onClick={() => {
                setDependencyType('CONTROL');
                setSelectedEntityId('');
              }}
              className={`p-3 rounded-lg border text-left flex items-center gap-3 transition-all ${
                dependencyType === 'CONTROL'
                  ? 'bg-indigo-600/20 border-indigo-500/50 text-slate-100'
                  : 'bg-slate-900 border-slate-800 text-slate-400 hover:bg-slate-800/60'
              }`}
            >
              <Shield className={`h-5 w-5 ${dependencyType === 'CONTROL' ? 'text-indigo-400' : 'text-slate-500'}`} />
              <div>
                <div className="text-xs font-semibold">Internal Control</div>
                <div className="text-[10px] text-slate-400">Phase 2 Safeguards</div>
              </div>
            </button>
          </div>
        </div>

        {/* Dynamic Entity Selector */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
            Select {dependencyType === 'VENDOR' ? 'Vendor' : 'Control'} <span className="text-rose-400">*</span>
          </label>

          {dependencyType === 'VENDOR' ? (
            <select
              value={selectedEntityId}
              onChange={(e) => setSelectedEntityId(e.target.value)}
              disabled={isVendorsLoading}
              required
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
            >
              <option value="">{isVendorsLoading ? 'Loading vendors...' : '-- Select Vendor --'}</option>
              {vendors.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.legal_name} ({v.vendor_code}) — {v.calculated_tier || 'UNCLASSIFIED'}
                </option>
              ))}
            </select>
          ) : (
            <select
              value={selectedEntityId}
              onChange={(e) => setSelectedEntityId(e.target.value)}
              disabled={isControlsLoading}
              required
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
            >
              <option value="">{isControlsLoading ? 'Loading controls...' : '-- Select Organization Control --'}</option>
              {controls.map((c) => (
                <option key={c.id} value={c.id}>
                  Control #{c.id} ({c.subcategory?.identifier || 'N/A'}: {c.subcategory?.title || 'Control'}) — {c.status}
                </option>
              ))}
            </select>
          )}
          <p className="text-[11px] text-slate-400 mt-1">
            Links critical operational SLA and control implementation telemetry to this business process.
          </p>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
            Contextual Dependency Notes
          </label>
          <textarea
            rows={2}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="e.g. Primary cloud hosting provider with 99.99% SLA..."
            className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
          <Button type="button" variant="secondary" onClick={onClose} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button
            type="submit"
            disabled={mutation.isPending || !selectedEntityId}
            className="bg-indigo-600 hover:bg-indigo-500 flex items-center gap-2"
          >
            <Link2 size={15} />
            {mutation.isPending ? 'Linking...' : 'Link Dependency'}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
