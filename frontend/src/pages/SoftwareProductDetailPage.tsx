import React, { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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
import { SoftwareComponentModal } from '../components/supply_chain/SoftwareComponentModal';
import { ComponentVulnerabilityModal } from '../components/supply_chain/ComponentVulnerabilityModal';
import { SupplyChainExemptionModal } from '../components/supply_chain/SupplyChainExemptionModal';
import { SupplyChainLineageCard } from '../components/supply_chain/SupplyChainLineageCard';
import type {
  ProductLifecycleState,
  SoftwareComponent,
  SupplyChainRiskBand,
} from '../types';
import {
  ArrowLeft,
  FileCode,
  Box,
  ShieldAlert,
  ShieldCheck,
  Plus,
  ExternalLink,
  Edit2,
  GitBranch,
  Layers,
  Calendar,
} from 'lucide-react';

export const SoftwareProductDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const productId = Number(id);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { hasRole } = useAuth();

  const canManage = hasRole('ADMIN', 'MANAGER', 'GRC_ANALYST');
  const canAssess = hasRole('ADMIN', 'MANAGER', 'GRC_ANALYST', 'SECURITY_ANALYST');

  // Modals state
  const [isProductModalOpen, setIsProductModalOpen] = useState(false);
  const [isSbomModalOpen, setIsSbomModalOpen] = useState(false);
  const [isComponentModalOpen, setIsComponentModalOpen] = useState(false);
  const [selectedSbomIdForComponent, setSelectedSbomIdForComponent] = useState<number | null>(null);
  const [isVulnModalOpen, setIsVulnModalOpen] = useState(false);
  const [selectedComponentForVuln, setSelectedComponentForVuln] = useState<SoftwareComponent | null>(null);
  const [isExemptionModalOpen, setIsExemptionModalOpen] = useState(false);

  // Queries
  const { data: product, isLoading: isProductLoading, error: productError } = useQuery({
    queryKey: ['supply-chain-product', productId],
    queryFn: () => supplyChainService.getProduct(productId),
    enabled: !isNaN(productId),
  });

  const { data: sboms = [], isLoading: isSbomsLoading } = useQuery({
    queryKey: ['supply-chain-product-sboms', productId],
    queryFn: () => supplyChainService.listProductSBOMs(productId),
    enabled: !isNaN(productId),
  });

  // Find Active SBOM
  const activeSbom = sboms.find((s) => s.status === 'ACTIVE') || sboms[0];

  // Components Query for the active SBOM
  const { data: components = [], isLoading: isComponentsLoading } = useQuery({
    queryKey: ['supply-chain-sbom-components', activeSbom?.id],
    queryFn: () => (activeSbom ? supplyChainService.listSBOMComponents(activeSbom.id) : []),
    enabled: Boolean(activeSbom?.id),
  });

  // Lifecycle status mutation
  const statusMutation = useMutation({
    mutationFn: (newStatus: ProductLifecycleState) =>
      supplyChainService.updateProductStatus(productId, {
        status: newStatus,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['supply-chain-product', productId] });
      queryClient.invalidateQueries({ queryKey: ['supply-chain-products'] });
      queryClient.invalidateQueries({ queryKey: ['supply-chain-posture'] });
    },
    onError: (err: any) => {
      alert(err?.response?.data?.detail || 'Failed to update lifecycle status.');
    },
  });

  const getRiskBandBadge = (band?: SupplyChainRiskBand) => {
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

  const getLifecycleBadge = (state?: ProductLifecycleState) => {
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

  if (isProductLoading) {
    return (
      <div className="flex justify-center items-center py-24">
        <LoadingSpinner />
      </div>
    );
  }

  if (productError || !product) {
    return (
      <div className="p-8 text-center space-y-4">
        <p className="text-sm text-rose-400">Software Product not found or access restricted.</p>
        <Button size="sm" variant="outline" onClick={() => navigate('/supply-chain')}>
          Back to Supply Chain Register
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb & Navigation */}
      <div className="flex items-center justify-between">
        <Link
          to="/supply-chain"
          className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-200 transition-colors"
        >
          <ArrowLeft size={14} />
          <span>Back to Supply Chain Register</span>
        </Link>

        <div className="flex items-center gap-2">
          {canManage && product.lifecycle_state !== 'RETIRED' && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => setIsProductModalOpen(true)}
              className="flex items-center gap-1.5"
            >
              <Edit2 size={13} />
              <span>Edit Metadata</span>
            </Button>
          )}

          {canManage && product.lifecycle_state !== 'RETIRED' && (
            <Button
              size="sm"
              onClick={() => setIsSbomModalOpen(true)}
              className="flex items-center gap-1.5"
            >
              <FileCode size={14} />
              <span>Ingest New SBOM</span>
            </Button>
          )}

          {canAssess && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => setIsExemptionModalOpen(true)}
              className="flex items-center gap-1.5"
            >
              <ShieldCheck size={14} className="text-indigo-400" />
              <span>Request Exemption</span>
            </Button>
          )}
        </div>
      </div>

      {/* Hero Header Card */}
      <div className="p-6 bg-slate-900/80 border border-slate-800 rounded-xl space-y-4">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-2xl font-bold text-slate-100 font-mono tracking-tight">
                {product.product_code}
              </h1>
              {getLifecycleBadge(product.lifecycle_state)}
              <Badge variant={product.criticality_tier === 'CRITICAL' ? 'danger' : 'warning'}>
                {product.criticality_tier}
              </Badge>
              <span className="font-mono text-xs text-slate-400">v{product.version_tag}</span>
            </div>
            <h2 className="text-base text-slate-200 font-medium mt-1">{product.name}</h2>
            {product.description && (
              <p className="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed">
                {product.description}
              </p>
            )}
          </div>

          {/* Exposure Index Gauge */}
          <div className="p-4 bg-slate-950/80 border border-slate-800 rounded-xl flex items-center gap-4 min-w-[220px]">
            <div>
              <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">
                Product Exposure Index
              </span>
              <div className="text-3xl font-bold font-mono text-indigo-400 mt-0.5">
                {product.supply_chain_exposure_index.toFixed(1)}
              </div>
              <span className="text-[10px] text-slate-500">SCEI composite score</span>
            </div>
            <div className="flex flex-col items-end gap-1">
              {getRiskBandBadge(product.risk_band)}
              <span className="text-[10px] text-slate-500">Risk Band</span>
            </div>
          </div>
        </div>

        {/* Technical Repositories & Lifecycle Controls */}
        <div className="pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-4 text-xs">
          <div className="flex flex-wrap items-center gap-4 text-slate-400">
            {product.repository_url && (
              <a
                href={product.repository_url}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1.5 text-indigo-400 hover:underline"
              >
                <GitBranch size={14} />
                <span>Source Repository</span>
                <ExternalLink size={11} />
              </a>
            )}
            {product.build_pipeline_url && (
              <a
                href={product.build_pipeline_url}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1.5 text-indigo-400 hover:underline"
              >
                <Layers size={14} />
                <span>CI/CD Pipeline</span>
                <ExternalLink size={11} />
              </a>
            )}
            <div className="flex items-center gap-1 text-slate-500">
              <Calendar size={13} />
              <span>Cataloged: {new Date(product.created_at).toLocaleDateString()}</span>
            </div>
          </div>

          {/* State Machine Transition Actions */}
          {canManage && product.lifecycle_state !== 'RETIRED' && (
            <div className="flex items-center gap-2">
              <span className="text-slate-400 font-medium">Transition State:</span>
              {product.lifecycle_state === 'DRAFT' && (
                <Button
                  size="xs"
                  variant="outline"
                  onClick={() => statusMutation.mutate('ACTIVE')}
                  disabled={statusMutation.isPending}
                  className="text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/10"
                >
                  Publish Active
                </Button>
              )}
              {product.lifecycle_state === 'ACTIVE' && (
                <Button
                  size="xs"
                  variant="outline"
                  onClick={() => statusMutation.mutate('DEPRECATED')}
                  disabled={statusMutation.isPending}
                  className="text-amber-400 border-amber-500/30 hover:bg-amber-500/10"
                >
                  Deprecate
                </Button>
              )}
              {product.lifecycle_state === 'DEPRECATED' && (
                <>
                  <Button
                    size="xs"
                    variant="outline"
                    onClick={() => statusMutation.mutate('ACTIVE')}
                    disabled={statusMutation.isPending}
                    className="text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/10"
                  >
                    Reactivate
                  </Button>
                  <Button
                    size="xs"
                    variant="outline"
                    onClick={() => {
                      if (confirm('Permanently retire this product? Retired products are completely locked against future mutations.')) {
                        statusMutation.mutate('RETIRED');
                      }
                    }}
                    disabled={statusMutation.isPending}
                    className="text-rose-400 border-rose-500/30 hover:bg-rose-500/10"
                  >
                    Retire (Lock)
                  </Button>
                </>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Cross-Module Lineage */}
      <SupplyChainLineageCard product={product} />

      {/* SBOM Manifests Section */}
      <Card>
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
              <FileCode size={15} className="text-indigo-400" />
              <span>Software Bill of Materials (SBOM) Manifests</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Ingested CycloneDX and SPDX manifest revisions.
            </p>
          </div>

          {canManage && product.lifecycle_state !== 'RETIRED' && (
            <Button size="xs" onClick={() => setIsSbomModalOpen(true)} className="flex items-center gap-1">
              <Plus size={13} />
              <span>Upload SBOM</span>
            </Button>
          )}
        </div>

        <Table>
          <TableHead>
            <TableRow>
              <TableHeaderCell>SBOM Code</TableHeaderCell>
              <TableHeaderCell>Format &amp; Version</TableHeaderCell>
              <TableHeaderCell>SHA-256 Digest</TableHeaderCell>
              <TableHeaderCell>Tool &amp; Author</TableHeaderCell>
              <TableHeaderCell>Components</TableHeaderCell>
              <TableHeaderCell>Vulnerable</TableHeaderCell>
              <TableHeaderCell>Prohibited OSS</TableHeaderCell>
              <TableHeaderCell>Status</TableHeaderCell>
              <TableHeaderCell className="text-right">Action</TableHeaderCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {isSbomsLoading ? (
              <TableRow>
                <TableCell colSpan={9} className="text-center py-6">
                  <LoadingSpinner />
                </TableCell>
              </TableRow>
            ) : sboms.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9} className="text-center py-6 text-xs text-slate-500">
                  No SBOM manifests ingested for this product. Click "Upload SBOM" to import CycloneDX or SPDX JSON.
                </TableCell>
              </TableRow>
            ) : (
              sboms.map((sb) => (
                <TableRow key={sb.id}>
                  <TableCell className="font-mono text-xs font-semibold text-indigo-400">
                    <Link to={`/supply-chain/sboms/${sb.id}`} className="hover:underline">
                      {sb.sbom_code}
                    </Link>
                  </TableCell>
                  <TableCell className="text-xs text-slate-300">
                    {sb.format} (v{sb.spec_version})
                  </TableCell>
                  <TableCell className="font-mono text-[11px] text-slate-400 truncate max-w-[120px]">
                    {sb.sha256_hash.substring(0, 12)}...
                  </TableCell>
                  <TableCell className="text-xs text-slate-400">
                    {sb.tool_name || 'Generic'} ({sb.author_name || 'System'})
                  </TableCell>
                  <TableCell className="font-mono text-xs text-slate-200">
                    {sb.total_components_count}
                  </TableCell>
                  <TableCell className="font-mono text-xs text-amber-400">
                    {sb.vulnerable_components_count}
                  </TableCell>
                  <TableCell className="font-mono text-xs text-rose-400">
                    {sb.prohibited_licenses_count}
                  </TableCell>
                  <TableCell>
                    <Badge variant={sb.status === 'ACTIVE' ? 'success' : 'default'}>
                      {sb.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      size="xs"
                      variant="ghost"
                      onClick={() => navigate(`/supply-chain/sboms/${sb.id}`)}
                      title="Inspect Manifest"
                    >
                      <ExternalLink size={13} />
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </Card>

      {/* Component Inventory Section (Active SBOM) */}
      <Card>
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
              <Box size={15} className="text-sky-400" />
              <span>Active SBOM Component Inventory ({activeSbom?.sbom_code || 'None'})</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Direct &amp; transitive dependencies indexed with CRI scores and license compliance classifications.
            </p>
          </div>

          {canManage && activeSbom && product.lifecycle_state !== 'RETIRED' && (
            <Button
              size="xs"
              onClick={() => {
                setSelectedSbomIdForComponent(activeSbom.id);
                setIsComponentModalOpen(true);
              }}
              className="flex items-center gap-1"
            >
              <Plus size={13} />
              <span>Add Component</span>
            </Button>
          )}
        </div>

        <Table>
          <TableHead>
            <TableRow>
              <TableHeaderCell>Component / PURL</TableHeaderCell>
              <TableHeaderCell>Version</TableHeaderCell>
              <TableHeaderCell>Ecosystem</TableHeaderCell>
              <TableHeaderCell>License</TableHeaderCell>
              <TableHeaderCell>Depth</TableHeaderCell>
              <TableHeaderCell>Vulns</TableHeaderCell>
              <TableHeaderCell>Component Risk Index</TableHeaderCell>
              <TableHeaderCell className="text-right">Actions</TableHeaderCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {isComponentsLoading ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-6">
                  <LoadingSpinner />
                </TableCell>
              </TableRow>
            ) : components.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-6 text-xs text-slate-500">
                  No components cataloged in the active SBOM manifest.
                </TableCell>
              </TableRow>
            ) : (
              components.map((comp) => (
                <TableRow key={comp.id}>
                  <TableCell>
                    <div className="font-semibold text-xs text-slate-100 font-mono">{comp.name}</div>
                    {comp.purl && (
                      <div className="text-[10px] text-slate-400 font-mono truncate max-w-xs">{comp.purl}</div>
                    )}
                  </TableCell>
                  <TableCell className="font-mono text-xs text-slate-300">
                    {comp.version}
                  </TableCell>
                  <TableCell className="text-xs text-slate-300">
                    {comp.ecosystem}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs text-slate-300">{comp.declared_license || 'Unknown'}</span>
                      {comp.is_license_prohibited && (
                        <Badge variant="danger">PROHIBITED</Badge>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant={comp.is_direct_dependency ? 'info' : 'default'}>
                      {comp.is_direct_dependency ? 'Direct (1)' : `Transitive (${comp.dependency_depth})`}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-mono text-xs">
                    {comp.vulnerabilities_count > 0 ? (
                      <span className="text-amber-400 font-bold">{comp.vulnerabilities_count} CVE</span>
                    ) : (
                      <span className="text-slate-500">0</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-slate-100">
                        {comp.component_risk_index.toFixed(1)}
                      </span>
                      {getRiskBandBadge(comp.risk_band)}
                      {comp.is_exempted && (
                        <span className="text-[10px] px-1 bg-emerald-500/20 text-emerald-300 rounded border border-emerald-500/30">
                          Exempt
                        </span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      {canAssess && (
                        <Button
                          size="xs"
                          variant="ghost"
                          onClick={() => {
                            setSelectedComponentForVuln(comp);
                            setIsVulnModalOpen(true);
                          }}
                          title="Link Phase 14 CVE Vulnerability"
                          className="text-amber-400 hover:text-amber-300"
                        >
                          <ShieldAlert size={13} />
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

      {/* MODALS */}
      {isProductModalOpen && (
        <SoftwareProductModal
          isOpen={isProductModalOpen}
          onClose={() => setIsProductModalOpen(false)}
          product={product}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ['supply-chain-product', productId] });
            queryClient.invalidateQueries({ queryKey: ['supply-chain-products'] });
          }}
        />
      )}

      {isSbomModalOpen && (
        <SBOMUploadModal
          isOpen={isSbomModalOpen}
          onClose={() => setIsSbomModalOpen(false)}
          productId={productId}
          product={product}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ['supply-chain-product', productId] });
            queryClient.invalidateQueries({ queryKey: ['supply-chain-product-sboms', productId] });
            queryClient.invalidateQueries({ queryKey: ['supply-chain-posture'] });
          }}
        />
      )}

      {isComponentModalOpen && selectedSbomIdForComponent && (
        <SoftwareComponentModal
          isOpen={isComponentModalOpen}
          onClose={() => {
            setIsComponentModalOpen(false);
            setSelectedSbomIdForComponent(null);
          }}
          sbomId={selectedSbomIdForComponent}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ['supply-chain-sbom-components', selectedSbomIdForComponent] });
            queryClient.invalidateQueries({ queryKey: ['supply-chain-product', productId] });
            queryClient.invalidateQueries({ queryKey: ['supply-chain-posture'] });
          }}
        />
      )}

      {isVulnModalOpen && selectedComponentForVuln && (
        <ComponentVulnerabilityModal
          isOpen={isVulnModalOpen}
          onClose={() => {
            setIsVulnModalOpen(false);
            setSelectedComponentForVuln(null);
          }}
          component={selectedComponentForVuln}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ['supply-chain-sbom-components', activeSbom?.id] });
            queryClient.invalidateQueries({ queryKey: ['supply-chain-product', productId] });
            queryClient.invalidateQueries({ queryKey: ['supply-chain-posture'] });
          }}
        />
      )}

      {isExemptionModalOpen && (
        <SupplyChainExemptionModal
          isOpen={isExemptionModalOpen}
          onClose={() => setIsExemptionModalOpen(false)}
          productId={productId}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ['supply-chain-exemptions'] });
            queryClient.invalidateQueries({ queryKey: ['supply-chain-product', productId] });
          }}
        />
      )}
    </div>
  );
};
export default SoftwareProductDetailPage;
