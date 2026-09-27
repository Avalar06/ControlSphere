import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { resilienceService } from '../../lib/resilienceService';
import { tprmService } from '../../lib/tprmService';
import { api } from '../../lib/api';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import type {
  BusinessProcess,
  CloudAsset,
  DataAsset,
  DependencyType,
  OrganizationControl,
} from '../../types';
import {
  AlertTriangle,
  Building2,
  Cloud,
  Database,
  Layers,
  Link2,
  Shield,
} from 'lucide-react';

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
  const [isSpof, setIsSpof] = useState<boolean>(false);
  const [propagationWeight, setPropagationWeight] = useState<string>('1.0');
  const [recoveryPriority, setRecoveryPriority] = useState<string>('1');
  const [notes, setNotes] = useState<string>('');
  const [criticalityNotes, setCriticalityNotes] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data: vendors = [], isLoading: isVendorsLoading } = useQuery({
    queryKey: ['resilience-dep-vendors'],
    queryFn: () => tprmService.listVendors(),
    enabled: isOpen && dependencyType === 'VENDOR',
  });

  const { data: controls = [], isLoading: isControlsLoading } = useQuery({
    queryKey: ['resilience-dep-controls'],
    queryFn: async () => {
      const response = await api.get<OrganizationControl[]>('/controls');
      return response.data;
    },
    enabled: isOpen && dependencyType === 'CONTROL',
  });

  const { data: cloudAssets = [], isLoading: isCloudLoading } = useQuery({
    queryKey: ['resilience-dep-cloud-assets'],
    queryFn: async () => {
      const response = await api.get<CloudAsset[]>('/cloudsec/assets');
      return response.data;
    },
    enabled: isOpen && dependencyType === 'CLOUD_ASSET',
  });

  const { data: dataAssets = [], isLoading: isDataLoading } = useQuery({
    queryKey: ['resilience-dep-data-assets'],
    queryFn: async () => {
      const response = await api.get<DataAsset[]>('/privacy/assets');
      return response.data;
    },
    enabled: isOpen && dependencyType === 'DATA_ASSET',
  });

  const { data: processes = [], isLoading: isProcessesLoading } = useQuery({
    queryKey: ['resilience-dep-processes'],
    queryFn: () => resilienceService.listProcesses(),
    enabled: isOpen && dependencyType === 'PROCESS',
  });

  const mutation = useMutation({
    mutationFn: async () => {
      const id = parseInt(selectedEntityId, 10);
      if (!id || isNaN(id)) {
        throw new Error('Please select a valid target entity.');
      }
      const weight = isSpof ? 1.0 : parseFloat(propagationWeight) || 1.0;
      const priority = Math.max(1, parseInt(recoveryPriority, 10) || 1);

      return resilienceService.addProcessDependency(processId, {
        dependency_type: dependencyType,
        vendor_id: dependencyType === 'VENDOR' ? id : null,
        organization_control_id: dependencyType === 'CONTROL' ? id : null,
        cloud_asset_id: dependencyType === 'CLOUD_ASSET' ? id : null,
        data_asset_id: dependencyType === 'DATA_ASSET' ? id : null,
        depends_on_process_id: dependencyType === 'PROCESS' ? id : null,
        is_single_point_of_failure: isSpof,
        failure_propagation_weight: weight,
        recovery_priority_order: priority,
        notes: notes.trim() || null,
        criticality_notes: criticalityNotes.trim() || null,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resilience-process', processId] });
      queryClient.invalidateQueries({ queryKey: ['resilience-dependencies', processId] });
      queryClient.invalidateQueries({ queryKey: ['resilience-dep-health', processId] });
      queryClient.invalidateQueries({ queryKey: ['resilience-processes'] });
      queryClient.invalidateQueries({ queryKey: ['resilience-dashboard'] });
      onSuccess();
      onClose();
      setSelectedEntityId('');
      setIsSpof(false);
      setPropagationWeight('1.0');
      setRecoveryPriority('1');
      setNotes('');
      setCriticalityNotes('');
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

  const categoryButtons: {
    type: DependencyType;
    label: string;
    subtitle: string;
    icon: React.ReactNode;
  }[] = [
    {
      type: 'VENDOR',
      label: 'Third-Party Vendor',
      subtitle: 'Phase 9 TPRM',
      icon: <Building2 className="h-4 w-4" />,
    },
    {
      type: 'CONTROL',
      label: 'Internal Control',
      subtitle: 'Phase 2 Safeguards',
      icon: <Shield className="h-4 w-4" />,
    },
    {
      type: 'CLOUD_ASSET',
      label: 'Cloud Infrastructure',
      subtitle: 'Phase 11 CloudSec',
      icon: <Cloud className="h-4 w-4" />,
    },
    {
      type: 'DATA_ASSET',
      label: 'Data Asset',
      subtitle: 'Phase 12 Privacy/Data',
      icon: <Database className="h-4 w-4" />,
    },
    {
      type: 'PROCESS',
      label: 'Upstream Process',
      subtitle: 'Process Lineage DAG',
      icon: <Layers className="h-4 w-4" />,
    },
  ];

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Link Upstream Process Dependency">
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
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
            {categoryButtons.map((cat) => (
              <button
                key={cat.type}
                type="button"
                onClick={() => {
                  setDependencyType(cat.type);
                  setSelectedEntityId('');
                }}
                className={`p-2.5 rounded-lg border text-left flex items-center gap-2.5 transition-all ${
                  dependencyType === cat.type
                    ? 'bg-indigo-600/20 border-indigo-500/50 text-slate-100'
                    : 'bg-slate-900 border-slate-800 text-slate-400 hover:bg-slate-800/60'
                }`}
              >
                <span className={dependencyType === cat.type ? 'text-indigo-400' : 'text-slate-500'}>
                  {cat.icon}
                </span>
                <div>
                  <div className="text-xs font-semibold">{cat.label}</div>
                  <div className="text-[10px] text-slate-400">{cat.subtitle}</div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Dynamic Entity Selector */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
            Select Target ({dependencyType}) <span className="text-rose-400">*</span>
          </label>

          {dependencyType === 'VENDOR' && (
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
          )}

          {dependencyType === 'CONTROL' && (
            <select
              value={selectedEntityId}
              onChange={(e) => setSelectedEntityId(e.target.value)}
              disabled={isControlsLoading}
              required
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
            >
              <option value="">
                {isControlsLoading ? 'Loading controls...' : '-- Select Organization Control --'}
              </option>
              {controls.map((c) => (
                <option key={c.id} value={c.id}>
                  Control #{c.id} ({c.subcategory?.identifier || 'N/A'}: {c.subcategory?.title || 'Control'}) — {c.status}
                </option>
              ))}
            </select>
          )}

          {dependencyType === 'CLOUD_ASSET' && (
            <select
              value={selectedEntityId}
              onChange={(e) => setSelectedEntityId(e.target.value)}
              disabled={isCloudLoading}
              required
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
            >
              <option value="">
                {isCloudLoading ? 'Loading cloud assets...' : '-- Select Cloud Infrastructure Asset --'}
              </option>
              {cloudAssets.map((ca) => (
                <option key={ca.id} value={ca.id}>
                  {ca.resource_name} ({ca.provider} / {ca.region}) — {ca.posture_status}
                </option>
              ))}
            </select>
          )}

          {dependencyType === 'DATA_ASSET' && (
            <select
              value={selectedEntityId}
              onChange={(e) => setSelectedEntityId(e.target.value)}
              disabled={isDataLoading}
              required
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
            >
              <option value="">
                {isDataLoading ? 'Loading data assets...' : '-- Select Governed Data Asset --'}
              </option>
              {dataAssets.map((da) => (
                <option key={da.id} value={da.id}>
                  {da.name} ({da.asset_code}) — {da.data_sensitivity_level}
                </option>
              ))}
            </select>
          )}

          {dependencyType === 'PROCESS' && (
            <select
              value={selectedEntityId}
              onChange={(e) => setSelectedEntityId(e.target.value)}
              disabled={isProcessesLoading}
              required
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
            >
              <option value="">
                {isProcessesLoading ? 'Loading processes...' : '-- Select Upstream Business Process --'}
              </option>
              {processes
                .filter((p: BusinessProcess) => p.id !== processId)
                .map((p: BusinessProcess) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.criticality_tier})
                  </option>
                ))}
            </select>
          )}
        </div>

        {/* SPOF, Propagation Weight & Recovery Priority */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="p-2.5 bg-slate-900 border border-slate-800 rounded-lg flex items-center gap-2.5">
            <input
              id="spof-check"
              type="checkbox"
              checked={isSpof}
              onChange={(e) => {
                setIsSpof(e.target.checked);
                if (e.target.checked) setPropagationWeight('1.0');
              }}
              className="rounded border-slate-700 bg-slate-950 text-indigo-600 focus:ring-indigo-500"
            />
            <label htmlFor="spof-check" className="text-xs font-semibold text-slate-200 cursor-pointer">
              Single Point of Failure (SPOF)
            </label>
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">
              Propagation Weight (0.01–1.0)
            </label>
            <input
              type="number"
              step="0.05"
              min="0.05"
              max="1.0"
              disabled={isSpof}
              value={isSpof ? '1.0' : propagationWeight}
              onChange={(e) => setPropagationWeight(e.target.value)}
              className="w-full px-3 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-xs font-mono text-slate-100 disabled:opacity-60"
            />
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">
              Recovery Priority Order
            </label>
            <input
              type="number"
              min="1"
              step="1"
              value={recoveryPriority}
              onChange={(e) => setRecoveryPriority(e.target.value)}
              className="w-full px-3 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-xs font-mono text-slate-100"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
              Dependency Context Notes
            </label>
            <textarea
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Primary settlement cluster in us-east-1..."
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
              SPOF / Criticality Notes
            </label>
            <textarea
              rows={2}
              value={criticalityNotes}
              onChange={(e) => setCriticalityNotes(e.target.value)}
              placeholder="e.g. Requires active-passive RDS failover promotion..."
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>
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
