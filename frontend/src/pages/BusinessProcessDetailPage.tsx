import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../context/AuthContext';
import { resilienceService } from '../lib/resilienceService';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Table, TableBody, TableCell, TableHead, TableHeaderCell, TableRow } from '../components/ui/Table';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { ProcessModal } from '../components/resilience/ProcessModal';
import { BiaModal } from '../components/resilience/BiaModal';
import { BiaApprovalModal } from '../components/resilience/BiaApprovalModal';
import { DependencyModal } from '../components/resilience/DependencyModal';
import { OutageImpactCard } from '../components/resilience/OutageImpactCard';
import { BiaHistoryCard } from '../components/resilience/BiaHistoryCard';
import type { BusinessImpactAnalysis, CriticalityTier } from '../types';
import {
  AlertTriangle,
  ArrowLeft,
  Building2,
  Clock,
  Edit2,
  Link2,
  Lock,
  Plus,
  Shield,
  ShieldCheck,
  Trash2,
} from 'lucide-react';

export const BusinessProcessDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const processId = parseInt(id || '0', 10);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { hasRole } = useAuth();

  const canManage = hasRole('ADMIN', 'MANAGER', 'GRC_ANALYST');
  const canApprove = hasRole('ADMIN', 'MANAGER');

  // Modals state
  const [isProcessModalOpen, setIsProcessModalOpen] = useState(false);
  const [isBiaModalOpen, setIsBiaModalOpen] = useState(false);
  const [editingBia, setEditingBia] = useState<BusinessImpactAnalysis | null>(null);
  const [isApprovalModalOpen, setIsApprovalModalOpen] = useState(false);
  const [approvingBia, setApprovingBia] = useState<BusinessImpactAnalysis | null>(null);
  const [isDependencyModalOpen, setIsDependencyModalOpen] = useState(false);

  // Queries
  const {
    data: process,
    isLoading: isProcessLoading,
    isError: isProcessError,
    refetch: refetchProcess,
  } = useQuery({
    queryKey: ['resilience-process', processId],
    queryFn: () => resilienceService.getProcess(processId),
    enabled: processId > 0,
  });

  const {
    data: bias = [],
  } = useQuery({
    queryKey: ['resilience-process-bias', processId],
    queryFn: () => resilienceService.listProcessBias(processId),
    enabled: processId > 0,
  });

  const {
    data: dependencies = [],
  } = useQuery({
    queryKey: ['resilience-dependencies', processId],
    queryFn: () => resilienceService.listDependencies(processId),
    enabled: processId > 0,
  });

  const removeDepMutation = useMutation({
    mutationFn: (depId: number) => resilienceService.removeDependency(depId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resilience-process', processId] });
      queryClient.invalidateQueries({ queryKey: ['resilience-dependencies', processId] });
    },
  });

  if (isProcessLoading) {
    return (
      <div className="py-20 flex justify-center">
        <LoadingSpinner text="Loading business process telemetry..." />
      </div>
    );
  }

  if (isProcessError || !process) {
    return (
      <div className="p-8 bg-rose-500/10 border border-rose-500/30 rounded-xl text-center space-y-3">
        <AlertTriangle className="h-10 w-10 text-rose-400 mx-auto" />
        <h2 className="text-base font-bold text-slate-100">Business Process Not Found</h2>
        <p className="text-xs text-slate-400">
          The requested business process does not exist or is not authorized under the current tenant organization.
        </p>
        <Button variant="secondary" onClick={() => navigate('/resilience')} className="text-xs">
          Return to Process Register
        </Button>
      </div>
    );
  }

  const activeBia = process.active_bia;

  const getTierBadge = (tier: CriticalityTier) => {
    switch (tier) {
      case 'TIER_1':
        return <Badge variant="danger">TIER 1 — MISSION CRITICAL</Badge>;
      case 'TIER_2':
        return <Badge variant="warning">TIER 2 — HIGH IMPACT</Badge>;
      case 'TIER_3':
        return <Badge variant="info">TIER 3 — MODERATE</Badge>;
      case 'TIER_4':
        return <Badge variant="default">TIER 4 — LOW IMPACT</Badge>;
      default:
        return <Badge variant="default">{tier}</Badge>;
    }
  };

  return (
    <div className="space-y-6 pb-16">
      {/* Navigation Breadcrumb & Back */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/resilience')}
          className="flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-slate-200 transition-colors"
        >
          <ArrowLeft size={16} />
          <span>Back to Process Register</span>
        </button>

        <div className="flex items-center gap-2">
          {getTierBadge(process.criticality_tier)}
          <span className="text-xs font-mono text-slate-500">ID #{process.id}</span>
        </div>
      </div>

      {/* Process Header & Overview Card */}
      <Card className="border-slate-800 bg-slate-900/90 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold text-slate-100">{process.name}</h1>
            </div>
            <p className="text-xs text-slate-400 mt-1 max-w-3xl">
              {process.description || 'No detailed scope or service boundary description provided.'}
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {canManage && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setIsProcessModalOpen(true)}
                className="text-xs flex items-center gap-1.5"
              >
                <Edit2 size={13} />
                <span>Edit Process</span>
              </Button>
            )}

            {canManage && (
              <Button
                size="sm"
                onClick={() => {
                  setEditingBia(null);
                  setIsBiaModalOpen(true);
                }}
                className="text-xs flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-500 text-white"
              >
                <Plus size={14} />
                <span>Draft New BIA</span>
              </Button>
            )}
          </div>
        </div>

        {/* Process Metadata Details */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
          <div>
            <span className="text-slate-500 block text-[10px] uppercase font-semibold">Process Owner</span>
            <span className="text-slate-200">{process.owner?.full_name || `User #${process.owner_id}`}</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px] uppercase font-semibold">Criticality Tier</span>
            <span className="text-slate-200">{process.criticality_tier}</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px] uppercase font-semibold">Registered At</span>
            <span className="text-slate-200">{new Date(process.created_at).toLocaleDateString()}</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px] uppercase font-semibold">Last Updated</span>
            <span className="text-slate-200">{new Date(process.updated_at).toLocaleDateString()}</span>
          </div>
        </div>
      </Card>

      {/* Active Baseline Card */}
      {activeBia ? (
        <Card className="border-emerald-950/60 bg-slate-900/90 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2.5">
              <ShieldCheck className="h-5 w-5 text-emerald-400" />
              <div>
                <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
                  Active Approved BIA Baseline (Version {activeBia.version})
                  <Badge variant="success">ACTIVE BASELINE</Badge>
                  <Lock size={13} className="text-slate-400" />
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Governed operational recovery thresholds &amp; financial disruption metrics approved under four-eyes separation.
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3.5">
            <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800">
              <span className="text-[10px] font-semibold text-slate-400 uppercase font-mono">Recovery Time (RTO)</span>
              <div className="text-xl font-bold font-mono text-emerald-400 mt-1">{activeBia.rto_hours}h</div>
              <span className="text-[10px] text-slate-500 mt-1 block">Target recovery window</span>
            </div>

            <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800">
              <span className="text-[10px] font-semibold text-slate-400 uppercase font-mono">Recovery Point (RPO)</span>
              <div className="text-xl font-bold font-mono text-slate-200 mt-1">{activeBia.rpo_hours}h</div>
              <span className="text-[10px] text-slate-500 mt-1 block">Maximum data loss</span>
            </div>

            <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800">
              <span className="text-[10px] font-semibold text-slate-400 uppercase font-mono">Max Downtime (MTD)</span>
              <div className="text-xl font-bold font-mono text-amber-400 mt-1">{activeBia.mtd_hours}h</div>
              <span className="text-[10px] text-slate-500 mt-1 block">Disruption tolerance ceiling</span>
            </div>

            <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800">
              <span className="text-[10px] font-semibold text-slate-400 uppercase font-mono">Hourly Disruption</span>
              <div className="text-xl font-bold font-mono text-indigo-300 mt-1">
                ${activeBia.hourly_downtime_cost.toLocaleString()}
              </div>
              <span className="text-[10px] text-slate-500 mt-1 block">Loss per downtime hour</span>
            </div>

            <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800">
              <span className="text-[10px] font-semibold text-slate-400 uppercase font-mono">Fixed Outage Cost</span>
              <div className="text-xl font-bold font-mono text-slate-200 mt-1">
                ${activeBia.fixed_outage_cost.toLocaleString()}
              </div>
              <span className="text-[10px] text-slate-500 mt-1 block">Initial mobilization loss</span>
            </div>
          </div>

          <div className="p-3 bg-slate-950/40 rounded-lg border border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between text-xs text-slate-400 gap-2">
            <div>
              <span className="font-semibold text-slate-300">Four-Eyes Governance Trail:</span>{' '}
              Drafted by <span className="font-mono text-slate-200">{activeBia.requested_by?.full_name || `User #${activeBia.requested_by_id}`}</span> |{' '}
              Approved by <span className="font-mono text-emerald-400 font-semibold">{activeBia.approved_by?.full_name || `User #${activeBia.approved_by_id}`}</span> on{' '}
              <span className="font-mono text-slate-200">{activeBia.approved_at ? new Date(activeBia.approved_at).toLocaleDateString() : 'N/A'}</span>
            </div>
          </div>
        </Card>
      ) : (
        <Card className="border-amber-900/40 bg-amber-950/10 p-6 text-center space-y-3">
          <Clock className="h-8 w-8 text-amber-400 mx-auto" />
          <h3 className="text-sm font-bold text-slate-100">No Active BIA Baseline Established</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            This business process has no formally approved BIA baseline. Create a draft BIA and submit it for secondary managerial review.
          </p>
          {canManage && (
            <Button
              onClick={() => {
                setEditingBia(null);
                setIsBiaModalOpen(true);
              }}
              className="bg-indigo-600 hover:bg-indigo-500 text-xs"
            >
              <Plus size={14} className="mr-1" /> Draft Initial BIA
            </Button>
          )}
        </Card>
      )}

      {/* Outage Loss Simulation Engine (Rendered when active BIA exists) */}
      {activeBia && <OutageImpactCard bia={activeBia} />}

      {/* Cross-Module Dependencies Section */}
      <Card className="border-slate-800 bg-slate-900/90 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <Link2 className="h-5 w-5 text-indigo-400" />
            <div>
              <h3 className="text-sm font-semibold text-slate-100">
                Upstream Process Dependencies ({dependencies.length})
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Links to Phase 9 critical suppliers (TPRM) and Phase 2 organizational safeguards.
              </p>
            </div>
          </div>

          {canManage && (
            <Button
              size="sm"
              onClick={() => setIsDependencyModalOpen(true)}
              className="text-xs flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-500 text-white"
            >
              <Plus size={14} />
              <span>Link Dependency</span>
            </Button>
          )}
        </div>

        {dependencies.length === 0 ? (
          <div className="p-8 text-center bg-slate-950/60 rounded-xl border border-slate-800">
            <Link2 className="h-8 w-8 text-slate-600 mx-auto mb-2" />
            <p className="text-xs text-slate-400 font-medium">No vendor or control dependencies linked to this process.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHead>
                <TableRow>
                  <TableHeaderCell>Dependency Type</TableHeaderCell>
                  <TableHeaderCell>Target Reference</TableHeaderCell>
                  <TableHeaderCell>Context Notes</TableHeaderCell>
                  <TableHeaderCell>Linked Date</TableHeaderCell>
                  <TableHeaderCell className="text-right">Actions</TableHeaderCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {dependencies.map((dep) => (
                  <TableRow key={dep.id}>
                    <TableCell>
                      {dep.dependency_type === 'VENDOR' ? (
                        <div className="flex items-center gap-1.5 text-purple-300 text-xs font-semibold">
                          <Building2 size={14} />
                          <span>Third-Party Vendor</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1.5 text-emerald-300 text-xs font-semibold">
                          <Shield size={14} />
                          <span>Internal Control</span>
                        </div>
                      )}
                    </TableCell>

                    <TableCell className="font-mono text-xs text-slate-200">
                      {dep.dependency_type === 'VENDOR' ? `Vendor #${dep.dependency_id}` : `Control #${dep.dependency_id}`}
                    </TableCell>

                    <TableCell className="text-xs text-slate-400">
                      {dep.notes || <span className="italic text-slate-600">No notes</span>}
                    </TableCell>

                    <TableCell className="text-xs font-mono text-slate-500">
                      {new Date(dep.created_at).toLocaleDateString()}
                    </TableCell>

                    <TableCell className="text-right">
                      {canManage && (
                        <Button
                          variant="danger"
                          size="sm"
                          onClick={() => removeDepMutation.mutate(dep.id)}
                          disabled={removeDepMutation.isPending}
                          className="text-xs py-1 px-2"
                        >
                          <Trash2 size={12} />
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </Card>

      {/* BIA Version History & Audit Trail */}
      <BiaHistoryCard
        processId={processId}
        bias={bias}
        onApproveClick={(b) => {
          setApprovingBia(b);
          setIsApprovalModalOpen(true);
        }}
        onEditClick={(b) => {
          setEditingBia(b);
          setIsBiaModalOpen(true);
        }}
        canManage={canManage}
        canApprove={canApprove}
      />

      {/* Modals */}
      <ProcessModal
        isOpen={isProcessModalOpen}
        onClose={() => setIsProcessModalOpen(false)}
        onSuccess={() => refetchProcess()}
        initialProcess={process}
      />

      <BiaModal
        isOpen={isBiaModalOpen}
        onClose={() => {
          setIsBiaModalOpen(false);
          setEditingBia(null);
        }}
        onSuccess={() => {
          refetchProcess();
          queryClient.invalidateQueries({ queryKey: ['resilience-process-bias', processId] });
        }}
        processId={processId}
        initialBia={editingBia}
      />

      {approvingBia && (
        <BiaApprovalModal
          isOpen={isApprovalModalOpen}
          onClose={() => {
            setIsApprovalModalOpen(false);
            setApprovingBia(null);
          }}
          onSuccess={() => {
            refetchProcess();
            queryClient.invalidateQueries({ queryKey: ['resilience-process-bias', processId] });
          }}
          bia={approvingBia}
        />
      )}

      <DependencyModal
        isOpen={isDependencyModalOpen}
        onClose={() => setIsDependencyModalOpen(false)}
        onSuccess={() => {
          refetchProcess();
          queryClient.invalidateQueries({ queryKey: ['resilience-dependencies', processId] });
        }}
        processId={processId}
      />
    </div>
  );
};
