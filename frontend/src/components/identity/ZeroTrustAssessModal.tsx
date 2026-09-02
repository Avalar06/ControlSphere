import React, { useState, useEffect } from 'react';
import { X, ShieldCheck, Activity } from 'lucide-react';
import type {
  GovernedIdentity,
  ZeroTrustAssessmentCreate,
  ZeroTrustPreviewResponse,
} from '../../types';
import { identityGovernanceService } from '../../lib/identityGovernanceService';

interface ZeroTrustAssessModalProps {
  isOpen: boolean;
  onClose: () => void;
  identity: GovernedIdentity;
  onSuccess: () => void;
}

export const ZeroTrustAssessModal: React.FC<ZeroTrustAssessModalProps> = ({
  isOpen,
  onClose,
  identity,
  onSuccess,
}) => {
  const [formData, setFormData] = useState<ZeroTrustAssessmentCreate>({
    assessment_code: `ZT-${identity.identity_code}-${Date.now().toString().slice(-4)}`,
    device_health_score: 95.0,
    auth_strength_score: 90.0,
    context_risk_score: 10.0,
    behavioral_anomaly_score: 5.0,
  });
  const [preview, setPreview] = useState<ZeroTrustPreviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    const fetchPreview = async () => {
      try {
        const res = await identityGovernanceService.previewZeroTrust({
          device_health_score: formData.device_health_score,
          auth_strength_score: formData.auth_strength_score,
          context_risk_score: formData.context_risk_score,
          behavioral_anomaly_score: formData.behavioral_anomaly_score,
        });
        setPreview(res);
      } catch (err) {
        console.error('Failed to preview Zero Trust score', err);
      }
    };
    fetchPreview();
  }, [
    isOpen,
    formData.device_health_score,
    formData.auth_strength_score,
    formData.context_risk_score,
    formData.behavioral_anomaly_score,
  ]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await identityGovernanceService.assessZeroTrust(identity.id, formData);
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to record Zero Trust evaluation');
    } finally {
      setLoading(false);
    }
  };

  const getTrustBadge = (trust: string) => {
    switch (trust) {
      case 'HIGH_TRUST':
        return 'bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border-emerald-300 dark:border-emerald-800';
      case 'CONDITIONAL_TRUST':
        return 'bg-blue-100 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border-blue-300 dark:border-blue-800';
      case 'LOW_TRUST':
        return 'bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border-amber-300 dark:border-amber-800';
      default:
        return 'bg-rose-100 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 border-rose-300 dark:border-rose-800';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-xl w-full max-w-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between bg-gray-50/50 dark:bg-gray-800/50">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Continuous Zero Trust Assessment
            </h2>
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

          {/* Realtime Score Preview */}
          {preview && (
            <div className="p-4 bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800/60 rounded-xl flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-blue-700 dark:text-blue-300">
                  Calculated Zero Trust Assurance Score (ZTAS)
                </p>
                <div className="flex items-center gap-3 mt-1">
                  <span className="text-3xl font-bold text-blue-900 dark:text-blue-100">
                    {preview.zero_trust_assurance_score}%
                  </span>
                  <span className={`px-2.5 py-0.5 text-xs font-semibold rounded-full border ${getTrustBadge(preview.trust_level)}`}>
                    {preview.trust_level.replace('_', ' ')}
                  </span>
                </div>
              </div>
              <Activity className="w-8 h-8 text-blue-600 dark:text-blue-400 opacity-80" />
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                Device Health Score (0 - 100, 30% Weight)
              </label>
              <input
                type="number"
                min="0"
                max="100"
                step="1"
                value={formData.device_health_score}
                onChange={(e) => setFormData({ ...formData, device_health_score: parseFloat(e.target.value) || 0 })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                Auth Strength Score (0 - 100, 35% Weight)
              </label>
              <input
                type="number"
                min="0"
                max="100"
                step="1"
                value={formData.auth_strength_score}
                onChange={(e) => setFormData({ ...formData, auth_strength_score: parseFloat(e.target.value) || 0 })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                Context Risk Score (0 - 100, 20% Weight)
              </label>
              <input
                type="number"
                min="0"
                max="100"
                step="1"
                value={formData.context_risk_score}
                onChange={(e) => setFormData({ ...formData, context_risk_score: parseFloat(e.target.value) || 0 })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                Behavioral Anomaly Score (0 - 100, 15% Weight)
              </label>
              <input
                type="number"
                min="0"
                max="100"
                step="1"
                value={formData.behavioral_anomaly_score}
                onChange={(e) => setFormData({ ...formData, behavioral_anomaly_score: parseFloat(e.target.value) || 0 })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />
            </div>
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
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-xl shadow-sm disabled:opacity-50"
            >
              {loading ? 'Evaluating...' : 'Persist Assessment'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
