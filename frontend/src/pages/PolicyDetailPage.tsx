import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft,
  CheckCircle,
  History,
  Shield,
  Plus,
  Trash2,
  AlertCircle,
  FileCheck2,
  Send,
  Archive,
  Lock,
  GitCompare,
  UserCheck,
  AlertTriangle,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../lib/api';
import type {
  FrameworkSubcategory,
  Policy,
  PolicyStatus,
  PolicyVersionStatus,
  PolicyReviewStage,
  PolicyReviewStatus,
} from '../types';
import { Card, CardHeader } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';

export const PolicyDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user, hasPermission } = useAuth();
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [selectedVersionNum, setSelectedVersionNum] = useState<number | null>(null);
  const [allSubcategories, setAllSubcategories] = useState<FrameworkSubcategory[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // New Version Modal
  const [isVersionModalOpen, setIsVersionModalOpen] = useState(false);
  const [newVersionContent, setNewVersionContent] = useState('');
  const [newVersionSummary, setNewVersionSummary] = useState('');
  const [isSubmittingVersion, setIsSubmittingVersion] = useState(false);

  // Submit for Review Modal
  const [isSubmitReviewModalOpen, setIsSubmitReviewModalOpen] = useState(false);
  const [reviewStage, setReviewStage] = useState<PolicyReviewStage>('SECURITY_REVIEW');
  const [submitReviewNotes, setSubmitReviewNotes] = useState('');
  const [isSubmittingReview, setIsSubmittingReview] = useState(false);

  // Review / Decision Modal (Four-Eyes Approval)
  const [isReviewActionModalOpen, setIsReviewActionModalOpen] = useState(false);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<number | null>(null);
  const [reviewDecision, setReviewDecision] = useState<'APPROVE' | 'REJECT' | 'REQUEST_CHANGES'>('APPROVE');
  const [reviewActionNotes, setReviewActionNotes] = useState('');
  const [isSubmittingReviewAction, setIsSubmittingReviewAction] = useState(false);

  // Version Publishing state
  const [isPublishingVersion, setIsPublishingVersion] = useState(false);

  // Diff Mode state
  const [isDiffMode, setIsDiffMode] = useState(false);

  // Add Control Mapping Modal
  const [isMappingModalOpen, setIsMappingModalOpen] = useState(false);
  const [selectedSubcatId, setSelectedSubcatId] = useState<string>('');
  const [isSubmittingMapping, setIsSubmittingMapping] = useState(false);

  const fetchPolicy = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const { data } = await api.get<Policy>(`/api/v1/policies/${id}`);
      setPolicy(data);
      if (data.current_version) {
        setSelectedVersionNum(data.current_version.version_number);
        setNewVersionContent(data.current_version.content);
      }

      // Fetch controls subcategories for mapping dropdown
      const { data: ctrlList } = await api.get<any[]>('/api/v1/controls');
      const subcats = ctrlList.map((c) => c.subcategory).filter(Boolean);
      setAllSubcategories(subcats);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to load policy.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchPolicy();
  }, [id]);

  const handleStatusTransition = async (newStatus: PolicyStatus, reason?: string) => {
    if (!policy) return;
    setStatusMessage(null);
    try {
      const { data: updated } = await api.post<Policy>(`/api/v1/policies/${policy.id}/status`, {
        status: newStatus,
        reason: reason || `Status transitioned to ${newStatus}`,
      });
      setPolicy(updated);
      setStatusMessage(`Policy status updated to ${newStatus}.`);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to transition policy status.');
    }
  };

  const handleCreateVersion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!policy) return;
    setIsSubmittingVersion(true);
    setError(null);
    try {
      await api.post(`/api/v1/policies/${policy.id}/versions`, {
        content: newVersionContent,
        change_summary: newVersionSummary,
      });
      setIsVersionModalOpen(false);
      setNewVersionSummary('');
      await fetchPolicy();
      setStatusMessage('New immutable policy version created in DRAFT status.');
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to create version.');
    } finally {
      setIsSubmittingVersion(false);
    }
  };

  const handleSubmitForReview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!policy || !currentDisplayVersion) return;
    setIsSubmittingReview(true);
    setError(null);
    try {
      await api.post(`/api/v1/policies/${policy.id}/versions/${currentDisplayVersion.id}/submit-review`, {
        review_stage: reviewStage,
        review_notes: submitReviewNotes,
      });
      setIsSubmitReviewModalOpen(false);
      setSubmitReviewNotes('');
      await fetchPolicy();
      setStatusMessage(`Version v${currentDisplayVersion.version_number} submitted for ${reviewStage.replace('_', ' ')}.`);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to submit version for review.');
    } finally {
      setIsSubmittingReview(false);
    }
  };

  const handleReviewDecision = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!policy || !currentDisplayVersion || !selectedWorkflowId) return;
    setIsSubmittingReviewAction(true);
    setError(null);
    try {
      await api.post(
        `/api/v1/policies/${policy.id}/versions/${currentDisplayVersion.id}/review/${selectedWorkflowId}`,
        {
          decision: reviewDecision,
          review_notes: reviewActionNotes,
        }
      );
      setIsReviewActionModalOpen(false);
      setReviewActionNotes('');
      setSelectedWorkflowId(null);
      await fetchPolicy();
      setStatusMessage(`Review workflow decision recorded: ${reviewDecision}.`);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to record review decision.');
    } finally {
      setIsSubmittingReviewAction(false);
    }
  };

  const handlePublishVersion = async (versionId: number) => {
    if (!policy) return;
    setIsPublishingVersion(true);
    setError(null);
    try {
      await api.post(`/api/v1/policies/${policy.id}/versions/${versionId}/publish`);
      await fetchPolicy();
      setStatusMessage(`Policy version published successfully. Previous active versions superseded.`);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to publish policy version.');
    } finally {
      setIsPublishingVersion(false);
    }
  };

  const handleAddMapping = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!policy || !selectedSubcatId) return;
    setIsSubmittingMapping(true);
    try {
      const { data: updated } = await api.post<Policy>(`/api/v1/policies/${policy.id}/mappings`, {
        subcategory_id: parseInt(selectedSubcatId, 10),
      });
      setPolicy(updated);
      setIsMappingModalOpen(false);
      setSelectedSubcatId('');
      setStatusMessage('Control mapping established.');
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to map control.');
    } finally {
      setIsSubmittingMapping(false);
    }
  };

  const handleRemoveMapping = async (subcatId: number) => {
    if (!policy) return;
    try {
      const { data: updated } = await api.delete<Policy>(
        `/api/v1/policies/${policy.id}/mappings/${subcatId}`
      );
      setPolicy(updated);
      setStatusMessage('Control mapping removed.');
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to remove control mapping.');
    }
  };

  if (isLoading) {
    return <LoadingSpinner text="Loading policy document & versions..." />;
  }

  if (!policy) {
    return (
      <div className="p-8 text-center text-slate-400">
        <p>Policy not found.</p>
        <Link to="/policies" className="text-indigo-400 text-xs underline mt-2 block">
          Back to Policies
        </Link>
      </div>
    );
  }

  const currentDisplayVersion =
    policy.versions?.find((v) => v.version_number === selectedVersionNum) ||
    policy.current_version;

  const previousVersion = policy.versions?.find(
    (v) => v.version_number === (currentDisplayVersion?.version_number || 1) - 1
  );

  const pendingWorkflow = currentDisplayVersion?.reviews?.find(
    (r) => r.status === 'PENDING'
  );

  const isCreatorOfCurrentVersion =
    user?.id !== undefined &&
    currentDisplayVersion?.created_by_id !== undefined &&
    user.id === currentDisplayVersion.created_by_id;

  const getStatusBadge = (status: PolicyStatus) => {
    switch (status) {
      case 'PUBLISHED':
        return <Badge variant="success">PUBLISHED</Badge>;
      case 'APPROVED':
        return <Badge variant="purple">APPROVED</Badge>;
      case 'UNDER_REVIEW':
        return <Badge variant="warning">UNDER REVIEW</Badge>;
      case 'ARCHIVED':
        return <Badge variant="default">ARCHIVED</Badge>;
      case 'DRAFT':
      default:
        return <Badge variant="info">DRAFT</Badge>;
    }
  };

  const getVersionStatusBadge = (status?: PolicyVersionStatus) => {
    switch (status) {
      case 'PUBLISHED':
        return <Badge variant="success">PUBLISHED</Badge>;
      case 'APPROVED':
        return <Badge variant="purple">APPROVED</Badge>;
      case 'UNDER_REVIEW':
        return <Badge variant="warning">UNDER REVIEW</Badge>;
      case 'SUPERSEDED':
        return <Badge variant="default">SUPERSEDED</Badge>;
      case 'ARCHIVED':
        return <Badge variant="default">ARCHIVED</Badge>;
      case 'DRAFT':
      default:
        return <Badge variant="info">DRAFT</Badge>;
    }
  };

  const getReviewStatusBadge = (status: PolicyReviewStatus) => {
    switch (status) {
      case 'APPROVED':
        return <Badge variant="success">APPROVED</Badge>;
      case 'REJECTED':
        return <Badge variant="danger">REJECTED</Badge>;
      case 'CHANGES_REQUESTED':
        return <Badge variant="warning">CHANGES REQUESTED</Badge>;
      case 'PENDING':
      default:
        return <Badge variant="info">PENDING</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Back Link & Header */}
      <div>
        <Link
          to="/policies"
          className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-slate-200 transition-colors mb-3"
        >
          <ArrowLeft size={13} />
          <span>Back to Policies Repository</span>
        </Link>

        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-xl font-bold text-slate-100">{policy.title}</h1>
              {getStatusBadge(policy.status)}
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-300">
                {policy.policy_type.replace('_', ' ')}
              </span>
            </div>
            {policy.description && (
              <p className="text-xs text-slate-400 mt-1 max-w-3xl">{policy.description}</p>
            )}
          </div>

          {/* Top Level Policy Actions */}
          <div className="flex items-center gap-2 flex-wrap">
            {hasPermission('policy:manage') && policy.status !== 'ARCHIVED' && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleStatusTransition('ARCHIVED')}
              >
                <Archive size={13} />
                Archive Policy
              </Button>
            )}

            {hasPermission('policy:manage') && (
              <Button
                size="sm"
                variant="secondary"
                onClick={() => {
                  setNewVersionContent(currentDisplayVersion?.content || '');
                  setIsVersionModalOpen(true);
                }}
              >
                <Plus size={13} />
                New Version
              </Button>
            )}
          </div>
        </div>
      </div>

      {statusMessage && (
        <div className="p-3 rounded bg-emerald-950/60 border border-emerald-800 text-emerald-300 text-xs flex items-center gap-2">
          <FileCheck2 size={15} />
          <span>{statusMessage}</span>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-lg bg-rose-950/60 border border-rose-800/70 text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle size={16} className="shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Main Grid: Document Viewer + Sidebar Meta */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Document Viewer (2 Cols) */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            {/* Version Bar */}
            <div className="p-4 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-2 flex-wrap">
                <History size={14} className="text-indigo-400" />
                <span className="text-xs font-semibold text-slate-200">
                  Version v{currentDisplayVersion?.version_number || 1}
                </span>
                {getVersionStatusBadge(currentDisplayVersion?.status)}
                {currentDisplayVersion?.content_hash_sha256 && (
                  <span
                    className="inline-flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-emerald-400"
                    title={`Cryptographic SHA-256 Hash: ${currentDisplayVersion.content_hash_sha256}`}
                  >
                    <Lock size={10} />
                    SHA256:{currentDisplayVersion.content_hash_sha256.substring(0, 10)}...
                  </span>
                )}
              </div>

              <div className="flex items-center gap-2 flex-wrap">
                {/* Diff Toggle */}
                {previousVersion && (
                  <Button
                    size="xs"
                    variant={isDiffMode ? 'primary' : 'outline'}
                    onClick={() => setIsDiffMode(!isDiffMode)}
                  >
                    <GitCompare size={12} />
                    {isDiffMode ? 'Standard View' : 'Compare Diff'}
                  </Button>
                )}

                {/* Version Selector Dropdown */}
                {policy.versions && policy.versions.length > 1 && (
                  <select
                    value={selectedVersionNum || policy.current_version?.version_number}
                    onChange={(e) => {
                      setSelectedVersionNum(parseInt(e.target.value, 10));
                      setIsDiffMode(false);
                    }}
                    className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-xs text-slate-300 focus:outline-none focus:border-indigo-500 font-mono"
                  >
                    {policy.versions.map((v) => (
                      <option key={v.id} value={v.version_number}>
                        v{v.version_number} ({v.status}) — {new Date(v.created_at).toLocaleDateString()}
                      </option>
                    ))}
                  </select>
                )}
              </div>
            </div>

            {/* Version Governance Action Bar */}
            {currentDisplayVersion && (
              <div className="px-4 py-3 bg-slate-900/50 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs">
                <div className="text-slate-400">
                  <span>Revision: </span>
                  <span className="text-slate-200">{currentDisplayVersion.change_summary || 'Baseline version'}</span>
                  {currentDisplayVersion.created_by && (
                    <span className="ml-2 text-slate-500">
                      by {currentDisplayVersion.created_by.full_name}
                    </span>
                  )}
                  {currentDisplayVersion.approved_by && (
                    <span className="ml-2 text-purple-400">
                      · Approved by {currentDisplayVersion.approved_by.full_name}
                    </span>
                  )}
                </div>

                {/* Action Buttons based on Version Lifecycle */}
                <div className="flex items-center gap-2 flex-wrap">
                  {/* Submit DRAFT for Review */}
                  {currentDisplayVersion.status === 'DRAFT' && hasPermission('policy:manage') && (
                    <Button
                      size="xs"
                      variant="warning"
                      onClick={() => setIsSubmitReviewModalOpen(true)}
                    >
                      <Send size={12} />
                      Submit for Formal Review
                    </Button>
                  )}

                  {/* Four-Eyes Review Action */}
                  {currentDisplayVersion.status === 'UNDER_REVIEW' && pendingWorkflow && (
                    <>
                      {isCreatorOfCurrentVersion ? (
                        <div className="flex items-center gap-1 text-[11px] text-amber-400 bg-amber-950/40 border border-amber-800/60 px-2 py-1 rounded">
                          <AlertTriangle size={12} />
                          <span>Four-Eyes Governance: Creator cannot self-approve</span>
                        </div>
                      ) : (
                        hasPermission('policy:approve') && (
                          <Button
                            size="xs"
                            variant="primary"
                            onClick={() => {
                              setSelectedWorkflowId(pendingWorkflow.id);
                              setIsReviewActionModalOpen(true);
                            }}
                          >
                            <UserCheck size={12} />
                            Review & Decide (Four-Eyes)
                          </Button>
                        )
                      )}
                    </>
                  )}

                  {/* Publish APPROVED Version */}
                  {currentDisplayVersion.status === 'APPROVED' && hasPermission('policy:manage') && (
                    <Button
                      size="xs"
                      variant="success"
                      isLoading={isPublishingVersion}
                      onClick={() => handlePublishVersion(currentDisplayVersion.id)}
                    >
                      <CheckCircle size={12} />
                      Publish Version
                    </Button>
                  )}
                </div>
              </div>
            )}

            {/* Document Content / Diff View */}
            <div className="p-6">
              {isDiffMode && previousVersion ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <span className="text-[11px] font-semibold text-slate-400 block mb-1">
                        Previous Version v{previousVersion.version_number} ({previousVersion.status})
                      </span>
                      <div className="prose prose-invert max-w-none text-xs text-rose-300/80 font-mono whitespace-pre-wrap leading-relaxed bg-rose-950/20 p-4 rounded-lg border border-rose-900/40 max-h-[500px] overflow-y-auto">
                        {previousVersion.content}
                      </div>
                    </div>
                    <div>
                      <span className="text-[11px] font-semibold text-emerald-400 block mb-1">
                        Selected Version v{currentDisplayVersion?.version_number} ({currentDisplayVersion?.status})
                      </span>
                      <div className="prose prose-invert max-w-none text-xs text-emerald-300 font-mono whitespace-pre-wrap leading-relaxed bg-emerald-950/20 p-4 rounded-lg border border-emerald-900/40 max-h-[500px] overflow-y-auto">
                        {currentDisplayVersion?.content}
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="prose prose-invert max-w-none text-xs text-slate-300 font-mono whitespace-pre-wrap leading-relaxed bg-slate-950/70 p-4 rounded-lg border border-slate-800/80">
                  {currentDisplayVersion?.content || 'No content drafted.'}
                </div>
              )}
            </div>
          </Card>

          {/* Review Workflow Audit Trail Card */}
          {currentDisplayVersion?.reviews && currentDisplayVersion.reviews.length > 0 && (
            <Card>
              <CardHeader
                title={`Review & Approval Audit Trail (${currentDisplayVersion.reviews.length})`}
                subtitle="Tamper-evident log of formal Four-Eyes review stages and approver decisions."
              />
              <div className="p-3">
                <div className="space-y-2">
                  {currentDisplayVersion.reviews.map((wf) => (
                    <div
                      key={wf.id}
                      className="p-3 rounded bg-slate-950 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-slate-400 font-semibold">{wf.workflow_code}</span>
                          <span className="text-indigo-400 font-medium">[{wf.review_stage.replace('_', ' ')}]</span>
                          {getReviewStatusBadge(wf.status)}
                        </div>
                        {wf.review_notes && (
                          <p className="text-slate-300 text-[11px] italic">"{wf.review_notes}"</p>
                        )}
                        <div className="flex items-center gap-3 text-[11px] text-slate-500">
                          {wf.created_by && <span>Submitted by: {wf.created_by.full_name}</span>}
                          {wf.reviewed_by && <span>Reviewed by: {wf.reviewed_by.full_name}</span>}
                          {wf.approved_by && <span>Approved by: {wf.approved_by.full_name}</span>}
                        </div>
                      </div>

                      <div className="text-[11px] font-mono text-slate-500 shrink-0">
                        {wf.reviewed_at ? (
                          <span>{new Date(wf.reviewed_at).toLocaleDateString()}</span>
                        ) : (
                          <span className="text-amber-400/80">Pending Decision</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </Card>
          )}
        </div>

        {/* Sidebar Meta: Mapped Controls & Lifecycle (1 Col) */}
        <div className="space-y-6">
          {/* Metadata Card */}
          <Card>
            <CardHeader title="Policy Governance Meta" />
            <div className="p-4 space-y-3 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-800/80">
                <span className="text-slate-400">Owner</span>
                <span className="text-slate-200 font-medium">
                  {policy.owner?.full_name || 'Unassigned'}
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/80">
                <span className="text-slate-400">Total Versions</span>
                <span className="text-slate-200 font-mono font-medium">
                  {policy.total_versions}
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/80">
                <span className="text-slate-400">Active Version</span>
                <span className="text-emerald-400 font-mono font-medium">
                  v{policy.current_version?.version_number || 1} ({policy.current_version?.status || 'DRAFT'})
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/80">
                <span className="text-slate-400">Created</span>
                <span className="text-slate-300">
                  {new Date(policy.created_at).toLocaleDateString()}
                </span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-400">Last Modified</span>
                <span className="text-slate-300">
                  {new Date(policy.updated_at).toLocaleDateString()}
                </span>
              </div>
            </div>
          </Card>

          {/* Mapped Controls Card */}
          <Card>
            <div className="p-4 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Shield size={14} className="text-emerald-400" />
                <h3 className="text-xs font-semibold text-slate-200">
                  Mapped Controls ({policy.mapped_subcategories?.length || 0})
                </h3>
              </div>

              {hasPermission('policy:manage') && (
                <Button
                  size="xs"
                  variant="secondary"
                  onClick={() => setIsMappingModalOpen(true)}
                >
                  <Plus size={11} />
                  Link Control
                </Button>
              )}
            </div>

            <div className="p-3 space-y-2">
              {(!policy.mapped_subcategories || policy.mapped_subcategories.length === 0) ? (
                <div className="py-4 text-center text-xs text-slate-500 italic">
                  No framework controls mapped yet.
                </div>
              ) : (
                policy.mapped_subcategories.map((sub) => (
                  <div
                    key={sub.id}
                    className="p-2.5 rounded bg-slate-950 border border-slate-800/80 flex items-center justify-between text-xs"
                  >
                    <div>
                      <span className="font-mono font-bold text-indigo-300">{sub.identifier}</span>
                      <span className="block text-[11px] text-slate-300 line-clamp-1">
                        {sub.title}
                      </span>
                    </div>

                    {hasPermission('policy:manage') && (
                      <button
                        type="button"
                        onClick={() => handleRemoveMapping(sub.id)}
                        className="text-slate-500 hover:text-rose-400 p-1 transition-colors"
                        title="Remove Mapping"
                      >
                        <Trash2 size={13} />
                      </button>
                    )}
                  </div>
                ))
              )}
            </div>
          </Card>
        </div>
      </div>

      {/* New Version Modal */}
      <Modal
        isOpen={isVersionModalOpen}
        onClose={() => setIsVersionModalOpen(false)}
        title={`Create New Policy Version (v${(policy.current_version?.version_number || 1) + 1})`}
      >
        <form onSubmit={handleCreateVersion} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Change Summary / Revision Notes
            </label>
            <input
              type="text"
              required
              value={newVersionSummary}
              onChange={(e) => setNewVersionSummary(e.target.value)}
              placeholder="e.g. Added section 3.4 for API key rotation..."
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Policy Content (Markdown)
            </label>
            <textarea
              required
              rows={10}
              value={newVersionContent}
              onChange={(e) => setNewVersionContent(e.target.value)}
              className="w-full font-mono bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="pt-3 flex justify-end gap-2 border-t border-slate-800">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setIsVersionModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={isSubmittingVersion}
            >
              Save Immutable Version
            </Button>
          </div>
        </form>
      </Modal>

      {/* Submit for Review Modal */}
      <Modal
        isOpen={isSubmitReviewModalOpen}
        onClose={() => setIsSubmitReviewModalOpen(false)}
        title={`Submit Version v${currentDisplayVersion?.version_number} for Review`}
      >
        <form onSubmit={handleSubmitForReview} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Review Stage</label>
            <select
              value={reviewStage}
              onChange={(e) => setReviewStage(e.target.value as PolicyReviewStage)}
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="SECURITY_REVIEW">Security Review</option>
              <option value="LEGAL_REVIEW">Legal Review</option>
              <option value="EXECUTIVE_APPROVAL">Executive Approval</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Submission Notes / Justification
            </label>
            <textarea
              rows={4}
              value={submitReviewNotes}
              onChange={(e) => setSubmitReviewNotes(e.target.value)}
              placeholder="Provide background, legal references, or key changes for reviewers..."
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="pt-3 flex justify-end gap-2 border-t border-slate-800">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setIsSubmitReviewModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="warning"
              size="sm"
              isLoading={isSubmittingReview}
            >
              Submit for Formal Review
            </Button>
          </div>
        </form>
      </Modal>

      {/* Four-Eyes Review Decision Modal */}
      <Modal
        isOpen={isReviewActionModalOpen}
        onClose={() => setIsReviewActionModalOpen(false)}
        title="Four-Eyes Review & Approval Decision"
      >
        <form onSubmit={handleReviewDecision} className="space-y-4">
          <div className="p-3 bg-indigo-950/40 border border-indigo-800/60 rounded text-xs text-indigo-300">
            <span className="font-semibold block mb-0.5">Four-Eyes Integrity Control</span>
            You are reviewing as an independent authorized stakeholder. Self-approval of authored policies is strictly blocked.
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Review Decision</label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setReviewDecision('APPROVE')}
                className={`flex-1 py-2 px-3 rounded border text-xs font-medium transition-colors ${
                  reviewDecision === 'APPROVE'
                    ? 'bg-emerald-950 border-emerald-500 text-emerald-300'
                    : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                Approve Version
              </button>
              <button
                type="button"
                onClick={() => setReviewDecision('REQUEST_CHANGES')}
                className={`flex-1 py-2 px-3 rounded border text-xs font-medium transition-colors ${
                  reviewDecision === 'REQUEST_CHANGES'
                    ? 'bg-amber-950 border-amber-500 text-amber-300'
                    : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                Request Changes
              </button>
              <button
                type="button"
                onClick={() => setReviewDecision('REJECT')}
                className={`flex-1 py-2 px-3 rounded border text-xs font-medium transition-colors ${
                  reviewDecision === 'REJECT'
                    ? 'bg-rose-950 border-rose-500 text-rose-300'
                    : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                Reject Version
              </button>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Reviewer Notes / Findings
            </label>
            <textarea
              required
              rows={4}
              value={reviewActionNotes}
              onChange={(e) => setReviewActionNotes(e.target.value)}
              placeholder="Detail observations, approvals, or requirements for required revisions..."
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="pt-3 flex justify-end gap-2 border-t border-slate-800">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setIsReviewActionModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant={reviewDecision === 'APPROVE' ? 'success' : reviewDecision === 'REJECT' ? 'danger' : 'warning'}
              size="sm"
              isLoading={isSubmittingReviewAction}
            >
              Submit {reviewDecision.replace('_', ' ')}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Add Control Mapping Modal */}
      <Modal
        isOpen={isMappingModalOpen}
        onClose={() => setIsMappingModalOpen(false)}
        title="Link Framework Control Outcome"
      >
        <form onSubmit={handleAddMapping} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Select Framework Control Outcome
            </label>
            <select
              required
              value={selectedSubcatId}
              onChange={(e) => setSelectedSubcatId(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
            >
              <option value="">-- Choose NIST CSF 2.0 Subcategory --</option>
              {allSubcategories.map((sub) => (
                <option key={sub.id} value={sub.id}>
                  {sub.identifier} — {sub.title}
                </option>
              ))}
            </select>
          </div>

          <div className="pt-3 flex justify-end gap-2 border-t border-slate-800">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setIsMappingModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={isSubmittingMapping}
            >
              Link to Policy
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};