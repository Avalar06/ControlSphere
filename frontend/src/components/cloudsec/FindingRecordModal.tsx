import React, { useState, useEffect } from 'react';
import { X, ShieldAlert } from 'lucide-react';
import type { CloudAsset, CloudBenchmarkRule, CloudSecurityFindingCreate, EvaluationStatus, RuleSeverity } from '../../types';
import { cloudSecService } from '../../lib/cloudSecService';

interface FindingRecordModalProps {
  isOpen: boolean;
  onClose: () => void;
  asset: CloudAsset;
  onSuccess: () => void;
}

export const FindingRecordModal: React.FC<FindingRecordModalProps> = ({ isOpen, onClose, asset, onSuccess }) => {
  const [rules, setRules] = useState<CloudBenchmarkRule[]>([]);
  const [formData, setFormData] = useState<CloudSecurityFindingCreate>({
    finding_code: `FIND-${asset.asset_code}-${Date.now().toString().slice(-4)}`,
    cloud_asset_id: asset.id,
    rule_id: 0,
    evaluation_status: 'FAILED',
    severity: 'HIGH',
    actual_value: '',
    expected_value: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    const fetchRules = async () => {
      try {
        const data = await cloudSecService.listRules();
        setRules(data);
        if (data.length > 0) {
          setFormData((prev) => ({ ...prev, rule_id: data[0].id }));
        }
      } catch (err) {
        console.error('Failed to load rules', err);
      }
    };
    fetchRules();
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.rule_id) {
      setError('Please select a benchmark check rule');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await cloudSecService.recordFinding(formData);
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to record finding');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-xl w-full max-w-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between bg-gray-50/50 dark:bg-gray-800/50">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-rose-600 dark:text-rose-400" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Record CSPM Finding</h2>
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
              Benchmark Rule *
            </label>
            <select
              value={formData.rule_id}
              onChange={(e) => {
                const selectedRule = rules.find((r) => r.id === parseInt(e.target.value));
                setFormData({
                  ...formData,
                  rule_id: parseInt(e.target.value),
                  severity: selectedRule ? selectedRule.severity : formData.severity,
                });
              }}
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-rose-500 focus:outline-none"
            >
              {rules.length === 0 ? (
                <option value={0}>No rules available</option>
              ) : (
                rules.map((r) => (
                  <option key={r.id} value={r.id}>
                    [{r.rule_code}] {r.title} ({r.severity})
                  </option>
                ))
              )}
            </select>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                Evaluation Status *
              </label>
              <select
                value={formData.evaluation_status}
                onChange={(e) => setFormData({ ...formData, evaluation_status: e.target.value as EvaluationStatus })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-rose-500 focus:outline-none"
              >
                <option value="FAILED">FAILED (Non-Compliant)</option>
                <option value="PASSED">PASSED (Compliant)</option>
                <option value="SUPPRESSED">SUPPRESSED (Risk Accepted)</option>
                <option value="REMEDIATED">REMEDIATED (Resolved)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                Severity *
              </label>
              <select
                value={formData.severity}
                onChange={(e) => setFormData({ ...formData, severity: e.target.value as RuleSeverity })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-rose-500 focus:outline-none"
              >
                <option value="CRITICAL">Critical (-25 Posture Penalty)</option>
                <option value="HIGH">High (-15 Posture Penalty)</option>
                <option value="MEDIUM">Medium (-8 Posture Penalty)</option>
                <option value="LOW">Low (-3 Posture Penalty)</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
              Actual Configuration Value
            </label>
            <textarea
              rows={2}
              value={formData.actual_value || ''}
              onChange={(e) => setFormData({ ...formData, actual_value: e.target.value })}
              placeholder="e.g. port 22 open to 0.0.0.0/0, PublicRead enabled"
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-rose-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
              Expected Baseline Value
            </label>
            <textarea
              rows={2}
              value={formData.expected_value || ''}
              onChange={(e) => setFormData({ ...formData, expected_value: e.target.value })}
              placeholder="e.g. port 22 restricted to corporate bastion, PublicAccessBlock enabled"
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-rose-500 focus:outline-none"
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
              className="px-4 py-2 text-sm font-medium text-white bg-rose-600 hover:bg-rose-700 rounded-xl shadow-sm disabled:opacity-50"
            >
              {loading ? 'Recording...' : 'Record Finding'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
