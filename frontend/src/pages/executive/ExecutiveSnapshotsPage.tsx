import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ShieldCheck,
  Plus,
  RefreshCw,
  ChevronRight,
  Download,
  Hash,
} from 'lucide-react';
import { executiveService } from '../../lib/executiveService';
import { ExecutiveSnapshotModal } from '../../components/executive/ExecutiveSnapshotModal';
import type { ExecutiveSnapshot } from '../../types';
import { useAuth } from '../../context/AuthContext';

export const ExecutiveSnapshotsPage: React.FC = () => {
  const { user } = useAuth();
  const [snapshots, setSnapshots] = useState<ExecutiveSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [exportingId, setExportingId] = useState<number | null>(null);

  const canManage = user?.role === 'ADMIN' || user?.role === 'MANAGER' || user?.role === 'GRC_ANALYST';

  const loadSnapshots = async () => {
    try {
      const data = await executiveService.listSnapshots();
      setSnapshots(data);
    } catch (err) {
      console.error('Failed to load snapshots:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSnapshots();
  }, []);

  const handleExport = async (snapshotId: number, format: 'PDF' | 'JSON') => {
    setExportingId(snapshotId);
    try {
      const artifact = await executiveService.exportSnapshot(snapshotId, format);
      await executiveService.downloadExport(artifact.id, artifact.original_filename);
    } catch (err) {
      console.error('Failed to export snapshot:', err);
    } finally {
      setExportingId(null);
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
              Immutable Snapshots
            </span>
          </nav>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
            Cryptographic Posture Snapshots
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Immutable, point-in-time governance records anchored with deterministic SHA-256 integrity hashes.
          </p>
        </div>

        {canManage && (
          <button
            onClick={() => setIsModalOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-all shadow-sm"
          >
            <Plus className="h-4 w-4" />
            Capture Snapshot
          </button>
        )}
      </div>

      {/* Snapshots List */}
      {loading ? (
        <div className="flex min-h-[300px] items-center justify-center">
          <RefreshCw className="h-6 w-6 animate-spin text-indigo-600" />
        </div>
      ) : snapshots.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-200 dark:border-slate-800 p-12 text-center">
          <ShieldCheck className="h-10 w-10 text-slate-400 mx-auto mb-3" />
          <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200">No Snapshots Found</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            Capture an immutable snapshot to freeze live posture metrics, control evaluations, and source manifest lineage.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {snapshots.map((snap) => (
            <div
              key={snap.id}
              className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4"
            >
              <div className="space-y-1.5 max-w-lg">
                <div className="flex items-center gap-2.5">
                  <span className="font-mono text-sm font-black text-indigo-600 dark:text-indigo-400">
                    {snap.snapshot_code}
                  </span>
                  <span className="text-xs text-slate-400">
                    {new Date(snap.calculated_at).toLocaleString()}
                  </span>
                </div>

                <div className="flex items-center gap-1.5 text-[11px] font-mono text-slate-500 dark:text-slate-400">
                  <Hash className="h-3 w-3 shrink-0 text-slate-400" />
                  <span className="truncate">Hash: {snap.data_hash_sha256}</span>
                </div>
              </div>

              {/* Metrics Grid in Row */}
              <div className="flex items-center gap-4 text-xs">
                <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 text-center min-w-[5.5rem]">
                  <span className="text-[10px] text-slate-400 block">Posture</span>
                  <span className="text-sm font-extrabold text-indigo-600 dark:text-indigo-400">
                    {snap.overall_posture_score.toFixed(1)}%
                  </span>
                </div>

                <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 text-center min-w-[5.5rem]">
                  <span className="text-[10px] text-slate-400 block">ALE Exposure</span>
                  <span className="text-sm font-bold text-slate-800 dark:text-slate-200">
                    ${(snap.financial_exposure_ale / 1000).toFixed(1)}k
                  </span>
                </div>

                <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 text-center min-w-[5.5rem]">
                  <span className="text-[10px] text-slate-400 block">Audit Ready</span>
                  <span className="text-sm font-bold text-cyan-600 dark:text-cyan-400">
                    {snap.audit_readiness_index.toFixed(0)}%
                  </span>
                </div>

                {/* Export Buttons */}
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleExport(snap.id, 'PDF')}
                    disabled={exportingId === snap.id}
                    className="p-2 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-100 dark:hover:bg-indigo-900 border border-indigo-200 dark:border-indigo-800 transition-colors shadow-sm disabled:opacity-50 text-xs font-semibold flex items-center gap-1"
                    title="Export Forensic PDF"
                  >
                    <Download className="h-3.5 w-3.5" /> PDF
                  </button>

                  <button
                    onClick={() => handleExport(snap.id, 'JSON')}
                    disabled={exportingId === snap.id}
                    className="p-2 rounded-lg bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700 transition-colors shadow-sm disabled:opacity-50 text-xs font-semibold"
                    title="Export Deterministic JSON"
                  >
                    JSON
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <ExecutiveSnapshotModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={loadSnapshots}
      />
    </div>
  );
};
