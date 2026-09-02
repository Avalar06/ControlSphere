import React, { useState, useEffect } from 'react';
import { X, Clock } from 'lucide-react';
import type { GovernedIdentity, IdentityEntitlement, JITAccessRequestCreate } from '../../types';
import { identityGovernanceService } from '../../lib/identityGovernanceService';

interface JITRequestModalProps {
  isOpen: boolean;
  onClose: () => void;
  identities: GovernedIdentity[];
  onSuccess: () => void;
}

export const JITRequestModal: React.FC<JITRequestModalProps> = ({
  isOpen,
  onClose,
  identities,
  onSuccess,
}) => {
  const [entitlements, setEntitlements] = useState<IdentityEntitlement[]>([]);
  const [formData, setFormData] = useState<JITAccessRequestCreate>({
    request_code: `JIT-${Date.now().toString().slice(-6)}`,
    identity_id: identities[0]?.id || 0,
    entitlement_id: 0,
    requested_duration_minutes: 60,
    business_justification: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    const fetchEntitlements = async () => {
      try {
        const data = await identityGovernanceService.listEntitlements({ is_privileged: true });
        setEntitlements(data);
        if (data.length > 0) {
          setFormData((prev) => ({
            ...prev,
            identity_id: identities[0]?.id || 0,
            entitlement_id: data[0].id,
          }));
        }
      } catch (err) {
        console.error('Failed to load privileged entitlements', err);
      }
    };
    fetchEntitlements();
  }, [isOpen, identities]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.identity_id || !formData.entitlement_id) {
      setError('Please select an identity and privileged entitlement');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await identityGovernanceService.createJITRequest(formData);
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to submit JIT request');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-xl w-full max-w-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between bg-gray-50/50 dark:bg-gray-800/50">
          <div className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-amber-600 dark:text-amber-400" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Request Just-In-Time (JIT) Privileged Access
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

          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
              Governed Identity *
            </label>
            <select
              value={formData.identity_id}
              onChange={(e) => setFormData({ ...formData, identity_id: parseInt(e.target.value) })}
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-amber-500 focus:outline-none"
            >
              {identities.map((id) => (
                <option key={id.id} value={id.id}>
                  {id.full_name} ({id.email}) - [{id.identity_code}]
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
              Privileged Entitlement *
            </label>
            <select
              value={formData.entitlement_id}
              onChange={(e) => setFormData({ ...formData, entitlement_id: parseInt(e.target.value) })}
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-amber-500 focus:outline-none"
            >
              {entitlements.map((ent) => (
                <option key={ent.id} value={ent.id}>
                  [{ent.system_type}] {ent.name} - {ent.resource_name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
              Requested Elevation Window (Minutes, max 480) *
            </label>
            <input
              type="number"
              min="15"
              max="480"
              step="15"
              value={formData.requested_duration_minutes}
              onChange={(e) => setFormData({ ...formData, requested_duration_minutes: parseInt(e.target.value) || 60 })}
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-amber-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
              Business Justification / Emergency Ticket ID *
            </label>
            <textarea
              rows={3}
              required
              value={formData.business_justification}
              onChange={(e) => setFormData({ ...formData, business_justification: e.target.value })}
              placeholder="e.g. Mitigating production outage incident SEV-1 ticket INC-8924 database lock"
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-amber-500 focus:outline-none"
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
              {loading ? 'Submitting...' : 'Submit Request'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
