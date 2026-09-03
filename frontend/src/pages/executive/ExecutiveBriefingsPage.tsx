import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  FileText,
  Plus,
  RefreshCw,
  ChevronRight,
  CheckCircle2,
  XCircle,
  Clock,
} from 'lucide-react';
import { executiveService } from '../../lib/executiveService';
import type { ExecutiveBriefing, BriefingStatus, ExecutiveSnapshot } from '../../types';
import { useAuth } from '../../context/AuthContext';

export const ExecutiveBriefingsPage: React.FC = () => {
  const { user } = useAuth();
  const [briefings, setBriefings] = useState<ExecutiveBriefing[]>([]);
  const [snapshots, setSnapshots] = useState<ExecutiveSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<BriefingStatus | undefined>(undefined);
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  // Form states
  const [briefingCode, setBriefingCode] = useState(
    `BRF-${new Date().getFullYear()}-Q${Math.floor((new Date().getMonth() + 3) / 3)}`
  );
  const [title, setTitle] = useState('');
  const [periodStart, setPeriodStart] = useState('2026-07-01');
  const [periodEnd, setPeriodEnd] = useState('2026-09-30');
  const [selectedSnapshotId, setSelectedSnapshotId] = useState<number | null>(null);
  const [executiveSummary, setExecutiveSummary] = useState('');
  const [strategicRecommendations, setStrategicRecommendations] = useState('');
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const canManage = user?.role === 'ADMIN' || user?.role === 'MANAGER' || user?.role === 'GRC_ANALYST';

  const loadData = async () => {
    try {
      const [brfData, snapData] = await Promise.all([
        executiveService.listBriefings({ status: statusFilter }),
        executiveService.listSnapshots(),
      ]);
      setBriefings(brfData);
      setSnapshots(snapData);
      if (snapData.length > 0 && !selectedSnapshotId) {
        setSelectedSnapshotId(snapData[0].id);
      }
    } catch (err) {
      console.error('Failed to load briefings:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [statusFilter]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSnapshotId) {
      setFormError('Please select a reference posture snapshot');
      return;
    }
    setSubmitting(true);
    setFormError(null);

    try {
      await executiveService.generateBriefing({
        briefing_code: briefingCode.trim(),
        title: title.trim(),
        reporting_period_start: periodStart,
        reporting_period_end: periodEnd,
        snapshot_id: selectedSnapshotId,
        executive_summary: executiveSummary.trim(),
        strategic_recommendations: strategicRecommendations.trim() || undefined,
      });
      setIsCreateOpen(false);
      loadData();
    } catch (err: any) {
      setFormError(err?.response?.data?.detail || 'Failed to create briefing draft');
    } finally {
      setSubmitting(false);
    }
  };

  const getStatusBadge = (status: BriefingStatus) => {
    switch (status) {
      case 'APPROVED':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800">
            <CheckCircle2 className="h-3 w-3" /> APPROVED
          </span>
        );
      case 'SUBMITTED_FOR_REVIEW':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-amber-50 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 border border-amber-200 dark:border-amber-800">
            <Clock className="h-3 w-3" /> PENDING SIGN-OFF
          </span>
        );
      case 'REJECTED':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-rose-50 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 border border-rose-200 dark:border-rose-800">
            <XCircle className="h-3 w-3" /> REJECTED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
            DRAFT
          </span>
        );
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <nav className="flex items-center gap-2 text-xs text-slate-500 mb-1">
            <Link to="/executive" className="hover:underline">
              Executive Governance
            </Link>
            <ChevronRight className="h-3 w-3" />
            <span className="font-semibold text-slate-800 dark:text-slate-200">
              Board Briefings
            </span>
          </nav>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
            Executive & Board Briefings
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Periodic cyber-risk summaries with automated period-over-period delta analysis and mandatory Four-Eyes approval.
          </p>
        </div>

        {canManage && (
          <button
            onClick={() => setIsCreateOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-all shadow-sm"
          >
            <Plus className="h-4 w-4" />
            New Executive Briefing
          </button>
        )}
      </div>

      {/* Filter Bar */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2 border-b border-slate-200 dark:border-slate-800 text-xs">
        {(['ALL', 'DRAFT', 'SUBMITTED_FOR_REVIEW', 'APPROVED', 'REJECTED'] as const).map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s === 'ALL' ? undefined : (s as BriefingStatus))}
            className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
              (s === 'ALL' && statusFilter === undefined) || statusFilter === s
                ? 'bg-indigo-600 text-white font-semibold shadow-sm'
                : 'bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800'
            }`}
          >
            {s.replace(/_/g, ' ')}
          </button>
        ))}
      </div>

      {/* Briefings Grid */}
      {loading ? (
        <div className="flex min-h-[300px] items-center justify-center">
          <RefreshCw className="h-6 w-6 animate-spin text-indigo-600" />
        </div>
      ) : briefings.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-200 dark:border-slate-800 p-12 text-center">
          <FileText className="h-10 w-10 text-slate-400 mx-auto mb-3" />
          <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200">No Briefings Found</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            Generate an executive briefing from an existing snapshot to present cyber-risk KPIs and deltas to the board.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {briefings.map((briefing) => (
            <Link
              key={briefing.id}
              to={`/executive/briefings/${briefing.id}`}
              className="group p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm hover:border-indigo-500/60 hover:shadow-md transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="font-mono text-xs font-bold text-indigo-600 dark:text-indigo-400">
                    {briefing.briefing_code}
                  </span>
                  {getStatusBadge(briefing.status)}
                </div>

                <h3 className="font-bold text-slate-900 dark:text-white text-base group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                  {briefing.title}
                </h3>

                <p className="text-xs text-slate-500 dark:text-slate-400 mt-2 line-clamp-2">
                  {briefing.executive_summary}
                </p>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-[11px] text-slate-400">
                <span>Period: <strong>{briefing.reporting_period_start} → {briefing.reporting_period_end}</strong></span>
                {briefing.period_over_period_deltas?.posture_score_delta !== undefined && (
                  <span
                    className={`font-bold ${
                      briefing.period_over_period_deltas.posture_score_delta >= 0
                        ? 'text-emerald-500'
                        : 'text-rose-500'
                    }`}
                  >
                    {briefing.period_over_period_deltas.posture_score_delta >= 0 ? '+' : ''}
                    {briefing.period_over_period_deltas.posture_score_delta.toFixed(1)}%
                  </span>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Create Briefing Modal */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="w-full max-w-lg rounded-2xl bg-white dark:bg-slate-900 p-6 shadow-2xl border border-slate-200 dark:border-slate-800 my-8">
            <h3 className="font-bold text-slate-900 dark:text-white text-lg mb-4">
              Create Executive Briefing Draft
            </h3>

            {formError && (
              <p className="p-3 mb-4 rounded-lg bg-rose-50 dark:bg-rose-950/50 text-xs text-rose-600 border border-rose-200">
                {formError}
              </p>
            )}

            <form onSubmit={handleCreate} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Briefing Code *
                  </label>
                  <input
                    type="text"
                    required
                    value={briefingCode}
                    onChange={(e) => setBriefingCode(e.target.value)}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white font-mono"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Reference Snapshot *
                  </label>
                  <select
                    required
                    value={selectedSnapshotId || ''}
                    onChange={(e) => setSelectedSnapshotId(Number(e.target.value))}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                  >
                    {snapshots.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.snapshot_code} ({s.overall_posture_score.toFixed(1)}%)
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Briefing Title *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g., Q3 2026 Executive Cyber Risk & Posture Briefing"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Period Start *
                  </label>
                  <input
                    type="date"
                    required
                    value={periodStart}
                    onChange={(e) => setPeriodStart(e.target.value)}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Period End *
                  </label>
                  <input
                    type="date"
                    required
                    value={periodEnd}
                    onChange={(e) => setPeriodEnd(e.target.value)}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Executive Narrative * (min 10 chars)
                </label>
                <textarea
                  rows={3}
                  required
                  minLength={10}
                  value={executiveSummary}
                  onChange={(e) => setExecutiveSummary(e.target.value)}
                  placeholder="Executive overview of risk trends, exposure remediations, and compliance readiness..."
                  className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Strategic Recommendations
                </label>
                <textarea
                  rows={2}
                  value={strategicRecommendations}
                  onChange={(e) => setStrategicRecommendations(e.target.value)}
                  placeholder="Strategic security budget recommendations and focus areas..."
                  className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsCreateOpen(false)}
                  className="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg disabled:opacity-50"
                >
                  {submitting ? 'Generating...' : 'Create Draft'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
