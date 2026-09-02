import React, { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
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
import { SoftwareComponentModal } from '../components/supply_chain/SoftwareComponentModal';
import { ComponentVulnerabilityModal } from '../components/supply_chain/ComponentVulnerabilityModal';
import type { SoftwareComponent, SupplyChainRiskBand } from '../types';
import {
  ArrowLeft,
  Box,
  ShieldAlert,
  Plus,
  Copy,
  Check,
  Calendar,
  User,
  Wrench,
  Package,
} from 'lucide-react';

export const SBOMDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const sbomId = Number(id);
  const navigate = useNavigate();
  const { hasRole } = useAuth();

  const canManage = hasRole('ADMIN', 'MANAGER', 'GRC_ANALYST');
  const canAssess = hasRole('ADMIN', 'MANAGER', 'GRC_ANALYST', 'SECURITY_ANALYST');

  const [copiedHash, setCopiedHash] = useState(false);
  const [isComponentModalOpen, setIsComponentModalOpen] = useState(false);
  const [isVulnModalOpen, setIsVulnModalOpen] = useState(false);
  const [selectedComponentForVuln, setSelectedComponentForVuln] = useState<SoftwareComponent | null>(null);

  // Queries
  const { data: sbom, isLoading: isSbomLoading, error: sbomError, refetch: refetchSbom } = useQuery({
    queryKey: ['supply-chain-sbom', sbomId],
    queryFn: () => supplyChainService.getSBOM(sbomId),
    enabled: !isNaN(sbomId),
  });

  const { data: components = [], isLoading: isComponentsLoading, refetch: refetchComponents } = useQuery({
    queryKey: ['supply-chain-sbom-components', sbomId],
    queryFn: () => supplyChainService.listSBOMComponents(sbomId),
    enabled: !isNaN(sbomId),
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

  const handleCopyHash = () => {
    if (sbom?.sha256_hash) {
      navigator.clipboard.writeText(sbom.sha256_hash);
      setCopiedHash(true);
      setTimeout(() => setCopiedHash(false), 2000);
    }
  };

  if (isSbomLoading) {
    return (
      <div className="flex justify-center items-center py-24">
        <LoadingSpinner />
      </div>
    );
  }

  if (sbomError || !sbom) {
    return (
      <div className="p-8 text-center space-y-4">
        <p className="text-sm text-rose-400">SBOM Manifest not found or access restricted.</p>
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
          to={`/supply-chain/products/${sbom.software_product_id}`}
          className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-200 transition-colors"
        >
          <ArrowLeft size={14} />
          <span>Back to Product #{sbom.software_product_id}</span>
        </Link>

        {canManage && sbom.status === 'ACTIVE' && (
          <Button
            size="sm"
            onClick={() => setIsComponentModalOpen(true)}
            className="flex items-center gap-1.5"
          >
            <Plus size={14} />
            <span>Catalog Component</span>
          </Button>
        )}
      </div>

      {/* Hero Card */}
      <div className="p-6 bg-slate-900/80 border border-slate-800 rounded-xl space-y-4">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-2xl font-bold text-slate-100 font-mono tracking-tight">
                {sbom.sbom_code}
              </h1>
              <Badge variant={sbom.status === 'ACTIVE' ? 'success' : 'default'}>
                {sbom.status}
              </Badge>
              <Badge variant="info">{sbom.format}</Badge>
              <span className="font-mono text-xs text-slate-400">Spec v{sbom.spec_version}</span>
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-400 mt-2">
              <Package size={13} className="text-indigo-400" />
              <span>Belongs to Software Product:</span>
              <Link
                to={`/supply-chain/products/${sbom.software_product_id}`}
                className="text-indigo-400 hover:underline font-mono font-medium"
              >
                Product #{sbom.software_product_id}
              </Link>
            </div>
          </div>

          <div className="flex gap-3">
            <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-lg text-center min-w-[100px]">
              <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider block">Components</span>
              <span className="text-xl font-bold font-mono text-slate-100">{sbom.total_components_count}</span>
            </div>
            <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-lg text-center min-w-[100px]">
              <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider block">Vulnerable</span>
              <span className="text-xl font-bold font-mono text-amber-400">{sbom.vulnerable_components_count}</span>
            </div>
            <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-lg text-center min-w-[100px]">
              <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider block">Prohibited</span>
              <span className="text-xl font-bold font-mono text-rose-400">{sbom.prohibited_licenses_count}</span>
            </div>
          </div>
        </div>

        {/* Cryptographic SHA-256 Digest Box */}
        <div className="p-3 bg-slate-950/90 border border-slate-800 rounded-lg flex items-center justify-between gap-4">
          <div className="overflow-hidden">
            <span className="text-[10px] uppercase font-semibold text-slate-500 tracking-wider block">
              Cryptographic SHA-256 Integrity Digest (Immutable)
            </span>
            <span className="font-mono text-xs text-emerald-400 truncate block mt-0.5 select-all">
              {sbom.sha256_hash}
            </span>
          </div>
          <Button
            size="xs"
            variant="outline"
            onClick={handleCopyHash}
            className="flex items-center gap-1 shrink-0"
          >
            {copiedHash ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
            <span>{copiedHash ? 'Copied' : 'Copy Hash'}</span>
          </Button>
        </div>

        {/* Metadata Strip */}
        <div className="pt-2 border-t border-slate-800/80 flex flex-wrap items-center gap-6 text-xs text-slate-400">
          <div className="flex items-center gap-1.5">
            <Wrench size={13} className="text-slate-500" />
            <span>Generating Tool: <strong className="text-slate-200">{sbom.tool_name || 'Generic Parser'}</strong></span>
          </div>
          <div className="flex items-center gap-1.5">
            <User size={13} className="text-slate-500" />
            <span>Author: <strong className="text-slate-200">{sbom.author_name || 'Automated Pipeline'}</strong></span>
          </div>
          <div className="flex items-center gap-1.5">
            <Calendar size={13} className="text-slate-500" />
            <span>Ingested At: <strong className="text-slate-200">{new Date(sbom.created_at).toLocaleString()}</strong></span>
          </div>
        </div>
      </div>

      {/* Component Registry Table */}
      <Card>
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
              <Box size={15} className="text-sky-400" />
              <span>Cataloged Component Registry ({components.length})</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Direct &amp; transitive dependencies with Package URLs and Component Risk Indices.
            </p>
          </div>

          {canManage && sbom.status === 'ACTIVE' && (
            <Button size="xs" onClick={() => setIsComponentModalOpen(true)} className="flex items-center gap-1">
              <Plus size={13} />
              <span>Add Component</span>
            </Button>
          )}
        </div>

        <Table>
          <TableHead>
            <TableRow>
              <TableHeaderCell>Package Name / PURL</TableHeaderCell>
              <TableHeaderCell>Version</TableHeaderCell>
              <TableHeaderCell>Ecosystem</TableHeaderCell>
              <TableHeaderCell>License</TableHeaderCell>
              <TableHeaderCell>Depth</TableHeaderCell>
              <TableHeaderCell>CVE Links</TableHeaderCell>
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
                  No components cataloged in this SBOM manifest.
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
      {isComponentModalOpen && (
        <SoftwareComponentModal
          isOpen={isComponentModalOpen}
          onClose={() => setIsComponentModalOpen(false)}
          sbomId={sbomId}
          onSuccess={() => {
            refetchComponents();
            refetchSbom();
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
            refetchComponents();
            refetchSbom();
          }}
        />
      )}
    </div>
  );
};
export default SBOMDetailPage;
