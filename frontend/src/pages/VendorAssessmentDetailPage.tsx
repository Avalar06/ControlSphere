import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  Check,
  CheckCircle2,
  Clock,
  FileText,
  Lock,
  RefreshCw,
  Save,
  Send,
  ShieldCheck,
  ThumbsDown,
  ThumbsUp,
  XCircle,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { tprmService } from '../lib/tprmService';
import type {
  VendorAssessment,
  VendorAssessmentItemUpdate,
  VendorAssessmentStatus,
  VendorResponseStatus,
} from '../types';

export const VendorAssessmentDetailPage: React.FC = () => {
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const id = Number(assessmentId);
  const navigate = useNavigate();
  const { hasRole, user: currentUser } = useAuth();

  const canAssess = hasRole('ADMIN', 'GRC_ANALYST', 'SECURITY_ANALYST', 'MANAGER');
  const canApprove = hasRole('ADMIN', 'MANAGER');

  const [loading, setLoading] = useState(true);
  const [assessment, setAssessment] = useState<VendorAssessment | null>(null);

  // Local questionnaire edit buffer: item_id -> VendorAssessmentItemUpdate
  const [itemUpdates, setItemUpdates] = useState<Record<number, VendorAssessmentItemUpdate>>({});
  const [saveLoading, setSaveLoading] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  // Workflow Action Modals
  const [showApproveModal, setShowApproveModal] = useState(false);
  const [approveNotes, setApproveNotes] = useState('');
  const [approveLoading, setApproveLoading] = useState(false);

  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectionReason, setRejectionReason] = useState('');
  const [rejectNotes, setRejectNotes] = useState('');
  const [rejectLoading, setRejectLoading] = useState(false);

  const fetchAssessment = async () => {
    if (!id) return;
    setLoading(true);
    setActionError(null);
    try {
      const data = await tprmService.getVendorAssessment(id);
      setAssessment(data);

      // Initialize buffer with existing response values
      const initialBuffer: Record<number, VendorAssessmentItemUpdate> = {};
      if (data.items) {
        for (const item of data.items) {
          initialBuffer[item.id] = {
            response_status: item.response_status,
            vendor_response_text: item.vendor_response_text || '',
            assessor_notes: item.assessor_notes || '',
          };
        }
      }
      setItemUpdates(initialBuffer);
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Failed to load vendor assessment.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAssessment();
  }, [id]);

  const isImmutable =
    assessment?.status === 'APPROVED' || assessment?.status === 'SUPERSEDED';
  const isDraft = assessment?.status === 'DRAFT';
  const isSubmitted = assessment?.status === 'SUBMITTED';
  const isInReview = assessment?.status === 'IN_REVIEW';

  // Live Score Calculator based on current buffer
  const calculateLiveScore = (): number => {
    if (!assessment?.items || assessment.items.length === 0) return 100.0;
    let totalApplicableWeight = 0.0;
    let weightedSum = 0.0;

    for (const item of assessment.items) {
      const update = itemUpdates[item.id];
      const status = update?.response_status ?? item.response_status;
      const weight = Math.max(0.1, item.weight);

      if (status === 'NOT_APPLICABLE') continue;

      totalApplicableWeight += weight;
      let ratio = 0.0;
      if (status === 'COMPLIANT') ratio = 1.0;
      else if (status === 'PARTIALLY_COMPLIANT') ratio = 0.5;

      weightedSum += weight * ratio;
    }

    if (totalApplicableWeight === 0.0) return 100.0;
    return Math.round((weightedSum / totalApplicableWeight) * 1000) / 10;
  };

  const handleResponseChange = (itemId: number, newStatus: VendorResponseStatus) => {
    if (isImmutable) return;
    setItemUpdates((prev) => ({
      ...prev,
      [itemId]: {
        ...prev[itemId],
        response_status: newStatus,
      },
    }));
  };

  const handleTextChange = (
    itemId: number,
    field: 'vendor_response_text' | 'assessor_notes',
    value: string
  ) => {
    if (isImmutable) return;
    setItemUpdates((prev) => ({
      ...prev,
      [itemId]: {
        ...prev[itemId],
        [field]: value,
      },
    }));
  };

  // Save changes to backend
  const handleSaveChanges = async () => {
    if (!assessment || isImmutable) return;
    setSaveLoading(true);
    setActionError(null);
    setSaveMessage(null);
    try {
      const updated = await tprmService.updateAssessmentItems(assessment.id, itemUpdates);
      setAssessment(updated);
      setSaveMessage('Questionnaire responses saved and score recalculated.');
      setTimeout(() => setSaveMessage(null), 4000);
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Failed to save assessment items.');
    } finally {
      setSaveLoading(false);
    }
  };

  // Submit assessment (DRAFT -> SUBMITTED)
  const handleSubmit = async () => {
    if (!assessment) return;
    if (!window.confirm('Submit this questionnaire for security review?')) return;
    setSaveLoading(true);
    setActionError(null);
    try {
      // First save any unsaved buffer changes
      await tprmService.updateAssessmentItems(assessment.id, itemUpdates);
      const submitted = await tprmService.submitAssessment(assessment.id);
      setAssessment(submitted);
      setSaveMessage('Assessment submitted for review.');
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Failed to submit assessment.');
    } finally {
      setSaveLoading(false);
    }
  };

  // Start Review (SUBMITTED -> IN_REVIEW)
  const handleStartReview = async () => {
    if (!assessment) return;
    setSaveLoading(true);
    setActionError(null);
    try {
      const inReview = await tprmService.startAssessmentReview(assessment.id);
      setAssessment(inReview);
      setSaveMessage('Assessment moved to IN_REVIEW.');
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Failed to transition assessment to review.');
    } finally {
      setSaveLoading(false);
    }
  };

  // Approve Assessment (IN_REVIEW -> APPROVED)
  const handleApprove = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!assessment) return;
    setApproveLoading(true);
    setActionError(null);
    try {
      const approved = await tprmService.approveAssessment(assessment.id, {
        review_notes: approveNotes.trim() || undefined,
      });
      setAssessment(approved);
      setShowApproveModal(false);
      setApproveNotes('');
      setSaveMessage('Assessment approved! Vendor residual risk score updated.');
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Failed to approve assessment.');
    } finally {
      setApproveLoading(false);
    }
  };

  // Reject Assessment (IN_REVIEW -> DRAFT)
  const handleReject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!assessment) return;
    if (rejectionReason.trim().length < 5) {
      setActionError('Rejection reason must be at least 5 characters.');
      return;
    }

    setRejectLoading(true);
    setActionError(null);
    try {
      const rejected = await tprmService.rejectAssessment(assessment.id, {
        rejection_reason: rejectionReason.trim(),
        review_notes: rejectNotes.trim() || undefined,
      });
      setAssessment(rejected);
      setShowRejectModal(false);
      setRejectionReason('');
      setRejectNotes('');
      setSaveMessage('Assessment rejected and returned to DRAFT.');
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Failed to reject assessment.');
    } finally {
      setRejectLoading(false);
    }
  };

  if (loading && !assessment) {
    return (
      <div className="py-20 text-center text-slate-500">
        <RefreshCw size={24} className="animate-spin mx-auto mb-3 text-indigo-400" />
        <span>Loading assessment workspace...</span>
      </div>
    );
  }

  if (!assessment) {
    return (
      <div className="p-8 text-center bg-slate-900 border border-slate-800 rounded-lg">
        <AlertCircle size={32} className="mx-auto mb-2 text-red-400" />
        <h2 className="text-lg font-bold text-slate-100">Assessment Not Found</h2>
        <button
          onClick={() => navigate('/vendors')}
          className="mt-4 px-4 py-2 text-xs font-semibold rounded-md bg-indigo-600 text-white"
        >
          Return to Vendor Portfolio
        </button>
      </div>
    );
  }

  const liveScore = calculateLiveScore();
  const isAssessor = currentUser?.id === assessment.assessor_id;

  const getStatusBadge = (status: VendorAssessmentStatus) => {
    switch (status) {
      case 'APPROVED':
        return (
          <span className="px-2.5 py-1 rounded text-xs font-bold bg-emerald-950 text-emerald-400 border border-emerald-800 flex items-center gap-1.5">
            <CheckCircle2 size={13} />
            <span>APPROVED</span>
          </span>
        );
      case 'IN_REVIEW':
        return (
          <span className="px-2.5 py-1 rounded text-xs font-bold bg-purple-950 text-purple-400 border border-purple-800 flex items-center gap-1.5">
            <Clock size={13} />
            <span>IN REVIEW</span>
          </span>
        );
      case 'SUBMITTED':
        return (
          <span className="px-2.5 py-1 rounded text-xs font-bold bg-blue-950 text-blue-400 border border-blue-800 flex items-center gap-1.5">
            <Send size={13} />
            <span>SUBMITTED</span>
          </span>
        );
      case 'REJECTED':
        return (
          <span className="px-2.5 py-1 rounded text-xs font-bold bg-red-950 text-red-400 border border-red-800 flex items-center gap-1.5">
            <XCircle size={13} />
            <span>REJECTED</span>
          </span>
        );
      case 'SUPERSEDED':
        return (
          <span className="px-2.5 py-1 rounded text-xs font-bold bg-slate-800 text-slate-400 border border-slate-700 flex items-center gap-1.5">
            <Lock size={13} />
            <span>SUPERSEDED</span>
          </span>
        );
      case 'DRAFT':
      default:
        return (
          <span className="px-2.5 py-1 rounded text-xs font-bold bg-slate-800 text-slate-300 border border-slate-700 flex items-center gap-1.5">
            <FileText size={13} />
            <span>DRAFT</span>
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Back Link */}
      <div>
        <Link
          to={`/vendors/${assessment.vendor_id}`}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-indigo-400 transition-colors mb-3"
        >
          <ArrowLeft size={14} />
          <span>Back to Vendor Profile</span>
        </Link>

        {/* Assessment Header Card */}
        <div className="bg-slate-900/90 p-5 rounded-xl border border-slate-800 shadow-xs space-y-4">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            <div className="space-y-1">
              <div className="flex flex-wrap items-center gap-2.5">
                <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
                  {assessment.assessment_code}
                </span>
                <h1 className="text-2xl font-bold text-slate-100 tracking-tight">
                  {assessment.title}
                </h1>
                {getStatusBadge(assessment.status)}
              </div>

              <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400 pt-1">
                <span>
                  Type:{' '}
                  <strong className="text-slate-200">
                    {assessment.assessment_type.replace('_', ' ')}
                  </strong>
                </span>
                <span>&bull;</span>
                <span>
                  Assessor:{' '}
                  <strong className="text-slate-200">
                    {assessment.assessor?.full_name || 'N/A'}
                  </strong>
                </span>
                {assessment.reviewer && (
                  <>
                    <span>&bull;</span>
                    <span>
                      Reviewer:{' '}
                      <strong className="text-slate-200">
                        {assessment.reviewer.full_name}
                      </strong>
                    </span>
                  </>
                )}
                {assessment.valid_until && (
                  <>
                    <span>&bull;</span>
                    <span>
                      Valid Until:{' '}
                      <strong className="text-slate-200">
                        {new Date(assessment.valid_until).toLocaleDateString()}
                      </strong>
                    </span>
                  </>
                )}
              </div>
            </div>

            {/* Score & Gauge */}
            <div className="flex items-center gap-3 p-3 rounded-lg bg-slate-950 border border-slate-800 min-w-[200px] justify-between">
              <div>
                <div className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">
                  Assessment Score
                </div>
                <div className="text-2xl font-mono font-bold text-emerald-400">
                  {liveScore.toFixed(1)}%
                </div>
              </div>

              <div className="text-right text-[11px] text-slate-400">
                <div>Items: {assessment.items?.length || 0}</div>
                <div className="text-indigo-400 font-medium">
                  {isImmutable ? 'Authoritative' : 'Live Preview'}
                </div>
              </div>
            </div>
          </div>

          {/* Rejection / Review Notes Callout */}
          {assessment.rejection_reason && (
            <div className="p-3.5 rounded-lg bg-red-950/40 border border-red-800/60 text-xs text-red-300">
              <div className="font-semibold flex items-center gap-1.5 mb-1">
                <AlertTriangle size={14} className="text-red-400" />
                <span>Assessment Rejection Reason:</span>
              </div>
              <p>{assessment.rejection_reason}</p>
            </div>
          )}

          {assessment.review_notes && isImmutable && (
            <div className="p-3.5 rounded-lg bg-emerald-950/40 border border-emerald-800/60 text-xs text-emerald-300">
              <div className="font-semibold flex items-center gap-1.5 mb-1">
                <CheckCircle2 size={14} className="text-emerald-400" />
                <span>Reviewer Approval Notes:</span>
              </div>
              <p>{assessment.review_notes}</p>
            </div>
          )}

          {/* Feedback alerts */}
          {saveMessage && (
            <div className="p-3 rounded-md bg-emerald-950/80 border border-emerald-800 text-xs text-emerald-300 font-medium flex items-center gap-2">
              <Check size={14} />
              <span>{saveMessage}</span>
            </div>
          )}

          {actionError && (
            <div className="p-3 rounded-md bg-red-950/80 border border-red-800 text-xs text-red-300 font-medium flex items-center gap-2">
              <AlertCircle size={14} />
              <span>{actionError}</span>
            </div>
          )}

          {/* Lifecycle Action Bar */}
          <div className="pt-2 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-3">
            <div className="text-xs text-slate-400">
              {isDraft && (
                <span>
                  Questionnaire is currently in <strong>DRAFT</strong>. Complete answers and submit for review.
                </span>
              )}
              {isSubmitted && (
                <span>
                  Assessment has been <strong>SUBMITTED</strong>. An independent reviewer must initiate review.
                </span>
              )}
              {isInReview && (
                <span>
                  Assessment is <strong>IN REVIEW</strong>. Four-eyes separation of duties enforced.
                </span>
              )}
              {isImmutable && (
                <span className="flex items-center gap-1 text-slate-400">
                  <Lock size={12} className="text-amber-400" />
                  <span>Permanent historical record. Responses are immutable.</span>
                </span>
              )}
            </div>

            <div className="flex items-center gap-2">
              {/* Draft actions */}
              {isDraft && canAssess && (
                <>
                  <button
                    onClick={handleSaveChanges}
                    disabled={saveLoading}
                    className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold rounded-md bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors disabled:opacity-50"
                  >
                    <Save size={13} />
                    <span>{saveLoading ? 'Saving...' : 'Save Draft'}</span>
                  </button>

                  <button
                    onClick={handleSubmit}
                    disabled={saveLoading}
                    className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold rounded-md bg-blue-600 hover:bg-blue-500 text-white transition-colors disabled:opacity-50"
                  >
                    <Send size={13} />
                    <span>Submit for Review</span>
                  </button>
                </>
              )}

              {/* Submitted actions */}
              {isSubmitted && canApprove && (
                <button
                  onClick={handleStartReview}
                  disabled={saveLoading}
                  className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold rounded-md bg-purple-600 hover:bg-purple-500 text-white transition-colors disabled:opacity-50"
                >
                  <Clock size={13} />
                  <span>Start Review</span>
                </button>
              )}

              {/* In-Review actions */}
              {isInReview && canApprove && (
                <>
                  <button
                    onClick={() => setShowRejectModal(true)}
                    className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold rounded-md bg-red-900/80 hover:bg-red-800 text-red-200 border border-red-700 transition-colors"
                  >
                    <ThumbsDown size={13} />
                    <span>Reject</span>
                  </button>

                  <button
                    onClick={() => setShowApproveModal(true)}
                    disabled={isAssessor}
                    title={
                      isAssessor
                        ? 'Four-eyes separation of duties: The assessor cannot approve their own assessment.'
                        : 'Approve Assessment'
                    }
                    className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold rounded-md bg-emerald-600 hover:bg-emerald-500 text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    <ThumbsUp size={13} />
                    <span>Approve Assessment</span>
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Questionnaire Line Items */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
            <FileText size={16} className="text-indigo-400" />
            <span>Questionnaire Assessment Items ({assessment.items?.length || 0})</span>
          </h3>

          {!isImmutable && (
            <span className="text-xs text-slate-400 font-mono">
              Live Score: <strong className="text-emerald-400">{liveScore.toFixed(1)}%</strong>
            </span>
          )}
        </div>

        <div className="space-y-3">
          {!assessment.items || assessment.items.length === 0 ? (
            <div className="p-8 text-center bg-slate-900 border border-slate-800 rounded-lg text-slate-500 text-xs">
              No questions found in this assessment questionnaire.
            </div>
          ) : (
            assessment.items.map((item) => {
              const currentStatus =
                itemUpdates[item.id]?.response_status ?? item.response_status;
              const currentVendorText =
                itemUpdates[item.id]?.vendor_response_text ?? item.vendor_response_text ?? '';
              const currentAssessorNotes =
                itemUpdates[item.id]?.assessor_notes ?? item.assessor_notes ?? '';

              return (
                <div
                  key={item.id}
                  className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 space-y-3"
                >
                  <div className="flex flex-col md:flex-row md:items-start justify-between gap-3">
                    <div className="space-y-1 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-800 text-indigo-300 border border-slate-700">
                          {item.question_key}
                        </span>
                        <span className="text-xs text-slate-400">
                          Weight: <strong>{item.weight}</strong>
                        </span>
                      </div>
                      <h4 className="text-xs font-semibold text-slate-100">
                        {item.question_text}
                      </h4>
                    </div>

                    {/* Response Selection Buttons */}
                    <div className="flex flex-wrap items-center gap-1.5 shrink-0">
                      <button
                        type="button"
                        disabled={isImmutable}
                        onClick={() => handleResponseChange(item.id, 'COMPLIANT')}
                        className={`px-2.5 py-1 rounded text-xs font-semibold transition-all ${
                          currentStatus === 'COMPLIANT'
                            ? 'bg-emerald-600 text-white shadow-xs'
                            : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200'
                        } ${isImmutable ? 'cursor-not-allowed opacity-90' : ''}`}
                      >
                        Compliant (100%)
                      </button>

                      <button
                        type="button"
                        disabled={isImmutable}
                        onClick={() => handleResponseChange(item.id, 'PARTIALLY_COMPLIANT')}
                        className={`px-2.5 py-1 rounded text-xs font-semibold transition-all ${
                          currentStatus === 'PARTIALLY_COMPLIANT'
                            ? 'bg-amber-600 text-white shadow-xs'
                            : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200'
                        } ${isImmutable ? 'cursor-not-allowed opacity-90' : ''}`}
                      >
                        Partial (50%)
                      </button>

                      <button
                        type="button"
                        disabled={isImmutable}
                        onClick={() => handleResponseChange(item.id, 'NON_COMPLIANT')}
                        className={`px-2.5 py-1 rounded text-xs font-semibold transition-all ${
                          currentStatus === 'NON_COMPLIANT'
                            ? 'bg-red-600 text-white shadow-xs'
                            : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200'
                        } ${isImmutable ? 'cursor-not-allowed opacity-90' : ''}`}
                      >
                        Non-Compliant (0%)
                      </button>

                      <button
                        type="button"
                        disabled={isImmutable}
                        onClick={() => handleResponseChange(item.id, 'NOT_APPLICABLE')}
                        className={`px-2.5 py-1 rounded text-xs font-semibold transition-all ${
                          currentStatus === 'NOT_APPLICABLE'
                            ? 'bg-slate-600 text-white shadow-xs'
                            : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200'
                        } ${isImmutable ? 'cursor-not-allowed opacity-90' : ''}`}
                      >
                        N/A (Exclude)
                      </button>
                    </div>
                  </div>

                  {/* Text Details & Assessor Notes */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 border-t border-slate-800/60 text-xs">
                    <div>
                      <label className="block text-[11px] text-slate-400 font-medium mb-1">
                        Vendor Explanation / Control Statement
                      </label>
                      <textarea
                        rows={2}
                        disabled={isImmutable}
                        placeholder="Vendor's documented response or control narrative..."
                        value={currentVendorText}
                        onChange={(e) =>
                          handleTextChange(item.id, 'vendor_response_text', e.target.value)
                        }
                        className="w-full px-2.5 py-1.5 text-xs rounded-md bg-slate-950 border border-slate-800 text-slate-200 placeholder-slate-600 focus:outline-hidden focus:border-indigo-500 disabled:opacity-60"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] text-slate-400 font-medium mb-1">
                        Assessor Evaluation &amp; Verification Notes
                      </label>
                      <textarea
                        rows={2}
                        disabled={isImmutable}
                        placeholder="Internal assessor verification observations, evidence links..."
                        value={currentAssessorNotes}
                        onChange={(e) =>
                          handleTextChange(item.id, 'assessor_notes', e.target.value)
                        }
                        className="w-full px-2.5 py-1.5 text-xs rounded-md bg-slate-950 border border-slate-800 text-slate-200 placeholder-slate-600 focus:outline-hidden focus:border-indigo-500 disabled:opacity-60"
                      />
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Approve Modal */}
      {showApproveModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-xl bg-slate-900 border border-slate-800 shadow-xl overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldCheck size={18} className="text-emerald-400" />
                <h3 className="text-base font-bold text-slate-100">
                  Four-Eyes Assessment Approval
                </h3>
              </div>
              <button
                onClick={() => setShowApproveModal(false)}
                className="text-slate-400 hover:text-slate-200 text-lg leading-none"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleApprove} className="p-6 space-y-4">
              <p className="text-xs text-slate-300 leading-relaxed">
                By approving this assessment, the questionnaire score of{' '}
                <strong className="text-emerald-400">{liveScore.toFixed(1)}%</strong> will be
                locked permanently into the historical record and will immediately update the vendor's
                residual risk telemetry.
              </p>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Reviewer Approval Notes (Optional)
                </label>
                <textarea
                  rows={3}
                  placeholder="Record summary of verification, SOC 2 alignment, or approval notes..."
                  value={approveNotes}
                  onChange={(e) => setApproveNotes(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-md bg-slate-950 border border-slate-800 text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
                />
              </div>

              <div className="pt-2 flex items-center justify-end gap-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowApproveModal(false)}
                  className="px-4 py-2 text-xs font-medium rounded-md bg-slate-800 text-slate-300 hover:bg-slate-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={approveLoading}
                  className="px-4 py-2 text-xs font-semibold rounded-md bg-emerald-600 hover:bg-emerald-500 text-white disabled:opacity-50"
                >
                  {approveLoading ? 'Approving...' : 'Confirm Approval'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Reject Modal */}
      {showRejectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-xl bg-slate-900 border border-slate-800 shadow-xl overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle size={18} className="text-red-400" />
                <h3 className="text-base font-bold text-slate-100">
                  Reject Assessment Questionnaire
                </h3>
              </div>
              <button
                onClick={() => setShowRejectModal(false)}
                className="text-slate-400 hover:text-slate-200 text-lg leading-none"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleReject} className="p-6 space-y-4">
              <p className="text-xs text-slate-300 leading-relaxed">
                Rejecting this assessment will return it to <strong>DRAFT</strong> status, allowing
                the assessor and vendor to revise responses and provide required remediation evidence.
              </p>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Mandatory Rejection Reason <span className="text-red-400">*</span>
                </label>
                <textarea
                  required
                  rows={3}
                  placeholder="Specify why this assessment was rejected (e.g. missing SOC 2 evidence for MFA)..."
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-md bg-slate-950 border border-slate-800 text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Additional Notes (Optional)
                </label>
                <textarea
                  rows={2}
                  placeholder="Additional guidance for the assessor..."
                  value={rejectNotes}
                  onChange={(e) => setRejectNotes(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-md bg-slate-950 border border-slate-800 text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
                />
              </div>

              <div className="pt-2 flex items-center justify-end gap-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowRejectModal(false)}
                  className="px-4 py-2 text-xs font-medium rounded-md bg-slate-800 text-slate-300 hover:bg-slate-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={rejectLoading}
                  className="px-4 py-2 text-xs font-semibold rounded-md bg-red-600 hover:bg-red-500 text-white disabled:opacity-50"
                >
                  {rejectLoading ? 'Rejecting...' : 'Confirm Rejection'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
