import React from 'react';
import { Users, Shield, AlertOctagon, ShieldAlert } from 'lucide-react';
import type { IdentityPostureSummaryResponse } from '../../types';

interface IdentityPostureCardProps {
  summary: IdentityPostureSummaryResponse | null;
  loading: boolean;
}

export const IdentityPostureCard: React.FC<IdentityPostureCardProps> = ({ summary, loading }) => {
  if (loading || !summary) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-28 bg-gray-100 dark:bg-gray-800 rounded-xl animate-pulse" />
        ))}
      </div>
    );
  }

  const getRiskColor = (score: number) => {
    if (score <= 30) return 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800';
    if (score <= 60) return 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/40 border-amber-200 dark:border-amber-800';
    return 'text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/40 border-rose-200 dark:border-rose-800';
  };

  return (
    <div className="space-y-4 mb-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Identity Risk Score */}
        <div className={`p-4 rounded-xl border ${getRiskColor(summary.average_identity_risk_score)} flex items-center justify-between`}>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider opacity-80">Avg Identity Risk (IRS)</p>
            <p className="text-3xl font-bold mt-1">{summary.average_identity_risk_score.toFixed(1)}</p>
            <p className="text-xs mt-1 opacity-90">
              {summary.high_risk_identities_count} high-risk identities
            </p>
          </div>
          <ShieldAlert className="w-10 h-10 opacity-80" />
        </div>

        {/* Governed Identities */}
        <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex items-center justify-between shadow-sm">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">Total Identities</p>
            <p className="text-3xl font-bold text-gray-900 dark:text-white mt-1">{summary.total_identities}</p>
            <p className="text-xs text-purple-600 font-medium mt-1">
              {summary.privileged_identities_count} Privileged Accounts
            </p>
          </div>
          <Users className="w-10 h-10 text-indigo-500 dark:text-indigo-400" />
        </div>

        {/* Zero Trust Assurance */}
        <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex items-center justify-between shadow-sm">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">Zero Trust Assurance</p>
            <p className="text-3xl font-bold text-gray-900 dark:text-white mt-1">{summary.average_zero_trust_score.toFixed(1)}%</p>
            <p className="text-xs text-blue-600 font-medium mt-1">
              Continuous Risk-Engine
            </p>
          </div>
          <Shield className="w-10 h-10 text-blue-500 dark:text-blue-400" />
        </div>

        {/* SoD Violations & Pending Reviews */}
        <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex items-center justify-between shadow-sm">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">Active SoD Violations</p>
            <p className="text-3xl font-bold text-rose-600 dark:text-rose-400 mt-1">{summary.active_sod_violations_count}</p>
            <p className="text-xs text-amber-600 font-medium mt-1">
              {summary.pending_certifications_count} Pending Certifications
            </p>
          </div>
          <AlertOctagon className="w-10 h-10 text-rose-500 dark:text-rose-400" />
        </div>
      </div>
    </div>
  );
};
