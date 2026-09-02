import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  CheckCircle2,
  XCircle,
  Lock,
} from 'lucide-react';
import { identityGovernanceService } from '../lib/identityGovernanceService';
import type {
  AccessCertificationCampaign,
  AccessCertificationItem,
  CertificationDecision,
} from '../types';

export const CertificationCampaignDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const campaignId = parseInt(id || '0');

  const [campaign, setCampaign] = useState<AccessCertificationCampaign | null>(null);
  const [items, setItems] = useState<AccessCertificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [decisionFilter, setDecisionFilter] = useState<string>('ALL');

  const fetchCampaignData = async () => {
    if (!campaignId) return;
    setLoading(true);
    try {
      const [campRes, itemsRes] = await Promise.all([
        identityGovernanceService.getCampaign(campaignId),
        identityGovernanceService.listCampaignItems(campaignId),
      ]);
      setCampaign(campRes);
      setItems(itemsRes);
    } catch (err) {
      console.error('Failed to load campaign data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCampaignData();
  }, [campaignId]);

  const handleReview = async (itemId: number, decision: CertificationDecision) => {
    try {
      await identityGovernanceService.reviewCertificationItem(itemId, {
        decision,
        decision_justification: `Decision recorded during ${campaign?.campaign_code} certification cycle`,
      });
      fetchCampaignData();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to review certification item');
    }
  };

  const handleFinalize = async () => {
    if (!campaign) return;
    const confirm = window.confirm(
      'Are you sure you want to FINALIZE this campaign? All access decisions will be locked permanently.'
    );
    if (!confirm) return;
    try {
      await identityGovernanceService.finalizeCampaign(campaign.id);
      fetchCampaignData();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to finalize campaign');
    }
  };

  if (loading || !campaign) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const filteredItems = items.filter(
    (item) => decisionFilter === 'ALL' || item.decision === decisionFilter
  );

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
          {campaign.status !== 'FINALIZED' && (
            <button
              onClick={handleFinalize}
              className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-sm flex items-center gap-2"
            >
              <Lock className="w-4 h-4" />
              Finalize Campaign & Lock Decisions
            </button>
          )}
        </div>
      </div>

      {/* Hero Banner */}
      <div className="p-6 bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{campaign.title}</h1>
              <span
                className={`text-xs px-2.5 py-1 font-semibold rounded-full ${
                  campaign.status === 'FINALIZED'
                    ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
                    : 'bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300'
                }`}
              >
                {campaign.status}
              </span>
            </div>
            <p className="text-xs font-mono text-gray-500 mt-1">
              Code: {campaign.campaign_code} • Type: {campaign.campaign_type} • Deadline: {campaign.deadline}
            </p>
          </div>

          <div className="flex items-center gap-6">
            <div className="text-right">
              <p className="text-xs uppercase font-semibold text-gray-500">Certified</p>
              <p className="text-2xl font-bold text-emerald-600 mt-0.5">{campaign.certified_items_count}</p>
            </div>
            <div className="text-right">
              <p className="text-xs uppercase font-semibold text-gray-500">Revoked</p>
              <p className="text-2xl font-bold text-rose-600 mt-0.5">{campaign.revoked_items_count}</p>
            </div>
            <div className="text-right">
              <p className="text-xs uppercase font-semibold text-gray-500">Total Items</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-0.5">{campaign.total_items_count}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Certification Line Items */}
      <div className="p-4 bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm space-y-4">
        <div className="flex justify-between items-center">
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">Access Entitlements Under Review</h3>
            <p className="text-xs text-gray-500 mt-0.5">Four-Eyes rule: You cannot certify your own identity.</p>
          </div>

          <select
            value={decisionFilter}
            onChange={(e) => setDecisionFilter(e.target.value)}
            className="px-3 py-1.5 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-xs font-medium text-gray-900 dark:text-white"
          >
            <option value="ALL">All Decisions</option>
            <option value="PENDING">Pending Review</option>
            <option value="CERTIFIED">Certified</option>
            <option value="REVOKED">Revoked</option>
          </select>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-gray-600 dark:text-gray-400">
            <thead className="text-xs uppercase bg-gray-50 dark:bg-gray-800/50 text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-800">
              <tr>
                <th className="px-4 py-3 font-semibold">Identity</th>
                <th className="px-4 py-3 font-semibold">Entitlement / System</th>
                <th className="px-4 py-3 font-semibold">SoD Status</th>
                <th className="px-4 py-3 font-semibold">Decision</th>
                <th className="px-4 py-3 font-semibold text-right">Four-Eyes Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
              {filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                    No certification items matching filter.
                  </td>
                </tr>
              ) : (
                filteredItems.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/50">
                    <td className="px-4 py-3">
                      <div className="font-semibold text-gray-900 dark:text-white">{item.identity?.full_name}</div>
                      <div className="text-xs text-gray-500 font-mono">{item.identity?.email}</div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-900 dark:text-white">{item.entitlement?.name}</div>
                      <div className="text-xs text-gray-500 font-mono">
                        [{item.entitlement?.system_type}] {item.entitlement?.resource_name}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {item.is_sod_violation ? (
                        <span className="text-xs font-semibold px-2 py-0.5 rounded bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300">
                          SoD Conflict
                        </span>
                      ) : (
                        <span className="text-xs text-gray-400">Clean</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`text-xs px-2 py-0.5 font-semibold rounded-full ${
                          item.decision === 'CERTIFIED'
                            ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
                            : item.decision === 'REVOKED'
                            ? 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300'
                            : 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300'
                        }`}
                      >
                        {item.decision}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      {campaign.status !== 'FINALIZED' && item.decision === 'PENDING' ? (
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleReview(item.id, 'CERTIFIED')}
                            className="px-2.5 py-1 text-xs font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 dark:bg-emerald-950/40 dark:hover:bg-emerald-900 dark:text-emerald-300 border border-emerald-300 rounded-lg transition-colors flex items-center gap-1"
                          >
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            Certify
                          </button>
                          <button
                            onClick={() => handleReview(item.id, 'REVOKED')}
                            className="px-2.5 py-1 text-xs font-semibold text-rose-700 bg-rose-50 hover:bg-rose-100 dark:bg-rose-950/40 dark:hover:bg-rose-900 dark:text-rose-300 border border-rose-300 rounded-lg transition-colors flex items-center gap-1"
                          >
                            <XCircle className="w-3.5 h-3.5" />
                            Revoke
                          </button>
                        </div>
                      ) : (
                        <span className="text-xs text-gray-400 italic">Decision Recorded</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
