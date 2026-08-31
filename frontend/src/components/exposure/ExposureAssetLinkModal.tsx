import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { resilienceService } from '../../lib/resilienceService';
import { tprmService } from '../../lib/tprmService';
import { api } from '../../lib/api';
import type {
  AssetType,
  Environment,
  ExposureAssetLinkCreate,
  VulnerabilityExposure,
} from '../../types';
import { AlertTriangle } from 'lucide-react';

interface ExposureAssetLinkModalProps {
  isOpen: boolean;
  onClose: () => void;
  exposure: VulnerabilityExposure | null;
  onSubmit: (data: ExposureAssetLinkCreate) => Promise<void>;
  isSubmitting?: boolean;
}

export const ExposureAssetLinkModal: React.FC<ExposureAssetLinkModalProps> = ({
  isOpen,
  onClose,
  exposure,
  onSubmit,
  isSubmitting = false,
}) => {
  const [assetIdentifier, setAssetIdentifier] = useState('');
  const [assetType, setAssetType] = useState<AssetType>('SERVER');
  const [environment, setEnvironment] = useState<Environment>('PRODUCTION');
  const [processId, setProcessId] = useState<number | ''>('');
  const [vendorId, setVendorId] = useState<number | ''>('');
  const [controlId, setControlId] = useState<number | ''>('');
  const [notes, setNotes] = useState('');
  const [error, setError] = useState<string | null>(null);

  // Fetch candidate Business Processes (Phase 13)
  const { data: processes = [] } = useQuery({
    queryKey: ['resilience-processes-lookup'],
    queryFn: () => resilienceService.listProcesses({ limit: 100 }),
    enabled: isOpen,
  });

  // Fetch candidate Vendors (Phase 9)
  const { data: vendors = [] } = useQuery({
    queryKey: ['tprm-vendors-lookup'],
    queryFn: () => tprmService.listVendors({ limit: 100 }),
    enabled: isOpen,
  });

  // Fetch candidate Controls (Phase 2)
  const { data: controls = [] } = useQuery({
    queryKey: ['controls-lookup'],
    queryFn: async () => {
      const res = await api.get<any[]>('/controls', { params: { limit: 100 } });
      return res.data;
    },
    enabled: isOpen,
  });

  useEffect(() => {
    setAssetIdentifier('');
    setAssetType('SERVER');
    setEnvironment('PRODUCTION');
    setProcessId('');
    setVendorId('');
    setControlId('');
    setNotes('');
    setError(null);
  }, [isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!assetIdentifier.trim()) {
      setError('Asset identifier is required (e.g. srv-app-prod-01).');
      return;
    }

    try {
      const payload: ExposureAssetLinkCreate = {
        asset_identifier: assetIdentifier.trim(),
        asset_type: assetType,
        environment: environment,
        process_id: processId !== '' ? Number(processId) : null,
        vendor_id: vendorId !== '' ? Number(vendorId) : null,
        control_id: controlId !== '' ? Number(controlId) : null,
        notes: notes.trim() || null,
      };
      await onSubmit(payload);
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to link asset.');
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Link Technical Asset to ${exposure?.cve_id}`}
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
            Asset Identifier <span className="text-rose-400">*</span>
          </label>
          <input
            type="text"
            required
            value={assetIdentifier}
            onChange={(e) => setAssetIdentifier(e.target.value)}
            placeholder="e.g. srv-auth-prod-01 / k8s-cluster-core / 10.0.1.25"
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono"
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Asset Type
            </label>
            <select
              value={assetType}
              onChange={(e) => setAssetType(e.target.value as AssetType)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
            >
              <option value="SERVER">SERVER</option>
              <option value="DATABASE">DATABASE</option>
              <option value="CLOUD_SERVICE">CLOUD SERVICE</option>
              <option value="NETWORK_DEVICE">NETWORK DEVICE</option>
              <option value="APPLICATION">APPLICATION</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Environment
            </label>
            <select
              value={environment}
              onChange={(e) => setEnvironment(e.target.value as Environment)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
            >
              <option value="PRODUCTION">PRODUCTION</option>
              <option value="STAGING">STAGING</option>
              <option value="DEVELOPMENT">DEVELOPMENT</option>
            </select>
          </div>
        </div>

        <div className="border-t border-slate-800/80 pt-3 space-y-3">
          <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">
            Cross-Module Impact & Governance Links (Optional)
          </p>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Linked Business Process (Phase 13 Blast Radius)
            </label>
            <select
              value={processId}
              onChange={(e) => setProcessId(e.target.value ? Number(e.target.value) : '')}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
            >
              <option value="">-- No Process Linked (1.00× Multiplier) --</option>
              {processes.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.criticality_tier})
                </option>
              ))}
            </select>
            <p className="text-[11px] text-slate-500 mt-1">
              Linking a Tier 1 process automatically scales exposure index by 1.25×.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Linked Third-Party Vendor (Phase 9)
              </label>
              <select
                value={vendorId}
                onChange={(e) => setVendorId(e.target.value ? Number(e.target.value) : '')}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
              >
                <option value="">-- No Vendor Linked --</option>
                {vendors.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.legal_name} ({v.vendor_code})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Linked Control (Phase 2)
              </label>
              <select
                value={controlId}
                onChange={(e) => setControlId(e.target.value ? Number(e.target.value) : '')}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
              >
                <option value="">-- No Control Linked --</option>
                {controls.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.identifier || `Control #${c.id}`} - {c.title || c.status}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">
            Asset Notes
          </label>
          <textarea
            rows={2}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Configuration details, host roles, or compensating architecture..."
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 resize-none"
          />
        </div>

        <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
          <Button variant="outline" type="button" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button variant="primary" type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Linking...' : 'Link Asset'}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
