import React, { useState } from 'react';
import { X, KeyRound } from 'lucide-react';
import type { IdentityEntitlementCreate, SystemType } from '../../types';

interface IdentityEntitlementModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: IdentityEntitlementCreate) => Promise<void>;
}

export const IdentityEntitlementModal: React.FC<IdentityEntitlementModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
}) => {
  const [formData, setFormData] = useState<IdentityEntitlementCreate>({
    entitlement_code: '',
    name: '',
    system_type: 'AWS_IAM',
    resource_name: '',
    permission_scope: '',
    is_privileged: false,
    is_high_risk: false,
    risk_weight: 1.0,
    description: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await onSubmit(formData);
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to create entitlement');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-xl w-full max-w-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between bg-gray-50/50 dark:bg-gray-800/50">
          <div className="flex items-center gap-2">
            <KeyRound className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Create Entitlement Catalog Item</h2>
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
                Entitlement Code *
              </label>
              <input
                type="text"
                required
                value={formData.entitlement_code}
                onChange={(e) => setFormData({ ...formData, entitlement_code: e.target.value })}
                placeholder="e.g. AWS-IAM-ADMIN"
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                Name *
              </label>
              <input
                type="text"
                required
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="e.g. AdministratorAccess"
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                Target System Type *
              </label>
              <select
                value={formData.system_type}
                onChange={(e) => setFormData({ ...formData, system_type: e.target.value as SystemType })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              >
                <option value="AWS_IAM">AWS IAM</option>
                <option value="AZURE_RBAC">Azure RBAC / Entra ID</option>
                <option value="OKTA">Okta Directory</option>
                <option value="ACTIVE_DIRECTORY">Active Directory (LDAP)</option>
                <option value="DATABASE_ROLE">Database Role / Schema</option>
                <option value="SAAS_APPLICATION">SaaS Application Scope</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
                Risk Weight (1.0 to 10.0)
              </label>
              <input
                type="number"
                min="1.0"
                max="10.0"
                step="0.5"
                value={formData.risk_weight}
                onChange={(e) => setFormData({ ...formData, risk_weight: parseFloat(e.target.value) || 1.0 })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
              Resource Name / Target *
            </label>
            <input
              type="text"
              required
              value={formData.resource_name}
              onChange={(e) => setFormData({ ...formData, resource_name: e.target.value })}
              placeholder="e.g. Production AWS Account 123456789012"
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
              Permission Scope *
            </label>
            <input
              type="text"
              required
              value={formData.permission_scope}
              onChange={(e) => setFormData({ ...formData, permission_scope: e.target.value })}
              placeholder="e.g. *:* or ReadOnlyAccess"
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            />
          </div>

          <div className="flex gap-6 pt-2">
            <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.is_privileged}
                onChange={(e) => setFormData({ ...formData, is_privileged: e.target.checked })}
                className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 w-4 h-4"
              />
              <span className="font-semibold text-purple-600">Privileged Entitlement</span>
            </label>

            <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.is_high_risk}
                onChange={(e) => setFormData({ ...formData, is_high_risk: e.target.checked })}
                className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 w-4 h-4"
              />
              <span className="text-rose-600 font-medium">High Risk Flag</span>
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
              className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-sm disabled:opacity-50"
            >
              {loading ? 'Creating...' : 'Create Entitlement'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
