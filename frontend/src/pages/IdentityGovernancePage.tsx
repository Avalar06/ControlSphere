import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Users,
  KeyRound,
  CheckCircle2,
  AlertOctagon,
  Clock,
  Plus,
  Search,
  ExternalLink,
  RefreshCw,
} from 'lucide-react';
import { identityGovernanceService } from '../lib/identityGovernanceService';
import { IdentityPostureCard } from '../components/identity/IdentityPostureCard';
import { GovernedIdentityModal } from '../components/identity/GovernedIdentityModal';
import { IdentityEntitlementModal } from '../components/identity/IdentityEntitlementModal';
import { AccessCampaignModal } from '../components/identity/AccessCampaignModal';
import { JITRequestModal } from '../components/identity/JITRequestModal';
import { SoDPolicyModal } from '../components/identity/SoDPolicyModal';
import type {
  GovernedIdentity,
  AccessCertificationCampaign,
  JITAccessRequest,
  IdentityPostureSummaryResponse,
  GovernedIdentityCreate,
  IdentityEntitlementCreate,
  AccessCertificationCampaignCreate,
  IdentityRiskBand,
} from '../types';

export const IdentityGovernancePage: React.FC = () => {
  const navigate = useNavigate();
  const [summary, setSummary] = useState<IdentityPostureSummaryResponse | null>(null);
  const [identities, setIdentities] = useState<GovernedIdentity[]>([]);
  const [campaigns, setCampaigns] = useState<AccessCertificationCampaign[]>([]);
  const [jitRequests, setJitRequests] = useState<JITAccessRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'IDENTITIES' | 'CAMPAIGNS' | 'JIT'>('IDENTITIES');

  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('ALL');
  const [riskFilter, setRiskFilter] = useState<string>('ALL');

  const [isIdentityModalOpen, setIsIdentityModalOpen] = useState(false);
  const [isEntitlementModalOpen, setIsEntitlementModalOpen] = useState(false);
  const [isCampaignModalOpen, setIsCampaignModalOpen] = useState(false);
  const [isJITModalOpen, setIsJITModalOpen] = useState(false);
  const [isSoDModalOpen, setIsSoDModalOpen] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [sumRes, idRes, campRes, jitRes] = await Promise.all([
        identityGovernanceService.getPostureSummary(),
        identityGovernanceService.listIdentities(),
        identityGovernanceService.listCampaigns(),
        identityGovernanceService.listJITRequests(),
      ]);
      setSummary(sumRes);
      setIdentities(idRes);
      setCampaigns(campRes);
      setJitRequests(jitRes);
    } catch (err) {
      console.error('Failed to load identity governance data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreateIdentity = async (data: GovernedIdentityCreate) => {
    await identityGovernanceService.createIdentity(data);
    fetchData();
  };

  const handleCreateCampaign = async (data: AccessCertificationCampaignCreate) => {
    await identityGovernanceService.createCampaign(data);
    fetchData();
  };

  const filteredIdentities = identities.filter((identity) => {
    const matchesSearch =
      identity.identity_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
      identity.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      identity.email.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesType = typeFilter === 'ALL' || identity.identity_type === typeFilter;
    const matchesRisk = riskFilter === 'ALL' || identity.risk_band === riskFilter;

    return matchesSearch && matchesType && matchesRisk;
  });

  const getRiskBadge = (band: IdentityRiskBand, score: number) => {
    switch (band) {
      case 'LOW':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
            LOW ({score})
          </span>
        );
      case 'MODERATE':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 dark:bg-blue-950/50 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
            MODERATE ({score})
          </span>
        );
      case 'HIGH':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
            HIGH ({score})
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 dark:bg-rose-950/50 dark:text-rose-300 border border-rose-200 dark:border-rose-800">
            CRITICAL ({score})
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Users className="w-7 h-7 text-indigo-600 dark:text-indigo-400" />
            Identity Governance & Administration (IGA)
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Phase 19: Unified identity lifecycle, automated access certifications, Four-Eyes SoD rules, and Zero Trust telemetry.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setIsSoDModalOpen(true)}
            className="px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors flex items-center gap-1.5 shadow-sm"
          >
            <AlertOctagon className="w-4 h-4 text-rose-500" />
            SoD Policy
          </button>
          <button
            onClick={() => setIsEntitlementModalOpen(true)}
            className="px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors flex items-center gap-1.5 shadow-sm"
          >
            <KeyRound className="w-4 h-4 text-indigo-500" />
            Entitlement Catalog
          </button>
          <button
            onClick={() => setIsCampaignModalOpen(true)}
            className="px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors flex items-center gap-1.5 shadow-sm"
          >
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
            Launch UAR
          </button>
          <button
            onClick={() => setIsIdentityModalOpen(true)}
            className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-sm transition-colors flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Register Identity
          </button>
        </div>
      </div>

      {/* Posture Telemetry */}
      <IdentityPostureCard summary={summary} loading={loading} />

      {/* Navigation Tabs */}
      <div className="flex gap-3 border-b border-gray-200 dark:border-gray-800 pb-2">
        <button
          onClick={() => setActiveTab('IDENTITIES')}
          className={`px-4 py-2 text-sm font-medium rounded-xl transition-colors flex items-center gap-2 ${
            activeTab === 'IDENTITIES'
              ? 'bg-indigo-50 text-indigo-600 dark:bg-indigo-950/50 dark:text-indigo-400'
              : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white'
          }`}
        >
          <Users className="w-4 h-4" />
          Governed Identities ({identities.length})
        </button>
        <button
          onClick={() => setActiveTab('CAMPAIGNS')}
          className={`px-4 py-2 text-sm font-medium rounded-xl transition-colors flex items-center gap-2 ${
            activeTab === 'CAMPAIGNS'
              ? 'bg-indigo-50 text-indigo-600 dark:bg-indigo-950/50 dark:text-indigo-400'
              : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white'
          }`}
        >
          <CheckCircle2 className="w-4 h-4" />
          Access Certification Campaigns ({campaigns.length})
        </button>
        <button
          onClick={() => setActiveTab('JIT')}
          className={`px-4 py-2 text-sm font-medium rounded-xl transition-colors flex items-center gap-2 ${
            activeTab === 'JIT'
              ? 'bg-indigo-50 text-indigo-600 dark:bg-indigo-950/50 dark:text-indigo-400'
              : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white'
          }`}
        >
          <Clock className="w-4 h-4" />
          JIT Elevation Requests ({jitRequests.length})
        </button>
      </div>

      {/* Tab: Governed Identities */}
      {activeTab === 'IDENTITIES' && (
        <div className="p-4 bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm space-y-4">
          <div className="flex flex-col md:flex-row gap-4 justify-between">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search identities by code, name, or email..."
                className="w-full pl-9 pr-4 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              />
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              >
                <option value="ALL">All Identity Types</option>
                <option value="WORKFORCE_EMPLOYEE">Workforce Employee</option>
                <option value="CONTRACTOR">Contractor</option>
                <option value="SERVICE_ACCOUNT">Service Account</option>
                <option value="MACHINE_WORKLOAD">Machine Workload</option>
              </select>

              <select
                value={riskFilter}
                onChange={(e) => setRiskFilter(e.target.value)}
                className="px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              >
                <option value="ALL">All Risk Bands</option>
                <option value="LOW">Low Risk</option>
                <option value="MODERATE">Moderate Risk</option>
                <option value="HIGH">High Risk</option>
                <option value="CRITICAL">Critical Risk</option>
              </select>

              <button
                onClick={fetchData}
                className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-gray-600 dark:text-gray-400">
              <thead className="text-xs uppercase bg-gray-50 dark:bg-gray-800/50 text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-800">
                <tr>
                  <th className="px-4 py-3 font-semibold">Identity / Code</th>
                  <th className="px-4 py-3 font-semibold">Type / Department</th>
                  <th className="px-4 py-3 font-semibold">Privileged</th>
                  <th className="px-4 py-3 font-semibold">MFA</th>
                  <th className="px-4 py-3 font-semibold">Risk Score (IRS)</th>
                  <th className="px-4 py-3 font-semibold">Status</th>
                  <th className="px-4 py-3 font-semibold text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                {filteredIdentities.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-gray-500">
                      No governed identities found.
                    </td>
                  </tr>
                ) : (
                  filteredIdentities.map((identity) => (
                    <tr
                      key={identity.id}
                      onClick={() => navigate(`/identity-governance/identities/${identity.id}`)}
                      className="hover:bg-gray-50/80 dark:hover:bg-gray-800/50 cursor-pointer transition-colors"
                    >
                      <td className="px-4 py-3">
                        <div className="font-semibold text-gray-900 dark:text-white flex items-center gap-1.5">
                          {identity.full_name}
                        </div>
                        <div className="text-xs font-mono text-gray-500">{identity.email}</div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-xs font-medium text-gray-800 dark:text-gray-200">
                          {identity.identity_type.replace('_', ' ')}
                        </span>
                        <div className="text-xs text-gray-500">{identity.department || 'General'}</div>
                      </td>
                      <td className="px-4 py-3">
                        {identity.is_privileged ? (
                          <span className="px-2 py-0.5 text-xs font-semibold rounded bg-purple-50 text-purple-700 dark:bg-purple-950/60 dark:text-purple-300 border border-purple-200 dark:border-purple-800">
                            PRIVILEGED
                          </span>
                        ) : (
                          <span className="text-xs text-gray-400">Standard</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {identity.mfa_enabled ? (
                          <span className="text-xs font-semibold text-emerald-600 flex items-center gap-1">
                            <CheckCircle2 className="w-3.5 h-3.5" /> Enforced
                          </span>
                        ) : (
                          <span className="text-xs text-rose-600 font-semibold">Missing</span>
                        )}
                      </td>
                      <td className="px-4 py-3">{getRiskBadge(identity.risk_band, identity.risk_score)}</td>
                      <td className="px-4 py-3">
                        <span
                          className={`text-xs font-medium ${
                            identity.employment_status === 'ACTIVE'
                              ? 'text-emerald-600'
                              : 'text-gray-500'
                          }`}
                        >
                          {identity.employment_status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/identity-governance/identities/${identity.id}`);
                          }}
                          className="p-1 text-gray-400 hover:text-indigo-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
                        >
                          <ExternalLink className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab: Campaigns */}
      {activeTab === 'CAMPAIGNS' && (
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-gray-600 dark:text-gray-400">
              <thead className="text-xs uppercase bg-gray-50 dark:bg-gray-800/50 text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-800">
                <tr>
                  <th className="px-4 py-3 font-semibold">Campaign Title / Code</th>
                  <th className="px-4 py-3 font-semibold">Type</th>
                  <th className="px-4 py-3 font-semibold">Review Progress</th>
                  <th className="px-4 py-3 font-semibold">Status</th>
                  <th className="px-4 py-3 font-semibold">Deadline</th>
                  <th className="px-4 py-3 font-semibold text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                {campaigns.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                      No access certification campaigns found.
                    </td>
                  </tr>
                ) : (
                  campaigns.map((camp) => (
                    <tr
                      key={camp.id}
                      onClick={() => navigate(`/identity-governance/campaigns/${camp.id}`)}
                      className="hover:bg-gray-50/80 dark:hover:bg-gray-800/50 cursor-pointer transition-colors"
                    >
                      <td className="px-4 py-3">
                        <div className="font-semibold text-gray-900 dark:text-white">{camp.title}</div>
                        <div className="text-xs font-mono text-gray-500">{camp.campaign_code}</div>
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-700 dark:text-gray-300">
                        {camp.campaign_type.replace(/_/g, ' ')}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-gray-900 dark:text-white">
                            {camp.certified_items_count + camp.revoked_items_count} / {camp.total_items_count}
                          </span>
                          <div className="w-20 bg-gray-200 dark:bg-gray-700 rounded-full h-1.5 overflow-hidden">
                            <div
                              className="bg-indigo-600 h-full"
                              style={{
                                width: `${
                                  camp.total_items_count > 0
                                    ? ((camp.certified_items_count + camp.revoked_items_count) /
                                        camp.total_items_count) *
                                      100
                                    : 0
                                }%`,
                              }}
                            />
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`text-xs px-2 py-0.5 font-semibold rounded-full ${
                            camp.status === 'FINALIZED'
                              ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
                              : 'bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300'
                          }`}
                        >
                          {camp.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-500">{camp.deadline}</td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/identity-governance/campaigns/${camp.id}`);
                          }}
                          className="p-1 text-gray-400 hover:text-indigo-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
                        >
                          <ExternalLink className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab: JIT Requests */}
      {activeTab === 'JIT' && (
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden">
          <div className="p-4 border-b border-gray-200 dark:border-gray-800 flex justify-between items-center bg-gray-50/50 dark:bg-gray-800/50">
            <div>
              <h3 className="font-semibold text-gray-900 dark:text-white">Just-In-Time Elevation Queue</h3>
              <p className="text-xs text-gray-500 mt-0.5">Four-Eyes principle enforced: Requester cannot self-approve.</p>
            </div>
            <button
              onClick={() => setIsJITModalOpen(true)}
              className="px-3 py-1.5 text-xs font-medium text-white bg-amber-600 hover:bg-amber-700 rounded-xl shadow-sm flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" />
              Submit JIT Request
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-gray-600 dark:text-gray-400">
              <thead className="text-xs uppercase bg-gray-50 dark:bg-gray-800/50 text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-800">
                <tr>
                  <th className="px-4 py-3 font-semibold">Request Code</th>
                  <th className="px-4 py-3 font-semibold">Duration</th>
                  <th className="px-4 py-3 font-semibold">Business Justification</th>
                  <th className="px-4 py-3 font-semibold">Status</th>
                  <th className="px-4 py-3 font-semibold">Created At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                {jitRequests.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                      No JIT requests submitted.
                    </td>
                  </tr>
                ) : (
                  jitRequests.map((jit) => (
                    <tr key={jit.id} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/50">
                      <td className="px-4 py-3 font-mono font-semibold text-gray-900 dark:text-white">
                        {jit.request_code}
                      </td>
                      <td className="px-4 py-3 text-xs font-semibold text-amber-600">
                        {jit.requested_duration_minutes} Mins
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-700 dark:text-gray-300 max-w-xs truncate">
                        {jit.business_justification}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`text-xs px-2 py-0.5 font-semibold rounded-full ${
                            jit.approval_status === 'APPROVED'
                              ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
                              : jit.approval_status === 'REJECTED'
                              ? 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300'
                              : 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300'
                          }`}
                        >
                          {jit.approval_status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-500">{new Date(jit.created_at).toLocaleString()}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modals */}
      <GovernedIdentityModal
        isOpen={isIdentityModalOpen}
        onClose={() => setIsIdentityModalOpen(false)}
        onSubmit={handleCreateIdentity}
      />
      <IdentityEntitlementModal
        isOpen={isEntitlementModalOpen}
        onClose={() => setIsEntitlementModalOpen(false)}
        onSubmit={async (data: IdentityEntitlementCreate) => {
          await identityGovernanceService.createEntitlement(data);
          fetchData();
        }}
      />
      <AccessCampaignModal
        isOpen={isCampaignModalOpen}
        onClose={() => setIsCampaignModalOpen(false)}
        onSubmit={handleCreateCampaign}
      />
      <JITRequestModal
        isOpen={isJITModalOpen}
        onClose={() => setIsJITModalOpen(false)}
        identities={identities}
        onSuccess={fetchData}
      />
      <SoDPolicyModal
        isOpen={isSoDModalOpen}
        onClose={() => setIsSoDModalOpen(false)}
        onSuccess={fetchData}
      />
    </div>
  );
};
