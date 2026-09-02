import React, { useState, useEffect } from 'react';
import { X, Cpu, Key } from 'lucide-react';
import type {
  CloudAsset,
  CloudIAMBlastRadiusCreate,
  CloudIAMBlastRadiusPreviewResponse,
  DataAccessScope,
} from '../../types';
import { cloudSecService } from '../../lib/cloudSecService';

interface BlastRadiusModalProps {
  isOpen: boolean;
  onClose: () => void;
  asset: CloudAsset;
  onSuccess: () => void;
}

export const BlastRadiusModal: React.FC<BlastRadiusModalProps> = ({ isOpen, onClose, asset, onSuccess }) => {
  const [formData, setFormData] = useState<CloudIAMBlastRadiusCreate>({
    analysis_code: `BLAST-${asset.asset_code}-${Date.now().toString().slice(-4)}`,
    cloud_asset_id: asset.id,
    iam_principal_arn: '',
    effective_permissions_count: 5,
    admin_privilege_granted: false,
    cross_account_access: false,
    data_access_scope: 'RESTRICTED_READ',
  });
  const [preview, setPreview] = useState<CloudIAMBlastRadiusPreviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    const fetchPreview = async () => {
      try {
        const res = await cloudSecService.previewBlastRadius({
          effective_permissions_count: formData.effective_permissions_count,
          admin_privilege_granted: formData.admin_privilege_granted,
          cross_account_access: formData.cross_account_access,
          data_access_scope: formData.data_access_scope,
        });
        setPreview(res);
      } catch (err) {
        console.error('Failed to preview blast radius', err);
      }
    };
    fetchPreview();
  }, [
    isOpen,
    formData.effective_permissions_count,
    formData.admin_privilege_granted,
    formData.cross_account_access,
    formData.data_access_scope,
  ]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await cloudSecService.analyzeBlastRadius(formData);
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to record blast radius analysis');
    } finally {
      setLoading(false);
    }
  };

  const getBandBadge = (band: string) => {
    switch (band) {
      case 'CRITICAL':
        return 'bg-rose-100 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 border-rose-300 dark:border-rose-800';
      case 'HIGH':
        return 'bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border-amber-300 dark:border-amber-800';
      case 'MODERATE':
        return 'bg-blue-100 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border-blue-300 dark:border-blue-800';
      default:
        return 'bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border-emerald-300 dark:border-emerald-800';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-xl w-full max-w-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between bg-gray-50/50 dark:bg-gray-800/50">
          <div className="flex items-center gap-2">
            <Key className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Calculate IAM Blast Radius</h2>
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

          {/* Realtime Calculation Preview */}
          {preview && (
            <div className="p-4 bg-purple-50 dark:bg-purple-950/30 border border-purple-200 dark:border-purple-800/60 rounded-xl flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-purple-700 dark:text-purple-300">
                  Authoritative Blast Radius Index
                </p>
                <div className="flex items-center gap-3 mt-1">
                  <span className="text-3xl font-bold text-purple-900 dark:text-purple-100">
                    {preview.blast_radius_index}
                  </span>
                  <span className={`px-2.5 py-0.5 text-xs font-semibold rounded-full border ${getBandBadge(preview.risk_band)}`}>
                    {preview.risk_band}
                  </span>
                </div>
              </div>
              <Cpu className="w-8 h-8 text-purple-600 dark:text-purple-400 opacity-80" />
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
              IAM Principal ARN *
            </label>
            <input
              type="text"
              required
              value={formData.iam_principal_arn}
              onChange={(e) => setFormData({ ...formData, iam_principal_arn: e.target.value })}
              placeholder="arn:aws:iam::123456789012:role/DataPipelineServiceRole"
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm font-mono text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500 focus:outline-none"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                Effective Permissions Count
              </label>
              <input
                type="number"
                min="0"
                max="1000"
                value={formData.effective_permissions_count}
                onChange={(e) => setFormData({ ...formData, effective_permissions_count: parseInt(e.target.value) || 0 })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                Data Access Scope
              </label>
              <select
                value={formData.data_access_scope}
                onChange={(e) => setFormData({ ...formData, data_access_scope: e.target.value as DataAccessScope })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500 focus:outline-none"
              >
                <option value="METADATA_ONLY">Metadata Only (+0)</option>
                <option value="RESTRICTED_READ">Restricted Read (+10)</option>
                <option value="FULL_DATASTORE">Full Datastore (+30)</option>
              </select>
            </div>
          </div>

          <div className="space-y-2 pt-2">
            <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.admin_privilege_granted}
                onChange={(e) => setFormData({ ...formData, admin_privilege_granted: e.target.checked })}
                className="rounded border-gray-300 text-purple-600 focus:ring-purple-500 w-4 h-4"
              />
              <span className="font-medium">Administrator Privilege Granted (*:* access) (+50 Penalty)</span>
            </label>

            <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.cross_account_access}
                onChange={(e) => setFormData({ ...formData, cross_account_access: e.target.checked })}
                className="rounded border-gray-300 text-purple-600 focus:ring-purple-500 w-4 h-4"
              />
              <span>Cross-Account Trust Relationship Configured (+20 Penalty)</span>
            </label>
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
              className="px-4 py-2 text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 rounded-xl shadow-sm disabled:opacity-50"
            >
              {loading ? 'Evaluating...' : 'Persist Analysis'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
