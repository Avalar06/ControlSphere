import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  Play,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  Paperclip,
  Trash2,
  Plus,
  FileText,
  RefreshCw,
  ExternalLink,
} from 'lucide-react';
import { assessmentService } from '../lib/assessmentService';
import { evidenceService } from '../lib/evidenceService';
import { findingService } from '../lib/findingService';
import { useAuth } from '../context/AuthContext';
import type {
  AssessmentConclusion,
  FindingSeverity,
  FindingType,
} from '../types';

export const AssessmentDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { hasRole } = useAuth();
  const canAssess = hasRole('ADMIN', 'GRC_ANALYST', 'SECURITY_ANALYST');

  const assessmentId = Number(id);

  // Modals state
  const [showCompleteModal, setShowCompleteModal] = useState(false);
  const [completeConclusion, setCompleteConclusion] = useState<AssessmentConclusion>('EFFECTIVE');
  const [completeSummary, setCompleteSummary] = useState('');
  const [completeLimitations, setCompleteLimitations] = useState('');

  const [showLinkEvidenceModal, setShowLinkEvidenceModal] = useState(false);
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<number | ''>('');

  const [showLogFindingModal, setShowLogFindingModal] = useState(false);
  const [findingTitle, setFindingTitle] = useState('');
  const [findingDesc, setFindingDesc] = useState('');
  const [findingType, setFindingType] = useState<FindingType>('CONTROL_GAP');
  const [findingSeverity, setFindingSeverity] = useState<FindingSeverity>('MEDIUM');
  const [findingImpact, setFindingImpact] = useState(3);
  const [findingLikelihood, setFindingLikelihood] = useState(3);
  const [findingRecommendation, setFindingRecommendation] = useState('');
  const [findingDueDate, setFindingDueDate] = useState('');

  const [actionError, setActionError] = useState<string | null>(null);

  // Queries
  const { data: assessment, isLoading, error } = useQuery({
    queryKey: ['assessment', assessmentId],
    queryFn: () => assessmentService.getAssessmentById(assessmentId),
    enabled: !isNaN(assessmentId),
  });

  const { data: availableEvidence = [] } = useQuery({
    queryKey: ['availableEvidenceForControl', assessment?.organization_control_id],
    queryFn: () =>
      evidenceService.getEvidenceItems({
        organization_control_id: assessment?.organization_control_id,
      }),
    enabled: !!assessment?.organization_control_id,
  });

  const { data: assessmentFindings = [] } = useQuery({
    queryKey: ['assessmentFindings', assessmentId],
    queryFn: () => findingService.getFindings({ assessment_id: assessmentId }),
    enabled: !isNaN(assessmentId),
  });

  // Mutations
  const startMutation = useMutation({
    mutationFn: () => assessmentService.startAssessment(assessmentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assessment', assessmentId] });
      queryClient.invalidateQueries({ queryKey: ['assessments'] });
    },
    onError: (err: any) => setActionError(err.response?.data?.detail || 'Failed to start assessment.'),
  });

  const completeMutation = useMutation({
    mutationFn: () =>
      assessmentService.completeAssessment(assessmentId, {
        conclusion: completeConclusion,
        summary: completeSummary,
        limitations: completeLimitations || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assessment', assessmentId] });
      queryClient.invalidateQueries({ queryKey: ['assessments'] });
      queryClient.invalidateQueries({ queryKey: ['assessmentStats'] });
      setShowCompleteModal(false);
    },
    onError: (err: any) => setActionError(err.response?.data?.detail || 'Failed to complete assessment.'),
  });

  const supersedeMutation = useMutation({
    mutationFn: () => assessmentService.supersedeAssessment(assessmentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assessment', assessmentId] });
      queryClient.invalidateQueries({ queryKey: ['assessments'] });
      queryClient.invalidateQueries({ queryKey: ['assessmentStats'] });
    },
    onError: (err: any) => setActionError(err.response?.data?.detail || 'Failed to supersede assessment.'),
  });

  const linkEvidenceMutation = useMutation({
    mutationFn: (evId: number) => assessmentService.linkEvidence(assessmentId, evId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assessment', assessmentId] });
      setShowLinkEvidenceModal(false);
      setSelectedEvidenceId('');
    },
    onError: (err: any) => setActionError(err.response?.data?.detail || 'Failed to link evidence.'),
  });

  const unlinkEvidenceMutation = useMutation({
    mutationFn: (evId: number) => assessmentService.unlinkEvidence(assessmentId, evId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assessment', assessmentId] });
    },
    onError: (err: any) => setActionError(err.response?.data?.detail || 'Failed to unlink evidence.'),
  });

  const createFindingMutation = useMutation({
    mutationFn: findingService.createFinding,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assessmentFindings', assessmentId] });
      queryClient.invalidateQueries({ queryKey: ['findings'] });
      setShowLogFindingModal(false);
      setFindingTitle('');
      setFindingDesc('');
      setFindingRecommendation('');
    },
    onError: (err: any) => setActionError(err.response?.data?.detail || 'Failed to create finding.'),
  });

  const handleLogFinding = (e: React.FormEvent) => {
    e.preventDefault();
    if (!assessment) return;
    createFindingMutation.mutate({
      organization_control_id: assessment.organization_control_id,
      assessment_id: assessmentId,
      title: findingTitle,
      description: findingDesc,
      finding_type: findingType,
      severity: findingSeverity,
      impact: findingImpact,
      likelihood: findingLikelihood,
      recommendation: findingRecommendation,
      due_date: findingDueDate || undefined,
    });
  };

  if (isLoading) {
    return <div className="text-center py-20 text-slate-400">Loading assessment details...</div>;
  }

  if (error || !assessment) {
    return (
      <div className="p-6 bg-slate-900 border border-slate-800 rounded-xl text-center space-y-3">
        <h3 className="text-lg font-bold text-rose-400">Assessment Not Found</h3>
        <p className="text-sm text-slate-400">The requested assessment does not exist or you do not have permission.</p>
        <button
          onClick={() => navigate('/assessments')}
          className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg"
        >
          Back to Assessments
        </button>
      </div>
    );
  }

  const isEditable = assessment.status === 'DRAFT' || assessment.status === 'IN_PROGRESS';

  return (
    <div className="space-y-6">
      {/* Navigation Breadcrumb & Back */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/assessments')}
          className="inline-flex items-center gap-2 text-xs font-medium text-slate-400 hover:text-slate-200 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Assessments
        </button>

        {/* Action Controls */}
        {canAssess && (
          <div className="flex items-center gap-2">
            {assessment.status === 'DRAFT' && (
              <button
                onClick={() => startMutation.mutate()}
                disabled={startMutation.isPending}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-medium transition-colors"
              >
                <Play className="w-3.5 h-3.5" /> Start Assessment
              </button>
            )}

            {isEditable && (
              <button
                onClick={() => {
                  setCompleteSummary(assessment.summary || '');
                  setCompleteLimitations(assessment.limitations || '');
                  setShowCompleteModal(true);
                }}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-medium transition-colors"
              >
                <CheckCircle2 className="w-3.5 h-3.5" /> Complete Assessment
              </button>
            )}

            {assessment.status === 'COMPLETED' && (
              <button
                onClick={() => supersedeMutation.mutate()}
                disabled={supersedeMutation.isPending}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium transition-colors"
              >
                <RefreshCw className="w-3.5 h-3.5" /> Supersede Assessment
              </button>
            )}
          </div>
        )}
      </div>

      {actionError && (
        <div className="p-3 bg-rose-950/80 border border-rose-800 text-rose-200 text-xs rounded-lg flex items-center justify-between">
          <span>{actionError}</span>
          <button onClick={() => setActionError(null)} className="text-rose-400">&times;</button>
        </div>
      )}

      {/* Header Card */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-6 shadow-xs space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold text-indigo-400 bg-indigo-950 border border-indigo-800 px-2 py-0.5 rounded">
                {assessment.control_identifier || `Control #${assessment.organization_control_id}`}
              </span>
              <span className="text-xs px-2 py-0.5 rounded font-mono bg-slate-950 text-slate-400 border border-slate-800">
                {assessment.assessment_method}
              </span>
              <span className="text-xs px-2 py-0.5 rounded font-semibold bg-slate-800 text-slate-300 border border-slate-700">
                {assessment.status}
              </span>
            </div>
            <h1 className="text-xl font-bold text-slate-100">
              {assessment.control_title || 'Organization Control Assessment'}
            </h1>
          </div>

          <div className="flex items-center gap-3">
            <div className="text-right">
              <div className="text-xs text-slate-500">Authoritative Conclusion</div>
              <div className="mt-0.5">
                {assessment.conclusion === 'EFFECTIVE' && (
                  <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold bg-emerald-950 text-emerald-300 border border-emerald-800">
                    <CheckCircle2 className="w-4 h-4" /> EFFECTIVE
                  </span>
                )}
                {assessment.conclusion === 'PARTIALLY_EFFECTIVE' && (
                  <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold bg-amber-950 text-amber-300 border border-amber-800">
                    <AlertTriangle className="w-4 h-4" /> PARTIALLY EFFECTIVE
                  </span>
                )}
                {assessment.conclusion === 'INEFFECTIVE' && (
                  <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold bg-rose-950 text-rose-300 border border-rose-800">
                    <XCircle className="w-4 h-4" /> INEFFECTIVE
                  </span>
                )}
                {assessment.conclusion === 'NOT_ASSESSED' && (
                  <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-slate-800 text-slate-400 border border-slate-700">
                    <Clock className="w-4 h-4" /> NOT ASSESSED
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Metadata Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-slate-800/80 text-xs">
          <div>
            <span className="text-slate-500 block">Assessor</span>
            <span className="text-slate-200 font-medium">{assessment.assessor?.full_name || 'Unassigned'}</span>
          </div>
          <div>
            <span className="text-slate-500 block">Assessment Date</span>
            <span className="text-slate-200 font-medium">{assessment.assessment_date}</span>
          </div>
          <div>
            <span className="text-slate-500 block">Scope</span>
            <span className="text-slate-200 font-medium">{assessment.assessment_scope || 'Organization-wide'}</span>
          </div>
          <div>
            <span className="text-slate-500 block">Completed At</span>
            <span className="text-slate-200 font-medium">
              {assessment.completed_at ? new Date(assessment.completed_at).toLocaleString() : 'In Evaluation'}
            </span>
          </div>
        </div>

        {/* Evaluation Summary & Limitations */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-slate-800/80 text-xs">
          <div className="space-y-1">
            <span className="font-semibold text-slate-400 uppercase tracking-wider text-[10px]">
              Assessor Summary &amp; Findings
            </span>
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-slate-300 whitespace-pre-wrap">
              {assessment.summary || 'No summary notes documented.'}
            </div>
          </div>

          <div className="space-y-1">
            <span className="font-semibold text-slate-400 uppercase tracking-wider text-[10px]">
              Scope Limitations &amp; Exclusions
            </span>
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-slate-400 whitespace-pre-wrap">
              {assessment.limitations || 'None documented.'}
            </div>
          </div>
        </div>
      </div>

      {/* Linked Evidence Section */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <Paperclip className="w-4 h-4 text-indigo-400" /> Linked Evidence Artifacts
            </h2>
            <p className="text-xs text-slate-400">
              Evidence items supporting this control assessment conclusion.
            </p>
          </div>
          {isEditable && canAssess && (
            <button
              onClick={() => setShowLinkEvidenceModal(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-indigo-300 rounded-lg text-xs font-medium transition-colors"
            >
              <Plus className="w-3.5 h-3.5" /> Link Evidence
            </button>
          )}
        </div>

        {assessment.evidence_links && assessment.evidence_links.length > 0 ? (
          <div className="divide-y divide-slate-800 border border-slate-800 rounded-lg overflow-hidden">
            {assessment.evidence_links.map((link) => (
              <div
                key={link.id}
                className="p-3 bg-slate-950/60 flex items-center justify-between gap-4 text-xs"
              >
                <div className="flex items-center gap-3">
                  <FileText className="w-4 h-4 text-indigo-400 shrink-0" />
                  <div>
                    <div className="font-semibold text-slate-200">
                      {link.evidence?.title || link.evidence?.original_filename}
                    </div>
                    <div className="text-slate-500 font-mono text-[11px]">
                      {link.evidence?.file_extension.toUpperCase()} &bull; {link.evidence?.status} &bull; SHA-256: {link.evidence?.sha256_hash.slice(0, 12)}...
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span className="text-[11px] text-slate-500">
                    Linked: {new Date(link.created_at).toLocaleDateString()}
                  </span>
                  {isEditable && canAssess && (
                    <button
                      onClick={() => unlinkEvidenceMutation.mutate(link.evidence_id)}
                      className="p-1 text-rose-400 hover:text-rose-300 hover:bg-rose-950/50 rounded transition-colors"
                      title="Unlink evidence"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-6 bg-slate-950/40 rounded-lg border border-dashed border-slate-800 text-xs text-slate-500">
            No evidence artifacts linked to this assessment yet.
          </div>
        )}
      </div>

      {/* Deficiency Findings Section */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-400" /> Deficiency Findings
            </h2>
            <p className="text-xs text-slate-400">
              Gaps and vulnerabilities identified during this assessment.
            </p>
          </div>
          {canAssess && (
            <button
              onClick={() => setShowLogFindingModal(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-rose-600/90 hover:bg-rose-500 text-white rounded-lg text-xs font-medium transition-colors"
            >
              <Plus className="w-3.5 h-3.5" /> Log Deficiency Finding
            </button>
          )}
        </div>

        {assessmentFindings.length > 0 ? (
          <div className="grid grid-cols-1 gap-3">
            {assessmentFindings.map((f) => (
              <div
                key={f.id}
                onClick={() => navigate(`/findings/${f.id}`)}
                className="group bg-slate-950/80 hover:bg-slate-800/60 border border-slate-800 p-4 rounded-lg cursor-pointer transition-all flex items-center justify-between gap-4"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-950 text-rose-300 border border-rose-800">
                      {f.severity}
                    </span>
                    <span className="text-[11px] font-mono text-slate-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                      Risk: {f.risk_score}/25 ({f.risk_band})
                    </span>
                    <span className="text-[11px] font-semibold text-slate-300">
                      {f.status}
                    </span>
                  </div>
                  <h4 className="text-sm font-semibold text-slate-200 group-hover:text-indigo-300 transition-colors">
                    {f.title}
                  </h4>
                  <p className="text-xs text-slate-400 line-clamp-1">{f.recommendation}</p>
                </div>

                <ExternalLink className="w-4 h-4 text-slate-500 group-hover:text-indigo-400 transition-colors" />
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-6 bg-slate-950/40 rounded-lg border border-dashed border-slate-800 text-xs text-slate-500">
            No deficiency findings logged for this assessment.
          </div>
        )}
      </div>

      {/* Complete Assessment Modal */}
      {showCompleteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-xs">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" /> Complete Control Assessment
            </h3>
            <p className="text-xs text-slate-400">
              Document your authoritative conclusion based on verified evidence. Once completed, assessment results are permanently recorded and cannot be mutated.
            </p>

            <div className="space-y-3 text-sm">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Authoritative Conclusion <span className="text-rose-400">*</span>
                </label>
                <select
                  value={completeConclusion}
                  onChange={(e) => setCompleteConclusion(e.target.value as AssessmentConclusion)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 text-sm focus:outline-hidden focus:border-indigo-500"
                >
                  <option value="EFFECTIVE">EFFECTIVE &mdash; Control is fully implemented and operating effectively</option>
                  <option value="PARTIALLY_EFFECTIVE">PARTIALLY EFFECTIVE &mdash; Control is active but contains partial gaps</option>
                  <option value="INEFFECTIVE">INEFFECTIVE &mdash; Control is non-functional or severely deficient</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Assessment Summary / Conclusion Rationale <span className="text-rose-400">*</span>
                </label>
                <textarea
                  rows={4}
                  required
                  placeholder="Summarize evidence inspected, testing procedures executed, and rationale for conclusion..."
                  value={completeSummary}
                  onChange={(e) => setCompleteSummary(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-slate-200 text-sm focus:outline-hidden focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Scope Limitations / Exclusions
                </label>
                <input
                  type="text"
                  placeholder="e.g. Evaluated cloud systems only"
                  value={completeLimitations}
                  onChange={(e) => setCompleteLimitations(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 text-sm focus:outline-hidden focus:border-indigo-500"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setShowCompleteModal(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-lg"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => completeMutation.mutate()}
                disabled={!completeSummary.trim() || completeMutation.isPending}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg disabled:opacity-50"
              >
                {completeMutation.isPending ? 'Finalizing...' : 'Finalize & Sign Assessment'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Link Evidence Modal */}
      {showLinkEvidenceModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-xs">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <Paperclip className="w-4 h-4 text-indigo-400" /> Link Evidence Item
            </h3>
            <p className="text-xs text-slate-400">
              Select an uploaded evidence artifact belonging to this control.
            </p>

            <select
              value={selectedEvidenceId}
              onChange={(e) => setSelectedEvidenceId(Number(e.target.value))}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 text-sm focus:outline-hidden focus:border-indigo-500"
            >
              <option value="">-- Choose evidence artifact --</option>
              {availableEvidence.map((ev) => (
                <option key={ev.id} value={ev.id}>
                  {ev.title || ev.original_filename} ({ev.status})
                </option>
              ))}
            </select>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setShowLinkEvidenceModal(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-lg"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={!selectedEvidenceId || linkEvidenceMutation.isPending}
                onClick={() => linkEvidenceMutation.mutate(Number(selectedEvidenceId))}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg disabled:opacity-50"
              >
                Link Artifact
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Log Finding Modal */}
      {showLogFindingModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-xs">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-rose-400" /> Log Deficiency Finding
            </h3>

            <form onSubmit={handleLogFinding} className="space-y-3 text-sm">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Finding Title <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. MFA bypass vulnerability on admin portal"
                  value={findingTitle}
                  onChange={(e) => setFindingTitle(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 text-sm focus:outline-hidden focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Finding Type</label>
                  <select
                    value={findingType}
                    onChange={(e) => setFindingType(e.target.value as FindingType)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 text-sm focus:outline-hidden"
                  >
                    <option value="CONTROL_GAP">Control Gap</option>
                    <option value="EVIDENCE_GAP">Evidence Gap</option>
                    <option value="POLICY_GAP">Policy Gap</option>
                    <option value="PROCESS_GAP">Process Gap</option>
                    <option value="TECHNICAL_GAP">Technical Gap</option>
                    <option value="OTHER">Other</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Severity</label>
                  <select
                    value={findingSeverity}
                    onChange={(e) => setFindingSeverity(e.target.value as FindingSeverity)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 text-sm focus:outline-hidden"
                  >
                    <option value="CRITICAL">Critical</option>
                    <option value="HIGH">High</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="LOW">Low</option>
                    <option value="INFORMATIONAL">Informational</option>
                  </select>
                </div>
              </div>

              {/* 5x5 Deterministic Risk preview */}
              <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg grid grid-cols-3 gap-3 items-center">
                <div>
                  <label className="block text-[10px] font-semibold text-slate-400">Impact (1-5)</label>
                  <input
                    type="number"
                    min={1}
                    max={5}
                    value={findingImpact}
                    onChange={(e) => setFindingImpact(Number(e.target.value))}
                    className="w-full bg-slate-900 border border-slate-800 rounded px-2 py-1 text-slate-200 text-xs"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-semibold text-slate-400">Likelihood (1-5)</label>
                  <input
                    type="number"
                    min={1}
                    max={5}
                    value={findingLikelihood}
                    onChange={(e) => setFindingLikelihood(Number(e.target.value))}
                    className="w-full bg-slate-900 border border-slate-800 rounded px-2 py-1 text-slate-200 text-xs"
                  />
                </div>
                <div className="text-right">
                  <div className="text-[10px] text-slate-500">Risk Score</div>
                  <div className="text-sm font-bold text-indigo-400">
                    {findingImpact * findingLikelihood} / 25
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Description <span className="text-rose-400">*</span>
                </label>
                <textarea
                  rows={2}
                  required
                  placeholder="Detailed description of the deficiency..."
                  value={findingDesc}
                  onChange={(e) => setFindingDesc(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200 text-sm focus:outline-hidden"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Recommendation <span className="text-rose-400">*</span>
                </label>
                <textarea
                  rows={2}
                  required
                  placeholder="Recommended remediation steps..."
                  value={findingRecommendation}
                  onChange={(e) => setFindingRecommendation(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200 text-sm focus:outline-hidden"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Remediation Due Date</label>
                <input
                  type="date"
                  value={findingDueDate}
                  onChange={(e) => setFindingDueDate(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 text-sm focus:outline-hidden"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowLogFindingModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createFindingMutation.isPending}
                  className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold rounded-lg disabled:opacity-50"
                >
                  Log Finding
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
export default AssessmentDetailPage;
