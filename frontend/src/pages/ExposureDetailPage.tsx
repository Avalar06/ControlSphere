import React, { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../context/AuthContext';
import { exposureService } from '../lib/exposureService';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Table, TableBody, TableCell, TableHead, TableHeaderCell, TableRow } from '../components/ui/Table';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { ExposureModal } from '../components/exposure/ExposureModal';
import { ExposureStatusModal } from '../components/exposure/ExposureStatusModal';
import { ExposureAssetLinkModal } from '../components/exposure/ExposureAssetLinkModal';
import { ExposureExceptionModal } from '../components/exposure/ExposureExceptionModal';
import { BlastRadiusCard } from '../components/exposure/BlastRadiusCard';
import { ExposureLineageCard } from '../components/exposure/ExposureLineageCard';
import type {
  ExposureAssetLinkCreate,
  ExposureException,
  ExposureExceptionCreate,
  ExposureExceptionReviewRequest,
  ExposureSeverity,
  ExposureStatus,
  VulnerabilityExposureUpdate,
} from '../types';
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Clock,
  Edit2,
  Flame,
  Lock,
  Plus,
  RefreshCw,
  Target,
  Trash2,
  XCircle,
} from 'lucide-react';

export const ExposureDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const exposureId = parseInt(id || '0', 10);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { hasRole } = useAuth();

  const canManage = hasRole('ADMIN', 'MANAGER', 'SECURITY_ANALYST', 'GRC_ANALYST');
  const canApprove = hasRole('ADMIN', 'MANAGER');

  // Modals state
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isStatusModalOpen, setIsStatusModalOpen] = useState(false);
  const [isAssetLinkModalOpen, setIsAssetLinkModalOpen] = useState(false);
  const [isExceptionModalOpen, setIsExceptionModalOpen] = useState(false);
  const [exceptionModalMode, setExceptionModalMode] = useState<'request' | 'review'>('request');
  const [selectedExceptionForReview, setSelectedExceptionForReview] = useState<ExposureException | null>(null);

  // Queries
  const {
    data: exposure,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ['exposure-detail', exposureId],
    queryFn: () => exposureService.getExposure(exposureId),
    enabled: exposureId > 0,
  });

  const { data: assetLinks = [] } = useQuery({
    queryKey: ['exposure-assets', exposureId],
    queryFn: () => exposureService.listAssetLinks(exposureId),
    enabled: exposureId > 0,
  });

  const { data: exceptions = [] } = useQuery({
    queryKey: ['exposure-exceptions', exposureId],
    queryFn: () => exposureService.listExceptions({ exposure_id: exposureId }),
    enabled: exposureId > 0,
  });

  // Mutations
  const updateMutation = useMutation({
    mutationFn: (data: VulnerabilityExposureUpdate) => exposureService.updateExposure(exposureId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exposure-detail', exposureId] });
      queryClient.invalidateQueries({ queryKey: ['exposures-list'] });
    },
  });

  const statusMutation = useMutation({
    mutationFn: ({ status, notes }: { status: ExposureStatus; notes?: string }) =>
      exposureService.updateStatus(exposureId, { status, notes }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exposure-detail', exposureId] });
      queryClient.invalidateQueries({ queryKey: ['exposures-list'] });
    },
  });

  const linkAssetMutation = useMutation({
    mutationFn: (data: ExposureAssetLinkCreate) => exposureService.linkAsset(exposureId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exposure-detail', exposureId] });
      queryClient.invalidateQueries({ queryKey: ['exposure-assets', exposureId] });
      queryClient.invalidateQueries({ queryKey: ['exposures-list'] });
    },
  });

  const unlinkAssetMutation = useMutation({
    mutationFn: (linkId: number) => exposureService.unlinkAsset(linkId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exposure-detail', exposureId] });
      queryClient.invalidateQueries({ queryKey: ['exposure-assets', exposureId] });
      queryClient.invalidateQueries({ queryKey: ['exposures-list'] });
    },
  });

  const requestExceptionMutation = useMutation({
    mutationFn: (data: ExposureExceptionCreate) => exposureService.requestException(exposureId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exposure-detail', exposureId] });
      queryClient.invalidateQueries({ queryKey: ['exposure-exceptions', exposureId] });
      queryClient.invalidateQueries({ queryKey: ['exposures-list'] });
    },
  });

  const reviewExceptionMutation = useMutation({
    mutationFn: ({ exceptionId, data }: { exceptionId: number; data: ExposureExceptionReviewRequest }) =>
      exposureService.reviewException(exceptionId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exposure-detail', exposureId] });
      queryClient.invalidateQueries({ queryKey: ['exposure-exceptions', exposureId] });
      queryClient.invalidateQueries({ queryKey: ['exposures-list'] });
    },
  });

  const spawnRemediationMutation = useMutation({
    mutationFn: () => exposureService.spawnRemediation(exposureId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exposure-detail', exposureId] });
      queryClient.invalidateQueries({ queryKey: ['exposures-list'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => exposureService.deleteExposure(exposureId),
    onSuccess: () => {
      navigate('/exposure');
    },
  });

  if (isLoading) {
    return (
      <div className="py-20 flex justify-center">
        <LoadingSpinner text="Loading threat exposure telemetry..." />
      </div>
    );
  }

  if (isError || !exposure) {
    return (
      <div className="p-8 bg-rose-500/10 border border-rose-500/30 rounded-xl text-center space-y-3">
        <AlertTriangle className="h-10 w-10 text-rose-400 mx-auto" />
        <h2 className="text-base font-bold text-slate-100">Vulnerability Exposure Not Found</h2>
        <p className="text-xs text-slate-400">
          The requested exposure record does not exist or is not authorized under the current tenant organization.
        </p>
        <Button variant="outline" size="sm" onClick={() => navigate('/exposure')}>
          Return to Exposure Register
        </Button>
      </div>
    );
  }

  const isResolved = exposure.status === 'RESOLVED';

  // Base score preview computation
  const baseScorePreview = (exposure.cvss_score * 0.4) + (exposure.epss_score * 100 * 0.35) + (exposure.cisa_kev ? 25 : 0);
  const blastMultiplier = baseScorePreview > 0 ? Number((exposure.exposure_index / baseScorePreview).toFixed(2)) : 1.0;

  const getSeverityBadge = (sev: ExposureSeverity) => {
    switch (sev) {
      case 'CRITICAL':
        return <Badge variant="danger">CRITICAL</Badge>;
      case 'HIGH':
        return <Badge variant="warning">HIGH</Badge>;
      case 'MEDIUM':
        return <Badge variant="info">MEDIUM</Badge>;
      case 'LOW':
        return <Badge variant="default">LOW</Badge>;
      default:
        return <Badge variant="default">{sev}</Badge>;
    }
  };

  const getStatusBadge = (st: ExposureStatus) => {
    switch (st) {
      case 'OPEN':
        return <Badge variant="default">OPEN</Badge>;
      case 'UNDER_INVESTIGATION':
        return <Badge variant="info">INVESTIGATING</Badge>;
      case 'REMEDIATING':
        return <Badge variant="warning">REMEDIATING</Badge>;
      case 'EXCEPTION_REQUESTED':
        return <Badge variant="warning">EXCEPTION PENDING</Badge>;
      case 'EXCEPTION_APPROVED':
        return <Badge variant="info">EXCEPTION APPROVED</Badge>;
      case 'EXCEPTION_REJECTED':
        return <Badge variant="danger">EXCEPTION REJECTED</Badge>;
      case 'RESOLVED':
        return <Badge variant="success">RESOLVED (IMMUTABLE)</Badge>;
      default:
        return <Badge variant="default">{st}</Badge>;
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Back link */}
      <div>
        <button
          onClick={() => navigate('/exposure')}
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Threat Exposure Register
        </button>
      </div>

      {/* Resolved Immutability Notice */}
      {isResolved && (
        <div className="p-4 bg-emerald-950/30 border border-emerald-500/40 rounded-xl flex items-start gap-3 text-xs text-emerald-300">
          <Lock className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />
          <div>
            <h4 className="font-bold text-slate-100">RECORD RESOLVED & ARCHIVED (PERMANENTLY IMMUTABLE)</h4>
            <p className="text-emerald-300/80 mt-0.5">
              This vulnerability exposure has been verified as resolved. In accordance with enterprise GRC immutability standards, telemetry fields, status transitions, asset links, and exceptions are permanently locked.
            </p>
          </div>
        </div>
      )}

      {/* Header Banner */}
      <div className="p-6 bg-slate-900/60 border border-slate-800 rounded-xl space-y-4">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-xl font-bold text-indigo-400">{exposure.cve_id}</span>
              {exposure.cwe_id && (
                <span className="font-mono text-xs text-slate-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                  {exposure.cwe_id}
                </span>
              )}
              {getSeverityBadge(exposure.severity)}
              {getStatusBadge(exposure.status)}
              {exposure.cisa_kev && (
                <Badge variant="danger" className="flex items-center gap-1">
                  <Flame className="h-3.5 w-3.5" /> CISA KEV WEAPONIZED
                </Badge>
              )}
            </div>
            <h1 className="text-lg font-bold text-slate-100">{exposure.title}</h1>
            {exposure.description && (
              <p className="text-xs text-slate-300 max-w-3xl leading-relaxed">{exposure.description}</p>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => refetch()} className="flex items-center gap-1">
              <RefreshCw className="h-3.5 w-3.5" /> Refresh
            </Button>

            {canManage && !isResolved && (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsStatusModalOpen(true)}
                  className="flex items-center gap-1.5"
                >
                  <Activity className="h-3.5 w-3.5" />
                  Transition Status
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsEditModalOpen(true)}
                  className="flex items-center gap-1.5"
                >
                  <Edit2 className="h-3.5 w-3.5" />
                  Edit Telemetry
                </Button>

                {!exposure.remediation_plan_id && (
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => {
                      if (confirm('Spawn a Phase 11 Corrective Action Plan (CAPA) linked to this vulnerability?')) {
                        spawnRemediationMutation.mutate();
                      }
                    }}
                    disabled={spawnRemediationMutation.isPending}
                    className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-500"
                  >
                    <Target className="h-3.5 w-3.5" />
                    {spawnRemediationMutation.isPending ? 'Spawning...' : 'Spawn CAPA'}
                  </Button>
                )}

                <Button
                  variant="danger"
                  size="sm"
                  onClick={() => {
                    if (confirm(`Delete exposure ${exposure.cve_id}? This action cannot be undone.`)) {
                      deleteMutation.mutate();
                    }
                  }}
                  className="flex items-center gap-1"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </>
            )}
          </div>
        </div>

        {/* Remediation banner if linked */}
        {exposure.remediation_plan_id && (
          <div className="p-3 bg-emerald-950/20 border border-emerald-500/30 rounded-lg flex items-center justify-between text-xs">
            <div className="flex items-center gap-2 text-emerald-400">
              <Target className="h-4 w-4" />
              <span>
                Active Phase 11 Remediation Plan: <strong>Plan #{exposure.remediation_plan_id}</strong>
              </span>
            </div>
            <Link
              to={`/remediations/${exposure.remediation_plan_id}`}
              className="inline-flex items-center gap-1 text-xs font-bold text-emerald-400 hover:text-emerald-300 hover:underline"
            >
              Open CAPA Workspace
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        )}
      </div>

      {/* Telemetry & Mathematical Scoring Row (6 Cards) */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <Card className="p-4 bg-slate-900/60 border-slate-800 space-y-1">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">CVSS Base</span>
          <div className="text-2xl font-bold font-mono text-slate-100">{exposure.cvss_score.toFixed(1)}</div>
          <span className="text-[10px] text-slate-500">Weight: 40% (×0.40)</span>
        </Card>

        <Card className="p-4 bg-slate-900/60 border-slate-800 space-y-1">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">EPSS Probability</span>
          <div className="text-2xl font-bold font-mono text-indigo-400">
            {(exposure.epss_score * 100).toFixed(1)}%
          </div>
          <span className="text-[10px] text-slate-500">Weight: 35% (×0.35)</span>
        </Card>

        <Card className="p-4 bg-slate-900/60 border-slate-800 space-y-1">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1">
            <Flame className="h-3 w-3 text-rose-400" /> CISA KEV
          </span>
          <div className="text-2xl font-bold font-mono text-rose-400">
            {exposure.cisa_kev ? '+25.0' : '0.0'}
          </div>
          <span className="text-[10px] text-slate-500">Active Weaponization</span>
        </Card>

        <Card className="p-4 bg-slate-900/60 border-slate-800 space-y-1">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Base Score</span>
          <div className="text-2xl font-bold font-mono text-slate-200">
            {baseScorePreview.toFixed(2)}
          </div>
          <span className="text-[10px] text-slate-500">Pre-Multiplier</span>
        </Card>

        <Card className="p-4 bg-slate-900/60 border-slate-800 space-y-1">
          <span className="text-[11px] font-semibold text-indigo-400 uppercase tracking-wider">Blast Multiplier</span>
          <div className="text-2xl font-bold font-mono text-indigo-300">
            {blastMultiplier.toFixed(2)}×
          </div>
          <span className="text-[10px] text-slate-500">Phase 13 Criticality</span>
        </Card>

        <Card className="p-4 bg-slate-900/60 border-indigo-500/40 bg-indigo-950/20 space-y-1">
          <span className="text-[11px] font-semibold text-indigo-300 uppercase tracking-wider">Final Index</span>
          <div className="text-2xl font-bold font-mono text-rose-400">
            {exposure.exposure_index.toFixed(2)}
          </div>
          <span className="text-[10px] text-slate-400">Server-Authoritative / 100</span>
        </Card>
      </div>

      {/* SLA & Four-Eyes Exception Governance Card */}
      <Card className="p-6 space-y-6 bg-slate-900/60 border-slate-800">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Clock className="h-5 w-5 text-indigo-400" />
              <h3 className="text-base font-bold text-slate-100">
                Remediation SLA Governance & Exception Lifecycle
              </h3>
            </div>
            <p className="text-xs text-slate-400">
              Authoritative SLA calendar deadline derived from severity and CISA KEV status.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 text-xs">
              <span className="text-slate-400 mr-2">SLA Due Date:</span>
              <span className="font-mono font-bold text-slate-100">
                {new Date(exposure.remediation_sla_due).toLocaleDateString()} (
                {new Date(exposure.remediation_sla_due).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })})
              </span>
            </div>

            {canManage && !isResolved && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setExceptionModalMode('request');
                  setIsExceptionModalOpen(true);
                }}
                className="flex items-center gap-1.5"
              >
                <Plus className="h-4 w-4" />
                Request SLA Extension
              </Button>
            )}
          </div>
        </div>

        {/* Exception History Table */}
        <div className="space-y-3">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Four-Eyes SLA Deferral Exception Requests ({exceptions.length})
          </h4>

          {exceptions.length === 0 ? (
            <p className="text-xs text-slate-500 italic">
              No SLA extension exceptions requested for this vulnerability.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHead>
                  <TableRow>
                    <TableHeaderCell>ID</TableHeaderCell>
                    <TableHeaderCell>Requested By</TableHeaderCell>
                    <TableHeaderCell>Original SLA</TableHeaderCell>
                    <TableHeaderCell>Requested SLA</TableHeaderCell>
                    <TableHeaderCell>Justification & Mitigations</TableHeaderCell>
                    <TableHeaderCell>Decision</TableHeaderCell>
                    <TableHeaderCell className="text-right">Actions</TableHeaderCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {exceptions.map((exc) => {
                    const isPending = exc.status === 'PENDING';
                    return (
                      <TableRow key={exc.id}>
                        <TableCell className="font-mono text-xs font-bold text-slate-300">
                          #{exc.id}
                        </TableCell>
                        <TableCell className="text-xs text-slate-300">
                          {exc.requested_by?.full_name || `User #${exc.requested_by_id}`}
                        </TableCell>
                        <TableCell className="text-xs text-slate-400 font-mono">
                          {new Date(exc.original_sla_due).toLocaleDateString()}
                        </TableCell>
                        <TableCell className="text-xs font-bold text-indigo-400 font-mono">
                          {new Date(exc.requested_sla_due).toLocaleDateString()}
                        </TableCell>
                        <TableCell className="text-xs text-slate-300 max-w-xs">
                          <p className="line-clamp-2">{exc.justification}</p>
                          {exc.compensating_controls && (
                            <p className="text-[11px] text-emerald-400 line-clamp-1 mt-0.5">
                              Mitigation: {exc.compensating_controls}
                            </p>
                          )}
                        </TableCell>
                        <TableCell>
                          {exc.status === 'APPROVED' ? (
                            <Badge variant="success" className="flex items-center gap-1 w-fit">
                              <CheckCircle2 className="h-3 w-3" /> APPROVED
                            </Badge>
                          ) : exc.status === 'REJECTED' ? (
                            <Badge variant="danger" className="flex items-center gap-1 w-fit">
                              <XCircle className="h-3 w-3" /> REJECTED
                            </Badge>
                          ) : (
                            <Badge variant="warning" className="flex items-center gap-1 w-fit">
                              <Clock className="h-3 w-3" /> PENDING REVIEW
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          {isPending && canApprove && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                setSelectedExceptionForReview(exc);
                                setExceptionModalMode('review');
                                setIsExceptionModalOpen(true);
                              }}
                              className="text-xs"
                            >
                              Review Request
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      </Card>

      {/* Blast Radius Card */}
      <BlastRadiusCard
        exposure={exposure}
        assetLinks={assetLinks}
        onOpenLinkModal={() => setIsAssetLinkModalOpen(true)}
        onUnlinkAsset={(linkId) => unlinkAssetMutation.mutate(linkId)}
        canManage={canManage}
        isResolved={isResolved}
      />

      {/* Lineage Card */}
      <ExposureLineageCard exposure={exposure} />

      {/* Modals */}
      <ExposureModal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        initialData={exposure}
        onSubmit={async (data) => {
          await updateMutation.mutateAsync(data as VulnerabilityExposureUpdate);
        }}
        isSubmitting={updateMutation.isPending}
      />

      <ExposureStatusModal
        isOpen={isStatusModalOpen}
        onClose={() => setIsStatusModalOpen(false)}
        exposure={exposure}
        onSubmit={async (st, notes) => {
          await statusMutation.mutateAsync({ status: st, notes });
        }}
        isSubmitting={statusMutation.isPending}
      />

      <ExposureAssetLinkModal
        isOpen={isAssetLinkModalOpen}
        onClose={() => setIsAssetLinkModalOpen(false)}
        exposure={exposure}
        onSubmit={async (data) => {
          await linkAssetMutation.mutateAsync(data);
        }}
        isSubmitting={linkAssetMutation.isPending}
      />

      <ExposureExceptionModal
        isOpen={isExceptionModalOpen}
        onClose={() => {
          setIsExceptionModalOpen(false);
          setSelectedExceptionForReview(null);
        }}
        exposure={exposure}
        mode={exceptionModalMode}
        exceptionToReview={selectedExceptionForReview}
        onRequestSubmit={async (data) => {
          await requestExceptionMutation.mutateAsync(data);
        }}
        onReviewSubmit={async (exceptionId, data) => {
          await reviewExceptionMutation.mutateAsync({ exceptionId, data });
        }}
        isSubmitting={requestExceptionMutation.isPending || reviewExceptionMutation.isPending}
      />
    </div>
  );
};
