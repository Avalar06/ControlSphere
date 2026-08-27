import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  Building2,
  ExternalLink,
  Filter,
  Plus,
  RefreshCw,
  Search,
  ShieldAlert,
  ShieldCheck,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { tprmService } from '../lib/tprmService';
import { api } from '../lib/api';
import type {
  User,
  Vendor,
  VendorCreate,
  VendorOverviewResponse,
  VendorRiskBand,
  VendorStatus,
  VendorTier,
} from '../types';

export const VendorsPage: React.FC = () => {
  const navigate = useNavigate();
  const { hasRole } = useAuth();
  const canManage = hasRole('ADMIN', 'GRC_ANALYST', 'SECURITY_ANALYST', 'MANAGER');

  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState<VendorOverviewResponse | null>(null);
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [users, setUsers] = useState<User[]>([]);

  // Filters
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [tierFilter, setTierFilter] = useState<string>('ALL');
  const [riskBandFilter, setRiskBandFilter] = useState<string>('ALL');

  // Create Modal
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createForm, setCreateForm] = useState<VendorCreate>({
    vendor_code: '',
    legal_name: '',
    trade_name: '',
    business_owner_id: undefined,
  });
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [overviewData, vendorsData, usersData] = await Promise.all([
        tprmService.getOverview().catch(() => null),
        tprmService.listVendors().catch(() => []),
        api.get<User[]>('/users').then((r) => r.data).catch(() => []),
      ]);
      setOverview(overviewData);
      setVendors(vendorsData);
      setUsers(usersData);
    } catch (err) {
      console.error('Failed to load TPRM data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreateVendor = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createForm.vendor_code.trim() || !createForm.legal_name.trim()) {
      setCreateError('Vendor code and legal name are required.');
      return;
    }

    setCreateLoading(true);
    setCreateError(null);
    try {
      const newVendor = await tprmService.createVendor({
        vendor_code: createForm.vendor_code.trim().toUpperCase(),
        legal_name: createForm.legal_name.trim(),
        trade_name: createForm.trade_name?.trim() || undefined,
        business_owner_id: createForm.business_owner_id || undefined,
      });
      setShowCreateModal(false);
      setCreateForm({
        vendor_code: '',
        legal_name: '',
        trade_name: '',
        business_owner_id: undefined,
      });
      await fetchData();
      navigate(`/vendors/${newVendor.id}`);
    } catch (err: any) {
      setCreateError(err.response?.data?.detail || 'Failed to create vendor profile.');
    } finally {
      setCreateLoading(false);
    }
  };

  // Filtered vendors
  const filteredVendors = vendors.filter((v) => {
    if (search.trim()) {
      const q = search.toLowerCase();
      const matchCode = v.vendor_code.toLowerCase().includes(q);
      const matchLegal = v.legal_name.toLowerCase().includes(q);
      const matchTrade = v.trade_name?.toLowerCase().includes(q);
      if (!matchCode && !matchLegal && !matchTrade) return false;
    }
    if (statusFilter !== 'ALL' && v.vendor_status !== statusFilter) return false;
    if (tierFilter !== 'ALL' && v.effective_tier !== tierFilter) return false;
    if (riskBandFilter !== 'ALL' && v.risk_band !== riskBandFilter) return false;
    return true;
  });

  const getTierBadge = (tier: VendorTier, isOverridden: boolean) => {
    switch (tier) {
      case 'TIER_1_CRITICAL':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-red-950/80 text-red-400 border border-red-800/80 font-mono">
            <span>Tier 1 (Critical)</span>
            {isOverridden && <span className="text-[10px] text-amber-400 font-bold">*</span>}
          </span>
        );
      case 'TIER_2_SIGNIFICANT':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-amber-950/80 text-amber-400 border border-amber-800/80 font-mono">
            <span>Tier 2 (Significant)</span>
            {isOverridden && <span className="text-[10px] text-amber-400 font-bold">*</span>}
          </span>
        );
      case 'TIER_3_MODERATE':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-blue-950/80 text-blue-400 border border-blue-800/80 font-mono">
            <span>Tier 3 (Moderate)</span>
            {isOverridden && <span className="text-[10px] text-amber-400 font-bold">*</span>}
          </span>
        );
      case 'TIER_4_LOW':
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-700 font-mono">
            <span>Tier 4 (Low)</span>
            {isOverridden && <span className="text-[10px] text-amber-400 font-bold">*</span>}
          </span>
        );
    }
  };

  const getRiskBandBadge = (band: VendorRiskBand) => {
    switch (band) {
      case 'CRITICAL':
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-red-900/60 text-red-300 border border-red-700/60">
            CRITICAL
          </span>
        );
      case 'HIGH':
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-orange-900/60 text-orange-300 border border-orange-700/60">
            HIGH
          </span>
        );
      case 'MODERATE':
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-amber-900/60 text-amber-300 border border-amber-700/60">
            MODERATE
          </span>
        );
      case 'LOW':
      default:
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-900/60 text-emerald-300 border border-emerald-700/60">
            LOW
          </span>
        );
    }
  };

  const getStatusBadge = (status: VendorStatus) => {
    switch (status) {
      case 'ACTIVE':
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-950/80 text-emerald-400 border border-emerald-800/80">
            ACTIVE
          </span>
        );
      case 'ONBOARDING':
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-indigo-950/80 text-indigo-400 border border-indigo-800/80">
            ONBOARDING
          </span>
        );
      case 'UNDER_REVIEW':
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-amber-950/80 text-amber-400 border border-amber-800/80">
            UNDER REVIEW
          </span>
        );
      case 'SUSPENDED':
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-red-950/80 text-red-400 border border-red-800/80">
            SUSPENDED
          </span>
        );
      case 'OFFBOARDED':
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
            OFFBOARDED
          </span>
        );
      case 'PROSPECT':
      default:
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-700">
            PROSPECT
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-100 tracking-tight">
              Third-Party &amp; Vendor Risk Management (TPRM)
            </h1>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-indigo-950 text-indigo-400 border border-indigo-800">
              Phase 9
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Deterministic supply-chain cyber risk tiering, engagement scoring, and vendor assessment governance.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchData}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-md bg-slate-900 border border-slate-700 text-slate-300 hover:text-slate-100 hover:bg-slate-800 transition-colors disabled:opacity-50"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>

          {canManage && (
            <button
              onClick={() => setShowCreateModal(true)}
              className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-md bg-indigo-600 hover:bg-indigo-500 text-white transition-colors shadow-xs"
            >
              <Plus size={14} />
              <span>Register Vendor</span>
            </button>
          )}
        </div>
      </div>

      {/* Executive Overview KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-lg bg-slate-900/90 border border-slate-800 shadow-xs">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Total Vendors Scoped</span>
            <Building2 size={16} className="text-indigo-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-slate-100 font-mono">
            {overview?.total_vendors ?? vendors.length}
          </div>
          <div className="mt-1 text-[11px] text-slate-400 flex items-center gap-1.5">
            <span className="text-emerald-400 font-medium">
              {overview?.status_distribution?.ACTIVE || 0} Active
            </span>
            <span>&bull;</span>
            <span>{overview?.status_distribution?.ONBOARDING || 0} Onboarding</span>
          </div>
        </div>

        <div className="p-4 rounded-lg bg-slate-900/90 border border-slate-800 shadow-xs">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Average Residual Risk</span>
            <ShieldAlert size={16} className="text-amber-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-amber-400 font-mono">
            {overview?.average_residual_risk ?? 0.0}
            <span className="text-xs text-slate-400 font-normal ml-1">/ 100</span>
          </div>
          <div className="mt-1 text-[11px] text-slate-400">
            Defensible 20% risk floor enforced
          </div>
        </div>

        <div className="p-4 rounded-lg bg-slate-900/90 border border-slate-800 shadow-xs">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>High / Critical Risk Vendors</span>
            <AlertTriangle size={16} className="text-red-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-red-400 font-mono">
            {overview?.high_or_critical_risk_vendors ?? 0}
          </div>
          <div className="mt-1 text-[11px] text-slate-400">
            Requires continuous monitoring &amp; annual audits
          </div>
        </div>

        <div className="p-4 rounded-lg bg-slate-900/90 border border-slate-800 shadow-xs">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Tier 1 (Critical) Vendors</span>
            <ShieldCheck size={16} className="text-red-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-slate-100 font-mono">
            {overview?.tier_distribution?.TIER_1_CRITICAL || 0}
          </div>
          <div className="mt-1 text-[11px] text-slate-400 flex items-center gap-1.5">
            <span>{overview?.tier_distribution?.TIER_2_SIGNIFICANT || 0} Tier 2</span>
            <span>&bull;</span>
            <span>{overview?.tier_distribution?.TIER_3_MODERATE || 0} Tier 3</span>
          </div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="p-3.5 rounded-lg bg-slate-900/70 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="flex flex-1 items-center gap-2">
          <div className="relative flex-1 max-w-md">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Search vendor code, legal name, or trade name..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-md bg-slate-950 border border-slate-800 text-slate-200 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
            />
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <Filter size={13} />
            <span>Filters:</span>
          </div>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-2.5 py-1.5 text-xs rounded-md bg-slate-950 border border-slate-800 text-slate-300 focus:outline-hidden focus:border-indigo-500"
          >
            <option value="ALL">All Statuses</option>
            <option value="PROSPECT">Prospect</option>
            <option value="ONBOARDING">Onboarding</option>
            <option value="ACTIVE">Active</option>
            <option value="UNDER_REVIEW">Under Review</option>
            <option value="SUSPENDED">Suspended</option>
            <option value="OFFBOARDED">Offboarded</option>
          </select>

          <select
            value={tierFilter}
            onChange={(e) => setTierFilter(e.target.value)}
            className="px-2.5 py-1.5 text-xs rounded-md bg-slate-950 border border-slate-800 text-slate-300 focus:outline-hidden focus:border-indigo-500"
          >
            <option value="ALL">All Tiers</option>
            <option value="TIER_1_CRITICAL">Tier 1 (Critical)</option>
            <option value="TIER_2_SIGNIFICANT">Tier 2 (Significant)</option>
            <option value="TIER_3_MODERATE">Tier 3 (Moderate)</option>
            <option value="TIER_4_LOW">Tier 4 (Low)</option>
          </select>

          <select
            value={riskBandFilter}
            onChange={(e) => setRiskBandFilter(e.target.value)}
            className="px-2.5 py-1.5 text-xs rounded-md bg-slate-950 border border-slate-800 text-slate-300 focus:outline-hidden focus:border-indigo-500"
          >
            <option value="ALL">All Risk Bands</option>
            <option value="LOW">Low Risk</option>
            <option value="MODERATE">Moderate Risk</option>
            <option value="HIGH">High Risk</option>
            <option value="CRITICAL">Critical Risk</option>
          </select>
        </div>
      </div>

      {/* Vendor Table */}
      <div className="rounded-lg bg-slate-900/90 border border-slate-800 overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-950/70 text-slate-400 font-semibold uppercase tracking-wider text-[11px]">
                <th className="py-3 px-4">Vendor Code &amp; Legal Name</th>
                <th className="py-3 px-4">Effective Tier</th>
                <th className="py-3 px-4">Inherent Risk</th>
                <th className="py-3 px-4">Residual Risk &amp; Band</th>
                <th className="py-3 px-4">Lifecycle Status</th>
                <th className="py-3 px-4">Business Owner</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-500">
                    <RefreshCw size={20} className="animate-spin mx-auto mb-2 text-indigo-400" />
                    <span>Loading vendor portfolio...</span>
                  </td>
                </tr>
              ) : filteredVendors.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-500">
                    <Building2 size={24} className="mx-auto mb-2 text-slate-600" />
                    <span>No vendors match the specified search or filter criteria.</span>
                  </td>
                </tr>
              ) : (
                filteredVendors.map((v) => {
                  const isOverridden = !!v.override_tier;
                  return (
                    <tr
                      key={v.id}
                      onClick={() => navigate(`/vendors/${v.id}`)}
                      className="hover:bg-slate-800/40 cursor-pointer transition-colors"
                    >
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-indigo-400">
                            {v.vendor_code}
                          </span>
                          <span className="font-semibold text-slate-200">
                            {v.legal_name}
                          </span>
                        </div>
                        {v.trade_name && (
                          <div className="text-[11px] text-slate-400 italic mt-0.5">
                            DBA: {v.trade_name}
                          </div>
                        )}
                      </td>

                      <td className="py-3.5 px-4">
                        {getTierBadge(v.effective_tier, isOverridden)}
                      </td>

                      <td className="py-3.5 px-4 font-mono font-medium text-slate-300">
                        {v.calculated_inherent_risk.toFixed(1)}
                      </td>

                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-slate-100">
                            {v.residual_risk_score.toFixed(1)}
                          </span>
                          {getRiskBandBadge(v.risk_band)}
                        </div>
                      </td>

                      <td className="py-3.5 px-4">
                        {getStatusBadge(v.vendor_status)}
                      </td>

                      <td className="py-3.5 px-4 text-slate-300">
                        {v.business_owner?.full_name || (
                          <span className="text-slate-500 italic">Unassigned</span>
                        )}
                      </td>

                      <td className="py-3.5 px-4 text-right">
                        <span className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-400 hover:text-indigo-300">
                          <span>View Workspace</span>
                          <ExternalLink size={13} />
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Register Vendor Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-xs p-4">
          <div className="w-full max-w-lg rounded-xl bg-slate-900 border border-slate-800 shadow-xl overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Building2 size={18} className="text-indigo-400" />
                <h3 className="text-base font-bold text-slate-100">
                  Register New Vendor Profile
                </h3>
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-slate-200 text-lg leading-none"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleCreateVendor} className="p-6 space-y-4">
              {createError && (
                <div className="p-3 rounded-md bg-red-950/80 border border-red-800 text-xs text-red-300">
                  {createError}
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Vendor Code <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. VEND-AWS-01, VEND-OKTA-01"
                  value={createForm.vendor_code}
                  onChange={(e) =>
                    setCreateForm({ ...createForm, vendor_code: e.target.value })
                  }
                  className="w-full px-3 py-2 text-xs font-mono rounded-md bg-slate-950 border border-slate-800 text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500 uppercase"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Legal Entity Name <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Amazon Web Services, Inc."
                  value={createForm.legal_name}
                  onChange={(e) =>
                    setCreateForm({ ...createForm, legal_name: e.target.value })
                  }
                  className="w-full px-3 py-2 text-xs rounded-md bg-slate-950 border border-slate-800 text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Trade Name / DBA (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. AWS Cloud Infrastructure"
                  value={createForm.trade_name}
                  onChange={(e) =>
                    setCreateForm({ ...createForm, trade_name: e.target.value })
                  }
                  className="w-full px-3 py-2 text-xs rounded-md bg-slate-950 border border-slate-800 text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Internal Business Owner
                </label>
                <select
                  value={createForm.business_owner_id || ''}
                  onChange={(e) =>
                    setCreateForm({
                      ...createForm,
                      business_owner_id: e.target.value ? Number(e.target.value) : undefined,
                    })
                  }
                  className="w-full px-3 py-2 text-xs rounded-md bg-slate-950 border border-slate-800 text-slate-100 focus:outline-hidden focus:border-indigo-500"
                >
                  <option value="">-- Select Business Owner --</option>
                  {users.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.full_name} ({u.email}) — {u.role}
                    </option>
                  ))}
                </select>
              </div>

              <div className="pt-2 flex items-center justify-end gap-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 text-xs font-medium rounded-md bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-slate-100 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createLoading}
                  className="px-4 py-2 text-xs font-semibold rounded-md bg-indigo-600 hover:bg-indigo-500 text-white transition-colors disabled:opacity-50"
                >
                  {createLoading ? 'Registering...' : 'Register Vendor'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
