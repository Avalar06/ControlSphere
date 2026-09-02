import React from 'react';
import { Cloud, ShieldCheck, ShieldAlert, GitCommit } from 'lucide-react';
import type { CloudPostureSummaryResponse } from '../../types';

interface CloudPostureCardProps {
  summary: CloudPostureSummaryResponse | null;
  loading: boolean;
}

export const CloudPostureCard: React.FC<CloudPostureCardProps> = ({ summary, loading }) => {
  if (loading || !summary) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-28 bg-gray-100 dark:bg-gray-800 rounded-xl animate-pulse" />
        ))}
      </div>
    );
  }

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800';
    if (score >= 70) return 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/40 border-amber-200 dark:border-amber-800';
    return 'text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/40 border-rose-200 dark:border-rose-800';
  };

  return (
    <div className="space-y-4 mb-6">
      {/* Top Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Posture Score */}
        <div className={`p-4 rounded-xl border ${getScoreColor(summary.average_posture_score)} flex items-center justify-between`}>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider opacity-80">Avg Posture Score</p>
            <p className="text-3xl font-bold mt-1">{summary.average_posture_score}%</p>
            <p className="text-xs mt-1 opacity-90">
              {summary.compliant_assets_count} of {summary.total_cloud_assets} assets compliant
            </p>
          </div>
          <ShieldCheck className="w-10 h-10 opacity-80" />
        </div>

        {/* Total Assets */}
        <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex items-center justify-between shadow-sm">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">Cloud Assets</p>
            <p className="text-3xl font-bold text-gray-900 dark:text-white mt-1">{summary.total_cloud_assets}</p>
            <div className="flex gap-2 text-xs text-gray-500 mt-1">
              <span className="text-rose-600 font-medium">{summary.non_compliant_assets_count} Non-Compliant</span>
              <span>•</span>
              <span className="text-amber-600 font-medium">{summary.deviated_assets_count} Deviated</span>
            </div>
          </div>
          <Cloud className="w-10 h-10 text-blue-500 dark:text-blue-400" />
        </div>

        {/* Open Findings */}
        <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex items-center justify-between shadow-sm">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">Open CSPM Findings</p>
            <p className="text-3xl font-bold text-gray-900 dark:text-white mt-1">{summary.total_open_findings}</p>
            <p className="text-xs text-rose-600 font-medium mt-1">
              {summary.critical_findings_count} Critical Severity
            </p>
          </div>
          <ShieldAlert className="w-10 h-10 text-rose-500 dark:text-rose-400" />
        </div>

        {/* Configuration Drift & IAM Blast */}
        <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex items-center justify-between shadow-sm">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">Active Drifts</p>
            <p className="text-3xl font-bold text-gray-900 dark:text-white mt-1">{summary.active_drifts_count}</p>
            <p className="text-xs text-purple-600 font-medium mt-1">
              Avg Blast Radius: {summary.average_blast_radius_score}
            </p>
          </div>
          <GitCommit className="w-10 h-10 text-amber-500 dark:text-amber-400" />
        </div>
      </div>
    </div>
  );
};
