import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ChevronRight,
  Download,
  FileCheck,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';
import { executiveService } from '../../lib/executiveService';
import type { ExecutiveDossier } from '../../types';
import { useAuth } from '../../context/AuthContext';

export const DossierDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();

  const [dossier, setDossier] = useState<ExecutiveDossier | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const dossierId = Number(id);

  const loadDossier = async () => {
    try {
      const data = await executiveService.getDossier(dossierId);
      setDossier(data);
    } catch (err) {
      console.error('Failed to load dossier:', err);
      setError('Dossier not found or unauthorized access.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDossier();
  }, [dossierId]);

  const handleCompile = async () => {
    setActionLoading(true);
    setError(null);
    try {
      const updated = await executiveService.compileDossier(dossierId);
      setDossier(updated);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to compile dossier');
    } finally {
      setActionLoading(false);
    }
  };

  const handleFinalize = async () => {
    setActionLoading(true);
    setError(null);
    try {
      const updated = await executiveService.finalizeDossier(dossierId);
      setDossier(updated);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to finalize dossier');
    } finally {
      setActionLoading(false);
    }
  };

  const handleExport = async (format: 'PDF' | 'JSON') => {
    setActionLoading(true);
    try {
      const artifact = await executiveService.exportDossier(dossierId, format);
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

  if (!dossier) {
    return (
      <div className="p-8 text-center">
        <p className="text-slate-500">{error || 'Dossier not found.'}</p>
        <Link to="/executive/dossiers" className="mt-4 inline-block text-indigo-600 font-semibold text-sm">
          Return to Dossiers
        </Link>
      </div>
    );
  }

  const isFinalized = dossier.status === 'FINALIZED';
  const isCompiled = dossier.status === 'COMPILED';
  const canFinalize = (user?.role === 'ADMIN' || user?.role === 'MANAGER') && user.id !== dossier.created_by_id && user.id !== dossier.compiled_by_id;

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
            <Link to="/executive/dossiers" className="hover:underline">
              Dossiers
            </Link>
            <ChevronRight className="h-3 w-3" />
            <span className="font-semibold text-slate-800 dark:text-slate-200">{dossier.dossier_code}</span>
          </nav>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">{dossier.title}</h1>
            <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800">
              {dossier.status}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {!isFinalized && (
            <button
              onClick={handleCompile}
              disabled={actionLoading}
              className="px-3.5 py-2 rounded-xl bg-slate-800 text-white text-xs font-semibold hover:bg-slate-700 shadow-sm flex items-center gap-1.5 disabled:opacity-50"
            >
              <FileCheck className="h-4 w-4" />
              {isCompiled ? 'Re-Compile Dossier' : 'Compile Dossier'}
            </button>
          )}

          {isCompiled && !isFinalized && canFinalize && (
            <button
              onClick={handleFinalize}
              disabled={actionLoading}
              className="px-3.5 py-2 rounded-xl bg-emerald-600 text-white text-xs font-semibold hover:bg-emerald-500 shadow-sm flex items-center gap-1.5 disabled:opacity-50"
            >
              <CheckCircle2 className="h-4 w-4" />
              Four-Eyes Finalize
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

      {/* Main Metadata & Narrative */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {/* Executive Statement Card */}
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-sm">
            <h3 className="font-bold text-slate-900 dark:text-white text-sm mb-2">Executive Statement</h3>
            <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
              {dossier.executive_summary || 'No executive statement supplied.'}
            </p>

            {dossier.regulatory_commentary && (
              <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800">
                <h4 className="font-bold text-slate-900 dark:text-white text-xs mb-1">Regulatory Commentary</h4>
                <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                  {dossier.regulatory_commentary}
                </p>
              </div>
            )}
          </div>

          {/* Compiled Sections */}
          {dossier.compiled_sections && (
            <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-sm">
              <h3 className="font-bold text-slate-900 dark:text-white text-sm mb-4">
                Compiled Evidence & Posture Snapshot
              </h3>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
                <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800">
                  <span className="text-[11px] text-slate-400 block">Overall Posture</span>
                  <span className="text-lg font-black text-indigo-600 dark:text-indigo-400">
                    {dossier.compiled_sections.overall_posture_score?.toFixed(1)}%
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800">
                  <span className="text-[11px] text-slate-400 block">Inherent Risk</span>
                  <span className="text-lg font-black text-amber-500">
                    {dossier.compiled_sections.inherent_risk_index?.toFixed(1)}
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800">
                  <span className="text-[11px] text-slate-400 block">Residual Risk</span>
                  <span className="text-lg font-black text-emerald-500">
                    {dossier.compiled_sections.residual_risk_index?.toFixed(1)}
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800">
                  <span className="text-[11px] text-slate-400 block">Audit Readiness</span>
                  <span className="text-lg font-black text-cyan-500">
                    {dossier.compiled_sections.audit_readiness_index?.toFixed(1)}%
                  </span>
                </div>
              </div>

              {/* Frameworks Scope */}
              {dossier.compiled_sections.framework_scope && (
                <div>
                  <h4 className="text-xs font-bold text-slate-700 dark:text-slate-300 mb-2">
                    Harmonized Framework Scope
                  </h4>
                  <div className="space-y-2">
                    {dossier.compiled_sections.framework_scope.map((fw: any, i: number) => (
                      <div
                        key={i}
                        className="p-3 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 flex justify-between items-center text-xs"
                      >
                        <span className="font-semibold text-slate-800 dark:text-slate-200">
                          {fw.framework_name} ({fw.framework_code})
                        </span>
                        <span className="text-slate-500">{fw.controls_count} In-Scope Controls</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Sidebar Audit Metadata */}
        <div className="space-y-6">
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-sm text-xs space-y-3">
            <h3 className="font-bold text-slate-900 dark:text-white text-sm pb-2 border-b border-slate-100 dark:border-slate-800">
              Audit Trail & Lineage
            </h3>

            <div>
              <span className="text-slate-400 block">Dossier Code</span>
              <span className="font-mono font-bold text-slate-800 dark:text-slate-200">
                {dossier.dossier_code}
              </span>
            </div>

            <div>
              <span className="text-slate-400 block">Dossier Type</span>
              <span className="font-semibold text-slate-800 dark:text-slate-200">
                {dossier.dossier_type.replace('_', ' ')}
              </span>
            </div>

            <div>
              <span className="text-slate-400 block">Created At</span>
              <span className="text-slate-700 dark:text-slate-300">
                {new Date(dossier.created_at).toLocaleString()}
              </span>
            </div>

            {dossier.compiled_at && (
              <div>
                <span className="text-slate-400 block">Compiled At</span>
                <span className="text-slate-700 dark:text-slate-300">
                  {new Date(dossier.compiled_at).toLocaleString()}
                </span>
              </div>
            )}

            {dossier.finalized_at && (
              <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
                <span className="text-emerald-500 font-semibold block">Finalized Sign-Off</span>
                <span className="text-slate-700 dark:text-slate-300">
                  {new Date(dossier.finalized_at).toLocaleString()}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
