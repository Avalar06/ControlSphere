import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { privacyService } from '../lib/privacyService';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from '../components/ui/Table';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { DataAssetModal } from '../components/privacy/DataAssetModal';
import { ProcessingActivityModal } from '../components/privacy/ProcessingActivityModal';
import { DPIAModal } from '../components/privacy/DPIAModal';
import { DataTransferModal } from '../components/privacy/DataTransferModal';
import { PrivacyApprovalModal } from '../components/privacy/PrivacyApprovalModal';
import { PrivacyLifecycleModal } from '../components/privacy/PrivacyLifecycleModal';
import type {
  DataAsset,
  DataSensitivityLevel,
  DataTransferAssessment,
  DPIAAssessment,
  DPIARiskBand,
  JurisdictionRiskTier,
  PrivacyApprovalStatus,
  ProcessingActivity,
  ProcessingLegalBasis,
  ProcessingLifecycleState,
} from '../types';
import {
  Activity,
  ArrowRight,
  Database,
  Edit2,
  Eye,
  FileCheck2,
  FileText,
  Filter,
  Globe,
  Lock,
  PieChart,
  Plus,
  Search,
  ShieldAlert,
  ShieldCheck,
  Trash2,
} from 'lucide-react';

type TabKey = 'activities' | 'assets' | 'dpia' | 'transfers' | 'posture';

export const PrivacyGovernancePage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { hasRole } = useAuth();

  const canManage = hasRole('ADMIN', 'MANAGER', 'GRC_ANALYST');
  const canAssess = hasRole('ADMIN', 'MANAGER', 'GRC_ANALYST', 'SECURITY_ANALYST');
  const canApprove = hasRole('ADMIN', 'MANAGER');

  const [activeTab, setActiveTab] = useState<TabKey>('activities');
  const [searchQuery, setSearchQuery] = useState('');

  // Filters
  const [activityStateFilter, setActivityStateFilter] = useState<ProcessingLifecycleState | 'ALL'>('ALL');
  const [activityLegalBasisFilter, setActivityLegalBasisFilter] = useState<ProcessingLegalBasis | 'ALL'>('ALL');
  const [assetSensitivityFilter, setAssetSensitivityFilter] = useState<DataSensitivityLevel | 'ALL'>('ALL');
  const [dpiaRiskBandFilter, setDpiaRiskBandFilter] = useState<DPIARiskBand | 'ALL'>('ALL');
  const [dpiaStatusFilter, setDpiaStatusFilter] = useState<PrivacyApprovalStatus | 'ALL'>('ALL');
  const [transferTierFilter, setTransferTierFilter] = useState<JurisdictionRiskTier | 'ALL'>('ALL');

  // Modals state
  const [isAssetModalOpen, setIsAssetModalOpen] = useState(false);
  const [editingAsset, setEditingAsset] = useState<DataAsset | null>(null);

  const [isActivityModalOpen, setIsActivityModalOpen] = useState(false);
  const [editingActivity, setEditingActivity] = useState<ProcessingActivity | null>(null);

  const [isDPIAModalOpen, setIsDPIAModalOpen] = useState(false);
  const [editingDPIA, setEditingDPIA] = useState<DPIAAssessment | null>(null);

  const [isTransferModalOpen, setIsTransferModalOpen] = useState(false);
  const [editingTransfer, setEditingTransfer] = useState<DataTransferAssessment | null>(null);

  const [lifecycleActivity, setLifecycleActivity] = useState<ProcessingActivity | null>(null);

  // Approval review modal state
  const [approvalModalData, setApprovalModalData] = useState<{
    isOpen: boolean;
    targetType: 'DPIA' | 'TRANSFER';
    targetId: number;
    targetCode: string;
    creatorOrRequesterId: number;
    currentStatus: PrivacyApprovalStatus;
  }>({
    isOpen: false,
    targetType: 'DPIA',
    targetId: 0,
    targetCode: '',
    creatorOrRequesterId: 0,
    currentStatus: 'PENDING',
  });

  // Queries
  const { data: postureSummary } = useQuery({
    queryKey: ['privacy-posture-summary'],
    queryFn: () => privacyService.getPostureSummary(),
  });

  const { data: activities = [], isLoading: isActivitiesLoading } = useQuery({
    queryKey: ['privacy-activities', activityStateFilter, activityLegalBasisFilter],
    queryFn: () =>
      privacyService.listProcessingActivities({
        lifecycle_state: activityStateFilter === 'ALL' ? undefined : activityStateFilter,
        legal_basis: activityLegalBasisFilter === 'ALL' ? undefined : activityLegalBasisFilter,
      }),
  });

  const { data: assets = [], isLoading: isAssetsLoading } = useQuery({
    queryKey: ['privacy-assets', assetSensitivityFilter],
    queryFn: () =>
      privacyService.listDataAssets({
        sensitivity: assetSensitivityFilter === 'ALL' ? undefined : assetSensitivityFilter,
      }),
  });

  const { data: dpias = [], isLoading: isDPIAsLoading } = useQuery({
    queryKey: ['privacy-dpias', dpiaRiskBandFilter, dpiaStatusFilter],
    queryFn: () =>
      privacyService.listDPIAs({
        risk_band: dpiaRiskBandFilter === 'ALL' ? undefined : dpiaRiskBandFilter,
        status_filter: dpiaStatusFilter === 'ALL' ? undefined : dpiaStatusFilter,
      }),
  });

  const { data: transfers = [], isLoading: isTransfersLoading } = useQuery({
    queryKey: ['privacy-transfers', transferTierFilter],
    queryFn: () =>
      privacyService.listDataTransfers({
        tier: transferTierFilter === 'ALL' ? undefined : transferTierFilter,
      }),
  });

  // Delete mutations
  const deleteAssetMutation = useMutation({
    mutationFn: (id: number) => privacyService.deleteDataAsset(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['privacy-assets'] });
      queryClient.invalidateQueries({ queryKey: ['privacy-posture-summary'] });
    },
  });

  const deleteActivityMutation = useMutation({
    mutationFn: (id: number) => privacyService.deleteProcessingActivity(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['privacy-activities'] });
      queryClient.invalidateQueries({ queryKey: ['privacy-posture-summary'] });
    },
  });

  // Filtered lists with local search query
  const filteredActivities = activities.filter(
    (a) =>
      a.activity_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a.purpose_description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredAssets = assets.filter(
    (a) =>
      a.asset_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredDPIAs = dpias.filter(
    (d) =>
      d.assessment_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
      d.risk_band.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredTransfers = transfers.filter(
    (t) =>
      t.transfer_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.destination_country.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getSensitivityBadge = (level: DataSensitivityLevel) => {
    switch (level) {
      case 'SPECIAL_CATEGORY':
        return <Badge variant="danger">SPECIAL CATEGORY (Art 9)</Badge>;
      case 'RESTRICTED_PII':
        return <Badge variant="warning">RESTRICTED PII</Badge>;
      case 'CONFIDENTIAL':
        return <Badge variant="info">CONFIDENTIAL</Badge>;
      case 'INTERNAL':
        return <Badge variant="default">INTERNAL</Badge>;
      case 'PUBLIC':
        return <Badge variant="success">PUBLIC</Badge>;
    }
  };

  const getLifecycleBadge = (state: ProcessingLifecycleState) => {
    switch (state) {
      case 'ACTIVE':
        return <Badge variant="success">ACTIVE</Badge>;
      case 'DPO_REVIEW':
        return <Badge variant="warning">DPO REVIEW</Badge>;
      case 'DRAFT':
        return <Badge variant="default">DRAFT</Badge>;
      case 'SUSPENDED':
        return <Badge variant="danger">SUSPENDED</Badge>;
      case 'ARCHIVED':
        return <Badge variant="default">ARCHIVED</Badge>;
      case 'RETIRED':
        return <Badge variant="danger">RETIRED (LOCKED)</Badge>;
    }
  };

  const getRiskBandBadge = (band: DPIARiskBand) => {
    switch (band) {
      case 'LOW':
        return <Badge variant="success">LOW</Badge>;
      case 'MODERATE':
        return <Badge variant="info">MODERATE</Badge>;
      case 'HIGH':
        return <Badge variant="warning">HIGH</Badge>;
      case 'VERY_HIGH':
        return <Badge variant="danger">VERY HIGH</Badge>;
      case 'CRITICAL':
        return <Badge variant="danger">CRITICAL</Badge>;
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 rounded-lg bg-indigo-600/10 border border-indigo-500/20 text-indigo-400">
              <Lock size={20} />
            </span>
            <div>
              <h1 className="text-xl font-bold text-slate-100">
                Continuous Privacy Governance (PRIVACY-GRC)
              </h1>
              <p className="text-xs text-slate-400">
                Article 30 RoPA Registry, DPIA Risk Quantification &amp; Cross-Border Transfer Impact Governance
              </p>
            </div>
          </div>
        </div>

        {/* Global Actions */}
        <div className="flex flex-wrap items-center gap-2">
          {canManage && (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setEditingAsset(null);
                  setIsAssetModalOpen(true);
                }}
                className="flex items-center gap-1.5"
              >
                <Plus size={14} />
                <span>New Data Asset</span>
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  setEditingActivity(null);
                  setIsActivityModalOpen(true);
                }}
                className="flex items-center gap-1.5"
              >
                <Plus size={14} />
                <span>New RoPA Activity</span>
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Executive Telemetry Row */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <Card className="p-3.5 bg-slate-900/90 border-slate-800">
          <div className="text-[11px] font-medium text-slate-400 uppercase">Data Assets</div>
          <div className="text-2xl font-bold font-mono text-slate-100 mt-1">
            {postureSummary?.total_data_assets ?? '—'}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">Catalogued stores</div>
        </Card>

        <Card className="p-3.5 bg-slate-900/90 border-slate-800">
          <div className="text-[11px] font-medium text-slate-400 uppercase">Active RoPAs</div>
          <div className="text-2xl font-bold font-mono text-emerald-400 mt-1">
            {postureSummary?.active_ropa_count ?? '—'}
            <span className="text-xs text-slate-500 font-normal"> / {postureSummary?.total_processing_activities ?? '—'}</span>
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">Article 30 flows</div>
        </Card>

        <Card className="p-3.5 bg-slate-900/90 border-slate-800">
          <div className="text-[11px] font-medium text-slate-400 uppercase">High/Critical Risks</div>
          <div className="text-2xl font-bold font-mono text-rose-400 mt-1">
            {postureSummary?.high_risk_processing_count ?? '—'}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">Requiring mitigation</div>
        </Card>

        <Card className="p-3.5 bg-slate-900/90 border-slate-800">
          <div className="text-[11px] font-medium text-slate-400 uppercase">Cross-Border TIAs</div>
          <div className="text-2xl font-bold font-mono text-sky-400 mt-1">
            {postureSummary?.cross_border_transfers_count ?? '—'}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">Chapter V transfers</div>
        </Card>

        <Card className="p-3.5 bg-slate-900/90 border-slate-800">
          <div className="text-[11px] font-medium text-slate-400 uppercase">Pending Approvals</div>
          <div className="text-2xl font-bold font-mono text-amber-400 mt-1">
            {(postureSummary?.pending_dpia_approvals ?? 0) +
              (postureSummary?.pending_transfer_approvals ?? 0)}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">Four-Eyes review</div>
        </Card>

        <Card className="p-3.5 bg-slate-900/90 border-slate-800">
          <div className="text-[11px] font-medium text-slate-400 uppercase">Avg Residual Risk</div>
          <div className="text-2xl font-bold font-mono text-indigo-400 mt-1">
            {postureSummary?.average_residual_risk_score !== undefined
              ? `${postureSummary.average_residual_risk_score.toFixed(1)}`
              : '—'}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">Server-calculated RRS</div>
        </Card>
      </div>

      {/* Tabs & Search Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-1.5 overflow-x-auto">
          <button
            onClick={() => setActiveTab('activities')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors cursor-pointer flex items-center gap-2 ${
              activeTab === 'activities'
                ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <FileText size={14} />
            <span>RoPA Register ({activities.length})</span>
          </button>
          <button
            onClick={() => setActiveTab('assets')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors cursor-pointer flex items-center gap-2 ${
              activeTab === 'assets'
                ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <Database size={14} />
            <span>Data Assets ({assets.length})</span>
          </button>
          <button
            onClick={() => setActiveTab('dpia')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors cursor-pointer flex items-center gap-2 ${
              activeTab === 'dpia'
                ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <ShieldAlert size={14} />
            <span>DPIA Assessments ({dpias.length})</span>
          </button>
          <button
            onClick={() => setActiveTab('transfers')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors cursor-pointer flex items-center gap-2 ${
              activeTab === 'transfers'
                ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <Globe size={14} />
            <span>Cross-Border Transfers ({transfers.length})</span>
          </button>
          <button
            onClick={() => setActiveTab('posture')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors cursor-pointer flex items-center gap-2 ${
              activeTab === 'posture'
                ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <PieChart size={14} />
            <span>Posture Telemetry</span>
          </button>
        </div>

        {activeTab !== 'posture' && (
          <div className="relative w-full sm:w-64">
            <Search size={14} className="absolute left-2.5 top-2.5 text-slate-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search privacy records..."
              className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded-md text-slate-200 focus:outline-hidden focus:border-indigo-500"
            />
          </div>
        )}
      </div>

      {/* ─── TAB 1: RoPA ACTIVITIES REGISTER ─────────────────────────────────── */}
      {activeTab === 'activities' && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <Filter size={13} />
              <span>State:</span>
              <select
                value={activityStateFilter}
                onChange={(e) => setActivityStateFilter(e.target.value as any)}
                className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-200 focus:outline-hidden"
              >
                <option value="ALL">ALL STATES</option>
                <option value="DRAFT">DRAFT</option>
                <option value="DPO_REVIEW">DPO_REVIEW</option>
                <option value="ACTIVE">ACTIVE</option>
                <option value="SUSPENDED">SUSPENDED</option>
                <option value="ARCHIVED">ARCHIVED</option>
                <option value="RETIRED">RETIRED</option>
              </select>
            </div>

            <div className="flex items-center gap-2 text-xs text-slate-400">
              <span>Legal Basis:</span>
              <select
                value={activityLegalBasisFilter}
                onChange={(e) => setActivityLegalBasisFilter(e.target.value as any)}
                className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-200 focus:outline-hidden"
              >
                <option value="ALL">ALL LEGAL BASES</option>
                <option value="CONSENT">CONSENT</option>
                <option value="CONTRACT_PERFORMANCE">CONTRACT_PERFORMANCE</option>
                <option value="LEGAL_OBLIGATION">LEGAL_OBLIGATION</option>
                <option value="LEGITIMATE_INTERESTS">LEGITIMATE_INTERESTS</option>
              </select>
            </div>
          </div>

          <Card className="overflow-hidden border-slate-800">
            {isActivitiesLoading ? (
              <div className="p-8 flex justify-center">
                <LoadingSpinner />
              </div>
            ) : filteredActivities.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-500">
                No GDPR Article 30 processing activities match your criteria.
              </div>
            ) : (
              <Table>
                <TableHead>
                  <TableRow>
                    <TableHeaderCell>CODE</TableHeaderCell>
                    <TableHeaderCell>NAME &amp; PURPOSE</TableHeaderCell>
                    <TableHeaderCell>LEGAL BASIS</TableHeaderCell>
                    <TableHeaderCell>LIFECYCLE</TableHeaderCell>
                    <TableHeaderCell>DPO STATUS</TableHeaderCell>
                    <TableHeaderCell>TRIGGERS</TableHeaderCell>
                    <TableHeaderCell className="text-right">ACTIONS</TableHeaderCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredActivities.map((act) => (
                    <TableRow key={act.id}>
                      <TableCell className="font-mono text-xs font-semibold text-indigo-400">
                        <Link
                          to={`/privacy/processing/${act.id}`}
                          className="hover:underline flex items-center gap-1"
                        >
                          {act.activity_code}
                          <ArrowRight size={11} className="text-slate-500" />
                        </Link>
                      </TableCell>
                      <TableCell>
                        <div className="font-medium text-slate-200 text-xs">{act.name}</div>
                        <div className="text-[11px] text-slate-400 truncate max-w-xs">
                          {act.purpose_description}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="default">{act.legal_basis}</Badge>
                      </TableCell>
                      <TableCell>{getLifecycleBadge(act.lifecycle_state)}</TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            act.dpo_approval_status === 'APPROVED'
                              ? 'success'
                              : act.dpo_approval_status === 'REJECTED'
                              ? 'danger'
                              : 'warning'
                          }
                        >
                          {act.dpo_approval_status}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1.5 flex-wrap text-[10px]">
                          {act.is_special_category_data && (
                            <span className="px-1.5 py-0.5 rounded bg-rose-950 text-rose-300 font-mono">
                              ART 9
                            </span>
                          )}
                          {act.is_automated_decision_making && (
                            <span className="px-1.5 py-0.5 rounded bg-purple-950 text-purple-300 font-mono">
                              ART 22
                            </span>
                          )}
                          {act.is_cross_border_transfer && (
                            <span className="px-1.5 py-0.5 rounded bg-sky-950 text-sky-300 font-mono">
                              TRANSFER
                            </span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => navigate(`/privacy/processing/${act.id}`)}
                            title="View RoPA Detail"
                          >
                            <Eye size={14} />
                          </Button>
                          {canManage && act.lifecycle_state !== 'RETIRED' && (
                            <>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  setEditingActivity(act);
                                  setIsActivityModalOpen(true);
                                }}
                                title="Edit RoPA"
                              >
                                <Edit2 size={14} />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setLifecycleActivity(act)}
                                title="Transition Lifecycle State"
                              >
                                <Activity size={14} />
                              </Button>
                              {act.lifecycle_state !== 'ACTIVE' && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => {
                                    if (confirm(`Delete activity ${act.activity_code}?`)) {
                                      deleteActivityMutation.mutate(act.id);
                                    }
                                  }}
                                  title="Delete RoPA"
                                  className="text-rose-400 hover:text-rose-300"
                                >
                                  <Trash2 size={14} />
                                </Button>
                              )}
                            </>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </Card>
        </div>
      )}

      {/* ─── TAB 2: DATA ASSETS INVENTORY ───────────────────────────────────── */}
      {activeTab === 'assets' && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <Filter size={13} />
            <span>Sensitivity:</span>
            <select
              value={assetSensitivityFilter}
              onChange={(e) => setAssetSensitivityFilter(e.target.value as any)}
              className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-200 focus:outline-hidden"
            >
              <option value="ALL">ALL CLASSIFICATIONS</option>
              <option value="PUBLIC">PUBLIC</option>
              <option value="INTERNAL">INTERNAL</option>
              <option value="CONFIDENTIAL">CONFIDENTIAL</option>
              <option value="RESTRICTED_PII">RESTRICTED_PII</option>
              <option value="SPECIAL_CATEGORY">SPECIAL_CATEGORY</option>
            </select>
          </div>

          <Card className="overflow-hidden border-slate-800">
            {isAssetsLoading ? (
              <div className="p-8 flex justify-center">
                <LoadingSpinner />
              </div>
            ) : filteredAssets.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-500">
                No personal data assets catalogued.
              </div>
            ) : (
              <Table>
                <TableHead>
                  <TableRow>
                    <TableHeaderCell>CODE</TableHeaderCell>
                    <TableHeaderCell>NAME</TableHeaderCell>
                    <TableHeaderCell>CLASSIFICATION</TableHeaderCell>
                    <TableHeaderCell>STORAGE TYPE</TableHeaderCell>
                    <TableHeaderCell>JURISDICTION</TableHeaderCell>
                    <TableHeaderCell>ENCRYPTION</TableHeaderCell>
                    <TableHeaderCell>RETENTION</TableHeaderCell>
                    <TableHeaderCell className="text-right">ACTIONS</TableHeaderCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredAssets.map((asset) => (
                    <TableRow key={asset.id}>
                      <TableCell className="font-mono text-xs font-semibold text-indigo-400">
                        <Link
                          to={`/privacy/assets/${asset.id}`}
                          className="hover:underline flex items-center gap-1"
                        >
                          {asset.asset_code}
                          <ArrowRight size={11} className="text-slate-500" />
                        </Link>
                      </TableCell>
                      <TableCell>
                        <div className="font-medium text-slate-200 text-xs">{asset.name}</div>
                        <div className="text-[11px] text-slate-400 truncate max-w-xs">
                          {asset.description || 'No description provided'}
                        </div>
                      </TableCell>
                      <TableCell>{getSensitivityBadge(asset.data_sensitivity_level)}</TableCell>
                      <TableCell className="font-mono text-xs text-slate-300">
                        {asset.storage_type}
                      </TableCell>
                      <TableCell className="text-xs text-slate-300">
                        {asset.hosting_jurisdiction}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1.5 text-[10px]">
                          {asset.is_encrypted_at_rest && (
                            <span className="px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-300">
                              REST
                            </span>
                          )}
                          {asset.is_encrypted_in_transit && (
                            <span className="px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-300">
                              TRANSIT
                            </span>
                          )}
                          {asset.is_pseudonymized && (
                            <span className="px-1.5 py-0.5 rounded bg-purple-950 text-purple-300">
                              PSEUDO
                            </span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-xs text-slate-300 font-mono">
                        {asset.retention_period_months ? `${asset.retention_period_months} mo` : '—'}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => navigate(`/privacy/assets/${asset.id}`)}
                            title="View Data Asset Detail"
                          >
                            <Eye size={14} />
                          </Button>
                          {canManage && (
                            <>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  setEditingAsset(asset);
                                  setIsAssetModalOpen(true);
                                }}
                                title="Edit Asset"
                              >
                                <Edit2 size={14} />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  if (confirm(`Delete data asset ${asset.asset_code}?`)) {
                                    deleteAssetMutation.mutate(asset.id);
                                  }
                                }}
                                title="Delete Asset"
                                className="text-rose-400 hover:text-rose-300"
                              >
                                <Trash2 size={14} />
                              </Button>
                            </>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </Card>
        </div>
      )}

      {/* ─── TAB 3: DPIA ASSESSMENTS ─────────────────────────────────────────── */}
      {activeTab === 'dpia' && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <Filter size={13} />
                <span>Risk Band:</span>
                <select
                  value={dpiaRiskBandFilter}
                  onChange={(e) => setDpiaRiskBandFilter(e.target.value as any)}
                  className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-200 focus:outline-hidden"
                >
                  <option value="ALL">ALL RISK BANDS</option>
                  <option value="LOW">LOW</option>
                  <option value="MODERATE">MODERATE</option>
                  <option value="HIGH">HIGH</option>
                  <option value="VERY_HIGH">VERY HIGH</option>
                  <option value="CRITICAL">CRITICAL</option>
                </select>
              </div>

              <div className="flex items-center gap-2 text-xs text-slate-400">
                <span>DPO Status:</span>
                <select
                  value={dpiaStatusFilter}
                  onChange={(e) => setDpiaStatusFilter(e.target.value as any)}
                  className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-200 focus:outline-hidden"
                >
                  <option value="ALL">ALL STATUSES</option>
                  <option value="PENDING">PENDING</option>
                  <option value="APPROVED">APPROVED</option>
                  <option value="REJECTED">REJECTED</option>
                </select>
              </div>
            </div>

            {canAssess && (
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  setEditingDPIA(null);
                  setIsDPIAModalOpen(true);
                }}
                className="flex items-center gap-1.5"
              >
                <Plus size={14} />
                <span>Initiate DPIA</span>
              </Button>
            )}
          </div>

          <Card className="overflow-hidden border-slate-800">
            {isDPIAsLoading ? (
              <div className="p-8 flex justify-center">
                <LoadingSpinner />
              </div>
            ) : filteredDPIAs.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-500">
                No DPIA assessments recorded.
              </div>
            ) : (
              <Table>
                <TableHead>
                  <TableRow>
                    <TableHeaderCell>CODE</TableHeaderCell>
                    <TableHeaderCell>ACTIVITY ID</TableHeaderCell>
                    <TableHeaderCell>INHERENT RISK (IRS)</TableHeaderCell>
                    <TableHeaderCell>RESIDUAL RISK (RRS)</TableHeaderCell>
                    <TableHeaderCell>RISK BAND</TableHeaderCell>
                    <TableHeaderCell>DPO CONSULTATION</TableHeaderCell>
                    <TableHeaderCell className="text-right">ACTIONS</TableHeaderCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredDPIAs.map((d) => (
                    <TableRow key={d.id}>
                      <TableCell className="font-mono text-xs font-semibold text-indigo-400">
                        {d.assessment_code}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-slate-300">
                        <Link
                          to={`/privacy/processing/${d.processing_activity_id}`}
                          className="hover:underline flex items-center gap-1 text-slate-300 hover:text-indigo-400"
                        >
                          Activity #{d.processing_activity_id}
                          <ArrowRight size={11} className="text-slate-500" />
                        </Link>
                      </TableCell>
                      <TableCell className="font-mono text-xs text-amber-400 font-bold">
                        {d.inherent_risk_score.toFixed(1)} / 100
                      </TableCell>
                      <TableCell className="font-mono text-xs text-indigo-400 font-bold">
                        {d.residual_risk_score.toFixed(1)} / 100
                      </TableCell>
                      <TableCell>{getRiskBandBadge(d.risk_band)}</TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            d.dpo_consultation_status === 'APPROVED'
                              ? 'success'
                              : d.dpo_consultation_status === 'REJECTED'
                              ? 'danger'
                              : 'warning'
                          }
                        >
                          {d.dpo_consultation_status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {canAssess && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setEditingDPIA(d);
                                setIsDPIAModalOpen(true);
                              }}
                              title="Update DPIA Scores"
                            >
                              <Edit2 size={14} />
                            </Button>
                          )}
                          {canApprove && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                setApprovalModalData({
                                  isOpen: true,
                                  targetType: 'DPIA',
                                  targetId: d.id,
                                  targetCode: d.assessment_code,
                                  creatorOrRequesterId: d.created_by_id,
                                  currentStatus: d.dpo_consultation_status,
                                });
                              }}
                              className="flex items-center gap-1 text-xs"
                            >
                              <ShieldCheck size={13} />
                              <span>Review</span>
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </Card>
        </div>
      )}

      {/* ─── TAB 4: CROSS-BORDER TRANSFERS ──────────────────────────────────── */}
      {activeTab === 'transfers' && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <Filter size={13} />
              <span>Jurisdiction Tier:</span>
              <select
                value={transferTierFilter}
                onChange={(e) => setTransferTierFilter(e.target.value as any)}
                className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-200 focus:outline-hidden"
              >
                <option value="ALL">ALL TIERS</option>
                <option value="ADEQUATE_EEA_EQUIVALENT">ADEQUATE</option>
                <option value="MODERATE_SAFEGUARDS_REQUIRED">MODERATE SAFEGUARDS</option>
                <option value="HIGH_RISK_SURVEILLANCE">HIGH RISK SURVEILLANCE</option>
                <option value="RESTRICTED_EMBARGOED">RESTRICTED EMBARGOED</option>
              </select>
            </div>

            {canAssess && (
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  setEditingTransfer(null);
                  setIsTransferModalOpen(true);
                }}
                className="flex items-center gap-1.5"
              >
                <Plus size={14} />
                <span>Assess New Transfer</span>
              </Button>
            )}
          </div>

          <Card className="overflow-hidden border-slate-800">
            {isTransfersLoading ? (
              <div className="p-8 flex justify-center">
                <LoadingSpinner />
              </div>
            ) : filteredTransfers.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-500">
                No cross-border transfer assessments recorded.
              </div>
            ) : (
              <Table>
                <TableHead>
                  <TableRow>
                    <TableHeaderCell>CODE</TableHeaderCell>
                    <TableHeaderCell>DESTINATION</TableHeaderCell>
                    <TableHeaderCell>JURISDICTION TIER</TableHeaderCell>
                    <TableHeaderCell>MECHANISM</TableHeaderCell>
                    <TableHeaderCell>TRANSFER RISK (TRI)</TableHeaderCell>
                    <TableHeaderCell>STATUS</TableHeaderCell>
                    <TableHeaderCell className="text-right">ACTIONS</TableHeaderCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredTransfers.map((t) => (
                    <TableRow key={t.id}>
                      <TableCell className="font-mono text-xs font-semibold text-indigo-400">
                        {t.transfer_code}
                      </TableCell>
                      <TableCell>
                        <div className="font-medium text-slate-200 text-xs">{t.destination_country}</div>
                        <div className="text-[10px] text-slate-500">From: {t.source_country}</div>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            t.destination_jurisdiction_tier === 'ADEQUATE_EEA_EQUIVALENT'
                              ? 'success'
                              : t.destination_jurisdiction_tier === 'MODERATE_SAFEGUARDS_REQUIRED'
                              ? 'info'
                              : 'danger'
                          }
                        >
                          {t.destination_jurisdiction_tier}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-xs text-slate-300">
                        {t.transfer_mechanism}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-sky-400 font-bold">
                        {t.transfer_risk_index.toFixed(1)} / 100
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            t.approval_status === 'APPROVED'
                              ? 'success'
                              : t.approval_status === 'REJECTED'
                              ? 'danger'
                              : 'warning'
                          }
                        >
                          {t.approval_status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {canApprove && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                setApprovalModalData({
                                  isOpen: true,
                                  targetType: 'TRANSFER',
                                  targetId: t.id,
                                  targetCode: t.transfer_code,
                                  creatorOrRequesterId: t.requested_by_id,
                                  currentStatus: t.approval_status,
                                });
                              }}
                              className="flex items-center gap-1 text-xs"
                            >
                              <ShieldCheck size={13} />
                              <span>Review</span>
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </Card>
        </div>
      )}

      {/* ─── TAB 5: EXECUTIVE POSTURE & TELEMETRY ────────────────────────────── */}
      {activeTab === 'posture' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Risk Band Distribution */}
          <Card className="p-5 bg-slate-900 border-slate-800">
            <h3 className="text-sm font-semibold text-slate-200 mb-3 flex items-center gap-2">
              <ShieldAlert size={16} className="text-rose-400" />
              DPIA Risk Band Distribution
            </h3>
            {postureSummary?.risk_band_distribution ? (
              <div className="space-y-2">
                {Object.entries(postureSummary.risk_band_distribution).map(([band, count]) => (
                  <div key={band} className="flex items-center justify-between text-xs p-2 rounded bg-slate-950/60 border border-slate-800/80">
                    <span className="text-slate-300 font-mono">{band}</span>
                    <span className="font-bold text-indigo-400">{count} assessments</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-xs text-slate-500">No telemetry available</div>
            )}
          </Card>

          {/* Legal Basis Distribution */}
          <Card className="p-5 bg-slate-900 border-slate-800">
            <h3 className="text-sm font-semibold text-slate-200 mb-3 flex items-center gap-2">
              <FileCheck2 size={16} className="text-indigo-400" />
              Article 6 Legal Basis Distribution
            </h3>
            {postureSummary?.legal_basis_distribution ? (
              <div className="space-y-2">
                {Object.entries(postureSummary.legal_basis_distribution).map(([basis, count]) => (
                  <div key={basis} className="flex items-center justify-between text-xs p-2 rounded bg-slate-950/60 border border-slate-800/80">
                    <span className="text-slate-300 font-mono">{basis}</span>
                    <span className="font-bold text-emerald-400">{count} activities</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-xs text-slate-500">No telemetry available</div>
            )}
          </Card>

          {/* Sensitivity Distribution */}
          <Card className="p-5 bg-slate-900 border-slate-800 md:col-span-2">
            <h3 className="text-sm font-semibold text-slate-200 mb-3 flex items-center gap-2">
              <Database size={16} className="text-cyan-400" />
              Data Asset Sensitivity Breakdown
            </h3>
            {postureSummary?.sensitivity_distribution ? (
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                {Object.entries(postureSummary.sensitivity_distribution).map(([level, count]) => (
                  <div key={level} className="p-3 rounded bg-slate-950/60 border border-slate-800 text-center">
                    <div className="text-[10px] text-slate-400 font-mono uppercase">{level}</div>
                    <div className="text-xl font-bold font-mono text-cyan-400 mt-1">{count}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-xs text-slate-500">No telemetry available</div>
            )}
          </Card>
        </div>
      )}

      {/* ─── MODALS ─────────────────────────────────────────────────────────── */}
      <DataAssetModal
        isOpen={isAssetModalOpen}
        onClose={() => setIsAssetModalOpen(false)}
        asset={editingAsset}
        onSuccess={() => {
          queryClient.invalidateQueries({ queryKey: ['privacy-assets'] });
          queryClient.invalidateQueries({ queryKey: ['privacy-posture-summary'] });
        }}
      />

      <ProcessingActivityModal
        isOpen={isActivityModalOpen}
        onClose={() => setIsActivityModalOpen(false)}
        activity={editingActivity}
        onSuccess={() => {
          queryClient.invalidateQueries({ queryKey: ['privacy-activities'] });
          queryClient.invalidateQueries({ queryKey: ['privacy-posture-summary'] });
        }}
      />

      <DPIAModal
        isOpen={isDPIAModalOpen}
        onClose={() => setIsDPIAModalOpen(false)}
        dpia={editingDPIA}
        onSuccess={() => {
          queryClient.invalidateQueries({ queryKey: ['privacy-dpias'] });
          queryClient.invalidateQueries({ queryKey: ['privacy-posture-summary'] });
        }}
      />

      <DataTransferModal
        isOpen={isTransferModalOpen}
        onClose={() => setIsTransferModalOpen(false)}
        transfer={editingTransfer}
        onSuccess={() => {
          queryClient.invalidateQueries({ queryKey: ['privacy-transfers'] });
          queryClient.invalidateQueries({ queryKey: ['privacy-posture-summary'] });
        }}
      />

      <PrivacyLifecycleModal
        isOpen={Boolean(lifecycleActivity)}
        onClose={() => setLifecycleActivity(null)}
        activity={lifecycleActivity}
        onSuccess={() => {
          queryClient.invalidateQueries({ queryKey: ['privacy-activities'] });
          queryClient.invalidateQueries({ queryKey: ['privacy-posture-summary'] });
        }}
      />

      <PrivacyApprovalModal
        isOpen={approvalModalData.isOpen}
        onClose={() =>
          setApprovalModalData((prev) => ({ ...prev, isOpen: false }))
        }
        targetType={approvalModalData.targetType}
        targetId={approvalModalData.targetId}
        targetCode={approvalModalData.targetCode}
        creatorOrRequesterId={approvalModalData.creatorOrRequesterId}
        currentStatus={approvalModalData.currentStatus}
        onSuccess={() => {
          queryClient.invalidateQueries({ queryKey: ['privacy-dpias'] });
          queryClient.invalidateQueries({ queryKey: ['privacy-transfers'] });
          queryClient.invalidateQueries({ queryKey: ['privacy-posture-summary'] });
        }}
      />
    </div>
  );
};
