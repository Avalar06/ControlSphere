import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { supplyChainService } from '../lib/supplyChainService';
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
import { SoftwareProductModal } from '../components/supply_chain/SoftwareProductModal';
import { SBOMUploadModal } from '../components/supply_chain/SBOMUploadModal';
import { SupplyChainExemptionModal } from '../components/supply_chain/SupplyChainExemptionModal';
import { SupplyChainApprovalModal } from '../components/supply_chain/SupplyChainApprovalModal';
import { SupplyChainRiskCard } from '../components/supply_chain/SupplyChainRiskCard';
import type {
  BusinessCriticality,
  ProductLifecycleState,
  SoftwareProduct,
  SupplyChainApprovalStatus,
  SupplyChainExemption,
  SupplyChainRiskBand,
} from '../types';
import {
  Package,
  FileCode,
  Box,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  Plus,
  Search,
  Filter,
  Eye,
  Edit2,
  Trash2,
  Scale,
} from 'lucide-react';

type TabKey = 'products' | 'sboms' | 'components' | 'exemptions' | 'engine';

export const SupplyChainGovernancePage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { hasRole } = useAuth();

  const canManage = hasRole('ADMIN', 'MANAGER', 'GRC_ANALYST');
  const canAssess = hasRole('ADMIN', 'MANAGER', 'GRC_ANALYST', 'SECURITY_ANALYST');
  const canApprove = hasRole('ADMIN', 'MANAGER');

  const [activeTab, setActiveTab] = useState<TabKey>('products');
  const [searchQuery, setSearchQuery] = useState('');

  // Filters
  const [productStateFilter, setProductStateFilter] = useState<ProductLifecycleState | 'ALL'>('ALL');
  const [productTierFilter, setProductTierFilter] = useState<BusinessCriticality | 'ALL'>('ALL');
  const [exemptionStatusFilter, setExemptionStatusFilter] = useState<SupplyChainApprovalStatus | 'ALL'>('ALL');

  // Modals state
  const [isProductModalOpen, setIsProductModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<SoftwareProduct | null>(null);

  const [isSbomModalOpen, setIsSbomModalOpen] = useState(false);
  const [selectedProductIdForSbom, setSelectedProductIdForSbom] = useState<number | null>(null);

  const [isExemptionModalOpen, setIsExemptionModalOpen] = useState(false);
  const [selectedExemptionProduct, setSelectedExemptionProduct] = useState<number | null>(null);

  const [isApprovalModalOpen, setIsApprovalModalOpen] = useState(false);
  const [selectedExemptionForApproval, setSelectedExemptionForApproval] = useState<SupplyChainExemption | null>(null);

  // Queries
  const { data: posture } = useQuery({
    queryKey: ['supply-chain-posture'],
    queryFn: () => supplyChainService.getPostureSummary(),
  });

  const { data: products = [], isLoading: isProductsLoading } = useQuery({
    queryKey: ['supply-chain-products', productStateFilter, productTierFilter],
    queryFn: () =>
      supplyChainService.listProducts({
        lifecycle_state: productStateFilter === 'ALL' ? undefined : productStateFilter,
        criticality_tier: productTierFilter === 'ALL' ? undefined : productTierFilter,
      }),
  });

  const { data: exemptions = [], isLoading: isExemptionsLoading } = useQuery({
    queryKey: ['supply-chain-exemptions', exemptionStatusFilter],
    queryFn: () =>
      supplyChainService.listExemptions({
        approval_status: exemptionStatusFilter === 'ALL' ? undefined : exemptionStatusFilter,
      }),
  });

  const { data: policies = [], isLoading: isPoliciesLoading } = useQuery({
    queryKey: ['supply-chain-policies'],
    queryFn: () => supplyChainService.listPolicies(),
  });

  // Delete Product Mutation
  const deleteMutation = useMutation({
    mutationFn: (id: number) => supplyChainService.deleteProduct(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['supply-chain-products'] });
      queryClient.invalidateQueries({ queryKey: ['supply-chain-posture'] });
    },
    onError: (err: any) => {
      alert(err?.response?.data?.detail || 'Failed to delete product (Active products cannot be deleted).');
    },
  });

  const getRiskBandBadge = (band: SupplyChainRiskBand) => {
    switch (band) {
      case 'CRITICAL':
        return <Badge variant="danger">CRITICAL</Badge>;
      case 'HIGH':
        return <Badge variant="warning">HIGH</Badge>;
      case 'MODERATE':
        return <Badge variant="purple">MODERATE</Badge>;
      case 'LOW':
      default:
        return <Badge variant="success">LOW</Badge>;
    }
  };

  const getLifecycleBadge = (state: ProductLifecycleState) => {
    switch (state) {
      case 'ACTIVE':
        return <Badge variant="success">ACTIVE</Badge>;
      case 'DRAFT':
        return <Badge variant="default">DRAFT</Badge>;
      case 'DEPRECATED':
        return <Badge variant="warning">DEPRECATED</Badge>;
      case 'RETIRED':
        return <Badge variant="danger">RETIRED</Badge>;
      default:
        return <Badge variant="default">{state}</Badge>;
    }
  };

  const getApprovalBadge = (status: SupplyChainApprovalStatus) => {
    switch (status) {
      case 'APPROVED':
        return <Badge variant="success">APPROVED</Badge>;
      case 'PENDING':
        return <Badge variant="warning">PENDING</Badge>;
      case 'REJECTED':
        return <Badge variant="danger">REJECTED</Badge>;
      case 'REVOKED':
        return <Badge variant="default">REVOKED</Badge>;
      default:
        return <Badge variant="default">{status}</Badge>;
    }
  };

  const filteredProducts = products.filter((p) => {
    const q = searchQuery.toLowerCase();
    return (
      p.product_code.toLowerCase().includes(q) ||
      p.name.toLowerCase().includes(q) ||
      p.product_type.toLowerCase().includes(q)
    );
  });

  const filteredExemptions = exemptions.filter((e) => {
    const q = searchQuery.toLowerCase();
    return (
      e.exemption_code.toLowerCase().includes(q) ||
      e.reason.toLowerCase().includes(q) ||
      (e.requested_by?.full_name || '').toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-100 tracking-tight">
              Software Supply Chain &amp; SBOM Governance (SUPPLYCHAIN-GRC)
            </h1>
            <Badge variant="purple">Phase 17</Badge>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Catalog software products, ingest SBOM manifests (CycloneDX/SPDX), quantify component risks (CRI &amp; SCEI), detect prohibited licenses, and enforce Four-Eyes risk exemptions.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {canManage && (
            <Button
              size="sm"
              onClick={() => {
                setEditingProduct(null);
                setIsProductModalOpen(true);
              }}
              className="flex items-center gap-1.5"
            >
              <Plus size={15} />
              <span>Catalog Product</span>
            </Button>
          )}
          {canAssess && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                setSelectedExemptionProduct(null);
                setIsExemptionModalOpen(true);
              }}
              className="flex items-center gap-1.5"
            >
              <ShieldCheck size={15} className="text-indigo-400" />
              <span>Request Exemption</span>
            </Button>
          )}
        </div>
      </div>

      {/* Executive Telemetry Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="p-4 bg-slate-900/70 border border-slate-800 rounded-xl">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5 mb-1">
            <Package size={13} className="text-indigo-400" />
            <span>Products</span>
          </span>
          <div className="text-2xl font-bold text-slate-100 font-mono">
            {posture?.total_products ?? 0}
          </div>
          <span className="text-[10px] text-emerald-400 mt-0.5 block">
            {posture?.active_products_count ?? 0} active in production
          </span>
        </div>

        <div className="p-4 bg-slate-900/70 border border-slate-800 rounded-xl">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5 mb-1">
            <Box size={13} className="text-sky-400" />
            <span>Components</span>
          </span>
          <div className="text-2xl font-bold text-slate-100 font-mono">
            {posture?.total_components_cataloged ?? 0}
          </div>
          <span className="text-[10px] text-slate-400 mt-0.5 block">
            Direct &amp; Transitive dependencies
          </span>
        </div>

        <div className="p-4 bg-slate-900/70 border border-slate-800 rounded-xl">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5 mb-1">
            <AlertTriangle size={13} className="text-amber-400" />
            <span>Vulnerable</span>
          </span>
          <div className="text-2xl font-bold text-amber-400 font-mono">
            {posture?.vulnerable_components_count ?? 0}
          </div>
          <span className="text-[10px] text-slate-400 mt-0.5 block">
            Linked to Phase 14 CVEs
          </span>
        </div>

        <div className="p-4 bg-slate-900/70 border border-slate-800 rounded-xl">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5 mb-1">
            <Scale size={13} className="text-rose-400" />
            <span>Prohibited OSS</span>
          </span>
          <div className="text-2xl font-bold text-rose-400 font-mono">
            {posture?.prohibited_license_violations ?? 0}
          </div>
          <span className="text-[10px] text-rose-400 mt-0.5 block">
            Copyleft / IP Policy triggers
          </span>
        </div>

        <div className="p-4 bg-slate-900/70 border border-slate-800 rounded-xl">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5 mb-1">
            <ShieldCheck size={13} className="text-emerald-400" />
            <span>Pending SoD</span>
          </span>
          <div className="text-2xl font-bold text-indigo-400 font-mono">
            {posture?.pending_exemptions_count ?? 0}
          </div>
          <span className="text-[10px] text-slate-400 mt-0.5 block">
            Four-Eyes review queue
          </span>
        </div>

        <div className="p-4 bg-slate-900/70 border border-slate-800 rounded-xl">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5 mb-1">
            <ShieldAlert size={13} className="text-purple-400" />
            <span>Mean Exposure</span>
          </span>
          <div className="text-2xl font-bold text-slate-100 font-mono">
            {(posture?.average_exposure_index ?? 0).toFixed(1)}
          </div>
          <span className="text-[10px] text-slate-400 mt-0.5 block">
            Average Product SCEI Index
          </span>
        </div>
      </div>

      {/* Tabs & Search */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2 overflow-x-auto pb-1 sm:pb-0">
          <button
            onClick={() => setActiveTab('products')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors ${
              activeTab === 'products'
                ? 'bg-indigo-600 text-white'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <Package size={14} />
            <span>Software Products</span>
          </button>

          <button
            onClick={() => setActiveTab('exemptions')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors ${
              activeTab === 'exemptions'
                ? 'bg-indigo-600 text-white'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <ShieldCheck size={14} />
            <span>Four-Eyes Exemptions</span>
            {Boolean(posture?.pending_exemptions_count) && (
              <span className="px-1.5 py-0.2 bg-amber-500 text-slate-950 font-bold rounded-full text-[10px]">
                {posture?.pending_exemptions_count}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab('engine')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors ${
              activeTab === 'engine'
                ? 'bg-indigo-600 text-white'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <Scale size={14} />
            <span>Risk Engine &amp; Policies</span>
          </button>
        </div>

        <div className="relative w-full sm:w-64">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search supply chain..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
          />
        </div>
      </div>

      {/* TAB CONTENT */}

      {/* 1. Software Products Tab */}
      {activeTab === 'products' && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <Filter size={13} className="text-slate-500" />
              <span className="text-xs text-slate-400">Lifecycle State:</span>
              <select
                value={productStateFilter}
                onChange={(e) => setProductStateFilter(e.target.value as any)}
                className="px-2.5 py-1 bg-slate-900 border border-slate-800 rounded text-xs text-slate-300 focus:outline-hidden focus:border-indigo-500"
              >
                <option value="ALL">All States</option>
                <option value="DRAFT">Draft</option>
                <option value="ACTIVE">Active</option>
                <option value="DEPRECATED">Deprecated</option>
                <option value="RETIRED">Retired</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400">Criticality:</span>
              <select
                value={productTierFilter}
                onChange={(e) => setProductTierFilter(e.target.value as any)}
                className="px-2.5 py-1 bg-slate-900 border border-slate-800 rounded text-xs text-slate-300 focus:outline-hidden focus:border-indigo-500"
              >
                <option value="ALL">All Criticalities</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>
            </div>
          </div>

          <Card className="p-0 overflow-hidden">
            <Table>
              <TableHead>
                <TableRow>
                  <TableHeaderCell>Product Code</TableHeaderCell>
                  <TableHeaderCell>Product Name</TableHeaderCell>
                  <TableHeaderCell>Type</TableHeaderCell>
                  <TableHeaderCell>Criticality</TableHeaderCell>
                  <TableHeaderCell>Version</TableHeaderCell>
                  <TableHeaderCell>SCEI Risk Index</TableHeaderCell>
                  <TableHeaderCell>Status</TableHeaderCell>
                  <TableHeaderCell className="text-right">Actions</TableHeaderCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {isProductsLoading ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center py-8">
                      <LoadingSpinner />
                    </TableCell>
                  </TableRow>
                ) : filteredProducts.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center py-8 text-xs text-slate-500">
                      No Software Products found. Click "Catalog Product" to register an application.
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredProducts.map((p) => (
                    <TableRow key={p.id}>
                      <TableCell className="font-mono text-xs font-semibold text-indigo-400">
                        <Link to={`/supply-chain/products/${p.id}`} className="hover:underline">
                          {p.product_code}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <div className="font-medium text-slate-100 text-xs">{p.name}</div>
                        {p.description && (
                          <div className="text-[11px] text-slate-400 truncate max-w-xs">
                            {p.description}
                          </div>
                        )}
                      </TableCell>
                      <TableCell className="text-xs text-slate-300">
                        {p.product_type.replace(/_/g, ' ')}
                      </TableCell>
                      <TableCell>
                        <Badge variant={p.criticality_tier === 'CRITICAL' ? 'danger' : p.criticality_tier === 'HIGH' ? 'warning' : 'info'}>
                          {p.criticality_tier}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-xs text-slate-300">
                        v{p.version_tag}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold text-slate-100">
                            {p.supply_chain_exposure_index.toFixed(1)}
                          </span>
                          {getRiskBandBadge(p.risk_band)}
                        </div>
                      </TableCell>
                      <TableCell>{getLifecycleBadge(p.lifecycle_state)}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <Button
                            size="xs"
                            variant="ghost"
                            onClick={() => navigate(`/supply-chain/products/${p.id}`)}
                            title="View Product Detail &amp; SBOMs"
                          >
                            <Eye size={13} />
                          </Button>
                          {canManage && (
                            <Button
                              size="xs"
                              variant="ghost"
                              onClick={() => {
                                setSelectedProductIdForSbom(p.id);
                                setIsSbomModalOpen(true);
                              }}
                              title="Ingest SBOM Manifest"
                              className="text-indigo-400 hover:text-indigo-300"
                            >
                              <FileCode size={13} />
                            </Button>
                          )}
                          {canManage && p.lifecycle_state !== 'RETIRED' && (
                            <Button
                              size="xs"
                              variant="ghost"
                              onClick={() => {
                                setEditingProduct(p);
                                setIsProductModalOpen(true);
                              }}
                              title="Edit Metadata"
                            >
                              <Edit2 size={13} />
                            </Button>
                          )}
                          {canManage && p.lifecycle_state !== 'ACTIVE' && (
                            <Button
                              size="xs"
                              variant="ghost"
                              onClick={() => {
                                if (confirm(`Are you sure you want to delete ${p.product_code}?`)) {
                                  deleteMutation.mutate(p.id);
                                }
                              }}
                              title="Delete Product"
                              className="text-rose-400 hover:text-rose-300"
                            >
                              <Trash2 size={13} />
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </Card>
        </div>
      )}

      {/* 2. Four-Eyes Risk Exemptions Tab */}
      {activeTab === 'exemptions' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Filter size={13} className="text-slate-500" />
              <span className="text-xs text-slate-400">Approval Status:</span>
              <select
                value={exemptionStatusFilter}
                onChange={(e) => setExemptionStatusFilter(e.target.value as any)}
                className="px-2.5 py-1 bg-slate-900 border border-slate-800 rounded text-xs text-slate-300 focus:outline-hidden focus:border-indigo-500"
              >
                <option value="ALL">All Statuses</option>
                <option value="PENDING">Pending Review</option>
                <option value="APPROVED">Approved</option>
                <option value="REJECTED">Rejected</option>
              </select>
            </div>

            {canAssess && (
              <Button
                size="sm"
                onClick={() => {
                  setSelectedExemptionProduct(null);
                  setIsExemptionModalOpen(true);
                }}
                className="flex items-center gap-1.5"
              >
                <Plus size={14} />
                <span>Submit Exemption Request</span>
              </Button>
            )}
          </div>

          <Card className="p-0 overflow-hidden">
            <Table>
              <TableHead>
                <TableRow>
                  <TableHeaderCell>Exemption Code</TableHeaderCell>
                  <TableHeaderCell>Target Resource</TableHeaderCell>
                  <TableHeaderCell>Reason &amp; Justification</TableHeaderCell>
                  <TableHeaderCell>Compensating Controls</TableHeaderCell>
                  <TableHeaderCell>Requested By</TableHeaderCell>
                  <TableHeaderCell>Status</TableHeaderCell>
                  <TableHeaderCell className="text-right">Four-Eyes Action</TableHeaderCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {isExemptionsLoading ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8">
                      <LoadingSpinner />
                    </TableCell>
                  </TableRow>
                ) : filteredExemptions.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8 text-xs text-slate-500">
                      No Supply Chain Exemptions found.
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredExemptions.map((ex) => (
                    <TableRow key={ex.id}>
                      <TableCell className="font-mono text-xs font-semibold text-indigo-400">
                        {ex.exemption_code}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-slate-300">
                        {ex.component_id ? `Component #${ex.component_id}` : `Product #${ex.software_product_id}`}
                      </TableCell>
                      <TableCell className="text-xs text-slate-200 max-w-xs">
                        <div className="line-clamp-2">{ex.reason}</div>
                      </TableCell>
                      <TableCell className="text-xs text-slate-300 max-w-xs">
                        <div className="line-clamp-2">{ex.compensating_controls}</div>
                      </TableCell>
                      <TableCell className="text-xs text-slate-400">
                        {ex.requested_by?.full_name || `User #${ex.requested_by_id}`}
                      </TableCell>
                      <TableCell>{getApprovalBadge(ex.approval_status)}</TableCell>
                      <TableCell className="text-right">
                        {ex.approval_status === 'PENDING' && canApprove ? (
                          <Button
                            size="xs"
                            variant="outline"
                            onClick={() => {
                              setSelectedExemptionForApproval(ex);
                              setIsApprovalModalOpen(true);
                            }}
                            className="text-amber-400 border-amber-500/30 hover:bg-amber-500/10"
                          >
                            <span>Review (SoD)</span>
                          </Button>
                        ) : (
                          <span className="text-[11px] text-slate-500 italic">
                            {ex.approval_status === 'PENDING' ? 'Awaiting Manager Review' : 'Finalized'}
                          </span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </Card>
        </div>
      )}

      {/* 3. Risk Engine & Policies Tab */}
      {activeTab === 'engine' && (
        <div className="space-y-6">
          <SupplyChainRiskCard />

          {/* License Compliance Policies */}
          <Card>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-semibold text-slate-100">
                  Open Source License Compliance Policies
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Automated policy rules evaluated during component cataloging and SBOM ingestion.
                </p>
              </div>
            </div>

            <Table>
              <TableHead>
                <TableRow>
                  <TableHeaderCell>License Name</TableHeaderCell>
                  <TableHeaderCell>SPDX ID</TableHeaderCell>
                  <TableHeaderCell>Risk Category</TableHeaderCell>
                  <TableHeaderCell>Strictly Prohibited</TableHeaderCell>
                  <TableHeaderCell>Justification Mandated</TableHeaderCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {isPoliciesLoading ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-6">
                      <LoadingSpinner />
                    </TableCell>
                  </TableRow>
                ) : policies.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-6 text-xs text-slate-500">
                      Standard default policies active (Permissive, Weak Copyleft, Strong Copyleft, Prohibited).
                    </TableCell>
                  </TableRow>
                ) : (
                  policies.map((pol) => (
                    <TableRow key={pol.id}>
                      <TableCell className="font-semibold text-xs text-slate-200">
                        {pol.license_name}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-slate-400">
                        {pol.spdx_identifier || '—'}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            pol.risk_category === 'PROHIBITED' || pol.risk_category === 'STRONG_COPYLEFT'
                              ? 'danger'
                              : pol.risk_category === 'WEAK_COPYLEFT'
                              ? 'warning'
                              : 'success'
                          }
                        >
                          {pol.risk_category}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {pol.is_strictly_prohibited ? (
                          <span className="text-xs text-rose-400 font-semibold">Yes (Violation)</span>
                        ) : (
                          <span className="text-xs text-slate-400">No</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {pol.justification_required ? (
                          <span className="text-xs text-amber-400 font-medium">Mandatory</span>
                        ) : (
                          <span className="text-xs text-slate-400">Optional</span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </Card>
        </div>
      )}

      {/* MODALS */}
      {isProductModalOpen && (
        <SoftwareProductModal
          isOpen={isProductModalOpen}
          onClose={() => setIsProductModalOpen(false)}
          product={editingProduct}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ['supply-chain-products'] });
            queryClient.invalidateQueries({ queryKey: ['supply-chain-posture'] });
          }}
        />
      )}

      {isSbomModalOpen && selectedProductIdForSbom && (
        <SBOMUploadModal
          isOpen={isSbomModalOpen}
          onClose={() => {
            setIsSbomModalOpen(false);
            setSelectedProductIdForSbom(null);
          }}
          productId={selectedProductIdForSbom}
          product={products.find((p) => p.id === selectedProductIdForSbom)}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ['supply-chain-products'] });
            queryClient.invalidateQueries({ queryKey: ['supply-chain-posture'] });
          }}
        />
      )}

      {isExemptionModalOpen && (
        <SupplyChainExemptionModal
          isOpen={isExemptionModalOpen}
          onClose={() => {
            setIsExemptionModalOpen(false);
            setSelectedExemptionProduct(null);
          }}
          productId={selectedExemptionProduct}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ['supply-chain-exemptions'] });
            queryClient.invalidateQueries({ queryKey: ['supply-chain-posture'] });
          }}
        />
      )}

      {isApprovalModalOpen && selectedExemptionForApproval && (
        <SupplyChainApprovalModal
          isOpen={isApprovalModalOpen}
          onClose={() => {
            setIsApprovalModalOpen(false);
            setSelectedExemptionForApproval(null);
          }}
          exemption={selectedExemptionForApproval}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ['supply-chain-exemptions'] });
            queryClient.invalidateQueries({ queryKey: ['supply-chain-posture'] });
            queryClient.invalidateQueries({ queryKey: ['supply-chain-products'] });
          }}
        />
      )}
    </div>
  );
};
export default SupplyChainGovernancePage;
