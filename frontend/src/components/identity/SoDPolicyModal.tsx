import React, { useState, useEffect } from 'react';
import { X, AlertOctagon } from 'lucide-react';
import type { IdentityEntitlement, SoDConflictPolicyCreate, SoDPolicySeverity } from '../../types';
import { identityGovernanceService } from '../../lib/identityGovernanceService';

interface SoDPolicyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const SoDPolicyModal: React.FC<SoDPolicyModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [entitlements, setEntitlements] = useState<IdentityEntitlement[]>([]);
  const [formData, setFormData] = useState<SoDConflictPolicyCreate>({
    policy_code: '',
    name: '',
    entitlement_a_id: 0,
    entitlement_b_id: 0,
    severity: 'HIGH',
    description: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    const fetchEntitlements = async () => {
      try {
        const data = await identityGovernanceService.listEntitlements();
        setEntitlements(data);
        if (data.length >= 2) {
          setFormData((prev) => ({
            ...prev,
            entitlement_a_id: data[0].id,
            entitlement_b_id: data[1].id,
          }));
        }
      } catch (err) {
        console.error('Failed to load entitlements', err);
      }
    };
    fetchEntitlements();
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (formData.entitlement_a_id === formData.entitlement_b_id) {
      setError('Entitlement A and Entitlement B must be distinct for Segregation of Duties.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await identityGovernanceService.createSoDPolicy(formData);
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to create SoD policy');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-xl w-full max-w-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between bg-gray-50/50 dark:bg-gray-800/50">
          <div className="flex items-center gap-2">
            <AlertOctagon className="w-5 h-5 text-rose-600 dark:text-rose-400" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Create Segregation of Duties (SoD) Policy
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

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                Policy Code *
              </label>
              <input
                type="text"
                required
                value={formData.policy_code}
                onChange={(e) => setFormData({ ...formData, policy_code: e.target.value })}
                placeholder="e.g. SOD-FIN-PAYROLL-01"
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-rose-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                Severity *
              </label>
              <select
                value={formData.severity}
                onChange={(e) => setFormData({ ...formData, severity: e.target.value as SoDPolicySeverity })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-rose-500 focus:outline-none"
              >
                <option value="CRITICAL">Critical Violation</option>
                <option value="HIGH">High Severity</option>
                <option value="MEDIUM">Medium Severity</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
              Policy Name *
            </label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="e.g. Accounts Payable Creator vs Invoice Approver"
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-rose-500 focus:outline-none"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                Conflicting Entitlement A *
              </label>
              <select
                value={formData.entitlement_a_id}
                onChange={(e) => setFormData({ ...formData, entitlement_a_id: parseInt(e.target.value) })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-rose-500 focus:outline-none"
              >
                {entitlements.map((ent) => (
                  <option key={ent.id} value={ent.id}>
                    [{ent.system_type}] {ent.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                Conflicting Entitlement B *
              </label>
              <select
                value={formData.entitlement_b_id}
                onChange={(e) => setFormData({ ...formData, entitlement_b_id: parseInt(e.target.value) })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-rose-500 focus:outline-none"
              >
                {entitlements.map((ent) => (
                  <option key={ent.id} value={ent.id}>
                    [{ent.system_type}] {ent.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
              Description & Business Impact
            </label>
            <textarea
              rows={2}
              value={formData.description || ''}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Why possessing both entitlements creates toxic authorization risk..."
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
              {loading ? 'Creating...' : 'Create Policy'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
