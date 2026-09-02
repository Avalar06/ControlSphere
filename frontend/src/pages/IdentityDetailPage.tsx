import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  AlertOctagon,
  Plus,
  Activity,
} from 'lucide-react';
import { identityGovernanceService } from '../lib/identityGovernanceService';
import { EntitlementAssignModal } from '../components/identity/EntitlementAssignModal';
import { ZeroTrustAssessModal } from '../components/identity/ZeroTrustAssessModal';
import type {
  GovernedIdentity,
  EntitlementAssignment,
  SoDConflictViolation,
} from '../types';

export const IdentityDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const identityId = parseInt(id || '0');

  const [identity, setIdentity] = useState<GovernedIdentity | null>(null);
  const [assignments, setAssignments] = useState<EntitlementAssignment[]>([]);
  const [violations, setViolations] = useState<SoDConflictViolation[]>([]);
  const [loading, setLoading] = useState(true);

  const [isAssignModalOpen, setIsAssignModalOpen] = useState(false);
  const [isZeroTrustModalOpen, setIsZeroTrustModalOpen] = useState(false);

  const fetchIdentityData = async () => {
    if (!identityId) return;
    setLoading(true);
    try {
      const [idRes, assignRes, violRes] = await Promise.all([
        identityGovernanceService.getIdentity(identityId),
        identityGovernanceService.listIdentityAssignments(identityId),
        identityGovernanceService.listSoDViolations({ identity_id: identityId }),
      ]);
      setIdentity(idRes);
      setAssignments(assignRes);
      setViolations(violRes);
    } catch (err) {
      console.error('Failed to load identity details', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIdentityData();
  }, [identityId]);

  const handleSuspend = async () => {
    if (!identity) return;
    const confirm = window.confirm('Are you sure you want to SUSPEND this governed identity?');
    if (!confirm) return;
    try {
      await identityGovernanceService.updateIdentity(identity.id, {
        employment_status: 'SUSPENDED',
      });
      fetchIdentityData();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to suspend identity');
    }
  };

  if (loading || !identity) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/identity-governance')}
          className="inline-flex items-center gap-2 text-sm font-medium text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Identity Governance
        </button>

        <div className="flex items-center gap-3">
          {identity.employment_status === 'ACTIVE' && (
            <button
              onClick={handleSuspend}
              className="px-3 py-1.5 text-xs font-medium text-rose-700 dark:text-rose-300 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 rounded-xl hover:bg-rose-100 dark:hover:bg-rose-900 transition-colors"
            >
              Suspend Identity
            </button>
          )}
        </div>
      </div>

      {/* Hero Banner */}
      <div className="p-6 bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{identity.full_name}</h1>
              <span className="text-xs px-2.5 py-1 font-semibold rounded-full bg-indigo-50 text-indigo-700 dark:bg-indigo-950/50 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
                {identity.identity_type.replace('_', ' ')}
              </span>
              <span
                className={`text-xs px-2 py-0.5 rounded font-medium ${
                  identity.employment_status === 'ACTIVE'
                    ? 'bg-emerald-50 text-emerald-700'
                    : 'bg-gray-100 text-gray-700'
                }`}
              >
                {identity.employment_status}
              </span>
            </div>
            <p className="text-xs font-mono text-gray-500 mt-1">
              {identity.email} • Code: {identity.identity_code} • Department: {identity.department || 'N/A'}
            </p>
          </div>

          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-xs uppercase font-semibold text-gray-500">Identity Risk Score (IRS)</p>
              <p className="text-3xl font-bold text-gray-900 dark:text-white mt-0.5">{identity.risk_score.toFixed(1)}</p>
            </div>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-3 pt-4 border-t border-gray-100 dark:border-gray-800">
          <button
            onClick={() => setIsAssignModalOpen(true)}
            className="px-3 py-1.5 text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-sm flex items-center gap-1.5"
          >
            <Plus className="w-3.5 h-3.5" />
            Assign Entitlement
          </button>
          <button
            onClick={() => setIsZeroTrustModalOpen(true)}
            className="px-3 py-1.5 text-xs font-medium text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800 rounded-xl hover:bg-blue-100 flex items-center gap-1.5"
          >
            <Activity className="w-3.5 h-3.5" />
            Evaluate Zero Trust Score
          </button>
        </div>
      </div>

      {/* SoD Violations Alert Banner if any */}
      {violations.length > 0 && (
        <div className="p-4 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 rounded-2xl flex items-start gap-3">
          <AlertOctagon className="w-5 h-5 text-rose-600 dark:text-rose-400 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-rose-900 dark:text-rose-200 text-sm">
              Segregation of Duties (SoD) Violations Detected ({violations.length})
            </h3>
            <p className="text-xs text-rose-700 dark:text-rose-300 mt-0.5">
              This identity possesses conflicting entitlements that violate enterprise authorization controls.
            </p>
          </div>
        </div>
      )}

      {/* Assigned Entitlements Table */}
      <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-gray-200 dark:border-gray-800 flex justify-between items-center bg-gray-50/50 dark:bg-gray-800/50">
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">Assigned Entitlements & Permissions</h3>
            <p className="text-xs text-gray-500 mt-0.5">Direct and role-inherited permission grants.</p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-gray-600 dark:text-gray-400">
            <thead className="text-xs uppercase bg-gray-50 dark:bg-gray-800/50 text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-800">
              <tr>
                <th className="px-4 py-3 font-semibold">Entitlement Name / Code</th>
                <th className="px-4 py-3 font-semibold">Target System</th>
                <th className="px-4 py-3 font-semibold">Resource / Scope</th>
                <th className="px-4 py-3 font-semibold">Assignment Type</th>
                <th className="px-4 py-3 font-semibold">Risk Weight</th>
                <th className="px-4 py-3 font-semibold">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
              {assignments.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                    No entitlements currently assigned.
                  </td>
                </tr>
              ) : (
                assignments.map((a) => (
                  <tr key={a.id} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/50">
                    <td className="px-4 py-3">
                      <div className="font-semibold text-gray-900 dark:text-white">{a.entitlement?.name}</div>
                      <div className="text-xs font-mono text-gray-500">{a.entitlement?.entitlement_code}</div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 text-xs font-mono font-semibold rounded bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200">
                        {a.entitlement?.system_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs">
                      <div className="font-medium text-gray-900 dark:text-white">{a.entitlement?.resource_name}</div>
                      <div className="text-gray-500 font-mono">{a.entitlement?.permission_scope}</div>
                    </td>
                    <td className="px-4 py-3 text-xs font-semibold">{a.assignment_type}</td>
                    <td className="px-4 py-3 font-bold text-gray-900 dark:text-white">
                      {a.entitlement?.risk_weight.toFixed(1)}
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs px-2 py-0.5 font-semibold rounded-full bg-emerald-100 text-emerald-800">
                        Active
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modals */}
      <EntitlementAssignModal
        isOpen={isAssignModalOpen}
        onClose={() => setIsAssignModalOpen(false)}
        identity={identity}
        onSuccess={fetchIdentityData}
      />
      <ZeroTrustAssessModal
        isOpen={isZeroTrustModalOpen}
        onClose={() => setIsZeroTrustModalOpen(false)}
        identity={identity}
        onSuccess={fetchIdentityData}
      />
    </div>
  );
};
