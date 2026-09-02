import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  ShieldAlert,
  Plus,
  GitCommit,
  Key,
} from 'lucide-react';
import { cloudSecService } from '../lib/cloudSecService';
import { FindingRecordModal } from '../components/cloudsec/FindingRecordModal';
import { DriftRecordModal } from '../components/cloudsec/DriftRecordModal';
import { BlastRadiusModal } from '../components/cloudsec/BlastRadiusModal';
import type {
  CloudAsset,
  CloudSecurityFinding,
  CloudConfigurationDrift,
} from '../types';

export const CloudAssetDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const assetId = parseInt(id || '0');

  const [asset, setAsset] = useState<CloudAsset | null>(null);
  const [findings, setFindings] = useState<CloudSecurityFinding[]>([]);
  const [drifts, setDrifts] = useState<CloudConfigurationDrift[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'FINDINGS' | 'DRIFT' | 'BLAST_RADIUS'>('FINDINGS');

  const [isFindingModalOpen, setIsFindingModalOpen] = useState(false);
  const [isDriftModalOpen, setIsDriftModalOpen] = useState(false);
  const [isBlastModalOpen, setIsBlastModalOpen] = useState(false);

  const fetchAssetData = async () => {
    if (!assetId) return;
    setLoading(true);
    try {
      const [assetRes, findingsRes, driftsRes] = await Promise.all([
        cloudSecService.getAsset(assetId),
        cloudSecService.listFindings({ asset_id: assetId }),
        cloudSecService.listDrifts({ asset_id: assetId }),
      ]);
      setAsset(assetRes);
      setFindings(findingsRes);
      setDrifts(driftsRes);
    } catch (err) {
      console.error('Failed to load asset details', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAssetData();
  }, [assetId]);

  const handleDecommission = async () => {
    if (!asset) return;
    const confirm = window.confirm(
      'Are you sure you want to transition this cloud asset to DECOMMISSIONED state?'
    );
    if (!confirm) return;
    try {
      await cloudSecService.updateAssetStatus(asset.id, {
        lifecycle_state: 'DECOMMISSIONED',
        notes: 'Governed decommissioning audit',
      });
      fetchAssetData();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to update asset lifecycle');
    }
  };

  if (loading || !asset) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/cloud-security')}
          className="inline-flex items-center gap-2 text-sm font-medium text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Cloud Security
        </button>

        <div className="flex items-center gap-3">
          {asset.lifecycle_state === 'ACTIVE' && (
            <button
              onClick={handleDecommission}
              className="px-3 py-1.5 text-xs font-medium text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 rounded-xl hover:bg-amber-100 dark:hover:bg-amber-900 transition-colors"
            >
              Decommission Asset
            </button>
          )}
        </div>
      </div>

      {/* Asset Hero Banner */}
      <div className="p-6 bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <span className="px-2.5 py-1 text-xs font-mono font-bold rounded bg-blue-50 text-blue-700 dark:bg-blue-950/50 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
                {asset.provider}
              </span>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{asset.resource_name}</h1>
              <span className="text-xs px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300">
                {asset.environment}
              </span>
            </div>
            <p className="text-xs font-mono text-gray-500 dark:text-gray-400 mt-1 break-all">{asset.resource_arn}</p>
          </div>

          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-xs uppercase font-semibold text-gray-500 dark:text-gray-400">Posture Score</p>
              <p className="text-3xl font-bold text-gray-900 dark:text-white mt-0.5">{asset.posture_score}%</p>
            </div>
            <div className="text-right">
              <p className="text-xs uppercase font-semibold text-gray-500 dark:text-gray-400">Blast Radius</p>
              <p className="text-3xl font-bold text-purple-600 dark:text-purple-400 mt-0.5">
                {asset.blast_radius_score.toFixed(1)}
              </p>
            </div>
          </div>
        </div>

        {/* Metadata Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-gray-100 dark:border-gray-800 text-xs">
          <div>
            <span className="text-gray-500 dark:text-gray-400">Account ID:</span>
            <p className="font-semibold text-gray-900 dark:text-white font-mono mt-0.5">{asset.account_id}</p>
          </div>
          <div>
            <span className="text-gray-500 dark:text-gray-400">Region:</span>
            <p className="font-semibold text-gray-900 dark:text-white mt-0.5">{asset.region}</p>
          </div>
          <div>
            <span className="text-gray-500 dark:text-gray-400">Criticality:</span>
            <p className="font-semibold text-gray-900 dark:text-white mt-0.5">{asset.criticality}</p>
          </div>
          <div>
            <span className="text-gray-500 dark:text-gray-400">Encryption at Rest:</span>
            <p className="font-semibold text-gray-900 dark:text-white mt-0.5">
              {asset.encryption_enabled ? 'Enabled (KMS)' : 'Disabled'}
            </p>
          </div>
        </div>
      </div>

      {/* Detail Navigation Tabs & Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-200 dark:border-gray-800 pb-2">
        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab('FINDINGS')}
            className={`px-4 py-2 text-sm font-medium rounded-xl transition-colors flex items-center gap-2 ${
              activeTab === 'FINDINGS'
                ? 'bg-blue-50 text-blue-600 dark:bg-blue-950/50 dark:text-blue-400'
                : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white'
            }`}
          >
            <ShieldAlert className="w-4 h-4" />
            CSPM Findings ({findings.length})
          </button>
          <button
            onClick={() => setActiveTab('DRIFT')}
            className={`px-4 py-2 text-sm font-medium rounded-xl transition-colors flex items-center gap-2 ${
              activeTab === 'DRIFT'
                ? 'bg-blue-50 text-blue-600 dark:bg-blue-950/50 dark:text-blue-400'
                : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white'
            }`}
          >
            <GitCommit className="w-4 h-4" />
            Configuration Drift ({drifts.length})
          </button>
          <button
            onClick={() => setActiveTab('BLAST_RADIUS')}
            className={`px-4 py-2 text-sm font-medium rounded-xl transition-colors flex items-center gap-2 ${
              activeTab === 'BLAST_RADIUS'
                ? 'bg-blue-50 text-blue-600 dark:bg-blue-950/50 dark:text-blue-400'
                : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white'
            }`}
          >
            <Key className="w-4 h-4" />
            IAM Blast Radius
          </button>
        </div>

        <div>
          {activeTab === 'FINDINGS' && (
            <button
              onClick={() => setIsFindingModalOpen(true)}
              className="px-3 py-1.5 text-xs font-medium text-white bg-rose-600 hover:bg-rose-700 rounded-xl shadow-sm flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" />
              Record Finding
            </button>
          )}
          {activeTab === 'DRIFT' && (
            <button
              onClick={() => setIsDriftModalOpen(true)}
              className="px-3 py-1.5 text-xs font-medium text-white bg-amber-600 hover:bg-amber-700 rounded-xl shadow-sm flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" />
              Record Drift
            </button>
          )}
          {activeTab === 'BLAST_RADIUS' && (
            <button
              onClick={() => setIsBlastModalOpen(true)}
              className="px-3 py-1.5 text-xs font-medium text-white bg-purple-600 hover:bg-purple-700 rounded-xl shadow-sm flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" />
              Analyze Blast Radius
            </button>
          )}
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === 'FINDINGS' && (
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-gray-600 dark:text-gray-400">
              <thead className="text-xs uppercase bg-gray-50 dark:bg-gray-800/50 text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-800">
                <tr>
                  <th className="px-4 py-3 font-semibold">Finding Code</th>
                  <th className="px-4 py-3 font-semibold">Evaluation Status</th>
                  <th className="px-4 py-3 font-semibold">Severity</th>
                  <th className="px-4 py-3 font-semibold">Calculated Risk Score</th>
                  <th className="px-4 py-3 font-semibold">Evaluated At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                {findings.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                      No security findings recorded for this asset.
                    </td>
                  </tr>
                ) : (
                  findings.map((f) => (
                    <tr key={f.id} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/50">
                      <td className="px-4 py-3 font-mono font-semibold text-gray-900 dark:text-white">
                        {f.finding_code}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`text-xs px-2 py-0.5 font-semibold rounded-full ${
                            f.evaluation_status === 'PASSED'
                              ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
                              : 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300'
                          }`}
                        >
                          {f.evaluation_status}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-xs font-semibold text-rose-600 dark:text-rose-400">{f.severity}</span>
                      </td>
                      <td className="px-4 py-3 font-bold text-gray-900 dark:text-white">{f.risk_score}</td>
                      <td className="px-4 py-3 text-xs text-gray-500">{new Date(f.evaluated_at).toLocaleString()}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'DRIFT' && (
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-gray-600 dark:text-gray-400">
              <thead className="text-xs uppercase bg-gray-50 dark:bg-gray-800/50 text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-800">
                <tr>
                  <th className="px-4 py-3 font-semibold">Drift Code</th>
                  <th className="px-4 py-3 font-semibold">Attribute Path</th>
                  <th className="px-4 py-3 font-semibold">Severity</th>
                  <th className="px-4 py-3 font-semibold">Drift Score</th>
                  <th className="px-4 py-3 font-semibold">Status</th>
                  <th className="px-4 py-3 font-semibold">Detected At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                {drifts.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                      No configuration drifts detected.
                    </td>
                  </tr>
                ) : (
                  drifts.map((d) => (
                    <tr key={d.id} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/50">
                      <td className="px-4 py-3 font-mono font-semibold text-gray-900 dark:text-white">
                        {d.drift_code}
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-gray-700 dark:text-gray-300">
                        {d.attribute_path}
                      </td>
                      <td className="px-4 py-3 font-semibold text-amber-600">{d.drift_severity}</td>
                      <td className="px-4 py-3 font-bold text-gray-900 dark:text-white">{d.drift_score}</td>
                      <td className="px-4 py-3 text-xs font-semibold">{d.status}</td>
                      <td className="px-4 py-3 text-xs text-gray-500">{new Date(d.detected_at).toLocaleString()}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'BLAST_RADIUS' && (
        <div className="p-6 bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-bold text-gray-900 dark:text-white">IAM Blast Radius Quantification</h3>
              <p className="text-xs text-gray-500 mt-1">
                Deterministic mathematical model quantifying access propagation risk from IAM role misconfiguration.
              </p>
            </div>
            <div className="p-3 bg-purple-50 dark:bg-purple-950/40 rounded-xl border border-purple-200 dark:border-purple-800">
              <span className="text-2xl font-bold text-purple-700 dark:text-purple-300">
                {asset.blast_radius_score.toFixed(1)} / 100
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Modals */}
      <FindingRecordModal
        isOpen={isFindingModalOpen}
        onClose={() => setIsFindingModalOpen(false)}
        asset={asset}
        onSuccess={fetchAssetData}
      />
      <DriftRecordModal
        isOpen={isDriftModalOpen}
        onClose={() => setIsDriftModalOpen(false)}
        asset={asset}
        onSuccess={fetchAssetData}
      />
      <BlastRadiusModal
        isOpen={isBlastModalOpen}
        onClose={() => setIsBlastModalOpen(false)}
        asset={asset}
        onSuccess={fetchAssetData}
      />
    </div>
  );
};
