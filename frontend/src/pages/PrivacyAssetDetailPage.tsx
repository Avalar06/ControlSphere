import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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
import { PrivacyLineageCard } from '../components/privacy/PrivacyLineageCard';
import { DataAssetModal } from '../components/privacy/DataAssetModal';
import type { DataSensitivityLevel } from '../types';
import {
  ArrowLeft,
  ArrowRight,
  Calendar,
  Edit2,
  FileText,
  HardDrive,
  ShieldCheck,
  Trash2,
} from 'lucide-react';

export const PrivacyAssetDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const assetId = Number(id);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { hasRole } = useAuth();

  const canManage = hasRole('ADMIN', 'MANAGER', 'GRC_ANALYST');

  const [isEditModalOpen, setIsEditModalOpen] = useState(false);

  // Queries
  const {
    data: asset,
    isLoading: isAssetLoading,
    isError,
  } = useQuery({
    queryKey: ['privacy-asset-detail', assetId],
    queryFn: () => privacyService.getDataAsset(assetId),
    enabled: !isNaN(assetId),
  });

  const { data: allActivities = [] } = useQuery({
    queryKey: ['privacy-activities-all'],
    queryFn: () => privacyService.listProcessingActivities(),
  });

  // Filter linked activities that have matching cross-module lineage or reference
  const linkedActivities = allActivities.filter(
    (act) =>
      (asset?.business_process_id && act.business_process_id === asset.business_process_id) ||
      (asset?.ai_system_id && act.ai_system_id === asset.ai_system_id) ||
      (asset?.vendor_id && act.vendor_id === asset.vendor_id)
  );

  const deleteMutation = useMutation({
    mutationFn: () => privacyService.deleteDataAsset(assetId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['privacy-assets'] });
      navigate('/privacy');
    },
  });

  if (isAssetLoading) {
    return (
      <div className="p-12 flex justify-center">
        <LoadingSpinner />
      </div>
    );
  }

  if (isError || !asset) {
    return (
      <div className="p-8 text-center space-y-3">
        <div className="text-rose-400 font-medium text-sm">Data Asset Not Found</div>
        <p className="text-xs text-slate-500">
          The requested personal data asset does not exist or you lack permission to view it.
        </p>
        <Button variant="outline" size="sm" onClick={() => navigate('/privacy')}>
          Back to Privacy Workspace
        </Button>
      </div>
    );
  }

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

  return (
    <div className="space-y-6 pb-12">
      {/* Top Breadcrumb */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/privacy')}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
        >
          <ArrowLeft size={14} />
          <span>Back to Data Assets Inventory</span>
        </button>
        <div className="text-xs text-slate-500 font-mono">
          Last updated: {new Date(asset.updated_at).toLocaleString()}
        </div>
      </div>

      {/* Main Header Banner */}
      <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono text-sm font-bold text-indigo-400 px-2 py-0.5 rounded bg-indigo-950/60 border border-indigo-800/60">
                {asset.asset_code}
              </span>
              {getSensitivityBadge(asset.data_sensitivity_level)}
              <Badge variant="default">Storage: {asset.storage_type}</Badge>
              <Badge variant="info">Region: {asset.hosting_jurisdiction}</Badge>
            </div>
            <h1 className="text-xl font-bold text-slate-100 mt-2">{asset.name}</h1>
            <p className="text-xs text-slate-400 mt-1 max-w-3xl">
              {asset.description || 'No description recorded for this personal data repository.'}
            </p>
          </div>

          {/* Action Bar */}
          <div className="flex items-center gap-2">
            {canManage && (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsEditModalOpen(true)}
                  className="flex items-center gap-1.5"
                >
                  <Edit2 size={13} />
                  <span>Edit Asset</span>
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    if (confirm(`Permanently delete data asset ${asset.asset_code}?`)) {
                      deleteMutation.mutate();
                    }
                  }}
                  className="text-rose-400 hover:text-rose-300"
                >
                  <Trash2 size={14} />
                </Button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Grid: Safeguards & Retention */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Storage & Volume */}
        <Card className="p-4 bg-slate-900 border-slate-800 space-y-2">
          <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <HardDrive size={14} className="text-indigo-400" />
            Infrastructure Profile
          </div>
          <div className="space-y-1.5 text-xs pt-1">
            <div className="flex justify-between">
              <span className="text-slate-400">Storage Architecture:</span>
              <span className="text-slate-200 font-mono">{asset.storage_type}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Hosting Jurisdiction:</span>
              <span className="text-slate-200 font-mono">{asset.hosting_jurisdiction}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Data Volume Tier:</span>
              <span className="text-slate-200 font-mono font-bold">{asset.data_volume_range}</span>
            </div>
          </div>
        </Card>

        {/* Technical Safeguards */}
        <Card className="p-4 bg-slate-900 border-slate-800 space-y-2">
          <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <ShieldCheck size={14} className="text-emerald-400" />
            Encryption &amp; Safeguards
          </div>
          <div className="space-y-1.5 text-xs pt-1">
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Encrypted at Rest:</span>
              <Badge variant={asset.is_encrypted_at_rest ? 'success' : 'danger'}>
                {asset.is_encrypted_at_rest ? 'YES (ENCRYPTED)' : 'UNENCRYPTED'}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Encrypted in Transit:</span>
              <Badge variant={asset.is_encrypted_in_transit ? 'success' : 'danger'}>
                {asset.is_encrypted_in_transit ? 'YES (TLS 1.3)' : 'UNENCRYPTED'}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Pseudonymized:</span>
              <Badge variant={asset.is_pseudonymized ? 'info' : 'default'}>
                {asset.is_pseudonymized ? 'PSEUDONYMIZED' : 'PLAIN IDENTIFIERS'}
              </Badge>
            </div>
          </div>
        </Card>

        {/* Retention Policy */}
        <Card className="p-4 bg-slate-900 border-slate-800 space-y-2">
          <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <Calendar size={14} className="text-cyan-400" />
            Retention Governance
          </div>
          <div className="space-y-1.5 text-xs pt-1">
            <div className="flex justify-between">
              <span className="text-slate-400">Retention Limit:</span>
              <span className="text-cyan-400 font-bold font-mono">
                {asset.retention_period_months ? `${asset.retention_period_months} months` : 'Indefinite'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Registration Date:</span>
              <span className="text-slate-300 font-mono">
                {new Date(asset.created_at).toLocaleDateString()}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Catalog Owner:</span>
              <span className="text-slate-300 font-mono">User #{asset.owner_id}</span>
            </div>
          </div>
        </Card>
      </div>

      {/* Cross-Module GRC Lineage */}
      <PrivacyLineageCard
        businessProcessId={asset.business_process_id}
        aiSystemId={asset.ai_system_id}
        vendorId={asset.vendor_id}
      />

      {/* Linked RoPA Activities */}
      <Card className="p-5 bg-slate-900 border-slate-800 space-y-3">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <FileText size={16} className="text-indigo-400" />
            <h3 className="text-sm font-semibold text-slate-200">
              Related Processing Activities (RoPA Flows)
            </h3>
          </div>
          <span className="text-xs text-slate-400 font-mono">
            {linkedActivities.length} linked
          </span>
        </div>

        {linkedActivities.length === 0 ? (
          <div className="py-6 text-center text-xs text-slate-500">
            No active RoPA flows directly mapped to this data asset repository.
          </div>
        ) : (
          <Table>
            <TableHead>
              <TableRow>
                <TableHeaderCell>ROPA CODE</TableHeaderCell>
                <TableHeaderCell>NAME</TableHeaderCell>
                <TableHeaderCell>LEGAL BASIS</TableHeaderCell>
                <TableHeaderCell>LIFECYCLE STATE</TableHeaderCell>
                <TableHeaderCell className="text-right">VIEW</TableHeaderCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {linkedActivities.map((act) => (
                <TableRow key={act.id}>
                  <TableCell className="font-mono text-xs font-bold text-indigo-400">
                    {act.activity_code}
                  </TableCell>
                  <TableCell className="text-xs text-slate-200">{act.name}</TableCell>
                  <TableCell>
                    <Badge variant="default">{act.legal_basis}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        act.lifecycle_state === 'ACTIVE'
                          ? 'success'
                          : act.lifecycle_state === 'RETIRED'
                          ? 'danger'
                          : 'warning'
                      }
                    >
                      {act.lifecycle_state}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => navigate(`/privacy/processing/${act.id}`)}
                    >
                      <ArrowRight size={14} />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Card>

      {/* Edit Modal */}
      <DataAssetModal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        asset={asset}
        onSuccess={() => {
          queryClient.invalidateQueries({ queryKey: ['privacy-asset-detail', assetId] });
        }}
      />
    </div>
  );
};
