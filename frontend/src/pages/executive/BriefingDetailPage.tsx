import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ChevronRight,
  Download,
  CheckCircle2,
  AlertCircle,
  Send,
  RefreshCw,
  TrendingUp,
} from 'lucide-react';
import { executiveService } from '../../lib/executiveService';
import { BriefingReviewModal } from '../../components/executive/BriefingReviewModal';
import type { ExecutiveBriefing } from '../../types';
import { useAuth } from '../../context/AuthContext';

export const BriefingDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();

  const [briefing, setBriefing] = useState<ExecutiveBriefing | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [isReviewOpen, setIsReviewOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const briefingId = Number(id);

  const loadBriefing = async () => {
    try {
      const data = await executiveService.getBriefing(briefingId);
      setBriefing(data);
    } catch (err) {
      console.error('Failed to load briefing:', err);
      setError('Briefing not found or access denied.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBriefing();
  }, [briefingId]);

  const handleSubmitForReview = async () => {
    setActionLoading(true);
    setError(null);
    try {
      const updated = await executiveService.submitBriefing(briefingId);
      setBriefing(updated);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to submit briefing');
    } finally {
      setActionLoading(false);
    }
  };

  const handleExport = async (format: 'PDF' | 'JSON') => {
    setActionLoading(true);
    try {
      const artifact = await executiveService.exportBriefing(briefingId, format);
      await executiveService.downloadExport(artifact.id, artifact.original_filename);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to generate export artifact');
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <RefreshCw className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  if (!briefing) {
    return (
      <div className="p-8 text-center">
        <p className="text-slate-500">{error || 'Briefing not found.'}</p>
        <Link to="/executive/briefings" className="mt-4 inline-block text-indigo-600 font-semibold text-sm">
          Return to Briefings
        </Link>
      </div>
    );
  }

  const isDraft = briefing.status === 'DRAFT';
  const isSubmitted = briefing.status === 'SUBMITTED_FOR_REVIEW';
  const canReview = (user?.role === 'ADMIN' || user?.role === 'MANAGER') && user.id !== briefing.generated_by_id;

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <nav className="flex items-center gap-2 text-xs text-slate-500 mb-1">
            <Link to="/executive" className="hover:underline">
              Executive
            </Link>
            <ChevronRight className="h-3 w-3" />
            <Link to="/executive/briefings" className="hover:underline">
              Briefings
            </Link>
            <ChevronRight className="h-3 w-3" />
            <span className="font-semibold text-slate-800 dark:text-slate-200">{briefing.briefing_code}</span>
          </nav>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">{briefing.title}</h1>
            <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800">
              {briefing.status.replace(/_/g, ' ')}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isDraft && (
            <button
              onClick={handleSubmitForReview}
              disabled={actionLoading}
              className="px-3.5 py-2 rounded-xl bg-slate-800 text-white text-xs font-semibold hover:bg-slate-700 shadow-sm flex items-center gap-1.5 disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
              Submit for Sign-Off
            </button>
          )}

          {isSubmitted && canReview && (
            <button
              onClick={() => setIsReviewOpen(true)}
              disabled={actionLoading}
              className="px-3.5 py-2 rounded-xl bg-emerald-600 text-white text-xs font-semibold hover:bg-emerald-500 shadow-sm flex items-center gap-1.5 disabled:opacity-50"
            >
              <CheckCircle2 className="h-4 w-4" />
              Four-Eyes Sign-Off
            </button>
          )}

          <button
            onClick={() => handleExport('PDF')}
            disabled={actionLoading}
            className="px-3.5 py-2 rounded-xl bg-indigo-600 text-white text-xs font-semibold hover:bg-indigo-500 shadow-sm flex items-center gap-1.5 disabled:opacity-50"
          >
            <Download className="h-4 w-4" />
            Export PDF
          </button>

          <button
            onClick={() => handleExport('JSON')}
            disabled={actionLoading}
            className="px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 text-xs font-semibold hover:bg-slate-50 dark:hover:bg-slate-800 shadow-sm disabled:opacity-50"
          >
            JSON
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-rose-50 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-800 flex items-center gap-2 text-xs text-rose-600 dark:text-rose-400">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Main Narrative & Deltas Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {/* Executive Summary Card */}
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-sm">
            <h3 className="font-bold text-slate-900 dark:text-white text-sm mb-2">Executive Summary</h3>
            <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
              {briefing.executive_summary}
            </p>

            {briefing.strategic_recommendations && (
              <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800">
                <h4 className="font-bold text-slate-900 dark:text-white text-xs mb-1">
                  Strategic Recommendations
                </h4>
                <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                  {briefing.strategic_recommendations}
                </p>
              </div>
            )}
          </div>

          {/* Key Achievements & Emerging Risks */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-sm">
              <h4 className="font-bold text-emerald-600 dark:text-emerald-400 text-xs uppercase tracking-wider mb-3">
                Key Achievements
              </h4>
              {briefing.key_achievements.length === 0 ? (
                <p className="text-xs text-slate-400 italic">None noted.</p>
              ) : (
                <ul className="space-y-1.5 text-xs text-slate-600 dark:text-slate-300">
                  {briefing.key_achievements.map((item: string, i: number) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-emerald-500">•</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-sm">
              <h4 className="font-bold text-amber-600 dark:text-amber-400 text-xs uppercase tracking-wider mb-3">
                Emerging Risks
              </h4>
              {briefing.emerging_risks.length === 0 ? (
                <p className="text-xs text-slate-400 italic">None noted.</p>
              ) : (
                <ul className="space-y-1.5 text-xs text-slate-600 dark:text-slate-300">
                  {briefing.emerging_risks.map((item: string, i: number) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-amber-500">•</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>

        {/* Sidebar: Deltas & Sign-Off Info */}
        <div className="space-y-6">
          {/* Deltas Card */}
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-sm text-xs space-y-3">
            <h3 className="font-bold text-slate-900 dark:text-white text-sm pb-2 border-b border-slate-100 dark:border-slate-800 flex items-center gap-1.5">
              <TrendingUp className="h-4 w-4 text-indigo-500" />
              Period-over-Period Deltas
            </h3>

            <div className="flex justify-between items-center py-1">
              <span className="text-slate-500">Posture Score Delta</span>
              <span
                className={`font-bold ${
                  (briefing.period_over_period_deltas?.posture_score_delta || 0) >= 0
                    ? 'text-emerald-500'
                    : 'text-rose-500'
                }`}
              >
                {(briefing.period_over_period_deltas?.posture_score_delta || 0) >= 0 ? '+' : ''}
                {briefing.period_over_period_deltas?.posture_score_delta?.toFixed(1) || '0.0'}%
              </span>
            </div>

            <div className="flex justify-between items-center py-1">
              <span className="text-slate-500">Inherent Risk Delta</span>
              <span className="font-bold text-slate-800 dark:text-slate-200">
                {briefing.period_over_period_deltas?.inherent_risk_delta?.toFixed(1) || '0.0'}
              </span>
            </div>

            <div className="flex justify-between items-center py-1">
              <span className="text-slate-500">Residual Risk Delta</span>
              <span className="font-bold text-slate-800 dark:text-slate-200">
                {briefing.period_over_period_deltas?.residual_risk_delta?.toFixed(1) || '0.0'}
              </span>
            </div>

            <div className="flex justify-between items-center py-1">
              <span className="text-slate-500">Audit Readiness Delta</span>
              <span className="font-bold text-slate-800 dark:text-slate-200">
                {briefing.period_over_period_deltas?.audit_readiness_delta?.toFixed(1) || '0.0'}%
              </span>
            </div>
          </div>

          {/* Sign-Off History Card */}
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-sm text-xs space-y-2">
            <h3 className="font-bold text-slate-900 dark:text-white text-sm pb-2 border-b border-slate-100 dark:border-slate-800">
              Sign-Off Governance
            </h3>

            <div>
              <span className="text-slate-400 block">Reporting Period</span>
              <span className="font-semibold text-slate-800 dark:text-slate-200">
                {briefing.reporting_period_start} to {briefing.reporting_period_end}
              </span>
            </div>

            <div>
              <span className="text-slate-400 block">Created At</span>
              <span className="text-slate-700 dark:text-slate-300">
                {new Date(briefing.created_at).toLocaleString()}
              </span>
            </div>

            {briefing.approved_at && (
              <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
                <span className="text-emerald-500 font-semibold block">Signed Off By Reviewer</span>
                <span className="text-slate-700 dark:text-slate-300">
                  {new Date(briefing.approved_at).toLocaleString()}
                </span>
                {briefing.review_notes && (
                  <p className="mt-1 text-slate-500 italic">"{briefing.review_notes}"</p>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      <BriefingReviewModal
        briefing={briefing}
        isOpen={isReviewOpen}
        onClose={() => setIsReviewOpen(false)}
        onSuccess={loadBriefing}
      />
    </div>
  );
};
