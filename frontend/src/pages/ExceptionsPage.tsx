import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  FileWarning,
  Plus,
  Search,
  ArrowRight,
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ShieldCheck,
} from 'lucide-react';
import { api } from '../lib/api';
import { exceptionService } from '../lib/exceptionService';
import type { ExceptionCreatePayload } from '../lib/exceptionService';
import type {
  ExceptionStatus,
  ExceptionType,
  OrganizationControl,
} from '../types';

export const ExceptionsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<ExceptionStatus | ''>('');
  const [typeFilter, setTypeFilter] = useState<ExceptionType | ''>('');
  const [activeOnly, setActiveOnly] = useState(false);
  const [expiredOnly, setExpiredOnly] = useState(false);
  const [isRequestModalOpen, setIsRequestModalOpen] = useState(false);

  const [formData, setFormData] = useState<ExceptionCreatePayload>({
    title: '',
    description: '',
    justification: '',
    exception_type: 'CONTROL_DEVIATION',
    expiry_date: '',
    effective_date: '',
    residual_risk_level: 'MODERATE',
    linked_organization_control_id: undefined,
  });

  const { data: stats, isLoading: isStatsLoading } = useQuery({
    queryKey: ['exceptionStats'],
    queryFn: exceptionService.getStats,
  });

  const { data: controls = [] } = useQuery({
    queryKey: ['controls'],
    queryFn: async () => {
      const res = await api.get<OrganizationControl[]>('/api/v1/controls');
      return res.data;
    },
  });

  const { data: exceptions = [], isLoading: isExceptionsLoading } = useQuery({
    queryKey: [
      'exceptions',
      statusFilter,
      typeFilter,
      activeOnly,
      expiredOnly,
      search,
    ],
    queryFn: () =>
      exceptionService.listExceptions({
        status: statusFilter || undefined,
        exception_type: typeFilter || undefined,
        active_only: activeOnly || undefined,
        expired_only: expiredOnly || undefined,
        search: search || undefined,
      }),
  });

  const createMutation = useMutation({
    mutationFn: exceptionService.createException,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exceptions'] });
      queryClient.invalidateQueries({ queryKey: ['exceptionStats'] });
      setIsRequestModalOpen(false);
      setFormData({
        title: '',
        description: '',
        justification: '',
        exception_type: 'CONTROL_DEVIATION',
        expiry_date: '',
        effective_date: '',
        residual_risk_level: 'MODERATE',
        linked_organization_control_id: undefined,
      });
    },
  });

  const getEffectiveStatusBadge = (effectiveStatus: string) => {
    switch (effectiveStatus) {
      case 'ACTIVE':
        return 'bg-emerald-950/60 text-emerald-400 border-emerald-800/80';
      case 'EXPIRED':
        return 'bg-red-950/60 text-red-400 border-red-800/80';
      case 'REJECTED':
        return 'bg-slate-800 text-slate-400 border-slate-700';
      case 'CLOSED':
        return 'bg-slate-900 text-slate-400 border-slate-800';
      case 'UNDER_REVIEW':
        return 'bg-yellow-950/60 text-yellow-400 border-yellow-800/80';
      case 'APPROVED':
        return 'bg-blue-950/60 text-blue-400 border-blue-800/80';
      default:
        return 'bg-indigo-950/60 text-indigo-400 border-indigo-800/80';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
            <FileWarning className="w-6 h-6 text-amber-400" />
            Security Exceptions Register
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Governed deviation management with validity windows, compensating controls, and reviewer approval workflows.
          </p>
        </div>
        <button
          onClick={() => setIsRequestModalOpen(true)}
          className="flex items-center justify-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white text-sm font-medium rounded-lg shadow-sm transition-colors cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          Request Exception
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Active Exceptions</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <p className="text-2xl font-bold text-emerald-400 mt-2">
            {isStatsLoading ? '...' : stats?.active_count ?? 0}
          </p>
          <p className="text-xs text-slate-400 mt-2">
            Currently approved and within validity window
          </p>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Pending Review</span>
            <Clock className="w-4 h-4 text-yellow-400" />
          </div>
          <p className="text-2xl font-bold text-yellow-400 mt-2">
            {isStatsLoading ? '...' : (stats?.requested_count ?? 0) + (stats?.under_review_count ?? 0)}
          </p>
          <p className="text-xs text-slate-400 mt-2">
            {stats?.requested_count ?? 0} requested, {stats?.under_review_count ?? 0} under review
          </p>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Expiring Soon (≤ 14d)</span>
            <AlertCircle className="w-4 h-4 text-amber-400" />
          </div>
          <p className="text-2xl font-bold text-amber-400 mt-2">
            {isStatsLoading ? '...' : stats?.expiring_soon_count ?? 0}
          </p>
          <p className="text-xs text-slate-400 mt-2">
            Requires renewal or closure
          </p>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Expired Exceptions</span>
            <XCircle className="w-4 h-4 text-red-400" />
          </div>
          <p className="text-2xl font-bold text-red-400 mt-2">
            {isStatsLoading ? '...' : stats?.expired_count ?? 0}
          </p>
          <p className="text-xs text-slate-400 mt-2">
            Past validity date requiring action
          </p>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[240px]">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search exceptions by title, description, or justification..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-amber-500"
          />
        </div>

        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value as ExceptionType)}
          className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-300 focus:outline-none focus:border-amber-500"
        >
          <option value="">All Exception Types</option>
          <option value="CONTROL_DEVIATION">Control Deviation</option>
          <option value="POLICY_EXCEPTION">Policy Exception</option>
          <option value="CONFIGURATION_STANDARD">Configuration Standard</option>
          <option value="THIRD_PARTY_VENDOR">Third Party Vendor</option>
          <option value="ACCESS_CONTROL">Access Control</option>
        </select>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as ExceptionStatus)}
          className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-300 focus:outline-none focus:border-amber-500"
        >
          <option value="">All Workflow Statuses</option>
          <option value="REQUESTED">Requested</option>
          <option value="UNDER_REVIEW">Under Review</option>
          <option value="APPROVED">Approved</option>
          <option value="ACTIVE">Active</option>
          <option value="EXPIRED">Expired</option>
          <option value="REJECTED">Rejected</option>
          <option value="CLOSED">Closed</option>
        </select>

        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              setActiveOnly(!activeOnly);
              if (!activeOnly) setExpiredOnly(false);
            }}
            className={`px-3 py-2 rounded-lg text-xs font-medium border transition-colors cursor-pointer ${
              activeOnly
                ? 'bg-emerald-950/60 text-emerald-400 border-emerald-700'
                : 'bg-slate-950 text-slate-400 border-slate-800'
            }`}
          >
            Active Only
          </button>
          <button
            onClick={() => {
              setExpiredOnly(!expiredOnly);
              if (!expiredOnly) setActiveOnly(false);
            }}
            className={`px-3 py-2 rounded-lg text-xs font-medium border transition-colors cursor-pointer ${
              expiredOnly
                ? 'bg-red-950/60 text-red-400 border-red-700'
                : 'bg-slate-950 text-slate-400 border-slate-800'
            }`}
          >
            Expired Only
          </button>
        </div>
      </div>

      {/* Exceptions Table */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-950/50 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                <th className="py-3 px-4">Exception Title &amp; Rationale</th>
                <th className="py-3 px-4">Type</th>
                <th className="py-3 px-4">Effective Status</th>
                <th className="py-3 px-4">Validity Window</th>
                <th className="py-3 px-4">Compensating Controls</th>
                <th className="py-3 px-4">Residual Risk</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-sm">
              {isExceptionsLoading ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    Loading security exceptions...
                  </td>
                </tr>
              ) : exceptions.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    No exceptions match the current filter criteria.
                  </td>
                </tr>
              ) : (
                exceptions.map((exc) => (
                  <tr key={exc.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3 px-4 max-w-xs">
                      <Link
                        to={`/exceptions/${exc.id}`}
                        className="font-medium text-slate-200 hover:text-amber-400 transition-colors block truncate"
                      >
                        {exc.title}
                      </Link>
                      <p className="text-xs text-slate-400 line-clamp-1 mt-0.5">
                        {exc.justification}
                      </p>
                      {exc.linked_control && (
                        <div className="text-[11px] text-slate-500 mt-1">
                          Control: {exc.linked_control.subcategory?.identifier}
                        </div>
                      )}
                    </td>
                    <td className="py-3 px-4 text-xs font-medium text-slate-300">
                      {exc.exception_type.replace('_', ' ')}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold border ${getEffectiveStatusBadge(
                          exc.effective_status
                        )}`}
                      >
                        {exc.effective_status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-xs text-slate-300">
                      <div>Expires: {exc.expiry_date}</div>
                      {exc.effective_date && (
                        <div className="text-[11px] text-slate-500">
                          Effective: {exc.effective_date}
                        </div>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-1.5 text-xs text-slate-300">
                        <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                        <span>{exc.compensating_controls_count} linked</span>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <span className="text-xs font-medium text-slate-300">
                        {exc.residual_risk_level}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Link
                        to={`/exceptions/${exc.id}`}
                        className="inline-flex items-center gap-1 text-xs font-medium text-amber-400 hover:text-amber-300 transition-colors"
                      >
                        Review
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

      {/* Request Exception Modal */}
      {isRequestModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 space-y-4 my-8 shadow-2xl">
            <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              <FileWarning className="w-5 h-5 text-amber-400" />
              Request Security Exception
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
                  Exception Title *
                </label>
                <input
                  type="text"
                  required
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="e.g. Temporary Port 22 SSH Exception for Disaster Recovery"
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-amber-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Scope &amp; Description *
                </label>
                <textarea
                  required
                  rows={2}
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Affected systems, network boundaries, or asset groups..."
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-amber-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Business &amp; Technical Justification *
                </label>
                <textarea
                  required
                  rows={3}
                  value={formData.justification}
                  onChange={(e) => setFormData({ ...formData, justification: e.target.value })}
                  placeholder="Why is standard compliance impossible? Detail operational impact..."
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-amber-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Exception Type
                  </label>
                  <select
                    value={formData.exception_type}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        exception_type: e.target.value as ExceptionType,
                      })
                    }
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-amber-500"
                  >
                    <option value="CONTROL_DEVIATION">Control Deviation</option>
                    <option value="POLICY_EXCEPTION">Policy Exception</option>
                    <option value="CONFIGURATION_STANDARD">Configuration Standard</option>
                    <option value="THIRD_PARTY_VENDOR">Third Party Vendor</option>
                    <option value="ACCESS_CONTROL">Access Control</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Residual Risk Level
                  </label>
                  <select
                    value={formData.residual_risk_level}
                    onChange={(e) =>
                      setFormData({ ...formData, residual_risk_level: e.target.value })
                    }
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-amber-500"
                  >
                    <option value="LOW">Low</option>
                    <option value="MODERATE">Moderate</option>
                    <option value="HIGH">High</option>
                    <option value="CRITICAL">Critical</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Effective Date
                  </label>
                  <input
                    type="date"
                    value={formData.effective_date}
                    onChange={(e) =>
                      setFormData({ ...formData, effective_date: e.target.value })
                    }
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-amber-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Expiration Date *
                  </label>
                  <input
                    type="date"
                    required
                    value={formData.expiry_date}
                    onChange={(e) => setFormData({ ...formData, expiry_date: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-amber-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Linked Control (Optional)
                </label>
                <select
                  value={formData.linked_organization_control_id || ''}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      linked_organization_control_id: e.target.value
                        ? parseInt(e.target.value, 10)
                        : undefined,
                    })
                  }
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-amber-500"
                >
                  <option value="">None</option>
                  {controls.map((c: OrganizationControl) => (
                    <option key={c.id} value={c.id}>
                      {c.subcategory?.identifier} - {c.subcategory?.title}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsRequestModalOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium rounded-lg transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending || !formData.expiry_date}
                  className="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white text-sm font-medium rounded-lg transition-colors cursor-pointer disabled:opacity-50"
                >
                  {createMutation.isPending ? 'Submitting...' : 'Submit Exception Request'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
