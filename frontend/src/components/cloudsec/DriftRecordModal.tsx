import React, { useState } from 'react';
import { X, GitCommit } from 'lucide-react';
import type { CloudAsset, CloudConfigurationDriftCreate, DriftSeverity } from '../../types';
import { cloudSecService } from '../../lib/cloudSecService';

interface DriftRecordModalProps {
  isOpen: boolean;
  onClose: () => void;
  asset: CloudAsset;
  onSuccess: () => void;
}

export const DriftRecordModal: React.FC<DriftRecordModalProps> = ({ isOpen, onClose, asset, onSuccess }) => {
  const [formData, setFormData] = useState<CloudConfigurationDriftCreate>({
    drift_code: `DRIFT-${asset.asset_code}-${Date.now().toString().slice(-4)}`,
    cloud_asset_id: asset.id,
    attribute_path: '',
    baseline_value: '',
    drifted_value: '',
    drift_severity: 'HIGH',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await cloudSecService.recordDrift(formData);
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to record drift event');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-xl w-full max-w-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between bg-gray-50/50 dark:bg-gray-800/50">
          <div className="flex items-center gap-2">
            <GitCommit className="w-5 h-5 text-amber-600 dark:text-amber-400" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Record Configuration Drift</h2>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg text-gray-400 hover:text-gray-500">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-rose-50 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-800 rounded-xl text-sm text-rose-600 dark:text-rose-400">
              {error}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
              Attribute JSON / Config Path *
            </label>
            <input
              type="text"
              required
              value={formData.attribute_path}
              onChange={(e) => setFormData({ ...formData, attribute_path: e.target.value })}
              placeholder="e.g. ServerSideEncryptionConfiguration.rules[0].applyServerSideEncryptionByDefault"
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm font-mono text-gray-900 dark:text-white focus:ring-2 focus:ring-amber-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
              Drift Severity *
            </label>
            <select
              value={formData.drift_severity}
              onChange={(e) => setFormData({ ...formData, drift_severity: e.target.value as DriftSeverity })}
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-amber-500 focus:outline-none"
            >
              <option value="CRITICAL">Critical (Score: 90.00)</option>
              <option value="HIGH">High (Score: 70.00)</option>
              <option value="MEDIUM">Medium (Score: 40.00)</option>
              <option value="LOW">Low (Score: 15.00)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
              IaC / Baseline Value *
            </label>
            <textarea
              rows={2}
              required
              value={formData.baseline_value}
              onChange={(e) => setFormData({ ...formData, baseline_value: e.target.value })}
              placeholder="e.g. { SSEAlgorithm: 'aws:kms', KMSMasterKeyId: 'arn:aws:kms:...' }"
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm font-mono text-gray-900 dark:text-white focus:ring-2 focus:ring-amber-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
              Detected Drifted Live Value *
            </label>
            <textarea
              rows={2}
              required
              value={formData.drifted_value}
              onChange={(e) => setFormData({ ...formData, drifted_value: e.target.value })}
              placeholder="e.g. null (Encryption disabled manually in console)"
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm font-mono text-gray-900 dark:text-white focus:ring-2 focus:ring-amber-500 focus:outline-none"
            />
          </div>

          <div className="pt-4 border-t border-gray-200 dark:border-gray-800 flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 text-sm font-medium text-white bg-amber-600 hover:bg-amber-700 rounded-xl shadow-sm disabled:opacity-50"
            >
              {loading ? 'Recording...' : 'Record Drift'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
