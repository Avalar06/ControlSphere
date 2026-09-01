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
import { PrivacyRiskCard } from '../components/privacy/PrivacyRiskCard';
import { PrivacyLineageCard } from '../components/privacy/PrivacyLineageCard';
import { PrivacyLifecycleModal } from '../components/privacy/PrivacyLifecycleModal';
import { PrivacyApprovalModal } from '../components/privacy/PrivacyApprovalModal';
import { ProcessingActivityModal } from '../components/privacy/ProcessingActivityModal';
import { DPIAModal } from '../components/privacy/DPIAModal';
import { DataTransferModal } from '../components/privacy/DataTransferModal';
import type {
  DataTransferAssessment,
  DPIAAssessment,
  PrivacyApprovalStatus,
} from '../types';
import {
  Activity,
  ArrowLeft,
  Edit2,
  FileText,
  Globe,
  Layers,
  Lock,
  Plus,
  Scale,
  ShieldAlert,
  ShieldCheck,
  Trash2,
} from 'lucide-react';

type TabKey = 'overview' | 'dpia' | 'transfers' | 'lineage';

export const PrivacyProcessingDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const activityId = Number(id);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { hasRole } = useAuth();

  const canManage = hasRole('ADMIN', 'MANAGER', 'GRC_ANALYST');
  const canAssess = hasRole('ADMIN', 'MANAGER', 'GRC_ANALYST', 'SECURITY_ANALYST');
  const canApprove = hasRole('ADMIN', 'MANAGER');

  const [activeTab, setActiveTab] = useState<TabKey>('overview');

  // Modals state
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isLifecycleModalOpen, setIsLifecycleModalOpen] = useState(false);
  const [isDPIAModalOpen, setIsDPIAModalOpen] = useState(false);
  const [editingDPIA, setEditingDPIA] = useState<DPIAAssessment | null>(null);
  const [isTransferModalOpen, setIsTransferModalOpen] = useState(false);
  const [editingTransfer, setEditingTransfer] = useState<DataTransferAssessment | null>(null);

  // Approval review modal
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
  const {
    data: activity,
    isLoading: isActivityLoading,
    isError,
  } = useQuery({
    queryKey: ['privacy-activity-detail', activityId],
    queryFn: () => privacyService.getProcessingActivity(activityId),
    enabled: !isNaN(activityId),
  });

  const { data: dpias = [], isLoading: isDPIAsLoading } = useQuery({
    queryKey: ['privacy-dpias-for-activity', activityId],
    queryFn: () => privacyService.listDPIAs({ activity_id: activityId }),
    enabled: !isNaN(activityId),
  });

  const { data: transfers = [], isLoading: isTransfersLoading } = useQuery({
    queryKey: ['privacy-transfers-for-activity', activityId],
    queryFn: () => privacyService.listDataTransfers({ activity_id: activityId }),
    enabled: !isNaN(activityId),
  });

  const deleteMutation = useMutation({
    mutationFn: () => privacyService.deleteProcessingActivity(activityId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['privacy-activities'] });
      navigate('/privacy');
    },
  });

  if (isActivityLoading) {
    return (
      <div className="p-12 flex justify-center">
        <LoadingSpinner />
      </div>
    );
  }

  if (isError || !activity) {
    return (
      <div className="p-8 text-center space-y-3">
        <div className="text-rose-400 font-medium text-sm">Processing Activity Not Found</div>
        <p className="text-xs text-slate-500">
          The requested RoPA record does not exist or you do not have permission to view it.
        </p>
        <Button variant="outline" size="sm" onClick={() => navigate('/privacy')}>
          Back to Privacy Workspace
        </Button>
      </div>
    );
  }

  const isRetired = activity.lifecycle_state === 'RETIRED';
  const latestDPIA = dpias.length > 0 ? dpias[0] : undefined;

  return (
    <div className="space-y-6 pb-12">
      {/* Top Breadcrumb & Nav */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/privacy')}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
        >
          <ArrowLeft size={14} />
          <span>Back to RoPA Register</span>
        </button>
        <div className="text-xs text-slate-500 font-mono">
          Last updated: {new Date(activity.updated_at).toLocaleString()}
        </div>
      </div>

      {/* Main Header Banner */}
      <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono text-sm font-bold text-indigo-400 px-2 py-0.5 rounded bg-indigo-950/60 border border-indigo-800/60">
                {activity.activity_code}
              </span>
              <Badge
                variant={
                  activity.lifecycle_state === 'ACTIVE'
                    ? 'success'
                    : activity.lifecycle_state === 'RETIRED'
                    ? 'danger'
                    : activity.lifecycle_state === 'DPO_REVIEW'
                    ? 'warning'
                    : 'default'
                }
              >
                {activity.lifecycle_state}
              </Badge>
              <Badge
                variant={
                  activity.dpo_approval_status === 'APPROVED'
                    ? 'success'
                    : activity.dpo_approval_status === 'REJECTED'
                    ? 'danger'
                    : 'warning'
                }
              >
                DPO: {activity.dpo_approval_status}
              </Badge>
              <Badge variant="default">{activity.legal_basis}</Badge>
            </div>
            <h1 className="text-xl font-bold text-slate-100 mt-2">{activity.name}</h1>
            <p className="text-xs text-slate-400 mt-1 max-w-3xl">
              {activity.purpose_description}
            </p>
          </div>

          {/* Action Bar */}
          <div className="flex items-center gap-2 flex-wrap">
            {canManage && !isRetired && (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsEditModalOpen(true)}
                  className="flex items-center gap-1.5"
                >
                  <Edit2 size={13} />
                  <span>Edit RoPA</span>
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsLifecycleModalOpen(true)}
                  className="flex items-center gap-1.5"
                >
                  <Activity size={13} />
                  <span>Transition State</span>
                </Button>
              </>
            )}

            {canAssess && !isRetired && (
              <>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => {
                    setEditingDPIA(null);
                    setIsDPIAModalOpen(true);
                  }}
                  className="flex items-center gap-1.5"
                >
                  <ShieldAlert size={13} />
                  <span>Conduct DPIA</span>
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setEditingTransfer(null);
                    setIsTransferModalOpen(true);
                  }}
                  className="flex items-center gap-1.5"
                >
                  <Globe size={13} />
                  <span>Assess Transfer</span>
                </Button>
              </>
            )}

            {canManage && activity.lifecycle_state !== 'ACTIVE' && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  if (confirm(`Permanently delete activity ${activity.activity_code}?`)) {
                    deleteMutation.mutate();
                  }
                }}
                className="text-rose-400 hover:text-rose-300"
              >
                <Trash2 size={14} />
              </Button>
            )}
          </div>
        </div>

        {/* Immutability Alert */}
        {isRetired && (
          <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-800/60 flex items-start gap-2.5">
            <Lock size={16} className="text-rose-400 shrink-0 mt-0.5" />
            <div className="text-xs text-rose-300">
              <strong>Governance Immutability Lock:</strong> This processing activity has been permanently RETIRED. Under Article 30 auditability standards, retired records are read-only and cannot be mutated or transitioned.
            </div>
          </div>
        )}
      </div>

      {/* Authoritative Risk Telemetry Card */}
      {latestDPIA && (
        <PrivacyRiskCard
          inherentRiskScore={latestDPIA.inherent_risk_score}
          residualRiskScore={latestDPIA.residual_risk_score}
          riskBand={latestDPIA.risk_band}
          priorConsultationRequired={latestDPIA.prior_consultation_required}
          title={`Latest DPIA Telemetry (${latestDPIA.assessment_code})`}
        />
      )}

      {/* Tabs */}
      <div className="border-b border-slate-800 flex items-center gap-2">
        <button
          onClick={() => setActiveTab('overview')}
          className={`px-4 py-2 text-xs font-medium border-b-2 transition-colors cursor-pointer flex items-center gap-2 ${
            activeTab === 'overview'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <FileText size={14} />
          <span>Article 30 Overview</span>
        </button>
        <button
          onClick={() => setActiveTab('dpia')}
          className={`px-4 py-2 text-xs font-medium border-b-2 transition-colors cursor-pointer flex items-center gap-2 ${
            activeTab === 'dpia'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <ShieldAlert size={14} />
          <span>DPIA Assessments ({dpias.length})</span>
        </button>
        <button
          onClick={() => setActiveTab('transfers')}
          className={`px-4 py-2 text-xs font-medium border-b-2 transition-colors cursor-pointer flex items-center gap-2 ${
            activeTab === 'transfers'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Globe size={14} />
          <span>Cross-Border Transfers ({transfers.length})</span>
        </button>
        <button
          onClick={() => setActiveTab('lineage')}
          className={`px-4 py-2 text-xs font-medium border-b-2 transition-colors cursor-pointer flex items-center gap-2 ${
            activeTab === 'lineage'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Layers size={14} />
          <span>GRC Lineage</span>
        </button>
      </div>

      {/* ─── TAB 1: OVERVIEW ─────────────────────────────────────────────────── */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="p-5 bg-slate-900 border-slate-800 space-y-4">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2 pb-2 border-b border-slate-800">
              <Scale size={16} className="text-indigo-400" />
              Data Subject &amp; Categories Specification
            </h3>
            <div className="space-y-3 text-xs">
              <div>
                <div className="text-slate-500 font-medium">Data Subject Categories</div>
                <div className="text-slate-200 font-mono mt-0.5">
                  {activity.data_subject_categories}
                </div>
              </div>
              <div>
                <div className="text-slate-500 font-medium">Personal Data Categories</div>
                <div className="text-slate-200 font-mono mt-0.5">
                  {activity.personal_data_categories}
                </div>
              </div>
              <div>
                <div className="text-slate-500 font-medium">Data Controller Entity</div>
                <div className="text-slate-200 mt-0.5">
                  {activity.data_controller_name || 'Standard Organizational Controller'}
                </div>
              </div>
              <div>
                <div className="text-slate-500 font-medium">Security &amp; Encryption Measures</div>
                <div className="text-slate-300 mt-0.5 bg-slate-950 p-2.5 rounded border border-slate-800">
                  {activity.security_measures_summary || 'Standard controls and RBAC baseline enforced.'}
                </div>
              </div>
            </div>
          </Card>

          <Card className="p-5 bg-slate-900 border-slate-800 space-y-4">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2 pb-2 border-b border-slate-800">
              <ShieldCheck size={16} className="text-emerald-400" />
              Regulatory Checkpoints &amp; Triggers
            </h3>
            <div className="space-y-2.5 text-xs">
              <div className="flex items-center justify-between p-2 rounded bg-slate-950 border border-slate-800">
                <span className="text-slate-300">Article 9 Special Category Data</span>
                <Badge variant={activity.is_special_category_data ? 'danger' : 'default'}>
                  {activity.is_special_category_data ? 'YES' : 'NO'}
                </Badge>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-slate-950 border border-slate-800">
                <span className="text-slate-300">Article 22 Automated Decision / Profiling</span>
                <Badge variant={activity.is_automated_decision_making ? 'warning' : 'default'}>
                  {activity.is_automated_decision_making ? 'YES' : 'NO'}
                </Badge>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-slate-950 border border-slate-800">
                <span className="text-slate-300">Large-Scale Systematic Monitoring</span>
                <Badge variant={activity.is_large_scale_monitoring ? 'warning' : 'default'}>
                  {activity.is_large_scale_monitoring ? 'YES' : 'NO'}
                </Badge>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-slate-950 border border-slate-800">
                <span className="text-slate-300">Vulnerable Data Subjects</span>
                <Badge variant={activity.is_vulnerable_subjects ? 'warning' : 'default'}>
                  {activity.is_vulnerable_subjects ? 'YES' : 'NO'}
                </Badge>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-slate-950 border border-slate-800">
                <span className="text-slate-300">Chapter V International Transfer</span>
                <Badge variant={activity.is_cross_border_transfer ? 'info' : 'default'}>
                  {activity.is_cross_border_transfer ? 'YES' : 'NO'}
                </Badge>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* ─── TAB 2: DPIA ASSESSMENTS ─────────────────────────────────────────── */}
      {activeTab === 'dpia' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-sm font-semibold text-slate-200">
              Data Protection Impact Assessments (DPIA)
            </h3>
            {canAssess && !isRetired && (
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  setEditingDPIA(null);
                  setIsDPIAModalOpen(true);
                }}
                className="flex items-center gap-1.5"
              >
                <Plus size={13} />
                <span>New DPIA</span>
              </Button>
            )}
          </div>

          <Card className="overflow-hidden border-slate-800">
            {isDPIAsLoading ? (
              <div className="p-8 flex justify-center">
                <LoadingSpinner />
              </div>
            ) : dpias.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-500">
                No DPIA assessments recorded for this processing activity.
              </div>
            ) : (
              <Table>
                <TableHead>
                  <TableRow>
                    <TableHeaderCell>ASSESSMENT CODE</TableHeaderCell>
                    <TableHeaderCell>INHERENT RISK (IRS)</TableHeaderCell>
                    <TableHeaderCell>RESIDUAL RISK (RRS)</TableHeaderCell>
                    <TableHeaderCell>RISK BAND</TableHeaderCell>
                    <TableHeaderCell>DPO CONSULTATION</TableHeaderCell>
                    <TableHeaderCell>CREATED BY</TableHeaderCell>
                    <TableHeaderCell className="text-right">ACTIONS</TableHeaderCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {dpias.map((d) => (
                    <TableRow key={d.id}>
                      <TableCell className="font-mono text-xs font-bold text-indigo-400">
                        {d.assessment_code}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-amber-400 font-bold">
                        {d.inherent_risk_score.toFixed(1)} / 100
                      </TableCell>
                      <TableCell className="font-mono text-xs text-indigo-400 font-bold">
                        {d.residual_risk_score.toFixed(1)} / 100
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            d.risk_band === 'LOW'
                              ? 'success'
                              : d.risk_band === 'MODERATE'
                              ? 'info'
                              : d.risk_band === 'HIGH'
                              ? 'warning'
                              : 'danger'
                          }
                        >
                          {d.risk_band}
                        </Badge>
                      </TableCell>
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
                      <TableCell className="text-xs text-slate-400">
                        User #{d.created_by_id}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {canAssess && !isRetired && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setEditingDPIA(d);
                                setIsDPIAModalOpen(true);
                              }}
                              title="Edit DPIA"
                            >
                              <Edit2 size={13} />
                            </Button>
                          )}
                          {canApprove && !isRetired && (
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
                              <span>DPO Review</span>
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

      {/* ─── TAB 3: CROSS-BORDER TRANSFERS ──────────────────────────────────── */}
      {activeTab === 'transfers' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-sm font-semibold text-slate-200">
              Cross-Border Transfer Impact Assessments (TIA)
            </h3>
            {canAssess && !isRetired && (
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  setEditingTransfer(null);
                  setIsTransferModalOpen(true);
                }}
                className="flex items-center gap-1.5"
              >
                <Plus size={13} />
                <span>New Transfer</span>
              </Button>
            )}
          </div>

          <Card className="overflow-hidden border-slate-800">
            {isTransfersLoading ? (
              <div className="p-8 flex justify-center">
                <LoadingSpinner />
              </div>
            ) : transfers.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-500">
                No cross-border transfers linked to this processing activity.
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
                    <TableHeaderCell>APPROVAL STATUS</TableHeaderCell>
                    <TableHeaderCell className="text-right">ACTIONS</TableHeaderCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {transfers.map((t) => (
                    <TableRow key={t.id}>
                      <TableCell className="font-mono text-xs font-bold text-indigo-400">
                        {t.transfer_code}
                      </TableCell>
                      <TableCell className="text-xs text-slate-200 font-medium">
                        {t.destination_country}
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
                        {canApprove && !isRetired && (
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
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </Card>
        </div>
      )}

      {/* ─── TAB 4: GRC LINEAGE ─────────────────────────────────────────────── */}
      {activeTab === 'lineage' && (
        <PrivacyLineageCard
          businessProcessId={activity.business_process_id}
          aiSystemId={activity.ai_system_id}
          vendorId={activity.vendor_id}
          remediationPlanId={latestDPIA?.remediation_plan_id}
        />
      )}

      {/* ─── MODALS ─────────────────────────────────────────────────────────── */}
      <ProcessingActivityModal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        activity={activity}
        onSuccess={() => {
          queryClient.invalidateQueries({ queryKey: ['privacy-activity-detail', activityId] });
        }}
      />

      <PrivacyLifecycleModal
        isOpen={isLifecycleModalOpen}
        onClose={() => setIsLifecycleModalOpen(false)}
        activity={activity}
        onSuccess={() => {
          queryClient.invalidateQueries({ queryKey: ['privacy-activity-detail', activityId] });
        }}
      />

      <DPIAModal
        isOpen={isDPIAModalOpen}
        onClose={() => setIsDPIAModalOpen(false)}
        dpia={editingDPIA}
        processingActivityId={activityId}
        onSuccess={() => {
          queryClient.invalidateQueries({ queryKey: ['privacy-dpias-for-activity', activityId] });
        }}
      />

      <DataTransferModal
        isOpen={isTransferModalOpen}
        onClose={() => setIsTransferModalOpen(false)}
        transfer={editingTransfer}
        processingActivityId={activityId}
        onSuccess={() => {
          queryClient.invalidateQueries({ queryKey: ['privacy-transfers-for-activity', activityId] });
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
          queryClient.invalidateQueries({ queryKey: ['privacy-dpias-for-activity', activityId] });
          queryClient.invalidateQueries({ queryKey: ['privacy-transfers-for-activity', activityId] });
          queryClient.invalidateQueries({ queryKey: ['privacy-activity-detail', activityId] });
        }}
      />
    </div>
  );
};
