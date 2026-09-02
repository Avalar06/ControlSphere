import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Cloud,
  Shield,
  Plus,
  Search,
  ExternalLink,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  RefreshCw,
} from 'lucide-react';
import { cloudSecService } from '../lib/cloudSecService';
import { CloudPostureCard } from '../components/cloudsec/CloudPostureCard';
import { CloudAssetModal } from '../components/cloudsec/CloudAssetModal';
import { BenchmarkRuleModal } from '../components/cloudsec/BenchmarkRuleModal';
import type {
  CloudAsset,
  CloudPostureSummaryResponse,
  CloudProvider,
  CloudPostureStatus,
  CloudAssetCreate,
} from '../types';

export const CloudSecurityPage: React.FC = () => {
  const navigate = useNavigate();
  const [summary, setSummary] = useState<CloudPostureSummaryResponse | null>(null);
  const [assets, setAssets] = useState<CloudAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [providerFilter, setProviderFilter] = useState<string>('ALL');
  const [environmentFilter, setEnvironmentFilter] = useState<string>('ALL');
  const [postureFilter, setPostureFilter] = useState<string>('ALL');

  const [isAssetModalOpen, setIsAssetModalOpen] = useState(false);
  const [isRuleModalOpen, setIsRuleModalOpen] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [sumRes, assetsRes] = await Promise.all([
        cloudSecService.getPostureSummary(),
        cloudSecService.listAssets(),
      ]);
      setSummary(sumRes);
      setAssets(assetsRes);
    } catch (err) {
      console.error('Failed to load cloud security data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreateAsset = async (data: CloudAssetCreate) => {
    await cloudSecService.createAsset(data);
    fetchData();
  };

  const filteredAssets = assets.filter((asset) => {
    const matchesSearch =
      asset.asset_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
      asset.resource_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      asset.resource_arn.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesProvider = providerFilter === 'ALL' || asset.provider === providerFilter;
    const matchesEnv = environmentFilter === 'ALL' || asset.environment === environmentFilter;
    const matchesPosture = postureFilter === 'ALL' || asset.posture_status === postureFilter;

    return matchesSearch && matchesProvider && matchesEnv && matchesPosture;
  });

  const getPostureBadge = (status: CloudPostureStatus, score: number) => {
    switch (status) {
      case 'COMPLIANT':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
            <CheckCircle2 className="w-3.5 h-3.5" />
            COMPLIANT ({score}%)
          </span>
        );
      case 'NON_COMPLIANT':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 dark:bg-rose-950/50 dark:text-rose-300 border border-rose-200 dark:border-rose-800">
            <XCircle className="w-3.5 h-3.5" />
            NON-COMPLIANT ({score}%)
          </span>
        );
      case 'DEVIATED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
            <AlertTriangle className="w-3.5 h-3.5" />
            DEVIATED ({score}%)
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-gray-50 text-gray-700 dark:bg-gray-800 dark:text-gray-300 border border-gray-200 dark:border-gray-700">
            UNASSESSED
          </span>
        );
    }
  };

  const getProviderLogo = (provider: CloudProvider) => {
    return (
      <span className="px-2 py-0.5 text-xs font-mono font-bold rounded bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 border border-gray-300 dark:border-gray-700">
        {provider}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Cloud className="w-7 h-7 text-blue-600 dark:text-blue-400" />
            Cloud Security Posture Management (CSPM)
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Phase 18: Continuous configuration auditing, automated drift detection, and IAM blast radius quantification.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsRuleModalOpen(true)}
            className="px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors flex items-center gap-2 shadow-sm"
          >
            <Shield className="w-4 h-4 text-blue-500" />
            Add Rule
          </button>
          <button
            onClick={() => setIsAssetModalOpen(true)}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-xl shadow-sm transition-colors flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Register Asset
          </button>
        </div>
      </div>

      {/* Posture Summary Telemetry Card */}
      <CloudPostureCard summary={summary} loading={loading} />

      {/* Filters & Search */}
      <div className="p-4 bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row gap-4 justify-between">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search assets by code, resource name, or ARN..."
              className="w-full pl-9 pr-4 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <select
              value={providerFilter}
              onChange={(e) => setProviderFilter(e.target.value)}
              className="px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
            >
              <option value="ALL">All Providers</option>
              <option value="AWS">AWS</option>
              <option value="AZURE">Azure</option>
              <option value="GCP">GCP</option>
              <option value="OCI">OCI</option>
              <option value="ALIBABA">Alibaba</option>
            </select>

            <select
              value={environmentFilter}
              onChange={(e) => setEnvironmentFilter(e.target.value)}
              className="px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
            >
              <option value="ALL">All Environments</option>
              <option value="PRODUCTION">Production</option>
              <option value="STAGING">Staging</option>
              <option value="DEVELOPMENT">Development</option>
              <option value="SANDBOX">Sandbox</option>
            </select>

            <select
              value={postureFilter}
              onChange={(e) => setPostureFilter(e.target.value)}
              className="px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
            >
              <option value="ALL">All Posture Statuses</option>
              <option value="COMPLIANT">Compliant</option>
              <option value="NON_COMPLIANT">Non-Compliant</option>
              <option value="DEVIATED">Deviated</option>
            </select>

            <button
              onClick={fetchData}
              className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Cloud Asset Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-gray-600 dark:text-gray-400">
            <thead className="text-xs uppercase bg-gray-50 dark:bg-gray-800/50 text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-800">
              <tr>
                <th className="px-4 py-3 font-semibold">Asset Code / Name</th>
                <th className="px-4 py-3 font-semibold">Provider / Type</th>
                <th className="px-4 py-3 font-semibold">Environment</th>
                <th className="px-4 py-3 font-semibold">Posture Status</th>
                <th className="px-4 py-3 font-semibold">IAM Blast Radius</th>
                <th className="px-4 py-3 font-semibold">Lifecycle</th>
                <th className="px-4 py-3 font-semibold text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
              {filteredAssets.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                    No cloud assets registered matching current filters.
                  </td>
                </tr>
              ) : (
                filteredAssets.map((asset) => (
                  <tr
                    key={asset.id}
                    onClick={() => navigate(`/cloud-security/assets/${asset.id}`)}
                    className="hover:bg-gray-50/80 dark:hover:bg-gray-800/50 cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3">
                      <div className="font-semibold text-gray-900 dark:text-white flex items-center gap-1.5">
                        {asset.resource_name}
                      </div>
                      <div className="text-xs font-mono text-gray-500 dark:text-gray-400">{asset.asset_code}</div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {getProviderLogo(asset.provider)}
                        <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
                          {asset.resource_type.replace('_', ' ')}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs font-medium px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300">
                        {asset.environment}
                      </span>
                    </td>
                    <td className="px-4 py-3">{getPostureBadge(asset.posture_status, asset.posture_score)}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-gray-900 dark:text-white">
                          {asset.blast_radius_score.toFixed(1)}
                        </span>
                        <div className="w-16 bg-gray-200 dark:bg-gray-700 rounded-full h-1.5 overflow-hidden">
                          <div
                            className={`h-full ${
                              asset.blast_radius_score > 70
                                ? 'bg-rose-500'
                                : asset.blast_radius_score > 40
                                ? 'bg-amber-500'
                                : 'bg-blue-500'
                            }`}
                            style={{ width: `${Math.min(100, asset.blast_radius_score)}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`text-xs font-medium ${
                          asset.lifecycle_state === 'ACTIVE'
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : 'text-gray-500'
                        }`}
                      >
                        {asset.lifecycle_state}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/cloud-security/assets/${asset.id}`);
                        }}
                        className="p-1 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
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

      {/* Modals */}
      <CloudAssetModal
        isOpen={isAssetModalOpen}
        onClose={() => setIsAssetModalOpen(false)}
        onSubmit={handleCreateAsset}
      />
      <BenchmarkRuleModal
        isOpen={isRuleModalOpen}
        onClose={() => setIsRuleModalOpen(false)}
        onSuccess={fetchData}
      />
    </div>
  );
};
