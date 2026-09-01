import React, { useState, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { privacyService } from '../../lib/privacyService';
import type {
  DataAsset,
  DataAssetCreate,
  DataAssetUpdate,
  DataSensitivityLevel,
} from '../../types';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface DataAssetModalProps {
  isOpen: boolean;
  onClose: () => void;
  asset?: DataAsset | null;
  onSuccess: () => void;
}

export const DataAssetModal: React.FC<DataAssetModalProps> = ({
  isOpen,
  onClose,
  asset,
  onSuccess,
}) => {
  const isEdit = Boolean(asset);

  const [assetCode, setAssetCode] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [sensitivity, setSensitivity] = useState<DataSensitivityLevel>('INTERNAL');
  const [volumeRange, setVolumeRange] = useState('LOW');
  const [storageType, setStorageType] = useState('POSTGRES_DB');
  const [hostingJurisdiction, setHostingJurisdiction] = useState('EU_EEA');
  const [isEncryptedAtRest, setIsEncryptedAtRest] = useState(true);
  const [isEncryptedInTransit, setIsEncryptedInTransit] = useState(true);
  const [isPseudonymized, setIsPseudonymized] = useState(false);
  const [retentionMonths, setRetentionMonths] = useState<number>(12);
  const [businessProcessId, setBusinessProcessId] = useState<string>('');
  const [aiSystemId, setAiSystemId] = useState<string>('');
  const [vendorId, setVendorId] = useState<string>('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (asset) {
      setAssetCode(asset.asset_code);
      setName(asset.name);
      setDescription(asset.description || '');
      setSensitivity(asset.data_sensitivity_level);
      setVolumeRange(asset.data_volume_range);
      setStorageType(asset.storage_type);
      setHostingJurisdiction(asset.hosting_jurisdiction);
      setIsEncryptedAtRest(asset.is_encrypted_at_rest);
      setIsEncryptedInTransit(asset.is_encrypted_in_transit);
      setIsPseudonymized(asset.is_pseudonymized);
      setRetentionMonths(asset.retention_period_months ?? 12);
      setBusinessProcessId(asset.business_process_id ? String(asset.business_process_id) : '');
      setAiSystemId(asset.ai_system_id ? String(asset.ai_system_id) : '');
      setVendorId(asset.vendor_id ? String(asset.vendor_id) : '');
    } else {
      setAssetCode('');
      setName('');
      setDescription('');
      setSensitivity('INTERNAL');
      setVolumeRange('LOW');
      setStorageType('POSTGRES_DB');
      setHostingJurisdiction('EU_EEA');
      setIsEncryptedAtRest(true);
      setIsEncryptedInTransit(true);
      setIsPseudonymized(false);
      setRetentionMonths(12);
      setBusinessProcessId('');
      setAiSystemId('');
      setVendorId('');
    }
    setErrorMsg(null);
  }, [asset, isOpen]);

  const mutation = useMutation({
    mutationFn: async () => {
      if (isEdit && asset) {
        const updateData: DataAssetUpdate = {
          name: name.trim(),
          description: description.trim() || null,
          data_sensitivity_level: sensitivity,
          data_volume_range: volumeRange,
          storage_type: storageType.trim(),
          hosting_jurisdiction: hostingJurisdiction.trim(),
          is_encrypted_at_rest: isEncryptedAtRest,
          is_encrypted_in_transit: isEncryptedInTransit,
          is_pseudonymized: isPseudonymized,
          retention_period_months: retentionMonths ? Number(retentionMonths) : null,
          business_process_id: businessProcessId ? Number(businessProcessId) : null,
          ai_system_id: aiSystemId ? Number(aiSystemId) : null,
          vendor_id: vendorId ? Number(vendorId) : null,
        };
        return privacyService.updateDataAsset(asset.id, updateData);
      } else {
        const createData: DataAssetCreate = {
          asset_code: assetCode.trim(),
          name: name.trim(),
          description: description.trim() || null,
          data_sensitivity_level: sensitivity,
          data_volume_range: volumeRange,
          storage_type: storageType.trim(),
          hosting_jurisdiction: hostingJurisdiction.trim(),
          is_encrypted_at_rest: isEncryptedAtRest,
          is_encrypted_in_transit: isEncryptedInTransit,
          is_pseudonymized: isPseudonymized,
          retention_period_months: retentionMonths ? Number(retentionMonths) : null,
          business_process_id: businessProcessId ? Number(businessProcessId) : null,
          ai_system_id: aiSystemId ? Number(aiSystemId) : null,
          vendor_id: vendorId ? Number(vendorId) : null,
        };
        return privacyService.createDataAsset(createData);
      }
    },
    onSuccess: () => {
      setErrorMsg(null);
      onSuccess();
      onClose();
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || err.message || 'Failed to save data asset';
      setErrorMsg(msg);
    },
  });

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEdit ? `Edit Data Asset: ${asset?.asset_code}` : 'Register New Data Asset'}
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          mutation.mutate();
        }}
        className="space-y-4"
      >
        {/* Asset Code & Name */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Asset Code <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              required
              disabled={isEdit}
              value={assetCode}
              onChange={(e) => setAssetCode(e.target.value.toUpperCase())}
              placeholder="e.g. DA-CUST-001"
              className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-hidden focus:border-indigo-500 font-mono disabled:opacity-60"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Asset Name <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Customer Master Postgres DB"
              className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-hidden focus:border-indigo-500"
            />
          </div>
        </div>

        {/* Description */}
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">Description</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            placeholder="Functional description and personal data categories stored..."
            className="w-full bg-slate-950 border border-slate-800 rounded-md p-2 text-xs text-slate-200 focus:outline-hidden focus:border-indigo-500 placeholder:text-slate-600"
          />
        </div>

        {/* Sensitivity & Volume */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Data Sensitivity Classification
            </label>
            <select
              value={sensitivity}
              onChange={(e) => setSensitivity(e.target.value as DataSensitivityLevel)}
              className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-hidden focus:border-indigo-500"
            >
              <option value="PUBLIC">PUBLIC</option>
              <option value="INTERNAL">INTERNAL</option>
              <option value="CONFIDENTIAL">CONFIDENTIAL</option>
              <option value="RESTRICTED_PII">RESTRICTED_PII (GDPR PII)</option>
              <option value="SPECIAL_CATEGORY">SPECIAL_CATEGORY (Art 9)</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Data Volume Range
            </label>
            <select
              value={volumeRange}
              onChange={(e) => setVolumeRange(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-hidden focus:border-indigo-500"
            >
              <option value="LOW">LOW (&lt;10k data subjects)</option>
              <option value="MEDIUM">MEDIUM (10k - 1M data subjects)</option>
              <option value="HIGH">HIGH (&gt;1M data subjects)</option>
            </select>
          </div>
        </div>

        {/* Storage Type & Jurisdiction */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Storage Type</label>
            <input
              type="text"
              value={storageType}
              onChange={(e) => setStorageType(e.target.value)}
              placeholder="e.g. POSTGRES_DB, S3_BUCKET"
              className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-hidden focus:border-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Hosting Jurisdiction
            </label>
            <input
              type="text"
              value={hostingJurisdiction}
              onChange={(e) => setHostingJurisdiction(e.target.value)}
              placeholder="e.g. EU_EEA, US_EAST"
              className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-hidden focus:border-indigo-500"
            />
          </div>
        </div>

        {/* Security Controls */}
        <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 space-y-2">
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            Technical &amp; Organizational Safeguards
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-xs">
            <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={isEncryptedAtRest}
                onChange={(e) => setIsEncryptedAtRest(e.target.checked)}
                className="rounded border-slate-800 bg-slate-900 text-indigo-600 focus:ring-0"
              />
              <span>Encrypted at Rest</span>
            </label>
            <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={isEncryptedInTransit}
                onChange={(e) => setIsEncryptedInTransit(e.target.checked)}
                className="rounded border-slate-800 bg-slate-900 text-indigo-600 focus:ring-0"
              />
              <span>Encrypted in Transit</span>
            </label>
            <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={isPseudonymized}
                onChange={(e) => setIsPseudonymized(e.target.checked)}
                className="rounded border-slate-800 bg-slate-900 text-indigo-600 focus:ring-0"
              />
              <span>Pseudonymized</span>
            </label>
          </div>
        </div>

        {/* Retention & Cross-Module */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Retention (Months)
            </label>
            <input
              type="number"
              min={1}
              max={1200}
              value={retentionMonths}
              onChange={(e) => setRetentionMonths(Number(e.target.value))}
              className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-hidden focus:border-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Business Process ID
            </label>
            <input
              type="number"
              value={businessProcessId}
              onChange={(e) => setBusinessProcessId(e.target.value)}
              placeholder="e.g. 1"
              className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-hidden focus:border-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">AI System ID</label>
            <input
              type="number"
              value={aiSystemId}
              onChange={(e) => setAiSystemId(e.target.value)}
              placeholder="e.g. 1"
              className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-hidden focus:border-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Vendor ID</label>
            <input
              type="number"
              value={vendorId}
              onChange={(e) => setVendorId(e.target.value)}
              placeholder="e.g. 1"
              className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-hidden focus:border-indigo-500"
            />
          </div>
        </div>

        {/* Error message */}
        {errorMsg && (
          <div className="p-3 rounded-lg bg-rose-950/50 border border-rose-800/80 flex items-start gap-2 text-xs text-rose-300">
            <AlertCircle size={15} className="shrink-0 mt-0.5" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
          <Button variant="ghost" type="button" onClick={onClose} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button variant="primary" type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? (
              <span className="flex items-center gap-1.5">
                <RefreshCw size={14} className="animate-spin" />
                Saving...
              </span>
            ) : isEdit ? (
              'Update Asset'
            ) : (
              'Register Asset'
            )}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
