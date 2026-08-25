import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  ShieldAlert,
  Plus,
  Search,
  ArrowRight,
  TrendingDown,
  AlertTriangle,
  Clock,
  Layers,
} from 'lucide-react';
import { riskService } from '../lib/riskService';
import type { RiskCreatePayload } from '../lib/riskService';
import type {
  RiskCategory,
  RiskSource,
  RiskStatus,
  RiskTreatmentStrategy,
} from '../types';

export const RisksPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<RiskStatus | ''>('');
  const [bandFilter, setBandFilter] = useState('');
  const [appetiteFilter, setAppetiteFilter] = useState('');
  const [treatmentFilter, setTreatmentFilter] = useState<RiskTreatmentStrategy | ''>('');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  // Form State
  const [formData, setFormData] = useState<RiskCreatePayload>({
    title: '',
    description: '',
    risk_category: 'CYBERSECURITY',
    risk_source: 'INTERNAL_AUDIT',
    inherent_impact: 3,
    inherent_likelihood: 3,
    target_risk_band: 'MODERATE',
    treatment_strategy: 'NOT_SPECIFIED',
    treatment_plan: '',
    treatment_due_date: '',
  });

  const { data: stats, isLoading: isStatsLoading } = useQuery({
    queryKey: ['riskStats'],
    queryFn: riskService.getStats,
  });

  const { data: risks = [], isLoading: isRisksLoading } = useQuery({
    queryKey: [
      'risks',
      statusFilter,
      bandFilter,
      appetiteFilter,
      treatmentFilter,
      search,
    ],
    queryFn: () =>
      riskService.listRisks({
        status: statusFilter || undefined,
        inherent_band: bandFilter || undefined,
        appetite_status: appetiteFilter || undefined,
        treatment_strategy: treatmentFilter || undefined,
        search: search || undefined,
      }),
  });

  const createMutation = useMutation({
    mutationFn: riskService.createRisk,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['risks'] });
      queryClient.invalidateQueries({ queryKey: ['riskStats'] });
      queryClient.invalidateQueries({ queryKey: ['riskHeatmap'] });
      setIsCreateModalOpen(false);
      setFormData({
        title: '',
        description: '',
        risk_category: 'CYBERSECURITY',
        risk_source: 'INTERNAL_AUDIT',
        inherent_impact: 3,
        inherent_likelihood: 3,
        target_risk_band: 'MODERATE',
        treatment_strategy: 'NOT_SPECIFIED',
        treatment_plan: '',
        treatment_due_date: '',
      });
    },
  });

  const getBandBadge = (band: string) => {
    switch (band) {
      case 'CRITICAL':
        return 'bg-red-950/60 text-red-400 border-red-800/80';
      case 'HIGH':
        return 'bg-amber-950/60 text-amber-400 border-amber-800/80';
      case 'MODERATE':
        return 'bg-yellow-950/60 text-yellow-400 border-yellow-800/80';
      default:
        return 'bg-emerald-950/60 text-emerald-400 border-emerald-800/80';
    }
  };

  const getAppetiteBadge = (status: string) => {
    switch (status) {
      case 'ABOVE_APPETITE':
        return 'bg-red-900/40 text-red-300 border-red-700/60';
      case 'NEAR_LIMIT':
        return 'bg-yellow-900/40 text-yellow-300 border-yellow-700/60';
      default:
        return 'bg-emerald-900/40 text-emerald-300 border-emerald-700/60';
    }
  };

  const getStatusBadge = (status: RiskStatus) => {
    switch (status) {
      case 'CLOSED':
        return 'bg-slate-800 text-slate-400 border-slate-700';
      case 'ACCEPTED':
        return 'bg-purple-950/60 text-purple-400 border-purple-800/80';
      case 'MONITORING':
        return 'bg-blue-950/60 text-blue-400 border-blue-800/80';
      case 'MITIGATING':
        return 'bg-cyan-950/60 text-cyan-400 border-cyan-800/80';
      case 'TREATMENT_PLANNED':
        return 'bg-indigo-950/60 text-indigo-400 border-indigo-800/80';
      case 'ASSESSED':
        return 'bg-yellow-950/60 text-yellow-400 border-yellow-800/80';
      default:
        return 'bg-slate-900 text-slate-300 border-slate-700';
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
            <ShieldAlert className="w-6 h-6 text-indigo-400" />
            Enterprise Risk Register
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Deterministic inherent vs residual risk evaluation, appetite alignment, and mitigation traceability.
          </p>
        </div>
        <button
          onClick={() => setIsCreateModalOpen(true)}
          className="flex items-center justify-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg shadow-sm transition-colors cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          New Risk
        </button>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Total Identified Risks</span>
            <Layers className="w-4 h-4 text-indigo-400" />
          </div>
          <p className="text-2xl font-bold text-slate-100 mt-2">
            {isStatsLoading ? '...' : stats?.total_risks ?? 0}
          </p>
          <div className="flex items-center gap-2 mt-2 text-xs text-slate-400">
            <span className="text-red-400 font-semibold">{stats?.critical_inherent_count ?? 0} Critical</span>
            <span>•</span>
            <span className="text-amber-400 font-semibold">{stats?.high_inherent_count ?? 0} High</span>
          </div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Above Risk Appetite</span>
            <AlertTriangle className="w-4 h-4 text-red-400" />
          </div>
          <p className="text-2xl font-bold text-red-400 mt-2">
            {isStatsLoading ? '...' : stats?.above_appetite_count ?? 0}
          </p>
          <p className="text-xs text-slate-400 mt-2">
            {stats?.near_limit_count ?? 0} near acceptable limit
          </p>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Risk Reduction</span>
            <TrendingDown className="w-4 h-4 text-emerald-400" />
          </div>
          <p className="text-2xl font-bold text-emerald-400 mt-2">
            {isStatsLoading ? '...' : `${stats?.inherent_vs_residual_reduction ?? 0}%`}
          </p>
          <p className="text-xs text-slate-400 mt-2">
            Inherent to residual score delta
          </p>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Overdue Treatments</span>
            <Clock className="w-4 h-4 text-amber-400" />
          </div>
          <p className="text-2xl font-bold text-amber-400 mt-2">
            {isStatsLoading ? '...' : stats?.overdue_treatments_count ?? 0}
          </p>
          <p className="text-xs text-slate-400 mt-2">
            {stats?.due_soon_treatments_count ?? 0} due within 7 days
          </p>
        </div>
      </div>

      {/* Filters and Search Bar */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[240px]">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search risks by title, description, or treatment..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        <select
          value={bandFilter}
          onChange={(e) => setBandFilter(e.target.value)}
          className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-300 focus:outline-none focus:border-indigo-500"
        >
          <option value="">All Inherent Bands</option>
          <option value="CRITICAL">Critical (17-25)</option>
          <option value="HIGH">High (10-16)</option>
          <option value="MODERATE">Moderate (5-9)</option>
          <option value="LOW">Low (1-4)</option>
        </select>

        <select
          value={appetiteFilter}
          onChange={(e) => setAppetiteFilter(e.target.value)}
          className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-300 focus:outline-none focus:border-indigo-500"
        >
          <option value="">All Appetite Statuses</option>
          <option value="ABOVE_APPETITE">Above Appetite</option>
          <option value="NEAR_LIMIT">Near Limit</option>
          <option value="WITHIN_APPETITE">Within Appetite</option>
        </select>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as RiskStatus)}
          className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-300 focus:outline-none focus:border-indigo-500"
        >
          <option value="">All Statuses</option>
          <option value="IDENTIFIED">Identified</option>
          <option value="ASSESSED">Assessed</option>
          <option value="TREATMENT_PLANNED">Treatment Planned</option>
          <option value="MITIGATING">Mitigating</option>
          <option value="MONITORING">Monitoring</option>
          <option value="ACCEPTED">Accepted</option>
          <option value="CLOSED">Closed</option>
        </select>

        <select
          value={treatmentFilter}
          onChange={(e) => setTreatmentFilter(e.target.value as RiskTreatmentStrategy)}
          className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-300 focus:outline-none focus:border-indigo-500"
        >
          <option value="">All Treatment Strategies</option>
          <option value="MITIGATE">Mitigate</option>
          <option value="TRANSFER">Transfer</option>
          <option value="AVOID">Avoid</option>
          <option value="ACCEPT">Accept</option>
        </select>
      </div>

      {/* Risks Table */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-950/50 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                <th className="py-3 px-4">Risk Title & Details</th>
                <th className="py-3 px-4">Category</th>
                <th className="py-3 px-4">Inherent Risk</th>
                <th className="py-3 px-4">Residual Risk</th>
                <th className="py-3 px-4">Appetite Status</th>
                <th className="py-3 px-4">Treatment</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-sm">
              {isRisksLoading ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-500">
                    Loading enterprise risk register...
                  </td>
                </tr>
              ) : risks.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-500">
                    No risk items match the current filters.
                  </td>
                </tr>
              ) : (
                risks.map((risk) => (
                  <tr key={risk.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3 px-4 max-w-xs">
                      <Link
                        to={`/risks/${risk.id}`}
                        className="font-medium text-slate-200 hover:text-indigo-400 transition-colors block truncate"
                      >
                        {risk.title}
                      </Link>
                      <p className="text-xs text-slate-400 line-clamp-1 mt-0.5">
                        {risk.description}
                      </p>
                      <div className="flex items-center gap-2 mt-1 text-[11px] text-slate-500">
                        <span>{risk.linked_controls_count} controls</span>
                        <span>•</span>
                        <span>{risk.linked_findings_count} findings</span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-xs font-medium text-slate-300">
                      {risk.risk_category}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold border ${getBandBadge(
                          risk.inherent_band
                        )}`}
                      >
                        {risk.inherent_score} ({risk.inherent_band})
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      {risk.residual_score !== null && risk.residual_score !== undefined ? (
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold border ${getBandBadge(
                            risk.residual_band || 'LOW'
                          )}`}
                        >
                          {risk.residual_score} ({risk.residual_band})
                        </span>
                      ) : (
                        <span className="text-xs text-slate-500 italic">Not Assessed</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${getAppetiteBadge(
                          risk.appetite_status
                        )}`}
                      >
                        {risk.appetite_status.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <div className="text-xs font-medium text-slate-300">
                        {risk.treatment_strategy}
                      </div>
                      {risk.treatment_due_date && (
                        <div
                          className={`text-[11px] mt-0.5 ${
                            risk.treatment_overdue_status === 'OVERDUE'
                              ? 'text-red-400 font-semibold'
                              : 'text-slate-400'
                          }`}
                        >
                          Due: {risk.treatment_due_date}
                        </div>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold border ${getStatusBadge(
                          risk.status
                        )}`}
                      >
                        {risk.status.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Link
                        to={`/risks/${risk.id}`}
                        className="inline-flex items-center gap-1 text-xs font-medium text-indigo-400 hover:text-indigo-300 transition-colors"
                      >
                        Manage
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create Risk Modal */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 space-y-4 my-8 shadow-2xl">
            <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-indigo-400" />
              Register New Risk
            </h2>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                createMutation.mutate(formData);
              }}
              className="space-y-4"
            >
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Risk Title *
                </label>
                <input
                  type="text"
                  required
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="e.g. Unauthenticated API Endpoints in Mobile Backend"
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Description & Impact Context *
                </label>
                <textarea
                  required
                  rows={3}
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Detailed description of risk scenario and business impact..."
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Risk Category
                  </label>
                  <select
                    value={formData.risk_category}
                    onChange={(e) =>
                      setFormData({ ...formData, risk_category: e.target.value as RiskCategory })
                    }
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="CYBERSECURITY">Cybersecurity</option>
                    <option value="COMPLIANCE">Compliance</option>
                    <option value="OPERATIONAL">Operational</option>
                    <option value="FINANCIAL">Financial</option>
                    <option value="STRATEGIC">Strategic</option>
                    <option value="REPUTATIONAL">Reputational</option>
                    <option value="THIRD_PARTY">Third Party</option>
                    <option value="LEGAL">Legal</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Risk Source
                  </label>
                  <select
                    value={formData.risk_source}
                    onChange={(e) =>
                      setFormData({ ...formData, risk_source: e.target.value as RiskSource })
                    }
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="INTERNAL_AUDIT">Internal Audit</option>
                    <option value="EXTERNAL_AUDIT">External Audit</option>
                    <option value="THREAT_INTELLIGENCE">Threat Intelligence</option>
                    <option value="VULNERABILITY_ASSESSMENT">Vulnerability Assessment</option>
                    <option value="INCIDENT">Incident</option>
                    <option value="VENDOR_ASSESSMENT">Vendor Assessment</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 p-3 bg-slate-950/60 border border-slate-800 rounded-lg">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Inherent Impact (1-5)
                  </label>
                  <select
                    value={formData.inherent_impact}
                    onChange={(e) =>
                      setFormData({ ...formData, inherent_impact: parseInt(e.target.value, 10) })
                    }
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                  >
                    <option value={1}>1 - Negligible</option>
                    <option value={2}>2 - Minor</option>
                    <option value={3}>3 - Moderate</option>
                    <option value={4}>4 - Major</option>
                    <option value={5}>5 - Severe</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Inherent Likelihood (1-5)
                  </label>
                  <select
                    value={formData.inherent_likelihood}
                    onChange={(e) =>
                      setFormData({ ...formData, inherent_likelihood: parseInt(e.target.value, 10) })
                    }
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                  >
                    <option value={1}>1 - Rare</option>
                    <option value={2}>2 - Unlikely</option>
                    <option value={3}>3 - Possible</option>
                    <option value={4}>4 - Likely</option>
                    <option value={5}>5 - Almost Certain</option>
                  </select>
                </div>

                <div className="col-span-2 text-xs text-slate-400 mt-1 flex items-center justify-between">
                  <span>Calculated Inherent Score:</span>
                  <span className="font-bold text-indigo-400">
                    {formData.inherent_impact * formData.inherent_likelihood} / 25
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Treatment Strategy
                  </label>
                  <select
                    value={formData.treatment_strategy}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        treatment_strategy: e.target.value as RiskTreatmentStrategy,
                      })
                    }
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="NOT_SPECIFIED">Not Specified</option>
                    <option value="MITIGATE">Mitigate</option>
                    <option value="TRANSFER">Transfer</option>
                    <option value="AVOID">Avoid</option>
                    <option value="ACCEPT">Accept</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Target Risk Band
                  </label>
                  <select
                    value={formData.target_risk_band}
                    onChange={(e) =>
                      setFormData({ ...formData, target_risk_band: e.target.value })
                    }
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="LOW">Low Appetite (≤ 4)</option>
                    <option value="MODERATE">Moderate Appetite (≤ 9)</option>
                    <option value="HIGH">High Appetite (≤ 16)</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium rounded-lg transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors cursor-pointer disabled:opacity-50"
                >
                  {createMutation.isPending ? 'Creating...' : 'Register Risk'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
