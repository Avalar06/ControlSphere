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
  Check,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../lib/api';
import type { FrameworkSubcategory, Policy, PolicyStatus } from '../types';
import { Card, CardHeader } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';

export const PolicyDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { hasPermission } = useAuth();
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
    try {
      await api.post(`/api/v1/policies/${policy.id}/versions`, {
        content: newVersionContent,
        change_summary: newVersionSummary,
      });
      setIsVersionModalOpen(false);
      setNewVersionSummary('');
      await fetchPolicy();
      setStatusMessage('New immutable policy version created.');
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to create version.');
    } finally {
      setIsSubmittingVersion(false);
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
    return <LoadingSpinner text="Loading policy document &amp; versions..." />;
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

          {/* Status Action Buttons */}
          {hasPermission('policy:manage') && (
            <div className="flex items-center gap-2 flex-wrap">
              {policy.status === 'DRAFT' && (
                <Button
                  size="sm"
                  variant="warning"
                  onClick={() => handleStatusTransition('UNDER_REVIEW')}
                >
                  <Send size={13} />
                  Submit for Review
                </Button>
              )}

              {policy.status === 'UNDER_REVIEW' && (
                <Button
                  size="sm"
                  variant="primary"
                  onClick={() => handleStatusTransition('APPROVED')}
                >
                  <Check size={13} />
                  Approve Policy
                </Button>
              )}

              {policy.status === 'APPROVED' && (
                <Button
                  size="sm"
                  variant="success"
                  onClick={() => handleStatusTransition('PUBLISHED')}
                >
                  <CheckCircle size={13} />
                  Publish Policy
                </Button>
              )}

              {policy.status !== 'ARCHIVED' && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleStatusTransition('ARCHIVED')}
                >
                  <Archive size={13} />
                  Archive
                </Button>
              )}

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
            </div>
          )}
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
            <div className="p-4 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <History size={14} className="text-indigo-400" />
                <span className="text-xs font-semibold text-slate-200">
                  Viewing Version v{currentDisplayVersion?.version_number || 1}
                </span>
                <span className="text-[11px] text-slate-400">
                  · {currentDisplayVersion?.change_summary}
                </span>
              </div>

              {/* Version Selector Dropdown */}
              {policy.versions && policy.versions.length > 1 && (
                <select
                  value={selectedVersionNum || policy.current_version?.version_number}
                  onChange={(e) => setSelectedVersionNum(parseInt(e.target.value, 10))}
                  className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-xs text-slate-300 focus:outline-none focus:border-indigo-500 font-mono"
                >
                  {policy.versions.map((v) => (
                    <option key={v.id} value={v.version_number}>
                      v{v.version_number} — {new Date(v.created_at).toLocaleDateString()}
                    </option>
                  ))}
                </select>
              )}
            </div>

            <div className="p-6">
              <div className="prose prose-invert max-w-none text-xs text-slate-300 font-mono whitespace-pre-wrap leading-relaxed bg-slate-950/70 p-4 rounded-lg border border-slate-800/80">
                {currentDisplayVersion?.content || 'No content drafted.'}
              </div>
            </div>
          </Card>
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