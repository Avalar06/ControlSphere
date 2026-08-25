import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import { evidenceService } from '../lib/evidenceService';
import { useAuth } from '../context/AuthContext';
import type {
  EvidenceItem,
  EvidenceStatus,
  OrganizationControl,
  ReviewDecision,
} from '../types';
import {
  FileText,
  Upload,
  CheckCircle2,
  XCircle,
  Clock,
  Search,
  Filter,
  Download,
  Eye,
  AlertCircle,
  FileCheck,
  Hash,
  X,
  FileCode,
  Image as ImageIcon,
  RefreshCw,
} from 'lucide-react';

export const EvidencePage: React.FC = () => {
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [controlFilter, setControlFilter] = useState<string>('ALL');
  const [selectedEvidence, setSelectedEvidence] = useState<EvidenceItem | null>(null);
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  // Review Form state
  const [reviewDecision, setReviewDecision] = useState<ReviewDecision>('ACCEPT');
  const [reviewNotes, setReviewNotes] = useState('');
  const [rejectionReason, setRejectionReason] = useState('');
  const [reviewError, setReviewError] = useState('');

  // Upload Form state
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadControlId, setUploadControlId] = useState<number | ''>('');
  const [uploadRequirementId, setUploadRequirementId] = useState<number | ''>('');
  const [uploadTitle, setUploadTitle] = useState('');
  const [uploadDescription, setUploadDescription] = useState('');
  const [uploadError, setUploadError] = useState('');

  // Queries
  const { data: stats } = useQuery({
    queryKey: ['evidence-stats'],
    queryFn: evidenceService.getEvidenceStats,
  });

  const { data: evidenceItems = [], isLoading } = useQuery({
    queryKey: ['evidence-items', statusFilter, controlFilter, search],
    queryFn: () =>
      evidenceService.getEvidenceItems({
        status: statusFilter === 'ALL' ? undefined : (statusFilter as EvidenceStatus),
        organization_control_id: controlFilter === 'ALL' ? undefined : Number(controlFilter),
        search: search || undefined,
      }),
  });

  const { data: controls = [] } = useQuery<OrganizationControl[]>({
    queryKey: ['controls-list-simple'],
    queryFn: async () => {
      const res = await api.get<OrganizationControl[]>('/api/v1/controls');
      return res.data;
    },
  });


  const { data: requirements = [] } = useQuery({
    queryKey: ['requirements-for-upload', uploadControlId],
    queryFn: () =>
      uploadControlId
        ? evidenceService.getRequirements({ organization_control_id: Number(uploadControlId) })
        : Promise.resolve([]),
    enabled: !!uploadControlId,
  });

  // Mutations
  const uploadMutation = useMutation({
    mutationFn: evidenceService.uploadEvidence,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['evidence-items'] });
      queryClient.invalidateQueries({ queryKey: ['evidence-stats'] });
      setIsUploadOpen(false);
      resetUploadForm();
    },
    onError: (err: any) => {
      setUploadError(err.response?.data?.detail || 'Failed to upload evidence.');
    },
  });

  const reviewMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) =>
      evidenceService.reviewEvidence(id, data),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ['evidence-items'] });
      queryClient.invalidateQueries({ queryKey: ['evidence-stats'] });
      setSelectedEvidence(updated);
      setReviewNotes('');
      setRejectionReason('');
      setReviewError('');
    },
    onError: (err: any) => {
      setReviewError(err.response?.data?.detail || 'Review submission failed.');
    },
  });

  const submitReviewMutation = useMutation({
    mutationFn: (id: number) => evidenceService.submitForReview(id),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ['evidence-items'] });
      setSelectedEvidence(updated);
    },
  });

  const resetUploadForm = () => {
    setUploadFile(null);
    setUploadControlId('');
    setUploadRequirementId('');
    setUploadTitle('');
    setUploadDescription('');
    setUploadError('');
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setUploadFile(file);
      if (!uploadTitle) {
        setUploadTitle(file.name.replace(/\.[^/.]+$/, ''));
      }
      setUploadError('');
    }
  };

  const handleUploadSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) {
      setUploadError('Please select a file to upload.');
      return;
    }
    if (!uploadControlId) {
      setUploadError('Please select an organization control.');
      return;
    }

    const formData = new FormData();
    formData.append('file', uploadFile);
    formData.append('organization_control_id', String(uploadControlId));
    if (uploadRequirementId) {
      formData.append('evidence_requirement_id', String(uploadRequirementId));
    }
    if (uploadTitle) {
      formData.append('title', uploadTitle);
    }
    if (uploadDescription) {
      formData.append('description', uploadDescription);
    }

    uploadMutation.mutate(formData);
  };

  const handleReviewSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedEvidence) return;
    if (reviewDecision === 'REJECT' && !rejectionReason.trim()) {
      setReviewError('Rejection reason is required.');
      return;
    }

    reviewMutation.mutate({
      id: selectedEvidence.id,
      data: {
        decision: reviewDecision,
        review_notes: reviewNotes,
        rejection_reason: reviewDecision === 'REJECT' ? rejectionReason : undefined,
      },
    });
  };

  const handleDownload = async (ev: EvidenceItem) => {
    try {
      await evidenceService.downloadEvidence(ev.id, ev.original_filename);
    } catch (err) {
      alert('Failed to download evidence artifact.');
    }
  };

  const getStatusBadge = (status: EvidenceStatus) => {
    switch (status) {
      case 'ACCEPTED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" /> Accepted
          </span>
        );
      case 'UNDER_REVIEW':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Clock className="w-3.5 h-3.5" /> Under Review
          </span>
        );
      case 'UPLOADED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <Upload className="w-3.5 h-3.5" /> Uploaded
          </span>
        );
      case 'REJECTED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <XCircle className="w-3.5 h-3.5" /> Rejected
          </span>
        );
      case 'SUPERSEDED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-500/10 text-slate-400 border border-slate-500/20">
            <RefreshCw className="w-3.5 h-3.5" /> Superseded
          </span>
        );
    }
  };

  const getFileIcon = (ext: string) => {
    if (['.png', '.jpg', '.jpeg'].includes(ext)) {
      return <ImageIcon className="w-5 h-5 text-indigo-400" />;
    }
    if (['.csv', '.xlsx'].includes(ext)) {
      return <FileCode className="w-5 h-5 text-emerald-400" />;
    }
    return <FileText className="w-5 h-5 text-blue-400" />;
  };

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const canUpload = ['ADMIN', 'GRC_ANALYST', 'SECURITY_ANALYST'].includes(user?.role || '');
  const canReview = ['ADMIN', 'GRC_ANALYST', 'AUDITOR'].includes(user?.role || '');

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-slate-900/60 p-6 rounded-2xl border border-slate-800 backdrop-blur-xl">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-blue-500/10 rounded-xl border border-blue-500/20">
              <FileCheck className="w-6 h-6 text-blue-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">Evidence Repository</h1>
              <p className="text-sm text-slate-400">
                Audit-grade artifact storage, cryptographic validation, and assurance review workflow.
              </p>
            </div>
          </div>
        </div>

        {canUpload && (
          <button
            onClick={() => {
              resetUploadForm();
              setIsUploadOpen(true);
            }}
            className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-xl shadow-lg shadow-blue-500/20 transition-all duration-200"
          >
            <Upload className="w-4 h-4" />
            Upload Evidence
          </button>
        )}
      </div>

      {/* Assurance Summary Cards */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          <div className="bg-slate-900/40 p-4 rounded-xl border border-slate-800">
            <p className="text-xs font-medium text-slate-400">Total Artifacts</p>
            <p className="text-2xl font-bold text-white mt-1">{stats.total_evidence_items}</p>
          </div>
          <div className="bg-slate-900/40 p-4 rounded-xl border border-slate-800">
            <p className="text-xs font-medium text-blue-400">Uploaded</p>
            <p className="text-2xl font-bold text-blue-400 mt-1">{stats.uploaded_count}</p>
          </div>
          <div className="bg-slate-900/40 p-4 rounded-xl border border-slate-800">
            <p className="text-xs font-medium text-amber-400">Under Review</p>
            <p className="text-2xl font-bold text-amber-400 mt-1">{stats.pending_review_count}</p>
          </div>
          <div className="bg-slate-900/40 p-4 rounded-xl border border-slate-800">
            <p className="text-xs font-medium text-emerald-400">Accepted</p>
            <p className="text-2xl font-bold text-emerald-400 mt-1">{stats.accepted_count}</p>
          </div>
          <div className="bg-slate-900/40 p-4 rounded-xl border border-slate-800">
            <p className="text-xs font-medium text-rose-400">Rejected</p>
            <p className="text-2xl font-bold text-rose-400 mt-1">{stats.rejected_count}</p>
          </div>
          <div className="bg-slate-900/40 p-4 rounded-xl border border-slate-800">
            <p className="text-xs font-medium text-indigo-400">Assurance Coverage</p>
            <p className="text-2xl font-bold text-indigo-400 mt-1">{stats.overall_coverage_pct}%</p>
          </div>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-col md:flex-row gap-4 justify-between items-center bg-slate-900/40 p-4 rounded-xl border border-slate-800">
        <div className="flex flex-1 items-center gap-3 w-full md:w-auto">
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search title, filename, or SHA-256..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-white focus:outline-none focus:border-blue-500"
            />
          </div>

          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-300 px-3 py-2 focus:outline-none focus:border-blue-500"
            >
              <option value="ALL">All Statuses</option>
              <option value="UPLOADED">Uploaded</option>
              <option value="UNDER_REVIEW">Under Review</option>
              <option value="ACCEPTED">Accepted</option>
              <option value="REJECTED">Rejected</option>
              <option value="SUPERSEDED">Superseded</option>
            </select>
          </div>
        </div>

        <div className="flex items-center gap-2 w-full md:w-auto">
          <select
            value={controlFilter}
            onChange={(e) => setControlFilter(e.target.value)}
            className="w-full md:w-64 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-300 px-3 py-2 focus:outline-none focus:border-blue-500"
          >
            <option value="ALL">All Controls</option>
            {controls.map((c: OrganizationControl) => (
              <option key={c.id} value={c.id}>
                {c.subcategory?.identifier} — {c.subcategory?.title?.slice(0, 30)}...
              </option>
            ))}
          </select>

        </div>
      </div>

      {/* Evidence Table */}
      <div className="bg-slate-900/60 rounded-2xl border border-slate-800 overflow-hidden backdrop-blur-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-950/80 text-xs uppercase tracking-wider text-slate-400 border-b border-slate-800">
              <tr>
                <th className="py-3.5 px-4 font-semibold">Evidence Artifact</th>
                <th className="py-3.5 px-4 font-semibold">Control & Requirement</th>
                <th className="py-3.5 px-4 font-semibold">Status</th>
                <th className="py-3.5 px-4 font-semibold">Size</th>
                <th className="py-3.5 px-4 font-semibold">SHA-256 Hash</th>
                <th className="py-3.5 px-4 font-semibold">Uploader</th>
                <th className="py-3.5 px-4 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-400">
                    Loading evidence artifacts...
                  </td>
                </tr>
              ) : evidenceItems.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-500">
                    <FileText className="w-12 h-12 mx-auto mb-3 opacity-30 text-slate-400" />
                    No evidence items found matching your filters.
                  </td>
                </tr>
              ) : (
                evidenceItems.map((ev) => (
                  <tr key={ev.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-slate-800/60 rounded-lg border border-slate-700/50">
                          {getFileIcon(ev.file_extension)}
                        </div>
                        <div>
                          <p className="font-semibold text-white">{ev.title}</p>
                          <p className="text-xs text-slate-400">{ev.original_filename}</p>
                        </div>
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="space-y-1">
                        <span className="inline-block px-2 py-0.5 rounded text-xs font-mono font-bold bg-blue-500/10 text-blue-400 border border-blue-500/20">
                          {ev.control_identifier || 'Control'}
                        </span>
                        <p className="text-xs text-slate-400 truncate max-w-[200px]">
                          {ev.requirement_title || 'General Evidence'}
                        </p>
                      </div>
                    </td>
                    <td className="py-3.5 px-4">{getStatusBadge(ev.status)}</td>
                    <td className="py-3.5 px-4 text-xs font-mono text-slate-400">
                      {formatBytes(ev.file_size)}
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-1 font-mono text-xs text-slate-400 bg-slate-950 px-2 py-1 rounded border border-slate-800 max-w-[140px] truncate">
                        <Hash className="w-3 h-3 text-slate-500 flex-shrink-0" />
                        <span className="truncate">{ev.sha256_hash}</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-xs text-slate-400">
                      <p className="text-slate-200">{ev.uploaded_by?.full_name || 'System'}</p>
                      <p className="text-[11px] text-slate-500">
                        {new Date(ev.created_at).toLocaleDateString()}
                      </p>
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={async () => {
                            const full = await evidenceService.getEvidenceById(ev.id);
                            setSelectedEvidence(full);
                            setIsDetailOpen(true);
                          }}
                          className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
                          title="View Details & Review"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDownload(ev)}
                          className="p-1.5 text-slate-400 hover:text-blue-400 hover:bg-blue-500/10 rounded-lg transition-colors"
                          title="Download Artifact"
                        >
                          <Download className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Upload Evidence Modal */}
      {isUploadOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex justify-between items-center pb-4 border-b border-slate-800">
              <div className="flex items-center gap-2.5">
                <div className="p-2 bg-blue-500/10 rounded-lg border border-blue-500/20">
                  <Upload className="w-5 h-5 text-blue-400" />
                </div>
                <h3 className="text-lg font-bold text-white">Upload Evidence Artifact</h3>
              </div>
              <button
                onClick={() => setIsUploadOpen(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {uploadError && (
              <div className="flex items-center gap-2 p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-xl text-xs">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{uploadError}</span>
              </div>
            )}

            <form onSubmit={handleUploadSubmit} className="space-y-4">
              {/* File Dropzone */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                  Select Artifact File
                </label>
                <div className="border-2 border-dashed border-slate-700 hover:border-blue-500/60 rounded-xl p-5 text-center bg-slate-950/50 transition-colors">
                  <input
                    type="file"
                    id="evidence-file"
                    onChange={handleFileChange}
                    className="hidden"
                    accept=".pdf,.docx,.xlsx,.csv,.txt,.png,.jpg,.jpeg"
                  />
                  <label htmlFor="evidence-file" className="cursor-pointer block space-y-2">
                    <FileText className="w-8 h-8 mx-auto text-slate-400" />
                    <div className="text-xs text-slate-300">
                      {uploadFile ? (
                        <span className="font-semibold text-blue-400">
                          {uploadFile.name} ({formatBytes(uploadFile.size)})
                        </span>
                      ) : (
                        <span>
                          <strong className="text-blue-400 hover:underline">Click to browse</strong> or drag file here
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-slate-500">
                      Allowed: PDF, DOCX, XLSX, CSV, TXT, PNG, JPG (Max 25 MB)
                    </p>
                  </label>
                </div>
              </div>

              {/* Target Control */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                  Target Control *
                </label>
                <select
                  value={uploadControlId}
                  onChange={(e) => {
                    setUploadControlId(e.target.value ? Number(e.target.value) : '');
                    setUploadRequirementId('');
                  }}
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                >
                  <option value="">Select an organization control...</option>
                  {controls.map((c: OrganizationControl) => (
                    <option key={c.id} value={c.id}>
                      {c.subcategory?.identifier} — {c.subcategory?.title}
                    </option>
                  ))}
                </select>

              </div>

              {/* Target Requirement (Optional) */}
              {uploadControlId && requirements.length > 0 && (
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                    Associated Requirement (Optional)
                  </label>
                  <select
                    value={uploadRequirementId}
                    onChange={(e) => setUploadRequirementId(e.target.value ? Number(e.target.value) : '')}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                  >
                    <option value="">None (General Control Evidence)</option>
                    {requirements.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.is_required ? '[REQUIRED]' : '[OPTIONAL]'} {r.title}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Title */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                  Evidence Title
                </label>
                <input
                  type="text"
                  placeholder="e.g. Q3 Firewall Rule Export"
                  value={uploadTitle}
                  onChange={(e) => setUploadTitle(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              {/* Description */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                  Description / Context
                </label>
                <textarea
                  rows={2}
                  placeholder="Describe what this evidence artifact demonstrates..."
                  value={uploadDescription}
                  onChange={(e) => setUploadDescription(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500 resize-none"
                />
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsUploadOpen(false)}
                  className="px-4 py-2 text-sm font-medium text-slate-400 hover:text-white bg-slate-800/60 rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploadMutation.isPending}
                  className="flex items-center gap-2 px-5 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-xl shadow-lg shadow-blue-500/20"
                >
                  {uploadMutation.isPending ? 'Uploading & Hashing...' : 'Submit Evidence'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Evidence Detail & Review Modal */}
      {isDetailOpen && selectedEvidence && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6 shadow-2xl space-y-6 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex justify-between items-start pb-4 border-b border-slate-800">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-slate-800 rounded-xl border border-slate-700">
                  {getFileIcon(selectedEvidence.file_extension)}
                </div>
                <div>
                  <h3 className="text-xl font-bold text-white">{selectedEvidence.title}</h3>
                  <p className="text-xs text-slate-400">{selectedEvidence.original_filename}</p>
                </div>
              </div>
              <button
                onClick={() => setIsDetailOpen(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Metadata Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs bg-slate-950/50 p-4 rounded-xl border border-slate-800">
              <div>
                <span className="text-slate-500 block">Status</span>
                <span className="mt-1 block">{getStatusBadge(selectedEvidence.status)}</span>
              </div>
              <div>
                <span className="text-slate-500 block">Control</span>
                <span className="font-mono text-blue-400 font-bold mt-1 block">
                  {selectedEvidence.control_identifier}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block">File Size</span>
                <span className="text-slate-200 mt-1 block font-mono">
                  {formatBytes(selectedEvidence.file_size)}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block">Uploaded By</span>
                <span className="text-slate-200 mt-1 block">
                  {selectedEvidence.uploaded_by?.full_name || 'System'}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block">Uploaded At</span>
                <span className="text-slate-200 mt-1 block">
                  {new Date(selectedEvidence.created_at).toLocaleString()}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block">Requirement</span>
                <span className="text-slate-200 mt-1 block truncate">
                  {selectedEvidence.requirement_title || 'General Evidence'}
                </span>
              </div>
            </div>

            {/* SHA-256 Cryptographic Hash */}
            <div className="space-y-1.5 bg-slate-950 p-3.5 rounded-xl border border-slate-800">
              <span className="text-xs font-semibold text-slate-400 flex items-center gap-1.5">
                <Hash className="w-3.5 h-3.5 text-blue-400" /> Cryptographic SHA-256 Digest (Integrity Verified)
              </span>
              <div className="font-mono text-xs text-blue-300 break-all select-all">
                {selectedEvidence.sha256_hash}
              </div>
            </div>

            {/* Download Action */}
            <div className="flex justify-between items-center bg-slate-800/30 p-3.5 rounded-xl border border-slate-800">
              <span className="text-xs text-slate-300 font-medium">Download Original Binary Artifact</span>
              <button
                onClick={() => handleDownload(selectedEvidence)}
                className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold shadow-md transition-colors"
              >
                <Download className="w-3.5 h-3.5" /> Download File
              </button>
            </div>

            {/* Submit for Review Action (if UPLOADED or REJECTED) */}
            {['UPLOADED', 'REJECTED'].includes(selectedEvidence.status) && canUpload && (
              <div className="flex justify-between items-center bg-amber-500/10 p-3.5 rounded-xl border border-amber-500/20">
                <div>
                  <p className="text-xs font-bold text-amber-400">Ready for Assurance Review?</p>
                  <p className="text-[11px] text-slate-400">
                    Transition status to Under Review to alert auditors.
                  </p>
                </div>
                <button
                  onClick={() => submitReviewMutation.mutate(selectedEvidence.id)}
                  disabled={submitReviewMutation.isPending}
                  className="px-3.5 py-1.5 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-xs font-semibold shadow-md transition-colors"
                >
                  Submit for Review
                </button>
              </div>
            )}

            {/* Review History */}
            {selectedEvidence.reviews && selectedEvidence.reviews.length > 0 && (
              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Review & Decision History
                </h4>
                <div className="space-y-2.5">
                  {selectedEvidence.reviews.map((rev) => (
                    <div
                      key={rev.id}
                      className={`p-3.5 rounded-xl border text-xs space-y-1.5 ${
                        rev.decision === 'ACCEPT'
                          ? 'bg-emerald-500/5 border-emerald-500/20'
                          : 'bg-rose-500/5 border-rose-500/20'
                      }`}
                    >
                      <div className="flex justify-between items-center">
                        <span
                          className={`font-bold uppercase ${
                            rev.decision === 'ACCEPT' ? 'text-emerald-400' : 'text-rose-400'
                          }`}
                        >
                          Decision: {rev.decision}
                        </span>
                        <span className="text-slate-500">
                          {new Date(rev.reviewed_at).toLocaleString()}
                        </span>
                      </div>
                      <p className="text-slate-300">
                        <strong className="text-slate-400">Reviewer:</strong>{' '}
                        {rev.reviewer?.full_name || 'Auditor'} ({rev.reviewer?.email})
                      </p>
                      {rev.rejection_reason && (
                        <p className="text-rose-300">
                          <strong>Rejection Reason:</strong> {rev.rejection_reason}
                        </p>
                      )}
                      {rev.review_notes && (
                        <p className="text-slate-400">
                          <strong>Notes:</strong> {rev.review_notes}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Review Decision Form (for authorized reviewers) */}
            {canReview && selectedEvidence.status !== 'SUPERSEDED' && (
              <form onSubmit={handleReviewSubmit} className="space-y-3 pt-4 border-t border-slate-800">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Submit Auditor Decision
                </h4>

                {reviewError && (
                  <div className="p-2.5 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-lg text-xs">
                    {reviewError}
                  </div>
                )}

                <div className="flex gap-4">
                  <label className="flex items-center gap-2 text-xs font-semibold text-emerald-400 cursor-pointer">
                    <input
                      type="radio"
                      name="decision"
                      value="ACCEPT"
                      checked={reviewDecision === 'ACCEPT'}
                      onChange={() => setReviewDecision('ACCEPT')}
                      className="text-emerald-500 focus:ring-emerald-500"
                    />
                    Accept Artifact
                  </label>
                  <label className="flex items-center gap-2 text-xs font-semibold text-rose-400 cursor-pointer">
                    <input
                      type="radio"
                      name="decision"
                      value="REJECT"
                      checked={reviewDecision === 'REJECT'}
                      onChange={() => setReviewDecision('REJECT')}
                      className="text-rose-500 focus:ring-rose-500"
                    />
                    Reject Artifact
                  </label>
                </div>

                {reviewDecision === 'REJECT' && (
                  <div>
                    <label className="block text-[11px] font-semibold uppercase tracking-wider text-rose-400 mb-1">
                      Rejection Reason *
                    </label>
                    <textarea
                      rows={2}
                      placeholder="Detail why this artifact does not satisfy the requirement..."
                      value={rejectionReason}
                      onChange={(e) => setRejectionReason(e.target.value)}
                      required
                      className="w-full bg-slate-950 border border-rose-500/30 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-rose-500 resize-none"
                    />
                  </div>
                )}

                <div>
                  <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-1">
                    Review Notes / Audit Remarks
                  </label>
                  <input
                    type="text"
                    placeholder="Optional notes or reference ticket..."
                    value={reviewNotes}
                    onChange={(e) => setReviewNotes(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="submit"
                    disabled={reviewMutation.isPending}
                    className={`px-4 py-2 rounded-xl text-xs font-bold text-white shadow-md transition-colors ${
                      reviewDecision === 'ACCEPT'
                        ? 'bg-emerald-600 hover:bg-emerald-500'
                        : 'bg-rose-600 hover:bg-rose-500'
                    }`}
                  >
                    {reviewMutation.isPending
                      ? 'Submitting Decision...'
                      : `Confirm ${reviewDecision === 'ACCEPT' ? 'Acceptance' : 'Rejection'}`}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
