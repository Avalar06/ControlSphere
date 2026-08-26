import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft,
  CheckCircle2,
  Layers,
  RefreshCw,
  Search,
  ShieldCheck,
  Split,
  XCircle,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { harmonizationService } from '../lib/harmonizationService';
import type {
  FrameworkDetailedPostureResponse,
  SubcategoryComplianceMatrixItem,
} from '../types';

export const FrameworkPosturePage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const frameworkId = Number(id);
  const navigate = useNavigate();
  const { hasRole } = useAuth();
  const canExecute = hasRole('ADMIN', 'GRC_ANALYST', 'SECURITY_ANALYST', 'MANAGER');

  const [posture, setPosture] = useState<FrameworkDetailedPostureResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState(false);
  const [evalMessage, setEvalMessage] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState('');
  const [coverageFilter, setCoverageFilter] = useState<'ALL' | 'DIRECT' | 'INHERITED' | 'UNMAPPED'>('ALL');
  const [healthFilter, setHealthFilter] = useState<string>('ALL');

  const fetchPosture = async () => {
    if (!frameworkId) return;
    setLoading(true);
    try {
      const data = await harmonizationService.getFrameworkPosture(frameworkId);
      setPosture(data);
    } catch (err) {
      console.error('Failed to load framework posture matrix:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPosture();
  }, [frameworkId]);

  const handleEvaluate = async () => {
    if (!canExecute || !frameworkId) return;
    setEvaluating(true);
    setEvalMessage(null);
    try {
      const snap = await harmonizationService.evaluateFramework(frameworkId);
      setEvalMessage(`Snapshot created: ${snap.coverage_percentage.toFixed(1)}% coverage, ${snap.compliance_health_score.toFixed(1)}% compliance score.`);
      await fetchPosture();
    } catch (err: any) {
      setEvalMessage(err.response?.data?.detail || 'Evaluation failed.');
    } finally {
      setEvaluating(false);
    }
  };

  const getCoverageBadge = (item: SubcategoryComplianceMatrixItem) => {
    if (item.is_directly_covered) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-emerald-950/80 text-emerald-300 border border-emerald-800/80">
          <ShieldCheck className="h-3 w-3" />
          DIRECT
        </span>
      );
    }
    if (item.is_crosswalk_covered) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-indigo-950/80 text-indigo-300 border border-indigo-800/80">
          <Split className="h-3 w-3" />
          INHERITED
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-slate-800 text-slate-400">
        <XCircle className="h-3 w-3" />
        NOT COVERED
      </span>
    );
  };

  const getHealthBadge = (score: number, status: string) => {
    if (status === 'UNMAPPED' || score === 0) {
      return <span className="text-xs text-slate-500">Unmapped</span>;
    }
    if (score >= 80) {
      return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-950/80 text-emerald-300 border border-emerald-800/80">{score.toFixed(1)}% (Healthy)</span>;
    }
    if (score >= 60) {
      return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-950/80 text-blue-300 border border-blue-800/80">{score.toFixed(1)}% (Degraded)</span>;
    }
    if (score >= 40) {
      return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-950/80 text-amber-300 border border-amber-800/80">{score.toFixed(1)}% (At Risk)</span>;
    }
    return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-rose-950/80 text-rose-300 border border-rose-800/80">{score.toFixed(1)}% (Failing)</span>;
  };

  const filteredItems = posture?.subcategories.filter((item) => {
    if (coverageFilter === 'DIRECT' && !item.is_directly_covered) return false;
    if (coverageFilter === 'INHERITED' && !item.is_crosswalk_covered) return false;
    if (coverageFilter === 'UNMAPPED' && (item.is_directly_covered || item.is_crosswalk_covered)) return false;

    if (healthFilter !== 'ALL' && item.health_status !== healthFilter) return false;

    if (search) {
      const q = search.toLowerCase();
      const codeMatch = item.subcategory_identifier.toLowerCase().includes(q);
      const titleMatch = item.subcategory_title.toLowerCase().includes(q);
      const srcMatch = item.source_identifier?.toLowerCase().includes(q);
      if (!codeMatch && !titleMatch && !srcMatch) return false;
    }
    return true;
  }) || [];

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <RefreshCw className="h-8 w-8 text-indigo-500 animate-spin" />
      </div>
    );
  }

  if (!posture) {
    return (
      <div className="text-center py-16">
        <h2 className="text-xl font-bold text-slate-100">Framework Posture Not Found</h2>
        <Link to="/harmonization" className="mt-4 inline-flex items-center gap-2 text-indigo-400 text-sm">
          <ArrowLeft className="h-4 w-4" /> Back to Harmonization
        </Link>
      </div>
    );
  }

  const { overview } = posture;

  return (
    <div className="space-y-6 pb-12">
      {/* Header Breadcrumbs & Actions */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <button
            onClick={() => navigate('/harmonization')}
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition mb-2"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to Harmonization Overview
          </button>
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-indigo-950/80 border border-indigo-700/60 flex items-center justify-center text-indigo-400">
              <Layers className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">
                  {overview.framework_identifier}
                </span>
                <span className="text-xs text-slate-500">•</span>
                <span className="text-xs text-slate-400">Detailed Posture Breakdown</span>
              </div>
              <h1 className="text-2xl font-bold text-slate-100 tracking-tight">{overview.framework_name}</h1>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {canExecute && (
            <button
              onClick={handleEvaluate}
              disabled={evaluating}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition shadow-sm disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 ${evaluating ? 'animate-spin' : ''}`} />
              {evaluating ? 'Evaluating Framework...' : 'Evaluate Framework'}
            </button>
          )}
        </div>
      </div>

      {evalMessage && (
        <div className="p-4 rounded-lg bg-indigo-950/40 border border-indigo-800/60 text-indigo-200 text-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-indigo-400 shrink-0" />
            <span>{evalMessage}</span>
          </div>
          <button onClick={() => setEvalMessage(null)} className="text-slate-400 hover:text-slate-200">
            &times;
          </button>
        </div>
      )}

      {/* Posture Scoreboard */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Coverage Rate</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-emerald-400">{overview.coverage_percentage.toFixed(1)}%</span>
            <span className="text-xs text-slate-500">
              ({overview.total_covered_subcategories} / {overview.total_subcategories})
            </span>
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Compliance Health</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-blue-400">{overview.compliance_health_score.toFixed(1)}%</span>
            <span className="text-xs text-slate-500">Authoritative</span>
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Direct Coverage</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-slate-100">{overview.directly_covered_subcategories}</span>
            <span className="text-xs text-slate-500">Directly Implemented</span>
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Inherited (Crosswalk)</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-indigo-400">{overview.crosswalk_covered_subcategories}</span>
            <span className="text-xs text-slate-500">Harmonized</span>
          </div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-900/40 p-4 rounded-xl border border-slate-800/80">
        <div className="flex items-center gap-3 flex-1">
          <div className="relative flex-1 max-w-md">
            <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Search outcome identifier or title..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <select
            value={coverageFilter}
            onChange={(e) => setCoverageFilter(e.target.value as any)}
            className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-sm text-slate-300 focus:outline-none focus:border-indigo-500"
          >
            <option value="ALL">All Coverage Types</option>
            <option value="DIRECT">Direct Coverage Only</option>
            <option value="INHERITED">Inherited (Crosswalk) Only</option>
            <option value="UNMAPPED">Not Covered / Unmapped</option>
          </select>

          <select
            value={healthFilter}
            onChange={(e) => setHealthFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-sm text-slate-300 focus:outline-none focus:border-indigo-500"
          >
            <option value="ALL">All Health Bands</option>
            <option value="HEALTHY">Healthy (&ge; 80%)</option>
            <option value="DEGRADED">Degraded (60 - 79%)</option>
            <option value="AT_RISK">At Risk (40 - 59%)</option>
            <option value="FAILING">Failing (&lt; 40%)</option>
            <option value="UNMAPPED">Unmapped</option>
          </select>
        </div>

        <div className="text-xs text-slate-500">
          Showing {filteredItems.length} of {posture.subcategories.length} outcomes
        </div>
      </div>

      {/* Posture Matrix Table */}
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl overflow-hidden shadow-sm">
        <table className="w-full text-left text-sm text-slate-300">
          <thead className="bg-slate-950/80 text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-800">
            <tr>
              <th className="px-5 py-3.5">Outcome Identifier</th>
              <th className="px-5 py-3.5">Outcome Description</th>
              <th className="px-5 py-3.5">Coverage Status</th>
              <th className="px-5 py-3.5">Source Control</th>
              <th className="px-5 py-3.5">Crosswalk Confidence</th>
              <th className="px-5 py-3.5">Effective Health</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {filteredItems.map((item) => (
              <tr key={item.subcategory_id} className="hover:bg-slate-800/30 transition">
                <td className="px-5 py-3.5 font-mono text-xs text-indigo-400 font-semibold whitespace-nowrap">
                  {item.subcategory_identifier}
                </td>
                <td className="px-5 py-3.5">
                  <div className="font-medium text-slate-200">{item.subcategory_title}</div>
                  <div className="text-[11px] text-slate-500">
                    {item.function_identifier} &bull; {item.category_identifier}
                  </div>
                </td>
                <td className="px-5 py-3.5 whitespace-nowrap">{getCoverageBadge(item)}</td>
                <td className="px-5 py-3.5 font-mono text-xs whitespace-nowrap">
                  {item.is_directly_covered ? (
                    <span className="text-slate-300">Self (Direct)</span>
                  ) : item.is_crosswalk_covered ? (
                    <span className="text-indigo-400">{item.source_identifier || `Subcat #${item.source_subcategory_id}`}</span>
                  ) : (
                    <span className="text-slate-600">—</span>
                  )}
                </td>
                <td className="px-5 py-3.5 font-mono text-xs text-slate-300 whitespace-nowrap">
                  {item.crosswalk_confidence ? `${(item.crosswalk_confidence * 100).toFixed(0)}%` : item.is_directly_covered ? '100%' : '—'}
                </td>
                <td className="px-5 py-3.5 whitespace-nowrap">
                  {getHealthBadge(item.effective_health_score, item.health_status)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {filteredItems.length === 0 && (
          <div className="text-center py-12">
            <Layers className="h-8 w-8 text-slate-600 mx-auto mb-2" />
            <p className="text-slate-400 text-sm">No framework subcategories match your filters.</p>
          </div>
        )}
      </div>
    </div>
  );
};
