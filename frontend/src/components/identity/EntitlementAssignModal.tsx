import React, { useState, useEffect } from 'react';
import { X, Shield, AlertOctagon } from 'lucide-react';
import type {
  GovernedIdentity,
  IdentityEntitlement,
  EntitlementAssignmentCreate,
  AssignmentType,
} from '../../types';
import { identityGovernanceService } from '../../lib/identityGovernanceService';

interface EntitlementAssignModalProps {
  isOpen: boolean;
  onClose: () => void;
  identity: GovernedIdentity;
  onSuccess: () => void;
}

export const EntitlementAssignModal: React.FC<EntitlementAssignModalProps> = ({
  isOpen,
  onClose,
  identity,
  onSuccess,
}) => {
  const [entitlements, setEntitlements] = useState<IdentityEntitlement[]>([]);
  const [formData, setFormData] = useState<EntitlementAssignmentCreate>({
    entitlement_id: 0,
    assignment_type: 'DIRECT',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    const fetchEntitlements = async () => {
      try {
        const data = await identityGovernanceService.listEntitlements();
        setEntitlements(data);
        if (data.length > 0) {
          setFormData((prev) => ({ ...prev, entitlement_id: data[0].id }));
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
    if (!formData.entitlement_id) {
      setError('Please select an entitlement');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await identityGovernanceService.assignEntitlement(identity.id, formData);
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to assign entitlement');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-xl w-full max-w-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between bg-gray-50/50 dark:bg-gray-800/50">
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Assign Entitlement to Identity</h2>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg text-gray-400 hover:text-gray-500">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-rose-50 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-800 rounded-xl text-sm text-rose-600 dark:text-rose-400 flex items-start gap-2">
              <AlertOctagon className="w-5 h-5 flex-shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
              Select Entitlement *
            </label>
            <select
              value={formData.entitlement_id}
              onChange={(e) => setFormData({ ...formData, entitlement_id: parseInt(e.target.value) })}
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            >
              {entitlements.map((ent) => (
                <option key={ent.id} value={ent.id}>
                  [{ent.system_type}] {ent.name} - {ent.resource_name} ({ent.permission_scope})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
              Assignment Type
            </label>
            <select
              value={formData.assignment_type}
              onChange={(e) => setFormData({ ...formData, assignment_type: e.target.value as AssignmentType })}
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            >
              <option value="DIRECT">Direct Assignment</option>
              <option value="ROLE_INHERITED">Role Inherited</option>
              <option value="JIT_ELEVATION">Just-In-Time Elevation</option>
            </select>
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
              {loading ? 'Assigning...' : 'Assign Entitlement'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
