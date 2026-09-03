import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Layers,
  Plus,
  RefreshCw,
  ChevronRight,
  Clock,
  CheckCircle2,
  FileCheck,
} from 'lucide-react';
import { executiveService } from '../../lib/executiveService';
import { DossierCompilerModal } from '../../components/executive/DossierCompilerModal';
import type { ExecutiveDossier, DossierStatus } from '../../types';
import { useAuth } from '../../context/AuthContext';

export const RegulatoryDossiersPage: React.FC = () => {
  const { user } = useAuth();
  const [dossiers, setDossiers] = useState<ExecutiveDossier[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<DossierStatus | undefined>(undefined);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  const canManage = user?.role === 'ADMIN' || user?.role === 'MANAGER' || user?.role === 'GRC_ANALYST';

  const loadDossiers = async () => {
    try {
      const data = await executiveService.listDossiers({ status: statusFilter });
      setDossiers(data);
    } catch (err) {
      console.error('Failed to load regulatory dossiers:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDossiers();
  }, [statusFilter]);

  const getStatusBadge = (status: DossierStatus) => {
    switch (status) {
      case 'FINALIZED':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800">
            <CheckCircle2 className="h-3 w-3" /> FINALIZED
          </span>
        );
      case 'COMPILED':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800">
            <FileCheck className="h-3 w-3" /> COMPILED
          </span>
        );
      case 'UNDER_REVIEW':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-amber-50 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 border border-amber-200 dark:border-amber-800">
            <Clock className="h-3 w-3" /> UNDER REVIEW
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
              Regulatory Dossiers
            </span>
          </nav>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
            Multi-Framework Regulatory Dossiers
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Formal compliance manifests compiled from live controls, evidence, and audit trails with Four-Eyes sign-off.
          </p>
        </div>

        {canManage && (
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-all shadow-sm"
          >
            <Plus className="h-4 w-4" />
            New Regulatory Dossier
          </button>
        )}
      </div>

      {/* Filter Bar */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2 border-b border-slate-200 dark:border-slate-800 text-xs">
        {(['ALL', 'DRAFT', 'COMPILED', 'FINALIZED'] as const).map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s === 'ALL' ? undefined : (s as DossierStatus))}
            className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
              (s === 'ALL' && statusFilter === undefined) || statusFilter === s
                ? 'bg-indigo-600 text-white font-semibold shadow-sm'
                : 'bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800'
            }`}
          >
            {s.replace('_', ' ')}
          </button>
        ))}
      </div>

      {/* Dossiers List */}
      {loading ? (
        <div className="flex min-h-[300px] items-center justify-center">
          <RefreshCw className="h-6 w-6 animate-spin text-indigo-600" />
        </div>
      ) : dossiers.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-200 dark:border-slate-800 p-12 text-center">
          <Layers className="h-10 w-10 text-slate-400 mx-auto mb-3" />
          <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200">No Dossiers Found</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            Create a regulatory compliance dossier to package multi-framework evidence for board review or audit submission.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {dossiers.map((dossier) => (
            <Link
              key={dossier.id}
              to={`/executive/dossiers/${dossier.id}`}
              className="group p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm hover:border-indigo-500/60 hover:shadow-md transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="font-mono text-xs font-bold text-indigo-600 dark:text-indigo-400">
                    {dossier.dossier_code}
                  </span>
                  {getStatusBadge(dossier.status)}
                </div>

                <h3 className="font-bold text-slate-900 dark:text-white text-base group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                  {dossier.title}
                </h3>

                <p className="text-xs text-slate-500 dark:text-slate-400 mt-2 line-clamp-2">
                  {dossier.executive_summary || dossier.description || 'No summary statement provided.'}
                </p>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-[11px] text-slate-400">
                <span>Type: <strong className="text-slate-600 dark:text-slate-300">{dossier.dossier_type.replace('_', ' ')}</strong></span>
                <span>{new Date(dossier.created_at).toLocaleDateString()}</span>
              </div>
            </Link>
          ))}
        </div>
      )}

      <DossierCompilerModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={loadDossiers}
      />
    </div>
  );
};
