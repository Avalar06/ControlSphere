import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Database,
  ShieldCheck,
  GitBranch,
  Cloud,
  AlertTriangle,
  Plus,
  Search,
  Scale,
  Layers,
  ArrowRight,
  Hash,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { dataGovernanceService } from '../lib/dataGovernanceService';
import type {
  DataAssetType,
  DataClassificationLevelCreate,
  DataClassificationSchemeCreate,
  DataDisposalMethod,
  DataLineageEdgeCreate,
  DataLineageRelationshipType,
  DataSensitivityLevel,
  GovernedDataAssetCreate,
} from '../types/dataGovernance';

const SENSITIVITY_BADGE: Record<DataSensitivityLevel, string> = {
  PUBLIC: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  INTERNAL: 'bg-sky-500/15 text-sky-300 border-sky-500/30',
  CONFIDENTIAL: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  RESTRICTED_PII: 'bg-orange-500/15 text-orange-300 border-orange-500/30',
  SPECIAL_CATEGORY_SENSITIVE_PHI: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
};

const LIFECYCLE_BADGE: Record<string, string> = {
  DISCOVERED: 'bg-purple-500/15 text-purple-300 border-purple-500/30',
  REGISTERED: 'bg-blue-500/15 text-blue-300 border-blue-500/30',
  CLASSIFIED: 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30',
  ACTIVE: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  DEPRECATED: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  RETIRED: 'bg-slate-700/50 text-slate-400 border-slate-600/40',
};

export const DataGovernancePage: React.FC = () => {
  const queryClient = useQueryClient();
  const { hasRole } = useAuth();

  const canManage = hasRole('ADMIN', 'MANAGER', 'GRC_ANALYST');
  const canClassifyOrLineage = hasRole(
    'ADMIN',
    'MANAGER',
    'GRC_ANALYST',
    'SECURITY_ANALYST'
  );
  const canApprove = hasRole('ADMIN', 'MANAGER');

  const [activeTab, setActiveTab] = useState<
    'catalog' | 'schemes' | 'lineage'
  >('catalog');
  const [lifecycleFilter, setLifecycleFilter] = useState<string>('');
  const [sensitivityFilter, setSensitivityFilter] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [selectedAssetId, setSelectedAssetId] = useState<number | null>(null);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  // Modals
  const [isCreateAssetOpen, setIsCreateAssetOpen] = useState(false);
  const [isClassifyOpen, setIsClassifyOpen] = useState(false);
  const [isOwnershipOpen, setIsOwnershipOpen] = useState(false);
  const [isRetireOpen, setIsRetireOpen] = useState(false);
  const [isCreateSchemeOpen, setIsCreateSchemeOpen] = useState(false);
  const [isAddLevelOpen, setIsAddLevelOpen] = useState(false);
  const [selectedSchemeId, setSelectedSchemeId] = useState<number | null>(null);
  const [isCreateLineageOpen, setIsCreateLineageOpen] = useState(false);
  const [isLinkCloudOpen, setIsLinkCloudOpen] = useState(false);
  const [isLinkRopaOpen, setIsLinkRopaOpen] = useState(false);
  const [isLinkControlOpen, setIsLinkControlOpen] = useState(false);

  // Form states
  const [newAsset, setNewAsset] = useState<GovernedDataAssetCreate>({
    asset_code: '',
    name: '',
    description: '',
    asset_type: 'DATABASE_TABLE',
    initial_lifecycle_state: 'REGISTERED',
    data_sensitivity_level: 'INTERNAL',
    data_volume_range: '10K_100K',
    storage_type: 'POSTGRES_DB',
    hosting_jurisdiction: 'EU_EEA',
    is_encrypted_at_rest: true,
    is_encrypted_in_transit: true,
    is_pseudonymized: false,
    retention_period_months: 36,
  });

  const [classifyForm, setClassifyForm] = useState({
    scheme_id: 0,
    level_id: 0,
    justification: '',
    require_approval: false,
  });

  const [ownershipForm, setOwnershipForm] = useState({
    owner_id: '',
    steward_id: '',
    justification: '',
    require_approval: true,
  });

  const [retireForm, setRetireForm] = useState<{
    disposal_method: DataDisposalMethod;
    retirement_notes: string;
    retirement_evidence_id: string;
    mode: 'request' | 'finalize';
  }>({
    disposal_method: 'CRYPTOGRAPHIC_ERASURE',
    retirement_notes: '',
    retirement_evidence_id: '',
    mode: 'request',
  });

  const [newScheme, setNewScheme] = useState<DataClassificationSchemeCreate>({
    scheme_code: '',
    name: '',
    description: '',
    version: 1,
    is_default: true,
  });

  const [newLevel, setNewLevel] = useState<DataClassificationLevelCreate>({
    level_code: '',
    name: '',
    description: '',
    ordinal_rank: 1,
    mapped_sensitivity_level: 'INTERNAL',
    requires_encryption_at_rest: true,
    requires_encryption_in_transit: true,
    requires_four_eyes_approval: false,
    default_retention_months: 24,
  });

  const [newLineage, setNewLineage] = useState<DataLineageEdgeCreate>({
    edge_code: '',
    source_data_asset_id: 0,
    target_data_asset_id: 0,
    relationship_type: 'ETL_TRANSFORMATION',
    transformation_summary: '',
    is_encrypted_in_transit: true,
    is_masked_or_anonymized: false,
    require_approval: false,
  });

  const [cloudLinkForm, setCloudLinkForm] = useState({
    cloud_asset_id: '',
    hosting_role: 'PRIMARY_STORE' as const,
    notes: '',
  });

  const [ropaLinkForm, setRopaLinkForm] = useState({
    processing_activity_id: '',
    usage_role: 'PRIMARY_SOURCE' as const,
    notes: '',
  });

  const [controlLinkForm, setControlLinkForm] = useState({
    organization_control_id: '',
    control_objective: 'ENCRYPTION_AT_REST' as const,
    coverage_notes: '',
  });

  // Queries
  const { data: summary } = useQuery({
    queryKey: ['dataGovSummary'],
    queryFn: dataGovernanceService.getSummary,
  });

  const { data: assets = [], isLoading: isAssetsLoading } = useQuery({
    queryKey: ['dataGovAssets', lifecycleFilter, sensitivityFilter],
    queryFn: () =>
      dataGovernanceService.listAssets({
        lifecycle_state: lifecycleFilter || undefined,
        sensitivity_level: sensitivityFilter || undefined,
      }),
  });

  const { data: dossier, isLoading: isDossierLoading } = useQuery({
    queryKey: ['dataGovDossier', selectedAssetId],
    queryFn: () => dataGovernanceService.getAssetDossier(selectedAssetId!),
    enabled: selectedAssetId !== null,
  });

  const { data: schemes = [] } = useQuery({
    queryKey: ['dataGovSchemes'],
    queryFn: () => dataGovernanceService.listSchemes(),
  });

  const { data: lineageEdges = [] } = useQuery({
    queryKey: ['dataGovLineage'],
    queryFn: () => dataGovernanceService.listLineageEdges(),
  });

  const invalidateAll = () => {
    setErrorBanner(null);
    queryClient.invalidateQueries({ queryKey: ['dataGovSummary'] });
    queryClient.invalidateQueries({ queryKey: ['dataGovAssets'] });
    queryClient.invalidateQueries({ queryKey: ['dataGovDossier'] });
    queryClient.invalidateQueries({ queryKey: ['dataGovSchemes'] });
    queryClient.invalidateQueries({ queryKey: ['dataGovLineage'] });
  };

  const handleMutationError = (err: unknown) => {
    const anyErr = err as { response?: { data?: { detail?: unknown } }; message?: string };
    const detail = anyErr?.response?.data?.detail;
    if (typeof detail === 'string') {
      setErrorBanner(detail);
    } else if (Array.isArray(detail)) {
      setErrorBanner(detail.map((d) => d.msg || JSON.stringify(d)).join('; '));
    } else {
      setErrorBanner(anyErr?.message || 'Operation failed');
    }
  };

  // Mutations
  const createAssetMutation = useMutation({
    mutationFn: dataGovernanceService.createAsset,
    onSuccess: (created) => {
      invalidateAll();
      setIsCreateAssetOpen(false);
      setSelectedAssetId(created.id);
    },
    onError: handleMutationError,
  });

  const classifyMutation = useMutation({
    mutationFn: ({
      assetId,
      payload,
    }: {
      assetId: number;
      payload: typeof classifyForm;
    }) => dataGovernanceService.requestClassification(assetId, payload),
    onSuccess: () => {
      invalidateAll();
      setIsClassifyOpen(false);
    },
    onError: handleMutationError,
  });

  const approveClassificationMutation = useMutation({
    mutationFn: dataGovernanceService.approveClassification,
    onSuccess: invalidateAll,
    onError: handleMutationError,
  });

  const activateAssetMutation = useMutation({
    mutationFn: dataGovernanceService.activateAsset,
    onSuccess: invalidateAll,
    onError: handleMutationError,
  });

  const updateOwnershipMutation = useMutation({
    mutationFn: ({
      assetId,
      payload,
    }: {
      assetId: number;
      payload: {
        owner_id?: number;
        steward_id?: number;
        justification: string;
        require_approval: boolean;
      };
    }) => dataGovernanceService.updateOwnership(assetId, payload),
    onSuccess: () => {
      invalidateAll();
      setIsOwnershipOpen(false);
    },
    onError: handleMutationError,
  });

  const approveOwnershipMutation = useMutation({
    mutationFn: dataGovernanceService.approveOwnershipTransfer,
    onSuccess: invalidateAll,
    onError: handleMutationError,
  });

  const retireAssetMutation = useMutation({
    mutationFn: async ({
      assetId,
      form,
    }: {
      assetId: number;
      form: typeof retireForm;
    }) => {
      const payload = {
        disposal_method: form.disposal_method,
        retirement_notes: form.retirement_notes,
        retirement_evidence_id: form.retirement_evidence_id
          ? Number(form.retirement_evidence_id)
          : null,
      };
      if (form.mode === 'finalize') {
        return dataGovernanceService.finalizeRetirement(assetId, payload);
      }
      return dataGovernanceService.requestRetirement(assetId, payload);
    },
    onSuccess: () => {
      invalidateAll();
      setIsRetireOpen(false);
    },
    onError: handleMutationError,
  });

  const createSchemeMutation = useMutation({
    mutationFn: dataGovernanceService.createScheme,
    onSuccess: () => {
      invalidateAll();
      setIsCreateSchemeOpen(false);
    },
    onError: handleMutationError,
  });

  const addLevelMutation = useMutation({
    mutationFn: ({
      schemeId,
      payload,
    }: {
      schemeId: number;
      payload: DataClassificationLevelCreate;
    }) => dataGovernanceService.addLevelToScheme(schemeId, payload),
    onSuccess: () => {
      invalidateAll();
      setIsAddLevelOpen(false);
    },
    onError: handleMutationError,
  });

  const submitSchemeMutation = useMutation({
    mutationFn: dataGovernanceService.submitScheme,
    onSuccess: invalidateAll,
    onError: handleMutationError,
  });

  const approveSchemeMutation = useMutation({
    mutationFn: dataGovernanceService.approveScheme,
    onSuccess: invalidateAll,
    onError: handleMutationError,
  });

  const createLineageMutation = useMutation({
    mutationFn: dataGovernanceService.createLineageEdge,
    onSuccess: () => {
      invalidateAll();
      setIsCreateLineageOpen(false);
    },
    onError: handleMutationError,
  });

  const approveLineageMutation = useMutation({
    mutationFn: dataGovernanceService.approveLineageEdge,
    onSuccess: invalidateAll,
    onError: handleMutationError,
  });

  const revokeLineageMutation = useMutation({
    mutationFn: ({ edgeId, reason }: { edgeId: number; reason: string }) =>
      dataGovernanceService.revokeLineageEdge(edgeId, {
        revocation_reason: reason,
      }),
    onSuccess: invalidateAll,
    onError: handleMutationError,
  });

  const linkCloudMutation = useMutation({
    mutationFn: ({
      assetId,
      cloud_asset_id,
      hosting_role,
      notes,
    }: {
      assetId: number;
      cloud_asset_id: number;
      hosting_role: 'PRIMARY_STORE' | 'REPLICA_STORE' | 'BACKUP_ARCHIVE' | 'PROCESSING_COMPUTE' | 'INGESTION_GATEWAY';
      notes?: string;
    }) =>
      dataGovernanceService.linkCloudAsset(assetId, {
        cloud_asset_id,
        hosting_role,
        notes,
      }),
    onSuccess: () => {
      invalidateAll();
      setIsLinkCloudOpen(false);
    },
    onError: handleMutationError,
  });

  const linkRopaMutation = useMutation({
    mutationFn: ({
      assetId,
      processing_activity_id,
      usage_role,
      notes,
    }: {
      assetId: number;
      processing_activity_id: number;
      usage_role: 'PRIMARY_SOURCE' | 'DERIVED_OUTPUT' | 'ANALYTICS_INPUT' | 'ARCHIVE_RETENTION' | 'VENDOR_TRANSFER';
      notes?: string;
    }) =>
      dataGovernanceService.linkProcessingActivity(assetId, {
        processing_activity_id,
        usage_role,
        notes,
      }),
    onSuccess: () => {
      invalidateAll();
      setIsLinkRopaOpen(false);
    },
    onError: handleMutationError,
  });

  const linkControlMutation = useMutation({
    mutationFn: ({
      assetId,
      organization_control_id,
      control_objective,
      coverage_notes,
    }: {
      assetId: number;
      organization_control_id: number;
      control_objective:
        | 'ENCRYPTION_AT_REST'
        | 'ENCRYPTION_IN_TRANSIT'
        | 'ACCESS_CONTROL'
        | 'DATA_MASKING_PSEUDONYMIZATION'
        | 'RETENTION_DISPOSAL'
        | 'BACKUP_INTEGRITY'
        | 'DLP_MONITORING';
      coverage_notes?: string;
    }) =>
      dataGovernanceService.linkControl(assetId, {
        organization_control_id,
        control_objective,
        coverage_notes,
      }),
    onSuccess: () => {
      invalidateAll();
      setIsLinkControlOpen(false);
    },
    onError: handleMutationError,
  });

  const filteredAssets = assets.filter((a) => {
    if (!searchTerm) return true;
    const q = searchTerm.toLowerCase();
    return (
      a.asset_code.toLowerCase().includes(q) ||
      a.name.toLowerCase().includes(q) ||
      a.storage_type.toLowerCase().includes(q)
    );
  });

  const activeSchemes = schemes.filter((s) => s.status === 'ACTIVE');

  return (
    <div className="p-6 space-y-6 text-slate-100">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-indigo-500/15 border border-indigo-500/30 text-indigo-400">
              <Database size={20} />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white">
                Data Governance, Classification &amp; Lineage
              </h1>
              <p className="text-xs text-slate-400">
                Batch 3 (DATA-GOVERNANCE-GRC) — Governed Data Asset Catalog,
                Monotonic Classification Schemes, DAG Lineage &amp; Cloud/RoPA
                Traceability
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          {canManage && (
            <button
              onClick={() => setIsCreateAssetOpen(true)}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-md bg-indigo-600 hover:bg-indigo-500 text-xs font-medium text-white transition"
            >
              <Plus size={15} />
              Register Data Asset
            </button>
          )}
          {canManage && (
            <button
              onClick={() => setIsCreateSchemeOpen(true)}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-md bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-medium text-slate-200 transition"
            >
              <Layers size={15} />
              New Classification Scheme
            </button>
          )}
          {canClassifyOrLineage && (
            <button
              onClick={() => setIsCreateLineageOpen(true)}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-md bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-medium text-slate-200 transition"
            >
              <GitBranch size={15} />
              Add Lineage Edge
            </button>
          )}
        </div>
      </div>

      {/* Error Banner */}
      {errorBanner && (
        <div className="flex items-center justify-between px-4 py-3 rounded-lg bg-rose-500/15 border border-rose-500/30 text-rose-200 text-xs">
          <div className="flex items-center gap-2">
            <AlertTriangle size={16} className="text-rose-400 shrink-0" />
            <span>{errorBanner}</span>
          </div>
          <button
            onClick={() => setErrorBanner(null)}
            className="text-rose-300 hover:text-white font-mono text-xs"
          >
            DISMISS
          </button>
        </div>
      )}

      {/* Executive KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Governed Data Assets</span>
            <Database size={15} className="text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {summary?.total_assets ?? 0}
          </div>
          <div className="mt-1 text-[11px] text-slate-400">
            {summary?.active_assets ?? 0} Active ·{' '}
            {summary?.restricted_or_phi_assets_count ?? 0} Restricted/PHI
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Classification Assurance</span>
            <ShieldCheck size={15} className="text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {summary?.classified_assets_count ?? 0}
          </div>
          <div className="mt-1 text-[11px] text-amber-300">
            {summary?.pending_classification_approvals ?? 0} Pending Four-Eyes
            Approval
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Active Lineage DAG Edges</span>
            <GitBranch size={15} className="text-sky-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {summary?.active_lineage_edges_count ?? 0}
          </div>
          <div className="mt-1 text-[11px] text-slate-400">
            {summary?.pending_lineage_approvals_count ?? 0} Pending Flow
            Approvals
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Cloud Posture Drift</span>
            <Cloud size={15} className="text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {summary?.cloud_posture_mismatch_count ?? 0}
          </div>
          <div className="mt-1 text-[11px] text-slate-400">
            {summary?.cloud_linked_assets_count ?? 0} Cloud-Linked Datasets
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Governance Health Score</span>
            <Scale size={15} className="text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400">
            {summary?.governance_health_score?.toFixed(1) ?? '100.0'}%
          </div>
          <div className="mt-1 text-[11px] text-slate-400">
            Steward Coverage: {summary?.steward_coverage_pct?.toFixed(0) ?? 0}%
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800">
        <button
          onClick={() => setActiveTab('catalog')}
          className={`px-4 py-2.5 text-xs font-semibold border-b-2 transition ${
            activeTab === 'catalog'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Governed Data Asset Catalog &amp; Dossier ({assets.length})
        </button>
        <button
          onClick={() => setActiveTab('schemes')}
          className={`px-4 py-2.5 text-xs font-semibold border-b-2 transition ${
            activeTab === 'schemes'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Classification Schemes &amp; Levels ({schemes.length})
        </button>
        <button
          onClick={() => setActiveTab('lineage')}
          className={`px-4 py-2.5 text-xs font-semibold border-b-2 transition ${
            activeTab === 'lineage'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Data Lineage DAG &amp; Provenance Ledger ({lineageEdges.length})
        </button>
      </div>

      {/* TAB 1: GOVERNED DATA ASSET CATALOG & DOSSIER */}
      {activeTab === 'catalog' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Asset List Column */}
          <div className="lg:col-span-6 space-y-4">
            <div className="flex flex-wrap items-center gap-2 bg-slate-900/70 p-3 rounded-lg border border-slate-800">
              <div className="relative flex-1 min-w-[180px]">
                <Search
                  size={14}
                  className="absolute left-3 top-2.5 text-slate-500"
                />
                <input
                  type="text"
                  placeholder="Search code, name, storage..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 rounded bg-slate-950 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>
              <select
                value={lifecycleFilter}
                onChange={(e) => setLifecycleFilter(e.target.value)}
                className="px-2.5 py-1.5 rounded bg-slate-950 border border-slate-800 text-xs text-slate-300"
              >
                <option value="">All Lifecycles</option>
                <option value="DISCOVERED">DISCOVERED</option>
                <option value="REGISTERED">REGISTERED</option>
                <option value="CLASSIFIED">CLASSIFIED</option>
                <option value="ACTIVE">ACTIVE</option>
                <option value="DEPRECATED">DEPRECATED</option>
                <option value="RETIRED">RETIRED</option>
              </select>
              <select
                value={sensitivityFilter}
                onChange={(e) => setSensitivityFilter(e.target.value)}
                className="px-2.5 py-1.5 rounded bg-slate-950 border border-slate-800 text-xs text-slate-300"
              >
                <option value="">All Sensitivities</option>
                <option value="PUBLIC">PUBLIC</option>
                <option value="INTERNAL">INTERNAL</option>
                <option value="CONFIDENTIAL">CONFIDENTIAL</option>
                <option value="RESTRICTED_PII">RESTRICTED_PII</option>
                <option value="SPECIAL_CATEGORY_SENSITIVE_PHI">
                  SPECIAL_CATEGORY_PHI
                </option>
              </select>
            </div>

            <div className="bg-slate-900/90 border border-slate-800 rounded-xl overflow-hidden">
              {isAssetsLoading ? (
                <div className="p-8 text-center text-xs text-slate-400">
                  Loading governed data assets...
                </div>
              ) : filteredAssets.length === 0 ? (
                <div className="p-8 text-center text-xs text-slate-500">
                  No governed data assets match the current filter.
                </div>
              ) : (
                <div className="divide-y divide-slate-800/80">
                  {filteredAssets.map((asset) => {
                    const isSelected = selectedAssetId === asset.id;
                    return (
                      <div
                        key={asset.id}
                        onClick={() => setSelectedAssetId(asset.id)}
                        className={`p-4 cursor-pointer transition hover:bg-slate-800/50 ${
                          isSelected
                            ? 'bg-indigo-950/30 border-l-2 border-l-indigo-500'
                            : ''
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-xs font-bold text-indigo-400">
                              {asset.asset_code}
                            </span>
                            <span
                              className={`text-[10px] px-2 py-0.5 rounded border font-mono ${
                                LIFECYCLE_BADGE[asset.lifecycle_state] ||
                                'bg-slate-800 text-slate-300'
                              }`}
                            >
                              {asset.lifecycle_state}
                            </span>
                          </div>
                          <span
                            className={`text-[10px] px-2 py-0.5 rounded border font-mono ${
                              SENSITIVITY_BADGE[asset.data_sensitivity_level]
                            }`}
                          >
                            {asset.data_sensitivity_level}
                          </span>
                        </div>
                        <div className="mt-1.5 text-sm font-semibold text-slate-100">
                          {asset.name}
                        </div>
                        <div className="mt-1 flex flex-wrap items-center gap-3 text-[11px] text-slate-400">
                          <span>Type: {asset.asset_type}</span>
                          <span>Storage: {asset.storage_type}</span>
                          <span>Region: {asset.hosting_jurisdiction}</span>
                          <span>
                            Class Status:{' '}
                            <strong className="text-slate-200">
                              {asset.classification_status}
                            </strong>
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Asset Governance Dossier Panel */}
          <div className="lg:col-span-6">
            {!selectedAssetId ? (
              <div className="h-full min-h-[360px] flex flex-col items-center justify-center p-8 rounded-xl bg-slate-900/50 border border-slate-800/80 text-center">
                <Database size={32} className="text-slate-600 mb-3" />
                <p className="text-sm font-medium text-slate-300">
                  Select a Governed Data Asset
                </p>
                <p className="text-xs text-slate-500 mt-1 max-w-md">
                  Inspect classification history, Four-Eyes approvals, upstream
                  &amp; downstream lineage, Cloud posture alignment, Privacy
                  RoPA links, and derived regulatory obligations.
                </p>
              </div>
            ) : isDossierLoading || !dossier ? (
              <div className="p-8 rounded-xl bg-slate-900/90 border border-slate-800 text-xs text-slate-400">
                Loading asset governance dossier...
              </div>
            ) : (
              <div className="space-y-4 bg-slate-900/90 border border-slate-800 rounded-xl p-5">
                <div className="flex items-start justify-between gap-3 border-b border-slate-800 pb-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-indigo-400">
                        {dossier.asset.asset_code}
                      </span>
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded border font-mono ${
                          LIFECYCLE_BADGE[dossier.asset.lifecycle_state]
                        }`}
                      >
                        {dossier.asset.lifecycle_state}
                      </span>
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded border font-mono ${
                          SENSITIVITY_BADGE[
                            dossier.asset.data_sensitivity_level
                          ]
                        }`}
                      >
                        {dossier.asset.data_sensitivity_level}
                      </span>
                    </div>
                    <h2 className="text-base font-bold text-white mt-1">
                      {dossier.asset.name}
                    </h2>
                    {dossier.asset.description && (
                      <p className="text-xs text-slate-400 mt-0.5">
                        {dossier.asset.description}
                      </p>
                    )}
                  </div>

                  {/* Lifecycle & Governance Actions */}
                  {dossier.asset.lifecycle_state !== 'RETIRED' && (
                    <div className="flex flex-wrap items-center gap-1.5">
                      {canClassifyOrLineage && (
                        <button
                          onClick={() => {
                            const defaultScheme = activeSchemes[0];
                            setClassifyForm({
                              scheme_id: defaultScheme?.id || 0,
                              level_id: defaultScheme?.levels?.[0]?.id || 0,
                              justification: '',
                              require_approval: false,
                            });
                            setIsClassifyOpen(true);
                          }}
                          className="px-2.5 py-1 rounded bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/40 text-indigo-300 text-[11px] font-medium"
                        >
                          Classify
                        </button>
                      )}
                      {canManage &&
                        dossier.asset.lifecycle_state === 'CLASSIFIED' && (
                          <button
                            onClick={() =>
                              activateAssetMutation.mutate(dossier.asset.id)
                            }
                            className="px-2.5 py-1 rounded bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/40 text-emerald-300 text-[11px] font-medium"
                          >
                            Activate
                          </button>
                        )}
                      {canManage && (
                        <button
                          onClick={() => setIsOwnershipOpen(true)}
                          className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-[11px]"
                        >
                          Ownership
                        </button>
                      )}
                      {canManage && (
                        <button
                          onClick={() => {
                            setRetireForm({
                              disposal_method: 'CRYPTOGRAPHIC_ERASURE',
                              retirement_notes: '',
                              retirement_evidence_id: '',
                              mode: canApprove ? 'finalize' : 'request',
                            });
                            setIsRetireOpen(true);
                          }}
                          className="px-2.5 py-1 rounded bg-rose-600/20 hover:bg-rose-600/30 border border-rose-500/40 text-rose-300 text-[11px]"
                        >
                          Retire
                        </button>
                      )}
                    </div>
                  )}
                </div>

                {/* Ownership & Pending Transfer Banner */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs bg-slate-950/70 p-3 rounded-lg border border-slate-800/80">
                  <div>
                    <span className="text-slate-500 block text-[10px]">
                      Owner ID
                    </span>
                    <span className="font-mono text-slate-200">
                      #{dossier.asset.owner_id}{' '}
                      {dossier.owner_active ? '(Active)' : '(Inactive!)'}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px]">
                      Steward ID
                    </span>
                    <span className="font-mono text-slate-200">
                      {dossier.asset.steward_id
                        ? `#${dossier.asset.steward_id}`
                        : 'Unassigned'}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px]">
                      Encryption
                    </span>
                    <span className="text-slate-200">
                      Rest: {dossier.asset.is_encrypted_at_rest ? 'Yes' : 'No'}{' '}
                      · Transit:{' '}
                      {dossier.asset.is_encrypted_in_transit ? 'Yes' : 'No'}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px]">
                      Retention
                    </span>
                    <span className="text-slate-200">
                      {dossier.asset.retention_period_months ?? 'N/A'} months
                    </span>
                  </div>
                </div>

                {dossier.asset.owner_transfer_status === 'PENDING_TRANSFER' && (
                  <div className="flex items-center justify-between p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-xs">
                    <div>
                      <span className="font-semibold text-amber-300">
                        Pending Ownership Transfer to User #
                        {dossier.asset.pending_owner_id}
                      </span>
                      <p className="text-[11px] text-slate-300 mt-0.5">
                        Justification:{' '}
                        {dossier.asset.owner_transfer_justification}
                      </p>
                    </div>
                    {canApprove && (
                      <button
                        onClick={() =>
                          approveOwnershipMutation.mutate(dossier.asset.id)
                        }
                        className="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] font-medium"
                      >
                        Four-Eyes Approve Transfer
                      </button>
                    )}
                  </div>
                )}

                {/* Cloud Posture Alignment Indicator */}
                <div
                  className={`p-3 rounded-lg border text-xs ${
                    dossier.cloud_alignment.cloud_posture_aligned
                      ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-200'
                      : 'bg-amber-500/10 border-amber-500/30 text-amber-200'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 font-semibold">
                      <Cloud size={15} />
                      <span>
                        Cloud Security Posture Alignment:{' '}
                        {dossier.cloud_alignment.cloud_posture_aligned
                          ? 'ALIGNED'
                          : 'DRIFT / MISMATCH DETECTED'}
                      </span>
                    </div>
                    {canManage && dossier.asset.lifecycle_state !== 'RETIRED' && (
                      <button
                        onClick={() => setIsLinkCloudOpen(true)}
                        className="text-[11px] underline hover:text-white"
                      >
                        + Link Cloud Asset
                      </button>
                    )}
                  </div>
                  {dossier.cloud_alignment.mismatch_flags.length > 0 && (
                    <div className="mt-1.5 flex flex-wrap gap-1.5">
                      {dossier.cloud_alignment.mismatch_flags.map((flag) => (
                        <span
                          key={flag}
                          className="px-2 py-0.5 rounded bg-rose-500/20 border border-rose-500/40 text-rose-300 font-mono text-[10px]"
                        >
                          {flag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Append-Only Classification History */}
                <div className="space-y-2">
                  <div className="text-xs font-semibold text-slate-300 flex items-center justify-between">
                    <span>
                      Immutable Classification History (
                      {dossier.classification_history.length})
                    </span>
                  </div>
                  {dossier.classification_history.length === 0 ? (
                    <p className="text-xs text-slate-500">
                      No governed classification records submitted yet.
                    </p>
                  ) : (
                    <div className="space-y-2 max-h-44 overflow-y-auto">
                      {dossier.classification_history.map((rec) => (
                        <div
                          key={rec.id}
                          className="p-2.5 rounded bg-slate-950 border border-slate-800 text-xs flex items-center justify-between gap-2"
                        >
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-mono font-bold text-indigo-400">
                                v{rec.version}
                              </span>
                              <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                                {rec.change_type}
                              </span>
                              <span
                                className={`font-mono text-[10px] px-1.5 py-0.5 rounded border ${
                                  SENSITIVITY_BADGE[rec.new_sensitivity_level]
                                }`}
                              >
                                {rec.new_sensitivity_level}
                              </span>
                              <span className="font-mono text-[10px] text-slate-400">
                                [{rec.status}]
                              </span>
                            </div>
                            <p className="text-[11px] text-slate-400 mt-1">
                              {rec.justification}
                            </p>
                          </div>
                          {rec.status === 'PENDING_APPROVAL' && canApprove && (
                            <button
                              onClick={() =>
                                approveClassificationMutation.mutate(rec.id)
                              }
                              className="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] font-medium shrink-0"
                            >
                              Approve (4-Eyes)
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Cross-Domain Bridges & Derived Regulatory Obligations */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-slate-800">
                  <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                    <div className="flex items-center justify-between text-xs font-semibold text-slate-300 mb-1.5">
                      <span>
                        Privacy RoPA Links ({dossier.processing_links.length})
                      </span>
                      {canManage &&
                        dossier.asset.lifecycle_state !== 'RETIRED' && (
                          <button
                            onClick={() => setIsLinkRopaOpen(true)}
                            className="text-[11px] text-indigo-400 hover:underline"
                          >
                            + Link RoPA
                          </button>
                        )}
                    </div>
                    {dossier.processing_links.length === 0 ? (
                      <p className="text-[11px] text-slate-500">
                        No linked ProcessingActivities.
                      </p>
                    ) : (
                      <ul className="space-y-1 text-[11px] text-slate-300">
                        {dossier.processing_links.map((pl) => (
                          <li key={pl.id} className="font-mono">
                            RoPA #{pl.processing_activity_id} ({pl.usage_role})
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>

                  <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                    <div className="flex items-center justify-between text-xs font-semibold text-slate-300 mb-1.5">
                      <span>
                        Control &amp; Regulatory Links (
                        {dossier.control_links.length})
                      </span>
                      {canManage &&
                        dossier.asset.lifecycle_state !== 'RETIRED' && (
                          <button
                            onClick={() => setIsLinkControlOpen(true)}
                            className="text-[11px] text-indigo-400 hover:underline"
                          >
                            + Link Control
                          </button>
                        )}
                    </div>
                    {dossier.regulatory_obligations.length > 0 ? (
                      <ul className="space-y-1 text-[11px] text-emerald-300">
                        {dossier.regulatory_obligations.map((ob) => (
                          <li key={ob.obligation_id}>
                            <strong>{ob.obligation_code}</strong>: {ob.title}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-[11px] text-slate-500">
                        {dossier.control_links.length} Controls linked · 0
                        Derived Regulatory Obligations
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: CLASSIFICATION SCHEMES & MONOTONIC LEVELS */}
      {activeTab === 'schemes' && (
        <div className="space-y-4">
          {schemes.length === 0 ? (
            <div className="p-8 rounded-xl bg-slate-900/90 border border-slate-800 text-center text-xs text-slate-400">
              No Data Classification Schemes created yet.
            </div>
          ) : (
            schemes.map((scheme) => (
              <div
                key={scheme.id}
                className="p-5 rounded-xl bg-slate-900/90 border border-slate-800 space-y-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-indigo-400">
                        {scheme.scheme_code} (v{scheme.version})
                      </span>
                      <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-200 font-mono text-[10px]">
                        {scheme.status}
                      </span>
                      {scheme.is_default && (
                        <span className="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-mono text-[10px]">
                          DEFAULT
                        </span>
                      )}
                    </div>
                    <h3 className="text-sm font-bold text-white mt-1">
                      {scheme.name}
                    </h3>
                  </div>

                  <div className="flex items-center gap-2">
                    {canManage && scheme.status === 'DRAFT' && (
                      <>
                        <button
                          onClick={() => {
                            setSelectedSchemeId(scheme.id);
                            setNewLevel({
                              level_code: `L${scheme.levels.length + 1}`,
                              name: '',
                              ordinal_rank: scheme.levels.length + 1,
                              mapped_sensitivity_level: 'INTERNAL',
                              requires_encryption_at_rest: true,
                              requires_encryption_in_transit: true,
                              requires_four_eyes_approval: false,
                              default_retention_months: 24,
                            });
                            setIsAddLevelOpen(true);
                          }}
                          className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 border border-slate-700"
                        >
                          + Add Level
                        </button>
                        <button
                          onClick={() => submitSchemeMutation.mutate(scheme.id)}
                          className="px-3 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 text-xs text-white font-medium"
                        >
                          Submit for Approval
                        </button>
                      </>
                    )}
                    {canApprove && scheme.status === 'PENDING_APPROVAL' && (
                      <button
                        onClick={() => approveSchemeMutation.mutate(scheme.id)}
                        className="px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-xs text-white font-medium"
                      >
                        Four-Eyes Approve Scheme
                      </button>
                    )}
                  </div>
                </div>

                {/* Levels Table */}
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-400">
                        <th className="py-2 pr-3">Rank</th>
                        <th className="py-2 pr-3">Level Code</th>
                        <th className="py-2 pr-3">Name</th>
                        <th className="py-2 pr-3">Mapped Sensitivity</th>
                        <th className="py-2 pr-3">Enc Rest</th>
                        <th className="py-2 pr-3">Four-Eyes</th>
                        <th className="py-2">Retention</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {scheme.levels.map((lvl) => (
                        <tr key={lvl.id}>
                          <td className="py-2 pr-3 font-mono font-bold text-indigo-400">
                            #{lvl.ordinal_rank}
                          </td>
                          <td className="py-2 pr-3 font-mono">
                            {lvl.level_code}
                          </td>
                          <td className="py-2 pr-3 font-medium text-white">
                            {lvl.name}
                          </td>
                          <td className="py-2 pr-3">
                            <span
                              className={`text-[10px] px-2 py-0.5 rounded border font-mono ${
                                SENSITIVITY_BADGE[lvl.mapped_sensitivity_level]
                              }`}
                            >
                              {lvl.mapped_sensitivity_level}
                            </span>
                          </td>
                          <td className="py-2 pr-3">
                            {lvl.requires_encryption_at_rest ? 'Yes' : 'No'}
                          </td>
                          <td className="py-2 pr-3">
                            {lvl.requires_four_eyes_approval
                              ? 'Required'
                              : 'Standard'}
                          </td>
                          <td className="py-2">
                            {lvl.default_retention_months ?? '-'} mo
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* TAB 3: DATA LINEAGE DAG & PROVENANCE LEDGER */}
      {activeTab === 'lineage' && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl overflow-hidden">
          {lineageEdges.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-400">
              No Data Lineage Edges recorded yet.
            </div>
          ) : (
            <div className="divide-y divide-slate-800">
              {lineageEdges.map((edge) => (
                <div
                  key={edge.id}
                  className="p-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3"
                >
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs font-bold text-indigo-400">
                        {edge.edge_code} (v{edge.version})
                      </span>
                      <span className="font-mono text-xs text-white flex items-center gap-1.5">
                        Asset #{edge.source_data_asset_id}
                        <ArrowRight size={13} className="text-indigo-400" />
                        Asset #{edge.target_data_asset_id}
                      </span>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                        {edge.relationship_type}
                      </span>
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded font-mono ${
                          edge.status === 'ACTIVE'
                            ? 'bg-emerald-500/15 text-emerald-300'
                            : edge.status === 'PENDING_APPROVAL'
                            ? 'bg-amber-500/15 text-amber-300'
                            : 'bg-rose-500/15 text-rose-300'
                        }`}
                      >
                        {edge.status}
                      </span>
                    </div>
                    {edge.transformation_summary && (
                      <p className="text-xs text-slate-300">
                        {edge.transformation_summary}
                      </p>
                    )}
                    <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-400 font-mono">
                      <span className="flex items-center gap-1">
                        <Hash size={12} />
                        SHA-256: {edge.provenance_hash.slice(0, 20)}...
                      </span>
                      <span>
                        Masked/Anonymized:{' '}
                        {edge.is_masked_or_anonymized ? 'YES' : 'NO'}
                      </span>
                      <span>
                        Transit Encrypted:{' '}
                        {edge.is_encrypted_in_transit ? 'YES' : 'NO'}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {edge.status === 'PENDING_APPROVAL' && canApprove && (
                      <button
                        onClick={() => approveLineageMutation.mutate(edge.id)}
                        className="px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium"
                      >
                        Four-Eyes Approve Flow
                      </button>
                    )}
                    {edge.status === 'ACTIVE' && canClassifyOrLineage && (
                      <button
                        onClick={() =>
                          revokeLineageMutation.mutate({
                            edgeId: edge.id,
                            reason:
                              'Lineage flow decommissioned by governance review',
                          })
                        }
                        className="px-3 py-1.5 rounded bg-rose-600/20 hover:bg-rose-600/30 border border-rose-500/40 text-rose-300 text-xs"
                      >
                        Revoke
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* MODAL: CREATE GOVERNED DATA ASSET */}
      {isCreateAssetOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-lg rounded-xl bg-slate-900 border border-slate-800 p-6 space-y-4">
            <h3 className="text-base font-bold text-white">
              Register Governed Data Asset
            </h3>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <label className="block text-slate-400 mb-1">Asset Code</label>
                <input
                  type="text"
                  value={newAsset.asset_code}
                  onChange={(e) =>
                    setNewAsset({ ...newAsset, asset_code: e.target.value })
                  }
                  placeholder="DA-CUST-PII-01"
                  className="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800 text-white"
                />
              </div>
              <div>
                <label className="block text-slate-400 mb-1">Asset Type</label>
                <select
                  value={newAsset.asset_type}
                  onChange={(e) =>
                    setNewAsset({
                      ...newAsset,
                      asset_type: e.target.value as DataAssetType,
                    })
                  }
                  className="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800 text-white"
                >
                  <option value="DATABASE_TABLE">DATABASE_TABLE</option>
                  <option value="DATA_LAKE_BUCKET">DATA_LAKE_BUCKET</option>
                  <option value="MESSAGE_STREAM">MESSAGE_STREAM</option>
                  <option value="SAAS_DATASET">SAAS_DATASET</option>
                  <option value="AI_TRAINING_CORPUS">AI_TRAINING_CORPUS</option>
                  <option value="BACKUP_ARCHIVE">BACKUP_ARCHIVE</option>
                </select>
              </div>
              <div className="col-span-2">
                <label className="block text-slate-400 mb-1">Name</label>
                <input
                  type="text"
                  value={newAsset.name}
                  onChange={(e) =>
                    setNewAsset({ ...newAsset, name: e.target.value })
                  }
                  placeholder="Customer Master Identity Table"
                  className="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800 text-white"
                />
              </div>
              <div>
                <label className="block text-slate-400 mb-1">
                  Initial Sensitivity
                </label>
                <select
                  value={newAsset.data_sensitivity_level}
                  onChange={(e) =>
                    setNewAsset({
                      ...newAsset,
                      data_sensitivity_level: e.target
                        .value as DataSensitivityLevel,
                    })
                  }
                  className="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800 text-white"
                >
                  <option value="PUBLIC">PUBLIC</option>
                  <option value="INTERNAL">INTERNAL</option>
                  <option value="CONFIDENTIAL">CONFIDENTIAL</option>
                  <option value="RESTRICTED_PII">RESTRICTED_PII</option>
                  <option value="SPECIAL_CATEGORY_SENSITIVE_PHI">
                    SPECIAL_CATEGORY_SENSITIVE_PHI
                  </option>
                </select>
              </div>
              <div>
                <label className="block text-slate-400 mb-1">
                  Initial Lifecycle
                </label>
                <select
                  value={newAsset.initial_lifecycle_state}
                  onChange={(e) =>
                    setNewAsset({
                      ...newAsset,
                      initial_lifecycle_state: e.target.value as
                        | 'DISCOVERED'
                        | 'REGISTERED',
                    })
                  }
                  className="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800 text-white"
                >
                  <option value="REGISTERED">REGISTERED</option>
                  <option value="DISCOVERED">DISCOVERED</option>
                </select>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-3">
              <button
                onClick={() => setIsCreateAssetOpen(false)}
                className="px-3 py-1.5 rounded bg-slate-800 text-xs text-slate-300"
              >
                Cancel
              </button>
              <button
                onClick={() => createAssetMutation.mutate(newAsset)}
                className="px-4 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 text-xs font-medium text-white"
              >
                Register Asset
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: SUBMIT CLASSIFICATION */}
      {isClassifyOpen && selectedAssetId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-md rounded-xl bg-slate-900 border border-slate-800 p-6 space-y-4 text-xs">
            <h3 className="text-base font-bold text-white">
              Submit Governed Classification
            </h3>
            <div>
              <label className="block text-slate-400 mb-1">
                Active Classification Scheme
              </label>
              <select
                value={classifyForm.scheme_id}
                onChange={(e) => {
                  const sid = Number(e.target.value);
                  const sch = activeSchemes.find((s) => s.id === sid);
                  setClassifyForm({
                    ...classifyForm,
                    scheme_id: sid,
                    level_id: sch?.levels?.[0]?.id || 0,
                  });
                }}
                className="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800 text-white"
              >
                <option value={0}>Select Active Scheme...</option>
                {activeSchemes.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.scheme_code} — {s.name} (v{s.version})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-slate-400 mb-1">
                Target Classification Level
              </label>
              <select
                value={classifyForm.level_id}
                onChange={(e) =>
                  setClassifyForm({
                    ...classifyForm,
                    level_id: Number(e.target.value),
                  })
                }
                className="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800 text-white"
              >
                {(
                  activeSchemes.find((s) => s.id === classifyForm.scheme_id)
                    ?.levels || []
                ).map((lvl) => (
                  <option key={lvl.id} value={lvl.id}>
                    #{lvl.ordinal_rank} {lvl.level_code} —{' '}
                    {lvl.mapped_sensitivity_level}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-slate-400 mb-1">
                Governance Justification
              </label>
              <textarea
                rows={3}
                value={classifyForm.justification}
                onChange={(e) =>
                  setClassifyForm({
                    ...classifyForm,
                    justification: e.target.value,
                  })
                }
                placeholder="Document data elements and regulatory classification rationale..."
                className="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800 text-white"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setIsClassifyOpen(false)}
                className="px-3 py-1.5 rounded bg-slate-800 text-slate-300"
              >
                Cancel
              </button>
              <button
                onClick={() =>
                  classifyMutation.mutate({
                    assetId: selectedAssetId,
                    payload: classifyForm,
                  })
                }
                className="px-4 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 text-white font-medium"
              >
                Submit Classification
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: OWNERSHIP & STEWARDSHIP */}
      {isOwnershipOpen && selectedAssetId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-md rounded-xl bg-slate-900 border border-slate-800 p-6 space-y-4 text-xs">
            <h3 className="text-base font-bold text-white">
              Update Data Owner / Steward
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-slate-400 mb-1">
                  New Owner User ID
                </label>
                <input
                  type="number"
                  value={ownershipForm.owner_id}
                  onChange={(e) =>
                    setOwnershipForm({
                      ...ownershipForm,
                      owner_id: e.target.value,
                    })
                  }
                  className="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800 text-white"
                />
              </div>
              <div>
                <label className="block text-slate-400 mb-1">
                  New Steward User ID
                </label>
                <input
                  type="number"
                  value={ownershipForm.steward_id}
                  onChange={(e) =>
                    setOwnershipForm({
                      ...ownershipForm,
                      steward_id: e.target.value,
                    })
                  }
                  className="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800 text-white"
                />
              </div>
            </div>
            <div>
              <label className="block text-slate-400 mb-1">Justification</label>
              <textarea
                rows={2}
                value={ownershipForm.justification}
                onChange={(e) =>
                  setOwnershipForm({
                    ...ownershipForm,
                    justification: e.target.value,
                  })
                }
                className="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800 text-white"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setIsOwnershipOpen(false)}
                className="px-3 py-1.5 rounded bg-slate-800 text-slate-300"
              >
                Cancel
              </button>
              <button
                onClick={() =>
                  updateOwnershipMutation.mutate({
                    assetId: selectedAssetId,
                    payload: {
                      owner_id: ownershipForm.owner_id
                        ? Number(ownershipForm.owner_id)
                        : undefined,
                      steward_id: ownershipForm.steward_id
                        ? Number(ownershipForm.steward_id)
                        : undefined,
                      justification: ownershipForm.justification,
                      require_approval: ownershipForm.require_approval,
                    },
                  })
                }
                className="px-4 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 text-white font-medium"
              >
                Submit Ownership Update
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: RETIRE DATA ASSET */}
      {isRetireOpen && selectedAssetId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-md rounded-xl bg-slate-900 border border-slate-800 p-6 space-y-4 text-xs">
            <h3 className="text-base font-bold text-white">
              Governed Data Asset Disposal &amp; Retirement
            </h3>
            <div>
              <label className="block text-slate-400 mb-1">
                Disposal Method
              </label>
              <select
                value={retireForm.disposal_method}
                onChange={(e) =>
                  setRetireForm({
                    ...retireForm,
                    disposal_method: e.target.value as DataDisposalMethod,
                  })
                }
                className="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800 text-white"
              >
                <option value="CRYPTOGRAPHIC_ERASURE">
                  CRYPTOGRAPHIC_ERASURE
                </option>
                <option value="SECURE_OVERWRITE">SECURE_OVERWRITE</option>
                <option value="PHYSICAL_DESTRUCTION">
                  PHYSICAL_DESTRUCTION
                </option>
                <option value="ANONYMIZATION_RETENTION">
                  ANONYMIZATION_RETENTION
                </option>
                <option value="ARCHIVAL_COLD_STORAGE">
                  ARCHIVAL_COLD_STORAGE
                </option>
              </select>
            </div>
            <div>
              <label className="block text-slate-400 mb-1">
                Disposal Certificate Evidence Item ID (Required for
                CONFIDENTIAL+)
              </label>
              <input
                type="number"
                value={retireForm.retirement_evidence_id}
                onChange={(e) =>
                  setRetireForm({
                    ...retireForm,
                    retirement_evidence_id: e.target.value,
                  })
                }
                placeholder="Accepted EvidenceItem ID"
                className="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800 text-white"
              />
            </div>
            <div>
              <label className="block text-slate-400 mb-1">
                Retirement &amp; Sanitization Notes
              </label>
              <textarea
                rows={3}
                value={retireForm.retirement_notes}
                onChange={(e) =>
                  setRetireForm({
                    ...retireForm,
                    retirement_notes: e.target.value,
                  })
                }
                className="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800 text-white"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setIsRetireOpen(false)}
                className="px-3 py-1.5 rounded bg-slate-800 text-slate-300"
              >
                Cancel
              </button>
              <button
                onClick={() =>
                  retireAssetMutation.mutate({
                    assetId: selectedAssetId,
                    form: { ...retireForm, mode: 'request' },
                  })
                }
                className="px-3 py-1.5 rounded bg-amber-600 hover:bg-amber-500 text-white font-medium"
              >
                Request Retirement
              </button>
              {canApprove && (
                <button
                  onClick={() =>
                    retireAssetMutation.mutate({
                      assetId: selectedAssetId,
                      form: { ...retireForm, mode: 'finalize' },
                    })
                  }
                  className="px-3 py-1.5 rounded bg-rose-600 hover:bg-rose-500 text-white font-medium"
                >
                  Finalize Retirement (4-Eyes)
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* MODAL: CREATE CLASSIFICATION SCHEME */}
      {isCreateSchemeOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-md rounded-xl bg-slate-900 border border-slate-800 p-6 space-y-4 text-xs">
            <h3 className="text-base font-bold text-white">
              Create Data Classification Scheme
            </h3>
            <div>
              <label className="block text-slate-400 mb-1">Scheme Code</label>
              <input
                type="text"
                value={newScheme.scheme_code}
                onChange={(e) =>
                  setNewScheme({ ...newScheme, scheme_code: e.target.value })
                }
                placeholder="CS-GLOBAL-2026"
                className="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800 text-white"
              />
            </div>
            <div>
              <label className="block text-slate-400 mb-1">Name</label>
              <input
                type="text"
                value={newScheme.name}
                onChange={(e) =>
                  setNewScheme({ ...newScheme, name: e.target.value })
                }
                placeholder="Enterprise Data Classification Standard"
                className="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800 text-white"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setIsCreateSchemeOpen(false)}
                className="px-3 py-1.5 rounded bg-slate-800 text-slate-300"
              >
                Cancel
              </button>
              <button
                onClick={() => createSchemeMutation.mutate(newScheme)}
                className="px-4 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 text-white font-medium"
              >
                Create Scheme
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: ADD LEVEL TO SCHEME */}
      {isAddLevelOpen && selectedSchemeId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-md rounded-xl bg-slate-900 border border-slate-800 p-6 space-y-4 text-xs">
            <h3 className="text-base font-bold text-white">
              Add Monotonic Classification Level
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-slate-400 mb-1">Level Code</label>
                <input
                  type="text"
                  value={newLevel.level_code}
                  onChange={(e) =>
                    setNewLevel({ ...newLevel, level_code: e.target.value })
                  }
                  className="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800 text-white"
                />
              </div>
              <div>
                <label className="block text-slate-400 mb-1">
                  Ordinal Rank (1-10)
                </label>
                <input
                  type="number"
                  value={newLevel.ordinal_rank}
                  onChange={(e) =>
                    setNewLevel({
                      ...newLevel,
                      ordinal_rank: Number(e.target.value),
                    })
                  }
                  className="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800 text-white"
                />
              </div>
              <div className="col-span-2">
                <label className="block text-slate-400 mb-1">Level Name</label>
                <input
                  type="text"
                  value={newLevel.name}
                  onChange={(e) =>
                    setNewLevel({ ...newLevel, name: e.target.value })
                  }
                  className="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800 text-white"
                />
              </div>
              <div className="col-span-2">
                <label className="block text-slate-400 mb-1">
                  Mapped Sensitivity Level
                </label>
                <select
                  value={newLevel.mapped_sensitivity_level}
                  onChange={(e) =>
                    setNewLevel({
                      ...newLevel,
                      mapped_sensitivity_level: e.target
                        .value as DataSensitivityLevel,
                    })
                  }
                  className="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800 text-white"
                >
                  <option value="PUBLIC">PUBLIC</option>
                  <option value="INTERNAL">INTERNAL</option>
                  <option value="CONFIDENTIAL">CONFIDENTIAL</option>
                  <option value="RESTRICTED_PII">RESTRICTED_PII</option>
                  <option value="SPECIAL_CATEGORY_SENSITIVE_PHI">
                    SPECIAL_CATEGORY_SENSITIVE_PHI
                  </option>
                </select>
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setIsAddLevelOpen(false)}
                className="px-3 py-1.5 rounded bg-slate-800 text-slate-300"
              >
                Cancel
              </button>
              <button
                onClick={() =>
                  addLevelMutation.mutate({
                    schemeId: selectedSchemeId,
                    payload: newLevel,
                  })
                }
                className="px-4 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 text-white font-medium"
              >
                Add Level
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: CREATE LINEAGE EDGE */}
      {isCreateLineageOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-md rounded-xl bg-slate-900 border border-slate-800 p-6 space-y-4 text-xs">
            <h3 className="text-base font-bold text-white">
              Register Directed Data Lineage Edge
            </h3>
            <div>
              <label className="block text-slate-400 mb-1">Edge Code</label>
              <input
                type="text"
                value={newLineage.edge_code}
                onChange={(e) =>
                  setNewLineage({ ...newLineage, edge_code: e.target.value })
                }
                placeholder="LIN-ETL-001"
                className="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800 text-white"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-slate-400 mb-1">
                  Source Asset
                </label>
                <select
                  value={newLineage.source_data_asset_id}
                  onChange={(e) =>
                    setNewLineage({
                      ...newLineage,
                      source_data_asset_id: Number(e.target.value),
                    })
                  }
                  className="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800 text-white"
                >
                  <option value={0}>Select Source...</option>
                  {assets.map((a) => (
                    <option key={a.id} value={a.id}>
                      #{a.id} {a.asset_code} ({a.data_sensitivity_level})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-slate-400 mb-1">
                  Target Asset
                </label>
                <select
                  value={newLineage.target_data_asset_id}
                  onChange={(e) =>
                    setNewLineage({
                      ...newLineage,
                      target_data_asset_id: Number(e.target.value),
                    })
                  }
                  className="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800 text-white"
                >
                  <option value={0}>Select Target...</option>
                  {assets.map((a) => (
                    <option key={a.id} value={a.id}>
                      #{a.id} {a.asset_code} ({a.data_sensitivity_level})
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <label className="block text-slate-400 mb-1">
                Relationship Type
              </label>
              <select
                value={newLineage.relationship_type}
                onChange={(e) =>
                  setNewLineage({
                    ...newLineage,
                    relationship_type: e.target
                      .value as DataLineageRelationshipType,
                  })
                }
                className="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800 text-white"
              >
                <option value="ETL_TRANSFORMATION">ETL_TRANSFORMATION</option>
                <option value="STREAM_REPLICATION">STREAM_REPLICATION</option>
                <option value="API_SYNDICATION">API_SYNDICATION</option>
                <option value="AGGREGATION">AGGREGATION</option>
                <option value="AI_FEATURE_EXTRACTION">
                  AI_FEATURE_EXTRACTION
                </option>
              </select>
            </div>
            <div>
              <label className="block text-slate-400 mb-1">
                Transformation / Sanitization Summary
              </label>
              <textarea
                rows={2}
                value={newLineage.transformation_summary || ''}
                onChange={(e) =>
                  setNewLineage({
                    ...newLineage,
                    transformation_summary: e.target.value,
                  })
                }
                placeholder="Required when flowing into a lower-sensitivity target asset..."
                className="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800 text-white"
              />
            </div>
            <label className="flex items-center gap-2 text-slate-300">
              <input
                type="checkbox"
                checked={Boolean(newLineage.is_masked_or_anonymized)}
                onChange={(e) =>
                  setNewLineage({
                    ...newLineage,
                    is_masked_or_anonymized: e.target.checked,
                  })
                }
              />
              Data is masked, tokenized, or anonymized in transformation
            </label>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setIsCreateLineageOpen(false)}
                className="px-3 py-1.5 rounded bg-slate-800 text-slate-300"
              >
                Cancel
              </button>
              <button
                onClick={() => createLineageMutation.mutate(newLineage)}
                className="px-4 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 text-white font-medium"
              >
                Create Lineage Edge
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: LINK CLOUD ASSET */}
      {isLinkCloudOpen && selectedAssetId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-sm rounded-xl bg-slate-900 border border-slate-800 p-6 space-y-4 text-xs">
            <h3 className="text-base font-bold text-white">
              Link Cloud Security Asset (Phase 18)
            </h3>
            <div>
              <label className="block text-slate-400 mb-1">
                CloudAsset ID
              </label>
              <input
                type="number"
                value={cloudLinkForm.cloud_asset_id}
                onChange={(e) =>
                  setCloudLinkForm({
                    ...cloudLinkForm,
                    cloud_asset_id: e.target.value,
                  })
                }
                className="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800 text-white"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setIsLinkCloudOpen(false)}
                className="px-3 py-1.5 rounded bg-slate-800 text-slate-300"
              >
                Cancel
              </button>
              <button
                onClick={() =>
                  linkCloudMutation.mutate({
                    assetId: selectedAssetId,
                    cloud_asset_id: Number(cloudLinkForm.cloud_asset_id),
                    hosting_role: cloudLinkForm.hosting_role,
                    notes: cloudLinkForm.notes,
                  })
                }
                className="px-4 py-1.5 rounded bg-indigo-600 text-white font-medium"
              >
                Link Cloud Asset
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: LINK ROPA */}
      {isLinkRopaOpen && selectedAssetId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-sm rounded-xl bg-slate-900 border border-slate-800 p-6 space-y-4 text-xs">
            <h3 className="text-base font-bold text-white">
              Link Privacy Processing Activity (Phase 16)
            </h3>
            <div>
              <label className="block text-slate-400 mb-1">
                ProcessingActivity ID
              </label>
              <input
                type="number"
                value={ropaLinkForm.processing_activity_id}
                onChange={(e) =>
                  setRopaLinkForm({
                    ...ropaLinkForm,
                    processing_activity_id: e.target.value,
                  })
                }
                className="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800 text-white"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setIsLinkRopaOpen(false)}
                className="px-3 py-1.5 rounded bg-slate-800 text-slate-300"
              >
                Cancel
              </button>
              <button
                onClick={() =>
                  linkRopaMutation.mutate({
                    assetId: selectedAssetId,
                    processing_activity_id: Number(
                      ropaLinkForm.processing_activity_id
                    ),
                    usage_role: ropaLinkForm.usage_role,
                    notes: ropaLinkForm.notes,
                  })
                }
                className="px-4 py-1.5 rounded bg-indigo-600 text-white font-medium"
              >
                Link RoPA
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: LINK CONTROL */}
      {isLinkControlOpen && selectedAssetId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-sm rounded-xl bg-slate-900 border border-slate-800 p-6 space-y-4 text-xs">
            <h3 className="text-base font-bold text-white">
              Link Organization Control
            </h3>
            <div>
              <label className="block text-slate-400 mb-1">
                OrganizationControl ID
              </label>
              <input
                type="number"
                value={controlLinkForm.organization_control_id}
                onChange={(e) =>
                  setControlLinkForm({
                    ...controlLinkForm,
                    organization_control_id: e.target.value,
                  })
                }
                className="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800 text-white"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setIsLinkControlOpen(false)}
                className="px-3 py-1.5 rounded bg-slate-800 text-slate-300"
              >
                Cancel
              </button>
              <button
                onClick={() =>
                  linkControlMutation.mutate({
                    assetId: selectedAssetId,
                    organization_control_id: Number(
                      controlLinkForm.organization_control_id
                    ),
                    control_objective: controlLinkForm.control_objective,
                    coverage_notes: controlLinkForm.coverage_notes,
                  })
                }
                className="px-4 py-1.5 rounded bg-indigo-600 text-white font-medium"
              >
                Link Control
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
export default DataGovernancePage;
