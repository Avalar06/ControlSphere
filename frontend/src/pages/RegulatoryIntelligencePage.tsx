import React, { useState, useEffect } from 'react';
import {
  Scale,
  BookOpen,
  AlertCircle,
  Shield,
  RefreshCw,
} from 'lucide-react';
import { regulatoryService } from '../lib/regulatoryService';
import type {
  RegulatorySource,
  RegulatoryMandate,
  RegulatoryObligation,
  RegulatoryChangeEvent,
  RegulatoryImpactLevel,
} from '../types';

export const RegulatoryIntelligencePage: React.FC = () => {
  const [sources, setSources] = useState<RegulatorySource[]>([]);
  const [mandates, setMandates] = useState<RegulatoryMandate[]>([]);
  const [obligations, setObligations] = useState<RegulatoryObligation[]>([]);
  const [changes, setChanges] = useState<RegulatoryChangeEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedMandateId, setSelectedMandateId] = useState<number | null>(null);

  // Review modal state
  const [reviewingChange, setReviewingChange] = useState<RegulatoryChangeEvent | null>(null);
  const [impactLevel, setImpactLevel] = useState<RegulatoryImpactLevel>('HIGH');
  const [gapSummary, setGapSummary] = useState('');
  const [actionPlan, setActionPlan] = useState('');
  const [reviewNotes, setReviewNotes] = useState('');

  const fetchData = async () => {
    setLoading(true);
    try {
      const [srcRes, mandRes, obRes, chgRes] = await Promise.all([
        regulatoryService.listSources(),
        regulatoryService.listMandates(),
        regulatoryService.listObligations(selectedMandateId || undefined),
        regulatoryService.listChanges(),
      ]);
      setSources(srcRes);
      setMandates(mandRes);
      setObligations(obRes);
      setChanges(chgRes);
    } catch (err) {
      console.error('Failed to load regulatory data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [selectedMandateId]);

  const handleSubmitReview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reviewingChange || !gapSummary.trim()) return;

    try {
      await regulatoryService.reviewChange(reviewingChange.id, {
        impact_level: impactLevel,
        gap_analysis_summary: gapSummary,
        action_plan: actionPlan,
        review_notes: reviewNotes,
      });
      setReviewingChange(null);
      setGapSummary('');
      setActionPlan('');
      setReviewNotes('');
      fetchData();
    } catch (err) {
      console.error('Failed to submit regulatory change review', err);
    }
  };

  const handleApproveChange = async (id: number) => {
    try {
      await regulatoryService.approveChange(id, { review_notes: 'Approved via Regulatory Intelligence Console.' });
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Four-Eyes check failed: Creator cannot approve own change event.');
    }
  };

  const handleDismissChange = async (id: number) => {
    const reason = prompt('Please provide dismissal rationale:');
    if (!reason) return;
    try {
      await regulatoryService.dismissChange(id, { dismissal_reason: reason });
      fetchData();
    } catch (err) {
      console.error('Failed to dismiss regulatory change', err);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'APPROVED':
      case 'ACTIVE':
      case 'COMPLIANT':
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
      case 'REVIEWED':
      case 'UNDER_REVIEW':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      case 'STAGED':
      case 'NEEDS_REVIEW':
      case 'PARTIALLY_COMPLIANT':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
      case 'DISMISSED':
      case 'NON_COMPLIANT':
        return 'bg-rose-500/20 text-rose-400 border-rose-500/30';
      default:
        return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <RefreshCw className="h-8 w-8 animate-spin text-primary-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <Scale className="h-7 w-7 text-primary-500" />
            Regulatory Intelligence & Mandates
          </h1>
          <p className="text-sm text-slate-400">
            Authoritative regulatory sources, statutory mandates, compliance obligations, and Four-Eyes change review workflows.
          </p>
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase">
            <span>Regulatory Sources</span>
            <BookOpen className="h-4 w-4 text-primary-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-white">{sources.length}</div>
          <div className="mt-1 text-xs text-slate-500">SEC, EBA, NIST, ISO Authorities</div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase">
            <span>Statutory Mandates</span>
            <Scale className="h-4 w-4 text-blue-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-white">{mandates.length}</div>
          <div className="mt-1 text-xs text-slate-500">Active Legal & Regulatory Directives</div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase">
            <span>Mapped Obligations</span>
            <Shield className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-white">{obligations.length}</div>
          <div className="mt-1 text-xs text-slate-500">Atomic Control-Mapped Requirements</div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase">
            <span>Regulatory Change Events</span>
            <AlertCircle className="h-4 w-4 text-amber-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-white">{changes.length}</div>
          <div className="mt-1 text-xs text-slate-500">Staged & Under Review</div>
        </div>
      </div>

      {/* Regulatory Change Feed (Four-Eyes Workflow) */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
        <h2 className="text-lg font-bold text-white flex items-center gap-2 mb-4">
          <AlertCircle className="h-5 w-5 text-amber-400" />
          Regulatory Change Feed & Four-Eyes Governance ({changes.length})
        </h2>

        {changes.length === 0 ? (
          <div className="text-xs text-slate-500">No regulatory change events recorded.</div>
        ) : (
          <div className="divide-y divide-slate-800 overflow-hidden rounded-lg border border-slate-800 bg-slate-950/40">
            {changes.map((chg) => (
              <div key={chg.id} className="p-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between hover:bg-slate-900/40 transition">
                <div className="space-y-1.5 max-w-3xl">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold ${getStatusBadge(chg.status)}`}>
                      {chg.status}
                    </span>
                    <span className="rounded bg-slate-800 px-2 py-0.5 text-xs font-mono text-slate-300">
                      {chg.change_type}
                    </span>
                    <span className="text-xs font-mono text-slate-500">{chg.change_code}</span>
                    <span className="text-xs text-slate-500">Pub: {chg.official_publication_date}</span>
                  </div>
                  <div className="text-sm font-semibold text-white">{chg.title}</div>
                  <div className="text-xs text-slate-400 line-clamp-2">{chg.raw_summary}</div>
                </div>

                <div className="flex items-center gap-2">
                  {chg.status === 'STAGED' && (
                    <button
                      onClick={() => setReviewingChange(chg)}
                      className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-500 transition"
                    >
                      Perform Review
                    </button>
                  )}

                  {chg.status === 'REVIEWED' && (
                    <button
                      onClick={() => handleApproveChange(chg.id)}
                      className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-500 transition"
                    >
                      Four-Eyes Approve
                    </button>
                  )}

                  {chg.status !== 'DISMISSED' && chg.status !== 'APPROVED' && (
                    <button
                      onClick={() => handleDismissChange(chg.id)}
                      className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs font-semibold text-slate-400 hover:bg-slate-800 hover:text-white transition"
                    >
                      Dismiss
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Mandates and Obligations Table */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Mandates List */}
        <div className="lg:col-span-1 rounded-xl border border-slate-800 bg-slate-900/50 p-6">
          <h2 className="text-md font-bold text-white mb-4">Statutory Mandates</h2>
          <div className="space-y-2">
            {mandates.map((m) => (
              <button
                key={m.id}
                onClick={() => setSelectedMandateId(m.id === selectedMandateId ? null : m.id)}
                className={`w-full text-left p-3 rounded-lg border transition ${
                  selectedMandateId === m.id
                    ? 'border-primary-500/50 bg-primary-500/10'
                    : 'border-slate-800 bg-slate-950/40 hover:bg-slate-900'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-semibold text-primary-400">{m.mandate_code}</span>
                  <span className="text-[10px] font-mono text-slate-500">{m.jurisdiction}</span>
                </div>
                <div className="text-xs font-medium text-white mt-1">{m.short_name}</div>
                <div className="text-[11px] text-slate-400 truncate mt-0.5">{m.title}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Obligations Detail */}
        <div className="lg:col-span-2 rounded-xl border border-slate-800 bg-slate-900/50 p-6">
          <h2 className="text-md font-bold text-white mb-4">
            Statutory Obligations {selectedMandateId ? `(Mandate #${selectedMandateId})` : '(All)'}
          </h2>
          <div className="space-y-3">
            {obligations.map((o) => (
              <div key={o.id} className="p-4 rounded-lg border border-slate-800 bg-slate-950/40 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-white">{o.obligation_code}</span>
                    {o.article_reference && (
                      <span className="rounded bg-slate-800 px-2 py-0.5 text-[11px] font-mono text-slate-300">
                        {o.article_reference}
                      </span>
                    )}
                  </div>
                  <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold ${getStatusBadge(o.compliance_status)}`}>
                    {o.compliance_status}
                  </span>
                </div>
                <div className="text-xs font-semibold text-slate-200">{o.title}</div>
                <div className="text-xs text-slate-400">{o.description}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Review Modal */}
      {reviewingChange && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-xl border border-slate-800 bg-slate-900 p-6 shadow-xl">
            <h3 className="text-lg font-bold text-white mb-1">Review Regulatory Change</h3>
            <p className="text-xs text-slate-400 mb-4">{reviewingChange.title} ({reviewingChange.change_code})</p>

            <form onSubmit={handleSubmitReview} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">Impact Level</label>
                <select
                  value={impactLevel}
                  onChange={(e) => setImpactLevel(e.target.value as RegulatoryImpactLevel)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:outline-none"
                >
                  <option value="CRITICAL">CRITICAL</option>
                  <option value="HIGH">HIGH</option>
                  <option value="MEDIUM">MEDIUM</option>
                  <option value="LOW">LOW</option>
                  <option value="INFORMATIONAL">INFORMATIONAL</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">Gap Analysis Summary</label>
                <textarea
                  required
                  rows={3}
                  placeholder="Identify compliance gaps against current controls..."
                  value={gapSummary}
                  onChange={(e) => setGapSummary(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">Action Plan</label>
                <textarea
                  rows={2}
                  placeholder="Recommended policy amendments or technical implementations..."
                  value={actionPlan}
                  onChange={(e) => setActionPlan(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setReviewingChange(null)}
                  className="rounded-lg border border-slate-700 px-4 py-2 text-xs font-medium text-slate-300 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-lg bg-primary-600 px-4 py-2 text-xs font-medium text-white hover:bg-primary-500"
                >
                  Submit Impact Review
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
